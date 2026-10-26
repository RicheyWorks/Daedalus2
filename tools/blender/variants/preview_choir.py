# SPDX-License-Identifier: MIT
"""Preview sheet for G53: the choir stone Quiet vs Humming (groove MI applied in memory) and the rope bridge chained by
sockets (anchor + 2 segments + anchor) at strength 3 / 2 / 1 and snapped (S1 + Snapped).
  blender -b --factory-startup --python preview_choir.py -- --manifest <G53_ChoirStones.choir_variants.json> --kit <ytm_g53.kit.json> --stage <dir> --tiles <tmp>
  python preview_choir.py --compose --manifest <...> --tiles <tmp> --out sheet.png"""
import argparse, json, math, os, sys

TILES = [("stone", "Quiet"), ("stone", "Humming"), ("bridge", "3"), ("bridge", "2"), ("bridge", "1"), ("bridge", "0")]


def _imp(bpy, path, loc, yaw=0.0):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=path); new = [x for x in bpy.data.objects if x not in before]
    for ob in new:
        if ob.name.startswith(("UCX_", "SOCKET_")):
            ob.hide_render = True
        if ob.parent is None or ob.parent not in new:
            ob.location = loc; ob.rotation_mode = "XYZ"; ob.rotation_euler.z += math.radians(yaw)
    return new


def render(o):
    import bpy
    from mathutils import Vector
    M = json.load(open(o.manifest, encoding="utf-8")); K = {a["asset"]: a for a in json.load(open(o.kit, encoding="utf-8"))["assets"]}; os.makedirs(o.tiles, exist_ok=True)
    V = {v["state"]: v["params"] for v in M["variants"]}
    def glb(a):
        return os.path.join(o.stage, a, a + ".glb")
    def sk(a, n):
        return Vector(next(s["location"] for s in K[a]["sockets"] if s["name"] == n))
    for kind, st in TILES:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if kind == "stone":
            for ob in _imp(bpy, glb(M["stone"]["mesh"]), Vector((0, 0, 0))):
                for ms in getattr(ob, "material_slots", []):
                    if ms.material and ms.material.name.split(".")[0] == M["stone"]["groove_slot"]:
                        m = ms.material.copy(); b = m.node_tree.nodes.get("Principled BSDF"); P = V[st]
                        b.inputs["Base Color"].default_value = P["GrooveBase"]["linear_rgba"]; b.inputs["Roughness"].default_value = P["Roughness"]["value"]
                        b.inputs["Emission Color"].default_value = P["EmissiveColour"]["linear_rgba"]; b.inputs["Emission Strength"].default_value = P["EmissiveStrength"]["value"] / 3
                        ms.material = m
        else:
            B = M["bridge"]; an = B["anchor"]["mesh"]; segs = [B["states"][st]["mesh"]] * 2 if st != "0" else [B["states"]["1"]["mesh"], B["states"]["0"]["mesh"]]
            _imp(bpy, glb(an), Vector((0, 0, 0))); end = sk(an, "SOCKET_Segment")
            for s in segs:                                     # place by socket: this segment's A onto the previous B
                org = end - sk(s, "SOCKET_Anchor_A"); _imp(bpy, glb(s), org); end = org + sk(s, "SOCKET_Anchor_B")
            a_s = sk(an, "SOCKET_Segment"); _imp(bpy, glb(an), Vector((end.x + a_s.x, 0, end.z - a_s.z)), 180)
        obs = [ob for ob in bpy.data.objects if ob.type == "MESH" and not ob.hide_render]
        pts = [ob.matrix_world @ Vector(c) for ob in obs for c in ob.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)]); c = (lo + hi) / 2; L = max(hi - lo)
        cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = 1.25 * L; co = bpy.data.objects.new("c", cam); bpy.context.scene.collection.objects.link(co)
        d = Vector((0.35, -0.8, 0.45) if kind == "bridge" else (0.5, -0.85, 0.35)).normalized(); co.location = c + d * L * 4; co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.camera = co; cam.clip_end = L * 10
        sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3.0 if st != "Humming" else 1.6; so = bpy.data.objects.new("s", sun); so.rotation_euler = (math.radians(35), math.radians(10), math.radians(30)); bpy.context.scene.collection.objects.link(so)
        s = bpy.context.scene; s.render.engine = "BLENDER_EEVEE_NEXT"; s.eevee.taa_render_samples = 16; s.render.resolution_x = 420; s.render.resolution_y = 320
        w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.53, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9 if st != "Humming" else 0.45
        s.view_settings.view_transform = "Standard"; s.render.filepath = os.path.join(o.tiles, "%s_%s.png" % (kind, st)); bpy.ops.render.render(write_still=True)


def compose(o):
    from PIL import Image, ImageDraw, ImageFont
    M = json.load(open(o.manifest, encoding="utf-8")); TW, TH, H = 420, 320, 44
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 20)
    except OSError:
        f = fb = ImageFont.load_default()
    W = Image.new("RGB", (3 * TW, 80 + 2 * (TH + H)), "white"); dr = ImageDraw.Draw(W)
    dr.text((12, 10), "G53 Choir Stones: ChoirStone groove MI + rope bridge strength states | youtube-master 49161 | NOT READY", fill="black", font=fb)
    dr.text((12, 40), "Humming = carve() CARVED (EmissiveStrength x RangeScale; preview /3). Bridges placed purely by sockets: Anchor + 2 x 2 m segments + Anchor (yaw 180).", fill=(70, 70, 70), font=f)
    lab = {("stone", "Quiet"): "ChoirStone Quiet (blank)", ("stone", "Humming"): "ChoirStone Humming (carved)", ("bridge", "3"): "strength 3: Seg_S3 x2",
           ("bridge", "2"): "strength 2: Seg_S2 x2 (fraying)", ("bridge", "1"): "strength 1: Seg_S1 x2 (badly frayed)", ("bridge", "0"): "strength 0: Seg_S1 + Seg_Snapped"}
    for i, k in enumerate(TILES):
        x, y = (i % 3) * TW, 70 + (i // 3) * (TH + H)
        dr.text((x + 8, y + 6), lab[k], fill="black", font=fb); W.paste(Image.open(os.path.join(o.tiles, "%s_%s.png" % k)).convert("RGB"), (x, y + H - 8))
    W.save(o.out); print(o.out, W.size)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("--compose", action="store_true"); ap.add_argument("--manifest", required=True); ap.add_argument("--kit"); ap.add_argument("--stage")
    ap.add_argument("--tiles", required=True); ap.add_argument("--out")
    o = ap.parse_args(argv); compose(o) if o.compose else render(o)
