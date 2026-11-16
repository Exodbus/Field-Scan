#!/usr/bin/env python3
"""Essai « hauteur » : fonctions communes (lecture d'OpenSfM, échelle, projection des pixels).

Conventions d'OpenSfM (opensfm/pygeometry) :
- pose : rotation R (vecteur de Rodrigues) et translation t, x_cam = R X + t ; centre = -R^T t ;
- coordonnées image normalisées : (u - L/2) / max(L, H), (v - H/2) / max(L, H) ;
- modèle « brown » : focal_x, focal_y, c_x, c_y, k1, k2, k3, p1, p2 ; « perspective » : focal, k1, k2.
"""
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

RACINE = Path(__file__).resolve().parents[1]
OUT = RACINE / "out/hauteur"
PROJET = OUT / "odm/ligne_a"
CM_PX = 1.1   # taille d'un pixel au sol retenue pour banavista (v5)


def rodrigues(v):
    v = np.asarray(v, float)
    th = np.linalg.norm(v)
    if th < 1e-12:
        return np.eye(3)
    k = v / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def lire_reconstructions(chemin=None):
    chemin = chemin or PROJET / "opensfm/reconstruction.json"
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def poses(rec):
    """{photo: (R, t, centre, camera)} pour une reconstruction."""
    res = {}
    for nom, s in rec["shots"].items():
        R = rodrigues(s["rotation"])
        t = np.asarray(s["translation"], float)
        res[nom] = (R, t, -R.T @ t, rec["cameras"][s["camera"]])
    return res


def focale(cam):
    return cam.get("focal", cam.get("focal_x"))


def echelle(rec):
    """k = mètres par unité du repère, et taille médiane d'un pixel au sol en unités (règle d'ODM, gsd.py)."""
    pts = np.array([p["coordinates"] for p in rec["points"].values()], float)
    arbre = cKDTree(pts[:, :2])
    gsd = []
    for nom, (R, t, c, cam) in poses(rec).items():
        _, vois = arbre.query(c[:2], k=9)
        h = c[2] - np.median(pts[vois, 2])
        gsd.append(h / (focale(cam) * max(cam["width"], cam["height"])))
    g = float(np.median(np.abs(gsd)))
    return CM_PX / 100.0 / g, g, np.array(gsd)


def normaliser_pixels(cam, u, v):
    L, H = cam["width"], cam["height"]
    m = max(L, H)
    return (np.asarray(u, float) - L / 2.0) / m, (np.asarray(v, float) - H / 2.0) / m


def desdistordre(cam, xn, yn):
    """Coordonnées normalisées -> coordonnées sur le plan focal (z = 1), par itérations de point fixe."""
    typ = cam["projection_type"]
    if typ == "brown":
        fx, fy = cam["focal_x"], cam["focal_y"]
        cx, cy = cam.get("c_x", 0.0), cam.get("c_y", 0.0)
        k1, k2, k3 = cam.get("k1", 0), cam.get("k2", 0), cam.get("k3", 0)
        p1, p2 = cam.get("p1", 0), cam.get("p2", 0)
        xd, yd = (xn - cx) / fx, (yn - cy) / fy
    elif typ in ("perspective", "simple_radial", "radial"):
        f = focale(cam)
        fx = cam.get("focal_x", f); fy = cam.get("focal_y", f)
        cx, cy = cam.get("c_x", 0.0), cam.get("c_y", 0.0)
        k1, k2, k3, p1, p2 = cam.get("k1", 0), cam.get("k2", 0), 0, 0, 0
        xd, yd = (xn - cx) / fx, (yn - cy) / fy
    else:
        raise ValueError(f"modèle de caméra non géré : {typ}")
    x, y = xd.copy(), yd.copy()
    for _ in range(30):
        r2 = x * x + y * y
        rad = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 ** 3
        dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        x, y = (xd - dx) / rad, (yd - dy) / rad
    return x, y


def rayons(pose, u, v):
    """Origine (centre) et directions (repère monde) des rayons des pixels (u, v) de la photo."""
    R, t, c, cam = pose
    xn, yn = normaliser_pixels(cam, u, v)
    x, y = desdistordre(cam, xn, yn)
    d = np.stack([x, y, np.ones_like(x)], 1) @ R   # R^T d, ligne par ligne
    return c, d


def projeter(pose, X):
    """Points monde (N, 3) -> pixels (u, v) de la photo (avec distorsion)."""
    R, t, c, cam = pose
    P = X @ R.T + t
    x, y = P[:, 0] / P[:, 2], P[:, 1] / P[:, 2]
    typ = cam["projection_type"]
    f = focale(cam)
    fx = cam.get("focal_x", f); fy = cam.get("focal_y", f)
    cx, cy = cam.get("c_x", 0.0), cam.get("c_y", 0.0)
    k1, k2 = cam.get("k1", 0), cam.get("k2", 0)
    k3, p1, p2 = (cam.get("k3", 0), cam.get("p1", 0), cam.get("p2", 0)) if typ == "brown" else (0, 0, 0)
    r2 = x * x + y * y
    rad = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 ** 3
    xd = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
    yd = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    m = max(cam["width"], cam["height"])
    return (fx * xd + cx) * m + cam["width"] / 2.0, (fy * yd + cy) * m + cam["height"] / 2.0
