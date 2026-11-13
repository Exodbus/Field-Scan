"""Vote des axes linéaires (B′) : carte de preuve des centres (équipe COMPTAGE, convergence-engineer).

Prototype, version du 7 novembre 2026. Pré-enregistrement : `docs/recherche/notes/convergence-engineer.md` § 1.2.

Formulation compatible avec l'indice « orientations convergentes » (H4) ; ce n'est pas une reconstitution.

Entrée : le champ d'orientation de `comptage_math/orientation.py` (importé, non modifié),
z = c · e^{2iφ}, φ = direction du gradient, c = cohérence.

Vote (vraisemblance de von Mises en angle doublé, leaf-mathematician, `modele_feuille.md` § 3) :
    a(x)  = m(x) · c(x)^{p−1} · z(x)                       (module c^p, masque de végétation m)
    k(d)  = ρ(|d|) e^{−2i arg d},  ρ(r) = r_min / r sur [r_min, r_max]   (k(−d) = k(d))
    V     = −Re(a ∗ k)                                    (signe −1 : axes linéaires radiaux)
    z_an  = V / √(½ (|a|² ∗ ρ²) + ε)                      (z sous le nul « orientations uniformes indépendantes »)
    z_vote = (z_an − médiane) / (1,4826 · MAD) sur les pixels valides (z robuste par image, comme A′ dans E-006)
"""
from __future__ import annotations

import math

import numpy as np
from scipy.signal import fftconvolve

from comptage_math import orientation as O

SIGMA_G_M = 0.04   # E-003, T_feuille
SIGMA_T_M = 0.10
R_MIN_M = 0.20


def noyau(res, r_max, r_min=R_MIN_M, rho_forme="inv"):
    """Noyau complexe k(d) = ρ(|d|) e^{−2i arg d} et ρ² (res en m/px).
    rho_forme : "inv" (ρ = r_min/r, E-008) ou "cst" (ρ = 1 sur [r_min, r_max], E-014)."""
    R = int(math.ceil(r_max / res))
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float64)
    r = np.hypot(xx, yy) * res
    dedans = (r >= r_min) & (r <= r_max)
    rho = np.where(dedans, (r_min / np.maximum(r, 1e-9)) if rho_forme == "inv" else 1.0, 0.0)
    k = rho * np.exp(-2j * np.arctan2(yy, xx))
    return k.astype(np.complex64), (rho ** 2).astype(np.float32)


def champ(rgb, res, sigma_t_m=SIGMA_T_M, masque="provisoire", canal="luminance", sigma_g_m=SIGMA_G_M):
    """Champ T_feuille (luminance, σ_g 4 cm, σ_t 10 cm par défaut) et masque de végétation. rgb float (H, W, 3) en RGB 0–255.
    masque : "provisoire" (orientation.masque_vegetation, E-008 à E-012) ou "couleur" (couleur.masque_vegetation, E-014).
    sigma_g_m : échelle de dérivation (E-022 ; défaut 4 cm = B′ figé, inchangé)."""
    bgr = np.ascontiguousarray(rgb[..., ::-1]).clip(0, 255).astype(np.uint8)
    # canal "exg" : témoin T2 (test_final.md § 7), tenseur sur l'ExG normalisé au lieu de la luminance
    Y = O.luminance(bgr) if canal == "luminance" else O.exg_norm_bgr(bgr).astype(np.float32)
    z, _ = O.tenseur(Y, sigma_g_m / res, sigma_t_m / res)
    if masque == "couleur":
        from comptage_math import couleur as CO
        m = CO.masque_vegetation(rgb, rgb.sum(2) > 15, res)
    else:
        m = O.masque_vegetation(bgr)
    return z, m


def zrob(S, valide):
    x = S[valide]
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med))) * 1.4826
    if mad <= 1e-12:
        mad = float(x.std()) + 1e-12
    return ((S - med) / mad).astype(np.float32)


