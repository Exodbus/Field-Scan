#!/usr/bin/env python3
"""M-entraîneur (nuit du 13/11) : P(photo prise de loin) de l'aiguilleur de la chaîne sur roamer_dev_loin_feuilles
(jeu de réglage du plan 4.3), sur processeur, 2 fils. Sortie : out/maladies/nuit_1311/kaggle/p_loin_roamer_dev_loin.csv.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_loin_roamer.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
import torch  # noqa: E402
torch.set_num_threads(2)
from fieldscan.modules import maladies  # noqa: E402

SORTIE = RACINE / "out/maladies/nuit_1311/kaggle/p_loin_roamer_dev_loin.csv"
d = pd.read_csv(RACINE / "data/roamer_dev_loin_feuilles/feuilles.csv")
chemins = [str(RACINE / "data/roamer_dev_loin_feuilles" / c) for c in d.image]
a = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")
P, t0 = [], time.time()
for k in range(0, len(chemins), 64):
    P.append(maladies.p_loin(chemins[k:k + 64], a, lot=32))
    print(f"{k + 64}/{len(chemins)} ({(time.time() - t0) / (k + 64):.2f} s par photo)", flush=True)
pd.DataFrame(dict(chemin=d.image, etat=d.etat, projet=d.projet, p_loin=np.concatenate(P))).to_csv(SORTIE, index=False)
print("écrit", SORTIE)
