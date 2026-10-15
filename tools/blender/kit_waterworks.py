# SPDX-License-Identifier: MIT
"""Waterworks kit: reusable builders for stream-side craft pieces on Team Claude's HD islands.

Every builder takes the hd_island module as `H`, so it uses H's primitives, named materials and GROUP. Everything it
makes lands in the same export, and nothing here owns a scene. Coordinates are island-local metres before the deck
shift: z is absolute, and the deck datum is H.DECK. The caller shifts everything by -DECK with the rest of the island.

  waterwheel(H, name, x, y, yaw, radius, width, paddles, broken)  breastshot wheel + flume + A-frames. `broken` drops
                                                                  that many paddles (some lie on the bank) and adds a
                                                                  snapped flume board
  boardwalk(H, name, pts, h, width)                               plank walk on posts along a polyline, with rope rails
  footbridge(H, name, a, b, deck_z, width)                        arched plank bridge from a to b
  repair_station(H, name, x, y, z, yaw, parts)                    bench, vise, spare paddles, one labelled crate per
                                                                  power-unit part, amber work lamp
  reed_bed(H, name, cx, cy, rx, ry, h, seed, water_z)             reeds and cattails in the shallows, plus a drying rack
                                                                  with cut bundles (harvest)
  refuge(H, name, x, y, z, yaw)                                   stilted round hut, reed-thatch roof, warm windows,
                                                                  hearth smoke stack, warning bell
  keeper_post(H, name, x, y, z)                                   keeper's lantern, bench and water-gauge staff
  signpost(H, name, x, y, z, arms)                                one arm per choice, colour-coded

Choice colours make the three player choices readable at a distance: REPAIR is amber brass, HARVEST is reed gold,
REFUGE is hearth red. The keeper's lantern is spring teal. Builders return the objects they made.
"""
import math
import random

CHOICE_RGB = {"repair": (.95, .62, .16), "harvest": (.86, .78, .30), "refuge": (.92, .30, .18), "keeper": (.25, .85, .80)}


def _mats(H):
    return {
        "wood": H.material("Reedwood", (.42, .26, .12), .75),
        "dark": H.material("Reedwood_Dark", (.24, .14, .07), .8),
        "iron": H.material("IronBand", (.30, .30, .32), .45, .85),
        "brass": H.material("Brass", (.72, .50, .15), .35, .8),
        "rope": H.material("Rope", (.70, .60, .40), .95),
        "thatch": H.material("ReedThatch", (.74, .62, .30), .95),
        "reed": H.material("Reed", (.42, .55, .22), .85),
        "cattail": H.material("Cattail", (.36, .22, .12), .9),
        "water": H.material("FlumeWater", (.30, .62, .78), .05, 0, .2, .7),
        "stone": H.material("MillStone", (.55, .54, .50), .9),
    }


def _lamp(H, name, x, y, z, key, power=3.0):
    return H.sphere(name, (x, y, z), (.32, .32, .38), H.material("Glow_" + key, CHOICE_RGB[key], .3, 0, power), 10, 6)


