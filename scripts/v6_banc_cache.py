#!/usr/bin/env python3
"""Cache des cartes de chaleur (agent C-banc). Exemple :
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/v6_banc_cache.py --modeles v5 --groupes base --jeux dense plantain jeunes mm neg
Les jeux juges (segmento, cg, banano, neg_test) ne sont mis en cache que par scripts/v6_banc_juges.py, à la fin."""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--modeles", nargs="+", default=["v5", "v3", "v4"])
ap.add_argument("--groupes", nargs="+", default=["base", "tta", "ech"])
ap.add_argument("--jeux", nargs="+", default=["dense", "plantain", "jeunes", "mm", "neg_q"])
ap.add_argument("--fils", type=int, default=0)
a = ap.parse_args()
assert not set(a.jeux) & {"segmento", "cg", "banano", "neg_test"}, "les juges ne se mettent pas en cache ici"
for g in a.groupes:
    for j in a.jeux:
        for m in a.modeles:
            t0 = time.time()
            bc.ecrire_cache(m, g, j, a.fils, journal=lambda s: print(s, flush=True))
            print(f"{time.strftime('%H:%M:%S')} cache {m} {g} {j} : {time.time() - t0:.0f} s", flush=True)
