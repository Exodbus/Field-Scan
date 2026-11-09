#!/usr/bin/env python3
"""Règles d'adoption de la v7 et de la v8 (docs/protocole_maladies_v7.md, section 3 ; docs/protocole_maladies_v8.md,
section 2), modèle de référence v2, même code pour tous, chacun à ses propres seuils.

1. Non-régression : conditions de la section 5 du protocole de la v5 (scripts/mesurer_adoption_v5.py) sur la
   validation tanzanienne et BananaLSD.
2. « De loin » sur les feuilles de val_loin (mesure unique) : feuilles malades dites malades (cercosporiose, fusariose
   ou malade non identifiée) >= v2 + 10 points ; feuilles saines dites malades <= v2 + 5 points.
3. Départage (v8, section 2) : si les deux sont adoptables, le plus fort gain de feuilles malades dites malades ;
   écart < 2 points -> v8.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_adoption_loin.py --dossier out/maladies/kaggle_adoption_finale
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mesurer_adoption_v5 import MALADE, mesures, part  # noqa: E402


def loin(dossier, modele):
    f = pd.read_csv(Path(dossier) / f"predictions_{modele}_val_loin_feuilles.csv")
    dit = f.reponse.isin(MALADE)
    return dict(malades_dites_malades=part(dit, f.classe_vraie.eq("malade")),
                saines_dites_malades=part(dit, f.classe_vraie.eq("saine")),
                par_projet={p: part(dit, g.classe_vraie.eq("malade") | g.classe_vraie.eq("saine")) for p, g in f.groupby("jeu")},
                reponses=pd.crosstab(f.classe_vraie, f.reponse).to_dict("index"))


def conditions(m, r, l, lr):
    p = lambda x, k: x[k]["part"]  # noqa: E731
    return {
        "validation_malades_dites_saines <= v2 + 0,005": p(m, "validation_malades_dites_saines") <= p(r, "validation_malades_dites_saines") + 0.005,
        "validation_fausses_alertes <= v2 + 0,01": p(m, "validation_fausses_alertes") <= p(r, "validation_fausses_alertes") + 0.01,
        "validation_nommee_juste >= 0,95": p(m, "validation_nommee_juste") >= 0.95,
        "bananalsd_sigatoka_nommee >= v2 - 0,02": p(m, "bananalsd_sigatoka_nommee") >= p(r, "bananalsd_sigatoka_nommee") - 0.02,
        "bananalsd_saines_bien_classees >= v2 - 0,02": p(m, "bananalsd_saines_bien_classees") >= p(r, "bananalsd_saines_bien_classees") - 0.02,
        "bananalsd_inconnues_dites_saines <= v2 + 0,01": p(m, "bananalsd_inconnues_dites_saines") <= p(r, "bananalsd_inconnues_dites_saines") + 0.01,
        "loin_malades_dites_malades >= v2 + 0,10": p(l, "malades_dites_malades") >= p(lr, "malades_dites_malades") + 0.10,
        "loin_saines_dites_malades <= v2 + 0,05": p(l, "saines_dites_malades") <= p(lr, "saines_dites_malades") + 0.05,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default="out/maladies/kaggle_adoption_finale")
    ap.add_argument("--modeles", nargs="+", default=["v7", "v8"])
    a = ap.parse_args(argv)
    r, lr = mesures(a.dossier, "v2"), loin(a.dossier, "v2")
    bilan = dict(v2=dict(mesures=r, loin=lr))
    for nm in a.modeles:
        m, l = mesures(a.dossier, nm), loin(a.dossier, nm)
        c = conditions(m, r, l, lr)
        bilan[nm] = dict(mesures=m, loin=l, conditions=c, adoptable=all(c.values()))
        print(f"=== {nm} (référence v2)")
        for k in [k for k in m if not k.endswith("matrice")]:
            print(f"  {k:46s} v2 {r[k]['part']}   {nm} {m[k]['part']}")
        for k in ("malades_dites_malades", "saines_dites_malades"):
            print(f"  loin_{k:41s} v2 {lr[k]['part']} ({lr[k]['k']}/{lr[k]['n']})   {nm} {l[k]['part']} ({l[k]['k']}/{l[k]['n']})")
        for k, ok in c.items():
            print("   OK   " if ok else "   ÉCHEC", k)
    adoptables = [nm for nm in a.modeles if bilan[nm]["adoptable"]]
    if not adoptables:
        choix = "v2"
    elif len(adoptables) == 1:
        choix = adoptables[0]
    else:
        g = {nm: bilan[nm]["loin"]["malades_dites_malades"]["part"] for nm in adoptables}
        choix = "v8" if abs(g["v7"] - g["v8"]) < 0.02 else max(g, key=g.get)
    bilan["modele_de_la_chaine"] = choix
    (Path(a.dossier) / "bilan_adoption_loin.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
    print("adoptables :", adoptables, "-> modèle de la chaîne :", choix)


if __name__ == "__main__":
    main()
