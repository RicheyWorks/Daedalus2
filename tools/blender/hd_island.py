# SPDX-License-Identifier: MIT
"""High-end (smooth-mesh) sky islands for Daedalus2 — Team Claude's next-level Blender pass.

What "next level" means here (learned from Codex's cast/polish tools and Ultra's Lumenwake craft, rebuilt original):
  * terrain is ONE continuous mesh from an authored height function (hills, level terraces, lake basin, stream channel,
    waterfall lip) blended with smoothstep — not voxels — smooth-shaded, vertex-coloured by height/slope/sunlight
    through a Principled BSDF with a VertexColor node;
  * the keel is a strata shell (layered, jagged, ore-vein material slots) closing to a Heartstone cluster;
  * water is the terrain clipped at the water level (so shores are exact), streams are ribbons, the waterfall a
    sheet, and the SKY RIVER a bevelled curve tube arcing from a source islet 40 m up into the lake;
  * everything built from bevelled/smooth primitives with named materials (roughness / metallic / emission) so Unreal
    gets real material slots (lanterns and windows glow);
  * foliage, rocks, flowers and grass are seeded scatters using shared mesh data (instances), kind-aware;
  * each island ships LOD1/LOD2 (decimated terrain), UCX_ collision for every walkable terrace and the deck, and a
    json manifest with chemistry, sockets and metrics; previews rendered headless (Workbench, material colours).

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/hd_island.py -- OUT_DIR SEED [kind] [--render]
Metres, Z up, faces +Y. Pivot = plateau centre at z=0 (deck datum 10 m = Ultra's Lumenwake standard), so an island
drops onto a 256 m Super Island pitch unchanged. `build(seed, kind, out_dir, offset)` is reused by hd_cluster.py.
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import island_chemistry as CH  # noqa: E402

R = 110.0                 # plateau half-width (superellipse)
DECK = 10.0               # Lumenwake deck datum
WATER = 7.25              # lake / stream water level
KINDS = {
    #            grass dark        grass light       cliff             sand             water             accent          tree
    "meadow":  ((.28, .48, .25), (.52, .62, .24), (.30, .32, .30), (.68, .58, .34), (.04, .40, .46), (.93, .41, .25), "round"),
    "volcano": ((.22, .20, .18), (.40, .30, .18), (.16, .13, .13), (.30, .24, .20), (.90, .30, .05), (1.0, .45, .05), "dead"),
    "frost":   ((.84, .90, .94), (.96, .98, 1.0), (.55, .62, .70), (.80, .86, .92), (.45, .70, .90), (.70, .90, 1.0), "pine"),
    "mesa":    ((.70, .50, .30), (.85, .65, .38), (.60, .32, .18), (.86, .72, .48), (.10, .45, .50), (.95, .70, .30), "palm"),
    "mire":    ((.20, .32, .18), (.34, .44, .20), (.25, .25, .20), (.40, .36, .26), (.12, .28, .22), (.60, .90, .40), "mangrove"),
    "crystal": ((.55, .45, .75), (.75, .65, .95), (.40, .35, .55), (.70, .62, .85), (.40, .80, 1.0), (.90, .60, 1.0), "crystal"),
}
MATS = {}


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def seg_dist(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / max(1e-6, dx * dx + dy * dy)))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def material(name, rgb, rough=.8, metal=0.0, emit=0.0, alpha=1.0, vcol=None):
    key = (name, vcol)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new("HD_" + name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*rgb, 1)
        p.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    if vcol:
        n = m.node_tree.nodes.new("ShaderNodeVertexColor")
        n.layer_name = vcol
        m.node_tree.links.new(n.outputs["Color"], p.inputs["Base Color"])
    MATS[key] = m
    return m


# ---- primitives (all return linked objects; `group` collects them for export) --------------------------------
GROUP = []


def mesh(name, verts, faces, mat, smooth_shade=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    if smooth_shade:
        for f in me.polygons:
            f.use_smooth = True
    GROUP.append(ob)
    return ob


def box(name, loc, size, mat, bevel=.12, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = ob.modifiers.new("Crafted edge", "BEVEL")
        mod.width, mod.segments = bevel, 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.data.materials.append(mat)
    GROUP.append(ob)
    return ob


def sphere(name, loc, size, mat, seg=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for f in ob.data.polygons:
        f.use_smooth = True
    ob.data.materials.append(mat)
    GROUP.append(ob)
    return ob


def cone(name, loc, r1, r2, depth, mat, n=12, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=r1, radius2=r2, depth=depth, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    for f in ob.data.polygons:
        f.use_smooth = True
    ob.data.materials.append(mat)
    GROUP.append(ob)
    return ob


def beam(name, a, b, r, mat, n=8):
    a, b = Vector(a), Vector(b)
    ob = cone(name, (a + b) / 2, r, r, (b - a).length, mat, n)
    ob.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return ob


def tube(name, points, radius, mat, res=24):
    """A bevelled bezier curve through `points` (3D), converted to a mesh — the sky river / rope bridges."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution, cu.resolution_u = radius, 4, res
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.object
    ob.data.materials.append(mat)
    for f in ob.data.polygons:
        f.use_smooth = True
    GROUP.append(ob)
    return ob


