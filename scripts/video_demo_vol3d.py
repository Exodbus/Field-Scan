"""Vidéo de démonstration, plan 6 : vol de caméra Blender (Eevee) au-dessus des 13 parcelles de Basse-Pointe.

Reconstruit la scène depuis out/visite_basse_pointe_zone/ (sol = photo IGN, bananiers = formes de bananiers.glb posées
aux positions de bananiers.bin, canne = touffes simples aux positions de canne.bin, contours de parcelles en relief,
panneaux flottants) et rend les images d'un des trois plans :
  A  descente de 230 m à 150 m au-dessus des parcelles, panneaux visibles ;
  B  descente jusqu'à une allée entre deux rangs de la parcelle R050, vol en rase-mottes, remontée ;
  C  mode Santé : zones moins vertes en orange (sol et bananiers), orbite autour des zones de R050.
Les bananiers et la canne sont une illustration (aucun comptage). Les textures viennent de video_demo_preparer.py.

    blender.exe -b --factory-startup -P scripts/video_demo_vol3d.py -- --plan A --pourcent 33 --fps 15 --debut 1 --fin 5 \
        --sortie out/video_demo/travail/test

Les images déjà rendues sont sautées (reprise possible). 4 fils au plus.
"""
import argparse
import os
import gzip
import json
import math
import sys
import time
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector

RACINE = Path(__file__).resolve().parents[1]
V = RACINE / "out/visite_basse_pointe_zone"
T = RACINE / "out/video_demo/travail"
DUREES = {"A": 9.0, "B": 17.0, "C": 9.0}
N_FORMES = 12
SCRATCH_GLB = None


# ------------------------------------------------------------------------------------------------ données
def lire_donnees():
    d = json.loads((V / "donnees.json").read_text(encoding="utf-8"))
    E = d["emprise"]
    dt = np.dtype([("x", "<u2"), ("y", "<u2"), ("forme", "u1"), ("drap", "u1"), ("rot", "u1"), ("ech", "u1")])
    res = {}
    for nom in ("bananiers", "canne"):
        info = d["plantes"][nom]
        brut = (V / info["fichier"]).read_bytes()[: info["n"] * 8]
        a = np.frombuffer(brut, dtype=dt)
        res[nom] = dict(x=E["xmin"] + a["x"] * 0.02, y=E["ymin"] + a["y"] * 0.02, forme=a["forme"].astype(int),
                        drap=a["drap"].astype(int), rot=a["rot"] / 256 * 2 * math.pi,
                        ech=0.9 + 0.25 * a["ech"] / 255)
    mb = gzip.decompress((V / "masque.bin.gz").read_bytes())
    mw, mh = d["masque"]["px"]
    masque = np.frombuffer(mb[: mw * mh], dtype=np.uint8).reshape(mh, mw)
    for nom in ("bananiers", "canne"):
        r = res[nom]
        c = np.clip(((r["x"] - E["xmin"]) / 0.5).astype(int), 0, mw - 1)
        l = np.clip(((r["y"] - E["ymin"]) / 0.5).astype(int), 0, mh - 1)
        r["parcelle"] = masque[l, c].astype(int)  # 0 = hors zone, i = parcelles[i - 1]
    return d, res


def rangee_et_allee(d, bn, id_parc):
    """Direction des rangs d'une parcelle et une allée libre (milieu du plus grand vide entre deux rangs)."""
    i = [p["id"] for p in d["parcelles"]].index(id_parc) + 1
    m = bn["parcelle"] == i
    X = np.c_[bn["x"][m], bn["y"][m]]
    meilleur = (-1, 0)
    for th in np.arange(0, 180, 0.5):
        r = math.radians(th)
        n = np.array([-math.sin(r), math.cos(r)])
        h, _ = np.histogram(X @ n, bins=np.arange((X @ n).min(), (X @ n).max() + 0.2, 0.2))
        sc = (h.astype(float) ** 2).sum()
        if sc > meilleur[0]:
            meilleur = (sc, th)
    th = math.radians(meilleur[1])
    u = np.array([math.cos(th), math.sin(th)])   # le long des rangs
    n = np.array([-math.sin(th), math.cos(th)])  # perpendiculaire
    cen = X.mean(axis=0)
    po = (X - cen) @ n
    ps = (X - cen) @ u
    # on ne garde que les plantes proches du centre le long des rangs, pour que l'allée y passe
    cent = np.abs(ps) < 60
    vals = np.sort(np.unique(np.round(po[cent], 1)))
    ecarts = np.diff(vals)
    # plus grand vide dans la bande centrale (|offset| < 40 m)
    ok = (np.abs(vals[:-1]) < 40)
    k = int(np.argmax(np.where(ok, ecarts, 0)))
    off = float((vals[k] + vals[k + 1]) / 2)
    # étendue de l'allée le long des rangs : là où il y a des plantes de la parcelle de part et d'autre
    s = np.arange(ps.min(), ps.max(), 1.0)
    proche = np.array([(np.abs(po - off) < 4.5)[(np.abs(ps - v) < 1.0)].any() for v in s])
    return dict(angle_deg=meilleur[1], u=u, n=n, off=off, cen=cen, ecart_m=float(ecarts[k]),
                s_min=float(s[proche].min()) if proche.any() else -50.0, s_max=float(s[proche].max()) if proche.any() else 50.0)


