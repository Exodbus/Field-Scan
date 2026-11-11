#!/usr/bin/env python3
"""Écrit requirements.txt avec les versions EXACTES installées dans l'environnement courant.

Seules les bibliothèques utilisées directement par Field Scan sont listées ; leurs propres dépendances
sont installées automatiquement par pip. Une bibliothèque absente est signalée.

Exemple :
    python scripts/ecrire_requirements.py
"""
from importlib import metadata
from pathlib import Path

PAQUETS = [
    ("numpy", "calcul"), ("pandas", "tableaux"), ("scipy", "zones, filtres"),
    ("rasterio", "lecture des images géoréférencées"), ("geopandas", "parcelles, GeoJSON"), ("shapely", "géométries"),
    ("pyproj", "systèmes de coordonnées"), ("Pillow", "photos"), ("PyYAML", "config.yaml"), ("matplotlib", "vignettes, cartes"),
    ("onnxruntime", "module maladies (processeur)"), ("torch", "module comptage"), ("torchvision", "module comptage"),
    ("deepforest", "module comptage"), ("timm", "module maladies (v10b, DINOv3)"), ("scikit-learn", "scripts d'évaluation"),
]


def main():
    lignes, absents = ["# Versions exactes de l'environnement de développement (écrit par scripts/ecrire_requirements.py)"], []
    for nom, usage in PAQUETS:
        try:
            lignes.append(f"{nom}=={metadata.version(nom)}  # {usage}")
        except metadata.PackageNotFoundError:
            absents.append(nom)
    Path("requirements.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
    if absents:
        print(f"\nAbsents de l'environnement (non écrits) : {', '.join(absents)}")
    print("\nrequirements.txt écrit.")


if __name__ == "__main__":
    main()
