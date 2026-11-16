#!/usr/bin/env python3
"""Temps par photo, F1 contre un élève (un seul ConvNeXt-Tiny DINOv3 lu en 384 px), même machine, mêmes photos, 2 fils.

F1 (comme fieldscan/modules/maladies.py, _executer_melange) : aiguilleur + v10b (3 réseaux, 4 vues, 384 px) + soupe + v2
(224 px) + morceaux 2 x 2 de la v10b sur les photos dont la réponse vient du lecteur proche.
Élève : aiguilleur + 1 réseau (4 vues, 384 px ; ou 1 vue) + v2 seulement sur les photos « loin ».
Le temps ne dépend que de l'architecture : sans poids d'élève, le réseau 0 de la v10b sert de remplaçant (même réseau).
Chargement des modèles exclu ; F1 et élève alternés photo par photo pour partager les à-coups de la machine.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_entr_temps.py [n_photos] [poids_eleve.pt]
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
import torch  # noqa: E402
torch.set_num_threads(2)
from fieldscan.modules import maladies  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
L = pd.read_csv(RACINE / "out/maladies/v10b/predictions_v10b_validation.csv")
chemins = [str(RACINE / c) for c in L.chemin.sample(n, random_state=2026)]
m10 = maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")
mso = maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids")
mv2 = maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids")
a = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")
eleve = {**m10, "reseaux": m10["reseaux"][:1]}
if len(sys.argv) > 2:
    import timm
    r = timm.create_model("convnext_tiny.dinov3_lvd1689m", pretrained=False, num_classes=4)
    w = torch.load(sys.argv[2], map_location="cpu", weights_only=True)
    r.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in w.items()})
    eleve["reseaux"] = [r.eval()]
eleve1 = {**eleve, "vues": ["identite"]}
t = {"F1": [], "eleve_4vues": [], "eleve_1vue": []}
for c in chemins:
    t0 = time.perf_counter()
    pl = maladies.p_loin([c], a)
    maladies.predire_convnext([c], m10); maladies.predire_convnext([c], mso); pv2 = maladies.predire_convnext([c], mv2)
    if pl[0] < 0.5:   # photo proche : morceaux lus (comme la chaîne installée)
        maladies.predire_convnext(maladies.morceaux_2x2(c), m10)
    t["F1"].append(time.perf_counter() - t0)
    for nom, e in (("eleve_4vues", eleve), ("eleve_1vue", eleve1)):
        t0 = time.perf_counter()
        pl = maladies.p_loin([c], a)
        maladies.predire_convnext([c], e)
        if pl[0] >= 0.5:
            maladies.predire_convnext([c], mv2)
        t[nom].append(time.perf_counter() - t0)
    print({k: round(v[-1], 2) for k, v in t.items()}, flush=True)
res = {k: float(np.mean(v)) for k, v in t.items()}
res["rapport_eleve_4vues_sur_F1"] = res["eleve_4vues"] / res["F1"]
res["rapport_eleve_1vue_sur_F1"] = res["eleve_1vue"] / res["F1"]
res["photos"], res["fils"] = n, 2
print(json.dumps(res, indent=1))
(RACINE / "out/maladies/nuit_1311/kaggle/temps.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
