#!/usr/bin/env python3
"""Contrôle visuel sans annotation : les détections d'un ou plusieurs modèles dessinées sur chaque carré.

Pour chaque zone : l'orthomosaïque, côte à côte pour chaque modèle, avec un point par pied détecté,
le nombre de pieds et la densité par hectare. Sert à juger à l'œil (oublis, doublons, fausses détections)
quand aucune référence n'est annotée.

Exemple :
    python scripts/planche_detections.py --zones-evaluees EO1 EO2 EO3 EO4 \\
        --detections "réentraîné (0,35)=out/comptage/eloro_dense/detections.geojson" \\
                     "ancien (0,4)=out/comptage/eloro_ancien/detections.geojson"
"""
import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--detections", nargs="+", required=True, help="« nom=chemin » vers un detections.geojson (avec zone_id)")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--zones-evaluees", nargs="+", required=True)
    ap.add_argument("--seuil", type=float, default=None, help="ne garder que les détections de score au moins égal (si colonne score)")
    ap.add_argument("--out", default="out/comptage/controle_visuel")
    ap.add_argument("--grand", action="store_true", help="image grande et nette (environ 2 000 pixels par carré), pour juger à l'œil")
    args = ap.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sources = []
    for item in args.detections:
        nom, chemin = item.split("=", 1)
        sources.append((nom, gpd.read_file(chemin)))
    zones = gpd.read_file(args.zones)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    for zid in args.zones_evaluees:
        z = zones[zones.zone_id == zid]
        if z.empty:
            print(f"{zid} : zone introuvable"); continue
        site = z.iloc[0]["site"]
        with rasterio.open(Path(args.orthos) / f"{site} RGB.tif") as src:
            b = transform_bounds(z.crs, src.crs, *z.buffer(0).total_bounds) if z.crs != src.crs else tuple(z.total_bounds)
            fen = from_bounds(*b, src.transform)
            f = max(1, int(max(fen.width, fen.height) / (2200 if args.grand else 1100)))
            img = np.moveaxis(src.read([1, 2, 3], window=fen, out_shape=(3, int(fen.height / f), int(fen.width / f)), boundless=True), 0, -1)
            crs = src.crs
        surface_ha = float(z.to_crs(z.estimate_utm_crs()).area.iloc[0]) / 1e4
        cote, dpi = (10.0, 220) if args.grand else (7.5, 100)
        fig, axes = plt.subplots(1, len(sources), figsize=(cote * len(sources), cote + 0.3), dpi=dpi, squeeze=False)
        lignes = []
        for ax, (nom, det) in zip(axes[0], sources):
            d = det[det.zone_id == zid] if "zone_id" in det else det
            if args.seuil is not None and "score" in d:
                d = d[d.score >= args.seuil]
            d = d.to_crs(crs)
            d = d[d.within(z.to_crs(crs).geometry.iloc[0])]
            ax.imshow(img, extent=(b[0], b[2], b[1], b[3]))
            if len(d):
                ax.scatter(d.geometry.x, d.geometry.y, s=(18 if args.grand else 28), c="#ff2bd6" if args.grand else "#00e5ff",
                           edgecolors="white" if args.grand else "black", linewidths=0.8)
            ax.set_axis_off()
            ax.set_title(f"{nom} : {len(d)} pieds ({len(d) / surface_ha:.0f} par ha)", fontsize=11)
            lignes.append(f"{nom} {len(d)}")
        fig.suptitle(f"{zid} ({site}, {z.iloc[0].get('classe_couvert', '')}) : contrôle visuel, sans référence", fontsize=12)
        fig.tight_layout()
        chemin = out / f"controle_{zid}.png"
        fig.savefig(chemin); plt.close(fig)
        print(f"{zid} : " + " | ".join(lignes) + f" -> {chemin}")


if __name__ == "__main__":
    main()
