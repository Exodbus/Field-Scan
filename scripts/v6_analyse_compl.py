#!/usr/bin/env python3
"""Analyses complémentaires (agent C-analyste) sur pieds_<tag>.csv et fausses_<tag>.csv :
  1. fausses « isolées » : part co-détectée par le v3 (et le v4) à moins de 20 px, comparée aux vraies détections ;
  2. effet d'une baisse de seuil du v5 (0,30 -> 0,25 -> 0,20 -> 0,15) : pieds gagnés, fausses ajoutées, par jeu ;
  3. plus proches voisins annotés très proches (< 30 px) : distances (doublons d'annotation ?) ;
  4. doublons : taille de la boîte du pied déjà retrouvé ;
  5. densité des fausses près du bord (par unité de surface) ;
  6. part des oubliés du v5 retrouvés par le v3 et/ou le v4 (gain maximal d'un mélange parfait).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_compl.py --tag base
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import v6_analyse_erreurs as ae  # noqa: E402

bc = ae.bc
ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="base")
ap.add_argument("--jeux", nargs="+", default=None)
a = ap.parse_args()
S = ae.SORTIE
P = pd.read_csv(S / f"pieds_{a.tag}.csv"); D = pd.read_csv(S / f"fausses_{a.tag}.csv")
jeux = a.jeux or list(P.jeu.unique())
out = [f"# Analyses complémentaires ({a.tag})\n", f"`scripts/v6_analyse_compl.py --tag {a.tag}` [M]\n"]


def dets(modele, jeu, nom, seuil):
    xy, sc = bc.pics(ae.carte(modele, "base", jeu, nom), bc.K_PICS, seuil)
    return xy, sc


# 1 et 2
out.append("\n## 1. Fausses détections du v5 co-détectées par un autre modèle (à 20 px)\n")
out.append("| jeu | catégorie | n | v3 aussi | v4 aussi | (référence : vraies détections du v5, v3 aussi) |\n| --- | --- | --- | --- | --- | --- |")
out2 = ["\n## 2. Baisse du seuil du v5 : pieds gagnés et fausses ajoutées (cumul depuis 0,30)\n",
        "| jeu | seuil | retrouvés | fausses (hors ignorées) | gain de pieds | fausses ajoutées | fausses ajoutées par pied gagné | F1 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |"]
for j in jeux:
    items = {e["nom"]: e for e in ae.items_complets(j)}
    d5 = D[(D.modele == "v5") & (D.jeu == j)]
    p5 = P[(P.modele == "v5") & (P.jeu == j)]
    co = {"v3": [], "v4": []}
    ref = []
    for nom, g in d5.groupby("image"):
        for m in ("v3", "v4"):
            if m not in set(P.modele):
                continue
            xy, _ = dets(m, j, nom, ae.SEUILS_ADOPTES[m])
            for r in g.itertuples():
                co[m].append((r.cat, bool(len(xy)) and np.hypot(xy[:, 0] - r.x, xy[:, 1] - r.y).min() <= 20))
    # référence : pieds retrouvés par le v5 et aussi par le v3
    pr = P[(P.jeu == j) & (P.modele.isin(["v3", "v5"]))].pivot_table(index=["image", "x", "y"], columns="modele", values="retrouve")
    refv = pr[pr.v5 == 1].v3.mean() if "v3" in pr else np.nan
    for cat in ["isolee", "doublon", "bord", "decalee"]:
        c3 = [b for c, b in co["v3"] if c == cat]; c4 = [b for c, b in co["v4"] if c == cat]
        if c3:
            out.append(f"| {j} | {cat} | {len(c3)} | {np.mean(c3):.0%} | {np.mean(c4):.0%} | {refv:.0%} |")
    # 2. seuils
    base = None
    for s in [0.30, 0.25, 0.20, 0.15]:
        vp = fp = fn = 0
        for nom, e in items.items():
            xy, sc = dets("v5", j, nom, s)
            g = ae.dans_compte(xy, e) if len(xy) else np.zeros(0, bool)
            n, f, m = bc.compter(xy[g], e["pts"], e["ign"])
            vp += n; fp += f; fn += m
        if base is None:
            base = (vp, fp)
        dv, df = vp - base[0], fp - base[1]
        out2.append(f"| {j} | {s:.2f} | {vp} | {fp} | {dv} | {df} | {df / dv if dv else float('nan'):.2f} | {bc.prf(vp, fp, fn)[2]:.3f} |")
out += out2

# 3
out.append("\n## 3. Mères dont le plus proche voisin annoté est à moins de 30 px (1,5 m)\n")
out.append("| jeu | n | < 10 px | 10-20 px | 20-30 px | rappel v5 |\n| --- | --- | --- | --- | --- | --- |")
for j in jeux:
    g = P[(P.modele == "v5") & (P.jeu == j) & (P.ppv < 30)]
    out.append(f"| {j} | {len(g)} | {(g.ppv < 10).sum()} | {((g.ppv >= 10) & (g.ppv < 20)).sum()} | {(g.ppv >= 20).sum()} | {g.retrouve.mean():.2f} |")

# 4
out.append("\n## 4. Doublons du v5 : taille de la boîte du pied le plus proche (dense, btd)\n")
for j in [x for x in jeux if x in ("dense", "btd_val")]:
    p5 = P[(P.modele == "v5") & (P.jeu == j)]
    d5 = D[(D.modele == "v5") & (D.jeu == j) & (D.cat == "doublon")]
    tailles = []
    for r in d5.itertuples():
        q = p5[p5.image == r.image]
        k = np.hypot(q.x - r.x, q.y - r.y).idxmin()
        tailles.append(q.loc[k, "taille"])
    t = np.array(tailles)
    out.append(f"- {j} : {len(t)} doublons ; taille médiane du pied visé {np.nanmedian(t):.0f} px (tous les pieds : "
               f"{p5.taille.median():.0f} px) ; part des doublons sur des pieds de 70 px et plus : {np.mean(t >= 70):.0%} "
               f"(part de ces pieds : {np.mean(p5.taille >= 70):.0%})")

# 5
out.append("\n## 5. Fausses du v5 par bande de distance au bord (densité par rapport à l'intérieur)\n")
out.append("| jeu | bande | fausses | part de la surface comptée | fausses / part de surface (relatif à > 40 px) |\n| --- | --- | --- | --- | --- |")
for j in jeux:
    items = ae.items_complets(j)
    surf = {"0-20": 0, "20-40": 0, ">40": 0}
    for e in items:
        yy, xx = np.mgrid[0:e["h"]:4, 0:e["l"]:4]
        xy = np.c_[xx.ravel() + 2, yy.ravel() + 2].astype(float)
        g = ae.dans_compte(xy, e)
        b = ae.dist_bord(xy[g], e)
        surf["0-20"] += (b <= 20).sum(); surf["20-40"] += ((b > 20) & (b <= 40)).sum(); surf[">40"] += (b > 40).sum()
    d5 = D[(D.modele == "v5") & (D.jeu == j) & (D.cat != "rejet_annote_ignore")]
    n = {"0-20": (d5.bord <= 20).sum(), "20-40": ((d5.bord > 20) & (d5.bord <= 40)).sum(), ">40": (d5.bord > 40).sum()}
    tot = sum(surf.values())
    dens_int = n[">40"] / max(surf[">40"], 1)
    for k in surf:
        out.append(f"| {j} | {k} | {n[k]} | {surf[k] / tot:.0%} | {(n[k] / max(surf[k], 1)) / max(dens_int, 1e-9):.2f} |")

# 6
out.append("\n## 6. Oubliés du v5 retrouvés par un autre modèle (chacun à son seuil)\n")
out.append("| jeu | oubliés v5 | retrouvés par v3 | par v4 | par v3 ou v4 |\n| --- | --- | --- | --- | --- |")
pv = P.pivot_table(index=["jeu", "image", "x", "y"], columns="modele", values="retrouve").reset_index()
for j in jeux:
    g = pv[(pv.jeu == j) & (pv.v5 == 0)]
    if not len(g):
        continue
    v3 = g.v3 == 1 if "v3" in g else pd.Series(False, g.index)
    v4 = g.v4 == 1 if "v4" in g else pd.Series(False, g.index)
    out.append(f"| {j} | {len(g)} | {v3.sum()} ({v3.mean():.0%}) | {v4.sum()} ({v4.mean():.0%}) | {(v3 | v4).sum()} ({(v3 | v4).mean():.0%}) |")

(S / f"compl_{a.tag}.md").write_text("\n".join(out) + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(out))
