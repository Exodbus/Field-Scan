#!/usr/bin/env python3
"""Calibre la taille des couronnes des bananiers 3D sur la photo réelle (couverture verte vue de dessus).

Règle, écrite avant de regarder les résultats :
  - zone bananier = pixels à moins de 2,5 m d'un centre de plants.csv, hors des disques des arbres d'agroforesterie
    (arbres_photo.csv) ;
  - part de vert = part des pixels de cette zone dont l'ExG normalisé (2g - r - b) / (r + g + b) dépasse 0,03 ;
  - on rend la vue de dessus (soleil haut, mêmes cadrage et échelle que la photo) pour chaque facteur d'échelle
    candidat et on garde celui dont la part de vert est la plus proche de celle de la photo.
C'est un réglage d'apparence du décor : il ne touche à aucune donnée ni à aucun modèle.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_calibrer.py --donnees out/rendu_blender/v3 \
        --rendus 1.0=essai_100.png 1.15=essai_115.png
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

RES = 0.05


def part_vert(rgb, zone, seuil=0.03):
    a = rgb.astype("float32")
    s = a.sum(-1) + 1e-6
    exg = (2 * a[..., 1] - a[..., 0] - a[..., 2]) / s
    return float(((exg > seuil) & (s > 30))[zone].mean())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--donnees", default="out/rendu_blender/v3")
    ap.add_argument("--rendus", nargs="+", required=True, help="facteur=chemin du rendu de dessus")
    a = ap.parse_args(argv)
    d = RACINE / a.donnees
    photo = np.asarray(Image.open(d / "tuile.png").convert("RGB"))
    h, l = photo.shape[:2]
    plants = pd.read_csv(d / "plants.csv")
    graines = np.zeros((h, l), bool)
    graines[plants.y_px.round().astype(int).clip(0, h - 1), plants.x_px.round().astype(int).clip(0, l - 1)] = True
    zone = ndi.distance_transform_edt(~graines) * RES <= 2.5
    if (d / "arbres_photo.csv").exists():
        yy, xx = np.mgrid[0:h, 0:l]
        for _, r in pd.read_csv(d / "arbres_photo.csv").iterrows():
            zone &= (xx - r.x_px) ** 2 + (yy - r.y_px) ** 2 > (r.rayon_m / RES) ** 2
    ref = part_vert(photo, zone)
    res = {"photo": round(ref, 4), "zone_part_image": round(float(zone.mean()), 3), "rendus": {}}
    for item in a.rendus:
        k, chemin = item.split("=", 1)
        im = np.asarray(Image.open(chemin).convert("RGB").resize((l, h), Image.BILINEAR))
        res["rendus"][k] = round(part_vert(im, zone), 4)
    meilleur = min(res["rendus"], key=lambda k: abs(res["rendus"][k] - ref))
    res["retenu"] = meilleur
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (d / "calibration_couronnes.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
