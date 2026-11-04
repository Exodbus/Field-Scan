#!/usr/bin/env python3
"""Pré-annotation des photos DJI de jeunes bananiers avec le modèle hébergé de Roboflow (plants-bana/3).

But : gagner du temps. Les points proposés sont écrits dans une couche À PART (pre_annotations.gpkg) ; ils ne
deviennent une référence qu'après relecture complète (points faux supprimés, plants oubliés ajoutés).

Précautions (voir docs/consigne_annotation_jeunes_bananiers.md) :
- seulement les photos d'ENTRAÎNEMENT (dji_0546, dji_0548) par défaut ; la photo de validation (dji_0544) est
  annotée sans pré-annotation, pour que la référence ne soit pas influencée par un modèle ;
- plants-bana/3 a été entraîné sur ces mêmes photos, avec leurs boîtes incomplètes : il risque de les reproduire.
  On regarde donc le résultat avant de décider de s'en servir.

Lecture : chaque photo est découpée en une grille de --grille x --grille tuiles qui se recouvrent, chaque tuile
envoyée en 640 x 640 (taille d'entraînement du modèle) ; doublons fusionnés (NMS) ; seuil de confiance bas
(--confiance) pour proposer large, la note est gardée dans le champ « score ». Réponses mises en cache.
La clé est lue dans ROBOFLOW_API_KEY, jamais écrite dans un fichier.

Exemple (PowerShell) :
    $env:ROBOFLOW_API_KEY = "..."
    python scripts/preannoter_jeunes_bananiers.py --grille 1 2 3
"""
import argparse
import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from evaluer_modele_roboflow import interroger, nms  # noqa: E402


def tuiles(largeur, hauteur, n, recouvrement=0.15):
    """Fenêtres (x0, y0, x1, y1) d'une grille n x n qui se recouvrent."""
    if n == 1:
        return [(0, 0, largeur, hauteur)]
    tw, th = largeur / (n - (n - 1) * recouvrement), hauteur / (n - (n - 1) * recouvrement)
    pas_x, pas_y = tw * (1 - recouvrement), th * (1 - recouvrement)
    return [(round(i * pas_x), round(j * pas_y), round(i * pas_x + tw), round(j * pas_y + th)) for j in range(n) for i in range(n)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", default="data/drone/jeunes_bananiers")
    ap.add_argument("--images", nargs="+", default=["dji_0546", "dji_0548"])
    ap.add_argument("--modele", default="plants-bana/3")
    ap.add_argument("--point-acces", default="https://detect.roboflow.com")
    ap.add_argument("--grille", type=int, nargs="+", default=[1, 2, 3], help="grilles essayées (une couche par grille)")
    ap.add_argument("--confiance", type=int, default=10, help="seuil de confiance en %% (bas : on propose large)")
    args = ap.parse_args(argv)
    cle = os.environ.get("ROBOFLOW_API_KEY")
    if not cle:
        raise SystemExit("Définis d'abord la clé : $env:ROBOFLOW_API_KEY = \"...\"")
    dossier = Path(args.dossier)
    cadres = {c["image"]: c for c in json.loads((dossier / "cadres.json").read_text(encoding="utf-8"))["images"]}
    cache = dossier / "cache_roboflow"
    cache.mkdir(exist_ok=True)
    sortie = dossier / "pre_annotations.gpkg"
    for g in args.grille:
        lignes = []
        for nom in args.images:
            img = Image.open(dossier / f"{nom}.jpg").convert("RGB")
            boites, notes = [], []
            for k, (x0, y0, x1, y1) in enumerate(tuiles(img.width, img.height, g)):
                morceau = img.crop((x0, y0, x1, y1))
                fx, fy = (x1 - x0) / 640, (y1 - y0) / 640
                rep = interroger(morceau.resize((640, 640)), args.modele, cle, cache / f"{nom}_g{g}_{k}_c{args.confiance}.json",
                                 args.point_acces, args.confiance)
                for p in rep.get("predictions", []):
                    if "banana" not in str(p.get("class", "")).lower():         # même filtre que evaluer_modele_roboflow.py
                        continue
                    cx, cy, w, h = p["x"] * fx + x0, p["y"] * fy + y0, p["width"] * fx, p["height"] * fy
                    boites.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
                    notes.append(float(p["confidence"]))
            garde = nms(boites, notes) if boites else []
            dx = cadres[nom]["decalage_x"]
            dessin = img.copy()
            d = ImageDraw.Draw(dessin)
            for i in garde:
                bx0, by0, bx1, by1 = boites[i]
                cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
                lignes.append(dict(image=nom, type="mere", score=round(notes[i], 3), source=f"{args.modele} grille {g}",
                                   geometry=Point(cx + dx, -cy)))
                r = 25
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 43, 214), width=8)
            dessin.resize((1800, round(1800 * img.height / img.width))).save(dossier / f"apercu_{nom}_grille{g}.jpg", quality=85)
            print(f"grille {g}, {nom} : {len(garde)} plants proposés (confiance >= {args.confiance} %)")
        couche = f"grille_{g}"
        gdf = gpd.GeoDataFrame(lignes, geometry="geometry", crs="EPSG:3857") if lignes else \
            gpd.GeoDataFrame({"image": [], "type": [], "score": [], "source": []}, geometry=[], crs="EPSG:3857")
        gdf.to_file(sortie, layer=couche, driver="GPKG")
    print(f"Couches dans {sortie} ; aperçus apercu_*.jpg dans {dossier}")


if __name__ == "__main__":
    main()
