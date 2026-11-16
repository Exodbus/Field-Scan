#!/usr/bin/env python3
"""Récupère les sorties d'un carnet Kaggle de M-entraîneur (nuit du 13/11) dans out/maladies/nuit_1311/kaggle/<lot>/.
Les fichiers du maître (maitre_*.npz) vont dans out/maladies/nuit_1311/kaggle/maitre/, les poids (*.pt) dans
modeles/maladies_nuit_1311/<lot>/ (jamais commités).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_recuperer.py <lot>
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
lot = sys.argv[1]
KAG = RACINE / "out/maladies/nuit_1311/kaggle"
dos = KAG / lot
dos.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", f"affilecorentin/m13-{lot.replace('_', '-')}",
                    "-p", str(dos), "-o"], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout[-800:], r.stderr[-800:])
(KAG / "maitre").mkdir(exist_ok=True)
for f in dos.glob("maitre_*.npz"):
    shutil.move(str(f), KAG / "maitre" / f.name)
pts = list(dos.glob("*.pt"))
if pts:
    m = RACINE / "modeles/maladies_nuit_1311" / lot
    m.mkdir(parents=True, exist_ok=True)
    for f in pts:
        shutil.move(str(f), m / f.name)
print(sorted(p.name for p in dos.iterdir()))
