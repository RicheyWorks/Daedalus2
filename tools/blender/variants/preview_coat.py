# SPDX-License-Identifier: MIT
"""Preview sheet for a coat-variant manifest, without re-exporting the mesh (G28).
  blender -b --factory-startup --python preview_coat.py -- --glb <mesh.glb> --manifest <x.coat_variants.json> --mask <png> --tiles <tmp>
  python preview_coat.py --compose --manifest <...> --tiles <tmp> --out sheet.png
The glb is imported read-only into an in-memory scene; only the manifest's slot gets a node material:
lerp(CoatBase, CoatPattern, illustrative pattern) then the storm streak through the manifest's top-down mask projection.
Patterns here are stand-ins (Voronoi spots, wave stripes, noise ridges); in UE the G21 Gray-Scott field drives them."""
import argparse, json, math, os, sys

COLS = [("Spots", False), ("Stripes", False), ("Labyrinth", False), ("None", False), ("Stripes", True)]


def render(o):
    import bpy
    from mathutils import Vector
    M = json.load(open(o.manifest, encoding="utf-8")); os.makedirs(o.tiles, exist_ok=True)
    by = {(v["colour"], v["storm_marked"]): v for v in M["variants"]}; mk = M["mask"]
    for col in M["colours"]:
        for key, storm in COLS:
            bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=o.glb)
            v = by[(col, storm)]; P = v["params"]
            obs = [ob for ob in bpy.data.objects if ob.type == "MESH"]
            for ob in obs:
                for i, ms in enumerate(ob.material_slots):
                    if ms.material and ms.material.name.split(".")[0] == M["slot"]:
                        ms.material = coat_material(bpy, P, M, mk, o.mask, key, storm)
            pts = [ob.matrix_world @ Vector(c) for ob in obs for c in ob.bound_box]
            lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)]); c = (lo + hi) / 2; L = max(hi - lo)
            cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = 1.25 * L; co = bpy.data.objects.new("c", cam); bpy.context.scene.collection.objects.link(co)
            d = Vector((0.8, -0.55, 0.6)).normalized(); co.location = c + d * L * 4; co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); bpy.context.scene.camera = co
            sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3.5; so = bpy.data.objects.new("s", sun); so.rotation_euler = (math.radians(40), math.radians(10), math.radians(30)); bpy.context.scene.collection.objects.link(so)
            s = bpy.context.scene; s.render.engine = "BLENDER_EEVEE_NEXT"; s.eevee.taa_render_samples = 16; s.render.resolution_x = s.render.resolution_y = 360
            w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.57, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
            s.view_settings.view_transform = "Standard"
            s.render.filepath = os.path.join(o.tiles, "%s_%s%s.png" % (col, key, "_Storm" if storm else "")); bpy.ops.render.render(write_still=True)


