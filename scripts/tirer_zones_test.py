#!/usr/bin/env python3
"""Tire des carrés d'annotation sur un site de test, stratifiés par couvert végétal (graine fixe).

Le site est découpé en carrés candidats (40 m par défaut) entièrement dans l'image ; pour chacun, la part
de végétation est mesurée (excès de vert ExG > seuil, sur une grille de 50 cm). Les candidats sont rangés en
trois tiers (couvert ouvert, moyen, fermé) et l'on tire au hasard --par-classe carrés dans chaque tiers.
Le tirage ne dépend que de l'image, jamais d'un modèle : le test reste honnête.

Les carrés sont ajoutés au fichier des zones (copie de sauvegarde faite avant), avec site, split = test,
part de végétation et classe de couvert, et une planche de repérage est écrite.

Exemple :
    python scripts/tirer_zones_test.py --site "Carlos Vera Guevara" --prefixe CG
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fieldscan import drone  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default="Carlos Vera Guevara")
    ap.add_argument("--prefixe", default="CG")
    ap.add_argument("--orthos", default="data/drone/reforestree/wwf_ecuador/RGB Orthomosaics")
    ap.add_argument("--zones", default="data/drone/reforestree/prepare/zones_annotation.geojson")
    ap.add_argument("--cote", type=float, default=40.0, help="côté des carrés en mètres")
    ap.add_argument("--par-classe", type=int, default=2)
    ap.add_argument("--seuil-exg", type=float, default=0.05)
    ap.add_argument("--pas", type=float, default=10.0, help="décalage entre carrés candidats, en mètres")
    ap.add_argument("--couverture-min", type=float, default=0.95, help="part minimale du carré couverte par l'image")
    ap.add_argument("--graine", type=int, default=2026)
    args = ap.parse_args(argv)

    ortho = Path(args.orthos) / f"{args.site} RGB.tif"
    zones = gpd.read_file(args.zones) if Path(args.zones).exists() else None
    with rasterio.open(ortho) as src:
        crs_src, bornes = src.crs, src.bounds
    utm = gpd.GeoSeries([box(*bornes)], crs=crs_src).estimate_utm_crs()
    x0, y0, x1, y1 = transform_bounds(crs_src, utm, *bornes)
    res = 0.5
    rgb, valide, t = drone.lire_fenetre(str(ortho), utm, (x0, y0, x1, y1), res)
    vert = drone.exg(rgb, valide) > args.seuil_exg

    existantes = zones.to_crs(utm).geometry.union_all() if zones is not None and len(zones) else None
    h, l = valide.shape
    print(f"Image : {valide.sum() * res * res / 1e4:.2f} ha survolés, emprise {l * res:.0f} x {h * res:.0f} m")

    def candidats_pour(cote):
        n, pas = int(cote / res), max(1, int(args.pas / res))
        liste = []
        for i in range(0, h - n + 1, pas):
            for j in range(0, l - n + 1, pas):
                if valide[i:i + n, j:j + n].mean() < args.couverture_min:
                    continue
                g = box(t.c + j * res, t.f - (i + n) * res, t.c + (j + n) * res, t.f - i * res)
                if existantes is not None and g.intersects(existantes):
                    continue
                liste.append(dict(geometry=g, part_vegetation=round(float(vert[i:i + n, j:j + n].mean()), 3)))
        return pd.DataFrame(liste)

    def tirer(c, k):
        """k carrés par tiers de végétation, sans chevauchement ; la classe la plus rare d'abord (graine fixe)."""
        rng = random.Random(args.graine)
        par_classe, pris = {}, []
        for classe in sorted(("ouvert", "moyen", "ferme"), key=lambda cl: (c.classe_couvert == cl).sum()):
            ordre = sorted(c.index[c.classe_couvert == classe]); rng.shuffle(ordre)
            choisis = []
            for ix in ordre:
                if len(choisis) == k:
                    break
                if not any(c.loc[ix, "geometry"].intersects(c.loc[jx, "geometry"]) for jx in pris):
                    choisis.append(ix); pris.append(ix)
            if len(choisis) < k:
                return None
            par_classe[classe] = choisis
        return [par_classe[cl][r] for r in range(k) for cl in ("ouvert", "moyen", "ferme")]

    tires = None
    for k in range(args.par_classe, 0, -1):          # d'abord le nombre demandé par classe, puis moins
        for cote in [args.cote] + [x for x in (35, 30, 25, 20) if x < args.cote]:
            c = candidats_pour(cote)
            if len(c) < 3 * k:
                continue
            c["classe_couvert"] = pd.qcut(c.part_vegetation.rank(method="first"), 3, labels=["ouvert", "moyen", "ferme"]).astype(str)
            tires = tirer(c, k)
            if tires:
                break
        if tires:
            break
    if not tires:
        raise SystemExit("Aucun tirage possible, même avec des carrés de 20 m et un carré par classe")
    print(f"Retenu : {len(tires)} carrés de {cote:.0f} m ({k} par classe de couvert), parmi {len(c)} candidats ; "
          f"tiers de végétation : {c.groupby('classe_couvert').part_vegetation.agg(['min', 'max']).round(2).to_dict('index')}")
    deja = set(zones.zone_id) if zones is not None else set()
    k, nouvelles = 1, []
    for ix in tires:
        while f"{args.prefixe}{k}" in deja:
            k += 1
        zid = f"{args.prefixe}{k}"; deja.add(zid)
        nouvelles.append(dict(zone_id=zid, site=args.site, split="test", part_vegetation=c.loc[ix, "part_vegetation"],
                              classe_couvert=c.loc[ix, "classe_couvert"], geometry=c.loc[ix, "geometry"]))
    nouv = gpd.GeoDataFrame(nouvelles, geometry="geometry", crs=utm)
    print(nouv.drop(columns="geometry").to_string(index=False))

    if zones is not None:
        sauvegarde = Path(args.zones).with_suffix(".avant_test.geojson")
        if not sauvegarde.exists():
            shutil.copy(args.zones, sauvegarde)
        toutes = pd.concat([zones, nouv.to_crs(zones.crs)], ignore_index=True)
    else:
        toutes = nouv
    gpd.GeoDataFrame(toutes, geometry="geometry", crs=(zones.crs if zones is not None else utm)).to_file(args.zones, driver="GeoJSON")
    print(f"\nZones ajoutées à {args.zones} (sauvegarde : {Path(args.zones).with_suffix('.avant_test.geojson')})")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pas = max(1, int(max(h, l) / 1200))
    img = np.moveaxis(rgb[:, ::pas, ::pas], 0, -1) / 255
    img[~valide[::pas, ::pas]] = 1
    fig, ax = plt.subplots(figsize=(9, 9), dpi=110)
    ax.imshow(np.clip(img, 0, 1), extent=(t.c, t.c + l * res, t.f - h * res, t.f))
    couleurs = {"ouvert": "#fdd835", "moyen": "#fb8c00", "ferme": "#e53935"}
    for _, z in nouv.iterrows():
        gpd.GeoSeries([z.geometry]).boundary.plot(ax=ax, color=couleurs[z.classe_couvert], linewidth=2)
        cx, cy = z.geometry.centroid.coords[0]
        ax.text(cx, cy, z.zone_id, color="white", fontsize=11, ha="center", va="center", weight="bold")
    ax.set_axis_off(); ax.set_title(f"{args.site} : carrés de test (jaune ouvert, orange moyen, rouge fermé)")
    fig.tight_layout()
    chemin = Path(args.zones).parent / f"zones_test_{args.prefixe}.png"
    fig.savefig(chemin); plt.close(fig)
    print(f"Planche de repérage : {chemin}")


if __name__ == "__main__":
    main()
