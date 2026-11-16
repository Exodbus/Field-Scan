#!/usr/bin/env python3
"""Mesure de réglage des candidats de M-entraîneur (nuit du 13/11) contre F1, règle 4.3 du plan du 13/11.

Jeux : validation Tanzanie, TDTU, PSFD, Éthiopie, AgroVisionBD (coût de réglage = moyenne des 5) et roamer_dev_loin_feuilles
(contrôle : malades sans alerte <= F1 + 2). Aucun juge.
F1 est recalculé ici sur les mêmes photos, avec le même code (scripts/m12_banc_finalistes.py, F1_trois_morceaux2x2) :
  - réglage (4 jeux) : caches de la nuit du 12/11 (out/maladies/v10b, cinq_classes, dinov2_ft ; morceaux 2 x 2 de
    out/maladies/nuit_1112/banc/kaggle_morceaux) ;
  - AgroVisionBD : réponses déjà calculées (out/controle_nuit_1112/juge_m/vierge/reponses_F1_trois_morceaux2x2.csv,
    morceaux lus là où la décision en dépend) ;
  - roamer_dev_loin : maître calculé par le carnet m13 (maitre_roamer_dev_loin.npz) + aiguilleur local.
Candidat (élève) : chaîne = aiguilleur ; photo « loin » : v2 si elle alerte, sinon l'élève ; photo « proche » : l'élève ;
décision decider_convnext aux seuils de la v10b sauf la confiance (0,70 par défaut, celle de F1).
Plis : TDTU et Éthiopie lus par le pli qui ne les a pas appris ; validation, PSFD, AgroVisionBD, roamer lus par chaque pli :
comptes = moyenne des plis (pire pli gardé).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_mesurer.py <dossier des CSV> <candidat> [...] [--seuil 0.70]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m12_banc_commun as B  # noqa: E402
import m12_banc_finalistes as MF  # noqa: E402

KAG = RACINE / "out/maladies/nuit_1311/kaggle"
REGLAGE5 = ["validation", "tdtu", "psfd", "ethiopie", "agrovision"]
TOUS = REGLAGE5 + ["roamer_dev_loin"]
COLS = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
VIERGE = RACINE / "out/controle_nuit_1112/juge_m/vierge"


def _jeux():
    """{jeu: dict(chemin, malade, loin, r_loin, f1)} : vérité, branche loin et réponse de F1 par photo."""
    J = B.charger_reglage()
    out = {}
    for j in B.REGLAGE:
        d = J[j]
        g2 = np.load(RACINE / f"out/maladies/nuit_1112/banc/kaggle_morceaux/morceaux_{j}.npz")["g2"].astype("float64")
        f1 = MF.repondre(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], MF.CANDIDATS["F1_trois_morceaux2x2"], G2=g2)
        out[j] = dict(chemin=list(d["chemin"]), malade=d["malade"], loin=d["loin"], Pv2=d["Pv2"], f1=f1)
    li = pd.read_csv(RACINE / "data/raw/nuit_1112/figshare_agrovisionbd_bangladesh/liste.csv")
    li = li[li.retenue].reset_index(drop=True)
    rf = pd.read_csv(VIERGE / "reponses_F1_trois_morceaux2x2.csv")
    assert list(rf.chemin) == list(li.chemin)
    pl = np.load(VIERGE / "p_loin.npy")
    out["agrovision"] = dict(chemin=list(li.chemin), malade=(li.classe != "saine").to_numpy(), loin=pl >= 0.5,
                             Pv2=np.load(VIERGE / "p_v2.npy").astype("float64"), f1=rf.reponse.to_numpy(dtype=object))
    m = KAG / "maitre" / "maitre_roamer_dev_loin.npz"
    if m.exists() and (KAG / "p_loin_roamer_dev_loin.csv").exists():
        pr = pd.read_csv(KAG / "p_loin_roamer_dev_loin.csv")
        z = np.load(m, allow_pickle=True)
        assert list(z["chemin"]) == list(pr.chemin)
        pl = pr.p_loin.to_numpy()
        f1 = MF.repondre(z["P10"].astype("float64"), z["Pso"].astype("float64"), z["Pv2"].astype("float64"), pl,
                         MF.CANDIDATS["F1_trois_morceaux2x2"], G2=z["G2"].astype("float64"))
        out["roamer_dev_loin"] = dict(chemin=list(pr.chemin), malade=(pr.etat == "malade").to_numpy(), loin=pl >= 0.5,
                                      Pv2=z["Pv2"].astype("float64"), f1=f1)
    for d in out.values():
        d["r_loin"] = maladies.decider_convnext(d["Pv2"], B.M_V2)[0]
    return out


JEUX = _jeux()


def compter(j, rep):
    d = JEUX[j]
    al = np.isin(np.asarray(rep, dtype=object), list(B.ALERTE))
    m = d["malade"]
    return dict(msa=int((m & ~al).sum()), nm=int(m.sum()), sea=int((~m & al).sum()), ns=int((~m).sum()),
                sea_averif=int((~m & (np.asarray(rep) == "a_verifier")).sum()))


def cout(c):
    return 100 * (3 * c["msa"] / c["nm"] + (c["sea"] / c["ns"] if c["ns"] else 0.0))


def reponse_eleve(j, P, seuil):
    d = JEUX[j]
    rp = maladies.decider_convnext(P, {**B.M_V10B, "seuil": seuil})[0]
    rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
    return np.where(d["loin"], rl, rp)


def reference_f1():
    r = {j: compter(j, JEUX[j]["f1"]) for j in JEUX}
    for c in r.values():
        c["cout"] = cout(c)
    r["cout_reglage"] = float(np.mean([r[j]["cout"] for j in REGLAGE5]))
    r["cout_reglage_4"] = float(np.mean([r[j]["cout"] for j in B.REGLAGE]))
    return r


def lire(f, j):
    df = pd.read_csv(f).set_index("chemin").loc[JEUX[j]["chemin"]]
    return df[COLS].to_numpy("float64")


def charger(dossier, nom):
    """{jeu: [P par pli]} ; « final » accepté (un seul réseau)."""
    d = Path(dossier)
    P = {}
    for j in TOUS:
        if j not in JEUX:
            continue
        if (d / f"predictions_{nom}_{j}.csv").exists():
            P[j] = [lire(d / f"predictions_{nom}_{j}.csv", j)]
        else:
            fs = sorted(d.glob(f"predictions_{nom}_{j}_pli_*.csv")) + sorted(d.glob(f"predictions_{nom}_final_{j}.csv"))
            if fs:
                P[j] = [lire(f, j) for f in fs]
    return P


def bilan(P, ref, seuil=0.70):
    r = {}
    for j, Ps in P.items():
        cs = [compter(j, reponse_eleve(j, Pk, seuil)) for Pk in Ps]
        c = {k: float(np.mean([x[k] for x in cs])) for k in cs[0]}
        c["cout"] = float(np.mean([cout(x) for x in cs]))
        c["pire_pli"] = (max(x["msa"] for x in cs), max(x["sea"] for x in cs))
        r[j] = c
    ok5 = all(j in r for j in REGLAGE5)
    r["cout_reglage"] = float(np.mean([r[j]["cout"] for j in REGLAGE5])) if ok5 else float("nan")
    v = r.get("validation", {})
    conds = dict(
        cout=ok5 and r["cout_reglage"] <= ref["cout_reglage"] - 1.0,
        tanzanie=bool(v) and v["msa"] <= 14 and v["sea"] <= 77,
        pays=all(100 * (r[j]["msa"] / r[j]["nm"] - ref[j]["msa"] / ref[j]["nm"]) <= 2.0 for j in REGLAGE5 if j in r),
        roamer=("roamer_dev_loin" not in ref) or ("roamer_dev_loin" in r and r["roamer_dev_loin"]["msa"] <= ref["roamer_dev_loin"]["msa"] + 2))
    r["conditions_sans_temps"] = conds
    r["finaliste_sans_temps"] = bool(all(conds.values()) and ok5 and "roamer_dev_loin" in r)
    # écart de décisions avec F1 (variante rapide), sur les 5 jeux de réglage, premier pli
    diff, n, msa_plus = 0, 0, 0
    for j in REGLAGE5:
        if j in P:
            rep = reponse_eleve(j, np.mean(P[j], 0), seuil)
            a1, a2 = np.isin(rep, list(B.ALERTE)), np.isin(JEUX[j]["f1"], list(B.ALERTE))
            diff += int((a1 != a2).sum()); n += len(rep); msa_plus += int((JEUX[j]["malade"] & a2 & ~a1).sum())
    r["decisions_differentes_F1"] = (diff, n)
    r["malades_perdues_vs_F1"] = msa_plus
    return r


def ligne(nom, r):
    t = []
    for j in TOUS:
        if j in r:
            c = r[j]
            s = f"{j[:5]} {c['msa']:.4g}/{c['nm']}" + (f" ; {c['sea']:.4g}/{c['ns']} ({c['sea_averif']:.3g} av)" if c["ns"] else "")
            t.append(s + f" c={c['cout']:.2f}")
    return f"{nom:28s} réglage={r['cout_reglage']:.2f} | " + " | ".join(t)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    seuil = float(sys.argv[sys.argv.index("--seuil") + 1]) if "--seuil" in sys.argv else 0.70
    if "--seuil" in sys.argv:
        args.remove(sys.argv[sys.argv.index("--seuil") + 1])
    ref = reference_f1()
    print(ligne("F1 (même code)", ref), f"| coût 4 jeux {ref['cout_reglage_4']:.2f}")
    (KAG / "reference_F1.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")
    for nom in args[1:]:
        r = bilan(charger(args[0], nom), ref, seuil)
        print(ligne(f"{nom} (confiance {seuil:.2f})", r))
        print("   conditions :", r["conditions_sans_temps"], "| décisions ≠ F1 :", r["decisions_differentes_F1"],
              "| malades perdues vs F1 :", r["malades_perdues_vs_F1"])
        (Path(args[0]) / f"bilan_{nom}_{seuil:.2f}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def exporter(dossier, nom, sortie=None):
    """Probabilités moyennes des plis, au format des caches (chemin, jeu, classe_vraie, p_saine, ...), un fichier par jeu,
    pour les mélanges de M-banc (famille C) : out/maladies/nuit_1311/kaggle/pour_banc/<nom>/predictions_<nom>_<jeu>.csv."""
    sortie = Path(sortie or KAG / "pour_banc" / nom)
    sortie.mkdir(parents=True, exist_ok=True)
    for j, Ps in charger(dossier, nom).items():
        P = np.mean(Ps, 0)
        d = pd.DataFrame(dict(chemin=JEUX[j]["chemin"], jeu=j, classe_vraie=np.where(JEUX[j]["malade"], "malade", "saine")))
        for k, c in enumerate(COLS):
            d[c] = P[:, k].round(6)
        d.to_csv(sortie / f"predictions_{nom}_{j}.csv", index=False)
    return sortie
