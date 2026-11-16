#!/usr/bin/env python3
"""A2 « plantain du Ghana » : facteur d'échelle, fixé avant toute détection (avenant du 15/11, section A2).

Règle : facteur de réduction qui ramène la médiane de la plus petite distance entre boîtes voisines à 2,5 m,
soit 50 px à 5 cm/px ; arrondi à 0,1. La médiane est prise sur toutes les boîtes de toutes les photos
(chaque boîte : distance au centre de boîte le plus proche dans la même photo ; photos d'au moins 2 boîtes).
Lit seulement les annotations (data/raw/plantain_ghana_m2/annotations/*.csv), aucune image, aucun modèle.
Écrit out/jeux_neufs_1511/a2_echelle.json ; le texte est rédigé dans plantain_echelle.md.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.stdout.reconfigure(encoding="utf-8")  # en mode -I, PYTHONIOENCODING est ignoré
ANN = RACINE / "data/raw/plantain_ghana_m2/annotations"
OUT = RACINE / "out/jeux_neufs_1511"
CIBLE_PX = 50.0          # 2,5 m à 5 cm/px


def main():
    toutes, par_photo, cotes = [], [], []
    for f in sorted(ANN.glob("*.csv")):
        b = pd.read_csv(f)
        if len(b) >= 1:
            cotes += np.sqrt(b.largeur * b.hauteur).tolist()
        if len(b) < 2:
            continue
        xy = b[["cx", "cy"]].to_numpy(float)
        d, _ = cKDTree(xy).query(xy, k=2)
        ppv = d[:, 1]
        toutes += ppv.tolist()
        par_photo.append(float(np.median(ppv)))
    toutes = np.array(toutes)
    med = float(np.median(toutes))
    brut = CIBLE_PX / med
    facteur = round(brut, 1)
    res = dict(boites=int(len(toutes)), photos=len(par_photo), ppv_mediane_px=round(med, 2),
               ppv_q25_px=round(float(np.percentile(toutes, 25)), 2), ppv_q75_px=round(float(np.percentile(toutes, 75)), 2),
               ppv_mediane_des_medianes_px=round(float(np.median(par_photo)), 2),
               ppv_medianes_photo_min_max=[round(min(par_photo), 2), round(max(par_photo), 2)],
               cote_boite_mediane_px=round(float(np.median(cotes)), 2),
               facteur_brut=round(brut, 4), facteur=facteur,
               cm_px_origine_implicite=round(5 * facteur, 2),
               taille_reduite=[round(7952 * facteur), round(5304 * facteur)],
               ppv_mediane_apres_reduction_px=round(med * facteur, 2),
               cote_boite_mediane_apres_reduction_m=round(float(np.median(cotes)) * facteur * 0.05, 2))
    (OUT / "a2_echelle.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
