#!/usr/bin/env python3
"""Essai 10 en veille (agent C-banc) : surveille out/comptage_v6/kaggle/ ; chaque nouveau modèle centres_5cm_<nom>.onnx
(nom absent de modeles_nuit.json) est déclaré, mis en cache sur le réglage (5 jeux + sans bananier), puis la grille
de l'essai 10 (liste_e10, écrite à 00:40) est mesurée. S'arrête à l'heure --fin (HH:MM, le lendemain si besoin)."""
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
KAGGLE = RACINE / "out/comptage_v6/kaggle"
DECL = RACINE / "out/comptage_v6/banc/modeles_nuit.json"
PY = str(RACINE / ".venv/Scripts/python.exe")
ENV = dict(__import__("os").environ, PYTHONIOENCODING="utf-8")

ap = argparse.ArgumentParser()
ap.add_argument("--fin", default="04:40")
a = ap.parse_args()
h, m = map(int, a.fin.split(":"))
fin = dt.datetime.now().replace(hour=h, minute=m, second=0)
if fin < dt.datetime.now():
    fin += dt.timedelta(days=1)


def journal(s):
    print(f"{time.strftime('%H:%M:%S')} {s}", flush=True)


while dt.datetime.now() < fin:
    decl = json.loads(DECL.read_text(encoding="utf-8")) if DECL.exists() else {}
    nouveaux = {}
    for p in sorted(KAGGLE.rglob("centres_5cm_*.onnx")):
        nom = p.stem.replace("centres_5cm_", "")
        if nom not in decl and nom not in nouveaux and p.stat().st_size > 1e6 and time.time() - p.stat().st_mtime > 60:
            nouveaux[nom] = p.relative_to(RACINE).as_posix()
    if not nouveaux:
        time.sleep(60)
        continue
    journal(f"nouveaux modèles : {nouveaux}")
    decl.update(nouveaux)
    DECL.write_text(json.dumps(decl, indent=1), encoding="utf-8")
    procs = [subprocess.Popen([PY, "-I", "-u", "scripts/v6_banc_cache.py", "--modeles", n, "--groupes", "base", "--jeux",
                               "jeunes", "mm", "plantain", "dense", "btd_val", "neg", "--fils", "3"], cwd=RACINE, env=ENV,
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) for n in nouveaux]
    for p in procs:
        p.wait()
    journal("caches écrits ; mesure de la grille de l'essai 10")
    r = subprocess.run([PY, "-I", "-u", "scripts/v6_banc_essais.py", "--liste", "e10", "--procs", "4", "--affiche", "200"],
                       cwd=RACINE, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (RACINE / "out/comptage_v6/banc/log_essais_e10.txt").write_text(r.stdout + r.stderr, encoding="utf-8")
    journal("essai 10 mesuré : out/comptage_v6/banc/log_essais_e10.txt")
journal("fin de la veille")
