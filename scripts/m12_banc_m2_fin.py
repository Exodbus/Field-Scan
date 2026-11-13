#!/usr/bin/env python3
"""Essais 5 et 6, suite : grille fine (0,60 à 0,78 par 0,02) sur les jeux de réglage entiers, base « à trois », pour les
lectures qui gagnaient sur la grille grossière : 2 x 2 (max, 2 plus fortes, ou bruité ; moyenne avec l'entière) et
moyenne 384 + 512 px. Règle « finaliste » complète du plan (4.4). Facultatif : 3 x 3 si g3_<jeu>.npz est présent."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from m12_banc_trois import geo3  # noqa: E402

K = B.SORTIE / "kaggle_morceaux"
jeux = B.charger_reglage()
ref = B.reference(jeux)
g3_present = all((K / f"g3_{j}.npz").exists() for j in B.REGLAGE)
for j, d in jeux.items():
    d["G2"] = np.load(K / f"morceaux_{j}.npz")["g2"].astype("float64")
    d["P512"] = pd.read_csv(K / f"p512_{j}.csv")[["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]].to_numpy("float64")
    if g3_present:
        d["G3"] = np.load(K / f"g3_{j}.npz")["g3"].astype("float64")


def avec_saine(P, ps):
    reste = np.clip(1 - P[:, 0], 1e-9, None)
    Q = P * ((1 - ps) / reste)[:, None]
    Q[:, 0] = ps
    return Q


def morceaux(cle, reunir):
    def f(d):
        m = 1 - d[cle][:, :, 0]
        a = {"max": m.max(1), "2 plus fortes": np.sort(m, 1)[:, -2:].mean(1), "ou bruité": 1 - np.prod(1 - m, 1)}[reunir]
        return avec_saine(d["P10"], 1 - ((1 - d["P10"][:, 0]) + a) / 2)
    return f


LECTURES = {"entière 384": lambda d: d["P10"], "moyenne 384 + 512": lambda d: (d["P10"] + d["P512"]) / 2}
for g in (["G2", "G3"] if g3_present else ["G2"]):
    for r in ("max", "2 plus fortes", "ou bruité"):
        LECTURES[f"{g.lower()} {r} / moyenne avec entière"] = morceaux(g, r)

ESSAIS = []
for nom, f in LECTURES.items():
    print(f"\n--- à trois (1,1,1), loin « v2 ou proche », v10b lue par : {nom} ---")
    for t in [round(x, 2) for x in np.arange(0.60, 0.781, 0.02)]:
        r = {}
        for j, d in jeux.items():
            rp = B.decider_v10b(geo3({**d, "P10": f(d)}, 1, 1, 1), seuil=t)
            rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
            r[j] = B.mesure(d, np.where(d["loin"], rl, rp))
        r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
        ok, det = B.finaliste(r, ref)
        ESSAIS.append(dict(famille="essais 5-6 fin", nom=f"{nom} t={t}", finaliste=ok, detail=det, **r))
        print(("F " if ok else "  ") + B.ligne(f"t={t}", r))
print("essais :", len(ESSAIS))
(B.SORTIE / f"essais_m2_fin{'_g3' if g3_present else ''}.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
