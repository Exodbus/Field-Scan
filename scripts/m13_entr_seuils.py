#!/usr/bin/env python3
"""Réglage de la confiance (règle B) d'un élève sur le réglage (5 jeux), grille 0,40 à 0,80 par pas de 0,01 ; le seuil
retenu minimise le coût de réglage parmi ceux qui remplissent les conditions « finaliste » sans le temps (plan 4.3).
Compté comme un essai par candidat ; chiffre optimiste (seuil choisi sur les jeux qui le mesurent). Contrôle « croisé » :
pour chaque jeu, seuil choisi sur les 4 autres (sans contrainte) et appliqué au jeu laissé de côté.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_seuils.py <dossier> <candidat> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_entr_mesurer as M  # noqa: E402

GRILLE = np.round(np.arange(0.40, 0.801, 0.01), 2)
ref = M.reference_f1()
for nom in sys.argv[2:]:
    P = M.charger(sys.argv[1], nom)
    res = {float(s): M.bilan(P, ref, float(s)) for s in GRILLE}
    ok = {s: r for s, r in res.items() if r["finaliste_sans_temps"]}
    meilleur = min(ok, key=lambda s: ok[s]["cout_reglage"]) if ok else min(res, key=lambda s: res[s]["cout_reglage"])
    croise = []
    for j in M.REGLAGE5:
        autres = [k for k in M.REGLAGE5 if k != j]
        s = min(res, key=lambda s: np.mean([res[s][k]["cout"] for k in autres]))
        croise.append(res[s][j]["cout"])
    r = res[meilleur]
    print(M.ligne(f"{nom} confiance {meilleur:.2f}", r))
    print(f"   finaliste (sans temps) : {r['finaliste_sans_temps']} {r['conditions_sans_temps']} | seuils valides : "
          f"{sorted(ok)[:1]}..{sorted(ok)[-1:]} ({len(ok)}) | coût croisé {np.mean(croise):.2f}")
    (Path(sys.argv[1]) / f"seuils_{nom}.json").write_text(json.dumps(dict(seuil=meilleur, cout=r["cout_reglage"], cout_croise=float(np.mean(croise)),
        valides=sorted(ok), bilan=r), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
