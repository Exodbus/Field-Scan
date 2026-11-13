#!/usr/bin/env python3
"""M-analyste (nuit du 12/11) : diagnostic rapide d'un candidat v12 (pays lus par le pli qui ne les a pas appris).

Pour chaque candidat de out/maladies/nuit_1112/kaggle/<c>/ :
- AUC saines / malades par pays (pli tenu à l'écart) et pour la validation (moyenne des plis), comparée à la v10b
  et au lecteur proche de F1 (M-banc) ;
- raccourci « pays = malade » : P(malade) médiane des saines et part >= 0,5 ;
- PSFD : taux de ratées (P(saine) >= 0,5186) sur les copies tournées et sur les photos droites ;
- mélange avec F1 (somme des logits, poids 0,25 / 0,5) : AUC, pour savoir si le candidat apporte une information neuve.
Aucun réseau lancé, juges jamais lus.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/m12_analyse_v12.py [candidats ...]
Sortie : out/maladies/analyse/v12_diagnostic.csv (une ligne par candidat et par jeu, ajoutée)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
KAG = RACINE / "out/maladies/nuit_1112/kaggle"
SORTIE = RACINE / "out/maladies/analyse"
T = pd.read_csv(SORTIE / "table_reglage.csv").merge(
    pd.read_csv(SORTIE / "psfd_copies.csv")[["chemin", "coins_noirs"]], on="chemin", how="left")
T["coins_noirs"] = T.coins_noirs.fillna(False).astype(bool)
T = T.set_index("chemin")
SEUIL_B = 0.5186470150947571


def auc(pos, neg):
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().to_numpy()
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p) - np.log(1 - p)


def dossier_nom(c):
    """« a1 » -> (kaggle/a1, a1) ; « lot2/a2 » -> (kaggle/lot2, a2)."""
    return (KAG / c.split("/")[0], c.split("/")[1]) if "/" in c else (KAG / c, c)


def lire(c):
    d, c = dossier_nom(c)
    out = {}
    for p in ["tdtu", "psfd", "ethiopie"]:
        f = d / f"predictions_{c}_{p}.csv"
        if f.exists():
            out[p] = pd.read_csv(f).set_index("chemin").p_saine
    v = [pd.read_csv(f).set_index("chemin").p_saine for f in sorted(d.glob(f"predictions_{c}_validation_pli_*.csv"))]
    if v:
        out["validation"] = sum(v) / len(v)
    return out


def main(cands):
    lignes = []
    for c in cands:
        if not dossier_nom(c)[0].exists():
            print(c, "absent")
            continue
        for j, ps in lire(c).items():
            s = T.loc[ps.index]
            m = s.malade.to_numpy()
            pc, pf, pv = 1 - ps.to_numpy(), 1 - s.ps_F1_trois_morceaux2x2.to_numpy(), 1 - s.ps_v10b.to_numpy()
            L = dict(candidat=c, jeu=j, n=len(s), auc_cand=auc(pc[m], pc[~m]), auc_v10b=auc(pv[m], pv[~m]),
                     auc_F1=auc(pf[m], pf[~m]),
                     auc_F1_plus_0_25=auc(*(lambda x: (x[m], x[~m]))(logit(pf) + 0.25 * logit(pc))),
                     auc_F1_plus_0_5=auc(*(lambda x: (x[m], x[~m]))(logit(pf) + 0.5 * logit(pc))),
                     ratees_seuil_b=int((m & (ps.to_numpy() >= SEUIL_B)).sum()), n_malades=int(m.sum()),
                     saines_alerte_seuil_b=int((~m & (ps.to_numpy() < SEUIL_B)).sum()), n_saines=int((~m).sum()))
            if (~m).any():
                L.update(pm_saines_mediane=float(np.median(pc[~m])), part_saines_pm_sup_0_5=float((pc[~m] >= 0.5).mean()))
            if j == "psfd":
                cn = s.coins_noirs.to_numpy()
                L.update(ratees_tournees=float((ps.to_numpy()[cn] >= SEUIL_B).mean()),
                         ratees_droites=float((ps.to_numpy()[~cn] >= SEUIL_B).mean()))
            lignes.append(L)
    t = pd.DataFrame(lignes)
    f = SORTIE / "v12_diagnostic.csv"
    if f.exists():
        t = pd.concat([pd.read_csv(f)[lambda x: ~x.candidat.isin(cands)], t])
    t.to_csv(f, index=False)
    pd.set_option("display.width", 250)
    print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:] or ["a1", "c1", "c2"])
