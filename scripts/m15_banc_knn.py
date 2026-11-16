#!/usr/bin/env python3
"""Banc de M-banc, journée du 15/11 : lecteur kNN sur les traits déjà extraits, morceaux comptés par seuil,
« à vérifier » -> « saine » pour les photos vues de loin, combinaisons avec MC1-OU-proche.
Règles écrites avant tout calcul : docs/journee_2026-11-15/journal_m_banc.md (14 h 00). Règle « finaliste » : plan du
13/11, section 4.3. Réutilise sans les modifier scripts/m13_banc_commun.py et scripts/m14_banc.py (caches de la nuit).
Aucun juge, aucun test n'est chargé.

    PYTHONIOENCODING=utf-8 OMP_NUM_THREADS=2 .venv/Scripts/python.exe -I -u scripts/m15_banc_knn.py etape1
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import m13_banc_commun as C  # noqa: E402
import m14_banc as M  # noqa: E402

SORTIE = RACINE / "out/maladies/jour_1511/banc"
SORTIE.mkdir(parents=True, exist_ok=True)
JEUX5 = C.JEUX5
TOUS = JEUX5 + ["roamer"]
ALERTE = list(C.ALERTE)
KAG = M.KAG
P2K = M.SORTIE / "kaggle"
GRAINES = {0: (KAG / "lot2p", "d3b"), 1: (P2K / "lot1", "d3g1"), 2: (P2K / "lot2", "d3g2"), 3: (P2K / "lot2", "d3g3")}


# --------------------------------------------------------------------------------------------------------------------
# Lecteur kNN (journal, 14 h 00)
def traits(d):
    return np.sqrt(np.clip(np.concatenate([d["P10"], d["Pso"], d["Pv2"]], 1), 0, 1))


def knn_p(Xq, Xm, ym, k, bloc=1000):
    """P(malade) équilibrée : voisin malade pèse 1/n_malades(mémoire), voisin sain 1/n_saines(mémoire)."""
    wm, ws = 1.0 / max(ym.sum(), 1), 1.0 / max((~ym).sum(), 1)
    nm2 = (Xm ** 2).sum(1)
    out = np.empty(len(Xq))
    for i in range(0, len(Xq), bloc):
        q = Xq[i:i + bloc]
        d2 = (q ** 2).sum(1)[:, None] + nm2[None, :] - 2 * q @ Xm.T
        idx = np.argpartition(d2, k, axis=1)[:, :k]
        lab = ym[idx]
        a, b = lab.sum(1) * wm, (~lab).sum(1) * ws
        out[i:i + bloc] = a / (a + b)
    return out


def calculer_knn(jeux, k):
    X = {j: traits(jeux[j]) for j in TOUS}
    for j in TOUS:
        mem = [x for x in JEUX5 if x != j]   # roamer : les 5 jeux de réglage
        Xm = np.concatenate([X[x] for x in mem])
        ym = np.concatenate([jeux[x]["malade"] for x in mem])
        jeux[j]["PK"] = knn_p(X[j], Xm, ym, k)


def auroc(score, y):
    r = rankdata(score)
    n1, n0 = int(y.sum()), int((~y).sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# --------------------------------------------------------------------------------------------------------------------
# Règles : (d, G2) -> réponses
def f1(d, G2):
    return M.f1(d, G2)


def k_rattrape(s, partout=False):
    def regle(d, G2):
        a = f1(d, G2)
        zone = np.ones(len(a), bool) if partout else ~d["loin"]
        return np.where(zone & ~np.isin(a, ALERTE) & (d["PK"] >= s), "a_verifier", a).astype(object)
    return regle


def k_saine(q, partout=False, base=None):
    def regle(d, G2):
        a = (base or f1)(d, G2)
        zone = np.ones(len(a), bool) if partout else d["loin"]
        return np.where(zone & (a == "a_verifier") & (d["PK"] <= q), "saine", a).astype(object)
    return regle


def n_morceaux(m, s):
    def regle(d, G2):
        a = f1(d, G2)
        n = ((1 - G2[:, :, 0]) >= s).sum(1)
        return np.where(~d["loin"] & ~np.isin(a, ALERTE) & (n >= m), "a_verifier", a).astype(object)
    return regle


def compose(*regles_sur_base):
    """C1 : K1 puis K3 appliqués à la suite (K3 agit sur les photos « loin », K1 sur les « proches »)."""
    def regle(d, G2):
        a = f1(d, G2)
        for f in regles_sur_base:
            a = f(d, a)
        return a
    return regle


def mc1_filtre(d, G2):
    """C3 : MC1-OU-proche, mais l'alerte apportée par l'élève n'est gardée que si P_kNN >= 0,50."""
    a, b = f1(d, G2), M.chaine_eleve(d)
    ajout = ~d["loin"] & ~np.isin(a, ALERTE) & np.isin(b, ALERTE) & (d["PK"] >= 0.50)
    return np.where(ajout, b, a).astype(object)


