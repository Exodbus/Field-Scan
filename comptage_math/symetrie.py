# -*- coding: utf-8 -*-
"""Transformée de symétrie radiale rapide (FRST) à l'échelle de la couronne — E-023 (convergence-engineer).

[S] G. Loy et A. Zelinsky, « Fast Radial Symmetry for Detecting Points of Interest », IEEE TPAMI 25(8), 2003.
Formulation : docs/experiment-log.md, entrée E-023 ; précisions écrites avant calcul dans
docs/recherche/notes/convergence-engineer.md § 13.0. Le vote B′ (votes.py) n'est pas modifié.

Pour chaque pixel p de gradient g (luminance lissée à σ_s), p± = p ± round(n ĝ) :
    O_n(p±) ± 1, M_n(p±) ± |g| ; Õ_n = O_n écrêté à ± k_n ; F_n = (M_n / k_n) (|Õ_n| / k_n)^α ;
    S = moyenne sur n de F_n ∗ A_n, A_n gaussienne d'écart-type 0,25 n.
Polarités : "pos" (votes en p+ : centre clair), "neg" (votes en p−, signe retourné : centre sombre),
"deux" (accumulation signée de l'article, score |S|).
numpy, scipy et OpenCV seulement.
"""
import cv2
import numpy as np

from comptage_math import orientation as O

RAYONS_M = (0.6, 0.9, 1.2, 1.5)
K_N = 8.0
POLARITES = ("pos", "neg", "deux")


def _accumuler(idx, poids, n_pix):
    return np.bincount(idx, weights=poids, minlength=n_pix)


def frst(lum, res, sigma_s_m, rayons_m=RAYONS_M, alphas=(1.0, 2.0), polarites=POLARITES, vote=None, k_n=K_N):
    """lum : luminance (H, W) float ; res : m/px ; vote : masque bool des pixels qui votent (None = tous).
    Retourne {(polarite, alpha): S (H, W) float32}, S ≥ 0 au centre recherché pour chaque polarité."""
    H, W = lum.shape
    s_px = max(sigma_s_m / res, 0.5)
    L = cv2.GaussianBlur(lum.astype(np.float32), (0, 0), s_px, borderType=cv2.BORDER_REFLECT)
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    mag = np.hypot(gx, gy)
    ok = mag > 1e-6
    if vote is not None:
        ok &= vote
    yy, xx = np.nonzero(ok)
    m = mag[yy, xx].astype(np.float64)
    ux, uy = gx[yy, xx] / mag[yy, xx], gy[yy, xx] / mag[yy, xx]
    n_pix = H * W
    somme = {(p, a): np.zeros((H, W), np.float64) for p in polarites for a in alphas}
    for n_m in rayons_m:
        n = n_m / res
        acc = {}
        for sgn, cle in ((1, "+"), (-1, "-")):
            tx = np.rint(xx + sgn * n * ux).astype(np.int64)
            ty = np.rint(yy + sgn * n * uy).astype(np.int64)
            dedans = (tx >= 0) & (tx < W) & (ty >= 0) & (ty < H)
            i = ty[dedans] * W + tx[dedans]
            acc[cle] = (_accumuler(i, None, n_pix).reshape(H, W), _accumuler(i, m[dedans], n_pix).reshape(H, W))
        On_p, Mn_p = acc["+"]
        On_m, Mn_m = acc["-"]
        sig = 0.25 * n
        for p in polarites:
            if p == "pos":
                On, Mn = On_p, Mn_p
            elif p == "neg":
                On, Mn = On_m, Mn_m           # signe retourné : S ≥ 0 au centre sombre
            else:
                On, Mn = On_p - On_m, Mn_p - Mn_m
            Ot = np.clip(On, -k_n, k_n)
            for a in alphas:
                F = (Mn / k_n) * (np.abs(Ot) / k_n) ** a
                Sn = cv2.GaussianBlur(F.astype(np.float32), (0, 0), sig, borderType=cv2.BORDER_CONSTANT)
                somme[(p, a)] += Sn
    out = {}
    for (p, a), s in somme.items():
        s = s / len(rayons_m)
        out[(p, a)] = (np.abs(s) if p == "deux" else s).astype(np.float32)
    return out


def masque_vote(valide, res, sigma_s_m):
    """Pixels valides érodés de ⌈3 σ_s / res⌉ + 1 px : les bords noirs du disque ne votent pas (§ 13.0)."""
    r = int(np.ceil(3 * sigma_s_m / res)) + 1
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.erode(valide.astype(np.uint8), k, borderType=cv2.BORDER_CONSTANT, borderValue=1).astype(bool)


def zrob_masque(S, masque):
    """z robuste : médiane et MAD sur le masque, appliquées à toute la tuile."""
    x = S[masque] if masque.sum() >= 100 else S.ravel()
    med = float(np.median(x))
    mad = 1.4826 * float(np.median(np.abs(x - med)))
    if mad <= 1e-12:
        mad = float(x.std()) + 1e-12
    return ((S - med) / mad).astype(np.float32)


def cartes_frst(rgb, res, sigmas_s_m=(0.08, 0.16), rayons_m=RAYONS_M, alphas=(1.0, 2.0), masque_z=None):
    """Image RGB (0–255, float) → {(σ_s, polarite, alpha): z_FRST}. masque_z : masque de normalisation
    (végétation de votes.champ ∩ valide) ; None = pixels valides."""
    bgr = np.ascontiguousarray(rgb[..., ::-1]).clip(0, 255).astype(np.uint8)
    lum = O.luminance(bgr).astype(np.float32)
    valide = rgb.sum(2) > 15
    mz = valide if masque_z is None else masque_z
    out = {}
    for ss in sigmas_s_m:
        S = frst(lum, res, ss, rayons_m, alphas, vote=masque_vote(valide, res, ss))
        for (p, a), s in S.items():
            out[(ss, p, a)] = zrob_masque(s, mz)
    return out
