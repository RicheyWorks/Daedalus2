# SPDX-License-Identifier: MIT
"""Flying dragons for Daedalus2 — 504 rigged voxel dragons (12 elements x 6 forms x 7 variants), on the shared
voxel_creatures rig (root/body/head/tail/leg.L/R/wing.L/R) with Idle (hover) / Walk (cruise) / Run (dive) / Attack /
Hurt / Turn / Jump (launch) / Action (breath) clips. Registers itself as the "dragon" family in voxel_creatures.EXTRA
so export_creatures.py / build() work unchanged:  species name = "dragon_<element>_<form>_<nn>".

Each dragon is deterministic from its name: the variant index seeds horns, tail tip, pattern, wing shape, size,
spines and extras, so the same name always rebuilds the same dragon (ADR-054 rule: nothing stored, everything replayable).

Elements (breath + colours):  fire ice storm earth forest shadow light crystal ocean lava poison gold
Forms:  wyvern (2 legs, big wings), classic (4 legs), serpent (long body, ribbon wings), drake (stocky, short wings),
        fairy (small, butterfly wings), elder (huge, double horns, crown spines)
Realm chemistry hook: an element matches a realm's power source / ores (fire~volcano, ice~frost, crystal~crystal,
ocean~mire/water, earth/forest~meadow, gold~LEGENDARY grade) — see island_chemistry.REALMS and the json "element".
"""
import random

import voxel_creatures as VC

box = VC.box
PAL = VC.PAL

ELEMENTS = {
    # element: (scale, belly, accent/breath, membrane, horn)
    "fire":    ("drg_red",    "drg_amber",  "drg_flame",  "drg_mem_r", "horn"),
    "ice":     ("drg_ice",    "drg_white",  "drg_frost",  "drg_mem_c", "drg_white"),
    "storm":   ("drg_slate",  "drg_grey",   "drg_bolt",   "drg_mem_g", "drg_grey"),
    "earth":   ("drg_brown",  "drg_sand",   "drg_rock",   "drg_mem_b", "horn"),
    "forest":  ("drg_green",  "drg_lime",   "drg_leaf",   "drg_mem_v", "drg_brown"),
    "shadow":  ("drg_black",  "drg_violet", "drg_void",   "drg_mem_k", "drg_black"),
    "light":   ("drg_white",  "drg_gold",   "drg_sun",    "drg_mem_w", "drg_gold"),
    "crystal": ("drg_pink",   "drg_white",  "drg_prism",  "drg_mem_p", "drg_prism"),
    "ocean":   ("drg_teal",   "drg_ice",    "drg_wave",   "drg_mem_t", "drg_white"),
    "lava":    ("drg_black",  "drg_flame",  "drg_magma",  "drg_mem_r", "drg_rock"),
    "poison":  ("drg_purple", "drg_lime",   "drg_toxic",  "drg_mem_v", "drg_black"),
    "gold":    ("drg_gold",   "drg_amber",  "drg_sun",    "drg_mem_y", "drg_white"),
}
PAL.update({
    "drg_red": (0.70, 0.15, 0.10), "drg_amber": (0.95, 0.65, 0.20), "drg_flame": (1.00, 0.45, 0.05), "drg_mem_r": (0.85, 0.35, 0.15),
    "drg_ice": (0.70, 0.88, 0.98), "drg_white": (0.95, 0.96, 0.98), "drg_frost": (0.80, 0.95, 1.00), "drg_mem_c": (0.55, 0.80, 0.95),
    "drg_slate": (0.35, 0.40, 0.50), "drg_grey": (0.60, 0.62, 0.68), "drg_bolt": (1.00, 0.95, 0.40), "drg_mem_g": (0.45, 0.50, 0.62),
    "drg_brown": (0.45, 0.30, 0.18), "drg_sand": (0.82, 0.72, 0.50), "drg_rock": (0.50, 0.48, 0.44), "drg_mem_b": (0.60, 0.45, 0.30),
    "drg_green": (0.20, 0.50, 0.22), "drg_lime": (0.65, 0.85, 0.30), "drg_leaf": (0.40, 0.75, 0.30), "drg_mem_v": (0.35, 0.60, 0.30),
    "drg_black": (0.10, 0.09, 0.12), "drg_violet": (0.40, 0.20, 0.55), "drg_void": (0.25, 0.05, 0.40), "drg_mem_k": (0.22, 0.18, 0.30),
    "drg_gold": (0.95, 0.78, 0.25), "drg_sun": (1.00, 0.95, 0.70), "drg_mem_w": (0.98, 0.95, 0.85), "drg_mem_y": (0.98, 0.85, 0.40),
    "drg_pink": (0.90, 0.55, 0.80), "drg_prism": (0.75, 0.90, 1.00), "drg_mem_p": (0.95, 0.75, 0.90),
    "drg_teal": (0.15, 0.55, 0.60), "drg_wave": (0.30, 0.75, 0.90), "drg_mem_t": (0.25, 0.65, 0.70),
    "drg_magma": (1.00, 0.30, 0.05), "drg_purple": (0.45, 0.15, 0.55), "drg_toxic": (0.55, 1.00, 0.20),
    "drg_eye": (1.00, 0.85, 0.10), "drg_claw": (0.90, 0.90, 0.80), "drg_fang": (0.98, 0.98, 0.92),
})
FORMS = {
    # form: (size, legs, body_len, neck_len, wing_span, wing_kind, horn_pairs, stocky)
    "wyvern":  (1.0, 2, 10, 4, 12, "bat", 1, False),
    "classic": (1.1, 4, 12, 5, 11, "bat", 1, False),
    "serpent": (0.9, 2, 20, 7, 7, "ribbon", 1, False),
    "drake":   (1.0, 4, 10, 2, 6, "bat", 1, True),
    "fairy":   (0.6, 2, 7, 3, 9, "butterfly", 1, False),
    "elder":   (1.6, 4, 14, 6, 15, "bat", 2, True),
}
HORNS = ("straight", "ram", "crown", "antler")
TAILS = ("spade", "fin", "club", "tuft")
PATTERNS = ("plain", "stripes", "spots", "plates", "gradient")
VARIANTS = 7


