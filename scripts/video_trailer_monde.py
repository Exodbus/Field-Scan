"""Trailer Field Scan : construction du grand domaine de bananiers autour de la parcelle v4 (importé par
video_trailer_rendu3d.py, qui tourne dans Blender).

Idée : la parcelle détaillée v4 (334 bananiers réels, au centre) est répétée sur une grille de blocs de 66 m séparés par
des pistes de terre de 8 m. Les blocs voisins sont faits de bananiers simplifiés (formes générées ici : tronc plus
feuilles courbes en bandes), en deux niveaux de détail selon la distance à la caméra. Les positions des pieds de
chaque bloc reprennent celles de plants.csv (retournées ou tournées de 90 degrés, avec un léger décalage), donc les
rangs restent plausibles. Tout est fabriqué en tableaux numpy et injecté dans de gros maillages (un par bloc).
Les arbres et buissons éloignés de la lisière d'origine sont remplacés par des silhouettes simples (10 + 5 maillages
à 100 000 sommets chacun pesaient 125 millions de sommets) ; les haies de bord de piste sont ajoutées.
"""
import math

import bmesh  # noqa: F401
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PAS_BLOC = 74.0          # distance entre centres de blocs (m) : bloc 66 m + piste 8 m
DEMI_BLOC = 33.0


# ------------------------------------------------------------------------------------------------- matériaux
def materiau(nom, couleur, rug=0.6, translucide=0.0, bruit=0.0, echelle=0.07, clair=1.7):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rug
    bsdf.inputs["Specular IOR Level"].default_value = 0.12
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs[0].default_value = (*couleur, 1)
    src = base.outputs[0]
    if bruit > 0:                                   # variation de teinte (coordonnées d'objet = mètres), deux échelles
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = echelle
        n.inputs["Detail"].default_value = 4.0
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        n2 = nt.nodes.new("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = echelle * 7.0
        n2.inputs["Detail"].default_value = 2.0
        nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
        mm = nt.nodes.new("ShaderNodeMath")
        mm.operation = "ADD"
        mm.use_clamp = True
        nt.links.new(n.outputs["Fac"], mm.inputs[0])
        nt.links.new(n2.outputs["Fac"], mm.inputs[1])
        mm2 = nt.nodes.new("ShaderNodeMath")
        mm2.operation = "SUBTRACT"
        mm2.inputs[1].default_value = 0.45
        mm2.use_clamp = True
        nt.links.new(mm.outputs["Value"], mm2.inputs[0])
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        nt.links.new(mm2.outputs["Value"], mx.inputs[0])
        nt.links.new(base.outputs[0], mx.inputs[6])
        mx.inputs[7].default_value = (couleur[0] * clair, couleur[1] * clair, couleur[2] * clair, 1)
        src = mx.outputs[2]
    nt.links.new(src, bsdf.inputs["Base Color"])
    if translucide > 0:
        sortie = nt.nodes["Material Output"]
        tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
        nt.links.new(src, tr.inputs["Color"])
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = translucide
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], sortie.inputs["Surface"])
    return m


def creer_materiaux():
    return dict(
        feuille_a=materiau("px_feuille_a", (0.115, 0.29, 0.045), 0.6, 0.22),
        feuille_b=materiau("px_feuille_b", (0.085, 0.235, 0.04), 0.6, 0.22),
        feuille_c=materiau("px_feuille_c", (0.17, 0.33, 0.06), 0.6, 0.22),
        tronc=materiau("px_tronc", (0.20, 0.27, 0.09), 0.7),
        canopee=materiau("px_canopee", (0.035, 0.095, 0.02), 0.95, 0.0, 1.0, 0.09, 2.6),
        couronne=materiau("px_couronne", (0.11, 0.19, 0.055), 0.7, 0.15, 0.7),
        ecorce=materiau("px_ecorce", (0.12, 0.085, 0.06), 0.9),
        sol=materiau("px_sol", (0.20, 0.095, 0.052), 0.95, 0.0, 0.8),
        piste=materiau("px_piste", (0.38, 0.22, 0.14), 0.95, 0.0, 0.5),
    )


