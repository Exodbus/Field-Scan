#!/usr/bin/env python3
"""Parcelles RPG (déclarées à la PAC) de Basse-Pointe, découpées sur l'emprise de l'orthophoto, et comparaison avec les
parcelles automatiques (out/demo_martinique/parcelles_auto_utm.geojson).

Le RPG est une donnée d'entrée (le parcellaire de l'exploitant), pas une référence d'évaluation : la comparaison est
donnée pour information, sans seuil ni décision.

Sorties dans out/demo_martinique_rpg/ :
  parcelles_rpg.geojson (EPSG:4326, pour run.py), parcelles_rpg_utm.geojson (EPSG:5490),
  comparaison_auto_rpg.csv, comparaison_resume.json, comparaison_auto_rpg.jpg

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_martinique_rpg.py
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from shapely.geometry import box  # noqa: E402

RPG = RACINE / "data/raw/rpg_martinique_basse_pointe"
ORTHO = RACINE / "data/raw/ortho_martinique_basse_pointe/ortho_martinique_basse_pointe_2025_20cm.tif"
AUTO = RACINE / "out/demo_martinique/parcelles_auto_utm.geojson"
OUT = RACINE / "out/demo_martinique_rpg"
SURFACE_MIN_HA = 0.1        # morceaux de bord plus petits : retirés après le découpage


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    codes = {f["properties"]["code_culture"]: f["properties"]["libelle_culture"]
             for f in json.loads((RPG / "codes_cultures.json").read_text(encoding="utf-8"))["features"]}
    with rasterio.open(ORTHO) as src:
        b = src.bounds
        assert src.crs.to_epsg() == 5490
    emprise = box(b.left, b.bottom, b.right, b.top)
    g = gpd.read_file(RPG / "parcelles_graphiques.geojson").to_crs(5490)
    g["geometry"] = g.geometry.make_valid().intersection(emprise)
    g = g[~g.geometry.is_empty].copy()
    g["surface_ha"] = (g.area / 1e4).round(3)
    g = g[g.surface_ha >= SURFACE_MIN_HA].copy()
    # identifiants R001... du nord-ouest au sud-est (par bandes de 300 m)
    c = g.geometry.representative_point()
    g["_ordre"] = ((b.top - c.y) // 300) * 1e6 + (c.x - b.left)
    g = g.sort_values("_ordre").reset_index(drop=True)
    g["parcelle_id"] = [f"R{i + 1:03d}" for i in range(len(g))]
    g["culture_code"] = g["code_cultu"]
    g["culture"] = g["code_cultu"].map(codes)
    g["source"] = "RPG (IGN, Etalab 2.0)"
    garder = ["parcelle_id", "culture_code", "culture", "surface_ha", "num_ilot", "num_parcel", "source", "geometry"]
    g = g[garder]
    g.to_file(OUT / "parcelles_rpg_utm.geojson", driver="GeoJSON")
    g.to_crs(4326).to_file(OUT / "parcelles_rpg.geojson", driver="GeoJSON")
    print(f"{len(g)} parcelles RPG dans l'emprise ({g.surface_ha.sum():.1f} ha) ;",
          g.groupby("culture_code").surface_ha.agg(["count", "sum"]).round(1).to_dict("index"))

    # comparaison (information) : pour chaque parcelle RPG, la parcelle automatique de plus grand recouvrement
    a = gpd.read_file(AUTO).to_crs(5490)
    a["geometry"] = a.geometry.make_valid()
    lignes = []
    for r in g.itertuples():
        cand = a[a.intersects(r.geometry)]
        best = (None, 0.0, 0.0)
        for q in cand.itertuples():
            inter = r.geometry.intersection(q.geometry).area
            iou = inter / r.geometry.union(q.geometry).area
            if iou > best[1]:
                best = (q.parcelle_id, iou, inter / r.geometry.area)
        lignes.append(dict(parcelle_rpg=r.parcelle_id, culture=r.culture_code, surface_ha=r.surface_ha,
                           auto_meilleure=best[0], iou=round(best[1], 3), part_couverte=round(best[2], 3),
                           n_auto_touchees=int(len(cand))))
    t = pd.DataFrame(lignes)
    t.to_csv(OUT / "comparaison_auto_rpg.csv", index=False, encoding="utf-8")
    ban = t[t.culture == "BEF"]
    resume = dict(
        parcelles_rpg=len(t), parcelles_auto=len(a),
        iou_median=round(float(t.iou.median()), 3),
        part_iou_sup_0_7=round(float((t.iou >= 0.7).mean()), 3),
        part_iou_sup_0_5=round(float((t.iou >= 0.5).mean()), 3),
        bananeraie_iou_median=round(float(ban.iou.median()), 3),
        bananeraie_part_iou_sup_0_7=round(float((ban.iou >= 0.7).mean()), 3),
        auto_par_parcelle_rpg_mediane=float(t.n_auto_touchees.median()),
        note="Information seulement : le RPG est le parcellaire déclaré, pas une vérité terrain du découpage visuel "
             "(une parcelle déclarée peut regrouper plusieurs blocs, ou en partager un).")
    (OUT / "comparaison_resume.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(resume, ensure_ascii=False, indent=1))

    # image : RPG (bananes en cyan, canne en magenta, autres en blanc) et automatiques (jaune fin), à 1 m/px
    with rasterio.open(ORTHO) as src:
        k = 5
        img = src.read(out_shape=(3, src.height // k, src.width // k), resampling=Resampling.average)
    im = Image.fromarray(np.ascontiguousarray(img.transpose(1, 2, 0))).convert("RGB")
    dr = ImageDraw.Draw(im)
    res = 0.2 * k

    def px(x, y):
        return ((x - b.left) / res, (b.top - y) / res)

    def tracer(geom, couleur, largeur):
        for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            if p.geom_type == "Polygon":
                dr.line([px(*xy) for xy in p.exterior.coords], fill=couleur, width=largeur)
    for q in a.itertuples():
        tracer(q.geometry, (255, 235, 59), 1)
    couleurs = {"BEF": (0, 229, 255), "CSA": (255, 64, 200)}
    for r in g.itertuples():
        tracer(r.geometry, couleurs.get(r.culture_code, (255, 255, 255)), 3)
    im.save(OUT / "comparaison_auto_rpg.jpg", quality=85)


if __name__ == "__main__":
    main()
