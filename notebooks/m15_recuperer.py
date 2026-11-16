#!/usr/bin/env python3
"""Récupère les sorties du carnet Kaggle m15-soupe (M-kaggle, 15/11) et fait les contrôles :
- probabilités dans out/maladies/jour_1511/kaggle/lot_soupe/, soupes (*.pt) dans modeles/maladies_jour_1511/s4/
  (avec une copie de seuils.json de d3b, format de la v10b ; jamais commités) ;
- SHA-256 des 8 poids lus par le carnet = SHA-256 des fichiers locaux des graines ;
- d3b relu sur Kaggle (pli sans TDTU, validation) = probabilités de lot2p (écart maximal).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15_recuperer.py
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
dos = RACINE / "out/maladies/jour_1511/kaggle/lot_soupe"
dos.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
if "--sans-telechargement" not in sys.argv:
    r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", "affilecorentin/m15-soupe", "-p", str(dos), "-o"],
                       env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-600:], r.stderr[-600:])
mod = RACINE / "modeles/maladies_jour_1511/s4"
mod.mkdir(parents=True, exist_ok=True)
for f in dos.glob("*.pt"):
    shutil.move(str(f), mod / f.name)
shutil.copy(RACINE / "modeles/maladies_nuit_1311/d3b/seuils.json", mod / "seuils.json")
ctrl = {}
# SHA-256 lus par le carnet contre fichiers locaux
log = next(dos.glob("*.log")).read_text(encoding="utf-8", errors="replace")
locaux = {p.name: p for d in ("modeles/maladies_nuit_1311/d3b", "modeles/maladies_nuit_1411/lot1", "modeles/maladies_nuit_1411/lot2")
          for p in (RACINE / d).glob("*.pt")}
vus = dict(re.findall(r"(maladies_m13\w+?\.pt) sha256 ([0-9a-f]{64})", log))
ctrl["sha_identiques"] = {n: hashlib.sha256(locaux[n].read_bytes()).hexdigest() == h for n, h in vus.items()}
ctrl["nb_poids_lus"] = len(vus)
# d3b relu
a = pd.read_csv(dos / "controle_d3b_validation_pli_tdtu.csv").set_index("chemin")
b = pd.read_csv(RACINE / "out/maladies/nuit_1311/kaggle/lot2p/predictions_d3b_validation_pli_tdtu.csv").set_index("chemin")
cols = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]
ctrl["d3b_relu_ecart_max"] = float((a.loc[b.index, cols] - b[cols]).abs().max().max())
ctrl["soupes"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(mod.glob("*.pt"))}
print(json.dumps(ctrl, indent=1))
(RACINE / "out/maladies/jour_1511/kaggle/controle_soupe.json").write_text(json.dumps(ctrl, indent=1), encoding="utf-8")
print(sorted(p.name for p in dos.iterdir()))
