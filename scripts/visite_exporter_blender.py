"""Scène de la visite 3D (out/visite_parcelle/scene.glb), exportée en glTF binaire depuis Blender.

Réutilise les générateurs de la v4 sans les modifier (scripts/blender_bananier.py, blender_decor.py,
blender_scene.py) et produit une scène allégée pour le navigateur :
  - bananiers : les 48 formes de la v4 (mêmes graines), simplifiées par le modificateur Decimate, en deux niveaux
    de détail (proche : 22 % des faces, loin : 5 %), instanciées sur chaque pied de pieds.json (extension glTF
    EXT_mesh_gpu_instancing : un nœud par forme et par niveau, une instance par pied). La forme, l'orientation et
    l'échelle de chaque pied sont lues dans pieds.json (scripts/visite_generer.py). Ouvert dans une autre
    visionneuse, le glb montre les deux niveaux superposés : c'est la page qui choisit l'un ou l'autre ;
  - arbres d'agroforesterie (arbres_photo, illustratifs) : arbres de la v4 avec moins de feuilles ;
  - sol de la parcelle et prairie : le matériau procédural de la v4 « cuit » en images (Cycles, couleur diffuse
    seule), plaqué sur des plans ; terrain lointain en couleurs par sommet ;
  - décor allégé : quelques arbres de lisière (instances de 6 formes), deux pistes de terre, herbe et feuilles
    mortes au sol dans la parcelle.
Matériaux simples, compatibles glTF : couleur de base (couleur par sommet ou image), rugosité, double face pour
les feuilles. Aucun nœud Cycles complexe n'est exporté.

Après l'export, le script relit le glb, retrouve l'indice de chaque pied dans les instances de sa forme et l'écrit
dans pieds.json (champ « instance » : nœud et indice, pour chacun des deux niveaux), pour la teinte « santé », la
mise en évidence du pied choisi et le niveau de détail de la page. Les images cuites du sol sont gardées dans
<dossier>/cuisson/ (--reutiliser-cuisson évite de les recuire : la cuisson prend ~7 min sur 2 fils).

    blender.exe -b --factory-startup -t 2 -P scripts/visite_exporter_blender.py -- [--dossier out/visite_parcelle]
                [--ratio 0.22] [--cuisson-parcelle 4096] [--reutiliser-cuisson]
"""
import argparse
import json
import math
import struct
import sys
import time
from pathlib import Path

import bpy
import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_bananier as bb  # noqa: E402
import blender_decor as bd  # noqa: E402
import blender_scene as bs  # noqa: E402

# demi-côtés (m) : plan « sol de la parcelle » = emprise + ~4 m, arrondi au pas de la prairie (37,5 m pour Flora Pluas) ;
# prairie cuite autour (200 m au moins) ; au-delà, terrain lointain en couleurs par sommet
PAS_PRAIRIE = 2.5         # pas de la grille de la prairie (m)


# ----------------------------------------------------------------------------------------------- matériaux simples
def mat_simple(nom, rugosite=0.7, double_face=True, image=None, specular=0.3):
    """Principled BSDF : couleur de base = couleur par sommet (« couleur ») ou image ; rien d'autre."""
    ma = bpy.data.materials.new(nom)
    ma.use_nodes = True
    nt = ma.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = rugosite
    p.inputs["Specular IOR Level"].default_value = specular
    if image is None:
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "couleur"
        nt.links.new(vc.outputs["Color"], p.inputs["Base Color"])
    else:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(p.outputs[0], sortie.inputs["Surface"])
    ma.use_backface_culling = not double_face
    return ma


def sans_uv(me):
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])


