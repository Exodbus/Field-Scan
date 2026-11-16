#!/usr/bin/env python3
"""Récupère les sorties de mon propre carnet Kaggle c14-<lot> (agent C-piste2, 14/11) et les range.
Copie de scripts/c13_entr_recuperer.py (C-entraîneur), avec mes dossiers :
sorties brutes -> out/comptage/nuit_1311/piste2/kaggle_envoi/c14_<lot>/sortie ; ONNX, json, .pt -> modeles/comptage_nuit_1411/ ;
journaux, console, reglage*.csv, json -> out/comptage/nuit_1311/piste2/kaggle/<lot>/. Le jeton n'est jamais lu ni affiché.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c14_recuperer.py lot1
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
lot = sys.argv[1]
dossier = RACINE / f"out/comptage/nuit_1311/piste2/kaggle_envoi/c14_{lot}/sortie"
dossier.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", f"affilecorentin/c14-{lot.replace('_', '-')}",
                "-p", str(dossier), "-o"], env=env, check=False)
modeles = RACINE / "modeles/comptage_nuit_1411"; modeles.mkdir(parents=True, exist_ok=True)
out = RACINE / "out/comptage/nuit_1311/piste2/kaggle" / lot; out.mkdir(parents=True, exist_ok=True)
for p in dossier.rglob("*"):
    if not p.is_file():
        continue
    if p.suffix in (".onnx", ".pt"):
        shutil.copy2(p, modeles / p.name)
    if p.suffix in (".json", ".csv", ".txt", ".log"):
        cible = out / p.relative_to(dossier)
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, cible)
        if p.name.startswith("centres_5cm_") and p.suffix == ".json":
            shutil.copy2(p, modeles / p.name)
for j in sorted(modeles.glob("centres_5cm_*.json")):
    d = json.loads(j.read_text(encoding="utf-8"))
    r = d.get("retenu", {})
    deg = d.get("degrade", {})
    print(j.stem, "seuil", d.get("seuil"), "moyenne", r.get("moyenne"), "4 anciennes", r.get("moyenne_4_v5"), "err", r.get("erreur_compte"),
          "fp_neg", r.get("fp_neg"), "| 11 cm :", {k: v.get("moyenne") for k, v in deg.items()}, "| écart ONNX", d.get("ecart_onnx"))