def coat_material(bpy, P, M, mk, mask_path, key, storm):
    m = bpy.data.materials.new("CoatPreview"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
    bsdf = N["Principled BSDF"]; tc = N.new("ShaderNodeTexCoord")
    base = P["CoatBase"]["linear_rgba"]; pat = P["CoatPattern"]["linear_rgba"]
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs[6].default_value = base; mix.inputs[7].default_value = pat
    if key == "Spots":
        t = N.new("ShaderNodeTexVoronoi"); t.inputs["Scale"].default_value = 18; Lk(tc.outputs["Object"], t.inputs["Vector"])
        f = N.new("ShaderNodeMath"); f.operation = "LESS_THAN"; f.inputs[1].default_value = 0.32; Lk(t.outputs["Distance"], f.inputs[0]); fac = f.outputs[0]
    elif key == "Stripes":
        t = N.new("ShaderNodeTexWave"); t.inputs["Scale"].default_value = 9; t.wave_type = "BANDS"; t.bands_direction = "Y"; Lk(tc.outputs["Object"], t.inputs["Vector"])
        f = N.new("ShaderNodeMath"); f.operation = "GREATER_THAN"; f.inputs[1].default_value = 0.55; Lk(t.outputs["Fac"], f.inputs[0]); fac = f.outputs[0]
    elif key == "Labyrinth":
        t = N.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = 14; t.inputs["Detail"].default_value = 1.0; Lk(tc.outputs["Object"], t.inputs["Vector"])
        a = N.new("ShaderNodeMath"); a.operation = "SUBTRACT"; a.inputs[1].default_value = 0.5; Lk(t.outputs["Fac"], a.inputs[0])
        b = N.new("ShaderNodeMath"); b.operation = "ABSOLUTE"; Lk(a.outputs[0], b.inputs[0])
        f = N.new("ShaderNodeMath"); f.operation = "LESS_THAN"; f.inputs[1].default_value = 0.035; Lk(b.outputs[0], f.inputs[0]); fac = f.outputs[0]
    else:
        fac = None
    if fac is not None:
        Lk(fac, mix.inputs[0])
    else:
        mix.inputs[0].default_value = 0.0
    out = mix.outputs[2]
    amt = P["StormStreakAmount"]["value"]
    if amt > 0:
        sx = N.new("ShaderNodeSeparateXYZ"); Lk(tc.outputs["Object"], sx.inputs[0])
        u = N.new("ShaderNodeMapRange"); u.inputs[1].default_value = mk["u"]["min_cm"] / 100; u.inputs[2].default_value = (mk["u"]["min_cm"] + mk["u"]["size_cm"]) / 100; Lk(sx.outputs[0], u.inputs[0])
        ny = N.new("ShaderNodeMath"); ny.operation = "MULTIPLY"; ny.inputs[1].default_value = -1.0; Lk(sx.outputs[1], ny.inputs[0])   # UE Y = -Blender Y
        vv = N.new("ShaderNodeMapRange"); vv.inputs[1].default_value = mk["v"]["min_cm"] / 100; vv.inputs[2].default_value = (mk["v"]["min_cm"] + mk["v"]["size_cm"]) / 100; Lk(ny.outputs[0], vv.inputs[0])
        cb = N.new("ShaderNodeCombineXYZ"); Lk(u.outputs[0], cb.inputs[0]); Lk(vv.outputs[0], cb.inputs[1])
        im = N.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(mask_path); im.image.colorspace_settings.name = "Non-Color"; im.extension = "CLIP"; Lk(cb.outputs[0], im.inputs[0])
        fd = N.new("ShaderNodeMath"); fd.operation = "MULTIPLY"; fd.inputs[1].default_value = amt; Lk(im.outputs["Color"], fd.inputs[0])
        m2 = N.new("ShaderNodeMix"); m2.data_type = "RGBA"; Lk(fd.outputs[0], m2.inputs[0]); Lk(out, m2.inputs[6]); m2.inputs[7].default_value = M["parent_material"]["storm_streak_colour"]["linear_rgba"]
        mt = N.new("ShaderNodeMapRange"); Lk(fd.outputs[0], mt.inputs[0]); mt.inputs[3].default_value = 0.0; mt.inputs[4].default_value = M["parent_material"]["storm_streak_colour"]["metallic"]
        Lk(mt.outputs[0], bsdf.inputs["Metallic"]); out = m2.outputs[2]
    Lk(out, bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.7
    return m


def compose(o):
    from PIL import Image, ImageDraw, ImageFont
    M = json.load(open(o.manifest, encoding="utf-8")); T, H, LW = 360, 46, 240
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
    except OSError:
        f = fb = ImageFont.load_default()
    W = Image.new("RGB", (LW + len(COLS) * T, 90 + len(M["colours"]) * (T + H)), "white"); dr = ImageDraw.Draw(W)
    dr.text((12, 10), "G28 Turing-coat pup variants on %s (mesh untouched, art-master-flex) | oddsreaper 48824 | blender-team 2026-10-19" % M["asset"], fill="black", font=fb)
    dr.text((12, 42), "Coat slot only: CoatBase -> CoatPattern by coat key (patterns illustrative; the G21 Gray-Scott field drives them in UE). Silver storm streak = StormStreakMask x StormStreakAmount.", fill=(70, 70, 70), font=f)
    for j, (k, st) in enumerate(COLS):
        dr.text((LW + j * T + 8, 66), "coat key %s%s" % (k, " + storm-mark" if st else ""), fill="black", font=f)
    by = {(v["colour"], v["storm_marked"]): v for v in M["variants"]}
    for i, col in enumerate(M["colours"]):
        y = 90 + i * (T + H); b = by[(col, False)]["params"]
        dr.text((10, y + 10), col, fill="black", font=fb)
        for n, (lab, hx) in enumerate((("CoatBase", b["CoatBase"]["srgb_hex"]), ("CoatPattern", b["CoatPattern"]["srgb_hex"]))):
            dr.rectangle([10, y + 50 + n * 46, 40, y + 80 + n * 46], fill="#" + hx, outline="black"); dr.text((46, y + 56 + n * 46), "%s #%s" % (lab, hx), fill="black", font=f)
        for j, (k, st) in enumerate(COLS):
            x = LW + j * T; W.paste(Image.open(os.path.join(o.tiles, "%s_%s%s.png" % (col, k, "_Storm" if st else ""))).convert("RGB"), (x, y))
            dr.text((x + 6, y + T + 4), "%s/%s%s -> %s" % (k, col, "/Storm" if st else "", M["lookup"]["%s/%s%s" % (k, col, "/Storm" if st else "")]), fill=(60, 60, 60), font=f)
    W.save(o.out); print(o.out, W.size)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("--compose", action="store_true"); ap.add_argument("--glb"); ap.add_argument("--manifest", required=True)
    ap.add_argument("--mask"); ap.add_argument("--tiles", required=True); ap.add_argument("--out")
    o = ap.parse_args(argv); compose(o) if o.compose else render(o)
