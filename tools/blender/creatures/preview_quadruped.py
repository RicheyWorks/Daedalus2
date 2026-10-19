# SPDX-License-Identifier: MIT
"""Pose preview sheet for a blender-quadruped/v1 build (reusable): the rest pose at 3/4 view plus frames sampled from every baked
clip in the exported glb (side view), so the sheet shows the rig actually moves.
  blender -b --factory-startup --python preview_quadruped.py -- --glb <Asset.glb> --tiles <tmp>
  python preview_quadruped.py --compose --tiles <tmp> --title "..." --out sheet.png"""
import argparse, json, math, os, sys

SAMPLES = {"Idle": (0.5,), "Walk": (0.0, 0.25, 0.5, 0.75), "Run": (0.0, 0.33, 0.66)}


def render(o):
    import bpy
    from mathutils import Vector
    os.makedirs(o.tiles, exist_ok=True); shots = []
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=o.glb)
    arm = next(x for x in bpy.data.objects if x.type == "ARMATURE"); meshes = [x for x in bpy.data.objects if x.type == "MESH"]
    acts = {a.name: a for a in bpy.data.actions}
    def act(clip):
        return next((a for n, a in acts.items() if n == clip or n.endswith("|" + clip) or n.startswith(clip)), None)
    s = bpy.context.scene; s.render.engine = "BLENDER_EEVEE_NEXT"; s.eevee.taa_render_samples = 16; s.render.resolution_x = 360; s.render.resolution_y = 300
    w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.57, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    s.view_settings.view_transform = "Standard"
    sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3.5; so = bpy.data.objects.new("s", sun); so.rotation_euler = (math.radians(35), math.radians(10), math.radians(30)); s.collection.objects.link(so)
    cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; co = bpy.data.objects.new("c", cam); s.collection.objects.link(co); s.camera = co
    def frame_cam(d):
        pts = [m.matrix_world @ Vector(c) for m in meshes for c in m.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)]); c = (lo + hi) / 2; L = max(hi - lo) * 1.15
        cam.ortho_scale = 1.15 * L; dv = Vector(d).normalized(); co.location = c + dv * L * 4; co.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler(); cam.clip_end = L * 10
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    s.frame_set(0); frame_cam((0.6, -0.75, 0.45)); s.render.filepath = os.path.join(o.tiles, "rest.png"); bpy.ops.render.render(write_still=True); shots.append(["rest", "rest pose", 0])
    side = (1.0, -0.12, 0.18)
    for clip, fr in SAMPLES.items():
        a = act(clip)
        if a is None:
            raise SystemExit("clip %s not in glb (actions: %s)" % (clip, sorted(acts)))
        arm.animation_data_create(); arm.animation_data.action = a; f0, f1 = a.frame_range
        for k, t in enumerate(fr):
            f = int(round(f0 + (f1 - f0) * t)); s.frame_set(f); frame_cam(side)
            n = "%s_%d" % (clip, k); s.render.filepath = os.path.join(o.tiles, n + ".png"); bpy.ops.render.render(write_still=True); shots.append([n, "%s f%d" % (clip, f), f])
    json.dump(shots, open(os.path.join(o.tiles, "shots.json"), "w"))


def compose(o):
    from PIL import Image, ImageDraw, ImageFont
    shots = json.load(open(os.path.join(o.tiles, "shots.json"))); TW, TH, H, cols = 360, 300, 26, 3
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15); fb = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 19)
    except OSError:
        f = fb = ImageFont.load_default()
    rows = (len(shots) + cols - 1) // cols; W = Image.new("RGB", (cols * TW, 50 + rows * (TH + H)), "white"); dr = ImageDraw.Draw(W)
    dr.text((10, 12), o.title, fill="black", font=fb)
    for i, (n, lab, _) in enumerate(shots):
        x, y = (i % cols) * TW, 50 + (i // cols) * (TH + H)
        W.paste(Image.open(os.path.join(o.tiles, n + ".png")).convert("RGB"), (x, y)); dr.text((x + 8, y + TH + 4), lab, fill="black", font=f)
    W.save(o.out); print(o.out, W.size)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("--compose", action="store_true"); ap.add_argument("--glb"); ap.add_argument("--tiles", required=True)
    ap.add_argument("--title", default=""); ap.add_argument("--out")
    o = ap.parse_args(argv); compose(o) if o.compose else render(o)
