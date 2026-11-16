"""Bananier procédural pour Blender, version 2 (maillage généré par script, aucun modèle ni texture téléchargé).

Morphologie visée (bananier Cavendish adulte, Musa AAA) :
  - faux-tronc épais (diamètre 22 à 30 cm au pied, s'affinant peu), 2,2 à 3,3 m jusqu'à la couronne, fait de
    gaines foliaires emboîtées en spirale (arêtes visibles), bulbe évasé au sol, gaines extérieures sèches et
    lambeaux bruns dans le bas, taches brun-noir ;
  - couronne de 8 à 12 feuilles vivantes en spirale (divergence ~160°), pétiole court (0,3 à 0,6 m), limbe de
    1,6 à 2,3 m sur 0,5 à 0,7 m ; jeunes feuilles dressées, vieilles feuilles arquées et retombantes ;
  - limbe : nervure centrale épaisse (tube), demi-limbes qui retombent en Λ, nervures latérales obliques (~72° de
    la nervure centrale) ; la grille du limbe SUIT les nervures latérales, si bien que les déchirures (faces
    retirées entre deux rangées) passent le long des nervures, du bord vers la nervure centrale, comme sur un
    vrai bananier ; les lanières libres retombent chacune un peu ;
  - feuille cigare enroulée au centre ; feuilles sèches brunes pendantes le long du faux-tronc (« jupe ») ;
  - rejets : rejets épées (feuilles étroites dressées) et parfois un rejet « fils » de 1 à 1,6 m ;
  - régime (illustratif, sur une partie des pieds) : hampe arquée qui pend, 6 à 8 mains de doigts verts tournés
    vers le haut, rachis nu et bourgeon mâle violacé.

Formes, tailles et proportions sont des valeurs typiques de la littérature agronomique, pas des mesures de la
parcelle. Seules les positions des pieds (scène) viennent de nos données.

Utilisé par scripts/blender_scene.py. Lancé seul, rend des plants isolés pour contrôle :
    blender.exe -b --factory-startup -t 6 -P scripts/blender_bananier.py -- --out controle.png [--vue loin]
"""
import math
import sys

import bpy
import numpy as np

HAUT = np.array([0.0, 0.0, 1.0])

# matériaux (indices)
M_FEUILLE, M_TRONC, M_SECHE, M_FRUIT = 0, 1, 2, 3


