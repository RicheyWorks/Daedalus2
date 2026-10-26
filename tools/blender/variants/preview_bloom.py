# SPDX-License-Identifier: MIT
"""Preview sheet for the G48 bee-bloom beds: each Flora planted on Prop_Bee_FlowerBed, BLOOM vs FROST.
  blender -b --factory-startup --python preview_bloom.py -- --manifest <G48_BeeFlora.flora_variants.json> --stage <g48 staging dir> --root <bot-team dir> --tiles <tmp>
  python preview_bloom.py --compose --manifest <...> --tiles <tmp> --out sheet.png
Clumps are imported read-only at the bed's SOCKET_Plant_* (pick + yaw from the manifest). FROST applies the MI params to a
copy of each slot material in memory (lerp to FrostTint by FrostAmount, flat rime, roughness): the preview of M_BeeFlora."""
import argparse, json, math, os, sys


def frosted(mat, P):
    m = mat.copy(); m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
    if not b:
        return m
    bc = list(b.inputs["Base Color"].default_value)[:3]                  # same as M_BeeFlora: lerp to FrostTint, rime (flat 0.15 here, Fresnel in UE)
    a = P["FrostAmount"]["value"]; tint = P["FrostTint"]["linear_rgba"]; r = P["RimeAmount"]["value"] * 0.15
    c = [(1 - a) * bc[i] + a * tint[i] for i in range(3)]; c = [(1 - r) * c[i] + r * 0.9 for i in range(3)]
    b.inputs["Base Color"].default_value = c + [1.0]
    b.inputs["Roughness"].default_value = (1 - a) * b.inputs["Roughness"].default_value + a * P["FrostRoughness"]["value"]
    return m


def render(o):
    import bpy
    from mathutils import Vector
    M = json.load(open(o.manifest, encoding="utf-8")); os.makedirs(o.tiles, exist_ok=True); V = {v["name"]: v for v in M["variants"]}
    for f in M["flora_order"]:
        E = M["flora"][f]; paths = {m["mesh"]: (os.path.join(o.stage, m["mesh"], m["mesh"] + ".glb") if m["mesh_path"].startswith("staging/") else os.path.join(o.root, *m["mesh_path"].split("/"))) for m in E["meshes"]}
        for st in M["states"]:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=os.path.join(o.stage, M["bed"]["mesh"], M["bed"]["mesh"] + ".glb"))
            for ob in [x for x in bpy.data.objects if x.name.startswith(("UCX_", "SOCKET_"))]:
                ob.hide_render = True
            hit = 0
            for q in E["plants"]:
                before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=paths[q["mesh"]]); new = [x for x in bpy.data.objects if x not in before]
                for ob in new:
                    if ob.name.startswith(("UCX_", "SOCKET_")):
                        ob.hide_render = True
                    if ob.parent is None or ob.parent not in new:
                        ob.location = Vector(ob.location) + Vector(q["location_m"]); ob.rotation_mode = "XYZ"; ob.rotation_euler.z += math.radians(q["yaw_deg"])
                    if ob.type == "MESH" and st == "FROST":
                        for ms in ob.material_slots:
                            s = next((s for s in E["slots"] if ms.material and ms.material.name.split(".")[0] == s["slot"]), None)
                            if s:
                                ms.material = frosted(ms.material, V[s["mi"][st]]["params"]); hit += 1
            if st == "FROST" and not hit:
                raise SystemExit("no flora slot matched for " + f)
            obs = [ob for ob in bpy.data.objects if ob.type == "MESH" and not ob.hide_render]
            pts = [ob.matrix_world @ Vector(c) for ob in obs for c in ob.bound_box]
            lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)]); c = (lo + hi) / 2; L = max(hi - lo)
            cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = 1.25 * L; co = bpy.data.objects.new("c", cam); bpy.context.scene.collection.objects.link(co)
            d = Vector((0.45, -0.75, 0.8)).normalized(); co.location = c + d * L * 4; co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); bpy.context.scene.camera = co; cam.clip_end = L * 10
            sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3.5; so = bpy.data.objects.new("s", sun); so.rotation_euler = (math.radians(35), math.radians(10), math.radians(30)); bpy.context.scene.collection.objects.link(so)
            s = bpy.context.scene; s.render.engine = "BLENDER_EEVEE_NEXT"; s.eevee.taa_render_samples = 16; s.render.resolution_x = 400; s.render.resolution_y = 300
            w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.57, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
            s.view_settings.view_transform = "Standard"; s.render.filepath = os.path.join(o.tiles, "%s_%s.png" % (f, st)); bpy.ops.render.render(write_still=True)


def compose(o):
    from PIL import Image, ImageDraw, ImageFont
    M = json.load(open(o.manifest, encoding="utf-8")); TW, TH, H, LW = 400, 300, 26, 150; FL = M["flora_order"]
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 20)
    except OSError:
        f = fb = ImageFont.load_default()
    W = Image.new("RGB", (LW + len(FL) * TW, 96 + len(M["states"]) * (TH + H)), "white"); dr = ImageDraw.Draw(W)
    dr.text((12, 10), "G48 bee-bloom beds: Prop_Bee_FlowerBed + flora clumps on SOCKET_Plant_00..07 | pythagoras 49144 | NOT READY", fill="black", font=fb)
    dr.text((12, 40), "FROST = MI swap on the clump slots (M_BeeFlora), meshes untouched. CLOVER / HEATHER reuse pythagoras pcg-ecology glbs.", fill=(70, 70, 70), font=f)
    for j, fl in enumerate(FL):
        E = M["flora"][fl]; dr.text((LW + j * TW + 8, 66), "%s (%s)" % (fl, E["band"]), fill="black", font=fb)
        dr.text((LW + j * TW + 8, 88 - 4), E["meshes"][0]["mesh"] + (" ..V10" if len(E["meshes"]) > 1 else ""), fill=(60, 60, 60), font=f)
    for i, st in enumerate(M["states"]):
        y = 104 + i * (TH + H); dr.text((10, y + 12), st, fill="black", font=fb)
        dr.text((10, y + 42), "BLOOM: own colours" if st == "BLOOM" else "frost day hits\nopen blooms:\nFrostAmount,\nFrostTint, Rime", fill=(60, 60, 60), font=f)
        for j, fl in enumerate(FL):
            W.paste(Image.open(os.path.join(o.tiles, "%s_%s.png" % (fl, st))).convert("RGB"), (LW + j * TW, y))
    W.save(o.out); print(o.out, W.size)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("--compose", action="store_true"); ap.add_argument("--manifest", required=True); ap.add_argument("--stage")
    ap.add_argument("--root"); ap.add_argument("--tiles", required=True); ap.add_argument("--out")
    o = ap.parse_args(argv); compose(o) if o.compose else render(o)
