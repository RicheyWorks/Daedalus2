# SPDX-License-Identifier: MIT
"""Build blender-kit/v1 assets headless (blender-team). Heavy step: run only with no compute HOLD, under a short lock.
  blender -b --factory-startup --python tools/blender/kit/build_kit.py -- --set <x.kit.json> --out <staging dir> [--only A,B]
Per asset writes <out>/<Asset>/<Asset>.glb (+ <Asset>_LOD1.glb unless the recipe says lod1 false), <Asset>.blend and
build_report.json (and <Asset>.sockets.json, the Unreal-space socket sidecar), tris per object read back from the built meshes, bounds, sockets, collision, sha256). Refuses an
--out inside a watched art/ folder. Never marks anything READY. Geometry comes from kitlib (the same numbers the tests
predict), so predicted == built is checked here too."""
import argparse, hashlib, json, os, sys
import bpy, bmesh
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitlib as K
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sockets_sidecar as SS


def args():
    a = argparse.ArgumentParser()
    a.add_argument("--set", required=True); a.add_argument("--out", required=True); a.add_argument("--only", default="")
    return a.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def linear(h):
    return tuple((int(h[k:k + 2], 16) / 255.0) ** 2.2 for k in (0, 2, 4)) + (1.0,)


def part_into(bm, p, lod, offset, slot):
    t = bmesh.new()
    if p["shape"] == "box":
        bmesh.ops.create_cube(t, size=1.0)
        sx, sy, sz = p["size"]
        for v in t.verts:
            v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
        if p.get("bevel", True):
            bmesh.ops.bevel(t, geom=list(t.edges), offset=min(sx, sy, sz) * K.BEVEL, segments=1, affect="EDGES")
    else:
        vs = K.local_verts(p, lod); vv = [t.verts.new(v) for v in vs]
        n = p["lod1"]["segments"] if lod and p.get("lod1", {}).get("segments") else p["segments"]
        rings = len(vs) // n
        for r in range(rings - 1):
            for i in range(n):
                j = (i + 1) % n
                t.faces.new((vv[r * n + i], vv[r * n + j], vv[(r + 1) * n + j], vv[(r + 1) * n + i]))
        caps = [True, True] if p["shape"] == "cyl" else p["caps"]
        if caps[0]: t.faces.new([vv[i] for i in reversed(range(n))])
        if caps[1]: t.faces.new([vv[(rings - 1) * n + i] for i in range(n)])
        bmesh.ops.recalc_face_normals(t, faces=t.faces)
    if p.get("rot"):
        M = Matrix([[K.rot_matrix(p["rot"])[i][j] for j in range(3)] for i in range(3)]).to_4x4()
        bmesh.ops.transform(t, matrix=M, verts=t.verts)
    c = Vector(p["centre"]) - Vector(offset)
    for v in t.verts:
        v.co += c
    for f in t.faces:
        f.material_index = slot
    me = bpy.data.meshes.new("tmp"); t.to_mesh(me); t.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)


def coll_mesh(c, offset):
    t = bmesh.new()
    if c["shape"] == "box":
        bmesh.ops.create_cube(t, size=1.0)
        for v in t.verts:
            v.co.x *= c["size"][0]; v.co.y *= c["size"][1]; v.co.z *= c["size"][2]
    elif c["shape"] == "cyl":
        vs = K.local_verts({"shape": "cyl", "axis": c["axis"], "r1": c["r1"], "r2": c["r2"], "length": c["length"], "segments": c["segments"]})
        vv = [t.verts.new(v) for v in vs]; n = c["segments"]
        for i in range(n):
            j = (i + 1) % n; t.faces.new((vv[i], vv[j], vv[n + j], vv[n + i]))
        t.faces.new([vv[i] for i in reversed(range(n))]); t.faces.new([vv[n + i] for i in range(n)])
        bmesh.ops.recalc_face_normals(t, faces=t.faces)
    else:
        bmesh.ops.create_uvsphere(t, u_segments=c["segments"], v_segments=c["rings"], radius=c["radius"])
    for v in t.verts:
        v.co += Vector(c["centre"]) - Vector(offset)
    me = bpy.data.meshes.new(c["name"]); t.to_mesh(me); t.free()
    return me


def tris_of(me):
    return sum(len(f.vertices) - 2 for f in me.polygons)


