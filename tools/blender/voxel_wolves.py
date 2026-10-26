# SPDX-License-Identifier: MIT
"""Wolves for Daedalus2 — 504 rigged voxel wolves (12 kinds x 6 coats x 7 variants) on the shared voxel_creatures
rig, family "wolf": Idle (ears and tail alive) / Walk (trot) / Run (gallop) / Attack (lunge-snap) / Hurt / Turn /
Jump (pounce) / Action (howl). Registers in voxel_creatures.EXTRA; species name = "wolf_<kind>_<coat>_<nn>".

Built in 5 cm voxels (export with scale=5.0) so the silhouette reads as a wolf and not a dog-shaped box: a deep,
narrow chest that drops below the elbow, a tucked waist, the shoulder standing higher than the hip, a long muzzle
with a lighter mask, triangular ears, a neck ruff, hind legs with a visible hock, and a bushy tail carried low.

Kinds carry the real shapes: the big pale arctic and tundra wolves, the rangy long-legged maned wolf with its huge
ears and black stockings, the slim red Ethiopian-style highland wolf, the small rust-flanked red wolf. Coats
(classic, saddle, pale, melanistic, sable, frosted) and the variant (size, eye colour, tail carriage, ear size,
ruff, white socks, a torn ear) are deterministic from the name.

Ecology (island_chemistry): wolves are the predator half of the rabbit cycle (voxel_rabbits) — packs den on frost,
meadow and mesa islands, keep rabbit numbers below the crop-raid line, and can be tamed at the kennel (Kennel
tonics) as guard animals for the livestock pens. `ECOLOGY` carries the numbers the game reads.
"""
import random

import voxel_creatures as VC

box = VC.box
PAL = VC.PAL
PAL.update({
    "wolf_grey": (0.52, 0.52, 0.52), "wolf_grey_d": (0.32, 0.31, 0.31), "wolf_cream": (0.90, 0.86, 0.76), "wolf_white": (0.95, 0.95, 0.93),
    "wolf_tan": (0.70, 0.55, 0.36), "wolf_rust": (0.72, 0.40, 0.20), "wolf_red": (0.80, 0.36, 0.16), "wolf_black": (0.12, 0.11, 0.12),
    "wolf_char": (0.24, 0.22, 0.22), "wolf_sable": (0.46, 0.36, 0.24), "wolf_frost": (0.80, 0.84, 0.88), "wolf_buff": (0.82, 0.72, 0.52),
    "wolf_brown": (0.42, 0.30, 0.20), "wolf_nose": (0.07, 0.06, 0.06), "wolf_eye_a": (0.95, 0.65, 0.10), "wolf_eye_g": (0.98, 0.85, 0.25),
    "wolf_eye_i": (0.60, 0.85, 1.00), "wolf_eye_b": (0.35, 0.22, 0.10), "wolf_ear_in": (0.75, 0.55, 0.50), "wolf_claw": (0.20, 0.18, 0.16),
    "wolf_tongue": (0.85, 0.35, 0.40),
})
KINDS = {
    # kind: (back, flank, belly/mask, size, leg factor, ear factor, ruff, muzzle len)
    "grey":       ("wolf_grey_d", "wolf_grey",  "wolf_cream", 1.00, 1.00, 1.0, 2, 5),
    "timber":     ("wolf_char",   "wolf_tan",   "wolf_cream", 1.10, 1.00, 1.0, 2, 5),
    "arctic":     ("wolf_white",  "wolf_white", "wolf_white", 1.05, 0.90, 0.8, 3, 4),
    "tundra":     ("wolf_frost",  "wolf_white", "wolf_white", 1.15, 0.95, 0.9, 3, 5),
    "red":        ("wolf_brown",  "wolf_rust",  "wolf_cream", 0.85, 1.05, 1.1, 1, 5),
    "maned":      ("wolf_black",  "wolf_red",   "wolf_white", 0.95, 1.45, 1.6, 2, 5),
    "highland":   ("wolf_red",    "wolf_red",   "wolf_white", 0.80, 1.10, 1.2, 0, 6),
    "steppe":     ("wolf_tan",    "wolf_buff",  "wolf_cream", 0.90, 1.00, 1.0, 1, 5),
    "mountain":   ("wolf_char",   "wolf_grey",  "wolf_white", 1.10, 1.00, 0.9, 3, 5),
    "coastal":    ("wolf_char",   "wolf_sable", "wolf_buff",  0.85, 1.00, 1.0, 1, 5),
    "desert":     ("wolf_tan",    "wolf_buff",  "wolf_white", 0.80, 1.10, 1.3, 0, 5),
    "dire":       ("wolf_black",  "wolf_char",  "wolf_grey",  1.35, 1.00, 0.9, 3, 6),
}
COATS = ("classic", "saddle", "pale", "melanistic", "sable", "frosted")
EYES = ("wolf_eye_a", "wolf_eye_g", "wolf_eye_i", "wolf_eye_b")
VARIANTS = 7
ECOLOGY = {
    "family": "wolf", "role": "predator", "prey": ["rabbit", "duneback calves (if pens unguarded)"],
    "pack": {"min": 3, "max": 8, "alpha_scale": 1.12},
    "islands": {"frost": 1.0, "meadow": 0.6, "mesa": 0.5, "crystal": 0.2, "volcano": 0.1, "mire": 0.2},
    "cycle": "Lotka-Volterra with the rabbit population: prey peak leads predator peak by ~1/4 cycle",
    "kennel": {"tame_with": "stillmoss tonic + 3 fed rabbits", "job": "guard livestock pens at night (halves raid chance)"},
    "drops": {"pelt": "craft@tannery", "fang": "craft@smithy"},
    "spawn_note": "dens near caves (island_chemistry geology.caves); howl at night is the audio cue",
}


