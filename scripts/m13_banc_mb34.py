#!/usr/bin/env python3
"""MB1-B (grille fine), MB3 (mélanges avec v12a13 / v12a14) et MB4 (malades peu tachées), grilles écrites dans
docs/nuit_2026-11-13/journal_m_banc.md (23 h 52) avant le calcul.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_mb34.py [mb1fin] [mb3] [mb4] [--roamer]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m13_banc_commun as C  # noqa: E402
import m13_banc_regles as R  # noqa: E402
from fieldscan.modules import maladies  # noqa: E402

AL = list(C.ALERTE)
KAG = RACINE / "out/maladies/nuit_1112/kaggle"
COLS = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]


def charger_v12(nom, jeux):
    """Probabilités de la v12 sur les 4 anciens jeux (pli qui n'a pas appris le pays ; validation = moyenne des plis) ;
    AgroVisionBD et roamer : modèle final, si calculé (out/maladies/nuit_1311/banc/v12_<nom>_<jeu>.npy)."""
    out = {}
    for j in ("validation", "tdtu", "psfd", "ethiopie"):
        if j == "validation":
            f = sorted((KAG / nom).glob(f"predictions_{nom}_validation*.csv"))
            P, ch = np.mean([pd.read_csv(x)[COLS].to_numpy("float64") for x in f], 0), pd.read_csv(f[0]).chemin
        else:
            x = pd.read_csv(KAG / nom / f"predictions_{nom}_{j}.csv")
            P, ch = x[COLS].to_numpy("float64"), x.chemin
        assert list(ch) == list(jeux[j]["chemin"]), (nom, j)
        out[j] = P
    for j in ("agrovision", "roamer"):
        f = C.SORTIE / f"v12_{nom}_{j}.npy"
        if f.exists():
            out[j] = np.load(f)
    return out


def geo_v12(P10l, Pso, Pv2, P12, w):
    w = np.asarray(w, float) / sum(w)
    lg = sum(wi * np.log(np.clip(P[:, :3], 1e-9, 1)) for wi, P in zip(w, (P10l, Pso, Pv2, P12)))
    q = np.hstack([np.exp(lg), (w[0] * P10l[:, 3] + w[3] * P12[:, 3])[:, None]])
    return q / q.sum(1, keepdims=True)


def mb3(V, w, t):
    def r(d, G2):
        P = geo_v12(maladies.lecture_morceaux(d["P10"], G2), d["Pso"], d["Pv2"], V[d["_nom"]], w)
        return R.f1_like(d, R.proche(d, G2, t, P))
    return r


def mb4(mode, u, h):
    def r(d, G2):
        P = R.melange(d, G2)
        x = R.f1_like(d, R.proche(d, G2, 0.70, P)).copy()
        if mode == "u":
            hes = P[:, 0] < u
        else:
            hes = np.minimum(np.minimum(d["P10"][:, 0], d["Pso"][:, 0]), d["Pv2"][:, 0]) < 0.5
        pmax = (1 - G2[:, :, 0]).max(1)
        x[~np.isin(x, AL) & hes & (pmax >= h)] = "malade_non_identifiee"
        return x
    return r


if __name__ == "__main__":
    AVEC_ROAMER = "--roamer" in sys.argv
    jeux = C.charger(roamer=AVEC_ROAMER)
    for j, d in jeux.items():
        d["_nom"] = j
    NOMS = C.JEUX5 + (["roamer"] if AVEC_ROAMER else [])
    ref = C.evaluer(jeux, C.f1, NOMS)
    print(C.ligne("F1", ref), flush=True)
    GRILLE = []
    if "mb1fin" in sys.argv:
        GRILLE += [("MB1-B", f"loin : proche seul à tL={t}", R.mb1_b_proche(t)) for t in (0.65, 0.675, 0.725, 0.75, 0.80)]
    if "mb4" in sys.argv:
        GRILLE += [("MB4", f"pire morceau >= {h} si P(saine) mélange < {u}", mb4("u", u, h)) for u in (0.80, 0.85, 0.90)
                   for h in (0.5, 0.7, 0.9)]
        GRILLE += [("MB4", f"pire morceau >= {h} si un lecteur < 0,5", mb4("l", None, h)) for h in (0.5, 0.7, 0.9)]
    V12 = {}
    if "mb3" in sys.argv:
        for nom in ("a13", "a14"):
            V12[nom] = charger_v12(nom, jeux)
            for w in ((1, 1, 1, 1), (1, 1, 1, 0.5), (1, 1, 0, 1)):
                GRILLE += [("MB3", f"géo v10b+morceaux, soupe, v2, {nom} poids {w} t={t}", mb3(V12[nom], w, t), nom)
                           for t in (0.66, 0.68, 0.70, 0.72, 0.74, 0.76, 0.78, 0.80)]
    cpt = C.Compteur("_".join(a for a in sys.argv[1:] if not a.startswith("--")) + ("_roamer" if AVEC_ROAMER else ""))
    for fam, nom, regle, *v12 in GRILLE:
        noms = NOMS
        if fam == "MB3":   # v12 absente d'AgroVisionBD / roamer tant qu'elle n'est pas calculée
            noms = [j for j in NOMS if j in V12[v12[0]]]
        r = C.evaluer(jeux, regle, noms)
        if "cout_reglage" not in r:
            r["cout_4"] = float(np.mean([r[j]["cout"] for j in ("validation", "tdtu", "psfd", "ethiopie")]))
            r["cout_reglage"] = float("nan")
            ok, det, inc = False, {"note": f"coût à 4 jeux {r['cout_4']:.2f} (F1 35,96)"}, None
        else:
            ok, det, inc = C.finaliste(r, ref)
        cpt.ajouter(fam, nom, r, ok, det)
        extra = ""
        for j in ("psfd", "ethiopie"):
            d = jeux[j]
            ratees = d["malade"] & ~r[j]["_alerte"]
            extra += f" {j[:4]}:" + ",".join(f"{k}={v}" for k, v in pd.Series(d["vraie"][ratees]).value_counts().items())
        print(("F " if ok else "  ") + C.ligne(f"{fam} {nom}", r) + f" | inc {inc} | {det} |{extra}", flush=True)
    print("essais :", cpt.ecrire())
