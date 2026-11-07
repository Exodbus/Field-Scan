# -*- coding: utf-8 -*-
"""Modèles paramétriques d'une feuille de bananier vue du dessus et d'un plant.

Implémentation de référence (leaf-mathematician) des deux modèles décrits dans
`docs/recherche/modele_feuille.md` :

- Modèle A, « étoile de gaussiennes anisotropes » : formulation compatible avec
  les indices « gaussiennes », « formes », « orientations » (H1, H2, H4).
  Rendu : `rendre_plant_A`. Détecteur : `filtre_A` (banque de filtres adaptés
  ancrés au centre, vraisemblance gaussienne profilée).
- Modèle B, « bandes nervurées striées et profil radial de couleur » :
  formulation compatible avec les indices « stries », « orientations »,
  « couleurs » (H3, H4, H5). Rendu : `rendre_plant_B`. Détecteur : `filtre_B`
  (vraisemblance von Mises d'un champ d'orientation, réduite à une convolution
  complexe, plus un terme radial de couleur).

Aucun de ces modèles n'est « la fonction de Philemon », qui est inconnue.
Tous les intervalles de paramètres sont des hypothèses [H] tant que
banana-morphology ne les a pas sourcés.

Conventions : image en tableau (ligne, colonne) ; coordonnées métriques
x = colonne × res, y = ligne × res (y vers le bas) ; angle θ mesuré de l'axe x
vers l'axe y ; résolution `res` en mètres par pixel. Images RVB flottantes
dans [0, 1].
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np
from scipy import ndimage

# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------


@dataclass
class Feuille:
    """Une feuille vue du dessus. Les champs inutiles à un modèle sont ignorés."""
    theta: float            # direction de la nervure depuis le centre (rad)
    longueur: float         # L, longueur du limbe (m)              [H] 0,8–2,5
    largeur: float          # W, largeur maximale du limbe (m)      [H] 0,35–0,9
    r0: float               # distance centre → base du limbe (m)   [H] 0,1–0,6
    amplitude: float = 1.0  # a, contraste de l'indice de végétation (modèle A)
    courbure: float = 0.0   # κ, courbure de la nervure (1/m)       [H] |κ| ≤ 0,6/L
    lambda_stries: float = 0.10  # λ, espacement des déchirures (m) [H] 0,03–0,20
    angle_stries: float = math.pi / 2  # β, angle stries/nervure    [H] 60°–90°
    contraste_stries: float = 0.5      # c_s, profondeur des stries [H] 0–0,8
    largeur_nervure: float = 0.03      # largeur de la nervure (m)  [H] 0,02–0,06
    seche: bool = False                # feuille sèche (brune)


@dataclass
class Plant:
    """Un plant : centre (m) et feuilles ; terme central optionnel."""
    cx: float
    cy: float
    feuilles: list = field(default_factory=list)
    amplitude_centre: float = 0.3   # a_c, tache centrale (modèle A, H1)  [H]
    sigma_centre: float = 0.10      # σ_c (m)                              [H]
    rayon_coeur: float = 0.25       # r_c, rayon du centre plus clair (B)  [H]
    gain_coeur: float = 0.25        # ΔL, éclaircissement relatif (B, H5b) [H]
    cigare: bool = True             # feuille cigare au centre (B)
    petioles: bool = True           # pétioles visibles (B)
    trou_centre: float = 0.0        # rayon (m) d'un vide sombre au centre (B), [O] dji_0546


@dataclass
class ParamsA:
    """Paramètres du détecteur A (valeurs moyennes a priori, [H])."""
    longueur: float = 1.25
    largeur: float = 0.55
    r0: float = 0.25
    n_theta: int = 16
    m_top: int = 4            # nombre de directions retenues (feuilles distinctes)
    res_travail: float = 0.05  # m/px
    echelle: float = 1.0      # multiplicateur global (test d'erreur d'échelle)
    surround: float = 3.0     # σ du surround latéral = surround × σ_W
    canal: str = "exg"        # "exg" (E-002) ou "luminance" (A-L, OBJ-V5)


@dataclass
class ParamsB:
    """Paramètres du détecteur B (valeurs moyennes a priori, [H])."""
    lambda_stries: float = 0.10
    r_in: float = 0.15
    r_out: float = 1.8
    largeur: float = 0.55
    k_feuilles: int = 7
    res_vote: float = 0.10
    poids_couleur: float = 0.0  # 0 = stries seules ; > 0 ajoute H5b
    signe: float = 1.0          # +1 : stries dominantes (échelle fine), cf. P-B3
    sigma_derivee: float | None = None   # σ_g (m) ; défaut λ/4
    sigma_integration: float | None = None  # σ_t (m) ; défaut λ
    echelle: float = 1.0


# ---------------------------------------------------------------------------
# Tirage de plants (a priori [H])
# ---------------------------------------------------------------------------


def tirer_plant(rng, cx, cy, L_min=0.9, L_max=1.6, k_min=5, k_max=9):
    """Tire un plant selon les intervalles a priori [H] du modèle."""
    K = int(rng.integers(k_min, k_max + 1))
    theta0 = rng.uniform(0, 2 * math.pi)
    feuilles = []
    for k in range(K):
        L = rng.uniform(L_min, L_max)
        feuilles.append(Feuille(
            theta=theta0 + 2 * math.pi * k / K + rng.normal(0, 0.25),
            longueur=L,
            largeur=L * rng.uniform(0.33, 0.45),
            r0=rng.uniform(0.10, 0.35),
            amplitude=rng.uniform(0.7, 1.0),
            courbure=rng.uniform(-0.5, 0.5) / L,
            lambda_stries=rng.uniform(0.06, 0.15),
            angle_stries=math.radians(rng.uniform(70, 90)),
            contraste_stries=rng.uniform(0.3, 0.7),
            largeur_nervure=rng.uniform(0.02, 0.05),
            seche=(k == 0 and rng.random() < 0.3),
        ))
    return Plant(cx=cx, cy=cy, feuilles=feuilles,
                 amplitude_centre=rng.uniform(0.0, 0.5),
                 rayon_coeur=rng.uniform(0.15, 0.3),
                 gain_coeur=rng.uniform(0.1, 0.35))


# ---------------------------------------------------------------------------
# Repères locaux
# ---------------------------------------------------------------------------


def _boite(plant, res, forme, marge=0.2):
    """Fenêtre (l0, l1, c0, c1) couvrant le plant, et grilles X, Y (m)."""
    R = max(f.r0 + f.longueur for f in plant.feuilles) + marge
    H, W = forme
    c0 = max(0, int((plant.cx - R) / res)); c1 = min(W, int((plant.cx + R) / res) + 1)
    l0 = max(0, int((plant.cy - R) / res)); l1 = min(H, int((plant.cy + R) / res) + 1)
    if c1 <= c0 or l1 <= l0:
        return None
    X, Y = np.meshgrid((np.arange(c0, c1) + 0.5) * res, (np.arange(l0, l1) + 0.5) * res)
    return (l0, l1, c0, c1), X, Y


def _repere(f, X, Y, cx, cy):
    """u : coordonnée le long de θ ; t : coordonnée perpendiculaire."""
    dx, dy = X - cx, Y - cy
    c, s = math.cos(f.theta), math.sin(f.theta)
    return dx * c + dy * s, -dx * s + dy * c


# ---------------------------------------------------------------------------
# Modèle A : rendu
# ---------------------------------------------------------------------------


def feuille_A(f, X, Y, cx, cy):
    """g_k(x) = a exp(-(u-μ)²/2σ_L² - t²/2σ_W²), μ = r0 + L/2, σ_L = L/4, σ_W = W/4."""
    u, t = _repere(f, X, Y, cx, cy)
    mu, sL, sW = f.r0 + f.longueur / 2, f.longueur / 4, f.largeur / 4
    return f.amplitude * np.exp(-(u - mu) ** 2 / (2 * sL ** 2) - t ** 2 / (2 * sW ** 2))


def plant_A(plant, X, Y):
    """Indice de végétation du plant : a_c·G_iso(σ_c) + Σ_k g_k (avant écrêtage)."""
    r2 = (X - plant.cx) ** 2 + (Y - plant.cy) ** 2
    v = plant.amplitude_centre * np.exp(-r2 / (2 * plant.sigma_centre ** 2))
    for f in plant.feuilles:
        v = v + feuille_A(f, X, Y, plant.cx, plant.cy)
    return v


SOL = np.array([0.42, 0.34, 0.24])
VERT = np.array([0.20, 0.42, 0.12])
BRUN = np.array([0.48, 0.36, 0.20])
CLAIR = np.array([0.45, 0.66, 0.25])
NERVURE = np.array([0.55, 0.65, 0.35])


def rendre_scene_A(plants, forme, res, fond_img=None):
    """Carte v ∈ [0,1] (union écrêtée des plants), puis RVB = fond(1-v) + vert·v."""
    v = np.zeros(forme, np.float32)
    for p in plants:
        b = _boite(p, res, forme, marge=0.5)
        if b is None:
            continue
        (l0, l1, c0, c1), X, Y = b
        v[l0:l1, c0:c1] += plant_A(p, X, Y).astype(np.float32)
    v = np.clip(v, 0, 1)
    if fond_img is None:
        fond_img = np.broadcast_to(SOL, forme + (3,))
    return (v[..., None] * VERT + (1 - v[..., None]) * fond_img).astype(np.float32)


# ---------------------------------------------------------------------------
# Modèle B : rendu
# ---------------------------------------------------------------------------


def masque_B(f, X, Y, cx, cy, flou=0.01):
    """Limbe en bande autour d'une nervure parabolique.

    s = u - r0 (abscisse le long du limbe), v = t - κu²/2 (écart à la nervure),
    demi-largeur w(s) = W/2 · sin(πs/L)^0,4 ; masque doux de largeur `flou` (m).
    Retourne (masque, s, v).
    """
    u, t = _repere(f, X, Y, cx, cy)
    s = u - f.r0
    v = t - 0.5 * f.courbure * u ** 2
    sc = np.clip(s / f.longueur, 0, 1)
    w = 0.5 * f.largeur * np.sin(math.pi * sc) ** 0.4
    m = np.clip((w - np.abs(v)) / flou + 0.5, 0, 1)
    m *= (s >= 0) & (s <= f.longueur)
    return m, s, v


def texture_B(f, s, v, rng):
    """Stries : déchirures fines le long des nervures secondaires.

    phase = 2π (s sinβ - |v| cosβ)/λ + bruit lent ; modulation
    1 - c_s · a_j · ((1 + cos phase)/2)^6, a_j amplitude aléatoire par période.
    Plus la nervure : + δ exp(-v²/2σ_n²).
    """
    beta = f.angle_stries
    phase = 2 * math.pi * (s * math.sin(beta) - np.abs(v) * math.cos(beta)) / f.lambda_stries
    phase = phase + 0.6 * np.sin(2 * math.pi * s / max(f.longueur, 1e-3) * 1.7 + rng.uniform(0, 6.3))
    j = np.floor(phase / (2 * math.pi)).astype(np.int64)
    amp = rng.uniform(0.2, 1.0, size=4096)
    a = amp[np.mod(j, 4096)]
    mod = 1 - f.contraste_stries * a * ((1 + np.cos(phase)) / 2) ** 6
    sn = f.largeur_nervure / 2.355
    nerv = np.exp(-v ** 2 / (2 * sn ** 2))
    return mod, nerv


def rendre_scene_B(plants, forme, res, rng, fond_img=None):
    """Peint les feuilles de chaque plant (plus âgées d'abord) sur `fond_img`."""
    img = np.zeros(forme + (3,), np.float32)
    img[:] = SOL if fond_img is None else fond_img
    for p in plants:
        b = _boite(p, res, forme, marge=0.2)
        if b is None:
            continue
        (l0, l1, c0, c1), X, Y = b
        zone = img[l0:l1, c0:c1]
        r2 = (X - p.cx) ** 2 + (Y - p.cy) ** 2
        coeur = 1 + p.gain_coeur * np.exp(-r2 / (2 * p.rayon_coeur ** 2))
        # vide sombre au centre (sol, ombre), peint avant les feuilles
        if p.trou_centre > 0:
            mt = np.clip((p.trou_centre - np.sqrt(r2)) / 0.02 + 0.5, 0, 1)
            zone[:] = zone * (1 - mt[..., None]) + (0.35 * SOL) * mt[..., None]
        # pétioles : segments fins du centre à la base du limbe
        for f in (p.feuilles if p.petioles else []):
            u, t = _repere(f, X, Y, p.cx, p.cy)
            mp = np.clip((0.025 - np.abs(t)) / 0.01 + 0.5, 0, 1) * ((u >= 0) & (u <= f.r0 + 0.02))
            zone[:] = zone * (1 - mp[..., None]) + (NERVURE * 0.9) * mp[..., None]
        for f in p.feuilles:  # ordre = âge : la première est la plus vieille
            m, s, v = masque_B(f, X, Y, p.cx, p.cy, flou=max(0.01, res))
            if not m.any():
                continue
            mod, nerv = texture_B(f, s, v, rng)
            base = BRUN if f.seche else VERT * rng.uniform(0.85, 1.15)
            col = base[None, None, :] * (mod * coeur)[..., None]
            col = col * (1 - 0.6 * nerv[..., None]) + NERVURE * (0.6 * nerv[..., None])
            zone[:] = zone * (1 - m[..., None]) + col * m[..., None]
        if p.cigare:
            mc = np.clip((0.08 - np.sqrt(r2)) / 0.01 + 0.5, 0, 1)
            zone[:] = zone * (1 - mc[..., None]) + CLAIR * mc[..., None]
    return img


# ---------------------------------------------------------------------------
# Scène : fond, bruit
# ---------------------------------------------------------------------------


def fond(forme, res, rng, herbe=True):
    """Sol à texture lente et touffes d'herbe isotropes (sans stries)."""
    H, W = forme
    lent = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), 1.0 / res)
    lent /= lent.std() + 1e-9
    out = np.broadcast_to(SOL, (H, W, 3)) * (1 + 0.10 * lent[..., None])
    if herbe:
        h = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), 0.3 / res)
        h = (h > np.quantile(h, 0.85)).astype(np.float32)
        fin = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), max(0.5, 0.01 / res))
        fin /= fin.std() + 1e-9
        herbe_col = np.array([0.30, 0.45, 0.20]) * (1 + 0.15 * fin[..., None])
        hm = h[..., None] * 0.8
        out = out * (1 - hm) + herbe_col * hm
    return out.astype(np.float32)


