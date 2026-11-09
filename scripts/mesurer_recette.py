#!/usr/bin/env python3
"""Mesure unique de ConvNeXt-R (docs/protocole_maladies_recette.md, section 4). À lancer une seule fois.

Adoption : règle de DINOv2-FT (référence v2). Départage entre candidats adoptables (soupe v2 + v8, DINOv2-FT si son bilan
existe, ConvNeXt-R) : meilleur rappel équilibré BananaLSD ; DINOv2-FT doit dépasser le meilleur ConvNeXt d'au moins
0,01 ; entre la soupe et ConvNeXt-R, un écart inférieur à 0,01 garde la soupe.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/mesurer_recette.py --dossier out/maladies/recette
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from mesurer_adoption_v5 import mesures  # noqa: E402
from mesurer_dinov2_ft import auc_loin, equilibre  # noqa: E402

GPU = RACINE / "out/maladies/kaggle_adoption_finale"
SOUPE = RACINE / "out/maladies/melange"
BILAN_DINO = RACINE / "out/maladies/dinov2_ft/bilan_dinov2_ft.json"
JEUX = ("validation", "bananalsd", "val_loin_feuilles")


def conditions(m, r, a, ar):
    p = lambda x, k: x[k]["part"]  # noqa: E731
    return {
        "validation_malades_dites_saines <= v2 + 0,005": p(m, "validation_malades_dites_saines") <= p(r, "validation_malades_dites_saines") + 0.005,
        "validation_fausses_alertes <= v2 + 0,01": p(m, "validation_fausses_alertes") <= p(r, "validation_fausses_alertes") + 0.01,
        "validation_nommee_juste >= 0,95": p(m, "validation_nommee_juste") >= 0.95,
        "bananalsd_sigatoka_nommee >= v2 - 0,02": p(m, "bananalsd_sigatoka_nommee") >= p(r, "bananalsd_sigatoka_nommee") - 0.02,
        "bananalsd_saines_bien_classees >= v2 - 0,02": p(m, "bananalsd_saines_bien_classees") >= p(r, "bananalsd_saines_bien_classees") - 0.02,
        "bananalsd_inconnues_dites_saines <= v2 + 0,01": p(m, "bananalsd_inconnues_dites_saines") <= p(r, "bananalsd_inconnues_dites_saines") + 0.01,
        "auc_loin >= v2 - 0,02": a >= ar - 0.02,
        "garde : inconnues dites Sigatoka <= v2 + 0,05": p(m, "bananalsd_inconnues_dites_sigatoka") <= p(r, "bananalsd_inconnues_dites_sigatoka") + 0.05,
        "gain : rappel équilibré BananaLSD >= v2 + 0,01": equilibre(m) >= equilibre(r) + 0.01,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default="out/maladies/recette")
    dos = RACINE / ap.parse_args(argv).dossier
    sortie = dos / "bilan_recette.json"
    if sortie.exists():
        sys.exit(f"{sortie} existe déjà : mesure unique, rien n'est refait.")
    for j in JEUX:
        g, d = pd.read_csv(GPU / f"predictions_v2_{j}.csv"), pd.read_csv(dos / f"predictions_convnext_r_{j}.csv")
        assert (g.chemin == d.chemin).all(), f"photos différentes : {j}"
        g.to_csv(dos / f"predictions_v2_{j}.csv", index=False)
        pd.read_csv(SOUPE / f"predictions_soupe_{j}.csv").to_csv(dos / f"predictions_soupe_{j}.csv", index=False)
    r, m, s = mesures(dos, "v2"), mesures(dos, "convnext_r"), mesures(dos, "soupe")
    ar, am = auc_loin(dos, "v2"), auc_loin(dos, "convnext_r")
    c = conditions(m, r, am, ar)
    adoptables = {"soupe": equilibre(s)}
    if all(c.values()):
        adoptables["convnext_r"] = equilibre(m)
    dino = json.loads(BILAN_DINO.read_text(encoding="utf-8")) if BILAN_DINO.exists() else None
    if dino and dino["dinov2_ft"]["adoptable"]:
        adoptables["dinov2_ft"] = dino["dinov2_ft"]["equilibre"]
    convnext = {k: v for k, v in adoptables.items() if k != "dinov2_ft"}
    meilleur_cnx = "convnext_r" if "convnext_r" in convnext and convnext["convnext_r"] >= convnext["soupe"] + 0.01 else "soupe"
    retenu = meilleur_cnx
    if "dinov2_ft" in adoptables and adoptables["dinov2_ft"] >= adoptables[meilleur_cnx] + 0.01:
        retenu = "dinov2_ft"
    bilan = dict(v2=dict(mesures=r, auc_loin=ar, equilibre=equilibre(r)), soupe=dict(mesures=s, equilibre=equilibre(s)),
                 convnext_r=dict(mesures=m, auc_loin=am, equilibre=equilibre(m), conditions=c, adoptable=all(c.values())),
                 dinov2_ft_bilan_lu=dino is not None, adoptables=adoptables, retenu=retenu)
    sortie.write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    for k in [k for k in m if not k.endswith("matrice")]:
        print(f"  {k:46s} v2 {r[k]['k']}/{r[k]['n']}  ConvNeXt-R {m[k]['k']}/{m[k]['n']}  soupe {s[k]['k']}/{s[k]['n']}")
    print(f"  {'auc_loin':46s} v2 {ar:.3f}  ConvNeXt-R {am:.3f}")
    print(f"  {'rappel équilibré BananaLSD':46s} v2 {equilibre(r):.4f}  ConvNeXt-R {equilibre(m):.4f}  soupe {equilibre(s):.4f}")
    for k, ok in c.items():
        print("   OK   " if ok else "   ÉCHEC", k)
    print("ConvNeXt-R adoptable :", all(c.values()), "| adoptables :", {k: round(v, 4) for k, v in adoptables.items()},
          "| bilan DINOv2-FT lu :", dino is not None, "| retenu :", retenu)


if __name__ == "__main__":
    main()
