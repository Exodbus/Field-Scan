#!/usr/bin/env python3
"""Démo finale : diagnostic du détecteur de centres v5 sur un carré d'une parcelle (aucun réglage modifié).

But : comprendre pourquoi la chaîne trouve (ou ne trouve pas) des pieds sur un site, sans toucher aux réglages
de la chaîne. Le carré est lu comme le fait la chaîne (fieldscan.drone.lire_fenetre : UTM, moyenne) à la
résolution du détecteur (5 cm, celle de la chaîne), puis, pour comparaison seulement, à d'autres résolutions.
On rapporte la carte de probabilité (maximum, centiles) et le nombre de pics au-dessus de plusieurs seuils.
Rien de ceci n'est une mesure de qualité : aucune référence annotée n'existe sur ces sites.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_diagnostic_comptage.py --site silkwood --parcelle P19
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import geopandas as gpd
import matplotlib
import numpy as np
from scipy.ndimage import maximum_filter

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fieldscan import drone

SITES = {
    "martinique": dict(ortho=RACINE / "data/raw/ortho_martinique_basse_pointe/ortho_martinique_basse_pointe_2025_20cm.tif",
                       demo=RACINE / "out/demo_martinique"),
    "silkwood": dict(ortho=RACINE / "data/raw/ortho_qld_silkwood_2022/ortho_qld_silkwood_2022_10cm.tif",
                     demo=RACINE / "out/demo_silkwood"),
}
MODELE = RACINE / "modeles/centres_5cm_v5.onnx"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", choices=list(SITES), required=True)
    ap.add_argument("--parcelle", required=True)
    ap.add_argument("--cote", type=float, default=40.0)
    ap.add_argument("--resolutions-cm", default="5,4,10", help="la première est celle de la chaîne")
    ap.add_argument("--fils", type=int, default=2)
    a = ap.parse_args()
    import onnxruntime as ort
    site = SITES[a.site]
    parc = gpd.read_file(site["demo"] / "parcelles_auto.geojson")
    utm = parc.estimate_utm_crs()
    parc = parc.to_crs(utm).set_index("parcelle_id")
    c = parc.geometry[a.parcelle].representative_point()
    bornes = (c.x - a.cote / 2, c.y - a.cote / 2, c.x + a.cote / 2, c.y + a.cote / 2)
    det = drone.DetecteurCentres(MODELE)
    so = ort.SessionOptions(); so.intra_op_num_threads = a.fils; so.inter_op_num_threads = 1
    det.sess = ort.InferenceSession(str(MODELE), so, providers=["CPUExecutionProvider"])
    resultats = []
    res_cm = [float(r) for r in a.resolutions_cm.split(",")]
    fig, axs = plt.subplots(2, len(res_cm), figsize=(6 * len(res_cm), 12), dpi=90)
    for k, r in enumerate(res_cm):
        rgb, valide, t = drone.lire_fenetre(site["ortho"], utm, bornes, r / 100)
        proba = det.carte(rgb, valide)
        pic = (proba == maximum_filter(proba, size=det.k_pics, mode="constant"))
        ligne = dict(resolution_cm=r, taille_px=list(valide.shape), proba_max=round(float(proba.max()), 3),
                     proba_p99=round(float(np.percentile(proba, 99)), 3), proba_p90=round(float(np.percentile(proba, 90)), 3))
        for s in (0.05, 0.1, 0.2, 0.3):
            ligne[f"pics_sup_{s}"] = int((pic & (proba >= s)).sum())
        resultats.append(ligne)
        img = np.moveaxis(rgb, 0, -1).clip(0, 255).astype("uint8")
        x0, y0, x1, y1 = bornes
        axs[0, k].imshow(img, extent=(x0, x1, y0, y1))
        j, i = np.nonzero(pic & (proba >= det.seuil))
        axs[0, k].scatter(x0 + (i + 0.5) * det.stride * r / 100, y1 - (j + 0.5) * det.stride * r / 100, s=40,
                          facecolors="none", edgecolors="red")
        axs[0, k].set_title(f"{r:g} cm/px : {ligne['pics_sup_0.3']} pics >= {det.seuil}", fontsize=11)
        im = axs[1, k].imshow(proba, vmin=0, vmax=max(0.3, float(proba.max())), cmap="magma")
        axs[1, k].set_title(f"probabilité (max {ligne['proba_max']})", fontsize=11)
        plt.colorbar(im, ax=axs[1, k], fraction=0.046)
        for ax in axs[:, k]:
            ax.set_axis_off()
    fig.suptitle(f"{a.site}, {a.parcelle} : carré de {a.cote:.0f} m au point représentatif ; détecteur v5 ; "
                 f"la chaîne travaille à {res_cm[0]:g} cm", fontsize=12)
    fig.tight_layout()
    sortie = site["demo"] / "controle_pieds"; sortie.mkdir(parents=True, exist_ok=True)
    fig.savefig(sortie / f"diagnostic_{a.parcelle}.png"); plt.close(fig)
    (sortie / f"diagnostic_{a.parcelle}.json").write_text(json.dumps(resultats, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