def instance(name, base, loc, scale=1.0, rot_z=0.0):
    ob = bpy.data.objects.new(name, base.data)
    ob.location = loc
    ob.scale = (scale, scale, scale)
    ob.rotation_euler = (0, 0, rot_z)
    bpy.context.scene.collection.objects.link(ob)
    GROUP.append(ob)
    return ob


# ---- the authored island ---------------------------------------------------------------------------------------
def inside(x, y, r=R):
    return (x / r) ** 4 + (y / r) ** 4 <= 1


def rim_radius(angle, r=R):
    c, s = math.cos(angle), math.sin(angle)
    return r / (abs(c) ** 4 + abs(s) ** 4) ** .25


def author(seed, kind):
    """Deterministic layout: hills, terraces, lake, stream to a waterfall lip, spring, path, buildings."""
    rng = random.Random(seed * 31 + 7)
    lake = (rng.uniform(-30, 10), rng.uniform(-25, 15), rng.uniform(22, 30), rng.uniform(16, 22))
    hills = [(rng.uniform(-70, 70), rng.uniform(30, 75), rng.uniform(28, 40), rng.uniform(16, 26)),
             (rng.uniform(40, 80), rng.uniform(-70, -20), rng.uniform(25, 35), rng.uniform(6, 12)),
             (rng.uniform(-85, -40), rng.uniform(-60, 0), rng.uniform(22, 32), rng.uniform(4, 9))]
    # terraces: landmark on the big hill's shoulder, a town on the flats, a farm, a dock terrace at the rim
    hx, hy, hs, hh = hills[0]
    terraces = [(hx - 14, hy - 12, 15, DECK + hh * .55, "landmark"), (45, -45, 16, DECK + .5, "town"),
                (-55, -45, 14, DECK + .4, "farm"), (rng.choice([-1, 1]) * 95, rng.uniform(-30, 30), 9, DECK, "dock")]
    # the stream leaves the lake toward the far rim and falls off it
    ang = rng.uniform(0, math.tau)
    lip = (rim_radius(ang) * .98 * math.cos(ang), rim_radius(ang) * .98 * math.sin(ang))
    lx, ly = lake[0], lake[1]
    stream = [(lx, ly)]
    for i in range(1, 6):
        t = i / 5
        px, py = lx + (lip[0] - lx) * t, ly + (lip[1] - ly) * t
        n = 9 * math.sin(t * math.pi) * math.sin(seed + t * 7)
        stream.append((px - (lip[1] - ly) / 200 * n, py + (lip[0] - lx) / 200 * n))
    spring = [(hx - 6, hy - 4), (hx - 10, hy - 20), (lx + lake[2] * .6, ly + lake[3] * .7)]
    # path: town -> landmark -> farm -> dock, as a rounded polyline
    path = [terraces[1][:2], (lx + lake[2] + 8, ly), terraces[0][:2], (lx - lake[2] - 8, ly), terraces[2][:2], terraces[3][:2]]
    # source islet for the sky river: off the rim, opposite the waterfall, 40 m up
    ia = ang + math.pi + rng.uniform(-.4, .4)
    islet = (1.55 * R * math.cos(ia), 1.55 * R * math.sin(ia), 40.0, 34.0)
    return {"lake": lake, "hills": hills, "terraces": terraces, "stream": stream, "lip": lip, "spring": spring, "path": path,
            "islet": islet, "ang": ang}


def make_height(A, seed, kind, r=R, base=DECK, islet=False):
    lake = A["lake"]

    def h(x, y):
        z = base + .8 * noise.noise(Vector((x / 23 + seed, y / 23, 0))) + .35 * noise.noise(Vector((x / 7, y / 7 + seed, 1)))
        if islet:
            z += 4 * math.exp(-((x / 14) ** 2 + (y / 14) ** 2))
            pond = math.hypot(x, y) / 7
            z = z * (1 - (1 - smooth((pond - .9) / .3))) + (base - 2.5) * (1 - smooth((pond - .9) / .3))
            return z
        for hx, hy, s, hh in A["hills"]:
            z += hh * math.exp(-(((x - hx) / s) ** 2 + ((y - hy) / (s * .9)) ** 2))
        pond = math.sqrt(((x - lake[0]) / lake[2]) ** 2 + ((y - lake[1]) / lake[3]) ** 2)
        z = z * smooth((pond - 1.15) / .6) + base * (1 - smooth((pond - 1.15) / .6))     # littoral shelf
        for tx, ty, tr, tz, _ in A["terraces"]:
            b = 1 - smooth((math.hypot(x - tx, y - ty) - tr) / 6)
            z = z * (1 - b) + tz * b
        basin = 1 - smooth((pond - .85) / .3)
        d = min(seg_dist(x, y, a, b) for poly in (A["stream"], A["spring"]) for a, b in zip(poly, poly[1:]))
        channel = 1 - smooth((d - 2.0) / 5.0)
        low = max(basin, channel)
        z = z * (1 - low) + (base - 5.6) * low
        # rim: a soft crest so the cliff edge reads, then the waterfall lip notch
        rr = math.hypot(x, y) / rim_radius(math.atan2(y, x), r)
        z += 1.2 * (1 - smooth((abs(rr - .93) - .02) / .05)) * (1 - low)
        return z
    return h


