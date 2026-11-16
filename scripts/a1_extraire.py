#!/usr/bin/env python3
"""A1 PlantVillage / Penn State : extraction de `bxw-leaf.zip` et des annotations XML correspondantes. Aucun modèle.

Règles : `docs/journee_2026-11-15/avenant_jeux_neufs.md`, section A1. Rien n'est exécuté dans l'archive.
  - images : `bxw-leaf/<nom>.jpg` -> `data/raw/plantvillage_psu/extrait/bxw-leaf/<nom>.jpg`, sans `__MACOSX` ;
  - annotations : les XML de `banana_annotations_all.zip` dont le nom de base est celui d'une photo
    -> `data/raw/plantvillage_psu/extrait/annotations_bxw_leaf/<nom>.xml` ;
  - manifeste : `extrait/manifeste.csv` (nom, taille, SHA-256, annotation trouvée).
Seuls des noms de base « sûrs » (lettres, chiffres, `_`, `-`, `.`) sont écrits, à plat.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/a1_extraire.py
"""
import csv
import hashlib
import re
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")

SRC = RACINE / "data/raw/plantvillage_psu"
DEST = SRC / "extrait"
SUR = re.compile(r"^[A-Za-z0-9_.\-]+$")


def main():
    (DEST / "bxw-leaf").mkdir(parents=True, exist_ok=True)
    (DEST / "annotations_bxw_leaf").mkdir(parents=True, exist_ok=True)
    lignes = []
    with zipfile.ZipFile(SRC / "bxw-leaf.zip") as z:
        for m in z.infolist():
            if m.is_dir() or "__MACOSX" in m.filename:
                continue
            parts = m.filename.split("/")
            nom = parts[-1]
            if len(parts) != 2 or parts[0] != "bxw-leaf" or not nom.lower().endswith(".jpg") or not SUR.match(nom):
                print("ignoré :", m.filename)
                continue
            donnees = z.read(m)
            (DEST / "bxw-leaf" / nom).write_bytes(donnees)
            lignes.append(dict(nom=nom, taille=len(donnees), sha256=hashlib.sha256(donnees).hexdigest()))
    bases = {Path(l["nom"]).stem: l for l in lignes}
    trouvees = 0
    with zipfile.ZipFile(SRC / "banana_annotations_all.zip") as z:
        for m in z.infolist():
            if m.is_dir() or "__MACOSX" in m.filename or not m.filename.lower().endswith(".xml"):
                continue
            nom = m.filename.split("/")[-1]
            base = Path(nom).stem
            if base in bases and SUR.match(nom):
                (DEST / "annotations_bxw_leaf" / nom).write_bytes(z.read(m))
                bases[base]["annotation"] = nom
                trouvees += 1
    lignes.sort(key=lambda l: l["nom"])
    with open(DEST / "manifeste.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["nom", "taille", "sha256", "annotation"])
        w.writeheader()
        for l in lignes:
            w.writerow({**l, "annotation": l.get("annotation", "")})
    print(f"{len(lignes)} photos extraites ; {trouvees} annotations XML correspondantes")


if __name__ == "__main__":
    main()
