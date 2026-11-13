#!/usr/bin/env python3
"""Essai 8 : compte par intégrale de la carte de chaleur, comparé au compte par pics (erreur de compte seulement).

Compte d'une image = somme de la carte (cellules dont le centre est dans le disque ou le carré mesuré) / K.
K (« masse d'un plant ») est réglé sur le réglage de deux façons : K commun (somme des cartes / somme des annotés,
tous jeux de réglage réunis) ; et, pour mémoire, K par jeu (optimiste : il connaît le jeu). Variante : somme des
seules cellules au-dessus de 0,10 (retire le bruit de fond). L'erreur de compte d'un jeu = |compté / annotés − 1|.
Les juges ne sont pas lus ici.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402
import v6_banc_essais as es  # noqa: E402


def masse(carte, e, plancher):
    H, W = carte.shape
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = (xx + 0.5) * bc.STRIDE, (yy + 0.5) * bc.STRIDE
    if e["zone"] is not None:
        x0, y0, x1, y1 = e["zone"]
        g = (cx >= x0) & (cx <= x1) & (cy >= y0) & (cy <= y1)
    elif e["masque"] is not None:
        mx, my, mr = e["masque"]
        g = (cx - mx) ** 2 + (cy - my) ** 2 <= mr ** 2
    else:
        g = np.ones_like(carte, bool)
    c = np.where(carte >= plancher, carte, 0.0)
    return float(c[g].sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cartes", nargs="+", default=["v5:base", "v3:base", "v5:m8", "moy:v3+v5"])
    a = ap.parse_args()
    jeux = es.jeux_reglage()
    items = {j: bc.jeu(j) for j in jeux + ["neg"]}
    res = {}
    for spec in a.cartes:
        for plancher in (0.0, 0.10):
            s, n = {}, {}
            for j in jeux + ["neg"]:
                tot = 0.0
                for e in items[j]:
                    ctx = bc.Contexte(j, e)
                    if spec.startswith("moy:"):
                        c = np.mean([ctx.carte(m) for m in spec[4:].split("+")], 0)
                    else:
                        m, v = spec.split(":")
                        c = ctx.carte(m, v)
                    tot += masse(c, e, plancher)
                s[j], n[j] = tot, sum(len(e["pts"]) for e in items[j])
            K = sum(s[j] for j in jeux) / sum(n[j] for j in jeux)
            err = {j: abs(s[j] / K / n[j] - 1) for j in jeux}
            kj = {j: s[j] / n[j] for j in jeux}
            res[f"{spec}_plancher{plancher}"] = dict(K_commun=K, K_par_jeu=kj, err_par_jeu=err, err_moyenne=float(np.mean(list(err.values()))),
                                                     compte_par_jeu={j: s[j] / K for j in jeux}, annotes=n,
                                                     faux_sur_negatifs=s["neg"] / K)
            print(f"{spec:12s} plancher {plancher:.2f} : K {K:.2f} ; erreur de compte " +
                  ", ".join(f"{j} {err[j]:.3f}" for j in jeux) + f" ; moyenne {res[f'{spec}_plancher{plancher}']['err_moyenne']:.3f} ; "
                  f"« plants » comptés sur les images sans bananier {s['neg'] / K:.0f} ; K par jeu " + ", ".join(f"{j} {kj[j]:.2f}" for j in jeux))
    (bc.SORTIE / "essai8_integrale.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
