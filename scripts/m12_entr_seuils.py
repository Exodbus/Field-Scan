#!/usr/bin/env python3
"""Réglage des seuils d'un candidat v12 sur le RÉGLAGE seulement (Tanzanie, moyenne des plis, + TDTU, PSFD, Éthiopie).

Grille : seuil_alerte (0,725 à 0,98) × seuil de confiance / règle B (0,02 à 0,70 ; avec la règle B, une photo est dite saine si P(saine) ≥ max(règle B, 1 − alerte)) ; seuil_nom et seuil_inconnu_malade de la v10b.
Couple retenu : coût moyen le plus bas parmi ceux qui respectent les contraintes « finaliste » (Tanzanie ≤ 14 ratées et
≤ 77 fausses alertes, aucun pays ne perd plus de 2 points de malades sans alerte). Chaque appel compte pour un essai.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_entr_seuils.py <dossier> <candidat>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m12_entr_mesurer as M  # noqa: E402

dossier, nom = sys.argv[1], sys.argv[2]
pays, val = M.charger_recette(dossier, nom)
meilleur = None
for sa in [0.725, 0.8, 0.85, 0.9, 0.95, 0.98]:
    for sc in np.round(np.arange(0.02, 0.701, 0.01), 3):
        m = dict(M.M_V10B, seuil_alerte=float(sa), seuil=float(sc))
        b = M.bilan(pays, val, m)
        tz = b["comptes"]["validation"]
        ok = tz[0] <= 14 and tz[2] <= 77 and all(v <= 2 for v in b["perte_pays"].values())
        if ok and (meilleur is None or b["cout_moyen"] < meilleur[2]["cout_moyen"]):
            meilleur = (float(sa), float(sc), b)
if meilleur is None:
    print(nom, ": aucun couple ne respecte les contraintes")
else:
    sa, sc, b = meilleur
    print(M.ENTETE)
    print(M.ligne(f"{nom} seuils réglés (alerte {sa}, règle B {sc})", b))
    d = Path(dossier) / nom if (Path(dossier) / nom).is_dir() else Path(dossier)
    (d / f"seuils_regles_{nom}.json").write_text(json.dumps(dict(seuil_alerte=sa, seuil_confiance=sc, bilan=b), ensure_ascii=False, indent=1), encoding="utf-8")
