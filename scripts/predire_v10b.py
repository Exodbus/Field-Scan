#!/usr/bin/env python3
"""Prédictions de la v10b du binôme (et de la soupe, de la v2 et de l'aiguilleur pour la Cordana du Pérou) sur nos jeux,
pour docs/protocole_maladies_v10b.md (amendement 1). Probabilités seules, aucun score affiché.

Mêmes photos et même ordre que les fichiers de prédictions existants (scripts/evaluer_module_maladies.py). Ordre de
calcul : validation (garde-fou G1), puis Cordana du Pérou, TDTU, PSFD, Éthiopie, BananaLSD. Un fichier déjà écrit
n'est pas recalculé.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/predire_v10b.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

SORTIE = RACINE / "out/maladies/v10b"
SORTIE.mkdir(parents=True, exist_ok=True)
DOS, ANCIENS = RACINE / "out/maladies/cinq_classes", RACINE / "out/maladies/dinov2_ft"


def fichier(c):
    return str(RACINE / c) if c.startswith("data/") else str(RACINE / "out/maladies/maladies_nuit" / c)


def ecrire(df, P, classes, nom):
    noms = {"saine": "p_saine", "cercosporiose_noire": "p_black_sigatoka", "fusariose": "p_fusarium", "autre_maladie": "p_autre"}
    out = df[["chemin", "jeu", "classe_vraie"]].copy()
    for k, c in enumerate(classes):
        out[noms[c]] = P[:, k].round(6)
    out.to_csv(SORTIE / nom, index=False)


def predire(m, df, nom):
    if (SORTIE / nom).exists():
        print(f"{nom} : déjà calculé", flush=True)
        return
    t = time.time()
    P = maladies.predire_convnext([fichier(c) for c in df.chemin], m)
    ecrire(df, P, m["classes"], nom)
    print(f"{nom} : {len(df)} photos en {(time.time() - t) / 60:.1f} min", flush=True)


idx = pd.read_csv(RACINE / "data/feuilles/index.csv")
idx = idx[idx.retenue.astype(bool) & idx.ensemble.eq("test_perou")]
perou = pd.DataFrame(dict(chemin="data/feuilles/" + idx.chemin.values, jeu="cordana_perou", classe_vraie=idx.classe.values))
jeux = {"validation": pd.read_csv(ANCIENS / "predictions_v2_validation.csv"), "cordana_perou": perou}
for j in ("tdtu", "psfd", "ethiopie"):
    jeux[j] = pd.read_csv(DOS / f"predictions_v2_{j}.csv")
jeux["bananalsd"] = pd.read_csv(ANCIENS / "predictions_v2_bananalsd.csv")

v10b = maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")
for j in ("validation", "cordana_perou"):
    predire(v10b, jeux[j], f"predictions_v10b_{j}.csv")
# Cordana du Pérou : la chaîne actuelle (soupe, v2, aiguilleur) n'a pas encore de prédictions
for nom_m, dos in (("soupe", "modeles/maladies_soupe_v2_v8/poids"), ("v2", "modeles/maladies_binome/maladies_v2/poids")):
    predire(maladies.charger_convnext(RACINE / dos), perou, f"predictions_{nom_m}_cordana_perou.csv")
if not (SORTIE / "p_loin_cordana_perou.csv").exists():
    a = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")
    pd.DataFrame(dict(chemin=perou.chemin, p_loin=maladies.p_loin([fichier(c) for c in perou.chemin], a, lot=32))).to_csv(
        SORTIE / "p_loin_cordana_perou.csv", index=False)
    print("p_loin_cordana_perou.csv : fait", flush=True)
for j in ("tdtu", "psfd", "ethiopie", "bananalsd"):
    predire(v10b, jeux[j], f"predictions_v10b_{j}.csv")
print("fini", flush=True)
