#!/usr/bin/env python3
"""Détections du v5 (modeles/centres_5cm_v5.onnx, lecture seule) sur les images de images_dense.csv, pour E-001.

Chaque image préparée est ramenée à 5 cm/px (facteur cm_par_px / 5 ; 1 pour la validation), passée au détecteur de
la chaîne (fieldscan.drone.DetecteurCentres, maxima au-dessus de 0,05), puis les centres sont ramenés en pixels de
l'image préparée. Sortie : CSV image_path,x,y,score (interface de scripts/math_evaluer.py).

    python out/comptage_math/evaluation/v5_detecter.py --roles controle_repro val_iter dev annexe_segmento
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RACINE))
from fieldscan.drone import DetecteurCentres  # noqa: E402

EVAL = RACINE / "out/comptage_math/evaluation"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", nargs="+", required=True)
    ap.add_argument("--out", default=str(EVAL / "v5"))
    args = ap.parse_args()
    L = pd.read_csv(EVAL / "images_dense.csv")
    L = L[L.role.isin(args.roles)]
    det = DetecteurCentres(RACINE / "modeles/centres_5cm_v5.onnx")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lignes, t0 = [], time.time()
    for n, r in enumerate(L.itertuples(), 1):
        img = Image.open(RACINE / "data/drone/comptage_v5_5cm/images" / r.image_path).convert("RGB")
        f = r.cm_par_px / 5.0
        if abs(f - 1) > 1e-3:
            img = img.resize((max(1, round(img.width * f)), max(1, round(img.height * f))), Image.LANCZOS)
        rgb = np.moveaxis(np.asarray(img), -1, 0)
        xy, sc = det.predire(rgb, np.ones(rgb.shape[1:], bool), seuil_min=0.05)
        for (x, y), s in zip(xy / f, sc):
            lignes.append((r.image_path, round(float(x), 2), round(float(y), 2), round(float(s), 5)))
        if n % 200 == 0:
            print(f"{n}/{len(L)} images, {time.time() - t0:.0f} s", flush=True)
    nom = "_".join(args.roles)
    pd.DataFrame(lignes, columns=["image_path", "x", "y", "score"]).to_csv(out / f"detections_{nom}.csv", index=False)
    print(f"{len(L)} images en {time.time() - t0:.0f} s -> {out / f'detections_{nom}.csv'}")


if __name__ == "__main__":
    main()
