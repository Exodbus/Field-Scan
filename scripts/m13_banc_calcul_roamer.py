#!/usr/bin/env python3
"""M-banc, nuit du 13/11 : probabilités des lecteurs de F1 sur data/roamer_dev_loin_feuilles (jeu de réglage « loin »).

Calcule, avec le code de la chaîne (fieldscan.modules.maladies), pour les 2 985 feuilles :
  p_loin (aiguilleur), v2, soupe, v10b (lecture entière 384 px, 4 vues).
Ordre : malades d'abord (ordre tiré au hasard, graine 2026), puis saines. Sauvegarde après chaque lot de 32 photos ;
relancer le script reprend là où il s'est arrêté. 3 fils torch au plus (machine partagée).
Sorties : out/maladies/nuit_1311/banc/roamer/ (p_loin.npy, p_v2.npy, p_soupe.npy, p_v10b.npy, chemins.csv, temps.json).
Les morceaux 2 x 2 sont lus à part (scripts/m13_banc_calcul_g2.py), seulement là où une décision en dépend.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_calcul_roamer.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
import torch  # noqa: E402

torch.set_num_threads(3)
from fieldscan.modules import maladies  # noqa: E402

DOS = RACINE / "out/maladies/nuit_1311/banc/roamer"
DOS.mkdir(parents=True, exist_ok=True)
LOT = 32


def main():
    d = pd.read_csv(RACINE / "data/roamer_dev_loin_feuilles/feuilles.csv")
    n = len(d)
    rng = np.random.default_rng(2026)
    mal, sai = np.flatnonzero(d.etat.eq("malade")), np.flatnonzero(d.etat.eq("saine"))
    ordre = np.concatenate([rng.permutation(mal), rng.permutation(sai)])
    chemins = [str(RACINE / "data/roamer_dev_loin_feuilles" / c) for c in d.image]
    pd.DataFrame({"image": d.image, "etat": d.etat, "projet": d.projet}).to_csv(DOS / "chemins.csv", index=False)
    f = {k: DOS / f"p_{k}.npy" for k in ("loin", "v2", "soupe", "v10b")}
    forme = {"loin": (n,), "v2": (n, 3), "soupe": (n, 3), "v10b": (n, 4)}
    P = {k: (np.load(f[k]) if f[k].exists() else np.full(forme[k], np.nan)) for k in f}
    tj = DOS / "temps.json"
    temps = json.loads(tj.read_text(encoding="utf-8")) if tj.exists() else {k: [0.0, 0] for k in f}
    t0 = time.time()
    agu = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")
    m = {"v2": maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids"),
         "soupe": maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids"),
         "v10b": maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")}
    print(f"modèles chargés en {time.time() - t0:.0f} s", flush=True)
    reste = [i for i in ordre if np.isnan(P["v10b"][i, 0])]
    print(f"{n - len(reste)} photos déjà faites, {len(reste)} à faire", flush=True)
    for k0 in range(0, len(reste), LOT):
        idx = np.array(reste[k0:k0 + LOT])
        ch = [chemins[i] for i in idx]
        t = time.time()
        P["loin"][idx] = maladies.p_loin(ch, agu)
        temps["loin"][0] += time.time() - t
        for k in ("v2", "soupe", "v10b"):
            t = time.time()
            P[k][idx] = maladies.predire_convnext(ch, m[k])
            temps[k][0] += time.time() - t
        for k in f:
            temps[k][1] += len(idx)
            np.save(f[k], P[k])
        tj.write_text(json.dumps(temps), encoding="utf-8")
        fait = int((~np.isnan(P["v10b"][:, 0])).sum())
        print(time.strftime("%H:%M:%S"), f"{fait}/{n} ;", " ".join(f"{k} {v[0] / max(v[1], 1):.2f} s" for k, v in temps.items()),
              flush=True)
    print("fini", flush=True)


if __name__ == "__main__":
    main()
