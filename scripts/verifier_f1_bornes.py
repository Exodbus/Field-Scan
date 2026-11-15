"""Vérifie le correctif F1_bornes de fieldscan/modules/maladies.py (_melange_bornes) sur les probabilités en cache des
5 jeux de réglage : mêmes alertes que F1 ? Les lecteurs sont remplacés par les probabilités en cache (aucun réseau lancé)."""
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m13_banc_commun as C  # noqa: E402


class Journal:
    def info(self, t):
        pass


class Ctx:
    journal = Journal()


jeux = C.charger(roamer=False)
total = dict(photos=0, comparees=0, alertes_diff=0, noms_diff=0, morceaux_lus=0, morceaux_manquants=0)
for nom in C.JEUX5:
    d = jeux[nom]
    n = len(d["P10"])
    lus = {"g": 0}

    def predire(chemins, m, lot=16, d=d, lus=lus):
        if isinstance(chemins[0], tuple):
            lus["g"] += len(chemins) // 4
            return np.array([d["G2"][i, q] for (_, i, q) in chemins])
        idx = [int(c) for c in chemins]
        return {"v10b": d["P10"], "soupe": d["Pso"], "v2": d["Pv2"]}[m["nom"]][idx]

    maladies.predire_convnext = predire
    maladies.morceaux_2x2 = lambda c: [("g", int(c), q) for q in range(4)]
    m = {**C.M_PROCHE_F1, "nom": "v10b"}
    ms, mv2 = {"nom": "soupe"}, {**C.M_LOIN, "nom": "v2"}
    rep, *_ = maladies._melange_bornes(Ctx(), [str(i) for i in range(n)], m, ms, mv2, d["p_loin"], C.M_PROCHE_F1, C.M_LOIN)
    a_f1, r_f1, inconnu = C.bornes(d, C.f1)          # F1 installé (morceaux lus partout où il faut)
    manq = np.isnan(d["G2"][:, :, 0]).any(1)
    ok = ~inconnu                                     # photos où l'alerte de F1 est connue
    a_b = np.isin(rep, list(C.ALERTE))
    total["photos"] += n
    total["comparees"] += int(ok.sum())
    total["alertes_diff"] += int((a_b != a_f1)[ok].sum())
    total["noms_diff"] += int((rep != r_f1)[ok & ~manq].sum())
    total["morceaux_lus"] += lus["g"]
    print(f"{nom:10s} n={n:5d} comparées={int(ok.sum()):5d} alertes différentes={int((a_b != a_f1)[ok].sum())} "
          f"morceaux lus={lus['g']} (F1 complet en lirait {int((~((d['p_loin'] >= 0.5) & np.isin(d['r_loin'], list(maladies.MALADES)))).sum())})")
print(total)
