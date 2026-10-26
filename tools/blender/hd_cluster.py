# SPDX-License-Identifier: MIT
"""Eight connected HD islands = one "Octet" Super Island (Ultra's standard: distinct plots on a 256 m pitch, sockets
at ±(R+10) m, 10 m deck datum, bridges 16 m wide at the deck). Ten themed octets, one per seed:

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/hd_cluster.py -- OUT_DIR SEED [--plot I | --links] [--render]
  --plot I : build + export only plot I (0 = hub) in this process — run 8 fresh processes, so the scene never fills up
             (one process for all 8 slowed from 17 s to 65 s per plot as objects accumulated);
  --links  : build bridges, sky streams and theme props, write the layout json; with --render, import the 8 plot GLBs
             and render the whole octet.
  (neither): all of it in one process (slow; fine for a single preview).

Layout: a hub island at the centre and seven around it on a 295 m ring (ring neighbours exactly 256 m apart), so every island
touches the hub and its two ring neighbours — 14 rope-plank bridges, and the hub's sky river feeds a ring canal:
each ring island's lake spills a sky stream to the next island clockwise (7 sky streams), so water flows around the
whole octet through the air. Theme = kinds per plot + accent palette + props (seasons / holidays). Output: one GLB +
FBX per island (pivot at its own deck centre, offset in the json) plus `<name>_Bridges` and `<name>_Canal` meshes
and a layout json with sockets, so Codex can place plots individually or the whole octet.
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hd_island as H  # noqa: E402

PITCH = 256.0                                   # neighbour-to-neighbour (Ultra's Super Island pitch)
RING = PITCH / (2 * math.sin(math.pi / 7))      # 295 m: ring radius that puts ring neighbours exactly one pitch apart
THEMES = [
    # name, hub kind, ring kinds (7), accent, prop
    ("Spring",     "meadow",  ["meadow", "meadow", "mire", "meadow", "crystal", "meadow", "mesa"],    (.93, .55, .75), "blossom"),
    ("Summer",     "mesa",    ["meadow", "mesa", "mesa", "meadow", "mire", "mesa", "meadow"],         (1.0, .80, .20), "sunflower"),
    ("Harvest",    "meadow",  ["meadow", "mesa", "meadow", "meadow", "mire", "meadow", "mesa"],       (.95, .50, .10), "pumpkin"),
    ("Winter",     "frost",   ["frost", "frost", "frost", "crystal", "frost", "frost", "frost"],      (.75, .90, 1.0), "snowman"),
    ("Easter",     "meadow",  ["meadow", "meadow", "meadow", "mire", "meadow", "crystal", "meadow"],  (.85, .70, .95), "egg"),
    ("Halloween",  "mire",    ["mire", "volcano", "mire", "mire", "crystal", "mire", "volcano"],      (1.0, .45, .05), "jack"),
    ("Christmas",  "frost",   ["frost", "frost", "meadow", "frost", "crystal", "frost", "frost"],     (.85, .10, .15), "gift"),
    ("Valentine",  "meadow",  ["meadow", "crystal", "meadow", "meadow", "mire", "meadow", "crystal"], (1.0, .35, .55), "heart"),
    ("Midsummer",  "crystal", ["meadow", "crystal", "meadow", "mire", "crystal", "meadow", "crystal"], (.55, 1.0, .80), "aurora"),
    ("NewYear",    "volcano", ["volcano", "mesa", "crystal", "volcano", "mesa", "crystal", "volcano"], (1.0, .85, .30), "firework"),
]


def layout():
    pts = [(0.0, 0.0)]
    for i in range(7):
        a = i * math.tau / 7 + math.pi / 14
        pts.append((RING * math.cos(a), RING * math.sin(a)))
    edges = [(0, i) for i in range(1, 8)] + [(i, 1 + i % 7) for i in range(1, 8)]
    return pts, edges


def islet_angle(i, pts):
    """Ring islets point away from the hub; the hub's islet sits in the gap between two ring plots."""
    if i == 0:
        return math.pi / 14 + math.pi / 7
    return math.atan2(pts[i][1], pts[i][0])


