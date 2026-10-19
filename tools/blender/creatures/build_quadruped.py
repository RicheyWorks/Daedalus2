# SPDX-License-Identifier: MIT
"""Build a blender-quadruped/v1 (or any bones/parts/clips creature recipe, e.g. blender-insect/v1) headless into a skinned glb with Idle/Walk/Run glTF animations (blender-team).
  blender -b --factory-startup --python tools/blender/creatures/build_quadruped.py -- --recipe <x.quad.json> --out <staging dir>
Writes <out>/<Asset>/<Asset>.glb (mesh + armature + skin + 3 animations), <Asset>_LOD1.glb (same skeleton, skin, no clips),
<Asset>.blend, build_report.json (tris, bones, bind result per part, weight checks, glb read-back: joints, animations, channels).
Recipes with "sockets" (bone-bound, e.g. bird_rig G142 SOCKET_LegBand) also get SOCKET_ empties parented to their bones in both glbs
and <Asset>.sockets.json (bone, rest location, offset from the bone head in model axes / bone-local / UE cm): UE builds skeleton
sockets from the sidecar, since stock glTF Interchange does not turn empties into skeleton sockets.
Refuses a watched art/ folder. Never marks anything READY."""
import argparse, hashlib, json, os, struct, sys
import bpy, bmesh
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import quadruped_rig as Q
from build_kit import part_into, linear, tris_of, sha


def args():
    a = argparse.ArgumentParser(); a.add_argument("--recipe", required=True); a.add_argument("--out", required=True)
    return a.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def materials(m):
    for md in m["materials"]:
        mat = bpy.data.materials.new(md["name"]); mat.use_nodes = True; rgb = linear(md["hex"])
        pb = mat.node_tree.nodes["Principled BSDF"]
        pb.inputs["Base Color"].default_value = rgb; pb.inputs["Roughness"].default_value = md["roughness"]
        pb.inputs["Metallic"].default_value = md["metallic"]; mat.diffuse_color = rgb


def build_mesh(m, lod):
    parts = [p for p in m["parts"] if K.in_lod(p, lod)]
    used = sorted({p["slot"] for p in parts}); remap = {s: i for i, s in enumerate(used)}
    bm = bmesh.new(); ranges = []
    for p in parts:
        a = len(bm.verts); part_into(bm, p, lod, (0, 0, 0), remap[p["slot"]]); ranges.append((p["name"], p["bone"], a, len(bm.verts)))
    me = bpy.data.meshes.new(m["asset"]); bm.to_mesh(me); bm.free()
    for s in used:
        me.materials.append(bpy.data.materials[m["materials"][s]["name"]])
    ob = bpy.data.objects.new(m["asset"], me); bpy.context.scene.collection.objects.link(ob)
    return ob, ranges


def build_armature(m):
    arm = bpy.data.armatures.new(m["asset"] + "_Skeleton"); ob = bpy.data.objects.new(m["asset"] + "_Armature", arm)
    bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for b in m["bones"]:
        eb = arm.edit_bones.new(b["name"]); eb.head = b["head"]; eb.tail = b["tail"]; eb.roll = 0.0
    for b in m["bones"]:
        if b["parent"]:
            arm.edit_bones[b["name"]].parent = arm.edit_bones[b["parent"]]; arm.edit_bones[b["name"]].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def bind(m, me_ob, arm_ob, ranges):
    """ARMATURE_AUTO (bone heat), then validate per part; rigid fallback for parts heat got wrong; <= 4 influences, normalised."""
    bpy.ops.object.select_all(action="DESELECT"); me_ob.select_set(True); arm_ob.select_set(True)
    bpy.context.view_layer.objects.active = arm_ob
    auto_ok = m.get("bind_mode", "auto") != "rigid"      # rigid recipes (insects: tiny, plate-like parts) skip bone heat
    rigid = {p["name"] for p in m["parts"] if p.get("rigid")}
    try:
        if not auto_ok:
            raise RuntimeError("recipe bind_mode rigid")
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    except Exception as e:      # heat failure: parent with empty groups, then everything falls back to rigid
        auto_ok = False; print("ARMATURE_AUTO failed:", e)
        bpy.ops.object.parent_set(type="ARMATURE_NAME")
    for b in m["bones"]:
        if b["name"] not in me_ob.vertex_groups:
            me_ob.vertex_groups.new(name=b["name"])
    G = {g.index: g.name for g in me_ob.vertex_groups}; vg = me_ob.vertex_groups; me = me_ob.data
    result = {"auto_parts": [], "rigid_parts": []}
    for name, bone, a, z in ranges:
        good = name not in rigid
        for i in range(a, z if good else a):
            ws = [(g.weight, G[g.group]) for g in me.vertices[i].groups if g.weight > 1e-4]
            if not ws or Q.hops(m["bones"], max(ws)[1], bone) > 2:
                good = False; break
        if good and auto_ok:
            result["auto_parts"].append(name)
        else:
            idx = list(range(a, z))
            for g in vg: g.remove(idx)
            vg[bone].add(idx, 1.0, "REPLACE"); result["rigid_parts"].append(name)
    maxinf, unweighted, badsum = 0, 0, 0
    for v in me.vertices:
        ws = sorted(((g.weight, g.group) for g in v.groups if g.weight > 1e-4), reverse=True)
        keep = ws[:4]; tot = sum(w for w, _ in keep)
        for w, gi in ws[4:]: vg[G[gi]].remove([v.index])
        for w, gi in keep: vg[G[gi]].add([v.index], w / tot, "REPLACE")
    for v in me.vertices:
        ws = [g.weight for g in v.groups if g.weight > 1e-4]
        maxinf = max(maxinf, len(ws)); unweighted += not ws; badsum += abs(sum(ws) - 1) > 1e-3
    result.update({"method": "ARMATURE_AUTO bone heat" if auto_ok else ("rigid per part (recipe bind_mode)" if m.get("bind_mode") == "rigid" else "ARMATURE_AUTO failed -> rigid"), "max_influences": maxinf, "unweighted_vertices": unweighted,
                   "non_normalised_vertices": badsum, "vertices": len(me.vertices)})
    return result


