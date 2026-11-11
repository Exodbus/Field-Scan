#!/usr/bin/env python3
"""Amendement 3 du protocole docs/protocole_maladies_cinq_classes.md : politique (b) pour la branche « loin » (v2).
Décision sur les photos du robot de dev_loin (rôle apprentissage_loin), rapport sur val_loin robot et le téléphone.
Coût = 2 x malades sans alerte + saines en alerte ; « je ne sais pas » = sans alerte.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/mesurer_jnsp_loin.py
"""
import json, sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

LOIN = Path("C:/Users/coren/kaggle_tmp/photos_loin")
SORTIE = RACINE / "out/maladies/cinq_classes"
l = pd.read_csv(LOIN / "liste_photos_loin.csv")
l = l[l.role.isin(["apprentissage_loin", "indicatif_robot_val_loin", "mesure_loin_telephone"])].reset_index(drop=True)
cache = SORTIE / "predictions_v2_photos_loin.csv"
m = maladies.charger_convnext(RACINE / "modeles/maladies_binome/maladies_v2/poids")
if cache.exists():
    d = pd.read_csv(cache)
else:
    P = maladies.predire_convnext([str(LOIN / f) for f in l.fichier], m)
    rep, pm, conf, _ = maladies.decider_convnext(P, m)
    d = l.assign(p_saine=P[:, 0], p_malade=pm, reponse=rep)
    d.to_csv(cache, index=False)
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee"}
d["malade"] = ~d.source.str.contains("healthy")
d["reponse_b"] = d.reponse.where(~((d.reponse == "je_ne_sais_pas") & (d.p_malade >= m["seuil_alerte"])), "malade_non_identifiee")
res = {}
for role, g in d.groupby("role"):
    for pol in ("reponse", "reponse_b"):
        al = g[pol].isin(ALERTE)
        res[f"{role}_{'a' if pol == 'reponse' else 'b'}"] = dict(
            malades_sans_alerte=int((g.malade & ~al).sum()), n_malades=int(g.malade.sum()),
            saines_en_alerte=int((~g.malade & al).sum()), n_saines=int((~g.malade).sum()),
            cout=2 * int((g.malade & ~al).sum()) + int((~g.malade & al).sum()))
adopte = res["apprentissage_loin_b"]["cout"] < res["apprentissage_loin_a"]["cout"]
print(pd.DataFrame(res).T.to_string())
print("seuil d'alerte de la v2 :", m["seuil_alerte"], "| politique (b) adoptée pour la branche « loin » :", adopte)
(SORTIE / "bilan_jnsp_loin.json").write_text(json.dumps(dict(mesures=res, politique_b_adoptee=adopte), ensure_ascii=False, indent=1),
                                            encoding="utf-8")