def bruit(img, rng, sigma_bruit=0.04):
    """Gain global tiré dans [0,8 ; 1,2] puis bruit gaussien par canal."""
    out = img * rng.uniform(0.8, 1.2)
    out = out + rng.normal(0, sigma_bruit, out.shape).astype(np.float32)
    return np.clip(out, 0, 1).astype(np.float32)


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------


def exg_norm(img):
    """Indice de végétation ExG normalisé (2G - R - B)/(R + G + B)."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (2 * g - r - b) / (r + g + b + 1e-6)


def reechantillonner(a, res, res_cible):
    """Moyenne par zone (INTER_AREA) si res_cible > res, sinon inchangé."""
    if res_cible <= res * 1.0001:
        return a, res
    f = res / res_cible
    H, W = a.shape[:2]
    nh, nw = max(1, int(round(H * f))), max(1, int(round(W * f)))
    out = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_AREA)
    return out, res * H / nh


def _correler(a, k):
    """Corrélation (même taille, ancre au centre du noyau, bord réfléchi)."""
    return cv2.filter2D(a.astype(np.float32), cv2.CV_32F, k.astype(np.float32),
                        borderType=cv2.BORDER_REFLECT)


def pics(score, res, rayon_nms=0.8, tau=0.25):
    """Maxima locaux (rayon `rayon_nms` m) de score ≥ τ × max. Retourne (N, 2) en m (x, y)."""
    r = max(1, int(round(rayon_nms / res)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disque = (xx ** 2 + yy ** 2) <= r * r
    mx = ndimage.maximum_filter(score, footprint=disque, mode="nearest")
    smax = float(score.max())
    ok = (score >= mx) & (score > 0)
    if np.isfinite(tau):  # tau = -inf : aucun seuil (lecture au budget)
        ok &= score >= tau * smax
    l, c = np.nonzero(ok)
    pts = np.stack([(c + 0.5) * res, (l + 0.5) * res], 1) if len(l) else np.zeros((0, 2))
    # dédoublonnage des plateaux
    garde = []
    for i in np.argsort(-score[l, c]):
        if all(np.hypot(*(pts[i] - pts[j])) > rayon_nms for j in garde):
            garde.append(i)
    return pts[garde], score[l, c][garde]


def pics_mad(score, res, rayon_nms=0.8, z0=3.0):
    """Règle A′ : maxima locaux de z = (S - médiane(S)) / (1,4826 MAD(S)) ≥ z0.

    Médiane et MAD sur toute la carte de score de l'image. Indépendant du plus
    fort pic de l'image (contrairement à τ × max) et du gain photométrique.
    """
    med = float(np.median(score))
    mad = float(np.median(np.abs(score - med))) * 1.4826 + 1e-12
    z = (score - med) / mad
    pts, sc = pics(z, res, rayon_nms, tau=0.0)
    garde = sc >= z0
    return pts[garde], sc[garde]


def pics_budget(score, res, n, rayon_nms=0.8):
    """Les n plus forts maxima locaux (lecture « au budget », OBJ-C8)."""
    pts, sc = pics(score, res, rayon_nms, tau=-np.inf)
    return pts[:n], sc[:n]


def apparier(pred, vrai, seuil=0.5):
    """Appariement glouton par distance croissante. Retourne (tp, fp, fn, erreurs)."""
    if len(pred) == 0 or len(vrai) == 0:
        return 0, len(pred), len(vrai), np.zeros(0)
    d = np.hypot(pred[:, None, 0] - vrai[None, :, 0], pred[:, None, 1] - vrai[None, :, 1])
    paires = sorted(((d[i, j], i, j) for i in range(len(pred)) for j in range(len(vrai))
                     if d[i, j] <= seuil))
    up, uv, err = set(), set(), []
    for dd, i, j in paires:
        if i not in up and j not in uv:
            up.add(i); uv.add(j); err.append(dd)
    tp = len(err)
    return tp, len(pred) - tp, len(vrai) - tp, np.array(err)


# ---------------------------------------------------------------------------
# Modèle A : filtre (vraisemblance gaussienne profilée)
# ---------------------------------------------------------------------------


def gabarit_A(theta, p: ParamsA, res):
    """h_θ(d) = G(d; μe_θ, σ_L, σ_W) - G(d; μe_θ, σ_L, s·σ_W), chaque terme de somme 1.

    Gaussienne anisotrope ancrée au centre (décalée de μ le long de θ), moins un
    surround latéral : somme nulle, donc réponse nulle sur une végétation uniforme.
    """
    e = p.echelle
    L, W, r0 = p.longueur * e, p.largeur * e, p.r0 * e
    mu, sL, sW = r0 + L / 2, L / 4, W / 4
    R = mu + 2.5 * sL
    n = int(math.ceil(R / res))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1].astype(np.float64) * res
    c, s = math.cos(theta), math.sin(theta)
    u, t = xx * c + yy * s, -xx * s + yy * c
    g1 = np.exp(-(u - mu) ** 2 / (2 * sL ** 2) - t ** 2 / (2 * sW ** 2))
    g2 = np.exp(-(u - mu) ** 2 / (2 * sL ** 2) - t ** 2 / (2 * (p.surround * sW) ** 2))
    h = g1 / g1.sum() - g2 / g2.sum()
    return h / np.sqrt((h ** 2).sum())


def canal_A(img, canal="exg"):
    """Image d'entrée du modèle A : ExG normalisé (chromatique) ou luminance (moyenne RVB)."""
    if canal == "exg":
        return exg_norm(img).astype(np.float32)
    if canal == "luminance":
        return img.mean(-1).astype(np.float32)
    raise ValueError(canal)