def names():
    return tuple("dragon_%s_%s_%02d" % (e, f, v) for e in ELEMENTS for f in FORMS for v in range(1, VARIANTS + 1))


def spec(species):
    _, element, form, var = species.split("_")
    var = int(var)
    rng = random.Random(list(ELEMENTS).index(element) * 1000 + list(FORMS).index(form) * 10 + var)
    size, legs, blen, nlen, span, wkind, horn_pairs, stocky = FORMS[form]
    return {
        "element": element, "form": form, "variant": var,
        "size": size * (0.85 + 0.3 * rng.random()),
        "legs": legs, "body_len": blen + rng.randint(-1, 2), "neck_len": nlen + rng.randint(-1, 1),
        "span": span + rng.randint(-1, 2), "wing_kind": wkind, "horn_pairs": horn_pairs,
        "horns": HORNS[(var + list(FORMS).index(form)) % len(HORNS)],
        "tail": TAILS[(var * 3 + list(ELEMENTS).index(element)) % len(TAILS)],
        "pattern": PATTERNS[(var * 2 + list(FORMS).index(form)) % len(PATTERNS)],
        "spines": rng.random() < 0.7, "beard": rng.random() < 0.3, "frill": rng.random() < 0.35,
        "stocky": stocky, "rng": rng.random(),
    }


