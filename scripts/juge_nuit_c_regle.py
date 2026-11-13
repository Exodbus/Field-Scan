#!/usr/bin/env python3
"""Juge comptage, nuit du 12 au 13 novembre 2026 : tableaux et règle d'adoption 3.4 (plan de la nuit), sans rien régler.

Lit out/controle_nuit_1112/juge_c/mesure_{segmento,cg,banano,neg_test}.json (mesure principale) et applique :
  moyenne des F1 (segmento, cg, banano) >= celle du v5 à 0,30 - 0,010 ;
  erreur de compte moyenne (3 juges) <= celle du v5 à 0,30 ;
  fausses détections sans bananier < 1 % ;
entre finalistes qui passent : meilleure moyenne de réglage (chiffres ONNX recalculés par le Contrôleur, verdicts.md).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_nuit_c_regle.py --liste A B C
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
D = RACINE / "out/controle_nuit_1112/juge_c"
JUGES = ["segmento", "cg", "banano"]
REGLAGE = {"E10_moy_v6e+v5": 0.8822, "v6f": 0.8780, "E5p90b_moy34_v5_d0.1": 0.8549, "v5_030": 0.7777, "v5_020": 0.7923}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", nargs="+", required=True)
    a = ap.parse_args()
    M = {j: json.loads((D / f"mesure_{j}.json").read_text(encoding="utf-8"))["candidats"] for j in JUGES + ["neg_test"]}
    noms = a.liste + ["v5_030", "v5_020"]
    t = {}
    for n in noms:
        f1 = [M[j][n]["f1"] for j in JUGES]
        er = [M[j][n]["err"] for j in JUGES]
        t[n] = dict(f1=dict(zip(JUGES, f1)), err=dict(zip(JUGES, er)), moy_f1=sum(f1) / 3, moy_err=sum(er) / 3,
                    moy_f1_sans_seg=(M["cg"][n]["f1"] + M["banano"][n]["f1"]) / 2,
                    moy_err_sans_seg=(M["cg"][n]["err"] + M["banano"][n]["err"]) / 2,
                    fp=M["neg_test"][n]["fp"], arbres=M["neg_test"][n]["arbres"], taux=M["neg_test"][n]["taux"])
    ref = t["v5_030"]
    passe = {}
    for n in a.liste:
        c1 = t[n]["moy_f1"] >= ref["moy_f1"] - 0.010
        c2 = t[n]["moy_err"] <= ref["moy_err"]
        c3 = t[n]["taux"] < 0.01
        t[n]["conditions"] = dict(f1=c1, err=c2, fausses=c3)
        passe[n] = c1 and c2 and c3
    ok = [n for n in a.liste if passe[n]]
    adopte = max(ok, key=lambda n: REGLAGE[n]) if ok else None
    res = dict(tableau=t, reference="v5_030", seuil_f1=ref["moy_f1"] - 0.010, seuil_err=ref["moy_err"], passe=passe,
               adoption=adopte, reglage=REGLAGE)
    (D / "regle_adoption.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in noms:
        x = t[n]
        print(f"{n:24s} " + " ".join(f"{j} {x['f1'][j]:.4f}/{x['err'][j]:.3f}" for j in JUGES)
              + f" | moy F1 {x['moy_f1']:.4f} err {x['moy_err']:.3f} | sans seg F1 {x['moy_f1_sans_seg']:.4f} err {x['moy_err_sans_seg']:.3f}"
              + f" | fausses {x['fp']}/{x['arbres']} ({x['taux']:.2%})" + (f" | {x['conditions']} -> {passe[n]}" if n in passe else ""))
    print(f"seuil F1 {ref['moy_f1'] - 0.010:.4f} ; seuil erreur {ref['moy_err']:.3f} ; adoption : {adopte or 'aucune'}")


if __name__ == "__main__":
    main()
