# -*- coding: utf-8 -*-
"""Prospection des GPS des images de drone déjà sur le disque (15/11/2026).

Lecture seule sur data/ : rien n'est écrit ni modifié dans data/, aucun accès réseau.

Étape 1 (« inventaire ») : pour chaque photo (fichier libre ou membre de zip) et chaque GeoTIFF,
lit l'EXIF (GPS, date, appareil, focale), le XMP DJI (RelativeAltitude, FlightYawDegree,
GimbalPitchDegree...) dans les octets du JPEG, et le géoréférencement des GeoTIFF (rasterio).
Sortie : out/prospection_drone_gps_1511/inventaire_gps.csv

Les dossiers de tuiles fabriquées par nos scripts (comptage_v*_5cm, roboflow_centres_5cm...)
sont seulement échantillonnés (ils n'ont pas d'EXIF : ils sont réécrits par nos scripts) et
résumés par une ligne par dossier.

Lancement :
  PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/prospection_drone_gps.py inventaire
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

SORTIE = RACINE / "out" / "prospection_drone_gps_1511"
DATA = RACINE / "data"
FILS = 6
TETE = 512 * 1024  # octets lus au début de chaque membre de zip (EXIF + XMP)

EXT_IMG = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".mpo", ".bmp", ".webp"}

# Jeux de photos ou d'orthos d'origine (lecture de chaque image)
DOSSIERS_LIBRES = [
    ("plantain_ghana_m2", DATA / "raw" / "plantain_ghana_m2" / "images"),
    ("jeunes_bananiers", DATA / "drone" / "jeunes_bananiers"),
]
ZIPS = sorted((DATA / "roboflow").glob("*.zip")) + sorted((DATA / "roboflow_nuit_1112" / "comptage").glob("*/*.zip")) + [
    DATA / "drone" / "jeunes_bananiers" / "jeunes_bananiers_annotes.zip",
]
# Tuiles fabriquées par nos scripts : échantillon seulement
DOSSIERS_DERIVES = [
    "drone/comptage_v3_5cm", "drone/comptage_v4_5cm", "drone/comptage_v5_5cm", "drone/comptage_v6_5cm",
    "drone/decoupage_comptage", "drone/decoupage_comptage_v4", "drone/decoupage_comptage_v5",
    "drone/decoupage_comptage_v6", "drone/multiple_tree_5cm", "drone/roboflow_centres_5cm",
    "drone/roboflow_deepforest", "drone/roboflow_deepforest_v2", "drone/validation_points_5cm",
    "drone/reforestree/deepforest", "drone/reforestree/deepforest_5cm",
]
ECHANTILLON_DERIVE = 150

CHAMPS = [
    "jeu", "chemin", "membre", "type", "largeur", "hauteur", "lat", "lon", "alt_abs_m", "alt_rel_m",
    "source_gps", "date", "marque", "modele", "focale_mm", "focale_35mm", "yaw_vol", "yaw_nacelle",
    "pitch_nacelle", "roll_camera", "vert_cs", "crs", "ouest", "sud", "est", "nord", "pixel_m", "note",
]


# ---------------------------------------------------------------- lecture EXIF / XMP
def _rat(v):
    try:
        return float(v)
    except Exception:
        try:
            return v[0] / v[1]
        except Exception:
            return None


def _dms(v, ref):
    try:
        d, m, s = (_rat(x) for x in v)
        x = d + m / 60 + s / 3600
        if ref in ("S", "W", b"S", b"W"):
            x = -x
        return x
    except Exception:
        return None


RE_XMP = re.compile(rb"<x:xmpmeta.*?</x:xmpmeta>", re.S)
RE_ATTR = re.compile(r"([A-Za-z0-9\-]+):([A-Za-z0-9]+)=\"([^\"]*)\"")
RE_ELEM = re.compile(r"<([A-Za-z0-9\-]+):([A-Za-z0-9]+)>([^<]*)</\1:\2>")


def lire_xmp(octets: bytes) -> dict:
    m = RE_XMP.search(octets)
    if not m:
        return {}
    txt = m.group(0).decode("utf-8", "replace")
    out = {}
    for pre, nom, val in RE_ATTR.findall(txt) + RE_ELEM.findall(txt):
        out[f"{pre}:{nom}"] = val.strip()
    return out


def _f(x):
    try:
        return float(str(x).replace("+", ""))
    except Exception:
        return None


def lire_image(fp, octets_tete: bytes | None) -> dict:
    """fp : objet fichier ouvrable par PIL ; octets_tete : début du fichier (pour le XMP)."""
    r = {}
    try:
        im = Image.open(fp)
        r["largeur"], r["hauteur"] = im.size
        r["type"] = im.format
        exif = im.getexif()
    except Exception as e:  # noqa: BLE001
        r["note"] = f"illisible: {type(e).__name__}"
        return r
    if exif:
        r["marque"] = str(exif.get(271, "") or "").strip("\x00 ")
        r["modele"] = str(exif.get(272, "") or "").strip("\x00 ")
        try:
            ex = exif.get_ifd(0x8769)
        except Exception:
            ex = {}
        r["date"] = str(ex.get(36867) or exif.get(306) or "").strip("\x00 ")
        if ex.get(37386) is not None:
            r["focale_mm"] = _rat(ex.get(37386))
        if ex.get(41989):
            r["focale_35mm"] = ex.get(41989)
        try:
            g = exif.get_ifd(0x8825)
        except Exception:
            g = {}
        if g and 2 in g and 4 in g:
            lat = _dms(g[2], g.get(1))
            lon = _dms(g[4], g.get(3))
            if lat is not None and lon is not None and not (lat == 0 and lon == 0):
                r["lat"], r["lon"] = lat, lon
                r["source_gps"] = "EXIF"
            if 6 in g:
                a = _rat(g[6])
                if a is not None:
                    if g.get(5) in (1, b"\x01"):
                        a = -a
                    r["alt_abs_m"] = a
    if octets_tete is None:
        try:
            fp.seek(0)
            octets_tete = fp.read(TETE)
        except Exception:
            octets_tete = b""
    x = lire_xmp(octets_tete)
    if x:
        if x.get("drone-dji:RelativeAltitude"):
            r["alt_rel_m"] = _f(x["drone-dji:RelativeAltitude"])
        if x.get("drone-dji:AbsoluteAltitude") and "alt_abs_m" not in r:
            r["alt_abs_m"] = _f(x["drone-dji:AbsoluteAltitude"])
        r["yaw_vol"] = _f(x.get("drone-dji:FlightYawDegree"))
        r["yaw_nacelle"] = _f(x.get("drone-dji:GimbalYawDegree"))
        r["pitch_nacelle"] = _f(x.get("drone-dji:GimbalPitchDegree"))
        # Géomarquage « Camera: » (autopilote, style Pix4D/Wingtra) : attitude de l'appareil
        if x.get("Camera:Yaw") and r["yaw_vol"] is None:
            r["yaw_vol"] = _f(x.get("Camera:Yaw"))
            r["pitch_nacelle"] = _f(x.get("Camera:Pitch"))
            r["roll_camera"] = _f(x.get("Camera:Roll"))
            r["vert_cs"] = x.get("Camera:VertCS", "")
        if "lat" not in r:
            la = _f(x.get("drone-dji:GpsLatitude") or x.get("drone-dji:Latitude"))
            lo = _f(x.get("drone-dji:GpsLongitude") or x.get("drone-dji:Longitude") or x.get("drone-dji:GpsLongtitude"))
            if la is not None and lo is not None and not (la == 0 and lo == 0):
                r["lat"], r["lon"], r["source_gps"] = la, lo, "XMP"
        cles = sorted(k for k in x if not k.startswith(("x:", "rdf:", "xmlns")))
        r["note"] = (r.get("note", "") + " xmp:" + ",".join(cles)[:300]).strip()
    r.setdefault("source_gps", "aucun")
    return r


def lire_geotiff(chemin: Path) -> dict:
    import rasterio
    from rasterio.warp import transform_bounds

    r = {"type": "GeoTIFF"}
    try:
        with rasterio.open(chemin) as ds:
            r["largeur"], r["hauteur"] = ds.width, ds.height
            if ds.crs is None:
                r["source_gps"] = "aucun"
                r["note"] = "TIFF sans géoréférencement"
                return r
            r["crs"] = ds.crs.to_string()
            o, s, e, n = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds, densify_pts=21)
            r.update(ouest=o, sud=s, est=e, nord=n, lat=(s + n) / 2, lon=(o + e) / 2, source_gps="GeoTIFF")
            px = abs(ds.transform.a)
            if ds.crs.is_geographic:
                import math

                px = px * 111320 * math.cos(math.radians(r["lat"]))
            r["pixel_m"] = px
            tags = ds.tags()
            r["date"] = tags.get("TIFFTAG_DATETIME", "")
            if tags.get("TIFFTAG_SOFTWARE"):
                r["note"] = "logiciel=" + tags["TIFFTAG_SOFTWARE"]
            # Repère local factice (jeunes bananiers : cadres.json, EPSG:3857 autour de 0,0, pixel de 1 m)
            if abs(r["lat"]) < 0.5 and abs(r["lon"]) < 0.5 and abs(px - 1.0) < 1e-6:
                r["source_gps"] = "aucun"
                r["note"] = "repère local factice (cadres.json : x = colonne + décalage, y = -ligne), pas une géoréférence"
                for k in ("lat", "lon", "ouest", "sud", "est", "nord", "pixel_m"):
                    r.pop(k, None)
    except Exception as e:  # noqa: BLE001
        r["note"] = f"illisible: {type(e).__name__}: {e}"[:200]
        r["source_gps"] = "aucun"
    return r


# ---------------------------------------------------------------- parcours
def rel(p: Path) -> str:
    return p.relative_to(RACINE).as_posix()


def traiter_fichier(jeu: str, p: Path) -> dict:
    if p.suffix.lower() in (".tif", ".tiff"):
        r = lire_geotiff(p)
        if "crs" not in r:
            with open(p, "rb") as f:
                r2 = lire_image(f, None)
            r2.update({k: v for k, v in r.items() if k not in r2})
            r = r2
    else:
        with open(p, "rb") as f:
            tete = f.read(TETE)
            f.seek(0)
            r = lire_image(f, tete)
    r.update(jeu=jeu, chemin=rel(p))
    return r


def traiter_zip(z: Path) -> list[dict]:
    jeu = z.stem
    lignes = []
    try:
        zf = zipfile.ZipFile(z)
    except Exception as e:  # noqa: BLE001
        return [{"jeu": jeu, "chemin": rel(z), "note": f"zip illisible {e}", "source_gps": "aucun"}]
    with zf:
        for info in zf.infolist():
            nom = info.filename
            if info.is_dir() or Path(nom).suffix.lower() not in EXT_IMG or "__MACOSX" in nom:
                continue
            with zf.open(info) as f:
                if Path(nom).suffix.lower() in (".tif", ".tiff"):
                    data = f.read()
                    # GeoTIFF dans un zip : lecture rasterio en mémoire
                    r = {}
                    try:
                        from rasterio.io import MemoryFile

                        with MemoryFile(data) as mf, mf.open() as ds:
                            if ds.crs is not None:
                                from rasterio.warp import transform_bounds

                                o, s, e, n = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)
                                r.update(type="GeoTIFF", crs=ds.crs.to_string(), ouest=o, sud=s, est=e, nord=n,
                                         lat=(s + n) / 2, lon=(o + e) / 2, source_gps="GeoTIFF",
                                         largeur=ds.width, hauteur=ds.height)
                    except Exception:
                        pass
                    if not r:
                        r = lire_image(io.BytesIO(data), data[:TETE])
                else:
                    tete = f.read(TETE)
                    r = lire_image(io.BytesIO(tete), tete)
            r.update(jeu=jeu, chemin=rel(z), membre=nom)
            lignes.append(r)
    return lignes


def resume_derive(d: str) -> dict:
    import random

    dossier = DATA / d
    fichiers = [p for p in dossier.rglob("*") if p.suffix.lower() in EXT_IMG]
    random.Random(2026).shuffle(fichiers)
    ech = fichiers[:ECHANTILLON_DERIVE]
    n_gps = n_exif = 0
    for p in ech:
        try:
            with Image.open(p) as im:
                ex = im.getexif()
            if ex:
                n_exif += 1
                if ex.get_ifd(0x8825):
                    n_gps += 1
        except Exception:
            pass
    return {
        "jeu": Path(d).name, "chemin": rel(dossier), "membre": "(dossier de tuiles dérivées)",
        "type": "dossier", "source_gps": "aucun" if n_gps == 0 else "EXIF",
        "note": f"tuiles fabriquées par nos scripts ; {len(fichiers)} images ; échantillon {len(ech)} : "
                f"{n_exif} avec EXIF, {n_gps} avec GPS",
    }


def inventaire():
    SORTIE.mkdir(parents=True, exist_ok=True)
    lignes: list[dict] = []
    taches = []
    with ThreadPoolExecutor(FILS) as ex:
        for jeu, d in DOSSIERS_LIBRES:
            for p in sorted(d.iterdir()):
                if p.is_file() and p.suffix.lower() in EXT_IMG and not p.name.startswith("apercu_"):
                    taches.append(ex.submit(traiter_fichier, jeu, p))
        # tous les GeoTIFF de data/ (hors dossiers déjà lus)
        deja = {d.resolve() for _, d in DOSSIERS_LIBRES}
        for p in sorted(DATA.rglob("*.tif")):
            if p.parent.resolve() in deja or "feuilles" in p.parts:
                continue
            jeu = "reforestree" if "reforestree" in p.parts else p.parent.name
            taches.append(ex.submit(traiter_fichier, jeu, p))
        zt = [ex.submit(traiter_zip, z) for z in ZIPS if z.exists()]
        dt = [ex.submit(resume_derive, d) for d in DOSSIERS_DERIVES if (DATA / d).exists()]
        for t in taches:
            lignes.append(t.result())
        for t in zt:
            lignes.extend(t.result())
        for t in dt:
            lignes.append(t.result())
    with open(SORTIE / "inventaire_gps.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, extrasaction="ignore")
        w.writeheader()
        for r in lignes:
            w.writerow({k: ("" if r.get(k) is None else (f"{r[k]:.7f}" if isinstance(r.get(k), float) else r[k]))
                        for k in CHAMPS})
    # résumé par jeu
    from collections import Counter, defaultdict

    par = defaultdict(Counter)
    for r in lignes:
        par[r["jeu"]][r.get("source_gps", "aucun")] += 1
        if r.get("alt_rel_m") is not None:
            par[r["jeu"]]["alt_rel"] += 1
        if r.get("modele"):
            par[r["jeu"]]["modele:" + str(r["modele"])] += 1
    print(json.dumps(par, ensure_ascii=False, indent=1))
    print(len(lignes), "lignes")


# ---------------------------------------------------------------- étape 2 : vol du Ghana
GHANA = DATA / "raw" / "plantain_ghana_m2"
# Sony RX1R II : capteur plein format 35,9 × 24,0 mm, 7 952 px de large [S, fiche Sony] ; focale 35 mm (EXIF)
PAS_PIXEL_M = 35.9e-3 / 7952
REDUC = 8  # décodage JPEG à 1/8 (draft)


def _lire_inventaire():
    with open(SORTIE / "inventaire_gps.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _vignette(p: Path, gris=False):
    import numpy as np

    im = Image.open(p)
    im.draft("RGB", (7952 // REDUC + 1, 5304 // REDUC + 1))
    im = im.convert("RGB")
    a = np.asarray(im)
    if gris:
        import cv2

        return cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    return a


def _deplacement(ga, gb):
    """Translation (tx, ty) de l'image A vers B (pixels réduits), rotation (degrés), nombre d'inliers."""
    import cv2
    import numpy as np

    orb = cv2.ORB_create(6000, fastThreshold=10)
    ka, da = orb.detectAndCompute(ga, None)
    kb, db = orb.detectAndCompute(gb, None)
    if da is None or db is None or len(ka) < 50 or len(kb) < 50:
        return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    bons = []
    for m in bf.knnMatch(da, db, k=2):
        if len(m) == 2 and m[0].distance < 0.8 * m[1].distance:
            bons.append(m[0])
    if len(bons) < 30:
        return None
    pa = np.float32([ka[m.queryIdx].pt for m in bons])
    pb = np.float32([kb[m.trainIdx].pt for m in bons])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=5000)
    if M is None or inl is None or inl.sum() < 25:
        return None
    rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    ech = float(np.hypot(M[0, 0], M[1, 0]))
    # déplacement du centre de l'image
    c = np.array([ga.shape[1] / 2, ga.shape[0] / 2, 1.0])
    cb = M @ c
    return float(cb[0] - c[0]), float(cb[1] - c[1]), rot, ech, int(inl.sum())


def ghana():
    import math

    import cv2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from pyproj import Transformer
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    lignes = [r for r in _lire_inventaire() if r["jeu"] == "plantain_ghana_m2"]
    for r in lignes:
        r["num"] = int(re.search(r"_(\d{5})\.JPG$", r["chemin"], re.I).group(1))
    lignes.sort(key=lambda r: r["num"])
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32630", always_xy=True)
    for r in lignes:
        r["x"], r["y"] = tr.transform(float(r["lon"]), float(r["lat"]))
        r["alt"] = float(r["alt_abs_m"])
        r["yaw"] = float(r["yaw_vol"])
        r["t"] = r["date"]
    chemins = [RACINE / r["chemin"] for r in lignes]
    with ThreadPoolExecutor(FILS) as ex:
        gris = list(ex.map(lambda p: _vignette(p, True), chemins))
    H, W = gris[0].shape
    fact = 7952 / W

    # 1. paires consécutives : GSD et orientation mesurées
    paires = []

    def _paire(i):
        a, b = lignes[i], lignes[i + 1]
        if b["num"] - a["num"] != 1:
            return None
        d = _deplacement(gris[i], gris[i + 1])
        if d is None:
            return None
        tx, ty, rot, ech, n = d
        dE, dN = b["x"] - a["x"], b["y"] - a["y"]
        dist = math.hypot(dE, dN)
        dpx = math.hypot(tx, ty) * fact
        if dpx < 50 or dist < 3:
            return None
        # mouvement de la caméra dans l'image (repère y vers le haut) = -(tx, -ty)
        ang_img = math.atan2(ty, -tx)
        ang_map = math.atan2(dN, dE)
        theta = math.degrees(ang_map - ang_img)
        az_haut = (-theta) % 360  # azimut (depuis le nord, sens horaire) du haut de l'image
        recouv = max(0.0, 1 - abs(tx) / W) * max(0.0, 1 - abs(ty) / H)
        return dict(i=a["num"], j=b["num"], dist_m=dist, depl_px=dpx, gsd_m=dist / dpx, az_haut=az_haut,
                    ecart_yaw=(az_haut - a["yaw"] + 180) % 360 - 180, rot=rot, ech=ech, inliers=n,
                    recouvrement=recouv, alt_a=a["alt"])

    with ThreadPoolExecutor(FILS) as ex:
        paires = [p for p in ex.map(_paire, range(len(lignes) - 1)) if p]
    # seuil fixé après un premier passage (écart-type de la mesure divisé par 2 au-dessus de 100 inliers) :
    # en dessous, l'appariement ORB sur la végétation est instable. Aucun modèle n'est jugé ici.
    sures = [p for p in paires if p["inliers"] >= 100]
    gsd = float(np.median([p["gsd_m"] for p in sures]))
    agl = gsd * 0.035 / PAS_PIXEL_M
    alt_med = float(np.median([r["alt"] for r in lignes]))
    sol = alt_med - agl
    ecart = float(np.median([p["ecart_yaw"] for p in sures]))
    # 2. empreintes
    polys = []
    for r in lignes:
        h = r["alt"] - sol
        g = h * PAS_PIXEL_M / 0.035
        r["gsd"] = g
        az = math.radians(r["yaw"] + ecart)
        up = np.array([math.sin(az), math.cos(az)])  # haut de l'image (E, N)
        right = np.array([up[1], -up[0]])
        c = np.array([r["x"], r["y"]])
        hw, hh = 7952 * g / 2, 5304 * g / 2
        pts = [c + sx * hw * right + sy * hh * up for sx, sy in ((-1, 1), (1, 1), (1, -1), (-1, -1))]
        r["poly"] = Polygon(pts)
        r["up"], r["right"] = up, right
        polys.append(r["poly"])
    union = unary_union(polys)
    surf_ha = union.area / 1e4
    # lignes de vol : changement de cap
    caps = []
    for a, b in zip(lignes, lignes[1:]):
        caps.append(math.degrees(math.atan2(b["x"] - a["x"], b["y"] - a["y"])) % 360)
    # écartement des lignes : distance perpendiculaire entre photos de lignes voisines
    # recouvrement latéral estimé = 1 - écartement / largeur au sol perpendiculaire au vol
    # (on regroupe en lignes par cap ± 20° et continuité)
    # nouvelle ligne quand le cap de l'appareil (Camera:Yaw) se retourne ou quand la numérotation saute
    groupes, cour = [], [0]
    for k in range(1, len(lignes)):
        dyaw = abs(((lignes[k]["yaw"] - lignes[k - 1]["yaw"]) + 180) % 360 - 180)
        if dyaw > 90 or lignes[k]["num"] - lignes[k - 1]["num"] > 3:
            groupes.append(cour)
            cour = []
        cour.append(k)
    groupes.append(cour)
    groupes = [g for g in groupes if len(g) >= 3]
    # pour chaque ligne : droite moyenne ; distance entre lignes voisines
    centres_l = []
    for g in groupes:
        xs = np.array([lignes[k]["x"] for k in g])
        ys = np.array([lignes[k]["y"] for k in g])
        centres_l.append((xs.mean(), ys.mean(), len(g), lignes[g[0]]["num"], lignes[g[-1]]["num"]))
    # direction principale de vol
    cap_med = float(np.median([c % 180 for c in caps]))
    perp = np.array([math.cos(math.radians(cap_med)), -math.sin(math.radians(cap_med))])
    pos_perp = sorted(float(np.dot([c[0], c[1]], perp)) for c in centres_l)
    ecarts = np.diff(pos_perp)
    larg_sol = 7952 * gsd  # le grand côté de l'image est-il perpendiculaire au vol ?
    haut_sol = 5304 * gsd
    angle_up_vol = float(np.median([abs(((p["az_haut"] - cap_med) + 90) % 180 - 90) for p in paires]))
    cote_perp = larg_sol if angle_up_vol < 45 else haut_sol

    # 3. boîtes annotées
    tailles, nboites = [], {}
    for r in lignes:
        nom = Path(r["chemin"]).stem
        f = GHANA / "annotations" / f"{nom}.csv"
        n = 0
        if f.exists():
            with open(f, encoding="utf-8") as fh:
                for b in csv.DictReader(fh):
                    tailles.append(math.sqrt(float(b["largeur"]) * float(b["hauteur"])) * r["gsd"])
                    n += 1
        nboites[r["num"]] = n

    # 4. netteté : variance du laplacien sur un recadrage central pleine résolution
    def _nettete(p):
        im = Image.open(p)
        cx, cy = 7952 // 2, 5304 // 2
        a = np.asarray(im.crop((cx - 1000, cy - 1000, cx + 1000, cy + 1000)).convert("L"), dtype=np.float32)
        return float(cv2.Laplacian(a, cv2.CV_32F).var())

    ech_net = chemins[:: max(1, len(chemins) // 20)]
    with ThreadPoolExecutor(FILS) as ex:
        nets = list(ex.map(_nettete, ech_net))

    resume = dict(
        n_photos=len(lignes), numeros=f"{lignes[0]['num']}..{lignes[-1]['num']}",
        date_exif=f"{lignes[0]['t']} -> {lignes[-1]['t']}",
        n_paires_appariees=len(paires), n_paires_sures=len(sures), gsd_m_mediane=gsd,
        gsd_m_q10_q90=[float(np.percentile([p['gsd_m'] for p in sures], q)) for q in (10, 90)],
        hauteur_sol_m=agl, altitude_vol_mediane_msl=alt_med, sol_estime_msl=sol,
        altitude_vol_min_max=[min(r["alt"] for r in lignes), max(r["alt"] for r in lignes)],
        ecart_yaw_mediane_deg=ecart, recouvrement_long_median=float(np.median([p["recouvrement"] for p in paires])),
        recouvrement_long_q10=float(np.percentile([p["recouvrement"] for p in paires], 10)),
        empreinte_photo_m=[7952 * gsd, 5304 * gsd], emprise_union_ha=surf_ha,
        emprise_enveloppe_ha=union.convex_hull.area / 1e4,
        n_lignes_vol=len(groupes), lignes_numeros=[[c[3], c[4], c[2]] for c in centres_l], cap_principal_deg=cap_med, ecarts_lignes_m=[round(float(e), 1) for e in ecarts],
        cote_image_perpendiculaire_au_vol_m=cote_perp,
        recouvrement_lateral_estime=[round(1 - float(e) / cote_perp, 2) for e in ecarts],
        boites_total=sum(nboites.values()), taille_boite_m_mediane=float(np.median(tailles)),
        taille_boite_m_q10_q90=[float(np.percentile(tailles, q)) for q in (10, 90)],
        nettete_laplacien_centre=[round(v, 1) for v in nets],
    )
    lon0, lat0 = tr.transform(*union.centroid.coords[0], direction="INVERSE")
    o, s, e, n = union.bounds
    m = 300
    bb = [tr.transform(o - m, s - m, direction="INVERSE"), tr.transform(e + m, n + m, direction="INVERSE")]
    resume["centre_lat_lon"] = [lat0, lon0]
    resume["emprise_wgs84_OSEN"] = list(tr.transform(o, s, direction="INVERSE")) + list(tr.transform(e, n, direction="INVERSE"))
    resume["rectangle_sentinel2_OSEN"] = [round(bb[0][0], 5), round(bb[0][1], 5), round(bb[1][0], 5), round(bb[1][1], 5)]
    with open(SORTIE / "ghana_vol.json", "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=1)
    with open(SORTIE / "ghana_paires.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(paires[0]))
        w.writeheader()
        w.writerows(paires)
    import geopandas as gpd

    gpd.GeoDataFrame(
        {"num": [r["num"] for r in lignes], "nom": [Path(r["chemin"]).name for r in lignes],
         "alt_msl": [r["alt"] for r in lignes], "gsd_cm": [r["gsd"] * 100 for r in lignes],
         "boites": [nboites[r["num"]] for r in lignes]},
        geometry=[r["poly"] for r in lignes], crs="EPSG:32630",
    ).to_crs("EPSG:4326").to_file(SORTIE / "ghana_empreintes.geojson", driver="GeoJSON")
    print(json.dumps(resume, ensure_ascii=False, indent=1))

    # 5. carte des positions et empreintes
    fig, ax = plt.subplots(figsize=(11, 11))
    for r in lignes:
        xs, ys = r["poly"].exterior.xy
        ax.plot(np.array(xs) - o, np.array(ys) - s, lw=0.4, color="0.6")
    xs = np.array([r["x"] for r in lignes]) - o
    ys = np.array([r["y"] for r in lignes]) - s
    sc = ax.scatter(xs, ys, c=[r["num"] for r in lignes], cmap="viridis", s=18, zorder=3)
    for r in lignes[::10]:
        ax.annotate(str(r["num"]), (r["x"] - o, r["y"] - s), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ux, uy = union.exterior.xy if union.geom_type == "Polygon" else union.convex_hull.exterior.xy
    ax.plot(np.array(ux) - o, np.array(uy) - s, color="crimson", lw=1.2, label=f"union des empreintes : {surf_ha:.1f} ha")
    ax.set_aspect("equal")
    ax.set_xlabel("est (m), UTM 30N")
    ax.set_ylabel("nord (m)")
    plt.colorbar(sc, ax=ax, shrink=0.6, label="numéro de photo")
    ax.legend(loc="upper right")
    ax.set_title(f"Ghana, Sefwi Adabokrom : {len(lignes)} photos (vol 04), centre {lat0:.4f} N {abs(lon0):.4f} O\n"
                 f"empreinte {7952 * gsd:.0f} × {5304 * gsd:.0f} m, {gsd * 100:.2f} cm/px (mesuré), hauteur ≈ {agl:.0f} m")
    fig.savefig(SORTIE / "ghana_carte_positions.jpg", dpi=110, bbox_inches="tight", pil_kwargs={"quality": 88})
    plt.close(fig)

    # 6. assemblage approximatif par GPS (pas une orthomosaïque) : 0,5 m/px, photo la plus proche du centre
    res = 0.5
    Wc, Hc = int((e - o) / res) + 1, int((n - s) / res) + 1
    toile = np.full((Hc, Wc, 3), 255, np.uint8)
    meilleur = np.full((Hc, Wc), np.inf, np.float32)
    yy, xx = np.mgrid[0:Hc, 0:Wc]

    def _rgb(p):
        return _vignette(p, False)

    with ThreadPoolExecutor(FILS) as ex:
        couleurs = list(ex.map(_rgb, chemins))
    for r, img in zip(lignes, couleurs):
        g = r["gsd"] * fact  # m par pixel réduit
        h_, w_ = img.shape[:2]
        # pixel réduit (u, v) -> carte : centre + (u - w/2) g right - (v - h/2) g up
        A = np.zeros((2, 3), np.float64)
        for k, (vec, sgn) in enumerate(((r["right"], 1), (r["up"], -1))):
            pass
        cx_, cy_ = (r["x"] - o) / res, (n - r["y"]) / res
        # colonnes de la toile : E/res ; lignes : -N/res
        R = np.array([[r["right"][0], -r["up"][0]], [-r["right"][1], r["up"][1]]]) * g / res
        t = np.array([cx_, cy_]) - R @ np.array([w_ / 2, h_ / 2])
        A[:, :2] = R
        A[:, 2] = t
        warp = cv2.warpAffine(img, A, (Wc, Hc), flags=cv2.INTER_AREA, borderValue=(0, 0, 0))
        msk = cv2.warpAffine(np.ones((h_, w_), np.uint8), A, (Wc, Hc), flags=cv2.INTER_NEAREST, borderValue=0) > 0
        dist = np.hypot(xx - cx_, yy - cy_).astype(np.float32)
        sel = msk & (dist < meilleur)
        toile[sel] = warp[sel]
        meilleur[sel] = dist[sel]
    Image.fromarray(toile).save(SORTIE / "ghana_assemblage_gps_50cm.jpg", quality=88)
    big = max(Wc, Hc)
    if big > 2400:
        k = 2400 / big
        Image.fromarray(toile).resize((int(Wc * k), int(Hc * k)), Image.LANCZOS).save(
            SORTIE / "ghana_assemblage_gps_apercu.jpg", quality=88)

    # 7. planche de vignettes (12 photos réparties) avec nombre de boîtes
    choix = [lignes[int(k)] for k in np.linspace(0, len(lignes) - 1, 12)]
    fig, axs = plt.subplots(3, 4, figsize=(20, 10.5))
    for ax, r in zip(axs.ravel(), choix):
        ax.imshow(couleurs[lignes.index(r)])
        ax.set_title(f"{r['num']:05d} : {nboites[r['num']]} boîtes, alt {r['alt']:.0f} m", fontsize=10)
        ax.axis("off")
    fig.suptitle("Ghana, vol 04 (31/01/2023 d'après le nom, 28/02/2023 d'après l'EXIF) : 12 photos sur "
                 f"{len(lignes)}, emprise d'une photo {7952 * gsd:.0f} × {5304 * gsd:.0f} m", fontsize=13)
    fig.tight_layout()
    fig.savefig(SORTIE / "ghana_planche.jpg", dpi=80, pil_kwargs={"quality": 85})
    plt.close(fig)

    # 8. zoom pleine résolution + même zone ramenée à 5 cm/px, avec boîtes
    r = lignes[len(lignes) // 2]
    best = max(lignes, key=lambda q: nboites[q["num"]])
    for etiquette, q in (("milieu", r), ("max_boites", best)):
        im = Image.open(RACINE / q["chemin"])
        nom = Path(q["chemin"]).stem
        bx = []
        f = GHANA / "annotations" / f"{nom}.csv"
        if f.exists():
            with open(f, encoding="utf-8") as fh:
                bx = [tuple(map(float, (b["cx"], b["cy"], b["largeur"], b["hauteur"]))) for b in csv.DictReader(fh)]
        if bx and etiquette == "max_boites":
            cxm, cym = np.median([b[0] for b in bx]), np.median([b[1] for b in bx])
        else:
            cxm, cym = 3976, 2652
        cxm = int(min(max(cxm, 750), 7952 - 750))
        cym = int(min(max(cym, 750), 5304 - 750))
        crop = im.crop((cxm - 750, cym - 750, cxm + 750, cym + 750)).convert("RGB")
        k5 = q["gsd"] / 0.05
        petit = crop.resize((max(1, int(1500 * k5)), max(1, int(1500 * k5))), Image.LANCZOS)
        fig, axs = plt.subplots(1, 2, figsize=(16, 8))
        axs[0].imshow(crop)
        for (bxx, byy, bw, bh) in bx:
            if abs(bxx - cxm) < 750 and abs(byy - cym) < 750:
                axs[0].add_patch(plt.Rectangle((bxx - cxm + 750 - bw / 2, byy - cym + 750 - bh / 2), bw, bh,
                                               fill=False, ec="yellow", lw=0.8))
        axs[0].set_title(f"{nom} : 1 500 px pleine résolution ({q['gsd'] * 100:.2f} cm/px, {1500 * q['gsd']:.0f} m), boîtes « plantain »")
        axs[1].imshow(petit, interpolation="nearest")
        axs[1].set_title(f"même zone ramenée à 5 cm/px ({petit.size[0]} px) : ce que verrait le v5")
        for a_ in axs:
            a_.axis("off")
        fig.tight_layout()
        fig.savefig(SORTIE / f"ghana_zoom_{etiquette}.jpg", dpi=90, pil_kwargs={"quality": 88})
        plt.close(fig)


# ---------------------------------------------------------------- étape 3 : regroupement par lieu
# Ce qui ne se lit pas dans les fichiers vient de l'examen visuel des planches (étiquette [O]) ou
# des notes du dépôt (étiquette [S]) ; c'est écrit à la main ici et justifié dans candidats.md.
JUGEMENT = {
    "plantain_ghana_m2": dict(
        pays="Ghana", region="Sefwi Adabokrom, Western North [S nom de fichier ; position EXIF]",
        nature="photos brutes de drone (Sony RX1R II, WingtraOne probable [H])",
        bananeraie="non : mosaïque paysanne (friches, recrûs, forêt, palmiers à huile, cases) avec jeunes plantains épars sur abattis [O]",
        parcelles="oui, plusieurs champs paysans d'environ 0,5 à 3 ha [H], sans limites nettes [O]",
        net="oui : 1,9 cm/px, net au centre [O, M]"),
    "Carlos Vera Arteaga": dict(pays="Équateur", region="ReforesTree, région nord [S carnet]",
                                nature="orthomosaïque de drone (WWF Équateur)",
                                bananeraie="non : agroforesterie (cacao, arbres, jeunes bananiers) [S carnet]",
                                parcelles="non : un champ d'environ 2 ha", net="oui : 1,0 cm/px"),
    "Carlos Vera Guevara": dict(pays="Équateur", region="ReforesTree, région nord [S carnet]",
                                nature="orthomosaïque de drone (WWF Équateur)",
                                bananeraie="non : agroforesterie, 14 % de bananiers [S carnet]",
                                parcelles="non : un champ d'environ 2 ha", net="oui : 1,2 cm/px"),
    "Leonor Aspiazu": dict(pays="Équateur", region="ReforesTree, région nord [S carnet]",
                           nature="orthomosaïque de drone (WWF Équateur)",
                           bananeraie="non : agroforesterie, 39 % de bananiers [S carnet]",
                           parcelles="non : un champ d'environ 2 ha", net="oui : 1,1 cm/px"),
    "Manuel Macias": dict(pays="Équateur", region="ReforesTree, région nord [S carnet]",
                          nature="orthomosaïque de drone (WWF Équateur)",
                          bananeraie="non : agroforesterie, 48 % de bananiers [S carnet]",
                          parcelles="non : un champ d'environ 2 ha", net="oui : 1,1 cm/px"),
    "Flora Pluas": dict(pays="Équateur", region="ReforesTree, région sud [S carnet]",
                        nature="orthomosaïque de drone (WWF Équateur)",
                        bananeraie="non : agroforesterie, 65 % de bananiers (355 /ha) [S carnet]",
                        parcelles="non : un champ d'environ 2,5 ha", net="oui : 1,0 cm/px"),
    "Nestor Macias": dict(pays="Équateur", region="ReforesTree, région sud [S carnet]",
                          nature="orthomosaïque de drone (WWF Équateur)",
                          bananeraie="non : agroforesterie, 57 % de bananiers (360 /ha) [S carnet]",
                          parcelles="non : un champ d'environ 2,4 ha", net="oui : 1,1 cm/px"),
    "El Oro OAM": dict(pays="Équateur", region="Machala, campus de l'UTMACH [S out/demo_eloro]",
                       nature="orthomosaïque de drone (DJI FC2204, OpenAerialMap)",
                       bananeraie="partiel : deux bandes de bananeraie (1,3 à 2 ha) dans un campus [S out/demo_eloro]",
                       parcelles="non : campus (bâtiments, essais, prairies)", net="oui : 6,4 cm/px, le v5 y répond [S]"),
    "ortho_martinique_basse_pointe": dict(pays="Martinique (France)", region="Basse-Pointe [S]",
                                          nature="orthophoto d'avion IGN (hors périmètre drone)",
                                          bananeraie="oui : plaine bananière en blocs [S out/demo_finale]",
                                          parcelles="oui : 196 parcelles automatiques [S]",
                                          net="non : 20 cm/px, v5 muet [S out/demo_finale]"),
    "ortho_qld_silkwood_2022": dict(pays="Australie", region="Silkwood, Queensland [S]",
                                    nature="orthophoto d'avion SISP (hors périmètre drone)",
                                    bananeraie="oui : ferme bananière commerciale [S out/demo_finale]",
                                    parcelles="oui : 4 à 5 blocs crédibles [S]",
                                    net="non : 10 cm/px, v5 muet [S out/demo_finale]"),
}


def _utm_epsg(lon, lat):
    z = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + z


def _rect_s2(o, s, e, n, marge=300.0):
    from pyproj import Transformer

    epsg = _utm_epsg((o + e) / 2, (s + n) / 2)
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    xs, ys = zip(*[tr.transform(a, b) for a in (o, e) for b in (s, n)])
    x0, x1, y0, y1 = min(xs) - marge, max(xs) + marge, min(ys) - marge, max(ys) + marge
    lo = [tr.transform(a, b, direction="INVERSE") for a in (x0, x1) for b in (y0, y1)]
    return [round(min(p[0] for p in lo), 5), round(min(p[1] for p in lo), 5),
            round(max(p[0] for p in lo), 5), round(max(p[1] for p in lo), 5)]


def _apercu_geotiff(p: Path, cote=900):
    import numpy as np
    import rasterio

    with rasterio.open(p) as ds:
        k = max(ds.width, ds.height) / cote
        h, w = int(ds.height / k), int(ds.width / k)
        a = ds.read(out_shape=(ds.count, h, w))
        if ds.count >= 4:
            valide = a[3] > 0
        else:
            valide = a[:3].sum(0) > 15
        rgb = np.moveaxis(a[:3], 0, -1).copy()
        rgb[~valide] = 255
        # surface valide : fraction de pixels valides × surface de l'emprise (en m)
        from rasterio.warp import transform_bounds

        o, s, e, n = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)
        epsg = _utm_epsg((o + e) / 2, (s + n) / 2)
        x0, y0, x1, y1 = transform_bounds(ds.crs, f"EPSG:{epsg}", *ds.bounds)
        surf = (x1 - x0) * (y1 - y0) * valide.mean() / 1e4
    return rgb, surf, (o, s, e, n), (x1 - x0, y1 - y0)


def lieux():
    import math

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    inv = _lire_inventaire()
    pts = [r for r in inv if r["source_gps"] in ("EXIF", "XMP", "GeoTIFF") and r["lat"]]
    # regroupement par lien simple à 1 km
    n = len(pts)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def dist_km(a, b):
        la1, lo1, la2, lo2 = map(math.radians, (float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"])))
        return 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))

    for i in range(n):
        for j in range(i + 1, n):
            if dist_km(pts[i], pts[j]) < 1.0:
                parent[find(i)] = find(j)
    groupes = {}
    for i, r in enumerate(pts):
        groupes.setdefault(find(i), []).append(r)
    ghana_vol = json.loads((SORTIE / "ghana_vol.json").read_text(encoding="utf-8"))
    sortie = []
    apercus = []
    for k, (g, rs) in enumerate(sorted(groupes.items(), key=lambda kv: -len(kv[1]))):
        jeux = sorted({r["jeu"] for r in rs})
        if jeux == ["plantain_ghana_m2"]:
            o, s, e, n_ = ghana_vol["emprise_wgs84_OSEN"]
            dates = sorted(r["date"] for r in rs)
            j = JUGEMENT["plantain_ghana_m2"]
            sortie.append(dict(
                lieu="GH-ADABOKROM", **{kk: j[kk] for kk in ("pays", "region", "nature")}, jeux="plantain_ghana_m2",
                n_images=len(rs), lat=round(ghana_vol["centre_lat_lon"][0], 4), lon=round(ghana_vol["centre_lat_lon"][1], 4),
                date=f"{dates[0][:10].replace(':', '-')} (EXIF) ; 2023-01-31 (nom de fichier)",
                emprise_ha=round(ghana_vol["emprise_union_ha"], 1),
                resolution_cm=round(ghana_vol["gsd_m_mediane"] * 100, 2),
                source_resolution="mesurée : déplacement image / déplacement GPS entre photos voisines",
                bananeraie=j["bananeraie"], plusieurs_parcelles=j["parcelles"], net_5cm=j["net"],
                rect_sentinel2_OSEN=",".join(f"{v:.5f}" for v in ghana_vol["rectangle_sentinel2_OSEN"]),
                remarque=f"photos 2 à 266 dont 66 absentes (98 à 163) ; recouvrement longitudinal médian "
                         f"{ghana_vol['recouvrement_long_median']:.0%} ; hauteur ≈ {ghana_vol['hauteur_sol_m']:.0f} m"))
            continue
        for r in rs:
            nom = Path(r["chemin"]).stem.replace(" RGB", "")
            p = RACINE / r["chemin"]
            rgb, surf, (o, s, e, n_), (lx, ly) = _apercu_geotiff(p)
            apercus.append((nom, rgb, surf, float(r["pixel_m"])))
            j = JUGEMENT.get(nom, JUGEMENT.get(r["jeu"], {}))
            sortie.append(dict(
                lieu=f"G{k:02d}-{nom[:24].replace(' ', '_')}", pays=j.get("pays", "?"), region=j.get("region", ""),
                nature=j.get("nature", "GeoTIFF"), jeux=r["jeu"], n_images=1,
                lat=round(float(r["lat"]), 4), lon=round(float(r["lon"]), 4), date=r["date"] or "non lue dans le fichier",
                emprise_ha=round(surf, 1), resolution_cm=round(float(r["pixel_m"]) * 100, 2),
                source_resolution="GeoTIFF", bananeraie=j.get("bananeraie", ""),
                plusieurs_parcelles=j.get("parcelles", ""), net_5cm=j.get("net", ""),
                rect_sentinel2_OSEN=",".join(f"{v:.5f}" for v in _rect_s2(o, s, e, n_)),
                remarque=f"emprise {lx:.0f} × {ly:.0f} m ; groupe de {len(rs)} GeoTIFF à moins de 1 km" if len(rs) > 1
                else f"emprise {lx:.0f} × {ly:.0f} m"))
    champs = list(sortie[0])
    with open(SORTIE / "lieux.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        w.writerows(sortie)
    for s_ in sortie:
        print({k: s_[k] for k in ("lieu", "pays", "lat", "lon", "n_images", "emprise_ha", "resolution_cm", "rect_sentinel2_OSEN")})
    # planche des GeoTIFF
    nc = 4
    nl = math.ceil(len(apercus) / nc)
    fig, axs = plt.subplots(nl, nc, figsize=(5 * nc, 5 * nl))
    for ax in axs.ravel():
        ax.axis("off")
    for ax, (nom, rgb, surf, px) in zip(axs.ravel(), apercus):
        ax.imshow(rgb)
        ax.set_title(f"{nom}\n{surf:.1f} ha valides, {px * 100:.1f} cm/px", fontsize=10)
    fig.tight_layout()
    fig.savefig(SORTIE / "planche_geotiff.jpg", dpi=70, pil_kwargs={"quality": 85})
    plt.close(fig)
    # carte du monde simplifiée des lieux (sans fond de carte : aucun téléchargement)
    fig, ax = plt.subplots(figsize=(12, 5))
    for s_ in sortie:
        ax.scatter(s_["lon"], s_["lat"], s=40)
        ax.annotate(s_["lieu"], (s_["lon"], s_["lat"]), fontsize=7, xytext=(4, 4), textcoords="offset points",
                    rotation=20)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-40, 40)
    ax.axhline(0, color="0.8", lw=0.5)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_title("Lieux géoréférencés trouvés dans data/ (photos à GPS et GeoTIFF)")
    ax.grid(alpha=0.3)
    fig.savefig(SORTIE / "carte_lieux_monde.jpg", dpi=100, bbox_inches="tight", pil_kwargs={"quality": 85})
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("etape", choices=["inventaire", "ghana", "lieux"])
    a = ap.parse_args()
    if a.etape == "inventaire":
        inventaire()
    elif a.etape == "ghana":
        ghana()
    elif a.etape == "lieux":
        lieux()
