#!/usr/bin/env python3
"""Cartes de chaleur des jeux de réglage absents du cache de C-banc (agent C-analyste), dans out/comptage/analyse/cache/.
Même calcul que scripts/v6_banc_commun.py (cartes_image), 3 fils onnxruntime. Jamais les juges.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/v6_analyse_cache.py --modeles v5 v3 --groupe base --jeu btd_val
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import v6_analyse_erreurs as ae  # noqa: E402

bc = ae.bc
ap = argparse.ArgumentParser()
ap.add_argument("--modeles", nargs="+", default=["v5", "v3"])
ap.add_argument("--groupe", default="base")
ap.add_argument("--jeu", required=True)
ap.add_argument("--fils", type=int, default=3)
a = ap.parse_args()
assert a.jeu not in ae.INTERDITS
ae.CACHE_A.mkdir(parents=True, exist_ok=True)
items = ae.items_complets(a.jeu) if a.jeu != "neg" else bc.jeu("neg")
for m in a.modeles:
    variantes = bc.VARIANTES[a.groupe]
    if all((ae.CACHE_A / f"{m}_{v}_{a.jeu}.json").exists() or bc.chemin_cache(m, v, a.jeu).with_suffix(".json").exists()
           for v in variantes):
        print("déjà en cache", m, a.groupe, a.jeu, flush=True)
        continue
    sess = bc.session(m, a.fils)
    blocs, index, pos = {v: [] for v in variantes}, {v: {} for v in variantes}, {v: 0 for v in variantes}
    t0 = time.time()
    for n, e in enumerate(items):
        for v, c in bc.cartes_image(sess, bc.lire(e["chemin"]), a.groupe).items():
            blocs[v].append(c.ravel()); index[v][e["nom"]] = [pos[v], c.shape[0], c.shape[1]]; pos[v] += c.size
        if n % 50 == 0:
            print(f"{time.strftime('%H:%M:%S')} {m} {a.groupe} {a.jeu} {n}/{len(items)}", flush=True)
    for v in variantes:
        q = ae.CACHE_A / f"{m}_{v}_{a.jeu}"
        np.concatenate(blocs[v]).astype("float32").tofile(q.with_suffix(".f32"))
        q.with_suffix(".json").write_text(json.dumps(index[v]), encoding="utf-8")
    print(f"{time.strftime('%H:%M:%S')} {m} {a.groupe} {a.jeu} fini en {time.time() - t0:.0f} s", flush=True)
