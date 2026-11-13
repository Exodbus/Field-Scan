#!/usr/bin/env python3
"""Essai 9 : effet d'une marge au bord des tuiles (1 m = 20 px à 5 cm), mesuré sans changer la référence.

Pour chaque candidat donné : F1 par jeu avec la mesure de référence (marge 0) et avec une marge m (annotés ET détections
à moins de m px du bord de l'image retirés). L'écart dit quelle part des erreurs vient des bords de tuile. Seuls les jeux
en tuiles (dense, plantain, btd_val) changent : jeunes est mesuré dans un disque, MM dans un carré loin du bord.
Le seuil de chaque candidat est celui de la règle 3.4 (lu dans tableau_reglage.json). Juges non lus.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402
import v6_banc_essais as es  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidats", nargs="+", default=["v5"])
    ap.add_argument("--marges", nargs="+", type=int, default=[10, 20, 40])
    a = ap.parse_args()
    E = es.charger()
    tab = {l["nom"]: l for l in json.loads((bc.SORTIE / "tableau_reglage.json").read_text(encoding="utf-8"))["lignes"]}
    T = pd.concat([pd.read_csv(bc.D / "tuiles.csv"), pd.read_csv(bc.D6 / "tuiles.csv")]).drop_duplicates("image_path").set_index("image_path")
    jeux = [j for j in es.jeux_reglage() if j in ("dense", "plantain", "btd_val")]
    res = {}
    for nom in a.candidats:
        e, s = E[nom], tab[nom]["seuil"]
        f = ca.construire(e["fabrique"], e["reglages"])
        res[nom] = {}
        for j in jeux:
            items = bc.jeu(j)
            ligne = {"0": round(bc.mesurer_jeu(f, j, items)[s]["f1"], 4)}
            for m in a.marges:
                def g(ctx, m=m):
                    xy, sc = f(ctx)
                    w, h = T.loc[ctx.nom, "largeur"], T.loc[ctx.nom, "hauteur"]
                    k = (xy[:, 0] >= m) & (xy[:, 0] <= w - m) & (xy[:, 1] >= m) & (xy[:, 1] <= h - m)
                    return xy[k], sc[k]
                it2 = []
                for e2 in items:
                    w, h = T.loc[e2["nom"], "largeur"], T.loc[e2["nom"], "hauteur"]
                    p = e2["pts"]
                    k = (p[:, 0] >= m) & (p[:, 0] <= w - m) & (p[:, 1] >= m) & (p[:, 1] <= h - m)
                    it2.append(dict(e2, pts=p[k]))
                ligne[str(m)] = round(bc.mesurer_jeu(g, j, it2)[s]["f1"], 4)
            res[nom][j] = ligne
            print(f"{nom:36s} seuil {s:.2f} {j:9s} F1 selon la marge (px) : {ligne}")
    (bc.SORTIE / "essai9_marge.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
