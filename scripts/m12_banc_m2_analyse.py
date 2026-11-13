#!/usr/bin/env python3
"""Essais 5 et 6 (plan docs/plan_nuit_10h.md) : lecture en morceaux et à 512 px par la v10b, réglage seul.

Entrées : out/maladies/nuit_1112/banc/kaggle_morceaux/ (sorties du carnet affilecorentin/m12-banc-morceaux) :
morceaux_<jeu>.npz (indices de l'échantillon, e384 et g3 sur l'échantillon, g2 sur toutes les photos), p512_<jeu>.csv.

P(malade) des morceaux réunie par maximum, moyenne des 2 plus fortes, « ou bruité » ; combinée à la lecture entière
(morceaux seuls, maximum, moyenne). La probabilité v10b modifiée garde les proportions des maladies de la lecture
entière : P(saine) remplacée, le reste remis à l'échelle. Chaque chaîne est ensuite décidée par le code de la chaîne.
Deux chaînes de base : installée (v10b seule, loin = v2) et finaliste « à trois » (géo 1,1,1, loin = v2 ou proche).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_m2_analyse.py [echantillon|complet]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from m12_banc_trois import geo3  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else "echantillon"
K = B.SORTIE / "kaggle_morceaux"
jeux0 = B.charger_reglage()
ref_complet = B.reference(jeux0)
ESSAIS = []


def sous(d, idx):
    return {k: (v[idx] if isinstance(v, np.ndarray) and len(v) == len(d["chemin"]) else v) for k, v in d.items()}


def avec_saine(P, ps):
    """P (n, 4) dont P(saine) est remplacée par ps, les autres classes gardant leurs proportions."""
    reste = np.clip(1 - P[:, 0], 1e-9, None)
    Q = P * ((1 - ps) / reste)[:, None]
    Q[:, 0] = ps
    return Q


# chargement
jeux, ecart = {}, {}
for j in B.REGLAGE:
    z = np.load(K / f"morceaux_{j}.npz")
    d = dict(jeux0[j])
    d["G2"] = z["g2"].astype("float64")
    p512 = pd.read_csv(K / f"p512_{j}.csv")
    assert list(p512.chemin) == list(d["chemin"])
    d["P512"] = p512[["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]].to_numpy("float64")
    if MODE == "echantillon":
        idx = z["indices"]
        d = sous(d, idx)
        d["G3"] = z["g3"].astype("float64")
        ecart[j] = float(np.abs(z["e384"] - d["P10"]).max())   # contrôle demi-précision contre le cache 32 bits
    jeux[j] = d
if ecart:
    print("écart maximal lecture entière Kaggle (demi-précision) / cache :", {j: round(v, 4) for j, v in ecart.items()})

REUNIR = {"max": lambda m: m.max(1), "2 plus fortes": lambda m: np.sort(m, 1)[:, -2:].mean(1),
          "ou bruité": lambda m: 1 - np.prod(1 - m, 1)}
COMBINER = {"morceaux seuls": lambda e, a: a, "max avec entière": lambda e, a: np.maximum(e, a),
            "moyenne avec entière": lambda e, a: (e + a) / 2}
BASES = {"installée": dict(f=lambda d, P10: P10, loin_ou=False, grille=[B.M_V10B["seuil"], 0.40, 0.46, 0.52, 0.58, 0.64, 0.70]),
         "à trois": dict(f=lambda d, P10: geo3({**d, "P10": P10}, 1, 1, 1), loin_ou=True, grille=[0.62, 0.66, 0.70, 0.74, 0.78])}


def evaluer(f_P10, base, t):
    b = BASES[base]
    r = {}
    for j, d in jeux.items():
        rp = B.decider_v10b(b["f"](d, f_P10(d)), seuil=t)
        if b["loin_ou"]:
            rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
            rep = np.where(d["loin"], rl, rp)
        else:
            rep = np.where(d["loin"], d["r_loin"], rp)
        r[j] = B.mesure(d, rep)
    r["cout_moyen"] = float(np.mean([r[j]["cout"] for j in jeux]))
    return r


def tanzanie_ok(r):   # limites du plan ramenées en taux : 14 / 2 001 et 77 / 1 000
    v = r["validation"]
    return v["msa"] / v["nm"] <= 14 / 2001 + 1e-12 and v["sea"] / v["ns"] <= 77 / 1000 + 1e-12


def montrer(nom, r, gain=None):
    print(("ok " if tanzanie_ok(r) else "   ") + B.ligne(nom, r) + ("" if gain is None else f" | gain {gain:+.2f}"), flush=True)


grilles = {"g2": "G2"} if MODE == "complet" else {"g2": "G2", "g3": "G3"}
for base in BASES:
    print(f"\n######## base : {base} ########")
    entiere = {t: evaluer(lambda d: d["P10"], base, t) for t in BASES[base]["grille"]}
    ref_t = BASES[base]["grille"][0] if base == "installée" else 0.74
    ref = entiere[ref_t]
    for t, r in entiere.items():
        montrer(f"entière 384 t={t:.4g}", r)
    meilleur_entier = min((r["cout_moyen"] for r in entiere.values() if tanzanie_ok(r)), default=np.inf)
    # essai 6 : 512 px, et moyenne 384 + 512
    for nom, f in [("entière 512", lambda d: d["P512"]), ("moyenne 384 + 512", lambda d: (d["P10"] + d["P512"]) / 2)]:
        for t in BASES[base]["grille"]:
            r = evaluer(f, base, t)
            ESSAIS.append(dict(famille="essai 6", nom=f"{base} / {nom} / t={t}", tanzanie_ok=tanzanie_ok(r), **r))
            montrer(f"{nom} t={t:.4g}", r, ref["cout_moyen"] - r["cout_moyen"])
    # essai 5 : morceaux
    for g, cle in grilles.items():
        for nr, fr in REUNIR.items():
            for nc, fc in COMBINER.items():
                for t in BASES[base]["grille"]:
                    def f(d, fr=fr, fc=fc, cle=cle):
                        pm = fc(1 - d["P10"][:, 0], fr(1 - d[cle][:, :, 0]))
                        return avec_saine(d["P10"], 1 - pm)
                    r = evaluer(f, base, t)
                    ESSAIS.append(dict(famille=f"essai 5 {g}", nom=f"{base} / {nr} / {nc} / t={t}", tanzanie_ok=tanzanie_ok(r),
                                       gain_sur_meilleur_entier=meilleur_entier - r["cout_moyen"], **r))
                    montrer(f"{g} {nr} / {nc} t={t:.4g}", r, meilleur_entier - r["cout_moyen"])
    ok = [e for e in ESSAIS if e["nom"].startswith(base) and e["tanzanie_ok"] and e["famille"].startswith("essai 5")]
    if ok:
        m = min(ok, key=lambda e: e["cout_moyen"])
        print(f"\n>> {base} : meilleur morceaux (Tanzanie dans les limites) {m['cout_moyen']:.2f} ({m['nom']}) ;"
              f" meilleure lecture entière, même grille {meilleur_entier:.2f} ; gain {meilleur_entier - m['cout_moyen']:+.2f}")
print(f"\nessais : {len(ESSAIS)}")
(B.SORTIE / f"essais_m2_{MODE}.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
