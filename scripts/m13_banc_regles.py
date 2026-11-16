#!/usr/bin/env python3
"""Règles candidates de M-banc (nuit du 13/11), toutes écrites comme regle(d, G2) -> réponses, sur les probabilités en
cache. d : dictionnaire d'un jeu (m13_banc_commun), G2 : morceaux 2 x 2 de la v10b (n, 4, 4), sans NaN.

Briques :
- proche(d, G2, t) : lecteur proche de F1 (v10b lue entière + morceaux, mélange géométrique à trois) décidé avec les
  seuils de la v10b sauf la confiance t (nombre ou tableau par photo) ;
- F1 = proche à 0,70 ; photo « loin » (p_loin >= 0,5) : réponse de la v2 si elle alerte, sinon celle du lecteur proche.
"""
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
from fieldscan.modules import maladies  # noqa: E402
import m12_banc_commun as B  # noqa: E402

AL = list(B.ALERTE)


def melange(d, G2):
    return maladies.melange_geometrique(maladies.lecture_morceaux(d["P10"], G2), d["Pso"], d["Pv2"])


def proche(d, G2, t=0.70, P=None):
    P = melange(d, G2) if P is None else P
    return maladies.decider_convnext(P, {**B.M_V10B, "seuil": t})[0].astype(object)


def f1_like(d, rp, loin=None):
    loin = d["loin"] if loin is None else loin
    rl = d["r_loin"]
    return np.where(loin & np.isin(rl, AL), rl, rp)


# ---------------------------------------------------------------- MB1
def mb1_a(tL):
    """Photo « loin » : v2 si elle alerte, sinon lecteur proche au seuil tL ; photo proche : F1."""
    def r(d, G2):
        P = melange(d, G2)
        rp, rpl = proche(d, G2, 0.70, P), proche(d, G2, tL, P)
        return np.where(d["loin"], np.where(np.isin(d["r_loin"], AL), d["r_loin"], rpl), rp)
    return r


def mb1_b_et(tL):
    """Photo « loin » en alerte seulement si la v2 et le lecteur proche (seuil tL) alertent."""
    def r(d, G2):
        P = melange(d, G2)
        rp, rpl = proche(d, G2, 0.70, P), proche(d, G2, tL, P)
        deux = np.isin(d["r_loin"], AL) & np.isin(rpl, AL)
        return np.where(d["loin"], np.where(deux, d["r_loin"], "saine"), rp)
    return r


def mb1_b_proche(tL):
    """Photo « loin » : lecteur proche seul au seuil tL (la v2 n'est plus lue)."""
    def r(d, G2):
        P = melange(d, G2)
        return np.where(d["loin"], proche(d, G2, tL, P), proche(d, G2, 0.70, P))
    return r


def mb1_c_seuil(s):
    """Aiguillage à p_loin >= s au lieu de 0,5."""
    def r(d, G2):
        return f1_like(d, proche(d, G2, 0.70), d["p_loin"] >= s)
    return r


def mb1_c_delta(delta):
    """Seuil du lecteur proche t = 0,70 - delta * p_loin, pour toutes les photos ; branche « loin » de F1."""
    def r(d, G2):
        return f1_like(d, proche(d, G2, 0.70 - delta * d["p_loin"]))
    return r


def avec_marge(base, m, portee):
    """« à vérifier » -> « saine » si la v10b entière, la soupe et la v2 donnent toutes P(saine) >= m.
    portee = « loin » (photos p_loin >= 0,5 seulement) ou « toutes »."""
    def r(d, G2):
        x = base(d, G2).copy()
        ps = np.minimum(np.minimum(d["P10"][:, 0], d["Pso"][:, 0]), d["Pv2"][:, 0])
        cond = (x == "a_verifier") & (ps >= m)
        if portee == "loin":
            cond &= d["loin"]
        x[cond] = "saine"
        return x
    return r


def f1(d, G2):
    return f1_like(d, proche(d, G2, 0.70))