# ------------------------------------------------------------------------------------------------- gabarits
def gabarit_bananier(rng, n_feuilles, n_seg, cotes):
    """Un bananier simplifié : (sommets, triangles, indice de matériau par triangle). Matériaux : 0, 1, 2 feuilles,
    3 tronc. Hauteur du tronc 2,3 m ; feuilles de 2,2 à 3,2 m, courbées vers le bas."""
    V, F, M = [], [], []
    h = 2.3
    for ring, (r, z) in enumerate(((0.20, 0.0), (0.13, h))):
        for s in range(cotes):
            a = 2 * math.pi * s / cotes
            V.append((r * math.cos(a), r * math.sin(a), z))
    for s in range(cotes):
        s2 = (s + 1) % cotes
        F += [(s, s2, cotes + s), (s2, cotes + s2, cotes + s)]
        M += [3, 3]
    for k in range(n_feuilles):
        t = k / max(n_feuilles - 1, 1)
        phi = k * 2.39996 + rng.uniform(-0.25, 0.25)
        el = math.radians(78 - 70 * t + rng.uniform(-6, 6))
        chute = math.radians(5 + 17 * t + rng.uniform(-2, 2))
        L = rng.uniform(2.3, 3.2)
        W = rng.uniform(0.55, 0.85)
        p = np.array([0.0, 0.0, h])
        pts = [p.copy()]
        for j in range(n_seg):
            el -= chute
            p = p + (L / n_seg) * np.array([math.cos(el) * math.cos(phi), math.cos(el) * math.sin(phi), math.sin(el)])
            pts.append(p.copy())
        lat = np.array([-math.sin(phi), math.cos(phi), 0.0])
        base = len(V)
        for j, q in enumerate(pts):
            s = j / n_seg
            w = 0.5 * W * math.sin(math.pi * min(0.10 + 0.9 * s, 1.0)) + 0.01
            V.append(tuple(q + lat * w + np.array([0, 0, -0.25 * w])))
            V.append(tuple(q + np.array([0, 0, 0.05])))
            V.append(tuple(q - lat * w + np.array([0, 0, -0.25 * w])))
        mat = (0, 1, 2)[k % 3]
        for j in range(n_seg):
            a, b = base + 3 * j, base + 3 * (j + 1)
            F += [(a, a + 1, b), (a + 1, b + 1, b), (a + 1, a + 2, b + 1), (a + 2, b + 2, b + 1)]
            M += [mat] * 4
    return np.array(V, np.float32), np.array(F, np.int32), np.array(M, np.int32)


def gabarit_arbre(rng, cotes=7, anneaux=3):
    """Arbre simplifié de hauteur 1 et d'emprise 1 (à mettre à l'échelle) : tronc effilé et couronne faite de trois
    lobes bosselés (silhouette moins boule). Matériaux : 0 couronne, 1 écorce."""
    V, F, M = [], [], []
    for r, z in ((0.03, 0.0), (0.018, 0.5)):
        for s in range(5):
            a = 2 * math.pi * s / 5
            V.append((r * math.cos(a), r * math.sin(a), z))
    for s in range(5):
        s2 = (s + 1) % 5
        F += [(s, s2, 5 + s), (s2, 5 + s2, 5 + s)]
        M += [1, 1]
    lobes = ((0.0, 0.0, 0.68, 0.40, 0.30), (0.20, 0.08, 0.58, 0.28, 0.22), (-0.18, -0.10, 0.55, 0.26, 0.20))
    for lx, ly, cz, rxy, rz in lobes:
        c0 = len(V)
        V.append((lx, ly, cz - rz))
        for i in range(1, anneaux + 1):
            ph = math.pi * i / (anneaux + 1)
            for s in range(cotes):
                a = 2 * math.pi * s / cotes + (i % 2) * 0.3
                rr = rxy * math.sin(ph) * rng.uniform(0.7, 1.15)
                V.append((lx + rr * math.cos(a), ly + rr * math.sin(a), cz - rz * math.cos(ph) * rng.uniform(0.85, 1.1)))
        V.append((lx, ly, cz + rz))
        top = len(V) - 1
        for s in range(cotes):
            s2 = (s + 1) % cotes
            F.append((c0, c0 + 1 + s2, c0 + 1 + s))
            F.append((top, top - cotes + s, top - cotes + s2))
            M += [0, 0]
        for i in range(anneaux - 1):
            a0 = c0 + 1 + i * cotes
            for s in range(cotes):
                s2 = (s + 1) % cotes
                F += [(a0 + s, a0 + s2, a0 + cotes + s), (a0 + s2, a0 + cotes + s2, a0 + cotes + s)]
                M += [0, 0]
    return np.array(V, np.float32), np.array(F, np.int32), np.array(M, np.int32)


