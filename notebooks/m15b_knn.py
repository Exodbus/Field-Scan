#!/usr/bin/env python3
"""Lecteur kNN (KD) et tête logistique (KT) sur les traits des soupes s4 : essais de M-kaggle2 (15/11, second tour).
Règles écrites avant calcul : docs/journee_2026-11-15/journal_m_kaggle2.md (16 h 09 ; empreinte dans
out/maladies/jour_1511/kaggle2/empreinte_regles.txt). Règle « finaliste » : plan du 13/11, 4.3.
Traits : sorties du carnet Kaggle m15b-traits (out/maladies/jour_1511/kaggle2/lot_traits/). Banc : scripts/m14_banc.py
(sans modification). Voisins et tête : SEULEMENT dans les autres pays que celui de la requête. Aucun juge, aucun test.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15b_knn.py
"""
import os

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[v] = "2"   # 2 fils au plus
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

torch.set_num_threads(2)
sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m14_banc as M  # noqa: E402

SORTIE = RACINE / "out/maladies/jour_1511/kaggle2"
T = SORTIE / "lot_traits"
KAG = RACINE / "out/maladies/nuit_1311/kaggle"
PLIS = ["tdtu", "ethiopie"]
T_F1B, T_F1, T_D3B = 10.2, 27.0, 4.1
T_KNN = 0.085 * T_D3B   # 2 lectures 224 px, 1 vue (estimation écrite à 14 h 15 par M-kaggle, reprise à 16 h 09)
# Pays de la requête à retirer en plus de la mémoire (règle de 16 h 09)
BANGLADESH = ["mendeley_bd", "mendeley_5nfjzntwd8_bangladesh", "mendeley_6yy9522rdy_bangladesh"]
MEME_PAYS = {"validation": ["tanzanie_2021"], "agrovision": BANGLADESH, "tdtu": [], "ethiopie": [], "psfd": [], "roamer": []}


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


