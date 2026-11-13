#!/usr/bin/env python3
"""Candidats sans entraînement du banc v6 (agent C-banc) : fabriques de fonctions Contexte -> (points, scores).

Familles : modèle seul (référence), C1 symétries, C2 mélanges de cartes, C3 échelles, C4 aiguillage, et idées voisines
(k_pics, seuil relatif, suppression des doublons par distance). Le registre REGISTRE associe un nom à (fabrique, réglages).
"""
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import maximum_filter, uniform_filter
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v6_banc_commun as bc  # noqa: E402

SEUIL_MEMBRE = {"v3": 0.20, "v4": 0.40, "v5": 0.30}      # seuils d'origine de chaque membre (leurs protocoles)


# ------------------------------------------------------------------------------------------------ outils
def supprimer_doublons(xy, sc, rayon):
    """Garde le point de plus haut score dans un rayon donné (px), de proche en proche."""
    if len(xy) < 2:
        return xy, sc
    ordre = np.argsort(-sc)
    xy, sc = xy[ordre], sc[ordre]
    arbre = cKDTree(xy)
    garde = np.ones(len(xy), bool)
    for i, voisins in enumerate(arbre.query_ball_point(xy, rayon)):
        if garde[i]:
            for j in voisins:
                if j > i:
                    garde[j] = False
    return xy[garde], sc[garde]


def signaux(carte, smin=0.2, k=bc.K_PICS):
    """Signaux mesurés sur l'image elle-même : nombre de pics, espacement médian au plus proche voisin (px à 5 cm),
    taille médiane des pics (nombre de cellules au-dessus de la moitié du pic, dans une fenêtre 9 x 9)."""
    xy, sc = bc.pics(carte, k, smin)
    if len(xy) < 5:
        return dict(n=len(xy), esp=np.nan, taille=np.nan)
    d, _ = cKDTree(xy).query(xy, k=2)
    j, i = (xy[:, 1] / bc.STRIDE).astype(int), (xy[:, 0] / bc.STRIDE).astype(int)
    c = np.pad(carte, 4)
    tailles = [(c[a:a + 9, b:b + 9] >= 0.5 * s).sum() for a, b, s in zip(j, i, sc)]
    return dict(n=len(xy), esp=float(np.median(d[:, 1])), taille=float(np.median(tailles)))


# ------------------------------------------------------------------------------------------------ fabriques
def f_seul(modele, variante="base", k=bc.K_PICS):
    return lambda ctx: bc.pics(ctx.carte(modele, variante), k)


def f_melange(membres, mode="moyenne", poids=None, variante="base", k=bc.K_PICS, calibre=False):
    """C2. Mélange des cartes des membres. calibre : chaque carte est d'abord multipliée par 0,30 / seuil du membre
    (met les trois membres sur l'échelle du v5), bornée à 1."""
    w = np.array(poids if poids is not None else [1.0] * len(membres), "float64")
    w = w / w.sum()

    def f(ctx):
        cs = []
        for m in membres:
            c = ctx.carte(m, variante).astype("float64")
            if calibre:
                c = np.minimum(1.0, c * 0.30 / SEUIL_MEMBRE[m])
            cs.append(c)
        if mode == "moyenne":
            c = sum(wi * ci for wi, ci in zip(w, cs))
        elif mode == "maximum":
            c = np.max(cs, 0)
        elif mode == "geometrique":
            c = np.exp(sum(wi * np.log(np.maximum(ci, 1e-6)) for wi, ci in zip(w, cs)))
        elif mode == "logit":
            z = sum(wi * np.log(np.clip(ci, 1e-6, 1 - 1e-6) / (1 - np.clip(ci, 1e-6, 1 - 1e-6))) for wi, ci in zip(w, cs))
            c = 1 / (1 + np.exp(-z))
        else:
            raise KeyError(mode)
        return bc.pics(c.astype("float32"), k)
    return f


