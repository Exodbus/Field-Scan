#!/usr/bin/env python3
"""Essai c16 (16/11) : tableaux et règle de docs/journee_2026-11-16/avenant_c16_juges.md (section 4), lus dans
out/comptage/jour_1611/juges/mesure_d<cm>_<jeu>.json. La décision ne lit que 11 cm ; 8 et 14 cm sont de l'information.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/c16_juges_regle.py
Écrit out/comptage/jour_1611/juges/regle.json et affiche les tableaux (Markdown).
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
J = RACINE / "out/comptage/jour_1611/juges"
NOMS = {"segmento": "segmento est", "cg": "CG, mères seules", "banano": "`banano_dense`"}


def v(x, n=3):
    return f"{x:.{n}f}".replace(".", ",")


def lire(cm, jeu):
    p = J / f"mesure_d{cm}_{jeu}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main():
    out = []
    for cm in (11, 8, 14):
        if not all(lire(cm, j) for j in ("segmento", "cg", "banano", "neg_test")):
            out.append(f"\n### {cm} cm/px : non lu\n"); continue
        out.append(f"\n### {cm} cm/px" + (" (décide)" if cm == 11 else " (information)") + "\n")
        out.append("| juge | modèle (seuil) | F1 | rappel | précision | détectés / annotés | erreur de compte |")
        out.append("| --- | --- | --- | --- | --- | --- | --- |")
        for j in ("segmento", "cg", "banano"):
            r = lire(cm, j)["candidats"]
            for m in ("v5", "c16_a"):
                x = r[m]
                out.append(f"| {NOMS[j]} | {m} ({v(x['seuil'], 2)}) | {v(x['f1'], 4)} | {v(x['r'])} | {v(x['p'])} | "
                           f"{x['detectes']} / {x['reels']} | {v(x['err_compte'])} |")
        n = lire(cm, "neg_test")["candidats"]
        out.append("\n| `test_negatifs` | fausses détections / arbres | taux |\n| --- | --- | --- |")
        for m in ("v5", "c16_a"):
            out.append(f"| {m} ({v(n[m]['seuil'], 2)}) | {n[m]['fp']} / {n[m]['arbres']} | {n[m]['taux']:.2%} |".replace(".", ","))
        moy = {m: sum(lire(cm, j)["candidats"][m]["f1"] for j in NOMS) / 3 for m in ("v5", "c16_a")}
        err = {m: sum(lire(cm, j)["candidats"][m]["err_compte"] for j in NOMS) / 3 for m in ("v5", "c16_a")}
        out.append(f"\nMoyenne des F1 des trois juges : v5 {v(moy['v5'], 4)}, c16_a {v(moy['c16_a'], 4)} ; "
                   f"erreur de compte moyenne : v5 {v(err['v5'])}, c16_a {v(err['c16_a'])}.")
        if cm == 11:
            cg = {m: lire(11, "cg")["candidats"][m]["f1"] for m in ("v5", "c16_a")}
            regle = dict(
                a=dict(valeur=moy["c16_a"], limite=moy["v5"] + 0.030, passe=moy["c16_a"] >= moy["v5"] + 0.030),
                b=dict(valeur=cg["c16_a"], limite=cg["v5"] - 0.020, passe=cg["c16_a"] >= cg["v5"] - 0.020),
                c=dict(valeur=err["c16_a"], limite=err["v5"], passe=err["c16_a"] <= err["v5"]),
                d=dict(valeur=n["c16_a"]["taux"], limite=0.01, passe=n["c16_a"]["taux"] < 0.01))
            regle["decision"] = "adoption proposée à Corentin" if all(regle[k]["passe"] for k in "abcd") else "non adopté"
            (J / "regle.json").write_text(json.dumps(regle, indent=1, ensure_ascii=False), encoding="utf-8")
            out.append("\n| condition (11 cm) | c16_a | limite | remplie |\n| --- | --- | --- | --- |")
            lib = {"a": "(a) moyenne des F1 ≥ v5 + 0,030", "b": "(b) CG ≥ v5 − 0,020", "c": "(c) erreur de compte ≤ v5",
                   "d": "(d) `test_negatifs` < 1 %"}
            for k in "abcd":
                f = (lambda x: f"{x:.2%}".replace(".", ",")) if k == "d" else (lambda x: v(x, 4))
                out.append(f"| {lib[k]} | {f(regle[k]['valeur'])} | {f(regle[k]['limite'])} | {'oui' if regle[k]['passe'] else '**non**'} |")
            out.append(f"\n**Décision selon la règle : {regle['decision']}.**")
    print("\n".join(out))


if __name__ == "__main__":
    main()