def _rot(dx, dy, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return dx * c - dy * s, dx * s + dy * c


def waterwheel(H, name, x, y, yaw, radius=3.4, width=1.4, paddles=12, broken=0, water_z=None):
    """Wheel in the plane of the stream (axle across it). `yaw` is the stream direction; the axle runs at yaw+90°."""
    M = _mats(H)
    wz = H.WATER if water_z is None else water_z
    cz = wz + radius - .7                                   # the lower paddles dip 0.7 m into the stream
    out = []
    ax, ay = _rot(0, 1, yaw)                                # axle direction (unit), across the stream
    half = width / 2 + .25
    # axle and hub
    out.append(H.beam(name + "_Axle", (x - ax * (half + 1.6), y - ay * (half + 1.6), cz), (x + ax * (half + 1.6), y + ay * (half + 1.6), cz), .22, M["iron"], 10))
    out.append(H.beam(name + "_Hub", (x - ax * .5, y - ay * .5, cz), (x + ax * .5, y + ay * .5, cz), .55, M["dark"], 12))
    # two rims as 24 short beams each, spokes, iron bands
    sx, sy = _rot(1, 0, yaw)                                # along-stream unit vector (wheel plane horizontal axis)
    rng = random.Random(len(name) * 97 + paddles)
    for side in (-1, 1):
        ox, oy = ax * side * width / 2, ay * side * width / 2
        pts = []
        for k in range(25):
            a = k / 24 * math.tau
            pts.append((x + ox + sx * radius * math.cos(a), y + oy + sy * radius * math.cos(a), cz + radius * math.sin(a)))
        for k in range(24):
            out.append(H.beam("%s_Rim%s_%02d" % (name, "L" if side < 0 else "R", k), pts[k], pts[k + 1], .12, M["wood"], 6))
        for k in range(8):
            a = k / 8 * math.tau
            out.append(H.beam("%s_Spoke%s_%d" % (name, "L" if side < 0 else "R", k), (x + ox, y + oy, cz),
                              (x + ox + sx * radius * math.cos(a), y + oy + sy * radius * math.cos(a), cz + radius * math.sin(a)), .09, M["dark"], 6))
    # paddles across the rims; `broken` of them missing, two of those lying on the bank
    missing = set(rng.sample(range(paddles), min(broken, paddles))) if broken else set()
    for k in range(paddles):
        a = k / paddles * math.tau
        px, py, pz = x + sx * (radius - .45) * math.cos(a), y + sy * (radius - .45) * math.cos(a), cz + (radius - .45) * math.sin(a)
        if k in missing:
            continue
        out.append(H.box("%s_Paddle_%02d" % (name, k), (px, py, pz), (.12, width + .2, .95), M["wood"], .02, (0, math.pi / 2 - a, yaw)))   # long side radial
    for j, k in enumerate(sorted(missing)[:2]):
        bx, by = x + ax * (half + 3 + j * 1.2) + sx * (j - .5) * 2, y + ay * (half + 3 + j * 1.2) + sy * (j - .5) * 2
        out.append(H.box("%s_FallenPaddle_%d" % (name, j), (bx, by, wz + .9 + j * .1), (.95, width + .2, .12), M["wood"], .02, (0, .2 * j, yaw + .6 * j)))
    # A-frame supports on both banks
    for side in (-1, 1):
        fx, fy = x + ax * side * (half + 1.2), y + ay * side * (half + 1.2)
        for d in (-1, 1):
            out.append(H.beam("%s_Frame%s_%s" % (name, "L" if side < 0 else "R", "a" if d < 0 else "b"),
                              (fx + sx * d * 2.2, fy + sy * d * 2.2, wz - 1.5), (fx, fy, cz + .3), .16, M["dark"], 6))
        out.append(H.box("%s_Bearing%s" % (name, "L" if side < 0 else "R"), (fx, fy, cz), (.7, .7, .6), M["brass"], .08, (0, 0, yaw)))
    # flume: a trough on trestles bringing water over the top from upstream (breastshot), with a water sheet
    fz = cz + radius * .55
    f0 = (x - sx * (radius + 9), y - sy * (radius + 9))
    f1 = (x - sx * (radius * .35), y - sy * (radius * .35))
    out.append(H.beam(name + "_Flume", (f0[0], f0[1], fz + .35), (f1[0], f1[1], fz), .55, M["wood"], 4))
    out.append(H.beam(name + "_FlumeWater", (f0[0], f0[1], fz + .62), (f1[0], f1[1], fz + .28), .38, M["water"], 4))
    for t in (.2, .55, .85):
        tx, ty = f0[0] + (f1[0] - f0[0]) * t, f0[1] + (f1[1] - f0[1]) * t
        out.append(H.beam("%s_Trestle_%d" % (name, int(t * 100)), (tx, ty, wz - 2), (tx, ty, fz + .2 - .35 * t), .14, M["dark"], 6))
    # the spill: a sheet falling from the flume lip onto the top paddles, and foam where the wheel meets the stream
    out.append(H.box(name + "_Spill", (f1[0] + sx * .35, f1[1] + sy * .35, fz - .2), (.12, width * .7, 1.1), M["water"], 0, (0, .35, yaw)))
    foam = H.material("Foam", (.92, .96, 1.0), .35, 0, 0, .75)
    for k in range(7):
        a = k / 7 * math.tau
        out.append(H.cone("%s_Foam_%d" % (name, k), (x + sx * 1.6 * math.cos(a) + ax * .6 * math.sin(a), y + sy * 1.6 * math.cos(a) + ay * .6 * math.sin(a), wz + .05),
                          .9 - .08 * k % 3, .5, .12, foam, 10))
    if broken:
        out.append(H.box(name + "_SnappedFlumeBoard", (f1[0] + ax * 1.6, f1[1] + ay * 1.6, wz + .6), (2.4, .4, .08), M["wood"], .02, (0, .5, yaw + .3)))
    return out


def boardwalk(H, name, pts, h, width=2.4, min_z=None, post_every=5):
    """Planks every 0.6 m along a polyline, on posts every `post_every` planks, with rope rails strung post to post
    (r3: no long rope spans; a rope never runs further than one post gap). Deck rides at max(ground, min_z) + 0.5."""
    M = _mats(H)
    lo = (H.WATER + .7) if min_z is None else min_z
    out, k = [], 0
    posts = {-1: [], 1: []}
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        yaw = math.atan2(y1 - y0, x1 - x0)
        n = max(1, int(L / .6))
        for i in range(n):
            t = (i + .5) / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            z = max(h(x, y), lo) + .5
            out.append(H.box("%s_Plank_%03d" % (name, k), (x, y, z), (.5, width, .1), M["wood"], .01, (0, 0, yaw)))
            if k % post_every == 0 or (i == n - 1 and (x1, y1) == pts[-1]):
                for side in (-1, 1):
                    ox, oy = _rot(0, side * (width / 2 + .1), yaw)
                    top = (x + ox, y + oy, z + 1.0)
                    out.append(H.beam("%s_Post_%03d_%s" % (name, k, "L" if side < 0 else "R"), (x + ox, y + oy, min(h(x, y), z) - .6), top, .07, M["dark"], 6))
                    if posts[side]:
                        out.append(H.beam("%s_Rail_%03d_%s" % (name, k, "L" if side < 0 else "R"), posts[side][-1], top, .035, M["rope"], 5))
                    posts[side].append(top)
            k += 1
    return out


def footbridge(H, name, a, b, deck_z, width=2.2, rise=.9):
    M = _mats(H)
    out = []
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    yaw = math.atan2(b[1] - a[1], b[0] - a[0])
    n = max(4, int(L / .55))
    prev = None
    for i in range(n + 1):
        t = i / n
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        z = deck_z + rise * math.sin(math.pi * t)
        if i < n:
            out.append(H.box("%s_Plank_%02d" % (name, i), (x, y, z), (.48, width, .12), M["wood"], .01, (0, 0, yaw)))
        for side in (-1, 1):
            ox, oy = _rot(0, side * (width / 2 + .12), yaw)
            if prev and i % 2 == 0:
                out.append(H.beam("%s_Rail_%02d_%s" % (name, i, "L" if side < 0 else "R"), (prev[0] + ox, prev[1] + oy, prev[2] + 1.0), (x + ox, y + oy, z + 1.0), .06, M["dark"], 6))
            if i % 4 == 0:
                out.append(H.beam("%s_Baluster_%02d_%s" % (name, i, "L" if side < 0 else "R"), (x + ox, y + oy, z), (x + ox, y + oy, z + 1.05), .06, M["dark"], 6))
        if i % 2 == 0:
            prev = (x, y, z)
    for end, nm in ((a, "A"), (b, "B")):
        out.append(H.box("%s_Abutment%s" % (name, nm), (end[0], end[1], deck_z - 1.6), (1.4, width + .6, 3.0), M["stone"], .2, (0, 0, yaw)))   # top sits under the deck
    return out


def repair_station(H, name, x, y, z, yaw=0.0, parts=()):
    """The REPAIR choice: bench + vise, a rack of spare paddles, one crate per power-unit part (labelled by object name)."""
    M = _mats(H)
    out = [H.box(name + "_Bench", (x, y, z + .45), (3.2, 1.2, .9), M["wood"], .05, (0, 0, yaw)),
           H.box(name + "_BenchTop", (x, y, z + .95), (3.4, 1.4, .12), M["dark"], .02, (0, 0, yaw))]
    vx, vy = _rot(1.2, 0, yaw)
    out.append(H.box(name + "_Vise", (x + vx, y + vy, z + 1.2), (.4, .5, .4), M["iron"], .04, (0, 0, yaw)))
    # spare paddle rack
    rx, ry = _rot(-2.6, .4, yaw)
    for k in range(5):
        px, py = _rot(-2.6, -.3 + k * .18, yaw)
        out.append(H.box("%s_SparePaddle_%d" % (name, k), (x + px, y + py, z + 1.0), (.12, 1.4, .9), M["wood"], .02, (0, .25, yaw)))
    out.append(H.beam(name + "_RackBar", (x + rx, y + ry - .6, z + 1.6), (x + rx, y + ry + .6, z + 1.6), .06, M["dark"], 6))
    # one crate per part, with a brass band so they read as engineered parts, not food
    for k, part in enumerate(parts):
        cx, cy = _rot(-1 + k * 1.05, -1.6, yaw)
        out.append(H.box("%s_PartCrate_%s" % (name, part), (x + cx, y + cy, z + .4), (.9, .9, .8), M["wood"], .04, (0, 0, yaw)))
        out.append(H.box("%s_PartCrate_%s_Band" % (name, part), (x + cx, y + cy, z + .55), (.94, .94, .12), M["brass"], .01, (0, 0, yaw)))
    # amber work lamp on a pole: REPAIR reads amber from across the stream
    lx, ly = _rot(1.9, .7, yaw)
    out.append(H.beam(name + "_LampPole", (x + lx, y + ly, z), (x + lx, y + ly, z + 3.2), .07, M["dark"], 6))
    out.append(_lamp(H, name + "_Lamp_Repair", x + lx, y + ly, z + 3.3, "repair"))
    return out


def reed_bed(H, name, cx, cy, rx, ry, h, seed=1, water_z=None, count=170):
    """The HARVEST choice (and the stream's living filter): reeds and cattails in the shallows, plus a drying rack."""
    M = _mats(H)
    wz = H.WATER if water_z is None else water_z
    rng = random.Random(seed * 13 + 5)
    out = []
    for k in range(count):
        a, r = rng.uniform(0, math.tau), math.sqrt(rng.random())
        x, y = cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)
        base = min(h(x, y), wz - .2)
        tall = rng.uniform(1.6, 2.8)
        out.append(H.cone("%s_Reed_%03d" % (name, k), (x, y, base + tall / 2), .07, .015, tall, M["reed"], 4))
        if k % 6 == 0:
            out.append(H.cone("%s_Cattail_%03d" % (name, k), (x, y, base + tall + .15), .09, .09, .45, M["cattail"], 6))
    # drying rack on the bank (cut bundles = the harvest)
    bx, by = cx + rx + 3, cy
    bz = h(bx, by)
    for d in (-1.4, 1.4):
        out.append(H.beam("%s_Rack_Post_%s" % (name, "a" if d < 0 else "b"), (bx, by + d, bz), (bx, by + d, bz + 2.2), .07, M["dark"], 6))
    out.append(H.beam(name + "_Rack_Bar", (bx, by - 1.5, bz + 2.1), (bx, by + 1.5, bz + 2.1), .05, M["dark"], 6))
    gold = H.material("ReedBundle", CHOICE_RGB["harvest"], .85)
    for k in range(5):
        out.append(H.cone("%s_Bundle_%d" % (name, k), (bx, by - 1.1 + k * .55, bz + 1.45), .16, .1, 1.3, gold, 6))
    return out


