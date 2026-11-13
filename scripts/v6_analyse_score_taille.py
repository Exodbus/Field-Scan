#!/usr/bin/env python3
"""Score du meilleur pic (rayon 20 px) selon la taille de boîte, par modèle et jeu (agent C-analyste).
Dit si le score dépend de la taille du plant (sous-confiance sur les petits) plutôt que d'un défaut de localisation.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_score_taille.py --tags base btd
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
S = RACINE / "out/comptage/analyse"
ap = argparse.ArgumentParser(); ap.add_argument("--tags", nargs="+", default=["base", "btd"]); ap.add_argument("--sortie", default="score_taille.md")
a = ap.parse_args()
P = pd.concat([pd.read_csv(S / f"pieds_{t}.csv") for t in a.tags])
P = P[P.taille.notna() & P.jeu.isin(["dense", "btd_val"])]
P["classe"] = pd.cut(P.taille, [0, 20, 25, 30, 35, 40, 50, 60, 80, 200], right=False)
out = ["# Score du meilleur pic selon la taille de boîte [M]\n", f"`scripts/v6_analyse_score_taille.py --tags {' '.join(a.tags)}`\n",
       "Médiane du score du meilleur pic à 20 px (0 si aucun pic au-dessus de 0,02) ; entre parenthèses, nombre de pieds.\n"]
cl = [str(c) for c in P.classe.cat.categories]
out.append("| modèle | variante | jeu | " + " | ".join(cl) + " |"); out.append("|" + " --- |" * (len(cl) + 3))
for (m, v, j), g in P.groupby(["modele", "variante", "jeu"], sort=False):
    cells = []
    for c in cl:
        h = g[g.classe.astype(str) == c]
        cells.append(f"{h.pic.median():.2f} ({len(h)})" if len(h) else "-")
    out.append(f"| {m} | {v} | {j} | " + " | ".join(cells) + " |")
(S / a.sortie).write_text("\n".join(out) + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8"); print("\n".join(out))
