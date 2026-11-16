#!/usr/bin/env python3
"""Renvoie le carnet de traits de M-kaggle (notebooks/m15_traits_kaggle.py, inchangé) sous un autre nom (M-kaggle2, 15/11).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15b_pousser.py [gpu|cpu|tent] [--essai]

gpu : affilecorentin/m15b-traits (T4 × 2) ; cpu : affilecorentin/m15c-traits (processeur Kaggle, aucun GPU) ;
tent : affilecorentin/m15b-tent (piste 3, notebooks/m15b_tent_kaggle.py, règles de 16 h 22 ; contrôle (4) sans objet).
Règles : docs/journee_2026-11-15/journal_m_kaggle2.md (16 h 07). Contrôles avant l'envoi, repris de notebooks/m15_pousser.py :
(1) le dossier d'envoi ne contient que le carnet et kernel-metadata.json (aucune image) ;
(2) le carnet garde les refus des juges (chemins, SHA-256 de test_perou) ;
(3) le contrôle de fuite des outils de M-entraîneur dit « aucun MD5 commun, aucun nom de juge » ;
(4) le code envoyé est octet pour octet celui du premier tour (même SHA-256 que l'envoi m15-traits).
Le jeton Kaggle n'est jamais lu ni affiché ici (kaggle.exe le lit lui-même).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
essai = "--essai" in sys.argv
MODE = ([a for a in sys.argv[1:] if not a.startswith("--")] or ["gpu"])[0]
assert MODE in ("gpu", "cpu", "tent")
NOM = {"gpu": "m15b-traits", "cpu": "m15c-traits", "tent": "m15b-tent"}[MODE]
if MODE == "tent":
    octets = (RACINE / "notebooks/m15b_tent_kaggle.py").read_bytes()
    assert b"X_APPR" not in octets   # aucune image d'apprentissage chargée
else:
    octets = (RACINE / "notebooks/m15_traits_kaggle.py").read_bytes()
    envoi1 = (RACINE / "out/maladies/jour_1511/kaggle/envoi/m15_traits/m15_traits.py").read_bytes()
    assert hashlib.sha256(octets).hexdigest() == hashlib.sha256(envoi1).hexdigest()   # (4)
src = octets.decode("utf-8")
assert 'INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")' in src   # (2)
assert "assert not SHA_JUGES & set(idx.sha256.dropna())" in src
ctrl = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/controle_fuite_outils.json").read_text(encoding="utf-8"))
assert ctrl["communs"] == [] and ctrl["noms_suspects"] == [], ctrl   # (3)
dossier = RACINE / f"out/maladies/jour_1511/kaggle2/envoi/{NOM}"
if dossier.exists():
    shutil.rmtree(dossier)
dossier.mkdir(parents=True)
code = NOM.replace("-", "_") + ".py"
(dossier / code).write_bytes(octets)
meta1 = json.loads((RACINE / "out/maladies/jour_1511/kaggle/envoi/m15_traits/kernel-metadata.json").read_text(encoding="utf-8"))
meta = dict(meta1, id=f"affilecorentin/{NOM}", title=NOM, code_file=code)
if MODE == "cpu":
    meta["enable_gpu"] = False
    meta.pop("machine_shape", None)
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
assert sorted(p.name for p in dossier.iterdir()) == sorted([code, "kernel-metadata.json"])   # (1)
print("contrôles avant envoi : OK", NOM, hashlib.sha256(octets).hexdigest()[:12])
if essai:
    sys.exit(0)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