# --------------------------------------------------------------------------------------------------------------------
def resume(nom, r, ref):
    s = M.resume(nom, r, ref)
    s["inconnues_agrovision"] = r["agrovision"].get("inconnues", 0)
    return s


def afficher(nom, r, ref):
    s = resume(nom, r, ref)
    print(M.ligne(nom, r))
    print("   passe(sans temps):", s["finaliste_sans_temps"], s["conditions"],
          {k: s[k] for k in ("alertes_differentes", "malades_perdues_vs_F1", "malades_rattrapees_vs_F1", "inconnues")},
          flush=True)
    return s


def preparer():
    jeux = M.charger()
    M.jeux_global = jeux
    M.lire_eleve(jeux, KAG / "pour_banc/d3b", "d3b")
    ref = M.evaluer(jeux, f1)
    print(M.ligne("F1 (référence)", ref))
    assert round(ref["cout_reglage"], 2) == 33.94 and ref["msa_total5"] == 243 and ref["roamer"]["msa"] == 227, "F1 ≠ 33,94"
    rmc = M.evaluer(jeux, M.mc1_ou_proche)
    print(M.ligne("MC1-OU-proche (d3b, référence)", rmc))
    assert round(rmc["cout_reglage"], 2) == 32.83
    return jeux, ref, rmc