def add_sockets(m, arm_ob):
    """SOCKET_ empties parented to their bones at the rest location. -> sidecar rows."""
    rows = []
    bpy.context.view_layer.update()
    for sk in m.get("sockets", []):
        e = bpy.data.objects.new(sk["name"], None); e.empty_display_type = "ARROWS"; e.empty_display_size = 0.03
        bpy.context.scene.collection.objects.link(e)
        e.parent = arm_ob; e.parent_type = "BONE"; e.parent_bone = sk["bone"]
        bpy.context.view_layer.update()
        e.matrix_world = Matrix.Translation(Vector(sk["location"]))
        bone = arm_ob.data.bones[sk["bone"]]
        local = bone.matrix_local.inverted() @ Vector(sk["location"])
        x, y, z = sk["offset_from_bone_head"]
        rows.append({"name": sk["name"], "bone": sk["bone"], "location_m": sk["location"], "offset_from_bone_head_m": sk["offset_from_bone_head"],
                     "offset_bone_local_m": [round(v, 6) + 0.0 for v in local], "offset_from_bone_head_ue_cm": [round(100 * x, 3) + 0.0, round(-100 * y, 3) + 0.0, round(100 * z, 3) + 0.0],
                     "location_ue_cm": [round(100 * sk["location"][0], 3) + 0.0, round(-100 * sk["location"][1], 3) + 0.0, round(100 * sk["location"][2], 3) + 0.0],
                     "rotation": sk.get("rotation", [0, 0, 0])})
    return rows


def bake_clips(m, arm_ob):
    ad = arm_ob.animation_data_create(); made = []
    for name, c in m["clips"].items():
        act = bpy.data.actions.new(name); act.use_fake_user = True; ad.action = act
        for pb in arm_ob.pose.bones:
            pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
        for bone, tr in c["tracks"].items():
            pb = arm_ob.pose.bones[bone]
            for f, v in tr.get("rot", []):
                pb.rotation_euler = v; pb.keyframe_insert("rotation_euler", frame=f, group=bone)
            for f, v in tr.get("loc", []):
                pb.location = v; pb.keyframe_insert("location", frame=f, group=bone)
        act.use_frame_range = True; act.frame_start = 0; act.frame_end = c["frames"]; act.use_cyclic = c["loop"]
        tk = ad.nla_tracks.new(); tk.name = name; tk.strips.new(name, 0, act)
        made.append({"name": name, "frames": c["frames"], "fps": c["fps"], "fcurves": len(act.fcurves)})
    ad.action = None
    for pb in arm_ob.pose.bones:
        pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.scene.render.fps = Q.FPS
    return made


def export(path, anims):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, export_apply=False, export_skins=True, export_all_influences=False,
                              export_animations=anims, export_animation_mode="ACTIONS", export_force_sampling=True, export_reset_pose_bones=True,
                              export_def_bones=False, export_extras=True)


