# SPDX-License-Identifier: MIT
"""Aquatic plants for Daedalus2 — 43 species x 6 growth stages = 258 voxel props for lakes, sky rivers, marsh rims,
waterfalls' plunge pools and the sea under the islands.

Families (and where hd_island / the game place them):
  pond       floating at the waterline — pivot = waterline, roots hang below (lakes, sky rivers)
  marsh      emergent at the shore — pivot = mud line, stems stand out of shallow water (lake rims, mire islands)
  submerged  rooted on the bed, fully under water — pivot = bed (lake floors, fishing spots)
  sea        marine algae and seagrass — pivot = seabed (the ocean under the islands, coastal islets)
  realm      Daedalus originals tied to the mechanics: rillprism reed (RingInfusion's cool herb), filter moss
             (cleans spring water: island_chemistry water.filter_needed), glowkelp, skylily, ember lotus, frost fern

Stages 1-6: sprout, young, mature, flowering, seeding, old. Each species' json says what it does in the game
(`USES`): food for which fish (island_chemistry FISH), spring-purity bonus, herb / craft / inn goods, cover for
fry and frogs, and which island kinds grow it. Voxels: 5 cm (10 cm for the big kelps).

    import voxel_aquatic as A
    A.plan("Prop_Aquatic_Pond_WaterLily_4")  -> [(x, y, z, colour)]
    A.CATALOG                                 -> {name: (family, voxel_cm)}
    A.build_all(out_dir)                      -> FBX + json per prop (Blender)
"""
import json
import math
import os
import random

import voxel_creatures as VC
import voxel_island as V

PAL = dict(VC.PAL)
PAL.update({
    "aq_pad": (0.22, 0.52, 0.22), "aq_pad_d": (0.14, 0.36, 0.16), "aq_pad_r": (0.55, 0.22, 0.20), "aq_leaf": (0.30, 0.62, 0.26),
    "aq_leaf_l": (0.50, 0.78, 0.38), "aq_leaf_d": (0.16, 0.40, 0.18), "aq_blade": (0.38, 0.62, 0.30), "aq_blade_y": (0.70, 0.72, 0.38),
    "aq_stem": (0.34, 0.55, 0.24), "aq_root": (0.55, 0.48, 0.38), "aq_mud": (0.30, 0.24, 0.18), "aq_cob": (0.40, 0.24, 0.12),
    "aq_plume": (0.78, 0.70, 0.55), "aq_white": (0.97, 0.96, 0.92), "aq_pink": (0.96, 0.62, 0.72), "aq_pink_d": (0.85, 0.35, 0.52),
    "aq_yellow": (0.98, 0.85, 0.20), "aq_purple": (0.60, 0.42, 0.85), "aq_blue": (0.38, 0.48, 0.92), "aq_pod": (0.55, 0.62, 0.30),
    "aq_pod_d": (0.35, 0.30, 0.18), "aq_fern_r": (0.68, 0.30, 0.22), "aq_lettuce": (0.62, 0.82, 0.45), "aq_moss": (0.20, 0.45, 0.18),
    "aq_kelp": (0.48, 0.40, 0.16), "aq_kelp_d": (0.32, 0.28, 0.12), "aq_kelp_l": (0.62, 0.55, 0.22), "aq_float": (0.55, 0.45, 0.18),
    "aq_sea_l": (0.40, 0.80, 0.35), "aq_wrack": (0.45, 0.38, 0.20), "aq_sarg": (0.70, 0.55, 0.20), "aq_dulse": (0.62, 0.15, 0.22),
    "aq_seagrass": (0.28, 0.55, 0.30), "aq_prism": (0.55, 0.85, 1.00), "aq_prism2": (0.85, 0.65, 1.00), "aq_glow": (0.45, 1.00, 0.85),
    "aq_glow2": (0.30, 0.75, 0.95), "aq_sky": (0.75, 0.88, 1.00), "aq_ember": (1.00, 0.45, 0.12), "aq_ember2": (1.00, 0.80, 0.30),
    "aq_frost": (0.80, 0.95, 1.00), "aq_frost2": (0.55, 0.80, 0.92), "aq_filter": (0.30, 0.60, 0.45), "aq_filter2": (0.70, 0.95, 0.80),
    "aq_horse": (0.38, 0.55, 0.30), "aq_band": (0.20, 0.25, 0.15), "aq_rice": (0.85, 0.75, 0.45), "aq_marig": (0.98, 0.78, 0.10),
})
STAGES = ("Sprout", "Young", "Mature", "Flowering", "Seeding", "Old")
GROW = (0.35, 0.55, 0.78, 1.0, 1.0, 1.25)


def _put(out, x, y, z, c):
    out.append((round(x), round(y), round(z), c))


def _box(out, x0, y0, z0, w, d, h, c):
    x0, y0, z0 = round(x0), round(y0), round(z0)
    for x in range(int(x0), int(x0 + w)):
        for y in range(int(y0), int(y0 + d)):
            for z in range(int(z0), int(z0 + h)):
                out.append((x, y, z, c))


def _blade(out, x, y, z0, h, dx, dy, c, tip=None, width=1, curl=0.0):
    """A leaf or stem rising from (x,y,z0) leaning (dx,dy) per unit height; optional droop curl at the top."""
    for k in range(int(h)):
        t = k / max(1, h - 1)
        bend = curl * t * t
        px, py = x + dx * k + bend * dx * 6, y + dy * k + bend * dy * 6
        pz = z0 + k - int(bend * 3)
        for w in range(width):
            _put(out, px + w * (1 if abs(dy) >= abs(dx) else 0), py + w * (1 if abs(dx) > abs(dy) else 0), pz, tip if (tip and k >= h - 2) else c)
    return x + dx * (h - 1), y + dy * (h - 1), z0 + h - 1


