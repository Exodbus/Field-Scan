"""Préparation commune des scènes Sentinel-2, partagée par les modules vigueur, stress et temporel.

Pour chaque scène complète qui recouvre les parcelles :
  - lecture des bandes B04, B05, B08, B8A, B11 et de la carte de classification SCL, dans les deux
    formats reconnus : export du Copernicus Browser (bandes déjà sur une même grille, réflectance en
    flottant, SCL en couleurs) ou produit officiel .SAFE (entiers avec décalage BOA_ADD_OFFSET, bandes
    à 20 m rééchantillonnées sur la grille 10 m de B04, SCL en classes numériques) ;
  - mise sur la grille de la première date utile (pour comparer les dates pixel à pixel) ;
  - indices NDVI = (B08-B04)/(B08+B04), NDRE = (B8A-B05)/(B8A+B05), NDMI = (B08-B11)/(B08+B11) ;
  - masque des nuages, cirrus et ombres, plus une marge de quelques pixels autour (bords mal détectés),
    et exclusion de l'eau ;
  - statut de chaque parcelle et de chaque date : ok, non_fiable (trop masquée), insuffisant, trop_petite.
Le résultat est mis en cache dans le contexte : chaque scène n'est lue qu'une fois.
"""
import re
import zipfile
from dataclasses import dataclass, field

import numpy as np
import rasterio
from rasterio import features
from rasterio.warp import Resampling, reproject, transform_bounds
from scipy import ndimage

BANDES = ("B04", "B05", "B08", "B8A", "B11")
INDICES = {"ndvi": ("B08", "B04"), "ndre": ("B8A", "B05"), "ndmi": ("B08", "B11")}
# SCL du Copernicus Browser : image colorée, palette standard -> classe
PALETTE = {(0, 0, 0): "nodata", (255, 0, 0): "sature", (47, 47, 47): "sombre", (100, 50, 0): "ombre_nuage",
           (0, 160, 0): "vegetation", (255, 230, 90): "sol_nu", (0, 0, 255): "eau", (128, 128, 128): "non_classe",
           (192, 192, 192): "nuage_moyen", (255, 255, 255): "nuage_fort", (100, 200, 255): "cirrus",
           (255, 150, 255): "neige"}
# SCL des produits .SAFE : classes numériques 0 à 11, dans le même ordre que la palette
CLASSES_SCL = list(PALETTE.values())
MASQUE = {"nodata", "sature", "sombre", "ombre_nuage", "nuage_moyen", "nuage_fort", "cirrus"}


@dataclass
class DonneesS2:
    dates: list = field(default_factory=list)
    sources: dict = field(default_factory=dict)        # date -> source
    profil: dict = None
    transform: object = None
    crs: object = None
    forme: tuple = None
    indices: dict = field(default_factory=dict)         # (indice, date) -> carte float32 (NaN hors pixels utiles)
    masque: dict = field(default_factory=dict)          # date -> pixels masqués (nuages...)
    idmap: np.ndarray = None                            # 0 hors parcelle, k pour la k-ième parcelle (érodée)
    ids: list = field(default_factory=list)
    statut: dict = field(default_factory=dict)          # (parcelle, date) -> statut
    pct_masque: dict = field(default_factory=dict)
    ecartees: list = field(default_factory=list)        # scènes non utilisées, avec la raison


def _ouvrir(chemin):
    """Chemin d'un fichier, ou « archive.zip::membre » (lecture dans le zip sans extraction)."""
    if "::" in chemin:
        z, m = chemin.split("::", 1)
        return rasterio.open(f"/vsizip/{z}/{m}")
    return rasterio.open(chemin)


