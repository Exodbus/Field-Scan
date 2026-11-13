#!/usr/bin/env python3
"""Essai 9 : mélange des candidats v12 (out/maladies/nuit_1112/kaggle/<nom>/) avec la v10b et le mélange à trois.

Pays : probabilités du pli qui n'a pas appris le pays. Validation Tanzanie : moyenne des 3 plis (chaque pli a vu la
Tanzanie en apprentissage mais pas la validation). Réglage seul.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_v12.py <nom> [<nom> ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402

KAG = B.SORTIE.parent / "kaggle"
COLS = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
jeux = B.charger_reglage()
ref = B.reference(jeux)


def charger(nom):
    d = KAG / nom
    out = {}
    for j in B.REGLAGE:
        if j == "validation":
            f = sorted(d.glob(f"predictions_{nom}_validation*.csv"))
            P = np.mean([pd.read_csv(x)[COLS].to_numpy("float64") for x in f], 0)
            chemins = pd.read_csv(f[0]).chemin
        else:
            x = pd.read_csv(d / f"predictions_{nom}_{j}.csv")
            P, chemins = x[COLS].to_numpy("float64"), x.chemin
        assert list(chemins) == list(jeux[j]["chemin"]), (nom, j)
        out[j] = P
    return out


def geo(Ps, poids):
    """Moyenne géométrique pondérée sur les 3 classes communes ; « autre » = moyenne pondérée des « autre » à 4 classes."""
    w = np.asarray(poids, float) / sum(poids)
    lg = sum(wi * np.log(np.clip(P[:, :3], 1e-9, 1)) for wi, P in zip(w, Ps))
    autre = sum(wi * P[:, 3] for wi, P in zip(w, Ps) if P.shape[1] == 4)
    q = np.hstack([np.exp(lg), np.asarray(autre).reshape(-1, 1) * np.ones((len(lg), 1))])
    return q / q.sum(1, keepdims=True)


ESSAIS = []
for nom in sys.argv[1:]:
    V = charger(nom)
    for desc, f, loin_ou in [
        (f"{nom} seul", lambda d, j: V[j], False),
        (f"moyenne v10b + {nom}", lambda d, j: (d["P10"] + V[j]) / 2, False),
        (f"géo v10b + {nom}", lambda d, j: geo([d["P10"], V[j]], [1, 1]), False),
        (f"géo à quatre (v10b, soupe, v2, {nom}) loin ou", lambda d, j: geo([d["P10"], d["Pso"], d["Pv2"], V[j]], [1, 1, 1, 1]), True),
        (f"géo à trois + {nom} poids 0,5, loin ou", lambda d, j: geo([d["P10"], d["Pso"], d["Pv2"], V[j]], [1, 1, 1, 0.5]), True)]:
        print(f"\n--- {desc} ---")
        for t in [0.52, 0.58, 0.62, 0.66, 0.70, 0.74, 0.78]:
            r = {}
            for j, d in jeux.items():
                rp = B.decider_v10b(f(d, j), seuil=t)
                rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp) if loin_ou else d["r_loin"]
                r[j] = B.mesure(d, np.where(d["loin"], rl, rp))
            r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
            ok, det = B.finaliste(r, ref)
            ESSAIS.append(dict(famille="essai 9", nom=f"{desc} t={t}", finaliste=ok, detail=det, **r))
            print(("F " if ok else "  ") + B.ligne(f"t={t}", r), flush=True)
print("essais :", len(ESSAIS))
(B.SORTIE / f"essais_v12_{'_'.join(sys.argv[1:])}.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