def gabarit_A_iso(p: ParamsA, res):
    """Témoin A-iso (OBJ-C2) : moyenne de h_θ sur θ, soit un anneau radial à somme nulle.

    Même profil le long du rayon que A, aucune anisotropie : ce qu'il reste de A
    si les feuilles ne comptent que comme une tache (H1).
    """
    thetas = 2 * math.pi * np.arange(p.n_theta) / p.n_theta
    h = np.mean([gabarit_A(th, p, res) for th in thetas], axis=0)
    h = h - h.mean()
    return h / np.sqrt((h ** 2).sum())


def filtre_A_iso(img, res, p: ParamsA = ParamsA()):
    """Score du témoin A-iso : [<v, h_iso(· - c)>]_+ . Retourne (score, res_score)."""
    v, rt = reechantillonner(canal_A(img, p.canal), res, p.res_travail)
    return np.maximum(_correler(v, gabarit_A_iso(p, rt)), 0), rt


def reponses_A(img, res, p: ParamsA = ParamsA()):
    """R_θ(c) = <v, h_θ(· - c)> pour N_θ directions. Retourne (R, res_travail)."""
    v = canal_A(img, p.canal)
    v, rt = reechantillonner(v, res, p.res_travail)
    thetas = 2 * math.pi * np.arange(p.n_theta) / p.n_theta
    R = np.stack([_correler(v, gabarit_A(th, p, rt)) for th in thetas])
    return R, rt


