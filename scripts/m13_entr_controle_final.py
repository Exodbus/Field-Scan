#!/usr/bin/env python3
"""Contrôle des modèles finaux (un réseau appris sur tout sauf PSFD, validation, AgroVisionBD) sur les jeux qu'ils n'ont
jamais appris (validation, PSFD, AgroVisionBD, roamer_dev_loin), aux couples (s_p, s_l) déjà choisis ; comparé à la
moyenne des plis et à F1. Information : TDTU et Éthiopie ont été appris par le modèle final, ils ne sont pas relus.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_controle_final.py
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_entr_mesurer as M  # noqa: E402
import m13_entr_seuils2 as S2  # noqa: E402,F401  (remplace reponse_eleve par la version à deux confiances)

ref = M.reference_f1()
out = {}
for nom in ("d2", "d3"):
    couple = tuple(json.loads((M.KAG / "lot1" / f"seuils2_{nom}.json").read_text(encoding="utf-8"))["couple"])
    for lot in ("final1", "lot1"):
        r = M.bilan(M.charger(M.KAG / lot, nom), ref, couple)
        print(M.ligne(f"{nom} {lot} {couple}", r))
        out[f"{nom}_{lot}"] = r
(M.KAG / "controle_final.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
