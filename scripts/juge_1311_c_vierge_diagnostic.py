#!/usr/bin/env python3
"""Juge comptage, 14/11/2026 : DIAGNOSTIC du test vierge banana_trees_kp, après sa lecture unique.

N'exécute AUCUN réseau : lit seulement les détections déjà enregistrées par la lecture
(out/controle_nuit_1311/juge_c/vierge/detections_vierge.npz) et les annotations (prepare/objets.csv, tuiles.csv).
Ne change rien au chiffre de la règle (rayon 20 px, seuil 0,30) ; sert à comprendre pourquoi il est si bas :
  - les points annotés tombent-ils dans l'image ? (bornes des coordonnées contre largeur / hauteur)
  - écartement des points : distance médiane au plus proche voisin, annotations contre détections (contrôle d'échelle) ;
  - distances détection -> annotation la plus proche, et décalage médian (dx, dy) des paires proches (contrôle de
    position, par exemple un étirement ou un décalage des coordonnées).
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -X utf8 -I -u scripts/juge_1311_c_vierge_diagnostic.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
DV = RACINE / "data/roboflow_nuit_1112/comptage/banana_trees_kp/prepare"
SORTIE = RACINE / "out/controle_nuit_1311/juge_c/vierge"


def ppv(p):
    if len(p) < 3:
        return np.nan
    return float(np.median(cKDTree(p).query(p, k=2)[0][:, 1]))


def main():
    T = pd.read_csv(DV / "tuiles.csv")
    T = T[T.ensemble == "test_vierge"]
    O = pd.read_csv(DV / "objets.csv")
    Z = np.load(SORTIE / "detections_vierge.npz")
    res = {}
    for cand in ["v5_030", "E5p90b_c13e_d-0.1"]:
        lignes, dist, dec = [], [], []
        for r in T.itertuples():
            a = O[(O.image_path == r.image_path) & (O.type == "mere")][["cx", "cy"]].to_numpy("f8")
            d = Z[f"{cand}|{r.image_path}"]
            d = d[d[:, 2] >= 0.30][:, :2].astype("f8")
            l = dict(image=r.image_path, largeur=r.largeur, hauteur=r.hauteur, annotes=len(a), detectes=len(d),
                     ann_xmax=float(a[:, 0].max()) if len(a) else np.nan, ann_ymax=float(a[:, 1].max()) if len(a) else np.nan,
                     ppv_annotes=ppv(a), ppv_detectes=ppv(d))
            if len(a) and len(d):
                dd, ii = cKDTree(a).query(d, k=1)
                dist += dd.tolist()
                ok = dd <= 60
                dec += (d[ok] - a[ii[ok]]).tolist()
            lignes.append(l)
        L = pd.DataFrame(lignes)
        L.to_csv(SORTIE / f"diagnostic_{cand}.csv", index=False)
        dist, dec = np.array(dist), np.array(dec)
        res[cand] = dict(
            photos=len(L),
            ann_hors_image=int(((L.ann_xmax > L.largeur) | (L.ann_ymax > L.hauteur)).sum()),
            taille_images_px=[int(L.largeur.median()), int(L.hauteur.median())],
            ppv_annotes_median_px=float(L.ppv_annotes.median()), ppv_detectes_median_px=float(L.ppv_detectes.median()),
            distance_det_annotation_px={f"q{int(q * 100)}": float(np.quantile(dist, q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
            part_det_a_20px=float((dist <= 20).mean()), part_det_a_40px=float((dist <= 40).mean()),
            decalage_median_px=[float(np.median(dec[:, 0])), float(np.median(dec[:, 1]))] if len(dec) else None,
            rapport_det_ann_par_photo={f"q{int(q * 100)}": float(np.quantile(L.detectes / L.annotes.clip(lower=1), q)) for q in (0.1, 0.5, 0.9)})
        print(cand, json.dumps(res[cand], ensure_ascii=False), flush=True)
    (SORTIE / "diagnostic.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
