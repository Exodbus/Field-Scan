#!/usr/bin/env python3
"""Pour information seulement (la règle 4.4 compte PSFD avec ses copies) : malades PSFD sans alerte hors copies tournées
à coins noirs (liste de M-analyste, out/maladies/analyse/psfd_copies.csv), chaîne complète, seuils v10b.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/m12_entr_psfd_info.py <dossier> <candidat> [...]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m12_entr_mesurer as M  # noqa: E402

c = pd.read_csv(M.RACINE / "out/maladies/analyse/psfd_copies.csv").set_index("chemin")
f = M.fixe("psfd")
droites = ~c.loc[f["chemin"], "coins_noirs"].to_numpy(bool)
ref = M.lire_csv(M.V10B / "predictions_v10b_psfd.csv", "psfd")
for nom, P in [("v10b", ref)] + [(n, M.charger_recette(sys.argv[1], n)[0]["psfd"]) for n in sys.argv[2:]]:
    rep = np.where(f["loin"], f["r_loin"], M.maladies.decider_convnext(P, M.M_V10B)[0])
    rate = ~np.isin(rep, list(M.ALERTE))
    print(f"{nom} : PSFD ratées {rate.sum()}/738 ; sans copies tournées {(rate & droites).sum()}/{droites.sum()}")
