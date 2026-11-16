#!/usr/bin/env python3
"""Mesure, vue de dessus, la teinte des arbres d'agroforesterie relativement aux bananiers, sur la photo et sur un
rendu : moyenne RVB (sRGB) dans les disques des arbres (70 % du rayon, arbres_photo.csv) et à moins de 1,2 m des
centres de bananiers (hors arbres), puis rapport arbres / bananiers par canal. Le but est un rapport du rendu
proche de celui de la photo (arbres ni trop sombres ni bleutés).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_teinte_arbres.py --donnees out/rendu_blender/v4 rendu.png [...]
"""
import argparse
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402


def mesure(chemin, plants, arbres):
    a = np.asarray(Image.open(chemin).convert("RGB")).astype(float)
    h, l = a.shape[:2]
    k = l / 1330
    yy, xx = np.mgrid[0:h, 0:l]
    arb = np.zeros((h, l), bool)
    for _, r in arbres.iterrows():
        arb |= (xx - r.x_px * k) ** 2 + (yy - r.y_px * k) ** 2 < (r.rayon_m / 0.05 * k * 0.7) ** 2
    g = np.zeros((h, l), bool)
    g[(plants.y_px * k).astype(int).clip(0, h - 1), (plants.x_px * k).astype(int).clip(0, l - 1)] = True
    ban = (ndi.distance_transform_edt(~g) * 0.05 / k < 1.2) & ~arb
    return a[arb].mean(0), a[ban].mean(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--donnees", default="out/rendu_blender/v4")
    ap.add_argument("rendus", nargs="+")
    a = ap.parse_args()
    d = RACINE / a.donnees
    plants, arbres = pd.read_csv(d / "plants.csv"), pd.read_csv(d / "arbres_photo.csv")
    for nom in [str(d / "tuile.png")] + a.rendus:
        ta, tb = mesure(nom, plants, arbres)
        print(f"{Path(nom).name:32s} arbres {ta.round(0)} bananiers {tb.round(0)} rapport {(ta / tb).round(2)}")


if __name__ == "__main__":
    main()
