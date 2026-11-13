#!/usr/bin/env python3
"""Esquisse chiffrée d'un aiguillage par image (agent C-analyste), pour orienter C-banc (essai 5), pas pour choisir.
Signal sans annotation : p90 = 90e centile des scores des pics du v5 >= 0,15 dans la zone comptée.
Règles comparées au v5 seul (seuil 0,30) :
  A(c, s) : seuil du v5 = s si p90 < c, sinon 0,30 ;
  B(c)    : v3 au seuil 0,20 si p90 < c, sinon v5 à 0,30.
Sortie : F1 et détectés / annotés par jeu de réglage, et fausses détections sur les images sans bananier si en cache.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_aiguillage.py
"""
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_analyse_erreurs as ae  # noqa: E402

bc = ae.bc
JEUX = ["dense", "plantain", "jeunes", "mm", "btd_val"]
REGLES = [("v5 seul 0,30", None, None, None), ("A c=0,50 s=0,15", 0.50, 0.15, "v5"), ("A c=0,50 s=0,20", 0.50, 0.20, "v5"),
          ("A c=0,45 s=0,15", 0.45, 0.15, "v5"), ("B c=0,50 (v3 0,20)", 0.50, 0.20, "v3")]


def p90(xy, sc):
    s = sc[sc >= 0.15]
    return np.percentile(s, 90) if len(s) else 0.0


def det(nom_jeu, e, regle):
    _, c, s, m = regle
    xy, sc = bc.pics(ae.carte("v5", "base", nom_jeu, e["nom"]), bc.K_PICS, 0.15)
    if "masque" in e:
        g = ae.dans_compte(xy, e) if len(xy) else np.zeros(0, bool)
        xy, sc = xy[g], sc[g]
    if c is None or p90(xy, sc) >= c:
        return xy[sc >= 0.30]
    if m == "v5":
        return xy[sc >= s]
    xy3, sc3 = bc.pics(ae.carte("v3", "base", nom_jeu, e["nom"]), bc.K_PICS, s)
    if "masque" in e:
        g = ae.dans_compte(xy3, e) if len(xy3) else np.zeros(0, bool)
        xy3 = xy3[g]
    return xy3


out = ["# Esquisse d'aiguillage par image [M]\n", "`scripts/v6_analyse_aiguillage.py`. 4 règles regardées sur le réglage : chiffres optimistes, à refaire par C-banc avec sa règle.\n",
       "| règle | " + " | ".join(JEUX) + " | moyenne F1 | sans bananier (fausses) |", "|" + " --- |" * (len(JEUX) + 3)]
items = {j: ae.items_complets(j) for j in JEUX}
try:
    neg = bc.jeu("neg"); ae.carte("v5", "base", "neg", neg[0]["nom"])
except Exception:
    neg = None
for r in REGLES:
    cells, f1s = [], []
    for j in JEUX:
        vp = fp = fn = nd = 0
        for e in items[j]:
            d = det(j, e, r)
            n, f, m = bc.compter(d, e["pts"], e["ign"]); vp += n; fp += f; fn += m; nd += len(d)
        f1 = bc.prf(vp, fp, fn)[2]; f1s.append(f1)
        cells.append(f"{f1:.3f} ({nd / (vp + fn):.2f})")
    nf = "-"
    if neg is not None:
        tot = arb = 0
        for e in neg:
            e2 = dict(e); e2.pop("masque", None)
            tot += len(det("neg", e2, r)); arb += e["n_autres"]
        nf = f"{tot} ({tot / arb:.2%})"
    out.append(f"| {r[0]} | " + " | ".join(cells) + f" | {np.mean(f1s):.3f} | {nf} |")
    print(out[-1], flush=True)
(ae.SORTIE / "aiguillage.md").write_text("\n".join(out) + "\n", encoding="utf-8")