def carte_votes(z, masque, res, r_max=1.3, p=1.0, signe=-1.0, valide=None, melanger=None, rho_forme="inv", normalisation="sd"):
    """Carte de votes à partir du champ d'orientation.

    z : champ complexe c·e^{2iφ} (orientation.tenseur) ; masque : pixels qui votent ; res : m/px.
    melanger : np.random.Generator pour le contrôle « orientations mélangées » (permutation de z dans le masque).
    Retourne dict(V=vote brut, z_an=z analytique, z=z robuste par image (pour la détection et la fusion avec A′)).
    """
    z = z.copy()
    if melanger is not None:
        idx = np.flatnonzero(masque)
        z.flat[idx] = z.flat[melanger.permutation(idx)]
    c = np.abs(z)
    a = np.where(masque, z * (c ** (p - 1.0) if p != 1 else 1.0), 0).astype(np.complex64)
    k, rho2 = noyau(res, r_max, rho_forme=rho_forme)
    V = signe * np.real(fftconvolve(a, k, mode="same")).astype(np.float32)
    if normalisation == "somme":
        # E-014 : normalisation par la somme des poids, V / Σ |a| ρ (alignement moyen pondéré)
        den = fftconvolve(np.abs(a), np.sqrt(rho2), mode="same")
        eps = 1e-3 * float(np.median(den[den > 0])) if (den > 0).any() else 1e-9
        z_an = (V / (np.maximum(den, 0) + eps)).astype(np.float32)
    else:
        var = 0.5 * fftconvolve(np.abs(a) ** 2, rho2, mode="same")
        eps = 1e-3 * float(np.median(var[var > 0])) if (var > 0).any() else 1e-9
        z_an = (V / np.sqrt(np.maximum(var, 0) + eps)).astype(np.float32)
    if valide is None:
        valide = np.ones(z.shape, bool)
    return dict(V=V, z_an=z_an, z=zrob(z_an, valide))


def carte_votes_image(rgb, res, r_max=1.3, p=1.0, melanger=None):
    """Raccourci : image RGB (0–255) → carte de votes ; valide = somme RGB > 15 (comme E-006)."""
    valide = rgb.sum(2) > 15
    z, m = champ(rgb, res)
    return carte_votes(z, m & valide, res, r_max, p, valide=valide, melanger=melanger)


def carte_votes_multi(rgb, res, r_max=1.6, p=1.0, sigmas_t=(SIGMA_T_M,), sigmas_g=None):
    """Fusion des votes sur plusieurs échelles σ_t (E-010, notes § 3.1) : z = zrob(Σ_s z_an,s).
    sigmas_g : échelles de dérivation associées (E-022), une par σ_t ; None = σ_g 4 cm partout (comportement E-010).
    Retourne dict(z=carte robuste, champ=z du canal σ_t = 10 cm (ou le premier), masque)."""
    valide = rgb.sum(2) > 15
    somme, z_ref, m_ref = None, None, None
    if sigmas_g is None:
        sigmas_g = (SIGMA_G_M,) * len(sigmas_t)
    for st, sg in zip(sigmas_t, sigmas_g):
        z, m = champ(rgb, res, st, sigma_g_m=sg)
        m &= valide
        zan = carte_votes(z, m, res, r_max, p, valide=valide)["z_an"]
        somme = zan if somme is None else somme + zan
        if z_ref is None or abs(st - SIGMA_T_M) < 1e-9:
            z_ref, m_ref = z, m
    return dict(z=zrob(somme, valide), champ=z_ref, masque=m_ref, valide=valide)


def attributs_candidats(z, masque, res, pts, r_max, r_min=R_MIN_M, n_secteurs=8, pas_anneau=0.2):
    """Attributs de chaque candidat (notes § 3.4) : n_soutien, fraction de soutien, couverture angulaire, rayon.

    z : champ c·e^{2iφ} ; pts : (n, 2) en pixels (x, y). t = −cos 2(φ − ψ) (1 = axe radial)."""
    H, W = z.shape
    c_all = np.abs(z)
    c_med = float(np.median(c_all[masque])) if masque.any() else 0.0
    R = int(np.ceil(r_max / res))
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    rr = np.hypot(xx, yy) * res
    disque = (rr >= r_min) & (rr <= r_max)
    dy, dx, dr = yy[disque], xx[disque], rr[disque]
    psi = np.arctan2(dy, dx)
    sect = ((psi + np.pi) / (2 * np.pi) * n_secteurs).astype(int) % n_secteurs
    bords = np.arange(r_min, r_max + 1e-9, pas_anneau)
    anneau = np.clip(np.digitize(dr, bords) - 1, 0, len(bords) - 1)
    out = []
    for x, y in pts:
        X, Y = int(x), int(y)
        px, py = X + dx, Y + dy
        ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        ok[ok] &= masque[py[ok], px[ok]]
        if ok.sum() < 10:
            out.append(dict(n_soutien=0, fraction_soutien=np.nan, couverture=np.nan, rayon=np.nan, n_pixels=int(ok.sum())))
            continue
        zz = z[py[ok], px[ok]]
        c = np.abs(zz)
        t = -np.cos(np.angle(zz) - 2 * psi[ok])
        sout = (t > 0.5) & (c > c_med)
        ct = c * t
        s_ = sect[ok]
        moy_s = np.bincount(s_, ct, n_secteurs) / np.maximum(np.bincount(s_, None, n_secteurs), 1)
        a_ = anneau[ok]
        prof = np.bincount(a_, ct, len(bords)) / np.maximum(np.bincount(a_, None, len(bords)), 1)
        if prof.max() > 0:
            k = np.nonzero(prof > 0.5 * prof.max())[0].max()
            rayon = float(min(bords[k] + pas_anneau, r_max))
        else:
            rayon = np.nan
        out.append(dict(n_soutien=int(sout.sum()), fraction_soutien=float((t > 0.5).mean()),
                        couverture=float((moy_s > 0.1).sum() / n_secteurs), rayon=rayon, n_pixels=int(ok.sum())))
    return out


