# SPDX-License-Identifier: MIT
"""Preview sheet for the G33 spring water kit, without re-exporting any mesh.
  blender -b --factory-startup --python preview_spring.py -- --manifest <G33_SpringWater.spring_variants.json> --mask <png> --root <bot-team dir> --tiles <tmp>
  python preview_spring.py --compose --manifest <...> --tiles <tmp> --out sheet.png
Each reused glb is imported read-only into an in-memory scene; only its water slot gets a node material built from the MI
params (WaterShallow/WaterDeep mixed by SiltMask x Turbidity, Roughness, Opacity)."""
import argparse, json, math, os, sys

SHOW = ["spring_1", "spring_2", "spring_5"]
GHOST = {"Prop_Well": "Prop_Well_M1"}       # preview only: the roof/posts slot hides the well water, so it is ghosted in memory


def water_material(bpy, P, mask_path):
    m = bpy.data.materials.new("WaterPreview"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
    bsdf = N["Principled BSDF"]; tc = N.new("ShaderNodeTexCoord")
    sc = N.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; sc.inputs["Scale"].default_value = P["SiltTiling"]["value"] * 4; Lk(tc.outputs["Object"], sc.inputs[0])
    im = N.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(mask_path); im.image.colorspace_settings.name = "Non-Color"; im.extension = "REPEAT"; Lk(sc.outputs[0], im.inputs[0])
    t = N.new("ShaderNodeMath"); t.operation = "MULTIPLY"; t.inputs[1].default_value = P["Turbidity"]["value"]; Lk(im.outputs["Color"], t.inputs[0])
    base = N.new("ShaderNodeMix"); base.data_type = "RGBA"; base.inputs[0].default_value = 0.5
    base.inputs[6].default_value = P["WaterShallow"]["linear_rgba"]; base.inputs[7].default_value = P["WaterDeep"]["linear_rgba"]
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; Lk(t.outputs[0], mix.inputs[0]); Lk(base.outputs[2], mix.inputs[6]); mix.inputs[7].default_value = P["WaterShallow"]["linear_rgba"]
    Lk(mix.outputs[2], bsdf.inputs["Base Color"])
    r = N.new("ShaderNodeMapRange"); Lk(t.outputs[0], r.inputs[0]); r.inputs[3].default_value = P["Roughness"]["value"]; r.inputs[4].default_value = 0.6; Lk(r.outputs[0], bsdf.inputs["Roughness"])
    bsdf.inputs["Alpha"].default_value = P["Opacity"]["value"]
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"
    return m


def render(o):
    import bpy
    from mathutils import Vector
    M = json.load(open(o.manifest, encoding="utf-8")); os.makedirs(o.tiles, exist_ok=True)
    for sid in SHOW:
        S = M["springs"][sid]
        for v in M["variants"]:
            bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=os.path.join(o.root, *S["mesh_path"].split("/")))
            obs = [ob for ob in bpy.data.objects if ob.type == "MESH"]; hit = 0
            for ob in obs:
                for ms in ob.material_slots:
                    if ms.material and ms.material.name.split(".")[0] == S["water_slot"]:
                        ms.material = water_material(bpy, v["params"], o.mask); hit += 1
            g = GHOST.get(S["mesh"])
            for ob in obs:
                for ms in ob.material_slots:
                    if g and ms.material and ms.material.name.split(".")[0] == g:
                        gm = ms.material.copy(); gm.use_nodes = True; b = gm.node_tree.nodes.get("Principled BSDF")
                        if b:
                            b.inputs["Alpha"].default_value = 0.12
                        try:
                            gm.surface_render_method = "BLENDED"
                        except AttributeError:
                            gm.blend_method = "BLEND"
                        ms.material = gm
            if not hit:
                raise SystemExit("water slot %s not found on %s" % (S["water_slot"], S["mesh"]))
            pts = [ob.matrix_world @ Vector(c) for ob in obs for c in ob.bound_box]
            lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)]); c = (lo + hi) / 2; L = max(hi - lo)
            cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = 1.9 * L; co = bpy.data.objects.new("c", cam); bpy.context.scene.collection.objects.link(co)
            d = Vector((0.7, -0.7, 0.95)).normalized(); co.location = c + d * L * 4; co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); bpy.context.scene.camera = co
            cam.clip_end = L * 10
            sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3.5; so = bpy.data.objects.new("s", sun); so.rotation_euler = (math.radians(35), math.radians(10), math.radians(30)); bpy.context.scene.collection.objects.link(so)
            s = bpy.context.scene; s.render.engine = "BLENDER_EEVEE_NEXT"; s.eevee.taa_render_samples = 16; s.render.resolution_x = s.render.resolution_y = 380
            w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.57, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
            s.view_settings.view_transform = "Standard"
            s.render.filepath = os.path.join(o.tiles, "%s_%s.png" % (sid, v["state"])); bpy.ops.render.render(write_still=True)


def compose(o):
    from PIL import Image, ImageDraw, ImageFont
    M = json.load(open(o.manifest, encoding="utf-8")); T, H, LW = 380, 30, 250
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
    except OSError:
        f = fb = ImageFont.load_default()
    W = Image.new("RGB", (LW + len(SHOW) * T, 92 + len(M["variants"]) * (T + H)), "white"); dr = ImageDraw.Draw(W)
    dr.text((12, 10), "G33 spring water kit (reused meshes, water slot only) | youtube-master 48984 | NOT READY", fill="black", font=fb)
    dr.text((12, 42), "clean(id) ? MI_Spring_Water_Clear : _Cloudy; SongClear fades 0 -> 1 on purify. Meshes untouched (well roof ghosted in this preview only).", fill=(70, 70, 70), font=f)
    for j, sid in enumerate(SHOW):
        S = M["springs"][sid]; dr.text((LW + j * T + 8, 68), "%s %s: %s" % (sid, S["name"], S["mesh"]), fill="black", font=f)
    for i, v in enumerate(M["variants"]):
        y = 92 + i * (T + H); P = v["params"]
        dr.text((10, y + 10), "%s (%s)" % (v["state"], v["draw_item"]), fill="black", font=fb)
        for n, k in enumerate(("WaterShallow", "WaterDeep")):
            dr.rectangle([10, y + 50 + n * 40, 40, y + 80 + n * 40], fill="#" + P[k]["srgb_hex"], outline="black"); dr.text((46, y + 56 + n * 40), "%s #%s" % (k, P[k]["srgb_hex"]), fill="black", font=f)
        dr.text((10, y + 140), "Turbidity %.2f  Opacity %.2f" % (P["Turbidity"]["value"], P["Opacity"]["value"]), fill="black", font=f)
        dr.text((10, y + 162), "Roughness %.2f  SongClear %.0f" % (P["Roughness"]["value"], P["SongClear"]["value"]), fill="black", font=f)
        dr.text((10, y + 184), v["name"], fill=(60, 60, 60), font=f)
        for j, sid in enumerate(SHOW):
            W.paste(Image.open(os.path.join(o.tiles, "%s_%s.png" % (sid, v["state"]))).convert("RGB"), (LW + j * T, y))
    W.save(o.out); print(o.out, W.size)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("--compose", action="store_true"); ap.add_argument("--manifest", required=True); ap.add_argument("--mask")
    ap.add_argument("--root"); ap.add_argument("--tiles", required=True); ap.add_argument("--out")
    o = ap.parse_args(argv); compose(o) if o.compose else render(o)
