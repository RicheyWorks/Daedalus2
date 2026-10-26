# SPDX-License-Identifier: MIT
"""Owls for Daedalus2 — 504 rigged voxel owls (14 species x 6 plumages x 6 variants) on the shared voxel_creatures
rig, family "owl": Idle (head swivel) / Walk (fly) / Run (fast fly) / Attack / Hurt / Turn / Jump / Action (silent
swoop). Registers in voxel_creatures.EXTRA; species name = "owl_<species>_<plumage>_<nn>".

Species carry the real silhouettes: ear tufts (great horned, long-eared, screech, eagle), heart face (barn), the
tiny elf owl, long-legged burrowing owl, the big round-faced snowy / great grey. Plumage patterns (plain, speckled,
barred, streaked, masked, dusted) and the variant (size, eye colour, wings folded or spread mid-flight, tail length,
brow ridge, spectacles) are deterministic from the name.
Night-side of the ecology: owls hunt the burrowers and insects (voxel_creatures), roost in Ancient trees
(voxel_flora), scout and warn in Ultra's Living Island Defense; owl eggs hatch in voxel_eggs' bird pool.
"""
import random

import voxel_creatures as VC

box = VC.box
PAL = VC.PAL
PAL.update({
    "owl_tawny": (0.62, 0.45, 0.26), "owl_cream": (0.93, 0.88, 0.74), "owl_grey": (0.55, 0.55, 0.52), "owl_white": (0.97, 0.97, 0.95),
    "owl_dark": (0.28, 0.22, 0.16), "owl_rust": (0.70, 0.38, 0.18), "owl_buff": (0.85, 0.72, 0.50), "owl_slate": (0.40, 0.42, 0.45),
    "owl_bark": (0.45, 0.35, 0.25), "owl_smoke": (0.68, 0.66, 0.62), "owl_face": (0.95, 0.92, 0.85), "owl_face_d": (0.75, 0.62, 0.45),
    "owl_eye_y": (1.00, 0.85, 0.10), "owl_eye_o": (1.00, 0.55, 0.05), "owl_eye_k": (0.08, 0.06, 0.06), "owl_beak": (0.25, 0.22, 0.20),
    "owl_talon": (0.20, 0.18, 0.16), "owl_speck": (0.30, 0.25, 0.20), "owl_bar": (0.38, 0.30, 0.22),
})
SPECIES = {
    # species: (body colour, face colour, belly, size, ear tufts, face shape, legs_h, tail)
    "barn":         ("owl_buff",  "owl_face",   "owl_white", 1.0, False, "heart", 3, 3),
    "snowy":        ("owl_white", "owl_white",  "owl_white", 1.3, False, "round", 2, 3),
    "great_horned": ("owl_tawny", "owl_face_d", "owl_cream", 1.3, True,  "round", 3, 4),
    "screech":      ("owl_grey",  "owl_smoke",  "owl_cream", 0.7, True,  "round", 2, 2),
    "barred":       ("owl_bark",  "owl_face",   "owl_cream", 1.1, False, "round", 3, 4),
    "eagle":        ("owl_rust",  "owl_face_d", "owl_buff",  1.5, True,  "round", 3, 4),
    "elf":          ("owl_grey",  "owl_face",   "owl_cream", 0.5, False, "round", 2, 2),
    "burrowing":    ("owl_tawny", "owl_face",   "owl_cream", 0.8, False, "round", 6, 2),
    "long_eared":   ("owl_bark",  "owl_face_d", "owl_buff",  1.0, True,  "round", 3, 4),
    "short_eared":  ("owl_buff",  "owl_face",   "owl_cream", 1.0, False, "round", 3, 4),
    "spectacled":   ("owl_dark",  "owl_face",   "owl_buff",  1.1, False, "round", 3, 3),
    "great_grey":   ("owl_slate", "owl_smoke",  "owl_grey",  1.5, False, "round", 2, 5),
    "tawny":        ("owl_rust",  "owl_face_d", "owl_cream", 1.0, False, "round", 3, 3),
    "pygmy":        ("owl_bark",  "owl_face",   "owl_cream", 0.6, False, "round", 2, 3),
}
PLUMAGES = ("plain", "speckled", "barred", "streaked", "masked", "dusted")
EYES = ("owl_eye_y", "owl_eye_o", "owl_eye_k")
VARIANTS = 6


