#!/usr/bin/env python3
"""Préparation des données d'entraînement DeepForest à partir de ReforesTree.

Pour chaque site d'entraînement et de validation :
  - lecture de l'orthomosaïque entière, rééchantillonnée à --resolution cm/pixel ;
  - découpage en tuiles de --taille pixels, avec --recouvrement ;
  - pour chaque tuile, les boîtes « bananier » de ReforesTree (après fusion des
    doublons, points_pieds.geojson), converties en pixels de la tuile.

Une seule classe, « Banana » : les autres arbres ne sont pas annotés, le modèle
apprend donc à les ignorer. Les tuiles sans bananier sont gardées comme exemples
négatifs (une ligne aux coordonnées 0, convention de DeepForest), sauf si elles
sont presque vides d'image.

Les sites de test (et Carlos Vera Arteaga, exclu) ne sont jamais exportés.

Sorties dans --out : images/*.png, train.csv, val.csv, resume.csv, parametres.json.

Exemple :
    python scripts/preparer_deepforest.py
"""
import argparse
import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from rasterio.enums import Resampling

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline_comptage import chemin_ortho, resolution_native_m  # noqa: E402

ETIQUETTE = "Banana"
SPLITS_EXPORTES = {"train": "train.csv", "val": "val.csv"}


def lire_site(chemin, res_m):
    """Image RGB (h, l, 3) uint8 rééchantillonnée, masque valide, et facteur pixels natifs -> pixels réduits."""
    with rasterio.open(chemin) as src:
        facteur = max(res_m / resolution_native_m(src), 1.0)
        h, l = round(src.height / facteur), round(src.width / facteur)
        data = src.read(out_shape=(src.count, h, l), resampling=Resampling.average)
        fx, fy = src.width / l, src.height / h
    rgb = np.moveaxis(data[:3], 0, -1).astype("uint8")
    valide = data[3] > 127 if data.shape[0] >= 4 else ~(data[:3] >= 250).all(0)
    rgb[~valide] = 0
    return rgb, valide, fx, fy


def positions(n, taille, pas):
    """Origines des tuiles le long d'un axe, la dernière collée au bord."""
    if n <= taille:
        return [0]
    p = list(range(0, n - taille, pas))
    return p + [n - taille]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/drone/reforestree/reforesTree.zip")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--points", default="data/drone/reforestree/prepare/points_pieds.geojson")
    ap.add_argument("--out", default="data/drone/reforestree/deepforest")
    ap.add_argument("--resolution", type=float, default=10.0, help="cm par pixel (défaut 10)")
    ap.add_argument("--taille", type=int, default=400, help="côté des tuiles en pixels (défaut 400)")
    ap.add_argument("--recouvrement", type=float, default=0.2, help="part de recouvrement entre tuiles (défaut 0,2)")
    ap.add_argument("--part-boite-min", type=float, default=0.5,
                    help="une boîte coupée par le bord est gardée si au moins cette part est dans la tuile")
    ap.add_argument("--part-image-min", type=float, default=0.5,
                    help="une tuile est gardée si au moins cette part contient de l'image")
    args = ap.parse_args(argv)

    res_m = args.resolution / 100
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    pts = gpd.read_file(args.points)
    pts = pts[pts.split.isin(SPLITS_EXPORTES)]
    pts = pts[pts.is_banana.astype(str).str.strip().str.lower().isin(["true", "1"])]
    pas = max(1, int(args.taille * (1 - args.recouvrement)))

    lignes, resume = [], []
    for site, sous in pts.groupby("site"):
        split = sous.split.iloc[0]
        print(f"{site} ({split}) : lecture à {args.resolution:g} cm/pixel...")
        rgb, valide, fx, fy = lire_site(chemin_ortho(site, args.orthos, args.zip), res_m)
        # Boîtes en pixels de l'image réduite (Xmin... sont en pixels de l'orthomosaïque d'origine)
        bx = np.c_[sous.Xmin / fx, sous.Ymin / fy, sous.Xmax / fx, sous.Ymax / fy]
        aires = (bx[:, 2] - bx[:, 0]) * (bx[:, 3] - bx[:, 1])
        h, l = valide.shape
        n_tuiles = n_vides = n_boites = 0
        for y0 in positions(h, args.taille, pas):
            for x0 in positions(l, args.taille, pas):
                y1, x1 = min(y0 + args.taille, h), min(x0 + args.taille, l)
                if valide[y0:y1, x0:x1].mean() < args.part_image_min:
                    continue
                nom = f"{site.replace(' ', '_')}_{args.resolution:g}cm_{x0}_{y0}.png"
                Image.fromarray(rgb[y0:y1, x0:x1]).save(out / "images" / nom)
                # Intersection de chaque boîte avec la tuile
                ix0, iy0 = np.maximum(bx[:, 0], x0), np.maximum(bx[:, 1], y0)
                ix1, iy1 = np.minimum(bx[:, 2], x1), np.minimum(bx[:, 3], y1)
                inter = np.clip(ix1 - ix0, 0, None) * np.clip(iy1 - iy0, 0, None)
                garde = inter >= args.part_boite_min * aires
                n_tuiles += 1
                if not garde.any():
                    lignes.append(dict(image_path=nom, xmin=0, ymin=0, xmax=0, ymax=0, label=ETIQUETTE, split=split))
                    n_vides += 1
                    continue
                for a, b, c, d in zip(ix0[garde] - x0, iy0[garde] - y0, ix1[garde] - x0, iy1[garde] - y0):
                    if c - a >= 2 and d - b >= 2:
                        lignes.append(dict(image_path=nom, xmin=int(round(a)), ymin=int(round(b)),
                                           xmax=int(round(c)), ymax=int(round(d)), label=ETIQUETTE, split=split))
                        n_boites += 1
        resume.append(dict(site=site, split=split, bananiers=len(sous), tuiles=n_tuiles,
                           tuiles_sans_bananier=n_vides, boites_exportees=n_boites,
                           cote_bananier_median_px=round(float(np.median(np.sqrt(aires))), 1)))

    df = pd.DataFrame(lignes)
    for split, fichier in SPLITS_EXPORTES.items():
        df[df.split == split].drop(columns="split").to_csv(out / fichier, index=False)
    pd.DataFrame(resume).to_csv(out / "resume.csv", index=False)
    (out / "parametres.json").write_text(json.dumps(dict(
        points=args.points, resolution_cm=args.resolution, taille_px=args.taille, taille_m=args.taille * res_m,
        recouvrement=args.recouvrement, part_boite_min=args.part_boite_min, part_image_min=args.part_image_min,
        etiquette=ETIQUETTE, sites={r["site"]: r["split"] for r in resume}), indent=2, ensure_ascii=False),
        encoding="utf-8")
    print("\n" + pd.DataFrame(resume).to_string(index=False))
    print(f"\nTuiles et annotations dans {out}/ (train.csv, val.csv, images/)")


if __name__ == "__main__":
    main()
