#!/usr/bin/env python3
"""Essai « hauteur », phase 2 (docs/protocole_hauteur_banavista.md, section 5 ; règles dans
docs/nuit_2026-11-13/journal_hauteur.md, écrites avant le calcul).

--etape reglage : balayage de la distance minimale d entre sommets sur la zone de réglage (première moitié).
--etape mesure --d D : une seule mesure (hauteur, v5, fusion v5 + sommets) sur la zone de mesure (seconde moitié).

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -I -u scripts/hauteur_phase2.py --etape reglage
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from hauteur_commun import OUT, echelle, lire_reconstructions, poses, projeter, rayons  # noqa: E402
from hauteur_grille import construire_grille  # noqa: E402

RAYON_DISQUE_PX = 2000      # règle du v5
R_FUSION_M = 1.0            # fusion des boîtes projetées
RAYON_APPARIEMENT_M = 1.0   # appariement du v5 (20 px à 5 cm)
SIGMA_PROJ_M = 0.5          # lissage du MNS pour couper les rayons
SIGMA_SOMMETS_M = 0.3       # lissage du MNS pour les sommets (fixé)
R_MIN_M, H_MIN_M = 2.0, 0.5  # le sommet dépasse d'au moins 0,5 m le minimum dans 2 m (fixé)
GRILLE_D = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5]
PAS_SOMMETS_M = 0.10        # grille de calcul des sommets (MNS lissé à 0,3 m, sous-échantillonné par 2)


# ---------------------------------------------------------------- référence
def boites_jointives(B):
    """Pour chaque boîte Bananas : intersection d'aire non nulle avec une autre boîte de la même photo."""
    B = B.copy()
    B["jointive"] = False
    for photo, g in B.groupby("photo"):
        x0, y0 = g.x.values, g.y.values
        x1, y1 = x0 + g.w.values, y0 + g.h.values
        ix = np.minimum(x1[:, None], x1[None]) - np.maximum(x0[:, None], x0[None])
        iy = np.minimum(y1[:, None], y1[None]) - np.maximum(y0[:, None], y0[None])
        inter = (ix > 0) & (iy > 0)
        np.fill_diagonal(inter, False)
        B.loc[g.index, "jointive"] = inter.any(1)
    return B


def couper_mns(pose, u, v, G, z_lisse_u):
    """Intersection des rayons des pixels (u, v) avec le MNS lissé (unités du repère)."""
    c, d = rayons(pose, u, v)
    z = np.full(len(u), np.nanmedian(z_lisse_u))
    for _ in range(10):
        s = (z - c[2]) / d[:, 2]
        X = c[None, :] + s[:, None] * d
        z = G.echantillonner(z_lisse_u, X[:, 0], X[:, 1])
    s = (z - c[2]) / d[:, 2]
    return c[None, :] + s[:, None] * d


def reference(rec, G, k):
    P = poses(rec)
    B = pd.read_csv(OUT / "boites_ligne_a.csv")
    B = boites_jointives(B[B.classe == "Bananas"].reset_index(drop=True))
    B["u"], B["v"] = B.x + B.w / 2, B.y + B.h / 2
    B["r_px"] = np.hypot(B.u - 2000, B.v - 1500)
    B = B[(B.r_px <= RAYON_DISQUE_PX) & B.photo.isin(P)].reset_index(drop=True)
    z_lisse = G.lisser(G.mns_u, SIGMA_PROJ_M)
    X = np.zeros((len(B), 3))
    for photo, g in B.groupby("photo"):
        X[g.index] = couper_mns(P[photo], g.u.values, g.v.values, G, z_lisse)
    B["X"], B["Y"], B["Z"] = X[:, 0] * k, X[:, 1] * k, X[:, 2] * k        # mètres
    # fusion, photos dans l'ordre DJI
    cent, membres = np.zeros((0, 2)), []
    for photo in sorted(B.photo.unique()):
        g = B[B.photo == photo]
        q = g[["X", "Y"]].values
        pris = np.zeros(len(q), bool)
        if len(cent):
            D = np.linalg.norm(q[:, None] - cent[None], axis=2)
            li, co = linear_sum_assignment(np.where(D <= R_FUSION_M, D, 1e6))
            ok = D[li, co] <= R_FUSION_M
            for a, b in zip(li[ok], co[ok]):
                membres[b].append(g.index[a]); pris[a] = True
        for a in np.nonzero(~pris)[0]:
            membres.append([g.index[a]])
        cent = np.array([B.loc[m, ["X", "Y"]].values.mean(0) for m in membres])
    lignes = []
    for m in membres:
        g = B.loc[m]
        nadir = g.loc[g.r_px.idxmin()]
        disp = np.hypot(g.X - g.X.mean(), g.Y - g.Y.mean())
        lignes.append(dict(X=g.X.mean(), Y=g.Y.mean(), n_boites=len(m), jointive=bool(nadir.jointive),
                           photo_nadir=nadir.photo, dispersion_m=float(disp.max()) if len(m) > 1 else np.nan))
    return pd.DataFrame(lignes), B


