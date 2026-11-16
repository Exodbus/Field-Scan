#!/usr/bin/env python3
"""Copie c16 (16/11) de notebooks/c15b_recuperer.py (seuls les dossiers changent : out/comptage/jour_1611/, modeles/comptage_jour_1611/).
Récupère les sorties d'un carnet Kaggle (agent C-kaggle, 15/11) et les range dans mes dossiers.
Copie adaptée de scripts/c14_recuperer.py : sorties brutes -> out/comptage/jour_1611/sorties/<slug>/ ;
ONNX, json, .pt -> modeles/comptage_jour_1511/ ; journaux et json -> out/comptage/jour_1511/kaggle/<slug>/.
Le jeton n'est jamais lu ni affiché.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c15_recuperer.py c14-lot2
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
slug = sys.argv[1]
dossier = RACINE / f"out/comptage/jour_1611/sorties/{slug}"
dossier.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "output", f"affilecorentin/{slug}",
                "-p", str(dossier), "-o"], env=env, check=False)
modeles = RACINE / "modeles/comptage_jour_1611"; modeles.mkdir(parents=True, exist_ok=True)
out = RACINE / "out/comptage/jour_1611" / slug; out.mkdir(parents=True, exist_ok=True)
noms = []
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
            noms.append(p.name)
for n in sorted(noms):
    d = json.loads((modeles / n).read_text(encoding="utf-8"))
    r = d.get("retenu", {})
    deg = d.get("degrade", {})
    print(n, "seuil", d.get("seuil"), "moyenne", r.get("moyenne"), "4 anciennes", r.get("moyenne_4_v5"), "err", r.get("erreur_compte"),
          "fp_neg", r.get("fp_neg"), "| 11 cm :", {k: v.get("moyenne") for k, v in deg.items()}, "| écart ONNX", d.get("ecart_onnx"))