def score_etoile(R, m_top):
    """S_A(c) = sqrt( moyenne des m plus grandes [R_θ(c)]_+², maxima locaux en θ seuls ).

    Profilage de la vraisemblance gaussienne : pour des feuilles disjointes,
    max_{a_k} -||v - Σ a_k g_k||² = Σ_k <v, g_k>²/||g_k||² ; on garde les
    m directions localement maximales (feuilles distinctes).
    """
    Rp = np.maximum(R, 0)
    loc = (Rp >= np.roll(Rp, 1, 0)) & (Rp >= np.roll(Rp, -1, 0))
    Q = np.where(loc, Rp, 0.0) ** 2
    Q = -np.sort(-Q, axis=0)[:m_top]
    return np.sqrt(Q.mean(0))


def filtre_A(img, res, p: ParamsA = ParamsA()):
    """Carte de score du centre selon le modèle A. Retourne (score, res_score)."""
    R, rt = reponses_A(img, res, p)
    return score_etoile(R, p.m_top), rt


# ---------------------------------------------------------------------------
# Modèle A″ : A′ + polarité (cycle 2, docs/recherche/modele_feuille.md § 9)
# ---------------------------------------------------------------------------


def anisotropie_angulaire(R):
    """a₂(c) = |Σ_θ [R_θ]_+ e^{2iθ}| / (Σ_θ [R_θ]_+ + ε) ∈ [0, 1].

    Petit pour une étoile (K ≥ 3 directions réparties), proche de 1 pour un
    dipôle (deux réponses opposées : milieu entre deux voisins).
    R : (N_θ, H, W), directions θ_k = 2πk/N_θ.
    """
    n = R.shape[0]
    th = 2 * math.pi * np.arange(n) / n
    Rp = np.maximum(R, 0)
    re = np.tensordot(np.cos(2 * th), Rp, axes=1)
    im = np.tensordot(np.sin(2 * th), Rp, axes=1)
    return np.hypot(re, im) / (Rp.sum(0) + 1e-9)


