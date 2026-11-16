#!/usr/bin/env python3
"""Arbres d'agroforesterie ILLUSTRATIFS placés sur les zones non-bananier visibles sur la photo réelle.

La parcelle Flora Pluas (ReforesTree) mêle bananiers et autres arbres. Nos données ne localisent que les
bananiers (détecteur v5). Pour que le rendu ne montre pas du sol nu là où la photo montre un arbre, on repère sur
la photo, par une règle simple et écrite d'avance, les couverts verts éloignés de tout centre détecté :
  1. végétation verte : ExG normalisé (2g - r - b) / (r + g + b) > 0,02 (les couverts gris-vert des arbres ont un
     ExG faible), lissé (médiane 7 px) ;
  2. loin des bananiers : à plus de 2,5 m de tout centre de plants.csv (une couronne de bananier fait ~2 m de rayon) ;
  3. ouverture morphologique (disque de 0,75 m) puis composantes d'au moins 12 m² ;
  4. centres d'arbres : maxima de la carte des distances au bord de la zone (au moins 1,6 m à l'intérieur), espacés
     d'au moins 4 m ; rayon de couronne = distance au bord + 1 m ; hauteur illustrative 2,2 x rayon + 3 m
     (bornée à 6-16 m).
Ce n'est pas un détecteur d'arbres validé : espèce, forme et hauteur sont illustratives, la position suit la
photo. Une herbe haute ou un bananier manqué par le détecteur peuvent être pris pour un arbre.

Sorties dans --donnees : arbres_photo.csv (x_m, y_m, rayon_m, hauteur_m, surface_zone_m2) et arbres_photo.png
(photo, masque retenu en jaune, arbres en cercles bleus, centres de bananiers en rouge).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/rendu_arbres.py --donnees out/rendu_blender/v3
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

RES = 0.05


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--donnees", default="out/rendu_blender/v3")
    ap.add_argument("--seuil-exg", type=float, default=0.02)
    ap.add_argument("--distance-m", type=float, default=2.5)
    ap.add_argument("--surface-min-m2", type=float, default=12.0)
    a = ap.parse_args(argv)
    d = RACINE / a.donnees
    rgb = np.asarray(Image.open(d / "tuile.png").convert("RGB")).astype("float32")
    h, l = rgb.shape[:2]
    s = rgb.sum(-1) + 1e-6
    exg = (2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]) / s
    vert = ndi.median_filter((exg > a.seuil_exg).astype(np.uint8), size=7) > 0
    plants = pd.read_csv(d / "plants.csv")
    graines = np.zeros((h, l), bool)
    graines[np.clip(plants.y_px.round().astype(int), 0, h - 1), np.clip(plants.x_px.round().astype(int), 0, l - 1)] = True
    dist_b = ndi.distance_transform_edt(~graines) * RES
    zone = vert & (dist_b > a.distance_m)
    r = int(round(0.75 / RES))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    zone = ndi.binary_opening(zone, structure=(xx ** 2 + yy ** 2) <= r * r)
    lab, n = ndi.label(zone)
    surf = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) * RES * RES
    garde = np.isin(lab, 1 + np.flatnonzero(surf >= a.surface_min_m2))
    lab = np.where(garde, lab, 0)
    dt = ndi.distance_transform_edt(garde) * RES
    # maxima de la distance au bord, espacés d'au moins 4 m (suppression gloutonne)
    cand = (dt == ndi.maximum_filter(dt, size=int(2.0 / RES))) & (dt >= 1.6)
    ys, xs = np.nonzero(cand)
    ordre = np.argsort(-dt[ys, xs])
    arbres = []
    for k in ordre:
        x, y = xs[k], ys[k]
        if any((x - ax) ** 2 + (y - ay) ** 2 < (4.0 / RES) ** 2 for ax, ay, *_ in arbres):
            continue
        rayon = float(dt[y, x]) + 1.0
        arbres.append((x, y, rayon, int(lab[y, x])))
    rows = []
    for x, y, rayon, k in arbres:
        rows.append(dict(x_m=round((x - l / 2) * RES, 2), y_m=round((h / 2 - y) * RES, 2), rayon_m=round(rayon, 2),
                         hauteur_m=round(float(np.clip(2.2 * rayon + 3.0, 6.0, 16.0)), 1),
                         surface_zone_m2=round(float(surf[k - 1]), 1), x_px=int(x), y_px=int(y)))
    df = pd.DataFrame(rows)
    df.to_csv(d / "arbres_photo.csv", index=False, encoding="utf-8")
    # image de contrôle
    im = Image.fromarray(rgb.astype(np.uint8))
    voile = np.zeros((h, l, 4), np.uint8)
    voile[garde] = (255, 220, 0, 90)
    im = Image.alpha_composite(im.convert("RGBA"), Image.fromarray(voile)).convert("RGB")
    dr = ImageDraw.Draw(im)
    for px, py in plants[["x_px", "y_px"]].to_numpy():
        dr.ellipse((px - 6, py - 6, px + 6, py + 6), outline=(255, 30, 30), width=3)
    for r_ in rows:
        R = r_["rayon_m"] / RES
        dr.ellipse((r_["x_px"] - R, r_["y_px"] - R, r_["x_px"] + R, r_["y_px"] + R), outline=(40, 120, 255), width=5)
    im.save(d / "arbres_photo.png")
    info = dict(regle=dict(seuil_exg=a.seuil_exg, distance_m=a.distance_m, surface_min_m2=a.surface_min_m2,
                           ouverture_m=0.75, maxima_espaces_m=4.0, distance_bord_min_m=1.6),
                n_arbres=len(rows), part_surface_zone=round(float(garde.mean()), 3))
    (d / "arbres_photo.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False))
    print(df.describe().round(2).to_string())


if __name__ == "__main__":
    main()