def readback(path):
    b = open(path, "rb").read(); n = struct.unpack_from("<I", b, 12)[0]; d = json.loads(b[20:20 + n])
    tris = sum((d["accessors"][q["indices"]]["count"] if "indices" in q else d["accessors"][q["attributes"]["POSITION"]]["count"]) // 3 for mm in d["meshes"] for q in mm["primitives"])
    an = []
    for a in d.get("animations", []):
        tmax = max(d["accessors"][s["input"]]["max"][0] for s in a["samplers"])
        an.append({"name": a["name"], "channels": len(a["channels"]), "seconds": round(tmax, 4)})
    return {"triangles": tris, "skins": len(d.get("skins", [])), "joints": [len(s["joints"]) for s in d.get("skins", [])],
            "joint_names": sorted(d["nodes"][j]["name"] for s in d.get("skins", []) for j in s["joints"]),
            "skinned_attrs": all("JOINTS_0" in q["attributes"] and "WEIGHTS_0" in q["attributes"] for mm in d["meshes"] for q in mm["primitives"]),
            "inverse_bind_matrices": all("inverseBindMatrices" in s for s in d.get("skins", [])), "animations": an,
            "mesh_nodes": [x["name"] for x in d["nodes"] if "mesh" in x],
            "socket_nodes": sorted(d["nodes"][c]["name"] for x in d["nodes"] for c in x.get("children", [])
                                   if d["nodes"][c]["name"].startswith("SOCKET_") and x["name"] in {d["nodes"][j]["name"] for s in d.get("skins", []) for j in s["joints"]})}


def one(m, lod, out_glb):
    bpy.ops.wm.read_factory_settings(use_empty=True); materials(m)
    me_ob, ranges = build_mesh(m, lod); arm_ob = build_armature(m); br = bind(m, me_ob, arm_ob, ranges)
    socks = add_sockets(m, arm_ob)
    clips = bake_clips(m, arm_ob) if lod == 0 else []
    pts = [v.co for v in me_ob.data.vertices]; lo = [round(min(p[i] for p in pts), 4) for i in range(3)]; hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
    t = tris_of(me_ob.data); export(out_glb, lod == 0)
    return {"triangles": t, "bounds_min": lo, "bounds_max": hi, "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)], "bind": br, "clips": clips, "sockets": socks}


def main():
    o = args(); m = json.load(open(o.recipe, encoding="utf-8")); out = os.path.abspath(o.out)
    if any(x.lower() == "art" for x in out.replace("\\", "/").split("/")):
        raise SystemExit("refusing to write inside a watched art/ folder; stage elsewhere")
    a = m["asset"]; d = os.path.join(out, a); os.makedirs(d, exist_ok=True)
    g0 = os.path.join(d, a + ".glb"); g1 = os.path.join(d, a + "_LOD1.glb"); bl = os.path.join(d, a + ".blend")
    r1 = one(m, 1, g1); r0 = one(m, 0, g0); bpy.ops.wm.save_as_mainfile(filepath=bl)
    rb0, rb1 = readback(g0), readback(g1); pr = m["predicted"]; bones = sorted(b["name"] for b in m["bones"])
    rep = {"asset": a, "status": "BUILT (staged, NOT READY)", "schema": m["schema"], "lod0": r0, "lod1": r1, "glb": rb0, "glb_lod1": rb1,
           "files": {f: {"bytes": os.path.getsize(os.path.join(d, f)), "sha256": sha(os.path.join(d, f))} for f in (a + ".glb", a + "_LOD1.glb", a + ".blend")}}
    rep["match"] = {"triangles": r0["triangles"] == pr["triangles"] == rb0["triangles"], "lod1_triangles": r1["triangles"] == pr["lod1_triangles"] == rb1["triangles"],
                    "bounds": all(abs(r0["bounds_min"][i] - pr["bounds_min"][i]) <= 0.001 and abs(r0["bounds_max"][i] - pr["bounds_max"][i]) <= 0.001 for i in range(3)),
                    "skeleton": rb0["joint_names"] == bones and rb1["joint_names"] == bones, "skinned": rb0["skinned_attrs"] and rb1["skinned_attrs"] and rb0["inverse_bind_matrices"],
                    "clips": sorted(x["name"] for x in rb0["animations"]) == sorted(m["clips"]) and all(abs(x["seconds"] - m["clips"][x["name"]]["seconds"]) < 0.02 for x in rb0["animations"]),
                    "lod1_no_clips": rb1["animations"] == [],
                    "weights": all(r["bind"]["max_influences"] <= 4 and r["bind"]["unweighted_vertices"] == 0 and r["bind"]["non_normalised_vertices"] == 0 for r in (r0, r1))}
    if m.get("sockets"):
        want = sorted(x["name"] for x in m["sockets"])
        rep["match"]["sockets_on_joints"] = rb0["socket_nodes"] == want and rb1["socket_nodes"] == want
        sc = {"schema": "bb-skeletal-sockets/1", "asset": a, "status": "STAGED NOT READY", "sockets": r0["sockets"],
              "how": "UE Skeleton editor: Add Socket on <bone>, Relative Location = offset_from_bone_head_ue_cm rotated into the imported bone frame "
                     "(offset_bone_local_m is the same offset in the Blender bone frame), Relative Rotation 0; the glb also carries the SOCKET_ empty "
                     "as a child of the joint for checking. Rotation [0, 0, 0] = model axes at rest (Z up)."}
        sp = os.path.join(d, a + ".sockets.json")
        with open(sp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(sc, f, indent=1); f.write("\n")
        rep["files"][a + ".sockets.json"] = {"bytes": os.path.getsize(sp), "sha256": sha(sp)}
    rep["ok"] = all(rep["match"].values())
    json.dump(rep, open(os.path.join(d, "build_report.json"), "w"), indent=1)
    print("QUADJSON " + json.dumps({"asset": a, "ok": rep["ok"], "tris": r0["triangles"], "lod1": r1["triangles"], "match": rep["match"], "bind": {k: (len(v) if isinstance(v, list) else v) for k, v in r0["bind"].items()},
                                     "anims": rb0["animations"]}), flush=True)


if __name__ == "__main__":
    main()