def ground(name, h, kind, r, vcol_name, grid=2.0):
    g, gl, cliff, sand, water, accent, _ = KINDS[kind]
    verts, faces, lookup = [], [], {}
    n = int(r / grid) + 1
    for iy in range(-n, n + 1):
        for ix in range(-n, n + 1):
            x, y = ix * grid, iy * grid
            if inside(x, y, r):
                lookup[ix, iy] = len(verts)
                verts.append((x, y, h(x, y)))
    for ix in range(-n, n):
        for iy in range(-n, n):
            ids = [(ix, iy), (ix + 1, iy), (ix + 1, iy + 1), (ix, iy + 1)]
            if all(p in lookup for p in ids):
                a, b, c, d = (lookup[p] for p in ids)
                faces.extend(((a, b, c), (a, c, d)))
    top = mesh(name, verts, faces, None)
    col = top.data.color_attributes.new(name=vcol_name, type="FLOAT_COLOR", domain="POINT")
    top.data.materials.append(material("Terrain_" + kind, g, .92, vcol=vcol_name))
    for i, (x, y, z) in enumerate(verts):
        # slope from neighbours
        dz = abs(h(x + 1.5, y) - h(x - 1.5, y)) + abs(h(x, y + 1.5) - h(x, y - 1.5))
        rock = smooth((dz - 2.2) / 1.6)
        shore = 1 - smooth((z - (WATER + .1)) / 1.6)
        sun = .35 * smooth((x - 20) / 90) + .15 * smooth((y - 30) / 80) + .15 * noise.noise(Vector((x / 15, y / 15, 2)))
        rgb = [g[k] * (1 - sun) + gl[k] * sun for k in range(3)]
        rgb = [rgb[k] * (1 - shore) + sand[k] * shore for k in range(3)]
        rgb = [rgb[k] * (1 - rock) + cliff[k] * rock for k in range(3)]
        col.data[i].color = (*rgb, 1)
    # rim crest ring to hide the grid's stepped edge
    rv, rf = [], []
    for fac in (.96, 1.0):
        for i in range(96):
            a = i * math.tau / 96
            rr = rim_radius(a, r) * fac
            rv.append((rr * math.cos(a), rr * math.sin(a), h(rr * math.cos(a), rr * math.sin(a)) + .03))
    for i in range(96):
        j = (i + 1) % 96
        rf.append((i, 96 + i, 96 + j, j))
    mesh(name + "_Crest", rv, rf, material("Crest_" + kind, g, .9))
    return top, verts, faces


def strata(name, h, kind, r, seed, chem):
    """The keel: six jagged strata layers down to a point, ore-vein slots from the chemistry, Heartstone at the tip."""
    _, _, cliff, _, _, accent, _ = KINDS[kind]
    rng = random.Random(seed)
    n = 96
    layers = [(1.0, 0), (.985, -5), (.92, -16), (.80, -30), (.62, -44), (.38, -56)]
    verts, faces, slots = [], [], []
    for li, (fac, depth) in enumerate(layers):
        for i in range(n):
            a = i * math.tau / n
            rr = rim_radius(a, r)
            x, y = rr * math.cos(a), rr * math.sin(a)
            z = h(x, y) if li == 0 else depth + 2.5 * math.sin(i * 1.7 + li) + rng.uniform(-1.5, 1.5)
            jag = 1 + (0 if li == 0 else .035 * math.sin(i * 2.3 + li * 1.1))
            verts.append((x * fac * jag, y * fac * jag, z))
    tip = (rng.uniform(-6, 6), rng.uniform(-6, 6), -68)
    verts.append(tip)
    for li in range(len(layers) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((li * n + i, (li + 1) * n + i, (li + 1) * n + j, li * n + j))
            slots.append(0 if li < 2 else (1 if (li + i // 9) % 3 else 2))
    last = (len(layers) - 1) * n
    for i in range(n):
        faces.append((last + i, len(verts) - 1, last + (i + 1) % n))
        slots.append(2)
    sh = mesh(name, verts, faces, material("Strata_" + kind, cliff, .95), smooth_shade=False)
    sh.data.materials.append(material("Strata_light_" + kind, tuple(min(1, c * 1.35) for c in cliff), .9))
    ore = {"iron": (.55, .35, .25), "copper": (.75, .45, .25), "gold": (.95, .78, .25), "silver": (.85, .87, .9),
           "starmetal": (.5, .9, 1.0), "crystal": (.7, .5, 1.0), "coal": (.12, .12, .14)}
    vein = next((k for k in chem.get("geology", {}).get("ores", []) if k in ore), "iron")
    sh.data.materials.append(material("Vein_" + vein, ore[vein], .5, .6 if vein in ("gold", "silver", "copper", "iron") else 0))
    for f, s in zip(sh.data.polygons, slots):
        f.material_index = s
    heart = material("Heartstone", accent, .3, 0, 2.5)
    for i in range(5):
        a = i * math.tau / 5
        c = cone(name + "_Heart%d" % i, (tip[0] + 3 * math.cos(a), tip[1] + 3 * math.sin(a), tip[2] + 8), 1.6, .2, 9, heart, 6)
        c.rotation_euler = (.35 * math.sin(a), .35 * math.cos(a), 0)
    return sh


def water_surface(name, verts, faces, kind, level=WATER):
    wv, wf = [], []
    for face in faces:
        poly = [verts[k] for k in face]
        out = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            ain, bin_ = a[2] <= level, b[2] <= level
            if ain:
                out.append((a[0], a[1], level))
            if ain != bin_:
                t = (level - a[2]) / (b[2] - a[2])
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, level))
        if len(out) >= 3:
            s = len(wv)
            wv.extend(out)
            wf.append(tuple(range(s, len(wv))))
    if wv:
        return mesh(name, wv, wf, material("Water_" + kind, KINDS[kind][4], .15, 0, 0, .85))


def ribbon(name, pts, width, h, mat, lift=.08):
    fitted = []
    for a, b in zip(pts, pts[1:]):
        c = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 1.5))
        fitted.extend((a[0] + (b[0] - a[0]) * i / c, a[1] + (b[1] - a[1]) * i / c) for i in range(c))
    fitted.append(pts[-1])
    verts, faces = [], []
    for i, (x, y) in enumerate(fitted):
        p0, p1 = fitted[max(0, i - 1)], fitted[min(len(fitted) - 1, i + 1)]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = max(.001, math.hypot(dx, dy))
        for side in (-1, 1):
            xx, yy = x - dy / L * width / 2 * side, y + dx / L * width / 2 * side
            verts.append((xx, yy, h(xx, yy) + lift))
        if i:
            faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    return mesh(name, verts, faces, mat)


