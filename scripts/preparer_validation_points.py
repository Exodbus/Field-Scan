#!/usr/bin/env python3
"""Découpe des carrés de référence manuelle (MM1, MM2 par défaut) pour valider un détecteur hors de la chaîne.

Pour chaque carré : l'orthomosaïque autour du carré (marge de 3 m), à --resolution cm/pixel, en PNG ;
les points de la référence manuelle en pixels (avec leur type : mere, rejet, incertain ; type vide = mere) ;
le cadre du carré en pixels (seules les détections à l'intérieur sont évaluées).

Sorties dans --out : images/<zone>.png, points.csv (image_path, zone_id, x, y, type), zones.csv
(image_path, zone_id, x0, y0, x1, y1), parametres.json, et <nom du dossier>.zip pour Kaggle.

Exemple :
    python scripts/preparer_validation_points.py --zones-evaluees MM1 MM2 --resolution 5
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan import drone  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--reference", default="data/drone/reforestree/prepare/annotations_manuelles.geojson")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--zones-evaluees", nargs="+", default=["MM1", "MM2"])
    ap.add_argument("--resolution", type=float, default=5.0, help="cm par pixel")
    ap.add_argument("--marge", type=float, default=3.0, help="marge autour du carré, en mètres")
    ap.add_argument("--out", default="data/drone/validation_points_5cm")
    args = ap.parse_args(argv)
    res = args.resolution / 100
    out = Path(args.out); (out / "images").mkdir(parents=True, exist_ok=True)
    zones = gpd.read_file(args.zones)
    utm = zones.estimate_utm_crs()
    zones = zones.to_crs(utm)
    ref = gpd.read_file(args.reference).to_crs(utm)
    brut = ref["type"].astype(str).str.strip().str.lower().str.replace("è", "e", regex=False)
    vides = ref["type"].isna() | brut.isin(["", "none", "nan", "null"])
    ref["type"] = brut.where(~vides, "mere")
    lignes_pts, lignes_z = [], []
    for zid in args.zones_evaluees:
        z = zones[zones.zone_id == zid]
        if z.empty:
            raise SystemExit(f"Zone absente de {args.zones} : {zid}")
        geom, site = z.geometry.iloc[0], z.iloc[0]["site"]
        x0, y0, x1, y1 = geom.buffer(args.marge).bounds
        rgb, valide, t = drone.lire_fenetre(str(Path(args.orthos) / f"{site} RGB.tif"), utm, (x0, y0, x1, y1), res)
        img = np.moveaxis(np.clip(rgb, 0, 255).astype("uint8"), 0, -1)
        img[~valide] = 0
        nom = f"{zid}.png"
        Image.fromarray(img).save(out / "images" / nom)
        px = lambda x, y: ((x - t.c) / res, (t.f - y) / res)
        gx0, gy0, gx1, gy1 = geom.bounds
        (a, b), (c, d) = px(gx0, gy1), px(gx1, gy0)
        lignes_z.append(dict(image_path=nom, zone_id=zid, x0=round(a, 1), y0=round(b, 1), x1=round(c, 1), y1=round(d, 1)))
        r = ref[(ref.zone_id == zid) & ref.within(geom)]
        for _, p in r.iterrows():
            x, y = px(p.geometry.x, p.geometry.y)
            lignes_pts.append(dict(image_path=nom, zone_id=zid, x=round(x, 1), y=round(y, 1), type=p["type"]))
        print(f"{zid} ({site}) : image {img.shape[1]} x {img.shape[0]} px, {len(r)} points "
              f"({r['type'].value_counts().to_dict()})")
    pd.DataFrame(lignes_pts).to_csv(out / "points.csv", index=False)
    pd.DataFrame(lignes_z).to_csv(out / "zones.csv", index=False)
    (out / "parametres.json").write_text(json.dumps(dict(vars(args)), indent=2, ensure_ascii=False), encoding="utf-8")
    nom_zip = f"{out.name}.zip"
    with zipfile.ZipFile(out / nom_zip, "w") as zz:
        for f in ("points.csv", "zones.csv", "parametres.json"):
            zz.write(out / f, f)
        for f in sorted((out / "images").iterdir()):
            zz.write(f, f"images/{f.name}")
    print(f"Archive pour Kaggle : {out / nom_zip}")


if __name__ == "__main__":
    main()
