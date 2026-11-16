#!/usr/bin/env python3
"""Contrôleur, nuit du 13/11 : contrôle indépendant de la « variante rapide » F1_bornes (M-banc, MB2).

F1_bornes : la soupe et la v10b ne sont pas lues pour les photos « loin » où la v2 alerte (la v2 décide seule) ; les
morceaux 2 x 2 ne sont lus que si l'alerte change entre les bornes « morceaux saine 100 % » et « malade 100 % ».
Ici, avec mon code (controle_1311_m_recalcul : règle d'alerte réécrite), sur les 5 jeux de réglage :
  1. alertes de F1_bornes = alertes de F1 photo par photo (morceaux réels là où ils sont lus, sinon décision de borne) ;
  2. parts de photos lues par chaque lecteur, pour F1 installé (`_executer_melange` : morceaux partout sauf « loin » + v2
     en alerte) et pour F1_bornes ;
  3. temps par photo estimé avec deux tables de temps par lecteur : celle mesurée par M-banc (temps_bilan.json, machine
     chargée) et celle du 13/11 (machine seule, journal de M-banc) ; règle : au moins 30 % de temps en moins.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/controle_1311_m_rapide.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import controle_1311_m_recalcul as R  # noqa: E402  (mon propre module)

jeux = R.charger(roamer=False)
T_LIBRE = dict(aiguilleur=0.58, v2=0.88, soupe=0.95, v10b=3.35, morceaux_2x2=10.7)   # 13/11, machine seule
TB = json.loads((R.BANC / "temps_bilan.json").read_text(encoding="utf-8"))
res, tot = {}, dict(n=0, diff=0, ratees_plus=0, lv=0, morc_f1=0, morc_var=0)
for j in R.JEUX5:
    d = jeux[j]
    a_f1, inc = R.bornes(lambda d_, G: R.alerte_f1(d_, G), d)
    assert not inc.any(), j
    lv = d["loin"] & (d["Pv2"][:, 0] <= 0.70)                 # la v2 décide seule
    # bornes avec TOUS les morceaux inconnus : la décision dépend-elle des morceaux ?
    dd = dict(d); dd["G2"] = np.full_like(d["G2"], np.nan)
    a_b, depend = R.bornes(lambda d_, G: R.alerte_f1(d_, G), dd)
    depend &= ~lv
    a_var = np.where(depend, a_f1, a_b)                        # morceaux réels seulement là où la décision en dépend
    a_var = np.where(lv, True, a_var)
    diff = int((a_var != a_f1).sum())
    rp = int((d["malade"] & ~a_var).sum() - (d["malade"] & ~a_f1).sum())
    n = len(a_f1)
    # morceaux connus sur AgroVisionBD : vérifier que toutes les photos « dépendantes » ont leurs morceaux lus
    manq = int((depend & np.isnan(d["G2"]).any(axis=(1, 2))).sum())
    parts = dict(lv=float(lv.mean()), morc_f1=float((~lv).mean()), morc_var=float(depend.mean()))

    def temps(T):
        f1 = T["aiguilleur"] + T["v2"] + T["soupe"] + T["v10b"] + parts["morc_f1"] * T["morceaux_2x2"]
        var = T["aiguilleur"] + T["v2"] + (1 - parts["lv"]) * (T["soupe"] + T["v10b"]) + parts["morc_var"] * T["morceaux_2x2"]
        return f1, var
    t_mb, t_li = temps(TB[j]["lecteurs"]), temps(T_LIBRE)
    res[j] = dict(n=n, diff=diff, ratees_en_plus=rp, morceaux_manquants=manq, **parts,
                  temps_mbanc=t_mb, temps_libre=t_li, parts_mbanc=dict(lv=TB[j]["part_lv"], morc_f1=TB[j]["part_morceaux_f1"],
                                                                         morc_var=TB[j]["part_morceaux_var"]))
    tot["n"] += n; tot["diff"] += diff; tot["ratees_plus"] += rp
    tot["lv"] += int(lv.sum()); tot["morc_f1"] += int((~lv).sum()); tot["morc_var"] += int(depend.sum())
    print(f"{j:11s} n {n} ; diff {diff} ; ratées en plus {rp} ; morceaux manquants {manq} ; v2 seule {lv.sum()} ; "
          f"morceaux F1 {(~lv).sum()} / variante {depend.sum()} (M-banc : {TB[j]['part_morceaux_var'] * n:.0f}) ; "
          f"temps (table M-banc) {t_mb[0]:.1f} -> {t_mb[1]:.1f} s ; (machine seule) {t_li[0]:.2f} -> {t_li[1]:.2f} s")
w = np.array([res[j]["n"] for j in R.JEUX5], "f8")
for k in ("temps_mbanc", "temps_libre"):
    f1 = float(np.average([res[j][k][0] for j in R.JEUX5], weights=w))
    var = float(np.average([res[j][k][1] for j in R.JEUX5], weights=w))
    res[k] = dict(f1=f1, variante=var, gain=1 - var / f1)
    print(f"{k} : F1 {f1:.2f} s, F1_bornes {var:.2f} s, gain {1 - var / f1:.1%}")
res["total"] = tot
print("total :", tot, f"; taux de décisions différentes {tot['diff'] / tot['n']:.4%}")
(R.OUT / "m_rapide.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