def _disc(out, cx, cy, z, r, c, edge=None, notch=True, ring=None):
    for x in range(int(cx - r) - 1, int(cx + r) + 2):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            d = math.hypot(x + .5 - cx, y + .5 - cy)
            if d > r:
                continue
            if notch and y > cy and abs(x + .5 - cx) < 0.9:           # the lily-pad slit
                continue
            col = edge if (edge and d > r - 1) else c
            if ring and d > r - 1:
                _put(out, x, y, z + 1, ring)                         # the giant pad's upturned rim
            _put(out, x, y, z, col)


def _ball(out, cx, cy, cz, r, c):
    for x in range(int(cx - r) - 1, int(cx + r) + 2):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for z in range(int(cz - r) - 1, int(cz + r) + 2):
                if (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 + (z + .5 - cz) ** 2 <= r * r:
                    _put(out, x, y, z, c)


def _flower(out, x, y, z, r, petal, centre, cup=True):
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if abs(dx) + abs(dy) <= r and (dx or dy):
                _put(out, x + dx, y + dy, z + (1 if cup and abs(dx) + abs(dy) == r else 0), petal)
    _put(out, x, y, z, centre)
    if r >= 2:
        _put(out, x, y, z + 1, centre)


def _roots(out, x, y, z, n, length, rng, c="aq_root"):
    for _ in range(n):
        px, py = x + rng.randint(-1, 1), y + rng.randint(-1, 1)
        for k in range(length + rng.randint(-1, 1)):
            _put(out, px, py, z - 1 - k, c)
            if rng.random() < 0.3:
                px += rng.choice((-1, 1))


# ---- species builders: fn(out, g, stage, rng) -------------------------------------------------------------------

def water_lily(out, g, st, rng, petal="aq_white"):
    for i in range(max(1, int(5 * g))):
        a = rng.random() * 6.28
        d = 0 if i == 0 else rng.uniform(3, 9 * g)
        _disc(out, d * math.cos(a), d * math.sin(a), 0, max(1.5, rng.uniform(2.4, 3.6) * g), "aq_pad", "aq_pad_d")
    _roots(out, 0, 0, 0, 3, int(4 * g) + 1, rng)
    if st >= 3:
        _flower(out, 1, -2, 1, 2, petal, "aq_yellow")
    if st == 4:
        _ball(out, -3, 3, 1, 1.0, "aq_pod")


def pink_lily(out, g, st, rng):
    water_lily(out, g, st, rng, petal="aq_pink")


def lotus(out, g, st, rng):
    for i in range(max(1, int(4 * g))):
        a = i * 2.2
        h = int(rng.uniform(4, 9) * g)
        x, y, z = _blade(out, 2 * math.cos(a), 2 * math.sin(a), 0, h, 0.15 * math.cos(a), 0.15 * math.sin(a), "aq_stem")
        _disc(out, x, y, z + 1, max(1.5, 3.4 * g), "aq_pad", "aq_leaf_l", notch=False)
    _roots(out, 0, 0, 0, 3, 5, rng)
    if st >= 3:
        x, y, z = _blade(out, 0, 0, 0, int(13 * g), 0, 0, "aq_stem")
        if st == 4:
            _box(out, x - 1, y - 1, z + 1, 3, 3, 2, "aq_pod")           # the seed head
            _box(out, x - 1, y - 1, z + 3, 3, 3, 1, "aq_pod_d")
        else:
            for k in range(3):
                _flower(out, x, y, z + 1 + k, 2 - (k == 2), "aq_pink" if k < 2 else "aq_pink_d", "aq_yellow")


def duckweed(out, g, st, rng):
    r = max(3, int(10 * g))
    for _ in range(int(60 * g * g) + 6):
        a, d = rng.random() * 6.28, rng.random() ** .6 * r
        _put(out, d * math.cos(a), d * math.sin(a), 0, rng.choice(("aq_leaf_l", "aq_lettuce", "aq_leaf")))


def water_fern(out, g, st, rng):
    r = max(3, int(9 * g))
    for _ in range(int(55 * g * g) + 6):
        a, d = rng.random() * 6.28, rng.random() ** .6 * r
        _put(out, d * math.cos(a), d * math.sin(a), 0, "aq_fern_r" if (st >= 4 and rng.random() < .6) else "aq_leaf")


def water_hyacinth(out, g, st, rng):
    for i in range(max(2, int(7 * g))):
        a = i * 0.9
        _ball(out, 1.5 * math.cos(a), 1.5 * math.sin(a), 1, 1.1, "aq_leaf_l")                        # swollen float stalks
        _blade(out, 2 * math.cos(a), 2 * math.sin(a), 2, int(4 * g) + 1, 0.3 * math.cos(a), 0.3 * math.sin(a), "aq_leaf", width=2)
    _roots(out, 0, 0, 0, 5, int(6 * g) + 2, rng, "aq_cob")
    if st >= 3:
        x, y, z = _blade(out, 0, 0, 1, int(9 * g), 0, 0, "aq_stem")
        for k in range(4):
            _box(out, x - 1, y - 1, z - k, 3, 3, 1, "aq_purple" if k % 2 == 0 else "aq_blue")


def water_lettuce(out, g, st, rng):
    for i in range(max(3, int(8 * g))):
        a = i * 0.8
        for k in range(max(2, int(5 * g))):
            _put(out, k * math.cos(a), k * math.sin(a), k // 2, "aq_lettuce" if k % 2 else "aq_leaf_l")
            _put(out, k * math.cos(a) + 1, k * math.sin(a), k // 2, "aq_lettuce")
    _roots(out, 0, 0, 0, 6, int(5 * g) + 2, rng, "aq_white")


def frogbit(out, g, st, rng):
    for i in range(max(2, int(9 * g))):
        a, d = rng.random() * 6.28, rng.uniform(0, 7 * g)
        _disc(out, d * math.cos(a), d * math.sin(a), 0, 1.4, "aq_pad", notch=False)
    if st >= 3:
        _flower(out, 0, 0, 1, 1, "aq_white", "aq_yellow")


def giant_waterlily(out, g, st, rng):
    _disc(out, 0, 0, 0, max(3, 13 * g), "aq_pad", "aq_pad_r", notch=False, ring="aq_pad_r")
    for i in range(int(2 * g)):
        _disc(out, (22 + 17 * i) * g, 4 * g * (1 if i % 2 else -1), 0, max(2, 8 * g), "aq_pad", "aq_pad_r", notch=False, ring="aq_pad_r")
    if st >= 3:
        _flower(out, -4 * g, -14 * g, 1, 3, "aq_white" if st == 3 else "aq_pink", "aq_yellow")
    _roots(out, 0, 0, 0, 4, 6, rng)


def cattail(out, g, st, rng):
    for i in range(max(3, int(9 * g))):
        a = rng.random() * 6.28
        _blade(out, rng.randint(-2, 2), rng.randint(-2, 2), 0, int(rng.uniform(14, 22) * g), 0.08 * math.cos(a), 0.08 * math.sin(a), "aq_blade", "aq_blade_y", curl=0.3)
    if st >= 3:
        for j in range(1 + int(2 * g)):
            x, y = rng.randint(-1, 1), rng.randint(-1, 1)
            _, _, z = _blade(out, x, y, 0, int(20 * g), 0, 0, "aq_stem")
            if st >= 4:
                _box(out, x, y, z - 5, 2, 2, 5, "aq_cob" if st == 4 else "aq_plume")          # the cob, fluffing at seed
                _blade(out, x, y, z, 3, 0, 0, "aq_blade_y")
    _box(out, -3, -3, -1, 7, 7, 1, "aq_mud")


def common_reed(out, g, st, rng):
    for i in range(max(3, int(11 * g))):
        x, y = rng.randint(-4, 4), rng.randint(-4, 4)
        h = int(rng.uniform(20, 32) * g)
        _, _, z = _blade(out, x, y, 0, h, 0, 0, "aq_stem")
        for k in range(3, h - 2, 4):
            _put(out, x + (1 if k % 8 else -1), y, k, "aq_blade")                               # leaves off the culm
            _put(out, x + (2 if k % 8 else -2), y, k - 1, "aq_blade")
        if st >= 4:
            _box(out, x, y, z - 2, 2, 1, 4, "aq_plume")
    _box(out, -5, -5, -1, 11, 11, 1, "aq_mud")


def papyrus(out, g, st, rng):
    for i in range(max(2, int(7 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        _, _, z = _blade(out, x, y, 0, int(rng.uniform(18, 28) * g), 0, 0, "aq_stem")
        n = max(4, int(10 * g))
        for k in range(n):                                                                      # the umbrella head
            a = k / n * 6.28
            for j in range(1, max(2, int(4 * g)) + 1):
                _put(out, x + j * math.cos(a), y + j * math.sin(a), z + 1 - j // 3, "aq_leaf_l" if st < 4 else "aq_blade_y")
    _box(out, -4, -4, -1, 9, 9, 1, "aq_mud")


def bulrush(out, g, st, rng):
    for i in range(max(3, int(10 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        _, _, z = _blade(out, x, y, 0, int(rng.uniform(12, 20) * g), 0.04 * rng.choice((-1, 1)), 0, "aq_leaf_d")
        if st >= 3 and rng.random() < .5:
            _box(out, x, y, z - 2, 2, 1, 2, "aq_cob")


def horsetail(out, g, st, rng):
    for i in range(max(3, int(8 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        h = int(rng.uniform(10, 16) * g)
        for k in range(h):
            _put(out, x, y, k, "aq_band" if k % 3 == 2 else "aq_horse")                       # jointed segments
            if k % 3 == 2 and k < h - 2:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    _put(out, x + dx, y + dy, k - 1, "aq_horse")
        if st >= 4:
            _box(out, x, y, h, 1, 1, 2, "aq_cob")


def arrowhead(out, g, st, rng):
    for i in range(max(2, int(6 * g))):
        a = i * 1.05
        x, y, z = _blade(out, 0, 0, 0, int(9 * g) + 2, 0.2 * math.cos(a), 0.2 * math.sin(a), "aq_stem")
        for k in range(max(2, int(4 * g))):                                                     # the arrow: tip + two barbs
            _box(out, x - k // 2, y, z + k, 1 + k, 1, 1, "aq_leaf")
        _put(out, x - 2, y, z - 1, "aq_leaf")
        _put(out, x + 2, y, z - 1, "aq_leaf")
    if st >= 3:
        x, y, z = _blade(out, 1, 1, 0, int(12 * g), 0, 0, "aq_stem")
        for k in range(3):
            _flower(out, x, y, z - 2 * k, 1, "aq_white", "aq_yellow", cup=False)


def pickerelweed(out, g, st, rng):
    for i in range(max(2, int(6 * g))):
        a = i * 1.05
        x, y, z = _blade(out, 0, 0, 0, int(8 * g) + 2, 0.18 * math.cos(a), 0.18 * math.sin(a), "aq_stem")
        _disc(out, x, y, z, 2.2, "aq_leaf", notch=False)
    if st >= 3:
        x, y, z = _blade(out, 0, 0, 0, int(13 * g), 0, 0, "aq_stem")
        _box(out, x - 1, y - 1, z - 4, 2, 2, 5, "aq_blue" if st < 5 else "aq_pod")


def yellow_iris(out, g, st, rng):
    for i in range(max(3, int(8 * g))):
        a = (i - 4) * 0.12
        _blade(out, i - 4, 0, 0, int(rng.uniform(12, 18) * g), a, 0, "aq_leaf", width=1)        # a fan of swords
    if st >= 3:
        for j in range(1 + int(g)):
            x, y, z = _blade(out, j * 2 - 1, 1, 0, int(16 * g), 0, 0, "aq_stem")
            if st == 4 or st == 6:
                _flower(out, x, y, z, 2, "aq_yellow", "aq_marig")
                _put(out, x, y + 2, z - 1, "aq_yellow")
                _put(out, x, y - 2, z - 1, "aq_yellow")
            elif st == 5:
                _box(out, x, y, z - 2, 1, 1, 3, "aq_pod")


def marsh_marigold(out, g, st, rng):
    for i in range(max(3, int(9 * g))):
        a = i * 0.7
        x, y, z = _blade(out, 0, 0, 0, int(4 * g) + 1, 0.4 * math.cos(a), 0.4 * math.sin(a), "aq_stem")
        _disc(out, x, y, z, 1.8, "aq_leaf_d", notch=False)
    if st >= 3:
        for i in range(max(2, int(6 * g))):
            a = rng.random() * 6.28
            _flower(out, 2 * math.cos(a), 2 * math.sin(a), int(5 * g) + 2, 1, "aq_marig", "aq_yellow")


def wild_rice(out, g, st, rng):
    for i in range(max(3, int(12 * g))):
        x, y = rng.randint(-4, 4), rng.randint(-4, 4)
        _, _, z = _blade(out, x, y, 0, int(rng.uniform(16, 24) * g), 0.05, 0.02, "aq_blade", curl=0.25)
        if st >= 4:
            for k in range(4):
                _put(out, x + 1 + k // 2, y, z - k, "aq_rice")


def tape_grass(out, g, st, rng):
    for i in range(max(3, int(12 * g))):
        x, y = rng.randint(-4, 4), rng.randint(-4, 4)
        h = int(rng.uniform(14, 26) * g)
        ph = rng.random() * 6.28
        for k in range(h):
            _put(out, x + round(math.sin(k * .35 + ph) * 1.2), y, k, "aq_seagrass" if k % 5 else "aq_leaf_l")
    _box(out, -5, -5, -1, 11, 11, 1, "aq_mud")


def hornwort(out, g, st, rng):
    for i in range(max(2, int(5 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        h = int(rng.uniform(12, 20) * g)
        for k in range(h):
            _put(out, x, y, k, "aq_leaf_d")
            if k % 2 == 0:                                                                     # whorls of needles
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
                    if rng.random() < .7:
                        _put(out, x + dx * (1 + (k % 4 == 0)), y + dy * (1 + (k % 4 == 0)), k + 1, "aq_moss")


def waterweed(out, g, st, rng):
    for i in range(max(2, int(6 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        h = int(rng.uniform(10, 18) * g)
        for k in range(h):
            _put(out, x, y, k, "aq_leaf")
            for dx, dy in ((1, 0), (-1, 0), (0, 1)):
                if (k + dx) % 2 == 0:
                    _put(out, x + dx, y + dy, k, "aq_leaf_l")
        if st == 4:
            _put(out, x, y, h, "aq_white")


def cabomba(out, g, st, rng):
    for i in range(max(2, int(5 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        h = int(rng.uniform(12, 18) * g)
        for k in range(h):
            _put(out, x, y, k, "aq_stem")
            if k % 3 == 1:
                for j in range(-2, 3):                                                         # fan-shaped leaves
                    _put(out, x + j, y + abs(j) // 2, k + abs(j) // 2, "aq_leaf_l")
        if st == 4:
            _flower(out, x, y, h, 1, "aq_white", "aq_yellow")


def amazon_sword(out, g, st, rng):
    for i in range(max(3, int(10 * g))):
        a = i * 0.63
        l = int(rng.uniform(7, 11) * g) + 2
        for k in range(l):
            w = 2 if 2 < k < l - 2 else 1
            _box(out, k * math.cos(a) * .7, k * math.sin(a) * .7, k * .9, w, 1, 1, "aq_leaf" if k % 4 else "aq_leaf_l")
    _box(out, -2, -2, -1, 5, 5, 1, "aq_mud")


def java_fern(out, g, st, rng):
    _box(out, -4, -1, 0, 8, 2, 1, "aq_cob")                                                   # rhizome on a stone
    _box(out, -5, -2, -2, 10, 4, 2, "stone" if "stone" in PAL else "aq_mud")
    for i in range(max(3, int(9 * g))):
        x = -4 + i % 8
        _blade(out, x, 0, 1, int(rng.uniform(6, 10) * g) + 1, rng.uniform(-.2, .2), rng.uniform(-.3, .3), "aq_leaf_d", "aq_cob" if st >= 5 else None, width=2, curl=.2)


def anubias(out, g, st, rng):
    _box(out, -3, -1, 0, 6, 2, 1, "aq_cob")
    for i in range(max(2, int(6 * g))):
        a = i * 1.05
        x, y, z = _blade(out, 0, 0, 1, int(4 * g) + 1, 0.3 * math.cos(a), 0.3 * math.sin(a), "aq_stem")
        _disc(out, x, y, z, 1.8 * max(.8, g), "aq_leaf_d", notch=False)
    if st == 4:
        _blade(out, 0, 0, 1, 6, 0, 0, "aq_stem", "aq_white")


def milfoil(out, g, st, rng):
    for i in range(max(2, int(6 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        h = int(rng.uniform(14, 22) * g)
        for k in range(h):
            _put(out, x, y, k, "aq_fern_r" if k > h - 3 else "aq_stem")
            if k % 2:
                for dx in (-2, -1, 1, 2):
                    _put(out, x + dx, y, k + (abs(dx) == 2), "aq_leaf_l")                      # feathery whorls


def pondweed(out, g, st, rng):
    for i in range(max(2, int(5 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        x2, y2, z = _blade(out, x, y, 0, int(rng.uniform(10, 16) * g), 0.05, 0, "aq_stem")
        for k in range(2, int(z), 4):
            _box(out, x + 1, y, k, 2, 1, 2, "aq_leaf")
        _box(out, x2 - 1, y2 - 1, z + 1, 3, 2, 1, "aq_leaf_l")                                 # floating leaf at the top
        if st >= 4:
            _box(out, x2, y2, z + 2, 1, 1, 2, "aq_cob")


def moss_ball(out, g, st, rng):
    for i in range(max(1, int(3 * g))):
        r = max(1.5, rng.uniform(2.2, 3.5) * g)
        cx = i * 7 - 7
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            for y in range(int(-r) - 1, int(r) + 2):
                for z in range(0, int(2 * r) + 2):
                    if (x + .5 - cx) ** 2 + (y + .5) ** 2 + (z + .5 - r) ** 2 <= r * r:
                        _put(out, x, y, z, "aq_moss" if (x + y + z) % 3 else "aq_leaf")


def giant_kelp(out, g, st, rng):
    _box(out, -3, -3, 0, 6, 6, 2, "aq_kelp_d")                                                 # holdfast
    for i in range(max(2, int(5 * g))):
        x, y = rng.randint(-2, 2), rng.randint(-2, 2)
        h = int(rng.uniform(30, 60) * g)
        ph = rng.random() * 6.28
        for k in range(2, h):
            px = x + round(math.sin(k * .08 + ph) * 2)
            _put(out, px, y, k, "aq_kelp_d")
            if k % 4 == 0:                                                                     # bladder + blade pairs
                side = 1 if (k // 4) % 2 else -1
                _put(out, px + side, y, k, "aq_float")
                for j in range(2, 6):
                    _put(out, px + side * j, y, k + j // 2, "aq_kelp" if j < 5 else "aq_kelp_l")
        if st >= 5:
            for j in range(6):
                _put(out, x + j - 3, y, h + (1 if j % 2 else 0), "aq_kelp_l")                  # the canopy at the surface


def bull_kelp(out, g, st, rng):
    _box(out, -2, -2, 0, 4, 4, 2, "aq_kelp_d")
    h = int(40 * g) + 4
    _blade(out, 0, 0, 2, h, 0.03, 0, "aq_kelp_d")
    top = (int(0.03 * h), 0, h + 2)
    _ball(out, top[0], 0, top[2], max(1.2, 2.2 * g), "aq_float")
    for i in range(max(3, int(8 * g))):
        a = i * 0.8
        for k in range(int(12 * g) + 3):
            _put(out, top[0] + k * math.cos(a) * .8, k * math.sin(a) * .8, top[2] - k // 3, "aq_kelp" if k % 3 else "aq_kelp_l")


def seagrass(out, g, st, rng):
    for i in range(max(5, int(26 * g))):
        x, y = rng.randint(-6, 6), rng.randint(-6, 6)
        _blade(out, x, y, 0, int(rng.uniform(6, 14) * g) + 1, rng.uniform(-.1, .1), rng.uniform(-.1, .1), "aq_seagrass", "aq_leaf_l", curl=.3)
    _box(out, -7, -7, -1, 15, 15, 1, "sand" if "sand" in PAL else "aq_mud")


def sea_lettuce(out, g, st, rng):
    for i in range(max(2, int(6 * g))):
        a = i * 1.05
        for k in range(int(6 * g) + 2):
            for w in range(-1, 2):
                _put(out, k * math.cos(a) + w * math.sin(a), k * math.sin(a) - w * math.cos(a), k // 2 + (w == 0 and k % 2), "aq_sea_l")


def bladderwrack(out, g, st, rng):
    _box(out, -1, -1, 0, 2, 2, 1, "aq_kelp_d")
    def branch(x, y, z, a, n, depth):
        for k in range(n):
            x, y, z = x + math.cos(a) * .6, y + math.sin(a) * .3, z + 1
            _put(out, x, y, z, "aq_wrack")
            if k % 3 == 1:
                _put(out, x + 1, y, z, "aq_float")                                             # the air bladders
        if depth:
            branch(x, y, z, a + .6, max(2, n - 2), depth - 1)
            branch(x, y, z, a - .6, max(2, n - 2), depth - 1)
    branch(0, 0, 0, 1.57, int(6 * g) + 2, 2 if g > .6 else 1)


def sargassum(out, g, st, rng):
    r = max(3, int(9 * g))
    for _ in range(int(40 * g * g) + 8):
        a, d = rng.random() * 6.28, rng.random() ** .7 * r
        x, y = d * math.cos(a), d * math.sin(a)
        _put(out, x, y, 0, "aq_sarg")
        if rng.random() < .3:
            _put(out, x, y, 1, "aq_float")
        if rng.random() < .3:
            _put(out, x, y, -1, "aq_sarg")


def sea_palm(out, g, st, rng):
    _box(out, -2, -2, 0, 4, 4, 1, "aq_kelp_d")
    for i in range(max(1, int(4 * g))):
        x, y, z = _blade(out, i * 2 - 2, 0, 1, int(rng.uniform(8, 13) * g) + 2, 0.05 * (i - 1), 0, "aq_kelp")
        for j in range(8):
            a = j / 8 * 6.28
            for k in range(1, 4):
                _put(out, x + k * math.cos(a) * .7, y + k * math.sin(a) * .7, z - k + 1, "aq_kelp_l")


def red_dulse(out, g, st, rng):
    for i in range(max(2, int(7 * g))):
        a = rng.random() * 6.28
        x, y, z = 0, 0, 0
        for k in range(int(8 * g) + 3):
            x, y, z = x + math.cos(a) * .4, y + math.sin(a) * .4, z + 1
            w = 2 if 2 < k < 7 else 1
            _box(out, x, y, z, w, 1, 1, "aq_dulse")
            a += rng.uniform(-.3, .3)


def rillprism_reed(out, g, st, rng):
    """RingInfusion's cool herb (rillprism) as it grows: reeds whose tips crystallise into prisms."""
    for i in range(max(3, int(8 * g))):
        x, y = rng.randint(-3, 3), rng.randint(-3, 3)
        _, _, z = _blade(out, x, y, 0, int(rng.uniform(12, 18) * g), 0, 0, "aq_blade")
        if st >= 3:
            _box(out, x, y, z + 1, 1, 1, 2 + (st >= 4), "aq_prism" if i % 2 else "aq_prism2")
            if st >= 4:
                _put(out, x + 1, y, z + 1, "aq_prism")
                _put(out, x - 1, y, z + 1, "aq_prism2")
    _box(out, -4, -4, -1, 9, 9, 1, "aq_mud")


def filter_moss(out, g, st, rng):
    """Cleans a spring: island_chemistry water.filter_needed islands plant it at the well and the filter hut."""
    r = max(3, int(8 * g))
    for x in range(-r, r + 1):
        for y in range(-r, r + 1):
            if x * x + y * y <= r * r:
                h = 1 + ((x * 3 + y * 5) % 3 == 0) + (st >= 3 and (x * 7 + y) % 5 == 0)
                for z in range(h):
                    _put(out, x, y, z, "aq_filter" if z == 0 else "aq_moss")
                if st >= 4 and (x + 2 * y) % 7 == 0:
                    _put(out, x, y, h, "aq_filter2")                                          # glowing filter beads


def glowkelp(out, g, st, rng):
    for i in range(max(2, int(4 * g))):
        x, y = rng.randint(-2, 2), rng.randint(-2, 2)
        h = int(rng.uniform(18, 30) * g)
        ph = rng.random() * 6.28
        for k in range(h):
            px = x + round(math.sin(k * .15 + ph) * 1.5)
            _put(out, px, y, k, "aq_glow" if (k % 6 == 5 or k > h - 3) else "aq_glow2" if k % 2 else "aq_kelp_d")
            if k % 5 == 2:
                _put(out, px + 1, y, k, "aq_glow2")


def skylily(out, g, st, rng):
    """Floats on the sky rivers: pale pads, petals drifting up off the flower."""
    for i in range(max(1, int(4 * g))):
        a = rng.random() * 6.28
        d = 0 if i == 0 else rng.uniform(3, 8 * g)
        _disc(out, d * math.cos(a), d * math.sin(a), 0, max(1.5, 3 * g), "aq_sky", "aq_white")
    if st >= 3:
        _flower(out, 0, 0, 1, 2, "aq_white", "aq_prism")
        if st >= 4:
            for k in range(5):
                _put(out, rng.randint(-3, 3), rng.randint(-3, 3), 4 + k * 2, "aq_sky")


def ember_lotus(out, g, st, rng):
    """Volcano islands' hot springs: dark pads, a flame-coloured flower."""
    for i in range(max(1, int(4 * g))):
        a = i * 1.6
        _disc(out, 4 * g * math.cos(a), 4 * g * math.sin(a), 0, max(1.5, 3 * g), "aq_pad_d", "aq_pad_r", notch=False)
    if st >= 3:
        x, y, z = _blade(out, 0, 0, 0, int(9 * g), 0, 0, "aq_pad_r")
        for k in range(3):
            _flower(out, x, y, z + k, 2 - (k == 2), "aq_ember" if k < 2 else "aq_ember2", "aq_ember2")


def frost_fern(out, g, st, rng):
    """Frost islands' meltwater pools: frond tips rimed with ice."""
    for i in range(max(3, int(8 * g))):
        a = i * 0.78
        _blade(out, 0, 0, 0, int(rng.uniform(7, 11) * g) + 1, 0.35 * math.cos(a), 0.35 * math.sin(a), "aq_frost2", "aq_frost", curl=.3)
    if st >= 4:
        _ball(out, 0, 0, 1, 1.3, "aq_frost")


SPECIES = {
    # name: (family, builder, voxel cm, uses)
    "WaterLily":      ("pond", water_lily, 5.0, {"fish": ["rillperch", "glassfin"], "cover": "frogs, fry", "goods": ["lily_root@inn"], "islands": ["meadow", "mire", "crystal"]}),
    "PinkLily":       ("pond", pink_lily, 5.0, {"fish": ["ember_koi"], "cover": "frogs", "goods": ["dye_pink@craft"], "islands": ["meadow", "mire"]}),
    "Lotus":          ("pond", lotus, 5.0, {"fish": ["ember_koi"], "goods": ["lotus_seed@inn", "shrine_offering@shrine"], "islands": ["meadow", "mesa"]}),
    "Duckweed":       ("pond", duckweed, 5.0, {"fish": ["rillperch"], "livestock": "hen feed@kennel", "purity": -0.05, "islands": ["mire"]}),
    "WaterFern":      ("pond", water_fern, 5.0, {"soil": "+fertility when composted (nitrogen)", "islands": ["mire", "meadow"]}),
    "WaterHyacinth":  ("pond", water_hyacinth, 5.0, {"purity": 0.08, "spreads": True, "goods": ["fibre@craft"], "islands": ["mire"]}),
    "WaterLettuce":   ("pond", water_lettuce, 5.0, {"purity": 0.05, "cover": "fry", "islands": ["mire", "meadow"]}),
    "Frogbit":        ("pond", frogbit, 5.0, {"cover": "frogs", "islands": ["meadow", "frost"]}),
    "GiantWaterLily": ("pond", giant_waterlily, 10.0, {"walkable": "a small pad carries a child-size avatar", "fish": ["glassfin"], "islands": ["meadow", "crystal"]}),
    "Cattail":        ("marsh", cattail, 5.0, {"purity": 0.06, "goods": ["reed_mat@craft", "torch_fluff@craft"], "cover": "nesting birds", "islands": ["mire", "meadow", "frost"]}),
    "CommonReed":     ("marsh", common_reed, 5.0, {"purity": 0.10, "goods": ["thatch@build", "reed_pipe@craft"], "islands": ["mire", "meadow"]}),
    "Papyrus":        ("marsh", papyrus, 5.0, {"goods": ["paper@ledger", "boat_reed@dock"], "islands": ["mesa", "volcano"]}),
    "Bulrush":        ("marsh", bulrush, 5.0, {"purity": 0.06, "goods": ["basket@craft"], "islands": ["mire"]}),
    "Horsetail":      ("marsh", horsetail, 5.0, {"goods": ["scouring_rush@smithy (polish)"], "islands": ["mire", "frost"]}),
    "Arrowhead":      ("marsh", arrowhead, 5.0, {"goods": ["duck_potato@inn"], "islands": ["meadow", "mire"]}),
    "Pickerelweed":   ("marsh", pickerelweed, 5.0, {"bees": "nectar@hive", "islands": ["meadow"]}),
    "YellowIris":     ("marsh", yellow_iris, 5.0, {"purity": 0.04, "goods": ["dye_yellow@craft"], "islands": ["meadow", "mire"]}),
    "MarshMarigold":  ("marsh", marsh_marigold, 5.0, {"bees": "early nectar@hive", "islands": ["frost", "mire"]}),
    "WildRice":       ("marsh", wild_rice, 5.0, {"crop": "wild_rice -> skyfarer_ration@inn", "islands": ["mire", "meadow"]}),
    "TapeGrass":      ("submerged", tape_grass, 5.0, {"fish": ["rillperch", "skytrout"], "purity": 0.04, "islands": ["meadow", "crystal"]}),
    "Hornwort":       ("submerged", hornwort, 5.0, {"purity": 0.06, "cover": "fry", "islands": ["meadow", "mire", "frost"]}),
    "Waterweed":      ("submerged", waterweed, 5.0, {"purity": 0.05, "fish": ["glassfin"], "islands": ["meadow"]}),
    "Cabomba":        ("submerged", cabomba, 5.0, {"fish": ["ember_koi"], "islands": ["volcano", "meadow"]}),
    "AmazonSword":    ("submerged", amazon_sword, 5.0, {"fish": ["glassfin", "ember_koi"], "islands": ["meadow", "crystal"]}),
    "JavaFern":       ("submerged", java_fern, 5.0, {"grows_on": "stones by waterfalls", "islands": ["crystal", "mesa"]}),
    "Anubias":        ("submerged", anubias, 5.0, {"grows_on": "driftwood", "islands": ["meadow", "mire"]}),
    "Milfoil":        ("submerged", milfoil, 5.0, {"fish": ["skytrout"], "cover": "fry", "islands": ["frost", "meadow"]}),
    "Pondweed":       ("submerged", pondweed, 5.0, {"fish": ["rillperch"], "livestock": "duck feed", "islands": ["meadow", "mire"]}),
    "MossBall":       ("submerged", moss_ball, 5.0, {"purity": 0.03, "goods": ["luck_charm@shop"], "islands": ["frost", "crystal"]}),
    "GiantKelp":      ("sea", giant_kelp, 10.0, {"fish": ["sea fish (voxel_creatures FISH)"], "goods": ["kelp@inn", "iodine@brew"], "habitat": "ocean under the islands"}),
    "BullKelp":       ("sea", bull_kelp, 10.0, {"goods": ["kelp_rope@dock"], "habitat": "coastal islets"}),
    "Seagrass":       ("sea", seagrass, 5.0, {"fish": ["sea fish"], "sea": "turtle and manatee grazing (voxel_creatures SEA)", "habitat": "shallows"}),
    "SeaLettuce":     ("sea", sea_lettuce, 5.0, {"goods": ["salad@inn"], "habitat": "tide pools"}),
    "Bladderwrack":   ("sea", bladderwrack, 5.0, {"goods": ["tonic_salt@brew"], "habitat": "rocky shores"}),
    "Sargassum":      ("sea", sargassum, 5.0, {"floats": True, "cover": "juvenile fish", "habitat": "open sea"}),
    "SeaPalm":        ("sea", sea_palm, 5.0, {"habitat": "surf rocks"}),
    "RedDulse":       ("sea", red_dulse, 5.0, {"goods": ["dye_red@craft", "snack@inn"], "habitat": "rocky shores"}),
    "RillprismReed":  ("realm", rillprism_reed, 5.0, {"herb": "rillprism (cool essence) @RingInfusion", "purity": 0.05, "islands": ["crystal", "meadow"]}),
    "FilterMoss":     ("realm", filter_moss, 5.0, {"purity": 0.25, "mechanic": "island_chemistry water.filter_needed: plant at the well to skip the filter hut", "islands": ["all"]}),
    "Glowkelp":       ("realm", glowkelp, 5.0, {"light": "lights caves and night lakes", "fish": ["glassfin"], "goods": ["glow_dye@craft"], "islands": ["crystal"]}),
    "Skylily":        ("realm", skylily, 5.0, {"habitat": "sky rivers and waterfall pools", "fish": ["skytrout"], "goods": ["airship_charm@dock"], "islands": ["all"]}),
    "EmberLotus":     ("realm", ember_lotus, 5.0, {"herb": "pairs with cinderbud (warm)", "fish": ["ember_koi"], "islands": ["volcano"]}),
    "FrostFern":      ("realm", frost_fern, 5.0, {"herb": "pairs with clearbell (cool)", "islands": ["frost"]}),
}
FAMILY_TAG = {"pond": "Pond", "marsh": "Marsh", "submerged": "Sub", "sea": "Sea", "realm": "Realm"}
PIVOT = {"pond": "waterline", "marsh": "mud line (stand in 0-0.5 m water)", "submerged": "lake bed", "sea": "seabed", "realm": "waterline/bed"}

CATALOG = {}
_KEY = {}
for sp, (fam, fn, cm, uses) in SPECIES.items():
    for i, stg in enumerate(STAGES, 1):
        n = "Prop_Aquatic_%s_%s_%d" % (FAMILY_TAG[fam], sp, i)
        CATALOG[n] = (fam, cm)
        _KEY[n] = (sp, i)

NAMES = tuple(CATALOG)


def plan(name):
    sp, i = _KEY[name]
    fam, fn, cm, uses = SPECIES[sp]
    rng = random.Random(sum(map(ord, sp)) * 10 + i)
    out = []
    fn(out, GROW[i - 1], i, rng)
    seen = {}
    for x, y, z, c in out:
        seen[(x, y, z)] = c
    return [(x, y, z, c) for (x, y, z), c in seen.items()]


def manifest():
    return {"stages": list(STAGES), "families": {f: PIVOT[f] for f in FAMILY_TAG},
            "species": {sp: {"family": f, "voxel_cm": cm, "uses": u} for sp, (f, _, cm, u) in SPECIES.items()},
            "purity_note": "sum of 'purity' over plants placed in an island's spring/lake adds to island_chemistry water.spring_purity (cap 1.0); FilterMoss alone can lift a filter_needed island over 0.6",
            "count": len(CATALOG)}


def build(name, out_dir):
    import bpy
    voxels = plan(name)
    fam, cm = CATALOG[name]
    sp, st = _KEY[name]
    ob = V._mesh_from_voxels(name, voxels, scale=cm, pal=PAL)
    for o in bpy.data.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    zs = [z for _, _, z, _ in voxels]
    with open(out[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "species": sp, "family": fam, "stage": STAGES[st - 1], "stage_index": st, "voxel_cm": cm, "voxels": len(voxels),
                   "pivot": PIVOT[fam], "height_m": round((max(zs) + 1) * cm / 100, 2), "depth_below_pivot_m": round(-min(0, min(zs)) * cm / 100, 2),
                   "uses": SPECIES[sp][3], "source": "tools/blender/voxel_aquatic.py"}, f, indent=1)
    bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return out


def build_all(out_dir, families=None, force=False):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "aquatic.manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest(), f, indent=1)
    done = []
    for name, (fam, _) in CATALOG.items():
        if families and fam not in families:
            continue
        if not force and os.path.exists(os.path.join(out_dir, name + ".fbx")):
            continue
        done.append(build(name, out_dir))
    return done


if __name__ == "__main__":
    import sys
    miss, empty = set(), []
    for n in CATALOG:
        p = plan(n)
        if not p:
            empty.append(n)
        for *_, c in p:
            if c not in PAL:
                miss.add(c)
    print(len(SPECIES), "species;", len(CATALOG), "props; empty", empty, "missing", sorted(miss))
    sys.exit(1 if miss or empty else 0)
