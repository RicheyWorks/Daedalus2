# SPDX-License-Identifier: MIT
"""Build Wpn_Slice1_Rifle in Blender from its pinned recipe manifest (blender-team). This is the heavy author/export step:
run it only in a coordinated Blender window, headless:
  blender -b --factory-startup --python tools/blender/weapons/build_rifle.py -- --manifest data/combat/slice1/Wpn_Slice1_Rifle.recipe.json --out <staging dir>
It writes <out>/Wpn_Slice1_Rifle.blend and .glb (+Y up, modifiers applied) plus build_report.json with the triangle count and
socket names read back from the built scene. It refuses an --out inside a watched art/ folder unless --allow-art is given at
the normal receiving gate. Never marks anything READY."""
import argparse, json, os, sys
import bpy, bmesh


def args():
    a = argparse.ArgumentParser()
    a.add_argument("--manifest", required=True); a.add_argument("--out", required=True); a.add_argument("--allow-art", action="store_true")
    return a.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def linear(h):
    return tuple((int(h[k:k + 2], 16) / 255.0) ** 2.2 for k in (0, 2, 4)) + (1.0,)


def part_bmesh(q):
    t = bmesh.new()
    if q["shape"] == "box":
        bmesh.ops.create_cube(t, size=1.0)
        sx, sy, sz = q["size"]
        for v in t.verts:
            v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
        bmesh.ops.bevel(t, geom=list(t.edges), offset=min(sx, sy, sz) * 0.12, segments=1, affect="EDGES")
    else:   # cyl_y: cylinder along Y with n-gon caps
        bmesh.ops.create_cone(t, cap_ends=True, cap_tris=False, segments=q["segments"], radius1=q["radius"], radius2=q["radius"], depth=q["length"])
        bmesh.ops.rotate(t, verts=t.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(1.5707963267948966, 3, "X"))
    for v in t.verts:
        v.co.x += q["centre"][0]; v.co.y += q["centre"][1]; v.co.z += q["centre"][2]
    for f in t.faces:
        f.material_index = q["slot"]
    return t


def main():
    o = args(); m = json.load(open(o.manifest, encoding="utf-8"))
    out = os.path.abspath(o.out)
    if not o.allow_art and any(p.lower() == "art" for p in out.replace("\\", "/").split("/")):
        raise SystemExit("refusing to write inside a watched art/ folder; stage elsewhere (or --allow-art at the receiving gate)")
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    name = m["asset"]; main = bmesh.new()
    for q in m["parts"]:
        t = part_bmesh(q); me_t = bpy.data.meshes.new("tmp"); t.to_mesh(me_t); t.free(); main.from_mesh(me_t); bpy.data.meshes.remove(me_t)
    me = bpy.data.meshes.new(name); main.to_mesh(me); main.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    for mat_d in m["materials"]:
        mat = bpy.data.materials.new(mat_d["name"]); mat.use_nodes = True; rgb = linear(mat_d["hex"])
        p = mat.node_tree.nodes["Principled BSDF"]; p.inputs["Base Color"].default_value = rgb; p.inputs["Roughness"].default_value = 0.6; mat.diffuse_color = rgb
        if mat_d["glow"]:
            p.inputs["Emission Color"].default_value = rgb; p.inputs["Emission Strength"].default_value = 2.0
        me.materials.append(mat)
    for s in m["sockets"]:
        e = bpy.data.objects.new(s["name"], None); e.empty_display_type = "ARROWS"; e.empty_display_size = 0.03
        e.location = s["location"]; e.parent = ob; bpy.context.scene.collection.objects.link(e)
        if any(x.get("attach") for x in m["sockets"]):   # held props: pre-rotate so native == sidecar (the gated crate/fixture stay as built)
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
            import sockets_sidecar as SS
            e.rotation_mode = "QUATERNION"; e.rotation_quaternion = SS.socket_blender_quat(s)
    ucx = []
    for c in m.get("collision", []):   # optional: UCX_ convex hull boxes (Unreal naming), unbevelled, parented to the mesh, no material
        t = bmesh.new(); bmesh.ops.create_cube(t, size=1.0)
        for v in t.verts:
            v.co.x = v.co.x * c["size"][0] + c["centre"][0]; v.co.y = v.co.y * c["size"][1] + c["centre"][1]; v.co.z = v.co.z * c["size"][2] + c["centre"][2]
        me_c = bpy.data.meshes.new(c["name"]); t.to_mesh(me_c); t.free()
        oc = bpy.data.objects.new(c["name"], me_c); oc.parent = ob; oc.display_type = "WIRE"; bpy.context.scene.collection.objects.link(oc)
        ucx.append({"name": c["name"], "triangles": sum(len(f.vertices) - 2 for f in me_c.polygons), "dimensions": [round(v, 4) for v in oc.dimensions]})
    tris = sum(len(f.vertices) - 2 for f in me.polygons)
    blend = os.path.join(out, name + ".blend"); glb = os.path.join(out, name + ".glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_yup=True, export_apply=True, export_extras=True)
    rep = {"asset": name, "triangles": tris, "predicted_triangles": m["predicted"]["triangles"], "dimensions": [round(v, 4) for v in ob.dimensions],
           "sockets": sorted(o2.name for o2 in bpy.data.objects if o2.name.startswith("SOCKET_")), "files": [blend, glb],
           "match": tris == m["predicted"]["triangles"], "status": "BUILT (staged, not READY)"}
    if ucx:
        rep["collision"] = ucx; rep["variant"] = m.get("variant"); rep["recipe_sha256"] = m.get("recipe_sha256")
    json.dump(rep, open(os.path.join(out, "build_report.json"), "w"), indent=1)
    print("BUILDJSON " + json.dumps(rep))


main()
