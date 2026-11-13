#!/usr/bin/env python3
"""Tableau des essais v6 (agent C-entraîneur) : lit out/comptage_v6/kaggle/<candidat>/centres_5cm_<candidat>.json (réglage seulement)
et écrit out/comptage_v6/kaggle/tableau_essais.md. Applique la règle « finaliste » 3.4 avec la référence v5 écrite au journal (23 h 37) :
moyenne des 5 F1 > 0,7923 + 0,010 ; aucun jeu sous (v5 à 0,20) − 0,020 ; erreur de compte ≤ 0,262."""
import json, sys
from pathlib import Path
RACINE = Path(__file__).resolve().parents[1]
K = RACINE / "out/comptage_v6/kaggle"
JEUX = ("dense", "plantain", "jeunes", "mm", "espace")
V5_20 = dict(dense=0.759, plantain=0.842, jeunes=0.869, mm=0.776, espace=0.716)     # v5 à 0,20 (règle 3.4)
V5_30 = dict(dense=0.779, plantain=0.886, jeunes=0.893, mm=0.857, espace=0.473)     # v5 adopté (0,30)
# lecture exacte depuis le fichier de référence
import csv
ref = {round(float(r["seuil"]), 2): r for r in csv.DictReader(open(K / "reference_v5/reglage.csv", encoding="utf-8"))}
for s, d in ((0.2, V5_20), (0.3, V5_30)):
    for j in JEUX:
        d[j] = float(ref[s][f"f1_{j}"])
MOY_REF, ERR_REF = float(ref[0.2]["moyenne"]), min(float(ref[0.2]["erreur_compte"]), float(ref[0.3]["erreur_compte"]))
lignes, fin = [], []
for js in sorted(K.glob("*/centres_5cm_*.json")):
    if js.parent.name.startswith("lot"):
        continue
    d = json.load(open(js, encoding="utf-8")); r = d["retenu"]
    m4 = sum(r[f"f1_{j}"] for j in JEUX[:4]) / 4
    pire = min(r[f"f1_{j}"] - V5_20[j] for j in JEUX)
    ok = r["moyenne"] > MOY_REF + 0.010 and pire >= -0.020 and r["erreur_compte"] <= ERR_REF and r["taux_fp_neg"] < 0.01
    info = f"{r['info_f1_finca']:.3f}" if "info_f1_finca" in r else "-"
    lignes.append(f"| {js.parent.name} | {r['seuil']} | " + " | ".join(f"{r['f1_' + j]:.3f}" for j in JEUX) +
                  f" | **{r['moyenne']:.4f}** | {m4:.4f} | {r['erreur_compte']:.3f} | {r['fp_neg']} ({r['taux_fp_neg']:.2%}) | "
                  + " ".join(f"{r['f1_' + j] - V5_30[j]:+.3f}" for j in JEUX) + f" | {info} | {'oui' if ok else 'non'} |")
    if ok:
        fin.append((r["moyenne"], js.parent.name))
entete = ("| candidat | seuil | dense | plantain | jeunes | MM | espacée | moyenne 5 | moyenne 4 anciennes | erreur de compte | sans bananier | "
          "écart au v5 (0,30) par jeu, dans l'ordre | finca (info) | finaliste 3.4 |\n|" + " --- |" * 14)
m4_30 = sum(V5_30[j] for j in JEUX[:4]) / 4
texte = (f"# Essais v6 du comptage (C-entraîneur) : réglage seulement\n\nRéférence v5 (même code, ONNX) : règle 3.4 seuil 0,20, moyenne 5 = {MOY_REF:.4f} ; "
         f"v5 adopté (0,30) : moyenne 4 anciennes = {m4_30:.4f}. Seuil finaliste : moyenne > {MOY_REF + 0.010:.4f}, aucun jeu sous v5(0,20) − 0,020, "
         f"erreur de compte ≤ {ERR_REF:.3f}.\n\n{entete}\n" + "\n".join(lignes) + "\n")
(K / "tableau_essais.md").write_text(texte, encoding="utf-8")
print(texte)
