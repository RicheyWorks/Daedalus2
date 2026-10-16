# SPDX-License-Identifier: MIT
"""Showcase renders for Team Claude lands: Cycles (CPU, denoised) with a physical sky. They are honest and comparable.

BEFORE and AFTER go through the same function, so camera, lens, light, sky, samples and resolution all match. Every
image is labelled a Blender render (not an Unreal capture), and a sidecar json records the settings, the source files
and their hashes, and the time. It runs headless anywhere `bpy` imports, so cloud renders need no PC time.

    python showcase_render.py OUT_DIR --glb A.glb [B.glb ...] --tag after --view hero|detail|top [--focus x,y,z]
        [--res 2560x1600] [--samples 96] [--frame auto|x,y,z,dist]

  * view hero: three-quarter island view; distance comes from the scene bounds, or --frame.
  * view detail: close three-quarter on --focus.
  * view top: orthographic plan.
GLB files import Y-up as Blender Z-up, so the coordinates match the recipe's.
"""
import hashlib
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load(glbs):
    for g in glbs:
        bpy.ops.import_scene.gltf(filepath=g)
    for o in bpy.data.objects:
        if o.name.startswith(("UCX_", "MKR_")) or "_LOD" in o.name:
            o.hide_render = True
            o.hide_set(True)
    vertex_colours()


def vertex_colours():
    """The glTF importer leaves COLOR_0 unused; the HD terrain is coloured by it. Wire any colour attribute into Base
    Color (multiplied with the material colour), so imported islands shade the way they do in their build scene."""
    done = set()
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.color_attributes:
            continue
        layer = o.data.color_attributes[0].name
        for m in o.data.materials:
            if not m or not m.use_nodes or m.name in done:
                continue
            nt = m.node_tree
            p = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if p is None or p.inputs["Base Color"].is_linked and any(l.from_node.type in ("VERTEX_COLOR", "ATTRIBUTE") for l in p.inputs["Base Color"].links):
                continue
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.layer_name = layer
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            src = p.inputs["Base Color"].links[0].from_socket if p.inputs["Base Color"].is_linked else None
            if src is not None:
                nt.links.new(src, mix.inputs["A"])
            else:
                mix.inputs["A"].default_value = p.inputs["Base Color"].default_value
            nt.links.new(vc.outputs["Color"], mix.inputs["B"])
            nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
            done.add(m.name)


def bounds():
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in bpy.data.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def stage(res=(2560, 1600), samples=96, sun_deg=(38, 140)):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"           # stylised palettes: keep the authored colours, no filmic wash
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    w = bpy.data.worlds.new("ShowcaseSky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    grad = nt.nodes.new("ShaderNodeTexGradient")            # horizon-to-zenith sky, same for every land
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = .5, (.78, .86, .95, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = .85, (.36, .55, .86, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = .9
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 2.6
    sun.data.color = (1.0, .95, .86)
    sun.data.angle = math.radians(1.2)
    sun.rotation_euler = (math.radians(90 - sun_deg[0]), 0, math.radians(sun_deg[1] + 90))
    sc.collection.objects.link(sun)
    return sc


def camera(view, focus=None, frame=None, lens=40):
    sc = bpy.context.scene
    cam = bpy.data.objects.new("ShowcaseCam", bpy.data.cameras.new("ShowcaseCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens, cam.data.clip_end = lens, 20000
    lo, hi = bounds()
    c = (lo + hi) / 2
    if view == "top":
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = frame[3] if frame else max(hi.x - lo.x, hi.y - lo.y) * 1.08
        cam.location = (frame[0], frame[1], 500) if frame else (c.x, c.y, hi.z + 400)
        cam.rotation_euler = (0, 0, 0)
        return cam
    if view == "hero":
        t = Vector(frame[:3]) if frame else Vector((c.x, c.y, c.z * .3))
        dist = frame[3] if frame else max(hi.x - lo.x, hi.y - lo.y) * 1.35
        d = Vector((math.cos(math.radians(-50)), math.sin(math.radians(-50)), .48)).normalized()
    else:
        t = Vector(focus)
        dist = frame[3] if frame else 46.0
        d = Vector((math.cos(math.radians(-38)), math.sin(math.radians(-38)), .42)).normalized()
    cam.location = t + d * dist
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(out_dir, glbs, tag, view, focus=None, frame=None, res=(2560, 1600), samples=96, name=None, adjust=None):
    """adjust(): optional hook run after the GLBs load and before lighting, e.g. to move a water sheet to a tide state."""
    clean()
    load(glbs)
    if adjust:
        adjust()
    stage(res, samples)
    cam = camera(view, focus, frame)
    os.makedirs(out_dir, exist_ok=True)
    base = name or os.path.splitext(os.path.basename(glbs[0]))[0]
    path = os.path.join(out_dir, "%s.%s.%s.png" % (base, tag, view))
    bpy.context.scene.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    meta = {"label": "Blender render (Cycles CPU, denoised) - NOT an Unreal capture", "tag": tag, "view": view, "file": os.path.basename(path),
            "sha256": sha(path), "bytes": os.path.getsize(path), "seconds": round(time.time() - t0, 1),
            "settings": {"engine": "CYCLES", "samples": samples, "resolution": list(res), "lens_mm": cam.data.lens, "camera_type": cam.data.type,
                         "camera_location": [round(v, 2) for v in cam.location], "camera_rotation": [round(v, 4) for v in cam.rotation_euler],
                         "view_transform": bpy.context.scene.view_settings.view_transform, "sky": "gradient sky (horizon .78/.86/.95 to zenith .36/.55/.86) + warm sun 2.6"},
            "sources": {os.path.basename(g): [os.path.getsize(g), sha(g)] for g in glbs},
            "blender": bpy.app.version_string, "rendered_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(path[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print("SHOWCASE %s %.0fs" % (path, meta["seconds"]), flush=True)
    return meta


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = os.path.abspath(a[0])
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    glbs = []
    if "--glb" in a:
        i = a.index("--glb") + 1
        while i < len(a) and not a[i].startswith("--"):
            glbs.append(os.path.abspath(a[i]))
            i += 1
    res = tuple(int(v) for v in opt("--res", "2560x1600").split("x"))
    fr = opt("--frame")
    render(out, glbs, opt("--tag", "after"), opt("--view", "hero"),
           focus=[float(v) for v in opt("--focus").split(",")] if opt("--focus") else None,
           frame=[float(v) for v in fr.split(",")] if fr else None, res=res, samples=int(opt("--samples", "96")), name=opt("--name"))