def etape1():
    jeux, ref, rmc = preparer()
    res = {"F1": resume("F1", ref, ref), "MC1-OU-proche": resume("MC1-OU-proche", rmc, ref), "essais": []}
    # choix de k sur validation + TDTU (3 essais de mesure)
    aucs = {}
    for k in (5, 10, 20):
        calculer_knn(jeux, k)
        aucs[k] = {j: auroc(jeux[j]["PK"], jeux[j]["malade"]) for j in ("validation", "tdtu")}
        aucs[k]["moy"] = float(np.mean([aucs[k]["validation"], aucs[k]["tdtu"]]))
        print("k =", k, aucs[k], flush=True)
    m = max(a["moy"] for a in aucs.values())
    k = max(kk for kk, a in aucs.items() if a["moy"] >= m - 0.002)
    res["auroc_k"], res["k"] = {str(kk): v for kk, v in aucs.items()}, k
    print("k choisi :", k)
    t0 = time.perf_counter()
    calculer_knn(jeux, k)
    dt = time.perf_counter() - t0
    n = sum(len(jeux[j]["chemin"]) for j in TOUS)
    res["temps_knn_s_par_photo"] = dt / n
    # AUROC sur tous les jeux (information, après le choix de k)
    res["auroc_tous"] = {j: auroc(jeux[j]["PK"], jeux[j]["malade"]) for j in TOUS if j != "psfd"}
    print("AUROC kNN (k choisi) :", res["auroc_tous"], "| temps kNN par photo :", f"{dt / n * 1e3:.3f} ms")
    np.savez(SORTIE / f"pk_k{k}.npz", **{j: jeux[j]["PK"] for j in TOUS})
    regles = {}
    for s in (0.80, 0.90, 0.95):
        regles[f"K1 rattrape proches s={s}"] = ("A", k_rattrape(s))
    for s in (0.90, 0.95):
        regles[f"K2 rattrape partout s={s}"] = ("A", k_rattrape(s, True))
    for q in (0.10, 0.20, 0.30):
        regles[f"K3 a_verifier->saine loin q={q}"] = ("A", k_saine(q))
    for q in (0.05, 0.10):
        regles[f"K4 a_verifier->saine partout q={q}"] = ("A", k_saine(q, True))
    for mm in (3, 4):
        for s in (0.60, 0.70, 0.80, 0.90):
            regles[f"N m={mm} s={s}"] = ("A", n_morceaux(mm, s))
    R = {}
    for nom, (fam, f) in regles.items():
        R[nom] = M.evaluer(jeux, f)
        s_ = afficher(nom, R[nom], ref)
        s_["famille"] = fam
        res["essais"].append(s_)
    for piste, pref in (("K1", "K1"), ("K2", "K2"), ("K3", "K3"), ("K4", "K4"), ("N", "N "), ("tous", "")):
        cands = {n_: R[n_] for n_ in R if n_.startswith(pref)}
        ch = M.choisir(cands, ref)
        cc, choix = M.croise(cands, ref)
        res[f"choix_{piste}"] = dict(choisi=ch, cout_croise=cc, choix_par_jeu_tenu=choix,
                                     plus_bas=min(cands, key=lambda x: cands[x]["cout_reglage"]))
        print(f"choix {piste} :", res[f"choix_{piste}"])
    (SORTIE / "bilan_etape1.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("essais :", len(res["essais"]) + 3)


def mc1_plus_saine(q):
    """C2 : MC1-OU-proche, puis K3 (« à vérifier » -> « saine » sur les photos « loin » si P_kNN <= q)."""
    return k_saine(q, base=M.mc1_ou_proche)


def mc1_plus_k5(s):
    """C4 : union des rattrapages de MC1-OU-proche (élève) et de K5 (P_kNN >= s) sur les photos proches."""
    def regle(d, G2):
        a = M.mc1_ou_proche(d, G2)
        return np.where(~d["loin"] & ~np.isin(a, ALERTE) & (d["PK"] >= s), "a_verifier", a).astype(object)
    return regle


def etape2():
    jeux, ref, rmc = preparer()
    z = np.load(SORTIE / "pk_k20.npz")
    for j in TOUS:
        jeux[j]["PK"] = z[j]
    res = {"essais": []}
    R = {}

    def essai(nom, fam, f):
        R[nom] = M.evaluer(jeux, f)
        s_ = afficher(nom, R[nom], ref)
        s_["famille"] = fam
        res["essais"].append(s_)
        return s_

    for s in (0.30, 0.40, 0.50, 0.60, 0.70):
        essai(f"K5 rattrape proches s={s}", "A", k_rattrape(s))
    k5 = {n_: R[n_] for n_ in R if n_.startswith("K5")}
    best = min(k5, key=lambda x: k5[x]["cout_reglage"])
    s_best = float(best.split("=")[1])
    rat_best = [e for e in res["essais"] if e["nom"] == best][0]["malades_rattrapees_vs_F1"]
    print("K5 de plus bas coût :", best, "| rattrapées :", rat_best)
    cc, choix = M.croise(k5, ref)
    res["choix_K5"] = dict(choisi=M.choisir(k5, ref), cout_croise=cc, plus_bas=best)
    # graines
    for g, src in GRAINES.items():
        M.lire_kaggle(jeux, [src])
        if g == 0:
            r0 = M.evaluer(jeux, M.mc1_ou_proche)
            assert round(r0["cout_reglage"], 2) == 32.83, "d3b relu depuis les plis ≠ pour_banc"
            c2 = essai("C2 MC1-OU-proche + K3 q=0.1 (graine 0)", "C", mc1_plus_saine(0.10))
        elif c2["finaliste_sans_temps"]:
            essai(f"C2 MC1-OU-proche + K3 q=0.1 (graine {g})", "C", mc1_plus_saine(0.10))
        essai(f"C3 MC1-OU-proche filtré kNN (graine {g})", "C", mc1_filtre)
        if rat_best > 0:
            essai(f"C4 MC1-OU-proche + K5 s={s_best} (graine {g})", "C", mc1_plus_k5(s_best))
        rg = M.evaluer(jeux, M.mc1_ou_proche)   # référence par graine (déjà mesurée par M-piste2, pas un essai)
        res[f"MC1-OU-proche graine {g}"] = resume(f"MC1-OU-proche graine {g}", rg, ref)
        print(M.ligne(f"[réf.] MC1-OU-proche graine {g}", rg))
    (SORTIE / "bilan_etape2.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("essais étape 2 :", len(res["essais"]))


if __name__ == "__main__":
    {"etape1": etape1, "etape2": etape2}[sys.argv[1]]()
