#!/usr/bin/env python3
"""Détections d'un candidat, point par point, sur les jeux de RÉGLAGE (pour C-analyste). Juges jamais lus.

Sortie : out/comptage_v6/banc/points/<candidat>.csv : jeu, image, x, y (pixels de l'image à 5 cm de l'archive), score,
compte (dans le disque ou le carré mesuré), retenu (score >= seuil de la règle 3.4), statut au seuil retenu
(vrai_positif, faux_positif, ignore : apparié à un point non-mère).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_banc_points.py --candidats v5 E5p90_t0.55_d0.15
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402
import v6_banc_essais as es  # noqa: E402


def statuts(det, certains, ignores, rayon=bc.RAYON_PX):
    st = np.array(["faux_positif"] * len(det), dtype=object)
    pris = set()
    if len(det) and len(certains):
        d = cdist(det, certains)
        li, co = linear_sum_assignment(np.where(d <= rayon, d, 1e6))
        for i, j in zip(li, co):
            if d[i, j] <= rayon:
                st[i] = "vrai_positif"; pris.add(i)
    reste = [i for i in range(len(det)) if i not in pris]
    if len(ignores) and reste:
        dm = cdist(det[reste], ignores).min(1)
        for i, v in zip(reste, dm):
            if v <= rayon:
                st[i] = "ignore"
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidats", nargs="+", required=True)
    a = ap.parse_args()
    E = es.charger()
    tab = {l["nom"]: l for l in json.loads((bc.SORTIE / "tableau_reglage.json").read_text(encoding="utf-8"))["lignes"]}
    (bc.SORTIE / "points").mkdir(exist_ok=True)
    for nom in a.candidats:
        e, s = E[nom], tab[nom]["seuil"]
        f = ca.construire(e["fabrique"], e["reglages"])
        lignes = []
        for j in es.jeux_reglage() + ["neg"]:
            for it in bc.jeu(j):
                xy, sc = f(bc.Contexte(j, it))
                xy, sc = np.asarray(xy, float).reshape(-1, 2), np.asarray(sc, float)
                if it["zone"] is not None:
                    x0, y0, x1, y1 = it["zone"]
                    dedans = (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
                else:
                    dedans = bc.dans_masque(xy, it["masque"])
                ret = dedans & (sc >= s)
                st = np.array([""] * len(xy), dtype=object)
                if j != "neg":
                    st[ret] = statuts(xy[ret], it["pts"], it["ign"])
                else:
                    st[ret] = "faux_positif"
                for (x, y), v, c, r, t in zip(xy, sc, dedans, ret, st):
                    lignes.append((j, it["nom"], round(x, 1), round(y, 1), round(v, 4), bool(c), bool(r), t))
        df = pd.DataFrame(lignes, columns=["jeu", "image", "x", "y", "score", "compte", "retenu", "statut"])
        df.to_csv(bc.SORTIE / "points" / f"{nom}.csv", index=False)
        print(nom, "seuil", s, df[df.retenu].groupby(["jeu", "statut"]).size().to_dict())


if __name__ == "__main__":
    main()
