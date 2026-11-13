#!/usr/bin/env python3
"""Contrôle de l'optimisme du réglage de la règle B (information, ne change aucune règle) : pour chaque jeu de réglage J,
le seuil est choisi sur les 3 autres jeux (coût moyen le plus bas), puis appliqué à J. Coût moyen « croisé » à comparer
au coût réglé sur les 4 jeux.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_entr_seuil_croise.py <dossier> <candidat> [...]"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m12_entr_mesurer as M  # noqa: E402

GRILLE = np.round(np.arange(0.30, 0.801, 0.01), 2)
for nom in sys.argv[2:]:
    pays, val = M.charger_recette(sys.argv[1], nom)
    couts = {}
    for sc in GRILLE:
        b = M.bilan(pays, val, dict(M.M_V10B, seuil=float(sc)))
        couts[sc] = b["couts"]
    jeux = list(couts[GRILLE[0]].keys())
    croise, choix = [], []
    for j in jeux:
        autres = [k for k in jeux if k != j]
        s = min(GRILLE, key=lambda sc: np.mean([couts[sc][k] for k in autres]))
        croise.append(couts[s][j]); choix.append(f"{j}:{s}")
    print(f"{nom} : coût croisé {np.mean(croise):.2f} ({', '.join(f'{c:.1f}' for c in croise)}) ; seuils {' '.join(choix)}")