def refuge(H, name, x, y, z, yaw=0.0, radius=3.2):
    """The REFUGE choice: a round reed-thatch hut on stilts with warm windows, a hearth stack and a warning bell."""
    M = _mats(H)
    floor = z + 1.4
    out = []
    for k in range(6):
        a = k / 6 * math.tau
        out.append(H.beam("%s_Stilt_%d" % (name, k), (x + radius * .85 * math.cos(a), y + radius * .85 * math.sin(a), z - .8),
                          (x + radius * .85 * math.cos(a), y + radius * .85 * math.sin(a), floor), .12, M["dark"], 6))
    out.append(H.cone(name + "_Floor", (x, y, floor), radius + .3, radius + .3, .25, M["wood"], 16))
    out.append(H.cone(name + "_Wall", (x, y, floor + 1.25), radius, radius, 2.3, M["wood"], 16))
    out.append(H.cone(name + "_Roof", (x, y, floor + 3.6), radius + 1.1, .2, 2.6, M["thatch"], 16))
    warm = H.material("Glow_refuge", CHOICE_RGB["refuge"], .3, 0, 2.5)
    for k in range(3):
        a = yaw + (k - 1) * .9
        out.append(H.box("%s_Window_%d" % (name, k), (x + radius * math.cos(a), y + radius * math.sin(a), floor + 1.4), (.15, .9, .7), warm, .02, (0, 0, a)))
    dx, dy = math.cos(yaw + math.pi), math.sin(yaw + math.pi)
    out.append(H.box(name + "_Door", (x + radius * dx, y + radius * dy, floor + 1.05), (.2, 1.0, 1.9), M["dark"], .02, (0, 0, yaw + math.pi)))
    for k in range(4):                                       # steps down from the door
        out.append(H.box("%s_Step_%d" % (name, k), (x + (radius + .6 + k * .55) * dx, y + (radius + .6 + k * .55) * dy, floor - .35 * (k + 1)), (.55, 1.2, .14), M["wood"], .01, (0, 0, yaw)))
    out.append(H.cone(name + "_Chimney", (x + .8, y + .8, floor + 4.6), .35, .3, 2.2, M["stone"], 8))
    bx, by = x + (radius + 2) * math.cos(yaw), y + (radius + 2) * math.sin(yaw)
    out.append(H.beam(name + "_BellPost", (bx, by, z), (bx, by, z + 3.4), .1, M["dark"], 6))
    out.append(H.cone(name + "_Bell", (bx, by, z + 3.0), .38, .22, .55, M["brass"], 10))
    return out