def terme_trou(Y, res, sigma_point=0.15, sigma_voisinage=0.6):
    """H(c) = G_0,6m * Y - G_0,15m * Y : positif si le point est plus sombre que son voisinage."""
    Y = Y.astype(np.float32)
    return (ndimage.gaussian_filter(Y, sigma_voisinage / res)
            - ndimage.gaussian_filter(Y, sigma_point / res))


def zrob_valide(S, valide=None):
    """Normalisation robuste (médiane, 1,4826 MAD) sur les pixels valides ; repli sur l'écart-type."""
    x = S[valide] if valide is not None else S.ravel()
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med))) * 1.4826
    if mad <= 1e-12:
        mad = float(x.std()) + 1e-12
    return (S - med) / mad


def score_A2(S_A, a2, H, beta=0.0, w_trou=0.0, z_vote=None, w_vote=0.0, valide=None):
    """z″ = zrob(S_A (1 - β a₂)) + w_trou zrob(H) + w_vote z_vote.

    z_vote : point d'entrée de la preuve externe (vote des axes linéaires B′,
    comptage_math/votes.py de convergence-engineer), déjà normalisée, même
    grille que S_A. w_vote = 0 au cycle 2.
    """
    z = zrob_valide(S_A * (1 - beta * a2), valide)
    if w_trou:
        z = z + w_trou * zrob_valide(H, valide)
    if w_vote and z_vote is not None:
        z = z + w_vote * z_vote
    return z


# ---------------------------------------------------------------------------
# Modèle B : filtre (vraisemblance von Mises du champ d'orientation + couleur)
# ---------------------------------------------------------------------------


def champ_orientation(img, res, p: ParamsB = ParamsB()):
    """Champ d'orientation en angle doublé z = <(g_x + i g_y)²>_σt / <|g|²>_σt.

    σ_g = λ/4 (dérivée), σ_t = λ (intégration). arg z = 2 × direction du
    gradient dominant ; |z| = cohérence ∈ [0, 1]. Pour des stries
    perpendiculaires à la nervure, le gradient dominant est parallèle à la
    nervure, donc radial. Pondéré par un masque de végétation (ExG lissé > 0,05).
    Retourne (z complexe, sigma_g en px).
    """
    lam = p.lambda_stries * p.echelle
    sg = (p.sigma_derivee if p.sigma_derivee is not None else lam / 4) / res
    st = (p.sigma_integration if p.sigma_integration is not None else lam) / res
    sg_eff = max(sg, 0.7)
    st = max(st, 1.5)
    Y = img.mean(-1).astype(np.float32)
    gx = ndimage.gaussian_filter(Y, sg_eff, order=(0, 1))
    gy = ndimage.gaussian_filter(Y, sg_eff, order=(1, 0))
    jxx = ndimage.gaussian_filter(gx * gx, st)
    jyy = ndimage.gaussian_filter(gy * gy, st)
    jxy = ndimage.gaussian_filter(gx * gy, st)
    z = ((jxx - jyy) + 2j * jxy) / (jxx + jyy + 1e-8)
    veg = ndimage.gaussian_filter(exg_norm(img).astype(np.float32), st)
    w = np.clip((veg - 0.05) / 0.10, 0, 1)
    return (z * w).astype(np.complex64), sg