# ---------------------------------------------------------------------------------------------------------------
# E-012 : recentrage des pics et suppression des non-maxima après recentrage (notes § 5.1)
# ---------------------------------------------------------------------------------------------------------------
def recentrer_barycentre(Z, pts, res, rayon=1.5, niveau=0.5):
    """Rb : barycentre, pondéré par Z − niveau·Z(pic), de la composante connexe du pic dans {Z ≥ niveau·Z(pic)},
    restreinte au disque de `rayon` m. Déplacement > rayon refusé. pts (n, 2) en pixels (x, y)."""
    from scipy import ndimage
    H, W = Z.shape
    R = int(np.ceil(rayon / res))
    out = np.array(pts, float).reshape(-1, 2).copy()
    for n, (x, y) in enumerate(out.copy()):
        X, Y = int(x), int(y)
        x0, x1, y0, y1 = max(0, X - R), min(W, X + R + 1), max(0, Y - R), min(H, Y + R + 1)
        w = Z[y0:y1, x0:x1]
        yy, xx = np.mgrid[y0:y1, x0:x1]
        zp = Z[min(Y, H - 1), min(X, W - 1)]
        haut = (w >= niveau * zp) & (((xx - X) ** 2 + (yy - Y) ** 2) <= R * R)
        lab, _ = ndimage.label(haut)
        l = lab[Y - y0, X - x0] if (0 <= Y - y0 < lab.shape[0] and 0 <= X - x0 < lab.shape[1]) else 0
        if l == 0:
            continue
        m = lab == l
        p = np.maximum(w[m] - niveau * zp, 0) + 1e-9
        bx, by = (xx[m] * p).sum() / p.sum() + 0.5, (yy[m] * p).sum() / p.sum() + 0.5
        if np.hypot(bx - x, by - y) * res <= rayon:
            out[n] = (bx, by)
    return out


def recentrer_mc(z, masque, res, pts, r_max, r_min=R_MIN_M, n_iter=3, d_max=1.5):
    """Rmc : point de convergence par moindres carrés des droites support (axe linéaire = φ + 90°),
    poids c · max(t, 0) · r_min / r, t = −cos 2(φ − ψ(p)) ; 3 itérations depuis le pic ; déplacement > d_max refusé."""
    H, W = z.shape
    R = int(np.ceil(r_max / res)) + int(np.ceil(d_max / res))
    ys, xs = np.nonzero(masque)
    out = np.array(pts, float).reshape(-1, 2).copy()
    for n, (x0, y0) in enumerate(out.copy()):
        sel = (np.abs(xs + 0.5 - x0) <= R) & (np.abs(ys + 0.5 - y0) <= R)
        px, py = xs[sel] + 0.5, ys[sel] + 0.5
        if len(px) < 10:
            continue
        zz = z[ys[sel], xs[sel]]
        c, phi = np.abs(zz), np.angle(zz) / 2
        ux, uy = np.cos(phi + np.pi / 2), np.sin(phi + np.pi / 2)
        p = np.array([x0, y0])
        for _ in range(n_iter):
            dx, dy = px - p[0], py - p[1]
            r = np.hypot(dx, dy) * res
            t = -np.cos(2 * phi - 2 * np.arctan2(dy, dx))
            w = c * np.maximum(t, 0) * np.where((r >= r_min) & (r <= r_max), r_min / np.maximum(r, 1e-9), 0)
            if w.sum() <= 0:
                break
            a11, a22, a12 = (w * (1 - ux * ux)).sum(), (w * (1 - uy * uy)).sum(), (w * (-ux * uy)).sum()
            b1 = (w * ((1 - ux * ux) * px - ux * uy * py)).sum()
            b2 = (w * (-ux * uy * px + (1 - uy * uy) * py)).sum()
            det = a11 * a22 - a12 * a12
            if abs(det) < 1e-9:
                break
            p = np.array([(a22 * b1 - a12 * b2) / det, (a11 * b2 - a12 * b1) / det])
        if np.all(np.isfinite(p)) and np.hypot(*(p - (x0, y0))) * res <= d_max:
            out[n] = p
    return out


