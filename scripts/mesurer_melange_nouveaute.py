#!/usr/bin/env python3
"""Mesure unique du mélange v2 + v8, de la soupe v2 + v8 et du détecteur de nouveauté sur la v2
(docs/protocole_maladies_melange_nouveaute.md, sections 2 et 3). À lancer une seule fois, après le commit du protocole.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_melange_nouveaute.py
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp, softmax
from scipy.stats import rankdata

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from mesurer_adoption_v5 import MALADE, NOMMEE, mesures, part  # noqa: E402

GPU = RACINE / "out/maladies/kaggle_adoption_finale"
DOS = RACINE / "out/maladies/melange"
NOUV = RACINE / "out/maladies/nouveaute"
P = ["p_saine", "p_black_sigatoka", "p_fusarium"]
JEUX = ["validation", "bananalsd", "val_loin_feuilles"]
VRAIE = {"saine": 0, "cercosporiose_noire": 1, "fusariose": 2}
NOMS = {"saine": "saine", "black_sigatoka": "cercosporiose_noire", "fusarium": "fusariose",
        "malade_non_identifiee": "malade_non_identifiee", "inconnu": "je_ne_sais_pas"}
CLASSES = ["saine", "black_sigatoka", "fusarium"]


def auc(score, positif):
    r = rankdata(score); n1 = int(positif.sum()); n0 = len(score) - n1
    return float((r[positif].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# ---------- partie A : seuils par les règles de la v2 (carnet v8, sections 6 et 7) ----------
def regler(p, v):
    malade, pm = v > 0, p[:, 1:].sum(1)
    couts = [(2 * int((~(pm >= s) & malade).sum()) + int(((pm >= s) & ~malade).sum()), s) for s in np.round(np.arange(0.05, 0.96, 0.05), 2)]
    alerte = float(min(couts)[1])
    partn, maladie = p[:, 1:].max(1) / np.maximum(pm, 1e-9), 1 + p[:, 1:].argmax(1)
    al, nom = (pm >= alerte) & malade, 1.0
    for s in np.round(np.arange(0.50, 1.0, 0.01), 2):
        n = al & (partn >= s)
        if n.sum() and (maladie[n] == v[n]).mean() >= 0.95:
            nom = float(s); break
    return dict(seuil_alerte=alerte, seuil_nom=nom, seuil_confiance=float(np.quantile(p.max(1), 0.05)))


def decider(p, s):
    pm = p[:, 1:].sum(1); partn = p[:, 1:].max(1) / np.maximum(pm, 1e-9)
    nom = np.array(CLASSES)[1 + p[:, 1:].argmax(1)]
    r = np.where(pm < s["seuil_alerte"], "saine", np.where(partn >= s["seuil_nom"], nom, "malade_non_identifiee")).astype(object)
    r[p.max(1) < s["seuil_confiance"]] = "inconnu"
    return [NOMS[x] for x in r]


def partie_a():
    for j in JEUX:
        shutil.copy(GPU / f"predictions_v2_{j}.csv", DOS / f"predictions_v2_{j}.csv")
    cand = {}
    for nom in ("melange", "soupe"):
        tab = {}
        for j in JEUX:
            a = pd.read_csv(GPU / f"predictions_v2_{j}.csv")
            if nom == "melange":
                b = pd.read_csv(GPU / f"predictions_v8_{j}.csv")
                assert (a.chemin == b.chemin).all()
                a[P] = (a[P].to_numpy() + b[P].to_numpy()) / 2
            else:
                b = pd.read_csv(DOS / f"predictions_soupe_{j}.csv")
                assert (a.chemin == b.chemin).all()
                a[P] = b[P].to_numpy()
            tab[j] = a
        val = tab["validation"]
        s = regler(val[P].to_numpy(), val.classe_vraie.map(VRAIE).to_numpy())
        for j, d in tab.items():
            d["reponse"] = decider(d[P].to_numpy(), s)
            d.to_csv(DOS / f"predictions_{nom}_{j}.csv", index=False)
        cand[nom] = s
    r = mesures(DOS, "v2")
    lv2 = pd.read_csv(DOS / "predictions_v2_val_loin_feuilles.csv")
    auc_v2 = auc(1 - lv2.p_saine.to_numpy(), lv2.classe_vraie.eq("malade").to_numpy())
    bilan = dict(v2=dict(mesures=r, auc_loin=auc_v2))
    p = lambda x, k: x[k]["part"]  # noqa: E731
    for nom, s in cand.items():
        m = mesures(DOS, nom)
        l = pd.read_csv(DOS / f"predictions_{nom}_val_loin_feuilles.csv")
        a_l = auc(1 - l.p_saine.to_numpy(), l.classe_vraie.eq("malade").to_numpy())
        c = {
            "validation_malades_dites_saines <= v2 + 0,005": p(m, "validation_malades_dites_saines") <= p(r, "validation_malades_dites_saines") + 0.005,
            "validation_fausses_alertes <= v2 + 0,01": p(m, "validation_fausses_alertes") <= p(r, "validation_fausses_alertes") + 0.01,
            "validation_nommee_juste >= 0,95": p(m, "validation_nommee_juste") >= 0.95,
            "bananalsd_sigatoka_nommee >= v2 - 0,02": p(m, "bananalsd_sigatoka_nommee") >= p(r, "bananalsd_sigatoka_nommee") - 0.02,
            "bananalsd_saines_bien_classees >= v2 - 0,02": p(m, "bananalsd_saines_bien_classees") >= p(r, "bananalsd_saines_bien_classees") - 0.02,
            "bananalsd_inconnues_dites_saines <= v2 + 0,01": p(m, "bananalsd_inconnues_dites_saines") <= p(r, "bananalsd_inconnues_dites_saines") + 0.01,
            "auc_loin >= v2 - 0,02": a_l >= auc_v2 - 0.02,
            "gain : bananalsd_sigatoka_nommee >= v2 + 0,01": m["bananalsd_sigatoka_nommee"]["k"] >= np.ceil((p(r, "bananalsd_sigatoka_nommee") + 0.01) * 473 - 1e-9),
        }
        bilan[nom] = dict(seuils=s, mesures=m, auc_loin=a_l, conditions=c, adoptable=all(c.values()))
    ad = [n for n in cand if bilan[n]["adoptable"]]
    if len(ad) == 2:
        g = {n: p(bilan[n]["mesures"], "bananalsd_sigatoka_nommee") for n in ad}
        ad = ["soupe"] if abs(g["melange"] - g["soupe"]) < 0.01 else [max(g, key=g.get)]
    bilan["retenu"] = ad[0] if ad else "v2"
    return bilan


# ---------- partie B : détecteur de nouveauté ----------
def charger(nom):
    d = np.load(NOUV / f"caracteristiques_{nom}.npz", allow_pickle=True)
    return d["car"].astype(np.float64), d["logits"].astype(np.float64), d["chemin"], d["classe"]


def inverse_reduite(x):
    s = np.cov(x, rowvar=False)
    return np.linalg.inv(0.9 * s + 0.1 * np.trace(s) / s.shape[0] * np.eye(s.shape[0]))


def scores(ajust, z, logits):
    """Les 4 variantes, moyennées sur les 3 réseaux."""
    car_a, _, _, cl_a = ajust
    out = {k: [] for k in "abcd"}
    for k in range(car_a.shape[0]):
        xa = car_a[k]
        mus = {c: xa[cl_a == c].mean(0) for c in sorted(set(cl_a))}
        icov = inverse_reduite(np.concatenate([xa[cl_a == c] - mus[c] for c in mus]))
        mu0, icov0 = xa.mean(0), inverse_reduite(xa)
        zk = z[k]
        d = np.stack([np.einsum("ij,jk,ik->i", zk - m, icov, zk - m) for m in mus.values()], 1)
        d0 = np.einsum("ij,jk,ik->i", zk - mu0, icov0, zk - mu0)
        out["a"].append(1 - softmax(logits[k], 1).max(1))
        out["b"].append(-logsumexp(logits[k], 1))
        out["c"].append(d.min(1))
        out["d"].append((d - d0[:, None]).min(1))
    return {k: np.mean(v, 0) for k, v in out.items()}


def partie_b():
    aj = charger("ajustement")
    sc = {}
    for nom in ("tdtu", "validation", "bananalsd"):
        car, lg, ch, cl = charger(nom)
        sc[nom] = (scores(aj, car, lg), ch, cl)
    s_t, _, cl_t = sc["tdtu"]
    auc_dev = {k: auc(s_t[k], cl_t == "autre_maladie") for k in "abcd"}
    meilleure = max(auc_dev.values())
    variante = next(k for k in "abcd" if auc_dev[k] >= meilleure - 0.01)
    seuil = float(np.quantile(sc["validation"][0][variante], 0.98))
    for j in ("validation", "bananalsd"):
        d = pd.read_csv(DOS / f"predictions_v2_{j}.csv")
        s, ch, _ = sc[j]
        sj = pd.Series(s[variante], index=ch).reindex(d.chemin).to_numpy()
        assert not np.isnan(sj).any()
        d["score_nouveaute"] = np.round(sj, 4)
        d["reponse"] = np.where(d.reponse.isin(NOMMEE) & (sj >= seuil), "malade_non_identifiee", d.reponse)
        d.to_csv(DOS / f"predictions_nouveaute_{j}.csv", index=False)
    r, m = mesures(DOS, "v2"), mesures(DOS, "nouveaute")

    def nommees(modele, jeu, masque):
        d = pd.read_csv(DOS / f"predictions_{modele}_{jeu}.csv")
        return part(d.reponse.isin(NOMMEE), masque(d))
    vm = lambda d: d.classe_vraie.ne("saine")  # noqa: E731
    bi = lambda d: d.classe_vraie.str.startswith("inconnue")  # noqa: E731
    ex = dict(validation_malades_nommees=(nommees("v2", "validation", vm), nommees("nouveaute", "validation", vm)),
              bananalsd_inconnues_nommees=(nommees("v2", "bananalsd", bi), nommees("nouveaute", "bananalsd", bi)))
    p = lambda x, k: x[k]["part"]  # noqa: E731
    c = {
        "validation_malades_nommees >= v2 - 0,02": ex["validation_malades_nommees"][1]["part"] >= ex["validation_malades_nommees"][0]["part"] - 0.02,
        "validation_nommee_juste >= 0,95": p(m, "validation_nommee_juste") >= 0.95,
        "bananalsd_sigatoka_nommee >= v2 - 0,02": p(m, "bananalsd_sigatoka_nommee") >= p(r, "bananalsd_sigatoka_nommee") - 0.02,
        "gain : bananalsd_inconnues_nommees <= v2 - 0,10": ex["bananalsd_inconnues_nommees"][1]["part"] <= ex["bananalsd_inconnues_nommees"][0]["part"] - 0.10,
    }
    return dict(auc_dev_tdtu=auc_dev, variante=variante, seuil=seuil, mesures=m, v2=r, nommees=ex, conditions=c,
                adopte=all(c.values()))


def main():
    sortie = DOS / "bilan_melange_nouveaute.json"
    if sortie.exists():
        sys.exit(f"{sortie} existe déjà : mesure unique, rien n'est refait.")
    bilan = dict(partie_a=partie_a(), partie_b=partie_b())
    sortie.write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    a, b = bilan["partie_a"], bilan["partie_b"]
    cles = ["validation_malades_dites_saines", "validation_fausses_alertes", "validation_nommee_juste", "bananalsd_sigatoka_nommee",
            "bananalsd_saines_bien_classees", "bananalsd_inconnues_dites_saines", "bananalsd_inconnues_dites_sigatoka"]
    print("=== Partie A")
    for k in cles:
        print(f"  {k:40s} v2 {a['v2']['mesures'][k]['part']}  mélange {a['melange']['mesures'][k]['part']}  soupe {a['soupe']['mesures'][k]['part']}")
    print(f"  {'auc_loin':40s} v2 {a['v2']['auc_loin']:.3f}  mélange {a['melange']['auc_loin']:.3f}  soupe {a['soupe']['auc_loin']:.3f}")
    for n in ("melange", "soupe"):
        print(" ", n, a[n]["seuils"], "adoptable :", a[n]["adoptable"], [k for k, ok in a[n]["conditions"].items() if not ok])
    print("  retenu :", a["retenu"])
    print("=== Partie B : AUC TDTU", {k: round(v, 3) for k, v in b["auc_dev_tdtu"].items()}, "variante", b["variante"], "seuil", round(b["seuil"], 3))
    for k, (u, v) in b["nommees"].items():
        print(f"  {k:40s} v2 {u['part']} ({u['k']}/{u['n']})  avec détecteur {v['part']} ({v['k']}/{v['n']})")
    for k in cles:
        print(f"  {k:40s} v2 {b['v2'][k]['part']}  avec détecteur {b['mesures'][k]['part']}")
    for k, ok in b["conditions"].items():
        print("   OK   " if ok else "   ÉCHEC", k)
    print("  détecteur adopté :", b["adopte"])


if __name__ == "__main__":
    main()