def _decalage_safe(scene, journal=None):
    """BOA_ADD_OFFSET des produits .SAFE (-1000 depuis la ligne de traitement 04.00, janvier 2022).

    1. lu dans MTD_MSIL2A.xml (source officielle) ; 2. sinon déduit de la ligne de traitement « _Nxxxx_ »
    présente dans le nom du produit OU dans les chemins des bandes (dossier .SAFE à l'intérieur du zip) ;
    3. sinon 0, avec un avertissement : des indices faux sans message seraient le pire défaut possible.
    """
    if getattr(scene, "_decalage", None) is not None:
        return scene._decalage
    valeur, origine = None, None
    if scene.metadonnees:
        try:
            if "::" in scene.metadonnees:
                z, m = scene.metadonnees.split("::", 1)
                with zipfile.ZipFile(z) as a:
                    xml = a.read(m).decode("utf-8", "ignore")
            else:
                xml = open(scene.metadonnees, encoding="utf-8", errors="ignore").read()
            trouve = re.findall(r"<BOA_ADD_OFFSET[^>]*>\s*(-?\d+)\s*<", xml)
            if trouve:
                valeur, origine = float(trouve[0]), "MTD_MSIL2A.xml"
            elif "BOA_ADD_OFFSET" not in xml:
                valeur, origine = 0.0, "MTD_MSIL2A.xml (pas de décalage : ligne de traitement antérieure à 04.00)"
        except Exception:
            pass
    if valeur is None:
        textes = [scene.source] + list(scene.bandes.values())
        m = next((re.search(r"_N(\d{2})(\d{2})_", t) for t in textes if re.search(r"_N(\d{2})(\d{2})_", t)), None)
        if m:
            valeur, origine = (-1000.0 if int(m.group(1)) >= 4 else 0.0), f"ligne de traitement N{m.group(1)}{m.group(2)}"
    if valeur is None:
        valeur, origine = 0.0, "inconnu"
        if journal:
            journal.avertir(f"  Sentinel-2 {scene.date} : décalage BOA_ADD_OFFSET introuvable (ni MTD_MSIL2A.xml ni ligne de "
                            "traitement) ; 0 supposé : vérifier les indices si le produit date de 2022 ou après")
    if journal:
        journal.info(f"  Sentinel-2 {scene.date} (.SAFE) : décalage des réflectances {valeur:+.0f} ({origine})")
    scene._decalage = valeur
    return valeur


def _classes_couleur(rgb):
    arr = np.rint(rgb * 255).astype(np.int32) if rgb.dtype.kind == "f" else rgb.astype(np.int32)
    meilleur = np.full(arr.shape[1:], 10 ** 9, dtype=np.int64)
    lab = np.zeros(arr.shape[1:], dtype=np.int8)
    for k, couleur in enumerate(PALETTE):
        d = sum((arr[c] - couleur[c]) ** 2 for c in range(3))
        mieux = d < meilleur
        meilleur[mieux], lab[mieux] = d[mieux], k
    return lab