def waterfall(name, A, h, kind):
    lx, ly = A["lip"]
    ang = A["ang"]
    nx, ny = math.cos(ang), math.sin(ang)
    top = h(lx - nx * 2, ly - ny * 2) + .1
    pts = [(lx - nx * 2 + ny * s, ly - ny * 2 - nx * s, top) for s in (-3, 3)]
    verts = [pts[0], pts[1], (pts[1][0] + nx * 3, pts[1][1] + ny * 3, top - 4), (pts[0][0] + nx * 3, pts[0][1] + ny * 3, top - 4),
             (pts[1][0] + nx * 4, pts[1][1] + ny * 4, top - 30), (pts[0][0] + nx * 4, pts[0][1] + ny * 4, top - 30),
             (pts[1][0] + nx * 3, pts[1][1] + ny * 3, top - 62), (pts[0][0] + nx * 3, pts[0][1] + ny * 3, top - 62)]
    faces = [(0, 1, 2, 3), (3, 2, 4, 5), (5, 4, 6, 7)]
    fall = mesh(name, verts, faces, material("Fall_" + kind, tuple(min(1, c + .35) for c in KINDS[kind][4]), .2, 0, 0, .7))
    mist = material("Mist", (.9, .95, 1.0), .4, 0, .3, .35)
    for i in range(6):
        sphere(name + "_Mist%d" % i, (lx + nx * (4 + i), ly + ny * (4 + i) + math.sin(i) * 2, top - 58 - i * 2), (2.5 + i * .4,) * 3, mist, 10, 6)
    return fall


def sky_river(name, A, h, hi, kind, islet_z):
    """Source pond on the islet -> arc 18 m up over the rim -> the lake. A tube, a thinner foam core and droplets."""
    ix, iy, _, ir = A["islet"]
    lake = A["lake"]
    start = Vector((ix - ir * .35 * math.copysign(1, ix), iy, islet_z + DECK - 2.2 + .6))
    end = Vector((lake[0], lake[1], WATER + .3))
    pts = []
    for i in range(7):
        t = i / 6
        p = start.lerp(end, t)
        p.z += 18 * math.sin(math.pi * t)
        side = Vector((-(end.y - start.y), end.x - start.x, 0)).normalized() * 9 * math.sin(3.2 * math.pi * t) * (1 - t) * t * 4
        pts.append(p + side)
    w = KINDS[kind][4]
    river = tube(name, pts, 2.2, material("SkyWater_" + kind, w, .12, 0, .15, .8))
    tube(name + "_Core", pts, 1.1, material("SkyFoam", (.85, .95, 1.0), .3, 0, .6, .6))
    drop = material("Droplet", tuple(min(1, c + .4) for c in w), .1, 0, .5, .7)
    rng = random.Random(len(name))
    for i in range(22):
        t = rng.random()
        p = start.lerp(end, t)
        p.z += 18 * math.sin(math.pi * t) - rng.uniform(1, 7)
        sphere(name + "_Drop%02d" % i, (p.x + rng.uniform(-4, 4), p.y + rng.uniform(-4, 4), p.z), (rng.uniform(.3, .9),) * 3, drop, 8, 5)
    cloud = material("Cloud", (.97, .97, 1.0), .9, 0, 0, .9)
    apex = pts[3]
    for i in range(7):
        sphere(name + "_Cloud%d" % i, (apex.x + rng.uniform(-14, 14), apex.y + rng.uniform(-10, 10), apex.z + 6 + rng.uniform(-2, 3)),
               (rng.uniform(5, 9), rng.uniform(4, 7), rng.uniform(2.5, 4)), cloud, 12, 6)
    return river


