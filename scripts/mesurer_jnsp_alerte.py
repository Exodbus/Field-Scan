#!/usr/bin/env python3
"""Amendement 2 du protocole docs/protocole_maladies_cinq_classes.md : « je ne sais pas » avec P(malade) >= seuil
d'alerte devient « malade, non identifiée » (politique b) ? Règle : (b) si son coût en validation (2 x malades sans
alerte + saines en alerte ; « je ne sais pas » = sans alerte) est strictement plus bas que celui de la règle actuelle (a).
Modèle : la soupe (branche « proche »), ses seuils. Le reste est rapporté sans effet.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_jnsp_alerte.py
"""
import json
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
SEUILS = json.loads((RACINE / "modeles/maladies_soupe_v2_v8/poids/seuils.json").read_text(encoding="utf-8"))
FICHIERS = {"validation": RACINE / "out/maladies/dinov2_ft/predictions_soupe_validation.csv",
            "bananalsd": RACINE / "out/maladies/dinov2_ft/predictions_soupe_bananalsd.csv",
            **{j: RACINE / f"out/maladies/cinq_classes/predictions_soupe_{j}.csv" for j in ("tdtu", "psfd", "ethiopie")}}
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee"}
SAINES = {"validation": "saine", "bananalsd": "saine", "tdtu": "saine", "ethiopie": "saine", "psfd": None}


def politique_b(d):
    pm = 1 - d.p_saine
    r = d.reponse.copy()
    r[(r == "je_ne_sais_pas") & (pm >= SEUILS["seuil_alerte"])] = "malade_non_identifiee"
    return r


res = {}
for j, f in FICHIERS.items():
    d = pd.read_csv(f)
    malade = d.classe_vraie.ne("saine")
    for nom, rep in (("a", d.reponse), ("b", politique_b(d))):
        al = rep.isin(ALERTE)
        res[f"{j}_{nom}"] = dict(malades_sans_alerte=int((malade & ~al).sum()), n_malades=int(malade.sum()),
                                 saines_en_alerte=int((~malade & al).sum()), n_saines=int((~malade).sum()),
                                 cout=2 * int((malade & ~al).sum()) + int((~malade & al).sum()))
adopte = res["validation_b"]["cout"] < res["validation_a"]["cout"]
print(pd.DataFrame(res).T.to_string())
print("seuil d'alerte de la soupe :", SEUILS["seuil_alerte"], "| politique (b) adoptée :", adopte)
(RACINE / "out/maladies/cinq_classes/bilan_jnsp_alerte.json").write_text(json.dumps(dict(mesures=res, politique_b_adoptee=adopte),
                                                                                   ensure_ascii=False, indent=1), encoding="utf-8")
