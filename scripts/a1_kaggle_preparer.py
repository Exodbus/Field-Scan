#!/usr/bin/env python3
"""Essai Kaggle A1 : jeu privé `affilecorentin/a1-appr-224` (avenant docs/journee_2026-11-16/avenant_a1_kaggle.md, §1).

Seules les 200 photos d'A1-appr partent. Contrôles :
  (1) rôle final `A1-appr` dans out/jeux_neufs_1611/a1_roles_finaux.csv, 200 photos ;
  (2) SHA-256 de chaque original recalculé et comparé à `manifeste.csv` ; aucun n'est dans A1-test
      (`a1_test_liste.csv`) ni parmi les 24 retirées ;
  (3) le dossier d'envoi ne contient que les 200 PNG, `a1_appr.csv` et `dataset-metadata.json`.
Préparation identique au carnet (preparer(chemin, 224, 448)) : tableau uint8 enregistré en PNG sans perte.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/a1_kaggle_preparer.py [--envoyer]
"""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")
OUT = RACINE / "out/jeux_neufs_1611"
SRC = RACINE / "data/raw/plantvillage_psu/extrait/bxw-leaf"
DOS = OUT / "a1_kaggle/envoi_jeu"
ID = "affilecorentin/a1-appr-224"


def fit_jpeg(im, taille):   # copie de notebooks/m13_entrainer_kaggle.py
    petite = ImageOps.fit(im, (taille, taille), method=Image.BILINEAR)
    t = io.BytesIO(); petite.save(t, format="JPEG", quality=95)
    return np.asarray(Image.open(t).convert("RGB"), dtype="uint8")


def ouvrir(chemin, lecture):   # copie de notebooks/m13_entrainer_kaggle.py
    with Image.open(chemin) as im:
        im.draft("RGB", (lecture, lecture))
        return ImageOps.exif_transpose(im).convert("RGB")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    roles = list(csv.DictReader(open(OUT / "a1_roles_finaux.csv", encoding="utf-8")))
    man = {l["nom"]: l["sha256"] for l in csv.DictReader(open(SRC.parent / "manifeste.csv", encoding="utf-8"))}
    appr = [r for r in roles if r["role_final"] == "A1-appr"]
    interdits = {r["nom"] for r in roles if r["role_final"] != "A1-appr"}
    sha_interdits = {man[n] for n in interdits}
    sha_test = {l["sha256"] for l in csv.DictReader(open(OUT / "a1_test_liste.csv", encoding="utf-8"))}
    assert len(appr) == 200 and len(interdits) == 207 and sha_test <= sha_interdits and len(sha_test) == 183   # (1)
    DOS.mkdir(parents=True, exist_ok=True)
    for f in DOS.iterdir():
        f.unlink()
    lignes = []
    for r in appr:
        p = SRC / r["nom"]
        s = sha(p)
        assert s == man[r["nom"]] and s not in sha_interdits, r["nom"]   # (2)
        x = fit_jpeg(ouvrir(p, 448), 224)
        assert x.shape == (224, 224, 3)
        png = Path(r["nom"]).stem + ".png"
        Image.fromarray(x).save(DOS / png)
        assert np.array_equal(np.asarray(Image.open(DOS / png).convert("RGB")), x)
        lignes.append(dict(nom=r["nom"], png=png, pays_origine=r["pays"], lot=r["lot"], sha256_origine=s,
                           classe_vraie="xanthomonas", source="plantvillage_psu"))
    with open(DOS / "a1_appr.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(lignes[0])); w.writeheader(); w.writerows(lignes)
    (DOS / "dataset-metadata.json").write_text(json.dumps({
        "title": "a1-appr-224", "id": ID, "licenses": [{"name": "CC-BY-NC-SA-4.0"}],
        "description": "200 feuilles de bananier atteintes de flétrissement bactérien (BXW), PlantVillage / Penn State "
                       "(ScholarSphere 99857c83-1c68-4277-92fa-8172c4474d25, CC BY-NC-SA 4.0), préparées en 224 px. "
                       "Usage scolaire, privé."}, ensure_ascii=False, indent=1), encoding="utf-8")
    # (3) rejoué sur le dossier tel qu'il sera envoyé
    noms = sorted(p.name for p in DOS.iterdir())
    assert noms == sorted([l["png"] for l in lignes] + ["a1_appr.csv", "dataset-metadata.json"]), noms[:5]
    relu = list(csv.DictReader(open(DOS / "a1_appr.csv", encoding="utf-8")))
    assert len(relu) == 200 and not {l["sha256_origine"] for l in relu} & sha_interdits
    assert not {Path(l["nom"]).stem for l in relu} & {Path(n).stem for n in interdits}
    taille = sum(p.stat().st_size for p in DOS.iterdir())
    print(f"contrôles OK : 200 photos A1-appr, 0 SHA-256 d'A1-test (183) ni des 24 retirées ; {taille / 1e6:.1f} Mo")
    if "--envoyer" in sys.argv:
        env = dict(os.environ, REQUESTS_CA_BUNDLE="C:/Users/coren/.certificats/bundle_windows.pem",
                   SSL_CERT_FILE="C:/Users/coren/.certificats/bundle_windows.pem", PYTHONIOENCODING="utf-8")
        r = subprocess.run([str(RACINE / ".venv/Scripts/kaggle.exe"), "datasets", "create", "-p", str(DOS), "-r", "zip"],
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout[-600:], r.stderr[-600:])
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