def noyau_B(p: ParamsB, res):
    """k(d) = ρ(|d|) e^{-2i arg d}, ρ(r) = min(1, K W / (2π r)) sur [r_in, r_out].

    ρ ∝ 1/r : fraction d'un cercle de rayon r couverte par K limbes de largeur W.
    """
    e = p.echelle
    rin, rout, W = p.r_in * e, p.r_out * e, p.largeur * e
    n = int(math.ceil(rout / res))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1].astype(np.float64) * res
    r = np.hypot(xx, yy)
    rho = np.minimum(1.0, p.k_feuilles * W / (2 * math.pi * np.maximum(r, 1e-6)))
    rho *= np.clip((r - rin) / (0.5 * rin + 1e-9), 0, 1) * np.clip((rout - r) / (0.2 * rout), 0, 1)
    ang = np.arctan2(yy, xx)
    return rho * np.cos(2 * ang), -rho * np.sin(2 * ang)


def score_orientation_B(z, res, p: ParamsB = ParamsB()):
    """Λ(c) = Re Σ_i z_i k(x_i - c) : log-vraisemblance (développement à faible κ).

    p(φ_i | c) = π_i(c) VM₂(φ_i; ψ_i(c), κ) + (1 - π_i(c))/π, ψ_i(c) = arg(x_i - c) ;
    log p/p₀ ≈ π_i(c) κ cos 2(φ_i - ψ_i) = κ Re[z_i ρ e^{-2iψ_i}].
    Retourne (Λ, res_vote).
    """
    zr, rv = reechantillonner(np.ascontiguousarray(z.real), res, p.res_vote)
    zi, _ = reechantillonner(np.ascontiguousarray(z.imag), res, p.res_vote)
    kr, ki = noyau_B(p, rv)
    # k(-d) = k(d) : corrélation = convolution
    lam = _correler(zr, kr) - _correler(zi, ki)
    return p.signe * lam, rv


def score_couleur_B(img, res, p: ParamsB, res_cible):
    """Terme H5b : clarté relative du centre, DoG radiale (r_c, 3 r_c) sur la végétation."""
    Y = img.mean(-1).astype(np.float32)
    Y, rt = reechantillonner(Y, res, res_cible)
    rc = 0.2 * p.echelle / rt
    return ndimage.gaussian_filter(Y, rc) - ndimage.gaussian_filter(Y, 3 * rc), rt


def _norm_robuste(a):
    med = np.median(a)
    mad = np.median(np.abs(a - med)) * 1.4826 + 1e-9
    return (a - med) / mad


def filtre_B(img, res, p: ParamsB = ParamsB(), melanger=None):
    """Carte de score du centre selon le modèle B. Retourne (score, res_score).

    `melanger` : générateur aléatoire ; si fourni, les orientations sont
    permutées entre pixels de végétation (contrôle « orientations mélangées »).
    """
    z, _ = champ_orientation(img, res, p)
    if melanger is not None:
        idx = np.flatnonzero(np.abs(z) > 0)
        ph = np.angle(z.flat[idx])
        z.flat[idx] = np.abs(z.flat[idx]) * np.exp(1j * melanger.permutation(ph))
    lam, rv = score_orientation_B(z, res, p)
    s = _norm_robuste(lam)
    if p.poids_couleur > 0:
        c, _ = score_couleur_B(img, res, p, rv)
        c = cv2.resize(c, (s.shape[1], s.shape[0]), interpolation=cv2.INTER_LINEAR)
        s = s + p.poids_couleur * _norm_robuste(c)
    return s, rv



# ---------------------------------------------------------------------------
# Modèle F : feuille entière détectée comme objet, un vecteur par feuille (C-003, E-018)
# ---------------------------------------------------------------------------
# Formulation compatible avec les indices « forme », « gaussiennes », « orientation »
# et « vecteurs posés sur les feuilles vers les centres » (discussion avec Baptiste,
# D-011). Ce n'est pas une reconstitution. Équations : `modele_feuille.md` § 10.


@dataclass
class ParamsF:
    longueurs: tuple = (0.8, 1.2, 1.8)   # L testées (m)                         [H]
    rapport_largeur: float = 0.4         # W = ω L                               [H] 0,33–0,45
    n_theta: int = 12                    # orientations sur [0, π)
    sigma_contraste: float = 1.0         # σ_b (m), normalisation locale du contraste
    z_feuille: float = 1.5               # seuil z d'une feuille
    rayon_pic_feuille: float = 0.15      # maxima locaux de R* (m)
    r0: float = 0.25                     # distance centre → base du limbe (m)  [H]
    d_fixe: float | None = None          # si donné : distance de vote fixe (témoin d'échelle)
    sigma_vote_min: float = 0.15         # σ_v = max(σ_min, η d)
    eta_vote: float = 0.25
    polarite: bool = False               # vote pondéré par l'effilement (gabarit impair)
    tau_effile: float = 0.4              # effilement du gabarit impair
    beta_polarite: float = 0.5           # π = tanh(β · P_z)
    contraste: str = "abs"               # "clair" : limbe plus clair que son entourage (E-018s, 1er essai, échec) ;
                                         # "abs" : limbe clair OU sombre, R = max |h ⋆ Ŷ| (E-018s, 2e essai)


