#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : décision (alerte oui / non) de chaque finaliste maladies sur N'IMPORTE QUEL jeu de
probabilités, par un code indépendant de celui des agents (deuxième avis pour l'agent Juge).

Entrées (même ordre de photos partout ; .npy tel quel, ou .csv aux colonnes p_saine, p_black_sigatoka, p_fusarium[, p_autre]
ou p_loin) :
  --v10b (n, 4)  --soupe (n, 3)  --v2 (n, 3)  --loin (n,)       [F1, F2, F3, référence]
  --v10b_512 (n, 4)            [F2]       --v10b_g2 (n, 4, 4)  [F1 : 4 morceaux 2 x 2]
  --v12a4 / --v12a7 / --v12a13 / --v12a14 (n, 4)  [v12 seuls, MODÈLE FINAL ; v12a14 sert aussi au mélange C_quatre_v12a14]
  --verite : CSV avec une colonne « malade » (0/1)
Règles (démontrées sur decider_convnext) : photo proche en alerte si P(saine) du lecteur < t ; photo loin (p_loin >= 0,5)
en alerte si P_v2(saine) <= 0,70, ou (F1, F2, F3) si le lecteur proche alerte aussi.
Sortie : CSV, une colonne 0/1 par candidat ; si --verite : malades sans alerte, saines en alerte, coût.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_appliquer.py --v10b ... --sortie alertes.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

T_V10B = 0.5186470150947571


def lire(f, n):
    f = Path(f)
    if f.suffix == ".npy":
        return np.load(f).astype("f8")
    d = pd.read_csv(f)
    return d["p_loin"].to_numpy("f8") if n == 0 else d[["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"][:n]].to_numpy("f8")


def ps_melange(P10, Pso, Pv2):
    lg = (np.log(np.clip(P10[:, :3], 1e-9, 1)) + np.log(np.clip(Pso, 1e-9, 1)) + np.log(np.clip(Pv2, 1e-9, 1))) / 3
    g = np.exp(lg)
    return g[:, 0] / (g.sum(1) + P10[:, 3] / 3)


def v10b_morceaux(P10, G2):
    pm = ((1 - P10[:, 0]) + np.sort(1 - G2[:, :, 0], 1)[:, -2:].mean(1)) / 2
    Q = P10 * (pm / np.clip(1 - P10[:, 0], 1e-9, None))[:, None]
    Q[:, 0] = 1 - pm
    return Q


def main():
    a = argparse.ArgumentParser()
    for k in ("v10b", "soupe", "v2", "loin", "v10b_512", "v10b_g2", "v12a4", "v12a7", "v12a13", "v12a14", "verite"):
        a.add_argument(f"--{k}")
    a.add_argument("--sortie", required=True)
    x = a.parse_args()
    loin = lire(x.loin, 0) >= 0.5
    Pv2 = lire(x.v2, 3)
    a_v2 = Pv2[:, 0] <= 0.70
    out = {}
    if x.v10b:
        P10 = lire(x.v10b, 4)
        out["reference_v10b"] = np.where(loin, a_v2, P10[:, 0] < T_V10B)
        if x.soupe:
            Pso = lire(x.soupe, 3)
            lect = {"F3_trois": (P10, 0.74)}
            if x.v10b_512:
                lect["F2_trois_384_512"] = ((P10 + lire(x.v10b_512, 4)) / 2, 0.72)
            if x.v10b_g2:
                lect["F1_trois_morceaux2x2"] = (v10b_morceaux(P10, np.load(x.v10b_g2).astype("f8")), 0.70)
            for n, (P, t) in lect.items():
                ap = ps_melange(P, Pso, Pv2) < t
                out[n] = np.where(loin, a_v2 | ap, ap)
    if x.v10b and x.soupe and x.v12a14:
        P10, Pso, P14 = lire(x.v10b, 4), lire(x.soupe, 3), lire(x.v12a14, 4)
        g = np.exp((np.log(np.clip(P10[:, :3], 1e-9, 1)) + np.log(np.clip(Pso, 1e-9, 1)) + np.log(np.clip(Pv2, 1e-9, 1))
                    + np.log(np.clip(P14[:, :3], 1e-9, 1))) / 4)
        ap = g[:, 0] / (g.sum(1) + (P10[:, 3] + P14[:, 3]) / 4) < 0.76
        out["C_quatre_v12a14"] = np.where(loin, a_v2 | ap, ap)
    for n, t in (("v12a4", T_V10B), ("v12a7", 0.69), ("v12a13", T_V10B), ("v12a14", T_V10B)):
        f = getattr(x, n)
        if f:
            out[n] = np.where(loin, a_v2, lire(f, 4)[:, 0] < t)
    df = pd.DataFrame({k: v.astype(int) for k, v in out.items()})
    df.to_csv(x.sortie, index=False)
    if x.verite:
        m = pd.read_csv(x.verite)["malade"].astype(bool).to_numpy()
        for k, al in out.items():
            msa, sea, nm, ns = int((m & ~al).sum()), int((~m & al).sum()), int(m.sum()), int((~m).sum())
            c = 100 * (3 * msa / max(nm, 1) + (sea / ns if ns else 0))
            print(f"{k:24s} malades sans alerte {msa}/{nm} ; saines en alerte {sea}/{ns} ; coût {c:.2f}")
    print("écrit :", x.sortie)


if __name__ == "__main__":
    main()
