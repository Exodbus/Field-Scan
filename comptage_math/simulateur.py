# -*- coding: utf-8 -*-
"""Simulateur v2 de bananeraie dense vue du dessus (D-013), version v2.3 (3e et dernière version).

v2.3 (changements sur v2.2, chacun justifié par une statistique CAL ; v2.2 conservée dans
`out/comptage_math/leaf-mathematician/D-013/v2.2/simulateur_v2.2.py`) :
- géométrie recalée avec les allées réellement utilisées (p = 0,3), σ_f plafonné par la part de cellules de 10 m vides
  de CAL, densité moyenne et CV des densités entre tuiles de CAL dans le critère, facteur de densité ;
- texture 12–30 cm du limbe : profil 1D le long de la nervure (plis et déchirures perpendiculaires à la nervure)
  au lieu du bruit isotrope « marbré » de v2.2, plus une part isotrope faible.

v2.2 (changements sur v2.1, chacun justifié par une statistique CAL ; v2.1 conservée dans
`out/comptage_math/leaf-mathematician/D-013/v2.1/simulateur_v2.1.py`) :
- positions : réseau rectangulaire perturbé + amincissement modulé par un champ lisse + cœur dur, à la place de
  l'inhibition douce séquentielle (pic de g(r), d1, taux de contact, CV de densité de CAL) ;
- texture du limbe à l'échelle 12–30 cm (bruit passe-bande isotrope) : fractions feuillage / herbe de CAL selon la
  règle de classes d'image-analyst ;
- effet tuile : fenêtres « sec » CAL au sol en proportion tirée par tuile, part d'herbe tirée par tuile
  (moyenne et dispersion entre tuiles des fractions « sec » et « herbe » de CAL).

Rédacteur unique : leaf-mathematician. Contrat : scientific-challenger, note, section « D-013 —
Critères d'acceptation du simulateur v2 ». Calibration : blocs CAL seulement de
`out/comptage_math/image-analyst/D-013/stats_photometriques.json`,
`out/comptage_math/plant-geometry/D-013/stats_geometriques.json`, et des tuiles / références CAL
de `bv_session_a` (`partage.csv`). Aucun score de détection n'a servi.

Ce module n'importe RIEN des modules de détection (ni `feuille.py`, ni `votes.py`, ni
`orientation.py`, ni gabarits) : seulement numpy, scipy.ndimage, OpenCV, json.

Tableau « formes et origines » (chaque forme fonctionnelle utilisée)
-------------------------------------------------------------------
| Élément | Forme fonctionnelle | Origine |
| --- | --- | --- |
| Positions des plants | réseau rectangulaire (pas b1, b2 = k·b1, orientation et origine uniformes) perturbé par N(0, σ_j²), cœur dur h (une des deux mères d'une paire trop proche est retirée), puis amincissement de probabilité logistique(c + σ_f Z(x)), Z champ gaussien lisse (ℓ_f) | g(r), d1, taux de contact, CV de densité de CAL [O] ; (b1, k, σ_j, σ_f, h) ajustés sur CAL |
| Densité de la scène | log-normale (ha⁻¹) ; allée sans plants (bande droite) dans une partie des scènes | densités par photo CAL [O] (`par_photo.csv`) ; allée [H], part et largeur choisies sur la dispersion des fractions entre tuiles de CAL |
| Taille de couronne s (côté de boîte) | log-normale ; copule gaussienne avec l'espacement local (ρ) | tailles CAL [O] ; Spearman taille–d1 = 0,42 sur CAL [O] |
| Envergure foliaire | R_e = f_env · s/2 · e^(N(0, σ_scène)) (stade de la parcelle) | [H] ; f_env choisi sur les fractions de classes de CAL |
| Nombre de feuilles K | 6 + 4 s/2,8 + N(0, 1,5), borné à [4, 15] | [H], `modele_feuille.md` § 2.2 (4 à 12), relevé pour la canopée jointive de CAL |
| Phyllotaxie | θ_k = θ0 + k · 144° + N(0, 0,25 rad) | [H] spirale 2/5 |
| Limbe | contour oblong : demi-largeur w(s) = W/2 · (1 − ǀ2s−1ǀ^p)^½ · (1 + τ(s−½)) · c_côté, bords non parallèles, base et sommet arrondis | [H] forme botanique du limbe de *Musa* (oblong, sommet tronqué arrondi) ; pas de gaussienne ni de bande de largeur constante |
| Nervure | courbe : décalage latéral κ u²/2 ; raccourcissement vertical inclus dans la longueur projetée | [H] |
| Déchirures | entailles perpendiculaires à la nervure (inclinaison ψ ≤ 0,2 rad), positions par processus de Poisson le long de la nervure, profondeur d·w, largeur g | [H] ; plus fréquentes sur les feuilles âgées |
| Pétiole | bande étroite (4–6 cm) du centre à la base du limbe | [H] |
| Cigare | ellipse claire 6 × 25 cm au centre | [H] |
| Feuilles sèches | feuilles pendantes au pied (projetées 0,4–1,0 m), couleur « sec » de CAL ; marges nécrosées des plus vieilles feuilles | couleur [O] CAL ; nombre choisi sur la fraction « sec » de CAL |
| Hauteurs | z = z_top(1 − 0,3 a) − retombée · (u/L)² ; z-buffer : l'ordre de recouvrement est aléatoire et les feuilles des voisins s'entremêlent | [H] |
| Couleur du limbe | Lab : moyenne et dispersions de la classe « feuillage_vert » de CAL ; demi-limbes inégalement éclairés ; ondulation ; côtes (profil corrélé le long de la nervure, bandes perpendiculaires à la nervure) ; plis 12–30 cm (profil 1D le long de la nervure) et part isotrope faible ; bruit fin | [O] CAL ; [H] partage des variances |
| Ombres | occultation ambiante : assombrissement exp(−(H_loc − z)/h0), H_loc = maximum local de la hauteur sur un disque r_ao | [H] ; ciel couvert, ombres sans direction [O] CAL ; (h0, r_ao) choisis sur la fraction et la longueur de corrélation des ombres de CAL |
| Fonds | collage (fenêtres de Hann, recouvrement ½) de fenêtres réelles CAL (herbe, sol, ombre, mixte, sec) à > 1,5 m de toute référence, prises dans quelques tuiles sources par scène ; mélange herbe/sol/sec par champs lissés, parts tirées par tuile | [O] CAL (`fonds_cal.npz`) |
| Rejets (non comptés) | petits plants à feuilles étroites, à 0,5–1,2 m de la mère | [H] entièrement (aucune statistique de rejet [O]) |
| Dégradation | rendu à 1 cm/px → moyenne par zone à la résolution tirée dans CAL → PSF gaussienne → gain → bruit → JPEG 95 | résolution, netteté, bruit, qualité JPEG [O] CAL |

Conventions : image (ligne, colonne) ; x = colonne × res, y = ligne × res (m) ; tuile de 512 px ;
région comptée = disque ∩ zone propre, comme `dev_dense_images.csv`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage

VERSION = "v2.3"
RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "out/comptage_math/leaf-mathematician/D-013/v2.3"
PARAMS = DOSSIER / "parametres_v2.3.json"
FONDS = DOSSIER / "fonds_cal.npz"
RES_FINE = 0.01          # m/px du rendu fin (contrat : ≤ 1 cm/px)
N_TUILE = 512
RAPPORT_PHOTO = 0.75     # hauteur / largeur de la photo (rectangle hors duquel la tuile est noire)

_CACHE = {}


def charger(params=None, fonds=None):
    """Paramètres (dict) et bibliothèque de fonds (dict de tableaux)."""
    if params is None:
        if "p" not in _CACHE:
            _CACHE["p"] = json.loads(Path(PARAMS).read_text(encoding="utf-8"))
        params = _CACHE["p"]
    if fonds is None:
        if "f" not in _CACHE:
            z = np.load(FONDS)
            _CACHE["f"] = {k: z[k] for k in z.files}
        fonds = _CACHE["f"]
    return params, fonds


def _v(p, k):
    """Valeur d'un paramètre (les entrées du JSON sont {valeur, source})."""
    e = p[k]
    return e["valeur"] if isinstance(e, dict) else e