def nms_points(pts, sc, rayon_px):
    """Suppression gloutonne par score décroissant (N1)."""
    from scipy.spatial import cKDTree
    if len(pts) == 0:
        return pts, sc
    ordre = np.argsort(-sc)
    arbre = cKDTree(pts)
    garde = np.zeros(len(pts), bool)
    pris = np.zeros(len(pts), bool)
    for i in ordre:
        if pris[i]:
            continue
        garde[i] = True
        pris[arbre.query_ball_point(pts[i], rayon_px)] = True
    return pts[garde], sc[garde]


# ---------------------------------------------------------------------------------------------------------------
# E-019 : F′, une feuille = un segment connexe cohérent du champ d'orientation de B′ (C-003, notes § 11)
# Ajout du 7 novembre 2026 ; les fonctions de B′ ci-dessus ne sont pas modifiées.
# Formulation compatible avec les indices « vecteurs sur les feuilles » et « orientation » ; ce n'est pas une reconstitution.
# ---------------------------------------------------------------------------------------------------------------
DELTA_M = R_MIN_M        # δ : distance base du limbe → centre, a priori = r_min de B′ (0,2 m), non réglé
KAPPA_SIGMA = 0.25       # σ_k = max(σ_min, κ d_k), comme modèle F (modele_feuille.md § 10.2)
SIGMA_MIN_M = 0.15
L_MAX_M = 2.6            # longueur de limbe maximale a priori (plant-geometry, 0,8–2,5 m) ; ℓ est tronquée