def tree_bases(kind, seed):
    """One shared mesh per species/variant; instances are placed by scatter()."""
    g, gl, cliff, sand, water, accent, shape = KINDS[kind]
    leaf = material("Leaf_" + kind, g, .93)
    leaf2 = material("Leaf2_" + kind, gl, .93)
    bark = material("Bark", (.28, .14, .07), .85)
    bases = []
    for v in range(3):
        parts = []
        if shape == "round":
            parts.append(cone("t", (0, 0, 2.2), .45, .3, 4.4, bark, 8))
            for k in range(3):
                a = k * 2.1
                parts.append(sphere("c", (1.3 * math.cos(a), 1.3 * math.sin(a), 5.2 + v * .4), (2.6, 2.6, 2.2), leaf if k else leaf2, 12, 7))
            parts.append(sphere("c", (0, 0, 6.6), (2.2, 2.2, 2.0), leaf2, 12, 7))
        elif shape == "pine":
            parts.append(cone("t", (0, 0, 3), .35, .15, 6, bark, 8))
            for k in range(4):
                parts.append(cone("c", (0, 0, 3.5 + k * 1.9 + v * .3), 2.6 - k * .55, .25, 2.6, leaf if k % 2 else leaf2, 10))
        elif shape == "palm":
            for k in range(5):
                parts.append(beam("t", (k * .35, 0, k * 1.5), ((k + 1) * .35, 0, (k + 1) * 1.5), .3 - k * .03, bark))
            for k in range(7):
                a = k * math.tau / 7
                fr = cone("f", (1.75 + 2 * math.cos(a), 2 * math.sin(a), 7.7), .9, .05, 4.5, leaf if k % 2 else leaf2, 6)
                fr.rotation_euler = (math.radians(70) * math.sin(a), -math.radians(70) * math.cos(a), 0)
                parts.append(fr)
        elif shape == "dead":
            parts.append(cone("t", (0, 0, 2.5), .4, .2, 5, bark, 7))
            for k in range(4):
                a = k * 1.6 + v
                parts.append(beam("b", (0, 0, 3 + k * .6), (2.5 * math.cos(a), 2.5 * math.sin(a), 5 + k * .8), .12, bark, 6))
        elif shape == "mangrove":
            for k in range(5):
                a = k * math.tau / 5
                parts.append(beam("r", (1.6 * math.cos(a), 1.6 * math.sin(a), 0), (0, 0, 2.5), .14, bark, 6))
            parts.append(cone("t", (0, 0, 3.5), .35, .25, 2.5, bark, 8))
            parts.append(sphere("c", (0, 0, 5.5), (2.8, 2.8, 1.6), leaf, 12, 7))
            parts.append(sphere("c", (.8, .5, 6.3), (1.8, 1.8, 1.2), leaf2, 12, 7))
        else:   # crystal
            cm = material("CrystalTree_" + str(v), (accent[0], accent[1], accent[2]), .2, 0, 1.2, .85)
            for k in range(3 + v):
                a = k * 2.0
                c = cone("x", (.8 * math.cos(a), .8 * math.sin(a), 2.5 + k * .3), .7, .05, 5 + k, cm, 6)
                c.rotation_euler = (.25 * math.sin(a), .25 * math.cos(a), 0)
                parts.append(c)
        bpy.ops.object.select_all(action="DESELECT")
        for p in parts:
            p.select_set(True)
            GROUP.remove(p)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        base = bpy.context.object
        base.name = "Tree_%s_%d" % (shape, v)
        base.location = (0, 0, -500)      # the template lives below the world; only instances show
        bases.append(base)
    return bases


def scatter(prefix, A, h, kind, seed, bases, lake, inner=R):
    rng = random.Random(seed * 13 + 5)
    g, gl, cliff, sand, water, accent, shape = KINDS[kind]
    rock = sphere("Rock_base", (0, 0, -500), (1, 1, .7), material("Rock_" + kind, cliff, .95), 8, 5)
    GROUP.remove(rock)
    flower = sphere("Flower_base", (0, 0, -500), (.25, .25, .2), material("Flower_" + kind, accent, .7), 6, 4)
    GROUP.remove(flower)
    tuft = cone("Tuft_base", (0, 0, -500), .35, .02, .9, material("Tuft_" + kind, gl, .9), 5)
    GROUP.remove(tuft)

    def free(x, y, margin=4):
        if not inside(x, y, inner * .95):
            return False
        pond = math.sqrt(((x - lake[0]) / lake[2]) ** 2 + ((y - lake[1]) / lake[3]) ** 2)
        if pond < 1.25:
            return False
        if min(seg_dist(x, y, a, b) for pl in (A["stream"], A["spring"], A["path"]) for a, b in zip(pl, pl[1:])) < margin:
            return False
        for tx, ty, tr, _, _ in A["terraces"]:
            if math.hypot(x - tx, y - ty) < tr + 2:
                return False
        return True
    n = 0
    tries = 0
    while n < 110 and tries < 3000:
        tries += 1
        x, y = rng.uniform(-inner, inner), rng.uniform(-inner, inner)
        if not free(x, y):
            continue
        slope = abs(h(x + 1.5, y) - h(x - 1.5, y)) + abs(h(x, y + 1.5) - h(x, y - 1.5))
        if slope > 2.0:
            continue
        instance("%s_Tree%03d" % (prefix, n), rng.choice(bases), (x, y, h(x, y) - .2), rng.uniform(.7, 1.35), rng.uniform(0, 6.3))
        n += 1
    for i in range(55):
        x, y = rng.uniform(-inner, inner), rng.uniform(-inner, inner)
        if inside(x, y, inner * .97) and free(x, y, 1):
            s = rng.uniform(.6, 2.6)
            ob = instance("%s_Rock%03d" % (prefix, i), rock, (x, y, h(x, y) - .3 * s), s, rng.uniform(0, 6.3))
            ob.scale = (s, s * rng.uniform(.6, 1.2), s * .7)
    for i in range(16):                         # flower drifts near the water and the path
        cx, cy = rng.uniform(-inner * .8, inner * .8), rng.uniform(-inner * .8, inner * .8)
        if not free(cx, cy, 2):
            continue
        for k in range(14):
            x, y = cx + rng.gauss(0, 3), cy + rng.gauss(0, 3)
            if free(x, y, 1.5):
                instance("%s_Flower%03d_%02d" % (prefix, i, k), flower, (x, y, h(x, y) + .15), rng.uniform(.7, 1.4))
    for i in range(140):
        x, y = rng.uniform(-inner, inner), rng.uniform(-inner, inner)
        if free(x, y, 1):
            instance("%s_Tuft%03d" % (prefix, i), tuft, (x, y, h(x, y) + .3), rng.uniform(.8, 1.6), rng.uniform(0, 6.3))


