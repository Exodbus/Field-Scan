#!/usr/bin/env python3
"""Lecteur kNN dans l'encodeur affiné (soupes s4) : essais KD1 à KD3 de M-kaggle (15/11).
Règles écrites avant calcul : docs/journee_2026-11-15/journal_m_kaggle.md (14 h 15). Règle « finaliste » : plan du 13/11, 4.3.
Traits : sorties du carnet Kaggle m15-traits (out/maladies/jour_1511/kaggle/lot_traits/). Banc : scripts/m14_banc.py (sans
modification). Aucun juge, aucun test.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15_knn.py
"""
import os

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[v] = "2"   # 2 fils au plus
import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m14_banc as M  # noqa: E402

SORTIE = RACINE / "out/maladies/jour_1511/kaggle"
T = SORTIE / "lot_traits"
KAG = RACINE / "out/maladies/nuit_1311/kaggle"
PLIS = ["tdtu", "ethiopie"]
T_F1B, T_F1, T_D3B = 10.2, 27.0, 4.1
T_KNN = 0.085 * T_D3B   # 2 lectures 224 px, 1 vue (estimation écrite à 14 h 15)


def auroc(score, y):
    y = np.asarray(y, bool)
    r = rankdata(score)
    n1, n0 = y.sum(), (~y).sum()
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def p_knn(Q, Mm, mal, k, lot=1000):
    """Vote équilibré des k plus proches voisins (cosinus ; traits déjà normalisés)."""
    w = np.where(mal, 1.0 / mal.sum(), 1.0 / (~mal).sum())
    out = np.empty(len(Q))
    for i in range(0, len(Q), lot):
        s = Q[i:i + lot] @ Mm.T
        idx = np.argpartition(-s, k, axis=1)[:, :k]
        ww = w[idx]
        out[i:i + lot] = (ww * mal[idx]).sum(1) / ww.sum(1)
    return out


def main():
    meta = pd.read_csv(T / "appr_meta.csv")
    print("pays de la mémoire :", sorted(meta.pays.unique()))
    assert {"tdtu", "ethiopie", "psfd"} <= set(meta.pays), "noms de pays inattendus"
    mal = meta.y.to_numpy() != 0
    F = {x: np.load(T / f"traits_s4_sans_{x}.npz") for x in PLIS}
    jeux = M.charger()
    M.jeux_global = jeux
    M.lire_eleve(jeux, KAG / "pour_banc/d3b", "d3b")
    ref = M.evaluer(jeux, M.f1)
    print(M.ligne("F1 (contrôle, attendu 33,94)", ref))
    assert abs(ref["cout_reglage"] - 33.94) < 0.005
    # P_kNN par jeu et par k (dans l'ordre du banc)
    PK = {}
    for k in (5, 10, 20):
        for j, d in jeux.items():
            jj = "roamer_dev_loin" if j == "roamer" else j
            ch = pd.read_csv(T / f"chemins_{jj}.csv").chemin.astype(str).tolist()
            pos = {c: i for i, c in enumerate(ch)}
            ordre = np.array([pos[str(c)] for c in d["chemin"]])
            plis = [j] if j in PLIS else PLIS
            ps = []
            for x in plis:
                garde = ~meta.pays.isin([x, "psfd"]).to_numpy()
                Q = F[x][f"mes_{jj}"].astype("float32")[ordre]
                ps.append(p_knn(Q, F[x]["appr"].astype("float32")[garde], mal[garde], k))
            PK[(k, j)] = np.mean(ps, 0)
    au = {k: {j: auroc(PK[(k, j)], jeux[j]["malade"]) for j in jeux} for k in (5, 10, 20)}
    moy = {k: (au[k]["validation"] + au[k]["tdtu"]) / 2 for k in au}
    best = max(moy.values())
    k = max(kk for kk in moy if moy[kk] >= best - 0.002)
    print("AUROC :", {kk: {j: round(v, 3) for j, v in a.items()} for kk, a in au.items()}, "→ k =", k)
    for j, d in jeux.items():
        d["PK"] = PK[(k, j)]
    ALERTE = M.ALERTE

    def kd1(s):
        def regle(d, G2):
            a = M.f1(d, G2)
            return np.where(~d["loin"] & ~np.isin(a, ALERTE) & (d["PK"] >= s), "a_verifier", a).astype(object)
        return regle

    def kd2(q):
        def regle(d, G2):
            a = M.f1(d, G2)
            return np.where(d["loin"] & (a == "a_verifier") & (d["PK"] <= q), "saine", a).astype(object)
        return regle

    res = {"k": k, "auroc": au, "F1": M.resume("F1", ref, ref)}
    R = {}
    for nom, f in [(f"KD1 s={s}", kd1(s)) for s in (0.50, 0.70, 0.90)] + [(f"KD2 q={q}", kd2(q)) for q in (0.05, 0.10, 0.20)]:
        R[nom] = (M.evaluer(jeux, f), f)
    s1 = min((n for n in R if n.startswith("KD1")), key=lambda n: R[n][0]["cout_reglage"])
    s2 = min((n for n in R if n.startswith("KD2")), key=lambda n: R[n][0]["cout_reglage"])
    f1_, f2_ = R[s1][1], R[s2][1]

    def kd3(d, G2):
        a, b = f1_(d, G2), f2_(d, G2)
        return np.where(a == "a_verifier", np.where(M.f1(d, G2) == "a_verifier", b, a), b).astype(object)
    R[f"KD3 ({s1} + {s2})"] = (M.evaluer(jeux, kd3), kd3)
    t = T_F1B + T_KNN
    for nom, (r, _) in R.items():
        s = M.resume(nom, r, ref)
        s["temps"] = dict(s_par_photo=round(t, 2), rapport_F1_bornes=round(t / T_F1B, 2), rapport_F1_installe=round(t / T_F1, 2),
                          passe_temps=t <= 1.2 * T_F1B, note="majorant composé : P_kNN lue sur toutes les photos")
        s["finaliste"] = bool(s["finaliste_sans_temps"] and s["temps"]["passe_temps"])
        res[nom] = s
        print(M.ligne(nom, r))
        print("   ", s["finaliste_sans_temps"], s["conditions"], {kk: s[kk] for kk in
              ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1", "inconnues")})
    (SORTIE / "bilan_knn.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("écrit :", SORTIE / "bilan_knn.json")


if __name__ == "__main__":
    main()