def names():
    return tuple("wolf_%s_%s_%02d" % (k, c, v) for k in KINDS for c in COATS for v in range(1, VARIANTS + 1))


def spec(species):
    kind, coat, v = species[len("wolf_"):].rsplit("_", 2)
    v = int(v)
    ki, ci = list(KINDS).index(kind), COATS.index(coat)
    rng = random.Random(ki * 1000 + ci * 10 + v)
    back, flank, belly, size, legf, earf, ruff, muz = KINDS[kind]
    if coat == "saddle":
        back = "wolf_black" if back != "wolf_black" else "wolf_char"
    elif coat == "pale":
        back, flank = ("wolf_frost", "wolf_cream") if kind not in ("arctic", "tundra") else ("wolf_white", "wolf_cream")
    elif coat == "melanistic":
        back, flank, belly = "wolf_black", "wolf_char", "wolf_grey_d" if kind != "maned" else "wolf_char"
    elif coat == "sable":
        back, flank = "wolf_brown", "wolf_sable"
    elif coat == "frosted":
        back = "wolf_frost"
    return {
        "kind": kind, "coat": coat, "variant": v, "back": back, "flank": flank, "belly": belly,
        "size": size * (0.9 + 0.2 * rng.random()), "leg": legf, "ear": earf * (0.85 + 0.3 * rng.random()),
        "ruff": max(0, ruff + rng.randint(-1, 1)), "muzzle": muz, "eye": EYES[(v + ki) % 4],
        "tail": ("low", "level", "low", "raised", "low", "level", "low")[v - 1], "socks": rng.random() < 0.3 or kind == "maned",
        "torn_ear": rng.random() < 0.12, "stockings": kind == "maned", "seed": rng.random(),
    }


