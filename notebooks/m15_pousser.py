#!/usr/bin/env python3
"""Envoie le carnet Kaggle privé de M-kaggle (15/11) : soupe de poids des 4 tirages de d3b, sans entraînement.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15_pousser.py [soupe|traits] [--essai]

soupe (14 h 01) : notebooks/m15_soupe_kaggle.py ; traits (14 h 15) : notebooks/m15_traits_kaggle.py (soupes lues dans les sorties de m15-soupe).

Reprend scripts/m14_pousser.py (sans le modifier). Contrôles avant l'envoi :
(1) le dossier d'envoi ne contient que le carnet et kernel-metadata.json (aucune image) ;
(2) le carnet garde les refus des juges (chemins, SHA-256 de test_perou) ;
(3) le contrôle de fuite des outils de M-entraîneur dit « aucun MD5 commun, aucun nom de juge ».
Le jeton Kaggle n'est jamais lu ni affiché ici (kaggle.exe le lit lui-même).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
essai = "--essai" in sys.argv
LOT = ([a for a in sys.argv[1:] if not a.startswith("--")] or ["soupe"])[0]
assert LOT in ("soupe", "traits")
src = (RACINE / f"notebooks/m15_{LOT}_kaggle.py").read_text(encoding="utf-8")
assert 'INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")' in src   # (2)
assert "assert not SHA_JUGES & set(idx.sha256.dropna())" in src
assert "banspot" not in src.replace('INTERDITS = ("banspot"', "")
ctrl = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/controle_fuite_outils.json").read_text(encoding="utf-8"))
assert ctrl["communs"] == [] and ctrl["noms_suspects"] == [], ctrl   # (3)
dossier = RACINE / f"out/maladies/jour_1511/kaggle/envoi/m15_{LOT}"
if dossier.exists():
    shutil.rmtree(dossier)
dossier.mkdir(parents=True)
(dossier / f"m15_{LOT}.py").write_text(src, encoding="utf-8")
jeux = ["affilecorentin/feuilles-pret-perou", "affilecorentin/feuilles-v3-ajouts", "affilecorentin/maladies-nuit",
        "affilecorentin/maladies-v10b-poids", "affilecorentin/maladies-v2-binome", "affilecorentin/feuilles-nuit-1112",
        "affilecorentin/roamer-dev-loin-feuilles", "affilecorentin/m13-entr-outils"]
meta = {"id": f"affilecorentin/m15-{LOT}", "title": f"m15-{LOT}", "code_file": f"m15_{LOT}.py",
        "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": jeux,
        "kernel_sources": ["affilecorentin/m13-lot2p", "affilecorentin/m14-lot1", "affilecorentin/m14-lot2"] if LOT == "soupe" else ["affilecorentin/m15-soupe"],
        "competition_sources": []}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
assert sorted(p.name for p in dossier.iterdir()) == sorted([f"m15_{LOT}.py", "kernel-metadata.json"])   # (1)
print("contrôles avant envoi : OK")
if essai:
    sys.exit(0)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