# ---------------------------------------------------------------------------
# Géométrie de la scène
# ---------------------------------------------------------------------------


_ZN = np.random.default_rng(0).normal(size=4000)


def _decalage_logit(m, sf):
    """c tel que E[logistique(c + sf Z)] = m, Z ~ N(0, 1) (bissection)."""
    lo, hi = -12.0, 12.0
    for _ in range(50):
        c = 0.5 * (lo + hi)
        if np.mean(1 / (1 + np.exp(-(c + sf * _ZN)))) < m:
            lo = c
        else:
            hi = c
    return c


def positions(rng, dens, cote, b1, k, sj, sf, lf, h):
    """Réseau rectangulaire perturbé et aminci sur [0, cote]² (m), densité visée dens (ha⁻¹).
    Pas b1 × k·b1, orientation et origine uniformes, bruit N(0, sj²) ; rétention logistique(c + sf·Z(x)),
    Z champ gaussien lisse de longueur lf, c tel que la densité moyenne soit dens ; cœur dur h appliqué avant
    l'amincissement (la rétention moyenne est calculée sur le réseau après cœur dur : densité visée conservée)."""
    from scipy.spatial import cKDTree
    b2 = k * b1
    m = dens * b1 * b2 / 1e4
    if m > 0.95:                                   # réseau trop lâche : on le resserre (même forme)
        f = math.sqrt(0.95 / m)
        b1, b2, m = b1 * f, b2 * f, 0.95
    ang = rng.uniform(0, math.pi)
    R = 0.75 * cote + 2 * b2
    i = np.arange(-int(R / b1) - 1, int(R / b1) + 2)
    j = np.arange(-int(R / b2) - 1, int(R / b2) + 2)
    I, J = np.meshgrid(i, j)
    u = (I.ravel() + rng.uniform()) * b1
    v = (J.ravel() + rng.uniform()) * b2
    x = cote / 2 + u * math.cos(ang) - v * math.sin(ang)
    y = cote / 2 + u * math.sin(ang) + v * math.cos(ang)
    pts = np.c_[x, y] + rng.normal(0, sj, (len(x), 2))
    pts = pts[(pts[:, 0] >= 0) & (pts[:, 0] < cote) & (pts[:, 1] >= 0) & (pts[:, 1] < cote)]
    garde = np.ones(len(pts), bool)
    for a, b in sorted(cKDTree(pts).query_pairs(h)):
        if garde[a] and garde[b]:
            garde[a if rng.random() < 0.5 else b] = False
    pts = pts[garde]
    m = min(0.95, dens / 1e4 / (len(pts) / cote ** 2))
    if sf > 0:
        n = 64
        pas = cote / n
        Z = ndimage.gaussian_filter(rng.normal(size=(n, n)), lf / pas, mode="wrap")
        Z /= Z.std() + 1e-9
        z = Z[np.clip((pts[:, 1] / pas).astype(int), 0, n - 1), np.clip((pts[:, 0] / pas).astype(int), 0, n - 1)]
        c = _decalage_logit(m, sf)
    else:
        z = np.zeros(len(pts))
        c = math.log(m / (1 - m))
    return pts[rng.random(len(pts)) < 1 / (1 + np.exp(-(c + sf * z)))]