def contraste_local(Y, valide, res, sigma_b=1.0):
    """Ŷ = (Y − G_σb ∗ Y) / √(G_σb ∗ (Y − G_σb ∗ Y)² + ε), calculé sur les pixels valides."""
    s = sigma_b / res
    m = valide.astype(np.float32)
    Yv = np.where(valide, Y, 0).astype(np.float32)
    nm = ndimage.gaussian_filter(m, s) + 1e-6
    mu = ndimage.gaussian_filter(Yv, s) / nm
    d = np.where(valide, Y - mu, 0).astype(np.float32)
    var = ndimage.gaussian_filter(d * d, s) / nm
    return (d / np.sqrt(var + 1e-4)).astype(np.float32)


def _profil_t(t, st):
    """Profil transverse à somme nulle : G(t; σ_t) − ⅓ G(t; 3σ_t) (non normalisées)."""
    return np.exp(-t ** 2 / (2 * st ** 2)) - np.exp(-t ** 2 / (2 * (3 * st) ** 2)) / 3.0


def _grille_tournee(R, res, theta):
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1] * res
    c, s_ = math.cos(theta), math.sin(theta)
    return xx * c + yy * s_, -xx * s_ + yy * c


def gabarit_feuille(L, theta, res, omega=0.4):
    """Gabarit pair d'une feuille entière centrée à l'origine, axe θ :
    h(s, t) = exp(−s²/2σ_s²) · [G(t; σ_t) − ⅓ G(t; 3σ_t)], σ_s = L/4, σ_t = W/4, W = ωL ; ‖h‖₂ = 1."""
    ss, st = L / 4, omega * L / 4
    R = int(math.ceil(max(3 * ss, 9 * st) / res))
    s, t = _grille_tournee(R, res, theta)
    h = np.exp(-s ** 2 / (2 * ss ** 2)) * _profil_t(t, st)
    h -= h.mean()
    return (h / (np.linalg.norm(h) + 1e-12)).astype(np.float32)


def gabarit_effile_impair(L, theta, res, omega=0.4, tau=0.4):
    """Gabarit impair : limbe plus large vers +u(θ) (pointe) que vers −u(θ) (base),
    σ_t(s) = σ_t (1 + τ s/(L/2)), moins son image par s → −s. Réponse > 0 : la base
    (donc le centre) est du côté −u(θ)."""
    ss, st = L / 4, omega * L / 4
    R = int(math.ceil(max(3 * ss, 9 * st * (1 + tau)) / res))
    s, t = _grille_tournee(R, res, theta)
    e = np.exp(-s ** 2 / (2 * ss ** 2))
    sp = st * np.clip(1 + tau * s / (L / 2), 0.3, None)
    sm = st * np.clip(1 - tau * s / (L / 2), 0.3, None)
    h = e * (_profil_t(t, sp) - _profil_t(t, sm))
    h -= h.mean()
    return (h / (np.linalg.norm(h) + 1e-12)).astype(np.float32)