def bridge(name, a, b, mat_wood, mat_rope):
    """A sagging rope-and-plank bridge between two deck sockets (z = 0 at both ends)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    n = max(8, int(L / 4))
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t)
        p.z = -6.0 * math.sin(math.pi * t)                      # catenary-ish sag
        pts.append(p)
    H.tube(name + "_Deck", pts, 1.2, mat_wood, 16)
    side = Vector((-d.y, d.x, 0)).normalized() * 7.5
    for s, sgn in (("L", 1), ("R", -1)):
        rail = [p + side * sgn + Vector((0, 0, 1.4)) for p in pts]
        H.tube(name + "_Rope" + s, rail, .18, mat_rope, 12)
        for i in range(0, n + 1, 3):
            H.beam(name + "_Post%s%02d" % (s, i), pts[i] + side * sgn, pts[i] + side * sgn + Vector((0, 0, 1.6)), .14, mat_wood)
    for i in range(0, n + 1, 2):                                 # cross planks
        H.box(name + "_Plank%02d" % i, pts[i], (1.0, 16.0, .25), mat_wood, .02, (0, 0, math.atan2(d.y, d.x)))
    for p, q in ((a, b), (b, a)):                                # gate posts + lanterns at each socket
        off = (q - p).normalized() * 2
        for sgn in (1, -1):
            H.beam(name + "_Gate%d" % sgn, p + off + side * sgn, p + off + side * sgn + Vector((0, 0, 4.5)), .3, mat_wood)
            H.sphere(name + "_GateLamp%d" % sgn, p + off + side * sgn + Vector((0, 0, 4.9)), (.5, .5, .6), H.material("WindowGlow", (1.0, .75, .35), .3, 0, 3.0), 8, 6)


def canal(name, centres, lakes, kind):
    """Ring sky-streams: each ring island's lake spills to the next island's lake through the air."""
    w = H.KINDS[kind][4]
    mat = H.material("SkyWater_" + kind, w, .12, 0, .15, .8)
    foam = H.material("SkyFoam", (.85, .95, 1.0), .3, 0, .6, .6)
    for i in range(1, 8):
        j = 1 + i % 7
        a = Vector((centres[i][0] + lakes[i][0], centres[i][1] + lakes[i][1], H.WATER - H.DECK + .3))
        b = Vector((centres[j][0] + lakes[j][0], centres[j][1] + lakes[j][1], H.WATER - H.DECK + .3))
        pts = []
        for k in range(7):
            t = k / 6
            p = a.lerp(b, t)
            p.z += 26 * math.sin(math.pi * t)
            side = Vector((-(b.y - a.y), b.x - a.x, 0)).normalized() * 12 * math.sin(2 * math.pi * t) * t * (1 - t) * 4
            pts.append(p + side)
        H.tube("%s_Stream%d" % (name, i), pts, 1.8, mat)
        H.tube("%s_Stream%d_Core" % (name, i), pts, .9, foam)


def theme_props(name, prop, accent, centres, seed):
    """One signature piece per island, seasonal."""
    acc = H.material("Accent_" + prop, accent, .5, 0, 1.0 if prop in ("jack", "aurora", "firework") else 0)
    green = H.material("Leaf_meadow", (.28, .48, .25), .93)
    snow = H.material("Snow", (.97, .98, 1.0), .9)
    for i, (cx, cy) in enumerate(centres):
        px, py, pz = cx + 20, cy - 30, 0.6
        pre = "%s_P%d_" % (name, i)
        if prop == "pumpkin" or prop == "jack":
            for k in range(5):
                H.sphere(pre + "Pumpkin%d" % k, (px + k * 3, py + (k % 2) * 2, pz + .9), (1.3, 1.3, 1.0), acc, 10, 6)
                H.cone(pre + "Stem%d" % k, (px + k * 3, py + (k % 2) * 2, pz + 2.1), .2, .1, .6, green, 6)
        elif prop == "snowman":
            for k, (r, z) in enumerate(((1.6, 1.6), (1.2, 4.0), (.9, 5.9))):
                H.sphere(pre + "Snow%d" % k, (px, py, pz + z), (r, r, r), snow, 12, 8)
            H.cone(pre + "Carrot", (px, py - 1.0, pz + 6.0), .15, .02, 1.2, H.material("Carrot", (1, .45, .1), .7), 6, (math.radians(90), 0, 0))
        elif prop == "egg":
            for k in range(9):
                em = H.material("Egg_%d" % (k % 4), ((.9 + k * .02) % 1, (.6 + k * .09) % 1, (.8 + k * .05) % 1), .5)
                H.sphere(pre + "Egg%d" % k, (px + (k % 3) * 2.5, py + (k // 3) * 2.5, pz + 1.0), (.8, .8, 1.1), em, 10, 6)
        elif prop == "gift":
            for k in range(6):
                H.box(pre + "Gift%d" % k, (px + (k % 3) * 3, py + (k // 3) * 3, pz + .9), (1.8, 1.8, 1.8), acc if k % 2 else H.material("GiftGreen", (.1, .5, .2), .6), .1)
            H.cone(pre + "Tree", (px + 10, py, pz + 5), 4, .2, 10, H.material("Leaf_frost", (.84, .90, .94), .93) if False else green, 10)
            H.sphere(pre + "Star", (px + 10, py, pz + 10.6), (.7, .7, .7), H.material("Star", (1, .9, .3), .3, 0, 3), 8, 5)
        elif prop == "heart":
            for k in range(3):
                H.sphere(pre + "HeartL%d" % k, (px - 1.2, py + k * 5, pz + 3), (1.4, 1.0, 1.4), acc, 10, 6)
                H.sphere(pre + "HeartR%d" % k, (px + 1.2, py + k * 5, pz + 3), (1.4, 1.0, 1.4), acc, 10, 6)
                H.cone(pre + "HeartTip%d" % k, (px, py + k * 5, pz + 1.3), 1.9, .05, 2.6, acc, 8, (math.radians(180), 0, 0))
        elif prop == "aurora":
            pts = [Vector((px - 60 + k * 30, py + 20 * math.sin(k), 60 + 10 * math.sin(k * 1.3 + seed))) for k in range(6)]
            H.tube(pre + "Aurora", pts, 3.5, H.material("Aurora", accent, .3, 0, 2.0, .45), 24)
        elif prop == "firework":
            for k in range(3):
                H.beam(pre + "Rocket%d" % k, (px + k * 6, py, pz), (px + k * 6, py, pz + 14 + k * 3), .25, acc)
                for m in range(8):
                    a = m * math.tau / 8
                    H.beam(pre + "Burst%d_%d" % (k, m), (px + k * 6, py, pz + 14 + k * 3), (px + k * 6 + 6 * math.cos(a), py + 6 * math.sin(a), pz + 14 + k * 3 + 4 * math.sin(a * 2)), .12, acc)
        elif prop in ("blossom", "sunflower"):
            for k in range(7):
                H.beam(pre + "Stem%d" % k, (px + k * 2.2, py, pz), (px + k * 2.2, py, pz + 2.5), .08, green)
                H.sphere(pre + "Head%d" % k, (px + k * 2.2, py, pz + 2.8), (.8, .3, .8), acc, 8, 5)


def theme(seed):
    tname, hub, ring, accent, prop = THEMES[(seed - 1) % len(THEMES)]
    return "Octet_%s_%d" % (tname, seed), tname, [hub] + ring, accent, prop


def build_plot(seed, i, out_dir):
    name, _, kinds, _, _ = theme(seed)
    pts, _ = layout()
    t0 = time.time()
    man = H.build(seed * 100 + i, kinds[i], out_dir, offset=(pts[i][0], pts[i][1], 0), prefix="%s_Plot%d_%s" % (name, i, kinds[i].title()), islet_dir=islet_angle(i, pts))
    print("PLOT %d %s %s tris=%d %.0fs" % (i, kinds[i], man["name"], man["triangles"], time.time() - t0), flush=True)
    return man


def build(seed, out_dir, export=True, plots=True):
    name, tname, kinds, accent, prop = theme(seed)
    hub = kinds[0]
    pts, edges = layout()
    mans, lakes = [], []
    t0 = time.time()
    for i, ((cx, cy), kind) in enumerate(zip(pts, kinds)):
        if plots:
            man = H.build(seed * 100 + i, kind, out_dir, offset=(cx, cy, 0), prefix="%s_Plot%d_%s" % (name, i, kind.title()), export=export, islet_dir=islet_angle(i, pts))
            print("PLOT %d %s %s %.0fs" % (i, kind, man["name"], time.time() - t0), flush=True)
        else:
            jp = os.path.join(out_dir, "%s_Plot%d_%s.json" % (name, i, kind.title()))
            man = json.load(open(jp, encoding="utf-8")) if os.path.exists(jp) else {"name": os.path.basename(jp)[:-5], "kind": kind, "seed": seed * 100 + i, "sockets": {}, "triangles": 0}
        mans.append(man)
        lakes.append(H.author(seed * 100 + i, kind)["lake"][:2])
    H.GROUP = []
    wood = H.material("Cedar", (.30, .14, .07), .7)
    rope = H.material("Rope", (.62, .52, .35), .9)
    for a, b in edges:
        pa, pb = Vector((*pts[a], 0)), Vector((*pts[b], 0))
        d = (pb - pa).normalized() * (H.R + 10)
        bridge("%s_Bridge_%d_%d" % (name, a, b), pa + d, pb - d, wood, rope)
    bridges = list(H.GROUP)
    H.GROUP = []
    canal(name + "_Canal", pts, lakes, hub)
    theme_props(name, prop, accent, pts, seed)
    extras = list(H.GROUP)
    lay = {"name": name, "theme": tname, "seed": seed, "pitch_m": PITCH, "standard": "Lumenwake Super Island (Ultra): 256 m pitch, sockets ±(R+10), deck 10 m",
           "plots": [{"index": i, "name": m["name"], "kind": m["kind"], "centre": list(pts[i]), "seed": m["seed"], "sockets": m["sockets"]} for i, m in enumerate(mans)],
           "bridges": [{"from": a, "to": b} for a, b in edges], "sky_streams": [{"from": i, "to": 1 + i % 7} for i in range(1, 8)],
           "prop": prop, "accent": accent, "triangles": sum(m["triangles"] for m in mans)}
    if export:
        H.export_group(os.path.join(out_dir, name + "_Bridges"), bridges)
        H.export_group(os.path.join(out_dir, name + "_Canal"), extras)
        with open(os.path.join(out_dir, name + ".layout.json"), "w", encoding="utf-8") as f:
            json.dump(lay, f, indent=1)
    print("OCTET %s plots=8 tris=%d %.0fs" % (name, lay["triangles"], time.time() - t0), flush=True)
    return name, lay


def import_plots(out_dir, name):
    import glob
    for g in sorted(glob.glob(os.path.join(out_dir, name + "_Plot*.glb"))):
        bpy.ops.import_scene.gltf(filepath=g)
    for o in bpy.data.objects:                         # the parked LODs and tree templates stay out of the picture
        if o.name.startswith("UCX_") or "_LOD" in o.name or o.location.z < -400:
            o.hide_render = True
    # Workbench MATERIAL view reads diffuse_color, which glTF import leaves white: copy Base Color back, and for the
    # vertex-coloured terrain use the mean of its colour attribute (the asset itself keeps the per-vertex colours)
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        for m in o.data.materials:
            if not m or not m.use_nodes:
                continue
            p = m.node_tree.nodes.get("Principled BSDF")
            if not p:
                continue
            bc = p.inputs["Base Color"]
            if bc.is_linked and o.data.color_attributes:
                ca = o.data.color_attributes[0]
                n = max(1, len(ca.data))
                acc = [0.0, 0.0, 0.0]
                for k in range(0, len(ca.data), max(1, n // 400)):
                    c = ca.data[k].color
                    acc = [acc[j] + c[j] for j in range(3)]
                cnt = len(range(0, len(ca.data), max(1, n // 400)))
                m.diffuse_color = (acc[0] / cnt, acc[1] / cnt, acc[2] / cnt, 1)
            elif not bc.is_linked:
                m.diffuse_color = tuple(bc.default_value)


def render(out_dir, name):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "MATERIAL", True, True
    sc.render.resolution_x, sc.render.resolution_y = 2000, 1250
    sc.world = bpy.data.worlds.new("Sky") if sc.world is None else sc.world
    sc.world.use_nodes = False
    sc.world.color = (.62, .74, .90)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens, cam.data.clip_end = 30, 100000
    for v, loc, tgt in (("hero", (900, -820, 420), (0, 0, -20)), ("top", (0, -120, 1150), (0, 0, 0))):
        d = Vector(tgt) - Vector(loc)
        cam.location = loc
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out_dir, "%s.%s.png" % (name, v))
        bpy.ops.render.render(write_still=True)
        print("RENDER " + sc.render.filepath, flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out_dir = os.path.abspath(argv[0])
    seed = int(argv[1])
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    os.makedirs(out_dir, exist_ok=True)
    if "--plot" in argv:
        build_plot(seed, int(argv[argv.index("--plot") + 1]), out_dir)
    else:
        links = "--links" in argv
        name, lay = build(seed, out_dir, export=True, plots=not links)
        if "--render" in argv:
            if links:
                import_plots(out_dir, name)
            render(out_dir, name)
