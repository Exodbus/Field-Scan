#!/usr/bin/env python3
"""Essai Kaggle A1 : envoi du carnet `affilecorentin/a1-lot1` (avenant docs/journee_2026-11-16/avenant_a1_kaggle.md, §3).

Contrôles avant l'envoi (repris de scripts/m14_pousser.py, sans le modifier) :
  (1) notebooks/a1_entrainer_kaggle.py ne diffère de notebooks/m13_entrainer_kaggle.py que par les changements de
      l'avenant (refus d'un maître neuf, bloc A1-appr, pli « sans TDTU » sans plantvillage_psu), plus MODE et RECETTES ;
  (2) le dossier d'envoi ne contient que le carnet et kernel-metadata.json (aucune image) ;
  (3) le contrôle de fuite des outils de M-entraîneur dit « aucun MD5 commun, aucun nom de juge » ;
  (4) le carnet garde ses refus (chemins de juges, SHA-256 de test_perou) ;
  (5) recettes = recette de d3b à l'identique, sauf `nom` et `graine` (0 à 3).
--essai : contrôles seulement. Le jeton Kaggle n'est jamais lu ni affiché ici (kaggle.exe le lit lui-même).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/a1_kaggle_pousser.py [--essai]
"""
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
essai = "--essai" in sys.argv
m13 = (RACINE / "notebooks/m13_entrainer_kaggle.py").read_text(encoding="utf-8")
a1 = (RACINE / "notebooks/a1_entrainer_kaggle.py").read_text(encoding="utf-8")
d3b = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/lot2p/recette_d3b.json").read_text(encoding="utf-8"))
d3b.pop("mode")
recettes = [{**d3b, "nom": f"a1g{g}", "graine": g} for g in range(4)]
assert all({k: v for k, v in r.items() if k not in ("nom", "graine")} == {k: v for k, v in d3b.items() if k not in ("nom", "graine")}
           for r in recettes)   # (5)
a, b = 'MODE = "plis"            # remplacé', 'RECETTES = [dict(nom="d1")]   # remplacé'
assert a in a1 and b in a1
src = a1.replace(a, 'MODE = "plis"   # remplacé').replace(b, f"RECETTES = {recettes!r}   # remplacé")
diff = [l for l in difflib.unified_diff(m13.splitlines(), src.splitlines(), lineterm="", n=0)
        if l[:1] in "+-" and not l.startswith(("+++", "---"))]
moins = [l for l in diff if l.startswith("-")]
plus = [l for l in diff if l.startswith("+")]
assert len(moins) == 3 and all(("MODE =" in l or "RECETTES =" in l or "appr.pays.isin([x] + retires)" in l) for l in moins), moins
assert len(plus) == 3 + 1 + 20, len(plus)   # MODE, RECETTES, pli ; refus du maître neuf ; bloc A1 (20 lignes)   (1)
assert 'INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")' in src   # (4)
assert "assert not SHA_JUGES & set(idx.sha256.dropna())" in src
ctrl = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/controle_fuite_outils.json").read_text(encoding="utf-8"))
assert ctrl["communs"] == [] and ctrl["noms_suspects"] == [], ctrl   # (3)
dossier = RACINE / "out/jeux_neufs_1611/a1_kaggle/envoi_carnet"
dossier.mkdir(parents=True, exist_ok=True)
for f in dossier.iterdir():
    f.unlink()
(dossier / "a1_lot1.py").write_text(src, encoding="utf-8")
jeux = ["affilecorentin/feuilles-pret-perou", "affilecorentin/feuilles-v3-ajouts", "affilecorentin/maladies-nuit",
        "affilecorentin/maladies-v10b-poids", "affilecorentin/maladies-v2-binome", "affilecorentin/feuilles-nuit-1112",
        "affilecorentin/roamer-dev-loin-feuilles", "affilecorentin/m13-entr-outils", "affilecorentin/a1-appr-224"]
meta = {"id": "affilecorentin/a1-lot1", "title": "a1-lot1", "code_file": "a1_lot1.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": jeux, "kernel_sources": ["affilecorentin/m13-lot1"],
        "competition_sources": []}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
assert sorted(p.name for p in dossier.iterdir()) == ["a1_lot1.py", "kernel-metadata.json"]   # (2)
print("contrôles avant envoi : OK ;", len(diff), "lignes changées ; recettes :", [(r["nom"], r["graine"]) for r in recettes])
if essai:
    sys.exit(0)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
