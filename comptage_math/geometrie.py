# -*- coding: utf-8 -*-
"""Contraintes géométriques de plantation (plant-geometry).

Sélection de candidats par processus ponctuel de Strauss (mode a posteriori) :

    E(S) = Σ_{i∈S} (z_i − t) − γ · #{ {i, j} ⊂ S : d_ij < r }

γ = ∞ donne un processus de Gibbs à cœur dur (ensemble indépendant de poids maximal).
Pré-enregistrement et origine des paramètres : `docs/recherche/notes/plant-geometry.md` (E-009).

Domaine de validité : plantation dense, mères seules ; r doit rester sous la distance minimale entre mères.
Toutes les distances sont en mètres.

Vérification synthétique : `python -I -u comptage_math/geometrie.py`.
"""
import math

import numpy as np
from scipy.spatial import cKDTree

INF = math.inf


class _Etat:
    """Ensemble courant, nombre de voisins gardés de chaque candidat, énergie."""

    def __init__(self, w, voisins, gamma):
        self.w = w
        self.v = voisins
        self.g = gamma
        self.dur = math.isinf(gamma)
        self.dans = np.zeros(len(w), bool)
        self.cnt = np.zeros(len(w), int)

    def gain_ajout(self, i):
        if self.dur:
            return self.w[i] if self.cnt[i] == 0 else -INF
        return self.w[i] - self.g * self.cnt[i]

    def ajouter(self, i):
        d = self.gain_ajout(i)
        self.dans[i] = True
        for j in self.v[i]:
            self.cnt[j] += 1
        return d

    def retirer(self, i):
        self.dans[i] = False
        for j in self.v[i]:
            self.cnt[j] -= 1
        return -self.gain_ajout(i)  # cnt[i] n'inclut jamais i lui-même

    def remplir(self, cands):
        """Ajoute gloutonnement (poids décroissant) les candidats de gain > 0. Retourne (gain, ajoutés)."""
        tot, ajout = 0.0, []
        for i in sorted(set(cands), key=lambda k: -self.w[k]):
            if not self.dans[i] and self.gain_ajout(i) > 1e-12:
                tot += self.ajouter(i)
                ajout.append(i)
        return tot, ajout


def selection_strauss(xy_m, z, r, gamma, t):
    """Indices (dans l'ordre d'entrée) des candidats gardés : mode EXACT du processus de Strauss.

    Programme linéaire en nombres entiers (scipy.optimize.milp, HiGHS) :
      max Σ w_i x_i − γ Σ_{(i,j), d<r} y_ij  s.c.  y_ij ≥ x_i + x_j − 1  (γ fini) ; x_i + x_j ≤ 1 (γ = ∞).
    La recherche locale (`selection_strauss_locale`) reste disponible, mais elle se bloque sur une chaîne
    centre–milieu–centre–… où les milieux sont plus forts un à un (vérification synthétique).

    xy_m : (n, 2) positions en mètres ; z : (n,) scores ; r : rayon d'interaction (m) ;
    gamma : pénalité par paire (math.inf = cœur dur) ; t : décalage de poids (poids = z − t).
    """
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix
    xy_m = np.asarray(xy_m, float).reshape(-1, 2)
    z = np.asarray(z, float)
    ok = np.flatnonzero(z - t > 0)
    if len(ok) == 0 or gamma <= 0:
        return ok
    w = z[ok] - t
    n = len(ok)
    P = np.array(sorted(cKDTree(xy_m[ok]).query_pairs(r)), int).reshape(-1, 2) if n > 1 else np.zeros((0, 2), int)
    m = len(P)
    if m == 0:
        return ok
    k = np.arange(m)
    if math.isinf(gamma):
        c = -w
        A = coo_matrix((np.ones(2 * m), (np.r_[k, k], np.r_[P[:, 0], P[:, 1]])), shape=(m, n))
        cons = LinearConstraint(A, -np.inf, 1)
        nv = n
    else:
        c = np.r_[-w, np.full(m, gamma)]
        # x_i + x_j − y_ij ≤ 1
        A = coo_matrix((np.r_[np.ones(2 * m), -np.ones(m)], (np.r_[k, k, k], np.r_[P[:, 0], P[:, 1], n + k])),
                       shape=(m, n + m))
        cons = LinearConstraint(A, -np.inf, 1)
        nv = n + m
    res = milp(c, constraints=cons, integrality=np.ones(nv), bounds=Bounds(0, 1))
    if res.x is None:
        raise RuntimeError(f"milp : {res.message}")
    return ok[np.flatnonzero(res.x[:n] > 0.5)]