def decimer(me, ratio, nom):
    """Simplifie un maillage par le modificateur Decimate (effondrement d'arêtes), sans opérateur."""
    if ratio >= 0.999:
        return me
    ob = bpy.data.objects.new("_tmp_" + nom, me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    nouveau = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    nouveau.name = nom
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return nouveau


def parent_vide(nom, collection):
    e = bpy.data.objects.new(nom, None)
    collection.objects.link(e)
    return e


# ----------------------------------------------------------------------------------------------- cuisson du sol
def cuire(materiau, demi, cote_px, chemin, echantillons=2):
    """Cuit la couleur diffuse d'un matériau procédural (terrain de la v4) sur un plan [-demi, demi]² (coordonnées
    objet = coordonnées du monde) et l'enregistre en JPEG."""
    sc = bpy.context.scene
    me = bpy.data.meshes.new("_cuisson")
    me.from_pydata([(-demi, -demi, 0), (demi, -demi, 0), (demi, demi, 0), (-demi, demi, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    me.materials.append(materiau)
    ob = bpy.data.objects.new("_cuisson", me)
    sc.collection.objects.link(ob)
    img = bpy.data.images.new("_cuisson_" + chemin.stem, cote_px, cote_px)
    nt = materiau.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.nodes.active = tex
    for o in sc.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = echantillons
    sc.render.bake.margin = 2
    t = time.time()
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    img.filepath_raw = str(chemin)
    img.file_format = "JPEG"
    try:
        img.save(filepath=str(chemin), quality=88)
    except TypeError:
        img.save()
    print(f"cuisson {chemin.name} {cote_px} px : {time.time() - t:.0f} s", flush=True)
    bpy.data.objects.remove(ob)
    nt.nodes.remove(tex)
    bpy.data.images.remove(img)


def hauteur_terrain(X, Y):
    """Même formule que blender_decor.terrain(), vectorisée."""
    r = np.hypot(X, Y)
    k1 = np.clip((r - 90) / 220, 0, 1) ** 2
    k2 = np.clip((r - 700) / 1600, 0, 1) ** 1.5
    return k1 * 9 * bd.bruit2d(X, Y, 11, 4, 1 / 160) + k2 * 120 * (0.6 + 0.4 * bd.bruit2d(X, Y, 12, 4, 1 / 900))


def plan_texture(nom, demi, image, col, trou=None, pas=None, rugosite=0.95):
    """Grille texturée [-demi, demi]² posée sur le terrain ; trou = demi-côté d'un carré central retiré."""
    pas = pas or demi / 8
    n = int(round(2 * demi / pas)) + 1
    g = np.linspace(-demi, demi, n)
    X, Y = np.meshgrid(g, g)
    Z = hauteur_terrain(X, Y) * (np.hypot(X, Y) > 90)
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    F = bb._grille(n, n)                                            # sens direct : normale vers le haut
    if trou is not None:
        c = V[F].mean(1)
        F = F[np.maximum(np.abs(c[:, 0]), np.abs(c[:, 1])) > trou]
    uv = (V[F.ravel(), :2] + demi) / (2 * demi)
    ma = mat_simple("mat_" + nom, rugosite, double_face=False, image=image, specular=0.2)
    ob = bd.maillage_rapide(nom, V, F, uv_coins=uv, materiaux=[ma], collection=col)
    return ob


def terrain_lointain(col, trou):
    """Terrain de la v4 (même relief), sans la partie couverte par la prairie cuite, couleurs par sommet."""
    n = 140
    t = np.linspace(-1, 1, n)
    g = np.sign(t) * np.abs(t) ** 2.2 * 3500.0
    X, Y = np.meshgrid(g, g)
    Z = hauteur_terrain(X, Y) - 0.3
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    F = bb._grille(n, n)
    garde = (np.maximum(np.abs(V[F][:, :, 0]), np.abs(V[F][:, :, 1])) > trou).any(1)
    F = F[garde]
    # couleurs : prairie avec grandes plaques, couvert forestier sur les collines (au-delà de ~200 m)
    b = bd.bruit2d(X, Y, 31, 4, 1 / 60).reshape(-1)
    prairie = np.array([0.075, 0.12, 0.028]) * (1 + 0.25 * b[:, None])
    bf = bd.bruit2d(X, Y, 32, 3, 1 / 250).reshape(-1)
    r = np.hypot(X, Y).reshape(-1)
    k = np.clip((r - 180) / 240, 0, 1) * np.clip((bf + 0.2) / 0.4, 0, 1)
    foret = np.array([0.035, 0.075, 0.022])
    C = prairie * (1 - k[:, None]) + foret * k[:, None]
    return bd.maillage_rapide("terrain_lointain", V, F, couleurs=np.clip(C, 0, 1),
                              materiaux=[mat_simple("mat_terrain_lointain", 0.95, False, specular=0.15)], collection=col)


def piste(points, largeur, nom, mat, col):
    """Piste de terre : ruban à 9 colonnes, ornières sombres, bande d'herbe au milieu, bords fondus vers la prairie
    (couleurs par sommet, au lieu du matériau procédural de blender_decor.materiau_chemin)."""
    P = np.asarray(points, float)
    seg = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(int(np.linalg.norm(b - a) / 2.0), 1)
        seg += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)[1:]]
    P = np.array(seg)
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    nrm = np.c_[-t[:, 1], t[:, 0]]
    v = np.array([0.0, 0.1, 0.22, 0.3, 0.38, 0.5, 0.62, 0.7, 0.78, 0.9, 1.0])
    rng = np.random.default_rng(len(nom))
    ond = 0.05 * np.sin(np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))] / 9.0)[:, None]
    vv = np.clip(v[None, :] + ond, 0, 1)
    V = P[:, None, :] + nrm[:, None, :] * ((vv - 0.5) * largeur)[..., None]
    Z = hauteur_terrain(V[..., 0], V[..., 1]) * (np.hypot(V[..., 0], V[..., 1]) > 90) + 0.05
    V = np.concatenate([V, Z[..., None]], -1)
    terre = np.array([0.20, 0.12, 0.065])
    orn = np.array([0.13, 0.075, 0.04])
    herbe = np.array([0.08, 0.12, 0.03])
    prairie = np.array([0.08, 0.12, 0.03])
    C = np.empty(V.shape)
    profil = [prairie, terre * 0.9 + prairie * 0.1, orn, terre, terre * 0.8 + herbe * 0.2, herbe,
              terre * 0.8 + herbe * 0.2, terre, orn, terre * 0.9 + prairie * 0.1, prairie]
    for j, c in enumerate(profil):
        C[:, j] = c
    C *= rng.uniform(0.85, 1.15, (len(P), 1, 1))
    F = bb._grille(len(P), len(v))[:, [0, 3, 2, 1]]   # rangées le long de la piste : retournées pour la normale vers le haut
    return bd.maillage_rapide(nom, V.reshape(-1, 3), F, couleurs=np.clip(C.reshape(-1, 3), 0, 1),
                              materiaux=[mat], collection=col)


