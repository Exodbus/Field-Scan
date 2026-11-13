#!/usr/bin/env python3
"""Fourchette d'estimation du bulletin (protocoles v3 section 4 bis, v4 et v5 section 7 bis), sur la VALIDATION seulement.

Rapport réel / détecté, au seuil du .json du modèle, avec le détecteur de la chaîne (fieldscan.drone.DetecteurCentres) :
- segmento est : tuiles de validation (boîtes Roboflow) ;
- dji_0544 : photo réduite à 5 cm, points et détections dans le disque de 2 000 px ;
- banavista session B (v5, option --ensemble-dense val_dense_bv) : photos entières, plants et détections dans le disque ;
- MM1-MM2 : carrés de la référence manuelle, mères seules, détections dans le carré.
coefficient_bas = plus petit rapport, coefficient_haut = plus grand. CG n'est jamais utilisé.

Exemples :
    python scripts/mesurer_fourchette_v3.py
    python scripts/mesurer_fourchette_v3.py --modele modeles/centres_5cm_v5.onnx --donnees data/drone/comptage_v5_5cm         --ensemble-plantation val_plantain --ensemble-dense val_dense_bv --out out/fourchette_v5.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from fieldscan.drone import DetecteurCentres  # noqa: E402


def detecter(det, chemin, seuil):
    rgb = np.moveaxis(np.asarray(Image.open(chemin).convert("RGB")), -1, 0)
    valide = np.ones(rgb.shape[1:], bool)
    xy, sc = det.predire(rgb, valide)
    return xy[sc >= seuil]


def compter_disque(det, d, r, O, seuil):
    """Plants (mères) et détections dans le disque de la ligne r de tuiles.csv."""
    xy = detecter(det, d / "images" / r.image_path, seuil)
    dans = (xy[:, 0] - r.masque_cx) ** 2 + (xy[:, 1] - r.masque_cy) ** 2 <= r.masque_r ** 2
    o = O[(O.image_path == r.image_path) & (O.type == "mere")]
    dans_o = (o.cx - r.masque_cx) ** 2 + (o.cy - r.masque_cy) ** 2 <= r.masque_r ** 2
    return int(dans_o.sum()), int(dans.sum())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modele", default="modeles/centres_5cm_v3.onnx")
    ap.add_argument("--donnees", default="data/drone/comptage_v3_5cm")
    ap.add_argument("--out", default="out/fourchette_v3.json")
    ap.add_argument("--ensemble-plantation", default="val_dense",
                    help="ensemble de validation des plantations : val_dense (v3, segmento est) ou val_plantain (v4, 100_metros)")
    ap.add_argument("--ensemble-dense", default=None,
                    help="ensemble dense mesuré dans le disque (v5 : val_dense_bv) ; absent en v3 et v4")
    args = ap.parse_args(argv)
    det = DetecteurCentres(args.modele)
    s = det.seuil
    d = Path(args.donnees)
    T, O = pd.read_csv(d / "tuiles.csv"), pd.read_csv(d / "objets.csv")
    res = {}

    # plantations : segmento est (v3) ou plantas_platano 100_metros (v4)
    reel = detecte = 0
    for nom in T[T.ensemble == args.ensemble_plantation].image_path:
        reel += int(((O.image_path == nom) & (O.type == "mere")).sum())
        detecte += len(detecter(det, d / "images" / nom, s))
    res["segmento_est" if args.ensemble_plantation == "val_dense" else "plantain_100_metros"] = dict(reel=reel, detecte=detecte)

    # banavista session B (v5) dans le disque
    if args.ensemble_dense:
        reel = detecte = 0
        for _, r in T[T.ensemble == args.ensemble_dense].iterrows():
            a, b = compter_disque(det, d, r, O, s)
            reel, detecte = reel + a, detecte + b
        res["dense_banavista_b"] = dict(reel=reel, detecte=detecte)

    # dji_0544 dans le disque
    reel, detecte = compter_disque(det, d, T[T.ensemble == "val_jeunes"].iloc[0], O, s)
    res["jeunes_dji_0544"] = dict(reel=reel, detecte=detecte)

    # MM1-MM2, mères seules, détections dans le carré
    P, Z = pd.read_csv(d / "mm" / "points.csv"), pd.read_csv(d / "mm" / "zones.csv")
    reel = detecte = 0
    for _, z in Z.iterrows():
        xy = detecter(det, d / "mm" / "images" / z.image_path, s)
        detecte += int(((xy[:, 0] >= z.x0) & (xy[:, 0] <= z.x1) & (xy[:, 1] >= z.y0) & (xy[:, 1] <= z.y1)).sum())
        reel += int(((P.zone_id == z.zone_id) & (P.type == "mere")).sum())
    res["mm1_mm2_meres"] = dict(reel=reel, detecte=detecte)

    for k, v in res.items():
        v["rapport"] = round(v["reel"] / v["detecte"], 3) if v["detecte"] else None
        print(f"{k:16s} : {v['reel']:5d} réels / {v['detecte']:5d} détectés -> rapport {v['rapport']}")
    rapports = [v["rapport"] for v in res.values() if v["rapport"]]
    bas, haut = round(min(rapports), 2), round(max(rapports), 2)
    print(f"Seuil {s} ; fourchette : coefficient_bas {bas}, coefficient_haut {haut}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(modele=args.modele, seuil=s, mesures=res, coefficient_bas=bas,
                                              coefficient_haut=haut), indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
