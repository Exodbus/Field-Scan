#!/usr/bin/env python3
"""Temps de bout en bout (lecture de l'image, carte ONNX, pics) des candidats C-kaggle2 contre le v5, ENTRELACÉS tuile
par tuile, 2 fils, comme scripts/juge_1511_c_temps.py (25 tuiles régulièrement espacées de dense et de val_negatifs,
RÉGLAGE seulement). Information, ne change pas la règle.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c15b_temps.py c15b_a c15b_b
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import numpy as np  # noqa: E402
import v6_banc_commun as bc  # noqa: E402

N, FILS = 25, 2


def main():
    noms = sys.argv[1:]
    for n in noms:
        bc.MODELES[n] = RACINE / f"modeles/comptage_jour_1511/centres_5cm_{n}.onnx"
    s = {m: bc.session(m, FILS) for m in ["v5"] + noms}
    res = {}
    for j in ["dense", "neg"]:
        items = bc.jeu(j)
        items = [items[i] for i in np.linspace(0, len(items) - 1, N).astype(int)]
        for m in s:
            bc.cartes_image(s[m], bc.lire(items[0]["chemin"]), "base")          # chauffe
        t = {m: 0.0 for m in s}
        for e in items:
            for m in s:
                t0 = time.perf_counter()
                img = bc.lire(e["chemin"])
                bc.pics(bc.cartes_image(s[m], img, "base")["base"])
                t[m] += time.perf_counter() - t0
        res[j] = {k: dict(s_par_tuile=round(v / N, 4), rapport_v5=round(v / t["v5"], 3)) for k, v in t.items()}
        print(j, json.dumps(res[j]), flush=True)
    res.update(fils=FILS, n=N, heure=time.strftime("%H:%M"))
    (RACINE / "out/comptage/jour_1511/kaggle2/temps.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
