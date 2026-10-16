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

import bmesh
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
EXTERNAL_WHEEL = False    # a recipe that builds its own stream wheel (kit_waterworks) sets this so gameplay() skips the inline one
LAST = {}                 # build() leaves its layout A, height h, chemistry and gameplay rows here for recipes that add on top


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


def _obj(name, bm, mat, loc=(0, 0, 0), rot=(0, 0, 0), smooth_shade=True):
    """bmesh -> object without bpy.ops (operators re-evaluate the whole scene; this does not)."""
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth_shade:
        me.shade_smooth() if hasattr(me, "shade_smooth") else [setattr(f, "use_smooth", True) for f in me.polygons]
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    GROUP.append(ob)
    return ob


def box(name, loc, size, mat, bevel=.12, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel and min(size) > 2.5 * bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=bevel, segments=2, affect="EDGES", profile=.5)
    return _obj(name, bm, mat, loc, rot, smooth_shade=False)


def sphere(name, loc, size, mat, seg=16, rings=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    # create_uvsphere emits its faces in a different order on every run (Blender 5.2, measured), so every GLB with a
    # sphere hashed differently each build. Sort faces by rounded centroid: same mesh, stable bytes.
    order = {f: k for k, f in enumerate(sorted(bm.faces, key=lambda f: tuple(round(c, 5) for c in f.calc_center_median())))}
    bm.faces.sort(key=lambda f: order[f])                  # bmesh sort keys must be numbers: rank by centroid
    bm.faces.index_update()
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    return _obj(name, bm, mat, loc)


def cone(name, loc, r1, r2, depth, mat, n=12, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r1, radius2=max(r2, 1e-4), depth=depth)
    return _obj(name, bm, mat, loc, rot)


def beam(name, a, b, r, mat, n=8):
    a, b = Vector(a), Vector(b)
    ob = cone(name, (a + b) / 2, r, r, max((b - a).length, 1e-3), mat, n)
    ob.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return ob


def _spline(points, res):
    """Catmull-Rom through the points (the curve passes through every control point, like AUTO bezier handles)."""
    P = [Vector(p) for p in points]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(res):
            t = k / res
            t2, t3 = t * t, t * t * t
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return out


def tube(name, points, radius, mat, res=24, sides=10):
    """A round tube swept along a smooth spline through `points` — sky rivers, streams, ropes, roots. Pure bmesh."""
    pts = _spline(points, max(4, res // 2))
    bm = bmesh.new()
    rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        t = t.normalized() if t.length > 1e-6 else Vector((1, 0, 0))
        side = t.cross(up)
        side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
        nrm = side.cross(t).normalized()
        rings.append([bm.verts.new(p + (side * math.cos(a) + nrm * math.sin(a)) * radius) for a in (k * math.tau / sides for k in range(sides))])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    for ring in (rings[0], rings[-1]):
        bm.faces.new(ring if ring is rings[-1] else list(reversed(ring)))
    return _obj(name, bm, mat)


def join_parts(name, parts):
    """Join parts (each one material) into one multi-material mesh, baking their transforms. No bpy.ops."""
    bm = bmesh.new()
    mats = []
    for o in parts:
        GROUP.remove(o)
        m = o.data.materials[0] if o.data.materials else None
        if m not in mats:
            mats.append(m)
        o.data.transform(o.matrix_basis)
        n0 = len(bm.faces)
        bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f.material_index = mats.index(m)
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def merge_static(name, objs, keep):
    """Join every single-material object (not in `keep`, not instanced) into one mesh per material, baking transforms.
    One island goes from ~860 objects to a few dozen: faster export, fewer draw calls in Unreal."""
    by_mat, gone = {}, []
    users = {}
    for o in objs:
        if o.type == "MESH":
            users[o.data.name] = users.get(o.data.name, 0) + 1
    for o in objs:
        if keep(o) or o.type != "MESH" or users.get(o.data.name, 0) > 1 or len(o.data.materials) != 1 or o.name.startswith(("UCX_", "MKR_")):
            continue
        m = o.data.materials[0]
        o.data.transform(o.matrix_basis)                 # no parents in these scenes, so basis == world
        bm = by_mat.setdefault(m.name, (bmesh.new(), m))[0]
        bm.from_mesh(o.data)
        gone.append(o)
    survivors = [o for o in objs if o not in gone]
    merged = []
    for mname, (bm, m) in by_mat.items():
        me = bpy.data.meshes.new(name + "_" + mname.replace("HD_", ""))
        bm.to_mesh(me)
        bm.free()
        me.materials.append(m)
        ob = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(ob)
        merged.append(ob)
    for o in gone:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return survivors + merged


def instance(name, base, loc, scale=1.0, rot_z=0.0):
    ob = bpy.data.objects.new(name, base.data)
    ob.location = loc
    ob.scale = (scale, scale, scale)
    ob.rotation_euler = (0, 0, rot_z)
    bpy.context.scene.collection.objects.link(ob)
    GROUP.append(ob)
    return ob


# ---- the authored island ---------------------------------------------------------------------------------------
SHAPE = {"p": 4.0, "ax": 1.0, "ay": 1.0, "rot": 0.0, "amp": 0.0, "lobes": 3, "ph": 0.0}


def set_shape(seed, variety=True):
    """Per-seed outline: superellipse exponent (2.3 round .. 6 squarish), stretch, rotation and a lobed wobble.
    Off (the classic rounded square) for cluster plots, which must keep Ultra's 220 m footprint on the 256 m pitch."""
    if not variety:
        SHAPE.update(p=4.0, ax=1.0, ay=1.0, rot=0.0, amp=0.0, lobes=3, ph=0.0)
        return dict(SHAPE)
    rng = random.Random(seed * 7919 + 13)
    st = rng.uniform(.8, 1.25)
    SHAPE.update(p=rng.choice((2.3, 2.8, 3.4, 4.0, 5.0, 6.0)), ax=st, ay=1 / st ** .5 if st > 1 else rng.uniform(.85, 1.15),
                 rot=rng.uniform(0, math.pi), amp=rng.choice((0.0, .04, .07, .1)), lobes=rng.randint(2, 5), ph=rng.uniform(0, math.tau))
    return dict(SHAPE)


def rim_radius(angle, r=None):
    r = R if r is None else r
    a = angle - SHAPE["rot"]
    c, s = math.cos(a) / SHAPE["ax"], math.sin(a) / SHAPE["ay"]
    p = SHAPE["p"]
    return r / (abs(c) ** p + abs(s) ** p) ** (1 / p) * (1 + SHAPE["amp"] * math.sin(SHAPE["lobes"] * angle + SHAPE["ph"]))


def inside(x, y, r=None):
    return math.hypot(x, y) <= rim_radius(math.atan2(y, x), r)


def fit(x, y, margin=.8, r=None):
    """Pull a point toward the centre until it sits inside `margin` of the outline (layouts written for the classic shape)."""
    d = math.hypot(x, y)
    lim = rim_radius(math.atan2(y, x), r) * margin
    if d <= lim or d == 0:
        return x, y
    return x * lim / d, y * lim / d


def author(seed, kind, islet_dir=None):
    """Deterministic layout: hills, terraces, lake, stream to a waterfall lip, spring, path, buildings."""
    rng = random.Random(seed * 31 + 7)
    lake = (rng.uniform(-30, 10), rng.uniform(-25, 15), rng.uniform(22, 30), rng.uniform(16, 22))
    lake = fit(lake[0], lake[1], .45) + lake[2:]
    hills = [(rng.uniform(-70, 70), rng.uniform(30, 75), rng.uniform(28, 40), rng.uniform(16, 26)),
             (rng.uniform(40, 80), rng.uniform(-70, -20), rng.uniform(25, 35), rng.uniform(6, 12)),
             (rng.uniform(-85, -40), rng.uniform(-60, 0), rng.uniform(22, 32), rng.uniform(4, 9))]
    # terraces: landmark on the big hill's shoulder, a town on the flats, a farm, a dock terrace at the rim
    hx, hy, hs, hh = hills[0]
    hx, hy = fit(hx, hy, .62)
    hills[0] = (hx, hy, hs, hh)
    da = (0 if rng.random() < .5 else math.pi) + rng.uniform(-.27, .27)                   # dock sits on the rim
    terraces = [fit(hx - 14, hy - 12, .62) + (15, DECK + hh * .55, "landmark"), fit(45, -45, .62) + (16, DECK + .5, "town"),
                fit(-55, -45, .62) + (14, DECK + .4, "farm"),
                (rim_radius(da) * .86 * math.cos(da), rim_radius(da) * .86 * math.sin(da), 9, DECK, "dock")]
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
    ia = ang + math.pi + rng.uniform(-.4, .4) if islet_dir is None else islet_dir   # clusters point islets outward
    islet = (1.42 * R * math.cos(ia), 1.42 * R * math.sin(ia), 40.0, 22.0)
    return {"lake": lake, "hills": hills, "terraces": terraces, "stream": stream, "lip": lip, "spring": spring, "path": path,
            "islet": islet, "ang": ang}


def make_height(A, seed, kind, r=None, base=DECK, islet=False):
    r = R if r is None else r
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


def ground(name, h, kind, r, vcol_name, grid=2.0, crest=True):
    g, gl, cliff, sand, water, accent, _ = KINDS[kind]
    verts, faces, lookup = [], [], {}
    n = int(r * 1.6 / grid) + 1                        # the outline can stretch up to ~1.5 r along its long axis
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
    if crest:
        mesh(name + "_Crest", rv, rf, material("Crest_" + kind, g, .9))
    return top, verts, faces


def strata(name, h, kind, r, seed, chem):
    """The keel: six jagged strata layers down to a point, ore-vein slots from the chemistry, Heartstone at the tip."""
    _, _, cliff, _, _, accent, _ = KINDS[kind]
    rng = random.Random(seed)
    n = 96
    k = r / R                                                     # the keel's depth scales with the plateau
    layers = [(1.0, 0), (.985, -5 * k), (.92, -16 * k), (.80, -30 * k), (.62, -44 * k), (.38, -56 * k)]
    verts, faces, slots = [], [], []
    for li, (fac, depth) in enumerate(layers):
        for i in range(n):
            a = i * math.tau / n
            rr = rim_radius(a, r)
            x, y = rr * math.cos(a), rr * math.sin(a)
            z = h(x, y) if li == 0 else h(0, 0) - DECK + depth + (2.5 * math.sin(i * 1.7 + li) + rng.uniform(-1.5, 1.5)) * k
            jag = 1 + (0 if li == 0 else .035 * math.sin(i * 2.3 + li * 1.1))
            verts.append((x * fac * jag, y * fac * jag, z))
    tip = (rng.uniform(-6, 6) * k, rng.uniform(-6, 6) * k, -68 * k)
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
        c = cone(name + "_Heart%d" % i, (tip[0] + 3 * k * math.cos(a), tip[1] + 3 * k * math.sin(a), h(0, 0) - DECK + tip[2] + 8 * k), 1.6 * k, .2, 9 * k, heart, 6)
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
    leaf = material("Leaf_" + kind, tuple(c * .8 for c in g), .93)
    leaf2 = material("Leaf2_" + kind, tuple(c * .85 for c in gl), .93)
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
        base = join_parts("Tree_%s_%d" % (shape, v), parts)
        base.location = (0, 0, -500)      # the template lives below the world; only instances show
        bases.append(base)
    return bases


def scatter(prefix, A, h, kind, seed, bases, lake, inner=None):
    inner = R if inner is None else inner
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
        x, y = rng.uniform(-1.5 * inner, 1.5 * inner), rng.uniform(-1.5 * inner, 1.5 * inner)
        if not free(x, y):
            continue
        slope = abs(h(x + 1.5, y) - h(x - 1.5, y)) + abs(h(x, y + 1.5) - h(x, y - 1.5))
        if slope > 2.0:
            continue
        instance("%s_Tree%03d" % (prefix, n), rng.choice(bases), (x, y, h(x, y) - .2), rng.uniform(.7, 1.35), rng.uniform(0, 6.3))
        n += 1
    for i in range(85):
        x, y = rng.uniform(-1.5 * inner, 1.5 * inner), rng.uniform(-1.5 * inner, 1.5 * inner)
        if inside(x, y, inner * .97) and free(x, y, 1):
            s = rng.uniform(.6, 2.6)
            ob = instance("%s_Rock%03d" % (prefix, i), rock, (x, y, h(x, y) - .3 * s), s, rng.uniform(0, 6.3))
            ob.scale = (s, s * rng.uniform(.6, 1.2), s * .7)
    for i in range(24):                         # flower drifts near the water and the path
        cx, cy = rng.uniform(-inner * .8, inner * .8), rng.uniform(-inner * .8, inner * .8)
        if not free(cx, cy, 2):
            continue
        for k in range(14):
            x, y = cx + rng.gauss(0, 3), cy + rng.gauss(0, 3)
            if free(x, y, 1.5):
                instance("%s_Flower%03d_%02d" % (prefix, i, k), flower, (x, y, h(x, y) + .15), rng.uniform(.7, 1.4))
    for i in range(210):
        x, y = rng.uniform(-1.5 * inner, 1.5 * inner), rng.uniform(-1.5 * inner, 1.5 * inner)
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


# ---- v2: what makes each kind its own place --------------------------------------------------------------------
def free_spot(A, h, rng, margin=6, tries=400, inner=None, max_slope=2.5):
    inner = R * .85 if inner is None else inner
    lake = A["lake"]
    for _ in range(tries):
        x, y = rng.uniform(-1.5 * inner, 1.5 * inner), rng.uniform(-1.5 * inner, 1.5 * inner)
        if not inside(x, y, inner):
            continue
        if math.sqrt(((x - lake[0]) / lake[2]) ** 2 + ((y - lake[1]) / lake[3]) ** 2) < 1.3:
            continue
        if min(seg_dist(x, y, a, b) for pl in (A["stream"], A["spring"], A["path"]) for a, b in zip(pl, pl[1:])) < margin:
            continue
        if any(math.hypot(x - t[0], y - t[1]) < t[2] + margin for t in A["terraces"]):
            continue
        if abs(h(x + 2, y) - h(x - 2, y)) + abs(h(x, y + 2) - h(x, y - 2)) > max_slope:
            continue
        return x, y
    return None


def kind_features(prefix, A, h, kind, seed):
    rng = random.Random(seed * 17 + 3)
    g, gl, cliff, sand, water, accent, _ = KINDS[kind]
    wood = material("Cedar", (.30, .14, .07), .7)
    stone = material("Flagstone", (.62, .56, .46), .9)
    hx, hy, hs, hh = A["hills"][0]
    top = h(hx, hy)
    if kind == "volcano":
        lava = material("Lava", (1.0, .35, .04), .4, 0, 6.0)
        obs = material("Obsidian", (.06, .05, .08), .15, .3)
        cone(prefix + "_Volcano_Cone", (hx, hy, top + 9), 26, 9, 18, material("Basalt", (.18, .15, .14), .95), 28)
        cone(prefix + "_Volcano_CraterRim", (hx, hy, top + 18.3), 9.5, 8, 1.2, obs, 28)
        cone(prefix + "_Volcano_Lava", (hx, hy, top + 18.2), 7.6, 7.6, .4, lava, 24)
        for i in range(5):                                   # lava rivulets down the flank
            a = i * math.tau / 5 + rng.uniform(-.3, .3)
            pts = [Vector((hx + (8 + k * 4.5) * math.cos(a + k * .08), hy + (8 + k * 4.5) * math.sin(a + k * .08), top + 18 - k * 4.2)) for k in range(5)]
            tube(prefix + "_Volcano_Flow%d" % i, pts, .8, lava, 12)
        smoke = material("Smoke", (.35, .33, .32), .9, 0, 0, .6)
        for i in range(6):
            sphere(prefix + "_Volcano_Smoke%d" % i, (hx + rng.uniform(-3, 3), hy + rng.uniform(-3, 3), top + 23 + i * 4.5), (3 + i, 3 + i, 2 + i * .6), smoke, 10, 6)
        for i in range(9):
            p = free_spot(A, h, rng, 4)
            if p:
                cone(prefix + "_Obsidian%d" % i, (p[0], p[1], h(*p) + 3), 1.4, .05, 7 + rng.uniform(0, 5), obs, 5, (rng.uniform(-.2, .2), rng.uniform(-.2, .2), 0))
        p = free_spot(A, h, rng, 8)
        if p:                                                # hot spring with steam
            cone(prefix + "_HotSpring", (p[0], p[1], h(*p) + .15), 4.5, 4.5, .3, material("HotSpring", (.35, .85, .85), .1, 0, .5, .85), 20)
            for k in range(4):
                sphere(prefix + "_Steam%d" % k, (p[0] + rng.uniform(-2, 2), p[1] + rng.uniform(-2, 2), h(*p) + 2 + k * 2), (1.6, 1.6, 1.2), material("Steam", (.95, .95, .95), .9, 0, 0, .5), 8, 5)
    elif kind == "frost":
        ice = material("Ice", (.75, .90, 1.0), .05, 0, .2, .75)
        snow = material("Snow", (.97, .98, 1.0), .9)
        for i in range(14):
            p = free_spot(A, h, rng, 3, max_slope=4)
            if p:
                for k in range(rng.randint(2, 4)):
                    cone(prefix + "_IceSpire%d_%d" % (i, k), (p[0] + rng.uniform(-2, 2), p[1] + rng.uniform(-2, 2), h(*p) + 3), rng.uniform(1, 2.2), .05, rng.uniform(5, 12), ice, 6,
                         (rng.uniform(-.25, .25), rng.uniform(-.25, .25), 0))
        cone(prefix + "_FrozenLake", (A["lake"][0], A["lake"][1], WATER + .15), A["lake"][2] * .95, A["lake"][2] * .95, .2, ice, 32).scale = (1, A["lake"][3] / A["lake"][2], 1)
        for i in range(10):
            p = free_spot(A, h, rng, 2)
            if p:
                sphere(prefix + "_Drift%d" % i, (p[0], p[1], h(*p)), (rng.uniform(3, 7), rng.uniform(2, 4), 1.2), snow, 12, 6)
        for i in range(40):                                  # icicles under the rim
            a = i * math.tau / 40
            rr = rim_radius(a) * .97
            x, y = rr * math.cos(a), rr * math.sin(a)
            cone(prefix + "_Icicle%02d" % i, (x, y, h(x, y) - 4), .6, .02, rng.uniform(4, 10), ice, 5, (math.pi, 0, 0))
    elif kind == "mesa":
        bands = [material("Butte%d" % k, c, .95) for k, c in enumerate(((.72, .42, .22), (.85, .62, .38), (.60, .30, .18)))]
        for i in range(4):
            p = free_spot(A, h, rng, 10)
            if p:
                w, z = rng.uniform(9, 16), h(*p)
                for k in range(5):
                    box(prefix + "_Butte%d_%d" % (i, k), (p[0], p[1], z + 1.6 + k * 3.2), (w - k * .9, w * .8 - k * .7, 3.2), bands[k % 3], .5)
        cact = material("Cactus", (.25, .50, .25), .8)
        for i in range(18):
            p = free_spot(A, h, rng, 2)
            if p:
                z = h(*p)
                hgt = rng.uniform(3, 6)
                cone(prefix + "_Cactus%d" % i, (p[0], p[1], z + hgt / 2), .45, .4, hgt, cact, 10)
                for sgn in (-1, 1):
                    if rng.random() < .7:
                        beam(prefix + "_CactusArm%d_%d" % (i, sgn), (p[0], p[1], z + hgt * .5), (p[0] + sgn * 1.3, p[1], z + hgt * .55), .3, cact)
                        beam(prefix + "_CactusArmUp%d_%d" % (i, sgn), (p[0] + sgn * 1.3, p[1], z + hgt * .55), (p[0] + sgn * 1.3, p[1], z + hgt * .85), .3, cact)
        p = free_spot(A, h, rng, 8)
        if p:                                                # vineyard rows
            vine = material("Vine", (.35, .45, .18), .85)
            grape = material("Grape", (.45, .15, .45), .5)
            for r_ in range(6):
                for k in range(8):
                    x, y = p[0] - 7 + k * 2, p[1] - 5 + r_ * 2
                    sphere(prefix + "_Vine%d_%d" % (r_, k), (x, y, h(x, y) + 1), (.9, .5, .9), vine, 6, 4)
                    if k % 2:
                        sphere(prefix + "_Grape%d_%d" % (r_, k), (x, y - .5, h(x, y) + .7), (.3, .3, .4), grape, 6, 4)
    elif kind == "mire":
        lily = material("Lily", (.25, .55, .25), .7)
        bloom = material("LilyBloom", (.98, .80, .90), .6)
        lx, ly, la, lb = A["lake"]
        for i in range(30):
            a, r_ = rng.uniform(0, math.tau), math.sqrt(rng.random()) * .85
            x, y = lx + la * r_ * math.cos(a), ly + lb * r_ * math.sin(a)
            cone(prefix + "_LilyPad%02d" % i, (x, y, WATER + .06), rng.uniform(.6, 1.3), rng.uniform(.6, 1.3), .08, lily, 10)
            if i % 4 == 0:
                sphere(prefix + "_LilyBloom%02d" % i, (x, y, WATER + .35), (.35, .35, .3), bloom, 8, 5)
        # boardwalk across the lake on posts
        pts = [(lx - la * 1.1, ly), (lx, ly + lb * .2), (lx + la * 1.1, ly)]
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 1.4)
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            for j in range(n):
                t = j / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                box(prefix + "_Boardwalk%d_%02d" % (k, j), (x, y, WATER + .7), (1.2, 3.0, .18), wood, .02, (0, 0, ang))
                if j % 3 == 0:
                    beam(prefix + "_BoardPost%d_%02d" % (k, j), (x, y, WATER - 2), (x, y, WATER + .6), .12, wood)
        reed = material("Cattail", (.45, .40, .20), .9)
        for i in range(60):
            a = rng.uniform(0, math.tau)
            x, y = lx + la * 1.05 * math.cos(a), ly + lb * 1.05 * math.sin(a)
            beam(prefix + "_Reed%02d" % i, (x, y, WATER - .3), (x + rng.uniform(-.3, .3), y + rng.uniform(-.3, .3), WATER + rng.uniform(1.5, 2.8)), .06, reed, 5)
        glow = material("Glowshroom", (.45, 1.0, .75), .4, 0, 3.0)
        for i in range(14):
            p = free_spot(A, h, rng, 2)
            if p:
                for k in range(3):
                    x, y = p[0] + rng.uniform(-1, 1), p[1] + rng.uniform(-1, 1)
                    beam(prefix + "_ShroomStem%d_%d" % (i, k), (x, y, h(x, y)), (x, y, h(x, y) + .8), .1, material("Stem", (.9, .9, .8), .8), 6)
                    sphere(prefix + "_ShroomCap%d_%d" % (i, k), (x, y, h(x, y) + .9), (.45, .45, .25), glow, 8, 5)
    elif kind == "crystal":
        for i in range(10):
            p = free_spot(A, h, rng, 5, max_slope=4)
            if not p:
                continue
            col = [(.75, .55, 1.0), (.45, .85, 1.0), (1.0, .55, .85)][i % 3]
            cm = material("Crystal%d" % (i % 3), col, .08, 0, 1.6, .8)
            z = h(*p)
            for k in range(rng.randint(3, 7)):
                a = rng.uniform(0, math.tau)
                cone(prefix + "_Crystal%d_%d" % (i, k), (p[0] + 1.2 * math.cos(a), p[1] + 1.2 * math.sin(a), z + 3), rng.uniform(1, 2.2), .1, rng.uniform(5, 14), cm, 6,
                     (.35 * math.sin(a), .35 * math.cos(a), 0))
        shard = material("Shard", accent, .1, 0, 2.0, .7)
        for i in range(16):                                  # shards floating above the plateau
            a, r_ = rng.uniform(0, math.tau), rng.uniform(20, 95)
            cone(prefix + "_FloatShard%02d" % i, (r_ * math.cos(a), r_ * math.sin(a), DECK + rng.uniform(25, 55)), rng.uniform(.8, 2), .05, rng.uniform(3, 7), shard, 5,
                 (rng.uniform(0, 3), rng.uniform(0, 3), 0))
    else:   # meadow: windmill on the big hill's shoulder + beehives + standing stones
        p = free_spot(A, h, rng, 8)
        if p:
            z = h(*p)
            cone(prefix + "_Windmill_Tower", (p[0], p[1], z + 6), 3.2, 2.2, 12, material("Plaster", (.80, .72, .55), .85), 12)
            cone(prefix + "_Windmill_Cap", (p[0], p[1], z + 13), 2.6, .3, 3, material("Roof_meadow", (.56, .25, .15), .6), 12)
            hub = Vector((p[0], p[1] - 2.6, z + 11))
            for k in range(4):
                a = k * math.pi / 2 + .3
                tip = hub + Vector((7 * math.cos(a), 0, 7 * math.sin(a)))
                beam(prefix + "_Windmill_Arm%d" % k, hub, tip, .15, wood)
                mid = hub.lerp(tip, .6)
                box(prefix + "_Windmill_Sail%d" % k, mid, (1.8, .08, 4.2), material("Sail", (.95, .92, .85), .8), .02, (0, -a + math.pi / 2, 0))
        hive = material("Hive", (.92, .78, .35), .7)
        for i in range(5):
            p = free_spot(A, h, rng, 3)
            if p:
                for k in range(3):
                    cone(prefix + "_Hive%d_%d" % (i, k), (p[0], p[1], h(*p) + .4 + k * .7), .9 - k * .15, .8 - k * .15, .7, hive, 12)
        p = free_spot(A, h, rng, 10)
        if p:
            for k in range(9):
                a = k * math.tau / 9
                x, y = p[0] + 8 * math.cos(a), p[1] + 8 * math.sin(a)
                box(prefix + "_StandingStone%d" % k, (x, y, h(x, y) + 2), (1.2, .8, 4 + rng.uniform(0, 1.5)), material("Rock_meadow", cliff, .95), .3,
                    (rng.uniform(-.08, .08), rng.uniform(-.08, .08), a))


def rim_details(prefix, h, kind, seed, r=None):
    r = R if r is None else r
    """Hanging roots/vines under the crest and small rocks drifting around the keel — sells the floating."""
    rng = random.Random(seed * 23 + 11)
    g, gl, cliff, _, _, _, _ = KINDS[kind]
    root = material("Root_" + kind, tuple(c * .7 for c in g) if kind not in ("frost", "volcano", "crystal") else (.25, .18, .12), .9)
    for i in range(48):
        a = i * math.tau / 48 + rng.uniform(-.05, .05)
        rr = rim_radius(a, r) * .99
        x, y = rr * math.cos(a), rr * math.sin(a)
        z = h(x, y) - 1
        L = rng.uniform(4, 14)
        pts = [Vector((x, y, z)), Vector((x * 1.01, y * 1.01, z - L * .4)), Vector((x * 1.005 + rng.uniform(-1, 1), y * 1.005 + rng.uniform(-1, 1), z - L))]
        tube(prefix + "_Root%02d" % i, pts, rng.uniform(.12, .3), root, 6)
    rock = material("Strata_" + kind, cliff, .95)
    for i in range(14):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(1.05, 1.35) * r
        s = rng.uniform(2, 6)
        ob = sphere(prefix + "_Drift%02d" % i, (d * math.cos(a), d * math.sin(a), rng.uniform(-30, 0)), (s, s * .8, s * .7), rock, 8, 5)
        cone(prefix + "_DriftKeel%02d" % i, (d * math.cos(a), d * math.sin(a), ob.location.z - s * .9), s * .7, .1, s * 1.6, rock, 7, (math.pi, 0, 0))


# ---- v2: gameplay — every placed piece comes from the chemistry or a mechanics data file ----------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _data(rel):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


ESSENCE_RGB = {"warm": (.95, .45, .20), "cool": (.35, .65, .95), "calm": (.55, .80, .55), "quick": (.95, .85, .30),
               "iron": (.55, .45, .40), "bright": (1.0, .95, .55)}
ORE_RGB = {"coal": (.12, .12, .14), "copper": (.78, .45, .22), "iron": (.60, .40, .32), "gold": (.95, .78, .25), "silver": (.86, .88, .92),
           "tin": (.80, .82, .84), "starmetal": (.50, .90, 1.0), "crystal": (.75, .55, 1.0), "emberite": (1.0, .55, .15), "obsidian": (.08, .06, .10)}
FRUIT_RGB = {"cherry": (.80, .10, .15), "orange": (1.0, .55, .10), "plum": (.45, .15, .45), "apple": (.85, .15, .12), "pear": (.80, .85, .30),
             "peach": (1.0, .65, .45), "lemon": (1.0, .92, .25), "fig": (.45, .25, .35), "date": (.55, .35, .15)}


def marker(GP, prefix, kind, ident, x, y, z, source, extra=None, post=True):
    """A named, exported gameplay hook: a small signpost mesh `MKR_<kind>_<id>` plus a manifest row citing its source."""
    if post:
        beam("MKR_%s_%s_%s" % (prefix, kind, ident), (x, y, z), (x, y, z + 2.2), .08, material("MarkerPost", (.95, .85, .30), .6, 0, .6), 6)
    row = {"kind": kind, "id": ident, "local": [round(x, 2), round(y, 2), round(z - DECK, 2)], "source": source}
    if extra:
        row.update(extra)
    GP.append(row)


def gameplay(prefix, A, h, kind, seed, chem):
    rng = random.Random(seed * 41 + 9)
    GP = []
    npcs = {n.get("id"): n for n in _data("data/npcs/npcs.json").get("npcs", [])}
    terr = {t[4]: t for t in A["terraces"]}
    wood = material("Cedar", (.30, .14, .07), .7)
    # spawn overlook (data/spawn/spawn.json: marker_spawn_overlook on the player's own island)
    lx, ly, lr, lz, _ = terr["landmark"]
    marker(GP, prefix, "spawn", "marker_spawn_overlook", lx + lr * .7, ly - lr * .3, lz, "data/spawn/spawn.json first_spawn")
    # NPC homes (data/npcs/npcs.json)
    tx, ty, tr, tz, _ = terr["town"]
    fx, fy, fr, fz, _ = terr["farm"]
    dx, dy, dr, dz, _ = terr["dock"]
    homes = {"npc_ark_keeper": (dx, dy, dz), "npc_trader": (tx - 10, ty - 10, tz), "npc_forge_smith": (tx + 3, ty + 14, tz),
             "npc_beast_tender": (fx + 9, fy - 2, fz), "npc_drydock_riveter": (dx - 4, dy + 4, dz), "npc_crater_scholar": (lx - 6, ly + 6, lz)}
    for nid, (x, y, z) in homes.items():
        if nid in npcs or not npcs:
            marker(GP, prefix, "npc", nid, x, y, z, "data/npcs/npcs.json", {"role": npcs.get(nid, {}).get("role")})
    # ark deck + latch (data/ark/travel.json: latch range 60 m, tows up to 3 islands)
    ark = _data("data/ark/travel.json")
    marker(GP, prefix, "ark", "ark_deck", dx, dy, dz, "data/ark/travel.json", {"latch_range_m": ark.get("latch", {}).get("range_m", 60)})
    # water sources (data/water/water.json) + the chemistry's spring purity / filter
    wsrc = [w.get("id") for w in _data("data/water/water.json").get("sources", [])]
    water = chem.get("water", {})
    marker(GP, prefix, "water", "well", tx, ty, tz, "data/water/water.json sources.well", post=False)
    sx, sy = A["spring"][0]
    marker(GP, prefix, "water", "spring", sx, sy, h(sx, sy), "data/water/water.json sources.spring + chemistry water.spring_purity",
           {"purity": water.get("spring_purity"), "filter_needed": water.get("filter_needed")})
    marker(GP, prefix, "water", "lake", A["lake"][0], A["lake"][1], WATER, "data/water/water.json sources.sea/lake", post=False)
    cone(prefix + "_RainCatch", (tx - 12, ty + 4, tz + 1), 1.1, 1.3, 2, wood, 12)
    marker(GP, prefix, "water", "rain_catch", tx - 12, ty + 4, tz, "data/water/water.json sources.rain_catch", post=False)
    if water.get("filter_needed"):
        box(prefix + "_FilterHut", (sx + 6, sy - 4, h(sx + 6, sy - 4) + 1.5), (3, 3, 3), wood, .1)
        marker(GP, prefix, "water", "filter_hut", sx + 6, sy - 4, h(sx + 6, sy - 4), "chemistry water.filter_needed + data/water/water.json purification")
    # fishing pier on the lake (chemistry water.fish)
    lkx, lky, la, lb = A["lake"]
    px, py = lkx + la * 1.05, lky
    for k in range(5):
        box(prefix + "_FishingPier%d" % k, (px - k * 1.6, py, WATER + .6), (1.6, 2.6, .2), wood, .02)
    beam(prefix + "_FishingPier_Rod", (px - 6.5, py, WATER + .8), (px - 9, py + 1.5, WATER + 3.5), .04, wood, 5)
    marker(GP, prefix, "fishing", "pier", px - 6, py, WATER + .6, "chemistry water.fish (Colony Ledger fishing)", {"fish": water.get("fish")})
    # herbs (chemistry flora.herbs + essences; data/herbs/herbs.json; RingInfusion brews)
    flora = chem.get("flora", {})
    herbs = flora.get("herbs", [])
    ess = flora.get("herb_essences", {})
    hc = (lx - lr - 10, ly)
    for i, hb in enumerate(herbs):
        a = i * math.tau / max(1, len(herbs))
        x, y = hc[0] + 6 * math.cos(a), hc[1] + 6 * math.sin(a)
        mat = material("Herb_" + hb, ESSENCE_RGB.get(ess.get(hb, ""), (.6, .8, .4)), .8, 0, .4)
        for k in range(7):
            xx, yy = x + rng.gauss(0, .9), y + rng.gauss(0, .9)
            cone(prefix + "_Herb_%s_%d" % (hb, k), (xx, yy, h(xx, yy) + .35), .25, .02, .8, mat, 5)
        marker(GP, prefix, "herb", hb, x, y, h(x, y), "chemistry flora.herbs + data/herbs/herbs.json + docs/mechanics/RingInfusion.md",
               {"essence": ess.get(hb)}, post=False)
    cone(prefix + "_BrewTrough", (hc[0], hc[1], h(*hc) + .5), 1.4, 1.2, 1, wood, 12)
    marker(GP, prefix, "craft", "brew_trough", hc[0], hc[1], h(*hc), "docs/mechanics/RingInfusion.md (brews)")
    # orchard (chemistry flora.orchard: fruit + uses)
    bark = material("Bark", (.28, .14, .07), .85)
    for i, (sp, info) in enumerate(sorted(flora.get("orchard", {}).items())):
        for k in range(4):
            x, y = fx - 14 + k * 5, fy + 14 + i * 6
            z = h(x, y)
            cone(prefix + "_Orchard_%s_%d_Trunk" % (sp, k), (x, y, z + 1.4), .3, .22, 2.8, bark, 8)
            sphere(prefix + "_Orchard_%s_%d_Crown" % (sp, k), (x, y, z + 3.6), (1.8, 1.8, 1.5), material("Leaf_orchard", (.22, .45, .20), .9), 10, 6)
            fruit = material("Fruit_" + info.get("fruit", sp), FRUIT_RGB.get(info.get("fruit", sp), (.9, .3, .2)), .5)
            for m in range(5):
                a = m * 1.3
                sphere(prefix + "_Orchard_%s_%d_Fruit%d" % (sp, k, m), (x + 1.5 * math.cos(a), y + 1.5 * math.sin(a), z + 3.2 + .4 * math.sin(m)), (.22, .22, .22), fruit, 6, 4)
        marker(GP, prefix, "orchard", sp, fx - 14, fy + 14 + i * 6, h(fx - 14, fy + 14 + i * 6), "chemistry flora.orchard", {"fruit": info.get("fruit"), "uses": info.get("uses")}, post=False)
    # livestock (chemistry fauna.livestock; data/livestock/animals.json housing/care)
    hide = material("Hide", (.85, .80, .72), .9)
    for i, (an, product) in enumerate(sorted(chem.get("fauna", {}).get("livestock", {}).items())):
        for k in range(3):
            x, y = fx + 8 + rng.uniform(-2.5, 2.5), fy - 6 + rng.uniform(-2.5, 2.5)
            z = h(x, y)
            box(prefix + "_Livestock_%s_%d_Body" % (an, k), (x, y, z + .9), (1.6 if an != "hen" else .6, .8 if an != "hen" else .5, .8 if an != "hen" else .5), hide, .15)
            box(prefix + "_Livestock_%s_%d_Head" % (an, k), (x + .9, y, z + 1.3), (.5, .45, .45), hide, .1)
        marker(GP, prefix, "livestock", an, fx + 8, fy - 6, fz, "chemistry fauna.livestock + data/livestock/animals.json", {"product": product}, post=False)
    # crops are placed by buildings() from chemistry soil.crops; record them
    soil = chem.get("soil", {})
    marker(GP, prefix, "crops", "+".join(soil.get("crops", [])), fx - 5, fy - 7, fz, "chemistry soil.crops / crop_rows / fertility (Ultra island_farm.py)",
           {"fertility": soil.get("fertility"), "rows": soil.get("crop_rows")}, post=False)
    # ore nodes (data/spawn/ore_nodes.json 40/km2, seeded by island seed; chemistry ores_here + geology.ore_mult)
    geo = chem.get("geology", {})
    ores = chem.get("ores_here", [])
    area_km2 = (2 * R) ** 2 * .88 / 1e6
    n_nodes = max(6, int(round(40 * area_km2 * geo.get("ore_mult", 1.0) * 4)))      # x4: the keel's faces count too
    for i in range(n_nodes):
        ore = ores[i % len(ores)] if ores else "iron"
        if ore == "starmetal" and not geo.get("starmetal_crater"):
            ore = "iron"
        spot = free_spot(A, h, rng, 3, max_slope=6)
        if not spot:
            continue
        x, y = spot
        z = h(x, y)
        rock = sphere(prefix + "_OreNode_%s_%02d" % (ore.title(), i), (x, y, z + .5), (1.4, 1.1, 1.0), material("Strata_" + kind, KINDS[kind][2], .95), 8, 5)
        for m in range(3):
            a = m * 2.1
            cone(prefix + "_OreNode_%s_%02d_Vein%d" % (ore.title(), i, m), (x + .9 * math.cos(a), y + .9 * math.sin(a), z + 1.1), .35, .05, .9,
                 material("Ore_" + ore, ORE_RGB.get(ore, (.6, .5, .4)), .4, .7 if ore in ("gold", "copper", "iron", "silver") else 0, 1.2 if ore in ("starmetal", "crystal") else 0), 5)
        marker(GP, prefix, "ore_node", "Prop_OreNode_%s_Small" % ore.title(), x, y, z, "data/spawn/ore_nodes.json + chemistry ores_here/geology.ore_mult", post=False)
    # caves (chemistry geology.caves) — mouths in the big hill's flank
    hx, hy, hs, hh = A["hills"][0]
    dark = material("CaveDark", (.02, .02, .03), 1)
    for i in range(int(geo.get("caves", 0))):
        a = i * 2.4 + 1
        x, y = hx + hs * .55 * math.cos(a), hy + hs * .55 * math.sin(a)
        sphere(prefix + "_CaveMouth%d" % i, (x, y, h(x, y) + 1), (2.4, 1.2, 2.0), dark, 12, 6)
        box(prefix + "_CaveLintel%d" % i, (x, y, h(x, y) + 3.2), (4.5, 1.5, .8), material("Strata_" + kind, KINDS[kind][2], .95), .3, (0, 0, a))
        marker(GP, prefix, "cave", "cave_%d" % i, x, y, h(x, y), "chemistry geology.caves (ADR-049 dig, ADR-050 geology)", post=False)
    # meteor crater with starmetal (chemistry geology.starmetal_crater / LEGENDARY grade)
    if geo.get("starmetal_crater"):
        spot = free_spot(A, h, rng, 10)
        if spot:
            x, y = spot
            z = h(x, y)
            cone(prefix + "_Crater_Rim", (x, y, z + .6), 9, 7, 1.4, material("Scorch", (.18, .14, .12), .95), 24)
            cone(prefix + "_Crater_Bowl", (x, y, z - .2), 7, 3, 1.2, material("Scorch", (.18, .14, .12), .95), 24, (math.pi, 0, 0))
            for k in range(5):
                cone(prefix + "_Starmetal%d" % k, (x + rng.uniform(-3, 3), y + rng.uniform(-3, 3), z + 1), .8, .05, 2.6, material("Ore_starmetal", ORE_RGB["starmetal"], .3, .6, 2.0), 5)
            marker(GP, prefix, "crater", "starmetal_crater", x, y, z, "chemistry geology.starmetal_crater (LEGENDARY) + Colony Ledger meteor event")
    # Power Unit (chemistry power_unit: parts + drive) — sited by its drive
    pu = chem.get("power_unit", {})
    drive = str(pu.get("drive", "the stream"))
    if "stream" in drive:
        x, y = A["stream"][3]
    elif "wind" in drive:
        x, y = hx + hs * .3, hy - hs * .3
    else:
        x, y = tx + 12, ty + 10
    marker(GP, prefix, "power_unit", "PowerUnit", x, y, h(x, y), "chemistry power_unit (Codex PowerUnit 86100 parts)",
           {"drive": drive, "parts": list(pu.get("parts", {}).keys()), "energy_per_unit": pu.get("energy_per_unit")})
    if "stream" in drive and not EXTERNAL_WHEEL:
        wheel = material("Steel", (.6, .64, .7), .4, .9)
        cone(prefix + "_PowerUnit_WaterWheel", (x, y, WATER + 1.6), 2.6, 2.6, .8, wheel, 16, (math.pi / 2, 0, 0))
        box(prefix + "_PowerUnit_Housing", (x + 3.5, y, h(x + 3.5, y) + 1.4), (2.6, 2.2, 2.8), material("Brass", (.72, .50, .15), .35, .8), .1)
    # shop + inn (chemistry economy.shop_stock / inn_menu) on the town terrace
    eco = chem.get("economy", {})
    crate = material("Crate", (.55, .38, .20), .8)
    for i, item in enumerate(eco.get("shop_stock", [])[:8]):
        box(prefix + "_ShopCrate_%s" % item, (tx - 12 + (i % 4) * 1.5, ty - 12 - (i // 4) * 1.5, tz + .5), (1.2, 1.2, 1.0), crate, .05)
    marker(GP, prefix, "shop", "trader_stall", tx - 12, ty - 12, tz, "chemistry economy.shop_stock + data/trade/prices.json", {"stock": eco.get("shop_stock")})
    marker(GP, prefix, "inn", "inn", tx + 8, ty - 6, tz, "chemistry economy.inn_menu + data/food/cooking.json", {"menu": eco.get("inn_menu")})
    # Colony Ledger production roles (tools/economy/colony_ledger.py): goods this island exports / imports
    GP.append({"kind": "ledger", "id": "goods", "goods": eco.get("goods"), "surplus": eco.get("surplus"), "need": eco.get("need"),
               "source": "chemistry economy + tools/economy/colony_ledger.py (produce / market_day)"})
    # Living Island Defense (Ultra, docs/mechanics/LIVING-ISLAND-DEFENSE.md): watch post on the approach, guard beds
    ang = A["ang"] + math.pi
    rr = rim_radius(ang) * .85
    wx, wy = rr * math.cos(ang), rr * math.sin(ang)
    box(prefix + "_WatchTower", (wx, wy, h(wx, wy) + 4), (2.5, 2.5, 8), wood, .1)
    box(prefix + "_WatchTower_Deck", (wx, wy, h(wx, wy) + 8.3), (4, 4, .4), wood, .05)
    marker(GP, prefix, "defense", "watch_post", wx, wy, h(wx, wy), "Ultra LIVING-ISLAND-DEFENSE.md (warning phase) + colony_ledger zombie_wave/settle_wave")
    trap = material("Trap", (.35, .70, .30), .7)
    for k in range(4):
        x, y = wx * .9 + rng.uniform(-6, 6), wy * .9 + rng.uniform(-6, 6)
        cone(prefix + "_GuardBed%d" % k, (x, y, h(x, y) + .6), 1, 1.2, 1.2, trap, 8)
        marker(GP, prefix, "defense", "guard_bed_%d" % k, x, y, h(x, y), "voxel_creatures carnivorous plants as defenders (LIVING-ISLAND-DEFENSE)", post=False)
    # egg nests (voxel_eggs hatching minigame, PORT06)
    nest = material("Nest", (.55, .42, .25), .95)
    for k in range(3):
        spot = free_spot(A, h, rng, 2)
        if spot:
            x, y = spot
            cone(prefix + "_Nest%d" % k, (x, y, h(x, y) + .2), 1.0, .7, .4, nest, 10)
            marker(GP, prefix, "egg_nest", "nest_%d" % k, x, y, h(x, y), "tools/blender/voxel_eggs.py (Prop_Egg_* hatch pools, PORT06)", post=False)
    # quests that reach markers on this island (data/quests/quests.json)
    for q in _data("data/quests/quests.json").get("quests", []):
        for st in q.get("steps", []):
            tgt = st.get("target") or st.get("npc")
            if tgt and any(r["id"] == tgt for r in GP):
                GP.append({"kind": "quest_step", "id": q.get("id"), "target": tgt, "source": "data/quests/quests.json"})
    return GP


def collision(prefix, A, name_terrain):
    """UCX_ boxes: one per terrace (walkable) + a deck slab under the plateau + the dock planks."""
    hid = material("Collision", (1, 0, 1), 1)
    for i, (tx, ty, tr, tz, role) in enumerate(A["terraces"]):
        ob = box("UCX_%s_%02d" % (name_terrain, i), (tx, ty, tz - 1.02), (tr * 1.8, tr * 1.8, 2), hid, 0)
        ob.display_type, ob.hide_render = "WIRE", True
    ob = box("UCX_%s_%02d" % (name_terrain, 9), (0, 0, DECK - 8), (R * 1.4, R * 1.4, 4), hid, 0)   # safety floor under the lake bed
    ob.display_type, ob.hide_render = "WIRE", True


def lods(top, name, h, kind):
    """LOD1/LOD2 = the same height function sampled on 4 m / 8 m grids (no decimation operator needed)."""
    out = []
    for level, grid in ((1, 4.0), (2, 8.0)):
        c, _, _ = ground(name + "_LOD%d" % level, h, kind, R, "HD_terrain", grid=grid, crest=False)
        c.location.z = -600 - level * 100          # parked below; the json says which is which
        out.append({"name": c.name, "grid_m": grid, "triangles": len(c.data.polygons)})
    return out


def build(seed, kind, out_dir, offset=(0, 0, 0), prefix=None, realm="WORLD-ZERO", export=True, islet_dir=None, variety=None):
    """Build one HD island at `offset`. Returns the manifest dict. GROUP holds every object made."""
    global GROUP
    GROUP = []
    chem = CH.profile(seed, realm)
    name = prefix or ("HDIsland_%s_%d" % (kind.title(), seed))
    shape = set_shape(seed, prefix is None if variety is None else variety)   # cluster plots keep the classic outline
    A = author(seed, kind, islet_dir)
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
    kind_features(name, A, h, kind, seed)
    GP = gameplay(name, A, h, kind, seed, chem)
    LAST.clear()
    LAST.update(A=A, h=h, chem=chem, GP=GP, name=name)
    rim_details(name, h, kind, seed)
    collision(name, A, name + "_Terrain")
    lod = lods(top, name + "_Terrain", h, kind)
    # move the whole island to its cluster offset and pivot so the deck sits at z=0
    for ob in GROUP:
        if ob.name.startswith("Tree_") or ob.name.endswith("_base"):
            continue
        ob.location = (ob.location.x + offset[0], ob.location.y + offset[1], ob.location.z + offset[2] - DECK)
    KEEP = ("_Terrain", "_Crest", "_Strata", "_Lake", "_Waterfall", "_SkyRiver", "_Path", "_Islet", "_Pond", "_LOD")
    GROUP = merge_static(name, GROUP, lambda o: any(t in o.name for t in KEEP))
    globals()["GROUP"] = GROUP
    man = {"name": name, "seed": seed, "kind": kind, "realm": realm, "offset": list(offset), "deck_m": DECK, "water_m": WATER,
           "plateau_half_width_m": R, "outline": shape, "sockets": {"E": [R + 10, 0, 0], "N": [0, R + 10, 0], "W": [-R - 10, 0, 0], "S": [0, -R - 10, 0]},
           "terraces": [{"x": t[0], "y": t[1], "r": t[2], "z": t[3] - DECK, "role": t[4]} for t in A["terraces"]],
           "islet": {"x": ix, "y": iy, "z": iz, "r": ir}, "waterfall_lip": list(A["lip"]), "lods": lod,
           "objects": len(GROUP), "triangles": sum(len(o.data.polygons) for o in GROUP if o.type == "MESH"),
           "gameplay": [dict(r, world=[r["local"][0] + offset[0], r["local"][1] + offset[1], r["local"][2] + offset[2]]) if "local" in r else r for r in GP],
           "mechanics_sources": sorted({r["source"] for r in GP}),
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
    for o in objs:
        if o.type == "MESH" and o.data.color_attributes:
            ca = o.data.color_attributes
            ca.active_color = ca[0]
            if hasattr(ca, "render_color_index"):
                ca.render_color_index = 0                # Blender 5.x writes COLOR_0 from the RENDER colour, not the active one
    try:                                            # Blender 4.2+: write COLOR_0 from the active colour attribute
        try:
            bpy.ops.export_scene.gltf(filepath=path + ".glb", export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
                                      export_vertex_color="ACTIVE", export_all_vertex_colors=False)
        except TypeError:
            bpy.ops.export_scene.gltf(filepath=path + ".glb", export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
                                      export_vertex_color="ACTIVE")
    except TypeError:
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
