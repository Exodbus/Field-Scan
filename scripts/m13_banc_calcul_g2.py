#!/usr/bin/env python3
"""M-banc, nuit du 13/11 : morceaux 2 x 2 de la v10b (code de la chaîne : maladies.morceaux_2x2, predire_convnext)
pour les photos dont une décision en dépend (bornes), sur AgroVisionBD ou roamer_dev_loin_feuilles.

Liste des photos : un fichier JSON d'indices (ordre du jeu dans m13_banc_commun). Sauvegarde après chaque lot de 4
photos dans out/maladies/nuit_1311/banc/g2_agrovision.npz ou roamer/g2_roamer.npz (indices, g2) ; reprise possible.
3 fils torch (seul calcul de M-banc en cours).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_calcul_g2.py agrovision liste.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
import torch  # noqa: E402

torch.set_num_threads(3)
from fieldscan.modules import maladies  # noqa: E402

SORTIE = RACINE / "out/maladies/nuit_1311/banc"


def main(jeu, liste):
    if jeu == "agrovision":
        chemins = [str(RACINE / c) for c in pd.read_csv(RACINE / "out/controle_nuit_1112/juge_m/vierge/reponses_installee.csv").chemin]
        f = SORTIE / "g2_agrovision.npz"
    else:
        chemins = [str(RACINE / "data/roamer_dev_loin_feuilles" / c) for c in pd.read_csv(SORTIE / "roamer/chemins.csv").image]
        f = SORTIE / "roamer/g2_roamer.npz"
    voulus = [int(i) for i in json.loads(Path(liste).read_text(encoding="utf-8"))]
    if f.exists():
        z = np.load(f)
        idx, g2 = list(z["indices"]), list(z["g2"])
    else:
        idx, g2 = [], []
    reste = [i for i in voulus if i not in set(idx)]
    print(f"{len(voulus)} voulues, {len(reste)} à lire", flush=True)
    m = maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")
    t0 = time.time()
    for k in range(0, len(reste), 4):
        lot = reste[k:k + 4]
        p = maladies.predire_convnext([t for i in lot for t in maladies.morceaux_2x2(chemins[i])], m).reshape(len(lot), 4, -1)
        idx += lot
        g2 += list(p)
        np.savez(f, indices=np.array(idx), g2=np.array(g2))
        print(time.strftime("%H:%M:%S"), f"{k + len(lot)}/{len(reste)} ({(time.time() - t0) / (k + len(lot)):.1f} s par photo)", flush=True)
    print("fini", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
