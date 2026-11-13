#!/usr/bin/env python3
"""Essai 8 : seuil de nom (seuil_nom) réglé pour moins d'autres maladies dites Sigatoka, alertes inchangées (réglage seul).

Substitut de la Cordana (juge, non lue) : photos malades autres que Sigatoka, dites « cercosporiose noire ». Règle écrite
avant (journal, 22 h 34) : minimiser ce total sur les 4 jeux, sous la contrainte Sigatoka nommée en validation >= 95 % de
la valeur au seuil installé 0,79. Pour la chaîne installée et pour le mélange à trois (1, 1, 1), t = 0,74.
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import m12_banc_commun as B  # noqa: E402
from m12_banc_trois import geo3, jeux  # noqa: E402

ESSAIS = []
SIG = ["cercosporiose_noire", "black_sigatoka", "sigatoka"]


def rep(d, f_P, t, sn, loin_ou):
    rp = B.decider_v10b(f_P(d), seuil=t, seuil_nom=sn)
    if loin_ou:
        rl = np.where(np.isin(d["r_loin"], list(B.ALERTE)), d["r_loin"], rp)
        return np.where(d["loin"], rl, rp)
    return np.where(d["loin"], d["r_loin"], rp)


for nom, f_P, t, loin_ou in [("installée", lambda d: d["P10"], B.M_V10B["seuil"], False),
                             ("à trois (1,1,1) t=0,74", lambda d: geo3(d, 1, 1, 1), 0.74, True)]:
    print(f"\n--- {nom} ---")
    res = []
    for sn in [0.50, 0.60, 0.70, 0.75, 0.79, 0.83, 0.87, 0.90, 0.95]:
        tot, det, alertes = 0, {}, 0
        for j, d in jeux.items():
            r = rep(d, f_P, t, sn, loin_ou)
            autre = d["malade"] & ~np.isin(d["vraie"], SIG)
            n = int((autre & (r == "cercosporiose_noire")).sum())
            tot += n
            det[j] = f"{n}/{int(autre.sum())}"
            alertes += int(np.isin(r, list(B.ALERTE)).sum())
        sig_val = int((jeux["validation"]["sig"] & (rep(jeux["validation"], f_P, t, sn, loin_ou) == "cercosporiose_noire")).sum())
        sig_pays = {j: int((jeux[j]["sig"] & (rep(jeux[j], f_P, t, sn, loin_ou) == "cercosporiose_noire")).sum()) for j in ("tdtu", "psfd", "ethiopie")}
        ESSAIS.append(dict(famille="essai 8", nom=f"{nom} seuil_nom={sn}", autres_dites_sigatoka=tot, detail=det,
                           sigatoka_nommee_validation=sig_val, sigatoka_nommee_pays=sig_pays, alertes=alertes))
        res.append((sn, tot, sig_val))
        print(f"  seuil_nom={sn:.2f} autres dites Sigatoka {tot:4d} {det} | Sigatoka nommée val {sig_val}/1000, pays {sig_pays} | alertes {alertes}")
    base = [s for sn, _, s in res if sn == 0.79][0]
    ok = [(sn, tot) for sn, tot, s in res if s >= 0.95 * base]
    print("  choix selon la règle :", min(ok, key=lambda x: (x[1], -x[0])))
print("essais :", len(ESSAIS))
(B.SORTIE / "essais_nom.json").write_text(json.dumps(ESSAIS, ensure_ascii=False, indent=1), encoding="utf-8")