# ------------------------------------------------------------------------------------------------ trajectoires
def hermite(pts, temps, t):
    """Spline de Catmull-Rom (temps non uniformes) sur des points 3D."""
    pts = [np.array(p, float) for p in pts]
    t = min(max(t, temps[0]), temps[-1])
    k = max(0, min(len(temps) - 2, np.searchsorted(temps, t, side="right") - 1))
    t0, t1 = temps[k], temps[k + 1]
    u = (t - t0) / (t1 - t0)
    p0, p1 = pts[k], pts[k + 1]
    m0 = (pts[k + 1] - pts[k - 1]) / (temps[k + 1] - temps[k - 1]) * (t1 - t0) if k > 0 else (p1 - p0)
    m1 = (pts[k + 2] - pts[k]) / (temps[k + 2] - temps[k]) * (t1 - t0) if k + 2 < len(pts) else (p1 - p0)
    h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1


def trajets(d, bn, geo):
    """Pour chaque plan : (positions, cibles, temps). Coordonnées en m, repère de donnees.json."""
    u, n, off, cen = geo["u"], geo["n"], geo["off"], geo["cen"]
    # allée : orientée de façon à s'éloigner du départ du plan B (qui arrive du nord-est)
    entree_s, sortie_s = geo["s_min"] + 12, geo["s_max"] - 12
    if sortie_s - entree_s > 150:
        mil = (entree_s + sortie_s) / 2
        entree_s, sortie_s = mil - 70, mil + 70
    P = lambda s, z: np.array([*(cen + off * n + s * u), z])
    A0, A1 = (-350, 70, 225.0), (-285, -190, 150.0)
    dirA = np.array(A1[:2], float) - np.array(A0[:2], float)
    dirA /= np.linalg.norm(dirA)
    tgA = lambda p, lead: np.array([p[0] + dirA[0] * lead, p[1] + dirA[1] * lead, 0.0])
    posA = [A0, (-322, -60, 185.0), A1, (-265, -250, 145.0)]
    tmA = [0, 3.2, 7.0, 9.0]
    cibA = [tgA(np.array(p), 150) for p in posA]
    plans = {"A": (posA, cibA, tmA)}
    # B : on arrive sur l'allée par son extrémité la plus proche de la fin du plan A
    if np.linalg.norm(P(entree_s, 0)[:2] - np.array(A1[:2])) > np.linalg.norm(P(sortie_s, 0)[:2] - np.array(A1[:2])):
        entree_s, sortie_s = sortie_s, entree_s
    sgn = 1 if sortie_s > entree_s else -1
    mid = (entree_s + sortie_s) / 2
    posB = [plans["A"][0][-1], P(entree_s - sgn * 70, 55), P(entree_s - sgn * 14, 3.6), P(entree_s, 2.1),
            P(mid, 2.1), P(sortie_s, 2.2), P(sortie_s + sgn * 26, 16), P(sortie_s + sgn * 75, 72)]
    cibB = [tgA(np.array(plans["A"][0][-1]), 150), P(entree_s + sgn * 20, 2.0), P(entree_s + sgn * 34, 2.6),
            P(entree_s + sgn * 40, 3.0), P(mid + sgn * 40, 3.0), P(sortie_s + sgn * 44, 4.5),
            P(mid, 6.0), P(mid - sgn * 10, 0.0)]
    tmB = [0, 3.5, 5.6, 6.6, 10.0, 13.2, 14.8, 17.0]
    plans["B"] = (posB, cibB, tmB)
    # C : orbite autour des zones moins vertes de R050
    zs = [z for z in d["zones_faibles"] if z["parcelle"] == "R050"]
    zs.sort(key=lambda z: -z["surface_ha"])
    pts = []
    for z in zs[:6]:
        r = np.array(z["anneaux"][0][0]).reshape(-1, 2)
        pts.append(r.mean(axis=0))
    ctr = np.mean(pts, axis=0)
    posC, cibC, tmC = [], [], []
    for k in range(6):
        a = math.radians(210 + k * 14)
        posC.append((ctr[0] + 70 * math.cos(a), ctr[1] + 70 * math.sin(a), 42 - 2.0 * k))
        cibC.append((ctr[0], ctr[1], 0.0))
        tmC.append(k * 9.0 / 5)
    plans["C"] = (posC, cibC, tmC)
    return plans


