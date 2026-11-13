#!/usr/bin/env python3
"""Pour information (décision du chef d'orchestre, 13/11 vers 0 h 20) : coût des finalistes avec PSFD compté sans les
copies tournées sur fond noir (out/maladies/analyse/psfd_copies.csv, colonne coins_noirs), et par groupe de quasi-copies
(dino_0.95 : une photo par groupe, la première). La règle 4.4 reste celle du plan (738 photos)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
import m12_banc_finalistes as F  # noqa: E402

J = B.charger_reglage()
K = B.SORTIE / "kaggle_morceaux"
for j, d in J.items():
    d["G2"] = np.load(K / f"morceaux_{j}.npz")["g2"].astype("float64")
    d["P512"] = pd.read_csv(K / f"p512_{j}.csv")[["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]].to_numpy("float64")
cp = pd.read_csv(RACINE / "out/maladies/analyse/psfd_copies.csv").set_index("chemin").loc[list(J["psfd"]["chemin"])]
masques = {"738 (règle)": np.ones(len(cp), bool), "sans copies tournées": ~cp.coins_noirs.to_numpy(bool),
           "un par groupe dino 0,95": ~cp["dino_0.95"].duplicated().to_numpy()}
for k, c in F.CANDIDATS.items():
    r = {j: B.mesure(d, F.repondre(d["P10"], d["Pso"], d["Pv2"], d["p_loin"], c, d["P512"], d["G2"])) for j, d in J.items()}
    rep = F.repondre(*(J["psfd"][x] for x in ("P10", "Pso", "Pv2", "p_loin")), c, J["psfd"]["P512"], J["psfd"]["G2"])
    al = np.isin(rep, list(B.ALERTE))
    t = []
    for nom, m in masques.items():
        cout_psfd = 300 * (~al & m).sum() / m.sum()
        moy = np.mean([r["validation"]["cout"], r["tdtu"]["cout"], cout_psfd, r["ethiopie"]["cout"]])
        t.append(f"{nom} : PSFD {int((~al & m).sum())}/{int(m.sum())} c={cout_psfd:.1f} moy={moy:.2f}")
    print(f"{k:28s} " + " | ".join(t))
