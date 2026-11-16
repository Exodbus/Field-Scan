#!/usr/bin/env python3
"""Contrôleur, nuit du 13/11 : recalcul indépendant des élèves de M-entraîneur (famille B) sur le réglage du plan 4.3.

Candidat = un élève (ensemble des 2 réseaux de plis : moyenne des probabilités) avec deux confiances (s_p ; s_l) :
  photo proche (p_loin < 0,5) : alerte ssi P_élève(saine) < s_p ;
  photo loin : alerte ssi la v2 alerte (P_v2(saine) <= 0,70) ou P_élève(saine) < s_l.
TDTU et Éthiopie : lus par le réseau du pli qui ne les a pas appris (fichiers predictions_<c>_<jeu>.csv) ; validation,
PSFD, AgroVisionBD, roamer : moyenne des probabilités des 2 plis (fichiers _pli_tdtu et _pli_ethiopie).
Vérité, p_loin, v2 : mes caches (controle_1311_m_recalcul.charger) ; roamer : feuilles.csv, p_loin et entrées de F1
calculées sur Kaggle par M-entraîneur (maitre_roamer_dev_loin.npz), F1 recalculé par ma règle.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_1311_m_eleves.py <dossier> <cand> <s_p> <s_l> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import controle_1311_m_recalcul as R  # noqa: E402

K = RACINE / "out/maladies/nuit_1311/kaggle"
C4 = ["p_saine", "p_black_sigatoka", "p_fusarium", "p_autre"]


def norm(c):
    return str(c).replace("\\", "/").split("Field-Scan/")[-1]


def roamer_f1():
    z = np.load(K / "maitre/maitre_roamer_dev_loin.npz", allow_pickle=True)
    pl = pd.read_csv(K / "p_loin_roamer_dev_loin.csv")
    f = pd.read_csv(RACINE / "data/roamer_dev_loin_feuilles/feuilles.csv")
    assert list(pl.chemin) == list(z["chemin"]) == list(f.image)
    d = dict(malade=f.etat.eq("malade").to_numpy(), P10=z["P10"].astype("f8"), Pso=z["Pso"].astype("f8"),
             Pv2=z["Pv2"].astype("f8"), pl=pl.p_loin.to_numpy("f8"), G2=z["G2"].astype("f8"), chemin=z["chemin"])
    d["loin"] = d["pl"] >= 0.5
    return d


def probas(dossier, c, j, ordre):
    """P(saine) de l'élève dans l'ordre `ordre` des chemins."""
    def lire(n):
        d = pd.read_csv(dossier / n)
        return pd.Series(d.p_saine.to_numpy("f8"), index=[norm(x) for x in d.chemin])
    if j in ("tdtu", "ethiopie"):
        s = lire(f"predictions_{c}_{j}.csv")
    else:
        jj = "roamer_dev_loin" if j == "roamer" else j
        s = (lire(f"predictions_{c}_{jj}_pli_tdtu.csv") + lire(f"predictions_{c}_{jj}_pli_ethiopie.csv")) / 2
    o = [norm(x) for x in ordre]
    assert set(o) <= set(s.index), (j, len(set(o) - set(s.index)))
    return s.loc[o].to_numpy("f8")


if __name__ == "__main__":
    dossier = RACINE / sys.argv[1]
    jeux = R.charger(roamer=False)
    jeux["roamer"] = roamer_f1()
    ref, _ = R.evaluer(jeux, lambda d, G: R.alerte_f1(d, G))
    print(R.texte("F1 (référence)", ref), flush=True)
    sortie = {"F1": ref}
    args = sys.argv[2:]
    for i in range(0, len(args), 3):
        c, sp, sl = args[i], float(args[i + 1]), float(args[i + 2])
        r = {}
        for j in R.JEUX5 + ["roamer"]:
            d = jeux[j]
            ps = probas(dossier, c, j, d["chemin"])
            al = np.where(d["loin"], (d["Pv2"][:, 0] <= 0.70) | (ps < sl), ps < sp)
            r[j] = R.mesure(d, al)
        r["cout_reglage"] = float(np.mean([r[j]["cout"] for j in R.JEUX5]))
        ok, det = R.regle_finaliste(r, ref, ratio_temps=0.3)   # temps contrôlé à part (2 réseaux contre 5 lecteurs + morceaux)
        print(R.texte(f"{c} ({sp} ; {sl})", r), flush=True)
        print(f"   finaliste 4.3 (temps supposé rempli) : {ok} {det}", flush=True)
        sortie[f"{c}_{sp}_{sl}"] = dict(r=r, finaliste=ok, conditions=det)
    (R.OUT / f"m_eleves_{dossier.name}.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1, default=str),
                                                          encoding="utf-8")
