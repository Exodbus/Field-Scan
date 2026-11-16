#!/usr/bin/env python3
"""Envoie un lot de recettes CE1 / CE2 sur Kaggle (carnet privé, T4 x 2), agent C-entraîneur, nuit du 13/11.
Repris de scripts/v6_entr_pousser.py (nuit du 12/11).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/c13_entr_pousser.py <lot> '<recettes JSON>' [jeux Kaggle en plus, séparés par des virgules]

Écrit C:/Users/coren/kaggle_tmp/c13_<lot>/c13_<lot>.py (lanceur + code de travail en base64) et kernel-metadata.json,
puis `kaggle kernels push`. Le jeton n'est jamais lu ni affiché par ce script.
"""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
lot, recettes = sys.argv[1], json.loads(sys.argv[2])
en_plus = [j for j in (sys.argv[3].split(",") if len(sys.argv) > 3 else []) if j]
carnets = [j for j in (sys.argv[4].split(",") if len(sys.argv) > 4 else []) if j]   # sorties de carnets précédents (poids)
cpu = os.environ.get("V6_CPU") == "1"            # carnet sans GPU (soupes, mesures) : ne prend pas de place GPU
travail = (RACINE / "notebooks" / "c13_travail_centres.py").read_bytes()
src = (RACINE / "notebooks" / "c13_lanceur_kaggle.py").read_text(encoding="utf-8")
a, b = "RECETTES = []   # remplacé", 'SOURCE_B64 = ""   # remplacé'
assert a in src and b in src
src = src.replace(a, f"RECETTES = {recettes!r}   # remplacé").replace(
    b, f'SOURCE_B64 = "{base64.b64encode(travail).decode()}"   # remplacé')
src = src.replace("PLACES_DEFAUT = 3", f"PLACES_DEFAUT = {int(os.environ.get('V6_PLACES', '3'))}")
for interdit in ("banana_trees_kp", "test_dense", "test_banano", "test_negatifs", "juge_c"):
    assert all(interdit not in json.dumps(r) for r in recettes), f"recette qui cite un juge : {interdit}"
dossier = Path(f"C:/Users/coren/kaggle_tmp/c13_{lot}")
dossier.mkdir(parents=True, exist_ok=True)
(dossier / f"c13_{lot}.py").write_text(src, encoding="utf-8")
slug = f"c13-{lot.replace('_', '-')}"
meta = {"id": f"affilecorentin/{slug}", "title": slug, "code_file": f"c13_{lot}.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": not cpu, "enable_internet": True,
        "dataset_sources": ["affilecorentin/comptage-v6-5cm"] + en_plus,
        "kernel_sources": carnets, "competition_sources": []}
if not cpu:
    meta["machine_shape"] = os.environ.get("C13_MACHINE", "NvidiaTeslaT4")   # NvidiaTeslaP100 si les T4 sont en file
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
