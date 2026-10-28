#!/usr/bin/env python3
"""Préparation du jeu ReforesTree pour le comptage des pieds.

Lit directement le zip Zenodo et produit, en UTM 17S (EPSG:32717) :
  - points_pieds.geojson : un point par arbre (centre de sa boîte), avec site,
    découpage, is_banana, score et taille de couronne ;
  - boites.geojson : les boîtes annotées, pour les voir dans QGIS ;
  - sites.geojson : l'emprise de chaque orthomosaïque, avec son découpage
    (utilisable comme « parcelles » pour le comptage par zone) ;
  - resume_sites.csv et parametres.json.

Points d'attention traités :
  - Les tuiles se recouvrent de 200 pixels : un même arbre peut être annoté
    dans deux tuiles. Les centres à moins de --doublon-m mètres et issus de
    tuiles différentes sont fusionnés (on garde la boîte la plus grande, la
    moins coupée par le bord de tuile).
  - Boîtes imbriquées : deux boîtes dont la plus petite est contenue à plus de
    --seuil-imbrication (défaut 70 %) dans l'autre sont signalées (colonne
    `imbriquee`, fichier imbrications.csv), sans être supprimées. Ce peut être
    un doublon d'annotation ou un pied mère et son rejet.
  - Les coordonnées sont recalculées à partir du géoréférencement de chaque
    orthomosaïque ; l'écart avec les colonnes lon/lat du fichier est mesuré.

Exemple :
    python scripts/prepare_reforestree.py
"""
import argparse
import json
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy.spatial import cKDTree
from shapely.geometry import Point, box

CRS_SORTIE = "EPSG:32717"  # UTM 17 Sud : tous les sites sont vers 79,5° O et 1 à 2° S
ANNOTATIONS = "annotations/cleaned/clean_annotations.csv"
DOSSIER_ORTHOS = "wwf_ecuador/RGB Orthomosaics"

# Découpage par site (voir carnet de données). Les deux sites Carlos Vera,
# à environ 200 m l'un de l'autre, restent toujours dans le même ensemble.
DECOUPAGES = {
    "site": {
        "Flora Pluas": "train", "Nestor Macias": "train", "Leonor Aspiazu": "train",
        "Manuel Macias": "val",
        "Carlos Vera Arteaga": "test", "Carlos Vera Guevara": "test",
    },
    "region": {  # variante plus stricte : entraînement au sud, test au nord (environ 115 km)
        "Flora Pluas": "train", "Nestor Macias": "train",
        "Leonor Aspiazu": "val",
        "Manuel Macias": "test", "Carlos Vera Arteaga": "test", "Carlos Vera Guevara": "test",
    },
}


def nom_site(img_name):
    """'Flora Pluas RGB' -> 'Flora Pluas'."""
    n = str(img_name).strip()
    return n[:-4].strip() if n.endswith(" RGB") else n


