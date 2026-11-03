"""Reconnaissance des données présentes dans le dossier --images.

Types reconnus :
  - scène Sentinel-2 exportée du Copernicus Browser : fichiers « AAAA-MM-JJ-…_L2A_B04_(Raw).tiff »,
    dans des dossiers ou des .zip (une scène par date) ;
  - produit Sentinel-2 L2A officiel (.SAFE, dossier ou .zip) : bandes JP2 et SCL ;
  - orthomosaïque de drone : GeoTIFF de 3 ou 4 bandes, résolution inférieure à `drone_resolution_max_m` ;
  - photos de feuilles : JPG ou PNG non géoréférencés (coordonnées GPS lues dans l'EXIF si présentes).
Tout le reste est listé avec la raison pour laquelle il est ignoré.
"""
import math
import re
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

RE_COPERNICUS = re.compile(r"^(\d{4}-\d{2}-\d{2}).*_L2A_(B\d{1,2}A?|True_color|Scene_classification_map_?)"
                           r"(?:_\(Raw\))?\.tiff?$", re.IGNORECASE)
RE_SAFE = re.compile(r"S2[ABC]_MSIL2A_(\d{8})T\d{6}.*\.SAFE", re.IGNORECASE)
RE_BANDE_SAFE = re.compile(r"_(B\d{1,2}A?|SCL)_(10|20|60)m\.jp2$", re.IGNORECASE)
EXT_PHOTOS = {".jpg", ".jpeg", ".png"}
EXT_RASTERS = {".tif", ".tiff"}
BANDES_S2 = ("B04", "B05", "B08", "B8A", "B11")
# Un produit .SAFE contient chaque bande en plusieurs résolutions (10, 20, 60 m) et des bandes inutiles ici :
# on ne retient que les bandes nécessaires, chacune à sa résolution native.
RESOLUTION_NATIVE = {"B04": 10, "B08": 10, "B05": 20, "B8A": 20, "B11": 20, "SCL": 20}
# Fichiers annexes connus (géoréférencement, aperçus, métadonnées) : ignorés sans être signalés
ANNEXES = {".xml", ".html", ".json", ".txt", ".md", ".jp2", ".gml", ".xsd", ".tfw", ".tifw", ".wld", ".kml", ".kmz",
           ".ovr", ".prj", ".aux", ".qpj", ".cpg", ".msk", ".jgw", ".pgw"}


@dataclass
class SceneS2:
    date: str
    format: str                      # "copernicus" ou "safe"
    source: str                      # dossier ou zip d'origine
    bandes: dict = field(default_factory=dict)   # nom -> chemin (ou "zip::membre")
    metadonnees: str = None                      # MTD_MSIL2A.xml des produits .SAFE (décalage BOA_ADD_OFFSET)

    @property
    def complete(self):
        return all(b in self.bandes for b in BANDES_S2 + ("SCL",))


@dataclass
class Ortho:
    chemin: str
    crs: str
    resolution_m: float
    bandes: int
    largeur: int
    hauteur: int


@dataclass
class Photo:
    chemin: str
    lat: float = None
    lon: float = None


@dataclass
class Inventaire:
    scenes: list = field(default_factory=list)
    orthos: list = field(default_factory=list)
    photos: list = field(default_factory=list)
    ignores: list = field(default_factory=list)

    def resume(self):
        dates = sorted({s.date for s in self.scenes})
        return dict(scenes_sentinel2=len(self.scenes), dates=dates,
                    scenes_incompletes=[s.date for s in self.scenes if not s.complete],
                    orthomosaiques=len(self.orthos), photos_feuilles=len(self.photos),
                    photos_localisees=sum(p.lat is not None for p in self.photos), fichiers_ignores=len(self.ignores))

    def en_dict(self):
        return dict(resume=self.resume(), scenes=[asdict(s) for s in self.scenes], orthos=[asdict(o) for o in self.orthos],
                    photos=[asdict(p) for p in self.photos], ignores=self.ignores)


def _ajouter_bande(scenes, date, fmt, source, bande, chemin):
    s = scenes.setdefault((date, source), SceneS2(date=date, format=fmt, source=source))
    if bande in s.bandes:
        raise ValueError(f"deux fichiers pour la bande {bande} à la date {date} ({source})")
    s.bandes[bande] = chemin


def _bande_copernicus(nom):
    m = RE_COPERNICUS.match(nom)
    if not m:
        return None
    bande = m.group(2)
    return m.group(1), "SCL" if bande.lower().startswith("scene") else bande.upper()


def _date_safe(texte):
    m = RE_SAFE.search(texte)
    return f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else None


def _gps_exif(chemin):
    """Latitude et longitude en degrés décimaux, si la photo contient des coordonnées GPS."""
    try:
        from PIL import Image
        gps = Image.open(chemin).getexif().get_ifd(0x8825)
        if not gps or 2 not in gps or 4 not in gps:
            return None, None
        dms = lambda v: float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        lat, lon = dms(gps[2]), dms(gps[4])
        return (-lat if gps.get(1) == "S" else lat), (-lon if gps.get(3) == "W" else lon)
    except Exception:
        return None, None


