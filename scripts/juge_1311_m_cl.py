#!/usr/bin/env python3
"""Contrôle sur 8 photos de réglage (validation Tanzanie) : d3b lu en mémoire channels_last donne-t-il les mêmes
probabilités que la lecture standard, et combien plus vite ? 4 fils, machine partagée."""
import sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE)); sys.path.insert(0, str(RACINE / "scripts"))
import torch
torch.set_num_threads(4)
from fieldscan.modules import maladies
import m12_banc_commun as B
ch = [str(c) for c in list(B.charger_reglage()["validation"]["chemin"])[100:108]]
ch = [c if Path(c).exists() else B.fichier(c) for c in ch]
m = maladies.charger_convnext(RACINE / "modeles/maladies_nuit_1311/d3b")
t0 = time.time(); P0 = maladies.predire_convnext(ch, m); t_std = (time.time() - t0) / len(ch)
for r in m["reseaux"]:
    r.to(memory_format=torch.channels_last)
t0 = time.time(); P1 = maladies.predire_convnext(ch, m); t_cl = (time.time() - t0) / len(ch)
print(f"standard {t_std:.2f} s/photo ; channels_last {t_cl:.2f} s/photo ; écart max {np.abs(P0 - P1).max():.2e}")