# ---------------------------------------------------------------- zones
def zone_de(points_m, rec, G, k, moitie_photos):
    """Booléen : point (mètres) dans la zone de la moitié donnée (photo la plus proche, disque, rasters valides)."""
    P = poses(rec)
    noms = sorted(P)
    C = np.array([P[n][2][:2] for n in noms]) * k
    _, idx = cKDTree(C).query(points_m, k=1)
    Xu, Yu = points_m[:, 0] / k, points_m[:, 1] / k
    Zu = G.echantillonner(G.lisser(G.mns_u, SIGMA_PROJ_M), Xu, Yu)
    ok = np.zeros(len(points_m), bool)
    for j, n in enumerate(noms):
        sel = np.nonzero(idx == j)[0]
        if not len(sel) or n not in moitie_photos:
            continue
        u, v = projeter(P[n], np.c_[Xu[sel], Yu[sel], Zu[sel]])
        ok[sel] = np.hypot(u - 2000, v - 1500) <= RAYON_DISQUE_PX
    return ok & G.valide_en(Xu, Yu)


# ---------------------------------------------------------------- méthodes
def sommets(G, k, d):
    """Sommets du MNS lissé (mètres), grille de 10 cm."""
    z = G.lisser(G.mns_u, SIGMA_SOMMETS_M) * k
    f = int(round(PAS_SOMMETS_M / G.pas_m))
    z = cv2.resize(z.astype("float32"), (z.shape[1] // f, z.shape[0] // f), interpolation=cv2.INTER_AREA)
    val = cv2.resize(G.valide.astype("uint8"), (z.shape[1], z.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
    zz = np.where(val, z, np.nanmin(z[val])).astype("float32")

    def disque(r_m):
        r = int(round(r_m / PAS_SOMMETS_M))
        return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    haut = zz - cv2.erode(zz, disque(R_MIN_M)) >= H_MIN_M
    pic = (zz >= cv2.dilate(zz, disque(d))) & haut & val
    n, lab, stats, cen = cv2.connectedComponentsWithStats(pic.astype("uint8"), connectivity=8)
    c = cen[1:]
    x_u = G.x0 + (c[:, 0] + 0.5) * f * G.pas_u
    y_u = G.y0 - (c[:, 1] + 0.5) * f * G.pas_u
    return np.c_[x_u, y_u] * k


def detections_v5(G, k):
    from fieldscan.drone import DetecteurCentres
    det = DetecteurCentres(RACINE / "modeles/centres_5cm_v5.onnx")
    rgb = np.moveaxis(G.rgb, -1, 0)
    xy, sc = det.predire(rgb, G.valide_ortho)
    xy = xy[sc >= det.seuil]
    return np.c_[G.x0 + xy[:, 0] * G.pas_u, G.y0 - xy[:, 1] * G.pas_u] * k, det.seuil


def fusion(v5, som, d):
    if not len(v5):
        return som
    dist, _ = cKDTree(v5).query(som, k=1)
    return np.r_[v5, som[dist > d]]


# ---------------------------------------------------------------- mesure
def mesurer(pred, ref, jointive):
    vp, pris = 0, np.zeros(len(ref), bool)
    if len(pred) and len(ref):
        D = np.linalg.norm(pred[:, None] - ref[None], axis=2)
        li, co = linear_sum_assignment(np.where(D <= RAYON_APPARIEMENT_M, D, 1e6))
        ok = D[li, co] <= RAYON_APPARIEMENT_M
        vp, pris[co[ok]] = int(ok.sum()), True
    fp, fn = len(pred) - vp, len(ref) - vp
    p = vp / (vp + fp) if vp + fp else 0.0
    r = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    nj = int(jointive.sum())
    return dict(vp=vp, fp=fp, fn=fn, P=round(p, 4), R=round(r, 4), F1=round(f1, 4),
                jointives=nj, rappel_jointives=round(float(pris[jointive].sum() / nj), 4) if nj else None,
                isolees=int((~jointive).sum()),
                rappel_isolees=round(float(pris[~jointive].sum() / (~jointive).sum()), 4) if (~jointive).sum() else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etape", choices=["reglage", "mesure"], required=True)
    ap.add_argument("--d", type=float)
    a = ap.parse_args()
    t0 = time.time()
    rec = lire_reconstructions()[0]
    k, _, _ = echelle(rec)
    G = construire_grille(rec, k)
    print(f"grille {G.mns_u.shape}, pas {G.pas_m:.3f} m, k = {k:.5f} m/unité ({time.time() - t0:.0f} s)")
    ref_cache = OUT / "reference_plants.csv"
    if ref_cache.exists():
        R = pd.read_csv(ref_cache)
    else:
        R, B = reference(rec, G, k)
        R.to_csv(ref_cache, index=False)
        B.to_csv(OUT / "boites_projetees.csv", index=False)
    print(f"référence : {len(R)} plants, {int(R.jointive.sum())} jointifs, dispersion médiane "
          f"{np.nanmedian(R.dispersion_m):.2f} m ({time.time() - t0:.0f} s)")
    ligne = json.loads((OUT / "ligne_a.json").read_text(encoding="utf-8"))
    moitie = set(ligne["reglage"] if a.etape == "reglage" else ligne["mesure"])
    refxy = R[["X", "Y"]].values
    zr = zone_de(refxy, rec, G, k, moitie)
    ref, jo = refxy[zr], R.jointive.values[zr]
    print(f"zone {a.etape} : {len(ref)} plants, {int(jo.sum())} jointifs")
    res = dict(etape=a.etape, k=k, plants=len(ref), jointifs=int(jo.sum()))
    if a.etape == "reglage":
        res["balayage"] = {}
        for d in GRILLE_D:
            s = sommets(G, k, d)
            s = s[zone_de(s, rec, G, k, moitie)]
            m = mesurer(s, ref, jo)
            res["balayage"][str(d)] = dict(detections=len(s), **m)
            print(d, len(s), m)
        meilleur = max(GRILLE_D, key=lambda d: (res["balayage"][str(d)]["F1"], d))
        res["d_retenu"] = meilleur
        print("d retenu :", meilleur)
    else:
        assert a.d is not None
        v5, seuil = detections_v5(G, k)
        np.save(OUT / "v5_detections_m.npy", v5)
        s = sommets(G, k, a.d)
        fu = fusion(v5, s, a.d)
        res["d"] = a.d
        res["seuil_v5"] = seuil
        for nom, pred in (("v5", v5), ("hauteur", s), ("fusion", fu)):
            pz = pred[zone_de(pred, rec, G, k, moitie)] if len(pred) else pred
            res[nom] = dict(detections=len(pz), **mesurer(pz, ref, jo))
            print(nom, res[nom])
        dv5, _ = cKDTree(v5).query(ref, k=1) if len(v5) else (np.array([np.nan]), None)
        res["controle_distance_mediane_plant_v5_m"] = round(float(np.median(dv5)), 3)
    res["duree_s"] = round(time.time() - t0)
    (OUT / f"phase2_{a.etape}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