def positions_scene(rng, S, M, p):
    """Mères de la scène, repère de la tuile (m) : densité log-normale CAL, réseau perturbé et aminci, allée."""
    cote = S + 2 * M
    dens = math.exp(rng.normal(_v(p, "densite_log_mu"), _v(p, "densite_log_sigma"))) * _v(p, "densite_facteur")  # ha⁻¹
    # allée sans plants (chemin, drain) dans une partie des scènes [H] ; densité hors allée relevée
    allee = rng.random() < _v(p, "p_allee")
    if allee:
        ang, c0, dl = rng.uniform(0, math.pi), rng.uniform(0, S, 2), rng.uniform(*_v(p, "allee_demi_largeur_m"))
        dens = dens * cote / max(cote - 2 * dl, 1.0)
    pts = positions(rng, dens, cote, _v(p, "reseau_b1_m"), _v(p, "reseau_k"), _v(p, "reseau_sigma_m"),
                    _v(p, "amincissement_sigma"), _v(p, "amincissement_l_m"), _v(p, "coeur_dur_m")) - M
    if allee:
        dist = np.abs((pts[:, 0] - c0[0]) * -math.sin(ang) + (pts[:, 1] - c0[1]) * math.cos(ang))
        pts = pts[dist > dl]
    return pts


def tailles(rng, pts, mu, sigma, rho):
    """Log-normale ; copule gaussienne avec l'espacement local (moyenne des 3 premiers voisins)."""
    from scipy.spatial import cKDTree
    from scipy.special import ndtri
    n = len(pts)
    if n < 4:
        return np.exp(mu + sigma * rng.normal(size=n))
    d, _ = cKDTree(pts).query(pts, k=4)
    e = d[:, 1:].mean(1)
    rang = (np.argsort(np.argsort(e)) + 0.5) / n
    z = rho * ndtri(rang) + math.sqrt(1 - rho ** 2) * rng.normal(size=n)
    return np.exp(mu + sigma * z)


# ---------------------------------------------------------------------------
# Feuilles et plants
# ---------------------------------------------------------------------------


def _lab_tire(rng, moy, ect, decal=(0.0, 0.0, 0.0)):
    return np.array([rng.normal(moy[i] + decal[i], ect[i]) for i in range(3)])