def selection_strauss_locale(xy_m, z, r, gamma, t, max_passes=50):
    """Recherche locale (glouton + mouvements 1 → k et k → 1). Approchée ; gardée pour comparaison."""
    xy_m = np.asarray(xy_m, float).reshape(-1, 2)
    z = np.asarray(z, float)
    ok = np.flatnonzero(z - t > 0)
    if len(ok) == 0:
        return np.zeros(0, int)
    w = z[ok] - t
    n = len(ok)
    voisins = [[] for _ in range(n)]
    if gamma > 0 and n > 1:
        for a, b in cKDTree(xy_m[ok]).query_pairs(r):
            voisins[a].append(b)
            voisins[b].append(a)
    if gamma <= 0:
        return ok
    E = _Etat(w, voisins, gamma)
    E.remplir(range(n))
    for _ in range(max_passes):
        ameliore = False
        # retraits simples (cas γ fini : une paire trop coûteuse)
        if not E.dur:
            for i in np.flatnonzero(E.dans):
                if -(w[i] - gamma * E.cnt[i]) > 1e-12:
                    E.retirer(i)
                    ameliore = True
        # « 1 → k » : retirer un point gardé et remplir son voisinage (milieu remplacé par deux centres)
        for j in sorted(np.flatnonzero(E.dans), key=lambda k: w[k]):
            if not E.dans[j] or not voisins[j]:
                continue
            d = E.retirer(j)
            g, ajout = E.remplir([k for k in voisins[j] if not E.dans[k]])
            if d + g > 1e-9:
                ameliore = True
            else:
                for k in ajout:
                    E.retirer(k)
                E.ajouter(j)
        # « k → 1 » : insérer un point en retirant ses voisins gardés, puis remplir autour
        for i in sorted(np.flatnonzero(~E.dans), key=lambda k: -w[k]):
            if E.dans[i]:
                continue
            gard = [k for k in voisins[i] if E.dans[k]]
            d = sum(E.retirer(k) for k in gard)
            d += E.ajouter(i) if E.gain_ajout(i) > -INF else -INF
            if d == -INF:
                for k in gard:
                    E.ajouter(k)
                continue
            autour = {m for k in gard for m in voisins[k]} - {i}
            g, ajout = E.remplir([m for m in autour if not E.dans[m]])
            if d + g > 1e-9:
                ameliore = True
            else:
                for m in ajout:
                    E.retirer(m)
                E.retirer(i)
                for k in gard:
                    E.ajouter(k)
        if not ameliore:
            break
    return ok[np.flatnonzero(E.dans)]


def energie(xy_m, z, garde, r, gamma, t):
    """Énergie E(S) d'un sous-ensemble (indices), pour contrôle."""
    g = np.asarray(garde, int)
    if len(g) == 0:
        return 0.0
    paires = len(cKDTree(np.asarray(xy_m, float)[g]).query_pairs(r))
    if paires and math.isinf(gamma):
        return -INF
    return float((np.asarray(z)[g] - t).sum() - (gamma * paires if paires else 0.0))


def log_intensite_conditionnelle(p_m, z_p, gardes_m, r, gamma, t, r_soi=1.0, inf_remplace=1e6):
    """log λ(p | S) = z(p) − t − γ · n_r(p), pour des points p (m) de score z_p.

    n_r(p) : détections gardées à moins de r de p, sans compter la plus proche si elle est à moins de r_soi
    (« le point lui-même »). γ = ∞ est remplacé par inf_remplace.
    """
    p_m = np.asarray(p_m, float).reshape(-1, 2)
    z_p = np.asarray(z_p, float)
    g = inf_remplace if math.isinf(gamma) else gamma
    if len(p_m) == 0:
        return np.zeros(0)
    gardes_m = np.asarray(gardes_m, float).reshape(-1, 2)
    if len(gardes_m) == 0:
        return z_p - t
    arbre = cKDTree(gardes_m)
    n = np.array([len(x) for x in arbre.query_ball_point(p_m, r)], float)
    dmin, _ = arbre.query(p_m, k=1)
    n -= ((dmin < r_soi) & (dmin < r)).astype(float)
    return z_p - t - g * np.maximum(n, 0)


def _verification_synthetique():
    """Deux centres (z = 2) à 2,2 m et leur milieu (z = 3) : la suppression gloutonne à 1,5 m garde le milieu,
    le mode de Strauss à cœur dur garde les deux centres ; un vrai voisin à 2,2 m n'est jamais supprimé."""
    xy = np.array([[0.0, 0.0], [2.2, 0.0], [1.1, 0.0], [10.0, 0.0]])
    z = np.array([2.0, 2.0, 3.0, 1.5])
    for gamma in (INF, 1.5):
        s = set(selection_strauss(xy, z, 1.5, gamma, 0.5).tolist())
        assert s == {0, 1, 3}, (gamma, s)
    # γ = 0 : pas de répulsion, tous les candidats au-dessus de t
    assert set(selection_strauss(xy, z, 1.5, 0.0, 0.5).tolist()) == {0, 1, 2, 3}
    # milieu plus fort que les deux centres réunis : il est gardé
    z2 = np.array([1.0, 1.0, 4.0, 1.5])
    assert set(selection_strauss(xy, z2, 1.5, INF, 0.5).tolist()) == {2, 3}
    # intensité conditionnelle : le milieu est pénalisé de 2γ, le centre ne l'est pas
    li = log_intensite_conditionnelle(xy[[0, 2]], [2.0, 3.0], xy[[0, 1, 3]], 1.5, 1.0, 0.5)
    assert np.allclose(li, [1.5, 0.5]), li
    # chaîne de 6 centres à 2,2 m et leurs 5 milieux plus forts : les 6 centres sont retrouvés
    c = np.c_[np.arange(6) * 2.2, np.zeros(6)]
    m = (c[1:] + c[:-1]) / 2
    xy3 = np.r_[c, m]
    z3 = np.r_[np.full(6, 1.5), np.full(5, 1.6)]  # 6 × 1,0 > 5 × 1,1
    s3 = selection_strauss(xy3, z3, 1.5, INF, 0.5)
    assert set(s3.tolist()) == set(range(6)), s3
    return "vérification synthétique : OK"


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(_verification_synthetique())
