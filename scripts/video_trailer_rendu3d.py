#!/usr/bin/env python3
"""Trailer Field Scan : rendu 3D des plans de drone (Blender, Eevee), heure dorée.

Ouvre en LECTURE la scène réaliste out/rendu_blender/v4/parcelle_bananiers.blend (rien n'y est réécrit), refait le
ciel et le soleil (lever de soleil, soleil bas et chaud), ajoute brume volumétrique, profondeur de champ et flou de
mouvement, puis rend un plan de drone image par image (trajectoires de caméra en splines de Catmull-Rom, accélérations
douces). Les images vont dans out/video_trailer/travail/<plan>/ ; l'étalonnage cinéma est fait ensuite par
scripts/video_trailer_etalonnage.py.

    blender.exe -b --factory-startup -P scripts/video_trailer_rendu3d.py -- --plan grue --fps 12 --ech 24
    blender.exe -b --factory-startup -P scripts/video_trailer_rendu3d.py -- --plan grue --tests 0,0.5,1 --larg 960 --haut 402

Plans : aube, rangs, orbite, fpv, grue, final (voir PLANS plus bas).
"""
import argparse
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_trailer_monde as monde  # noqa: E402
from mathutils import Euler, Quaternion, Vector

RACINE = Path(__file__).resolve().parents[1]
BLEND = RACINE / "out/rendu_blender/v4/parcelle_bananiers.blend"
PLANTS = RACINE / "out/rendu_blender/v4/plants.csv"
SORTIE = RACINE / "out/video_trailer/travail"
FPS_FILM = 24
FORCE_CIEL = 0.12
VTILE, VSAMPLES, VSHADOW, VEND = "8", 32, False, 250.0
ENERGIE_SOLEIL = 18.0
EE_EXTRA = ""
DEPTH_BRUME = 8000.0
DENSITE_MONDE = 0.0016
DENSITE_NAPPE = 0.045


# ----------------------------------------------------------------------------------------------------- trajectoires
def catmull(pts, u):
    """Spline de Catmull-Rom (uniforme) passant par pts, u dans [0, 1]."""
    p = [np.asarray(q, float) for q in pts]
    n = len(p) - 1
    x = min(max(u, 0.0), 1.0) * n
    i = min(int(x), n - 1)
    t = x - i
    p0, p1, p2, p3 = p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, n)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def doux(u, k=1.0):
    """Accélération douce : k = 0 linéaire, k = 1 lisse (smoothstep), k = 2 très lisse (smootherstep)."""
    u = min(max(u, 0.0), 1.0)
    s = u * u * (3 - 2 * u)
    s2 = u ** 3 * (u * (6 * u - 15) + 10)
    return u + (s - u) * min(k, 1) + (s2 - s) * max(k - 1, 0)


def couloir(plants):
    """Cherche une allée droite entre deux rangs : (point de départ, direction unitaire) qui traverse la parcelle en
    évitant au mieux les pieds (distance minimale maximale)."""
    meilleur = (-1, None, None)
    for ang in np.arange(0, 180, 3):
        t = math.radians(ang)
        d = np.array([math.cos(t), math.sin(t)])
        n = np.array([-d[1], d[0]])
        for off in np.arange(-14, 14, 0.4):
            c = n * off
            rel = plants - c
            along = rel @ d
            perp = np.abs(rel @ n)
            sel = np.abs(along) < 26
            dmin = perp[sel].min() if sel.any() else 99
            if dmin > meilleur[0]:
                meilleur = (dmin, c, d)
    return meilleur


