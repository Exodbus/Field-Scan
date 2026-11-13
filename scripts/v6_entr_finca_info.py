#!/usr/bin/env python3
"""Mesure POUR INFORMATION (hors règle) des ONNX donnés sur banano_finca (ancien juge du binôme), agent C-entraîneur.
Reprend la mesure de notebooks/v6_travail_centres.py. Usage : script.py <onnx> [<onnx> ...] (stride 4 ; v6b : suffixe :2:13)."""
import os, sys, json
from pathlib import Path
RACINE = Path(__file__).resolve().parents[1]; os.chdir(RACINE)
P = "data/roboflow_nuit_1112/comptage/banano_finca/prepare"
for arg in sys.argv[1:]:
    chemin, *opt = arg.split(":")
    stride, k = (int(opt[0]), int(opt[1])) if opt else (4, 7)
    os.environ.update(V6_DONNEES="data/drone/comptage_v6_5cm", V6_SORTIE="C:/Users/coren/kaggle_tmp/v6_essai/finca",
                      V6_RECETTE=json.dumps(dict(jeu_finca=P, stride=stride, k_pics=k, decalage=stride == 2)))
    src = open("notebooks/v6_travail_centres.py", encoding="utf-8").read().split("# ---------------------------------------------------------------- référence ONNX")[0]
    g = {"__name__": "finca"}; exec(compile(src, "travail", "exec"), g)
    m = g["mesurer_tuiles"](g["PredicteurOnnx"](chemin, stride), g["ECH"]["val_finca"])
    print(Path(chemin).name, " ; ".join(f"{s}: F1 {t['f1']:.3f} ({t['detectes']}/{t['reels']})" for s, t in m.items() if s in (0.2, 0.3, 0.35, 0.45)), flush=True)