def tirer_plant(rng, cx, cy, s, p, rejet=False, f_sec=1.0, f_env_scene=1.0):
    """Liste d'organes (dicts) d'un plant de taille s (m) centré en (cx, cy) (m)."""
    org = []
    fe0, fe1 = _v(p, "f_env")
    if rejet:
        K = int(rng.integers(3, 6))
        R_e = s / 2 * rng.uniform(fe0, fe1)
        wl = (0.15, 0.25)
    else:
        K = int(np.clip(round(6 + 4 * s / 2.8 + rng.normal(0, 1.5)), 4, 15))
        R_e = s / 2 * rng.uniform(fe0, fe1) * f_env_scene
        wl = (0.30, 0.42)
    z_top = s * rng.uniform(0.8, 1.0)
    theta0 = rng.uniform(0, 2 * math.pi)
    vert_m = np.add(_v(p, "lab_feuillage_moy"), [_v(p, "decalage_L_feuillage")] + list(_v(p, "decalage_ab_feuillage")))
    vert_e = _v(p, "lab_feuille_ect")
    for k in range(K):
        a = k / max(K - 1, 1)                      # âge relatif : 0 = la plus jeune
        th = theta0 + k * math.radians(144) + rng.normal(0, 0.25)
        r0 = rng.uniform(0.15, 0.45) * s / 2.8
        L = max(0.2, R_e * rng.uniform(0.75, 1.0) - r0)
        W = L * rng.uniform(*wl)
        nec = (not rejet) and a > 0.75 and rng.random() < _v(p, "p_marge_necrosee")
        org.append(dict(type="limbe", cx=cx, cy=cy, th=th, r0=r0, L=L, W=W,
                        kappa=rng.uniform(-0.35, 0.35) / L, p=rng.uniform(2.0, 3.5), tau=rng.uniform(-0.3, 0.3),
                        cote=(rng.uniform(0.85, 1.15), rng.uniform(0.85, 1.15)),
                        lam_t=max(0.04, 0.25 - 0.17 * a * rng.uniform(0.5, 1.0)), psi=rng.uniform(-0.2, 0.2),
                        z0=z_top * (1 - 0.3 * a) + rng.normal(0, 0.1), chute=L * (0.3 + 0.6 * a) * 0.6,
                        lab=_lab_tire(rng, vert_m, vert_e), eclair=rng.uniform(0, _v(p, "eclairage_demi_limbe")) * rng.choice([-1, 1]),
                        ond=(rng.uniform(0, _v(p, "ondulation_L")), rng.uniform(0.15, 0.5), rng.uniform(0, 2 * math.pi)),
                        necrose=rng.uniform(0.1, 0.3) if nec else 0.0, seche=False))
        org.append(dict(type="petiole", cx=cx, cy=cy, th=th, r0=r0, larg=rng.uniform(0.04, 0.06),
                        z0=z_top * (1 - 0.3 * a) + 0.05))
    if not rejet:
        for _ in range(rng.poisson(_v(p, "n_seches_par_plant") * f_sec)):
            th = rng.uniform(0, 2 * math.pi)
            L = rng.uniform(0.4, 1.0)
            org.append(dict(type="limbe", cx=cx, cy=cy, th=th, r0=rng.uniform(0.1, 0.3), L=L, W=L * rng.uniform(0.3, 0.5),
                            kappa=rng.uniform(-0.5, 0.5) / L, p=rng.uniform(2.0, 3.0), tau=rng.uniform(-0.4, 0.4),
                            cote=(rng.uniform(0.7, 1.1), rng.uniform(0.7, 1.1)), lam_t=0.06, psi=rng.uniform(-0.3, 0.3),
                            z0=rng.uniform(0.8, 2.0), chute=0.2, lab=_lab_tire(rng, _v(p, "lab_sec_moy"), _v(p, "lab_sec_ect")),
                            eclair=rng.uniform(-6, 6), ond=(0, 1, 0), necrose=0.0, seche=True))
        if rng.random() < 0.8:
            org.append(dict(type="cigare", cx=cx, cy=cy, th=rng.uniform(0, 2 * math.pi), z0=z_top + 0.1))
    return org


def _boite(cx, cy, rayon, Nf):
    c0 = max(0, int((cx - rayon) / RES_FINE))
    c1 = min(Nf, int((cx + rayon) / RES_FINE) + 2)
    l0 = max(0, int((cy - rayon) / RES_FINE))
    l1 = min(Nf, int((cy + rayon) / RES_FINE) + 2)
    if c1 <= c0 or l1 <= l0:
        return None
    X = (np.arange(c0, c1, dtype=np.float32) + 0.5) * RES_FINE
    Y = (np.arange(l0, l1, dtype=np.float32) + 0.5) * RES_FINE
    return (l0, l1, c0, c1), X[None, :], Y[:, None]


