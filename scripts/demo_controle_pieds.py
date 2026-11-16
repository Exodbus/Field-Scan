#!/usr/bin/env python3
"""Démo finale : contrôle visuel du comptage sur toute l'exploitation (aucune référence, aucune annotation).

Copie de `scripts/eloro_controle_pieds.py`, avec le site en paramètre (`--site martinique|silkwood`) ; même règle
de choix des extraits. Les extraits sont lus dans la résolution native de l'ortho (20 cm ou environ 9,5 cm), dans
un système UTM (WarpedVRT, plus proche voisin), et agrandis à l'affichage.

1. Vue d'ensemble (0,5 m par pixel) : parcelles automatiques et pieds détectés par la chaîne.
2. Extraits à pleine résolution (6,4 cm) : carrés de 40 m centrés sur le point représentatif (shapely
   representative_point, choix sans regard aux détections) des parcelles retenues, pieds détectés en rouge.
   Parcelles retenues : les 6 qui ont le plus de pieds détectés, plus les 2 de plus forte densité si elles
   n'y sont pas déjà. Si le carré du point représentatif contient moins de 5 détections, un second carré est
   centré sur la médiane des détections de la parcelle (pour voir ce que le détecteur y a pris).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_controle_pieds.py --site martinique
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

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SITES = {
    "martinique": dict(ortho=RACINE / "data/raw/ortho_martinique_basse_pointe/ortho_martinique_basse_pointe_2025_20cm.tif",
                       demo=RACINE / "out/demo_martinique", nom="Martinique (Basse-Pointe, IGN 20 cm)", res=0.20),
    "silkwood": dict(ortho=RACINE / "data/raw/ortho_qld_silkwood_2022/ortho_qld_silkwood_2022_10cm.tif",
                     demo=RACINE / "out/demo_silkwood", nom="Silkwood (Queensland, SISP 10 cm)", res=0.095),
}
COTE = 40.0


def lire_utm(src, crs, bornes, res, resampling, masquer=True):
    """RGB (H, W, 3) uint8 de la fenêtre `bornes` (x0, y0, x1, y1) en `crs`, au pas `res` (m)."""
    from rasterio.transform import from_origin
    from rasterio.vrt import WarpedVRT
    x0, y0, x1, y1 = bornes
    W, H = int(np.ceil((x1 - x0) / res)), int(np.ceil((y1 - y0) / res))
    with WarpedVRT(src, crs=crs, transform=from_origin(x0, y1, res, res), width=W, height=H,
                   resampling=resampling, nodata=0) as v:
        a = v.read([1, 2, 3])
    img = np.moveaxis(a, 0, -1).copy()
    if masquer:   # hors couverture en blanc (vue d'ensemble seulement : les ombres sont presque noires à pleine résolution)
        img[a.astype(int).sum(0) <= 15] = 255
    return img


def main():
    import argparse
    from shapely.geometry import Point
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", choices=list(SITES), required=True)
    ap.add_argument("--cote", type=float, default=COTE, help="côté des extraits (m)")
    args = ap.parse_args()
    site = SITES[args.site]
    DEMO, cote = site["demo"], args.cote
    sortie = DEMO / "controle_pieds"
    sortie.mkdir(parents=True, exist_ok=True)
    parc = gpd.read_file(DEMO / "parcelles_auto.geojson")
    crs = parc.estimate_utm_crs()
    parc = parc.to_crs(crs)
    pieds = gpd.read_file(DEMO / "chaine/pieds.geojson").to_crs(crs)
    tab = pd.read_csv(DEMO / "chaine/comptage_parcelles.csv").set_index("parcelle_id")
    with rasterio.open(site["ortho"]) as s:
        # 1. vue d'ensemble (0,5 m)
        b = parc.total_bounds
        img = lire_utm(s, crs, b, 0.5, Resampling.average)
        fig, ax = plt.subplots(figsize=(20, 20 * img.shape[0] / img.shape[1] + 0.6), dpi=100)
        ax.imshow(img, extent=(b[0], b[0] + img.shape[1] * 0.5, b[3] - img.shape[0] * 0.5, b[3]))
        parc.boundary.plot(ax=ax, color="yellow", linewidth=0.8)
        ax.scatter(pieds.geometry.x, pieds.geometry.y, s=0.3, c="red", edgecolors="none")
        for _, r in parc.iterrows():
            p = r.geometry.representative_point()
            n = int(tab.n_pieds.get(r.parcelle_id, 0)) if r.parcelle_id in tab.index else 0
            ax.text(p.x, p.y, f"{r.parcelle_id}\n{n}", color="white", fontsize=6, ha="center", va="center",
                    bbox=dict(facecolor="black", alpha=0.5, pad=1, edgecolor="none"))
        ax.set_axis_off()
        ax.set_title(f"{site['nom']} : {len(pieds)} pieds détectés (détecteur v5), {len(parc)} parcelles automatiques",
                     fontsize=12)
        fig.tight_layout(); fig.savefig(sortie / "vue_ensemble.png"); plt.close(fig)

        # 2. extraits à pleine résolution : 6 parcelles les plus peuplées + 2 plus denses (règle d'El Oro)
        choix = list(tab.sort_values("n_pieds", ascending=False).index[:6])
        choix += [p for p in tab[tab.n_pieds >= 20].sort_values("densite_ha", ascending=False).index[:2] if p not in choix]
        geoms = parc.set_index("parcelle_id").geometry
        lignes, centres = [], []
        for pid in choix:
            c = geoms[pid].representative_point()
            centres.append((pid, "rep", c))
            n_rep = len(pieds.cx[c.x - cote / 2:c.x + cote / 2, c.y - cote / 2:c.y + cote / 2])
            pp = pieds[pieds.parcelle_id == pid]
            if n_rep < 5 and len(pp):
                centres.append((pid, "det", Point(pp.geometry.x.median(), pp.geometry.y.median())))
        for pid, genre, c in centres:
            x0, y0, x1, y1 = c.x - cote / 2, c.y - cote / 2, c.x + cote / 2, c.y + cote / 2
            rgb = lire_utm(s, crs, (x0, y0, x1, y1), site["res"], Resampling.nearest, masquer=False)
            dedans = pieds.cx[x0:x1, y0:y1]
            fig, axs = plt.subplots(1, 2, figsize=(16, 8.3), dpi=100)
            for k, ax in enumerate(axs):
                ax.imshow(rgb, extent=(x0, x1, y0, y1), interpolation="nearest")
                if k == 1:
                    ax.scatter(dedans.geometry.x, dedans.geometry.y, s=30, facecolors="none", edgecolors="red", linewidths=1.3)
                    geoms[[pid]].boundary.plot(ax=ax, color="yellow", linewidth=1.5)
                ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off()
            r = tab.loc[pid]
            axs[0].set_title(f"{pid} ({'point représentatif' if genre == 'rep' else 'médiane des détections'}) : "
                             f"carré de {cote:.0f} m, pixel natif {site['res'] * 100:.1f} cm", fontsize=10)
            axs[1].set_title(f"{len(dedans)} pieds détectés dans le carré ; parcelle : {int(r.n_pieds)} pieds, "
                             f"{r.densite_ha:.0f}/ha", fontsize=10)
            fig.tight_layout(); fig.savefig(sortie / f"extrait_{pid}{'_detections' if genre == 'det' else ''}.png"); plt.close(fig)
            lignes.append(dict(parcelle_id=pid, centre="point représentatif" if genre == "rep" else "médiane des détections",
                               centre_x=round(c.x, 1), centre_y=round(c.y, 1), pieds_carre=len(dedans),
                               densite_carre_ha=round(len(dedans) / (cote * cote / 1e4))))
    pd.DataFrame(lignes).to_csv(sortie / "extraits.csv", index=False)
    print(pd.DataFrame(lignes).to_string(index=False))


if __name__ == "__main__":
    main()
