#!/usr/bin/env python3
"""Juge comptage, 15/11/2026 : tableaux et règle d'adoption du plan du 13/11 (5.3, qui renvoie à 3.4), sans rien régler.
Reprise de scripts/juge_1311_c_regle.py, avec la liste gelée du 15/11 (out/controle_jour_1511/liste_gelee.md).

Règle telle qu'écrite (docs/plan_nuit_2026-11-13.md, 5.3), valeurs FIXES du plan :
  moyenne des F1 de segmento est, CG et banano_dense >= 0,5901 ;
  erreur de compte (moyenne des 3 juges) <= 0,382 ;
  test_negatifs < 1 % ;
entre finalistes qui passent : la meilleure moyenne de réglage (liste gelée : CC1 0,8886, c15d 0,8822).
Information (ne change pas la règle) : moyennes sans segmento est, comme le 14/11.
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/juge_1511_c_regle.py
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
D = RACINE / "out/controle_jour_1511/juge_c"
JUGES = ["segmento", "cg", "banano"]
LISTE = ["CC1_v5h_50", "c15d"]
REGLAGE = {"CC1_v5h_50": 0.8886, "c15d": 0.8822, "v5_030": 0.7777}
SEUIL_F1, SEUIL_ERR, SEUIL_FAUSSES = 0.5901, 0.382, 0.01


def main():
    M = {j: json.loads((D / f"mesure_{j}.json").read_text(encoding="utf-8"))["candidats"] for j in JUGES + ["neg_test"]}
    t = {}
    for n in LISTE + ["v5_030"]:
        f1 = {j: M[j][n]["f1"] for j in JUGES}
        er = {j: M[j][n]["err_compte"] for j in JUGES}
        t[n] = dict(f1=f1, err=er, moy_f1=sum(f1.values()) / 3, moy_err=sum(er.values()) / 3,
                    moy_f1_sans_seg=(f1["cg"] + f1["banano"]) / 2, moy_err_sans_seg=(er["cg"] + er["banano"]) / 2,
                    detail={j: {k: M[j][n][k] for k in ("vp", "fp", "fn", "detectes", "reels", "p", "r")} for j in JUGES},
                    fp=M["neg_test"][n]["fp"], arbres=M["neg_test"][n]["arbres"], taux=M["neg_test"][n]["taux"])
    passe = {}
    for n in LISTE:
        c = dict(f1=t[n]["moy_f1"] >= SEUIL_F1, err=t[n]["moy_err"] <= SEUIL_ERR, fausses=t[n]["taux"] < SEUIL_FAUSSES)
        t[n]["conditions"] = c
        passe[n] = all(c.values())
    ok = [n for n in LISTE if passe[n]]
    adopte = max(ok, key=lambda n: REGLAGE[n]) if ok else None
    res = dict(tableau=t, seuils=dict(f1=SEUIL_F1, err=SEUIL_ERR, fausses=SEUIL_FAUSSES), passe=passe, adoption=adopte,
               reglage=REGLAGE, note="juges RELUS (plan du 13/11, section 3) ; banana_trees_kp non relu")
    (D / "regle_adoption.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in LISTE + ["v5_030"]:
        x = t[n]
        print(f"{n:12s} " + " ".join(f"{j} {x['f1'][j]:.4f}/{x['err'][j]:.3f}" for j in JUGES)
              + f" | moy F1 {x['moy_f1']:.4f} err {x['moy_err']:.3f} | sans seg F1 {x['moy_f1_sans_seg']:.4f} err {x['moy_err_sans_seg']:.3f}"
              + f" | fausses {x['fp']}/{x['arbres']} ({x['taux']:.2%})"
              + (f" | {x['conditions']} -> {passe[n]}" if n in passe else ""))
    print(f"seuils F1 {SEUIL_F1} ; erreur {SEUIL_ERR} ; fausses < 1 % ; adoption : {adopte or 'aucune'}")


if __name__ == "__main__":
    main()
