import bpy, collections, numpy as np
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.name.split("_")[0] not in ("arbre","buisson","bananier","haie","herbe","touffe"):
        print("OBJ", o.name, o.type, tuple(round(v,1) for v in o.location), tuple(round(v,1) for v in o.dimensions), len(o.data.vertices) if o.type=="MESH" else "")
b=[o for o in bpy.data.collections["bananiers"].objects]
print("BAN n", len(b), [o.name for o in b[:6]])
P=np.array([tuple(o.location) for o in b]); print("BAN loc", P.min(0), P.max(0))
t=[o for o in bpy.data.collections["lisiere"].objects]; print("LIS", [o.name for o in t[:5]])
P=np.array([tuple(o.location) for o in t]); print("LIS loc", P.min(0), P.max(0))
print("sun", bpy.data.objects["soleil"].rotation_euler, bpy.data.objects["soleil"].data.color, bpy.data.objects["soleil"].data.angle)
sky=[n for n in sc.world.node_tree.nodes if n.bl_idname=="ShaderNodeTexSky"][0]
print("sky", sky.sky_type, sky.sun_elevation, sky.sun_rotation, sky.air_density, sky.dust_density)
print(sc.view_settings.view_transform, sc.view_settings.look)
