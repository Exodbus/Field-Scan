#!/usr/bin/env python3
"""Tire au hasard (graine fixe 2026) 4 photos « taches » et 4 photos « saines » du jeu de juges BanSpot pour la démo.

BanSpot n'est dans aucune liste d'apprentissage (ni la v10b, ni la soupe, ni la v2) : il ne sert que de juge.
Les photos de data/demo_feuilles, elles, sont dans la liste d'apprentissage de la v10b : on ne les montre pas au jury.
Le tirage est fait avant de lancer la chaîne : on ne choisit pas les photos sur la réponse du modèle.

Copie les 8 photos dans out/demo_finale/photos_banspot/ et écrit tirage.csv (fichier, classe vraie).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/demo_finale_tirer_photos.py
"""
import csv
import random
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

SOURCE = RACINE / "data" / "raw" / "banspot" / "DATASET"
DEST = RACINE / "out" / "demo_finale" / "photos_banspot"
LISTE = RACINE / "out" / "maladies" / "banspot" / "reponses_banspot.csv"


def main():
    with open(LISTE, encoding="utf-8", newline="") as f:
        lignes = list(csv.DictReader(f))
    par_classe = {}
    for r in lignes:
        par_classe.setdefault(r["classe"], []).append(r["fichier"])
    rng = random.Random(2026)
    DEST.mkdir(parents=True, exist_ok=True)
    sortie = []
    for classe in sorted(par_classe):
        for fichier in rng.sample(sorted(par_classe[classe]), 4):
            src = SOURCE / Path(fichier).parent.name / Path(fichier).name
            nom = "banspot_" + Path(fichier).name.replace(" ", "_").replace("(", "").replace(")", "")
            shutil.copy2(src, DEST / nom)
            sortie.append(dict(photo=nom, classe_vraie=classe, origine=fichier))
    with open(DEST.parent / "tirage_banspot.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["photo", "classe_vraie", "origine"])
        w.writeheader()
        w.writerows(sortie)
    for s in sortie:
        print(s)


if __name__ == "__main__":
    main()