# ------------------------------------------------------------------------------------------------ scène
HAZE = (0.50, 0.62, 0.78, 1.0)
PORTEE = {"A": (350.0, 1000.0), "B": (100.0, 350.0), "C": (120.0, 350.0)}
PLAN = ["B"]


def brume(m, dmin=None, dmax=None, dens=0.45):
    """Brume de distance : le matériau se mélange à une couleur d'horizon entre dmin et dmax mètres de la caméra."""
    dmin, dmax = PORTEE[PLAN[0]]
    nt = m.node_tree
    out = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"][0]
    src = out.inputs["Surface"].links[0].from_socket
    cd = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = dmin, dmax
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.0, dens
    nt.links.new(cd.outputs["View Distance"], mr.inputs["Value"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = HAZE
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs["Result"], mx.inputs[0])
    nt.links.new(src, mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def mat_plante(nom, orange=False):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    pr = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pr.inputs["Roughness"].default_value = 0.55
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Color"
    if orange:
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        mu = nt.nodes.new("ShaderNodeMix")
        mu.data_type = "RGBA"
        mu.blend_type = "MULTIPLY"
        mu.inputs[0].default_value = 1.0
        mu.inputs[7].default_value = (2.2, 0.95, 0.12, 1.0)
        nt.links.new(vc.outputs["Color"], bw.inputs["Color"])
        nt.links.new(bw.outputs["Val"], mu.inputs[6])
        nt.links.new(mu.outputs[2], pr.inputs["Base Color"])
    else:
        sb = nt.nodes.new("ShaderNodeHueSaturation")
        sb.inputs["Saturation"].default_value = 1.25
        sb.inputs["Value"].default_value = 0.8
        nt.links.new(vc.outputs["Color"], sb.inputs["Color"])
        nt.links.new(sb.outputs["Color"], pr.inputs["Base Color"])
        pr.inputs["Specular IOR Level"].default_value = 0.15
    tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(pr.inputs["Base Color"].links[0].from_socket, tl.inputs["Color"])
    mt = nt.nodes.new("ShaderNodeMixShader")
    mt.inputs[0].default_value = 0.0
    nt.links.new(pr.outputs["BSDF"], mt.inputs[1])
    nt.links.new(tl.outputs[0], mt.inputs[2])
    nt.links.new((pr.outputs["BSDF"] if os.environ.get("FS_NOTR") else mt.outputs[0]), sortie.inputs["Surface"])
    return brume(m)


def mat_unie(nom, couleur, emission=0.0, rugosite=0.7):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    pr = m.node_tree.nodes["Principled BSDF"]
    pr.inputs["Base Color"].default_value = (*couleur, 1.0)
    pr.inputs["Roughness"].default_value = rugosite
    if emission:
        pr.inputs["Emission Color"].default_value = (*couleur, 1.0)
        pr.inputs["Emission Strength"].default_value = emission
    return brume(m)


def collection_hors_scene(nom):
    c = bpy.data.collections.new(nom)  # non liée à la scène : sert seulement de source d'instances
    return c


def charger_formes(glb):
    avant = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    nouveaux = [o for o in bpy.data.objects if o not in avant]
    objs = {o.name: o for o in nouveaux if o.type == "MESH"}
    mats = (mat_plante("plante_verte"), mat_plante("plante_orange", True))
    cols = {}
    for niv in (0, 1, 2):
        for var in (0, 1):
            c = collection_hors_scene(f"formes_l{niv}_{'o' if var else 'v'}")
            for k in range(N_FORMES):
                src = objs[f"b{k:02d}_l{niv}"]
                o = src.copy()
                o.data = src.data.copy()
                o.data.materials.clear()
                o.data.materials.append(mats[var])
                o.location = (0, 0, 0)
                o.rotation_euler = (0, 0, 0)
                o.parent = None
                c.objects.link(o)
            cols[(niv, var)] = c
    # niveau 3 : cône très simple pour les plantes lointaines
    for var in (0, 1):
        c = collection_hors_scene(f"formes_l3_{'o' if var else 'v'}")
        for k in range(N_FORMES):
            me = bpy.data.meshes.new(f"cone{k}_{var}")
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=7, radius1=2.0 + 0.05 * k, radius2=0.35,
                                  depth=3.6)
            bmesh.ops.translate(bm, vec=(0, 0, 2.1), verts=bm.verts)
            bm.to_mesh(me)
            bm.free()
            me.materials.append(mat_unie("cone_o" if var else "cone_v", (0.95, 0.4, 0.05) if var else (0.10, 0.22, 0.06)))
            o = bpy.data.objects.new(f"b{k:02d}_l3", me)
            c.objects.link(o)
        cols[(3, var)] = c
    for o in nouveaux:  # sources du glb : on les retire
        bpy.data.objects.remove(o)
    return cols


def instancier(nom, pos, idx, rot, ech, col):
    """Objet de points + Geometry Nodes : une instance de la collection (choisie par idx) sur chaque point."""
    n = len(pos)
    me = bpy.data.meshes.new(nom)
    me.vertices.add(n)
    me.vertices.foreach_set("co", np.asarray(pos, dtype=np.float32).ravel())
    for a, typ, val in (("idx", "INT", idx), ("rot", "FLOAT", rot), ("sc", "FLOAT", ech)):
        at = me.attributes.new(a, typ, "POINT")
        at.data.foreach_set("value", np.asarray(val, dtype=np.int32 if typ == "INT" else np.float32))
    me.update()
    ob = bpy.data.objects.new(nom, me)
    bpy.context.scene.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(nom, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nd = ng.nodes
    gi, go = nd.new("NodeGroupInput"), nd.new("NodeGroupOutput")
    iop = nd.new("GeometryNodeInstanceOnPoints")
    ci = nd.new("GeometryNodeCollectionInfo")
    ci.transform_space = "RELATIVE"
    ci.inputs["Collection"].default_value = col
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop.inputs["Pick Instance"].default_value = True

    def attr(nom_a, typ):
        a = nd.new("GeometryNodeInputNamedAttribute")
        a.data_type = typ
        a.inputs["Name"].default_value = nom_a
        return a
    a_idx, a_rot, a_sc = attr("idx", "INT"), attr("rot", "FLOAT"), attr("sc", "FLOAT")
    comb = nd.new("ShaderNodeCombineXYZ")
    eul = nd.new("FunctionNodeEulerToRotation")
    combs = nd.new("ShaderNodeCombineXYZ")
    L = ng.links
    L.new(gi.outputs[0], iop.inputs["Points"])
    L.new(ci.outputs["Instances"], iop.inputs["Instance"])
    L.new(a_idx.outputs[0], iop.inputs["Instance Index"])
    L.new(a_rot.outputs[0], comb.inputs["Z"])
    L.new(comb.outputs[0], eul.inputs[0])
    L.new(eul.outputs[0], iop.inputs["Rotation"])
    for ax in ("X", "Y", "Z"):
        L.new(a_sc.outputs[0], combs.inputs[ax])
    L.new(combs.outputs[0], iop.inputs["Scale"])
    L.new(iop.outputs["Instances"], go.inputs[0])
    mod = ob.modifiers.new("gn", "NODES")
    mod.node_group = ng
    return ob


def contours(d):
    me = bpy.data.meshes.new("contours")
    bm = bmesh.new()
    H, LAR = 1.4, 0.45
    for p in d["parcelles"]:
        for poly in p["bord"]:
            for r in poly:
                pts = np.array(r, float).reshape(-1, 2)
                m = len(pts)
                for i in range(m):
                    a, b = pts[i], pts[(i + 1) % m]
                    t = b - a
                    L = np.linalg.norm(t)
                    if L < 1e-6:
                        continue
                    nrm = np.array([-t[1], t[0]]) / L * LAR
                    v = [bm.verts.new((a[0] - nrm[0], a[1] - nrm[1], H)), bm.verts.new((a[0] + nrm[0], a[1] + nrm[1], H)),
                         bm.verts.new((b[0] + nrm[0], b[1] + nrm[1], H)), bm.verts.new((b[0] - nrm[0], b[1] - nrm[1], H))]
                    bm.faces.new(v)
                    w = [bm.verts.new((a[0], a[1], 0.0)), bm.verts.new((b[0], b[1], 0.0)),
                         bm.verts.new((b[0], b[1], H)), bm.verts.new((a[0], a[1], H))]
                    bm.faces.new(w)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("contours", me)
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new("contour")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.159, 0.624, 0.254, 1)  # #6FCF8A
    em.inputs["Strength"].default_value = 2.5
    tp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.6
    so = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tp.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], so.inputs["Surface"])
    brume(m)
    me.materials.append(m)
    return ob


