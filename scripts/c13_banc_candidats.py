#!/usr/bin/env python3
"""Candidats sans entraînement de la nuit du 13/11 (agent C-banc). Fabriques Contexte -> (points xy à 5 cm, scores).

Reprend les fabriques du banc v6 (scripts/v6_banc_candidats.py, importé sans modification) et ajoute :
  CB1 aiguillage_v2 : aiguillage p90 d'E5p90b avec seuil propre à la branche « petits » et conditions d'aiguillage
      supplémentaires (nombre de pics, régularité de l'espacement, part de végétation), accord des membres et
      filtre de végétation dans la branche « petits » ;
  CB2 resolution : candidats qui lisent une carte d'image dégradée (variante d8 / d11...) et un seuil fonction
      de la résolution d'origine (connue par le GeoTIFF dans la chaîne) ;
  CB3 trous : seconde passe à seuil bas, seulement aux places qu'annonce la géométrie de plantation.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_banc_commun as cc  # noqa: E402
import v6_banc_candidats as ca  # noqa: E402

bc = cc.bc


# ------------------------------------------------------------------------------------------------ outils
_VERT = {}


def part_verte(ctx):
    """Part de végétation verte de l'image (cache de c13_banc_vert.py, calculé sur l'image d'origine à 5 cm ; pour une
    image dégradée, la même valeur est reprise : la couleur moyenne change peu). Contexte sans cache : calcul direct."""
    if hasattr(ctx, "img"):
        import c13_banc_vert as cv
        return cv.part_verte(ctx.img)
    if not _VERT:
        import json
        _VERT.update(json.loads((cc.CACHE / "vert.json").read_text(encoding="utf-8")))
    return _VERT[ctx.nom_jeu][ctx.nom]


def _signal_p90(carte, smin=0.15, q=0.90, k=bc.K_PICS):
    _, sc = bc.pics(carte, k, smin)
    return (float(np.quantile(sc, q)) if len(sc) else np.nan), len(sc)


def _regularite(xy):
    """Coefficient de variation de la distance au plus proche voisin (petit = plantation régulière)."""
    if len(xy) < 6:
        return np.nan
    d, _ = cKDTree(xy).query(xy, k=2)
    d = d[:, 1]
    return float(np.std(d) / max(np.mean(d), 1e-6))


def _carte_melange(ctx, membres, mode="moyenne", variante="base"):
    cs = [ctx.carte(m, variante).astype("float64") for m in membres]
    if mode == "moyenne":
        return np.mean(cs, 0)
    if mode == "minimum":
        return np.min(cs, 0)
    if mode == "geometrique":
        return np.exp(np.mean([np.log(np.maximum(c, 1e-6)) for c in cs], 0))
    raise KeyError(mode)


def _valeur(carte, xy, rayon_cell=1):
    """Maximum de la carte dans un carré (2 r + 1) autour de chaque point (grille au quart)."""
    if not len(xy):
        return np.zeros(0)
    j = np.clip((xy[:, 1] / bc.STRIDE).astype(int), 0, carte.shape[0] - 1)
    i = np.clip((xy[:, 0] / bc.STRIDE).astype(int), 0, carte.shape[1] - 1)
    if rayon_cell == 0:
        return carte[j, i]
    from scipy.ndimage import maximum_filter
    m = maximum_filter(carte, size=2 * rayon_cell + 1, mode="constant")
    return m[j, i]


def promouvoir(A, P, mode="milieu", tol_d=0.30, tol_angle=25.0, min_ancres=6):
    """CB3 (géométrie de plantation) : masque des pics bas P (n x 2) à promouvoir, d'après les ancres A.
    Même règle que f_trous : P à plus de 0,5 d de toute ancre ; « milieu » : deux ancres à d (± tol_d) dans des
    directions opposées (180° ± tol_angle) ; « reseau » : place vide prédite par les deux vecteurs dominants ; « les_deux »."""
    promu = np.zeros(len(P), bool)
    if len(A) < min_ancres or not len(P):
        return promu
    ta = cKDTree(A)
    dd, ii = ta.query(A, k=2)
    d = float(np.median(dd[:, 1]))
    if not np.isfinite(d) or d <= 0:
        return promu
    dmin, _ = ta.query(P, k=1)
    loin = dmin > 0.5 * d
    if mode in ("milieu", "les_deux"):
        cmax = np.cos(np.radians(180 - tol_angle))
        for n, vs in enumerate(ta.query_ball_point(P, (1 + tol_d) * d)):
            if not loin[n] or len(vs) < 2:
                continue
            v = A[vs] - P[n]
            r = np.linalg.norm(v, axis=1)
            ok = r >= (1 - tol_d) * d
            v, r = v[ok], r[ok]
            if len(v) >= 2:
                u = v / r[:, None]
                if ((u @ u.T) <= cmax).any():
                    promu[n] = True
    if mode in ("reseau", "les_deux"):
        vec = A[ii[:, 1]] - A
        vec[vec[:, 0] < 0] *= -1
        ang = np.degrees(np.arctan2(vec[:, 1], vec[:, 0])) % 180
        h, _ = np.histogram(ang, bins=18, range=(0, 180))
        dirs = []
        for b in np.argsort(-h)[:4]:
            m = (ang >= 10 * b) & (ang < 10 * b + 10)
            if m.sum() >= 3:
                v = np.median(vec[m], 0)
                if all(abs(np.degrees(np.arctan2(v[1], v[0]) - np.arctan2(w[1], w[0]))) % 180 > 30 for w in dirs):
                    dirs.append(v)
            if len(dirs) == 2:
                break
        if dirs:
            preds = np.concatenate([A + s_ * v for v in dirs for s_ in (1, -1)])
            dp, _ = ta.query(preds, k=1)
            preds = preds[dp > 0.5 * d]
            if len(preds):
                dq, _ = cKDTree(preds).query(P, k=1)
                promu |= loin & (dq <= tol_d * d)
    return promu


# ------------------------------------------------------------------------------------------------ CB1
def f_aiguillage_v2(tau=0.55, smin=0.15, n_min=1, decalage=0.10, seuil_petit=None, petits=("v3", "v4"), mode_petit="moyenne",
                    grand="v5", variante="base", accord_v5=None, n_min_petit=0, reg_max=None, veg_min=None, veg_point=None,
                    ratio_max=None, dens_min=None, esp_max=None, ratio_min=None, compte_30=False, trous=None, vert_max=None, k=bc.K_PICS):
    """Aiguillage par image (CB1).
    Signal : 90e centile des scores des pics du v5 (>= smin) sous tau, avec au moins n_min pics, et en option :
      - n_min_petit : au moins ce nombre de pics dans la carte « petits » au seuil de la branche ;
      - reg_max : régularité (CV de la distance au plus proche voisin des pics « petits ») au plus reg_max ;
      - veg_min : part de végétation de l'image (indice ExG, carte « img/veg ») au moins veg_min ;
      - ratio_max : (pics « petits ») / (pics v5 à 0,30 + 1) au plus ratio_max (évite d'aiguiller une image où le v5 voit déjà tout) ;
      - dens_min : densité des pics du v5 (>= smin) d'au moins dens_min par hectare, et au moins 5 pics (une plantation de
        petits plants porte beaucoup de pics faibles ; une tuile sans bananier n'en porte que quelques-uns) ;
      - ratio_min : (pics « petits ») / (pics v5 à 0,30 + 1) au moins ratio_min (le v5 ne voit qu'une petite part de ce
        que voit la branche « petits » : signe de petits plants qu'il manque) ;
      - esp_max : espacement médian au plus proche voisin de ces pics d'au plus esp_max pixels à 5 cm.
    Branche « petits » : carte mélange des `petits` (moyenne, minimum ou géométrique) ;
      seuil_petit = None : score + decalage comparé au seuil de la grille (comme E5p90b) ;
      seuil_petit = s : seuil propre fixe (points gardés quel que soit le seuil de la grille) ;
      accord_v5 = a : un point « petits » n'est gardé que si la carte du v5 vaut au moins a dans un carré 3 x 3 ;
      veg_point = v : seulement si la part de végétation locale (carte veg) vaut au moins v.
    Sinon : v5 seul (score tel quel)."""
    def branche_petits(ctx):
        c = _carte_melange(ctx, petits, mode_petit, variante)
        plancher = (seuil_petit if seuil_petit is not None else bc.SEUILS[0] - decalage)
        xy, sc = bc.pics(c.astype("float32"), k, plancher)
        g = np.ones(len(xy), bool)
        if accord_v5 is not None and len(xy):
            g &= _valeur(ctx.carte(grand, variante), xy, 1) >= accord_v5
        if veg_point is not None and len(xy):
            g &= _valeur(ctx.carte("img", "veg"), xy, 0) >= veg_point
        xy, sc = xy[g], sc[g]
        sc = np.ones_like(sc) if seuil_petit is not None else sc + decalage
        if trous is not None and len(xy):
            # CB3 dans la branche « petits » : ancres = score rendu >= 0,30 ; pics bas = score rendu dans [trous["bas"], 0,30) ;
            # un pic bas promu (score 0,30) s'il bouche un trou de la géométrie de plantation (fonction promouvoir)
            a = sc >= 0.30
            b = (~a) & (sc >= trous["bas"])
            pm = promouvoir(xy[a], xy[b], trous.get("mode", "milieu"), trous.get("tol_d", 0.30), trous.get("tol_angle", 25.0))
            idx = np.nonzero(b)[0][pm]
            sc = sc.copy(); sc[idx] = 0.30
        return xy, sc

    def f(ctx):
        cg = ctx.carte(grand, variante)
        p90, n = _signal_p90(cg, smin, 0.90, k)
        vers = n >= max(n_min, 1) and p90 < tau
        if vers and vert_max is not None:
            # « jeune plantation sur sol nu » : part de pixels verts (ExG > 0,10, c13_banc_vert.py) au plus vert_max
            vers = part_verte(ctx) <= vert_max
        if vers and (dens_min is not None or esp_max is not None):
            xy5, _ = bc.pics(cg, k, smin)
            ha = cg.size * bc.STRIDE ** 2 * 0.05 ** 2 / 1e4
            if dens_min is not None:
                vers = len(xy5) >= 5 and len(xy5) / ha >= dens_min
            if vers and esp_max is not None:
                vers = len(xy5) >= 5 and float(np.median(cKDTree(xy5).query(xy5, k=2)[0][:, 1])) <= esp_max
        if vers and veg_min is not None:
            vers = float(ctx.carte("img", "veg").mean()) >= veg_min
        if vers and (n_min_petit or reg_max is not None or ratio_max is not None or ratio_min is not None):
            xy, sc = branche_petits(ctx)
            # compte au seuil de service (0,30 sur le score rendu) : n_min_petit et les rapports. Les candidats « CB1_npet*,
            # CB1_rmin* » de la liste cb1c comptaient tous les pics (seuil 0 + décalage) : erreur corrigée par compte_30.
            npet = int((sc >= 0.30).sum()) if compte_30 else len(xy)
            if npet < n_min_petit:
                vers = False
            elif reg_max is not None and not (_regularite(xy) <= reg_max):
                vers = False
            elif ratio_max is not None or ratio_min is not None:
                n5 = int((bc.pics(cg, k, 0.30)[1] >= 0.30).sum())
                q = npet / (n5 + 1)
                vers = (ratio_max is None or q <= ratio_max) and (ratio_min is None or q >= ratio_min)
            if vers:
                return xy, sc
        elif vers:
            return branche_petits(ctx)
        return bc.pics(cg, k)
    return f


# ------------------------------------------------------------------------------------------------ CB3
def f_trous(base_spec=("seul", {"modele": "v5"}), source="v5", variante="base", ancre=0.30, delta=0.10, plancher=None,
            tol_d=0.30, tol_angle=25.0, mode="milieu", k=bc.K_PICS, min_ancres=6, carte_bas=None):
    """CB3 : seconde passe à seuil bas dans les trous de la géométrie de plantation.
    1. Ancres = points du candidat de base de score >= ancre ; espacement d = médiane des distances au plus proche voisin.
    2. Pics bas = pics de la carte `source` (ou du mélange `carte_bas`) de score dans [ancre - delta, ancre), ou
       [plancher, ancre) si plancher est donné, à plus de 0,5 d de toute ancre.
    3. Un pic bas est promu (score porté à `ancre`, donc gardé à tout seuil de la grille <= ancre) :
       mode « milieu » : s'il existe deux ancres a, b à une distance d (± tol_d) du pic, dans des directions opposées
         (angle entre p->a et p->b à 180° ± tol_angle) : le pic bouche un trou au milieu d'un rang ;
       mode « reseau » : s'il tombe à moins de tol_d x d d'une place prédite a + v, où v est l'un des deux vecteurs
         du réseau de plantation (vecteurs au plus proche voisin les plus fréquents) et la place est vide ;
       mode « les_deux » : l'un ou l'autre.
    Moins de min_ancres ancres : rien n'est promu. Les points de base gardent leur score (la grille s'y applique)."""
    fb = construire(*base_spec)

    def f(ctx):
        xy, sc = fb(ctx)
        xy, sc = np.asarray(xy, "float64").reshape(-1, 2), np.asarray(sc, "float64")
        A = xy[sc >= ancre]
        if len(A) < min_ancres:
            return xy, sc
        ta = cKDTree(A)
        dd, ii = ta.query(A, k=2)
        d = float(np.median(dd[:, 1]))
        if not np.isfinite(d) or d <= 0:
            return xy, sc
        c = (_carte_melange(ctx, carte_bas, "moyenne", variante) if carte_bas else ctx.carte(source, variante)).astype("float32")
        bas = plancher if plancher is not None else ancre - delta
        pxy, psc = bc.pics(c, k, bas)
        g = psc < ancre
        pxy, psc = pxy[g], psc[g]
        if not len(pxy):
            return xy, sc
        dmin, _ = ta.query(pxy, k=1)
        g = dmin > 0.5 * d
        pxy, psc = pxy[g], psc[g]
        if not len(pxy):
            return xy, sc
        promu = np.zeros(len(pxy), bool)
        if mode in ("milieu", "les_deux"):
            voisins = ta.query_ball_point(pxy, (1 + tol_d) * d)
            cmax = np.cos(np.radians(180 - tol_angle))
            for n, vs in enumerate(voisins):
                if len(vs) < 2:
                    continue
                v = A[vs] - pxy[n]
                r = np.linalg.norm(v, axis=1)
                ok = r >= (1 - tol_d) * d
                v, r = v[ok], r[ok]
                if len(v) < 2:
                    continue
                u = v / r[:, None]
                cs = u @ u.T
                if (cs <= cmax).any():
                    promu[n] = True
        if mode in ("reseau", "les_deux"):
            vec = A[ii[:, 1]] - A
            vec[vec[:, 0] < 0] *= -1                                  # demi-plan canonique
            ang = np.degrees(np.arctan2(vec[:, 1], vec[:, 0])) % 180
            h, _ = np.histogram(ang, bins=18, range=(0, 180))
            dirs = []
            for b in np.argsort(-h)[:4]:
                m = (ang >= 10 * b) & (ang < 10 * b + 10)
                if m.sum() >= 3:
                    v = np.median(vec[m], 0)
                    if all(abs(np.degrees(np.arctan2(v[1], v[0]) - np.arctan2(w[1], w[0]))) % 180 > 30 for w in dirs):
                        dirs.append(v)
                if len(dirs) == 2:
                    break
            if dirs:
                preds = np.concatenate([A + s * v for v in dirs for s in (1, -1)])
                dp, _ = ta.query(preds, k=1)
                preds = preds[dp > 0.5 * d]                           # places vides
                if len(preds):
                    dq, _ = cKDTree(preds).query(pxy, k=1)
                    promu |= dq <= tol_d * d
        if promu.any():
            xy = np.concatenate([xy, pxy[promu]])
            sc = np.concatenate([sc, np.full(promu.sum(), ancre)])
        return xy, sc
    return f


FABRIQUES = dict(ca.FABRIQUES)
FABRIQUES.update(aiguillage_v2=f_aiguillage_v2, trous=f_trous)
ca.FABRIQUES.update(aiguillage_v2=f_aiguillage_v2, trous=f_trous)     # pour les petit_spec / base_spec imbriqués


def construire(fabrique, reglages):
    return FABRIQUES[fabrique](**reglages)