def build(m, lod, mats):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not mats:
        for md in m["materials"]:
            mat = bpy.data.materials.new(md["name"]); mat.use_nodes = True; rgb = linear(md["hex"])
            pb = mat.node_tree.nodes["Principled BSDF"]
            pb.inputs["Base Color"].default_value = rgb; pb.inputs["Roughness"].default_value = md["roughness"]
            pb.inputs["Metallic"].default_value = md["metallic"]; mat.diffuse_color = rgb
            if md["glow"]:
                pb.inputs["Emission Color"].default_value = rgb; pb.inputs["Emission Strength"].default_value = 2.0
    piv = {o["name"]: o["pivot"] for o in m["objects"]}
    obs = {}
    for o in m["objects"]:
        parts = [p for p in o["parts"] if K.in_lod(p, lod)]
        used = sorted({p["slot"] for p in parts}); remap = {s: i for i, s in enumerate(used)}
        bm = bmesh.new()
        for p in parts:
            part_into(bm, p, lod, o["pivot"], remap[p["slot"]])
        me = bpy.data.meshes.new(o["name"]); bm.to_mesh(me); bm.free()
        for s in used:
            me.materials.append(bpy.data.materials[m["materials"][s]["name"]])
        ob = bpy.data.objects.new(o["name"], me); bpy.context.scene.collection.objects.link(ob)
        if o["parent"]:
            ob.parent = obs[o["parent"]]; ob.location = Vector(o["pivot"]) - Vector(piv[o["parent"]])
        else:
            ob.location = o["pivot"]
        obs[o["name"]] = ob
    extra = {"sockets": [], "collision": []}
    if not lod:
        for s in m["sockets"]:
            par = s["parent"] or m["asset"]
            e = bpy.data.objects.new(s["name"], None); e.empty_display_type = "ARROWS"; e.empty_display_size = 0.03
            e.parent = obs[par]; e.location = Vector(s["location"]) - Vector(piv[par]); bpy.context.scene.collection.objects.link(e)
            e.rotation_mode = "QUATERNION"; e.rotation_quaternion = SS.socket_blender_quat(s)   # native == sidecar (UEB 48794/48821)
            extra["sockets"].append(s["name"])
        for c in m.get("collision", []):
            par = c["parent"] or m["asset"]
            me = coll_mesh(c, piv[par]); oc = bpy.data.objects.new(c["name"], me); oc.parent = obs[par]; oc.display_type = "WIRE"
            bpy.context.scene.collection.objects.link(oc); extra["collision"].append({"name": c["name"], "triangles": tris_of(me)})
    bpy.context.view_layer.update()
    return obs, extra


def measure(obs):
    pts = [o.matrix_world @ v.co for o in obs.values() for v in o.data.vertices]
    lo = [round(min(p[i] for p in pts), 4) for i in range(3)]; hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
    return {"objects": {n: tris_of(o.data) for n, o in obs.items()}, "triangles": sum(tris_of(o.data) for o in obs.values()),
            "bounds_min": lo, "bounds_max": hi, "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)],
            "materials": {n: [s.material.name for s in o.material_slots] for n, o in obs.items()}}


def export(path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, export_apply=True, export_extras=True, export_animations=False)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    o = args(); S = json.load(open(o.set, encoding="utf-8")); out = os.path.abspath(o.out)
    if any(x.lower() == "art" for x in out.replace("\\", "/").split("/")):
        raise SystemExit("refusing to write inside a watched art/ folder; stage elsewhere")
    only = set(filter(None, o.only.split(",")))
    for m in S["assets"]:
        if only and m["asset"] not in only:
            continue
        d = os.path.join(out, m["asset"]); os.makedirs(d, exist_ok=True); name = m["asset"]
        obs, extra = build(m, 0, False); got = measure(obs)
        glb = os.path.join(d, name + ".glb"); export(glb)
        blend = os.path.join(d, name + ".blend"); bpy.ops.wm.save_as_mainfile(filepath=blend)
        rep = {"asset": name, "status": "BUILT (staged, NOT READY)", "recipe_sha256": m["recipe_sha256"], "lod0": got,
               "sockets": extra["sockets"], "collision": extra["collision"],
               "files": {name + ".glb": {"bytes": os.path.getsize(glb), "sha256": sha(glb)}, name + ".blend": {"bytes": os.path.getsize(blend), "sha256": sha(blend)}}}
        pr = m["predicted"]
        rep["match"] = {"triangles": got["triangles"] == pr["triangles"],
                        "bounds": all(abs(got["bounds_min"][i] - pr["bounds_min"][i]) <= 0.001 and abs(got["bounds_max"][i] - pr["bounds_max"][i]) <= 0.001 for i in range(3)),
                        "objects": got["objects"] == pr["objects"], "collision_tris": sum(c["triangles"] for c in extra["collision"]) == pr["collision_tris"]}
        if pr["lod1_triangles"] is not None:
            obs1, _ = build(m, 1, False); g1 = measure(obs1)
            l1 = os.path.join(d, name + "_LOD1.glb"); export(l1)
            rep["lod1"] = {"triangles": g1["triangles"], "ratio": round(g1["triangles"] / got["triangles"], 3), "dimensions": g1["dimensions"]}
            rep["files"][name + "_LOD1.glb"] = {"bytes": os.path.getsize(l1), "sha256": sha(l1)}
            rep["match"]["lod1_triangles"] = g1["triangles"] == pr["lod1_triangles"]
        if m["sockets"]:   # stock glTF Interchange drops SOCKET_ empties (UEB 48518/48519): ship the UE-space sidecar too
            sp, sc = SS.write_for_glb(glb, m, d, name)
            rep["sockets_sidecar"] = os.path.basename(sp)
            rep["files"][os.path.basename(sp)] = {"bytes": os.path.getsize(sp), "sha256": sha(sp)}
            rep["match"]["sidecar_sockets"] = sorted(x["name"] for x in sc["sockets"]) == sorted(extra["sockets"])
        rep["ok"] = all(rep["match"].values())
        json.dump(rep, open(os.path.join(d, "build_report.json"), "w"), indent=1)
        print("KITJSON " + json.dumps({"asset": name, "ok": rep["ok"], "tris": got["triangles"], "lod1": rep.get("lod1", {}).get("triangles"), "match": rep["match"]}), flush=True)


if __name__ == "__main__":
    main()
