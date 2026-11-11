#!/usr/bin/env python3
"""Contrôle d'intégration du module maladies (docs/protocole_maladies_cinq_classes.md, section 4).

1. Sur 20 photos de validation (tirage fixe, graine 2026), les probabilités et réponses de fieldscan/modules/maladies.py
   pour le modèle « proche » doivent égaler celles du fichier de prédictions du modèle (10⁻³ près, réponses identiques).
2. L'aiguilleur enregistré envoie ces 20 photos vers « proche » et 10 photos de plantes entières (téléphone ROAMER, rôle
   mesure_loin_telephone) vers « loin », comme dans la mesure du protocole « deux branches ».
3. executer() tourne de bout en bout sur ces 30 photos avec un contexte minimal (sans GPS) et écrit maladies_photos.csv.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/verifier_module_maladies.py DOSSIER_MODELE PREDICTIONS_VALIDATION.csv
"""
import json, logging, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

dossier, fichier_val = Path(sys.argv[1]), Path(sys.argv[2])
v = pd.read_csv(fichier_val).sample(20, random_state=2026)
chemins = [str(RACINE / c) for c in v.chemin]
m = maladies.charger_convnext(dossier)
t0 = time.time()
P = maladies.predire_convnext(chemins, m)
rep, *_ = maladies.decider_convnext(P, m)
cols = [c for c in v.columns if c.startswith("p_")]
ecart = float(np.abs(P - v[cols].values).max())
attendu = v.reponse.replace({"inconnu": "je_ne_sais_pas"}).values
res = dict(ecart_max_probas=ecart, reponses_identiques=bool((rep == attendu).all()), secondes_par_photo=round((time.time() - t0) / 20, 2))
l = pd.read_csv("C:/Users/coren/kaggle_tmp/photos_loin/liste_photos_loin.csv")
loin = [str(Path("C:/Users/coren/kaggle_tmp/photos_loin") / f) for f in l[l.role.eq("mesure_loin_telephone")].sample(10, random_state=2026).fichier]
a = maladies.charger_aiguilleur(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz")
pl = maladies.p_loin(chemins + loin, a)
res["aiguilleur_proche_sur_validation"] = int((pl[:20] < 0.5).sum())
res["aiguilleur_loin_sur_plantes"] = int((pl[20:] >= 0.5).sum())
from fieldscan import config as _config  # noqa: E402
reglages = _config.charger(RACINE / "config.yaml")
reglages["maladies"].update(modele=str(dossier), modele_loin=str(RACINE / "modeles/maladies_binome/maladies_v2/poids"),
                            aiguilleur=str(RACINE / "modeles/maladies_aiguilleur/aiguilleur.npz"))
with tempfile.TemporaryDirectory() as tmp:
    ctx = SimpleNamespace(reglages=reglages, sortie=Path(tmp), journal=logging.getLogger("verif"),
                          inventaire=SimpleNamespace(photos=[SimpleNamespace(chemin=c, lat=None, lon=None) for c in chemins + loin]),
                          parcelles=gpd.GeoDataFrame(dict(parcelle_id=[]), geometry=[], crs="EPSG:4326"))
    r = maladies.executer(ctx)
    tab = pd.read_csv(Path(tmp) / "maladies_photos.csv")
    res["executer_branches"] = tab.branche.value_counts().to_dict()
    # réponses attendues de la chaîne : celles du modèle, plus la politique (b) de l'amendement 2 si jnsp_alerte est vrai
    rep_b = rep.astype(object)
    if reglages["maladies"].get("jnsp_alerte"):
        rep_b[(rep == "je_ne_sais_pas") & (1 - P[:, 0] >= m["seuil_alerte"])] = "malade_non_identifiee"
    res["executer_reponses_proches_identiques"] = bool((tab.reponse.values[:20] == rep_b).all())
    res["politique_b_photos_changees"] = int((rep_b != rep).sum())
    res["ecarts"] = [(a, b) for a, b in zip(tab.reponse.values[:20], rep_b) if a != b]
    res["executer_reponses"] = r.resume["reponses"]
print(json.dumps(res, ensure_ascii=False, indent=1))
ok = ecart < 1e-3 and res["reponses_identiques"] and res["aiguilleur_proche_sur_validation"] == 20 and res["executer_reponses_proches_identiques"]
print("CONTRÔLE D'INTÉGRATION :", "RÉUSSI" if ok else "ÉCHEC")
