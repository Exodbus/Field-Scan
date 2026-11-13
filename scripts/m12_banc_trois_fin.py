#!/usr/bin/env python3
"""Essai 7, suite : grille fine (0,60 à 0,84 par 0,02) pour les mélanges à trois (1,1,1) et (2,2,1), qui touchaient le
bord de la première grille (0,74). Sert à voir s'il y a un plateau. Réglage seul."""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from m12_banc_trois import geo3, reponses, jeux, ref  # noqa: E402

ESSAIS = []
for w in [(1, 1, 1), (2, 2, 1), (1, 1, 0)]:
    print(f"\n--- géo {w} ---")
    for t in [round(x, 2) for x in np.arange(0.60, 0.841, 0.02)]:
        r = {j: B.mesure(d, reponses(d, lambda d, w=w: geo3(d, *w), t)) for j, d in jeux.items()}
        r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
        ok, det = B.finaliste(r, ref)
        ESSAIS.append(dict(famille="essai 7 fin", nom=f"géo {w} t={t}", finaliste=ok, detail=det, **r))
        print(("F " if ok else "  ") + B.ligne(f"t={t}", r) + f" pire={max(r[j]['cout'] for j in B.REGLAGE):.1f}")
print("essais :", len(ESSAIS))
(B.SORTIE / "essais_trois_fin.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
