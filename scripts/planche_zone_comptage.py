#!/usr/bin/env python3
"""Dessine, pour chaque carré de la référence manuelle, l'orthomosaïque avec le statut de chaque point :
fausses détections (rouge, ✕), détections justes (bleu), bananiers de la référence oubliés (jaune, ○).

Entrées : les fichiers detections_statut.geojson et reference_statut.geojson de scripts/evaluer_comptage.py.

Exemple :
    python scripts/planche_zone_comptage.py --statut out/comptage/deepforest_dense_statut --zones-evaluees MM1 MM2
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
    ap.add_argument("--statut", required=True, help="dossier de sortie de evaluer_comptage.py")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--zones-evaluees", nargs="+", default=["MM1", "MM2"])
    ap.add_argument("--marge", type=float, default=3.0, help="marge autour du carré, en mètres")
    args = ap.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dossier = Path(args.statut)
    det = gpd.read_file(dossier / "detections_statut.geojson")
    ref = gpd.read_file(dossier / "reference_statut.geojson")
    zones = gpd.read_file(args.zones)
    for zid in args.zones_evaluees:
        z = zones[zones.zone_id == zid]
        if z.empty:
            print(f"Zone {zid} introuvable"); continue
        site = z.iloc[0].get("site")
        ortho = Path(args.orthos) / f"{site} RGB.tif"
        with rasterio.open(ortho) as src:
            zc = z.to_crs(src.crs)
            metrique = z.estimate_utm_crs()
            x0, y0, x1, y1 = z.to_crs(metrique).buffer(args.marge).total_bounds
            b = transform_bounds(metrique, src.crs, x0, y0, x1, y1)
            fen = from_bounds(*b, src.transform)
            facteur = max(1, int(max(fen.width, fen.height) / 1600))
            img = src.read([1, 2, 3], window=fen, out_shape=(3, int(fen.height / facteur), int(fen.width / facteur)), boundless=True)
            img = np.moveaxis(img, 0, -1)
            etendue = (b[0], b[2], b[1], b[3])
            crs = src.crs
        d, r = det[det.zone_id == zid].to_crs(crs), ref[ref.zone_id == zid].to_crs(crs)
        fig, ax = plt.subplots(figsize=(9, 9), dpi=110)
        ax.imshow(img, extent=etendue)
        zc.boundary.plot(ax=ax, color="white", linewidth=1.5)
        styles = {"vrai_positif": ("#1e88e5", "o", "détection juste"), "faux_positif": ("#e53935", "x", "fausse détection"),
                  "ignore_incertain": ("#9e9e9e", "o", "détection sur un point incertain (ignorée)")}
        for statut, (couleur, marque, libelle) in styles.items():
            sel = d[d.statut == statut]
            if len(sel):
                ax.scatter(sel.geometry.x, sel.geometry.y, c=couleur, marker=marque, s=70, linewidths=2.5, label=f"{libelle} ({len(sel)})")
        oublies = r[r.statut == "oublie"]
        if len(oublies):
            ax.scatter(oublies.geometry.x, oublies.geometry.y, facecolors="none", edgecolors="#fdd835", s=160, linewidths=2.5,
                       label=f"bananier oublié ({len(oublies)})")
        ax.set_axis_off(); ax.legend(loc="lower left", fontsize=9, framealpha=0.85)
        ax.set_title(f"{zid} ({site}) : {len(r)} bananiers dans la référence, {len(d)} détections", fontsize=11)
        fig.tight_layout()
        chemin = dossier / f"planche_{zid}.png"
        fig.savefig(chemin); plt.close(fig)
        print(f"{zid} : statuts des détections {d.statut.value_counts().to_dict()} | référence {r.statut.value_counts().to_dict()} -> {chemin}")


if __name__ == "__main__":
    main()