def sol(d, mode):
    E = d["emprise"]
    # contexte grisé autour de la zone
    C = d["tuiles"]["contexte"]
    for nom, img, x0, x1, y0, y1, z in (
            ("contexte", T / "contexte.jpg", C["xmin"], C["xmax"], C["ymin"], C["ymax"], -0.12),
            ("sol", T / ("sol_sante.jpg" if mode == "sante" else "sol_naturel.jpg"), E["xmin"], E["xmax"], E["ymin"], E["ymax"], 0.0)):
        me = bpy.data.meshes.new(nom)
        me.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(name="UVMap")
        for lo, c in zip(me.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            uv.data[lo.index].uv = c
        ob = bpy.data.objects.new(nom, me)
        bpy.context.scene.collection.objects.link(ob)
        m = bpy.data.materials.new(nom)
        m.use_nodes = True
        nt = m.node_tree
        im = nt.nodes.new("ShaderNodeTexImage")
        im.image = bpy.data.images.load(str(img))
        im.interpolation = "Linear"
        pr = nt.nodes["Principled BSDF"]
        pr.inputs["Roughness"].default_value = 0.95
        pr.inputs["Specular IOR Level"].default_value = 0.0
        hs = nt.nodes.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = 1.1
        hs.inputs["Value"].default_value = 0.95
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 0.9
        nz.inputs["Detail"].default_value = 6.0
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].color = (0.84, 0.84, 0.84, 1)
        cr.color_ramp.elements[1].color = (1.14, 1.14, 1.14, 1)
        nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
        mu = nt.nodes.new("ShaderNodeMix")
        mu.data_type = "RGBA"
        mu.blend_type = "MULTIPLY"
        mu.inputs[0].default_value = 1.0
        mu.inputs[7].default_value = (1.0, 1.0, 1.0, 1.0)
        wm = nt.nodes.new("ShaderNodeMix")
        wm.data_type = "RGBA"
        wm.blend_type = "MULTIPLY"
        wm.inputs[0].default_value = 1.0
        wm.inputs[7].default_value = (1.6, 1.08, 0.66, 1.0) if PLAN[0] == "B" else (1.12, 1.02, 0.86, 1.0)
        nt.links.new(im.outputs["Color"], hs.inputs["Color"])
        nt.links.new(hs.outputs["Color"], wm.inputs[6])
        nt.links.new(wm.outputs[2], mu.inputs[6])
        nt.links.new(cr.outputs["Color"], mu.inputs[7])
        nt.links.new(mu.outputs[2], pr.inputs["Base Color"])
        brume(m)
        me.materials.append(m)
    # au-delà du contexte : grand plan vert sombre
    me = bpy.data.meshes.new("loin")
    me.from_pydata([(-6000, -6000, -0.3), (6000, -6000, -0.3), (6000, 6000, -0.3), (-6000, 6000, -0.3)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("loin", me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat_unie("loin", (0.08, 0.16, 0.06)))


def panneaux(d):
    res = []
    for p in d["parcelles"]:
        me = bpy.data.meshes.new("pan_" + p["id"])
        me.from_pydata([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(name="UVMap")
        for lo, c in zip(me.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            uv.data[lo.index].uv = c
        ob = bpy.data.objects.new("pan_" + p["id"], me)
        bpy.context.scene.collection.objects.link(ob)
        m = bpy.data.materials.new("pan_" + p["id"])
        m.use_nodes = True
        nt = m.node_tree
        for nd in list(nt.nodes):
            nt.nodes.remove(nd)
        im = nt.nodes.new("ShaderNodeTexImage")
        im.image = bpy.data.images.load(str(T / f"panneau_{p['id']}.png"))
        em = nt.nodes.new("ShaderNodeEmission")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        so = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(im.outputs["Color"], em.inputs["Color"])
        nt.links.new(im.outputs["Alpha"], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], so.inputs["Surface"])
        m.surface_render_method = "BLENDED"
        me.materials.append(m)
        ob.visible_shadow = False
        res.append((ob, p))
    return res


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", choices=["A", "B", "C"], required=True)
    ap.add_argument("--pourcent", type=int, default=100)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--ech", type=int, default=24)
    ap.add_argument("--debut", type=int, default=1)
    ap.add_argument("--fin", type=int, default=0)
    ap.add_argument("--pas", type=int, default=1, help="ne rendre qu'une image sur pas (contrôles)")
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--glb", required=True, help="copie de bananiers.glb sans le remplissage d'octets nuls")
    ap.add_argument("--fils", type=int, default=4)
    ap.add_argument("--enregistrer", default="", help="chemin d'un .blend à écrire (sans rendu)")
    a = ap.parse_args(argv)
    t0 = time.time()
    plan, mode = a.plan, ("sante" if a.plan == "C" else "naturel")
    PLAN[0] = plan
    d, pl = lire_donnees()
    geo = rangee_et_allee(d, pl["bananiers"], "R050")
    print("allée R050 :", {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in geo.items()}, flush=True)
    tr = trajets(d, pl["bananiers"], geo)
    pos, cib, tem = tr[plan]
    duree = DUREES[plan]
    nimg = int(round(duree * a.fps))
    fin = a.fin or nimg
    # --- scène vide
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = a.pourcent
    sc.render.fps = a.fps
    sc.render.threads_mode = "FIXED"
    sc.render.threads = a.fils
    sc.eevee.taa_render_samples = a.ech
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = -0.3
    try:
        vs = sc.view_settings
        vs.use_curve_mapping = True
        cv = vs.curve_mapping.curves[3]
        cv.points.new(0.25, 0.19)
        cv.points.new(0.75, 0.82)
        vs.curve_mapping.update()
    except Exception as e:
        print("courbe :", e)
    try:
        sc.eevee.use_raytracing = False
        sc.eevee.use_fast_gi = False
    except Exception as e:
        print("eevee gi :", e)
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 94
    # monde : ciel bleu clair
    w = bpy.data.worlds.new("ciel")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    sk = w.node_tree.nodes.new("ShaderNodeTexSky")
    sk.sky_type = "SINGLE_SCATTERING"
    sk.sun_disc = False
    sk.sun_elevation = math.radians(20)
    sk.sun_rotation = math.radians(45)
    w.node_tree.links.new(sk.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.5
    sc.world = w
    sun = bpy.data.objects.new("soleil", bpy.data.lights.new("soleil", "SUN"))
    sun.data.energy = 3.8
    sun.data.color = (1.0, 0.886, 0.722)
    sun.data.angle = math.radians(0.5)
    sun.rotation_euler = (math.radians(70), 0.0, math.radians(-135))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    cam.data.lens = 26
    cam.data.clip_end = 3000
    cam.data.clip_start = 0.5
    sc.collection.objects.link(cam)
    sc.camera = cam
    sol(d, mode)
    contours(d)
    pans = panneaux(d)
    cols = charger_formes(a.glb)
    # --- plantes dans le voisinage de la trajectoire
    ech_t = np.linspace(0, duree, max(8, int(duree * 4)))
    chem = np.array([hermite(pos, tem, t) for t in ech_t])
    TIERS = [(0, 36.0), (1, 95.0), (2, 175.0), (3, 600.0 if plan == "A" else 340.0)]
    stats = {}
    for nom, jeu in (("bananiers", pl["bananiers"]), ("canne", pl["canne"])):
        X = np.c_[jeu["x"], jeu["y"]]
        dmin = np.full(len(X), 1e9)
        for p in chem:
            dh2 = (X[:, 0] - p[0]) ** 2 + (X[:, 1] - p[1]) ** 2
            dmin = np.minimum(dmin, np.sqrt(dh2 + (p[2] - 2.0) ** 2))
        dis = np.where(jeu["parcelle"] > 0, dmin, 1e9)  # seulement dans les parcelles de la zone
        jeu["d3"] = dis
        if nom == "canne":
            m = dis < (420 if plan == "A" else 230)
            pts = np.c_[jeu["x"][m], jeu["y"][m], np.zeros(m.sum())]
            ob = instancier("canne", pts, np.zeros(m.sum(), int), jeu["rot"][m], jeu["ech"][m], tuft_collection(jeu, m, mode))
            stats["canne"] = int(m.sum())
            continue
        lo = 0.0
        disj = dis * (1.0 + 0.3 * np.random.default_rng(11).uniform(-1, 1, len(dis)))
        for niv, hi in TIERS:
            m = (disj >= lo) & (disj < hi)
            lo = hi
            for var in (0, 1):
                mv = m & ((jeu["drap"] & 1) == var if mode == "sante" else (jeu["drap"] & 1) * 0 == var)
                k = int(mv.sum())
                if not k:
                    continue
                pts = np.c_[jeu["x"][mv], jeu["y"][mv], np.zeros(k)]
                instancier(f"ban_l{niv}_{var}", pts, jeu["forme"][mv] % N_FORMES, jeu["rot"][mv], jeu["ech"][mv], cols[(niv, var)])
                stats[f"ban_l{niv}_{var}"] = k
    print("instances :", stats, f"({time.time() - t0:.1f} s de préparation)", flush=True)
    if a.enregistrer:
        bpy.ops.wm.save_as_mainfile(filepath=a.enregistrer)
        return
    out = Path(a.sortie)
    out = out if out.is_absolute() else RACINE / out
    out.mkdir(parents=True, exist_ok=True)
    tps = []
    for f in range(a.debut, fin + 1, a.pas):
        fich = out / f"{f:04d}.jpg"
        if fich.exists():
            continue
        t = (f - 1) / a.fps
        p = hermite(pos, tem, t)
        c = hermite(cib, tem, t)
        cam.location = Vector(p)
        cam.rotation_euler = (Vector(c) - Vector(p)).to_track_quat("-Z", "Y").to_euler()
        for ob, par in pans:
            if par["id"] in ("R034", "R035"):
                ob.hide_render = True
                continue
            ax, ay = par["ancre"]
            dist = math.dist((ax, ay, 8.0), p)
            haut = max(p[2], 1.0)
            vis = min(1.0, max(0.0, (haut - 30.0) / 25.0))
            larg = min(max(0.26 * dist, 9.0), 62.0)
            ob.location = (ax, ay, 9.0 + larg * 0.2)
            ob.scale = (larg * vis, larg * 0.305 * vis, 1.0)
            ob.rotation_euler = cam.rotation_euler
            ob.hide_render = bool(vis < 0.02 or plan == "C")
        sc.render.filepath = str(fich)
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        tps.append(time.time() - t1)
        print(f"image {f}/{fin} : {tps[-1]:.1f} s", flush=True)
    if tps:
        print(f"moyenne {np.mean(tps):.1f} s par image", flush=True)


def tuft_collection(jeu, m, mode):
    """Collection d'une touffe de canne (une seule forme)."""
    c = collection_hors_scene("canne_touffe")
    me = bpy.data.meshes.new("touffe")
    bm = bmesh.new()
    rng = np.random.default_rng(3)
    for k in range(7):
        a = k / 7 * 2 * math.pi
        r0, r1, h = 0.12, 0.65, 2.3
        bx, by = r0 * math.cos(a), r0 * math.sin(a)
        tx, ty = r1 * math.cos(a), r1 * math.sin(a)
        wv = 0.16
        px, py = -math.sin(a) * wv, math.cos(a) * wv
        v = [bm.verts.new((bx - px, by - py, 0)), bm.verts.new((bx + px, by + py, 0)),
             bm.verts.new((tx * 0.6 + px * 0.4, ty * 0.6 + py * 0.4, h * 0.65)), bm.verts.new((tx * 0.6 - px * 0.4, ty * 0.6 - py * 0.4, h * 0.65))]
        bm.faces.new(v)
        v2 = [v[3], v[2], bm.verts.new((tx * 1.0, ty * 1.0, h))]
        bm.faces.new(v2)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_unie("canne", (0.42, 0.55, 0.14), rugosite=0.8))
    ob = bpy.data.objects.new("touffe", me)
    c.objects.link(ob)
    return c


main()
