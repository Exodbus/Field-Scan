#!/usr/bin/env python3
"""Règle d'adoption de la v5 (docs/protocole_maladies_v3_convnext.md, section 5, amendement 1), même code pour la v2
et la v5, chacune avec ses propres seuils (décision prise dans le carnet Kaggle affilecorentin/predictions-adoption-v5-v7).

Validation Tanzanie 2022-2023 (3 001) : malades dites saines (v5 <= v2 + 0,5 point) ; fausses alertes sur les saines
(v5 <= v2 + 1 point) ; maladie nommée juste quand elle est nommée (v5 >= 95 %).
BananaLSD (897) : Sigatoka nommée (v5 >= v2 - 2 points) ; saines bien classées (v5 >= v2 - 2 points) ; inconnues
(Cordana, Pestalotiopsis) dites saines (v5 <= v2 + 1 point). Rapporté sans effet : inconnues dites Sigatoka, et dites
« malade, non identifiée » ou « je ne sais pas ».

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_adoption_v5.py --dossier out/maladies/kaggle_adoption_v5
"""
import argparse
import json
from pathlib import Path

import pandas as pd

MALADE = {"cercosporiose_noire", "fusariose", "malade_non_identifiee"}
NOMMEE = {"cercosporiose_noire", "fusariose"}


def part(masque, total):
    n = int(total.sum())
    return dict(k=int((masque & total).sum()), n=n, part=round(float((masque & total).sum()) / n, 4) if n else None)


def mesures(dossier, modele):
    v = pd.read_csv(Path(dossier) / f"predictions_{modele}_validation.csv")
    b = pd.read_csv(Path(dossier) / f"predictions_{modele}_bananalsd.csv")
    vm, vs = v.classe_vraie.ne("saine"), v.classe_vraie.eq("saine")
    nommee = v.reponse.isin(NOMMEE) & vm
    bi = b.classe_vraie.str.startswith("inconnue")
    return {
        "validation_malades_dites_saines": part(v.reponse.eq("saine"), vm),
        "validation_fausses_alertes": part(v.reponse.isin(MALADE), vs),
        "validation_nommee_juste": part(v.reponse.eq(v.classe_vraie), nommee),
        "bananalsd_sigatoka_nommee": part(b.reponse.eq("cercosporiose_noire"), b.classe_vraie.eq("cercosporiose_noire")),
        "bananalsd_saines_bien_classees": part(b.reponse.eq("saine"), b.classe_vraie.eq("saine")),
        "bananalsd_inconnues_dites_saines": part(b.reponse.eq("saine"), bi),
        "bananalsd_inconnues_dites_sigatoka": part(b.reponse.eq("cercosporiose_noire"), bi),
        "bananalsd_inconnues_non_identifiees_ou_jnsp": part(b.reponse.isin(["malade_non_identifiee", "je_ne_sais_pas"]), bi),
        "validation_matrice": pd.crosstab(v.classe_vraie, v.reponse).to_dict("index"),
        "bananalsd_matrice": pd.crosstab(b.classe_vraie, b.reponse).to_dict("index"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default="out/maladies/kaggle_adoption_v5")
    a = ap.parse_args(argv)
    m2, m5 = mesures(a.dossier, "v2"), mesures(a.dossier, "v5")
    p = lambda m, k: m[k]["part"]  # noqa: E731
    conditions = {
        "validation_malades_dites_saines <= v2 + 0,005": p(m5, "validation_malades_dites_saines") <= p(m2, "validation_malades_dites_saines") + 0.005,
        "validation_fausses_alertes <= v2 + 0,01": p(m5, "validation_fausses_alertes") <= p(m2, "validation_fausses_alertes") + 0.01,
        "validation_nommee_juste >= 0,95": p(m5, "validation_nommee_juste") >= 0.95,
        "bananalsd_sigatoka_nommee >= v2 - 0,02": p(m5, "bananalsd_sigatoka_nommee") >= p(m2, "bananalsd_sigatoka_nommee") - 0.02,
        "bananalsd_saines_bien_classees >= v2 - 0,02": p(m5, "bananalsd_saines_bien_classees") >= p(m2, "bananalsd_saines_bien_classees") - 0.02,
        "bananalsd_inconnues_dites_saines <= v2 + 0,01": p(m5, "bananalsd_inconnues_dites_saines") <= p(m2, "bananalsd_inconnues_dites_saines") + 0.01,
    }
    bilan = dict(v2=m2, v5=m5, conditions=conditions, v5_adoptee=all(conditions.values()))
    (Path(a.dossier) / "bilan_adoption_v5.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
    for k in [k for k in m2 if not k.endswith("matrice")]:
        print(f"{k:48s} v2 {m2[k]['k']:>5}/{m2[k]['n']:<5} {m2[k]['part']}   v5 {m5[k]['k']:>5}/{m5[k]['n']:<5} {m5[k]['part']}")
    for c, ok in conditions.items():
        print("OK " if ok else "ÉCHEC", c)
    print("v5 adoptée :", bilan["v5_adoptee"])


if __name__ == "__main__":
    main()
