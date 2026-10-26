# SPDX-License-Identifier: MIT
"""Rabbits and hares for Daedalus2 — 504 rigged voxel rabbits (12 breeds x 6 coats x 7 variants) on the shared
voxel_creatures rig, family "rabbit": Idle (nose twitch, ear flick) / Walk (hop) / Run (bounding sprint) /
Attack (thump-kick) / Hurt / Turn / Jump (binky) / Action (rear up to look). Registers in voxel_creatures.EXTRA;
species name = "rabbit_<breed>_<coat>_<nn>".

Built in 2.5 cm voxels (export with scale=2.5): an egg-shaped body with the haunch higher than the shoulder, a
round head with eyes on the SIDES (prey animal), long ears with pink insides (or lop ears hanging down), long flat
hind feet, small forepaws and a cotton tail. Breeds carry the real shapes: the lean long-legged jackrabbit with
huge ears, the big-footed snowshoe hare, the tiny short-eared dwarf, the giant, the fluffy angora, the lionhead
mane, the lop, and the patterned dutch, harlequin and himalayan coats. Coats: agouti, white, black, chocolate,
blue, fawn. Variants: size, eye colour, ear angle, nose blaze, fur tufts.

Ecology (island_chemistry): prey half of the wolf cycle (voxel_wolves). Rabbits graze the crop rows (turnip,
carrot, cabbage, barley) and raise the crop-raid chance when numbers pass the line; they dig warrens in meadow
and mire soil, are a food and pelt source, and are a Helpful pet at the kennel (parcels_creatures CloverRabbit).
"""
import random

import voxel_creatures as VC

box = VC.box
PAL = VC.PAL
PAL.update({
    "rab_agouti": (0.55, 0.43, 0.30), "rab_agouti_d": (0.38, 0.29, 0.20), "rab_agouti_t": (0.70, 0.58, 0.42), "rab_white": (0.97, 0.96, 0.94),
    "rab_black": (0.13, 0.12, 0.13), "rab_choc": (0.36, 0.22, 0.14), "rab_blue": (0.50, 0.52, 0.58), "rab_fawn": (0.88, 0.66, 0.38),
    "rab_cream": (0.94, 0.89, 0.78), "rab_snow_b": (0.62, 0.48, 0.32), "rab_point": (0.22, 0.18, 0.18), "rab_orange": (0.92, 0.55, 0.25),
    "rab_ear_in": (0.95, 0.68, 0.70), "rab_nose": (0.90, 0.55, 0.60), "rab_eye_k": (0.06, 0.05, 0.05), "rab_eye_r": (0.80, 0.15, 0.20),
    "rab_eye_b": (0.30, 0.18, 0.10), "rab_eye_l": (0.35, 0.55, 0.85), "rab_claw": (0.40, 0.35, 0.32), "rab_tail": (0.99, 0.99, 0.98),
})
BREEDS = {
    # breed: (size, body length, ear length, ear mode, hind foot, leg factor, fluff, pattern)
    "cottontail":  (1.00, 1.00, 1.00, "up",   1.0, 1.00, 0, None),
    "jackrabbit":  (1.25, 1.15, 1.70, "up",   1.3, 1.35, 0, None),
    "snowshoe":    (1.15, 1.05, 1.10, "up",   1.6, 1.10, 0, "snowshoe"),
    "arctic_hare": (1.30, 1.10, 0.90, "up",   1.4, 1.10, 1, None),
    "lop":         (1.05, 1.00, 1.30, "lop",  1.0, 0.95, 0, None),
    "dutch":       (0.95, 0.95, 0.95, "up",   1.0, 1.00, 0, "dutch"),
    "angora":      (1.10, 1.00, 0.90, "up",   1.0, 0.90, 2, None),
    "lionhead":    (0.90, 0.95, 0.70, "up",   0.9, 0.95, 1, "mane"),
    "giant":       (1.55, 1.15, 1.10, "up",   1.2, 1.00, 0, None),
    "dwarf":       (0.70, 0.85, 0.55, "up",   0.8, 0.90, 0, None),
    "harlequin":   (1.00, 1.00, 1.00, "up",   1.0, 1.00, 0, "harlequin"),
    "himalayan":   (0.95, 1.05, 0.90, "up",   1.0, 1.00, 0, "points"),
}
COATS = {  # coat: (main, dark, light)
    "agouti": ("rab_agouti", "rab_agouti_d", "rab_agouti_t"), "white": ("rab_white", "rab_cream", "rab_white"),
    "black": ("rab_black", "rab_black", "rab_blue"), "chocolate": ("rab_choc", "rab_black", "rab_fawn"),
    "blue": ("rab_blue", "rab_point", "rab_cream"), "fawn": ("rab_fawn", "rab_orange", "rab_cream"),
}
EYES = ("rab_eye_k", "rab_eye_b", "rab_eye_l", "rab_eye_k")
VARIANTS = 7
VOXEL_CM = 2.5
ECOLOGY = {
    "family": "rabbit", "role": "prey / grazer", "predators": ["wolf", "owl", "fox"],
    "eats": ["turnip", "carrot", "cabbage", "barley", "dawnleaf", "clover"],
    "warren": {"soil": ["meadow", "mire", "parcels"], "per_island": [1, 3], "litter": [3, 8], "breed_days": 3},
    "crop_raid": {"line": 12, "note": "above 12 rabbits on an island each crop row loses yield unless a fence, a guard wolf or an owl roost is near"},
    "islands": {"meadow": 1.0, "mire": 0.6, "frost": 0.5, "mesa": 0.3, "crystal": 0.3, "volcano": 0.05},
    "cycle": "Lotka-Volterra with voxel_wolves; r-selected (big litters, short lives) vs the K-selected wolves",
    "kennel": {"pet": "Helpful pet (parcels_creatures CloverRabbit)", "job": "finds herbs: +1 herb pick per day"},
    "drops": {"meat": "stew@inn", "pelt": "craft@tannery", "foot": "luck charm@shop"},
}