def buildings(prefix, A, h, kind, chem):
    g, gl, cliff, sand, water, accent, _ = KINDS[kind]
    wall = material("Plaster", (.80, .72, .55), .85)
    wood = material("Cedar", (.30, .14, .07), .7)
    roof = material("Roof_" + kind, tuple(c * .6 for c in accent), .6)
    glow = material("WindowGlow", (1.0, .75, .35), .3, 0, 3.0)
    stone = material("Flagstone", (.62, .56, .46), .9)
    brass = material("Brass", (.72, .50, .15), .35, .8)
    for tx, ty, tr, tz, role in A["terraces"]:
        if role == "landmark":                                    # the lighthouse-shrine: stone drum, brass lantern, beacon
            cone(prefix + "_Shrine_Drum", (tx, ty, tz + 5), 6, 4.5, 10, stone, 16)
            cone(prefix + "_Shrine_Cap", (tx, ty, tz + 11.5), 5.2, 1.2, 3, roof, 16)
            sphere(prefix + "_Shrine_Beacon", (tx, ty, tz + 13.5), (1.6, 1.6, 1.6), glow, 12, 8)
            for i in range(6):
                a = i * math.tau / 6
                box(prefix + "_Shrine_Pillar%d" % i, (tx + 8 * math.cos(a), ty + 8 * math.sin(a), tz + 2.5), (.8, .8, 5), stone, .08)
            sphere(prefix + "_Shrine_Heart", (tx, ty, tz + 1.2), (1.2, 1.2, 1.2), material("Heartstone", accent, .3, 0, 2.5), 10, 6)
        elif role == "town":                                     # three cottages + inn + well + smithy forge
            for i, (dx, dy, w, d) in enumerate(((-8, 6, 7, 5), (7, 7, 6, 5), (-7, -7, 6, 6), (8, -6, 9, 6))):
                z = tz
                box(prefix + "_House%d_Walls" % i, (tx + dx, ty + dy, z + 2), (w, d, 4), wall, .1)
                box(prefix + "_House%d_Roof" % i, (tx + dx, ty + dy, z + 5.2), (w + 1.2, d + 1.2, 2.4), roof, .25, (0, math.radians(0), 0))
                box(prefix + "_House%d_Chimney" % i, (tx + dx + w * .3, ty + dy, z + 6.8), (.9, .9, 2.2), stone, .05)
                box(prefix + "_House%d_Door" % i, (tx + dx, ty + dy - d / 2 - .05, z + 1.1), (1.1, .2, 2.2), wood, .02)
                for sx in (-1, 1):
                    box(prefix + "_House%d_Window%d" % (i, sx + 1), (tx + dx + sx * w * .3, ty + dy - d / 2 - .05, z + 2.4), (1.1, .15, 1.0), glow, .02)
            cone(prefix + "_Well", (tx, ty, tz + .8), 1.6, 1.6, 1.6, stone, 12)
            box(prefix + "_Well_Roof", (tx, ty, tz + 3.2), (3, 3, .4), wood, .05)
            box(prefix + "_Forge", (tx + 1, ty + 12, tz + 1), (3, 2, 2), stone, .08)
            sphere(prefix + "_Forge_Fire", (tx + 1, ty + 12, tz + 2.2), (.7, .7, .5), material("Forge", (1, .4, .05), .4, 0, 4), 8, 5)
            box(prefix + "_Anvil", (tx + 4, ty + 12, tz + .7), (1.4, .6, .5), brass, .05)
            box(prefix + "_PowerUnit_Frame", (tx + 12, ty + 10, tz + 1.5), (2.5, 2.5, 3), brass, .08)   # Codex PowerUnit site
            cone(prefix + "_PowerUnit_Rotor", (tx + 12, ty + 10, tz + 3.4), 2.2, 2.2, .3, material("Steel", (.6, .64, .7), .4, .9), 12)
            sphere(prefix + "_PowerUnit_Crystal", (tx + 12, ty + 10, tz + 1.5), (.8, .8, .8), material("Heartstone", accent, .3, 0, 2.5), 8, 6)
        elif role == "farm":                                     # barn, silo, crop rows (chemistry crops), pen
            box(prefix + "_Barn", (tx - 4, ty + 6, tz + 2.5), (9, 6, 5), material("BarnRed", (.6, .15, .1), .8), .12)
            box(prefix + "_Barn_Roof", (tx - 4, ty + 6, tz + 6), (10, 7, 2), roof, .3)
            cone(prefix + "_Silo", (tx + 6, ty + 7, tz + 4), 2, 2, 8, material("Silo", (.75, .75, .72), .5, .4), 14)
            sphere(prefix + "_Silo_Cap", (tx + 6, ty + 7, tz + 8), (2.1, 2.1, 1.2), roof, 12, 6)
            crops = list(chem.get("soil", {}).get("crops", ["grain"]))[:4] or ["grain"]
            for r_ in range(4):
                cm = material("Crop_" + crops[r_ % len(crops)], ((.5 + .1 * r_) % 1, .7, .25), .9)
                for k in range(9):
                    sphere(prefix + "_Crop%d_%02d" % (r_, k), (tx - 9 + k * 2, ty - 4 - r_ * 2.2, h(tx - 9 + k * 2, ty - 4 - r_ * 2.2) + .4), (.6, .6, .7), cm, 6, 4)
            for k in range(8):
                a = k * math.tau / 8
                box(prefix + "_Fence%d" % k, (tx + 9 + 4 * math.cos(a), ty - 6 + 4 * math.sin(a), tz + .6), (.25, 1.8, 1.2), wood, .02, (0, 0, a))
        elif role == "dock":                                     # planks over the rim, mooring posts, sky-sea boat, lantern
            d = math.atan2(ty, tx)
            nx, ny = math.cos(d), math.sin(d)
            box(prefix + "_Dock_Planks", (tx + nx * 6, ty + ny * 6, tz + .2), (16, 5, .4), wood, .03, (0, 0, d))
            for k in range(3):
                beam(prefix + "_Dock_Post%d" % k, (tx + nx * (k * 6), ty + ny * (k * 6), tz - 6), (tx + nx * (k * 6), ty + ny * (k * 6), tz + 1.4), .3, wood)
            box(prefix + "_Boat_Hull", (tx + nx * 14 + ny * 5, ty + ny * 14 - nx * 5, tz - .2), (7, 2.6, 1.6), wood, .3, (0, 0, d))
            beam(prefix + "_Boat_Mast", (tx + nx * 14 + ny * 5, ty + ny * 14 - nx * 5, tz), (tx + nx * 14 + ny * 5, ty + ny * 14 - nx * 5, tz + 7), .12, wood)
            box(prefix + "_Boat_Sail", (tx + nx * 14 + ny * 5 + nx * 1.3, ty + ny * 14 - nx * 5 + ny * 1.3, tz + 4), (.1, 3.2, 4.5), material("Sail", (.95, .92, .85), .8), .02, (0, 0, d))
            beam(prefix + "_Lantern_Post", (tx, ty, tz), (tx, ty, tz + 4), .15, wood)
            sphere(prefix + "_Lantern", (tx, ty, tz + 4.3), (.5, .5, .6), glow, 8, 6)
    # lantern posts along the path, an arched plank bridge over the stream
    for i, (px, py) in enumerate(A["path"]):
        beam(prefix + "_PathLamp%d" % i, (px + 3, py, h(px + 3, py)), (px + 3, py, h(px + 3, py) + 3.2), .12, wood)
        sphere(prefix + "_PathLamp%d_Glow" % i, (px + 3, py, h(px + 3, py) + 3.5), (.4, .4, .5), glow, 8, 5)
    sx, sy = A["stream"][2]
    box(prefix + "_Bridge", (sx, sy, WATER + 1.2), (9, 2.4, .35), wood, .04)
    for k in (-3.5, 3.5):
        box(prefix + "_Bridge_Rail%d" % int(k), (sx + k, sy, WATER + 1.9), (.15, 2.4, 1.0), wood, .02)