def keeper_post(H, name, x, y, z):
    """Where the ecology keeper stands: a teal lantern, a bench and a water-gauge staff in the shallows."""
    M = _mats(H)
    out = [H.beam(name + "_LanternPole", (x, y, z), (x, y, z + 2.8), .07, M["dark"], 6),
           _lamp(H, name + "_Lantern_Keeper", x, y, z + 2.95, "keeper", 2.5),
           H.box(name + "_Bench", (x + 1.4, y, z + .45), (1.8, .5, .12), M["wood"], .02),
           H.box(name + "_BenchLegs", (x + 1.4, y, z + .2), (1.6, .4, .4), M["dark"], .02)]
    gx, gy = x - 2.5, y + 1.0
    out.append(H.beam(name + "_GaugeStaff", (gx, gy, z - 2.5), (gx, gy, z + 1.8), .06, M["dark"], 6))
    for k in range(6):
        out.append(H.box("%s_GaugeMark_%d" % (name, k), (gx, gy, z - 2 + k * .6), (.2, .04, .05), M["brass"], 0))
    return out


def signpost(H, name, x, y, z, arms):
    """`arms` = [(choice_key, yaw)]: one coloured arm per choice, pointing the way."""
    M = _mats(H)
    out = [H.beam(name + "_Pole", (x, y, z), (x, y, z + 3.0), .09, M["dark"], 6)]
    for k, (key, yaw) in enumerate(arms):
        ox, oy = math.cos(yaw) * .8, math.sin(yaw) * .8
        out.append(H.box("%s_Arm_%s" % (name, key), (x + ox, y + oy, z + 2.6 - k * .38), (1.6, .14, .3), H.material("Sign_" + key, CHOICE_RGB[key], .6, 0, .4), .02, (0, 0, yaw)))
    return out