def names():
    return tuple("rabbit_%s_%s_%02d" % (b, c, v) for b in BREEDS for c in COATS for v in range(1, VARIANTS + 1))


def spec(species):
    rest = species[len("rabbit_"):]
    breed = next(b for b in sorted(BREEDS, key=len, reverse=True) if rest.startswith(b + "_"))
    coat, v = rest[len(breed) + 1:].rsplit("_", 1)
    v = int(v)
    bi, ci = list(BREEDS).index(breed), list(COATS).index(coat)
    rng = random.Random(bi * 1000 + ci * 10 + v)
    size, blen, ear, mode, foot, legf, fluff, pattern = BREEDS[breed]
    main, dark, light = COATS[coat]
    if breed in ("arctic_hare",) and coat == "agouti":
        main, dark, light = "rab_white", "rab_cream", "rab_white"
    eye = "rab_eye_r" if (coat == "white" and v % 3 == 0) else EYES[(v + bi) % 4]
    return {
        "breed": breed, "coat": coat, "variant": v, "main": main, "dark": dark, "light": light,
        "size": size * (0.9 + 0.2 * rng.random()), "blen": blen, "ear": ear * (0.9 + 0.2 * rng.random()), "ear_mode": mode,
        "ear_splay": rng.randint(0, 1) if mode == "up" else 0, "foot": foot, "leg": legf, "fluff": fluff, "pattern": pattern,
        "eye": eye, "blaze": rng.random() < 0.25, "seed": rng.random(),
    }


def _ellipsoid(out, bone, cx, cy, cz, rx, ry, rz, colour_fn):
    for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for z in range(int(cz - rz) - 1, int(cz + rz) + 2):
                if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 + ((z + .5 - cz) / rz) ** 2 <= 1.0:
                    out.setdefault(bone, []).append((x, y, z, colour_fn(x, y, z)))


