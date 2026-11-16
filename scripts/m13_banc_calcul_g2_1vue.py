#!/usr/bin/env python3
"""MB2, essai « morceaux en 1 vue » : morceaux 2 x 2 de la v10b lus avec la seule vue d'origine (au lieu de 4 vues :
identité, deux miroirs, quart de tour), sur les seules photos des 5 jeux de réglage dont l'alerte de F1 dépend des
morceaux (bornes, m13_banc_mb2.masques) : ailleurs, l'alerte ne dépend pas de la lecture des morceaux.
Sauvegarde tous les 4 photos dans out/maladies/nuit_1311/banc/g2_1vue.npz (jeu, indice, g2) ; reprise possible.
3 fils torch.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_calcul_g2_1vue.py
"""
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import torch  # noqa: E402

torch.set_num_threads(3)
from fieldscan.modules import maladies  # noqa: E402
import m13_banc_commun as C  # noqa: E402
import m13_banc_mb2 as M2  # noqa: E402

F = C.SORTIE / "g2_1vue.npz"


def chemin(j, c):
    return str(RACINE / c) if j == "agrovision" else C.B.fichier(c)


def main():
    jeux = C.charger(roamer=False)
    voulus = []
    for j in C.JEUX5:
        _, dep = M2.masques(jeux[j])
        voulus += [(j, int(i)) for i in np.flatnonzero(dep)]
    if F.exists():
        z = np.load(F, allow_pickle=False)
        J, I, G = list(z["jeu"]), list(z["indice"]), list(z["g2"])
    else:
        J, I, G = [], [], []
    faits = set(zip(J, I))
    reste = [v for v in voulus if v not in faits]
    print(f"{len(voulus)} voulues, {len(reste)} à lire", flush=True)
    m = {**maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b"), "vues": ["identite"]}
    t0 = time.time()
    for k in range(0, len(reste), 4):
        lot = reste[k:k + 4]
        p = maladies.predire_convnext([t for j, i in lot for t in maladies.morceaux_2x2(chemin(j, jeux[j]["chemin"][i]))], m)
        p = p.reshape(len(lot), 4, -1)
        J += [j for j, _ in lot]; I += [i for _, i in lot]; G += list(p)
        np.savez(F, jeu=np.array(J), indice=np.array(I), g2=np.array(G))
        print(time.strftime("%H:%M:%S"), f"{k + len(lot)}/{len(reste)} ({(time.time() - t0) / (k + len(lot)):.1f} s par photo)", flush=True)
    print("fini", flush=True)


if __name__ == "__main__":
    main()