def f_echelles(modele, variantes=("base", "s35", "s70"), fusion="maximum", rayon=16, k=bc.K_PICS, gains=None):
    """C3. Plusieurs échelles. fusion « maximum » ou « moyenne » : sur les cartes ramenées à la grille de base ;
    « points » : pics de chaque échelle à sa résolution propre, réunis, doublons supprimés dans `rayon` px."""
    gains = gains or {}

    def f(ctx):
        if fusion in ("maximum", "moyenne"):
            cs = [ctx.carte(modele, v) * gains.get(v, 1.0) for v in variantes]
            c = np.max(cs, 0) if fusion == "maximum" else np.mean(cs, 0)
            return bc.pics(c.astype("float32"), k)
        xs, ss = [], []
        for v in variantes:
            c, e = ctx.carte_propre(modele, v)
            xy, sc = bc.pics(c, k, echelle=e)
            xs.append(xy); ss.append(sc * gains.get(v, 1.0))
        return supprimer_doublons(np.concatenate(xs), np.concatenate(ss), rayon)
    return f


def f_aiguillage(source="v5", smin=0.2, critere="taille", s_taille=12.0, s_esp=45.0, petit=("v3", "base"), grand=("v5", "base"),
                 decalage=0.10, k=bc.K_PICS):
    """C4. v3 quand les plants sont petits (taille des pics) ou espacés (espacement médian), v5 sinon.
    Les signaux sont mesurés sur la carte `source` de l'image. Les scores du v3 sont décalés de `decalage`
    (son seuil d'origine est 0,20, celui du v5 0,30) pour qu'une seule grille de seuils serve aux deux branches."""
    def f(ctx):
        s = signaux(ctx.carte(source, "base"), smin)
        vers_petit = False
        if s["n"] >= 5:
            t, e = s["taille"] < s_taille, s["esp"] > s_esp
            vers_petit = t if critere == "taille" else e if critere == "esp" else (t and e) if critere == "et" else (t or e)
        if vers_petit:
            xy, sc = bc.pics(ctx.carte(*petit), k, bc.SEUILS[0] - decalage)
            return xy, sc + decalage
        return bc.pics(ctx.carte(*grand), k)
    return f


def f_relatif(modele="v5", variante="base", quantile=0.9, cible=0.6, plancher=0.25, gain_max=2.0, n_min=8, k=bc.K_PICS):
    """Seuil relatif à l'image : si l'image porte au moins n_min pics et que leur quantile est au moins `plancher`,
    les scores sont multipliés par cible / quantile (au plus gain_max, au moins 1) : une image de petits plants aux
    réponses faibles mais régulières est remontée ; une image presque vide ne l'est pas."""
    def f(ctx):
        xy, sc = bc.pics(ctx.carte(modele, variante), k, 0.05)
        if len(sc) >= n_min:
            q = float(np.quantile(sc, quantile))
            if q >= plancher:
                sc = np.minimum(1.0, sc * float(np.clip(cible / q, 1.0, gain_max)))
        g = sc >= bc.SEUILS[0]
        return xy[g], sc[g]
    return f


def f_relatif_local(modele="v5", variante="base", fenetre=41, part=0.5, plancher=0.15, k=bc.K_PICS):
    """Seuil relatif au maximum local : un pic est gardé s'il vaut au moins `part` x le maximum de la carte dans une
    grande fenêtre ; son score devient max(score, seuil du pic voisin x part...) : ici score' = score / max local,
    mis à l'échelle du v5 (x 0,6), seulement si le maximum local dépasse `plancher`."""
    def f(ctx):
        c = ctx.carte(modele, variante)
        xy, sc = bc.pics(c, k, 0.05)
        if not len(sc):
            return xy, sc
        mx = maximum_filter(c, size=fenetre, mode="constant")
        j, i = (xy[:, 1] / bc.STRIDE).astype(int), (xy[:, 0] / bc.STRIDE).astype(int)
        loc = mx[j, i]
        rel = np.where(loc >= plancher, np.maximum(sc, part * sc / np.maximum(loc, 1e-6)), sc)
        g = rel >= bc.SEUILS[0]
        return xy[g], np.minimum(rel[g], 1.0)
    return f


