"""Classe les photos de feuilles d'un dossier avec le modèle maladies v2 et écrit un CSV.

Usage :
    python exemple.py DOSSIER_PHOTOS [--sortie feuilles.csv]

Une ligne par photo : probabilités (saine, Black Sigatoka, Fusarium) et réponse finale
(saine, black_sigatoka, fusarium, malade_non_identifiee ou inconnu).
"""
import argparse
import csv
from pathlib import Path

import classifieur

EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path, help="dossier des photos de feuilles (sous-dossiers compris)")
    ap.add_argument("--sortie", type=Path, default=Path("feuilles.csv"))
    ap.add_argument("--poids", type=Path, default=Path(__file__).parent / "poids")
    a = ap.parse_args()

    photos = sorted(p for p in a.dossier.rglob("*") if p.suffix.lower() in EXTENSIONS)
    if not photos:
        raise SystemExit(f"Aucune photo dans {a.dossier}")
    reseaux, seuils = classifieur.charger(a.poids)
    probas = classifieur.probabilites(reseaux, photos)
    reponses = classifieur.decider(probas, seuils)

    with open(a.sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["photo", "p_saine", "p_black_sigatoka", "p_fusarium", "reponse"])
        for photo, p, r in zip(photos, probas, reponses):
            w.writerow([str(photo), *(f"{x:.4f}" for x in p), r])
    print(f"{len(photos)} photos classées -> {a.sortie}")


if __name__ == "__main__":
    main()