def tete(X, mal):
    """Régression logistique binaire, poids équilibrés, L2 = 1e-4 ||w||², L-BFGS 200 itérations (règle de 16 h 09)."""
    X = torch.from_numpy(X)
    y = torch.from_numpy(mal.astype("float32"))
    pw = torch.where(y > 0, 0.5 / y.sum(), 0.5 / (1 - y).sum())
    w = torch.zeros(X.shape[1], requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([w, b], max_iter=200, line_search_fn="strong_wolfe", tolerance_grad=1e-9, tolerance_change=1e-12)

    def perte():
        opt.zero_grad()
        z = X @ w + b
        p = (pw * torch.nn.functional.binary_cross_entropy_with_logits(z, y, reduction="none")).sum() + 1e-4 * (w * w).sum()
        p.backward()
        return p
    opt.step(perte)
    return w.detach(), b.detach()


def main():
    t0 = time.time()
    meta = pd.read_csv(T / "appr_meta.csv")
    pays = meta.pays.astype(str).to_numpy()
    print("mémoire par pays :", meta.groupby("pays").size().to_dict())
    assert {"tdtu", "ethiopie", "tanzanie_2021", *BANGLADESH} <= set(pays), "noms de pays inattendus"
    assert "psfd" not in set(pays)   # PSFD n est jamais appris (pays_hors du carnet) : absent de la mémoire
    mal = meta.y.to_numpy() != 0
    F = {x: np.load(T / f"traits_s4_sans_{x}.npz") for x in PLIS}
    FA = {x: F[x]["appr"].astype("float32") for x in PLIS}
    jeux = M.charger()
    M.jeux_global = jeux
    M.lire_eleve(jeux, KAG / "pour_banc/d3b", "d3b")
    ref = M.evaluer(jeux, M.f1)
    print(M.ligne("F1 (contrôle, attendu 33,94)", ref))
    assert abs(ref["cout_reglage"] - 33.94) < 0.005
    # requêtes dans l'ordre du banc, et mémoire « autres pays » de chaque (jeu, pli)
    Q, GARDE = {}, {}
    for j, d in jeux.items():
        jj = "roamer_dev_loin" if j == "roamer" else j
        ch = pd.read_csv(T / f"chemins_{jj}.csv").chemin.astype(str).tolist()
        pos = {c: i for i, c in enumerate(ch)}
        ordre = np.array([pos[str(c)] for c in d["chemin"]])
        for x in ([j] if j in PLIS else PLIS):
            Q[(j, x)] = F[x][f"mes_{jj}"].astype("float32")[ordre]
            GARDE[(j, x)] = ~np.isin(pays, [x, "psfd"] + MEME_PAYS[j])
    taille = {f"{j}|{x}": dict(memoire=int(g.sum()), malades=int(mal[g].sum())) for (j, x), g in GARDE.items()}
    print("mémoires :", taille)
    # P_kNN
    PK = {}
    for k in (5, 10, 20):
        for j in jeux:
            ps = [p_knn(Q[(j, x)], FA[x][GARDE[(j, x)]], mal[GARDE[(j, x)]], k) for x in ([j] if j in PLIS else PLIS)]
            PK[(k, j)] = np.mean(ps, 0)
    au = {k: {j: auroc(PK[(k, j)], jeux[j]["malade"]) for j in jeux} for k in (5, 10, 20)}
    moy = {k: (au[k]["validation"] + au[k]["tdtu"]) / 2 for k in au}
    best = max(moy.values())
    k = max(kk for kk in moy if moy[kk] >= best - 0.002)
    print("AUROC kNN :", {kk: {j: round(v, 3) for j, v in a.items()} for kk, a in au.items()}, "→ k =", k, flush=True)
    # P_tête (une tête par mémoire distincte)
    tetes, PT = {}, {}
    for j in jeux:
        ps = []
        for x in ([j] if j in PLIS else PLIS):
            cle = (x, tuple(MEME_PAYS[j]))
            if cle not in tetes:
                g = GARDE[(j, x)]
                tetes[cle] = tete(FA[x][g], mal[g])
            w, b = tetes[cle]
            ps.append(torch.sigmoid(torch.from_numpy(Q[(j, x)]) @ w + b).numpy().astype("float64"))
        PT[j] = np.mean(ps, 0)
    au_t = {j: auroc(PT[j], jeux[j]["malade"]) for j in jeux}
    print("AUROC tête :", {j: round(v, 3) for j, v in au_t.items()}, f"({len(tetes)} têtes)", flush=True)
    for j, d in jeux.items():
        d["PK"] = PK[(k, j)]
        d["PT"] = PT[j]
    ALERTE = M.ALERTE

    def r1(cle, s):
        def regle(d, G2):
            a = M.f1(d, G2)
            return np.where(~d["loin"] & ~np.isin(a, ALERTE) & (d[cle] >= s), "a_verifier", a).astype(object)
        return regle

    def r2(cle, q):
        def regle(d, G2):
            a = M.f1(d, G2)
            return np.where(d["loin"] & (a == "a_verifier") & (d[cle] <= q), "saine", a).astype(object)
        return regle

    res = {"k": k, "auroc_knn": au, "auroc_tete": au_t, "memoires": taille, "F1": M.resume("F1", ref, ref)}
    R = {}
    for fam, cle in (("KD", "PK"), ("KT", "PT")):
        Rf = {}
        for nom, f in ([(f"{fam}1 s={s}", r1(cle, s)) for s in (0.50, 0.70, 0.90)]
                       + [(f"{fam}2 q={q}", r2(cle, q)) for q in (0.05, 0.10, 0.20)]):
            Rf[nom] = (M.evaluer(jeux, f), f)
        s1 = min((n for n in Rf if n.startswith(f"{fam}1")), key=lambda n: Rf[n][0]["cout_reglage"])
        s2 = min((n for n in Rf if n.startswith(f"{fam}2")), key=lambda n: Rf[n][0]["cout_reglage"])

        def r3(d, G2, f1_=Rf[s1][1], f2_=Rf[s2][1]):
            a, b = f1_(d, G2), f2_(d, G2)
            return np.where(M.f1(d, G2) == "a_verifier", b, a).astype(object)
        Rf[f"{fam}3 ({s1} + {s2})"] = (M.evaluer(jeux, r3), r3)
        R.update(Rf)
    t = T_F1B + T_KNN
    for nom, (r, _) in R.items():
        s = M.resume(nom, r, ref)
        s["temps"] = dict(s_par_photo=round(t, 2), rapport_F1_bornes=round(t / T_F1B, 2), rapport_F1_installe=round(t / T_F1, 2),
                          passe_temps=t <= 1.2 * T_F1B, note="estimation composée : traits lus sur toutes les photos")
        s["finaliste"] = bool(s["finaliste_sans_temps"] and s["temps"]["passe_temps"])
        res[nom] = s
        print(M.ligne(nom, r))
        print("   ", s["finaliste"], s["conditions"], {kk: s[kk] for kk in
              ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1", "inconnues")}, flush=True)
    res["essais"] = 3 + len(R)
    res["duree_s"] = round(time.time() - t0, 1)
    (SORTIE / "bilan_knn.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    np.savez(SORTIE / "p_knn_tete.npz", **{f"PK_{j}": jeux[j]["PK"] for j in jeux}, **{f"PT_{j}": jeux[j]["PT"] for j in jeux})
    print("écrit :", SORTIE / "bilan_knn.json", "essais :", res["essais"])


if __name__ == "__main__":
    main()
