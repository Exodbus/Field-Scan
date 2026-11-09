#!/usr/bin/env python3
"""Mesure unique de DINOv2-FT (docs/protocole_maladies_dinov2_ft.md, section 3). À lancer une seule fois.

Référence v2 (fichiers GPU de la nuit) : 6 conditions de non-régression ; AUC de loin >= v2 - 0,02 ; inconnues de
BananaLSD dites Sigatoka <= v2 + 5 points ; rappel équilibré BananaLSD >= v2 + 0,01. Départage avec la soupe v2 + v8 :
DINOv2-FT retenu seulement si son rappel équilibré BananaLSD >= soupe + 0,01.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_dinov2_ft.py --dossier out/maladies/dinov2_ft
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from mesurer_adoption_v5 import mesures  # noqa: E402
from mesurer_melange_nouveaute import auc  # noqa: E402

GPU = RACINE / "out/maladies/kaggle_adoption_finale"
SOUPE = RACINE / "out/maladies/melange"
JEUX = ("validation", "bananalsd", "val_loin_feuilles")


def equilibre(m):
    return (m["bananalsd_sigatoka_nommee"]["part"] + m["bananalsd_saines_bien_classees"]["part"]) / 2


def auc_loin(dos, modele):
    l = pd.read_csv(dos / f"predictions_{modele}_val_loin_feuilles.csv")
    return auc(1 - l.p_saine.to_numpy(), l.classe_vraie.eq("malade").to_numpy())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default="out/maladies/dinov2_ft")
    dos = RACINE / ap.parse_args(argv).dossier
    sortie = dos / "bilan_dinov2_ft.json"
    if sortie.exists():
        sys.exit(f"{sortie} existe déjà : mesure unique, rien n'est refait.")
    for j in JEUX:
        g, d = pd.read_csv(GPU / f"predictions_v2_{j}.csv"), pd.read_csv(dos / f"predictions_dinov2_ft_{j}.csv")
        assert (g.chemin == d.chemin).all(), f"photos différentes : {j}"
        g.to_csv(dos / f"predictions_v2_{j}.csv", index=False)
        s = SOUPE / f"predictions_soupe_{j}.csv"
        pd.read_csv(s).to_csv(dos / f"predictions_soupe_{j}.csv", index=False)
    r, m, s = mesures(dos, "v2"), mesures(dos, "dinov2_ft"), mesures(dos, "soupe")
    a2, ad = auc_loin(dos, "v2"), auc_loin(dos, "dinov2_ft")
    p = lambda x, k: x[k]["part"]  # noqa: E731
    c = {
        "validation_malades_dites_saines <= v2 + 0,005": p(m, "validation_malades_dites_saines") <= p(r, "validation_malades_dites_saines") + 0.005,
        "validation_fausses_alertes <= v2 + 0,01": p(m, "validation_fausses_alertes") <= p(r, "validation_fausses_alertes") + 0.01,
        "validation_nommee_juste >= 0,95": p(m, "validation_nommee_juste") >= 0.95,
        "bananalsd_sigatoka_nommee >= v2 - 0,02": p(m, "bananalsd_sigatoka_nommee") >= p(r, "bananalsd_sigatoka_nommee") - 0.02,
        "bananalsd_saines_bien_classees >= v2 - 0,02": p(m, "bananalsd_saines_bien_classees") >= p(r, "bananalsd_saines_bien_classees") - 0.02,
        "bananalsd_inconnues_dites_saines <= v2 + 0,01": p(m, "bananalsd_inconnues_dites_saines") <= p(r, "bananalsd_inconnues_dites_saines") + 0.01,
        "auc_loin >= v2 - 0,02": ad >= a2 - 0.02,
        "garde : inconnues dites Sigatoka <= v2 + 0,05": p(m, "bananalsd_inconnues_dites_sigatoka") <= p(r, "bananalsd_inconnues_dites_sigatoka") + 0.05,
        "gain : rappel équilibré BananaLSD >= v2 + 0,01": equilibre(m) >= equilibre(r) + 0.01,
    }
    adoptable = all(c.values())
    retenu = "dinov2_ft" if adoptable and equilibre(m) >= equilibre(s) + 0.01 else "soupe"
    bilan = dict(v2=dict(mesures=r, auc_loin=a2, equilibre=equilibre(r)), soupe=dict(mesures=s, equilibre=equilibre(s)),
                 dinov2_ft=dict(mesures=m, auc_loin=ad, equilibre=equilibre(m), conditions=c, adoptable=adoptable), retenu=retenu)
    sortie.write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    for k in [k for k in m if not k.endswith("matrice")]:
        print(f"  {k:46s} v2 {r[k]['k']}/{r[k]['n']}  DINOv2-FT {m[k]['k']}/{m[k]['n']}  soupe {s[k]['k']}/{s[k]['n']}")
    print(f"  {'auc_loin':46s} v2 {a2:.3f}  DINOv2-FT {ad:.3f}")
    print(f"  {'rappel équilibré BananaLSD':46s} v2 {equilibre(r):.4f}  DINOv2-FT {equilibre(m):.4f}  soupe {equilibre(s):.4f}")
    for k, ok in c.items():
        print("   OK   " if ok else "   ÉCHEC", k)
    print("DINOv2-FT adoptable :", adoptable, "| retenu (départage avec la soupe) :", retenu)


if __name__ == "__main__":
    main()
