#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : finaliste v12 à seuil réglé (règle B) : recalcul, plateau, « un jeu dehors », bootstrap.

Chaîne : aiguilleur (loin -> v2, alerte si P_v2(saine) <= 0,70) ; proche -> candidat, alerte si P(saine) < t
(seuil_alerte 0,725 n'agit pas tant que t > 0,275). Validation = moyenne des plis disponibles ; pays lus par le pli qui
ne les a pas appris. Grille t de 0,50 à 0,85 par 0,01. Un jeu dehors : t choisi sur les 3 autres (coût moyen le plus bas
sous les contraintes « finaliste » applicables), lu sur le jeu dehors. Réglage seulement.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_v12_seuil.py a7 0.69
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import controle_nuit_m_recalcul as R  # noqa: E402

REF = {"validation": (9, 2001, 57, 1000), "tdtu": (83, 1059, 177, 577), "psfd": (149, 738, 0, 0), "ethiopie": (179, 1134, 43, 155)}


def cout(msa, nm, sea, ns):
    return 100 * (3 * msa / nm + (sea / ns if ns else 0.0))


def main(c, t0):
    K = RACINE / f"out/maladies/nuit_1112/kaggle/{c}"
    jeux = R.charger()
    ps = {}
    for j in R.JEUX:
        d = jeux[j]
        fs = sorted(K.glob(f"predictions_{c}_validation_pli_*.csv")) if j == "validation" else [K / f"predictions_{c}_{j}.csv"]
        ps[j] = [pd.read_csv(f).set_index("chemin").loc[list(d["chemin"])].p_saine.to_numpy() for f in fs]
    grille = [round(x, 2) for x in np.arange(0.50, 0.855, 0.01)]

    def comptes(t, j, idx=None):
        d = jeux[j]
        m = d["malade"] if idx is None else d["malade"][idx]
        v2a = (d["Pv2"][:, 0] <= 0.70)
        out = []
        for p in ps[j]:
            a = np.where(d["loin"], v2a, p < t)
            a = a if idx is None else a[idx]
            out.append(((m & ~a).sum(), m.sum(), (~m & a).sum(), (~m).sum()))
        o = np.mean(np.array(out, float), 0)
        return o, max(x[0] for x in out), max(x[2] for x in out)

    ref_c = {j: cout(*REF[j]) for j in R.JEUX}

    def evalue(t, quels):
        r = {j: comptes(t, j) for j in quels}
        cm = np.mean([cout(*r[j][0]) for j in quels])
        ok = cm <= np.mean([ref_c[j] for j in quels]) - 1.0
        if "validation" in quels:
            v = r["validation"][0]
            ok &= v[0] <= 14 and v[2] <= 77
        for j in quels:
            if j != "validation":
                ok &= 100 * (r[j][0][0] / r[j][0][1] - REF[j][0] / REF[j][1]) <= 2.0
        return cm, bool(ok), r

    lignes = []
    cm0, ok0, r0 = evalue(t0, R.JEUX)
    lignes.append(f"{c} au seuil {t0} : coût moyen {cm0:.3f} ; finaliste {ok0} ; " + " ; ".join(
        f"{j} {r0[j][0][0]:.1f}/{r0[j][0][2]:.1f} (pire pli {r0[j][1]}/{r0[j][2]})" for j in R.JEUX))
    pl = [(t, *evalue(t, R.JEUX)[:2]) for t in grille]
    lignes.append("plateau (t : coût, F) : " + " ".join(f"{t:.2f}:{cm:.2f}{'F' if ok else '-'}" for t, cm, ok in pl))
    # un jeu dehors
    gd, gp = [], []
    for h in R.JEUX:
        q = [j for j in R.JEUX if j != h]
        cand = [(evalue(t, q)[0], t) for t in grille if evalue(t, q)[1]]
        if not cand:
            lignes.append(f"{h} dehors : aucun seuil finaliste sur les 3 autres")
            continue
        _, th = min(cand)
        ch = cout(*comptes(th, h)[0])
        c0 = cout(*comptes(t0, h)[0])
        gd.append(ref_c[h] - ch); gp.append(ref_c[h] - c0)
        lignes.append(f"{h} dehors : t choisi {th:.2f} ; coût dehors {ch:.2f} (au seuil officiel {c0:.2f} ; v10b {ref_c[h]:.2f})")
    if gd:
        lignes.append(f"gain moyen hors échantillon {np.mean(gd):.2f} contre {np.mean(gp):.2f} au seuil officiel (optimisme du seuil {np.mean(gp) - np.mean(gd):.2f})")
    # bootstrap apparié au seuil officiel
    rng = np.random.default_rng(2026)
    refa = {j: R.alertes(jeux[j], R.ps_proche(jeux[j], "384", None), 0.5186470150947571, False) for j in R.JEUX}
    diffs = []
    for _ in range(2000):
        tot = 0.0
        for j in R.JEUX:
            m = jeux[j]["malade"]
            i = rng.integers(0, len(m), len(m))
            o = comptes(t0, j, i)[0]
            mi, ai = m[i], refa[j][i]
            tot += cout(*o) - cout((mi & ~ai).sum(), mi.sum(), (~mi & ai).sum(), (~mi).sum())
        diffs.append(tot / 4)
    diffs = np.array(diffs)
    lignes.append(f"bootstrap : écart de coût contre v10b {diffs.mean():+.2f} (é.-t. {diffs.std():.2f}, IC 95 % "
                  f"[{np.quantile(diffs, 0.025):+.2f} ; {np.quantile(diffs, 0.975):+.2f}]) ; part des tirages sous 1 point de gain {np.mean(diffs > -1):.2f}")
    lignes.append("coût par jeu au seuil officiel contre v10b : " + ", ".join(f"{j} {cout(*r0[j][0]):.2f} / {ref_c[j]:.2f}" for j in R.JEUX))
    (R.OUT / f"m_{c}_seuil.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