# ---- r2 dressing: what makes the three choices readable up close (PootScoot 32419: hierarchy, grouping, separation) ----
PAD_RGB = {"repair": (.56, .55, .52), "harvest": (.80, .70, .38), "refuge": (.55, .30, .20)}


def choice_pad(H, name, x, y, z, key, radius=4.2):
    """A ground pad under each choice: flagstone (repair), straw mat (harvest), packed red earth (refuge)."""
    return [H.cone(name + "_Pad_" + key, (x, y, z + .1), radius, radius * .96, .22, H.material("Pad_" + key, PAD_RGB[key], .9), 20)]


def banner(H, name, x, y, z, key, height=4.2):
    """A pole with a pennant in the choice colour, readable from across the stream."""
    M = _mats(H)
    out = [H.beam(name + "_Pole", (x, y, z), (x, y, z + height), .07, M["dark"], 6)]
    top = z + height - .2
    verts = [(x, y, top), (x, y, top - 1.1), (x + 1.7, y, top - .55)]
    out.append(H.mesh(name + "_Pennant_" + key, verts, [(0, 1, 2), (0, 2, 1)], H.material("Cloth_" + key, CHOICE_RGB[key], .8)))
    return out


def awning(H, name, x, y, z, yaw, key, w=4.2, d=2.4):
    """A sloped cloth awning on four posts over a workplace (the repair bench), in the choice colour."""
    M = _mats(H)
    out = []
    for i, (dx, dy) in enumerate(((-w / 2, -d / 2), (w / 2, -d / 2), (-w / 2, d / 2), (w / 2, d / 2))):
        px, py = _rot(dx, dy, yaw)
        out.append(H.beam("%s_Post_%d" % (name, i), (x + px, y + py, z), (x + px, y + py, z + (2.6 if dy < 0 else 3.1)), .08, M["dark"], 6))
    out.append(H.box(name + "_Cloth_" + key, (x, y, z + 2.95), (w + .4, d + .5, .06), H.material("Cloth_" + key, CHOICE_RGB[key], .8), 0, (math.atan2(.5, d), 0, yaw)))
    return out