# ------------------------------------------------------------------------------------------------------------- plans
def definir_plans(plants):
    dmin, c, d = couloir(plants)
    n = np.array([-d[1], d[0]])
    print(f"couloir : distance minimale aux pieds {dmin:.2f} m, direction {d}", flush=True)

    def sur_couloir(s, h, lat=0.0):
        p = c + d * s + n * lat
        return (p[0], p[1], h)

    P = {}
    # aube : travelling latéral bas au bord de la parcelle, brume, soleil rasant dans le champ, mise au point glissante
    P["aube"] = dict(duree=5.5, soleil=(250, 9), focale=35, fstop=2.0, ease=1.0,
                     cam=[(-52, -46, 1.1), (-50, -30, 1.25), (-47, -12, 1.4), (-46, 8, 1.55), (-47, 28, 1.7)],
                     cible=[(-30, -30, 2.0), (-29, -14, 2.4), (-28, 4, 2.6), (-27, 22, 2.8), (-28, 40, 3.0)],
                     focus=[(-52 + 0, 0)], foc_pts=[8.0, 12.0, 16.0], roll=[0, 1.5, 0])
    # rangs : travelling bas entre deux rangs, profondeur de champ
    P["rangs"] = dict(duree=4.5, obt=0.25, soleil=(250, 10), focale=24, fstop=2.4, ease=0.6,
                      cam=[sur_couloir(-28, 1.15), sur_couloir(-12, 1.25), sur_couloir(6, 1.35), sur_couloir(24, 1.5)],
                      cible=[sur_couloir(-14, 1.9), sur_couloir(2, 2.0), sur_couloir(20, 2.2), sur_couloir(40, 2.4)],
                      foc_pts=[9.0, 11.0, 13.0], roll=[-1.0, 0, 1.0])
    # orbite : plongée verticale qui tourne doucement
    P["orbite"] = dict(duree=4.5, soleil=(250, 12), focale=30, fstop=8, ease=1.0, vertical=True,
                       cam=[(0, 0, 105), (0, 0, 92), (0, 0, 78)], cible=[(0, 0, 0)] * 3, roll=[0, 0, 0],
                       tour=(-35.0, 25.0))      # degrés : rotation de la caméra autour de l'axe vertical
    # fpv : survol rapide façon drone de course, bas, entre les rangs puis au ras des feuilles
    P["fpv"] = dict(duree=3.2, obt=0.2, soleil=(250, 10), focale=16, fstop=5.6, ease=0.0,
                    cam=[sur_couloir(-40, 2.4, 1.2), sur_couloir(-20, 1.9, -0.8), sur_couloir(-2, 2.3, 0.8),
                         sur_couloir(18, 2.0, -0.6), sur_couloir(40, 2.7, 0.4)],
                    cible=[sur_couloir(-20, 2.1, 0.0), sur_couloir(0, 2.2, 0.0), sur_couloir(20, 2.3, 0.0),
                           sur_couloir(40, 2.4, 0.0), sur_couloir(62, 2.6, 0.0)],
                    foc_pts=[14.0, 14.0, 14.0], roll=[-5, 7, -6, 6, -3], flou=1.0)
    # grue : révélation, on monte au-dessus des feuilles et la plantation apparaît jusqu'à l'horizon
    P["grue"] = dict(duree=10.0, arbres_parcelle=False, soleil=(295, 10), focale=28, fstop=2.8, ease=1.5,
                     cam=[(-14, -40, 1.5), (-16, -44, 4.5), (-24, -58, 14), (-34, -92, 34), (-44, -150, 62)],
                     cible=[(-6, -4, 3.5), (-6, -2, 3.0), (-4, 6, 2.0), (-2, 90, 4.0), (0, 520, 40.0)],
                     foc_pts=[26.0, 28.0, 70.0, 150.0, 300.0], roll=[0, 0, 0, 0, 0])
    # final : grand plan large sous le titre, glissement latéral à 40 m, soleil dans le cadre
    P["final"] = dict(duree=7.0, soleil=(295, 9), focale=26, fstop=8, ease=0.8, arbres_parcelle=False,
                      cam=[(-60, -130, 24), (-50, -118, 27), (-40, -105, 30)],
                      cible=[(-10, 420, 22), (-4, 420, 24), (4, 420, 26)], foc_pts=[300.0, 300.0, 300.0],
                      roll=[-1.0, 0, 1.0])
    # descente : de la vue zénithale (raccord avec la photo réelle) à l'allée, la caméra s'incline et plonge
    P["descente"] = dict(duree=5.0, soleil=(250, 11), focale=30, fstop=5.6, ease=1.0, arbres_parcelle=False,
                         cam=[(0, -5, 110), (-3, -14, 80), (-8, -26, 40), (-11, -34, 12), (-12, -37, 2.4)],
                         cible=[(0, -4.9, 0), (0, -6, 0), (-2, 2, 1), (-3, 14, 2.5), (-4, 30, 3.0)],
                         foc_pts=[110.0, 85.0, 45.0, 30.0, 14.0], roll=[0, 0, 0, 0, 0])
    # oblique : vol en diagonale à 22 m au-dessus des bananiers, regard incliné vers l'avant
    P["oblique"] = dict(duree=2.9, obt=0.3, soleil=(250, 10), focale=24, fstop=8, ease=0.4, arbres_parcelle=False,
                        cam=[(62, -84, 24), (36, -52, 22), (12, -22, 20)],
                        cible=[(-6, 20, 2), (-8, 26, 2), (-10, 32, 2)], foc_pts=[60.0, 50.0, 40.0], roll=[-2, 0, 2])
    # contre-plongée : très bas dans l'allée, regard vers le soleil à travers les feuilles
    P["contre"] = dict(duree=2.1, obt=0.25, soleil=(250, 11), focale=22, fstop=2.8, ease=0.3,
                       cam=[sur_couloir(12, 0.8, 0.0), sur_couloir(-2, 0.85, 0.0)],
                       cible=[sur_couloir(-30, 5.5, -9.0), sur_couloir(-36, 6.5, -9.0)], foc_pts=[9.0, 7.0], roll=[3, -2])
    return P