def _lab_rgb(L, a, b):
    lab = np.stack([np.clip(L, 0, 100), a, b], -1).astype(np.float32)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_Lab2RGB), 0, 1)


def peindre(o, tampons, rng, p):
    """Peint un organe dans les tampons fins (rgb, z, couvert) avec test de hauteur (z-buffer)."""
    rgb, zb, cov = tampons
    Nf = zb.shape[0]
    if o["type"] == "limbe":
        ext = o["r0"] + o["L"] + o["W"]
        cxl = o["cx"] + math.cos(o["th"]) * (o["r0"] + o["L"] / 2)
        cyl = o["cy"] + math.sin(o["th"]) * (o["r0"] + o["L"] / 2)
        b = _boite(cxl, cyl, o["L"] / 2 + o["W"], Nf)
        if b is None or ext <= 0:
            return
        (l0, l1, c0, c1), X, Y = b
        ct, st = math.cos(o["th"]), math.sin(o["th"])
        dx, dy = X - o["cx"], Y - o["cy"]
        u = (dx * ct + dy * st) - o["r0"]
        t = (-dx * st + dy * ct) - 0.5 * o["kappa"] * u * u
        L, W = o["L"], o["W"]
        s = u / L
        dedans = (s > 0) & (s < 1)
        sc = np.clip(s, 0, 1)
        w = 0.5 * W * np.sqrt(np.clip(1 - np.abs(2 * sc - 1) ** o["p"], 0, 1)) * (1 + o["tau"] * (sc - 0.5))
        w = w * np.where(t >= 0, o["cote"][0], o["cote"][1])
        at = np.abs(t)
        m = dedans & (at <= w)
        if not m.any():
            return
        # déchirures perpendiculaires à la nervure (une suite de positions par côté)
        r = at / np.maximum(w, 1e-4)
        for sgn in (1, -1):
            nt = rng.poisson(L / o["lam_t"]) + 1
            uj = np.sort(rng.uniform(0, L, nt))
            dj = rng.uniform(0.1, 0.9, nt)
            gj = rng.uniform(0.005, 0.02, nt)
            ua = u - at * math.tan(o["psi"])
            idx = np.clip(np.searchsorted(uj, ua), 1, nt - 1) if nt > 1 else np.zeros(ua.shape, int)
            for jj in (idx - 1, idx) if nt > 1 else (idx,):
                coupe = (np.abs(ua - uj[jj]) < gj[jj] / 2) & (r > 1 - dj[jj]) & ((t >= 0) if sgn > 0 else (t < 0))
                m &= ~coupe
        z = o["z0"] - o["chute"] * sc * sc
        lab = o["lab"]
        Lc = lab[0] + o["eclair"] * np.sign(t) * np.clip(r, 0, 1) + o["ond"][0] * np.sin(2 * np.pi * u / o["ond"][1] + o["ond"][2])
        # côtes du limbe : profil 1D le long de la nervure (bandes perpendiculaires à la nervure), corrélé sur σ_tex
        nb = max(8, int(L / RES_FINE) + 4)
        prof = ndimage.gaussian_filter1d(rng.normal(0, 1, nb), _v(p, "texture_limbe_m") / RES_FINE)
        prof *= _v(p, "texture_limbe_L") / (prof.std() + 1e-6)
        tex = prof[np.clip((u / RES_FINE).astype(int), 0, nb - 1)].astype(np.float32)
        # texture 12–30 cm (échelle de la règle « herbe » d'image-analyst) : plis du limbe, profil 1D passe-bande le
        # long de la nervure (bandes perpendiculaires à la nervure), plus une part isotrope faible, à basse résolution
        s1, s2 = _v(p, "texture_moyenne_m")
        if _v(p, "texture_moyenne_L") > 0:
            pb = rng.normal(0, 1, nb)
            pb = ndimage.gaussian_filter1d(pb, s1 / RES_FINE) - ndimage.gaussian_filter1d(pb, s2 / RES_FINE)
            pb *= _v(p, "texture_moyenne_L") / (pb.std() + 1e-6)
            tex = tex + pb[np.clip((u / RES_FINE).astype(int), 0, nb - 1)].astype(np.float32)
        if _v(p, "texture_iso_L") > 0:
            f = 4                                       # calcul à 4 cm/px puis agrandi (assez fin pour 12–30 cm)
            hh, ww = max(2, Lc.shape[0] // f + 1), max(2, Lc.shape[1] // f + 1)
            bb = rng.normal(0, 1, (hh, ww)).astype(np.float32)
            bp = ndimage.gaussian_filter(bb, s1 / RES_FINE / f) - ndimage.gaussian_filter(bb, s2 / RES_FINE / f)
            bp = cv2.resize(bp * (_v(p, "texture_iso_L") / (bp.std() + 1e-6)), (ww * f, hh * f), interpolation=cv2.INTER_LINEAR)
            tex = tex + bp[:Lc.shape[0], :Lc.shape[1]]
        Lc = Lc + tex + rng.normal(0, _v(p, "bruit_limbe_L"), Lc.shape).astype(np.float32)
        ac = np.broadcast_to(lab[1], Lc.shape).astype(np.float32).copy()
        bc = np.broadcast_to(lab[2], Lc.shape).astype(np.float32).copy()
        nerv = at < 0.02 + 0.01 * (1 - sc)
        Lc = np.where(nerv, Lc + 8, Lc)
        ac = np.where(nerv, ac + 6, ac)
        if o["necrose"] > 0:
            nec = r > 1 - o["necrose"]
            sm, se = _v(p, "lab_sec_moy"), _v(p, "lab_sec_ect")
            Lc = np.where(nec, sm[0] + rng.normal(0, se[0] / 2), Lc)
            ac = np.where(nec, sm[1], ac)
            bc = np.where(nec, sm[2], bc)
    elif o["type"] == "petiole":
        cxl = o["cx"] + math.cos(o["th"]) * o["r0"] / 2
        cyl = o["cy"] + math.sin(o["th"]) * o["r0"] / 2
        b = _boite(cxl, cyl, o["r0"] / 2 + 0.05, Nf)
        if b is None:
            return
        (l0, l1, c0, c1), X, Y = b
        dx, dy = X - o["cx"], Y - o["cy"]
        u = dx * math.cos(o["th"]) + dy * math.sin(o["th"])
        t = -dx * math.sin(o["th"]) + dy * math.cos(o["th"])
        m = (u >= 0) & (u <= o["r0"] + 0.03) & (np.abs(t) <= o["larg"] / 2)
        if not m.any():
            return
        z = o["z0"] + 0 * u
        Lc, ac, bc = 62 + 0 * u, -10 + 0 * u, 30 + 0 * u
    else:  # cigare
        b = _boite(o["cx"], o["cy"], 0.15, Nf)
        if b is None:
            return
        (l0, l1, c0, c1), X, Y = b
        dx, dy = X - o["cx"], Y - o["cy"]
        u = dx * math.cos(o["th"]) + dy * math.sin(o["th"])
        t = -dx * math.sin(o["th"]) + dy * math.cos(o["th"])
        m = (u / 0.125) ** 2 + (t / 0.03) ** 2 <= 1
        if not m.any():
            return
        z = o["z0"] + 0 * u
        Lc, ac, bc = 72 + 0 * u, -20 + 0 * u, 42 + 0 * u
    zz = zb[l0:l1, c0:c1]
    m = m & (z > zz)
    if not m.any():
        return
    col = _lab_rgb(np.broadcast_to(Lc, m.shape), np.broadcast_to(ac, m.shape), np.broadcast_to(bc, m.shape))
    rgb[l0:l1, c0:c1][m] = col[m]
    zz[m] = np.broadcast_to(z, m.shape)[m]
    cov[l0:l1, c0:c1][m] = 1


# ---------------------------------------------------------------------------
# Fonds réels CAL
# ---------------------------------------------------------------------------


def _quilt(rng, patchs, res_p, res, n, rgb=True):
    """Collage de fenêtres réelles (fenêtre de Hann, recouvrement 1/4) sur n × n px à la résolution res."""
    acc = np.zeros((n, n, 3), np.float32)
    poids = np.zeros((n, n), np.float32)
    k = rng.integers(0, len(patchs))
    tp = max(4, int(round(patchs.shape[1] * res_p[k] / res)))
    pas = max(2, tp // 2)
    hw = np.outer(np.hanning(tp + 2)[1:-1], np.hanning(tp + 2)[1:-1]).astype(np.float32) + 1e-3
    for y in range(-tp // 2 - int(rng.integers(0, pas)), n, pas):
        for x in range(-tp // 2 - int(rng.integers(0, pas)), n, pas):
            k = rng.integers(0, len(patchs))
            tpk = max(4, int(round(patchs.shape[1] * res_p[k] / res)))
            im = cv2.resize(patchs[k], (tpk, tpk), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
            im = np.rot90(im, rng.integers(0, 4))
            if rng.random() < 0.5:
                im = im[:, ::-1]
            hwk = hw if tpk == tp else np.outer(np.hanning(tpk + 2)[1:-1], np.hanning(tpk + 2)[1:-1]).astype(np.float32) + 1e-3
            ya, xa = max(0, y), max(0, x)
            yb, xb = min(n, y + tpk), min(n, x + tpk)
            if yb <= ya or xb <= xa:
                continue
            sl = (slice(ya - y, yb - y), slice(xa - x, xb - x))
            acc[ya:yb, xa:xb] += im[sl] * hwk[sl][..., None]
            poids[ya:yb, xa:xb] += hwk[sl]
    return acc / np.maximum(poids, 1e-6)[..., None]


def fond(rng, fonds, res, n, p):
    """Sol réel : mélange herbe / sol(+mixte, ombre) par un champ lissé de longueur de corrélation ℓ."""
    # cohérence spatiale : les fenêtres d'une scène viennent de quelques tuiles CAL tirées au hasard
    tu = np.unique(fonds["tuile"])
    src = np.isin(fonds["tuile"], rng.choice(tu, size=int(_v(p, "fond_tuiles_sources")), replace=False))
    cl = fonds["classe"]
    P, R = fonds["patchs"], fonds["res"]
    he = (cl == "herbe") & src
    so = ((cl == "sol") | (cl == "mixte") | (cl == "ombre")) & src
    se = cl == "sec"                                   # toutes tuiles : peu de fenêtres « sec »
    if he.sum() < 5:
        he = cl == "herbe"
    if so.sum() < 5:
        so = (cl == "sol") | (cl == "mixte") | (cl == "ombre")
    th = _quilt(rng, P[he], R[he], res, n)
    ts = _quilt(rng, P[so], R[so], res, n)
    ph = float(np.clip(rng.beta(*_v(p, "beta_part_herbe")), 0.02, 0.98))
    ch = ndimage.gaussian_filter(rng.normal(size=(n, n)).astype(np.float32), _v(p, "fond_correlation_m") / res)
    seuil = np.quantile(ch, 1 - ph)
    mh = ndimage.gaussian_filter((ch > seuil).astype(np.float32), 0.1 / res)[..., None]
    out = th * mh + ts * (1 - mh)
    # effet tuile « sec » : part du sol couverte de fenêtres « sec » CAL, log-normale par tuile
    ps = min(_v(p, "sec_sol_max"), math.exp(rng.normal(_v(p, "sec_sol_log_mu"), _v(p, "sec_sol_log_sigma"))))
    if se.sum() >= 5 and ps > 1e-3:
        tse = _quilt(rng, P[se], R[se], res, n)
        cs = ndimage.gaussian_filter(rng.normal(size=(n, n)).astype(np.float32), _v(p, "sec_sol_correlation_m") / res)
        ms = ndimage.gaussian_filter((cs > np.quantile(cs, 1 - ps)).astype(np.float32), 0.05 / res)[..., None]
        out = tse * ms + out * (1 - ms)
    return out   # BGR, comme les patchs (lus par OpenCV)


# ---------------------------------------------------------------------------
# Scène
# ---------------------------------------------------------------------------


def masque_region(g, n=N_TUILE):
    yy, xx = np.mgrid[0:n, 0:n]
    disque = (xx - g["disque_cx"]) ** 2 + (yy - g["disque_cy"]) ** 2 <= g["disque_r"] ** 2
    zone = (xx >= g["zx0"]) & (xx < g["zx1"]) & (yy >= g["zy0"]) & (yy < g["zy1"])
    return disque & zone


def scene(graine, params=None, fonds=None, retour_fin=False):
    """Une tuile simulée. Retourne un dict :
    image (BGR uint8 512 × 512, après JPEG), jpeg (octets), cm_par_px, geometrie (disque, zone),
    meres_px (N × 2, x, y), tailles_m (N), dans_region (N), rejets_px (M × 2), graine, version."""
    p, fonds = charger(params, fonds)
    rng = np.random.default_rng(graine)
    gabs = p["tuiles_cal"]["valeur"]
    g = dict(gabs[int(rng.integers(0, len(gabs)))])
    res = g["cm_par_px"] / 100.0
    S = N_TUILE * res
    M = _v(p, "marge_m")
    cote = S + 2 * M
    pts = positions_scene(rng, S, M, p)
    f_env_scene = math.exp(rng.normal(0, _v(p, "f_env_log_sigma_scene")))
    f_sec = math.exp(rng.normal(0, _v(p, "seches_log_sigma_scene")))
    s = tailles(rng, pts, _v(p, "taille_log_mu"), _v(p, "taille_log_sigma"), _v(p, "copule_rho"))
    # organes : rejets (non comptés), puis mères ; l'ordre de recouvrement est fixé par les hauteurs
    organes, rejets = [], []
    for (x, y), si in zip(pts, s):
        for _ in range(rng.poisson(_v(p, "rejets_par_mere"))):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(*_v(p, "rejet_distance_m"))
            xr, yr = x + d * math.cos(a), y + d * math.sin(a)
            organes += tirer_plant(rng, xr, yr, rng.uniform(*_v(p, "rejet_taille_m")), p, rejet=True)
            rejets.append((xr, yr))
        organes += tirer_plant(rng, x, y, si, p, f_sec=f_sec, f_env_scene=f_env_scene)
    Nf = int(round(S / RES_FINE))
    rgb = np.zeros((Nf, Nf, 3), np.float32)
    zb = np.zeros((Nf, Nf), np.float32)
    cov = np.zeros((Nf, Nf), np.float32)
    for k in rng.permutation(len(organes)):     # ordre de dessin aléatoire ; visibilité par hauteur
        peindre(organes[k], (rgb, zb, cov), rng, p)
    # ramené à la résolution de la tuile (moyenne par zone)
    a = cv2.resize(cov, (N_TUILE, N_TUILE), interpolation=cv2.INTER_AREA)
    col = cv2.resize(rgb * cov[..., None], (N_TUILE, N_TUILE), interpolation=cv2.INTER_AREA) / np.maximum(a, 1e-6)[..., None]
    zt = cv2.resize(zb, (N_TUILE, N_TUILE), interpolation=cv2.INTER_AREA)
    bg = fond(rng, fonds, res, N_TUILE, p)[..., ::-1]          # → RVB
    img = bg * (1 - a[..., None]) + col * a[..., None]
    # occultation ambiante (ombres de ciel couvert)
    r_ao = _v(p, "ao_rayon_m") / res
    hl = ndimage.maximum_filter(zt, size=max(3, int(2 * r_ao) | 1))
    hl = ndimage.gaussian_filter(hl, r_ao / 2)
    ombre = np.exp(-np.clip(hl - zt, 0, None) / _v(p, "ao_h0_m"))
    img = img * (_v(p, "ao_plancher") + (1 - _v(p, "ao_plancher")) * ombre)[..., None]
    # dégradation : PSF, gain, bruit, JPEG
    if _v(p, "psf_sigma_px") > 0:
        img = cv2.GaussianBlur(img.astype(np.float32), (0, 0), _v(p, "psf_sigma_px"))
    img = img * math.exp(rng.normal(0, _v(p, "gain_log_sigma")))
    img = img * 255.0 + rng.normal(0, _v(p, "bruit_sigma_niveaux"), img.shape)
    x0, x1 = g["disque_cx"] - g["disque_r"], g["disque_cx"] + g["disque_r"]
    y0, y1 = g["disque_cy"] - RAPPORT_PHOTO * g["disque_r"], g["disque_cy"] + RAPPORT_PHOTO * g["disque_r"]
    yy, xx = np.mgrid[0:N_TUILE, 0:N_TUILE]
    hors = (xx < x0) | (xx >= x1) | (yy < y0) | (yy >= y1)
    img[hors] = 0
    bgr = np.clip(img[..., ::-1], 0, 255).astype(np.uint8)
    ok, jp = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, int(_v(p, "jpeg_qualite"))])
    image = cv2.imdecode(jp, cv2.IMREAD_COLOR)
    # références : mères dont le centre est dans la tuile et dans la photo
    mpx = pts / res
    dedans = (mpx[:, 0] >= 0) & (mpx[:, 0] < N_TUILE) & (mpx[:, 1] >= 0) & (mpx[:, 1] < N_TUILE)
    dedans &= (mpx[:, 0] >= x0) & (mpx[:, 0] < x1) & (mpx[:, 1] >= y0) & (mpx[:, 1] < y1)
    reg = masque_region(g)
    mi = np.floor(mpx[dedans]).astype(int)
    dr = reg[mi[:, 1], mi[:, 0]]
    out = dict(image=image, jpeg=jp.tobytes(), cm_par_px=g["cm_par_px"], geometrie=g, meres_px=mpx[dedans],
               tailles_m=s[dedans], dans_region=dr, rejets_px=np.array(rejets).reshape(-1, 2) / res,
               graine=graine, version=VERSION)
    if retour_fin:
        out["couverture"] = a
    return out
