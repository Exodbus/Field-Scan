#!/usr/bin/env python3
"""Écrit out/maladies/jour_1511/kaggle2/tableau_essais.md à partir de bilan_knn.json (M-kaggle2, 15/11).
Aucun calcul, aucune décision : mise en forme des chiffres du banc. `finalistes.md` est rédigé à la main à partir de ce tableau.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u notebooks/m15b_finalistes.py
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RACINE = Path(__file__).resolve().parents[1]
S = RACINE / "out/maladies/jour_1511/kaggle2"
b = json.loads((S / "bilan_knn.json").read_text(encoding="utf-8"))
JEUX = ["validation", "tdtu", "psfd", "ethiopie", "agrovision"]


def cel(p, j):
    x = p[j]
    return f"{x['msa']}" if j == "psfd" else f"{x['msa']} ; {x['sea']}"


lignes = ["| Essai | Famille | Coût de réglage | Val. | TDTU | PSFD | Éth. | AgroVisionBD | Ratées (5 jeux) | roamer | "
          "Perdues / rattrapées vs F1 | Temps / F1_bornes | Finaliste |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
for nom, s in b.items():
    if not isinstance(s, dict) or "par_jeu" not in s:
        continue
    p = s["par_jeu"]
    fam = "réf." if nom == "F1" else "C"
    per = "—" if nom == "F1" else f"{s['malades_perdues_vs_F1']} / {s['malades_rattrapees_vs_F1']}"
    t = "1,00" if nom == "F1" else f"{s['temps']['rapport_F1_bornes']:.2f}".replace(".", ",")
    fin = "—" if nom == "F1" else ("**oui**" if s["finaliste"] else
                                  "non (" + ", ".join(k for k, v in s["conditions"].items() if not v) + ")")
    lignes.append(f"| {nom} | {fam} | {s['cout_reglage']:.2f} | " + " | ".join(cel(p, j) for j in JEUX)
                  + f" | {s['msa_total5']} | {s['roamer_msa']} | {per} | {t} | {fin} |".replace(".", ",", 0))
texte = "\n".join(lignes)
au = b["auroc_knn"]
texte += "\n\nAUROC de P_kNN par k (choix sur validation + TDTU) : " + "; ".join(
    f"k = {k} : " + ", ".join(f"{j} {v:.3f}" for j, v in a.items()) for k, a in au.items()) + f" → k = {b['k']}."
texte += "\n\nAUROC de P_tête (information) : " + ", ".join(f"{j} {v:.3f}" for j, v in b["auroc_tete"].items()) + "."
(S / "tableau_essais.md").write_text(texte + "\n", encoding="utf-8")
print(texte)
