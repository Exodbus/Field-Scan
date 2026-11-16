#!/usr/bin/env python3
"""Mesure du candidat livrable « ensemble des 2 réseaux des plis » (décision de 13 h 45, journal M-entraîneur) :
TDTU et Éthiopie lus par le réseau qui ne les a pas appris ; validation, PSFD, AgroVisionBD et roamer_dev_loin lus par
l'ensemble (moyenne des probabilités des 2 réseaux). Couple de confiances (s_p, s_l) repris de l'essai déjà fait sur la
recette (seuils2_<recette>.json du lot 1), sans nouveau réglage.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_ensemble.py <lot> <candidat>:<recette> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_entr_mesurer as M  # noqa: E402
import m13_entr_seuils2 as S2  # noqa: E402,F401

ref = M.reference_f1()
lot = sys.argv[1]
for arg in sys.argv[2:]:
    nom, recette = arg.split(":")
    couple = tuple(json.loads((M.KAG / "lot1" / f"seuils2_{recette}.json").read_text(encoding="utf-8"))["couple"])
    P = M.charger(M.KAG / lot, nom)
    E = {j: (Ps if j in ("tdtu", "ethiopie") else [np.mean(Ps, 0)]) for j, Ps in P.items()}
    for titre, Q in (("moyenne des plis", P), ("ensemble livrable", E)):
        r = M.bilan(Q, ref, couple)
        print(M.ligne(f"{nom} {titre} {couple}", r))
        print("   finaliste (sans temps) :", r["finaliste_sans_temps"], r["conditions_sans_temps"], "| décisions ≠ F1", r["decisions_differentes_F1"])
        (M.KAG / lot / f"bilan_{nom}_{titre.replace(' ', '_')}.json").write_text(json.dumps(dict(couple=couple, **r), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
