#!/usr/bin/env python3
"""Effet de l'échelle d'entrée sur les petits plants (agent C-analyste). Pour chaque (modèle, variante) en cache
(base = 5 cm ; s35 = image agrandie 5 -> 3,5 cm ; s70 = réduite 5 -> 7 cm), seuils 0,15 à 0,40 :
F1 du jeu, rappel par classe de taille de boîte, fausses détections. Pics à la résolution propre de la carte,
ramenés en pixels à 5 cm ; même appariement que le banc. Réglage seulement (dense, btd_val).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_echelle.py --jeux btd_val dense --modeles v5 v3
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
ap.add_argument("--jeux", nargs="+", default=["btd_val", "dense"])
ap.add_argument("--modeles", nargs="+", default=["v5", "v3"])
ap.add_argument("--variantes", nargs="+", default=["base", "s35", "s70"])
ap.add_argument("--sortie", default="echelle.md")
a = ap.parse_args()
BORNES = [0, 25, 30, 35, 40, 50, 1000]
SEUILS = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
out = ["# Effet de l'échelle d'entrée [M]\n", f"`scripts/v6_analyse_echelle.py --jeux {' '.join(a.jeux)} --modeles {' '.join(a.modeles)}`\n",
       "Rappel par classe de taille de boîte (px à 5 cm) ; F1 et détectés / annotés du jeu entier.\n"]
for j in a.jeux:
    items = ae.items_complets(j)
    out.append(f"\n## {j}\n")
    cl = [f"[{BORNES[k]}, {BORNES[k + 1]})" for k in range(len(BORNES) - 1)]
    out.append("| modèle | variante | seuil | F1 | P | R | détectés / annotés | " + " | ".join(cl) + " |")
    out.append("|" + " --- |" * (7 + len(cl)))
    for m in a.modeles:
        for v in a.variantes:
            try:
                ae.carte(m, v, j, items[0]["nom"])
            except FileNotFoundError:
                continue
            f = bc.ECHELLES.get(v, 1.0)
            pk = {}
            for e in items:
                xy, sc = bc.pics(ae.carte(m, v, j, e["nom"]), bc.K_PICS, min(SEUILS), echelle=f)
                g = ae.dans_compte(xy, e) if len(xy) else np.zeros(0, bool)
                pk[e["nom"]] = (xy[g], sc[g])
            for s in SEUILS:
                vp = fp = fn = det = 0
                tr, tt = np.zeros(len(cl)), np.zeros(len(cl))
                for e in items:
                    xy, sc = pk[e["nom"]]
                    d = xy[sc >= s]
                    det += len(d)
                    coup = ae.apparier(d, e["pts"])
                    ret = np.zeros(len(e["pts"]), bool); ret[list(coup.values())] = True
                    n, fpp, mm = bc.compter(d, e["pts"], e["ign"])
                    vp += n; fp += fpp; fn += mm
                    k = np.clip(np.searchsorted(BORNES, e["taille"], side="right") - 1, 0, len(cl) - 1)
                    np.add.at(tt, k, 1); np.add.at(tr, k, ret)
                p, r, f1 = bc.prf(vp, fp, fn)
                out.append(f"| {m} | {v} | {s:.2f} | {f1:.3f} | {p:.3f} | {r:.3f} | {det}/{vp + fn} ({det / (vp + fn):.2f}) | "
                           + " | ".join(f"{tr[k] / tt[k]:.2f}" if tt[k] else "-" for k in range(len(cl))) + " |")
            print(j, m, v, "fait", flush=True)
(ae.SORTIE / a.sortie).write_text("\n".join(out) + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8"); print("\n".join(out))
