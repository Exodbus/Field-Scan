#!/usr/bin/env python3
"""A2 « plantain du Ghana » : mesure de la référence v5 (réglage « agroforesterie », avenant du 15/11).

Rôle de A2 : réglage, jamais apprentissage, juge ni test. Lecture permise.
Mesure du banc v5 réutilisée par import, sans modification (scripts/v6_banc_commun.py) :
  image entière complétée en noir à un multiple de 32, sigmoïde, maxima locaux (fenêtre 7, pas 4), appariement un à un
  à distance minimale dans un rayon de 20 px à 5 cm/px (1 m), sans zone ignorée.
Spécifique à A2 :
  - réduction de l'original par le facteur fixé avant détection (out/jeux_neufs_1511/a2_echelle.json), Lanczos
    (comme scripts/preparer_comptage_v3.py) ;
  - référence = centre de boîte de l'API (annotations/<nom>.csv) × facteur ; centre de boîte = pied ;
  - v5 au seuil 0,30 (chiffres de la grille du banc gardés pour information) ;
  - chaque photo est mesurée seule (les photos d'un même vol se recouvrent : des plants sont comptés plusieurs fois).
Sorties : out/jeux_neufs_1511/a2_v5/ (par_photo.csv, total.json, detections.npz).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/jeux_neufs_a2_mesure_v5.py
"""
import csv
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")  # en mode -I, PYTHONIOENCODING est ignoré
sys.path.insert(0, str(RACINE / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

import v6_banc_commun as bc  # noqa: E402

A2 = RACINE / "data/raw/plantain_ghana_m2"
OUT = RACINE / "out/jeux_neufs_1511/a2_v5"
SEUIL = 0.30
FILS = 4
Image.MAX_IMAGE_PIXELS = 60_000_000


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ech = json.loads((RACINE / "out/jeux_neufs_1511/a2_echelle.json").read_text(encoding="utf-8"))
    f = float(ech["facteur"])
    sess = bc.session("v5", FILS)
    images = sorted((A2 / "images").glob("*.JPG"))
    lignes, dets = [], {}
    acc = {s: [0, 0, 0, 0, 0] for s in bc.SEUILS}       # vp, fp, fn, détectés, réels
    t0 = time.time()
    for n, p in enumerate(images):
        b = pd.read_csv(A2 / "annotations" / (p.stem + ".csv"))
        ref = b[["cx", "cy"]].to_numpy("float64") * f
        with Image.open(p) as im:
            im = im.convert("RGB")
            w, h = round(im.width * f), round(im.height * f)
            img = np.asarray(im.resize((w, h), Image.LANCZOS))
        x, hh, ww = bc.entree(img)
        carte = bc.sigmoide(bc._logits(sess, x))[:(hh + 3) // 4, :(ww + 3) // 4].astype("float32")
        xy, sc = bc.pics(carte, bc.K_PICS)
        dets[p.stem] = np.c_[xy, sc].astype("float32")
        for s in bc.SEUILS:
            d = xy[sc >= s]
            vp, fp, fn = bc.compter(d, ref, np.zeros((0, 2)))
            a = acc[s]
            a[0] += vp; a[1] += fp; a[2] += fn; a[3] += len(d); a[4] += len(ref)
            if abs(s - SEUIL) < 1e-9:
                pr, rr, f1 = bc.prf(vp, fp, fn)
                lignes.append(dict(photo=p.name, reels=len(ref), detectes=len(d), vp=vp, fp=fp, fn=fn,
                                   precision=round(pr, 4), rappel=round(rr, 4), f1=round(f1, 4),
                                   err_compte=round(len(d) / len(ref) - 1, 4) if len(ref) else None))
        if n % 10 == 0:
            print(f"  {n + 1}/{len(images)} ({time.time() - t0:.0f} s) {p.name} : {lignes[-1]}", flush=True)
    with open(OUT / "par_photo.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, list(lignes[0])); wr.writeheader(); wr.writerows(lignes)
    np.savez_compressed(OUT / "detections.npz", **dets)
    grille = {}
    for s, (vp, fp, fn, det, reels) in acc.items():
        pr, rr, f1 = bc.prf(vp, fp, fn)
        grille[f"{s:.2f}"] = dict(vp=vp, fp=fp, fn=fn, detectes=det, reels=reels, precision=round(pr, 4),
                                  rappel=round(rr, 4), f1=round(f1, 4), err_compte=round(abs(det / reels - 1), 4))
    L = pd.DataFrame(lignes)
    avec = L[L.reels > 0]
    total = dict(modele="v5 (modeles/centres_5cm_v5.onnx)", seuil=SEUIL, facteur=f, rayon_px=bc.RAYON_PX,
                 fenetre_pics=bc.K_PICS, photos=len(L), photos_avec_boites=int(len(avec)),
                 total=grille[f"{SEUIL:.2f}"],
                 err_compte_signee=round(grille[f"{SEUIL:.2f}"]["detectes"] / grille[f"{SEUIL:.2f}"]["reels"] - 1, 4),
                 f1_par_photo_mediane=round(float(avec.f1.median()), 4),
                 f1_par_photo_q10_q90=[round(float(avec.f1.quantile(0.1)), 4), round(float(avec.f1.quantile(0.9)), 4)],
                 err_compte_abs_par_photo_moyenne=round(float(avec.err_compte.abs().mean()), 4),
                 fp_photos_sans_boite=int(L[L.reels == 0].detectes.sum()),
                 grille_information=grille, duree_s=round(time.time() - t0))
    (OUT / "total.json").write_text(json.dumps(total, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in total.items() if k != "grille_information"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
