#!/usr/bin/env python3
"""Essai c16 (16/11) : tableaux de out/comptage/jour_1611/finalistes.md, lus dans out/comptage/jour_1611/mesures/*.json.
Applique la règle telle que l'a calculée notebooks/c16_mesure.py (avenant c16, section 4) ; aucun choix ici.
Classement des finalistes : moyenne des 5 F1 à 11 cm. Écrit out/comptage/jour_1611/tableaux.md.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/c16_finalistes.py
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
M = RACINE / "out/comptage/jour_1611/mesures"
ORDRE = ["v5", "c13a", "c15d", "c15b_a", "c15b_b", "c15b_c", "c15b_d", "c16_a", "c16_b", "c16_c", "c16_d"]
JEUX = ["dense", "plantain", "jeunes", "mm", "btd_val"]


def v(x, n=3):
    return "—" if x is None else f"{x:.{n}f}".replace(".", ",")


def oui(b):
    return {True: "oui", False: "**non**", None: "non mesuré"}[b]


def main():
    E = {n: json.loads((M / f"{n}.json").read_text(encoding="utf-8")) for n in ORDRE if (M / f"{n}.json").exists()}
    out = []
    out.append("### Réglage dégradé : F1 par jeu (dense / plantain / jeunes / MM / btd_val) et moyenne\n")
    out.append("| candidat | seuil | 8 cm | moy. 8 | 11 cm | **moy. 11** | 14 cm | moy. 14 |")
    out.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for n, e in E.items():
        if e.get("seuil") is None:
            out.append(f"| {n} | aucun | | | | | | |"); continue
        a = e["au_seuil"]
        cel = []
        for c in ("8", "11", "14"):
            cel += [" / ".join(v(a[c][f"f1_{j}"]) for j in JEUX), (f"**{v(a[c]['moyenne'], 4)}**" if c == "11" else v(a[c]["moyenne"], 4))]
        out.append(f"| {n} | {v(e['seuil'], 2)} | " + " | ".join(cel) + " |")
    out.append("\n### `val_negatifs` dégradé, agroforesterie (ReforesTree d'entraînement) et Ghana\n")
    out.append("| candidat | `val_negatifs` 8 / 11 / 14 cm | RT 11 cm : rappel des mères | RT 11 cm : pieds du v5 (5 cm) retrouvés | RT 8 / 14 cm : mères (info) | RT 8 / 14 cm : pieds du v5 (info) | Ghana 11 cm : F1 (rappel) |")
    out.append("| --- | --- | --- | --- | --- | --- | --- |")
    for n, e in E.items():
        if e.get("seuil") is None:
            continue
        a, r = e["au_seuil"], e["rt"]
        g = e.get("ghana_11")
        out.append(f"| {n} | " + " / ".join(f"{a[c]['fp_neg']} ({a[c]['taux_fp']:.2%})".replace(".", ",") for c in ("8", "11", "14"))
                   + f" | {v(r['11']['rappel_meres'])} | {v(r['11']['part_pieds_v5'])} | {v(r['8']['rappel_meres'])} / {v(r['14']['rappel_meres'])}"
                   + f" | {v(r['8']['part_pieds_v5'])} / {v(r['14']['part_pieds_v5'])} | "
                   + (f"{v(g['f1'])} ({v(g['rappel'])})" if g else "non mesuré") + " |")
    out.append("\n### Conditions de la règle 4.2\n")
    out.append("| candidat | 1. gain à 11 cm (≥ v5 + 0,030) | 2. pire perte par jeu (≥ −0,020) et moy. 8, 14 | 3. négatifs < 1 % | 4a. mères | 4b. pieds du v5 | 5. Ghana | **finaliste** |")
    out.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for n, e in E.items():
        if n == "v5":
            continue
        s = e.get("statut", {})
        if e.get("seuil") is None:
            out.append(f"| {n} | | | **non** (aucun seuil) | | | | **non** |"); continue
        g = s.get("c5_ghana") if "ghana_11" in e else None
        out.append(f"| {n} | {oui(s['c1_gain'])} | {oui(s['c2_pertes'])} ({v(s['pire_perte'])}, {s['pire_jeu'].replace('@', ' à ')} cm) | {oui(s['c3_negatifs'])}"
                   f" | {oui(s['c4a_meres'])} | {oui(s['c4b_pieds_v5'])} | {oui(g)} | **{'oui' if s.get('finaliste') else 'non'}** |")
    fin = sorted([n for n, e in E.items() if e.get("statut", {}).get("finaliste")], key=lambda n: -E[n]["au_seuil"]["11"]["moyenne"])
    out.append("\n### Classement des finalistes (moyenne à 11 cm)\n")
    for k, n in enumerate(fin, 1):
        out.append(f"{k}. `{n}` : {v(E[n]['au_seuil']['11']['moyenne'], 4)}")
    if not fin:
        out.append("aucun finaliste")
    manquants = [n for n in ORDRE if n not in E]
    if manquants:
        out.append(f"\nNon mesurés : {', '.join(manquants)}")
    (RACINE / "out/comptage/jour_1611/tableaux.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
