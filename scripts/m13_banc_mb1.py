#!/usr/bin/env python3
"""MB1 (photos vues de loin), grille écrite dans docs/nuit_2026-11-13/journal_m_banc.md (23 h 46) avant le calcul.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_mb1.py [--roamer]
"""
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_banc_commun as C  # noqa: E402
import m13_banc_regles as R  # noqa: E402

AVEC_ROAMER = "--roamer" in sys.argv
jeux = C.charger(roamer=AVEC_ROAMER)
NOMS = C.JEUX5 + (["roamer"] if AVEC_ROAMER else [])
ref = C.evaluer(jeux, C.f1, NOMS)
r2 = C.evaluer(jeux, R.f1, NOMS)
assert all((ref[j]["_alerte"] == r2[j]["_alerte"]).all() for j in NOMS), "R.f1 != F1 installé"
print(C.ligne("F1", ref), flush=True)

GRILLE = []
GRILLE += [("MB1-A", f"loin : v2 ou proche à tL={t}", R.mb1_a(t)) for t in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65)]
GRILLE += [("MB1-B", f"loin : v2 ET proche à tL={t}", R.mb1_b_et(t)) for t in (0.70, 0.80, 0.90)]
GRILLE += [("MB1-B", f"loin : proche seul à tL={t}", R.mb1_b_proche(t)) for t in (0.60, 0.70)]
GRILLE += [("MB1-C", f"aiguillage p_loin >= {s}", R.mb1_c_seuil(s)) for s in (0.3, 0.7, 0.9)]
GRILLE += [("MB1-C", f"seuil proche 0,70 - {dl} x p_loin", R.mb1_c_delta(dl)) for dl in (0.1, 0.2, 0.3)]
GRILLE += [("MB1-D", f"à vérifier -> saine si 3 lecteurs >= {m} ({p})", R.avec_marge(R.f1, m, p))
           for p in ("loin", "toutes") for m in (0.5, 0.6, 0.7, 0.8)]

cpt = C.Compteur("mb1" + ("_roamer" if AVEC_ROAMER else ""))
for fam, nom, regle in GRILLE:
    r = C.evaluer(jeux, regle, NOMS)
    ok, det, inc = C.finaliste(r, ref)
    cpt.ajouter(fam, nom, r, ok, det)
    print(("F " if ok else "  ") + C.ligne(f"{fam} {nom}", r) + f" | inconnues {inc} | {det}", flush=True)
print("essais :", cpt.ecrire())
