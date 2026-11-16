"""Scène Blender de la parcelle, version 2 : un bananier procédural sur chaque centre détecté par le comptage v5
(plants.csv, mosaïque de tuiles d'entraînement Flora Pluas), sol de bananeraie procédural, terrain jusqu'à
l'horizon, lisière d'arbres, ciel physique ; rendus Cycles sur processeur.

Entrées (écrites par scripts/rendu_preparer.py dans --donnees) : plants.csv, tuile.png, donnees_rendu.json.

Ce qui vient des données : la position de chaque pied (détecteur v5) et, en mode « sante », la teinte des
feuilles (ExG drone réel de la chaîne, écart à la médiane de la parcelle). Tout le reste est illustratif : forme
des bananiers (24 plants types tirés au hasard, puis tournés et mis à l'échelle), rejets, régimes, sol, herbe,
feuilles au sol, terrain, arbres, ciel.

Modes :
  - naturel : couleurs de feuilles procédurales ;
  - sante   : feuilles teintées par la vigueur RÉELLE de la chaîne. Aucune zone d'alerte ne touche la mosaïque :
              la teinte montre une mesure relative, pas une alerte.
Vues : drone (oblique, avec l'horizon), proche (un pied du bord sud et ses rejets, à hauteur d'homme),
dessus (orthographique, même cadrage que la mosaïque réelle), photo (oblique, photo réelle au sol, pour mémoire),
survol (animation : la caméra tourne autour de la parcelle).

Exemple :
    blender.exe -b --factory-startup -t 6 -P scripts/blender_scene.py -- --vue drone --mode naturel --echantillons 64
"""
import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_bananier as bb  # noqa: E402
import blender_decor as bd  # noqa: E402

# couleurs du bulletin (fieldscan/bulletin.py, COULEURS) pour les extrémités de l'échelle, jaune au milieu
ORANGE, JAUNE, VERT = "#ef6c00", "#e8c547", "#2e7d32"
ECART_BAS, ECART_HAUT = -0.05, 0.06   # écart ExG (pied - médiane de la parcelle) aux extrémités de l'échelle
N_TYPES = 48                          # plants types (formes procédurales), réutilisés par instances liées


def lineaire(hexa):
    c = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def couleur_ecart(e):
    """Échelle continue orange -> jaune -> vert selon l'écart ExG à la médiane de la parcelle."""
    if e != e:                                                     # NaN : gris
        return [0.2, 0.2, 0.2]
    if e <= 0:
        t = min(max((e - ECART_BAS) / (0 - ECART_BAS), 0), 1)
        a, b = lineaire(ORANGE), lineaire(JAUNE)
    else:
        t = min(max(e / ECART_HAUT, 0), 1)
        a, b = lineaire(JAUNE), lineaire(VERT)
    return [a[i] + (b[i] - a[i]) * t for i in range(3)]


def lire_plants(chemin):
    with open(chemin, encoding="utf-8") as f:
        return [dict(id=int(r["id"]), x=float(r["x_m"]), y=float(r["y_m"]),
                     ecart=float(r["exg_ecart_parcelle"]) if r["exg_ecart_parcelle"] else float("nan"))
                for r in csv.DictReader(f)]


def choisir_heros(plants, demi):
    """Plant de la vue rapprochée : sur le bord sud (caméra hors de la parcelle, rien devant), le plus dégagé,
    pas trop loin du milieu du bord."""
    xy = np.array([[p["x"], p["y"]] for p in plants])
    d = np.linalg.norm(xy[:, None] - xy[None], axis=2) + np.eye(len(xy)) * 99
    meilleur, note = None, -1e9
    for i, p in enumerate(plants):
        if p["y"] > -demi + 2.5 or abs(p["x"]) > demi * 0.5:
            continue
        devant = [j for j in range(len(plants)) if plants[j]["y"] < p["y"] - 0.5 and abs(plants[j]["x"] - p["x"]) < 3]
        n = d[i].min() - 2.0 * len(devant) - 0.05 * abs(p["x"])
        if n > note:
            meilleur, note = i, n
    return meilleur


