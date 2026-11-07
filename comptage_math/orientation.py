"""Champ d'orientation local et fiabilité par pixel (équipe VISION, orientation-engineer).

Prototype, version du 7 novembre 2026. Aucun vote de centre ici (rôle de convergence-engineer).

Conventions (identiques à `comptage_math/feuille.py`) :
- image en (ligne, colonne), x = colonne vers la droite, y = ligne vers le bas ;
- φ = direction du GRADIENT dominant (ou du vecteur d'onde d'un Gabor), en angle
  doublé z = c · e^{2iφ}, c ∈ [0, 1] la cohérence ;
- l'axe d'une STRUCTURE LINÉAIRE (bord de limbe, nervure) est φ + 90° ; celui de
  STRIES perpendiculaires à la nervure est φ (le gradient traverse les stries,
  donc il est parallèle à la nervure).

Conséquence, vue depuis un centre c et ψ = arg(x − c) :
- cos 2(φ − ψ) > 0 : gradient radial (stries, ou bord d'une tache isotrope : HF-06) ;
- cos 2(φ − ψ) < 0 : gradient tangentiel (bords de limbe et nervure radiaux).
Les deux mécanismes portent la même information « axe radial » mais avec des SIGNES
OPPOSÉS en angle doublé : un tenseur unique qui les mélange les fait s'annuler
(objection OBJ-V1, `docs/recherche/notes/orientation-engineer.md`).

Canaux fournis :
- `tenseur(Y, sg, st)` : tenseur de structure (dérivée σ_g, intégration σ_t, en px) ;
- `tenseur_unitaire(Y, sg, st)` : même chose avec gradients normalisés AVANT
  l'intégration (chaque pixel pèse 1 : un bord fort ne domine plus sa fenêtre) ;
- `gabor(Y, lam, n_theta)` : banc de Gabor complexes accordés à λ (px), orientation
  par moyenne en angle doublé des énergies ;
- `fiabilite(...)` : cohérence × énergie saturée × accord entre deux échelles,
  restreinte au masque de végétation.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from scipy import ndimage


def luminance(img_bgr):
    """Luminance en [0, 1] (image OpenCV BGR uint8)."""
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0


def exg_norm_bgr(img_bgr):
    b, g, r = [img_bgr[..., k].astype(np.float32) for k in range(3)]
    return (2 * g - r - b) / (r + g + b + 1e-6)


def masque_vegetation(img_bgr, sigma_px=2.0, seuil_exg=0.05, seuil_lum=0.18):
    """Masque provisoire (en attendant vegetation-color-engineer) : ExG lissé > seuil
    et luminance > seuil (exclut les ombres profondes, où l'ExG est du bruit)."""
    e = ndimage.gaussian_filter(exg_norm_bgr(img_bgr), sigma_px)
    y = ndimage.gaussian_filter(luminance(img_bgr), sigma_px)
    return (e > seuil_exg) & (y > seuil_lum)


def _gradients(Y, sg):
    sg = max(float(sg), 0.7)
    gx = ndimage.gaussian_filter(Y, sg, order=(0, 1))
    gy = ndimage.gaussian_filter(Y, sg, order=(1, 0))
    return gx, gy


def tenseur(Y, sg, st):
    """z = <(gx + i gy)²>_σt / <|g|²>_σt ; retourne (z, énergie <|g|²>)."""
    gx, gy = _gradients(Y, sg)
    st = max(float(st), 1.0)
    jxx = ndimage.gaussian_filter(gx * gx, st)
    jyy = ndimage.gaussian_filter(gy * gy, st)
    jxy = ndimage.gaussian_filter(gx * gy, st)
    e = jxx + jyy
    z = ((jxx - jyy) + 2j * jxy) / (e + 1e-10)
    return z.astype(np.complex64), e.astype(np.float32)


def tenseur_unitaire(Y, sg, st, eps_rel=0.05):
    """Tenseur à gradients normalisés : chaque pixel apporte e^{2iφ} pondéré par
    |g|²/(|g|² + ε²), ε = eps_rel × médiane de |g| (seuil de bruit). Un bord à fort
    contraste ne pèse pas plus qu'une strie faible mais nette."""
    gx, gy = _gradients(Y, sg)
    m2 = gx * gx + gy * gy
    eps2 = (eps_rel * np.median(np.sqrt(m2))) ** 2 + 1e-12
    w = m2 / (m2 + eps2)
    u = ((gx * gx - gy * gy) + 2j * gx * gy) / (m2 + 1e-12) * w
    st = max(float(st), 1.0)
    zr = ndimage.gaussian_filter(u.real.astype(np.float32), st)
    zi = ndimage.gaussian_filter(u.imag.astype(np.float32), st)
    wn = ndimage.gaussian_filter(w.astype(np.float32), st)
    return ((zr + 1j * zi) / (wn + 1e-6)).astype(np.complex64), wn


def gabor(Y, lam, n_theta=8, sigma_rel=0.56, gamma=0.5):
    """Banc de Gabor complexes (quadrature) accordés à la période λ (px).

    sigma = sigma_rel × λ (≈ 1 octave), gamma < 1 : enveloppe ALLONGÉE le long des
    stries (gamma = rapport des axes en travers / le long du vecteur d'onde dans la
    convention OpenCV : σ_y = σ/γ), ce qui favorise les motifs périodiques sur
    plusieurs périodes par rapport aux bords isolés.
    Orientation : z = Σ_k E_k e^{2iθ_k} / Σ_k E_k, θ_k = direction du vecteur d'onde.
    Retourne (z, énergie totale)."""
    lam = max(float(lam), 2.5)
    sig = sigma_rel * lam
    k = int(2 * math.ceil(3 * sig / min(gamma, 1.0)) + 1)
    num = np.zeros(Y.shape, np.complex64)
    den = np.zeros(Y.shape, np.float32)
    Yc = Y - ndimage.uniform_filter(Y, int(4 * lam) | 1)
    for t in range(n_theta):
        th = math.pi * t / n_theta
        kr = cv2.getGaborKernel((k, k), sig, th, lam, gamma, 0.0, ktype=cv2.CV_32F)
        ki = cv2.getGaborKernel((k, k), sig, th, lam, gamma, math.pi / 2, ktype=cv2.CV_32F)
        kr -= kr.mean()
        r = cv2.filter2D(Yc, cv2.CV_32F, kr)
        i = cv2.filter2D(Yc, cv2.CV_32F, ki)
        e = r * r + i * i
        num += e * np.exp(2j * th)
        den += e
    return (num / (den + 1e-10)).astype(np.complex64), den


def fiabilite(z_fin, z_gros, energie, masque, e_ref=None):
    """Fiabilité ∈ [0, 1] par pixel = cohérence × énergie saturée × accord d'échelles.

    - cohérence = |z_fin| ;
    - énergie saturée = E / (E + E_ref), E_ref = médiane de E sur le masque ;
    - accord = |cos 2(φ_fin − φ_gros)| (une même direction d'axe à deux échelles,
      quel que soit le mécanisme : stries et bords donnent des signes opposés, d'où
      la valeur absolue).
    Nulle hors du masque de végétation."""
    coh = np.abs(z_fin)
    if e_ref is None:
        e_ref = float(np.median(energie[masque])) if masque.any() else 1.0
    es = energie / (energie + e_ref + 1e-12)
    a = np.abs(np.cos(np.angle(z_fin) - np.angle(z_gros)))  # angles déjà doublés
    return (coh * es * a * masque).astype(np.float32)


def ecart_radial(z, xs, ys, cx, cy):
    """cos 2(φ − ψ) aux pixels (xs, ys) pour leurs centres (cx, cy) ;
    ψ = arg(x − c). Retourne (cos2, cohérence)."""
    zz = z[ys, xs]
    psi = np.arctan2(ys - cy, xs - cx)
    return np.cos(np.angle(zz) - 2 * psi), np.abs(zz)
