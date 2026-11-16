#!/usr/bin/env python3
"""Envoie le carnet ME3 (lecteur « loin », notebooks/m13_loin_kaggle.py) en carnet Kaggle privé (nuit du 13/11).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_pousser_loin.py <lot> '<recettes JSON>'

Écrit en dur RECETTES et LOIN_PAYS (photos de TDTU et d'Éthiopie dites « loin » par l'aiguilleur, caches
out/maladies/cinq_classes/p_loin_<jeu>.csv, p_loin >= 0,5).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
lot, recettes = sys.argv[1], json.loads(sys.argv[2])
loin = {j: pd.read_csv(RACINE / f"out/maladies/cinq_classes/p_loin_{j}.csv").query("p_loin >= 0.5").chemin.tolist() for j in ("tdtu", "ethiopie")}
src = (RACINE / "notebooks/m13_loin_kaggle.py").read_text(encoding="utf-8")
a, b = 'RECETTES = [dict(nom="l1")]   # remplacé', 'LOIN_PAYS = {}                # remplacé'
assert a in src and b in src
src = src.replace(a, f"RECETTES = {recettes!r}   # remplacé").replace(b, f"LOIN_PAYS = {loin!r}   # remplacé")
dossier = Path(f"C:/Users/coren/kaggle_tmp/m13_{lot}")
dossier.mkdir(parents=True, exist_ok=True)
(dossier / f"m13_{lot}.py").write_text(src, encoding="utf-8")
jeux = ["affilecorentin/feuilles-pret-perou", "affilecorentin/feuilles-v3-ajouts", "affilecorentin/maladies-nuit",
        "affilecorentin/maladies-v10b-poids", "affilecorentin/feuilles-nuit-1112", "affilecorentin/roamer-dev-loin-feuilles",
        "affilecorentin/m13-entr-outils", "affilecorentin/photos-loin", "affilecorentin/maladies-v2-binome"]
meta = {"id": f"affilecorentin/m13-{lot.replace('_', '-')}", "title": f"m13-{lot.replace('_', '-')}", "code_file": f"m13_{lot}.py",
        "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": os.environ.get("MACHINE", "NvidiaTeslaT4"), "dataset_sources": jeux, "kernel_sources": [], "competition_sources": []}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
print({j: len(v) for j, v in loin.items()}, "photos « loin »")
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
