#!/usr/bin/env python3
"""Démo El Oro : contrôle visuel du comptage sur toute l'exploitation (aucune référence, aucune annotation).

1. Vue d'ensemble (0,5 m par pixel) : parcelles automatiques et pieds détectés par la chaîne.
2. Extraits à pleine résolution (6,4 cm) : carrés de 40 m centrés sur le point représentatif (shapely
   representative_point, choix sans regard aux détections) des parcelles retenues, pieds détectés en rouge.
   Parcelles retenues : les 6 qui ont le plus de pieds détectés, plus les 2 de plus forte densité si elles
   n'y sont pas déjà. Si le carré du point représentatif contient moins de 5 détections, un second carré est
   centré sur la médiane des détections de la parcelle (pour voir ce que le détecteur y a pris).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/eloro_controle_pieds.py
"""
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORTHO = RACINE / "data/drone/reforestree/wwf_ecuador/RGB Orthomosaics/El Oro OAM RGB.tif"
DEMO = RACINE / "out/demo_eloro"
COTE = 40.0


def main():
    sortie = DEMO / "controle_pieds"
    sortie.mkdir(parents=True, exist_ok=True)
    with rasterio.open(ORTHO) as s:
        crs = s.crs
        parc = gpd.read_file(DEMO / "parcelles_auto.geojson").to_crs(crs)
        pieds = gpd.read_file(DEMO / "chaine/pieds.geojson").to_crs(crs)
        tab = pd.read_csv(DEMO / "chaine/comptage_parcelles.csv").set_index("parcelle_id")

        # 1. vue d'ensemble
        f = abs(s.transform.a) / 0.5
        H, W = int(s.height * f), int(s.width * f)
        a = s.read([1, 2, 3], out_shape=(3, H, W), resampling=Resampling.average)
        img = np.moveaxis(a, 0, -1).copy()
        img[a.sum(0) == 0] = 255
        b = s.bounds
        fig, ax = plt.subplots(figsize=(14, 14), dpi=100)
        ax.imshow(img, extent=(b.left, b.right, b.bottom, b.top))
        parc.boundary.plot(ax=ax, color="yellow", linewidth=1.2)
        ax.scatter(pieds.geometry.x, pieds.geometry.y, s=1.5, c="red", edgecolors="none")
        for _, r in parc.iterrows():
            p = r.geometry.representative_point()
            n = int(tab.n_pieds.get(r.parcelle_id, 0)) if r.parcelle_id in tab.index else 0
            ax.text(p.x, p.y, f"{r.parcelle_id}\n{n}", color="white", fontsize=8, ha="center", va="center",
                    bbox=dict(facecolor="black", alpha=0.5, pad=1, edgecolor="none"))
        ax.set_axis_off()
        ax.set_title(f"El Oro : {len(pieds)} pieds détectés (détecteur v5), {len(parc)} parcelles automatiques", fontsize=12)
        fig.tight_layout(); fig.savefig(sortie / "vue_ensemble.png"); plt.close(fig)

        # 2. extraits à pleine résolution
        choix = list(tab.sort_values("n_pieds", ascending=False).index[:6])
        choix += [p for p in tab[tab.n_pieds >= 20].sort_values("densite_ha", ascending=False).index[:2] if p not in choix]
        geoms = parc.set_index("parcelle_id").geometry
        lignes = []
        centres = []
        for pid in choix:
            c = geoms[pid].representative_point()
            centres.append((pid, "rep", c))
            n_rep = len(pieds.cx[c.x - COTE / 2:c.x + COTE / 2, c.y - COTE / 2:c.y + COTE / 2])
            pp = pieds[pieds.parcelle_id == pid]
            if n_rep < 5 and len(pp):
                from shapely.geometry import Point
                centres.append((pid, "det", Point(pp.geometry.x.median(), pp.geometry.y.median())))
        for pid, genre, c in centres:
            x0, y0, x1, y1 = c.x - COTE / 2, c.y - COTE / 2, c.x + COTE / 2, c.y + COTE / 2
            w = from_bounds(x0, y0, x1, y1, s.transform)
            rgb = np.moveaxis(s.read([1, 2, 3], window=w, boundless=True, fill_value=255), 0, -1)
            dedans = pieds.cx[x0:x1, y0:y1]
            fig, axs = plt.subplots(1, 2, figsize=(14, 7.2), dpi=100)
            for k, ax in enumerate(axs):
                ax.imshow(rgb, extent=(x0, x1, y0, y1))
                if k == 1:
                    ax.scatter(dedans.geometry.x, dedans.geometry.y, s=40, facecolors="none", edgecolors="red", linewidths=1.4)
                    geoms[[pid]].boundary.plot(ax=ax, color="yellow", linewidth=1.5)
                ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off()
            r = tab.loc[pid]
            axs[0].set_title(f"{pid} ({'point représentatif' if genre == 'rep' else 'médiane des détections'}) : image (carré de {COTE:.0f} m, 6,4 cm/px)", fontsize=10)
            axs[1].set_title(f"{len(dedans)} pieds détectés dans le carré ; parcelle : {int(r.n_pieds)} pieds, "
                             f"{r.densite_ha:.0f}/ha", fontsize=10)
            fig.tight_layout(); fig.savefig(sortie / f"extrait_{pid}{'_detections' if genre == 'det' else ''}.png"); plt.close(fig)
            lignes.append(dict(parcelle_id=pid, centre="point représentatif" if genre == "rep" else "médiane des détections", centre_x=round(c.x, 1), centre_y=round(c.y, 1), pieds_carre=len(dedans)))
    pd.DataFrame(lignes).to_csv(sortie / "extraits.csv", index=False)
    print(pd.DataFrame(lignes).to_string(index=False))


if __name__ == "__main__":
    main()