def instancier(gab, pos, rot, ech, mat_ids):
    """Instances d'un gabarit : pos (n,3), rot (n,), ech (n,3) ou (n,) -> (V, F, M) concaténés."""
    V, F, M = gab
    n = len(pos)
    ech = np.asarray(ech, np.float32)
    if ech.ndim == 1:
        ech = np.repeat(ech[:, None], 3, 1)
    c, s = np.cos(rot).astype(np.float32), np.sin(rot).astype(np.float32)
    X = V[None, :, 0] * ech[:, None, 0]
    Y = V[None, :, 1] * ech[:, None, 1]
    Z = V[None, :, 2] * ech[:, None, 2]
    Vx = X * c[:, None] - Y * s[:, None] + pos[:, None, 0]
    Vy = X * s[:, None] + Y * c[:, None] + pos[:, None, 1]
    Vz = Z + pos[:, None, 2]
    Vn = np.stack([Vx, Vy, Vz], -1).reshape(-1, 3)
    Fn = (F[None] + (np.arange(n, dtype=np.int32) * len(V))[:, None, None]).reshape(-1, 3)
    Mn = np.tile(np.asarray(mat_ids, np.int32)[M], n)
    return Vn, Fn, Mn


def objet_depuis(nom, V, F, M, materiaux, collection=None):
    me = bpy.data.meshes.new(nom)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", np.ascontiguousarray(V, np.float32).ravel())
    me.loops.add(len(F) * 3)
    me.loops.foreach_set("vertex_index", F.astype(np.int32).ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", (np.arange(len(F)) * 3).astype(np.int32))
    me.polygons.foreach_set("material_index", M.astype(np.int32))
    me.update()
    me.validate()
    for m in materiaux:
        me.materials.append(m)
    ob = bpy.data.objects.new(nom, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


# ------------------------------------------------------------------------------------------------- terrain
class Terrain:
    """Hauteur du terrain par lancer de rayons vertical sur une grille grossière, puis interpolation bilinéaire."""

    def __init__(self, x0, x1, y0, y1, pas=12.0):
        deps = bpy.context.evaluated_depsgraph_get()
        t = bpy.data.objects["terrain"]
        bvh = BVHTree.FromObject(t, deps)
        self.x0, self.y0, self.pas = x0, y0, pas
        xs = np.arange(x0, x1 + pas, pas)
        ys = np.arange(y0, y1 + pas, pas)
        self.h = np.zeros((len(ys), len(xs)), np.float32)
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                hit = bvh.ray_cast(Vector((x, y, 300.0)), Vector((0, 0, -1)))
                self.h[j, i] = hit[0].z if hit[0] is not None else 0.0

    def hauteur(self, x, y):
        u = (np.asarray(x) - self.x0) / self.pas
        v = (np.asarray(y) - self.y0) / self.pas
        u = np.clip(u, 0, self.h.shape[1] - 1.001)
        v = np.clip(v, 0, self.h.shape[0] - 1.001)
        i, j = u.astype(int), v.astype(int)
        fu, fv = u - i, v - j
        h = self.h
        return (h[j, i] * (1 - fu) * (1 - fv) + h[j, i + 1] * fu * (1 - fv) + h[j + 1, i] * (1 - fu) * fv
                + h[j + 1, i + 1] * fu * fv)


# ------------------------------------------------------------------------------------------------- domaine
def construire(plants, chemin, ix_plage=(-16, 16), iy_plage=(-4, 58), seed=7, masquer_arbres_parcelle=True,
               dist_proche=90.0, dist_moyen=190.0, dist_prisme=800.0, rayon_vue=6000.0):
    """plants : (n,2) positions de la parcelle v4 ; chemin : (k,3) points de la trajectoire de la caméra."""
    rng = np.random.default_rng(seed)
    mat = creer_materiaux()
    sc = bpy.context.scene
    col = bpy.data.collections.new("domaine")
    sc.collection.children.link(col)
    chemin = np.asarray(chemin, float)
    x0, x1 = ix_plage[0] * PAS_BLOC - 60, ix_plage[1] * PAS_BLOC + 60
    y0, y1 = iy_plage[0] * PAS_BLOC - 60, iy_plage[1] * PAS_BLOC + 60
    terrain = Terrain(x0, x1, y0, y1, 12.0)
    # blocs occupés (le bloc 0,0 est la parcelle v4 détaillée ; ~8 % de blocs laissés en prairie)
    occupe = {}
    for ix in range(ix_plage[0], ix_plage[1] + 1):
        for iy in range(iy_plage[0], iy_plage[1] + 1):
            occupe[(ix, iy)] = (ix, iy) == (0, 0) or True
    # gabarits de bananiers : 3 variantes de détail moyen, 3 de détail lointain
    g_moy = [gabarit_bananier(np.random.default_rng(100 + k), 9, 5, 7) for k in range(3)]
    g_loin = [gabarit_bananier(np.random.default_rng(200 + k), 6, 2, 4) for k in range(3)]
    mats_b = [mat["feuille_a"], mat["feuille_b"], mat["feuille_c"], mat["tronc"]]
    n_obj, n_plants = 0, 0
    prismes, n_prismes = [], 0
    for (ix, iy), occ in occupe.items():
        if not occ or (ix, iy) == (0, 0):
            continue
        cx, cy = ix * PAS_BLOC, iy * PAS_BLOC
        d = np.min(np.hypot(chemin[:, 0] - cx, chemin[:, 1] - cy))
        if d > rayon_vue:
            occupe[(ix, iy)] = False
            continue
        if d > dist_prisme:                       # très loin : une canopée en prisme bas (aucun détail à voir sous la brume)
            hh = float(terrain.hauteur(cx, cy))
            h0, h1 = hh - 0.5, hh + 2.6 + rng.uniform(-0.3, 0.5)
            x_a, x_b, y_a, y_b = cx - DEMI_BLOC, cx + DEMI_BLOC, cy - DEMI_BLOC, cy + DEMI_BLOC
            prismes.append((x_a, x_b, y_a, y_b, h0, h1))
            n_prismes += 1
            continue
        mode = int(rng.integers(0, 8))
        p = plants.copy()
        if mode & 1:
            p[:, 0] = -p[:, 0]
        if mode & 2:
            p[:, 1] = -p[:, 1]
        if mode & 4:
            p = p[:, ::-1].copy()
        p = p + rng.normal(0, 0.25, p.shape)
        p = p[rng.random(len(p)) > 0.04]
        px, py = p[:, 0] + cx, p[:, 1] + cy
        pz = terrain.hauteur(px, py)
        pos = np.stack([px, py, pz], 1).astype(np.float32)
        rot = rng.uniform(0, 2 * math.pi, len(p)).astype(np.float32)
        ech = rng.uniform(0.85, 1.15, len(p)).astype(np.float32)
        gabs = g_moy if d < dist_moyen else g_loin
        parts = []
        cls = rng.integers(0, 3, len(p))
        for k in range(3):
            s = cls == k
            if s.any():
                parts.append(instancier(gabs[k], pos[s], rot[s], ech[s], [0, 1, 2, 3]))
        V = np.concatenate([q[0] for q in parts])
        off = np.cumsum([0] + [len(q[0]) for q in parts[:-1]])
        F = np.concatenate([q[1] + o for q, o in zip(parts, off)])
        M = np.concatenate([q[2] for q in parts])
        objet_depuis(f"bloc_{ix}_{iy}", V, F, M, mats_b, col)
        n_obj += 1
        n_plants += len(p)
    if prismes:
        n = 8
        gx = np.linspace(0, 1, n + 1)
        Vp, Fp = [], []
        k0 = 0
        for (xa, xb, ya, yb, h0, h1) in prismes:
            X, Y = np.meshgrid(xa + (xb - xa) * gx, ya + (yb - ya) * gx)
            X = X + rng.normal(0, 0.9, X.shape)
            Y = Y + rng.normal(0, 0.9, Y.shape)
            dd = np.minimum(np.minimum(gx[None, :], 1 - gx[None, :]), np.minimum(gx[:, None], 1 - gx[:, None])) * n
            bord = np.clip(dd / 1.6, 0, 1) ** 0.8
            Z = h0 + 0.7 + (h1 - h0 - 0.7) * bord + rng.normal(0, 0.45, X.shape) * bord
            Vp.append(np.stack([X, Y, Z], -1).reshape(-1, 3))
            idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1) + k0
            a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
            Fp.append(np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)]))
            k0 += (n + 1) ** 2
        Vp = np.concatenate(Vp).astype(np.float32)
        Fp = np.concatenate(Fp).astype(np.int32)
        objet_depuis("canopee_lointaine", Vp, Fp, np.zeros(len(Fp), np.int32), [mat["canopee"]], col)
    print(f"domaine : {n_obj} blocs détaillés, {n_prismes} canopées lointaines, {n_plants} bananiers simplifiés", flush=True)
    # sol : un seul maillage (grille de 4 m) — terre dans les blocs occupés, piste autour
    pas = 4.0
    gx = np.arange(x0, x1 + pas, pas)
    gy = np.arange(y0, y1 + pas, pas)
    X, Y = np.meshgrid(gx, gy)
    Zs = terrain.hauteur(X, Y) + 0.03
    ny, nx = X.shape
    V = np.stack([X, Y, Zs], -1).reshape(-1, 3).astype(np.float32)
    cxm = (X[:-1, :-1] + X[1:, 1:]) / 2
    cym = (Y[:-1, :-1] + Y[1:, 1:]) / 2
    bx = np.rint(cxm / PAS_BLOC).astype(int)
    by = np.rint(cym / PAS_BLOC).astype(int)
    dans = (np.abs(cxm - bx * PAS_BLOC) <= DEMI_BLOC) & (np.abs(cym - by * PAS_BLOC) <= DEMI_BLOC)
    occ_arr = np.zeros(cxm.shape, bool)
    for (ix, iy), o in occupe.items():
        if o:
            occ_arr |= (bx == ix) & (by == iy)
    garde = occ_arr
    idx = np.arange(ny * nx).reshape(ny, nx)
    a, b, c, d_ = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
    q = np.stack([a, b, c, d_], -1)[garde]
    F = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]]).astype(np.int32)
    Mi = np.concatenate([np.where(dans[garde], 0, 1)] * 2).astype(np.int32)
    objet_depuis("sol_domaine", V, F, Mi, [mat["sol"], mat["piste"]], col)
    # lisière d'origine : on retire ce qui tombe dans le domaine, on simplifie le reste selon la distance
    for nom in ("piste_ouest", "piste_sud", "nuages"):
        bpy.data.objects[nom].hide_render = True
    proxies = {}
    n_h = n_p = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith(("arbre_", "buisson_", "haie_")):
            continue
        if o.name.startswith("arbre_parcelle"):
            if masquer_arbres_parcelle:
                o.hide_render = True
                n_h += 1
            continue
        bx_, by_ = o.location.x / PAS_BLOC, o.location.y / PAS_BLOC
        ix_, iy_ = int(round(bx_)), int(round(by_))
        if ix_range(ix_, ix_plage) and iy_range(iy_, iy_plage):
            o.hide_render = True
            n_h += 1
            continue
        d = np.min(np.hypot(chemin[:, 0] - o.location.x, chemin[:, 1] - o.location.y))
        if d > 2200:
            o.hide_render = True
            n_h += 1
            continue
        if d > 45.0:                              # plus de silhouettes : on retire l'arbre lointain (pas de boules)
            o.hide_render = True
            n_h += 1
    print(f"lisière : {n_h} objets masqués", flush=True)
    # le sol d'origine (herbe, feuilles au sol) reste ; la terre de la parcelle v4 est déjà dans la scène
    return terrain


def ix_range(i, plage):
    return plage[0] - 1 <= i <= plage[1] + 1


iy_range = ix_range
