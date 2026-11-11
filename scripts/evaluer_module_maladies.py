#!/usr/bin/env python3
"""Rapport (sans effet sur aucune décision) : module maladies complet de la nuit du 9 au 10 novembre, contre l'ancienne
chaîne (v2 seule, règle de la v2).

Module : aiguilleur loin / près ; photos « loin » -> v2 avec la politique (b) (amendement 3) ; photos « proche » -> soupe
avec la politique (b) de l'amendement 2 (« je ne sais pas » avec P(malade) >= seuil d'alerte -> « malade, non identifiée »).
Une photo est « en alerte » si la réponse est une maladie ou « malade, non identifiée ».
P(loin) : caractéristiques DINOv2 enregistrées (validation, BananaLSD) ou calculées par le module (TDTU, PSFD, Éthiopie).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/evaluer_module_maladies.py
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

DOS = RACINE / "out/maladies/cinq_classes"
ANCIENS = RACINE / "out/maladies/dinov2_ft"
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis"}
SOUPE = json.loads((RACINE / "modeles/maladies_soupe_v2_v8/poids/seuils.json").read_text(encoding="utf-8"))
V2 = json.loads((RACINE / "modeles/maladies_binome/maladies_v2/poids/seuils.json").read_text(encoding="utf-8"))
A = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")


def lire(m, j):
    return pd.read_csv((ANCIENS if j in ("validation", "bananalsd") else DOS) / f"predictions_{m}_{j}.csv")


def p_loin(j, chemins):
    cache = DOS / f"p_loin_{j}.csv"
    if cache.exists():
        c = pd.read_csv(cache)
        assert list(c.chemin) == list(chemins)
        return c.p_loin.values
    if j in ("validation", "bananalsd"):
        d = np.load(RACINE / f"out/maladies/dinov2/dinov2_{j}.npz", allow_pickle=True)
        assert list(d["chemin"]) == list(chemins)
        x = d["car"][0].astype(np.float64)
        z = ((x - A["moyenne"]) / A["ecart"]) @ A["poids"].T + A["biais"]
        z -= z.max(1, keepdims=True)
        p = np.exp(z[:, 1]) / np.exp(z).sum(1)
    else:
        f = [str(RACINE / c) if c.startswith("data/") else str(RACINE / "out/maladies/maladies_nuit" / c) for c in chemins]
        p = maladies.p_loin(f, A, lot=32)
    pd.DataFrame(dict(chemin=chemins, p_loin=p)).to_csv(cache, index=False)
    return p


def stats(rep, d):
    al, v = pd.Series(rep).isin(ALERTE).values, np.array(d.classe_vraie.values, dtype=object)
    rep = np.array(rep, dtype=object)
    malade = ~np.isin(v, ["saine"])
    out = dict(malades_sans_alerte=f"{int((malade & ~al).sum())}/{int(malade.sum())}",
               saines_en_alerte=f"{int((~malade & al).sum())}/{int((~malade).sum())}")
    sig = np.isin(v, ["cercosporiose_noire", "black_sigatoka", "sigatoka"])
    out["sigatoka_nommee"] = f"{int((sig & (rep == 'cercosporiose_noire')).sum())}/{int(sig.sum())}"
    inc = np.array([str(x).startswith("inconnue") for x in v])
    if inc.any():
        out["inconnues_dites_sigatoka"] = f"{int((inc & (rep == 'cercosporiose_noire')).sum())}/{int(inc.sum())}"
    return out


res = {}
for j in ("validation", "bananalsd", "tdtu", "psfd", "ethiopie"):
    v2, so = lire("v2", j), lire("soupe", j)
    assert list(v2.chemin) == list(so.chemin)
    pl = p_loin(j, list(v2.chemin))
    proche = so.reponse.values.astype(object)
    proche[(proche == "je_ne_sais_pas") & (1 - so.p_saine.values >= SOUPE["seuil_alerte"])] = "malade_non_identifiee"
    loin = v2.reponse.values.astype(object)   # amendement 3 : politique (b) aussi pour la branche « loin »
    loin[(loin == "je_ne_sais_pas") & (1 - v2.p_saine.values >= V2["seuil_alerte"])] = "malade_non_identifiee"
    module = np.where(pl >= 0.5, loin, proche)
    res[j] = dict(photos_loin=f"{int((pl >= 0.5).sum())}/{len(pl)}", ancienne_chaine_v2=stats(v2.reponse.values, v2),
                  module_nuit=stats(module, v2))
(DOS / "bilan_module_complet.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
lignes = []
for j, r in res.items():
    for k in r["ancienne_chaine_v2"]:
        lignes.append(dict(jeu=j, mesure=k, ancienne_chaine=r["ancienne_chaine_v2"][k], module_nuit=r["module_nuit"][k]))
    lignes.append(dict(jeu=j, mesure="photos aiguillées « loin »", ancienne_chaine="", module_nuit=r["photos_loin"]))
t = pd.DataFrame(lignes)
t.to_csv(DOS / "tableau_module_complet.csv", index=False)
print(t.to_string(index=False))