def types_de_plants(mats):
    """Bibliothèque de N_TYPES bananiers (graines fixes) : maillages non liés à la scène, instanciés ensuite."""
    types = []
    for k in range(N_TYPES):
        r = np.random.default_rng(500 + k)
        par = dict(H=float(r.uniform(2.3, 3.3)), n_feuilles=int(r.integers(8, 13)),
                   n_epees=int(r.choice([0, 1, 1, 2, 2, 3])), fils=bool(r.random() < 0.45),
                   avec_regime=bool(r.random() < 0.3))
        m = bb.Maillage()
        bb.plant_et_rejets(m, (0, 0, 0), r, **par)
        ob = m.objet(f"bananier_type_{k:02d}", mats, None)
        types.append((ob.data, par))
    return types


def construire(donnees, mode, vue, simple=False, echelle_plants=1.0):
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    info = json.loads((donnees / "donnees_rendu.json").read_text(encoding="utf-8"))
    demi = info["cote_px"][0] * info["resolution_m"] / 2
    plants = lire_plants(donnees / "plants.csv")
    heros = choisir_heros(plants, demi)
    xy = np.array([[p["x"], p["y"]] for p in plants])
    dist = np.linalg.norm(xy[:, None] - xy[None], axis=2) + np.eye(len(xy)) * 99
    bd.D_BRUME = 1e9 if vue == "dessus" else 2600.0
    bd.DENSITE_LISIERE = 0.25 if vue == "survol" else 1.0          # survol (EEVEE) : lisière allégée
    bd.ECLAT_AGRO = 0.65 if vue == "survol" else 0.85             # EEVEE éclaircit les couverts : compensé
    mats = bb.materiaux()
    col = bpy.data.collections.new("bananiers")
    sc.collection.children.link(col)
    t0 = time.time()
    types = types_de_plants(mats)
    n_sommets_types = sum(len(me.vertices) for me, _ in types)
    stats = dict(regimes=0, fils=0, epees=0)
    p_h = plants[heros]
    cam_proche = (p_h["x"] + 1.6, p_h["y"] - 6.2)
    for i, p in enumerate(plants):
        rng = np.random.default_rng(1000 + p["id"])
        voisin = dist[i].min()
        s = float(np.clip(0.78 + 0.12 * (voisin - 1.5), 0.8, 1.05) * rng.uniform(0.95, 1.05)) * echelle_plants
        if i == heros:                                              # plant unique, tourné vers la caméra proche
            az = math.atan2(cam_proche[1] - p["y"], cam_proche[0] - p["x"])
            m = bb.Maillage()
            par = dict(H=2.9, n_feuilles=11, n_epees=2, fils=True, avec_regime=True)
            bb.plant_et_rejets(m, (0, 0, 0), np.random.default_rng(7), **par,
                               azimut_rejets=[az - 0.9, az + 0.7, az + 2.4], az_regime=az + 0.35)
            ob = m.objet(f"bananier_{p['id']:03d}", mats, col)
            ob.scale = (s, s, s)
        else:
            me, par = types[int(rng.integers(N_TYPES))]
            ob = bpy.data.objects.new(f"bananier_{p['id']:03d}", me)
            col.objects.link(ob)
            ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
            ob.scale = (s, s, s * rng.uniform(0.95, 1.05))
        ob.location = (p["x"], p["y"], 0.0)
        ob.color = (*couleur_ecart(p["ecart"]), 1.0)
        ob["exg_ecart_parcelle"] = p["ecart"]
        ob["regime_illustratif"] = par["avec_regime"]
        ob["rejets_illustratifs"] = par["n_epees"] + int(par["fils"])
        stats["regimes"] += par["avec_regime"]
        stats["fils"] += par["fils"]
        stats["epees"] += par["n_epees"]
    print(f"{len(plants)} bananiers ({N_TYPES} types, {n_sommets_types} sommets uniques) en {time.time() - t0:.1f} s ; "
          f"héros : {p_h['id']} ; illustratif : {stats}")
    bb.regler_sante(mats, 0.65 if mode == "sante" else 0.0)

    # décor
    t0 = time.time()
    rng = np.random.default_rng(42)
    bd.terrain(demi, rng)
    centres = np.c_[xy, np.zeros(len(xy))]
    if not simple:
        bd.litiere(centres, rng, mats, par_plant=2.0)
        mat_h = bd.materiau_herbe()
        pts = bd.points_herbe(int((2 * demi) ** 2 * 0.9), (-demi, demi, -demi, demi), rng, centres, 0.55)
        bd.herbe(pts, rng, mat_h, hauteur=(0.08, 0.3), brins=(4, 8), nom="herbe_parcelle")
        if vue in ("proche", "heros"):                             # prairie dense devant la caméra rapprochée
            cx, cy = cam_proche
            pts = bd.points_herbe(45000, (cx - 14, cx + 14, -demi - 12, -demi + 0.8), rng)
            dcam = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
            pts = pts[rng.random(len(pts)) < np.clip(1.3 - dcam / 13, 0.05, 1)]
            pts = pts[np.maximum(np.abs(pts[:, 0]), np.abs(pts[:, 1])) > demi + 0.6 - 1.2 * rng.random(len(pts))]
            pts = pts[np.abs(pts[:, 1] + 37.8) > 1.6 + 0.4 * rng.random(len(pts))]   # pas d'herbe sur la piste sud
            bd.herbe(pts, rng, mat_h, hauteur=(0.12, 0.5), brins=(6, 12), nom="herbe_bord")
    col_a = bpy.data.collections.new("lisiere")
    sc.collection.children.link(col_a)
    n_arbres = bd.lisiere(demi, rng, col_a)
    # bordures de champs (haies) et pistes de terre : décor
    n_arbres += bd.haies(rng, col_a, demi, bd.BUISSONS)
    mat_c = bd.materiau_chemin()
    bd.chemin([(-170, -38.5), (-60, -38.0), (0, -37.6), (60, -38.2), (170, -40)], 3.6, "piste_sud", mat_c)
    bd.chemin([(-39.5, -38.0), (-39.0, 0), (-40.5, 60), (-46, 130), (-60, 200)], 3.2, "piste_ouest", mat_c)
    # arbres d'agroforesterie illustratifs, aux zones non-bananier repérées sur la photo (scripts/rendu_arbres.py)
    n_agro = 0
    if (donnees / "arbres_photo.csv").exists():
        with open(donnees / "arbres_photo.csv", encoding="utf-8") as f:
            lignes = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
        col_p = bpy.data.collections.new("arbres_parcelle")
        sc.collection.children.link(col_p)
        n_agro = bd.arbres_parcelle(lignes, col_p, [bd.materiau_arbre(), bd.materiau_ecorce()])
    if vue == "dessus":                                            # comparaison avec la photo : soleil haut, neutre
        bd.ciel(elevation=60.0, azimut=-100.0, energie_soleil=4.5)
    else:                                                          # fin d'après-midi tropicale : soleil bas, chaud
        # azimut propre à la vue : lumière de côté pour la vue de drone (caméra au sud-ouest), de trois quarts
        # arrière pour la vue rapprochée (caméra au sud, regard vers le nord)
        az = {"proche": -128.0, "heros": -128.0}.get(vue, -82.0)
        bd.ciel(elevation=24.0, azimut=az, energie_soleil=5.2, couleur=(1.0, 0.83, 0.64), force_ciel=0.13)
    if vue != "dessus":
        bd.nuages()
    print(f"décor (terrain, sol, herbe, {n_arbres} arbres de lisière, {n_agro} arbres d'agroforesterie) en {time.time() - t0:.1f} s")
    return plants, heros, demi, cam_proche


