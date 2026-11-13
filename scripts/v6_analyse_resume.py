#!/usr/bin/env python3
"""Tables de l'analyse d'erreurs (agent C-analyste) à partir de out/comptage/analyse/pieds_<tag>.csv et fausses_<tag>.csv.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_resume.py --tag base
Écrit out/comptage/analyse/tables_<tag>.md.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "out/comptage/analyse"


def taux(g):
    return f"{g.retrouve.mean():.2f} ({g.retrouve.sum()}/{len(g)})" if len(g) else "-"


def table_bins(P, col, bornes, titre):
    lignes = [f"\n### Rappel selon {titre}\n"]
    P = P[P[col].notna()].copy()
    P["classe"] = pd.cut(P[col], bornes, right=False)
    cl = [str(c) for c in P["classe"].cat.categories]
    lignes.append("| modèle | jeu | " + " | ".join(cl) + " |")
    lignes.append("|" + " --- |" * (len(cl) + 2))
    for (m, j), g in P.groupby(["modele", "jeu"], sort=False):
        cells = [taux(g[g.classe.astype(str) == c]) for c in cl]
        lignes.append(f"| {m} | {j} | " + " | ".join(cells) + " |")
    return "\n".join(lignes)


def profil_oublies(P):
    lignes = ["\n### Profil des oubliés (score du meilleur pic dans le rayon de 20 px)\n",
              "| modèle | jeu | oubliés | pic pris par une autre mère (fusion) | pic ≥ seuil hors fusion | pic dans [seuil/2, seuil) | pic dans [0,05, seuil/2) | pic < 0,05 (rien) | carte max < 0,05 |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for (m, j), g in P.groupby(["modele", "jeu"], sort=False):
        o = g[~g.retrouve]
        s = g.seuil.iloc[0]
        n = len(o)
        if not n:
            continue
        f = o.fusion
        a = (~f) & (o.pic >= s)
        b = (~f) & (o.pic < s) & (o.pic >= s / 2)
        c = (~f) & (o.pic < s / 2) & (o.pic >= 0.05)
        d = (~f) & (o.pic < 0.05)
        pc = lambda x: f"{x.sum()} ({x.mean():.0%})"
        lignes.append(f"| {m} | {j} | {n} | {pc(f)} | {pc(a)} | {pc(b)} | {pc(c)} | {pc(d)} | {pc(o.vmax < 0.05)} |")
    return "\n".join(lignes)


def table_fausses(Dd, P):
    lignes = ["\n### Fausses détections par catégorie\n",
              "| modèle | jeu | détectés / annotés | fausses | doublon d'un pied retrouvé | décalée (mère non retrouvée à 20-40 px) | bord (≤ 20 px) | annoté hors zone | isolée (rien à 40 px) | sur rejet annoté (ignorée) |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for (m, j), g in P.groupby(["modele", "jeu"], sort=False):
        d = Dd[(Dd.modele == m) & (Dd.jeu == j)]
        vp = g.retrouve.sum()
        fp = d[d.cat != "rejet_annote_ignore"]
        det = vp + len(d)
        cats = ["doublon", "decalee", "bord", "annote_hors_zone", "isolee"]
        cells = [f"{(fp.cat == c).sum()}" for c in cats]
        lignes.append(f"| {m} | {j} | {det}/{len(g)} ({det / len(g):.2f}) | {len(fp)} | " + " | ".join(cells)
                      + f" | {(d.cat == 'rejet_annote_ignore').sum()} |")
    return "\n".join(lignes)


def ecart(P, a="v3", b="v5"):
    lignes = [f"\n### Écart {a} / {b} (pied par pied, chacun à son seuil)\n",
              f"| jeu | les deux | {a} seul | {b} seul | aucun | rappel {a} | rappel {b} |", "| --- | --- | --- | --- | --- | --- | --- |"]
    cle = ["jeu", "image", "x", "y"]
    A = P[P.modele == a].set_index(cle).retrouve
    B = P[P.modele == b].set_index(cle).retrouve
    J = pd.concat([A.rename("a"), B.rename("b")], axis=1).dropna()
    for j, g in J.groupby(level=0, sort=False):
        lignes.append(f"| {j} | {(g.a & g.b).sum()} | {(g.a & ~g.b).sum()} | {(~g.a & g.b).sum()} | {(~g.a & ~g.b).sum()} | "
                      f"{g.a.mean():.3f} | {g.b.mean():.3f} |")
    return "\n".join(lignes)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="base")
    a = ap.parse_args()
    P = pd.read_csv(SORTIE / f"pieds_{a.tag}.csv")
    Dd = pd.read_csv(SORTIE / f"fausses_{a.tag}.csv")
    out = [f"# Tables de l'analyse d'erreurs ({a.tag})\n", "Généré par `scripts/v6_analyse_resume.py --tag " + a.tag + "` [M].\n"]
    out.append("\n### Rappel par jeu\n\n| modèle | seuil | " + " | ".join(P.jeu.unique()) + " |\n|" + " --- |" * (P.jeu.nunique() + 2))
    for m, g in P.groupby("modele", sort=False):
        out.append(f"| {m} | {g.seuil.iloc[0]} | " + " | ".join(taux(g[g.jeu == j]) for j in P.jeu.unique()) + " |")
    out.append(table_bins(P[P.jeu.isin(["dense", "btd_val"])], "taille", [0, 30, 40, 50, 60, 70, 80, 200], "la taille de boîte (px à 5 cm ; dense et btd seulement)"))
    out.append(table_bins(P, "rayon_vert", [0, 8, 12, 16, 20, 28, 36, 100], "le rayon vert estimé sur l'image [H] (px à 5 cm)"))
    out.append("\nPart des pieds dont le centre n'est pas vert (rayon_vert NaN) : " + ", ".join(
        f"{m}/{j} {g.rayon_vert.isna().mean():.0%} (rappel {g[g.rayon_vert.isna()].retrouve.mean():.2f})"
        for (m, j), g in P.groupby(["modele", "jeu"], sort=False) if m == P.modele.iloc[0]))
    out.append(table_bins(P, "ppv", [0, 30, 40, 50, 60, 80, 120, 1e9], "la distance au plus proche voisin annoté (px à 5 cm ; 20 px = 1 m)"))
    out.append(table_bins(P, "bord", [-1e9, 0, 20, 40, 80, 160, 1e9], "la distance au bord de la zone comptée (image, disque ou zone ; px)"))
    out.append(profil_oublies(P))
    out.append(table_fausses(Dd, P))
    if {"v3", "v5"} <= set(P.modele):
        out.append(ecart(P))
    neg = SORTIE / f"neg_{a.tag}.csv"
    if neg.exists():
        N = pd.read_csv(neg)
        out.append("\n### Images sans bananier (validation)\n\n| modèle | seuil | fausses | par groupe | scores (médiane, max) | images touchées |\n| --- | --- | --- | --- | --- | --- |")
        for m, g in N.groupby("modele", sort=False):
            out.append(f"| {m} | {g.seuil.iloc[0]} | {len(g)} | {g.groupe.value_counts().to_dict()} | "
                       f"{g.score.median():.2f}, {g.score.max():.2f} | {g.image.nunique()} |")
    (SORTIE / f"tables_{a.tag}.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(out))
