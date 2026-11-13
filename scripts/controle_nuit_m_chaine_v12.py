#!/usr/bin/env python3
"""Contrôleur, nuit du 12/11 : la chaîne locale (fieldscan.modules.maladies, processeur, 32 bits) charge-t-elle le
modèle final v12 et redonne-t-elle les probabilités du carnet Kaggle ? Quelques photos de VALIDATION seulement.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_nuit_m_chaine_v12.py a4 6
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

if __name__ == "__main__":
    c, n = sys.argv[1], int(sys.argv[2])
    p = pd.read_csv(RACINE / f"out/maladies/nuit_1112/kaggle/{sys.argv[3] if len(sys.argv) > 3 else 'final_' + c}/predictions_{c}_final_validation.csv")
    p = p.iloc[np.linspace(0, len(p) - 1, n).astype(int)]
    m = maladies.charger_convnext(RACINE / f"modeles/maladies_v12_essais/v12{c}")
    t0 = time.time()
    P = maladies.predire_convnext([str(RACINE / x) for x in p.chemin], m)
    dt = (time.time() - t0) / n
    ecart = np.abs(P - p[["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]].to_numpy()).max()
    l = f"{c} : chaîne locale contre carnet sur {n} photos de validation : écart maximal {ecart:.2e} ; {dt:.1f} s par photo (2 fils, machine partagée)"
    (RACINE / f"out/controle_nuit_1112/m_chaine_{c}.txt").write_text(l + "\n", encoding="utf-8")
    print(l)
