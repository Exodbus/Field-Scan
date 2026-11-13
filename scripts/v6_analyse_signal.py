#!/usr/bin/env python3
"""Signaux mesurables sur l'image seule (sans annotation) pour un aiguillage de seuil ou de modèle (agent C-analyste).
Par image et par jeu de réglage, avec la carte du v5 (et du v3) : nombre de pics >= 0,15 par 100 m², espacement médian
entre pics >= 0,15 (plus proche voisin, px à 5 cm), médiane et 90e centile des scores des pics >= 0,15. On regarde si
btd_val (petits plants) se sépare des autres jeux, et on donne la taille médiane des boîtes annotées pour lecture.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_signal.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_analyse_erreurs as ae  # noqa: E402

bc = ae.bc
L = []
for j in ["dense", "plantain", "jeunes", "mm", "btd_val"]:
    for e in ae.items_complets(j):
        for m in ("v5", "v3"):
            xy, sc = bc.pics(ae.carte(m, "base", j, e["nom"]), bc.K_PICS, 0.15)
            g = ae.dans_compte(xy, e) if len(xy) else np.zeros(0, bool)
            xy, sc = xy[g], sc[g]
            # surface comptée (px) approximée sur une grille de 4 px
            yy, xx = np.mgrid[0:e["h"]:4, 0:e["l"]:4]
            surf = ae.dans_compte(np.c_[xx.ravel() + 2, yy.ravel() + 2].astype(float), e).sum() * 16
            esp = np.median(cKDTree(xy).query(xy, k=2)[0][:, 1]) if len(xy) > 2 else np.nan
            L.append(dict(jeu=j, image=e["nom"], modele=m, n=len(xy), dens=len(xy) / (surf * 0.0025) * 100 if surf else np.nan,
                          esp=esp, med=np.median(sc) if len(sc) else np.nan, p90=np.percentile(sc, 90) if len(sc) else np.nan,
                          taille=np.nanmedian(e["taille"]) if len(e["taille"]) else np.nan, n_annot=len(e["pts"])))
D = pd.DataFrame(L)
D.to_csv(ae.SORTIE / "signaux_images.csv", index=False)
out = ["# Signaux par image (sans annotation) [M]\n", "`scripts/v6_analyse_signal.py` ; pics >= 0,15 dans la zone comptée. Quantiles 10 / 50 / 90 % sur les images du jeu.\n",
       "| modèle | jeu | images | pics / 100 m² | espacement médian (px) | score médian des pics | 90e centile des scores |", "| --- | --- | --- | --- | --- | --- | --- |"]
q = lambda s: " / ".join(f"{v:.2f}" if abs(v) < 10 else f"{v:.0f}" for v in np.nanpercentile(s, [10, 50, 90]))
for (m, j), g in D.groupby(["modele", "jeu"], sort=False):
    out.append(f"| {m} | {j} | {len(g)} | {q(g.dens)} | {q(g.esp)} | {q(g.med)} | {q(g.p90)} |")
(ae.SORTIE / "signaux.md").write_text("\n".join(out) + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8"); print("\n".join(out))
