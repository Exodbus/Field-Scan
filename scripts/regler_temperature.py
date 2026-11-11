#!/usr/bin/env python3
"""Mise à l'échelle de température des probabilités affichées (docs/protocole_maladies_cinq_classes.md, section 4).

T minimise la log-vraisemblance négative sur la validation (3 001), grille 0,30 à 3,00 par pas de 0,01, appliquée aux
probabilités du modèle telles qu'il les donne (moyenne des réseaux et des vues) : p_T ∝ p^(1/T). Les décisions ne changent
pas (seuils réglés sur les probabilités brutes).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/regler_temperature.py fichier_validation.csv [...]
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

INDICE = {"saine": 0, "cercosporiose_noire": 1, "fusariose": 2}


def temperature(f):
    d = pd.read_csv(f)
    P = np.clip(d[[c for c in d.columns if c.startswith("p_")]].values, 1e-12, 1)
    y = np.array([INDICE[c] for c in d.classe_vraie])
    meilleur = None
    for t in np.round(np.arange(0.30, 3.001, 0.01), 2):
        q = np.power(P, 1 / t); q /= q.sum(1, keepdims=True)
        nll = float(-np.log(q[np.arange(len(y)), y]).mean())
        if meilleur is None or nll < meilleur[1]:
            meilleur = (float(t), nll)
    brut = float(-np.log(P[np.arange(len(y)), y] / P.sum(1)).mean())
    return dict(fichier=str(f), temperature=meilleur[0], nll=round(meilleur[1], 5), nll_brut=round(brut, 5))


if __name__ == "__main__":
    print(json.dumps([temperature(Path(f)) for f in sys.argv[1:]], ensure_ascii=False, indent=1))