def collision(prefix, A, name_terrain):
    """UCX_ boxes: one per terrace (walkable) + a deck slab under the plateau + the dock planks."""
    hid = material("Collision", (1, 0, 1), 1)
    for i, (tx, ty, tr, tz, role) in enumerate(A["terraces"]):
        ob = box("UCX_%s_%02d" % (name_terrain, i), (tx, ty, tz - 1), (tr * 1.8, tr * 1.8, 2), hid, 0)
        ob.display_type = "WIRE"
    ob = box("UCX_%s_%02d" % (name_terrain, 9), (0, 0, DECK - 3), (R * 1.4, R * 1.4, 2), hid, 0)
    ob.display_type = "WIRE"


def lods(top, name):
    out = []
    for level, ratio in ((1, .35), (2, .12)):
        c = top.copy()
        c.data = top.data.copy()
        c.name = name + "_LOD%d" % level
        bpy.context.scene.collection.objects.link(c)
        bpy.ops.object.select_all(action="DESELECT")
        c.select_set(True)
        bpy.context.view_layer.objects.active = c
        m = c.modifiers.new("LOD", "DECIMATE")
        m.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=m.name)
        c.location.z = -600 - level * 100          # parked below; the json says which is which
        GROUP.append(c)
        out.append({"name": c.name, "ratio": ratio, "triangles": len(c.data.polygons)})
    return out


