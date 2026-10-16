# SPDX-License-Identifier: MIT
"""The Ocean Tide-Pen shelf: the art for data/ocean/tidepen.json and the ocean-tidepen-landing dock.

Revisions (each reproducible, earlier ones immutable):
  r1  the shelf, the pen, care station, landing; residents spread over the pools; every pool a 0.55 m basin.
  r2  the pen pool follows the habitat proposal data/ocean/habitat-tidepool-r1.json: shallow flats, a covered refuge
      under a rock overhang and a deep basin, at the proposed depths (measured on the final rock mesh, build fails if
      they drift); the pen water is its own role, PenWater, at the NORMAL level, so a host or a render can move it to
      the low/high states; all four residents live in the pen in their normal-state zones.
  r3  geometry as r2; the pen water is clear (alpha .32, lighter teal) so the bed, plants and residents read from
      above. r2's murky sheet (alpha .7) hid everything under it.

What the player sees, sailing down from World-Zero's rim dock:
  * A rock shelf of tide pools beside the Ocean pier.
  * One pool ringed by a low dry-stone wall: the PEN. Its wooden gate stays shut until settled_care holds
    (TidePenGate). A teal keeper lantern marks the gate.
  * A care station: a feeding trough and a drying rack of sea plants. Feeding is how care is earned.
  * The open sea edge where any creature may be left wild.
  * A landing walk with mooring posts for the sky-sea boat.

The residents and their habitat plants are READ from data/ocean/tidepen.json, not copied. Each resident is the voxel
body from voxel_creatures (sea_turtle, seahorse, crab, starfish), and each plant is the voxel_aquatic sea prop for
its species at stage 4. Every plant a resident needs is placed around it. The ledger rows carry status
design/data; nothing here is bound in a host or in Unreal.

    python tidepen_shelf.py OUT_DIR [--rev r1|r2]   (bpy module)  |  blender -b --python tidepen_shelf.py -- OUT_DIR [--rev r2]

Units are metres, Z up, sea level z = 0 (OceanTerrain.SEA_LEVEL). The shelf's own origin sits at the tide-pen
landing anchor. links.json gives that anchor in Ocean blocks, Y up: [24, 1, 24]. In Z-up metres that is
(24, -24, 1) from the pier; the manifest records the conversion. Roles pivot at their anchor, as in reedwheel_haven.
"""
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time

import bpy
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hd_island as H  # noqa: E402
import kit_waterworks as K  # noqa: E402
import voxel_aquatic as AQ  # noqa: E402
import voxel_creatures as VC  # noqa: E402
import voxel_island as VI  # noqa: E402