def segments_feuilles(z, masque, res, q_coh=0.5, n_classes=6, l_min=0.3, allong_min=1.5, recouv=0.5, melanger=None):
    """Segments-feuilles F′.

    1. Pixels cohérents : masque & c ≥ quantile q_coh de c sur le masque (c = |z|).
    2. Axe de la structure linéaire α = φ + 90° (B′ vote le long de cet axe), quantifié en n_classes classes de π/n_classes,
       deux quantifications décalées d'une demi-classe (une feuille à cheval sur une frontière reste entière dans l'une).
    3. Composantes 4-connexes par classe ; moments pondérés par c : centre p, axe u = moyenne en angle doublé de −z
       (orientation du tenseur, pas l'ACP des pixels), étendue ℓ = √12 · écart type des projections sur u,
       largeur w = √12 · écart type sur la normale (longueur d'un segment uniforme).
    4. Filtre : ℓ ≥ l_min, ℓ / w ≥ allong_min ; doublons entre les deux quantifications : glouton par nombre de pixels
       décroissant, un segment est gardé si au moins `recouv` de ses pixels ne sont pas déjà pris.
    melanger : np.random.Generator, contrôle « orientations mélangées » (permutation de z dans le masque, avant tout).
    Retourne dict de tableaux : x, y (px, centre), ux, uy, l (m), w (m), coh (cohérence moyenne), n (pixels).
    """
    from scipy import ndimage
    z = z.copy()
    if melanger is not None:
        idx = np.flatnonzero(masque)
        z.flat[idx] = z.flat[melanger.permutation(idx)]
    vide = {k: np.zeros(0) for k in ("x", "y", "ux", "uy", "l", "w", "coh", "n")}
    c = np.abs(z)
    ok = masque & (c > 0)
    if ok.sum() < 50:
        return vide
    fort = ok & (c >= np.quantile(c[ok], q_coh))
    alpha = (np.angle(-z) / 2.0) % np.pi
    H, W = z.shape
    yy, xx = np.mgrid[0:H, 0:W]
    n_min = max(5, int(l_min * l_min / allong_min / res / res))
    comps = []    # (n, indices plats, stats)
    for decal in (0.0, 0.5):
        q = np.floor(alpha / (np.pi / n_classes) + decal).astype(np.int32) % n_classes
        for k in range(n_classes):
            lab, n = ndimage.label(fort & (q == k))
            if n == 0:
                continue
            lf = lab.ravel()
            sel = np.flatnonzero(lf)
            ordre = sel[np.argsort(lf[sel], kind="stable")]
            nb = np.bincount(lf[ordre], minlength=n + 1)[1:]
            debuts = np.r_[0, np.cumsum(nb)]
            for j in np.flatnonzero(nb >= n_min):
                comps.append((int(nb[j]), ordre[debuts[j]:debuts[j + 1]]))
    comps.sort(key=lambda t: -t[0])
    pris = np.zeros(H * W, bool)
    out = {k: [] for k in vide}
    cf, zf, xf, yf = c.ravel(), z.ravel(), xx.ravel() + 0.5, yy.ravel() + 0.5
    for nb, ids in comps:
        libres = ~pris[ids]
        if libres.mean() < recouv:
            continue
        w8 = cf[ids]
        sw = w8.sum()
        mx, my = (w8 * xf[ids]).sum() / sw, (w8 * yf[ids]).sum() / sw
        a = np.angle((w8 * (-zf[ids])).sum()) / 2.0
        ux, uy = math.cos(a), math.sin(a)
        dx, dy = xf[ids] - mx, yf[ids] - my
        s, t = dx * ux + dy * uy, -dx * uy + dy * ux
        l = math.sqrt(12 * (w8 * s * s).sum() / sw) * res
        wd = math.sqrt(12 * (w8 * t * t).sum() / sw) * res
        if l < l_min or l < allong_min * wd:
            continue
        pris[ids] = True
        for k_, v in (("x", mx), ("y", my), ("ux", ux), ("uy", uy), ("l", l), ("w", wd), ("coh", sw / nb), ("n", nb)):
            out[k_].append(v)
    return {k: np.asarray(v, float) for k, v in out.items()}


def carte_votes_segments(seg, forme, res, poids="un", delta=DELTA_M, kappa=KAPPA_SIGMA, sigma_min=SIGMA_MIN_M,
                         l_max=L_MAX_M, d_fixe=None, sigma_fixe=None):
    """Carte F′ : chaque segment vote en un point de chaque côté, p ± d u, d = min(ℓ, l_max)/2 + δ.

    Noyau gaussien de crête 1 et d'écart type σ = max(σ_min, κ d) : avec poids « un », V(c) compte les feuilles qui
    désignent c. poids : « un » (une voix par feuille) ou « lc » (ℓ × cohérence moyenne).
    d_fixe, sigma_fixe : témoin d'échelle fixe (mêmes segments, distance et lissage communs).
    σ discrétisé sur une grille géométrique (pas de 2^{1/4}) pour un filtrage par niveau.
    """
    from scipy import ndimage
    H, W = forme
    V = np.zeros(forme, np.float32)
    if len(seg["x"]) == 0:
        return V
    d = (np.minimum(seg["l"], l_max) / 2 + delta) if d_fixe is None else np.full(len(seg["x"]), float(d_fixe))
    sig = np.maximum(sigma_min, kappa * d) if sigma_fixe is None else np.full(len(d), float(sigma_fixe))
    w = np.ones(len(d)) if poids == "un" else seg["l"] * seg["coh"]
    niveaux = sigma_min * 2.0 ** (np.arange(0, 12) / 4.0)
    nv = np.abs(np.log(sig[:, None] / niveaux[None, :])).argmin(1)
    for s_ in (-1.0, 1.0):
        px = seg["x"] + s_ * d * seg["ux"] / res
        py = seg["y"] + s_ * d * seg["uy"] / res
        ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        for k in np.unique(nv[ok]):
            m = ok & (nv == k)
            imp = np.zeros(forme, np.float32)
            np.add.at(imp, (py[m].astype(int), px[m].astype(int)), w[m])
            sp = niveaux[k] / res
            V += (ndimage.gaussian_filter(imp, sp, truncate=3.0) * (2 * math.pi * sp * sp)).astype(np.float32)
    return V