def shore_stones(H, name, pts, h, seed=1, every=1.6, water_z=None):
    """Rounded stones along a bank polyline: a crafted edge where the water meets the haven."""
    wz = H.WATER if water_z is None else water_z
    rng = random.Random(seed * 17 + 3)
    stone = H.material("ShoreStone", (.50, .50, .47), .85)
    out, k = [], 0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        for i in range(max(1, int(L / every))):
            t = i / max(1, int(L / every))
            x, y = x0 + (x1 - x0) * t + rng.uniform(-.4, .4), y0 + (y1 - y0) * t + rng.uniform(-.4, .4)
            s = rng.uniform(.45, .9)
            out.append(H.sphere("%s_Stone_%03d" % (name, k), (x, y, max(h(x, y), wz - .3) + s * .35), (s, s * rng.uniform(.8, 1.2), s * .6), stone, 8, 5))
            k += 1
    return out


def string_lights(H, name, pts, h, every=3.0, lift=2.1, min_z=None):
    """Warm bulbs along a walk polyline at rail height: the route reads at dusk."""
    lo = (H.WATER + .7) if min_z is None else min_z
    warm = H.material("Glow_string", (1.0, .80, .45), .3, 0, 4.0)
    out, k = [], 0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        for i in range(max(1, int(L / every))):
            t = (i + .5) / max(1, int(L / every))
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            out.append(H.sphere("%s_Bulb_%03d" % (name, k), (x, y, max(h(x, y), lo) + lift - .25 * math.sin(math.pi * t)), (.13, .13, .16), warm, 8, 5))
            k += 1
    return out


def blossom_tree(H, name, x, y, z, seed=1, rgb=(.93, .55, .75)):
    """Spring blossom (the Spring octet's accent prop): a twisted trunk and pink crowns, so the haven reads apart from
    the island's green tree masses."""
    rng = random.Random(seed * 29 + 11)
    M = _mats(H)
    bloom = H.material("Blossom", rgb, .7)
    out = [H.beam(name + "_Trunk", (x, y, z), (x + rng.uniform(-.6, .6), y + rng.uniform(-.6, .6), z + 3.2), .28, M["dark"], 8)]
    for k in range(4):
        out.append(H.sphere("%s_Crown_%d" % (name, k), (x + rng.uniform(-1.6, 1.6), y + rng.uniform(-1.6, 1.6), z + 3.6 + rng.uniform(0, 1.4)),
                            (rng.uniform(1.4, 2.1),) * 2 + (rng.uniform(1.1, 1.6),), bloom, 12, 7))
    return out