def plan(species):
    """Voxel plan per bone (10 cm voxels). Faces +Y, feet at z=0, wings spread for flight."""
    sp = spec(species)
    scale_c, belly_c, accent_c, mem_c, horn_c = ELEMENTS[sp["element"]]
    s = sp["size"]
    out = {}
    W = max(4, int(6 * s) + (2 if sp["stocky"] else 0))
    D = max(6, int(sp["body_len"] * s))
    H = max(4, int(6 * s) + (1 if sp["stocky"] else 0))
    L = max(3, int(5 * s))
    # body
    box(out, "body", -W // 2, -D // 2, L, W, D, H, scale_c)
    box(out, "body", -W // 2 + 1, -D // 2 + 1, L, W - 2, D - 2, 1, belly_c)          # belly plates
    if sp["pattern"] == "stripes":
        for y in range(-D // 2, D // 2, 3):
            box(out, "body", -W // 2, y, L + H - 1, W, 1, 1, accent_c)
    elif sp["pattern"] == "spots":
        r = random.Random(int(sp["rng"] * 1e6))
        for _ in range(5 + int(D / 2)):
            box(out, "body", r.randint(-W // 2, W // 2 - 1), r.randint(-D // 2, D // 2 - 1), L + H - 1, 1, 1, 1, accent_c)
    elif sp["pattern"] == "plates":
        for y in range(-D // 2 + 1, D // 2 - 1, 2):
            box(out, "body", -1, y, L + H, 2, 1, 1, accent_c)
    elif sp["pattern"] == "gradient":
        box(out, "body", -W // 2, -D // 2, L + H - 2, W, D // 3, 2, accent_c)
    if sp["spines"]:
        for y in range(-D // 2 + 1, D // 2, 2):
            box(out, "body", 0, y, L + H, 1, 1, 2 if sp["form"] == "elder" else 1, horn_c)
    # neck + head (head bone): the neck rises forward from the body's front-top
    n = max(2, int(sp["neck_len"] * s))
    hw = max(3, int(4 * s))
    ny0 = D // 2 - 1
    for i in range(n):
        box(out, "head", -hw // 2 + 1, ny0 + i, L + H - 2 + i, hw - 2, 1, 3, scale_c)
    hz = L + H - 2 + n
    hy = ny0 + n
    box(out, "head", -hw // 2, hy - 1, hz, hw, hw, hw - 1, scale_c)                    # skull
    box(out, "head", -hw // 2 + 1, hy + hw - 1, hz, hw - 2, max(2, int(3 * s)), 2, scale_c)   # snout
    box(out, "head", -hw // 2 + 1, hy + hw - 1, hz, hw - 2, max(2, int(3 * s)), 1, belly_c)
    snout_end = hy + hw - 1 + max(2, int(3 * s))
    box(out, "head", -hw // 2 + 1, snout_end - 1, hz + 2, 1, 1, 1, "drg_fang")
    box(out, "head", hw // 2 - 1, snout_end - 1, hz + 2, 1, 1, 1, "drg_fang")
    box(out, "head", -1, snout_end, hz + 1, 2, 1, 1, "nose")
    for sx in (-hw // 2, hw // 2 - 1):
        box(out, "head", sx, hy + hw - 2, hz + hw - 3, 1, 1, 1, "drg_eye")
    # horns
    for pair in range(sp["horn_pairs"]):
        yb = hy + 1 - pair * 2
        for sx in (-hw // 2, hw // 2 - 1):
            if sp["horns"] == "straight":
                box(out, "head", sx, yb, hz + hw - 1, 1, 1, 3 + int(2 * s), horn_c)
            elif sp["horns"] == "ram":
                box(out, "head", sx, yb - 1, hz + hw - 2, 1, 3, 1, horn_c)
                box(out, "head", sx, yb - 1, hz + hw - 3, 1, 1, 2, horn_c)
            elif sp["horns"] == "crown":
                for k in range(3):
                    box(out, "head", sx, yb - k, hz + hw - 1, 1, 1, 2 + k, horn_c)
            else:   # antler
                box(out, "head", sx, yb, hz + hw - 1, 1, 1, 3, horn_c)
                box(out, "head", sx - (1 if sx < 0 else 0), yb, hz + hw + 1, 2, 1, 1, horn_c)
                box(out, "head", sx, yb - 1, hz + hw + 2, 1, 2, 1, horn_c)
    if sp["frill"]:
        box(out, "head", -hw // 2 - 1, hy - 2, hz, hw + 2, 1, hw + 1, mem_c)
    if sp["beard"]:
        box(out, "head", -1, hy + hw - 1, hz - 2, 2, 1, 2, accent_c)
    # legs
    leg_pos = [(-W // 2, -D // 2 + 1), (W // 2 - 2, -D // 2 + 1)] if sp["legs"] == 2 else \
              [(-W // 2, D // 2 - 3), (W // 2 - 2, D // 2 - 3), (-W // 2, -D // 2 + 1), (W // 2 - 2, -D // 2 + 1)]
    for sx, sy in leg_pos:
        bone = "leg.L" if sx < 0 else "leg.R"
        box(out, bone, sx, sy, 0, 2, 2, L, scale_c)
        box(out, bone, sx, sy + 2, 0, 2, 1, 1, "drg_claw")                           # fore-claws
        box(out, bone, sx - (1 if sx < 0 else 0), sy, 0, 3, 2, 1, scale_c)
    if sp["legs"] == 2:                                                              # wyverns grip with wing thumbs
        pass
    # wings (spread): a bat wing = arm bar + fingers + membrane; ribbon = long thin fins; butterfly = round lobes
    span = max(4, int(sp["span"] * s))
    wz = L + H - 1
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        x0 = W // 2 if sgn > 0 else -W // 2 - 1
        if sp["wing_kind"] == "bat":
            for i in range(span):                                                   # leading arm sweeps up and out
                x = x0 + sgn * i
                zi = wz + min(i, span // 2) // 2
                box(out, bone, x, D // 2 - 3, zi, 1, 2, 1, scale_c)
                depth = max(2, int((D - 2) * (1 - i / span)) + 2)                   # membrane trails back, tapering
                box(out, bone, x, D // 2 - 3 - depth, zi - 1, 1, depth, 1, mem_c)
                if i % 3 == 2:                                                      # finger bones
                    box(out, bone, x, D // 2 - 3 - depth, zi, 1, depth, 1, scale_c)
            box(out, bone, x0 + sgn * (span - 1), D // 2 - 2, wz + span // 4, 1, 1, 2, "drg_claw")   # wing claw
        elif sp["wing_kind"] == "ribbon":
            for i in range(span):
                x = x0 + sgn * i
                box(out, bone, x, -D // 2 + 1, wz - 1, 1, D - 2, 1, mem_c if i % 2 else accent_c)
        else:   # butterfly
            for i in range(span):
                x = x0 + sgn * i
                lobe = int((span - i) * 0.9) + 2
                box(out, bone, x, D // 2 - 2 - lobe, wz - 1, 1, lobe, 1, mem_c)
                box(out, bone, x, D // 2 - 2 - lobe, wz - 1, 1, 1, 1, accent_c)
                if i in (span // 3, 2 * span // 3):
                    box(out, bone, x, D // 2 - 2 - lobe // 2, wz - 1, 1, 1, 1, "drg_eye")   # eye spots
    # tail
    tl = max(5, int(sp["body_len"] * 0.8 * s))
    for i in range(tl):
        wdt = 2 if i < tl // 2 else 1
        box(out, "tail", -wdt // 2 if wdt == 2 else 0, -D // 2 - 1 - i, L + H - 2 - i // 3, wdt, 1, wdt, scale_c)
        if sp["spines"] and i % 2 == 0:
            box(out, "tail", 0, -D // 2 - 1 - i, L + H - 2 - i // 3 + wdt, 1, 1, 1, horn_c)
    ty, tz = -D // 2 - 1 - tl, L + H - 2 - tl // 3
    if sp["tail"] == "spade":
        box(out, "tail", -1, ty - 2, tz - 1, 3, 3, 1, accent_c)
        box(out, "tail", 0, ty - 3, tz, 1, 1, 1, accent_c)
    elif sp["tail"] == "fin":
        box(out, "tail", 0, ty - 3, tz - 1, 1, 4, 3, mem_c)
    elif sp["tail"] == "club":
        box(out, "tail", -1, ty - 2, tz - 1, 3, 3, 3, horn_c)
    else:
        box(out, "tail", -1, ty - 2, tz, 3, 2, 1, accent_c)
        box(out, "tail", 0, ty - 3, tz, 1, 1, 2, accent_c)
    return out


NAMES = names()
VC.EXTRA["dragon"] = (NAMES, plan)


def manifest():
    return {n: {k: v for k, v in spec(n).items() if k != "rng"} for n in NAMES}


if __name__ == "__main__":
    import sys
    miss, empty = set(), []
    for n in NAMES:
        p = plan(n)
        if not sum(len(v) for v in p.values()):
            empty.append(n)
        for v in p.values():
            for *_, c in v:
                if c not in PAL:
                    miss.add(c)
    print(len(NAMES), "dragons; empty", empty, "missing", sorted(miss))
    sys.exit(1 if miss or empty else 0)