REV = "r3"                 # build(..., rev=) switches; r1 and r2 stay reproducible
PEN_WATER = {"r2": ((.18, .55, .60), .7), "r3": ((.32, .72, .74), .32)}   # pen sheet colour, alpha per revision
NAME = "TidePen_" + REV
LAND_ID = "ocean-tidepen-" + REV
HABITAT = "data/ocean/habitat-tidepool-r2.json"   # r2 of the proposal: residents have a body size
PEN_SURFACE = -.08         # the pen water at the NORMAL state (r1's pool sheet height)
ZONE_XY = {"shallow": (3.6, .4, 2.0), "deep": (-.6, -.3, 2.4), "refuge": (-4.4, 1.3, 1.5)}   # x, y, radius in the pen pool
DEPTH_TOL = .25            # measured zone depth may differ from the proposal by at most this
OVERHANG_CLEAR = .25       # no resident may touch the refuge overhang
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEED = 2410
CLEARANCE_M = 1.0          # resident to wall: no creature mesh may clip into the pen wall
RESIDENT_SCALE = 2.5       # r1: residents read at shelf scale (stylised: a 25 cm voxel); r2 uses the habitat's display voxel


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def data(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


# ---- the shelf: a rock bench stepping into the sea, with tide pools cut into it -------------------------------
POOLS = [  # x, y, rx, ry  (the first is the PEN pool)
    (0.0, 0.0, 6.5, 4.5), (-11.0, 4.0, 3.4, 2.6), (9.0, 6.5, 3.0, 2.2), (-6.0, -8.0, 2.8, 2.0), (11.5, -6.0, 2.4, 1.8)]
SHELF = (20.0, 14.0)       # half extents (x, y); the sea side is -y


ZONE_DEPTH = {}             # filled from HABITAT in r2
VOXEL_CM = []              # r2: the habitat's display voxel size


def pen_floor(x, y):
    """r2 pen bed: the zones' proposed depths below PEN_SURFACE, blended by Gaussian weight around each zone centre."""
    ws = [(math.exp(-(math.hypot(x - zx, y - zy) / r) ** 2), ZONE_DEPTH[z]) for z, (zx, zy, r) in ZONE_XY.items()]
    t = sum(w for w, _ in ws) or 1e-9
    return PEN_SURFACE - sum(w * d for w, d in ws) / t


def height(x, y):
    """Shelf top ~ +0.9 m, rough, falling below the sea toward -y; each pool a basin down to -0.55 m (r2: the pen
    pool's bed follows the habitat zones)."""
    n = .18 * mathutils.noise.noise(mathutils.Vector((x / 3.1, y / 3.1, SEED))) + .08 * mathutils.noise.noise(mathutils.Vector((x, y, 1)))
    edge = H.smooth((y + SHELF[1] * .55) / (SHELF[1] * .5))       # 0 at the sea edge -> 1 on the bench
    z = -1.6 * (1 - edge) + .9 * edge + n
    for i, (px, py, rx, ry) in enumerate(POOLS):
        d = math.sqrt(((x - px) / rx) ** 2 + ((y - py) / ry) ** 2)
        bed = pen_floor(x - px, y - py) if (i == 0 and ZONE_DEPTH) else -.55
        z = min(z, z * H.smooth((d - .75) / .35) + bed * (1 - H.smooth((d - .75) / .35)))
    rim = max(abs(x) / SHELF[0], abs(y) / SHELF[1])
    return z - 2.5 * H.smooth((rim - .9) / .1)                     # crumble into the sea at the outer edge


def shelf_mesh(name):
    verts, faces, cols, idx = [], [], [], {}
    g = .5 if REV == "r1" else .35                                     # r2: finer, so the zone depths hold on the mesh
    nx, ny = int(SHELF[0] / g), int(SHELF[1] / g)
    rock, wet, weed = (.42, .40, .38), (.25, .26, .27), (.22, .32, .18)
    for j in range(-ny, ny + 1):
        for i in range(-nx, nx + 1):
            x, y = i * g, j * g
            z = height(x, y)
            idx[i, j] = len(verts)
            verts.append((x, y, z))
            t = H.smooth((z + .3) / .9)
            c = tuple(wet[k] * (1 - t) + rock[k] * t for k in range(3))
            if -.2 < z < .25:                                           # the wet band where weed grows
                c = tuple(c[k] * .5 + weed[k] * .5 for k in range(3))
            cols.append(c)
    for j in range(-ny, ny):
        for i in range(-nx, nx):
            faces.append((idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for k, c in enumerate(cols):
        attr.data[k].color = (*c, 1)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(H.material("ShelfRock", (1, 1, 1), .9, vcol="Col"))
    for f in me.polygons:
        f.use_smooth = True
    H.GROUP.append(ob)
    return ob


def water(name, z, rx, ry, cx=0.0, cy=0.0, mat=None, n=40):
    """A flat elliptical water sheet (pools) or the sea disc."""
    verts = [(cx, cy, z)] + [(cx + rx * math.cos(a), cy + ry * math.sin(a), z) for a in (k / n * math.tau for k in range(n))]
    faces = [(0, k + 1, (k + 1) % n + 1) for k in range(n)]
    return H.mesh(name, verts, faces, mat or H.material("SeaWater", (.10, .42, .52), .05, 0, 0, .78), smooth_shade=False)


def sea_outside_pen(name, g=1.0):
    """r2: the sea sheet at z=0 with the pen basin cut out, so the pen shows its OWN water level (r1's sea disc ran
    under the whole shelf and filled the pen to sea level whatever its own sheet did)."""
    pcx, pcy, prx, pry = POOLS[0]
    verts, faces, idx = [], [], {}
    x0, x1, y0, y1 = -60, 60, -54, 34
    for j in range(int((y1 - y0) / g) + 1):
        for i in range(int((x1 - x0) / g) + 1):
            idx[i, j] = len(verts)
            verts.append((x0 + i * g, y0 + j * g, 0.0))
    for j in range(int((y1 - y0) / g)):
        for i in range(int((x1 - x0) / g)):
            cx, cy = x0 + (i + .5) * g, y0 + (j + .5) * g
            if ((cx - pcx) / (prx + .9)) ** 2 + ((cy - pcy) / (pry + .9)) ** 2 < 1:
                continue                                           # inside the pen wall: the pen's own water
            if height(cx, cy) > .6:
                continue                                           # dry bench: no sheet under the rock
            faces.append((idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]))
    return H.mesh(name, verts, faces, H.material("SeaWater", (.10, .42, .52), .05, 0, 0, .78), smooth_shade=False)


def voxel_obj(name, voxels, cm, loc, rot_z=0.0):
    ob = VI._mesh_from_voxels(name, voxels, scale=cm / 100.0, pal=AQ.PAL)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    H.GROUP.append(ob)
    return ob


def creature(species, loc, rot_z=0.0):
    vox = [v for part in VC.plan(species).values() for v in part]
    mx = (min(v[0] for v in vox) + max(v[0] for v in vox)) / 2
    my = (min(v[1] for v in vox) + max(v[1] for v in vox)) / 2
    vox = [(round(x - mx), round(y - my), z, c) for x, y, z, c in vox]      # pivot at the body's centre, feet at z=0
    return voxel_obj("%s_Resident_%s" % (NAME, species), vox, VOXEL_CM[0] if VOXEL_CM else 10.0 * RESIDENT_SCALE, loc, rot_z)


def plant(species, loc, stage=4, rot_z=0.0):
    nm = "Prop_Aquatic_Sea_%s_%d" % (species, stage)
    fam, cm = AQ.CATALOG[nm]
    return voxel_obj("%s_Plant_%s_%d" % (NAME, species, int(loc[0] * 10 + loc[1] * 100)), AQ.plan(nm), cm, loc, rot_z)


def stone_wall(name, cx, cy, rx, ry, gate_a, gap, rng):
    """Dry-stone ring around the pen pool, with a gap at angle gate_a for the gate."""
    M = H.material("DryStone", (.55, .53, .49), .9)
    out, k, a = [], 0, 0.0
    while a < math.tau:
        da = .55 / max(rx, ry)
        if abs((a - gate_a + math.pi) % math.tau - math.pi) > gap / 2:
            x, y = cx + (rx + .9) * math.cos(a), cy + (ry + .9) * math.sin(a)
            z = max(height(x, y), -.2)
            for lvl in range(2):
                s = rng.uniform(.45, .7)
                out.append(H.box("%s_Stone_%03d" % (name, k), (x, y, z + .25 + lvl * .42), (s * 1.3, s * .8, s * .55), M, .08, (0, 0, a + rng.uniform(-.2, .2))))
                k += 1
        a += da
    return out


def overhang(name, cx, cy, r, rng):
    """r2 refuge cover: a flat rock slab leaning out over the refuge from the wall side, on two stones."""
    M = H.material("DryStone", (.55, .53, .49), .9)
    ox, oy = cx - .5, cy + .9                                          # set back toward the north-west wall
    out = [H.box(name + "_Slab", (ox, oy, .2), (r * 1.9, r * 1.3, .32), M, .1, (0, 0, .35))]
    for k, (dx, dy) in enumerate(((-r * .8, r * .4), (r * .3, r * .7))):
        out.append(H.box("%s_Prop_%d" % (name, k), (ox + dx, oy + dy, -.35), (.6, .6, .9), M, .08, (0, 0, rng.uniform(0, 1))))
    return out


def gate(name, x, y, z, yaw, width=2.2):
    """A shut wooden gate between two posts, a teal keeper lantern on top: closed until settled_care holds."""
    M = K._mats(H)
    out = []
    ox, oy = math.cos(yaw + math.pi / 2) * width / 2, math.sin(yaw + math.pi / 2) * width / 2
    for s in (-1, 1):
        out.append(H.beam("%s_Post_%s" % (name, "a" if s < 0 else "b"), (x + ox * s, y + oy * s, z - .3), (x + ox * s, y + oy * s, z + 1.5), .1, M["dark"], 8))
    for k, hz in enumerate((.35, .8, 1.2)):
        out.append(H.box("%s_Rail_%d" % (name, k), (x, y, z + hz), (.1, width, .14), M["wood"], .02, (0, 0, yaw)))
    out.append(H.beam(name + "_Brace", (x - ox * .9, y - oy * .9, z + .35), (x + ox * .9, y + oy * .9, z + 1.2), .05, M["wood"], 6))
    out.append(K._lamp(H, name + "_Lantern_Keeper", x + ox, y + oy, z + 1.75, "keeper", 3.0))
    return out


def skiff(name, x, y, yaw):
    """A small sky-sea boat moored at the landing (floats; cannot fly - ADR-066)."""
    M = K._mats(H)
    hull = H.material("SkiffHull", (.55, .32, .16), .7)
    out = [H.box(name + "_Hull", (x, y, .25), (4.2, 1.5, .6), hull, .25, (0, 0, yaw)),
           H.box(name + "_Seat", (x, y, .55), (.4, 1.3, .12), M["wood"], .02, (0, 0, yaw)),
           H.beam(name + "_Mast", (x, y, .5), (x, y, 3.6), .06, M["dark"], 6)]
    fx, fy = math.cos(yaw), math.sin(yaw)
    out.append(H.mesh(name + "_Sail", [(x, y, 3.5), (x, y, 1.0), (x + fx * 1.8, y + fy * 1.8, 1.2)], [(0, 1, 2)], H.material("SkiffSail", (.95, .92, .82), .8)))
    return out


def role(name, objs, anchor):
    ob = H.join_parts(name, objs)
    ob.data.transform(mathutils.Matrix.Translation((-anchor[0], -anchor[1], -anchor[2])))
    ob.location = anchor
    H.GROUP.append(ob)
    return ob


def build(out_dir, rev=None):
    global REV, NAME, LAND_ID
    if rev:
        REV, NAME, LAND_ID = rev, "TidePen_" + rev, "ocean-tidepen-" + rev
    hab = data(HABITAT) if REV != "r1" else None
    ZONE_DEPTH.clear()
    VOXEL_CM.clear()
    if hab:
        ZONE_DEPTH.update({z["id"]: z["base_depth_m"] for z in hab["zones"]})
        VOXEL_CM.append(hab["display"]["voxel_cm"])
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    H.GROUP = []
    rng = random.Random(SEED)
    pen = data("data/ocean/tidepen.json")
    links = data("data/ocean/links.json")
    landing = next(d for d in links["docks"] if d["id"] == pen["landing"])
    bx, by, bz = landing["anchor"]["xyz"]                       # Ocean blocks, Y up
    anchor_zup = (bx, -bz, by)

    rock = shelf_mesh(NAME + "_Shelf")
    shelf = [rock, water(NAME + "_Sea", 0.0, 60, 44, 0, -10) if not hab else sea_outside_pen(NAME + "_Sea")]
    pools = [water("%s_PoolWater_%d" % (NAME, i), PEN_SURFACE, rx * .86, ry * .86, px, py, H.material("PoolWater", (.18, .55, .60), .05, 0, 0, .7))
             for i, (px, py, rx, ry) in enumerate(POOLS) if not (hab and i == 0)]
    shelf += pools
    pw_rgb, pw_alpha = PEN_WATER.get(REV, PEN_WATER["r2"])
    penwater = [water(NAME + "_PenWaterSheet", PEN_SURFACE, POOLS[0][2] + 1.0, POOLS[0][3] + 1.0, POOLS[0][0], POOLS[0][1],
                      H.material("PoolWater" if REV == "r2" else "PenWaterClear", pw_rgb, .05, 0, 0, pw_alpha))] if hab else []
    # the pen: wall + gate facing the care station (east)
    pcx, pcy, prx, pry = POOLS[0]
    gate_a = 0.0
    gx, gy = pcx + (prx + .9) * math.cos(gate_a), pcy + (pry + .9) * math.sin(gate_a)
    penparts = stone_wall(NAME + "_PenWall", pcx, pcy, prx, pry, gate_a, .55, rng)
    penparts += gate(NAME + "_PenGate", gx, gy, max(height(gx, gy), 0), gate_a)
    cover = overhang(NAME + "_Refuge", pcx + ZONE_XY["refuge"][0], pcy + ZONE_XY["refuge"][1], ZONE_XY["refuge"][2], rng) if hab else []
    # care station beside the gate: trough, drying rack of sea plants, a choice pad + keeper banner
    cx_, cy_ = gx + 4.5, gy + 1.5
    cz = height(cx_, cy_)
    care = [H.cone(NAME + "_CareTrough", (cx_, cy_, cz + .35), 1.1, .9, .7, K._mats(H)["wood"], 14)]
    care += K.choice_pad(H, NAME + "_Care", cx_ + 1, cy_ + .5, cz, "harvest", 3.0)
    care += K.banner(H, NAME + "_CareBanner", cx_ + 2.6, cy_ - 1.6, cz, "keeper")
    care += K.keeper_post(H, NAME + "_Keeper", cx_ - 1.5, cy_ + 3.2, height(cx_ - 1.5, cy_ + 3.2))
    rack_x, rack_y = cx_ + 2.8, cy_ + 2.2
    rz = height(rack_x, rack_y)
    M = K._mats(H)
    for d in (-1.2, 1.2):
        care.append(H.beam("%s_Rack_Post_%s" % (NAME, "a" if d < 0 else "b"), (rack_x, rack_y + d, rz), (rack_x, rack_y + d, rz + 1.9), .06, M["dark"], 6))
    care.append(H.beam(NAME + "_Rack_Bar", (rack_x, rack_y - 1.3, rz + 1.8), (rack_x, rack_y + 1.3, rz + 1.8), .045, M["dark"], 6))
    for k, sp in enumerate(sorted({p for r in pen["residents"] for p in r["food"]})):
        care.append(plant(sp, (rack_x, rack_y - .9 + k * .6, rz + .55), 3))
    # landing walk from the shelf's sea edge out over the water, mooring posts, the skiff
    lx0, ly0 = -14.0, -7.0
    walk_pts = [(lx0, ly0 + 5), (lx0, ly0), (lx0, ly0 - 9)]
    land = K.boardwalk(H, NAME + "_Landing", walk_pts, height, width=2.4, min_z=.35)
    for k, (mx, my) in enumerate(((lx0 + 1.7, ly0 - 8.5), (lx0 - 1.7, ly0 - 8.5), (lx0 + 1.7, ly0 - 4))):
        land.append(H.beam("%s_Mooring_%d" % (NAME, k), (mx, my, -1.5), (mx, my, 1.4), .14, M["dark"], 8))
    land += skiff(NAME + "_Skiff", lx0 + 3.6, ly0 - 7.5, math.pi / 2)
    land += K.banner(H, NAME + "_WildBanner", 16.0, -7.5, max(height(16, -7.5), 0), "harvest")   # the sea edge: leave wild
    # residents in their habitats, with every habitat plant each needs (from tidepen.json)
    homes = {"sea_turtle": (0, 0), "seahorse": (1, 0), "crab": (2, 1), "starfish": (4, 0)}
    residents, habitat = [], []
    placed = {}
    if hab:                                                            # r2: everyone lives in the pen, in its NORMAL-state zone
        spots = {"sea_turtle": (-1.4, -1.3, .3), "seahorse": (-4.4, 1.2, .02), "crab": (.9, .9, 0), "starfish": (-5.1, .5, 0)}
        for r in hab["residents"]:
            zone = r["zones"]["normal"][0]
            sx_, sy_, lift = spots[r["species"]]
            fz = height(pcx + sx_, pcy + sy_)
            residents.append(creature(r["species"], (pcx + sx_, pcy + sy_, fz + lift), math.pi / 2 if r["species"] == "sea_turtle" else rng.uniform(0, math.tau)))
            placed[r["species"]] = {"zone": zone, "xy": [sx_, sy_], "bed_z": round(fz, 3)}
        for z in hab["zones"]:
            zx, zy, zr = ZONE_XY[z["id"]]
            for k, hp in enumerate(z["plants"]):
                for m in range(3):
                    a, rr = rng.uniform(0, math.tau), zr * rng.uniform(.25, .7)
                    x_, y_ = pcx + zx + rr * math.cos(a), pcy + zy + rr * math.sin(a)
                    habitat.append(plant(hp, (x_, y_, height(x_, y_)), 4, rng.uniform(0, math.tau)))
    for r in ([] if hab else pen["residents"]):
        i, _ = homes.get(r["species"], (2, 0))
        px, py, rx, ry = POOLS[i]
        z = -.5 if r["species"] in ("sea_turtle", "seahorse") else max(height(px + rx * .9, py), -.3)
        sx_, sy_ = (px, py) if r["species"] in ("sea_turtle", "seahorse") else (px + rx * .9, py)
        yaw = math.pi / 2 if i == 0 else rng.uniform(0, math.tau)          # the pen's resident swims along the pool's long axis
        residents.append(creature(r["species"], (sx_, sy_, z), yaw))
        for k, hp in enumerate(r["habitat"]):
            for m in range(3):
                a = rng.uniform(0, math.tau)
                habitat.append(plant(hp, (px + rx * .6 * math.cos(a), py + ry * .6 * math.sin(a), -.55), 4, rng.uniform(0, math.tau)))
    # collision: the landing deck and the shelf bench (walkable), named for their role meshes
    hid = H.material("Collision", (1, 0, 1), 1)
    ucx = {"Landing": [], "Shelf": []}
    for k, (a, b) in enumerate(zip(walk_pts, walk_pts[1:])):
        ob = H.box("UCX_%s_Landing_%02d" % (NAME, k), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, .75), (2.4, abs(b[1] - a[1]), .3), hid, 0)
        ucx["Landing"].append(ob)
    ob = H.box("UCX_%s_Shelf_00" % NAME, (0, 3, .4), (SHELF[0] * 1.7, SHELF[1] * .9, .8), hid, 0)
    ucx["Shelf"].append(ob)
    for u in ucx["Landing"] + ucx["Shelf"]:
        u.display_type, u.hide_render = "WIRE", True
    # gameplay rows
    X = []
    H.marker(X, NAME, "dock", pen["landing"], lx0, ly0 - 8.5, .75, "data/ocean/links.json docks[ocean-tidepen-landing]",
             {"status": "data", "required_adapter": "a ConfigureHost loader for links.json (team-codex); docks are fed in code today"})
    H.marker(X, NAME, "pen_gate", "enclose", gx, gy, max(height(gx, gy), 0), "data/ocean/tidepen.json actions.enclose + daedalus-core TidePenGate",
             {"status": "design", "rule": pen["actions"]["enclose"], "required_adapter": "a host enclose/capture action that asks TidePenGate with host-recorded care events"})
    H.marker(X, NAME, "care", "feed", cx_, cy_, cz, "data/ocean/tidepen.json actions.feed",
             {"status": "design", "required_adapter": "a host feed action that writes a settled_care care event (no fact store exists yet)"})
    H.marker(X, NAME, "release", "leave_wild", 16.0, -7.5, 0, "data/ocean/tidepen.json actions.leave_wild",
             {"status": "design", "rule": pen["actions"]["leave_wild"]})
    for r in pen["residents"]:
        H.marker(X, NAME, "resident", r["species"], 0, 0, 0, "data/ocean/tidepen.json residents + voxel_creatures SEA", {"status": "data", "food": r["food"], "habitat": r["habitat"]}, post=False)
    # verify before joining: no resident clips the pen wall (vertex clearance, per resident, final placement)
    bpy.context.view_layer.update()
    wall_v = [o.matrix_world @ v.co for o in penparts for v in o.data.vertices]
    kd = mathutils.kdtree.KDTree(len(wall_v))
    for i, v in enumerate(wall_v):
        kd.insert(v, i)
    kd.balance()
    per = {o.name.split("_Resident_")[-1]: min(kd.find(o.matrix_world @ v.co)[2] for v in o.data.vertices) for o in residents}
    wall_clear = min(per.values())
    if wall_clear < CLEARANCE_M:
        raise RuntimeError("resident clips the pen wall: %s" % {k: round(v, 2) for k, v in per.items()})
    habitat_rec = None
    if hab:
        cv = [o.matrix_world @ v.co for o in cover for v in o.data.vertices]
        kc = mathutils.kdtree.KDTree(len(cv))
        for i, v in enumerate(cv):
            kc.insert(v, i)
        kc.balance()
        cov = min(kc.find(o.matrix_world @ v.co)[2] for o in residents for v in o.data.vertices)
        if cov < OVERHANG_CLEAR:
            raise RuntimeError("a resident touches the refuge overhang: %.2f m" % cov)
        low_z = PEN_SURFACE + min(s["offset_m"] for s in hab["water_states"])
        for o in residents:                                            # placed in its NORMAL zone, which it also uses at LOW
            sp = o.name.split("_Resident_")[-1]
            top = max((o.matrix_world @ v.co).z for v in o.data.vertices)
            placed[sp]["top_z"] = round(top, 3)
            placed[sp]["covered_at_low_m"] = round(low_z - top, 3)
            if top > low_z - .05:
                raise RuntimeError("%s sticks out of low water: top %.2f, low surface %.2f" % (sp, top, low_z))
        dg = bpy.context.evaluated_depsgraph_get()
        bvh = mathutils.bvhtree.BVHTree.FromObject(rock, dg)
        zones = []
        for z in hab["zones"]:
            zx, zy, _ = ZONE_XY[z["id"]]
            hit = bvh.ray_cast(mathutils.Vector((pcx + zx, pcy + zy, 20.0)), mathutils.Vector((0, 0, -1)))
            measured = PEN_SURFACE - hit[0].z
            if abs(measured - z["base_depth_m"]) > DEPTH_TOL:
                raise RuntimeError("zone %s depth drifted: proposed %.2f measured %.2f" % (z["id"], z["base_depth_m"], measured))
            zones.append({"id": z["id"], "centre_local": [zx, zy], "proposed_depth_m": z["base_depth_m"], "measured_depth_m": round(measured, 3), "cover": z["cover"]})
        states = [{"id": s["id"], "offset_m": s["offset_m"], "surface_z": round(PEN_SURFACE + s["offset_m"], 3),
                   "wet": {z["id"]: z["measured_depth_m"] + s["offset_m"] >= hab["wet_min_m"] for z in zones}} for s in hab["water_states"]]
        if states[0]["wet"]["shallow"] or not states[0]["wet"]["refuge"]:
            raise RuntimeError("measured bed does not give the proposal's tide: %s" % states[0]["wet"])
        habitat_rec = {"source": HABITAT, "sha256": sha(os.path.join(ROOT, HABITAT)), "metric": "ray cast down onto the final rock mesh at each zone centre",
                       "normal_surface_z": PEN_SURFACE, "tolerance_m": DEPTH_TOL, "zones": zones, "water_states": states,
                       "overhang_clearance_m": round(cov, 3), "residents": placed,
                       "pen_water": "role PenWater holds the sheet at the NORMAL level; translate it by offset_m (z) for low/high"}
    # roles
    roles = {
        "Shelf": role(NAME + "_Shelf_Role", shelf, (0.0, 0.0, 0.0)),
        "Pen": role(NAME + "_Pen", penparts + cover, (pcx, pcy, 0.0)),
        "CareStation": role(NAME + "_CareStation", care, (cx_, cy_, cz)),
        "Landing": role(NAME + "_Landing", land, (lx0, ly0, 0.0)),
        "Residents": role(NAME + "_Residents", residents, (0.0, 0.0, 0.0)),
        "Habitat": role(NAME + "_Habitat", habitat, (0.0, 0.0, 0.0)),
    }
    if hab:
        roles["PenWater"] = role(NAME + "_PenWater", penwater, (pcx, pcy, PEN_SURFACE))
    for k, us in ucx.items():
        for u in us:
            u.name = "UCX_%s_%02d" % (roles[k].name, us.index(u))
            u.data.transform(u.matrix_basis)
            u.matrix_basis.identity()
            u.data.transform(mathutils.Matrix.Translation(-roles[k].location))
            u.location = roles[k].location.copy()
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    for k, ob in roles.items():
        H.export_group(os.path.join(out_dir, "%s_%s" % (NAME, k)), [ob] + ucx.get(k, []))
        files[k] = "%s_%s" % (NAME, k)
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = None
    pts = [ob.location for ob in roles.values()]
    layout = {
        "land_id": LAND_ID, "name": NAME, "realm": "OCEAN", "not_a_deed": True, "status": "design",
        "frame": {"units": "metres, Z up, sea level z=0 (OceanTerrain.SEA_LEVEL)",
                  "origin": "the tide-pen landing anchor", "anchor_blocks_yup": [bx, by, bz], "anchor_zup_m": list(anchor_zup),
                  "conversion": "Ocean blocks (x, y_up, z) -> Blender (x, -z, y); 1 block = 1 m"},
        "sources": {"data/ocean/tidepen.json": sha(os.path.join(ROOT, "data/ocean/tidepen.json")), "data/ocean/links.json": sha(os.path.join(ROOT, "data/ocean/links.json"))},
        "story": "Sky-born sea creatures are cared for in the tide pools before anyone may pen them. The pen gate stays shut until settled_care holds; the sea edge is always open.",
        "roles": {k: {"file": files[k] + ".glb", "fbx": files[k] + ".fbx", "anchor": [round(v, 3) for v in ob.location],
                      "triangles": sum(len(p.vertices) - 2 for p in ob.data.polygons), "materials": [m.name for m in ob.data.materials if m],
                      "collision": [u.name for u in ucx.get(k, [])]} for k, ob in roles.items()},
        "residents": [{"species": r["species"], "food": r["food"], "habitat": r["habitat"], "habitat_plants_placed": 3 * len(r["habitat"])} for r in pen["residents"]],
        "clearance": {"metric": "minimum vertex distance, Residents to Pen wall, final geometry", "required_m": CLEARANCE_M, "measured_m": round(wall_clear, 3)},
        "gameplay": X,
        "showcase": {"hero": [0.0, -2.0, 0.0, 46.0], "detail": [round(gx, 2), round(gy, 2), 0.5, 16.0], "top": [0.0, -3.0, 0.0, 52.0]},
        "resident_scale": RESIDENT_SCALE if not hab else VOXEL_CM[0] / 10.0,
        "provenance": {"recipe": "tools/blender/tidepen_shelf.py + kit_waterworks + voxel_creatures + voxel_aquatic + hd_island",
                       "git": commit, "blender": bpy.app.version_string, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
    }
    if habitat_rec:
        layout["habitat"] = habitat_rec
    layout["island_file"] = files["Shelf"] + ".glb"
    layout["roles"] = {k: v for k, v in layout["roles"].items() if k != "Shelf"}
    layout["hashes"] = {f: [os.path.getsize(os.path.join(out_dir, f)), sha(os.path.join(out_dir, f))] for f in sorted(os.listdir(out_dir)) if f.endswith((".glb", ".fbx"))}
    with open(os.path.join(out_dir, NAME + ".layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=1)
    return layout, (sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    t0 = time.time()
    lay, _ = build(os.path.abspath(argv[0]), argv[argv.index("--rev") + 1] if "--rev" in argv else None)
    print("TIDEPEN %s roles=%d residents=%d clearance=%.2f %.0fs" % (lay["land_id"], len(lay["roles"]) + 1, len(lay["residents"]), lay["clearance"]["measured_m"], time.time() - t0), flush=True)
