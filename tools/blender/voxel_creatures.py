# SPDX-License-Identifier: MIT
"""Small voxel characters that move (Richey 14:20: "small characters moving around ... bunches of types, all animal
types, all carnivorous plant types, birds and bees").

Each species is a pure-Python **body plan**: boxes in 10 cm voxels, every box bound to a bone of the same 8-bone
rig Codex's realm creatures use (root, body, head, tail, leg.L, leg.R, wing.L, wing.R) with the same clip names
(Idle, Walk, Attack, Hurt), so Unreal treats a voxel hen and a Portal monster the same way. Meshing reuses the
island mesher (greedy quads + vertex colours); the rig, clips and GLB/FBX export happen only in Blender.

    import voxel_creatures as VC
    VC.plan("fox")                  -> {bone: [(x, y, z, colour)]} in 0.1 m voxels, +Y forward, Z up, feet at z=0
    VC.build("fox", out_dir)        -> out_dir/Creature_Fox.glb (+ .fbx, .json)   (Blender)
    VC.SPECIES                      -> every species by family: animals, birds, bees, carnivorous plants

Carnivorous plants animate too: their "head" bone is the trap (snap = Attack), "wing" bones are leaves, so a
flytrap closes on the player the way a dog bites. Plants have no Walk (they sway in Idle).
"""
import math
import os
import random

import voxel_island as V

import hero_island as HI
PAL = dict(HI.PAL)          # the island palette (soil, wool, flowers...) plus the creature colours below
PAL.update({
    "fur_r": (0.80, 0.42, 0.18), "fur_w": (0.95, 0.94, 0.90), "fur_k": (0.15, 0.14, 0.16), "fur_g": (0.55, 0.55, 0.58),
    "fur_b": (0.42, 0.28, 0.16), "fur_y": (0.90, 0.78, 0.40), "fur_p": (0.95, 0.70, 0.72), "fur_o": (0.95, 0.55, 0.20),
    "skin": (0.95, 0.80, 0.70), "nose": (0.10, 0.08, 0.08), "eye": (0.05, 0.05, 0.06), "eye_w": (1.00, 1.00, 1.00),
    "beak": (0.95, 0.70, 0.20), "feather_r": (0.85, 0.25, 0.20), "feather_b": (0.25, 0.45, 0.90), "feather_g": (0.25, 0.65, 0.30),
    "feather_k": (0.12, 0.12, 0.14), "feather_w": (0.95, 0.95, 0.95), "feather_y": (0.98, 0.85, 0.25), "feather_br": (0.55, 0.38, 0.22),
    "bee_y": (0.98, 0.80, 0.15), "bee_k": (0.12, 0.10, 0.08), "wing_c": (0.85, 0.92, 1.00), "sting": (0.30, 0.25, 0.20),
    "hay": (0.88, 0.75, 0.40), "shell": (0.35, 0.50, 0.30), "shell2": (0.25, 0.38, 0.22), "scale": (0.30, 0.65, 0.35), "belly": (0.90, 0.85, 0.60),
    "trap": (0.35, 0.70, 0.30), "trap_in": (0.90, 0.30, 0.40), "tooth": (0.95, 0.95, 0.85), "pitcher": (0.60, 0.80, 0.35),
    "pitcher_r": (0.75, 0.25, 0.30), "dew": (0.85, 0.95, 1.00), "stem": (0.30, 0.55, 0.25), "lid": (0.55, 0.30, 0.45),
    "bladder": (0.45, 0.65, 0.35), "horn": (0.80, 0.75, 0.60), "hoof": (0.25, 0.20, 0.18), "antler": (0.70, 0.60, 0.45),
})
BONES = (("root", (0, 0, 0), (0, 0, 0.1), None), ("body", (0, 0, 0.3), (0, 0, 0.6), "root"), ("head", (0, 0.3, 0.6), (0, 0.3, 0.9), "body"),
         ("tail", (0, -0.3, 0.5), (0, -0.6, 0.5), "body"), ("leg.L", (0.15, 0, 0.3), (0.15, 0, 0.0), "body"), ("leg.R", (-0.15, 0, 0.3), (-0.15, 0, 0.0), "body"),
         ("wing.L", (0.2, 0, 0.6), (0.6, 0, 0.6), "body"), ("wing.R", (-0.2, 0, 0.6), (-0.6, 0, 0.6), "body"))
CLIPS = (("Idle", 48), ("Walk", 24), ("Run", 16), ("Attack", 24), ("Hurt", 24), ("Turn", 24), ("Jump", 24), ("Action", 36))
# VISUAL-QUALITY-BAR.md 117: idle/walk/run/start-stop/turn/jump-land/role action, grounded feet, head attention.
# Walk and Run are stepped (CONSTANT keys) so feet plant instead of sliding; Turn yaws the body with the head leading;
# Jump tucks the legs and lands with a squash; Action is the role move (graze/peck/sting/snap/swim-flip/shamble-grab).


def box(out, bone, x0, y0, z0, w, d, h, colour):
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + d):
            for z in range(z0, z0 + h):
                out.setdefault(bone, []).append((x, y, z, colour))