def names():
    return tuple("owl_%s_%s_%02d" % (sp, pl, v) for sp in SPECIES for pl in PLUMAGES for v in range(1, VARIANTS + 1))


def spec(species):
    sp, pl, v = species[len("owl_"):].rsplit("_", 2)
    v = int(v)
    rng = random.Random(list(SPECIES).index(sp) * 1000 + PLUMAGES.index(pl) * 10 + v)
    body, face, belly, size, tufts, shape, legs_h, tail = SPECIES[sp]
    return {
        "species": sp, "plumage": pl, "variant": v, "body": body, "face": face, "belly": belly,
        "size": size * (0.85 + 0.3 * rng.random()), "tufts": tufts, "face_shape": shape, "legs_h": legs_h, "tail": tail + rng.randint(-1, 1),
        "eye": EYES[(v + list(SPECIES).index(sp)) % 3] if sp != "barn" else "owl_eye_k",
        "wings": "spread" if v % 2 == 0 else "folded", "brow": rng.random() < 0.5, "spectacles": sp == "spectacled" or rng.random() < 0.15,
        "seed": rng.random(),
    }


def plan(species):
    """Voxel plan per bone (10 cm voxels). Faces +Y, feet at z=0. Owls are upright: a tall oval body, big head."""
    o = spec(species)
    s = o["size"]
    out = {}
    W, D, H = max(4, int(5 * s)), max(4, int(5 * s)), max(5, int(7 * s))
    lh = o["legs_h"]
    body, face, belly = o["body"], o["face"], o["belly"]
    # body: oval column — narrower at the top and bottom
    for z in range(H):
        t = z / max(1, H - 1)
        shrink = 1 if (t < 0.15 or t > 0.85) else 0
        box(out, "body", -W // 2 + shrink, -D // 2 + shrink, lh + z, W - 2 * shrink, D - 2 * shrink, 1, body)
    box(out, "body", -W // 2 + 1, D // 2 - 1, lh + 1, W - 2, 1, H - 2, belly)                   # belly front
    rng = random.Random(int(o["seed"] * 1e6))
    if o["plumage"] == "speckled":
        for _ in range(6 + int(4 * s)):
            box(out, "body", rng.randint(-W // 2, W // 2 - 1), rng.randint(-D // 2, D // 2 - 1), lh + rng.randint(1, H - 2), 1, 1, 1, "owl_speck")
    elif o["plumage"] == "barred":
        for z in range(lh + 1, lh + H - 1, 2):
            box(out, "body", -W // 2, -D // 2, z, W, 1, 1, "owl_bar")
            box(out, "body", -W // 2 + 1, D // 2 - 1, z, W - 2, 1, 1, "owl_bar")
    elif o["plumage"] == "streaked":
        for x in range(-W // 2 + 1, W // 2 - 1, 2):
            box(out, "body", x, D // 2 - 1, lh + 1, 1, 1, H - 3, "owl_speck")
    elif o["plumage"] == "dusted":
        box(out, "body", -W // 2, -D // 2, lh + H - 2, W, D, 1, "owl_smoke")
    # head: a wide block with the facial disc on the front
    hw = max(4, int(6 * s))
    hh = max(3, int(5 * s))
    hz = lh + H - 1
    box(out, "head", -hw // 2, -hw // 2 + 1, hz, hw, hw - 1, hh, body)
    if o["face_shape"] == "heart":
        box(out, "head", -hw // 2 + 1, hw // 2, hz, hw - 2, 1, hh - 1, face)
        box(out, "head", -1, hw // 2, hz, 2, 1, 1, body)                                      # the heart's notch
    else:
        box(out, "head", -hw // 2 + 1, hw // 2, hz + 1, hw - 2, 1, hh - 2, face)
        box(out, "head", -hw // 2, hw // 2, hz + 1 + (hh - 2) // 2 - 1, 1, 1, 2, face)         # disc edges
        box(out, "head", hw // 2 - 1, hw // 2, hz + 1 + (hh - 2) // 2 - 1, 1, 1, 2, face)
    if o["plumage"] == "masked":
        box(out, "head", -hw // 2 + 1, hw // 2, hz + hh - 3, hw - 2, 1, 1, "owl_dark")
    ez = hz + hh // 2
    for sx in (-hw // 2 + 1, hw // 2 - 2):
        box(out, "head", sx, hw // 2, ez, 1 if hw < 6 else 2, 1, 1 if hw < 6 else 2, o["eye"])     # big forward eyes
        if o["spectacles"]:
            box(out, "head", sx - 1, hw // 2, ez - 1, 3 if hw < 6 else 4, 1, 1, "owl_face")
            box(out, "head", sx - 1, hw // 2, ez + (1 if hw < 6 else 2), 3 if hw < 6 else 4, 1, 1, "owl_face")
    if o["brow"]:
        box(out, "head", -hw // 2 + 1, hw // 2, ez + (1 if hw < 6 else 2), hw - 2, 1, 1, "owl_dark")
    box(out, "head", 0, hw // 2, ez - 1, 1, 1, 2, "owl_beak")                                  # hooked beak between the eyes
    if o["tufts"]:
        for sx in (-hw // 2, hw // 2 - 1):
            box(out, "head", sx, -hw // 2 + 2, hz + hh, 1, 2, 2 + int(s), body)
            box(out, "head", sx, -hw // 2 + 2, hz + hh + 2 + int(s), 1, 1, 1, "owl_dark")
    # legs + talons
    for sx, bone in ((-W // 2 + 1, "leg.L"), (W // 2 - 2, "leg.R")):
        box(out, bone, sx, 0, 0, 1, 1, lh, belly if lh > 3 else body)
        box(out, bone, sx - 1, 0, 0, 3, 2, 1, "owl_talon")
        box(out, bone, sx, -1, 0, 1, 1, 1, "owl_talon")
    # wings
    span = max(5, int(8 * s))
    wz = lh + H - 3
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        if o["wings"] == "folded":
            x0 = W // 2 if sgn > 0 else -W // 2 - 1
            box(out, bone, x0, -D // 2, lh + 1, 1, D - 1, H - 2, body)                       # folded along the flank
            box(out, bone, x0, -D // 2 - 2, lh + 1, 1, 2, 2, "owl_dark")                     # primaries cross at the back
            if o["plumage"] in ("barred", "speckled"):
                for z in range(lh + 2, lh + H - 2, 2):
                    box(out, bone, x0, -D // 2, z, 1, D - 1, 1, "owl_bar")
        else:
            for i in range(span):                                                           # spread mid-flight, soft trailing edge
                x = (W // 2 + i) if sgn > 0 else (-W // 2 - 1 - i)
                depth = max(2, int((D + 2) * (1 - 0.5 * i / span)))
                box(out, bone, x, D // 2 - 1 - depth, wz + (i // 3 if i < span // 2 else (span // 2) // 3 - (i - span // 2) // 3), 1, depth, 1, body)
                if i % 2 == 1:
                    box(out, bone, x, D // 2 - 1 - depth, wz + (i // 3 if i < span // 2 else (span // 2) // 3 - (i - span // 2) // 3), 1, 1, 1, "owl_dark")
    # tail
    tl = max(2, o["tail"])
    box(out, "tail", -1, -D // 2 - tl, lh + 1, 3 if W > 4 else 2, tl, 1, body)
    box(out, "tail", -1, -D // 2 - tl, lh + 1, 3 if W > 4 else 2, 1, 1, "owl_dark")
    return out


NAMES = names()
VC.EXTRA["owl"] = (NAMES, plan)


def manifest():
    return {n: {k: v for k, v in spec(n).items() if k != "seed"} for n in NAMES}


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
    print(len(NAMES), "owls;", len(hs), "unique; empty", empty, "missing", sorted(miss))
    sys.exit(1 if miss or empty or len(hs) != len(NAMES) else 0)
