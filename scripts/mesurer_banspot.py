#!/usr/bin/env python3
"""Test BanSpot (Kerala) de la chaîne maladies installée, une seule fois (docs/protocole_maladies_v10c_banspot.md, section 6).

Chaîne de config.yaml : aiguilleur ; « proche » -> v10b ; « loin » -> v2 (politique b). Rapporté : ancienne chaîne
(soupe en gros plan). Photos : les 1 292 de la liste du binôme, lues dans l'archive d'origine (data/raw/banspot).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/mesurer_banspot.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

SORTIE = RACINE / "out/maladies/banspot"
SORTIE.mkdir(parents=True, exist_ok=True)
CFG = yaml.safe_load((RACINE / "config.yaml").read_text(encoding="utf-8"))["maladies"]
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis", "a_verifier"}

liste = pd.read_csv(RACINE / "data/raw/partage_binome_v10b/partage_corentin_2026-11-11/banspot_liste_test.csv")
liste["photo"] = [str(RACINE / "data/raw/banspot/DATASET" / Path(f).parent.name / Path(f).name) for f in liste.fichier]
assert all(Path(p).exists() for p in liste.photo), "photos introuvables"
f = list(liste.photo)


def calcul(nom, fonction):
    chemin = SORTIE / f"{nom}.npy"
    if chemin.exists():
        return np.load(chemin)
    t = time.time(); r = fonction(); np.save(chemin, r)
    print(f"{nom} : {(time.time() - t) / 60:.1f} min", flush=True)
    return r


pl = calcul("p_loin", lambda: maladies.p_loin(f, maladies.charger_aiguilleur(RACINE / CFG["aiguilleur"]), lot=32))
loin = pl >= 0.5
m_proche = maladies.charger_convnext(RACINE / CFG["modele"]); m_proche["jnsp_alerte"] = bool(CFG.get("jnsp_alerte"))
m_loin = maladies.charger_convnext(RACINE / CFG["modele_loin"]); m_loin["jnsp_alerte"] = bool(CFG.get("jnsp_alerte_loin"))
m_soupe = maladies.charger_convnext(RACINE / "modeles/maladies_soupe_v2_v8/poids"); m_soupe["jnsp_alerte"] = True
P10 = calcul("p_v10b", lambda: maladies.predire_convnext(f, m_proche))
Pv2 = calcul("p_v2", lambda: maladies.predire_convnext(f, m_loin))
Pso = calcul("p_soupe", lambda: maladies.predire_convnext(f, m_soupe))
r_loin = maladies.decider_convnext(Pv2, m_loin)[0]
chaines = {"installee_v10b": np.where(loin, r_loin, maladies.decider_convnext(P10, m_proche)[0]),
           "ancienne_soupe": np.where(loin, r_loin, maladies.decider_convnext(Pso, m_soupe)[0]),
           "v10b_seule_sans_aiguilleur": maladies.decider_convnext(P10, m_proche)[0]}
malade = liste.classe.eq("taches").values
bilan = dict(photos=len(liste), malades=int(malade.sum()), saines=int((~malade).sum()), photos_loin=int(loin.sum()))
for nom, r in chaines.items():
    al = np.isin(r, list(ALERTE))
    bilan[nom] = dict(malades_sans_alerte=int((malade & ~al).sum()), saines_en_alerte=int((~malade & al).sum()),
                      saines_a_verifier=int((~malade & (r == "a_verifier")).sum()),
                      reponses_malades=pd.Series(r[malade]).value_counts().to_dict(),
                      reponses_saines=pd.Series(r[~malade]).value_counts().to_dict(),
                      par_ferme={fe: dict(malades_sans_alerte=int((malade & ~al & (liste.ferme == fe)).sum()),
                                          saines_en_alerte=int((~malade & al & (liste.ferme == fe)).sum()))
                                 for fe in sorted(liste.ferme.unique())})
liste.assign(p_loin=pl.round(4), **{f"reponse_{k}": v for k, v in chaines.items()}).drop(columns="photo").to_csv(
    SORTIE / "reponses_banspot.csv", index=False)
(SORTIE / "bilan_banspot.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(bilan, ensure_ascii=False, indent=1))