def photo_au_sol(donnees, demi):
    """Variante « photo » : la mosaïque réelle plaquée au sol, à l'échelle (5 cm/px), au-dessus du terrain."""
    sc = bpy.context.scene
    h = demi
    me = bpy.data.meshes.new("mosaique")
    me.from_pydata([(-h, -h, 0.01), (h, -h, 0.01), (h, h, 0.01), (-h, h, 0.01)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    ob = bpy.data.objects.new("mosaique_reelle", me)
    sc.collection.objects.link(ob)
    ma = bpy.data.materials.new("mosaique")
    ma.use_nodes = True
    nt = ma.node_tree
    p = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(donnees / "tuile.png"))
    tex.interpolation = "Cubic"
    teinte = nt.nodes.new("ShaderNodeHueSaturation")
    teinte.inputs["Value"].default_value = 0.8                     # photo déjà éclairée : un peu assombrie
    nt.links.new(tex.outputs["Color"], teinte.inputs["Color"])
    nt.links.new(teinte.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.95
    me.materials.append(ma)
    for nom in ("herbe_parcelle", "feuilles_au_sol"):
        o = bpy.data.objects.get(nom)
        if o is not None:
            bpy.data.objects.remove(o)


def camera(vue, plants, heros, demi, cam_proche, largeur, hauteur):
    sc = bpy.context.scene
    cam = bpy.data.objects.new("camera_" + vue, bpy.data.cameras.new("camera_" + vue))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.clip_end = 8000
    cam.data.sensor_width = 36
    if vue in ("drone", "photo"):
        cam.data.lens = 28
        cam.location = (-0.62 * demi * 2, -1.05 * demi * 2, 0.41 * demi * 2)
        bb.viser(cam, (0.14 * demi * 2, 0.44 * demi * 2, 0.0))
    elif vue == "proche":
        p = plants[heros]
        cam.data.lens = 20
        cam.location = (cam_proche[0], cam_proche[1], 1.55)
        bb.viser(cam, (p["x"] - 0.3, p["y"], 2.75))
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = math.hypot(cam_proche[0] - p["x"], cam_proche[1] - p["y"])
        cam.data.dof.aperture_fstop = 5.6
    elif vue == "heros":                                          # image de soutenance : plus large, plus de ciel
        p = plants[heros]
        cam.data.lens = 22
        cam.location = (cam_proche[0] + 1.2, cam_proche[1] - 2.6, 1.75)
        bb.viser(cam, (p["x"] - 0.8, p["y"] + 2.0, 3.1))
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = math.hypot(cam.location[0] - p["x"], cam.location[1] - p["y"])
        cam.data.dof.aperture_fstop = 8.0
    elif vue == "dessus":
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 2 * demi
        cam.location = (0, 0, 120)
        cam.rotation_euler = (0, 0, 0)
        largeur = hauteur = min(largeur, hauteur)
    elif vue == "survol":
        survol(cam, demi)
    sc.render.resolution_x, sc.render.resolution_y = largeur, hauteur
    sc.render.resolution_percentage = 100
    return cam


# survol : la partie 3D commence à l'image SURVOL_DEBUT (avant : la photo réelle, composée en 2D par
# scripts/rendu_survol.py) ; caméra d'abord à la verticale, nord en haut, emprise au sol de SURVOL_EMPRISE m de large
SURVOL_IMAGES, SURVOL_DEBUT, SURVOL_EMPRISE, SURVOL_FOCALE = 300, 49, 60.0, 35.0
FAST_GI = True                        # EEVEE : balayage d horizon (GI/occlusion) ; coûteux sur la carte intégrée


def survol_pose(t):
    """Pose de la caméra au temps t (0 = verticale au-dessus du centre, 1 = travelling oblique au-dessus des rangs) :
    position sur une courbe de Bézier cubique, cible interpolée, avec douceur aux deux bouts."""
    e = t * t * (3 - 2 * t)
    h0 = SURVOL_EMPRISE * SURVOL_FOCALE / 36.0
    P = [np.array(v, float) for v in ((0, 0, h0), (0, -26, h0 * 0.85), (-12, -46, 21), (-5, -20, 13))]
    pos = sum(c * w for c, w in zip(P, ((1 - e) ** 3, 3 * (1 - e) ** 2 * e, 3 * (1 - e) * e ** 2, e ** 3)))
    cible = np.array([0, 0, 0]) * (1 - e) + np.array([2, 30, 1.5]) * e
    return pos, cible


def survol(cam, demi, ips=24):
    """Survol : de la verticale (même cadrage que la photo) vers un travelling oblique au-dessus des rangs."""
    from mathutils import Vector
    sc = bpy.context.scene
    sc.render.fps = ips
    sc.frame_start, sc.frame_end = SURVOL_DEBUT, SURVOL_IMAGES
    cam.data.lens = SURVOL_FOCALE
    cam.rotation_mode = "QUATERNION"
    n = SURVOL_IMAGES - SURVOL_DEBUT
    q_prec = None
    for f in range(SURVOL_DEBUT, SURVOL_IMAGES + 1, 2):
        pos, cible = survol_pose((f - SURVOL_DEBUT) / n)
        cam.location = tuple(pos)
        d = Vector(tuple(cible - pos))
        q = d.to_track_quat("-Z", "Y") if f > SURVOL_DEBUT else Vector((0, 0, 1)).to_track_quat("Z", "Y")
        if f == SURVOL_DEBUT:
            from mathutils import Quaternion
            q = Quaternion((1, 0, 0, 0))                               # verticale, nord en haut de l'image
        if q_prec is not None and q.dot(q_prec) < 0:
            q.negate()
        cam.rotation_quaternion = q
        q_prec = q.copy()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)


def projeter(plants, chemin):
    """Projette chaque pied (x, y lus dans plants.csv) par la caméra active, avec la formule de Blender
    (world_to_camera_view) : pixel du pied au sol (z = 0) et du sommet du faux-tronc (objet du pied, z = 2,6 m à
    l'échelle de l'objet). Sert au contrôle d'alignement : rien n'est relu de l'image."""
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    sc = bpy.context.scene
    bpy.context.view_layer.update()                                # matrices monde à jour (caméra, objets)
    cam = sc.camera
    lx, ly = sc.render.resolution_x, sc.render.resolution_y
    out = []
    for p in plants:
        ob = bpy.data.objects.get(f"bananier_{p['id']:03d}")
        res = dict(id=p["id"], x_m=p["x"], y_m=p["y"])
        for nom, z in (("sol", 0.0), ("sommet", 2.6 * (ob.scale[2] if ob else 1.0))):
            q = world_to_camera_view(sc, cam, Vector((p["x"], p["y"], z)))
            res[nom] = [q.x * lx, (1 - q.y) * ly, q.z]
        res["objet_xy"] = list(ob.location[:2]) if ob else None
        out.append(res)
    chemin.write_text(json.dumps(dict(camera=cam.name, resolution=[lx, ly], pieds=out), ensure_ascii=False),
                      encoding="utf-8")
    print(f"PROJECTION {len(out)} pieds -> {chemin}")


def reglages_rendu(echantillons, fils):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = echantillons
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 4
    sc.render.threads_mode = "FIXED"
    sc.render.threads = fils
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.render.image_settings.file_format = "PNG"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--donnees", default=str(RACINE / "out/rendu_blender/v4"))
    ap.add_argument("--echelle-plants", type=float, default=1.0, help="facteur d'échelle de tous les bananiers")
    ap.add_argument("--vue", choices=["drone", "proche", "heros", "dessus", "photo", "survol"], required=True)
    ap.add_argument("--mode", choices=["naturel", "sante"], default="naturel")
    ap.add_argument("--echantillons", type=int, default=64)
    ap.add_argument("--fils", type=int, default=6)
    ap.add_argument("--largeur", type=int, default=1600)
    ap.add_argument("--hauteur", type=int, default=900)
    ap.add_argument("--sortie", help="PNG (défaut : <donnees>/vue_<vue>_<mode>.png) ; dossier d'images pour survol")
    ap.add_argument("--blend", help="enregistre aussi la scène .blend")
    ap.add_argument("--simple", action="store_true", help="sans herbe ni feuilles au sol (essais rapides)")
    ap.add_argument("--images", help="survol : sous-ensemble d'images, ex. 1-288 ou 1,100,200")
    ap.add_argument("--projection", help="écrit (JSON) la position en pixels de chaque pied, projeté par la caméra "
                                         "de la vue (pied au sol et sommet du faux-tronc), pour le contrôle d'alignement")
    ap.add_argument("--sans-rendu", action="store_true", help="avec --projection : ne rend pas l'image")
    ap.add_argument("--moteur", choices=["cycles", "eevee"], default="cycles",
                    help="eevee : rendu sur la carte graphique (essai pour l'animation)")
    a = ap.parse_args(argv)
    donnees = Path(a.donnees).resolve()
    plants, heros, demi, cam_proche = construire(donnees, a.mode, a.vue, a.simple, a.echelle_plants)
    if a.vue == "photo":
        photo_au_sol(donnees, demi)
    camera(a.vue, plants, heros, demi, cam_proche, a.largeur, a.hauteur)
    reglages_rendu(a.echantillons, a.fils)
    sc = bpy.context.scene
    if a.moteur == "eevee":
        sc.render.engine = "BLENDER_EEVEE"
        ee = sc.eevee
        ee.taa_render_samples = max(a.echantillons, 16)
        # rapprocher EEVEE de Cycles : ombres douces tracées, éclairage indirect et occlusion par rayons et
        # balayage d'horizon, résolution d'ombre fine ; même soleil, même transformation de couleur (AgX)
        for nom, val in (("use_raytracing", False), ("use_shadows", True), ("shadow_ray_count", 2),
                         ("shadow_step_count", 8), ("shadow_resolution_scale", 1.0), ("use_fast_gi", FAST_GI),
                         ("fast_gi_method", "GLOBAL_ILLUMINATION"), ("fast_gi_distance", 3.0),
                         ("fast_gi_ray_count", 4), ("fast_gi_step_count", 8), ("horizon_bias", 0.05),
                         ("ray_tracing_method", "SCREEN"), ("use_shadow_jitter_viewport", True)):
            if hasattr(ee, nom):
                try:
                    setattr(ee, nom, val)
                except (TypeError, ValueError):
                    pass
        opt = getattr(ee, "ray_tracing_options", None)
        if opt is not None:
            for nom, val in (("resolution_scale", "1"), ("trace_max_roughness", 0.6), ("use_denoise", True)):
                if hasattr(opt, nom):
                    try:
                        setattr(opt, nom, val)
                    except (TypeError, ValueError):
                        pass
        for ob in sc.objects:                                       # soleil : ombre douce, limite fine
            if ob.type == "LIGHT" and ob.data.type == "SUN":
                ob.data.use_shadow = True
                if hasattr(ob.data, "shadow_maximum_resolution"):
                    ob.data.shadow_maximum_resolution = 0.002
        print("EEVEE :", {k: getattr(ee, k) for k in ("use_raytracing", "use_fast_gi", "shadow_ray_count")
                          if hasattr(ee, k)})
    if a.projection:
        projeter(plants, Path(a.projection))
        if a.sans_rendu:
            return
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.blend).resolve()))
    if a.vue == "survol":
        # animation : seule la caméra bouge ; on garde la scène préparée d'une image à l'autre et on allège
        # l'éclairage indirect (le débruiteur compense le faible nombre d'échantillons)
        sc.render.use_persistent_data = True
        sc.cycles.max_bounces = 4
        sc.cycles.diffuse_bounces = 2
        sc.cycles.transmission_bounces = 2
        dossier = Path(a.sortie).resolve() if a.sortie else donnees / "survol_images"
        dossier.mkdir(parents=True, exist_ok=True)
        if a.images and "-" in a.images:
            d, f = map(int, a.images.split("-"))
            liste = range(d, f + 1)
        elif a.images:
            liste = [int(x) for x in a.images.split(",")]
        else:
            liste = range(sc.frame_start, sc.frame_end + 1)
        t = time.time()
        for f in liste:
            sortie = dossier / f"image_{f:04d}.png"
            if sortie.exists():
                continue
            sc.frame_set(f)
            sc.render.filepath = str(sortie)
            bpy.ops.render.render(write_still=True)
            print(f"SURVOL image {f} : {time.time() - t:.0f} s cumulées", flush=True)
        return
    sortie = Path(a.sortie) if a.sortie else donnees / f"vue_{a.vue}_{a.mode}.png"
    sc.render.filepath = str(sortie.resolve())
    t = time.time()
    bpy.ops.render.render(write_still=True)
    duree = time.time() - t
    print(f"RENDU {sortie.name} : {duree:.0f} s, {a.echantillons} échantillons, {a.fils} fils, "
          f"{sc.render.resolution_x}x{sc.render.resolution_y}")
    if sortie.resolve().parent != donnees:
        return                                                     # essai hors du dossier de sortie : pas de journal
    journal = donnees / "temps_rendu.json"
    tout = json.loads(journal.read_text(encoding="utf-8")) if journal.exists() else {}
    tout[sortie.name] = dict(secondes=round(duree), echantillons=a.echantillons, fils=a.fils,
                             resolution=[sc.render.resolution_x, sc.render.resolution_y],
                             heros_id=plants[heros]["id"])
    journal.write_text(json.dumps(tout, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
