#!/usr/bin/env python3
"""Essai c16 (16/11) : mesures R1 et R2 de docs/journee_2026-11-16/avenant_c16_installation.md (réglage seulement).

Source réellement basse résolution : image de réglage à 5 cm réduite à c cm/px (LANCZOS, comme la première étape de
`degrader`), JPEG 95, écrite en GeoTIFF temporaire hors dépôt (EPSG:32717, pixel c/100 m) ; relue à 5 cm par
`fieldscan.drone.lire_fenetre` (WarpedVRT, Resampling.average), sans modification. Variante « bilinear » (R1, seulement
si la lecture actuelle échoue) : copie locale de lire_fenetre qui ne change que le rééchantillonnage.

R1 : c16_a (0,35) et, pour information, v5 (0,30) : cartes et pics du banc (bc.cartes_image, bc.pics), mesure
bc.mesurer_jeu sur les 5 jeux de réglage (lecture gardée cc.jeu). R2 : rapports réels / détectés de c16_a (0,35) avec le
détecteur de la chaîne (fieldscan.drone.DetecteurCentres), comme scripts/mesurer_fourchette_v3.py, à 8, 11 et 14 cm.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c16_installation.py r1 [--lecture average|bilinear]
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c16_installation.py r2 [--lecture average|bilinear]
Sorties : out/comptage/jour_1611/installation/r1_<lecture>.json, r2_<lecture>.json
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "GDAL_NUM_THREADS"):
    os.environ[_v] = "1"
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from rasterio.vrt import WarpedVRT  # noqa: E402

import c13_banc_commun as cc  # noqa: E402  (garde-fou des juges)
import v6_banc_commun as bc  # noqa: E402
from fieldscan import drone  # noqa: E402

AVENANT = RACINE / "docs/journee_2026-11-16/avenant_c16_installation.md"
EMPREINTE = "2ceecb2eca8215d336ee07afb74ceb8bdd419d9178ac3a74ab4f1f7425b81de7"
C16A = RACINE / "modeles/comptage_jour_1611/centres_5cm_c16_a.onnx"
V5 = RACINE / "modeles/centres_5cm_v5.onnx"
TMP = Path("C:/Users/coren/kaggle_tmp/c16/installation")
SORTIE = RACINE / "out/comptage/jour_1611/installation"
CRS, X0, Y0 = "EPSG:32717", 500000.0, 9700000.0
FILS = 2


def session(chemin):
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = FILS; o.inter_op_num_threads = 1
    return ort.InferenceSession(str(chemin), o, providers=["CPUExecutionProvider"])


def geotiff_source(img, cm, chemin):
    """Source à cm cm/px : réduction LANCZOS (première étape de degrader), JPEG 95, GeoTIFF 3 bandes uint8."""
    if chemin.exists():
        return
    h, w = img.shape[:2]
    petit = Image.fromarray(img).resize((max(1, round(w * 5 / cm)), max(1, round(h * 5 / cm))), Image.LANCZOS)
    t = io.BytesIO(); petit.save(t, format="JPEG", quality=95)
    a = np.asarray(Image.open(io.BytesIO(t.getvalue())).convert("RGB"))
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".tmp.tif")
    with rasterio.open(tmp, "w", driver="GTiff", width=a.shape[1], height=a.shape[0], count=3, dtype="uint8", crs=CRS,
                       transform=from_origin(X0, Y0, cm / 100, cm / 100)) as dst:
        dst.write(np.moveaxis(a, -1, 0))
    os.replace(tmp, chemin)


def lire_fenetre_bilineaire(chemin, crs_metrique, bounds, resolution_m):
    """Copie de fieldscan.drone.lire_fenetre ; seul Resampling.average devient Resampling.bilinear."""
    x0, y0, x1, y1 = bounds
    largeur, hauteur = max(1, int(np.ceil((x1 - x0) / resolution_m))), max(1, int(np.ceil((y1 - y0) / resolution_m)))
    transform = from_origin(x0, y1, resolution_m, resolution_m)
    with rasterio.open(chemin) as src:
        with WarpedVRT(src, crs=crs_metrique, resampling=Resampling.bilinear, transform=transform,
                       width=largeur, height=hauteur, src_nodata=src.nodata, nodata=0) as vrt:
            a = vrt.read(indexes=list(range(1, min(src.count, 4) + 1)), out_dtype="float32")
    rgb = a[:3]
    valide = a[3] > 127 if a.shape[0] == 4 else rgb.sum(0) > 0
    if rgb.max() <= 1.0 + 1e-6 and rgb.max() > 0:
        rgb = rgb * 255.0
    return rgb, valide, transform


def relire(jeu, k, chemin_img, cm, lecture):
    """Image (3, H, W) float32 relue à 5 cm par le chemin de la chaîne, et son masque valide."""
    img = bc.lire(chemin_img)
    h, w = img.shape[:2]
    g = TMP / f"d{cm}" / jeu / f"{k:05d}.tif"
    geotiff_source(img, cm, g)
    f = drone.lire_fenetre if lecture == "average" else lire_fenetre_bilineaire
    rgb, valide, _ = f(g, CRS, (X0, Y0 - h * 0.05, X0 + w * 0.05, Y0), 0.05)
    return rgb, valide


def r1(lecture):
    sess = {"c16_a": (session(C16A), 0.35), "v5": (session(V5), 0.30)}
    res = {m: {} for m in sess}
    t0 = time.time()
    for jeu in cc.REGLAGE:
        items = cc.jeu(jeu)
        P = {m: {} for m in sess}
        for k, e in enumerate(items):
            rgb, valide = relire(jeu, k, e["chemin"], 11, lecture)
            img = np.moveaxis(np.where(valide[None], rgb, 0.0), 0, -1)
            for m, (s, _) in sess.items():
                P[m][e["nom"]] = bc.pics(bc.cartes_image(s, img, "base")["base"])
        for m, (_, seuil) in sess.items():
            r = bc.mesurer_jeu(lambda ctx, D=P[m]: D[ctx.nom], jeu, items)[seuil]
            res[m][jeu] = {k: r[k] for k in ("f1", "p", "r", "detectes", "reels", "err_compte")}
        print(f"{time.strftime('%H:%M:%S')} R1 {lecture} {jeu} : " + " ; ".join(f"{m} F1 {res[m][jeu]['f1']:.4f}" for m in sess)
              + f" ({time.time() - t0:.0f} s)", flush=True)
    for m in sess:
        res[m]["moyenne"] = float(np.mean([res[m][j]["f1"] for j in cc.REGLAGE]))
    limite = 0.8614 - 0.020
    out = dict(lecture=lecture, cm=11, limite=limite, simule_c16_a=0.8614, resultats=res,
               passe=bool(res["c16_a"]["moyenne"] >= limite))
    return out


def r2(lecture):
    det = drone.DetecteurCentres(C16A)
    det.sess = session(C16A); det.entree = det.sess.get_inputs()[0].name       # 2 fils (machine partagée)
    seuil = 0.35
    d = bc.D
    T, O = pd.read_csv(d / "tuiles.csv"), pd.read_csv(d / "objets.csv")
    res = {}
    for cm in (8, 11, 14):
        t0 = time.time()

        def detecter(jeu, k, chemin):
            rgb, valide = relire(jeu, k, chemin, cm, lecture)
            xy, sc = det.predire(rgb, valide)
            return xy[sc >= seuil]

        def disque(jeu, k, r):
            xy = detecter(jeu, k, d / "images" / r.image_path)
            dans = (xy[:, 0] - r.masque_cx) ** 2 + (xy[:, 1] - r.masque_cy) ** 2 <= r.masque_r ** 2
            o = O[(O.image_path == r.image_path) & (O.type == "mere")]
            dans_o = (o.cx - r.masque_cx) ** 2 + (o.cy - r.masque_cy) ** 2 <= r.masque_r ** 2
            return int(dans_o.sum()), int(dans.sum())

        m = {}
        # même ordre et mêmes indices d'images que cc.jeu (le cache GeoTIFF est partagé avec R1)
        noms = {j: [e["nom"] for e in cc.jeu(j)] for j in ("plantain", "dense", "jeunes", "mm")}
        reel = detecte = 0
        for k, nom in enumerate(noms["plantain"]):
            reel += int(((O.image_path == nom) & (O.type == "mere")).sum())
            detecte += len(detecter("plantain", k, d / "images" / nom))
        m["plantain_100_metros"] = dict(reel=reel, detecte=detecte)
        reel = detecte = 0
        Tb = {r.image_path: r for r in T[T.ensemble == "val_dense_bv"].itertuples()}
        for k, nom in enumerate(noms["dense"]):
            a, b = disque("dense", k, Tb[nom])
            reel, detecte = reel + a, detecte + b
        m["dense_banavista_b"] = dict(reel=reel, detecte=detecte)
        rj = T[T.ensemble == "val_jeunes"].iloc[0]
        assert noms["jeunes"] == [rj.image_path]
        a, b = disque("jeunes", 0, rj)
        m["jeunes_dji_0544"] = dict(reel=a, detecte=b)
        P, Z = pd.read_csv(d / "mm" / "points.csv"), pd.read_csv(d / "mm" / "zones.csv")
        reel = detecte = 0
        for k, (_, z) in enumerate(Z.iterrows()):
            assert noms["mm"][k] == z.image_path
            xy = detecter("mm", k, d / "mm" / "images" / z.image_path)
            detecte += int(((xy[:, 0] >= z.x0) & (xy[:, 0] <= z.x1) & (xy[:, 1] >= z.y0) & (xy[:, 1] <= z.y1)).sum())
            reel += int(((P.zone_id == z.zone_id) & (P.type == "mere")).sum())
        m["mm1_mm2_meres"] = dict(reel=reel, detecte=detecte)
        for v in m.values():
            v["rapport"] = round(v["reel"] / v["detecte"], 3) if v["detecte"] else None
        res[str(cm)] = m
        print(f"{time.strftime('%H:%M:%S')} R2 {cm} cm ({time.time() - t0:.0f} s) : "
              + " ; ".join(f"{k} {v['reel']}/{v['detecte']} = {v['rapport']}" for k, v in m.items()), flush=True)
    rapports = [v["rapport"] for m in res.values() for v in m.values() if v["rapport"]]
    return dict(lecture=lecture, seuil=seuil, detecteur="fieldscan.drone.DetecteurCentres", mesures=res,
                coefficient_bas=round(min(rapports), 2), coefficient_haut=round(max(rapports), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("etape", choices=["r1", "r2"]); ap.add_argument("--lecture", default="average", choices=["average", "bilinear"])
    a = ap.parse_args()
    assert hashlib.sha256(AVENANT.read_bytes()).hexdigest() == EMPREINTE, "empreinte de l'avenant différente"
    SORTIE.mkdir(parents=True, exist_ok=True)
    sortie = SORTIE / f"{a.etape}_{a.lecture}.json"
    assert not sortie.exists(), f"{sortie} existe déjà"
    out = r1(a.lecture) if a.etape == "r1" else r2(a.lecture)
    sortie.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("resultats", "mesures")}, ensure_ascii=False), flush=True)
    if a.etape == "r1":
        print({m: round(r["moyenne"], 4) for m, r in out["resultats"].items()}, flush=True)


if __name__ == "__main__":
    main()