def build(seed, kind, out_dir, offset=(0, 0, 0), prefix=None, realm="WORLD-ZERO", export=True):
    """Build one HD island at `offset`. Returns the manifest dict. GROUP holds every object made."""
    global GROUP
    GROUP = []
    chem = CH.profile(seed, realm)
    name = prefix or ("HDIsland_%s_%d" % (kind.title(), seed))
    A = author(seed, kind)
    h = make_height(A, seed, kind)
    top, verts, faces = ground(name + "_Terrain", h, kind, R, "HD_terrain")
    strata(name + "_Strata", h, kind, R, seed, chem)
    water_surface(name + "_Lake", verts, faces, kind)
    ribbon(name + "_Path", A["path"], 3.0, h, material("Flagstone", (.62, .56, .46), .9), .1)
    waterfall(name + "_Waterfall", A, h, kind)
    # source islet (smaller plateau, 40 m up) with its own pond, then the sky river
    ix, iy, iz, ir = A["islet"]
    hi = make_height(A, seed + 1, kind, ir, DECK + iz, islet=True)
    itop, iv, ifc = ground(name + "_Islet", hi, kind, ir, "HD_islet", grid=1.5)      # built at the origin, moved below
    strata(name + "_Islet_Strata", hi, kind, ir, seed + 1, chem)
    water_surface(name + "_Islet_Pond", iv, ifc, kind, DECK + iz - 2.2)
    for ob in list(GROUP):
        if ob.name.startswith(name + "_Islet"):
            ob.location.x += ix
            ob.location.y += iy
    sky_river(name + "_SkyRiver", A, h, hi, kind, iz)
    bases = tree_bases(kind, seed)
    scatter(name, A, h, kind, seed, bases, A["lake"])
    buildings(name, A, h, kind, chem)
    collision(name, A, name + "_Terrain")
    lod = lods(top, name + "_Terrain")
    # move the whole island to its cluster offset and pivot so the deck sits at z=0
    for ob in GROUP:
        if ob.name.startswith("Tree_") or ob.name.endswith("_base"):
            continue
        ob.location = (ob.location.x + offset[0], ob.location.y + offset[1], ob.location.z + offset[2] - DECK)
    man = {"name": name, "seed": seed, "kind": kind, "realm": realm, "offset": list(offset), "deck_m": DECK, "water_m": WATER,
           "plateau_half_width_m": R, "sockets": {"E": [R + 10, 0, 0], "N": [0, R + 10, 0], "W": [-R - 10, 0, 0], "S": [0, -R - 10, 0]},
           "terraces": [{"x": t[0], "y": t[1], "r": t[2], "z": t[3] - DECK, "role": t[4]} for t in A["terraces"]],
           "islet": {"x": ix, "y": iy, "z": iz, "r": ir}, "waterfall_lip": list(A["lip"]), "lods": lod,
           "objects": len(GROUP), "triangles": sum(len(o.data.polygons) for o in GROUP if o.type == "MESH"),
           "chemistry": chem, "materials": sorted({m.name for o in GROUP if o.type == "MESH" for m in o.data.materials if m})}
    if export:
        os.makedirs(out_dir, exist_ok=True)
        export_group(os.path.join(out_dir, name), GROUP)
        with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(man, f, indent=1)
    return man


def export_group(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        if o.type == "MESH":
            o.select_set(True)
    bpy.context.view_layer.objects.active = next(o for o in objs if o.type == "MESH")
    bpy.ops.export_scene.fbx(filepath=path + ".fbx", use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z",
                             mesh_smooth_type="FACE", use_mesh_modifiers=True, path_mode="AUTO")
    bpy.ops.export_scene.gltf(filepath=path + ".glb", export_format="GLB", use_selection=True, export_yup=True, export_apply=True)


def render(out_dir, name, views=("hero", "top", "under")):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity, sh.show_specular_highlight = "STUDIO", "MATERIAL", True, True, True
    sh.cavity_type, sh.curvature_ridge_factor, sh.curvature_valley_factor = "BOTH", 1.0, 1.0
    sc.render.resolution_x, sc.render.resolution_y = 1800, 1125
    sc.world = bpy.data.worlds.new("Sky") if sc.world is None else sc.world
    sc.world.use_nodes = False
    sc.world.color = (.62, .74, .90)
    cam = bpy.data.objects.get("Cam") or bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens, cam.data.clip_end = 32, 100000
    for v in views:
        if v == "hero":
            cam.location, target = (330, -290, 150), (0, 0, 5)
        elif v == "top":
            cam.location, target = (0, -60, 420), (0, 0, 0)
        else:
            cam.location, target = (300, -300, -120), (0, 0, -30)
        d = Vector(target) - Vector(cam.location)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out_dir, "%s.%s.png" % (name, v))
        bpy.ops.render.render(write_still=True)
        print("RENDER " + sc.render.filepath, flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out_dir = os.path.abspath(argv[0])
    seed = int(argv[1])
    kind = next((a for a in argv[2:] if a in KINDS), list(KINDS)[seed % len(KINDS)])
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    import time
    t0 = time.time()
    man = build(seed, kind, out_dir)
    print("HDISLAND %s objects=%d tris=%d %.0fs" % (man["name"], man["objects"], man["triangles"], time.time() - t0), flush=True)
    if "--render" in argv:
        render(out_dir, man["name"])
