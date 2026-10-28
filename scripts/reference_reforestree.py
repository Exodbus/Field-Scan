#!/usr/bin/env python3
"""Zone et référence « ReforesTree » pour tester sur un site entier, sans annotation manuelle.

Produit, au même format que les carrés et la référence manuelle (pour réutiliser
evaluer_comptage.py, baseline_comptage.py et detecter_deepforest.py sans les modifier) :
  - zones_sites.geojson : l'emprise de chaque site choisi, avec zone_id = nom du site ;
  - reference_reforestree.geojson : les bananiers annotés par ReforesTree (après fusion
    des doublons), avec type = 'mere'.

Attention : ReforesTree oublie environ 40 % des bananiers (mesuré sur Manuel Macias).
Contre cette référence, la précision est sous-estimée (un bananier trouvé mais non
annoté compte comme une erreur) : les scores servent à comparer des méthodes, pas à
donner une performance « vraie ». Carlos Vera Arteaga est refusé (référence trop mauvaise).

Exemple :
    python scripts/reference_reforestree.py --sites "Carlos Vera Guevara"
"""
import argparse
from pathlib import Path

import geopandas as gpd

EXCLUS = {"Carlos Vera Arteaga"}


def identifiant(site):
    return site.replace(" ", "_")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--points", default="data/drone/reforestree/prepare/points_pieds.geojson")
    ap.add_argument("--sites-fichier", default="data/drone/reforestree/prepare/sites.geojson")
    ap.add_argument("--sites", nargs="+", default=["Carlos Vera Guevara"])
    ap.add_argument("--out", default="data/drone/reforestree/prepare")
    args = ap.parse_args(argv)

    refuses = EXCLUS.intersection(args.sites)
    if refuses:
        raise SystemExit(f"Refus : {sorted(refuses)} est exclu (référence ReforesTree trop incomplète, voir carnet).")
    pts = gpd.read_file(args.points)
    sites = gpd.read_file(args.sites_fichier)
    inconnus = set(args.sites) - set(sites.site)
    if inconnus:
        raise SystemExit(f"Sites inconnus : {sorted(inconnus)}. Disponibles : {sorted(sites.site)}")

    zones = sites[sites.site.isin(args.sites)].copy()
    zones["zone_id"] = zones.site.map(identifiant)
    ref = pts[pts.site.isin(args.sites) & pts.is_banana.astype(str).str.strip().str.lower().isin(["true", "1"])].copy()
    ref = ref[["site", "geometry"]].assign(zone_id=lambda d: d.site.map(identifiant), type="mere")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    zones[["zone_id", "site", "split", "geometry"]].to_file(out / "zones_sites.geojson", driver="GeoJSON")
    ref[["zone_id", "type", "geometry"]].to_file(out / "reference_reforestree.geojson", driver="GeoJSON")
    for _, z in zones.iterrows():
        n = int((ref.zone_id == z.zone_id).sum())
        print(f"{z.site} ({z.split}) : zone_id = {z.zone_id}, {n} bananiers ReforesTree, "
              f"{z.geometry.area / 1e4:.2f} ha")
    print(f"Écrit : {out / 'zones_sites.geojson'} et {out / 'reference_reforestree.geojson'}")


if __name__ == "__main__":
    main()
