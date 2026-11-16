#!/usr/bin/env python3
"""Envoie un carnet Kaggle privé de l'agent M-entraîneur (nuit du 13/11).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_pousser.py <lot> <mode> '<recettes JSON>' [carnet_source_kaggle]

Copie notebooks/m13_entrainer_kaggle.py dans C:/Users/coren/kaggle_tmp/m13_<lot>/ avec MODE et RECETTES écrits en dur,
écrit kernel-metadata.json (privé, GPU T4) et lance `kaggle kernels push`. carnet_source_kaggle (facultatif) : sorties d'un
carnet précédent (maitre_appr.npz) fournies en entrée, pour ne pas recalculer le maître.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
lot, mode, recettes = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
source = sys.argv[4] if len(sys.argv) > 4 else None
carnet = os.environ.get("CARNET", "m13_entrainer_kaggle.py")
jeux = ["affilecorentin/feuilles-pret-perou", "affilecorentin/feuilles-v3-ajouts", "affilecorentin/maladies-nuit",
        "affilecorentin/maladies-v10b-poids", "affilecorentin/maladies-v2-binome", "affilecorentin/feuilles-nuit-1112",
        "affilecorentin/roamer-dev-loin-feuilles", "affilecorentin/m13-entr-outils"]
src = (RACINE / "notebooks" / carnet).read_text(encoding="utf-8")
a, b = 'MODE = "plis"            # remplacé', 'RECETTES = [dict(nom="d1")]   # remplacé'
assert a in src and b in src
src = src.replace(a, f"MODE = {mode!r}   # remplacé").replace(b, f"RECETTES = {recettes!r}   # remplacé")
dossier = Path(f"C:/Users/coren/kaggle_tmp/m13_{lot}")
dossier.mkdir(parents=True, exist_ok=True)
(dossier / f"m13_{lot}.py").write_text(src, encoding="utf-8")
meta = {"id": f"affilecorentin/m13-{lot.replace('_', '-')}", "title": f"m13-{lot.replace('_', '-')}", "code_file": f"m13_{lot}.py",
        "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": os.environ.get("MACHINE", "NvidiaTeslaT4"), "dataset_sources": jeux, "kernel_sources": [source] if source else [],
        "competition_sources": []}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
