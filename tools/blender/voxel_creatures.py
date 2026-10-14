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
    "shell": (0.35, 0.50, 0.30), "shell2": (0.25, 0.38, 0.22), "scale": (0.30, 0.65, 0.35), "belly": (0.90, 0.85, 0.60),
    "trap": (0.35, 0.70, 0.30), "trap_in": (0.90, 0.30, 0.40), "tooth": (0.95, 0.95, 0.85), "pitcher": (0.60, 0.80, 0.35),
    "pitcher_r": (0.75, 0.25, 0.30), "dew": (0.85, 0.95, 1.00), "stem": (0.30, 0.55, 0.25), "lid": (0.55, 0.30, 0.45),
    "bladder": (0.45, 0.65, 0.35), "horn": (0.80, 0.75, 0.60), "hoof": (0.25, 0.20, 0.18), "antler": (0.70, 0.60, 0.45),
})
BONES = (("root", (0, 0, 0), (0, 0, 0.1), None), ("body", (0, 0, 0.3), (0, 0, 0.6), "root"), ("head", (0, 0.3, 0.6), (0, 0.3, 0.9), "body"),
         ("tail", (0, -0.3, 0.5), (0, -0.6, 0.5), "body"), ("leg.L", (0.15, 0, 0.3), (0.15, 0, 0.0), "body"), ("leg.R", (-0.15, 0, 0.3), (-0.15, 0, 0.0), "body"),
         ("wing.L", (0.2, 0, 0.6), (0.6, 0, 0.6), "body"), ("wing.R", (-0.2, 0, 0.6), (-0.6, 0, 0.6), "body"))
CLIPS = (("Idle", 48), ("Walk", 24), ("Attack", 24), ("Hurt", 24))


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
        x0 = W // 2 if sgn > 0 else -W // 2 - wing_len
        box(out, bone, x0, -D // 2 + 1, legs_h + H - 2, wing_len, D - 2, 1, feather)
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
PLANTS = ("venus_flytrap", "pitcher", "monkey_cup", "sun_pitcher", "cobra_lily", "moccasin", "sundew", "dewy_pine", "rainbow_plant", "butterwort", "bladderwort", "corkscrew", "waterwheel")
SPECIES = {"animal": tuple(ANIMALS), "bird": tuple(BIRDS), "bee": tuple(BEES), "plant": PLANTS}


def plan(species):
    if species in ANIMALS:
        return _quadruped(**ANIMALS[species])
    if species in BIRDS:
        return _bird(**BIRDS[species])
    if species in BEES:
        return _bee(**BEES[species])
    if species in PLANTS:
        return _plant(species)
    raise KeyError(species)


def family_of(species):
    return next(f for f, names in SPECIES.items() if species in names)


def all_species():
    return [s for names in SPECIES.values() for s in names]


# ---- Blender: mesh, rig, clips, export -------------------------------------------------------------------------

def build(species, out_dir, scale=10.0):
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
        if fam == "plant" and clip == "Walk":
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
                if fam == "bee":
                    for side in ("L", "R"):
                        rig.pose.bones["wing." + side].rotation_euler.y = 0.9 * math.sin(ph * 6) * (1 if side == "L" else -1)
                    rig.pose.bones["body"].location.z = 0.05 * k * math.sin(ph) + 0.3 * k
                elif fam == "plant":
                    rig.pose.bones["body"].rotation_euler.y = 0.08 * math.sin(ph)
                    rig.pose.bones["head"].rotation_euler.x = 0.05 * math.sin(ph * 2)
                else:
                    rig.pose.bones["head"].rotation_euler.x = 0.08 * math.sin(ph)
                    rig.pose.bones["tail"].rotation_euler.z = 0.3 * math.sin(ph * 2)
            elif clip == "Walk":
                for side, sgn in (("L", 1), ("R", -1)):
                    rig.pose.bones["leg." + side].rotation_euler.x = 0.45 * math.sin(ph) * sgn
                    rig.pose.bones["wing." + side].rotation_euler.y = (0.8 if fam == "bird" else 0.15) * math.sin(ph * (2 if fam == "bird" else 1)) * sgn
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
        if clip == "Walk":
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
    import json
    with open(glb[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"species": species, "family": fam, "voxel_cm": scale, "height_m": round(zmax, 2), "bones": [b[0] for b in BONES],
                   "clips": [c for c, _ in CLIPS if not (fam == "plant" and c == "Walk")], "voxels": {b: len(v) for b, v in parts.items()}}, f, indent=1)
    return {"species": species, "glb": glb, "height_m": zmax}
