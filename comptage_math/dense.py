# -*- coding: utf-8 -*-
"""Distance aux trouées de la canopée — E-024 (dense-canopy-engineer).

Formulation : docs/experiment-log.md, entrée E-024 ; précisions écrites avant calcul dans
docs/recherche/notes/dense-canopy-engineer.md § 1.0. Le vote B′ (votes.py) n'est pas modifié.

Hypothèse [H] : en canopée dense, le centre d'un plant est le point de feuillage le plus éloigné des trouées
(formulation compatible avec la délimitation de couronnes par carte de distance, [S] Wang, Gong et Biging 2004,
PE&RS 70(3)).

    trouées = (non végétation) ∪ (luminance lissée à 5 cm < centile p de la végétation de la tuile)
    nettoyage : ouverture (disque r = max(1, round(2,5 cm / res)) px), puis suppression des composantes < a m²
    D = distance euclidienne aux trouées (m), lissée à σ_d, z robuste sur végétation ∩ valides.

numpy, scipy (ndimage) et OpenCV seulement.
"""
import cv2
import numpy as np
from scipy import ndimage

from comptage_math import orientation as O

SIGMA_LUM_M = 0.05
R_OUVERTURE_M = 0.025
SEUIL_VALIDE = 15


def valides(rgb):
    return rgb.sum(2) > SEUIL_VALIDE


def masque_vegetation(rgb):
    """Masque de votes.champ avec ses défauts (masque « provisoire ») = orientation.masque_vegetation(bgr)."""
    bgr = np.ascontiguousarray(rgb[..., ::-1]).clip(0, 255).astype(np.uint8)
    return O.masque_vegetation(bgr)


def luminance_lissee(rgb, res, sigma_m=SIGMA_LUM_M):
    bgr = np.ascontiguousarray(rgb[..., ::-1]).clip(0, 255).astype(np.uint8)
    Y = O.luminance(bgr).astype(np.float32)
    return cv2.GaussianBlur(Y, (0, 0), max(sigma_m / res, 0.3), borderType=cv2.BORDER_REFLECT)


def trouees_brutes(rgb, res, p, veg=None, valide=None):
    """Pixels hors végétation, ou de luminance lissée sous le centile p de la végétation valide de la tuile."""
    veg = masque_vegetation(rgb) if veg is None else veg
    valide = valides(rgb) if valide is None else valide
    Y = luminance_lissee(rgb, res)
    mv = veg & valide
    if mv.sum() < 1:
        return ~mv
    t = float(np.percentile(Y[mv], p))
    return (~veg) | (Y < t)


def nettoyer(trou, res, a_m2):
    """Ouverture par un disque, puis suppression des composantes (8-connexité) d'aire < a_m2."""
    r = max(1, int(round(R_OUVERTURE_M / res)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    t = cv2.morphologyEx(trou.astype(np.uint8), cv2.MORPH_OPEN, k, borderType=cv2.BORDER_REPLICATE)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(t, connectivity=8)
    a_px = a_m2 / (res * res)
    garde = np.zeros(n, bool)
    garde[1:] = stats[1:, cv2.CC_STAT_AREA] >= a_px
    return garde[lab]


def distance(trou, res):
    """Distance euclidienne (m) de chaque pixel à la trouée la plus proche ; l'extérieur de la tuile n'est pas une
    trouée. None si aucune trouée."""
    if not trou.any():
        return None
    return (ndimage.distance_transform_edt(~trou) * res).astype(np.float32)


def zrob_masque(S, masque):
    """z robuste : médiane et MAD × 1,4826 sur le masque (repli : toute la tuile), appliquées à toute la tuile."""
    x = S[masque] if masque.sum() >= 100 else S.ravel()
    med = float(np.median(x))
    mad = 1.4826 * float(np.median(np.abs(x - med)))
    if mad <= 1e-12:
        mad = float(x.std()) + 1e-12
    return ((S - med) / mad).astype(np.float32)


def cartes_distance(rgb, res, ps=(15, 25), aires_m2=(0.02, 0.08), sigmas_d_m=(0.10, 0.25), avec_trouees=False):
    """Image RGB (0–255, float) → {(p, a, σ_d): z_D}. Si avec_trouees : renvoie aussi {(p, a): trouées nettoyées}."""
    veg = masque_vegetation(rgb)
    val = valides(rgb)
    mz = veg & val
    out, tr = {}, {}
    for p in ps:
        brut = trouees_brutes(rgb, res, p, veg, val)
        for a in aires_m2:
            t = nettoyer(brut, res, a)
            tr[(p, a)] = t
            D = distance(t, res)
            for sd in sigmas_d_m:
                if D is None:
                    out[(p, a, sd)] = np.zeros(rgb.shape[:2], np.float32)
                    continue
                Ds = cv2.GaussianBlur(D, (0, 0), max(sd / res, 0.3), borderType=cv2.BORDER_REFLECT)
                out[(p, a, sd)] = zrob_masque(Ds, mz)
    return (out, tr) if avec_trouees else out
