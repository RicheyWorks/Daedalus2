# SPDX-License-Identifier: MIT
"""Preview contact sheet for a staged set (blender-team; every finished contest set gets one, prometheus 48809).
Two stages, one file:
  blender -b --factory-startup --python contact_sheet.py -- --dir <staging> --assets A,B,... --tiles <tmp>
      renders <tmp>/<asset>.png per asset (Workbench, material colours, front-right-above ortho view, Blender front = -Y)
      with a scale bar (1 m / 10 cm / 1 cm, the largest power of ten <= the asset's longest side) and <tmp>/<asset>.json.
  python contact_sheet.py --compose --tiles <tmp> --assets A,B,... --title "..." --out sheet.png
      lays the tiles on a grid with name, tris, size and the scale-bar length. Collision (UCX_/USP_) and sockets are hidden."""
import argparse, json, math, os, sys


def render(o):
    import bpy
    from mathutils import Vector
    os.makedirs(o.tiles, exist_ok=True)
    for a in o.assets.split(","):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        glb = os.path.join(o.dir, a, a + ".glb")
        bpy.ops.import_scene.gltf(filepath=glb)
        meshes = []
        for ob in list(bpy.data.objects):
            if ob.name.startswith(("UCX_", "USP_", "UCP_", "UBX_")):
                bpy.data.objects.remove(ob, do_unlink=True)
            elif ob.type == "MESH":
                meshes.append(ob)
        bpy.context.view_layer.update()
        pts = [ob.matrix_world @ Vector(c) for ob in meshes for c in ob.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
        size = hi - lo; L = max(size); bar = 10 ** math.floor(math.log10(L)) if L > 0 else 1.0
        t = bar * 0.025
        bpy.ops.mesh.primitive_cube_add(size=1, location=(lo.x + bar / 2, lo.y - max(0.08 * L, 2 * t), lo.z + t / 2))
        b = bpy.context.active_object; b.scale = (bar, t, t); b.name = "ScaleBar"
        mat = bpy.data.materials.new("bar"); mat.diffuse_color = (0.85, 0.1, 0.1, 1); b.data.materials.append(mat)
        c = (lo + hi) / 2; c.y -= 0.04 * L
        cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; cam.ortho_scale = 1.45 * max(size.x + 0.1 * L, size.z * 1.2, size.y + 0.2 * L, bar * 1.1)
        cam.clip_start = L * 0.001; cam.clip_end = L * 100
        co = bpy.data.objects.new("cam", cam); bpy.context.scene.collection.objects.link(co)
        d = Vector((0.55, -1.0, 0.45)).normalized(); co.location = c + d * L * 4
        co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); bpy.context.scene.camera = co
        s = bpy.context.scene; s.render.engine = "BLENDER_WORKBENCH"; s.display.shading.light = "STUDIO"; s.display.shading.color_type = "MATERIAL"
        s.display.shading.show_cavity = True; s.render.resolution_x = s.render.resolution_y = 420; s.render.film_transparent = False
        w = s.world or bpy.data.worlds.new("w"); s.world = w; w.color = (0.8, 0.8, 0.8)
        s.render.filepath = os.path.join(o.tiles, a + ".png"); bpy.ops.render.render(write_still=True)
        rep = json.load(open(os.path.join(o.dir, a, "build_report.json"), encoding="utf-8")) if os.path.exists(os.path.join(o.dir, a, "build_report.json")) else {}
        tris = (rep.get("lod0") or {}).get("triangles") or rep.get("triangles") or rep.get("tris")
        json.dump({"asset": a, "size_m": [round(v, 3) for v in size], "bar_m": bar, "tris": tris}, open(os.path.join(o.tiles, a + ".json"), "w"))


def compose(o):
    from PIL import Image, ImageDraw, ImageFont
    A = o.assets.split(","); cols = min(o.cols, len(A)); rows = math.ceil(len(A) / cols); T, H = 420, 70
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 17); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 26)
    except OSError:
        f = fb = ImageFont.load_default()
    W = Image.new("RGB", (cols * T, rows * (T + H) + 60), "white"); dr = ImageDraw.Draw(W)
    dr.text((14, 14), o.title, fill="black", font=fb)
    for i, a in enumerate(A):
        x, y = (i % cols) * T, 60 + (i // cols) * (T + H)
        W.paste(Image.open(os.path.join(o.tiles, a + ".png")).convert("RGB"), (x, y))
        j = json.load(open(os.path.join(o.tiles, a + ".json")))
        bar = j["bar_m"]; bl = "%g m" % bar if bar >= 1 else ("%g cm" % (bar * 100))
        dr.text((x + 8, y + T + 4), a, fill="black", font=f)
        dr.text((x + 8, y + T + 26), "%s tris | %s m | red bar = %s" % (j["tris"], " x ".join("%g" % v for v in j["size_m"]), bl), fill=(90, 90, 90), font=f)
        dr.rectangle([x, y, x + T - 1, y + T + H - 1], outline=(200, 200, 200))
    W.save(o.out); print(o.out, W.size)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("--compose", action="store_true"); ap.add_argument("--dir"); ap.add_argument("--assets", required=True)
    ap.add_argument("--tiles", required=True); ap.add_argument("--title", default=""); ap.add_argument("--out"); ap.add_argument("--cols", type=int, default=5)
    o = ap.parse_args(argv)
    compose(o) if o.compose else render(o)
