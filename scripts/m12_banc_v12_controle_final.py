#!/usr/bin/env python3
"""Contrôle du modèle final (3 réseaux appris sur tout sauf PSFD et la validation) sur la validation Tanzanie, dans le
mélange choisi de la famille C, au seuil choisi. Probabilités : out/maladies/nuit_1112/kaggle/final_*/predictions_<nom>_final_validation.csv.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_banc_v12_controle_final.py <nom> <mélange> <seuil>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import m12_banc_commun as B  # noqa: E402
from m12_banc_v12 import charger, geo, jeux  # noqa: E402
from m12_banc_v12_grille import MELANGES, reponses  # noqa: E402

nom, melange, t = ARGS[0], ARGS[1], float(ARGS[2])
f = sorted((B.SORTIE.parent / "kaggle").glob(f"final_*/predictions_{nom}_final_validation.csv"))
assert len(f) == 1, f
x = pd.read_csv(f[0])
d = jeux["validation"]
assert list(x.chemin) == list(d["chemin"])
Vf = x[["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]].to_numpy("float64")
Vp = charger(nom)["validation"]
for etiquette, V in (("plis (moyenne)", Vp), ("modèle final", Vf)):
    Ps = MELANGES[melange](d, V)
    m = B.mesure(d, reponses(d, geo(Ps, [1] * len(Ps)), t))
    print(f"{nom} / {melange} / t={t} / {etiquette} : validation {m['msa']}/{m['nm']} ratées ; {m['sea']}/{m['ns']} saines en alerte"
          f" (dont {m['sea_averif']} à vérifier) ; Sigatoka nommée {m['sig_nommee']}/{m['n_sig']} ; coût {m['cout']:.2f}"
          f" ; limites 14 et 77 : {'respectées' if m['msa'] <= 14 and m['sea'] <= 77 else 'DÉPASSÉES'}")
