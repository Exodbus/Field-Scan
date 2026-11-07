#!/usr/bin/env python3
"""Baseline explicite ExG + lissage gaussien + maxima locaux (E-001), recodée d'après scripts/baseline_comptage.py
(non modifié) pour les images préparées de images_dense.csv.

Pour chaque image, à sa résolution réelle cm_par_px :
  1. ExG = 2g - r - b en couleurs normalisées ; pixels de remplissage noirs (R+G+B <= 15) exclus ;
  2. lissage gaussien normalisé de sigma mètres (convolution qui ignore les pixels exclus) ;
  3. maxima locaux dans une fenêtre carrée impaire de côté `distance` mètres (plateau = un seul pic) ;
  4. score = ExG lissé au pic ; aucun seuil ici (il est choisi par scripts/math_evaluer.py sur le développement).

Grille (déclarée dans docs/recherche/notes/independent-evaluator.md, E-001) :
    --grille : sigma {0.35, 0.5, 0.75, 1.0, 1.25, 1.5} x distance {1.0, 1.5, 2.0, 2.5}, développement seul, choix du
    meilleur F1 cumulé ; puis --sigma S --distance D --roles val_iter avec le couple retenu.
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage

RACINE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
EVAL = RACINE / "out/comptage_math/evaluation"
SIGMAS = [0.35, 0.5, 0.75, 1.0, 1.25, 1.5]
DISTANCES = [1.0, 1.5, 2.0, 2.5]


def detecter_image(arg):
    chemin, cm, couples = arg
    rgb = np.asarray(Image.open(chemin).convert("RGB"), dtype="float32")
    s = rgb.sum(2)
    valide = s > 15
    s[s == 0] = 1
    exg = (2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]) / s
    res_m = cm / 100
    sorties = {}
    for sigma in sorted({c[0] for c in couples}):
        sp = sigma / res_m
        num = ndimage.gaussian_filter(np.where(valide, exg, 0).astype("float32"), sp)
        den = ndimage.gaussian_filter(valide.astype("float32"), sp)
        lisse = np.where(den > 0.2, num / np.maximum(den, 1e-6), -9.0)
        for (sg, dist) in couples:
            if sg != sigma:
                continue
            taille = max(3, int(round(dist / res_m)) | 1)
            pic = (lisse == ndimage.maximum_filter(lisse, size=taille)) & valide & (lisse > -9)
            lab, n = ndimage.label(pic)
            if n == 0:
                sorties[(sg, dist)] = np.zeros((0, 3))
                continue
            c = np.array(ndimage.center_of_mass(pic, lab, range(1, n + 1)))
            v = np.array(ndimage.maximum(lisse, lab, range(1, n + 1)))
            sorties[(sg, dist)] = np.c_[c[:, 1] + 0.5, c[:, 0] + 0.5, v]
    return sorties


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", nargs="+", required=True)
    ap.add_argument("--grille", action="store_true")
    ap.add_argument("--sigma", type=float)
    ap.add_argument("--distance", type=float)
    ap.add_argument("--out", default=str(EVAL / "baseline"))
    args = ap.parse_args()
    couples = [(s, d) for s in SIGMAS for d in DISTANCES] if args.grille else [(args.sigma, args.distance)]
    L = pd.read_csv(EVAL / "images_dense.csv")
    L = L[L.role.isin(args.roles)]
    taches = [(RACINE / "data/drone/comptage_v5_5cm/images" / r.image_path, r.cm_par_px, couples) for r in L.itertuples()]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(detecter_image, taches, chunksize=16))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for c in couples:
        lignes = [(im, round(float(x), 2), round(float(y), 2), round(float(v), 5))
                  for im, sortie in zip(L.image_path, res) for x, y, v in sortie[c]]
        nom = f"detections_s{c[0]}_d{c[1]}_{'_'.join(args.roles)}.csv"
        pd.DataFrame(lignes, columns=["image_path", "x", "y", "score"]).to_csv(out / nom, index=False)
    (out / "grille.json").write_text(json.dumps(dict(sigmas=SIGMAS, distances=DISTANCES), indent=1), encoding="utf-8")
    print(f"{len(L)} images, {len(couples)} couples -> {out}")


if __name__ == "__main__":
    main()