# ----------------------------------------------------------------------------------------------- maillage
class Maillage:
    """Accumulateur de sommets, faces (quads ou triangles), couleurs par sommet, UV par sommet et matériau."""

    def __init__(self):
        self.v, self.c, self.f, self.uv, self.mat = [], [], [], [], []
        self.n = 0

    def ajouter(self, verts, faces, couleurs, uvs, mat):
        verts = np.asarray(verts, "float64").reshape(-1, 3)
        faces = np.asarray(faces, np.int64)
        if len(verts) == 0 or len(faces) == 0:
            return
        couleurs = np.asarray(couleurs, "float64").reshape(len(verts), -1)
        if couleurs.shape[1] == 3:
            couleurs = np.c_[couleurs, np.ones(len(verts))]
        uvs = np.asarray(uvs, "float64").reshape(-1, 2)
        self.v.append(verts)
        self.c.append(np.clip(couleurs, 0, 1))
        self.f.append(faces + self.n)
        self.uv.append(uvs[faces].reshape(-1, 2))
        self.mat.append(np.full(len(faces), mat, np.int32))
        self.n += len(verts)

    def objet(self, nom, materiaux, collection):
        V = np.concatenate(self.v)
        C = np.concatenate(self.c)
        faces = [list(map(int, fa)) for bloc in self.f for fa in bloc]
        me = bpy.data.meshes.new(nom)
        me.from_pydata(V.tolist(), [], faces)
        attr = me.color_attributes.new("couleur", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", C.astype("float32").ravel())
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", np.concatenate(self.uv).astype("float32").ravel())
        me.polygons.foreach_set("material_index", np.concatenate(self.mat))
        me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
        for m in materiaux:
            me.materials.append(m)
        me.update()
        ob = bpy.data.objects.new(nom, me)
        if collection is not None:
            collection.objects.link(ob)
        return ob


def _grille(nl, nc):
    """Faces d'une grille nl x nc (indices ligne-major), tableau (F, 4)."""
    i, j = np.meshgrid(np.arange(nl - 1), np.arange(nc - 1), indexing="ij")
    a = (i * nc + j).ravel()
    return np.c_[a, a + 1, a + nc + 1, a + nc]


def _bruit1d(n, rng, octaves=3):
    """Bruit lisse 1D (somme de sinus à phases aléatoires), valeurs ~[-1, 1], longueur n."""
    x = np.linspace(0, 1, n)
    out = np.zeros(n)
    for o in range(octaves):
        f = (o + 1) * rng.uniform(1.5, 3.5)
        out += np.sin(2 * math.pi * f * x + rng.uniform(0, 6.3)) / (o + 1)
    return out / 1.8


def _courbe(L, phi0, phi1, p, azimut, derive=0.0, n=160):
    """Courbe plane (presque) : angle d'élévation phi(s) = phi0 + (phi1 - phi0) (s/L)^p, en degrés.
    Renvoie s, positions (depuis l'origine), tangentes, côté horizontal, normale."""
    s = np.linspace(0.0, L, n)
    phi = np.radians(phi0 + (phi1 - phi0) * (s / L) ** p)
    az = azimut + derive * (s / L) ** 2
    d = np.c_[np.cos(phi) * np.cos(az), np.cos(phi) * np.sin(az), np.sin(phi)]
    ds = np.diff(s)
    pos = np.vstack([np.zeros(3), np.cumsum((d[:-1] + d[1:]) / 2 * ds[:, None], axis=0)])
    cote = np.c_[-np.sin(az), np.cos(az), np.zeros(n)]
    norm = np.cross(cote, d)
    norm /= np.linalg.norm(norm, axis=1, keepdims=True)
    return s, pos, d, cote, norm


def _interp(sq, s, arr):
    """Interpolation d'un tableau (n, 3) défini en s, aux abscisses sq (forme quelconque)."""
    sq = np.clip(sq, s[0], s[-1])
    return np.stack([np.interp(sq, s, arr[:, k]) for k in range(3)], axis=-1)


def tube(m, pts, rayons, couleur, mat, n_cotes=6, couleurs_pts=None, ferme_bout=False):
    """Tube le long d'une polyligne pts (n, 3), rayon par point. Repère de Bishop simple."""
    pts = np.asarray(pts, float)
    n = len(pts)
    t = np.gradient(pts, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    ref = np.array([0.0, 0.0, 1.0]) if abs(t[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.zeros((n, 3))
    u0 = np.cross(t[0], ref)
    u0 /= np.linalg.norm(u0)
    u[0] = u0
    for i in range(1, n):                                           # transport parallèle
        v = u[i - 1] - np.dot(u[i - 1], t[i]) * t[i]
        u[i] = v / (np.linalg.norm(v) + 1e-12)
    w = np.cross(t, u)
    a = np.linspace(0, 2 * math.pi, n_cotes + 1)
    V = (pts[:, None, :] + rayons[:, None, None] * (np.cos(a)[None, :, None] * u[:, None, :]
                                                    + np.sin(a)[None, :, None] * w[:, None, :]))
    faces = _grille(n, n_cotes + 1)
    if couleurs_pts is None:
        C = np.tile(np.asarray(couleur, float)[:3], (n * (n_cotes + 1), 1))
    else:
        C = np.repeat(np.asarray(couleurs_pts, float)[:, :3], n_cotes + 1, axis=0)
    uv = np.stack(np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n_cotes + 1), indexing="ij"), -1)
    m.ajouter(V.reshape(-1, 3), faces, C, uv.reshape(-1, 2), mat)


# ----------------------------------------------------------------------------------------------- feuille
VERT_JAUNE = np.array([0.40, 0.42, 0.10])
BRUN_SEC = np.array([0.20, 0.12, 0.05])
PAILLE = np.array([0.36, 0.27, 0.13])
NERVURE = np.array([0.36, 0.45, 0.17])


def feuille(m, base, azimut, rng, petiole=0.45, longueur=2.0, largeur=0.6, phi0=60.0, phi1=-40.0, p=1.8,
            chute=0.25, n_dech=6, prof=(0.45, 1.0), couleur=(0.08, 0.24, 0.04), jaunit=0.0, seche=0.0,
            nl=64, nc=8, mat=M_FEUILLE, froisse=0.0, roulis_deg=10.0, angle_nerv=72.0, rayon_nervure=0.024,
            derive=None, pendre=0.08, forme="oblongue"):
    """Ajoute une feuille (pétiole + nervure centrale en tube + deux demi-limbes déchirés) au maillage."""
    base = np.asarray(base, float)
    L = petiole + longueur
    derive = rng.normal(0, 0.08) if derive is None else derive
    s, P, D, C, N = _courbe(L, phi0, phi1, p, azimut, derive)
    P = P + base
    roul = math.radians(rng.normal(0, roulis_deg))                 # limbe un peu penché sur le côté
    C = C * math.cos(roul) + N * math.sin(roul)
    N = np.cross(C, D)
    N /= np.linalg.norm(N, axis=1, keepdims=True)

    # nervure centrale + pétiole : tube effilé (le pétiole est épais, la nervure s'amincit vers la pointe)
    st = np.linspace(0, L * 0.97, 40)
    r = np.where(st < petiole, rayon_nervure * (1.25 - 0.35 * st / max(petiole, 1e-3)),
                 rayon_nervure * 0.85 * (1 - (st - petiole) / longueur) ** 0.8 + 0.002)
    col_nerv = NERVURE * (1 - seche) + PAILLE * seche
    tube(m, _interp(st, s, P) - _interp(st, s, N) * r[:, None] * 0.35, r, col_nerv * rng.uniform(0.9, 1.1), mat,
         n_cotes=6)

    # limbe : rangées le long de la nervure (u), colonnes de la nervure au bord (v) ; chaque rangée suit une
    # nervure latérale oblique (elle part de la nervure centrale et rejoint le bord plus près de la pointe)
    u = np.linspace(0, 1, nl)
    v = np.linspace(0, 1, nc)
    if forme == "lanceolee":                                       # rejet épée : étroite aux deux bouts, pointue
        w = 0.5 * largeur * np.sin(np.pi * np.clip(u, 0, 1) ** 0.8) ** 0.9
    else:                                                           # adulte : oblongue, base et pointe arrondies
        w = 0.5 * largeur * np.clip(u / 0.06, 0, 1) ** 0.5 * np.clip((1 - u) / 0.13, 0, 1) ** 0.6
    w = np.maximum(w, 0.004)
    k_nerv = 1.0 / math.tan(math.radians(angle_nerv))
    sr = petiole + u * longueur
    S = sr[:, None] + v[None, :] * w[:, None] * k_nerv               # (nl, nc)
    Pq, Cq, Nq = _interp(S, s, P), _interp(S, s, C), _interp(S, s, N)
    phase = rng.uniform(0, 6.3)
    base_c = np.asarray(couleur, float)
    ton = rng.choice([0.55, 0.8, 1.0, 1.25])                       # feuille sèche plus ou moins sombre
    for sgn in (-1, 1):
        # section en Λ : la moitié retombe, légère remontée près de la nervure, bord ondulé
        z = (0.10 * v[None, :] - chute * v[None, :] ** 1.6) * w[:, None]
        z = z + 0.012 * min(1.0, largeur / 0.5) * np.sin(u[:, None] * 35 + phase + sgn) * v[None, :] ** 2
        if froisse > 0:                                             # feuille sèche : chiffonnée
            z = z + froisse * np.outer(_bruit1d(nl, rng, 4), np.ones(nc)) * v[None, :]
            z = z + froisse * 0.6 * rng.normal(0, 1, (nl, nc)) * v[None, :] ** 1.5
        X = Pq + Cq * (sgn * v[None, :] * w[:, None])[..., None] + Nq * z[..., None]
        Dq = D_interp(S, s, D)
        # déchirures le long des nervures latérales : chaque déchirure est une rangée i où le limbe est coupé du
        # bord jusqu'à la colonne j0. Le limbe est construit en lanières (grilles séparées qui partagent la
        # position de leur rangée frontière) : une déchirure a une largeur nulle et ne s'ouvre que parce que
        # les lanières voisines retombent et glissent chacune un peu différemment.
        lignes = sorted(set(rng.integers(int(0.07 * nl), nl - 3, size=n_dech).tolist())) if n_dech > 0 else []
        bords = []
        for i in lignes:
            pr = rng.uniform(*prof)
            bords.append((i, min(max(int(math.floor((1 - pr) * (nc - 1))), 1), nc - 2)))
        limites = [(0, None)] + bords + [(nl - 1, None)]
        Xs, Fs, idx = [], [], []
        n0 = 0
        for (ia, ja), (ib, jb) in zip(limites[:-1], limites[1:]):
            if ib <= ia:
                continue
            rows = np.arange(ia, ib + 1)
            Xb = X[rows].copy()
            ouv = [j for j in (ja, jb) if j is not None]
            if len(ouv) == 2 or (ouv and rng.random() < 0.5):
                vl = v[max(ouv)]                                    # la lanière n'est libre qu'au-delà des deux
                k = np.clip((v - vl) / max(1 - vl, 1e-6), 0, 1) ** 1.3
                tombe = rng.uniform(0.0, pendre) * (0.5 + chute) * (1.0 if len(ouv) == 2 else 0.4)
                lat = rng.normal(0, 0.012)
                Xb += -Nq[rows] * (tombe * k)[None, :, None] + Dq[rows] * (lat * k)[None, :, None]
            for (jt, r_loc, sens) in ((ja, 0, 1), (jb, len(rows) - 1, -1)):   # petit écart aux lèvres
                if jt is not None:
                    kt = np.clip((v - v[jt]) / max(1 - v[jt], 1e-6), 0, 1)
                    Xb[r_loc] += Dq[rows[r_loc]] * (sens * rng.uniform(0.002, 0.008) * kt)[:, None]
            Xs.append(Xb.reshape(-1, 3))
            Fs.append(_grille(len(rows), nc) + n0)
            idx.append(rows)
            n0 += len(rows) * nc
        rows_all = np.concatenate(idx)
        # couleurs : nervure plus claire, bord plus sombre, jaunissement et dessèchement des vieilles feuilles
        col = base_c[None, None, :] * (1.06 - 0.16 * v[None, :, None]) * np.ones((nl, 1, 1))
        col = col * (1 + 0.07 * _bruit1d(nl, rng, 3))[:, None, None]
        col[:, 0] = 0.55 * NERVURE + 0.45 * base_c
        if jaunit > 0:
            kj = np.clip(jaunit * (v[None, :] ** 2 * 1.3 + u[:, None] ** 3), 0, 1)[..., None]
            col = col * (1 - kj) + VERT_JAUNE * kj
        if seche > 0:
            ks = np.clip(seche * (0.4 + v[None, :] ** 1.5 + u[:, None] ** 2) * 1.2, 0, 1)[..., None]
            raies = rng.uniform(0.65, 1.35, nl) * (1 + 0.35 * _bruit1d(nl, rng, 4))   # bandes le long des nervures
            brun = BRUN_SEC * ton * raies[:, None, None] * np.ones((1, nc, 1))
            brun = brun * (1 - 0.4 * v[None, :, None]) + PAILLE * 0.4 * v[None, :, None] * (seche > 0.95)
            col = col * (1 - ks) + brun * ks
        uv = np.stack([np.repeat(sr[:, None] / L, nc, 1), 0.5 + 0.5 * sgn * np.repeat(v[None, :], nl, 0)], -1)
        m.ajouter(np.concatenate(Xs), np.concatenate(Fs), col[rows_all].reshape(-1, 3),
                  uv[rows_all].reshape(-1, 2), mat)


def D_interp(Sq, s, D):
    d = _interp(Sq, s, D)
    return d / (np.linalg.norm(d, axis=-1, keepdims=True) + 1e-12)


# ----------------------------------------------------------------------------------------------- faux-tronc
TRONC_VERT = np.array([0.16, 0.20, 0.06])
TRONC_CLAIR = np.array([0.30, 0.33, 0.12])
TRONC_BRUN = np.array([0.20, 0.13, 0.06])


def tronc(m, o, H, r_bas, r_haut, rng, n_t=40, n_z=30, n_gaines=5, brun_bas=0.45, taches=True, mat=M_TRONC):
    """Faux-tronc : gaines emboîtées en spirale (marches du rayon), bulbe évasé, bas brun et sec, taches.
    Renvoie (centre du sommet, fonction rayon(t))."""
    o = np.asarray(o, float)
    t = np.linspace(0, 1, n_z) ** 1.3                              # plus de rangées près du sol (bulbe)
    th = np.linspace(0, 2 * math.pi, n_t + 1)
    pench = rng.normal(0, 0.02, 2)
    r0 = (r_bas + (r_haut - r_bas) * t ** 0.9) * (1 + 0.55 * (1 - t) ** 12)
    torsion = rng.uniform(0.4, 1.0) * H
    ph = rng.uniform(0, 6.3)
    f = np.mod((th[None, :] - torsion * t[:, None] + ph) / (2 * math.pi / n_gaines), 1.0)
    r = r0[:, None] * (0.98 + 0.05 * f)
    cx = o[0] + pench[0] * t * H
    cy = o[1] + pench[1] * t * H
    X = cx[:, None] + r * np.cos(th)[None, :]
    Y = cy[:, None] + r * np.sin(th)[None, :]
    Z = o[2] + np.repeat((t * H)[:, None], n_t + 1, 1)
    V = np.stack([X, Y, Z], -1)
    # couleurs
    raie = 1 + 0.10 * np.sin(th * rng.integers(9, 15) + ph)[None, :]
    k_clair = np.clip(f * 1.2 - 0.2, 0, 1) * 0.35                  # le bord de chaque gaine est plus clair
    col = TRONC_VERT * (1 - k_clair[..., None]) + TRONC_CLAIR * k_clair[..., None]
    col = col * raie[..., None] * (0.9 + 0.15 * t[:, None, None])
    col = col * (1 - 0.35 * (f < 0.06))[..., None]                 # ombre sous l'arête de la gaine
    if taches:                                                      # taches brun-noir du faux-tronc
        for _ in range(int(rng.integers(6, 14))):
            zc, tc = rng.uniform(0.05, 0.9), rng.uniform(0, 2 * math.pi)
            sz, st = rng.uniform(0.02, 0.08), rng.uniform(0.15, 0.5)
            dth = np.angle(np.exp(1j * (th[None, :] - tc)))
            g = np.exp(-((t[:, None] - zc) / sz) ** 2 - (dth / st) ** 2)
            col = col * (1 - 0.6 * g[..., None]) + np.array([0.06, 0.04, 0.02]) * 0.6 * g[..., None]
    sec = np.clip((brun_bas - t) / max(brun_bas, 1e-3), 0, 1)[:, None] ** 0.8
    plaques = (np.mod(np.floor((th[None, :] - torsion * t[:, None] + ph) / (2 * math.pi / n_gaines)), n_gaines)
               < rng.integers(2, 5))
    ks = np.clip(sec * (0.55 + 0.45 * plaques), 0, 1)[..., None]
    col = col * (1 - ks) + TRONC_BRUN * (0.85 + 0.3 * rng.random((n_z, n_t + 1, 1))) * ks
    uv = np.stack(np.meshgrid(t, th / (2 * math.pi), indexing="ij"), -1)
    m.ajouter(V.reshape(-1, 3), _grille(n_z, n_t + 1), col.reshape(-1, 3), uv.reshape(-1, 2), mat)

    def rayon(tt):
        return (r_bas + (r_haut - r_bas) * tt ** 0.9) * (1 + 0.55 * (1 - tt) ** 12)

    sommet = np.array([cx[-1], cy[-1], o[2] + H])
    return sommet, rayon, pench


def lambeaux(m, o, H, rayon, pench, rng, n):
    """Gaines extérieures sèches qui se détachent du bas du faux-tronc (lanières brunes)."""
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        z0 = rng.uniform(0.25, 0.65)
        lg = rng.uniform(0.35, 0.9) * H * 0.4
        larg = rng.uniform(0.07, 0.16)
        nn = 10
        tt = np.linspace(0, 1, nn)
        zz = np.clip(z0 - tt * lg / H, 0.02, 1)
        rad = rayon(zz) + 0.01 + (tt ** 2) * rng.uniform(0.05, 0.25)
        dirr = np.array([math.cos(a), math.sin(a), 0])
        tang = np.array([-math.sin(a), math.cos(a), 0])
        c = np.asarray(o) + np.c_[pench[0] * zz * H, pench[1] * zz * H, zz * H] + rad[:, None] * dirr
        V = np.concatenate([c - tang * larg / 2, c + tang * larg / 2], 1).reshape(nn, 2, 3)
        V[:, 1] += dirr * 0.01 * rng.normal(0, 1, (nn, 1))
        col = np.tile(PAILLE * rng.uniform(0.55, 0.95), (nn * 2, 1))
        uv = np.stack(np.meshgrid(tt, [0, 1], indexing="ij"), -1)
        m.ajouter(V.reshape(-1, 3), _grille(nn, 2), col, uv.reshape(-1, 2), M_SECHE)


def cigare(m, sommet, hauteur, rayon, rng, couleur=(0.30, 0.42, 0.10)):
    """Feuille cigare : jeune feuille enroulée, dressée au centre de la couronne."""
    n = 14
    tt = np.linspace(0, 1, n)
    incl = rng.normal(0, 0.06, 2)
    pts = np.asarray(sommet) + np.c_[incl[0] * tt * hauteur, incl[1] * tt * hauteur, tt * hauteur - 0.15]
    r = rayon * (1 - tt) ** 0.7 + 0.002
    tube(m, pts, r, np.asarray(couleur) * rng.uniform(0.9, 1.1), M_FEUILLE, n_cotes=8)


# ----------------------------------------------------------------------------------------------- régime
def regime(m, sommet, az, rng, taille=1.0):
    """Régime illustratif : hampe arquée, mains de doigts verts tournés vers le haut, rachis, bourgeon mâle."""
    L = 2.1 * taille
    s, P, D, C, N = _courbe(L, 72, -90, 0.55, az, 0.0, n=120)            # hampe : monte, se recourbe, pend
    P = P + np.asarray(sommet) + np.array([0, 0, 0.05])
    # longueur de hampe nue avant la première main : là où la hampe devient presque verticale
    i_a = int(np.argmax(np.degrees(np.arcsin(np.clip(D[:, 2], -1, 1))) < -62))
    s_a = s[i_a] + 0.05
    n_mains = int(rng.integers(6, 9))
    pas = 0.095 * taille
    s_b = s_a + n_mains * pas
    s_bout = min(s_b + rng.uniform(0.35, 0.55) * taille, L - 0.02)
    # hampe et rachis
    st = np.linspace(0, s_bout, 50)
    r = np.where(st < s_a, 0.034, np.where(st < s_b, 0.028, 0.014)) * taille
    colp = np.where((st < s_b)[:, None], np.array([0.20, 0.27, 0.08]), np.array([0.16, 0.14, 0.06]))
    tube(m, _interp(st, s, P), r, None, M_FRUIT, n_cotes=7, couleurs_pts=colp)
    # mains : doigts en deux rangées sur un arc d'environ 170°, tournés vers le haut
    ang0 = rng.uniform(0, 2 * math.pi)
    for k in range(n_mains):
        sk = s_a + (k + 0.5) * pas
        ck = _interp(np.array([sk]), s, P)[0]
        dk = D_interp(np.array([sk]), s, D)[0]
        e1 = np.cross(dk, np.array([1.0, 0.3, 0.0]))
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(dk, e1)
        nd = int(rng.integers(12, 17))
        centre = ang0 + k * math.radians(137.5)
        lg = (0.25 - 0.012 * k) * taille * rng.uniform(0.93, 1.07)
        for j in range(nd):
            rangee = j % 2
            a = centre + (j / (nd - 1) - 0.5) * math.radians(170) + rangee * 0.08
            radial = math.cos(a) * e1 + math.sin(a) * e2
            radial[2] *= 0.3
            radial /= np.linalg.norm(radial)
            depart = ck + radial * (0.04 + 0.03 * rangee) * taille + HAUT * (0.02 * rangee)
            tt = np.linspace(0, 1, 7)
            angle = np.radians(5 + 80 * tt ** 1.2 + rng.normal(0, 5))           # doigt courbé vers le haut
            dirs = np.cos(angle)[:, None] * radial + np.sin(angle)[:, None] * HAUT
            pts = depart + np.vstack([np.zeros(3), np.cumsum((dirs[:-1] + dirs[1:]) / 2 * lg / 6, axis=0)])
            rr = 0.021 * taille * np.sin(np.pi * (0.06 + 0.86 * tt)) ** 0.45
            rr[-1] = 0.004 * taille
            vert = np.array([0.17, 0.30, 0.05]) * rng.uniform(0.9, 1.1)
            colf = np.tile(vert, (7, 1))
            colf[-1] = (0.10, 0.08, 0.04)                                       # pointe sombre
            tube(m, pts, rr, None, M_FRUIT, n_cotes=5, couleurs_pts=colf)
    # bourgeon mâle : goutte violacée pointée vers le bas, au bout du rachis
    cb = _interp(np.array([s_bout]), s, P)[0]
    db = D_interp(np.array([s_bout]), s, D)[0]
    lb = rng.uniform(0.22, 0.3) * taille
    tt = np.linspace(0, 1, 12)
    pts = cb + db[None, :] * (tt * lb)[:, None]
    rr = 0.075 * taille * np.sin(np.pi * np.clip(0.12 + tt * 0.95, 0, 1) ** 0.75) ** 0.8 + 0.002
    colb = np.tile(np.array([0.24, 0.035, 0.06]), (12, 1)) * (1 - 0.3 * tt[:, None])
    tube(m, pts, rr, None, M_FRUIT, n_cotes=10, couleurs_pts=colb)


# ----------------------------------------------------------------------------------------------- plant
VERTS = [(0.075, 0.25, 0.040), (0.09, 0.27, 0.045), (0.10, 0.29, 0.05), (0.07, 0.22, 0.035), (0.095, 0.26, 0.035)]


def plant_mere(m, o, rng, H=2.7, n_feuilles=10, taille=1.0, avec_regime=False, n_seches=None, az_regime=None):
    """Plant mère : faux-tronc, jupe de feuilles sèches, couronne, cigare, régime éventuel."""
    o = np.asarray(o, float)
    r_bas = rng.uniform(0.13, 0.16) * taille
    r_haut = r_bas * rng.uniform(0.62, 0.72)
    sommet, rayon, pench = tronc(m, o, H, r_bas, r_haut, rng)
    lambeaux(m, o, H, rayon, pench, rng, int(rng.integers(2, 6)))
    vert = np.array(VERTS[rng.integers(len(VERTS))]) * rng.uniform(0.92, 1.08, 3)
    az0 = rng.uniform(0, 2 * math.pi)
    cigare(m, sommet, rng.uniform(0.5, 0.85) * taille, 0.045 * taille, rng)
    for k in range(n_feuilles):
        age = k / max(n_feuilles - 1, 1)                           # 0 = plus jeune (centre), 1 = plus vieille
        az = az0 + k * math.radians(160) + rng.normal(0, 0.15)
        zb = sommet[2] - 0.04 * k * taille
        base = np.array([sommet[0], sommet[1], zb]) + np.array([math.cos(az), math.sin(az), 0]) * r_haut * 0.5
        longueur = rng.uniform(1.65, 2.25) * (0.82 + 0.18 * min(age * 2.5, 1)) * taille
        largeur = float(np.clip(longueur * rng.uniform(0.27, 0.33), 0.45 * taille, 0.72 * taille))
        casse = age > 0.85 and rng.random() < 0.35                 # vieille feuille au pétiole cassé, pendante
        if casse:
            phi0, phi1, p = rng.uniform(5, 25), -88, 0.35
        else:
            phi0 = 62 - 32 * age + rng.normal(0, 4)
            phi1 = 12 - 100 * age ** 0.8 + rng.normal(0, 9)
            p = rng.uniform(1.5, 2.4)
        n_dech = int((1 + 17 * age ** 1.4) * rng.uniform(0.5, 1.3)) if k > 0 else 0
        jaunit = max(0.0, age - 0.65) * 2.2 * rng.uniform(0.3, 1.0) + (0.5 if casse else 0)
        feuille(m, base, az, rng, petiole=rng.uniform(0.3, 0.6) * taille, longueur=longueur, largeur=largeur,
                phi0=phi0, phi1=phi1, p=p, chute=rng.uniform(0.12, 0.28) + 0.25 * age, n_dech=n_dech,
                couleur=vert * (1.12 - 0.22 * age) + np.array([0.04, 0.05, 0.0]) * (age < 0.15),
                jaunit=jaunit, seche=0.25 * casse, rayon_nervure=0.024 * taille, pendre=0.04 + 0.12 * age)
    # jupe : feuilles mortes brunes pendues le long du faux-tronc
    n_seches = int(rng.integers(3, 7)) if n_seches is None else n_seches
    for _ in range(n_seches):
        az = rng.uniform(0, 2 * math.pi)
        zb = sommet[2] - rng.uniform(0.05, 0.55) * taille
        base = np.array([sommet[0], sommet[1], zb]) + np.array([math.cos(az), math.sin(az), 0]) * r_haut * 0.9
        lg = min(rng.uniform(1.1, 1.9) * taille, zb - 0.25)
        if lg < 0.4:
            continue
        feuille(m, base, az, rng, petiole=rng.uniform(0.04, 0.12) * taille, longueur=lg,
                largeur=rng.uniform(0.18, 0.34) * taille, phi0=rng.uniform(5, 35), phi1=-89,
                p=rng.uniform(0.15, 0.3), chute=rng.uniform(0.9, 1.4), n_dech=int(rng.integers(2, 7)),
                couleur=BRUN_SEC, seche=1.0, nl=30, nc=5, mat=M_SECHE, froisse=0.06, rayon_nervure=0.012,
                roulis_deg=25, pendre=0.06)
    if avec_regime:
        regime(m, sommet, (az0 + math.radians(80) + rng.normal(0, 0.3)) if az_regime is None else az_regime, rng, taille)
    return sommet


def rejet_epee(m, o, rng, taille=0.6):
    """Rejet épée : pseudo-tronc nettement conique (large à la base, pointu en haut, taché de brun-rouge),
    feuilles lancéolées étroites, dressées, qui partent du haut du cône et s'écartent un peu en éventail."""
    H = taille * rng.uniform(0.45, 0.8)
    r_bas = 0.06 * taille + rng.uniform(0.03, 0.05)
    sommet, _, _ = tronc(m, o, H, r_bas, r_bas * 0.22, rng, n_t=14, n_z=10, n_gaines=3, brun_bas=0.08, taches=True)
    vert = np.array(VERTS[rng.integers(len(VERTS))]) * rng.uniform(1.0, 1.2)
    az0 = rng.uniform(0, 2 * math.pi)
    n = int(rng.integers(3, 6))
    for k in range(n):
        age = k / max(n - 1, 1)
        lg = taille * rng.uniform(0.55, 0.95) * (1.1 - 0.3 * age)
        zb = sommet[2] - H * (0.08 + 0.3 * age)                    # les plus vieilles sortent plus bas sur le cône
        feuille(m, np.array([sommet[0], sommet[1], zb]), az0 + k * math.radians(150), rng, petiole=0.03 * taille,
                longueur=lg, largeur=lg * rng.uniform(0.10, 0.16), phi0=rng.uniform(72, 86) - 12 * age,
                phi1=rng.uniform(45, 70) - 45 * age, p=1.6, chute=0.25, n_dech=0, couleur=vert * (1.1 - 0.15 * age),
                nl=18, nc=4, rayon_nervure=0.006, roulis_deg=8, forme="lanceolee")


def rejet_fils(m, o, rng):
    """Rejet « fils » (successeur), 1 à 1,6 m : un petit bananier à feuilles déjà larges."""
    H = rng.uniform(0.6, 1.0)
    sommet, _, _ = tronc(m, o, H, rng.uniform(0.09, 0.11), 0.07, rng, n_t=24, n_z=14, brun_bas=0.3)
    vert = np.array(VERTS[rng.integers(len(VERTS))]) * 1.1
    az0 = rng.uniform(0, 2 * math.pi)
    n = int(rng.integers(5, 8))
    cigare(m, sommet, 0.35, 0.025, rng)
    for k in range(n):
        age = k / max(n - 1, 1)
        lg = rng.uniform(1.0, 1.5)
        feuille(m, sommet - np.array([0, 0, 0.03 * k]), az0 + k * math.radians(160), rng, petiole=0.2,
                longueur=lg, largeur=lg * rng.uniform(0.28, 0.34), phi0=80 - 35 * age,
                phi1=45 - 110 * age + rng.normal(0, 8), p=1.8, chute=0.2 + 0.2 * age,
                n_dech=int(10 * age ** 1.5 * rng.uniform(0.5, 1.2)), couleur=vert * (1.1 - 0.2 * age),
                nl=36, nc=6, rayon_nervure=0.013, jaunit=max(0, age - 0.7) * 2)


def plant_et_rejets(m, o, rng, H=2.7, n_feuilles=10, taille=1.0, n_epees=2, fils=False, avec_regime=False,
                    azimut_rejets=None, az_regime=None):
    """Plant mère + rejets (illustratifs). Les rejets sont à 0,3 à 0,6 m du pied mère."""
    o = np.asarray(o, float)
    plant_mere(m, o, rng, H, n_feuilles, taille, avec_regime, az_regime=az_regime)
    azs = list(azimut_rejets) if azimut_rejets is not None else list(rng.uniform(0, 2 * math.pi, n_epees + 1))
    for r in range(n_epees):
        a = azs[r % len(azs)]
        d = rng.uniform(0.3, 0.55) * taille
        rejet_epee(m, o + np.array([math.cos(a), math.sin(a), 0]) * d, rng, taille=rng.uniform(0.45, 0.9))
    if fils:
        a = azs[-1] + math.pi * 0.8
        d = rng.uniform(0.35, 0.5) * taille
        rejet_fils(m, o + np.array([math.cos(a), math.sin(a), 0]) * d, rng)


# ----------------------------------------------------------------------------------------------- matériaux
def _noeud(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items():
        n.inputs[k].default_value = v
    return n


def _mix_rgb(nt, a, b, fac, mode="MIX"):
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = mode
    if isinstance(fac, (int, float)):
        mx.inputs["Factor"].default_value = fac
    else:
        nt.links.new(fac, mx.inputs["Factor"])
    for entree, val in ((6, a), (7, b)):
        if isinstance(val, (tuple, list)):
            mx.inputs[entree].default_value = val
        else:
            nt.links.new(val, mx.inputs[entree])
    return mx.outputs[2]


def materiaux():
    """Feuille, faux-tronc, feuille sèche, fruit. Couleur des sommets (attribut « couleur »).
    Feuille : dessous plus pâle (glauque), translucide, nervures latérales en relief (bandes le long de U), et
    couleur « santé » : mélange avec la couleur de l'objet (Object Info), dosée par le nœud « fac_sante »
    (0 = rendu naturel). Seules les feuilles vivantes reçoivent la teinte."""
    res = []
    for nom, rugo, transl in (("feuille", 0.45, 0.22), ("tronc", 0.65, 0.0), ("feuille_seche", 0.85, 0.08),
                              ("fruit", 0.38, 0.0)):
        ma = bpy.data.materials.new(nom)
        ma.use_nodes = True
        nt = ma.node_tree
        nt.nodes.clear()
        sortie = nt.nodes.new("ShaderNodeOutputMaterial")
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = "couleur"
        couleur = attr.outputs["Color"]
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UVMap"
        p = _noeud(nt, "ShaderNodeBsdfPrincipled", Roughness=rugo)
        p.inputs["Specular IOR Level"].default_value = 0.4 if nom != "fruit" else 0.5
        if nom == "feuille":
            # variation douce de teinte le long de la feuille
            bruit = _noeud(nt, "ShaderNodeTexNoise", Scale=6.0, Detail=3.0)
            nt.links.new(uvn.outputs["UV"], bruit.inputs["Vector"])
            couleur = _mix_rgb(nt, couleur, (0.85, 0.95, 0.8, 1), 0.0)
            couleur = _mix_rgb(nt, couleur, bruit.outputs["Color"], 0.08, "OVERLAY")
            info = nt.nodes.new("ShaderNodeObjectInfo")
            fac = nt.nodes.new("ShaderNodeValue")
            fac.name = fac.label = "fac_sante"
            fac.outputs[0].default_value = 0.0
            couleur = _mix_rgb(nt, couleur, info.outputs["Color"], fac.outputs[0])
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            dessous = _mix_rgb(nt, couleur, (1.25, 1.3, 1.2, 1), 1.0, "MULTIPLY")
            couleur = _mix_rgb(nt, couleur, dessous, geo.outputs["Backfacing"])
        nt.links.new(couleur, p.inputs["Base Color"])
        surface = p.outputs[0]
        if transl > 0:
            tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
            nt.links.new(_mix_rgb(nt, couleur, (1.1, 1.3, 0.55, 1), 1.0, "MULTIPLY"), tr.inputs["Color"])
            ms = nt.nodes.new("ShaderNodeMixShader")
            ms.inputs[0].default_value = transl
            nt.links.new(p.outputs[0], ms.inputs[1])
            nt.links.new(tr.outputs[0], ms.inputs[2])
            surface = ms.outputs[0]
        nt.links.new(surface, sortie.inputs["Surface"])
        if nom in ("feuille", "feuille_seche", "tronc"):
            # feuilles : nervures latérales (bandes le long de U, U = position le long de la nervure centrale) ;
            # tronc : fibres verticales (bandes le long de V = angle autour du tronc)
            onde = nt.nodes.new("ShaderNodeTexWave")
            onde.wave_type = "BANDS"
            onde.bands_direction = "X" if nom != "tronc" else "Y"
            onde.inputs["Scale"].default_value = 140.0 if nom != "tronc" else 90.0
            onde.inputs["Distortion"].default_value = 2.0
            onde.inputs["Detail"].default_value = 1.0
            nt.links.new(uvn.outputs["UV"], onde.inputs["Vector"])
            bump = _noeud(nt, "ShaderNodeBump", Strength=0.12 if nom == "feuille" else 0.25)
            nt.links.new(onde.outputs["Fac"], bump.inputs["Height"])
            nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
        res.append(ma)
    return res


def regler_sante(materiaux_liste, facteur):
    for ma in materiaux_liste:
        n = ma.node_tree.nodes.get("fac_sante")
        if n is not None:
            n.outputs[0].default_value = facteur


# ----------------------------------------------------------------------------------------------- caméra
def viser(objet, cible):
    """Oriente une caméra (ou une lampe) vers un point."""
    from mathutils import Vector
    direction = Vector(cible) - objet.location
    objet.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


# ----------------------------------------------------------------------------------------------- contrôle seul
def _controle(chemin, vue="proche", graine=7):
    import time
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    mats = materiaux()
    t0 = time.time()
    m = Maillage()
    rng = np.random.default_rng(graine)
    plant_et_rejets(m, (0, 0, 0), rng, H=2.8, n_feuilles=11, n_epees=2, fils=True, avec_regime=True,
                    azimut_rejets=[math.radians(a) for a in (-100, -60, 200)])
    m2 = Maillage()
    plant_et_rejets(m2, (3.2, 2.2, 0), np.random.default_rng(graine + 1), H=2.5, n_feuilles=9, n_epees=1)
    ob = m.objet("bananier", mats, sc.collection)
    ob2 = m2.objet("bananier2", mats, sc.collection)
    print("sommets", len(ob.data.vertices), len(ob2.data.vertices), f"construits en {time.time() - t0:.1f} s")
    sol = bpy.data.meshes.new("sol")
    sol.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    so = bpy.data.objects.new("sol", sol)
    sc.collection.objects.link(so)
    ms = bpy.data.materials.new("sol")
    ms.use_nodes = True
    ms.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.16, 0.09, 0.05, 1)
    sol.materials.append(ms)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    if vue == "loin":
        cam.location = (7, -7, 6)
        viser(cam, (1.4, 0.9, 1.8))
    elif vue == "dessus":
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 9
        cam.location = (1.6, 1.1, 30)
        cam.rotation_euler = (0, 0, 0)
    else:
        cam.location = (2.0, -6.5, 1.6)
        viser(cam, (0.5, 0, 2.0))
    cam.data.lens = 26
    sc.camera = cam
    soleil = bpy.data.objects.new("soleil", bpy.data.lights.new("soleil", "SUN"))
    soleil.data.energy = 4
    soleil.rotation_euler = (math.radians(40), 0, math.radians(30))
    sc.collection.objects.link(soleil)
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.45, 0.6, 0.85, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    sc.world = w
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.render.resolution_x, sc.render.resolution_y = 960, 640
    sc.render.filepath = chemin
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--out" in argv:
        _controle(argv[argv.index("--out") + 1], argv[argv.index("--vue") + 1] if "--vue" in argv else "proche",
                  int(argv[argv.index("--graine") + 1]) if "--graine" in argv else 7)
