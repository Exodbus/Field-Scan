#!/usr/bin/env python3
"""Essai « hauteur », phase 1 (docs/protocole_hauteur_banavista.md, section 4).

--etape sfm : photos placées par OpenSfM (critère : au moins 80 %), échelle k (mètres par unité),
              résolutions à demander à ODM pour 2,5 cm au sol.
--etape mns : part de la zone vue couverte par le MNS d'ODM (critère : au moins 70 %), images de contrôle.

Zone vue : union des emprises des photos placées (cadre entier), projetées sur le plan horizontal à la
hauteur médiane des points clairsemés.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/hauteur_phase1.py --etape sfm
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from hauteur_commun import OUT, PROJET, echelle, lire_reconstructions, poses, rayons  # noqa: E402


def etape_sfm():
    recs = lire_reconstructions()
    ligne = json.loads((OUT / "ligne_a.json").read_text(encoding="utf-8"))
    n = ligne["n"]
    tailles = [len(r["shots"]) for r in recs]
    rec = recs[0]
    k, g, gsds = echelle(rec)
    cam = list(rec["cameras"].values())[0]
    res = dict(photos=n, reconstructions=len(recs), photos_par_reconstruction=tailles,
               placees_plus_grande=tailles[0], part_placees=round(tailles[0] / n, 3),
               critere_80=tailles[0] / n >= 0.80,
               non_placees=sorted(set(p["photo"] for p in ligne["photos"]) - set(rec["shots"])),
               points_clairsemes=len(rec["points"]),
               k_m_par_unite=k, gsd_unites=g, gsd_dispersion=[float(np.percentile(gsds, q)) for q in (5, 50, 95)],
               camera=cam,
               resolution_cm_pour_2_5cm=round(2.5 / 100 / k * 100, 4),
               resolution_cm_pour_5cm=round(5.0 / 100 / k * 100, 4))
    print(json.dumps(res, indent=1, ensure_ascii=False))
    (OUT / "phase1_sfm.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


def emprise(pose, z):
    cam = pose[3]
    L, H = cam["width"], cam["height"]
    u = np.r_[np.linspace(0, L, 21), np.full(21, L), np.linspace(L, 0, 21), np.zeros(21)]
    v = np.r_[np.zeros(21), np.linspace(0, H, 21), np.full(21, H), np.linspace(H, 0, 21)]
    c, d = rayons(pose, u, v)
    s = (z - c[2]) / d[:, 2]
    return c[None, :2] + s[:, None] * d[:, :2]


def etape_mns():
    import cv2
    import rasterio
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from hauteur_grille import lire_mns_repere  # noqa: E402
    rec = lire_reconstructions()[0]
    k, _, _ = echelle(rec)
    pts = np.array([p["coordinates"] for p in rec["points"].values()], float)
    z0 = float(np.median(pts[:, 2]))
    P = poses(rec)
    zone = unary_union([Polygon(emprise(p, z0)).buffer(0) for p in P.values()])
    mns, gt = lire_mns_repere()            # MNS en unités du repère, transformation (x0, px, y0, py)
    x0, px, y0, py = gt
    h, l = mns.shape
    # rastérise la zone vue sur la grille du MNS
    masque = np.zeros((h, l), np.uint8)
    geoms = zone.geoms if hasattr(zone, "geoms") else [zone]
    for g in geoms:
        xy = np.asarray(g.exterior.coords)
        cv2.fillPoly(masque, [np.c_[(xy[:, 0] - x0) / px, (xy[:, 1] - y0) / py].round().astype(np.int32)], 1)
        for trou in g.interiors:
            xy = np.asarray(trou.coords)
            cv2.fillPoly(masque, [np.c_[(xy[:, 0] - x0) / px, (xy[:, 1] - y0) / py].round().astype(np.int32)], 0)
    aire_zone_px = zone.area / (px * px)
    vue = masque.astype(bool)
    valide = np.isfinite(mns)
    couv = float((vue & valide).sum() / aire_zone_px)
    res = dict(aire_zone_m2=round(zone.area * k * k, 1), aire_zone_dans_raster=round(float(vue.sum() / aire_zone_px), 4),
               couverture_mns=round(couv, 4), critere_70=couv >= 0.70,
               taille_pixel_mns_cm=round(px * k * 100, 2),
               z_mns_m=[round(float(np.nanpercentile(mns, q) * k), 2) for q in (1, 50, 99)])
    print(json.dumps(res, indent=1, ensure_ascii=False))
    (OUT / "phase1_mns.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--etape", choices=["sfm", "mns"], required=True)
    a = ap.parse_args()
    etape_sfm() if a.etape == "sfm" else etape_mns()
