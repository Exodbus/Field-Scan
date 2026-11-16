"""Décor procédural de la parcelle (Blender) : terrain jusqu'à l'horizon, sol de bananeraie, herbe, feuilles mortes
au sol, lisière d'arbres, ciel physique et brume de distance. Tout est généré par script : aucune texture, HDRI,
modèle ni extension téléchargés.

Rien de ce module ne vient des données : c'est du décor. Les seules données réelles de la scène sont les positions
des pieds (détecteur v5) et la teinte « santé » (ExG de la chaîne), gérées par scripts/blender_scene.py.

Repère : origine au centre de la mosaïque, x vers l'est, y vers le nord, z vers le haut (mètres).
"""
import math

import bpy
import numpy as np

import blender_bananier as bb

BRUME = (0.56, 0.62, 0.70, 1.0)     # couleur de la brume (proche de l'horizon du ciel physique)
BUISSONS = []
DENSITE_LISIERE = 1.0               # part des feuilles des arbres de lisière et des haies (allégée pour le survol)
D_BRUME = 2500.0                    # distance caractéristique de la brume (m) ; très grande = pas de brume


# ----------------------------------------------------------------------------------------------- outils
def maillage_rapide(nom, V, F, couleurs=None, uv_coins=None, materiaux=(), collection=None, lisse=True):
    """Crée un objet maillage à partir de tableaux numpy (faces de taille constante), sans passer par des listes
    Python (rapide pour des centaines de milliers de sommets)."""
    V = np.asarray(V, "float32").reshape(-1, 3)
    F = np.asarray(F, np.int32)
    k = F.shape[1]
    me = bpy.data.meshes.new(nom)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(F.size)
    me.loops.foreach_set("vertex_index", F.ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", np.arange(0, F.size, k, dtype=np.int32))
    me.update(calc_edges=True)
    if couleurs is not None:
        c = np.asarray(couleurs, "float32").reshape(len(V), -1)
        if c.shape[1] == 3:
            c = np.c_[c, np.ones(len(V), "float32")]
        a = me.color_attributes.new("couleur", "FLOAT_COLOR", "POINT")
        a.data.foreach_set("color", c.ravel())
    if uv_coins is not None:
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", np.asarray(uv_coins, "float32").ravel())
    me.polygons.foreach_set("use_smooth", np.full(len(F), lisse))
    for m in materiaux:
        me.materials.append(m)
    me.validate()
    ob = bpy.data.objects.new(nom, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def bruit2d(x, y, graine, octaves=5, echelle=1.0):
    """Bruit lisse 2D (somme de sinusoïdes à directions et phases aléatoires), ~[-1, 1]."""
    r = np.random.default_rng(graine)
    out = np.zeros_like(x, dtype="float64")
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        for _ in range(3):
            a = r.uniform(0, math.pi)
            f = echelle * (2 ** o) * r.uniform(0.7, 1.3)
            out += amp * np.sin(f * (x * math.cos(a) + y * math.sin(a)) + r.uniform(0, 6.3))
            tot += amp
        amp *= 0.5
    return out / tot * 1.7


def _n(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items():
        n.inputs[k].default_value = v
    return n


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, val in enumerate((a, b)):
        if val is None:
            continue
        if isinstance(val, (int, float)):
            n.inputs[i].default_value = val
        else:
            nt.links.new(val, n.inputs[i])
    return n.outputs[0]


def _mix(nt, a, b, fac, mode="MIX"):
    return bb._mix_rgb(nt, a, b, fac, mode)


def _rampe(nt, fac, couleurs, positions=None):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    positions = positions or list(np.linspace(0, 1, len(couleurs)))
    while len(els) < len(couleurs):
        els.new(0.5)
    for e, c, p in zip(els, couleurs, positions):
        e.position = p
        e.color = (*c, 1) if len(c) == 3 else c
    nt.links.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]


def _seuil(nt, fac, bas, haut):
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.interpolation_type = "SMOOTHSTEP"
    nt.links.new(fac, mr.inputs["Value"])
    mr.inputs["From Min"].default_value = bas
    mr.inputs["From Max"].default_value = haut
    return mr.outputs["Result"]


def brume(nt, surface, distance_caracteristique=None, couleur=BRUME, force=0.7):
    """Perspective aérienne : mélange la surface avec une émission couleur de brume selon la distance à la
    caméra, fac = 1 - exp(-d / D). Approximation peu coûteuse d'un volume atmosphérique."""
    distance_caracteristique = distance_caracteristique or D_BRUME
    cam = nt.nodes.new("ShaderNodeCameraData")
    e = _math(nt, "MULTIPLY", cam.outputs["View Distance"], -1.0 / distance_caracteristique)
    e = _math(nt, "EXPONENT", e)
    fac = _math(nt, "SUBTRACT", 1.0, e, clamp=True)
    em = _n(nt, "ShaderNodeEmission", Strength=force)
    em.inputs["Color"].default_value = couleur
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac, ms.inputs[0])
    nt.links.new(surface, ms.inputs[1])
    nt.links.new(em.outputs[0], ms.inputs[2])
    return ms.outputs[0]


# ----------------------------------------------------------------------------------------------- terrain
def materiau_terrain(demi_cote, force_brume=1.0):
    """Sol : dans l'emprise de la mosaïque, terre brun-rouge, paillis de feuilles mortes et herbe éparse ;
    autour, prairie ; sur les collines lointaines, couvert forestier. Transition bruitée au bord de l'emprise."""
    ma = bpy.data.materials.new("terrain")
    ma.use_nodes = True
    nt = ma.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    pos = tc.outputs["Object"]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(pos, sep.inputs[0])
    # masque de l'emprise (carré de demi-côté demi_cote + 1,2 m, bord bruité)
    bord_bruit = _n(nt, "ShaderNodeTexNoise", Scale=0.35, Detail=4.0)
    nt.links.new(pos, bord_bruit.inputs["Vector"])
    d = _math(nt, "MAXIMUM", _math(nt, "ABSOLUTE", sep.outputs[0]), _math(nt, "ABSOLUTE", sep.outputs[1]))
    d = _math(nt, "ADD", d, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", bord_bruit.outputs["Fac"], 0.5), 6.0))
    dedans = _math(nt, "SUBTRACT", 1.0, _seuil(nt, d, demi_cote + 0.5, demi_cote + 2.0))

    # terre : brun-rouge, taches plus sombres (humides)
    b1 = _n(nt, "ShaderNodeTexNoise", Scale=0.9, Detail=8.0, Roughness=0.6)
    nt.links.new(pos, b1.inputs["Vector"])
    terre = _rampe(nt, b1.outputs["Fac"], [(0.075, 0.034, 0.017), (0.14, 0.066, 0.033), (0.21, 0.105, 0.052)],
                   [0.3, 0.5, 0.75])
    # paillis : fragments de feuilles mortes allongés (Voronoï étiré, deux orientations)
    paillis_cols = []
    # coordonnées déformées par un bruit : fragments aux contours irréguliers (pas de facettes polygonales)
    deform = _n(nt, "ShaderNodeTexNoise", Scale=2.2, Detail=5.0)
    nt.links.new(pos, deform.inputs["Vector"])
    ech = nt.nodes.new("ShaderNodeVectorMath")
    ech.operation = "SCALE"
    ech.inputs["Scale"].default_value = 0.45
    nt.links.new(deform.outputs["Color"], ech.inputs[0])
    pos_d = nt.nodes.new("ShaderNodeVectorMath")
    pos_d.operation = "ADD"
    nt.links.new(pos, pos_d.inputs[0])
    nt.links.new(ech.outputs["Vector"], pos_d.inputs[1])
    for k, (rot, sc) in enumerate(((0.5, (9.0, 2.0, 1.0)), (-0.9, (8.0, 1.7, 1.0)))):
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, rot)
        mp.inputs["Scale"].default_value = sc
        nt.links.new(pos_d.outputs["Vector"], mp.inputs["Vector"])
        vo = _n(nt, "ShaderNodeTexVoronoi", Scale=1.0, Randomness=1.0)
        nt.links.new(mp.outputs[0], vo.inputs["Vector"])
        paillis_cols.append((vo.outputs["Color"], vo.outputs["Distance"]))
    sep_c = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(paillis_cols[0][0], sep_c.inputs[0])
    sep_c2 = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(paillis_cols[1][0], sep_c2.inputs[0])
    teinte_p = _math(nt, "ADD", _math(nt, "MULTIPLY", sep_c.outputs[0], 0.5), _math(nt, "MULTIPLY", sep_c2.outputs[1], 0.5))
    paillis = _rampe(nt, teinte_p, [(0.08, 0.045, 0.02), (0.16, 0.095, 0.04), (0.26, 0.18, 0.085), (0.21, 0.16, 0.075)],
                     [0.1, 0.4, 0.7, 0.95])
    bp = _n(nt, "ShaderNodeTexNoise", Scale=0.45, Detail=5.0)
    nt.links.new(pos, bp.inputs["Vector"])
    couv_paillis = _seuil(nt, bp.outputs["Fac"], 0.44, 0.56)
    # herbe éparse dans la parcelle
    bh = _n(nt, "ShaderNodeTexNoise", Scale=0.6, Detail=6.0)
    nt.links.new(pos, bh.inputs["Vector"])
    couv_herbe = _math(nt, "MULTIPLY", _seuil(nt, bh.outputs["Fac"], 0.60, 0.70), 0.7)
    bf = _n(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=2.0)
    nt.links.new(pos, bf.inputs["Vector"])
    herbe = _rampe(nt, bf.outputs["Fac"], [(0.05, 0.08, 0.02), (0.10, 0.14, 0.04), (0.17, 0.17, 0.07)])
    dans = _mix(nt, terre, paillis, couv_paillis)
    dans = _mix(nt, dans, herbe, couv_herbe)
    grain = _n(nt, "ShaderNodeTexNoise", Scale=30.0, Detail=6.0)
    nt.links.new(pos, grain.inputs["Vector"])
    dans = _mix(nt, dans, grain.outputs["Color"], 0.12, "OVERLAY")
    # ombre entre les fragments de paillis
    bords = _seuil(nt, paillis_cols[0][1], 0.0, 0.12)
    dans = _mix(nt, dans, _mix(nt, dans, (0.4, 0.4, 0.4, 1), 1.0, "MULTIPLY"),
                _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, bords), couv_paillis))
    # prairie autour, plus sèche par grandes plaques ; forêt sur les collines (au-delà de ~200 m)
    bg = _n(nt, "ShaderNodeTexNoise", Scale=0.04, Detail=6.0)
    nt.links.new(pos, bg.inputs["Vector"])
    prairie = _rampe(nt, bg.outputs["Fac"], [(0.04, 0.08, 0.018), (0.08, 0.13, 0.028), (0.15, 0.15, 0.05), (0.20, 0.17, 0.07)],
                     [0.25, 0.5, 0.72, 0.9])
    bm = _n(nt, "ShaderNodeTexNoise", Scale=0.35, Detail=8.0, Roughness=0.65)
    nt.links.new(pos, bm.inputs["Vector"])
    prairie = _mix(nt, prairie, bm.outputs["Color"], 0.35, "OVERLAY")    # touffes et plaques moyennes
    prairie = _mix(nt, prairie, bf.outputs["Color"], 0.12, "OVERLAY")
    # grandes plaques de teinte (parcelles fauchées, sèches ou plus vertes)
    bpl = _n(nt, "ShaderNodeTexVoronoi", Scale=0.012, Randomness=1.0)
    nt.links.new(pos_d.outputs["Vector"], bpl.inputs["Vector"])
    teinte_pl = _rampe(nt, bpl.outputs["Color"], [(0.75, 0.85, 0.6), (1.0, 1.0, 1.0), (1.35, 1.15, 0.85), (0.85, 1.05, 0.75)])
    prairie = _mix(nt, prairie, teinte_pl, 1.0, "MULTIPLY")
    # touffes d'herbe (~1 m) : centre clair, pourtour sombre ; plaques sèches jaunies
    vt = _n(nt, "ShaderNodeTexVoronoi", Scale=1.1, Randomness=1.0)
    nt.links.new(pos_d.outputs["Vector"], vt.inputs["Vector"])
    touffe = _seuil(nt, vt.outputs["Distance"], 0.15, 0.6)
    prairie = _mix(nt, prairie, _mix(nt, prairie, (0.45, 0.5, 0.4, 1), 1.0, "MULTIPLY"), _math(nt, "MULTIPLY", touffe, 0.55))
    bsec = _n(nt, "ShaderNodeTexNoise", Scale=0.12, Detail=6.0, Roughness=0.7)
    nt.links.new(pos, bsec.inputs["Vector"])
    prairie = _mix(nt, prairie, (0.20, 0.17, 0.07, 1), _math(nt, "MULTIPLY", _seuil(nt, bsec.outputs["Fac"], 0.58, 0.7), 0.6))
    bfo =_n(nt, "ShaderNodeTexNoise", Scale=0.08, Detail=8.0, Roughness=0.7)
    nt.links.new(pos, bfo.inputs["Vector"])
    foret = _rampe(nt, bfo.outputs["Fac"], [(0.02, 0.05, 0.015), (0.05, 0.10, 0.03), (0.08, 0.13, 0.04)])
    r_xy = _math(nt, "SQRT", _math(nt, "ADD", _math(nt, "POWER", sep.outputs[0], 2.0), _math(nt, "POWER", sep.outputs[1], 2.0)))
    bfm = _n(nt, "ShaderNodeTexNoise", Scale=0.004, Detail=3.0)
    nt.links.new(pos, bfm.inputs["Vector"])
    couv_foret = _math(nt, "MULTIPLY", _seuil(nt, r_xy, 180.0, 420.0), _seuil(nt, bfm.outputs["Fac"], 0.38, 0.5))
    dehors = _mix(nt, prairie, foret, couv_foret)
    couleur = _mix(nt, dehors, dans, dedans)
    p = _n(nt, "ShaderNodeBsdfPrincipled", Roughness=0.92)
    p.inputs["Specular IOR Level"].default_value = 0.25
    nt.links.new(couleur, p.inputs["Base Color"])
    # relief fin : mottes et fragments
    bb_ = _n(nt, "ShaderNodeTexNoise", Scale=14.0, Detail=8.0)
    nt.links.new(pos, bb_.inputs["Vector"])
    haut = _math(nt, "ADD", bb_.outputs["Fac"], _math(nt, "MULTIPLY", paillis_cols[0][1], 0.6))
    haut = _math(nt, "SUBTRACT", haut, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", touffe, 1.5),
                                             _math(nt, "SUBTRACT", 1.0, dedans)))
    bump = _n(nt, "ShaderNodeBump", Strength=0.45, Distance=0.06)
    nt.links.new(haut, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    nt.links.new(brume(nt, p.outputs[0], force=force_brume), sortie.inputs["Surface"])
    return ma


def terrain(demi_cote, rng, rayon=3500.0, force_brume=1.0):
    """Terrain : plat sur la parcelle et ses abords (jusqu'à ~90 m), collines douces au-delà, reliefs plus marqués
    vers l'horizon. Grille plus fine au centre (pas croissant avec la distance)."""
    n = 260
    t = np.linspace(-1, 1, n)
    g = np.sign(t) * np.abs(t) ** 2.2 * rayon                       # pas fin au centre, large au bord
    X, Y = np.meshgrid(g, g)
    r = np.hypot(X, Y)
    k1 = np.clip((r - 90) / 220, 0, 1) ** 2
    k2 = np.clip((r - 700) / 1600, 0, 1) ** 1.5
    Z = k1 * 9 * bruit2d(X, Y, 11, 4, 1 / 160) + k2 * 120 * (0.6 + 0.4 * bruit2d(X, Y, 12, 4, 1 / 900))
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    F = bb._grille(n, n)
    ob = maillage_rapide("terrain", V, F, materiaux=[materiau_terrain(demi_cote, force_brume)])
    return ob


# ----------------------------------------------------------------------------------------------- herbe
def materiau_herbe(force_brume=1.0):
    ma = bpy.data.materials.new("herbe")
    ma.use_nodes = True
    nt = ma.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "couleur"
    p = _n(nt, "ShaderNodeBsdfPrincipled", Roughness=0.55)
    nt.links.new(attr.outputs["Color"], p.inputs["Base Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(_mix(nt, attr.outputs["Color"], (1.2, 1.4, 0.6, 1), 1.0, "MULTIPLY"), tr.inputs["Color"])
    ms = nt.nodes.new("ShaderNodeMixShader")
    ms.inputs[0].default_value = 0.25
    nt.links.new(p.outputs[0], ms.inputs[1])
    nt.links.new(tr.outputs[0], ms.inputs[2])
    nt.links.new(brume(nt, ms.outputs[0], force=force_brume), sortie.inputs["Surface"])
    return ma


def herbe(points, rng, mat, hauteur=(0.12, 0.4), brins=(4, 9), nom="herbe", couleurs=None):
    """Touffes d'herbe : chaque brin est une lanière effilée et courbée (3 segments)."""
    V, F, C = [], [], []
    n0 = 0
    couleurs = couleurs or [(0.07, 0.14, 0.03), (0.12, 0.20, 0.05), (0.20, 0.22, 0.07), (0.25, 0.22, 0.10)]
    pal = np.array(couleurs)
    nb = rng.integers(brins[0], brins[1] + 1, len(points))
    tot = int(nb.sum())
    base = np.repeat(np.asarray(points, float), nb, axis=0) + np.c_[rng.normal(0, 0.035, (tot, 2)), np.zeros(tot)]
    h = rng.uniform(*hauteur, tot) * np.repeat(rng.uniform(0.6, 1.2, len(points)), nb)
    az = rng.uniform(0, 2 * math.pi, tot)
    pench = rng.uniform(0.15, 0.9, tot)                            # courbure du brin
    larg = rng.uniform(0.006, 0.012, tot)
    lv = np.linspace(0, 1, 4)
    dirh = np.c_[np.cos(az), np.sin(az), np.zeros(tot)]
    perp = np.c_[-np.sin(az), np.cos(az), np.zeros(tot)]
    # position le long du brin : monte puis se courbe
    off_h = (pench[:, None] * h[:, None] * lv[None, :] ** 2)       # (tot, 4)
    off_z = h[:, None] * (lv[None, :] - 0.35 * pench[:, None] * lv[None, :] ** 2.5)
    centre = base[:, None, :] + dirh[:, None, :] * off_h[..., None] + np.array([0, 0, 1.0]) * off_z[..., None]
    w = larg[:, None] * (1 - lv[None, :]) + 0.0008
    gauche = centre - perp[:, None, :] * w[..., None]
    droite = centre + perp[:, None, :] * w[..., None]
    Vb = np.stack([gauche, droite], 2).reshape(tot, 8, 3)
    ids = np.arange(tot)[:, None] * 8
    f1 = np.array([[0, 1, 3, 2], [2, 3, 5, 4], [4, 5, 7, 6]])
    Fb = (ids[:, None, :] + f1[None]).reshape(-1, 4)
    col = pal[rng.integers(0, len(pal), tot)] * rng.uniform(0.8, 1.15, (tot, 1))
    Cb = np.repeat(col, 8, axis=0) * np.tile(np.r_[0.6, 0.6, 0.8, 0.8, 1, 1, 1.1, 1.1], tot)[:, None]
    return maillage_rapide(nom, Vb.reshape(-1, 3), Fb, couleurs=np.clip(Cb, 0, 1), materiaux=[mat])


def points_herbe(n, zone, rng, exclure=None, r_excl=0.6):
    """n points aléatoires dans le rectangle zone = (xmin, xmax, ymin, ymax), hors des disques d'exclusion."""
    pts = np.c_[rng.uniform(zone[0], zone[1], n), rng.uniform(zone[2], zone[3], n), np.zeros(n)]
    return filtrer(pts, exclure, r_excl)


def filtrer(pts, centres, r):
    """Retire les points à moins de r d'un des centres (calcul par blocs, sans scipy)."""
    if centres is None or len(centres) == 0:
        return pts
    c = np.asarray(centres)[:, :2]
    garde = np.ones(len(pts), bool)
    for i in range(0, len(pts), 4000):
        d = np.linalg.norm(pts[i:i + 4000, None, :2] - c[None], axis=2).min(1)
        garde[i:i + 4000] = d > r
    return pts[garde]


# ----------------------------------------------------------------------------------------------- litière
def litiere(centres, rng, mats, par_plant=2.0, nom="feuilles_au_sol"):
    """Feuilles mortes coupées posées au sol autour des pieds (paillis d'une bananeraie entretenue)."""
    m = bb.Maillage()
    n = int(len(centres) * par_plant)
    idx = rng.integers(0, len(centres), n)
    for i in idx:
        c = np.asarray(centres[i], float)
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0.4, 1.8)
        base = c + np.array([math.cos(a) * d, math.sin(a) * d, 0.015])
        bb.feuille(m, base, rng.uniform(0, 2 * math.pi), rng, petiole=0.05, longueur=rng.uniform(0.8, 1.8),
                   largeur=rng.uniform(0.2, 0.45), phi0=rng.uniform(-2, 4), phi1=rng.uniform(-4, 2), p=1.0,
                   chute=rng.uniform(-0.6, 0.2), n_dech=int(rng.integers(5, 14)), couleur=bb.BRUN_SEC,
                   seche=1.0, nl=18, nc=4, mat=bb.M_SECHE, froisse=0.03, rayon_nervure=0.008, roulis_deg=4,
                   pendre=0.01)
    return m.objet(nom, mats, bpy.context.scene.collection)


# ----------------------------------------------------------------------------------------------- arbres
def materiau_arbre(force_brume=1.0):
    """Feuillage : couleur des sommets (teinte propre à chaque arbre et à chaque amas), grain de feuilles
    (Voronoï fin en relief), creux assombris par l'occlusion ambiante entre les amas, un peu de translucidité."""
    ma = bpy.data.materials.new("arbre")
    ma.use_nodes = True
    nt = ma.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "couleur"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = _n(nt, "ShaderNodeTexVoronoi", Scale=7.0)
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    vo2 = _n(nt, "ShaderNodeTexVoronoi", Scale=19.0)
    nt.links.new(tc.outputs["Object"], vo2.inputs["Vector"])
    bruit = _n(nt, "ShaderNodeTexNoise", Scale=1.5, Detail=6.0)
    nt.links.new(tc.outputs["Object"], bruit.inputs["Vector"])
    couleur = _mix(nt, attr.outputs["Color"], bruit.outputs["Color"], 0.18, "OVERLAY")
    grain = _seuil(nt, vo2.outputs["Distance"], 0.25, 0.6)          # trous sombres entre les bouquets de feuilles
    couleur = _mix(nt, couleur, (0.0, 0.0, 0.0, 1), _math(nt, "MULTIPLY", grain, 0.45))
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 1.2
    ao.samples = 8
    fac_ao = _math(nt, "ADD", 0.3, _math(nt, "MULTIPLY", ao.outputs["AO"], 0.7))
    couleur = _mix(nt, couleur, (0.0, 0.0, 0.0, 1), _math(nt, "SUBTRACT", 1.0, fac_ao))
    p = _n(nt, "ShaderNodeBsdfPrincipled", Roughness=0.7)
    nt.links.new(couleur, p.inputs["Base Color"])
    feuilles = _n(nt, "ShaderNodeTexNoise", Scale=14.0, Detail=10.0, Roughness=0.75)
    nt.links.new(tc.outputs["Object"], feuilles.inputs["Vector"])
    bump = _n(nt, "ShaderNodeBump", Strength=0.7, Distance=0.12)
    nt.links.new(_math(nt, "ADD", feuilles.outputs["Fac"], _math(nt, "MULTIPLY", vo2.outputs["Distance"], 0.5)),
                 bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(_mix(nt, couleur, (1.2, 1.4, 0.6, 1), 1.0, "MULTIPLY"), tr.inputs["Color"])
    ms = nt.nodes.new("ShaderNodeMixShader")
    ms.inputs[0].default_value = 0.12
    nt.links.new(p.outputs[0], ms.inputs[1])
    nt.links.new(tr.outputs[0], ms.inputs[2])
    nt.links.new(brume(nt, ms.outputs[0], force=force_brume), sortie.inputs["Surface"])
    return ma


def materiau_ecorce(force_brume=1.0):
    ma = bpy.data.materials.new("ecorce")
    ma.use_nodes = True
    nt = ma.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "couleur"
    p = _n(nt, "ShaderNodeBsdfPrincipled", Roughness=0.9)
    p.inputs["Specular IOR Level"].default_value = 0.15
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # écorce : fissures verticales (Voronoï étiré le long du tronc), plaques plus claires ou verdâtres (lichens,
    # mousses) et grain fin ; teinte non uniforme
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (9.0, 9.0, 1.6)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    fis = _n(nt, "ShaderNodeTexVoronoi", Scale=1.0, Randomness=1.0)
    fis.feature = "DISTANCE_TO_EDGE"
    nt.links.new(mp.outputs[0], fis.inputs["Vector"])
    creux = _math(nt, "SUBTRACT", 1.0, _seuil(nt, fis.outputs["Distance"], 0.0, 0.08))
    plaques = _n(nt, "ShaderNodeTexNoise", Scale=1.2, Detail=6.0)
    nt.links.new(tc.outputs["Object"], plaques.inputs["Vector"])
    couleur = _mix(nt, attr.outputs["Color"], (0.16, 0.15, 0.12, 1), _seuil(nt, plaques.outputs["Fac"], 0.5, 0.7))
    couleur = _mix(nt, couleur, (0.07, 0.09, 0.04, 1), _math(nt, "MULTIPLY", _seuil(nt, plaques.outputs["Fac"], 0.25, 0.35), 0.0))
    mousse = _n(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=4.0)
    nt.links.new(tc.outputs["Object"], mousse.inputs["Vector"])
    couleur = _mix(nt, couleur, (0.06, 0.08, 0.035, 1), _math(nt, "MULTIPLY", _seuil(nt, mousse.outputs["Fac"], 0.58, 0.68), 0.7))
    couleur = _mix(nt, couleur, (0.0, 0.0, 0.0, 1), _math(nt, "MULTIPLY", creux, 0.6))
    grain = _n(nt, "ShaderNodeTexNoise", Scale=40.0, Detail=6.0)
    nt.links.new(tc.outputs["Object"], grain.inputs["Vector"])
    couleur = _mix(nt, couleur, grain.outputs["Color"], 0.2, "OVERLAY")
    nt.links.new(couleur, p.inputs["Base Color"])
    bump = _n(nt, "ShaderNodeBump", Strength=0.6, Distance=0.02)
    nt.links.new(_math(nt, "SUBTRACT", 1.0, creux), bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    nt.links.new(brume(nt, p.outputs[0], force=force_brume), sortie.inputs["Surface"])
    return ma


def _sphere(m, c, r, rng, couleur, n_lat=8, n_lon=14, bosses=0.18, mat=0):
    th = np.linspace(0.05, math.pi - 0.05, n_lat)
    ph = np.linspace(0, 2 * math.pi, n_lon + 1)
    T, P = np.meshgrid(th, ph, indexing="ij")
    d = np.stack([np.sin(T) * np.cos(P), np.sin(T) * np.sin(P), np.cos(T)], -1)
    ondes = np.zeros(T.shape)
    for _ in range(6):
        a = rng.normal(0, 1, 3)
        a /= np.linalg.norm(a)
        ondes += np.sin((d @ a) * rng.uniform(3, 7) + rng.uniform(0, 6.3))
    rr = r * (1 + bosses * ondes / 3) * np.where(d[..., 2] < 0, 0.7, 1.0)
    V = np.asarray(c) + d * rr[..., None]
    col = np.tile(np.asarray(couleur), (V.shape[0] * V.shape[1], 1)) * (0.7 + 0.45 * (d[..., 2].ravel()[:, None] + 1) / 2)
    m.ajouter(V.reshape(-1, 3), bb._grille(n_lat, n_lon + 1), col, np.zeros((V.shape[0] * V.shape[1], 2)), mat)


def _amas(m, c, r, rng, teinte, taille_feuille=0.35, densite=1.0):
    """Amas de feuillage : volume intérieur sombre (boule bosselée) couvert de petites feuilles en losange
    orientées au hasard vers l'extérieur ; silhouette découpée, lumière qui passe entre les feuilles."""
    _sphere(m, c, r * 0.62, rng, np.asarray(teinte) * 0.55, bosses=0.3, n_lat=6, n_lon=10)
    n = max(int(np.clip(380 * (r / 1.2) ** 2, 110, 650) * densite), 25)
    d = rng.normal(0, 1, (n, 3))
    d[:, 2] = d[:, 2] * 0.85 + 0.15
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    # feuilles posées sur la surface du volume (rayon 0,5 à 0,8) : aucune feuille isolée hors de l'amas
    centre = np.asarray(c) + d * r * rng.uniform(0.5, 0.8, (n, 1))
    nrm = d + rng.normal(0, 0.6, (n, 3))
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    a = np.cross(nrm, rng.normal(0, 1, (n, 3)))
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    b = np.cross(nrm, a)
    lg = taille_feuille * rng.uniform(0.8, 1.3, (n, 1)) / max(densite, 0.25) ** 0.5   # moins de feuilles : plus grandes
    lr = lg * rng.uniform(0.4, 0.55, (n, 1))
    # feuille elliptique (hexagone allongé, pointes arrondies) au lieu d'un losange
    ang = np.radians([0, 55, 125, 180, 235, 305])
    V = np.stack([centre + a * (lg / 2) * math.cos(t_) + b * (lr / 2) * math.sin(t_) for t_ in ang], 1)
    F = (np.arange(n)[:, None] * 6 + np.arange(6)[None]).astype(np.int64)
    clair = (0.75 + 0.5 * (d[:, 2:3] + 1) / 2) * rng.uniform(0.8, 1.2, (n, 1))
    col = np.repeat(np.clip(np.asarray(teinte)[None] * clair, 0, 1), 6, axis=0)
    m.ajouter(V.reshape(-1, 3), F, col, np.zeros((6 * n, 2)), 0)


PALETTE_AGRO = [(0.36, 0.55, 0.17), (0.39, 0.56, 0.19), (0.33, 0.52, 0.16), (0.41, 0.57, 0.18)]
ECLAT_AGRO = 0.85
PALETTE_ARBRES = [(0.050, 0.115, 0.028), (0.090, 0.140, 0.035), (0.055, 0.120, 0.065), (0.120, 0.165, 0.040),
                  (0.075, 0.105, 0.050), (0.070, 0.145, 0.038), (0.135, 0.150, 0.055)]


def arbre(rng, h, r_c, eclat=1.0, palette=None, densite=1.0):
    """Arbre feuillu générique (lisière, ombrage, agroforesterie) : tronc qui se divise en 3 à 5 charpentières,
    elles-mêmes ramifiées ; feuillage en amas de petites boules bosselées au bout des branches ; teinte propre à
    chaque arbre (palette de verts) et légère variation par amas. r_c ~ rayon horizontal de la couronne."""
    m = bb.Maillage()
    hf = h * rng.uniform(0.3, 0.45)
    pench = rng.normal(0, 0.04, 2)
    tt = np.linspace(0, 1, 7)
    pts = np.c_[pench[0] * tt * hf, pench[1] * tt * hf, tt * hf]
    ecorce = np.array([0.065, 0.055, 0.042]) * rng.uniform(0.75, 1.25)
    bb.tube(m, pts, np.linspace(0.04 * h, 0.03 * h, 7) * (1 + 0.6 * (1 - tt) ** 6), ecorce, 1, n_cotes=8)
    fourche = pts[-1]
    pal = palette or PALETTE_ARBRES
    vert = np.array(pal[rng.integers(len(pal))]) * rng.uniform(0.9, 1.1, 3) * eclat
    bouts = []
    n_br = int(rng.integers(3, 6))
    for b in range(n_br):
        az = 2 * math.pi * b / n_br + rng.normal(0, 0.35)
        el = math.radians(rng.uniform(30, 60))
        cible = np.array([math.cos(az) * 0.6 * r_c, math.sin(az) * 0.6 * r_c, h * rng.uniform(0.62, 0.82)])
        t = np.linspace(0, 1, 7)[:, None]
        d0 = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        L = np.linalg.norm(cible - fourche)
        ctrl = fourche + d0 * L * 0.5
        br = (1 - t) ** 2 * fourche + 2 * (1 - t) * t * ctrl + t ** 2 * cible     # courbe de Bézier
        bb.tube(m, br, np.linspace(0.022 * h, 0.008 * h, 7), ecorce, 1, n_cotes=6)
        bouts.append(cible)
        for sgn in (-1, 1):                                          # deux rameaux secondaires
            if rng.random() < 0.75:
                o = br[4]
                a2 = az + sgn * rng.uniform(0.5, 1.0)
                c2 = o + np.array([math.cos(a2) * 0.35 * r_c, math.sin(a2) * 0.35 * r_c, h * rng.uniform(0.05, 0.15)])
                bb.tube(m, np.linspace(o, c2, 4), np.linspace(0.009 * h, 0.004 * h, 4), ecorce, 1, n_cotes=5)
                bouts.append(c2)
    bouts.append(np.array([0, 0, h * 0.85]))                         # remplissage du sommet
    for e in bouts:
        teinte = vert * rng.uniform(0.85, 1.18, 3)
        for _ in range(int(rng.integers(4, 7))):
            dc = rng.normal(0, 0.17 * r_c, 3)                            # amas serrés autour du bout de branche
            dc[2] = abs(dc[2]) * 0.5
            _amas(m, e + dc, r_c * rng.uniform(0.22, 0.32), rng, teinte * rng.uniform(0.9, 1.1),
                  taille_feuille=0.035 * r_c + 0.07, densite=densite)
    return m


def arbres_parcelle(lignes, collection, mats_arbre):
    """Arbres d'agroforesterie illustratifs aux positions repérées sur la photo (scripts/rendu_arbres.py)."""
    n = 0
    for k, r_ in enumerate(lignes):
        rng = np.random.default_rng(700 + k)
        # palette gris-vert clair, réglée pour que, vue de dessus, le rapport de teinte arbres / bananiers du rendu
        # soit proche de celui de la photo (mesure : scripts/rendu_teinte_arbres.py)
        ob = arbre(rng, r_["hauteur_m"], 1.0 * r_["rayon_m"], eclat=ECLAT_AGRO, palette=PALETTE_AGRO).objet(f"arbre_parcelle_{k:02d}", mats_arbre, collection)
        ob.location = (r_["x_m"], r_["y_m"], 0.0)
        ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        ob["illustratif"] = "position repérée sur la photo, forme et hauteur inventées"
        n += 1
    return n


def lisiere(demi_cote, rng, collection, force_brume=1.0, n_var=10):
    """Lisière d'arbres autour de la parcelle (bande à 15-70 m du bord, en bouquets) et arbres épars au loin.
    Instances liées de n_var arbres types (le moteur de rendu ne stocke qu'une fois chaque maillage)."""
    mat_a = materiau_arbre(force_brume)
    mat_t = materiau_ecorce(force_brume)
    types = []
    for k in range(n_var):
        r = np.random.default_rng(900 + k)
        h = r.uniform(7, 20)
        m = arbre(r, h, r.uniform(3.0, 6.5) * h / 15, densite=DENSITE_LISIERE)
        ob = m.objet(f"arbre_type_{k}", [mat_a, mat_t], None)
        types.append(ob.data)
    buissons = []
    for k in range(5):                                              # buissons et arbustes de la prairie
        r = np.random.default_rng(950 + k)
        h = r.uniform(2.0, 4.5)
        ob = arbre(r, h, r.uniform(1.2, 2.2), densite=DENSITE_LISIERE).objet(f"buisson_type_{k}", [mat_a, mat_t], None)
        buissons.append(ob.data)
    global BUISSONS
    BUISSONS = buissons
    pos = []
    # bande de lisière : points sur des anneaux carrés autour de la parcelle, gardés selon un bruit (bouquets)
    for _ in range(6000):
        d = rng.uniform(35, 140)
        cote = rng.integers(4)
        u = rng.uniform(-demi_cote - d, demi_cote + d)
        x, y = [(u, demi_cote + d), (u, -demi_cote - d), (demi_cote + d, u), (-demi_cote - d, u)][cote]
        dens = bruit2d(np.array([x]), np.array([y]), 21, 3, 1 / 30)[0]
        if dens > 0.55 + (d - 35) / 160 and rng.random() < 0.3:
            pos.append((x, y))
    # buissons épars dans la prairie
    sol = bpy.data.objects.get("terrain")
    n_b = 0
    for _ in range(2500):
        x, y = rng.uniform(-260, 260, 2)
        if max(abs(x), abs(y)) < demi_cote + 6:
            continue
        if bruit2d(np.array([x]), np.array([y]), 23, 2, 1 / 40)[0] < 0.1 or rng.random() < 0.5:
            continue
        z = _hauteur_terrain(x, y) - 0.2 if math.hypot(x, y) > 90 else 0.0
        ob = bpy.data.objects.new(f"buisson_{n_b}", buissons[rng.integers(len(buissons))])
        ob.location = (x, y, z)
        ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        s = rng.uniform(0.6, 1.3)
        ob.scale = (s, s, s)
        collection.objects.link(ob)
        n_b += 1
    # arbres épars et bosquets plus loin
    for _ in range(9000):
        r = 110 + rng.exponential(500)
        a = rng.uniform(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        dens = bruit2d(np.array([x]), np.array([y]), 22, 3, 1 / 120)[0]
        if dens > 0.5 and rng.random() < 0.5:
            pos.append((x, y))
    pos = np.array(pos)
    # pas d'arbre dans l'emprise ni sur ses abords immédiats
    garde = np.maximum(np.abs(pos[:, 0]), np.abs(pos[:, 1])) > demi_cote + 12
    # ni du côté sud-est, entre la caméra de drone et la parcelle (un arbre proche y masquerait le cadre)
    garde &= ~((pos[:, 0] > demi_cote) & (pos[:, 1] < 0.4 * demi_cote) & (pos[:, 0] < demi_cote + 60))
    pos = pos[garde]
    sol = bpy.data.objects.get("terrain")
    for i, (x, y) in enumerate(pos):
        z = 0.0
        if sol is not None and math.hypot(x, y) > 90:
            z = _hauteur_terrain(x, y) - 0.3
        ob = bpy.data.objects.new(f"arbre_{i}", types[rng.integers(n_var)])
        ob.location = (x, y, z)
        ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        s = rng.uniform(0.75, 1.25)
        ob.scale = (s, s, s * rng.uniform(0.9, 1.1))
        collection.objects.link(ob)
    return len(pos)


def _hauteur_terrain(x, y):
    """Même formule que terrain() (pour poser les arbres au sol)."""
    X, Y = np.array([x]), np.array([y])
    r = math.hypot(x, y)
    k1 = min(max((r - 90) / 220, 0), 1) ** 2
    k2 = min(max((r - 700) / 1600, 0), 1) ** 1.5
    return float(k1 * 9 * bruit2d(X, Y, 11, 4, 1 / 160)[0] + k2 * 120 * (0.6 + 0.4 * bruit2d(X, Y, 12, 4, 1 / 900)[0]))


# ----------------------------------------------------------------------------------------------- ciel
def ciel(elevation=50.0, azimut=-100.0, force_ciel=0.16, energie_soleil=4.5, couleur=(1.0, 0.95, 0.88)):
    """Ciel physique (diffusion multiple, sans disque) et soleil cohérents ; azimut depuis le nord, vers l'est."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new("ciel")
    w.use_nodes = True
    nt = w.node_tree
    fond = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(elevation)
    sky.sun_rotation = math.radians(90 - azimut)
    try:
        sky.air_density = 1.0
        sky.aerosol_density = 0.7
    except AttributeError:
        pass
    nt.links.new(sky.outputs["Color"], fond.inputs["Color"])
    fond.inputs["Strength"].default_value = force_ciel
    sc.world = w
    lum = bpy.data.lights.new("soleil", "SUN")
    lum.energy = energie_soleil
    lum.angle = math.radians(1.5)
    lum.color = couleur
    so = bpy.data.objects.new("soleil", lum)
    sc.collection.objects.link(so)
    a, el = math.radians(azimut), math.radians(elevation)
    so.location = (math.sin(a) * math.cos(el), math.cos(a) * math.cos(el), math.sin(el))
    bb.viser(so, (0, 0, 0))
    return so


def nuages(altitude=900.0, demi_cote=9000.0, couverture=0.42):
    """Couche de cumulus procédurale (bruit seuillé sur un grand plan, transparent ailleurs). Elle ne projette
    pas d'ombre (visibilité « ombre » coupée) : l'éclairage de la parcelle reste celui du soleil seul."""
    sc = bpy.context.scene
    V = [(-demi_cote, -demi_cote, altitude), (demi_cote, -demi_cote, altitude), (demi_cote, demi_cote, altitude),
         (-demi_cote, demi_cote, altitude)]
    me = bpy.data.meshes.new("nuages")
    me.from_pydata(V, [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("nuages", me)
    sc.collection.objects.link(ob)
    ob.visible_shadow = False
    ma = bpy.data.materials.new("nuages")
    ma.use_nodes = True
    nt = ma.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    b = _n(nt, "ShaderNodeTexNoise", Scale=0.00045, Detail=10.0, Roughness=0.62)
    nt.links.new(tc.outputs["Object"], b.inputs["Vector"])
    dens = _seuil(nt, b.outputs["Fac"], 1 - couverture, 1 - couverture + 0.12)
    # bord plus sombre et plus mince : base grise des cumulus
    teinte = _rampe(nt, b.outputs["Fac"], [(0.55, 0.58, 0.64), (0.95, 0.95, 0.97)], [1 - couverture, 0.85])
    em = _n(nt, "ShaderNodeEmission", Strength=1.6)
    nt.links.new(teinte, em.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(dens, ms.inputs[0])
    nt.links.new(tr.outputs[0], ms.inputs[1])
    nt.links.new(brume(nt, em.outputs[0], distance_caracteristique=9000.0, force=1.6), ms.inputs[2])
    nt.links.new(ms.outputs[0], sortie.inputs["Surface"])
    me.materials.append(ma)
    for attr in ("visible_diffuse", "visible_glossy", "visible_transmission"):
        setattr(ob, attr, False)
    return ob


# ----------------------------------------------------------------------------------------------- chemins, haies
def materiau_chemin(force_brume=1.0):
    """Piste de terre : deux ornières plus sombres et tassées, bande d'herbe au milieu, bords qui se fondent dans
    la prairie (UV : u le long de la piste, v en travers de 0 à 1)."""
    ma = bpy.data.materials.new("chemin")
    ma.use_nodes = True
    nt = ma.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    b = _n(nt, "ShaderNodeTexNoise", Scale=1.5, Detail=8.0)
    nt.links.new(tc.outputs["Object"], b.inputs["Vector"])
    b2 = _n(nt, "ShaderNodeTexNoise", Scale=0.15, Detail=3.0)                 # ornières qui ondulent
    nt.links.new(tc.outputs["Object"], b2.inputs["Vector"])
    v = _math(nt, "ADD", sep.outputs[1], _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", b.outputs["Fac"], 0.5), 0.12))
    v = _math(nt, "ADD", v, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", b2.outputs["Fac"], 0.5), 0.18))
    terre = _rampe(nt, b.outputs["Fac"], [(0.12, 0.065, 0.035), (0.20, 0.12, 0.065), (0.26, 0.17, 0.10)])
    orn = _math(nt, "MAXIMUM", _seuil(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", v, 0.3)), 0.12, 0.02),
                _seuil(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", v, 0.7)), 0.12, 0.02))
    couleur = _mix(nt, terre, _mix(nt, terre, (0.8, 0.8, 0.8, 1), 1.0, "MULTIPLY"), _math(nt, "MULTIPLY", orn, b.outputs["Fac"]))
    milieu = _seuil(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", v, 0.5)), 0.1, 0.03)
    herbe = _rampe(nt, b.outputs["Fac"], [(0.05, 0.09, 0.02), (0.11, 0.14, 0.04)])
    couleur = _mix(nt, couleur, herbe, _math(nt, "MULTIPLY", milieu, 0.8))
    bord = _math(nt, "MULTIPLY", _seuil(nt, v, 0.0, 0.12), _seuil(nt, v, 1.0, 0.88))
    p = _n(nt, "ShaderNodeBsdfPrincipled", Roughness=0.95)
    nt.links.new(couleur, p.inputs["Base Color"])
    bump = _n(nt, "ShaderNodeBump", Strength=0.4, Distance=0.05)
    nt.links.new(b.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(bord, ms.inputs[0])
    nt.links.new(tr.outputs[0], ms.inputs[1])
    nt.links.new(brume(nt, p.outputs[0], force=force_brume), ms.inputs[2])
    nt.links.new(ms.outputs[0], sortie.inputs["Surface"])
    ma.blend_method = "BLEND" if hasattr(ma, "blend_method") else None
    return ma


def chemin(points, largeur, nom, mat):
    """Ruban de piste le long d'une polyligne (x, y), posé sur le terrain (même formule que terrain())."""
    P = np.asarray(points, float)
    seg = [P[0]]
    for a, b in zip(P[:-1], P[1:]):                                  # rééchantillonnage tous les 2 m
        n = max(int(np.linalg.norm(b - a) / 2.0), 1)
        seg += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)[1:]]
    P = np.array(seg)
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    nrm = np.c_[-t[:, 1], t[:, 0]]
    z = np.array([_hauteur_terrain(x, y) if math.hypot(x, y) > 90 else 0.0 for x, y in P]) + 0.04
    g, d = P - nrm * largeur / 2, P + nrm * largeur / 2
    V = np.stack([np.c_[g, z], np.c_[d, z]], 1)
    F = bb._grille(len(P), 2)
    lg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    uv = np.stack([np.repeat(lg[:, None] / 10, 2, 1), np.tile([0.0, 1.0], (len(P), 1))], -1).reshape(-1, 2)
    return maillage_rapide(nom, V.reshape(-1, 3), F, uv_coins=uv[F.ravel()], materiaux=[mat])


def haies(rng, collection, demi_cote, types):
    """Haies et bordures de champs : lignes d'arbustes (instances des buissons types) dans la prairie."""
    lignes = [((-260, -95), (-60, -80)), ((-60, -80), (-48, 160)), ((60, -120), (250, -70)), ((75, 50), (75, 230)),
              ((75, 50), (260, 40)), ((-250, 70), (-70, 60)), ((-140, -250), (-120, -110)), ((20, -260), (40, -125))]
    n = 0
    for (a, b) in lignes:
        a, b = np.array(a, float), np.array(b, float)
        L = np.linalg.norm(b - a)
        for t in np.arange(0, L, rng.uniform(2.5, 4.0)):
            if rng.random() < 0.18:                                 # trouées dans la haie
                continue
            p = a + (b - a) * t / L + rng.normal(0, 0.8, 2)
            if max(abs(p[0]), abs(p[1])) < demi_cote + 8:
                continue
            ob = bpy.data.objects.new(f"haie_{n}", types[rng.integers(len(types))])
            ob.location = (p[0], p[1], (_hauteur_terrain(*p) - 0.2) if math.hypot(*p) > 90 else 0.0)
            ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
            s = rng.uniform(0.6, 1.2)
            ob.scale = (s, s, s * rng.uniform(0.8, 1.2))
            collection.objects.link(ob)
            n += 1
    return n