def f_k_adaptatif(modele="v5", variante="base", smin=0.2, part=0.5, k_min=3, k_max=9):
    """k_pics adaptatif : fenêtre = `part` x espacement médian des pics de l'image (en cellules), impair, bornée."""
    def f(ctx):
        c = ctx.carte(modele, variante)
        s = signaux(c, smin)
        k = bc.K_PICS
        if s["n"] >= 5:
            k = int(np.clip(round(part * s["esp"] / bc.STRIDE), k_min, k_max))
            k += 1 - k % 2
        return bc.pics(c, k)
    return f


def f_doublons(modele="v5", variante="base", k=3, rayon=14):
    """Pics en fenêtre étroite puis suppression des doublons par distance (disque au lieu du carré de k_pics)."""
    def f(ctx):
        xy, sc = bc.pics(ctx.carte(modele, variante), k)
        return supprimer_doublons(xy, sc, rayon)
    return f


def f_lisse(modele="v5", variante="base", taille=3, k=bc.K_PICS, gain=1.0):
    """Carte lissée (moyenne taille x taille) avant les pics : retire les pics doubles sur une même couronne."""
    def f(ctx):
        return bc.pics((uniform_filter(ctx.carte(modele, variante), taille) * gain).astype("float32"), k)
    return f


def f_union(membres=(("v5", "base", 0.0), ("v3", "base", 0.10)), rayon=16, k=bc.K_PICS):
    """Réunion des pics de plusieurs membres (score décalé par membre), doublons supprimés dans `rayon` px."""
    def f(ctx):
        xs, ss = [], []
        for m, v, dec in membres:
            xy, sc = bc.pics(ctx.carte(m, v), k, bc.SEUILS[0] - dec)
            xs.append(xy); ss.append(sc + dec)
        return supprimer_doublons(np.concatenate(xs), np.concatenate(ss), rayon)
    return f


def f_aiguillage_p90(source="v5", smin=0.15, quantile=0.90, tau=0.50, decalage=0.10, petit=("v3", "base"),
                     grand=("v5", "base"), n_min=1, k=bc.K_PICS, petit_spec=None, grand_spec=None):
    """Essai 5 bis (proposé par C-analyste) : aiguillage par image sur le quantile (90 %) des scores des pics du v5
    (pics >= smin, image entière). Sous `tau` : branche « petits plants » (v3), scores décalés de +decalage (v3 au
    seuil de la grille moins decalage) ; sinon v5. Moins de n_min pics : v5.
    petit_spec / grand_spec : [fabrique, réglages] d'un autre candidat pour l'une des branches (creuser la piste)."""
    fp = construire(*petit_spec) if petit_spec else None
    fg = construire(*grand_spec) if grand_spec else None

    def f(ctx):
        _, sc = bc.pics(ctx.carte(source, "base"), k, smin)
        if len(sc) >= n_min and float(np.quantile(sc, quantile)) < tau:
            if fp is not None:
                xy, s2 = fp(ctx)
                g = s2 + decalage >= bc.SEUILS[0]
                return xy[g], s2[g] + decalage
            xy, s2 = bc.pics(ctx.carte(*petit), k, bc.SEUILS[0] - decalage)
            return xy, s2 + decalage
        return fg(ctx) if fg is not None else bc.pics(ctx.carte(*grand), k)
    return f


FABRIQUES = dict(aiguillage_p90=f_aiguillage_p90, seul=f_seul, melange=f_melange, echelles=f_echelles, aiguillage=f_aiguillage, relatif=f_relatif,
                 relatif_local=f_relatif_local, k_adaptatif=f_k_adaptatif, doublons=f_doublons, lisse=f_lisse, union=f_union)


def construire(fabrique, reglages):
    return FABRIQUES[fabrique](**reglages)