# ------------------------------------------------------------------------------------------------------------ scène
def preparer_scene(plan, larg, haut, ech, fils, brume=True):
    sc = bpy.context.scene
    az, el = plan["soleil"]
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = larg, haut, 100
    sc.render.fps, sc.render.fps_base = FPS_FILM, 1.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.threads_mode = "FIXED"
    sc.render.threads = fils
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    ee = sc.eevee
    ee.taa_render_samples = ech
    for nom, val in (("use_raytracing", True), ("ray_tracing_method", "SCREEN"), ("use_shadows", True),
                     ("shadow_ray_count", 2), ("shadow_step_count", 6), ("use_fast_gi", True),
                     ("fast_gi_method", "GLOBAL_ILLUMINATION"), ("fast_gi_distance", 4.0), ("fast_gi_ray_count", 2),
                     ("fast_gi_step_count", 6), ("use_volumetric_shadows", VSHADOW), ("volumetric_tile_size", VTILE),
                     ("volumetric_samples", VSAMPLES), ("volumetric_end", VEND), ("use_volume_custom_range", True),
                     ("volumetric_start", 0.5), ("motion_blur_steps", 6)):
        if hasattr(ee, nom):
            try:
                setattr(ee, nom, val)
            except (TypeError, ValueError) as e:
                print("réglage Eevee ignoré", nom, val, e)
    for kv in (EE_EXTRA.split(",") if EE_EXTRA else []):
        k, v = kv.split("=")
        cur = getattr(ee, k)
        setattr(ee, k, type(cur)(int(v)) if isinstance(cur, bool) else type(cur)(v))
    opt = ee.ray_tracing_options
    for nom, val in (("resolution_scale", "2"), ("use_denoise", True)):
        try:
            setattr(opt, nom, val)
        except (TypeError, ValueError):
            pass
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = plan.get("obt", 0.35)
    # ciel et soleil de l'heure dorée
    w = sc.world
    nt = w.node_tree
    sky = [n for n in nt.nodes if n.bl_idname == "ShaderNodeTexSky"][0]
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_size = math.radians(1.2)
    sky.sun_intensity = 1.0
    sky.sun_elevation = math.radians(el)
    sky.sun_rotation = math.radians(90 - az)
    sky.air_density = 1.4
    sky.aerosol_density = 1.6
    fond = [n for n in nt.nodes if n.bl_idname == "ShaderNodeBackground"][0]
    fond.inputs["Strength"].default_value = FORCE_CIEL
    sun = bpy.data.objects["soleil"]
    a, e = math.radians(az), math.radians(el)
    dirv = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = dirv.to_track_quat("Z", "Y")
    sun.data.energy = ENERGIE_SOLEIL
    sun.data.color = (1.0, 0.706, 0.42)           # #FFB46B
    sun.data.angle = math.radians(0.9)
    sun.data.use_shadow = True
    if hasattr(sun.data, "shadow_maximum_resolution"):
        sun.data.shadow_maximum_resolution = 0.004
    if hasattr(sun.data, "volume_factor"):
        sun.data.volume_factor = 1.0
    if brume in ("monde", "tout"):
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Color"].default_value = (1.0, 0.86, 0.7, 1)
        vol.inputs["Density"].default_value = DENSITE_MONDE
        vol.inputs["Anisotropy"].default_value = 0.55
        sortie = [n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputWorld"][0]
        nt.links.new(vol.outputs["Volume"], sortie.inputs["Volume"])
    if brume in ("nappe", "tout"):
        # brume : volume du monde (haleine de l'air) + nappe basse au ras du sol, diffusion vers l'avant (rayons)
        mesh = bpy.data.meshes.new("nappe")
        bpy.ops.object.select_all(action="DESELECT")
        ob = bpy.data.objects.new("nappe", mesh)
        sc.collection.objects.link(ob)
        s = 160.0
        v = [(-s, -s, -1), (s, -s, -1), (s, s, -1), (-s, s, -1), (-s, -s, 7), (s, -s, 7), (s, s, 7), (-s, s, 7)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        mesh.from_pydata(v, [], f)
        m = bpy.data.materials.new("nappe_brume")
        m.use_nodes = True
        mt = m.node_tree
        for nd in list(mt.nodes):
            mt.nodes.remove(nd)
        out = mt.nodes.new("ShaderNodeOutputMaterial")
        pv = mt.nodes.new("ShaderNodeVolumePrincipled")
        bruit = mt.nodes.new("ShaderNodeTexNoise")
        bruit.inputs["Scale"].default_value = 0.035
        bruit.inputs["Detail"].default_value = 2.0
        coord = mt.nodes.new("ShaderNodeTexCoord")
        mt.links.new(coord.outputs["Object"], bruit.inputs["Vector"])
        # densité : plus forte près du sol (z objet de -1 à 7 m), modulée par le bruit
        sep = mt.nodes.new("ShaderNodeSeparateXYZ")
        mt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
        mr = mt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = -1.0
        mr.inputs["From Max"].default_value = 7.0
        mr.inputs["To Min"].default_value = 1.0
        mr.inputs["To Max"].default_value = 0.0
        mt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        mul = mt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mt.links.new(mr.outputs["Result"], mul.inputs[0])
        mt.links.new(bruit.outputs["Fac"], mul.inputs[1])
        mul2 = mt.nodes.new("ShaderNodeMath")
        mul2.operation = "MULTIPLY"
        mul2.inputs[1].default_value = DENSITE_NAPPE
        mt.links.new(mul.outputs["Value"], mul2.inputs[0])
        mt.links.new(mul2.outputs["Value"], pv.inputs["Density"])
        pv.inputs["Color"].default_value = (1.0, 0.9, 0.78, 1)
        pv.inputs["Anisotropy"].default_value = 0.5
        mt.links.new(pv.outputs["Volume"], out.inputs["Volume"])
        mesh.materials.append(m)
        ob.visible_shadow = False
        ob.display_type = "WIRE"
    return sc


def compositeur(dossier):
    """Écrit l'image (PNG 16 bits) et la passe de brume (distance, PNG 16 bits) avec des noeuds File Output."""
    sc = bpy.context.scene
    sc.view_layers[0].use_pass_mist = True
    ms = sc.world.mist_settings
    ms.start, ms.depth, ms.falloff = 0.0, DEPTH_BRUME, "LINEAR"
    ng = bpy.data.node_groups.new("comp_trailer", "CompositorNodeTree")
    sc.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    fo = ng.nodes.new("CompositorNodeOutputFile")
    fo.directory = str(dossier)
    fo.file_name = "img_"
    fo.format.media_type = "IMAGE"
    fo.format.file_format = "PNG"
    fo.format.color_depth = "16"
    fo.format.color_mode = "RGB"
    it = fo.file_output_items
    it.clear()
    it.new("RGBA", "image")
    it.new("FLOAT", "brume")
    ng.links.new(rl.outputs["Image"], fo.inputs[0])
    ng.links.new(rl.outputs["Mist"], fo.inputs[1])
    return fo


def camera_et_animation(plan, frames, fps_rendu, centre_plans):
    """Une caméra, une pose par image rendue (interpolation linéaire entre poses : le flou de mouvement en dépend)."""
    sc = bpy.context.scene
    cam = bpy.data.objects["camera_drone"]
    cam.animation_data_clear()
    cam.parent = None
    cd = cam.data
    cd.lens = plan["focale"]
    cd.sensor_width = 36
    cd.sensor_fit = "HORIZONTAL"
    cd.clip_start, cd.clip_end = 0.1, 9000
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = plan["fstop"]
    cd.dof.aperture_blades = 7
    sc.camera = cam
    cam.rotation_mode = "QUATERNION"
    duree = plan["duree"]
    n_tot = int(round(duree * fps_rendu))
    for f in frames:
        u = (f - 1) / max(n_tot - 1, 1)
        s = doux(u, plan["ease"])
        pos = catmull(plan["cam"], s)
        cible = catmull(plan["cible"], s)
        if plan.get("vertical"):
            t = math.radians(plan["tour"][0] + (plan["tour"][1] - plan["tour"][0]) * s)
            q = Quaternion((0, 0, 1), t) @ Quaternion((1, 0, 0), 0)      # regard vers -Z, tourné autour de Z
            cam.location = tuple(pos)
            cam.rotation_quaternion = q
        else:
            dirv = Vector(cible - pos)
            q = dirv.to_track_quat("-Z", "Y")
            roll = math.radians(float(np.interp(s, np.linspace(0, 1, len(plan["roll"])), plan["roll"])))
            q = q @ Quaternion((0, 0, -1), roll)
            cam.location = tuple(pos)
            cam.rotation_quaternion = q
        fp = float(np.interp(s, np.linspace(0, 1, len(plan.get("foc_pts", [30.0]))), plan.get("foc_pts", [30.0])))
        cd.dof.focus_distance = fp
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cd.dof.keyframe_insert("focus_distance", frame=f)
    for fc in (cam.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
               if hasattr(cam.animation_data.action, "layers") else cam.animation_data.action.fcurves):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--fps", type=int, default=12, help="cadence de rendu (12 ou 24)")
    ap.add_argument("--ech", type=int, default=24, help="échantillons Eevee")
    ap.add_argument("--larg", type=int, default=1920)
    ap.add_argument("--haut", type=int, default=804)
    ap.add_argument("--fils", type=int, default=4)
    ap.add_argument("--tests", help="fractions de la durée, ex. 0,0.5,1 : images fixes d'essai")
    ap.add_argument("--debut", type=int, default=1)
    ap.add_argument("--fin", type=int, default=0)
    ap.add_argument("--sortie", default=None)
    ap.add_argument("--brume", default="aucune", choices=["aucune", "monde", "nappe", "tout"])
    ap.add_argument("--vtile", default="8")
    ap.add_argument("--vech", type=int, default=32)
    ap.add_argument("--vombre", type=int, default=0)
    ap.add_argument("--vfin", type=float, default=250.0)
    ap.add_argument("--ciel", type=float, default=0.05)
    ap.add_argument("--energie", type=float, default=22.0)
    ap.add_argument("--dm", type=float, default=0.0016)
    ap.add_argument("--dn", type=float, default=0.045)
    ap.add_argument("--soleil", help="azimut,élévation (degrés), remplace celui du plan")
    ap.add_argument("--sans-domaine", action="store_true")
    ap.add_argument("--ee", default="use_raytracing=0")
    ap.add_argument("--duree", type=float, default=0, help="remplace la durée du plan (s)")
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    plants = np.genfromtxt(PLANTS, delimiter=",", names=True)
    plants = np.stack([plants["x_m"], plants["y_m"]], 1)
    global EE_EXTRA
    EE_EXTRA = a.ee
    global DENSITE_MONDE, DENSITE_NAPPE, FORCE_CIEL, ENERGIE_SOLEIL
    FORCE_CIEL, ENERGIE_SOLEIL = a.ciel, a.energie
    global VTILE, VSAMPLES, VSHADOW, VEND
    VTILE, VSAMPLES, VSHADOW, VEND = a.vtile, a.vech, bool(a.vombre), a.vfin
    DENSITE_MONDE, DENSITE_NAPPE = a.dm, a.dn
    plan = definir_plans(plants)[a.plan]
    if a.duree:
        plan["duree"] = a.duree
    if a.soleil:
        plan["soleil"] = tuple(float(x) for x in a.soleil.split(","))
    n_tot = int(round(plan["duree"] * a.fps))
    sc = preparer_scene(plan, a.larg, a.haut, a.ech, a.fils, brume=a.brume)
    chemin = np.array([catmull(plan["cam"], u) for u in np.linspace(0, 1, 40)])
    if not a.sans_domaine:
        monde.construire(plants, chemin, masquer_arbres_parcelle=not plan.get("arbres_parcelle", False))
    sc.render.motion_blur_shutter = plan.get("obt", 0.35)
    if a.tests:
        fr = sorted({1 + int(round(float(x) * (n_tot - 1))) for x in a.tests.split(",")})
        camera_et_animation(plan, fr, a.fps, None)
        sortie = Path(a.sortie).resolve() if a.sortie else SORTIE / f"test_{a.plan}"
        sortie.mkdir(parents=True, exist_ok=True)
        fo = compositeur(sortie)
        for f in fr:
            t = time.time()
            sc.frame_set(f)
            fo.file_name = f"{f:04d}_"
            bpy.ops.render.render()
            print(f"IMAGE {a.plan} {f}/{n_tot} : {time.time() - t:.1f} s", flush=True)
        return
    fin = a.fin or n_tot
    frames = list(range(a.debut, fin + 1))
    camera_et_animation(plan, list(range(1, n_tot + 1)), a.fps, None)
    sortie = Path(a.sortie).resolve() if a.sortie else SORTIE / f"{a.plan}_{a.fps}"
    sortie.mkdir(parents=True, exist_ok=True)
    sc.render.use_persistent_data = True
    fo = compositeur(sortie)
    t0 = time.time()
    for f in frames:
        cible = sortie / f"{f:04d}_image.png"
        if cible.exists():
            continue
        t = time.time()
        sc.frame_set(f)
        fo.file_name = f"{f:04d}_"
        bpy.ops.render.render()
        print(f"IMAGE {a.plan} {f}/{n_tot} : {time.time() - t:.1f} s (cumul {time.time() - t0:.0f} s)", flush=True)


main()
