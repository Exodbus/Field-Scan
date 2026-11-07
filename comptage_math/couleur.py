# -*- coding: utf-8 -*-
"""Couleur et texture pour le comptage mathématique (vegetation-color-engineer).

Contenu (pré-enregistré dans docs/recherche/notes/vegetation-color-engineer.md § 1) :
  - indices : ExG normalisé, Lab (OpenCV, L* 0–100, a*, b*), teinte de Lab h = atan2(b*, a*) en degrés [0 ; 360) ;
  - carte d'ombres relative à la tuile : L* < 0,55 × médiane(L*) des pixels valides ;
  - masque de végétation « propre » : (ExG > 0,05 ou a* < −4) et non ombre. Le terme a* récupère les limbes pâles,
    presque blancs, dont l'ExG est faible mais qui restent du côté vert de l'axe a* ;
  - descripteurs autour d'un point, normalisés par tuile :
      d1 = fraction de « limbe large » (végétation lisse) dans un disque de rayon 1,5 m ;
      d2 = teinte moyenne de la végétation dans un disque de 1,0 m, moins la médiane de la tuile ;
      d3 = fraction non végétale (ni végétation ni ombre) dans un disque de 1,0 m.

Toutes les entrées sont des tableaux RGB float 0–255 (H, W, 3) et un masque `valide` (pixels de la tuile).
"""
import cv2
import numpy as np
from scipy import ndimage

SIGMA_LISSAGE_M = 0.04
SEUIL_OMBRE_REL = 0.55
SEUIL_EXG = 0.05
SEUIL_A = -4.0
SIGMA_TEXTURE_M = 0.06
RAYON_D1_M = 1.5
RAYON_D2_M = 1.0
RAYON_D3_M = 1.0


def exg_norm(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (2 * g - r - b) / (r + g + b + 1e-6)


def lab(rgb):
    """L* (0–100), a*, b* d'OpenCV sur un RGB float 0–255."""
    x = np.clip(rgb / 255.0, 0, 1).astype(np.float32)
    L = cv2.cvtColor(x, cv2.COLOR_RGB2Lab)
    return L[..., 0], L[..., 1], L[..., 2]


def _lisse(v, sigma_px):
    return ndimage.gaussian_filter(v.astype(np.float32), max(0.5, sigma_px))


def cartes(rgb, valide, res_m):
    """Indices lissés, carte d'ombres et masque propre. res_m : mètres par pixel."""
    s = SIGMA_LISSAGE_M / res_m
    Ls, a, b = lab(rgb)
    Ls, a, b = _lisse(Ls, s), _lisse(a, s), _lisse(b, s)
    e = _lisse(exg_norm(rgb), s)
    med_L = float(np.median(Ls[valide])) if valide.any() else 50.0
    ombre = (Ls < SEUIL_OMBRE_REL * med_L) & valide
    veg = ((e > SEUIL_EXG) | (a < SEUIL_A)) & ~ombre & valide
    h = np.mod(np.degrees(np.arctan2(b, a)), 360.0).astype(np.float32)
    return dict(L=Ls, a=a, b=b, exg=e, h=h, ombre=ombre, veg=veg, valide=valide)


def masque_vegetation(rgb, valide, res_m):
    """Masque de végétation propre (remplace le masque provisoire ExG > 0,05 et Y > 0,18)."""
    return cartes(rgb, valide, res_m)["veg"]


def masque_provisoire(rgb, sigma_px=2.0):
    """Masque provisoire d'orientation-engineer, recopié pour comparaison (orientation.masque_vegetation)."""
    e = ndimage.gaussian_filter(exg_norm(rgb), sigma_px)
    y = ndimage.gaussian_filter(cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
                                .astype(np.float32) / 255.0, sigma_px)
    return (e > 0.05) & (y > 0.18)


def _disque(r_px):
    r = max(1, int(round(r_px)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return ((xx ** 2 + yy ** 2) <= r * r).astype(np.float32)


def moyenne_disque(v, poids, r_px):
    """Moyenne de v pondérée par `poids` sur un disque de rayon r_px (cartes entières)."""
    k = _disque(r_px)
    num = cv2.filter2D((v * poids).astype(np.float32), -1, k, borderType=cv2.BORDER_CONSTANT)
    den = cv2.filter2D(poids.astype(np.float32), -1, k, borderType=cv2.BORDER_CONSTANT)
    return num / np.maximum(den, 1e-6), den


def carte_descripteurs(rgb, valide, res_m, C=None):
    """Cartes d1, d2, d3 (valeurs brutes, normalisées par tuile) et cartes de base."""
    if C is None:
        C = cartes(rgb, valide, res_m)
    veg, v = C["veg"], valide.astype(np.float32)
    # d1 : limbe large = végétation dont la variance locale de luminance est sous la médiane de la tuile
    st = SIGMA_TEXTURE_M / res_m
    Y = C["L"] / 100.0
    hp = Y - _lisse(Y, st)
    sd = np.sqrt(np.maximum(_lisse(hp * hp, st), 0))
    med_sd = float(np.median(sd[veg])) if veg.any() else 0.0
    limbe = veg & (sd < med_sd)
    d1, _ = moyenne_disque(limbe.astype(np.float32), v, RAYON_D1_M / res_m)
    # d2 : teinte moyenne de la végétation dans le disque, relative à la médiane de la tuile
    med_h = float(np.median(C["h"][veg])) if veg.any() else 0.0
    d2, den = moyenne_disque(C["h"], veg.astype(np.float32), RAYON_D2_M / res_m)
    d2 = np.where(den > 0.5, d2 - med_h, 0.0).astype(np.float32)
    # d3 : fraction non végétale (ni végétation propre, ni ombre)
    sol = valide & ~veg & ~C["ombre"]
    d3, _ = moyenne_disque(sol.astype(np.float32), v, RAYON_D3_M / res_m)
    return dict(d1=d1, d2=d2, d3=d3, limbe=limbe, C=C)


def echantillonner(carte, pts):
    if not len(pts):
        return np.zeros(0, np.float32)
    H, W = carte.shape
    x = np.clip(pts[:, 0].astype(int), 0, W - 1)
    y = np.clip(pts[:, 1].astype(int), 0, H - 1)
    return carte[y, x]


def descripteurs(rgb, valide, res_m, pts):
    """Descripteurs bruts (n, 3) aux points pts (x, y en pixels)."""
    D = carte_descripteurs(rgb, valide, res_m)
    return np.c_[echantillonner(D["d1"], pts), echantillonner(D["d2"], pts), echantillonner(D["d3"], pts)]
