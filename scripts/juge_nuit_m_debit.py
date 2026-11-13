#!/usr/bin/env python3
"""Juge maladies, nuit du 12/11 : débit de lecture sur 20 photos de RÉGLAGE (validation Tanzanie), aucune photo de juge.
Compare la lecture de la chaîne (predire_convnext, fp32) à la même lecture en mémoire « channels_last » (fp32) :
écart max des probabilités et temps. 4 fils.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_m_debit.py
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402
torch.set_num_threads(4)
d = pd.read_csv(RACINE / "out/maladies/v10b/predictions_v10b_validation.csv")
f = [str(RACINE / c) for c in d.chemin[:: 150][:20]]
m = maladies.charger_convnext(RACINE / "modeles/maladies_v12_essais/v12a14")
t = time.time(); P1 = maladies.predire_convnext(f, m); t1 = time.time() - t
print(f"chaîne fp32 : {t1 / len(f):.2f} s/photo", flush=True)
for r in m["reseaux"]:
    r.to(memory_format=torch.channels_last)
t = time.time(); P2 = maladies.predire_convnext(f, m); t2 = time.time() - t
print(f"channels_last : {t2 / len(f):.2f} s/photo ; écart max {np.abs(P1 - P2).max():.2e}", flush=True)