def _resolution_m(src):
    rx, ry = abs(src.transform.a), abs(src.transform.e)
    if src.crs is not None and src.crs.is_geographic:      # degrés -> mètres, à la latitude du centre
        lat = (src.bounds.top + src.bounds.bottom) / 2
        return min(rx * 111320 * math.cos(math.radians(lat)), ry * 110540)
    return min(rx, ry)


def reconnaitre(dossier, reglages):
    """Parcourt `dossier` et classe chaque fichier. Ne lit que les en-têtes."""
    import rasterio
    from rasterio.errors import NotGeoreferencedWarning
    import warnings

    inv, scenes = Inventaire(), {}
    racine = Path(dossier)
    if not racine.exists():
        raise SystemExit(f"Dossier introuvable : {racine}")
    res_max_drone = reglages["entrees"]["drone_resolution_max_m"]
    s2_min, s2_max = reglages["entrees"]["sentinel2_resolution_m"]

    for p in sorted(racine.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(racine))
        try:
            if p.suffix.lower() == ".zip":
                with zipfile.ZipFile(p) as z:
                    membres = [n for n in z.namelist() if not n.endswith("/")]
                date_safe = next((d for d in map(_date_safe, [p.name] + membres) if d), None)
                trouve = False
                for n in membres:
                    nom = PurePosixPath(n).name
                    if date_safe and RE_BANDE_SAFE.search(nom):
                        bande = RE_BANDE_SAFE.search(nom).group(1).upper()
                        res = int(RE_BANDE_SAFE.search(nom).group(2))
                        if RESOLUTION_NATIVE.get(bande) != res:
                            continue                           # bande inutile, ou autre résolution que la native
                        _ajouter_bande(scenes, date_safe, "safe", p.name, bande, f"{p}::{n}"); trouve = True
                    elif (b := _bande_copernicus(nom)):
                        _ajouter_bande(scenes, b[0], "copernicus", p.name, b[1], f"{p}::{n}"); trouve = True
                if not trouve:
                    inv.ignores.append(dict(fichier=rel, raison="archive sans bande Sentinel-2 reconnue"))
                mtd = next((n for n in membres if PurePosixPath(n).name.upper() == "MTD_MSIL2A.XML"), None)
                if mtd and date_safe and (date_safe, p.name) in scenes:
                    scenes[(date_safe, p.name)].metadonnees = f"{p}::{mtd}"
            elif "SAFE" in p.as_posix().upper() and p.suffix.lower() == ".jp2":
                m = RE_BANDE_SAFE.search(p.name)
                date = _date_safe(p.as_posix())
                if m and date:
                    bande, res = m.group(1).upper(), int(m.group(2))
                    if RESOLUTION_NATIVE.get(bande) == res:
                        dossier_safe = next(q for q in p.parents if q.name.upper().endswith(".SAFE"))
                        _ajouter_bande(scenes, date, "safe", dossier_safe.name, bande, str(p))
                        if (dossier_safe / "MTD_MSIL2A.xml").exists():
                            scenes[(date, dossier_safe.name)].metadonnees = str(dossier_safe / "MTD_MSIL2A.xml")
            elif (b := _bande_copernicus(p.name)):
                _ajouter_bande(scenes, b[0], "copernicus", p.parent.name, b[1], str(p))
            elif p.suffix.lower() in EXT_RASTERS:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", NotGeoreferencedWarning)
                    with rasterio.open(p) as src:
                        if src.crs is None:
                            inv.ignores.append(dict(fichier=rel, raison="GeoTIFF sans système de coordonnées"))
                            continue
                        res = _resolution_m(src)
                        if src.count in (3, 4) and res <= res_max_drone:
                            inv.orthos.append(Ortho(str(p), src.crs.to_string(), round(res, 4), src.count, src.width, src.height))
                        elif s2_min <= res <= s2_max:
                            inv.ignores.append(dict(fichier=rel, raison=f"GeoTIFF de {src.count} bandes à {res:.0f} m : "
                                                    "format Sentinel-2 non reconnu (bandes séparées attendues)"))
                        else:
                            inv.ignores.append(dict(fichier=rel, raison=f"GeoTIFF de {src.count} bandes à {res:.2f} m : type inconnu"))
            elif p.suffix.lower() in EXT_PHOTOS:
                if any(q.upper().endswith(".SAFE") for q in p.parts):
                    continue                                   # aperçus et logos du produit Sentinel-2
                lat, lon = _gps_exif(p)
                inv.photos.append(Photo(str(p), lat, lon))
            elif p.suffix.lower() not in ANNEXES:
                inv.ignores.append(dict(fichier=rel, raison="extension non traitée"))
        except Exception as e:  # un fichier illisible ne doit pas arrêter la reconnaissance
            inv.ignores.append(dict(fichier=rel, raison=f"illisible : {e}"))
    inv.scenes = sorted(scenes.values(), key=lambda s: (s.date, s.source))
    return inv