def plan(species):
    """Voxel plan per bone (5 cm voxels). Faces +Y, feet at z=0."""
    o = spec(species)
    s = o["size"]
    out = {}
    back, flank, belly = o["back"], o["flank"], o["belly"]
    L = max(6, int(9 * s * o["leg"]))                  # leg length to the elbow/stifle
    BL = max(14, int(20 * s))                          # torso length
    y0 = -BL // 2
    sock = "wolf_white" if o["socks"] and not o["stockings"] else None
    # torso: shoulder taller than hip, deep chest dropping below the elbow, tucked waist
    for i in range(BL):
        t = i / (BL - 1)                               # 0 = rump, 1 = chest
        top = L + int((7.4 + 1.6 * t) * s)
        if t > 0.62:
            bot = L - max(1, int(1.5 * s))             # brisket
        elif t > 0.30:
            bot = L + int((1.0 + 2.2 * (0.62 - t) / 0.32 * (t < 0.5)) * s)   # waist tuck
        else:
            bot = L + max(1, int(0.8 * s))
        w = max(4, int((5.0 if t > 0.6 else 4.2 if t > 0.3 else 4.8) * s))
        x0 = -w // 2
        y = y0 + i
        box(out, "body", x0, y, bot, w, 1, top - bot, flank)
        box(out, "body", x0, y, top - max(1, int(1.6 * s)), w, 1, max(1, int(1.6 * s)), back)        # dark back line
        box(out, "body", x0 + 1, y, bot, w - 2, 1, 1, belly)                                           # belly
        if t > 0.62:
            box(out, "body", x0 + 1, y, bot, w - 2, 1, max(1, (top - bot) // 3), belly)              # pale chest
    rng = random.Random(int(o["seed"] * 1e6))
    if o["coat"] == "frosted":
        for _ in range(int(14 * s)):
            box(out, "body", rng.randint(-2, 1), rng.randint(y0, y0 + BL - 1), L + int(7 * s), 1, 1, 1, "wolf_white")
    sh_top = L + int(9.0 * s)
    # neck + ruff, angled up and forward
    nw = max(4, int(4.4 * s))
    ny = y0 + BL - max(2, int(2 * s))
    nl = max(3, int(4 * s))
    for j in range(nl):                                                                             # neck runs forward, not up
        box(out, "head", -nw // 2, ny + j, sh_top - 4 + j // 2, nw, 2, max(4, int(5 * s)), flank)
    if o["ruff"]:
        r = o["ruff"]
        box(out, "head", -nw // 2 - 1, ny - 1, sh_top - 3, nw + 2, 2 + r, 3 + r, back if o["coat"] in ("melanistic",) else flank)
        box(out, "head", -nw // 2 - 1, ny + 1 + r, sh_top - 4, nw + 2, 1, 3 + r, belly)                 # pale throat bib
    # head: skull, stop, long muzzle, mask
    hw = max(4, int(5.2 * s))
    hh = max(4, int(4.6 * s))
    hd = max(4, int(4.6 * s))
    hy = ny + nl - 1
    hz = sh_top - 2 + nl // 2
    box(out, "head", -hw // 2, hy, hz, hw, hd, hh, flank)
    box(out, "head", -hw // 2, hy, hz + hh - 1, hw, hd, 1, back)                                       # dark crown
    mw = max(2, hw - 2 - (1 if hw > 5 else 0))
    ml = max(3, int(o["muzzle"] * s))
    mh0 = max(3, hh - 1)
    for j in range(ml):                                                                             # muzzle tapers to the nose
        mh = max(2, mh0 - (j * (mh0 - 2)) // max(1, ml - 1))
        y = hy + hd + j
        box(out, "head", -mw // 2, y, hz, mw, 1, mh, belly)                                           # the pale mask below
        box(out, "head", -mw // 2, y, hz + mh - 1, mw, 1, 1, flank if j < ml - 1 else "wolf_nose")   # bridge, then the nose
    box(out, "head", -mw // 2, hy + hd + ml - 1, hz, mw, 1, 1, "wolf_char")                            # chin/lip
    box(out, "head", -hw // 2, hy + hd - 1, hz, hw, 1, max(2, hh // 2), belly)                         # cheeks
    for sx in (-hw // 2, hw // 2 - 1):
        box(out, "head", sx, hy + hd - 1, hz + hh // 2 + 1, 1, 1, 1, o["eye"])                       # almond eyes, set forward
        box(out, "head", sx, hy + hd - 2, hz + hh // 2 + 1, 1, 1, 1, "wolf_char")                      # dark eye line
    # ears: triangles, tall for the maned / desert kinds
    eh = max(2, int(3.2 * s * o["ear"]))
    for side, sx in ((0, -hw // 2), (1, hw // 2 - 2)):
        torn = o["torn_ear"] and side == 0
        for k in range(eh - (1 if torn else 0)):
            wdt = 2 if k < eh - 1 else 1
            box(out, "head", sx + (1 if (wdt == 1 and side == 0) else 0), hy + 1, hz + hh + k, wdt, 2 if k < eh // 2 else 1, 1, back)
        box(out, "head", sx + (1 if side == 0 else 0), hy + 2, hz + hh, 1, 1, max(1, eh // 2), "wolf_ear_in")
    # legs: forelegs straight under the chest, hind legs with thigh + hock angle; paws 3 long
    lw = max(2, int(2.0 * s))
    stock = "wolf_black" if o["stockings"] else None
    for bone, sx in (("leg.L", -max(2, int(2.4 * s))), ("leg.R", max(2, int(2.4 * s)) - lw)):
        fy = y0 + BL - max(4, int(5 * s))
        box(out, bone, sx, fy, 1, lw, lw, L + 2, stock or flank)                                       # foreleg to the elbow
        box(out, bone, sx, fy, L - 1, lw, lw + 1, 3, stock or flank)                                   # elbow
        box(out, bone, sx, fy, 0, lw, lw + 1, 1, stock or "wolf_char")                                 # paw
        box(out, bone, sx, fy + lw, 0, lw, 1, 1, "wolf_claw")
        if sock:
            box(out, bone, sx, fy, 1, lw, lw, 2, sock)
        hy0 = y0 + max(1, int(1.2 * s))
        hock = max(2, int(L * 0.45))
        box(out, bone, sx, hy0 - 1, 1, lw, lw, hock, stock or flank)                                   # metatarsus, angled back
        box(out, bone, sx, hy0, hock, lw, lw, L - hock + 2, flank)                                     # gaskin
        box(out, bone, sx - (1 if sx < 0 else 0), hy0, L, lw + 1, lw + 2, max(3, int(4 * s)), flank)  # thigh
        box(out, bone, sx, hy0 - 1, 0, lw, lw + 1, 1, stock or "wolf_char")
        box(out, bone, sx, hy0 + lw, 0, lw, 1, 1, "wolf_claw")
        if sock:
            box(out, bone, sx, hy0 - 1, 1, lw, lw, 2, sock)
    # tail: bushy, carried low (or level / raised), dark tip
    tl = max(5, int(7.5 * s))
    tz = L + int(6 * s)
    drop = {"low": 0.75, "level": 0.3, "raised": -0.35}[o["tail"]]
    tw = max(2, int(2.6 * s))
    for j in range(tl):
        y = y0 - 1 - j
        z = int(tz - drop * j)
        th = 2 + (1 if 2 <= j < tl - 2 else 0) + (1 if s > 1.1 and 3 <= j < tl - 3 else 0)
        c = "wolf_black" if j >= tl - 2 else (back if j < 2 else flank)
        box(out, "tail", -tw // 2, y, z - th // 2, tw, 1, th, c)
    return _last_wins(out)


def _last_wins(out):
    """Later boxes paint over earlier ones (mask over muzzle etc.): keep one voxel per cell, the last written."""
    seen = {}
    for bone, vox in out.items():
        for x, y, z, c in vox:
            seen[(x, y, z)] = (bone, c)
    res = {}
    for (x, y, z), (bone, c) in seen.items():
        res.setdefault(bone, []).append((x, y, z, c))
    return res


NAMES = names()
VC.EXTRA["wolf"] = (NAMES, plan)
VOXEL_CM = 5.0


def manifest():
    return {"ecology": ECOLOGY, "voxel_cm": VOXEL_CM, "wolves": {n: {k: v for k, v in spec(n).items() if k != "seed"} for n in NAMES}}


if __name__ == "__main__":
    import sys
    miss, empty, hs = set(), [], set()
    for n in NAMES:
        p = plan(n)
        if not sum(len(v) for v in p.values()):
            empty.append(n)
        hs.add(hash(tuple(sorted((b, tuple(v)) for b, v in p.items()))))
        for v in p.values():
            for *_, c in v:
                if c not in PAL:
                    miss.add(c)
    print(len(NAMES), "wolves;", len(hs), "unique; empty", empty, "missing", sorted(miss))
    sys.exit(1 if miss or empty or len(hs) != len(NAMES) else 0)