def _quadruped(fur, belly=None, size=1.0, tail="short", ears="up", horns=None, spots=None, snout=2, legs=4, mane=None):
    """A generic four-legged plan in 10 cm voxels: body 8x14, head 6x6, legs 2x2, feet at z=0."""
    s = size
    out = {}
    W, D, H = max(4, int(8 * s)), max(8, int(14 * s)), max(4, int(6 * s))
    L = max(3, int(5 * s))
    box(out, "body", -W // 2, -D // 2, L, W, D, H, fur)
    if belly:
        box(out, "body", -W // 2 + 1, -D // 2 + 1, L, W - 2, D - 2, 1, belly)
    if spots:
        rng = random.Random(len(fur) * 7)
        for _ in range(6):
            box(out, "body", rng.randint(-W // 2, W // 2 - 2), rng.randint(-D // 2, D // 2 - 2), L + H - 1, 2, 2, 1, spots)
    hw, hd, hh = max(3, int(6 * s)), max(3, int(6 * s)), max(3, int(6 * s))
    hy = D // 2 - 1
    box(out, "head", -hw // 2, hy, L + H - 2, hw, hd, hh, fur)
    box(out, "head", -1, hy + hd, L + H - 1, 2, snout, 2, fur)
    box(out, "head", -1, hy + hd + snout, L + H, 2, 1, 1, "nose")
    for sx in (-hw // 2, hw // 2 - 1):
        box(out, "head", sx, hy + hd - 1, L + H + 1, 1, 1, 1, "eye")
        if ears == "up":
            box(out, "head", sx, hy + 1, L + H - 2 + hh, 1, 2, 2, fur)
        elif ears == "long":
            box(out, "head", sx, hy + 1, L + H - 2 + hh, 1, 1, 5, fur)
    if horns:
        for sx in (-hw // 2, hw // 2 - 1):
            box(out, "head", sx, hy + 2, L + H - 2 + hh, 1, 1, 3, horns)
    if mane:
        box(out, "body", -W // 2 - 1, D // 2 - 4, L + H - 1, W + 2, 4, 2, mane)
    for i, (sx, sy) in enumerate(((-W // 2, D // 2 - 3), (W // 2 - 2, D // 2 - 3), (-W // 2, -D // 2 + 1), (W // 2 - 2, -D // 2 + 1))[:legs]):
        bone = "leg.L" if sx < 0 else "leg.R"
        box(out, bone, sx, sy, 0, 2, 2, L, fur)
        box(out, bone, sx, sy, 0, 2, 2, 1, "hoof")
    if tail == "short":
        box(out, "tail", -1, -D // 2 - 2, L + H - 2, 2, 2, 2, fur)
    elif tail == "bushy":
        box(out, "tail", -1, -D // 2 - 5, L + H - 3, 2, 5, 3, fur)
        box(out, "tail", -1, -D // 2 - 6, L + H - 2, 2, 2, 2, "fur_w")
    elif tail == "long":
        box(out, "tail", -1, -D // 2 - 7, L + H - 2, 1, 7, 1, fur)
    return out


def _bird(feather, belly, size=1.0, beak_len=2, crest=None, legs_h=3, tail_len=3, wing_len=6):
    s = size
    out = {}
    W, D, H = max(3, int(4 * s)), max(4, int(6 * s)), max(3, int(4 * s))
    box(out, "body", -W // 2, -D // 2, legs_h, W, D, H, feather)
    box(out, "body", -W // 2 + 1, -D // 2 + 1, legs_h, W - 2, D - 1, 1, belly)
    hs = max(2, int(3 * s))
    box(out, "head", -hs // 2, D // 2 - 1, legs_h + H - 1, hs, hs, hs, feather)
    box(out, "head", -1, D // 2 - 1 + hs, legs_h + H, 1, beak_len, 1, "beak")
    for sx in (-hs // 2, hs // 2 - 1):
        box(out, "head", sx, D // 2 + hs - 2, legs_h + H + 1, 1, 1, 1, "eye")
    if crest:
        box(out, "head", -1, D // 2, legs_h + H - 1 + hs, 1, 2, 2, crest)
    box(out, "tail", -1, -D // 2 - tail_len, legs_h + H - 2, 2, tail_len, 1, feather)
    for sx, bone in ((-1, "leg.L"), (1, "leg.R")):
        box(out, bone, sx, 0, 0, 1, 1, legs_h, "beak")
        box(out, bone, sx - 1, 0, 0, 3, 2, 1, "beak")
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        # folded along the flank at rest (2 wide, the body's length); the Walk/fly clip rotates them out
        x0 = W // 2 if sgn > 0 else -W // 2 - 2
        box(out, bone, x0, -D // 2, legs_h + H - 3, 2, D - 1, 2, feather)
        box(out, bone, x0, -D // 2 - wing_len // 2, legs_h + H - 3, 2, wing_len // 2, 1, feather)   # primaries trail back
    return out


def _bee(size=1.0, stripes=True, body=("bee_y", "bee_k")):
    s = size
    out = {}
    D = max(4, int(6 * s))
    for y in range(-D // 2, D // 2):
        c = body[0] if (not stripes or (y + D // 2) % 2 == 0) else body[1]
        box(out, "body", -2, y, 2, 4, 1, 3, c)
    box(out, "head", -1, D // 2, 2, 3, 2, 3, "bee_k")
    for sx in (-1, 1):
        box(out, "head", sx, D // 2 + 2, 3, 1, 1, 1, "eye")
        box(out, "head", sx, D // 2 + 1, 5, 1, 1, 2, "bee_k")      # antennae
    box(out, "tail", 0, -D // 2 - 1, 3, 1, 1, 1, "sting")
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        x0 = 2 if sgn > 0 else -2 - 4
        box(out, bone, x0, -1, 5, 4, 3, 1, "wing_c")
    for sx, bone in ((-2, "leg.L"), (2, "leg.R")):
        for y in (-1, 0, 1):
            box(out, bone, sx, y, 0, 1, 1, 2, "bee_k")
    return out


def _fish(body, fin, size=1.0, long=False):
    """Fish for the lakes, sky rivers and basins (chemistry water.fish): tail = tail bone (wags), fins = wings."""
    s = size
    out = {}
    D = max(5, int((10 if long else 7) * s))
    H = max(2, int(3 * s))
    for y in range(-D // 2, D // 2):
        h = H if abs(y) < D // 3 else max(1, H - 1)
        box(out, "body", -1, y, 3, 2, 1, h, body if (y + D // 2) % 3 else fin)
    box(out, "head", -1, D // 2, 3, 2, 2, H, body)
    box(out, "head", 0, D // 2 + 1, 4, 1, 1, 1, "eye")
    box(out, "head", -1, D // 2 + 1, 4, 1, 1, 1, "eye")
    box(out, "tail", -1, -D // 2 - 2, 2, 2, 2, H + 2, fin)
    box(out, "wing.L", 1, -1, 3, 2, 2, 1, fin)
    box(out, "wing.R", -3, -1, 3, 2, 2, 1, fin)
    box(out, "body", -1, -1, 3 + H, 2, 3, 1, fin)        # dorsal fin
    return out


def _biped(skin, cloth, hat=None, size=1.0, rot=0, arms_out=True, crawler=False, tool=None, hair=None):
    """Zombies and other walkers: legs 2x2x6, torso 6x3x7, head 4x4x4, arms on the wing bones (zombies hold them
    out). `rot` = how rotten: 0 fresh, 1 green patches, 2 bones showing. A crawler has no legs and drags."""
    s = size
    out = {}
    L = 0 if crawler else max(4, int(6 * s))
    T = max(5, int(7 * s))
    rng = random.Random(len(skin) + rot)
    sk = ("scale", "fur_g", "skin")[min(rot, 2)] if skin == "zombie" else skin
    if not crawler:
        for sx, bone in ((-2, "leg.L"), (1, "leg.R")):
            box(out, bone, sx, -1, 0, 2, 2, L, cloth)
            box(out, bone, sx, -1, 0, 2, 2, 1, "hoof")
    box(out, "body", -3, -1, L, 6, 3, T, cloth)
    if rot >= 1:
        for _ in range(4):
            box(out, "body", rng.randint(-3, 1), -1, L + rng.randint(0, T - 2), 2, 1, 1, "scale")
    if rot >= 2:
        box(out, "body", -1, -2, L + T // 2, 2, 1, 3, "tooth")
    box(out, "head", -2, -2, L + T, 4, 4, 4, sk)
    for sx in (-2, 1):
        box(out, "head", sx, 2, L + T + 2, 1, 1, 1, "eye" if rot == 0 else "flower_r")
    box(out, "head", -1, 2, L + T + 1, 2, 1, 1, "nose")
    if hat:
        box(out, "head", -3, -3, L + T + 4, 6, 6, 1, hat)
        box(out, "head", -2, -2, L + T + 5, 4, 4, 2, hat)
    if hair:
        box(out, "head", -2, -2, L + T + 4, 4, 4, 1, hair)
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        x0 = 3 if sgn > 0 else -5
        if arms_out:
            box(out, bone, x0, 2, L + T - 2, 2, 6, 2, sk)      # arms straight out, zombie style
        else:
            box(out, bone, x0, -1, L + 1, 2, 2, T - 1, sk)
    if tool:
        box(out, "wing.R", -5, 8, L + T - 3, 1, 1, 5, tool)
    return out


def _dino(kind):
    out = {}
    if kind in ("trex", "raptor", "allosaurus", "carnotaurus"):
        big = kind in ("trex", "allosaurus", "carnotaurus")
        sc = "scale" if kind != "carnotaurus" else "fur_r"
        L = 9 if big else 6
        box(out, "leg.L", -3, -1, 0, 3, 3, L, sc)
        box(out, "leg.R", 1, -1, 0, 3, 3, L, sc)
        box(out, "body", -3, -4, L, 7, 10, 6 if big else 4, sc)
        box(out, "body", -2, -3, L, 5, 8, 1, "belly")
        box(out, "head", -2, 6, L + 4, 5, 8 if big else 5, 4, sc)
        for y in range(7, 13 if big else 10):
            box(out, "head", -2, y, L + 4, 1, 1, 1, "tooth")
            box(out, "head", 2, y, L + 4, 1, 1, 1, "tooth")
        box(out, "head", -2, 11 if big else 8, L + 7, 1, 1, 1, "eye")
        box(out, "head", 2, 11 if big else 8, L + 7, 1, 1, 1, "eye")
        box(out, "tail", -1, -14, L + 2, 3, 10, 3, sc)
        box(out, "tail", -1, -18, L + 3, 2, 4, 2, sc)
        box(out, "wing.L", 3, 5, L + 2, 1, 1, 3, sc)
        box(out, "wing.R", -3, 5, L + 2, 1, 1, 3, sc)
        if kind == "carnotaurus":
            box(out, "head", -2, 10, L + 8, 1, 1, 2, "horn")
            box(out, "head", 2, 10, L + 8, 1, 1, 2, "horn")
    elif kind in ("triceratops", "stegosaurus", "ankylosaurus", "brontosaurus"):
        sc = "fur_g" if kind != "brontosaurus" else "scale"
        big = kind == "brontosaurus"
        for sx, sy, bone in ((-4, 4, "leg.L"), (2, 4, "leg.R"), (-4, -4, "leg.L"), (2, -4, "leg.R")):
            box(out, bone, sx, sy, 0, 3, 3, 7 if big else 5, sc)
        H = 7 if big else 5
        box(out, "body", -4, -6, 5 if not big else 7, 9, 13, 7, sc)
        if kind == "triceratops":
            box(out, "head", -3, 6, 7, 7, 6, 5, sc)
            box(out, "head", -5, 5, 10, 11, 1, 4, "horn")           # frill
            for sx in (-3, 2):
                box(out, "head", sx, 11, 10, 1, 4, 1, "tooth")
            box(out, "head", 0, 12, 8, 1, 3, 1, "tooth")
        elif kind == "stegosaurus":
            box(out, "head", -2, 6, 6, 4, 5, 3, sc)
            for y in range(-6, 8, 3):
                box(out, "body", -1, y, 12, 2, 2, 4, "pitcher_r")   # plates
            box(out, "tail", -1, -14, 5, 3, 8, 3, sc)
            for y in (-13, -11):
                box(out, "tail", -1, y, 8, 1, 1, 3, "tooth")
        elif kind == "ankylosaurus":
            box(out, "head", -2, 6, 6, 4, 5, 3, sc)
            for x in range(-4, 5, 2):
                for y in range(-6, 7, 3):
                    box(out, "body", x, y, 12, 1, 1, 1, "shell2")
            box(out, "tail", -1, -14, 5, 3, 8, 3, sc)
            box(out, "tail", -2, -17, 5, 5, 3, 4, "shell2")         # club
        else:
            box(out, "body", -1, 6, 12, 3, 3, 10, sc)                # long neck
            box(out, "head", -2, 6, 22, 4, 5, 3, sc)
            box(out, "tail", -1, -20, 8, 3, 14, 3, sc)
        if kind != "stegosaurus" and kind != "ankylosaurus" and kind != "brontosaurus":
            box(out, "tail", -1, -12, 7, 3, 6, 3, sc)
    elif kind in ("pterodactyl", "quetzal"):
        box(out, "body", -2, -3, 6, 4, 7, 3, "fur_b")
        box(out, "head", -1, 4, 8, 3, 3, 3, "fur_b")
        box(out, "head", -1, 7, 8, 2, 6, 1, "beak")
        box(out, "head", -1, 3, 10, 2, 1, 4, "fur_b")              # crest
        box(out, "head", 1, 6, 9, 1, 1, 1, "eye")
        w = 14 if kind == "quetzal" else 9
        for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
            x0 = 2 if sgn > 0 else -2 - w
            box(out, bone, x0, -3, 7, w, 6, 1, "fur_b")
            box(out, bone, x0, -5, 7, w // 2, 2, 1, "fur_b")
        for sx, bone in ((-1, "leg.L"), (1, "leg.R")):
            box(out, bone, sx, 0, 3, 1, 1, 3, "fur_b")
        box(out, "tail", -1, -7, 7, 2, 4, 1, "fur_b")
    return out


def _sea(kind):
    out = {}
    if kind in ("shark", "dolphin", "orca", "whale", "narwhal"):
        big = kind in ("whale", "orca")
        c = {"shark": "fur_g", "dolphin": "feather_b", "orca": "fur_k", "whale": "feather_b", "narwhal": "fur_w"}[kind]
        D = 18 if big else 12
        H = 6 if big else 4
        for y in range(-D // 2, D // 2):
            h = H if abs(y) < D // 3 else H - 1
            box(out, "body", -2, y, 3, 5, 1, h, c)
        box(out, "body", -1, -D // 2, 2, 3, D, 1, "belly")
        box(out, "head", -2, D // 2, 3, 5, 4, H, c)
        box(out, "head", 2, D // 2 + 2, 5, 1, 1, 1, "eye")
        box(out, "head", -2, D // 2 + 2, 5, 1, 1, 1, "eye")
        if kind == "shark":
            for y in range(D // 2, D // 2 + 3):
                box(out, "head", -1, y, 3, 3, 1, 1, "tooth")
        if kind == "narwhal":
            box(out, "head", 0, D // 2 + 4, 5, 1, 8, 1, "tooth")
        box(out, "body", 0, -1, 3 + H, 1, 3, 3 if kind != "whale" else 1, c)     # dorsal
        box(out, "tail", -3, -D // 2 - 3, 4, 7, 3, 1, c)
        box(out, "wing.L", 3, 1, 3, 3, 3, 1, c)
        box(out, "wing.R", -5, 1, 3, 3, 3, 1, c)
        if kind == "orca":
            box(out, "body", -2, 2, 6, 5, 2, 1, "fur_w")
    elif kind in ("octopus", "squid", "jellyfish"):
        c = {"octopus": "fur_o", "squid": "fur_p", "jellyfish": "wing_c"}[kind]
        box(out, "head", -3, -3, 6, 6, 6, 5 if kind != "squid" else 9, c)
        box(out, "head", -2, 3, 8, 1, 1, 1, "eye")
        box(out, "head", 1, 3, 8, 1, 1, 1, "eye")
        for i, (dx, dy) in enumerate(((2, 2), (-3, 2), (2, -3), (-3, -3), (0, 3), (0, -4), (3, 0), (-4, 0))):
            bone = ("leg.L", "leg.R", "wing.L", "wing.R")[i % 4]
            for t in range(0, 6):
                box(out, bone, dx, dy, 6 - t, 1, 1, 1, c if kind != "jellyfish" else "dew")
    elif kind in ("crab", "lobster"):
        c = "feather_r"
        box(out, "body", -4, -2, 2, 8 if kind == "crab" else 4, 5 if kind == "crab" else 10, 3, c)
        box(out, "head", -1, 3 if kind == "crab" else 8, 4, 1, 1, 2, "eye")
        box(out, "head", 1, 3 if kind == "crab" else 8, 4, 1, 1, 2, "eye")
        for sx, bone in ((-6, "leg.L"), (5, "leg.R")):
            for y in (-2, 0, 2):
                box(out, bone, sx, y, 0, 2, 1, 2, c)
        box(out, "wing.L", 4, 3, 2, 3, 4, 2, c)
        box(out, "wing.R", -7, 3, 2, 3, 4, 2, c)
        if kind == "lobster":
            box(out, "tail", -2, -7, 2, 4, 5, 2, c)
    elif kind in ("sea_turtle", "seahorse", "manta", "eel", "clownfish", "pufferfish", "swordfish", "anglerfish", "starfish"):
        if kind == "sea_turtle":
            box(out, "body", -4, -5, 2, 8, 10, 3, "shell")
            box(out, "body", -3, -4, 5, 6, 8, 1, "shell2")
            box(out, "head", -1, 5, 3, 3, 3, 2, "scale")
            box(out, "head", 1, 7, 4, 1, 1, 1, "eye")
            for sx, sy, bone in ((-7, 3, "wing.L"), (4, 3, "wing.R"), (-6, -5, "leg.L"), (4, -5, "leg.R")):
                box(out, bone, sx, sy, 2, 3, 2, 1, "scale")
            box(out, "tail", -1, -7, 2, 2, 2, 1, "scale")
        elif kind == "seahorse":
            for z in range(0, 8):
                box(out, "body", -1, 0 if z < 5 else 1, z + 2, 2, 2, 1, "feather_y")
            box(out, "head", -1, 2, 10, 2, 3, 2, "feather_y")
            box(out, "head", 0, 5, 11, 1, 2, 1, "beak")
            box(out, "tail", -1, -1, 0, 2, 2, 2, "feather_y")
            box(out, "wing.L", 1, 0, 6, 1, 1, 2, "feather_r")
            box(out, "wing.R", -2, 0, 6, 1, 1, 2, "feather_r")
        elif kind == "manta":
            box(out, "body", -3, -4, 3, 6, 9, 2, "fur_k")
            box(out, "head", -2, 5, 3, 4, 2, 2, "fur_k")
            box(out, "wing.L", 3, -3, 3, 7, 7, 1, "fur_k")
            box(out, "wing.R", -10, -3, 3, 7, 7, 1, "fur_k")
            box(out, "tail", 0, -10, 3, 1, 6, 1, "fur_k")
        elif kind == "starfish":
            box(out, "body", -1, -1, 0, 2, 2, 1, "feather_r")
            for i, (dx, dy) in enumerate(((3, 0), (1, 3), (-3, 1), (-2, -3), (2, -3))):
                bone = ("wing.L", "wing.R", "leg.L", "leg.R", "tail")[i]
                for t in range(1, 4):
                    box(out, bone, int(dx * t / 3), int(dy * t / 3), 0, 1, 1, 1, "feather_r")
        else:
            c = {"eel": "fur_g", "clownfish": "fur_o", "pufferfish": "feather_y", "swordfish": "feather_b", "anglerfish": "fur_k"}[kind]
            f = _fish(c, "feather_w" if kind == "clownfish" else "fur_k", size=1.0 if kind != "eel" else 0.8, long=kind in ("eel", "swordfish"))
            out.update(f)
            if kind == "swordfish":
                box(out, "head", 0, 8, 4, 1, 8, 1, "tooth")
            if kind == "anglerfish":
                box(out, "head", 0, 5, 7, 1, 1, 3, "fur_k")
                box(out, "head", 0, 5, 10, 1, 1, 1, "lantern")
            if kind == "pufferfish":
                for dx, dz in ((-2, 5), (2, 5), (0, 7), (-2, 2), (2, 2)):
                    box(out, "body", dx, 0, dz, 1, 1, 1, "tooth")
    return out


def _insect(kind):
    """Insects and the small ground life: 10 cm voxels, legs on the leg bones, wings on the wing bones."""
    out = {}
    if kind in ("butterfly", "moth", "dragonfly", "firefly", "ladybug", "beetle", "grasshopper", "cicada", "mosquito"):
        body = {"butterfly": "bee_k", "moth": "fur_g", "dragonfly": "feather_b", "firefly": "bee_k", "ladybug": "feather_r", "beetle": "fur_k",
                "grasshopper": "feather_g", "cicada": "fur_b", "mosquito": "fur_g"}[kind]
        D = 6 if kind in ("dragonfly", "grasshopper") else 4
        box(out, "body", -1, -D // 2, 2, 2, D, 2, body)
        box(out, "head", -1, D // 2, 2, 2, 2, 2, body)
        box(out, "head", -1, D // 2 + 1, 3, 1, 1, 1, "eye")
        box(out, "head", 0, D // 2 + 1, 3, 1, 1, 1, "eye")
        if kind in ("butterfly", "moth"):
            wc = ("flower_p", "bee_y", "feather_b") if kind == "butterfly" else ("fur_g", "fur_b")
            for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
                x0 = 1 if sgn > 0 else -5
                box(out, bone, x0, -1, 3, 4, 3, 1, wc[0])
                box(out, bone, x0, -3, 3, 3, 2, 1, wc[1 % len(wc)])
                box(out, bone, x0 + 1, 0, 3, 1, 1, 1, wc[-1])
        elif kind == "dragonfly":
            for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
                x0 = 1 if sgn > 0 else -7
                box(out, bone, x0, -1, 4, 6, 1, 1, "wing_c")
                box(out, bone, x0, 1, 4, 6, 1, 1, "wing_c")
        elif kind == "ladybug":
            for (dx, dy) in ((0, 0), (-1, -1), (0, -2)):
                box(out, "body", dx, dy, 4, 1, 1, 1, "fur_k")
        elif kind == "firefly":
            box(out, "tail", -1, -D // 2 - 1, 2, 2, 1, 2, "lantern")
        elif kind == "grasshopper":
            for sx, bone in ((-2, "leg.L"), (2, "leg.R")):
                box(out, bone, sx, -2, 0, 1, 1, 4, body)
        for sx, bone in ((-2, "leg.L"), (2, "leg.R")):
            for y in (-1, 0, 1):
                box(out, bone, sx, y, 0, 1, 1, 2, "bee_k")
    elif kind in ("ant", "termite", "spider", "scorpion", "centipede", "earthworm", "snail", "slug", "woodlouse", "tick"):
        body = {"ant": "fur_k", "termite": "skin", "spider": "fur_k", "scorpion": "fur_y", "centipede": "fur_r", "earthworm": "fur_p",
                "snail": "fur_b", "slug": "fur_g", "woodlouse": "fur_g", "tick": "fur_r"}[kind]
        if kind in ("ant", "termite"):
            box(out, "body", -1, -2, 1, 2, 2, 2, body)
            box(out, "tail", -1, -5, 1, 2, 3, 2, body)
            box(out, "head", -1, 0, 1, 2, 2, 2, body)
            box(out, "head", -1, 2, 2, 1, 1, 1, "eye")
            for sx, bone in ((-2, "leg.L"), (2, "leg.R")):
                for y in (-2, 0, 1):
                    box(out, bone, sx, y, 0, 1, 1, 1, body)
        elif kind == "spider":
            box(out, "body", -2, -3, 1, 4, 3, 3, body)
            box(out, "head", -1, 0, 1, 2, 2, 2, body)
            for sx in (-1, 0):
                box(out, "head", sx, 2, 2, 1, 1, 1, "flower_r")
            for sx, bone in ((-4, "leg.L"), (3, "leg.R")):
                for y in (-3, -2, -1, 0):
                    box(out, bone, sx, y, 0, 2, 1, 1, body)
                    box(out, bone, sx + (1 if sx < 0 else 0), y, 1, 1, 1, 2, body)
        elif kind == "scorpion":
            box(out, "body", -2, -3, 1, 4, 5, 2, body)
            box(out, "head", -1, 2, 1, 2, 2, 2, body)
            for z in range(1, 7):
                box(out, "tail", 0, -4 - (z // 3), z, 1, 1, 1, body)
            box(out, "tail", 0, -4, 7, 1, 1, 1, "sting")
            box(out, "wing.L", 2, 2, 1, 2, 3, 1, body)
            box(out, "wing.R", -4, 2, 1, 2, 3, 1, body)
            for sx, bone in ((-3, "leg.L"), (2, "leg.R")):
                for y in (-2, 0):
                    box(out, bone, sx, y, 0, 1, 1, 1, body)
        elif kind == "centipede":
            for y in range(-6, 6):
                box(out, "body" if y > -3 else "tail", -1, y, 0, 2, 1, 1, body if y % 2 else "fur_k")
                box(out, "leg.L" if y % 2 else "leg.R", -2 if y % 2 else 1, y, 0, 1, 1, 1, body)
            box(out, "head", -1, 6, 0, 2, 2, 1, "fur_k")
        elif kind == "earthworm":
            for y in range(-6, 6):
                box(out, "body" if y > -3 else "tail", 0, y, 0 if abs(y) % 4 < 2 else 1, 1, 1, 1, body)
            box(out, "head", 0, 6, 0, 1, 2, 1, "flower_p")
        elif kind in ("snail", "slug"):
            box(out, "body", -1, -2, 0, 2, 6, 1, body)
            box(out, "head", -1, 4, 0, 2, 1, 2, body)
            box(out, "head", -1, 4, 2, 1, 1, 1, "eye")
            box(out, "head", 0, 4, 2, 1, 1, 1, "eye")
            if kind == "snail":
                for z in range(1, 4):
                    r = 3 - abs(z - 2)
                    box(out, "tail", -r + 1, -2 - r + 1, z, 2 * r - 1, 2 * r - 1, 1, "shell" if z % 2 else "shell2")
        else:
            box(out, "body", -1, -2, 0, 2, 4, 1, body)
            box(out, "head", -1, 2, 0, 2, 1, 1, "fur_k")
            for sx, bone in ((-2, "leg.L"), (2, "leg.R")):
                for y in (-2, 0):
                    box(out, bone, sx, y, 0, 1, 1, 1, body)
    return out


def _plant(kind):
    """Carnivorous plants: root at the soil, 'body' = stem, 'head' = the trap (Attack snaps it), wings = leaves."""
    out = {}
    box(out, "root", -3, -3, 0, 6, 6, 1, "soil")
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        box(out, bone, 1 if sgn > 0 else -6, -2, 1, 5, 4, 1, "stem")
    if kind in ("venus_flytrap", "waterwheel"):
        box(out, "body", -1, -1, 1, 2, 2, 5, "stem")
        box(out, "head", -3, -2, 6, 6, 5, 1, "trap")                # lower lobe
        box(out, "head", -2, -1, 7, 4, 3, 1, "trap_in")
        for x in range(-3, 3):
            box(out, "head", x, 3, 7, 1, 1, 2, "tooth")             # teeth along the hinge-opposite edge
        box(out, "head", -3, -2, 9, 6, 5, 1, "trap")                # upper lobe, open
    elif kind in ("pitcher", "monkey_cup", "sun_pitcher", "cobra_lily", "moccasin"):
        col = {"pitcher": "pitcher", "monkey_cup": "pitcher_r", "sun_pitcher": "pitcher", "cobra_lily": "pitcher", "moccasin": "pitcher_r"}[kind]
        box(out, "body", -1, -1, 1, 2, 2, 3, "stem")
        for z in range(4, 12):
            r = 2 if z < 10 else 3
            for x in range(-r, r + 1):
                for y in range(-r, r + 1):
                    if abs(x) == r or abs(y) == r:
                        out.setdefault("head", []).append((x, y, z, col if (x + y + z) % 3 else "pitcher_r"))
        if kind == "cobra_lily":
            box(out, "head", -3, 0, 12, 6, 4, 2, col)               # hooded top
            box(out, "head", -1, 3, 11, 2, 2, 1, "trap_in")        # the forked tongue
        else:
            box(out, "head", -3, -3, 13, 6, 6, 1, "lid")
    elif kind in ("sundew", "dewy_pine", "rainbow_plant"):
        box(out, "body", -1, -1, 1, 2, 2, 4, "stem")
        for i, (dx, dy) in enumerate(((3, 0), (-3, 1), (0, 3), (1, -3), (-2, -2), (2, 2))):
            for t in range(1, 5):
                x, y = int(round(dx * t / 4)), int(round(dy * t / 4))
                out.setdefault("head", []).append((x, y, 5 + t, "trap"))
            out.setdefault("head", []).append((dx, dy, 10, "dew"))
    elif kind == "butterwort":
        box(out, "body", -1, -1, 1, 2, 2, 2, "stem")
        for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
            box(out, bone, 1 if sgn > 0 else -8, -3, 2, 7, 6, 1, "trap")
            box(out, bone, 2 if sgn > 0 else -7, -2, 3, 5, 4, 1, "dew")
        box(out, "head", -1, -1, 3, 2, 2, 6, "stem")
        box(out, "head", -2, -2, 9, 4, 4, 2, "flower_p")
    elif kind in ("bladderwort", "corkscrew"):
        box(out, "body", -1, -1, 1, 2, 2, 6, "stem")
        for i in range(5):
            z = 2 + i * 2
            box(out, "head", (2 if i % 2 else -4), -1, z, 2, 2, 2, "bladder")
        box(out, "head", -1, -1, 7, 2, 2, 3, "stem")
        box(out, "head", -2, -2, 10, 4, 4, 1, "flower_y")
    return out


ANIMALS = {
    "dog": dict(fur="fur_b", belly="fur_w", tail="bushy", ears="down"), "cat": dict(fur="fur_g", size=0.8, tail="long"),
    "sheep": dict(fur="wool", belly="fur_k", ears="down"), "cow": dict(fur="fur_w", spots="fur_k", size=1.3, horns="horn", ears="down"),
    "goat": dict(fur="fur_g", horns="horn", tail="short"), "pig": dict(fur="fur_p", snout=3, tail="long", ears="down"),
    "rabbit": dict(fur="fur_w", size=0.6, ears="long", tail="short"), "fox": dict(fur="fur_o", belly="fur_w", tail="bushy", size=0.8),
    "deer": dict(fur="fur_b", belly="fur_w", size=1.2, horns="antler", legs=4), "bear": dict(fur="fur_b", size=1.5, ears="up"),
    "wolf": dict(fur="fur_g", belly="fur_w", tail="bushy"), "horse": dict(fur="fur_b", size=1.4, mane="fur_k", tail="long", ears="up"),
    "frog": dict(fur="scale", belly="belly", size=0.5, snout=1, tail=None, ears=None), "turtle": dict(fur="shell", belly="belly", size=0.6, tail="short", ears=None),
    "squirrel": dict(fur="fur_r", size=0.5, tail="bushy", ears="up"), "mouse": dict(fur="fur_g", size=0.35, tail="long", ears="up"),
    "hedgehog": dict(fur="fur_b", size=0.5, spots="fur_k", ears=None, tail=None), "donkey": dict(fur="fur_g", size=1.2, ears="long", tail="long"),
    "mule": dict(fur="fur_b", size=1.3, ears="long", tail="long", mane="fur_k"), "lizard": dict(fur="scale", size=0.45, tail="long", ears=None, snout=3),
    "raccoon": dict(fur="fur_g", belly="fur_w", tail="bushy", spots="fur_k", size=0.7), "otter": dict(fur="fur_b", belly="fur_y", size=0.7, tail="long"),
    "badger": dict(fur="fur_k", belly="fur_w", size=0.8, spots="fur_w"), "boar": dict(fur="fur_k", size=1.1, snout=3, horns="tooth"),
    "llama": dict(fur="fur_w", size=1.2, ears="up", tail="short", mane="fur_w"), "yak": dict(fur="fur_b", size=1.5, horns="horn", mane="fur_k"),
    "moose": dict(fur="fur_b", size=1.6, horns="antler", snout=3), "bison": dict(fur="fur_b", size=1.5, mane="fur_k", horns="horn"),
    "reindeer": dict(fur="fur_g", belly="fur_w", size=1.2, horns="antler"), "camel": dict(fur="fur_y", size=1.4, ears="up", tail="long"),
    "panda": dict(fur="fur_w", spots="fur_k", size=1.1, ears="up"), "koala": dict(fur="fur_g", size=0.6, ears="up", tail=None),
    "beaver": dict(fur="fur_b", size=0.7, tail="short", snout=2), "skunk": dict(fur="fur_k", spots="fur_w", size=0.6, tail="bushy"),
    "porcupine": dict(fur="fur_b", spots="fur_y", size=0.6), "armadillo": dict(fur="shell", belly="belly", size=0.6, tail="long"),
    "capybara": dict(fur="fur_b", size=1.0, ears="down", tail=None), "ferret": dict(fur="fur_y", size=0.4, tail="long"),
    "piglet": dict(fur="fur_p", size=0.5, snout=2, tail="long"), "lamb": dict(fur="wool", belly="fur_k", size=0.5),
    "calf": dict(fur="fur_w", spots="fur_k", size=0.7, ears="down"), "kid_goat": dict(fur="fur_g", size=0.5, tail="short"),
    "puppy": dict(fur="fur_b", belly="fur_w", size=0.5, tail="bushy", ears="down"), "kitten": dict(fur="fur_g", size=0.45, tail="long"),
    "tortoise": dict(fur="shell2", belly="belly", size=0.9, tail="short", ears=None),
    "bobcat": dict(fur="fur_y", spots="fur_b", size=0.8, tail="short", ears="up"), "lynx": dict(fur="fur_g", spots="fur_k", size=0.9, tail="short", ears="long"),
    "flying_squirrel": dict(fur="fur_g", belly="fur_w", size=0.45, tail="bushy", mane="fur_g"), "monkey": dict(fur="fur_b", belly="skin", size=0.7, tail="long", ears="up"),
    "wolverine": dict(fur="fur_k", spots="fur_y", size=0.9, tail="bushy"), "honey_badger": dict(fur="fur_k", mane="fur_w", size=0.8),
    "lion": dict(fur="fur_y", mane="fur_b", size=1.3, tail="long"), "tiger": dict(fur="fur_o", spots="fur_k", belly="fur_w", size=1.3, tail="long"),
    "cougar": dict(fur="fur_y", belly="fur_w", size=1.1, tail="long"), "leopard": dict(fur="fur_y", spots="fur_k", size=1.1, tail="long"),
    "snake": dict(fur="scale", size=0.3, tail="long", ears=None, legs=0, snout=3), "python": dict(fur="fur_b", spots="fur_y", size=0.4, tail="long", ears=None, legs=0, snout=3),
    "mammoth": dict(fur="fur_b", size=1.8, horns="tooth", mane="fur_b", snout=4), "sabretooth": dict(fur="fur_y", size=1.3, horns="tooth", tail="short"),
    "dodo": dict(fur="fur_g", belly="fur_w", size=0.7, legs=2, snout=3, tail="short", ears=None), "giant_sloth": dict(fur="fur_b", size=1.6, tail="short", ears="up"),
    "dire_wolf": dict(fur="fur_k", belly="fur_g", size=1.3, tail="bushy"), "glyptodon": dict(fur="shell", belly="belly", size=1.4, tail="long", ears=None),
    "moa": dict(fur="fur_b", size=1.5, legs=2, snout=2, tail=None, ears=None), "thylacine": dict(fur="fur_y", spots="fur_k", size=0.9, tail="long"),
    "gorilla": dict(fur="fur_k", belly="fur_g", size=1.3, tail=None, ears="up"), "lemur": dict(fur="fur_g", belly="fur_w", size=0.5, tail="long", ears="up"),
    "chimp": dict(fur="fur_k", belly="skin", size=0.8, tail=None, ears="up"), "sloth": dict(fur="fur_g", size=0.6, tail=None, ears="up"),
    # the ground life: burrowers (Richey 14:58 "animals that live in the ground")
    "mole": dict(fur="fur_k", size=0.4, snout=2, tail="short", ears=None), "gopher": dict(fur="fur_b", size=0.45, tail="short", ears="up"),
    "prairie_dog": dict(fur="fur_y", size=0.5, tail="short", ears="up"), "groundhog": dict(fur="fur_b", size=0.7, tail="short", ears="up"),
    "meerkat": dict(fur="fur_y", belly="fur_w", size=0.5, tail="long", ears="up"), "vole": dict(fur="fur_g", size=0.3, tail="short", ears="up"),
    "mole_rat": dict(fur="fur_p", size=0.35, snout=2, tail="long", ears=None), "chipmunk": dict(fur="fur_r", spots="fur_k", size=0.35, tail="bushy"),
    "wombat": dict(fur="fur_b", size=0.8, tail=None, ears="up"), "aardvark": dict(fur="fur_g", size=0.9, snout=4, tail="long", ears="long"),
    "pangolin": dict(fur="shell2", belly="belly", size=0.7, tail="long", ears=None), "echidna": dict(fur="fur_b", spots="fur_y", size=0.5, snout=3, ears=None, tail=None),
    "burrowing_owl": dict(fur="fur_b", belly="fur_w", size=0.5, legs=2, snout=1, tail="short"), "gila_monster": dict(fur="fur_k", spots="fur_o", size=0.5, tail="long", ears=None),
    "desert_tortoise": dict(fur="shell", belly="belly", size=0.6, tail="short", ears=None), "fennec_fox": dict(fur="fur_y", belly="fur_w", size=0.5, ears="long", tail="bushy"), "salamander": dict(fur="fur_o", spots="fur_k", size=0.4, tail="long", ears=None),
}
BIRDS = {
    "robin": dict(feather="feather_br", belly="feather_r", size=0.6), "jay": dict(feather="feather_b", belly="feather_w", crest="feather_b", size=0.7),
    "owl": dict(feather="feather_br", belly="feather_w", size=1.0, beak_len=1, crest="feather_br"), "crow": dict(feather="feather_k", belly="feather_k", size=0.9),
    "hummingbird": dict(feather="feather_g", belly="feather_w", size=0.4, beak_len=4, wing_len=4), "heron": dict(feather="feather_w", belly="feather_w", size=1.1, legs_h=8, beak_len=5),
    "parrot": dict(feather="feather_r", belly="feather_y", size=0.8, crest="feather_g"), "eagle": dict(feather="feather_br", belly="feather_w", size=1.3, wing_len=10),
    "seagull": dict(feather="feather_w", belly="feather_w", size=0.9, wing_len=8), "finch": dict(feather="feather_y", belly="feather_w", size=0.5),
    "duck": dict(feather="feather_g", belly="feather_br", size=0.9, legs_h=2, beak_len=3), "swan": dict(feather="feather_w", belly="feather_w", size=1.2, legs_h=2, tail_len=2),
    "woodpecker": dict(feather="feather_k", belly="feather_w", crest="feather_r", size=0.7, beak_len=3), "pigeon": dict(feather="feather_g", belly="feather_w", size=0.8),
    "kingfisher": dict(feather="feather_b", belly="feather_o" if "feather_o" in PAL else "feather_y", size=0.6, beak_len=4), "hen": dict(feather="feather_br", belly="feather_w", size=0.9, crest="feather_r", legs_h=3, wing_len=3),
    "rooster": dict(feather="feather_r", belly="feather_k", size=1.0, crest="feather_r", tail_len=5, wing_len=3), "penguin": dict(feather="feather_k", belly="feather_w", size=0.9, legs_h=1, wing_len=3),
}
BEES = {"honeybee": dict(size=1.0), "bumblebee": dict(size=1.4), "hornet": dict(size=1.3, body=("bee_y", "fur_b")), "queen_bee": dict(size=1.8),
        "sweat_bee": dict(size=0.7, body=("feather_g", "bee_k")), "mason_bee": dict(size=0.9, body=("feather_b", "bee_k")), "wasp": dict(size=1.1, body=("bee_y", "bee_k")),
        "carpenter_bee": dict(size=1.3, stripes=False, body=("bee_k", "bee_k")), "stingless_bee": dict(size=0.6, body=("fur_b", "bee_k"))}
FISH = {"rillperch": dict(body="feather_g", fin="feather_y", size=0.8), "glassfin": dict(body="wing_c", fin="feather_b", size=0.7),
        "skytrout": dict(body="feather_b", fin="feather_w", size=1.0), "ember_koi": dict(body="feather_r", fin="feather_y", size=1.1),
        "rainbow_eel": dict(body="blossom", fin="feather_b", size=0.8, long=True), "basin_ray": dict(body="fur_g", fin="fur_k", size=1.3),
        "lantern_carp": dict(body="feather_y", fin="feather_r", size=1.0), "stream_minnow": dict(body="fur_g", fin="feather_w", size=0.4)}
ZOMBIES = {
    "zombie_villager": dict(skin="zombie", cloth="fur_b", rot=1), "zombie_farmer": dict(skin="zombie", cloth="fur_y", hat="hay", rot=1, tool="plank"),
    "zombie_miner": dict(skin="zombie", cloth="fur_g", hat="iron", rot=1, tool="iron"), "zombie_knight": dict(skin="zombie", cloth="iron", hat="iron", rot=1),
    "zombie_king": dict(skin="zombie", cloth="pitcher_r", hat="gold", rot=2), "zombie_pirate": dict(skin="zombie", cloth="fur_k", hat="fur_k", rot=1, tool="tooth"),
    "zombie_bloated": dict(skin="zombie", cloth="fur_g", rot=2, size=1.3), "zombie_crawler": dict(skin="zombie", cloth="fur_b", rot=2, crawler=True),
    "zombie_runner": dict(skin="zombie", cloth="fur_w", rot=0, size=0.9, arms_out=False), "zombie_bride": dict(skin="zombie", cloth="fur_w", hair="fur_w", rot=1),
    "zombie_smith": dict(skin="zombie", cloth="fur_k", rot=1, tool="anvil"), "zombie_baker": dict(skin="zombie", cloth="fur_w", hat="fur_w", rot=1),
    "zombie_sailor": dict(skin="zombie", cloth="feather_b", hat="fur_w", rot=1), "zombie_hunter": dict(skin="zombie", cloth="fur_g", hat="fur_g", rot=0, tool="trunk"),
    "zombie_giant": dict(skin="zombie", cloth="fur_b", rot=2, size=1.8), "zombie_child": dict(skin="zombie", cloth="fur_p", rot=1, size=0.6),
    "zombie_beekeeper": dict(skin="zombie", cloth="fur_w", hat="bee_y", rot=1), "zombie_skeleton": dict(skin="tooth", cloth="tooth", rot=0, arms_out=True),
    "zombie_frost": dict(skin="clearbell", cloth="fur_w", rot=0), "zombie_ember": dict(skin="forge", cloth="fur_k", rot=2),
    "zombie_crystal": dict(skin="crystal", cloth="crystal2", rot=0), "zombie_mud": dict(skin="soil", cloth="dirt", rot=2),
    "ghoul": dict(skin="fur_g", cloth="fur_k", rot=2, size=1.1, arms_out=True), "wraith": dict(skin="smoke", cloth="smoke2", rot=0, crawler=False, arms_out=True),
}
DINOS = ("trex", "raptor", "allosaurus", "carnotaurus", "triceratops", "stegosaurus", "ankylosaurus", "brontosaurus", "pterodactyl", "quetzal")
SEA = ("shark", "dolphin", "orca", "whale", "narwhal", "octopus", "squid", "jellyfish", "crab", "lobster", "sea_turtle", "seahorse", "manta", "eel",
       "clownfish", "pufferfish", "swordfish", "anglerfish", "starfish")
INSECTS = ("butterfly", "moth", "dragonfly", "firefly", "ladybug", "beetle", "grasshopper", "cicada", "mosquito",
           "ant", "termite", "spider", "scorpion", "centipede", "earthworm", "snail", "slug", "woodlouse", "tick")
PLANTS = ("venus_flytrap", "pitcher", "monkey_cup", "sun_pitcher", "cobra_lily", "moccasin", "sundew", "dewy_pine", "rainbow_plant", "butterwort", "bladderwort", "corkscrew", "waterwheel")
SPECIES = {"animal": tuple(ANIMALS), "bird": tuple(BIRDS), "bee": tuple(BEES), "plant": PLANTS, "fish": tuple(FISH),
           "zombie": tuple(ZOMBIES), "dino": DINOS, "sea": SEA, "insect": INSECTS}
EXTRA = {}   # family -> (names, plan_fn): other catalogues (voxel_dragons) register here and ride the same rig/clips/export


def plan(species):
    if species in ANIMALS:
        return _quadruped(**ANIMALS[species])
    if species in BIRDS:
        return _bird(**BIRDS[species])
    if species in BEES:
        return _bee(**BEES[species])
    if species in PLANTS:
        return _plant(species)
    if species in FISH:
        return _fish(**FISH[species])
    if species in ZOMBIES:
        return _biped(**ZOMBIES[species])
    if species in DINOS:
        return _dino(species)
    if species in SEA:
        return _sea(species)
    if species in INSECTS:
        return _insect(species)
    for names, fn in EXTRA.values():
        if species in names:
            return fn(species)
    raise KeyError(species)


def family_of(species):
    for f, names in SPECIES.items():
        if species in names:
            return f
    return next(f for f, (names, _) in EXTRA.items() if species in names)


def all_species():
    return [s for names in SPECIES.values() for s in names] + [s for names, _ in EXTRA.values() for s in names]


# ---- Blender: mesh, rig, clips, export -------------------------------------------------------------------------

def build(species, out_dir, scale=10.0, keep=False):
    """One rigged voxel character: mesh (greedy quads, vertex colours, vertex groups per bone) + 8-bone armature +
    Idle/Walk/Attack/Hurt NLA clips, exported as GLB (animations) and FBX. 10 cm voxels -> `scale` cm per voxel."""
    import bmesh
    import bpy
    parts = plan(species)
    fam = family_of(species)
    name = "Creature_" + "".join(w.capitalize() for w in species.split("_"))
    for ob in list(bpy.data.objects):
        if ob.name.startswith(name):
            bpy.data.objects.remove(ob, do_unlink=True)
    # mesh: one bmesh, a vertex group per bone (rectangles never straddle bones because we mesh per bone)
    bm = bmesh.new()
    layer = bm.loops.layers.color.new("Col")
    deform = bm.verts.layers.deform.verify()
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    groups = {}
    for bone in [b[0] for b in BONES]:
        groups[bone] = ob.vertex_groups.new(name=bone).index
    for bone, voxels in parts.items():
        cache = {}
        for axis, sign, sl, u0, v0, w, h, c in V.greedy_quads(voxels):
            ua, va = [a for a in (0, 1, 2) if a != axis]
            col = tuple(q ** (1.0 / 2.2) for q in PAL[c]) + (1.0,)
            plane = sl + (1 if sign > 0 else 0)
            corners = []
            for (du, dv) in ((0, 0), (w, 0), (w, h), (0, h)):
                p = [0, 0, 0]
                p[axis] = plane
                p[ua] = u0 + du
                p[va] = v0 + dv
                corners.append(tuple(p))
            if (sign > 0) == (axis == 1):
                corners.reverse()
            vs = []
            for p in corners:
                v = cache.get(p)
                if v is None:
                    v = bm.verts.new((p[0] * scale / 100.0, p[1] * scale / 100.0, p[2] * scale / 100.0))   # metres for the GLB
                    v[deform][groups[bone]] = 1.0
                    cache[p] = v
                vs.append(v)
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            for loop in f.loops:
                loop[layer] = col
    bm.to_mesh(me)
    bm.free()
    # armature with the shared 8-bone layout, scaled to the creature's height
    zmax = max(z for vox in parts.values() for _, _, z, _ in vox) * scale / 100.0
    ymax = max(y for vox in parts.values() for _, y, _, _ in vox) * scale / 100.0
    k = max(zmax, 0.3) / 1.0
    arm = bpy.data.armatures.new(name + "_Rig")
    rig = bpy.data.objects.new(name + "_Rig", arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bn, hd, tl, parent in BONES:
        b = arm.edit_bones.new(bn)
        b.head = (hd[0] * k, hd[1] * k * (ymax / 0.3 if bn == "head" else 1.0), hd[2] * k)
        b.tail = (tl[0] * k, tl[1] * k * (ymax / 0.3 if bn == "head" else 1.0), tl[2] * k)
        if parent:
            b.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.parent = rig
    mod = ob.modifiers.new("Rig", "ARMATURE")
    mod.object = rig
    for p in rig.pose.bones:
        p.rotation_mode = "XYZ"
    # clips: the same names and feel as the Portal creatures; plants snap instead of walking
    for clip, n in CLIPS:
        if fam == "plant" and clip in ("Walk", "Run", "Jump", "Turn"):
            continue
        if fam in ("fish", "sea") and clip == "Jump":
            continue
        rig.animation_data_create()
        act = bpy.data.actions.new(name + "_" + clip)
        rig.animation_data.action = act
        for f in range(1, n + 2, 6 if clip == "Walk" else 3):
            ph = (f - 1) / n * 2 * math.pi
            for p in rig.pose.bones:
                p.location = (0, 0, 0)
                p.rotation_euler = (0, 0, 0)
            rig.pose.bones["body"].location.z = 0.02 * k * math.sin(ph)
            if clip == "Idle":
                if fam == "dragon":                                                 # hovering: slow wingbeats, tail sway
                    for side in ("L", "R"):
                        rig.pose.bones["wing." + side].rotation_euler.y = 0.7 * math.sin(ph * 2) * (1 if side == "L" else -1)
                    rig.pose.bones["body"].location.z = 0.25 * k + 0.06 * k * math.sin(ph * 2)
                    rig.pose.bones["tail"].rotation_euler.z = 0.25 * math.sin(ph)
                    rig.pose.bones["head"].rotation_euler.x = 0.1 * math.sin(ph)
                elif fam == "owl":                                                  # the owl look: slow head swivel, blink-bob
                    rig.pose.bones["head"].rotation_euler.z = 1.2 * math.sin(ph)
                    rig.pose.bones["head"].rotation_euler.x = 0.1 * math.sin(ph * 3)
                    rig.pose.bones["body"].location.z = 0.01 * k * math.sin(ph * 2)
                elif fam == "bee" or (fam == "insect" and len(parts.get("wing.L", [])) > 0):
                    for side in ("L", "R"):
                        rig.pose.bones["wing." + side].rotation_euler.y = 0.9 * math.sin(ph * 6) * (1 if side == "L" else -1)
                    rig.pose.bones["body"].location.z = 0.05 * k * math.sin(ph) + 0.3 * k
                elif fam == "plant":
                    rig.pose.bones["body"].rotation_euler.y = 0.08 * math.sin(ph)
                    rig.pose.bones["head"].rotation_euler.x = 0.05 * math.sin(ph * 2)
                else:
                    rig.pose.bones["head"].rotation_euler.x = 0.08 * math.sin(ph)
                    rig.pose.bones["tail"].rotation_euler.z = 0.3 * math.sin(ph * 2)
            elif clip in ("Walk", "Run") and fam == "dragon":                          # Walk = cruise, Run = dive-speed
                fast = 1.6 if clip == "Run" else 1.0
                for side, sgn in (("L", 1), ("R", -1)):
                    rig.pose.bones["wing." + side].rotation_euler.y = 1.0 * math.sin(ph * 2 * fast) * sgn
                    rig.pose.bones["leg." + side].rotation_euler.x = -0.6                 # legs tucked in flight
                rig.pose.bones["body"].location.z = 0.25 * k + 0.08 * k * math.sin(ph * 2 * fast)
                rig.pose.bones["body"].rotation_euler.x = 0.1 * fast
                rig.pose.bones["tail"].rotation_euler.x = 0.2 * math.sin(ph * 2 * fast)
                rig.pose.bones["head"].rotation_euler.x = -0.1 * fast
            elif clip == "Run" and fam not in ("plant",):
                for side, sgn in (("L", 1), ("R", -1)):
                    rig.pose.bones["leg." + side].rotation_euler.x = 0.8 * math.sin(ph) * sgn
                    rig.pose.bones["wing." + side].rotation_euler.y = (1.1 if fam in ("bird", "bee", "owl") else 0.4) * math.sin(ph * 2) * sgn
                rig.pose.bones["body"].location.z = 0.06 * k * abs(math.sin(ph))
                rig.pose.bones["body"].rotation_euler.x = 0.12                     # leans into the run
                rig.pose.bones["head"].rotation_euler.x = 0.15 * math.sin(ph * 2)
                rig.pose.bones["tail"].rotation_euler.z = 0.4 * math.sin(ph * 2)
            elif clip == "Turn":
                rig.pose.bones["head"].rotation_euler.z = 0.6 * math.sin(ph / 2)   # the head leads
                rig.pose.bones["body"].rotation_euler.z = 0.5 * math.sin(ph / 2 - 0.4)
                for side, sgn in (("L", 1), ("R", -1)):
                    rig.pose.bones["leg." + side].rotation_euler.x = 0.25 * math.sin(ph) * sgn
            elif clip == "Jump" and fam not in ("plant", "fish", "sea"):
                h = max(0.0, math.sin(ph)) if ph < math.pi else 0.0
                rig.pose.bones["body"].location.z = 0.6 * k * h - (0.08 * k * max(0.0, math.sin(ph - math.pi)))   # arc, then land squash
                for side in ("L", "R"):
                    rig.pose.bones["leg." + side].rotation_euler.x = -0.7 * h                     # tuck
                rig.pose.bones["head"].rotation_euler.x = -0.2 * h
            elif clip == "Action":
                if fam == "animal":
                    rig.pose.bones["head"].rotation_euler.x = 0.7 * (1 - math.cos(ph)) / 2          # graze
                elif fam == "bird":
                    rig.pose.bones["head"].rotation_euler.x = 0.9 * max(0.0, math.sin(ph * 3))      # peck
                elif fam == "bee":
                    rig.pose.bones["tail"].rotation_euler.x = 0.8 * max(0.0, math.sin(ph))          # sting
                    rig.pose.bones["body"].rotation_euler.x = -0.4 * max(0.0, math.sin(ph))
                elif fam in ("fish", "sea"):
                    rig.pose.bones["body"].rotation_euler.y = 2 * math.pi * (ph / (2 * math.pi))    # a full flip
                elif fam == "zombie":
                    for side in ("L", "R"):
                        rig.pose.bones["wing." + side].rotation_euler.x = -0.6 * (1 - math.cos(ph)) / 2   # grab
                    rig.pose.bones["head"].rotation_euler.x = 0.3 * math.sin(ph)
                elif fam == "owl":                                                              # silent swoop: wings wide, dip, talons forward
                    dip = (1 - math.cos(ph)) / 2
                    for side in ("L", "R"):
                        rig.pose.bones["wing." + side].rotation_euler.y = 1.3 * dip * (1 if side == "L" else -1)
                        rig.pose.bones["leg." + side].rotation_euler.x = -0.9 * dip
                    rig.pose.bones["body"].location.z = 0.3 * k * dip - 0.1 * k * max(0.0, math.sin(ph * 2))
                    rig.pose.bones["body"].rotation_euler.x = 0.3 * dip
                elif fam == "dragon":                                                           # breath: rear back, then pour it out
                    rear = max(0.0, math.sin(ph)) if ph < math.pi else 0.0
                    rig.pose.bones["head"].rotation_euler.x = -0.6 * rear + 0.5 * max(0.0, math.sin(ph - math.pi))
                    rig.pose.bones["body"].rotation_euler.x = -0.2 * rear
                    rig.pose.bones["body"].location.z = 0.25 * k
                    for side in ("L", "R"):
                        rig.pose.bones["wing." + side].rotation_euler.y = 0.8 * (1 if side == "L" else -1) * (0.5 + 0.5 * rear)
                elif fam == "dino":
                    rig.pose.bones["head"].rotation_euler.z = 0.5 * math.sin(ph)                    # roar sweep
                    rig.pose.bones["head"].rotation_euler.x = -0.4 * max(0.0, math.sin(ph))
                else:
                    rig.pose.bones["head"].rotation_euler.x = -0.9 * (1 - math.cos(ph)) / 2
            elif clip == "Walk" and fam == "fish":
                rig.pose.bones["tail"].rotation_euler.z = 0.5 * math.sin(ph * 2)
                rig.pose.bones["body"].rotation_euler.z = 0.1 * math.sin(ph * 2)
                rig.pose.bones["body"].location.z = 0.3 * k + 0.03 * k * math.sin(ph)
            elif clip == "Walk":
                for side, sgn in (("L", 1), ("R", -1)):
                    rig.pose.bones["leg." + side].rotation_euler.x = (0.3 if fam == "zombie" else 0.45) * math.sin(ph) * sgn
                if fam == "zombie":
                    rig.pose.bones["body"].rotation_euler.z = 0.15 * math.sin(ph)              # the shamble
                    rig.pose.bones["wing." + side].rotation_euler.y = (0.8 if fam in ("bird", "owl") else 0.15) * math.sin(ph * (2 if fam in ("bird", "owl") else 1)) * sgn
                rig.pose.bones["body"].location.z = 0.03 * k * abs(math.sin(ph))
                rig.pose.bones["head"].rotation_euler.x = 0.1 * math.sin(ph * 2)
            elif clip == "Attack":
                if fam == "plant":
                    rig.pose.bones["head"].rotation_euler.x = -0.9 * (1 - math.cos(ph)) / 2      # the trap snaps shut
                    for side in ("L", "R"):
                        rig.pose.bones["wing." + side].rotation_euler.y = 0.3 * (1 - math.cos(ph)) / 2 * (1 if side == "L" else -1)
                else:
                    rig.pose.bones["head"].rotation_euler.x = -0.4 * (1 - math.cos(ph)) / 2
                    rig.pose.bones["body"].location.y = 0.08 * k * math.sin(ph)
            elif clip == "Hurt":
                rig.pose.bones["body"].rotation_euler.z = 0.2 * math.sin(ph)
                rig.pose.bones["body"].location.z = -0.02 * k * (1 - math.cos(ph))
            for p in rig.pose.bones:
                p.keyframe_insert(data_path="rotation_euler", frame=f)
                p.keyframe_insert(data_path="location", frame=f)
        if clip in ("Walk", "Run") and fam != "dragon":      # flyers glide smoothly; walkers keep the stepped feel
            for fc in act.fcurves:
                for key in fc.keyframe_points:
                    key.interpolation = "CONSTANT"        # the stepped voxel feel, like the Portal creatures
        tr = rig.animation_data.nla_tracks.new()
        tr.name = clip
        tr.strips.new(clip, 1, act)
        rig.animation_data.action = None
    os.makedirs(out_dir, exist_ok=True)
    for o in bpy.data.objects:
        o.select_set(o in (ob, rig))
    bpy.context.view_layer.objects.active = ob
    glb = os.path.join(out_dir, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_animations=True, export_animation_mode="NLA_TRACKS", export_yup=True)
    bpy.ops.export_scene.fbx(filepath=glb[:-4] + ".fbx", use_selection=True, add_leaf_bones=False, bake_anim=True, bake_anim_use_nla_strips=True, axis_forward="-Y", axis_up="Z")
    clip_names = [t.name for t in rig.animation_data.nla_tracks]
    if not keep:                      # exports slow down as actions pile up in the scene: drop this creature's
        for o in (ob, rig):
            bpy.data.objects.remove(o, do_unlink=True)
        for a in list(bpy.data.actions):
            if a.name.startswith(name + "_"):
                bpy.data.actions.remove(a)
        for blk in (bpy.data.meshes, bpy.data.armatures):
            for d in list(blk):
                if d.users == 0:
                    blk.remove(d)
    import json
    with open(glb[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"species": species, "family": fam, "voxel_cm": scale, "height_m": round(zmax, 2), "bones": [b[0] for b in BONES],
                   "clips": clip_names, "voxels": {b: len(v) for b, v in parts.items()}}, f, indent=1)
    return {"species": species, "glb": glb, "height_m": zmax}
