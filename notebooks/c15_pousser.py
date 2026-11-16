#!/usr/bin/env python3
"""Envoie un lot de recettes sur Kaggle (carnet privé), agent C-kaggle, 15/11.
Copie de scripts/c14_pousser.py, avec le slug c15-<lot>, les carnets notebooks/c15_*.py, le dossier d'envoi
out/comptage/jour_1511/kaggle/envoi/ et des sorties de carnets en entrée (kernel_sources). Contrôle de fuite gardé :
aucune recette ni aucune entrée ne cite un juge ; le code de travail retire les ensembles test_* et cg/ par assert.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c15_pousser.py <lot> '<recettes JSON>' <jeux en plus> <carnets en entrée>

Machine : NvidiaTeslaT4 (2 GPU). Le jeton n'est jamais lu ni affiché par ce script.
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
carnets = [j for j in (sys.argv[4].split(",") if len(sys.argv) > 4 else []) if j]
travail = (RACINE / "notebooks" / "c15_travail_centres.py").read_bytes()
src = (RACINE / "notebooks" / "c15_lanceur_kaggle.py").read_text(encoding="utf-8")
a, b = "RECETTES = []   # remplacé", 'SOURCE_B64 = ""   # remplacé'
assert a in src and b in src
src = src.replace(a, f"RECETTES = {recettes!r}   # remplacé").replace(
    b, f'SOURCE_B64 = "{base64.b64encode(travail).decode()}"   # remplacé')
src = src.replace("PLACES_DEFAUT = 3", f"PLACES_DEFAUT = {int(os.environ.get('V6_PLACES', '2'))}")
for interdit in ("banana_trees_kp", "test_dense", "test_banano", "test_negatifs", "test_espace", "juge", "segmento", "/cg"):
    assert all(interdit not in json.dumps(r) for r in recettes), f"recette qui cite un juge : {interdit}"
for j in en_plus + carnets:
    assert not any(x in j for x in ("banana-trees-kp", "banana_trees_kp", "juge", "test", "banano-dense", "segmento")), f"entrée refusée : {j}"
dossier = RACINE / f"out/comptage/jour_1511/kaggle/envoi/c15_{lot}"
dossier.mkdir(parents=True, exist_ok=True)
(dossier / f"c15_{lot}.py").write_text(src, encoding="utf-8")
slug = f"c15-{lot.replace('_', '-')}"
meta = {"id": f"affilecorentin/{slug}", "title": slug, "code_file": f"c15_{lot}.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": ["affilecorentin/comptage-v6-5cm"] + en_plus,
        "kernel_sources": carnets, "competition_sources": [],
        "machine_shape": "NvidiaTeslaT4"}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
