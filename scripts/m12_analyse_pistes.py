#!/usr/bin/env python3
"""M-analyste (nuit du 12/11) : chiffrage des pistes tirées de l'analyse d'erreurs (réglage seulement).

Ce ne sont PAS des essais de sélection : chaque variante est chiffrée pour dire à M-banc / M-entraîneur ce qu'elle
peut rapporter au mieux ; s'ils la reprennent, ils la comptent dans leurs essais et la règlent eux-mêmes.

1. Séparabilité : AUC saines / malades par jeu et par modèle (v10b, soupe, v2, lecteur F1, candidats v12).
2. PSFD jeu augmenté : coûts de la chaîne installée et des finalistes (a) sur toutes les photos, (b) sans les copies
   tournées (coins noirs), (c) par groupe de quasi-copies (DINOv3 >= 0,95 : un groupe raté si la majorité l'est).
3. Variantes de décision sur F1 (même lecteur, même seuil) :
   - « F1 ou v10b sûre » : alerte aussi si P(saine) v10b < x (photos proches) ;
   - branche loin : « v2 ou proche » seulement si p_loin < y, v2 seule au-delà ;
   - plafond : ratées de F1 dont la marge est < 0,05 toutes rattrapées (ce que rapporterait un lecteur un peu meilleur).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_pistes.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "out/maladies/analyse"
T = pd.read_csv(SORTIE / "table_reglage.csv")
K1 = "F1_trois_morceaux2x2"
JEUX = ["validation", "tdtu", "psfd", "ethiopie"]
COP = pd.read_csv(SORTIE / "psfd_copies.csv")
T = T.merge(COP[["chemin", "coins_noirs", "dino_0.95"]], on="chemin", how="left")
T["coins_noirs"] = T.coins_noirs.fillna(False).astype(bool)


def auc(pos, neg):
    """P(score malade d'une malade > score d'une saine), scores = P(malade)."""
    pos, neg = np.asarray(pos), np.asarray(neg)
    r = pd.Series(np.concatenate([pos, neg])).rank().to_numpy()
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def cout(al, sub=None):
    """Coût moyen (points) d'un vecteur d'alertes sur T (ou un sous-ensemble). Renvoie (moyenne, détail)."""
    d = {}
    for j in JEUX:
        m = (T.jeu == j).to_numpy() if sub is None else ((T.jeu == j) & sub).to_numpy()
        mal, sa = T.malade.to_numpy() & m, ~T.malade.to_numpy() & m
        msa, sea = int((mal & ~al).sum()), int((sa & al).sum())
        d[j] = (msa, int(mal.sum()), sea, int(sa.sum()), 100 * (3 * msa / mal.sum() + (sea / sa.sum() if sa.sum() else 0)))
    return float(np.mean([d[j][4] for j in JEUX])), d


def fmt(nom, c):
    m, d = c
    return f"{nom:46s} moy={m:6.2f} | " + " | ".join(f"{j[:4]} {d[j][0]}/{d[j][1]} {d[j][2]}/{d[j][3]} c={d[j][4]:.1f}" for j in JEUX)


def main():
    res = {}
    print("1. AUC saines / malades (P(malade))")
    mods = {"v10b": 1 - T.ps_v10b, "soupe": 1 - T.ps_soupe, "v2": 1 - T.ps_v2, "lecteur F1": 1 - T[f"ps_{K1}"],
            "lecteur F3": 1 - T.ps_F3_trois}
    res["auc"] = {}
    for nom, s in mods.items():
        r = {j: auc(s[(T.jeu == j) & T.malade], s[(T.jeu == j) & ~T.malade]) for j in ["validation", "tdtu", "ethiopie"]}
        res["auc"][nom] = r
        print(f"  {nom:12s}", {k: round(v, 3) for k, v in r.items()})

    print("\n2. PSFD jeu augmenté : coûts selon le compte de PSFD")
    res["psfd"] = {}
    for ch in ["installee", "F3_trois", "F2_trois_384_512", K1, "reserve_geo_v10b_soupe_loin"]:
        al = T[f"al_{ch}"].to_numpy()
        tout = cout(al)
        sans = cout(al, ~T.coins_noirs)
        p = T[(T.jeu == "psfd") & T.malade]
        g = p.groupby("dino_0.95")[f"al_{ch}"].apply(lambda x: (~x).mean())
        taux_g = float((g > 0.5).mean())
        moy_g = float(np.mean([tout[1][j][4] for j in ["validation", "tdtu", "ethiopie"]] + [300 * taux_g]))
        res["psfd"][ch] = dict(tout=tout[0], sans_tournees=sans[0], psfd_par_groupes=moy_g,
                               psfd_cout=tout[1]["psfd"][4], psfd_cout_sans_tournees=sans[1]["psfd"][4], psfd_cout_groupes=300 * taux_g)
        print(f"  {ch:28s} coût moyen : toutes {tout[0]:.2f} ; sans copies tournées {sans[0]:.2f} ; PSFD par groupes {moy_g:.2f}"
              f"  (PSFD seul : {tout[1]['psfd'][4]:.1f} / {sans[1]['psfd'][4]:.1f} / {300 * taux_g:.1f})")

    print("\n3. Variantes de décision autour de F1")
    loin = T.loin.to_numpy()
    a_f1 = T[f"al_{K1}"].to_numpy()
    print(fmt("installée", cout(T.al_installee.to_numpy())))
    print(fmt("F1", cout(a_f1)))
    res["variantes"] = {}
    for x in [0.10, 0.15, 0.20, 0.25, 0.30]:
        al = a_f1 | (~loin & (T.ps_v10b.to_numpy() < x))
        c = cout(al)
        res["variantes"][f"F1 ou v10b<{x}"] = c[0]
        print(fmt(f"F1 ou P(saine) v10b < {x}", c))
    # branche loin : « v2 ou proche » seulement si p_loin < y
    a_v2 = T.al_v2_seule.to_numpy()
    for y in [0.7, 0.8, 0.9, 0.95, 0.99]:
        al = np.where(loin & (T.p_loin.to_numpy() >= y), a_v2, a_f1)
        c = cout(al)
        res["variantes"][f"F1 loin v2 seule si p_loin>={y}"] = c[0]
        print(fmt(f"F1, v2 seule si p_loin >= {y}", c))
    # plafond « presque »
    ps1 = T[f"ps_{K1}"].to_numpy()
    marge = np.where(loin, np.minimum(T.ps_v2.to_numpy() - 0.70, ps1 - 0.70), ps1 - 0.70)
    for z in [0.05, 0.10]:
        al = a_f1 | (T.malade.to_numpy() & (marge < z))
        c = cout(al)
        res["variantes"][f"plafond ratées marge<{z} rattrapées"] = c[0]
        print(fmt(f"plafond : ratées à marge < {z} rattrapées", c))
    (SORTIE / "pistes_bilan.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
