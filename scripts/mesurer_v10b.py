#!/usr/bin/env python3
"""Mesure unique de docs/protocole_maladies_v10b.md (amendement 1) : garde-fou G1 sur la validation, puis rapport.

Module actuel : aiguilleur ; « loin » -> v2, politique (b) ; « proche » -> soupe, politique (b).
Module v10b : même aiguilleur et même branche « loin » ; « proche » -> v10b, avec la décision de la chaîne
(fieldscan/modules/maladies.py : règle B, seuil de la v11, doute restant -> « à vérifier », qui donne une alerte).
Une photo est en alerte si sa réponse est une maladie, « malade, non identifiée » ou « à vérifier ».

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -u scripts/mesurer_v10b.py [jeu ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.modules import maladies  # noqa: E402

V10B, DOS, ANCIENS = RACINE / "out/maladies/v10b", RACINE / "out/maladies/cinq_classes", RACINE / "out/maladies/dinov2_ft"
ALERTE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee", "cordana", "pestalotiopsis", "a_verifier"}
LIMITE_G1 = 9 + 10   # module actuel en validation : 9 malades sans alerte sur 2 001 (protocole, section 3)


def seuils(dossier, **en_plus):
    s = json.loads((RACINE / dossier / "seuils.json").read_text(encoding="utf-8"))
    mb = (s.get("membres") or [{}])[0]
    return dict(classes=[maladies.NOMS_CHAINE[c] for c in s["classes"]], seuil=float(s["seuil_confiance"]),
                seuil_alerte=float(s["seuil_alerte"]), seuil_nom=float(s["seuil_nom"]), nommer_autre=not mb,
                regle_b=bool(s.get("regle_b")), seuil_inconnu_malade=s.get("seuil_inconnu_malade"), **en_plus)


M_SOUPE = seuils("modeles/maladies_soupe_v2_v8/poids", jnsp_alerte=True)
M_V2 = seuils("modeles/maladies_binome/maladies_v2/poids", jnsp_alerte=True)
M_V10B = seuils("modeles/maladies_binome/v10b", jnsp_alerte=True)


def probas(df):
    cols = [c for c in ("p_saine", "p_black_sigatoka", "p_fusarium", "p_autre") if c in df.columns]
    return df[cols].to_numpy(dtype="float64")


def lire(m, j):
    if j == "cordana_perou":
        return pd.read_csv(V10B / f"predictions_{m}_{j}.csv")
    if m == "v10b":
        return pd.read_csv(V10B / f"predictions_v10b_{j}.csv")
    return pd.read_csv((ANCIENS if j in ("validation", "bananalsd") else DOS) / f"predictions_{m}_{j}.csv")


def p_loin(j):
    return pd.read_csv((V10B if j == "cordana_perou" else DOS) / f"p_loin_{j}.csv")


def stats(rep, v):
    rep, v = np.array(rep, dtype=object), np.array(v, dtype=object)
    al, malade = np.isin(rep, list(ALERTE)), ~np.isin(v, ["saine"])
    out = dict(malades_sans_alerte=f"{int((malade & ~al).sum())}/{int(malade.sum())}",
               saines_en_alerte=f"{int((~malade & al).sum())}/{int((~malade).sum())}")
    sig = np.isin(v, ["cercosporiose_noire", "black_sigatoka", "sigatoka"])
    if sig.any():
        out["sigatoka_nommee"] = f"{int((sig & (rep == 'cercosporiose_noire')).sum())}/{int(sig.sum())}"
    inc = np.array([str(x).startswith("inconnue") for x in v])
    if inc.any():
        out["inconnues_en_alerte"] = f"{int((inc & al).sum())}/{int(inc.sum())}"
        out["inconnues_dites_sigatoka"] = f"{int((inc & (rep == 'cercosporiose_noire')).sum())}/{int(inc.sum())}"
    out["a_verifier"] = int((rep == "a_verifier").sum())
    out["malade_non_identifiee"] = int((rep == "malade_non_identifiee").sum())
    return out


def mesurer(j):
    v2, so, v10 = lire("v2", j), lire("soupe", j), lire("v10b", j)
    pl = p_loin(j)
    assert list(v2.chemin) == list(so.chemin) == list(v10.chemin) == list(pl.chemin), j
    loin = pl.p_loin.values >= 0.5
    r_loin = maladies.decider_convnext(probas(v2), M_V2)[0]
    actuel = np.where(loin, r_loin, maladies.decider_convnext(probas(so), M_SOUPE)[0])
    nouveau = np.where(loin, r_loin, maladies.decider_convnext(probas(v10), M_V10B)[0])
    par_classe = {c: dict(actuel=pd.Series(actuel[v2.classe_vraie == c]).value_counts().to_dict(),
                          v10b=pd.Series(nouveau[v2.classe_vraie == c]).value_counts().to_dict())
                  for c in sorted(v2.classe_vraie.unique())}
    return dict(photos=len(v2), photos_loin=int(loin.sum()), module_actuel=stats(actuel, v2.classe_vraie),
                module_v10b=stats(nouveau, v2.classe_vraie), reponses_par_classe=par_classe)


jeux = sys.argv[1:] or ["validation", "cordana_perou", "tdtu", "psfd", "ethiopie", "bananalsd"]
bilan_f = V10B / "bilan_v10b.json"
bilan = json.loads(bilan_f.read_text(encoding="utf-8")) if bilan_f.exists() else {}
for j in jeux:
    bilan[j] = mesurer(j)
    if j == "validation":
        n = int(bilan[j]["module_v10b"]["malades_sans_alerte"].split("/")[0])
        bilan[j]["garde_fou_G1"] = dict(limite=LIMITE_G1, valeur=n, rempli=n <= LIMITE_G1)
    if j == "bananalsd":
        bilan[j]["note"] = "vu par la v10b : 670 photos dans son apprentissage, 223 dans sa validation"
    print(j, json.dumps({k: v for k, v in bilan[j].items() if k != "reponses_par_classe"}, ensure_ascii=False), flush=True)
bilan_f.write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
