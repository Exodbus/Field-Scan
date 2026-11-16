#!/usr/bin/env python3
"""Envoie un lot de recettes sur Kaggle (carnet privé), agent C-piste2, 14/11.
Copie de scripts/c13_entr_pousser.py (C-entraîneur), avec le slug c14-<lot>, les carnets notebooks/c14_*.py (copies
exactes des carnets c13) et le dossier d'envoi dans out/comptage/nuit_1311/piste2/kaggle_envoi/. Contrôle de fuite
gardé : aucune recette ne cite un juge ; le code de travail retire les ensembles test_* et cg/ par assert.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c14_pousser.py <lot> '<recettes JSON>' [jeux Kaggle en plus]

Machine : C14_MACHINE (NvidiaTeslaP100 par défaut). Le jeton n'est jamais lu ni affiché par ce script.
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
travail = (RACINE / "notebooks" / "c14_travail_centres.py").read_bytes()
src = (RACINE / "notebooks" / "c14_lanceur_kaggle.py").read_text(encoding="utf-8")
a, b = "RECETTES = []   # remplacé", 'SOURCE_B64 = ""   # remplacé'
assert a in src and b in src
src = src.replace(a, f"RECETTES = {recettes!r}   # remplacé").replace(
    b, f'SOURCE_B64 = "{base64.b64encode(travail).decode()}"   # remplacé')
src = src.replace("PLACES_DEFAUT = 3", f"PLACES_DEFAUT = {int(os.environ.get('V6_PLACES', '3'))}")
for interdit in ("banana_trees_kp", "test_dense", "test_banano", "test_negatifs", "test_espace", "juge", "segmento", "/cg"):
    assert all(interdit not in json.dumps(r) for r in recettes), f"recette qui cite un juge : {interdit}"
for j in en_plus:
    assert not any(x in j for x in ("banana-trees-kp", "banana_trees_kp", "juge", "test")), f"jeu refusé : {j}"
dossier = RACINE / f"out/comptage/nuit_1311/piste2/kaggle_envoi/c14_{lot}"
dossier.mkdir(parents=True, exist_ok=True)
(dossier / f"c14_{lot}.py").write_text(src, encoding="utf-8")
slug = f"c14-{lot.replace('_', '-')}"
meta = {"id": f"affilecorentin/{slug}", "title": slug, "code_file": f"c14_{lot}.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": ["affilecorentin/comptage-v6-5cm"] + en_plus,
        "kernel_sources": [], "competition_sources": [],
        "machine_shape": os.environ.get("C14_MACHINE", "NvidiaTeslaP100")}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
