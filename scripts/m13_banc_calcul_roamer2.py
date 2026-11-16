#!/usr/bin/env python3
"""M-banc, reprise du 14/11 : suite du calcul roamer (scripts/m13_banc_calcul_roamer.py), par étapes, pour ne lire
que ce dont les décisions ont besoin. Mêmes fichiers de sortie (out/maladies/nuit_1311/banc/roamer/p_*.npy).

p_loin : repris de out/maladies/nuit_1311/kaggle/p_loin_roamer_dev_loin.csv (aiguilleur de la chaîne, calculé par
M-entraîneur ; identique au mien à 2 × 10^-16 près sur les 352 photos communes).
Étapes (malades seulement, ordre tiré au hasard de m13_banc_calcul_roamer.py) :
  A. v2 sur toutes les malades ;
  B. soupe + v10b sur les malades dont F1 a besoin : pas (« loin » et v2 en alerte) ;
  C. soupe + v10b sur les autres malades ;
  D. (si le temps le permet) les saines, dans le même ordre A puis B puis C.
Sauvegarde tous les 32 ; reprise possible. 3 fils torch.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m13_banc_calcul_roamer2.py
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
import m12_banc_commun as B  # noqa: E402

DOS = RACINE / "out/maladies/nuit_1311/banc/roamer"
LOT = 32


def main():
    d = pd.read_csv(RACINE / "data/roamer_dev_loin_feuilles/feuilles.csv")
    n = len(d)
    pl_csv = pd.read_csv(RACINE / "out/maladies/nuit_1311/kaggle/p_loin_roamer_dev_loin.csv")
    assert list(pl_csv.chemin) == list(d.image)
    rng = np.random.default_rng(2026)   # même ordre que m13_banc_calcul_roamer.py
    mal, sai = np.flatnonzero(d.etat.eq("malade")), np.flatnonzero(d.etat.eq("saine"))
    o_mal, o_sai = rng.permutation(mal), rng.permutation(sai)
    chemins = [str(RACINE / "data/roamer_dev_loin_feuilles" / c) for c in d.image]
    f = {k: DOS / f"p_{k}.npy" for k in ("loin", "v2", "soupe", "v10b")}
    P = {k: np.load(f[k]) for k in f}
    P["loin"] = pl_csv.p_loin.to_numpy("float64")
    np.save(f["loin"], P["loin"])
    m = {"v2": maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids"),
         "soupe": maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids"),
         "v10b": maladies.charger_convnext(RACINE / "modeles/maladies_binome/v10b")}
    temps = {k: [0.0, 0] for k in ("v2", "soupe", "v10b")}

    def lire(idx, lecteurs, etape):
        idx = [int(i) for i in idx]
        for k0 in range(0, len(idx), LOT):
            lot = idx[k0:k0 + LOT]
            ch = [chemins[i] for i in lot]
            for k in lecteurs:
                t = time.time()
                P[k][lot] = maladies.predire_convnext(ch, m[k])
                temps[k][0] += time.time() - t
                temps[k][1] += len(lot)
                np.save(f[k], P[k])
            print(time.strftime("%H:%M:%S"), etape, f"{k0 + len(lot)}/{len(idx)} ;",
                  " ".join(f"{k} {v[0] / max(v[1], 1):.2f} s" for k, v in temps.items()), flush=True)

    for nom, ordre in (("malades", o_mal), ("saines", o_sai)):
        lire([i for i in ordre if np.isnan(P["v2"][i, 0])], ["v2"], f"{nom} A (v2)")
        rl = maladies.decider_convnext(P["v2"], B.M_V2)[0]
        lv = (P["loin"] >= 0.5) & np.isin(rl, list(B.ALERTE))
        lire([i for i in ordre if not lv[i] and np.isnan(P["v10b"][i, 0])], ["soupe", "v10b"], f"{nom} B")
        lire([i for i in ordre if np.isnan(P["v10b"][i, 0])], ["soupe", "v10b"], f"{nom} C")
    (DOS / "temps2.json").write_text(json.dumps(temps), encoding="utf-8")
    print("fini", flush=True)


if __name__ == "__main__":
    main()