# ----------------------------------------------------------------------------------------------- relecture du glb
def lire_glb(chemin):
    data = chemin.read_bytes()
    n_json = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20:20 + n_json].decode("utf-8"))
    bin_ = data[20 + n_json + 8:]
    return doc, bin_


def accesseur(doc, bin_, i):
    a = doc["accessors"][i]
    bv = doc["bufferViews"][a["bufferView"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[a["componentType"]]
    deb = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    pas = bv.get("byteStride")
    if pas and pas != n * np.dtype(dt).itemsize:
        brut = np.frombuffer(bin_, np.uint8, count=pas * a["count"], offset=deb).reshape(a["count"], pas)
        return brut[:, :n * np.dtype(dt).itemsize].copy().view(dt).reshape(a["count"], n)
    return np.frombuffer(bin_, dt, count=a["count"] * n, offset=deb).reshape(a["count"], n)


def associer_instances(glb, pieds):
    """Pour chaque pied : nœud du glb qui porte les instances de sa forme, et indice de l'instance (retrouvé par la
    position : dans le glb, y vers le haut, donc (x, z) = (x_est, -y_nord))."""
    doc, bin_ = lire_glb(glb)
    par_forme = {}
    for i, nd in enumerate(doc["nodes"]):
        ext = nd.get("extensions", {}).get("EXT_mesh_gpu_instancing")
        nom = nd.get("name", "")
        if ext is None:
            continue
        # le nœud instancié est soit le parent vide « bananiers_forme_kk », soit son enfant
        k, niveau = None, None
        for cand in [nom] + [doc["nodes"][j].get("name", "") for j, p in enumerate(doc["nodes"]) if i in p.get("children", [])]:
            for pref, niv in (("bananiers_forme_", "proche"), ("bananiers_loin_", "loin")):
                if cand.startswith(pref):
                    k, niveau = int(cand.split("_")[-1]), niv
        if k is None:
            continue
        T = accesseur(doc, bin_, ext["attributes"]["TRANSLATION"])
        par_forme[(k, niveau)] = (nom, T)
    # forme portée par un seul pied : pas d'instanciation dans le glb (il en faut au moins deux), un nœud ordinaire
    # « pied_0123 » (ou « loin_0123 ») sous le vide de la forme ; la page le convertit en instance unique
    noms = {nd.get("name", ""): i for i, nd in enumerate(doc["nodes"])}
    parent = {c: i for i, nd in enumerate(doc["nodes"]) for c in nd.get("children", [])}
    n_ok, ecart_max = 0, 0.0
    for p in pieds:
        for niv, pref in (("proche", "pied"), ("loin", "loin")):
            i = noms.get(f"{pref}_{p['id']:04d}")
            if (p["forme"], niv) not in par_forme and i is not None and i in parent:
                t = doc["nodes"][i].get("translation", [0, 0, 0])
                par_forme[(p["forme"], niv)] = (doc["nodes"][parent[i]]["name"], np.array([t], np.float32))
        if (p["forme"], "proche") not in par_forme:
            p.pop("instance", None)
            continue
        inst = dict(forme=p["forme"])
        for niv, cle in (("proche", ""), ("loin", "_loin")):
            if (p["forme"], niv) not in par_forme:
                continue
            nom, T = par_forme[(p["forme"], niv)]
            d = np.hypot(T[:, 0] - p["x"], T[:, 2] + p["y"])
            j = int(d.argmin())
            ecart_max = max(ecart_max, float(d[j]))
            inst["noeud" + cle], inst["indice" + cle] = nom, j
        p["instance"] = inst
        n_ok += 1
    print(f"instances associées : {n_ok} / {len(pieds)} (écart max {ecart_max:.4f} m), {len(par_forme)} nœuds instanciés")
    return doc


# ----------------------------------------------------------------------------------------------- scène
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=str(RACINE / "out/visite_parcelle"))
    ap.add_argument("--ratio", type=float, default=0.22, help="Decimate des bananiers (part des faces gardées)")
    ap.add_argument("--ratio-loin", type=float, default=0.05, help="Decimate des bananiers lointains")
    ap.add_argument("--densite-agro", type=float, default=0.15, help="part des feuilles des arbres d'agroforesterie")
    ap.add_argument("--ratio-agro", type=float, default=0.45, help="Decimate des arbres d'agroforesterie")
    ap.add_argument("--n-lisiere", type=int, default=90, help="nombre d'arbres de lisière")
    ap.add_argument("--cuisson-parcelle", type=int, default=4096, help="côté (px) de l'image du sol de la parcelle")
    ap.add_argument("--cuisson-prairie", type=int, default=2048, help="côté (px) de l'image de la prairie")
    ap.add_argument("--reutiliser-cuisson", action="store_true", help="garder les images déjà cuites (cuisson/)")
    ap.add_argument("--herbe", type=float, default=0.25, help="densité de touffes d'herbe dans la parcelle (par m²)")
    ap.add_argument("--blend", help="enregistre aussi la scène .blend (contrôle)")
    a = ap.parse_args(argv)
    dossier = Path(a.dossier).resolve()
    doc = json.loads((dossier / "pieds.json").read_text(encoding="utf-8"))
    pieds, arbres, demi = doc["pieds"], doc.get("arbres", []), doc["demi_cote_m"]
    t_total = time.time()
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    bd.D_BRUME = 1e9                                                # pas de brume dans les couleurs cuites
    stats = {}
    demi_sol = math.ceil((demi + 4.0) / PAS_PRAIRIE) * PAS_PRAIRIE
    demi_prairie = max(200.0, math.ceil((demi + 160.0) / 50.0) * 50.0)
    ys, xo = -(demi + 4.5), -(demi + 6.0)                          # pistes : bord sud et bord ouest (Flora : -37,8 et -39,2)

    # ---- sol : cuisson du matériau procédural de la v4 (parcelle et prairie)
    cuis = dossier / "cuisson"
    cuis.mkdir(exist_ok=True)
    f_parc, f_prai = cuis / "sol_parcelle.jpg", cuis / "prairie.jpg"
    if not (a.reutiliser_cuisson and f_parc.exists() and f_prai.exists()):
        mt = bd.materiau_terrain(demi)
        cuire(mt, demi_sol, a.cuisson_parcelle, f_parc)
        cuire(mt, demi_prairie, a.cuisson_prairie, f_prai)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    col_sol = bpy.data.collections.new("sol")
    sc.collection.children.link(col_sol)
    im_parc = bpy.data.images.load(str(f_parc))
    im_prai = bpy.data.images.load(str(f_prai))
    plan_texture("sol_parcelle", demi_sol, im_parc, col_sol, pas=demi_sol / 8)
    plan_texture("prairie", demi_prairie, im_prai, col_sol, trou=demi_sol - 0.01, pas=PAS_PRAIRIE)
    terrain_lointain(col_sol, demi_prairie - 1.0)
    mat_piste = mat_simple("mat_piste", 0.95, False, specular=0.2)
    piste([(-170, ys - 0.7), (-60, ys - 0.2), (0, ys + 0.2), (60, ys - 0.4), (170, ys - 2.2)], 3.6, "piste_sud", mat_piste, col_sol)
    piste([(xo - 0.3, ys - 0.2), (xo + 0.2, 0), (xo - 1.3, 60), (xo - 6.8, 130), (xo - 20.8, 200)], 3.2, "piste_ouest", mat_piste, col_sol)

    # ---- bananiers : 48 formes de la v4, simplifiées, instanciées
    t0 = time.time()
    mats_b = [mat_simple("feuille", 0.55, True), mat_simple("tronc", 0.75, True),
              mat_simple("feuille_seche", 0.85, True), mat_simple("fruit", 0.45, True)]
    types = bs.types_de_plants(mats_b)                              # mêmes graines que la v4 (500 + k)
    n_avant = sum(len(me.vertices) for me, _ in types)
    formes, formes_loin = [], []
    for k, (me, par) in enumerate(types):
        sans_uv(me)
        loin = me.copy()                                            # niveau de détail « loin » (au-delà de ~22 m)
        formes.append(decimer(me, a.ratio, f"bananier_forme_{k:02d}"))
        formes_loin.append(decimer(loin, a.ratio_loin, f"bananier_loin_{k:02d}"))
    n_apres = sum(len(me.vertices) for me in formes)
    tri = lambda m: sum(len(q.vertices) - 2 for q in m.polygons)  # noqa: E731
    stats["bananiers"] = dict(formes=len(formes), sommets_avant=n_avant, sommets_apres=n_apres, ratio=a.ratio,
                              triangles=sum(tri(me) for me in formes), ratio_loin=a.ratio_loin,
                              sommets_loin=sum(len(me.vertices) for me in formes_loin),
                              triangles_loin=sum(tri(me) for me in formes_loin))
    print(f"48 formes : {n_avant} -> {n_apres} sommets en {time.time() - t0:.0f} s", flush=True)
    col_b = bpy.data.collections.new("bananiers")
    sc.collection.children.link(col_b)
    # deux niveaux de détail, chacun avec une instance par pied (même transformation) ; la page n'affiche que
    # l'un ou l'autre selon la distance au marcheur
    for prefixe, liste in (("bananiers_forme_", formes), ("bananiers_loin_", formes_loin)):
        vides = {}
        for p in sorted(pieds, key=lambda q: q["id"]):
            k = p["forme"]
            if k not in vides:
                vides[k] = parent_vide(f"{prefixe}{k:02d}", col_b)
            ob = bpy.data.objects.new(f"{'pied' if prefixe.endswith('forme_') else 'loin'}_{p['id']:04d}", liste[k])
            col_b.objects.link(ob)
            ob.parent = vides[k]
            ob.location = (p["x"], p["y"], 0.0)
            ob.rotation_euler = (0, 0, p["rotation"])
            ob.scale = tuple(p["echelle"])

    # ---- arbres d'agroforesterie (positions de arbres_photo.csv, formes illustratives de la v4, moins de feuilles)
    col_a = bpy.data.collections.new("arbres_parcelle")
    sc.collection.children.link(col_a)
    mat_f = mat_simple("feuillage", 0.75, True)
    mat_e = mat_simple("ecorce", 0.9, True, specular=0.15)
    n_agro = 0
    for k, r_ in enumerate(arbres):
        rng = np.random.default_rng(700 + k)                        # mêmes graines que blender_decor.arbres_parcelle
        me = bd.arbre(rng, r_["hauteur"], r_["rayon"], eclat=bd.ECLAT_AGRO, palette=bd.PALETTE_AGRO,
                      densite=a.densite_agro).objet(f"_arbre_{k:02d}", [mat_f, mat_e], None).data
        sans_uv(me)
        me = decimer(me, a.ratio_agro, f"arbre_parcelle_{k:02d}")
        ob = bpy.data.objects.new(f"arbre_parcelle_{k:02d}", me)
        col_a.objects.link(ob)
        ob.location = (r_["x"], r_["y"], 0.0)
        ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        n_agro += len(ob.data.vertices)
    stats["arbres_parcelle"] = dict(n=len(arbres), sommets=n_agro, densite_feuilles=a.densite_agro)

    # ---- lisière : 6 formes d'arbres (graines 900 + k de la v4), peu de feuilles, en bouquets à 45-160 m du bord
    col_l = bpy.data.collections.new("lisiere")
    sc.collection.children.link(col_l)
    formes_l = []
    for k in range(6):
        r = np.random.default_rng(900 + k)
        h = r.uniform(7, 20)
        ob = bd.arbre(r, h, r.uniform(3.0, 6.5) * h / 15, densite=0.1).objet(f"arbre_lisiere_{k}", [mat_f, mat_e], None)
        sans_uv(ob.data)
        formes_l.append(decimer(ob.data, 0.5, f"arbre_lisiere_forme_{k}"))
    rng = np.random.default_rng(21)
    pos = []
    for _ in range(20000):                                          # même règle de bouquets que blender_decor.lisiere
        d = rng.uniform(45, 160)
        cote = rng.integers(4)
        u = rng.uniform(-demi - d, demi + d)
        x, y = [(u, demi + d), (u, -demi - d), (demi + d, u), (-demi - d, u)][cote]
        dens = bd.bruit2d(np.array([x]), np.array([y]), 21, 3, 1 / 30)[0]
        if dens > 0.4 + (d - 45) / 220 and abs(y - ys) > 4 and abs(x - xo) > 4:   # pas sur les pistes
            pos.append((x, y, d))
    rng.shuffle(pos)                                                # bouquets répartis sur toute la bande
    garde = []
    for x, y, d in pos:                                             # espacement minimal 7 m
        if all((x - u) ** 2 + (y - v) ** 2 > 49 for u, v in garde):
            garde.append((x, y))
        if len(garde) >= a.n_lisiere:
            break
    vides_l = [parent_vide(f"lisiere_forme_{k}", col_l) for k in range(6)]
    for i, (x, y) in enumerate(garde):
        k = int(rng.integers(6))
        ob = bpy.data.objects.new(f"arbre_lisiere_{i:03d}", formes_l[k])
        col_l.objects.link(ob)
        ob.parent = vides_l[k]
        z = float(hauteur_terrain(np.array([x]), np.array([y]))[0]) * (math.hypot(x, y) > 90) - 0.2
        ob.location = (x, y, z)
        ob.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        s = rng.uniform(0.8, 1.2)
        ob.scale = (s, s, s * rng.uniform(0.9, 1.1))
    stats["lisiere"] = dict(n=len(garde), formes=6, sommets_par_forme=[len(m.vertices) for m in formes_l])

    # ---- herbe et feuilles mortes au sol dans la parcelle (géométrie de la v4, une seule fois)
    rng = np.random.default_rng(42)
    centres = np.c_[[p["x"] for p in pieds], [p["y"] for p in pieds], np.zeros(len(pieds))]
    tmp = bd.litiere(centres, rng, mats_b, par_plant=1.0, nom="_litiere")
    me = tmp.data
    bpy.data.objects.remove(tmp)
    sans_uv(me)
    lit = bpy.data.objects.new("feuilles_au_sol", decimer(me, 0.2, "feuilles_au_sol"))
    sc.collection.objects.link(lit)
    mat_h = mat_simple("herbe", 0.7, True)
    pts = bd.points_herbe(int((2 * demi) ** 2 * a.herbe), (-demi, demi, -demi, demi), rng, centres, 0.55)
    h1 = bd.herbe(pts, rng, mat_h, hauteur=(0.08, 0.3), brins=(4, 7), nom="herbe_parcelle")
    # bordure : herbe plus haute entre la parcelle et les pistes
    pts = bd.points_herbe(4000, (-demi - 9, demi + 9, -demi - 9, demi + 9), rng)
    pts = pts[np.maximum(np.abs(pts[:, 0]), np.abs(pts[:, 1])) > demi + 1.0]
    pts = pts[(np.abs(pts[:, 1] - ys) > 2.2) & (np.abs(pts[:, 0] - xo) > 2.0)]
    h2 = bd.herbe(pts, rng, mat_h, hauteur=(0.12, 0.45), brins=(4, 8), nom="herbe_bord")
    for o in (lit, h1, h2):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col_sol.objects.link(o)
    stats["sol"] = dict(feuilles_mortes_sommets=len(lit.data.vertices),
                        herbe_sommets=len(h1.data.vertices) + len(h2.data.vertices))

    # ---- export glTF binaire
    glb = dossier / "scene.glb"
    t0 = time.time()
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_gpu_instances=True,
                              export_vertex_color="MATERIAL", export_texcoords=True, export_normals=True,
                              export_tangents=False, export_image_format="JPEG", export_jpeg_quality=85,
                              export_apply=False, export_yup=True, export_cameras=False, export_lights=False,
                              export_extras=False, export_materials="EXPORT", use_selection=False)
    taille = glb.stat().st_size
    print(f"EXPORT {glb} : {taille / 1e6:.1f} Mo en {time.time() - t0:.0f} s", flush=True)
    gl = associer_instances(glb, pieds)
    stats["glb"] = dict(octets=taille, noeuds=len(gl["nodes"]), maillages=len(gl["meshes"]),
                        extensions=gl.get("extensionsUsed", []))
    stats["duree_s"] = round(time.time() - t_total)
    doc["scene"] = stats
    (dossier / "pieds.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("STATS", json.dumps(stats, ensure_ascii=False))
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.blend).resolve()))


if __name__ == "__main__":
    main()
