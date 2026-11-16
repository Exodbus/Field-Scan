#!/usr/bin/env python3
"""Envoie un carnet Kaggle privé de l'agent M-piste2 (14/11), avec contrôle de fuite avant l'envoi.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m14_pousser.py <lot> '<recettes JSON>' [--essai]

Reprend scripts/m13_entr_pousser.py (M-entraîneur) sans le modifier :
- copie notebooks/m14_entrainer_kaggle.py (copie identique de notebooks/m13_entrainer_kaggle.py) avec MODE et RECETTES
  écrits en dur, dans out/maladies/nuit_1311/piste2/envoi/m14_<lot>/ ;
- kernel-metadata.json : privé, forme P100, mêmes jeux Kaggle privés que M-entraîneur, maître repris de m13-lot1 ;
- contrôles avant l'envoi : (1) la copie ne diffère du carnet m13 que par MODE et RECETTES ; (2) le dossier d'envoi ne
  contient que le carnet et kernel-metadata.json (aucune image) ; (3) le contrôle de fuite des outils de M-entraîneur dit
  « aucun MD5 commun, aucun nom de juge » ; (4) le carnet garde ses refus (chemins de juges, SHA-256 de test_perou).
--essai : contrôles seulement, pas d'envoi. Le jeton Kaggle n'est jamais lu ni affiché ici (kaggle.exe le lit lui-même).
"""
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
lot, recettes = args[0], json.loads(args[1])
essai = "--essai" in sys.argv
m13 = (RACINE / "notebooks/m13_entrainer_kaggle.py").read_text(encoding="utf-8")
m14 = (RACINE / "notebooks/m14_entrainer_kaggle.py").read_text(encoding="utf-8")
assert m13 == m14, "notebooks/m14_entrainer_kaggle.py doit rester une copie identique du carnet m13"
a, b = 'MODE = "plis"            # remplacé', 'RECETTES = [dict(nom="d1")]   # remplacé'
assert a in m14 and b in m14
src = m14.replace(a, 'MODE = "plis"   # remplacé').replace(b, f"RECETTES = {recettes!r}   # remplacé")
diff = [l for l in difflib.unified_diff(m13.splitlines(), src.splitlines(), lineterm="", n=0)
        if l[:1] in "+-" and not l.startswith(("+++", "---"))]
assert len(diff) == 4 and all(("MODE =" in l or "RECETTES =" in l) for l in diff), diff   # (1)
assert 'INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")' in src   # (4)
assert "assert not SHA_JUGES & set(idx.sha256.dropna())" in src
ctrl = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/controle_fuite_outils.json").read_text(encoding="utf-8"))
assert ctrl["communs"] == [] and ctrl["noms_suspects"] == [], ctrl   # (3)
for R in recettes:
    assert not any(s in json.dumps(R).lower() for s in ("banspot", "perou", "test")), R
dossier = RACINE / "out/maladies/nuit_1311/piste2/envoi" / f"m14_{lot}"
dossier.mkdir(parents=True, exist_ok=True)
for f in dossier.iterdir():
    f.unlink()
(dossier / f"m14_{lot}.py").write_text(src, encoding="utf-8")
jeux = ["affilecorentin/feuilles-pret-perou", "affilecorentin/feuilles-v3-ajouts", "affilecorentin/maladies-nuit",
        "affilecorentin/maladies-v10b-poids", "affilecorentin/maladies-v2-binome", "affilecorentin/feuilles-nuit-1112",
        "affilecorentin/roamer-dev-loin-feuilles", "affilecorentin/m13-entr-outils"]
meta = {"id": f"affilecorentin/m14-{lot.replace('_', '-')}", "title": f"m14-{lot.replace('_', '-')}", "code_file": f"m14_{lot}.py",
        "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaP100", "dataset_sources": jeux, "kernel_sources": ["affilecorentin/m13-lot1"],
        "competition_sources": []}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
assert sorted(p.name for p in dossier.iterdir()) == sorted([f"m14_{lot}.py", "kernel-metadata.json"])   # (2)
print("contrôles avant envoi : OK ;", len(diff), "lignes changées (MODE, RECETTES) ; recettes :", [r["nom"] for r in recettes])
if essai:
    sys.exit(0)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