def _fft_corr(Yf, forme, forme_p, k):
    """Corrélation par FFT (hors image : Ŷ = 0)."""
    from scipy import fft as sfft
    H, W = forme
    Hp, Wp = forme_p
    kh, kw = k.shape
    K = np.zeros((Hp, Wp), np.float32)
    K[:kh, :kw] = k[::-1, ::-1]
    K = np.roll(K, (-(kh // 2), -(kw // 2)), (0, 1))
    out = sfft.irfft2(Yf * sfft.rfft2(K), s=(Hp, Wp))
    return out[:H, :W].astype(np.float32)


def reponses_feuilles(Yc, res, p: ParamsF = ParamsF()):
    """R*(x) = max_{L,θ} (h_{L,θ} ⋆ Ŷ)(x), avec les indices de L* et θ*, et la réponse impaire P à (L*, θ*)."""
    from scipy import fft as sfft
    H, W = Yc.shape
    Lm = max(p.longueurs)
    marge = int(math.ceil(max(3 * Lm / 4, 9 * p.rapport_largeur * Lm / 4 * (1 + p.tau_effile)) / res)) + 1
    Hp, Wp = sfft.next_fast_len(H + marge, True), sfft.next_fast_len(W + marge, True)
    Yp = np.zeros((Hp, Wp), np.float32)
    Yp[:H, :W] = Yc
    Yf = sfft.rfft2(Yp)
    Rmax = np.full((H, W), -np.inf, np.float32)
    iL = np.zeros((H, W), np.int16)
    iT = np.zeros((H, W), np.int16)
    Pm = np.zeros((H, W), np.float32)
    for a, L in enumerate(p.longueurs):
        for b in range(p.n_theta):
            th = math.pi * b / p.n_theta
            r = _fft_corr(Yf, (H, W), (Hp, Wp), gabarit_feuille(L, th, res, p.rapport_largeur))
            sgn = np.sign(r) if p.contraste == "abs" else 1.0
            if p.contraste == "abs":
                r = np.abs(r)
            mieux = r > Rmax
            Rmax[mieux] = r[mieux]
            iL[mieux] = a
            iT[mieux] = b
            if p.polarite:
                q = _fft_corr(Yf, (H, W), (Hp, Wp), gabarit_effile_impair(L, th, res, p.rapport_largeur, p.tau_effile))
                Pm[mieux] = (q * sgn)[mieux]   # limbe sombre : l'effilement s'inverse en signe
    return Rmax, iL, iT, Pm


def detecter_feuilles(rgb, res, valide, vegetation, p: ParamsF = ParamsF()):
    """Feuilles = maxima locaux de z(R*) ≥ z_f dans la végétation, puis suppression
    anisotrope : une feuille acceptée supprime les candidats dans son ellipse (|s| < L/2, |t| < W/2).
    rgb : float 0–255 (H, W, 3). Retourne dict(x, y (px), theta, L, z, pol) triés par z décroissant."""
    from scipy.spatial import cKDTree
    vide = dict(x=np.zeros(0), y=np.zeros(0), theta=np.zeros(0), L=np.zeros(0), z=np.zeros(0), pol=np.zeros(0))
    if valide.sum() < 100:
        return vide
    Y = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
    Yc = contraste_local(Y, valide, res, p.sigma_contraste)
    Rmax, iL, iT, Pm = reponses_feuilles(Yc, res, p)
    x = Rmax[valide]
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med))) * 1.4826 + 1e-9
    Z = (Rmax - med) / mad
    r = max(1, int(round(p.rayon_pic_feuille / res)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disque = ((xx ** 2 + yy ** 2) <= r * r).astype(np.uint8)
    mx = cv2.dilate(Z.astype(np.float32), disque)
    ok = (Z >= mx) & (Z >= p.z_feuille) & valide & vegetation
    l, c = np.nonzero(ok)
    if not len(l):
        return vide
    o = np.argsort(-Z[l, c], kind="stable")
    l, c = l[o], c[o]
    Ls = np.asarray(p.longueurs, float)[iL[l, c]]
    th = math.pi * iT[l, c].astype(float) / p.n_theta
    if p.polarite:
        pv = Pm[valide]
        madp = float(np.median(np.abs(pv - np.median(pv)))) * 1.4826 + 1e-9
        pol = np.tanh(p.beta_polarite * Pm[l, c] / madp)
    else:
        pol = np.zeros(len(l))
    pts = np.c_[c + 0.5, l + 0.5]
    arbre = cKDTree(pts)
    pris = np.zeros(len(l), bool)
    garde = []
    for i in range(len(l)):
        if pris[i]:
            continue
        garde.append(i)
        js = np.array(arbre.query_ball_point(pts[i], Ls[i] / 2 / res), int)
        if len(js):
            d = (pts[js] - pts[i]) * res
            s = d[:, 0] * math.cos(th[i]) + d[:, 1] * math.sin(th[i])
            t = -d[:, 0] * math.sin(th[i]) + d[:, 1] * math.cos(th[i])
            pris[js[(np.abs(s) < Ls[i] / 2) & (np.abs(t) < p.rapport_largeur * Ls[i] / 2)]] = True
    g = np.array(garde, int)
    return dict(x=pts[g, 0], y=pts[g, 1], theta=th[g], L=Ls[g], z=Z[l, c][g], pol=pol[g])


def carte_votes_feuilles(fe, forme, res, p: ParamsF = ParamsF(), melanger=None):
    """V(c) = Σ_k Σ_± q_k^± · exp(−|c − (p_k ∓ d_k u_k)|² / 2σ_k²), une voix par feuille.

    d_k = r0 + L_k/2 (ou d_fixe), σ_k = max(σ_min, η d_k), u_k = (cos θ_k, sin θ_k).
    Sans polarité : q± = ½. Avec : le centre est du côté −u si pol > 0, q⁻ = (1 + pol)/2, q⁺ = (1 − pol)/2.
    V se lit en « nombre de feuilles qui désignent c ». melanger : générateur ; permute θ (et pol) entre feuilles."""
    H, W = forme
    V = np.zeros(forme, np.float32)
    n = len(fe["x"])
    if n == 0:
        return V
    th, pol = fe["theta"], fe["pol"]
    if melanger is not None:
        perm = melanger.permutation(n)
        th, pol = th[perm], pol[perm]
    d = np.full(n, float(p.d_fixe)) if p.d_fixe is not None else p.r0 + fe["L"] / 2
    sig = np.maximum(p.sigma_vote_min, p.eta_vote * d)
    qm = (1 + pol) / 2 if p.polarite else np.full(n, 0.5)
    ux, uy = np.cos(th), np.sin(th)
    for sv in np.unique(np.round(sig, 4)):
        sel = np.abs(sig - sv) < 1e-4
        acc = np.zeros(forme, np.float32)
        for sgn, q in ((-1, qm[sel]), (+1, 1 - qm[sel])):
            vx = fe["x"][sel] + sgn * d[sel] * ux[sel] / res
            vy = fe["y"][sel] + sgn * d[sel] * uy[sel] / res
            ix, iy = np.floor(vx).astype(int), np.floor(vy).astype(int)
            ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
            np.add.at(acc, (iy[ok], ix[ok]), q[ok].astype(np.float32))
        s_px = sv / res
        V += ndimage.gaussian_filter(acc, s_px) * np.float32(2 * math.pi * s_px ** 2)
    return V
