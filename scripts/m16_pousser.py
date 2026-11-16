#!/usr/bin/env python3
"""Essai m16 (basse résolution) : envoi du carnet `affilecorentin/m16-lot1`
(avenant docs/journee_2026-11-16/avenant_m16_basse_resolution.md, §2).

Contrôles avant l'envoi (repris de scripts/a1_kaggle_pousser.py, sans le modifier) :
  (0) l'avenant a toujours l'empreinte de empreinte_avenant_m16.txt ;
  (1) notebooks/m16_entrainer_kaggle.py ne diffère de notebooks/m13_entrainer_kaggle.py que par (a) MODE et RECETTES,
      (b) ReduitJPEG (DEFAUT, classe, insertion en tête), (c) le refus d'un maître neuf, (d) le garde-fou de 105 min ;
  (2) le dossier d'envoi ne contient que le carnet et kernel-metadata.json (aucune image) ;
  (3) le contrôle de fuite des outils de M-entraîneur dit « aucun MD5 commun, aucun nom de juge » ;
  (4) le carnet garde ses refus (chemins de juges, SHA-256 de test_perou) ;
  (5) recettes = recette de d3b à l'identique, sauf `nom`, `graine` (0 à 3) et les clés de ReduitJPEG (p 0,4 ; 64-128 ; 50-90).
--essai : contrôles seulement. Le jeton Kaggle n'est jamais lu ni affiché ici (kaggle.exe le lit lui-même).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m16_pousser.py [--essai]
"""
import difflib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
essai = "--essai" in sys.argv
AV = RACINE / "docs/journee_2026-11-16/avenant_m16_basse_resolution.md"
emp = (RACINE / "docs/journee_2026-11-16/empreinte_avenant_m16.txt").read_text(encoding="utf-8").split()[0]
assert hashlib.sha256(AV.read_bytes()).hexdigest() == emp, "avenant modifié depuis son empreinte"   # (0)
m13 = (RACINE / "notebooks/m13_entrainer_kaggle.py").read_text(encoding="utf-8")
m16 = (RACINE / "notebooks/m16_entrainer_kaggle.py").read_text(encoding="utf-8")
d3b = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/lot2p/recette_d3b.json").read_text(encoding="utf-8"))
d3b.pop("mode")
AJOUT = dict(reduit_jpeg=0.4, reduit_cote=(64, 128), reduit_qualite=(50, 90))
recettes = [{**d3b, **AJOUT, "nom": f"m16g{g}", "graine": g} for g in range(4)]
FIXES = ("nom", "graine") + tuple(AJOUT)
assert all({k: v for k, v in r.items() if k not in FIXES} == {k: v for k, v in d3b.items() if k not in FIXES}
           for r in recettes)   # (5)
assert not set(AJOUT) & set(d3b)
a, b = 'MODE = "plis"            # remplacé', 'RECETTES = [dict(nom="d1")]   # remplacé'
assert a in m16 and b in m16
src = m16.replace(a, 'MODE = "plis"   # remplacé').replace(b, f"RECETTES = {recettes!r}   # remplacé")
diff = [l for l in difflib.unified_diff(m13.splitlines(), src.splitlines(), lineterm="", n=0)
        if l[:1] in "+-" and not l.startswith(("+++", "---"))]
moins = [l[1:] for l in diff if l.startswith("-")]
plus = [l[1:] for l in diff if l.startswith("+")]
assert len(moins) == 2 and all(("MODE =" in l or "RECETTES =" in l) for l in moins), moins
# (1) lignes ajoutées attendues : MODE, RECETTES ; (b) DEFAUT.update, classe ReduitJPEG (9 lignes + 2 vides), insertion ;
# (c) refus du maître neuf ; (d) garde-fou
attendu_debut = ["MODE =", "RECETTES =", "DEFAUT.update(reduit_jpeg=0.0", 'assert MAITRE_PRET, "m16', "class ReduitJPEG:",
                 '    """m16 (avenant', "    dans `qualite`", "    def __init__(self, p, cote, qualite)", "    def __call__(self, image):",
                 "        if random.random() >= self.p", "        w, h = image.size; c = random.randint(*self.cote)",
                 "        t = io.BytesIO(); image.resize((c, c)", '        return Image.open(t).convert("RGB").resize((w, h)',
                 "", "", '    if R["reduit_jpeg"] > 0: tr.insert(0, ReduitJPEG(', "            assert time.time() - T0 < 105 * 60"]
reste = list(plus)
for deb in attendu_debut:
    k = next((i for i, l in enumerate(reste) if (l.startswith(deb) if deb else l == "")), None)
    assert k is not None, ("ligne attendue absente", deb)
    reste.pop(k)
assert not reste, ("lignes en trop", reste)
assert 'INTERDITS = ("banspot", "cordana_perou", "test_perou", "sig_per", "symptomatic")' in src   # (4)
assert "assert not SHA_JUGES & set(idx.sha256.dropna())" in src
ctrl = json.loads((RACINE / "out/maladies/nuit_1311/kaggle/controle_fuite_outils.json").read_text(encoding="utf-8"))
assert ctrl["communs"] == [] and ctrl["noms_suspects"] == [], ctrl   # (3)
compile(src, "m16_lot1.py", "exec")
dossier = RACINE / "out/maladies/jour_1611/m16/envoi_carnet"
dossier.mkdir(parents=True, exist_ok=True)
for f in dossier.iterdir():
    f.unlink()
(dossier / "m16_lot1.py").write_text(src, encoding="utf-8")
jeux = ["affilecorentin/feuilles-pret-perou", "affilecorentin/feuilles-v3-ajouts", "affilecorentin/maladies-nuit",
        "affilecorentin/maladies-v10b-poids", "affilecorentin/maladies-v2-binome", "affilecorentin/feuilles-nuit-1112",
        "affilecorentin/roamer-dev-loin-feuilles", "affilecorentin/m13-entr-outils"]
meta = {"id": "affilecorentin/m16-lot1", "title": "m16-lot1", "code_file": "m16_lot1.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": jeux, "kernel_sources": ["affilecorentin/m13-lot1"],
        "competition_sources": []}
(dossier / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
assert sorted(p.name for p in dossier.iterdir()) == ["kernel-metadata.json", "m16_lot1.py"]   # (2)
print("contrôles avant envoi : OK ;", len(diff), "lignes changées ; recettes :", [(r["nom"], r["graine"]) for r in recettes])
if essai:
    sys.exit(0)
env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
           SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
sys.exit(subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "kernels", "push", "-p", str(dossier)], env=env).returncode)
