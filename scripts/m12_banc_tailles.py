#!/usr/bin/env python3
"""Essai « tailles » (recommandation 2 de M-analyste) : v10b lue en 224 px, en taille adaptée min(384, 2 x côté court),
et moyenne 384 + 224, dans le mélange à trois (loin « v2 ou proche »). Réglage seul.
Critère écrit avant (journal, 00 h 23) : finaliste de la règle du plan ET AUC v10b Éthiopie (224 px) >= 0,90."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from m12_banc_trois import geo3  # noqa: E402

K = B.SORTIE / "kaggle_tailles"
COLS = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
jeux = B.charger_reglage()
ref = B.reference(jeux)
for j, d in jeux.items():
    for nom in ("p224", "padapt"):
        x = pd.read_csv(K / f"{nom}_{j}.csv")
        assert list(x.chemin) == list(d["chemin"])
        d[nom] = x[COLS].to_numpy("float64")


def auc(score, malade):
    r = rankdata(score)
    n1, n0 = malade.sum(), (~malade).sum()
    return (r[malade].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n0 else float("nan")


LECT = {"384": lambda d: d["P10"], "224": lambda d: d["p224"], "adaptée": lambda d: d["padapt"],
        "moyenne 384 + 224": lambda d: (d["P10"] + d["p224"]) / 2}
print("AUC de la v10b seule (1 - P(saine)), toutes photos :")
for n, f in LECT.items():
    print(f"  {n:18s} " + " ".join(f"{j} {auc(1 - f(d)[:, 0], d['malade']):.3f}" for j, d in jeux.items() if (~d['malade']).any()))
print("AUC du mélange à trois :")
for n, f in LECT.items():
    print(f"  {n:18s} " + " ".join(f"{j} {auc(1 - geo3({**d, 'P10': f(d)}, 1, 1, 1)[:, 0], d['malade']):.3f}" for j, d in jeux.items() if (~d['malade']).any()))
ESSAIS = []
for n, f in LECT.items():
    if n == "384":
        continue
    print(f"\n--- à trois, v10b lue en {n}, loin « ou » ---")
    for t in [round(x, 2) for x in np.arange(0.60, 0.821, 0.02)]:
        r = {}
        for j, d in jeux.items():
            rp = B.decider_v10b(geo3({**d, "P10": f(d)}, 1, 1, 1), seuil=t)
            rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
            r[j] = B.mesure(d, np.where(d["loin"], rl, rp))
        r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
        ok, det = B.finaliste(r, ref)
        ESSAIS.append(dict(famille="tailles", nom=f"à trois / {n} / t={t}", finaliste=ok, detail=det, **r))
        print(("F " if ok else "  ") + B.ligne(f"t={t}", r), flush=True)
print("essais :", len(ESSAIS))
(B.SORTIE / "essais_tailles.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