def _lire_bande(src, g, plus_proche):
    """Bande lue SEULEMENT sur la fenêtre utile, puis ramenée sur la grille g (transform, crs, forme).

    Un produit .SAFE couvre une tuile de 110 km (environ 120 millions de pixels à 10 m) : on ne lit jamais
    la bande entière, seulement la fenêtre qui recouvre la grille cible (plus une petite marge).
    """
    from rasterio.windows import Window, from_bounds
    x0, y1 = g["transform"].c, g["transform"].f
    x1, y0 = x0 + g["forme"][1] * g["transform"].a, y1 + g["forme"][0] * g["transform"].e
    if src.crs != g["crs"]:
        x0, y0, x1, y1 = transform_bounds(g["crs"], src.crs, x0, y0, x1, y1)
    fen = from_bounds(x0, y0, x1, y1, src.transform)
    fen = Window(int(np.floor(fen.col_off)) - 2, int(np.floor(fen.row_off)) - 2, int(np.ceil(fen.width)) + 4, int(np.ceil(fen.height)) + 4)
    fen = fen.intersection(Window(0, 0, src.width, src.height))
    brut = src.read(1, window=fen).astype("float32")
    t_fen = src.window_transform(fen)
    if src.crs == g["crs"] and t_fen == g["transform"] and brut.shape == tuple(g["forme"]):
        return brut
    dest = np.full(g["forme"], np.nan, "float32")
    reproject(brut, dest, src_transform=t_fen, src_crs=src.crs, dst_transform=g["transform"], dst_crs=g["crs"],
              resampling=Resampling.nearest if plus_proche else Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    return dest


def _grille_parcelles(scene, parcelles, marge_m=300):
    """Grille 10 m de B04 restreinte à l'emprise des parcelles (plus une marge)."""
    from rasterio.windows import Window, from_bounds
    with _ouvrir(scene.bandes["B04"]) as ref:
        x0, y0, x1, y1 = parcelles.to_crs(ref.crs).total_bounds
        fen = from_bounds(x0 - marge_m, y0 - marge_m, x1 + marge_m, y1 + marge_m, ref.transform)
        fen = Window(int(np.floor(fen.col_off)), int(np.floor(fen.row_off)), int(np.ceil(fen.width)), int(np.ceil(fen.height)))
        fen = fen.intersection(Window(0, 0, ref.width, ref.height))
        t = ref.window_transform(fen)
        profil = dict(ref.profile, transform=t, width=int(fen.width), height=int(fen.height))
        return dict(transform=t, crs=ref.crs, forme=(int(fen.height), int(fen.width)), profil=profil)


def _lire_scene(scene, grille, journal=None):
    """Bandes (réflectance) et classes SCL, sur la grille `grille` (dict transform, crs, forme)."""
    g = grille
    sortie = {}
    for nom in BANDES + ("SCL",):
        with _ouvrir(scene.bandes[nom]) as src:
            if nom == "SCL" and scene.format == "copernicus":
                # SCL colorée (3 bandes) : classes calculées sur la fenêtre, puis ramenées sur la grille
                from rasterio.io import MemoryFile
                from rasterio.windows import from_bounds
                x0, y1 = g["transform"].c, g["transform"].f
                x1, y0 = x0 + g["forme"][1] * g["transform"].a, y1 + g["forme"][0] * g["transform"].e
                b = transform_bounds(g["crs"], src.crs, x0, y0, x1, y1) if src.crs != g["crs"] else (x0, y0, x1, y1)
                fen = from_bounds(*b, src.transform).round_offsets().round_lengths()
                lab = _classes_couleur(src.read(window=fen, boundless=True)).astype("float32")
                prof = dict(driver="GTiff", width=lab.shape[1], height=lab.shape[0], count=1, dtype="float32",
                            crs=src.crs, transform=src.window_transform(fen))
                with MemoryFile() as mf:
                    with mf.open(**prof) as tmp:
                        tmp.write(lab, 1)
                    with mf.open() as tmp:
                        sortie[nom] = _lire_bande(tmp, g, plus_proche=True)
                continue
            v = _lire_bande(src, g, plus_proche=(nom == "SCL"))
            if scene.format == "safe" and nom != "SCL":
                v = np.where((v == 0) | np.isnan(v), np.nan, (v + _decalage_safe(scene, journal)) / 10000.0)
            sortie[nom] = v
    return sortie, g


def _recouvre(scene, parcelles):
    with _ouvrir(scene.bandes["B04"]) as src:
        g, b, d, h = transform_bounds(src.crs, parcelles.crs, *src.bounds)
    x0, y0, x1, y1 = parcelles.total_bounds
    return not (x1 < g or x0 > d or y1 < b or y0 > h)


def indice_normalise(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where((a + b) > 1e-6, (a - b) / (a + b), np.nan).astype("float32")


def ecrire_carte(chemin, tableau, profil):
    p = dict(profil)
    p.update(driver="GTiff", count=1, dtype=tableau.dtype.name, compress="deflate",
             nodata=np.nan if tableau.dtype.kind == "f" else None)
    for cle in ("blockxsize", "blockysize", "tiled", "photometric"):
        p.pop(cle, None)
    with rasterio.open(chemin, "w", **p) as dst:
        dst.write(tableau, 1)


def preparer(ctx):
    """Prépare (une seule fois) les données Sentinel-2 utiles aux parcelles. Renvoie un DonneesS2."""
    if "s2" in ctx.cache:
        return ctx.cache["s2"]
    reg, journal = ctx.reglages, ctx.journal
    seuil_nuage, marge = reg["nuages"]["seuil_masque_pct"], reg["nuages"]["marge_px"]
    erosion_px, min_px = reg["nuages"].get("erosion_px", 1), reg["nuages"].get("min_pixels", 20)
    d = DonneesS2()
    retenues = []
    for s in ctx.inventaire.scenes:
        if not s.complete:
            d.ecartees.append(dict(date=s.date, source=s.source, raison="scène incomplète"))
        elif not _recouvre(s, ctx.parcelles):
            d.ecartees.append(dict(date=s.date, source=s.source, raison="ne recouvre aucune parcelle"))
        else:
            retenues.append(s)
    vues = set()
    for s in sorted(retenues, key=lambda s: (s.date, s.format != "copernicus")):
        if s.date in vues:   # deux scènes le même jour : on garde la première (export Copernicus en priorité)
            d.ecartees.append(dict(date=s.date, source=s.source, raison="autre scène déjà retenue pour cette date"))
            continue
        vues.add(s.date)
        if d.transform is None:
            g = _grille_parcelles(s, ctx.parcelles)
            d.transform, d.crs, d.forme, d.profil = g["transform"], g["crs"], g["forme"], g["profil"]
        bandes, _ = _lire_scene(s, dict(transform=d.transform, crs=d.crs, forme=d.forme), journal)
        if d.idmap is None:
            parc = ctx.parcelles.to_crs(d.crs)
            res = abs(d.transform.a)
            formes = [(geom.buffer(-erosion_px * res), k) for k, geom in enumerate(parc.geometry, start=1)
                      if not geom.buffer(-erosion_px * res).is_empty]
            d.idmap = features.rasterize(formes, out_shape=d.forme, transform=d.transform, fill=0, dtype="int32")
            d.ids = list(ctx.parcelles.parcelle_id)
        scl = bandes["SCL"]
        lab = np.where(np.isnan(scl), 0, scl).astype(int)
        masque = np.isin(lab, [k for k, n in enumerate(CLASSES_SCL) if n in MASQUE])
        eau = lab == CLASSES_SCL.index("eau")
        halo = ndimage.binary_dilation(masque, np.ones((3, 3), bool), iterations=marge) & ~masque if marge > 0 else False
        exclus = masque | eau | halo
        d.dates.append(s.date)
        d.sources[s.date] = s.source
        d.masque[s.date] = masque
        for nom, (a, b) in INDICES.items():
            d.indices[(nom, s.date)] = np.where(exclus, np.nan, indice_normalise(bandes[a], bandes[b])).astype("float32")
        for k, pid in enumerate(d.ids, start=1):
            m = d.idmap == k
            n_px = int(m.sum())
            pm = float(masque[m].mean() * 100) if n_px else np.nan
            utiles = int((m & ~exclus).sum())
            d.pct_masque[(pid, s.date)] = round(pm, 1) if n_px else np.nan
            d.statut[(pid, s.date)] = ("trop_petite" if n_px < min_px else "non_fiable" if pm > seuil_nuage
                                       else "insuffisant" if utiles < min_px else "ok")
        n_ok = sum(d.statut[(p, s.date)] == "ok" for p in d.ids)
        journal.info(f"  Sentinel-2 {s.date} ({s.format}, {s.source}) : {n_ok}/{len(d.ids)} parcelles exploitables")
    for e in d.ecartees:
        journal.info(f"  Sentinel-2 {e['date']} ({e['source']}) écartée : {e['raison']}")
    if not d.dates:
        raise RuntimeError("aucune scène Sentinel-2 complète ne recouvre les parcelles")
    ctx.cache["s2"] = d
    return d