def fusionner_doublons(g, seuil_m):
    """Fusionne les centres proches venant de tuiles différentes. Retourne (index gardés, nb conflits d'étiquette)."""
    gardes, conflits = [], 0
    for _, sous in g.groupby("site"):
        xy = np.c_[sous.geometry.x, sous.geometry.y]
        idx = sous.index.to_numpy()
        parent = list(range(len(idx)))

        def racine(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        tuiles = sous.img_path.to_numpy()
        for i, j in cKDTree(xy).query_pairs(seuil_m):
            if tuiles[i] != tuiles[j]:  # deux arbres d'une même tuile ne sont jamais fusionnés
                parent[racine(i)] = racine(j)
        groupes = {}
        for k in range(len(idx)):
            groupes.setdefault(racine(k), []).append(idx[k])
        for membres in groupes.values():
            if len(membres) > 1 and g.loc[membres, "is_banana"].nunique() > 1:
                conflits += 1
            gardes.append(g.loc[membres, "aire_m2"].idxmax())
    return sorted(gardes), conflits


def mesurer_imbrications(bxs, seuil):
    """Paires de boîtes dont la plus petite est contenue à plus de `seuil` dans l'autre."""
    cols = ["pied_id", "site", "img_path", "is_banana", "geometry"]
    g = bxs[cols].reset_index(drop=True)
    j = gpd.sjoin(g, g, predicate="intersects", how="inner", lsuffix="a", rsuffix="b")
    j = j[j.index < j.index_b]  # chaque paire une seule fois, sans comparer une boîte à elle-même
    if j.empty:
        return pd.DataFrame(columns=["pied_a", "pied_b", "site", "meme_tuile", "bananier_a", "bananier_b", "inclusion"])
    ga = g.geometry.loc[j.index].reset_index(drop=True)
    gb = g.geometry.loc[j.index_b].reset_index(drop=True)
    inter = ga.intersection(gb).area
    plus_petite = np.minimum(ga.area, gb.area)
    inclusion = (inter / plus_petite).to_numpy()
    paires = pd.DataFrame({
        "pied_a": j.pied_id_a.to_numpy(), "pied_b": j.pied_id_b.to_numpy(), "site": j.site_a.to_numpy(),
        "meme_tuile": (j.img_path_a.to_numpy() == j.img_path_b.to_numpy()),
        "bananier_a": j.is_banana_a.to_numpy(), "bananier_b": j.is_banana_b.to_numpy(),
        "inclusion": inclusion.round(3)})
    return paires[paires.inclusion > seuil].reset_index(drop=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default="data/drone/reforestree/reforesTree.zip")
    ap.add_argument("--out", default="data/drone/reforestree/prepare")
    ap.add_argument("--decoupage", choices=list(DECOUPAGES), default="site")
    ap.add_argument("--doublon-m", type=float, default=1.0,
                    help="distance sous laquelle deux centres de tuiles différentes sont un même arbre (défaut 1 m)")
    ap.add_argument("--seuil-imbrication", type=float, default=0.7,
                    help="part de la plus petite boîte contenue dans l'autre au-delà de laquelle la paire est signalée (défaut 0,7)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    chemin_zip = Path(args.zip).resolve().as_posix()
    decoupage = DECOUPAGES[args.decoupage]

    with zipfile.ZipFile(args.zip) as z, z.open(ANNOTATIONS) as f:
        a = pd.read_csv(f)
    a["site"] = a.img_name.map(nom_site)
    a["is_banana"] = a.is_banana.astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])
    inconnus = sorted(set(a.site) - set(decoupage))
    if inconnus:
        raise SystemExit(f"Sites sans découpage défini : {inconnus}")

    points, boites, sites, ecarts = [], [], [], {}
    for site, sous in a.groupby("site"):
        with rasterio.open(f"/vsizip/{chemin_zip}/{DOSSIER_ORTHOS}/{site} RGB.tif") as src:
            t, crs_src, bornes = src.transform, src.crs, src.bounds
        if crs_src is None:
            raise SystemExit(f"L'orthomosaïque de {site} n'est pas géoréférencée.")
        # Centre et coins des boîtes : pixels de l'orthomosaïque -> coordonnées de l'image (degrés)
        cx, cy = (sous.Xmin + sous.Xmax) / 2, (sous.Ymin + sous.Ymax) / 2
        lon, lat = t * (cx.to_numpy(), cy.to_numpy())
        x0, y0 = t * (sous.Xmin.to_numpy(), sous.Ymin.to_numpy())
        x1, y1 = t * (sous.Xmax.to_numpy(), sous.Ymax.to_numpy())

        pts = gpd.GeoSeries([Point(xy) for xy in zip(lon, lat)], crs=crs_src).to_crs(CRS_SORTIE)
        bx = gpd.GeoSeries([box(min(p, q), min(r, s), max(p, q), max(r, s)) for p, r, q, s in zip(x0, y0, x1, y1)],
                           crs=crs_src).to_crs(CRS_SORTIE)
        # Écart entre nos coordonnées et les colonnes lon/lat fournies, en mètres
        fournis = gpd.GeoSeries([Point(xy) for xy in zip(sous.lon, sous.lat)], crs="EPSG:4326").to_crs(CRS_SORTIE)
        d = pts.distance(fournis, align=False)
        ecarts[site] = (float(d.median()), float(d.max()))

        b = bx.bounds
        attributs = pd.DataFrame({
            "site": site, "split": decoupage[site], "is_banana": sous.is_banana.to_numpy(),
            "score": sous.score.round(3).to_numpy(), "img_path": sous.img_path.to_numpy(),
            "largeur_m": (b.maxx - b.minx).round(2).to_numpy(), "hauteur_m": (b.maxy - b.miny).round(2).to_numpy(),
            "Xmin": sous.Xmin.round(1).to_numpy(), "Ymin": sous.Ymin.round(1).to_numpy(),
            "Xmax": sous.Xmax.round(1).to_numpy(), "Ymax": sous.Ymax.round(1).to_numpy(),
        })
        attributs["aire_m2"] = (attributs.largeur_m * attributs.hauteur_m).round(2)
        points.append(gpd.GeoDataFrame(attributs, geometry=pts.to_numpy(), crs=CRS_SORTIE))
        boites.append(gpd.GeoDataFrame(attributs, geometry=bx.to_numpy(), crs=CRS_SORTIE))
        emprise = gpd.GeoSeries([box(*bornes)], crs=crs_src).to_crs(CRS_SORTIE)
        sites.append(gpd.GeoDataFrame({"site": [site], "split": [decoupage[site]]}, geometry=emprise.to_numpy(),
                                      crs=CRS_SORTIE))

    pts = pd.concat(points, ignore_index=True)
    bxs = pd.concat(boites, ignore_index=True)
    gardes, conflits = fusionner_doublons(pts, args.doublon_m)
    pts_avant = pts
    pts, bxs = pts.loc[gardes].reset_index(drop=True), bxs.loc[gardes].reset_index(drop=True)
    pts.insert(0, "pied_id", [f"RT{i:05d}" for i in range(len(pts))])
    bxs.insert(0, "pied_id", pts.pied_id)

    # Boîtes imbriquées, signalées sans être supprimées
    paires = mesurer_imbrications(bxs, args.seuil_imbrication)
    paires.to_csv(out / "imbrications.csv", index=False)
    concernes = set(paires.pied_a) | set(paires.pied_b)
    pts["imbriquee"] = pts.pied_id.isin(concernes)
    bxs["imbriquee"] = bxs.pied_id.isin(concernes)

    pts.to_file(out / "points_pieds.geojson", driver="GeoJSON")
    bxs.to_file(out / "boites.geojson", driver="GeoJSON")
    sites_gdf = pd.concat(sites, ignore_index=True)
    sites_gdf.to_file(out / "sites.geojson", driver="GeoJSON")

    resume = pts.groupby(["split", "site"]).agg(arbres=("pied_id", "size"), bananiers=("is_banana", "sum"))
    resume["doublons_retires"] = pts_avant.groupby("site").size().reindex(resume.index.get_level_values("site")).to_numpy() \
        - resume.arbres.to_numpy()
    resume["surface_ha"] = [round(sites_gdf.set_index("site").loc[s].geometry.area / 1e4, 2)
                            for s in resume.index.get_level_values("site")]
    resume["bananiers_par_ha"] = (resume.bananiers / resume.surface_ha).round(1)
    resume["ecart_lonlat_median_m"] = [round(ecarts[s][0], 2) for s in resume.index.get_level_values("site")]
    resume["ecart_lonlat_max_m"] = [round(ecarts[s][1], 2) for s in resume.index.get_level_values("site")]
    idx_sites = resume.index.get_level_values("site")
    par_site = paires.groupby("site")
    resume["paires_imbriquees"] = [int(par_site.size().get(s, 0)) for s in idx_sites]
    resume["dont_meme_tuile"] = [int(paires[(paires.site == s) & paires.meme_tuile].shape[0]) for s in idx_sites]
    resume["dont_bananier_bananier"] = [int(paires[(paires.site == s) & paires.bananier_a & paires.bananier_b].shape[0])
                                        for s in idx_sites]
    resume["part_arbres_imbriques"] = [round(float(pts[pts.site == s].imbriquee.mean()), 3) for s in idx_sites]
    resume.to_csv(out / "resume_sites.csv")

    (out / "parametres.json").write_text(json.dumps({
        "zip": str(args.zip), "annotations": ANNOTATIONS, "crs": CRS_SORTIE, "decoupage": args.decoupage,
        "sites": decoupage, "doublon_m": args.doublon_m, "boites_lues": int(len(pts_avant)),
        "pieds_apres_fusion": int(len(pts)), "groupes_a_etiquettes_contradictoires": int(conflits),
        "seuil_imbrication": args.seuil_imbrication, "paires_imbriquees": int(len(paires)),
        "arbres_dans_une_paire_imbriquee": int(len(concernes)),
        "point_du_pied": "centre de la boîte annotée"}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Boîtes lues : {len(pts_avant)} | après fusion des doublons (< {args.doublon_m} m, tuiles différentes) : "
          f"{len(pts)} | groupes aux étiquettes contradictoires : {conflits}")
    print(resume.to_string())
    print(f"\nBoîtes imbriquées (plus petite contenue à plus de {args.seuil_imbrication:.0%}) : {len(paires)} paires, "
          f"{len(concernes)} arbres concernés sur {len(pts)} ({len(concernes) / max(len(pts), 1):.1%}), "
          f"dont {int(paires.meme_tuile.sum())} paires dans une même tuile")
    print("\nTotal par ensemble :")
    print(pts.groupby("split").agg(arbres=("pied_id", "size"), bananiers=("is_banana", "sum")).to_string())
    print(f"\nRésultats dans {out}/")


if __name__ == "__main__":
    main()
