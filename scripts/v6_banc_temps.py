#!/usr/bin/env python3
"""Temps de calcul par hectare (processeur) d'un passage de réseau à 5 cm, par modèle, sur des images de réglage.
Coût d'un candidat = somme des passages qu'il fait (aiguillage p90 : v5 toujours, + v3 + v4 sur les images aiguillées ;
8 symétries : x 8). La machine est partagée cette nuit : chiffres indicatifs, à refaire machine libre."""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402

items = bc.jeu("dense")[:6] + bc.jeu("btd_val")[:6]
res = {}
for m in [m for m in ("v5", "v3", "v4", "v6a", "v6b", "v6c") if m in bc.MODELES]:
    s = bc.session(m)
    t = ha = 0.0
    for e in items:
        x, h, w = bc.entree(bc.lire(e["chemin"]))
        t0 = time.time(); bc._logits(s, x); t += time.time() - t0
        ha += h * w * 0.05 ** 2 / 1e4
    res[m] = t / ha
    print(f"{m} : {t / ha:.1f} s par hectare ({ha:.2f} ha lus)")
print(f"aiguillage p90, image « grands plants » : {res['v5']:.1f} s/ha ; image « petits plants » : {res['v5'] + res['v3'] + res['v4']:.1f} s/ha")
print(f"8 symétries du v5 : {8 * res['v5']:.1f} s/ha")
