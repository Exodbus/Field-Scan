"""Formes des bananiers d'illustration de la visite de Basse-Pointe (out/visite_martinique/bananiers.glb).

Les 48 formes de la v4 (scripts/blender_scene.types_de_plants, mêmes graines 500 + k), simplifiées par le
modificateur Decimate en trois niveaux de détail, sans aucun placement : la page web les instancie elle-même sur
les positions de bananiers.bin (scripts/visite_martinique_preparer.py), autour du marcheur seulement.

Pour alléger le navigateur, les quatre matériaux de la v4 (feuille, faux-tronc, feuille sèche, régime) sont
réunis en un seul (couleur par sommet) : un appel de dessin par forme et par niveau. La page reconnaît les
feuilles vivantes à leur couleur (verte) pour la teinte « santé ».

Nœuds du glb : « b<kk>_l<n> » (kk = forme 00 à 47, n = niveau 0 proche, 1 moyen, 2 loin), chacun à l'origine.
Réutilise sans les modifier scripts/visite_exporter_blender.py (mat_simple, decimer, sans_uv) et
scripts/blender_scene.py.

    blender.exe -b --factory-startup -t 2 -P scripts/visite_martinique_exporter_blender.py -- \
        [--ratios 0.10 0.025 0.008] [--dossier out/visite_martinique]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import bpy

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_scene as bs  # noqa: E402
import visite_exporter_blender as vx  # noqa: E402


def un_seul_materiau(me, mat):
    """Toutes les faces sur un seul matériau (couleur par sommet)."""
    me.polygons.foreach_set("material_index", [0] * len(me.polygons))
    me.materials.clear()
    me.materials.append(mat)
    me.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=str(RACINE / "out/visite_martinique"))
    ap.add_argument("--ratios", type=float, nargs=3, default=[0.10, 0.025, 0.008],
                    help="part des faces gardées pour les niveaux proche, moyen et loin")
    a = ap.parse_args(argv)
    dossier = Path(a.dossier).resolve()
    t0 = time.time()
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    mats_b = [vx.mat_simple("feuille", 0.55, True), vx.mat_simple("tronc", 0.75, True),
              vx.mat_simple("feuille_seche", 0.85, True), vx.mat_simple("fruit", 0.45, True)]
    mat_unique = vx.mat_simple("bananier", 0.6, True)
    types = bs.types_de_plants(mats_b)
    col = bpy.data.collections.new("formes")
    bpy.context.scene.collection.children.link(col)
    stats = dict(formes=len(types), ratios=a.ratios, sommets_origine=0, sommets=[0, 0, 0], triangles=[0, 0, 0],
                 hauteurs=[])
    for k, (me, par) in enumerate(types):
        vx.sans_uv(me)
        stats["sommets_origine"] += len(me.vertices)
        stats["hauteurs"].append(round(par["H"], 2))
        copies = [me] + [me.copy() for _ in range(2)]
        for n, (m, r) in enumerate(zip(copies, a.ratios)):
            m2 = vx.decimer(m, r, f"b{k:02d}_l{n}")
            un_seul_materiau(m2, mat_unique)
            ob = bpy.data.objects.new(f"b{k:02d}_l{n}", m2)
            col.objects.link(ob)
            ob.location = (0.0, 0.0, 0.0)
            stats["sommets"][n] += len(m2.vertices)
            stats["triangles"][n] += sum(len(q.vertices) - 2 for q in m2.polygons)
        print(f"forme {k:02d} : {time.time() - t0:.0f} s", flush=True)
    glb = dossier / "bananiers.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_vertex_color="MATERIAL",
                              export_texcoords=False, export_normals=True, export_tangents=False,
                              export_apply=False, export_yup=True, export_cameras=False, export_lights=False,
                              export_extras=False, export_materials="EXPORT", use_selection=False)
    stats["octets"] = glb.stat().st_size
    stats["duree_s"] = round(time.time() - t0)
    (dossier / "travail").mkdir(exist_ok=True)
    (dossier / "travail/bananiers_glb.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print("STATS", json.dumps(stats, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