def plan(species):
    """Voxel plan per bone (2.5 cm voxels). Faces +Y, feet at z=0. A sitting-ready crouch, haunch up."""
    o = spec(species)
    s = o["size"]
    out = {}
    main, dark, light = o["main"], o["dark"], o["light"]
    rng = random.Random(int(o["seed"] * 1e6))
    pat = o["pattern"]
    lift = max(2, int(2 * s * o["leg"]))                       # belly clearance
    rx, ry, rz = 4.2 * s + o["fluff"] * .6, 7.5 * s * o["blen"] + o["fluff"] * .5, 4.8 * s + o["fluff"] * .5
    cy, cz = 0.0, lift + rz

    def body_col(x, y, z):
        t = (y - (cy - ry)) / (2 * ry)                         # 0 rump .. 1 chest
        if z < lift + 2.0:
            return light                                       # pale belly
        if pat == "dutch":
            return "rab_white" if t > 0.55 else main
        if pat == "harlequin":
            return main if (int(y // 3) + (x > 0)) % 2 else ("rab_orange" if main != "rab_orange" else "rab_black")
        if pat == "points":
            return "rab_white"
        if pat == "snowshoe" and z < cz - 1:
            return "rab_white"
        if z > cz + rz * .55:
            return dark                                        # darker saddle
        return main

    _ellipsoid(out, "body", 0, cy - ry * .15, cz + rz * .1, rx, ry * .85, rz, body_col)                  # haunch-heavy egg
    _ellipsoid(out, "body", 0, cy + ry * .45, cz - rz * .15, rx * .85, ry * .5, rz * .78, body_col)     # chest, lower
    # head: round, set forward and up
    hr = 3.6 * s + (0.5 if o["fluff"] else 0)
    hy, hz = cy + ry * .95, cz + rz * .55

    def head_col(x, y, z):
        if pat == "points" and y > hy + hr * .45:
            return "rab_point"                                # dark nose point
        if pat == "dutch" and abs(x) <= 1 and y > hy:
            return "rab_white"                                # dutch blaze
        if o["blaze"] and abs(x) == 0 and y > hy + hr * .3 and z > hz:
            return "rab_white"
        if z < hz - hr * .35 and y > hy:
            return light                                      # pale chin
        return main if pat not in ("points",) else "rab_white"

    _ellipsoid(out, "head", 0, hy, hz, hr * .9, hr, hr * .92, head_col)
    _ellipsoid(out, "head", 0, hy + hr * .75, hz - hr * .25, hr * .55, hr * .5, hr * .5, head_col)       # muzzle
    ny, nz = int(round(hy + hr * 1.2)), int(round(hz - hr * .15))
    box(out, "head", 0, ny, nz, 1, 1, 1, "rab_nose")
    box(out, "head", -1, ny, nz, 1, 1, 1, "rab_nose")
    ez = int(round(hz + hr * .2))
    ey = int(round(hy + hr * .25))
    ex = int(round(hr * .9))
    for sx in (-ex, ex - 1):                                                                          # eyes on the sides
        box(out, "head", sx, ey, ez, 1, 2, 2, o["eye"])
        box(out, "head", sx, ey + 1, ez + 1, 1, 1, 1, "eye_w")
    if pat == "mane":
        _ellipsoid(out, "head", 0, hy - hr * .4, hz, hr * 1.2, hr * .6, hr * 1.1, lambda x, y, z: light if main == "rab_white" else main)
    # ears
    el = max(4, int(9 * s * o["ear"]))
    ear_col = "rab_point" if pat == "points" else (dark if pat != "dutch" else main)
    ez0 = int(round(hz + hr * .7))
    ey0 = int(round(hy - hr * .3))
    for side in (-1, 1):
        x0 = 1 if side > 0 else -3
        if o["ear_mode"] == "lop":
            ll = max(3, int(el * 0.55))                                                              # lops hang to the jaw, not the ground
            for k in range(ll):
                x = (int(hr) - 1 + (1 if k > 0 else 0)) if side > 0 else -(int(hr) + 1 + (1 if k > 0 else 0))
                z = ez0 + 1 - k
                box(out, "head", x, ey0, z, 2, 3, 1, main if k < ll - 1 else dark)
            continue
        splay = o["ear_splay"] * (k_s := 1)
        for k in range(el):
            x = x0 + side * (k * splay // 3)
            y = ey0 - k // 4                                                                          # swept slightly back
            w = 2
            box(out, "head", x, y, ez0 + k, w, 1, 1, ear_col if k > el - 3 and pat != "dutch" else main)
            if 1 <= k < el - 1:
                box(out, "head", x + (1 if side < 0 else 0), y + 1, ez0 + k, 1, 1, 1, "rab_ear_in")
    # fluff tufts (angora)
    if o["fluff"] >= 2:
        for _ in range(18):
            x, y, z = rng.randint(-int(rx), int(rx)), rng.randint(int(cy - ry), int(cy + ry)), rng.randint(lift + 2, int(cz + rz))
            box(out, "body", x, y, z, 1, 1, 1, light)
    # legs: long flat hind feet under the haunch, small forepaws under the chest
    fl = max(4, int(7 * s * o["foot"]))
    fw = max(2, int(2 * s))
    hx = int(rx * .55)
    fur_feet = "rab_white" if pat in ("snowshoe", "points") or o["coat"] == "white" else light
    for bone, x in (("leg.L", -hx - fw + 1), ("leg.R", hx)):
        hy0 = int(cy - ry * .85)
        box(out, bone, x, hy0, 0, fw, fl, 1, fur_feet)                                                # hind foot, flat
        box(out, bone, x, hy0, 1, fw, max(3, fl // 2), max(2, lift + 1), main if pat != "points" else "rab_point")   # hock
        box(out, bone, x, hy0 + fl, 0, fw, 1, 1, "rab_claw")
        fy = int(cy + ry * .55)
        px = x + (1 if bone == "leg.L" else -1)
        box(out, bone, px, fy, 0, max(1, fw - 1), 2, max(2, lift + 2), light if pat != "points" else "rab_point")    # forelegs
        box(out, bone, px, fy + 2, 0, max(1, fw - 1), 1, 1, "rab_claw")
    # cotton tail, up at the back
    tr = max(1.4, 1.8 * s)
    _ellipsoid(out, "tail", 0, cy - ry * 1.0, cz + rz * .25, tr, tr, tr, lambda x, y, z: "rab_tail" if pat != "points" else "rab_point")
    return _last_wins(out)


def _last_wins(out):
    seen = {}
    for bone, vox in out.items():
        for x, y, z, c in vox:
            seen[(x, y, z)] = (bone, c)
    res = {}
    for (x, y, z), (bone, c) in seen.items():
        res.setdefault(bone, []).append((x, y, z, c))
    return res


NAMES = names()
VC.EXTRA["rabbit"] = (NAMES, plan)


def manifest():
    return {"ecology": ECOLOGY, "voxel_cm": VOXEL_CM, "rabbits": {n: {k: v for k, v in spec(n).items() if k != "seed"} for n in NAMES}}


if __name__ == "__main__":
    import sys
    miss, empty, hs = set(), [], set()
    for n in NAMES:
        p = plan(n)
        if not sum(len(v) for v in p.values()):
            empty.append(n)
        hs.add(hash(tuple(sorted((b, tuple(sorted(v))) for b, v in p.items()))))
        for v in p.values():
            for *_, c in v:
                if c not in PAL:
                    miss.add(c)
    print(len(NAMES), "rabbits;", len(hs), "unique; empty", empty, "missing", sorted(miss))
    sys.exit(1 if miss or empty or len(hs) != len(NAMES) else 0)
