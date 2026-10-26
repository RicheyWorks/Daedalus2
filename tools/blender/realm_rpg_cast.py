# SPDX-License-Identifier: MIT
"""Rigged voxel casts for the two RPG realms — all original names and designs (REALMS.md rule 4: genres and feel,
never anyone's IP).

* PORTAL REALM (the 8-bit console RPG, ADR-052): art for every type in data/art/portal/population-plan.json that is
  still `art_status: Planned` — 49 enemy types, 50 friendly types, 5 bosses — 10 individuals per type, matching the
  plan's `variant_seed` (`enemy/<TYPE>/<n>`). BLIGHT_SLIME is skipped: Codex's polished slime is already validated.
  Exported as `Mob_Portal_<TYPE>_Voxel_NN` (Codex's polish exports are `Mob_Portal_<TYPE>_Polish_NN`).
* PRISMHEART REALM (the 16-bit crystal-era party RPG, ADR-067): eight job classes (heroes), thirty monster types,
  eight summon spirits, townsfolk, and a mount — exported as `Mob_Prism_<Name>_NN`.

Every body rides voxel_creatures' shared 8-bone rig (root/body/head/tail/leg.L/R/wing.L/R = Codex monster_rig) and its
Idle/Walk/Run/Attack/Hurt/Turn/Jump/Action clips; families register in voxel_creatures.EXTRA, names in NAMES.
`spec(name)` is deterministic from the name, so any individual rebuilds alone.
"""
import random

import voxel_creatures as VC

box = VC.box
PAL = VC.PAL


def col(rgb):
    """Register an arbitrary colour and return its palette key."""
    k = "c%02x%02x%02x" % tuple(int(max(0, min(1, c)) * 255) for c in rgb)
    PAL.setdefault(k, tuple(int(max(0, min(1, c)) * 255) / 255 for c in rgb))
    return k


def tint(rgb, f):
    return tuple(max(0, min(1, c * f)) for c in rgb)


def recolor(parts, mapping):
    return {b: [(x, y, z, mapping.get(c, c)) for x, y, z, c in v] for b, v in parts.items()}


def scale_plan(parts, k):
    """Nearest-neighbour voxel scale (k >= 1) — bosses and summons are the same bodies, bigger and blockier."""
    if k <= 1:
        return parts
    out = {}
    for b, v in parts.items():
        seen = set()
        for x, y, z, c in v:
            for dx in range(k):
                for dy in range(k):
                    for dz in range(k):
                        p = (x * k + dx, y * k + dy, z * k + dz)
                        if p not in seen:
                            seen.add(p)
                            out.setdefault(b, []).append((*p, c))
    return out


def top_of(parts, bone="head"):
    v = parts.get(bone) or parts["body"]
    zt = max(z for _, _, z, _ in v)
    xs = [x for x, _, z, _ in v if z == zt]
    ys = [y for _, y, z, _ in v if z == zt]
    return (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2, zt


def front_of(parts, bone="head"):
    v = parts.get(bone) or parts["body"]
    yf = max(y for _, y, _, _ in v)
    zs = [z for _, y, z, _ in v if y == yf]
    return yf, (min(zs) + max(zs)) // 2


def add_crown(parts, c, h=3):
    x, y, z = top_of(parts)
    for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2), (0, -2), (0, 2), (-2, 0), (2, 0)):
        box(parts, "head", x + dx, y + dy, z + 1, 1, 1, 1, c)
    for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
        box(parts, "head", x + dx, y + dy, z + 2, 1, 1, h - 1, c)
    return parts


def add_horn(parts, c, h=5):
    x, y, z = top_of(parts)
    yf, _ = front_of(parts)
    for i in range(h):
        box(parts, "head", x, min(yf - 1, y + 1) + i // 3, z + 1 + i, 1, 1, 1, c)
    return parts


# ---- archetypes (each returns {bone: [(x, y, z, colour)]}, feet at z=0, facing +Y) ----------------------------
def slime(c1, c2, size=1.0, drip=False):
    out = {}
    r = max(3, int(5 * size))
    h = max(3, int(4 * size))
    for x in range(-r, r + 1):
        for y in range(-r, r + 1):
            d = (x * x + y * y) ** .5 / r
            if d <= 1:
                top = int(h * (1 - d * d) ** .5) + 1
                for z in range(top):
                    out.setdefault("body" if z < top * .6 else "head", []).append((x, y, z, c1 if z < top - 1 else c2))
    if drip:
        box(out, "head", 0, 0, h + 1, 1, 1, 2, c2)
    yf = r
    box(out, "head", -2, yf - 1, h - 1, 1, 1, 2, "eye")
    box(out, "head", 1, yf - 1, h - 1, 1, 1, 2, "eye")
    box(out, "head", -1, yf, h - 3, 3, 1, 1, "nose")
    box(out, "tail", 0, -r, 1, 1, 1, 1, c1)
    return out


def wisp(c1, c2, size=1.0):
    out = {}
    base = 4
    for z in range(int(9 * size)):
        w = max(1, int((3.5 - abs(z - 3) * .55) * size))
        box(out, "body" if z < 5 else "head", -w, -w, base + z, 2 * w + 1, 2 * w + 1, 1, c1 if z % 3 else c2)
    box(out, "head", -1, int(3 * size), base + 3, 1, 1, 1, "eye")
    box(out, "head", 1, int(3 * size), base + 3, 1, 1, 1, "eye")
    box(out, "tail", 0, -1, base - 3, 1, 1, 3, c2)
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        box(out, bone, sgn * int(4 * size), 0, base + 3, 1, 1, 2, c2)
    return out


def orb(c1, eye_c, size=1.0):
    out = {}
    r = max(3, int(4 * size))
    zc = r + 4
    for x in range(-r, r + 1):
        for y in range(-r, r + 1):
            for z in range(-r, r + 1):
                if x * x + y * y + z * z <= r * r:
                    out.setdefault("body", []).append((x, y, zc + z, c1))
    box(out, "head", -2, r, zc - 2, 5, 1, 5, "eye_w")
    box(out, "head", -1, r + 1, zc - 1, 3, 1, 3, eye_c)
    box(out, "head", 0, r + 2, zc, 1, 1, 1, "eye")
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        box(out, bone, sgn * (r + 1) - (0 if sgn > 0 else 3), -1, zc, 4, 3, 1, tint(PAL[c1], .7) and col(tint(PAL[c1], .7)))
    box(out, "tail", 0, -r - 3, zc - 1, 1, 3, 1, c1)
    return out


def mushroom(cap, stem, spots=None, size=1.0):
    out = {}
    L = 2
    sw = max(2, int(3 * size))
    box(out, "body", -sw // 2 - 1, -1, L, sw + 1, 3, int(5 * size), stem)
    for sx, bone in ((-2, "leg.L"), (1, "leg.R")):
        box(out, bone, sx, 0, 0, 1, 1, L, stem)
    r = max(3, int(5 * size))
    zc = L + int(5 * size)
    for x in range(-r, r + 1):
        for y in range(-r, r + 1):
            d = (x * x + y * y) ** .5 / r
            if d <= 1:
                for z in range(int(3 * (1 - d * d)) + 1):
                    out.setdefault("head", []).append((x, y, zc + z, cap))
    if spots:
        rng = random.Random(len(cap))
        for _ in range(6):
            box(out, "head", rng.randint(-r + 1, r - 1), rng.randint(-r + 1, r - 1), zc + 3, 1, 1, 1, spots)
    yf = 1
    box(out, "body", -1, yf + 1, zc - 2, 1, 1, 1, "eye")
    box(out, "body", 1, yf + 1, zc - 2, 1, 1, 1, "eye")
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        box(out, bone, sgn * 2 - (0 if sgn > 0 else 0), 0, L + 2, 1, 1, 2, stem)
    return out


def humanoid(skin, cloth, trim=None, hat=None, hat_style="cap", hair=None, tool=None, tool_kind="staff", cape=None,
             armor=None, size=1.0, belly=None, beard=None, shield=None):
    """Townsfolk, heroes and knights: legs, torso, head with face, arms on the wing bones (down by the sides)."""
    s = size
    out = {}
    L = max(4, int(6 * s))
    T = max(5, int(7 * s))
    W = 6 if not belly else 7
    for sx, bone in ((-2, "leg.L"), (1, "leg.R")):
        box(out, bone, sx, -1, 0, 2, 2, L, armor or col(tint(PAL[cloth], .7)))
        box(out, bone, sx, -1, 0, 2, 3, 1, "hoof")
    box(out, "body", -W // 2, -1, L, W, 3, T, armor or cloth)
    if trim:
        box(out, "body", -W // 2, -1, L + 1, W, 3, 1, trim)       # belt
        box(out, "body", -1, 2, L + 2, 2, 1, T - 3, trim)          # placket / tabard stripe
    if cape:
        box(out, "tail", -W // 2, -2, L + 1, W, 1, T, cape)
    H = L + T
    box(out, "head", -2, -2, H, 4, 4, 4, skin)
    box(out, "head", -2, 2, H + 2, 1, 1, 1, "eye")
    box(out, "head", 1, 2, H + 2, 1, 1, 1, "eye")
    if beard:
        box(out, "head", -2, 2, H, 4, 1, 2, beard)
    if hair:
        box(out, "head", -2, -2, H + 4, 4, 4, 1, hair)
        box(out, "head", -2, -2, H + 1, 4, 1, 3, hair)
    if hat:
        if hat_style == "cap":
            box(out, "head", -2, -2, H + 4, 4, 5, 1, hat)
        elif hat_style == "wide":
            box(out, "head", -3, -3, H + 4, 6, 6, 1, hat)
            box(out, "head", -2, -2, H + 5, 4, 4, 1, hat)
        elif hat_style == "point":
            box(out, "head", -3, -3, H + 4, 6, 6, 1, hat)
            box(out, "head", -2, -2, H + 5, 4, 4, 2, hat)
            box(out, "head", -1, -1, H + 7, 2, 2, 2, hat)
            box(out, "head", 0, 0, H + 9, 1, 1, 2, hat)
        elif hat_style == "helm":
            box(out, "head", -3, -3, H + 1, 6, 6, 4, hat)
            box(out, "head", -2, 3, H + 2, 4, 0 or 1, 1, "eye")      # visor slit
            box(out, "head", 0, -1, H + 5, 1, 3, 2, trim or hat)      # crest
        elif hat_style == "crown":
            box(out, "head", -2, -2, H + 4, 4, 4, 1, hat)
            for dx, dy in ((-2, -2), (1, -2), (-2, 1), (1, 1)):
                box(out, "head", dx, dy, H + 5, 1, 1, 1, hat)
        elif hat_style == "hood":
            box(out, "head", -3, -3, H, 6, 5, 5, hat)
            box(out, "head", -2, 2, H + 1, 4, 1, 3, skin)
        elif hat_style == "band":
            box(out, "head", -2, -2, H + 3, 4, 4, 1, hat)
            box(out, "head", 0, -3, H + 2, 1, 1, 3, hat)
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        x0 = W // 2 if sgn > 0 else -W // 2 - 2
        box(out, bone, x0, -1, L + 2, 2, 2, T - 2, armor or cloth)
        box(out, bone, x0, -1, L + 1, 2, 2, 1, skin)               # hands
    if shield:
        box(out, "wing.L", W // 2 + 2, -2, L + 2, 1, 4, 4, shield)
    if tool:
        x = -W // 2 - 2
        if tool_kind == "staff":
            box(out, "wing.R", x, 2, 0, 1, 1, H + 4, tool)
            box(out, "wing.R", x - 1, 1, H + 3, 3, 3, 3, trim or tool)
        elif tool_kind == "sword":
            box(out, "wing.R", x, 2, L + 1, 1, 1, 2, "fur_b")
            box(out, "wing.R", x - 1, 2, L + 3, 3, 1, 1, trim or "gold")
            box(out, "wing.R", x, 2, L + 4, 1, 1, 8, tool)
        elif tool_kind == "lance":
            box(out, "wing.R", x, 2, 0, 1, 1, H + 8, tool)
            box(out, "wing.R", x - 1, 2, H + 8, 3, 1, 3, trim or tool)
        elif tool_kind == "dagger":
            box(out, "wing.R", x, 2, L + 1, 1, 1, 4, tool)
        elif tool_kind == "bow":
            for i in range(9):
                box(out, "wing.R", x, 2 + (1 if 2 < i < 6 else 0), L + i, 1, 1, 1, tool)
        elif tool_kind == "tool":
            box(out, "wing.R", x, 2, L + 1, 1, 1, 5, "fur_b")
            box(out, "wing.R", x - 1, 2, L + 6, 3, 1, 2, tool)
        elif tool_kind == "book":
            box(out, "wing.R", x, 2, L + 2, 2, 1, 3, tool)
        elif tool_kind == "lantern":
            box(out, "wing.R", x, 2, L + 1, 1, 1, 2, tool)
            box(out, "wing.R", x, 2, L - 1, 1, 1, 2, "glow" if "glow" in PAL else tool)
    return out


def golem(c1, c2, size=1.0, crystal=None):
    s = size
    out = {}
    L = int(5 * s)
    for sx, bone in ((-4, "leg.L"), (1, "leg.R")):
        box(out, bone, int(sx * s), -2, 0, int(3 * s), int(4 * s), L, c2)
    W, D, T = int(10 * s), int(6 * s), int(9 * s)
    box(out, "body", -W // 2, -D // 2, L, W, D, T, c1)
    if crystal:
        for i in range(4):
            box(out, "body", -W // 2 + 1 + i * 2, -D // 2 - 1, L + T - 2 - i, 1, 1, 3 + i, crystal)
    box(out, "head", -2, -1, L + T, 5, 4, 4, c2)
    box(out, "head", -1, 3, L + T + 2, 1, 1, 1, crystal or "eye")
    box(out, "head", 1, 3, L + T + 2, 1, 1, 1, crystal or "eye")
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        x0 = W // 2 if sgn > 0 else -W // 2 - int(3 * s)
        box(out, bone, x0, -2, L - 1, int(3 * s), int(4 * s), T, c2)
        box(out, bone, x0, -2, L - 3, int(3 * s), int(4 * s), 2, c1)          # big fists
    return out


def mimic(wood, metal, size=1.0):
    out = {}
    W, D = int(8 * size), int(6 * size)
    for sx, bone in ((-W // 2 + 1, "leg.L"), (W // 2 - 2, "leg.R")):
        box(out, bone, sx, -1, 0, 1, 1, 2, wood)
    box(out, "body", -W // 2, -D // 2, 2, W, D, 4, wood)
    box(out, "body", -W // 2, -D // 2, 4, W, D, 1, metal)
    box(out, "head", -W // 2, -D // 2, 6, W, D, 3, wood)                      # the lid snaps
    box(out, "head", -W // 2, -D // 2, 7, W, D, 1, metal)
    box(out, "head", -1, D // 2, 6, 2, 1, 2, "gold")                          # lock
    for x in range(-W // 2, W // 2, 2):
        box(out, "head", x, D // 2 - 1, 5, 1, 1, 1, "tooth")
        box(out, "body", x + 1, D // 2 - 1, 6, 1, 1, 1, "tooth")
    box(out, "body", -2, D // 2 - 1, 5, 4, 1, 1, "trap_in")                   # tongue
    box(out, "head", -2, D // 2 - 2, 8, 1, 1, 1, "flower_r")
    box(out, "head", 1, D // 2 - 2, 8, 1, 1, 1, "flower_r")
    return out


def crab(shell, claw, size=1.0):
    out = {}
    W, D = int(10 * size), int(6 * size)
    box(out, "body", -W // 2, -D // 2, 2, W, D, 3, shell)
    for i, sx in enumerate((-W // 2 - 1, W // 2)):
        bone = "leg.L" if i == 0 else "leg.R"
        for k in range(3):
            box(out, bone, sx, -D // 2 + 1 + k * 2, 0, 1, 1, 3, claw)
    for sgn, bone in ((1, "wing.L"), (-1, "wing.R")):
        x0 = W // 2 - 2 if sgn > 0 else -W // 2
        box(out, bone, x0, D // 2, 3, 3, 3, 2, claw)
        box(out, bone, x0, D // 2 + 3, 3, 3, 2, 3, claw)
    box(out, "head", -2, D // 2 - 1, 5, 1, 1, 2, "eye")
    box(out, "head", 1, D // 2 - 1, 5, 1, 1, 2, "eye")
    return out


def serpent(c1, c2, size=1.0, hood=False):
    out = {}
    n = int(16 * size)
    for i in range(n):
        y = -i
        x = int(2 * (1 if (i // 4) % 2 else -1) * min(1, i / 4))
        bone = "body" if i < n // 2 else "tail"
        box(out, bone, x - 1, y, 0, 3, 1, 2, c1 if i % 3 else c2)
    for z in range(1, int(6 * size)):
        box(out, "body", -1, 1, z, 3, 2, 1, c1)
    hz = int(6 * size)
    box(out, "head", -2, 0, hz, 4, 4, 3, c1)
    box(out, "head", -2, 3, hz + 2, 1, 1, 1, "eye")
    box(out, "head", 1, 3, hz + 2, 1, 1, 1, "eye")
    box(out, "head", 0, 4, hz, 1, 2, 1, "flower_r")
    if hood:
        box(out, "head", -4, -1, hz - 1, 8, 1, 5, c2)
    return out


def turtle(shell, skin, size=1.0, spikes=None):
    out = {}
    r = int(6 * size)
    for x in range(-r, r + 1):
        for y in range(-r, r + 1):
            d = (x * x + y * y) ** .5 / r
            if d <= 1:
                for z in range(int(4 * (1 - d * d)) + 1):
                    out.setdefault("body", []).append((x, y, 3 + z, shell))
    if spikes:
        for x, y in ((-2, -2), (2, 2), (-2, 2), (2, -2), (0, 0)):
            box(out, "body", x, y, 8, 1, 1, 2, spikes)
    for sx, sy, bone in ((-r + 1, r - 2, "leg.L"), (r - 2, r - 2, "leg.R"), (-r + 1, -r + 1, "leg.L"), (r - 2, -r + 1, "leg.R")):
        box(out, bone, sx, sy, 0, 2, 2, 3, skin)
    box(out, "head", -2, r, 3, 4, 4, 3, skin)
    box(out, "head", -2, r + 3, 5, 1, 1, 1, "eye")
    box(out, "head", 1, r + 3, 5, 1, 1, 1, "eye")
    box(out, "tail", 0, -r - 2, 3, 1, 2, 1, skin)
    return out


def from_species(sp, mapping=None):
    p = VC.plan(sp)
    return recolor(p, mapping or {})


# ---- PORTAL REALM roster (types from data/art/portal/population-plan.json) ------------------------------------
C = col
PORTAL_ENEMY = {
    "AshDrake":       lambda s: recolor(VC._dino("raptor"), {"scale": C((.35, .32, .30)), "belly": C((.9, .45, .15))}),
    "BOG_SLIME":      lambda s: slime(C((.35, .45, .20)), C((.50, .60, .25)), s, drip=True),
    "BoulderToad":    lambda s: recolor(VC._quadruped(fur=C((.45, .43, .40)), belly=C((.7, .65, .55)), size=1.4 * s, tail=None, ears=None, snout=1), {}),
    "BrambleHound":   lambda s: VC._quadruped(fur=C((.25, .40, .18)), belly=C((.45, .30, .18)), size=1.1 * s, tail="long", spots=C((.55, .15, .30))),
    "BriarBoar":      lambda s: VC._quadruped(fur=C((.40, .28, .16)), belly=C((.55, .40, .25)), size=1.3 * s, tail="short", horns="tooth", ears="up", snout=3, mane=C((.2, .45, .15))),
    "BrokenAutomaton": lambda s: golem(C((.50, .40, .30)), C((.35, .30, .28)), .8 * s, crystal=C((1.0, .6, .1))),
    "CaveMantis":     lambda s: recolor(VC._insect("grasshopper"), {}),
    "CinderRam":      lambda s: VC._quadruped(fur=C((.30, .22, .20)), belly=C((.95, .45, .10)), size=1.2 * s, horns=C((.95, .55, .15)), ears="up", tail="short"),
    "CliffHarrier":   lambda s: VC._bird(C((.50, .42, .32)), C((.85, .80, .70)), size=1.6 * s, beak_len=2, crest=C((.3, .25, .2)), wing_len=10),
    "CopperCrab":     lambda s: crab(C((.78, .45, .22)), C((.62, .35, .18)), s),
    "CrystalGolem":   lambda s: golem(C((.55, .70, .90)), C((.40, .45, .60)), 1.1 * s, crystal=C((.75, .90, 1.0))),
    "DUST_WISP":      lambda s: wisp(C((.80, .75, .60)), C((.65, .60, .45)), s),
    "EMBER_WISP":     lambda s: wisp(C((1.0, .55, .15)), C((1.0, .85, .30)), s),
    "EmberLizard":    lambda s: recolor(VC.plan("gila_monster"), {}),
    "GLASSBACK":      lambda s: turtle(C((.70, .90, .95)), C((.40, .55, .50)), s, spikes=C((.85, .95, 1.0))),
    "GLOOMWING":      lambda s: VC._bird(C((.18, .12, .25)), C((.35, .25, .45)), size=1.3 * s, beak_len=1, wing_len=12, tail_len=2),
    "GNASHBOX":       lambda s: mimic(C((.55, .35, .18)), C((.70, .65, .55)), s),
    "GlassViper":     lambda s: serpent(C((.70, .90, .95)), C((.45, .70, .80)), s),
    "GraniteBrute":   lambda s: golem(C((.55, .52, .50)), C((.40, .38, .36)), 1.3 * s),
    "IceNewt":        lambda s: recolor(VC.plan("salamander"), {}),
    "IronMole":       lambda s: recolor(VC.plan("mole"), {}),
    "IronjawWolf":    lambda s: VC._quadruped(fur=C((.45, .47, .50)), belly=C((.70, .72, .75)), size=1.2 * s, tail="bushy", horns=None, snout=3, mane=C((.30, .32, .35))),
    "LUCKY_DRIP":     lambda s: slime(C((.95, .80, .25)), C((1.0, .95, .55)), .7 * s, drip=True),
    "MOSS_KNIGHT":    lambda s: humanoid("fur_g", C((.25, .40, .20)), trim=C((.45, .35, .20)), hat=C((.25, .40, .20)), hat_style="helm", armor=C((.35, .45, .30)), tool="iron" if "iron" in PAL else C((.6, .6, .65)), tool_kind="sword", shield=C((.30, .25, .18)), size=1.1 * s),
    "MossbackOgre":   lambda s: humanoid(C((.45, .55, .35)), C((.40, .30, .20)), trim=C((.25, .45, .20)), size=1.5 * s, belly=True, tool=C((.40, .28, .16)), tool_kind="tool"),
    "MudGolem":       lambda s: golem(C((.40, .30, .20)), C((.30, .22, .15)), s),
    "ObsidianCrab":   lambda s: crab(C((.10, .08, .14)), C((.25, .15, .35)), 1.2 * s),
    "PUFFCAP":        lambda s: mushroom(C((.85, .30, .30)), C((.92, .88, .80)), spots=C((1, 1, 1)), size=s),
    "QuartzTurtle":   lambda s: turtle(C((.90, .85, .95)), C((.50, .45, .40)), 1.1 * s, spikes=C((1.0, .9, 1.0))),
    "RazorFinch":     lambda s: VC._bird(C((.75, .20, .20)), C((.95, .85, .75)), size=.9 * s, beak_len=3, crest=C((.95, .75, .2))),
    "ReefStalker":    lambda s: recolor(VC._sea("shark"), {}),
    "RiverSnapper":   lambda s: turtle(C((.35, .40, .25)), C((.45, .50, .30)), s, spikes=C((.25, .30, .18))),
    "RockBeetle":     lambda s: recolor(VC._insect("beetle"), {}),
    "RustKnight":     lambda s: humanoid("skin", C((.55, .30, .18)), trim=C((.40, .20, .10)), hat=C((.55, .30, .18)), hat_style="helm", armor=C((.55, .32, .20)), tool=C((.50, .30, .20)), tool_kind="sword", shield=C((.45, .25, .15)), size=1.1 * s),
    "SHADECAP":       lambda s: mushroom(C((.25, .18, .35)), C((.55, .50, .60)), spots=C((.6, .9, .7)), size=s),
    "SHARDBACK":      lambda s: turtle(C((.45, .55, .70)), C((.35, .35, .40)), s, spikes=C((.65, .85, 1.0))),
    "SHARD_TYRANT":   lambda s: golem(C((.25, .30, .45)), C((.15, .18, .28)), 1.5 * s, crystal=C((.70, .85, 1.0))),
    "STARE_ORB":      lambda s: orb(C((.55, .25, .55)), C((.95, .80, .20)), s),
    "STONE_KNIGHT":   lambda s: humanoid(C((.60, .58, .55)), C((.55, .55, .55)), trim=C((.40, .40, .42)), hat=C((.60, .60, .62)), hat_style="helm", armor=C((.62, .60, .58)), tool=C((.7, .7, .72)), tool_kind="lance", shield=C((.5, .5, .52)), size=1.15 * s),
    "SaltbackLurker": lambda s: recolor(VC._sea("anglerfish"), {}),
    "SandScorpion":   lambda s: recolor(VC._insect("scorpion"), {}),
    "SiltCrawler":    lambda s: recolor(VC._insect("centipede"), {}),
    "SlateSerpent":   lambda s: serpent(C((.35, .38, .42)), C((.25, .27, .30)), 1.2 * s, hood=True),
    "SmokeRaptor":    lambda s: recolor(VC._dino("raptor"), {"scale": C((.40, .40, .42)), "belly": C((.60, .60, .62))}),
    "StormHawk":      lambda s: VC._bird(C((.35, .40, .55)), C((.85, .88, .95)), size=1.5 * s, beak_len=2, crest=C((1.0, .95, .4)), wing_len=11),
    "StormRay":       lambda s: recolor(VC._sea("manta"), {}),
    "ThistleWasp":    lambda s: VC._bee(size=1.6 * s, body=(C((.55, .25, .60)), "bee_k")),
    "ThornCrawler":   lambda s: recolor(VC._insect("woodlouse"), {}),
    "TunnelWorm":     lambda s: recolor(VC._insect("earthworm"), {}),
}
# insects/sea/dino bodies are authored at 10 cm voxels for small animals — monsters export them bigger:
PORTAL_ENEMY_CM = {"CaveMantis": 30, "RockBeetle": 30, "SandScorpion": 30, "SiltCrawler": 30, "ThornCrawler": 30, "TunnelWorm": 35,
                   "EmberLizard": 18, "IceNewt": 20, "IronMole": 18, "ReefStalker": 12, "SaltbackLurker": 18, "StormRay": 14,
                   "AshDrake": 12, "SmokeRaptor": 12, "ThistleWasp": 25}

TOOLS = {"wood": C((.45, .30, .16)), "iron": C((.62, .62, .66)), "gold": C((.95, .78, .25)), "book": C((.55, .20, .20))}
SKINS = [C((.95, .80, .68)), C((.80, .60, .45)), C((.60, .42, .30)), C((.40, .28, .20))]
PORTAL_FRIEND = {
    # role: (cloth, trim, hat, hat_style, tool, tool_kind, extras)
    "Ambassador": ((.35, .20, .50), (.95, .78, .25), (.35, .20, .50), "cap", "book", "book", {}),
    "Apothecary": ((.30, .55, .45), (.85, .85, .80), None, None, "wood", "staff", {}),
    "Baker": ((.95, .92, .85), (.85, .65, .35), (1, 1, 1), "wide", None, None, {"belly": True}),
    "Bard": ((.70, .25, .25), (.95, .80, .30), (.70, .25, .25), "cap", "wood", "tool", {}),
    "Carpenter": ((.55, .40, .25), (.35, .25, .15), None, None, "iron", "tool", {}),
    "Cartographer": ((.40, .45, .30), (.80, .75, .55), (.40, .45, .30), "wide", "book", "book", {}),
    "Cook": ((.95, .95, .95), (.70, .20, .20), (1, 1, 1), "point", "iron", "tool", {"belly": True}),
    "DragonKeeper": ((.25, .40, .30), (.80, .30, .20), None, None, "wood", "staff", {"cape": (.80, .30, .20)}),
    "Farmer": ((.40, .55, .75), (.60, .45, .25), (.85, .75, .45), "wide", "wood", "tool", {}),
    "FerryCaptain": ((.15, .25, .45), (.95, .80, .30), (.15, .25, .45), "cap", "wood", "staff", {"beard": True}),
    "Fisher": ((.55, .60, .45), (.40, .35, .25), (.85, .75, .45), "wide", "wood", "lance", {}),
    "Healer": ((.95, .95, .95), (.85, .30, .35), (.95, .95, .95), "hood", "wood", "staff", {}),
    "Herbalist": ((.35, .50, .30), (.70, .55, .35), (.35, .50, .30), "hood", "wood", "staff", {}),
    "Innkeeper": ((.65, .45, .30), (.95, .90, .80), None, None, "gold", "lantern", {"belly": True}),
    "ItemMerchant": ((.30, .45, .65), (.95, .80, .30), (.30, .45, .65), "cap", "book", "book", {}),
    "Jeweller": ((.45, .25, .55), (.95, .80, .30), None, None, "gold", "dagger", {}),
    "Keymaker": ((.40, .38, .36), (.95, .78, .25), (.40, .38, .36), "cap", "gold", "tool", {}),
    "King": ((.60, .10, .15), (.95, .80, .30), (.95, .80, .30), "crown", "gold", "staff", {"cape": (.70, .10, .15), "beard": True}),
    "Knight": ((.60, .62, .66), (.25, .35, .70), (.62, .62, .66), "helm", "iron", "sword", {"armor": (.62, .64, .68), "shield": (.25, .35, .70)}),
    "Librarian": ((.35, .25, .45), (.80, .75, .60), None, None, "book", "book", {}),
    "LostTraveller": ((.50, .45, .35), (.35, .30, .25), (.45, .35, .25), "hood", "wood", "staff", {}),
    "Mason": ((.55, .52, .50), (.35, .30, .28), None, None, "iron", "tool", {}),
    "Messenger": ((.25, .55, .45), (.95, .85, .40), (.25, .55, .45), "cap", "book", "book", {}),
    "Miller": ((.92, .90, .82), (.55, .45, .30), (.92, .90, .82), "cap", "wood", "tool", {}),
    "Miner": ((.40, .35, .30), (.70, .55, .25), (.95, .80, .25), "cap", "iron", "tool", {}),
    "Musician": ((.25, .25, .55), (.95, .80, .30), (.25, .25, .55), "wide", "gold", "tool", {}),
    "Prince": ((.25, .35, .70), (.95, .80, .30), (.95, .80, .30), "crown", "iron", "sword", {"cape": (.25, .35, .70)}),
    "Princess": ((.90, .55, .75), (.95, .80, .30), (.95, .80, .30), "crown", None, None, {"hair": (.85, .70, .35)}),
    "Queen": ((.45, .20, .55), (.95, .80, .30), (.95, .80, .30), "crown", "gold", "staff", {"cape": (.45, .20, .55), "hair": (.30, .20, .15)}),
    "RainbowWarden": ((.90, .90, .95), (.55, .35, .85), (.55, .85, .95), "point", "gold", "staff", {"cape": (.95, .55, .45)}),
    "Ranger": ((.30, .40, .22), (.45, .30, .18), (.30, .40, .22), "hood", "wood", "bow", {}),
    "Refugee": ((.50, .45, .40), (.40, .35, .30), None, None, "wood", "staff", {}),
    "RescueGuide": ((.85, .50, .15), (.95, .95, .90), (.85, .50, .15), "cap", "gold", "lantern", {}),
    "RoyalGuard": ((.70, .15, .20), (.95, .80, .30), (.62, .62, .66), "helm", "iron", "lance", {"armor": (.62, .62, .66), "shield": (.70, .15, .20)}),
    "RoyalScribe": ((.30, .30, .45), (.95, .80, .30), None, None, "book", "book", {}),
    "Scholar": ((.25, .30, .45), (.85, .80, .65), (.25, .30, .45), "wide", "book", "book", {"beard": True}),
    "Scout": ((.40, .45, .30), (.30, .25, .18), (.40, .45, .30), "band", "iron", "dagger", {}),
    "Shepherd": ((.75, .70, .55), (.50, .40, .25), (.85, .75, .45), "wide", "wood", "staff", {}),
    "Smith": ((.35, .30, .28), (.55, .35, .20), None, None, "iron", "tool", {"belly": True, "beard": True}),
    "StableKeeper": ((.50, .40, .30), (.35, .30, .25), (.55, .45, .30), "wide", "wood", "tool", {}),
    "Steward": ((.25, .25, .30), (.95, .80, .30), None, None, "book", "book", {}),
    "Storyteller": ((.50, .30, .55), (.85, .75, .45), (.50, .30, .55), "point", "wood", "staff", {"beard": True}),
    "Tailor": ((.75, .45, .60), (.95, .90, .80), None, None, "iron", "dagger", {}),
    "Tinker": ((.45, .40, .30), (.70, .55, .25), (.45, .40, .30), "cap", "gold", "tool", {}),
    "Weaver": ((.65, .55, .75), (.95, .90, .80), (.65, .55, .75), "hood", "wood", "staff", {}),
    "WellKeeper": ((.35, .45, .55), (.60, .50, .35), None, None, "wood", "tool", {}),
}
PORTAL_UNICORNS = {"UnicornGuide": (.97, .95, .98), "UnicornMedic": (.95, .85, .90), "UnicornQuestgiver": (.90, .92, 1.0), "UnicornSentinel": (.85, .85, .95)}
MANES = [(.95, .55, .75), (.55, .75, .95), (.75, .55, .95), (.95, .85, .45), (.55, .95, .75)]
PORTAL_BOSS = {
    "GatebreakerColossus": lambda: scale_plan(golem(C((.45, .42, .40)), C((.30, .28, .27)), 1.2, crystal=C((1.0, .55, .15))), 2),
    "StormCrownDrake":     lambda: add_crown(scale_plan(recolor(VC._dino("allosaurus"), {"scale": C((.30, .35, .55)), "belly": C((.85, .88, .95))}), 2), C((1.0, .9, .4))),
    "IronrootBehemoth":    lambda: scale_plan(VC._quadruped(fur=C((.35, .30, .22)), belly=C((.25, .40, .20)), size=2.0, horns=C((.55, .55, .58)), tail="long", mane=C((.25, .45, .18)), snout=3), 2),
    "DeepRiverLeviathan":  lambda: scale_plan(serpent(C((.15, .35, .45)), C((.25, .55, .60)), 1.6, hood=True), 2),
    "CinderSpireGuardian": lambda: scale_plan(golem(C((.20, .15, .15)), C((.95, .40, .08)), 1.3, crystal=C((1.0, .7, .2))), 2),
}


# ---- PRISMHEART REALM (original 16-bit crystal-era party RPG) ---------------------------------------------------
PRISM_JOBS = {
    # job: (cloth, trim, hat, hat_style, weapon colour, weapon kind, extras)
    "Bladeward":   ((.25, .35, .65), (.90, .80, .35), (.70, .72, .78), "helm", (.80, .82, .88), "sword", {"armor": (.70, .72, .78), "shield": (.25, .35, .65), "cape": (.65, .15, .20)}),
    "Runecaster":  ((.20, .20, .45), (.95, .75, .25), (.20, .20, .45), "point", (.55, .35, .20), "staff", {"cape": (.30, .15, .45)}),
    "Lightmender": ((.96, .96, .96), (.85, .30, .35), (.96, .96, .96), "hood", (.85, .75, .45), "staff", {}),
    "Shadowstep":  ((.15, .15, .20), (.65, .15, .20), (.15, .15, .20), "band", (.75, .78, .82), "dagger", {"cape": (.20, .20, .28)}),
    "Beastcaller": ((.35, .50, .25), (.70, .50, .25), (.35, .50, .25), "hood", (.55, .40, .20), "bow", {}),
    "Gearwright":  ((.55, .40, .25), (.80, .65, .30), (.45, .35, .25), "cap", (.65, .55, .35), "tool", {"belly": False}),
    "Starlancer":  ((.20, .40, .45), (.85, .85, .95), (.25, .45, .50), "helm", (.75, .80, .90), "lance", {"armor": (.25, .45, .50), "cape": (.85, .85, .95)}),
    "Chronoseer":  ((.55, .45, .20), (.35, .80, .80), (.55, .45, .20), "wide", (.35, .80, .80), "staff", {"cape": (.30, .25, .15)}),
}
PRISM_MONSTERS = {
    "GlimmerImp":     lambda s: humanoid(C((.55, .30, .65)), C((.35, .15, .45)), trim=C((.95, .80, .30)), hat=C((.35, .15, .45)), hat_style="point", size=.7 * s, tool=C((.95, .8, .3)), tool_kind="staff"),
    "FrostPuddle":    lambda s: slime(C((.70, .88, 1.0)), C((.92, .97, 1.0)), s),
    "ThornbackBoar":  lambda s: VC._quadruped(fur=C((.40, .30, .18)), belly=C((.55, .45, .30)), size=1.4 * s, horns=C((.90, .85, .70)), mane=C((.20, .45, .18)), snout=3),
    "BoneLancer":     lambda s: humanoid(C((.92, .90, .85)), C((.75, .72, .68)), hat=C((.40, .38, .36)), hat_style="helm", tool=C((.55, .55, .58)), tool_kind="lance", armor=C((.40, .38, .36)), size=s),
    "CinderHound":    lambda s: VC._quadruped(fur=C((.20, .15, .12)), belly=C((1.0, .45, .10)), size=1.2 * s, tail="long", mane=C((1.0, .55, .10)), snout=3),
    "MirrorMoth":     lambda s: recolor(VC._insect("moth"), {}),
    "ClockworkSentry": lambda s: golem(C((.70, .55, .25)), C((.45, .40, .35)), .9 * s, crystal=C((.35, .85, .95))),
    "HollowArmor":    lambda s: humanoid(C((.05, .05, .08)), C((.55, .55, .60)), hat=C((.55, .55, .60)), hat_style="helm", armor=C((.55, .55, .60)), tool=C((.7, .7, .75)), tool_kind="sword", shield=C((.35, .35, .40)), size=1.2 * s),
    "SandWyrm":       lambda s: serpent(C((.80, .65, .40)), C((.60, .45, .25)), 1.3 * s),
    "GaleHarpy":      lambda s: VC._bird(C((.55, .75, .55)), C((.90, .85, .75)), size=1.5 * s, crest=C((.95, .55, .35)), wing_len=12),
    "BogLantern":     lambda s: wisp(C((.55, .95, .55)), C((.25, .55, .30)), s),
    "CoralGolem":     lambda s: golem(C((.95, .55, .55)), C((.80, .40, .45)), s, crystal=C((.95, .85, .70))),
    "IronshellTortoise": lambda s: turtle(C((.55, .58, .62)), C((.45, .40, .35)), 1.2 * s, spikes=C((.7, .72, .76))),
    "RatKing":        lambda s: add_crown(VC._quadruped(fur=C((.45, .40, .35)), belly=C((.65, .55, .50)), size=.9 * s, tail="long", ears="up", snout=2), C((.95, .78, .25)), 2),
    "EmberSalamander": lambda s: recolor(VC.plan("salamander"), {}),
    "StormRoc":       lambda s: VC._bird(C((.30, .32, .45)), C((.85, .88, .95)), size=2.0 * s, beak_len=3, crest=C((1.0, .95, .4)), wing_len=14),
    "CrystalMantis":  lambda s: recolor(VC._insect("grasshopper"), {}),
    "VoidEye":        lambda s: orb(C((.15, .10, .25)), C((.85, .25, .85)), 1.1 * s),
    "LanternGhoul":   lambda s: humanoid(C((.55, .65, .55)), C((.25, .25, .30)), hat=C((.20, .20, .25)), hat_style="hood", tool=C((1.0, .85, .35)), tool_kind="lantern", size=s),
    "AshTreant":      lambda s: golem(C((.35, .28, .20)), C((.25, .20, .15)), 1.2 * s, crystal=C((.30, .55, .25))),
    "MireHydra":      lambda s: serpent(C((.25, .45, .30)), C((.45, .60, .30)), 1.4 * s, hood=True),
    "RuneGargoyle":   lambda s: humanoid(C((.50, .50, .52)), C((.40, .40, .42)), trim=C((.35, .85, .90)), size=1.1 * s, cape=C((.40, .40, .42)), tool=C((.35, .85, .9)), tool_kind="staff"),
    "QuartzScarab":   lambda s: recolor(VC._insect("beetle"), {}),
    "ShadePanther":   lambda s: VC._quadruped(fur=C((.12, .10, .18)), belly=C((.25, .20, .35)), size=1.2 * s, tail="long", spots=C((.45, .25, .65)), snout=2),
    "TideKraken":     lambda s: recolor(VC._sea("octopus"), {}),
    "ThunderRam":     lambda s: VC._quadruped(fur=C((.85, .85, .90)), belly=C((.35, .40, .65)), size=1.3 * s, horns=C((1.0, .9, .35)), tail="short"),
    "MossBehemoth":   lambda s: VC._quadruped(fur=C((.30, .40, .25)), belly=C((.40, .35, .25)), size=1.9 * s, horns=C((.75, .70, .60)), mane=C((.25, .50, .20)), tail="long", snout=3),
    "DuneScorpion":   lambda s: recolor(VC._insect("scorpion"), {}),
    "GlassSerpent":   lambda s: serpent(C((.75, .92, .98)), C((.50, .80, .90)), 1.2 * s),
    "StarJelly":      lambda s: recolor(VC._sea("jellyfish"), {}),
}
PRISM_MONSTER_CM = {"MirrorMoth": 30, "CrystalMantis": 30, "QuartzScarab": 32, "DuneScorpion": 35, "EmberSalamander": 22, "TideKraken": 18, "StarJelly": 20}
PRISM_SUMMONS = {
    "Aurorawyrm":     lambda: add_crown(scale_plan(recolor(VC._dino("allosaurus"), {"scale": C((.85, .90, 1.0)), "belly": C((.95, .80, .95))}), 2), C((.6, 1.0, .9)), 4),
    "Tidecoil":       lambda: scale_plan(serpent(C((.20, .45, .75)), C((.55, .85, .95)), 1.8, hood=True), 2),
    "EmberforgeTitan": lambda: scale_plan(golem(C((.35, .18, .12)), C((1.0, .45, .10)), 1.4, crystal=C((1.0, .80, .30))), 2),
    "Galewing":       lambda: scale_plan(VC._bird(C((.85, .95, .90)), C((.55, .85, .75)), size=2.0, crest=C((.95, .95, .55)), wing_len=16), 2),
    "GlacierStag":    lambda: scale_plan(VC._quadruped(fur=C((.85, .92, 1.0)), belly=C((.65, .80, .95)), size=1.6, horns=C((.70, .90, 1.0)), tail="short"), 2),
    "Stormmane":      lambda: add_horn(scale_plan(VC._quadruped(fur=C((.30, .30, .40)), belly=C((.95, .90, .45)), size=1.5, mane=C((.95, .90, .45)), tail="long"), 2), C((1.0, .95, .5)), 7),
    "Rootfather":     lambda: scale_plan(golem(C((.40, .30, .20)), C((.25, .45, .20)), 1.5, crystal=C((.55, .85, .35))), 2),
    "Starfall":       lambda: scale_plan(orb(C((.95, .90, .55)), C((.55, .35, .95)), 1.5), 2),
}
PRISM_FOLK = {
    "CrystalKeeper": ((.55, .80, .90), (.95, .95, .98), (.55, .80, .90), "hood", "gold", "staff", {}),
    "Airwright": ((.55, .40, .25), (.80, .65, .30), (.30, .25, .20), "cap", "iron", "tool", {}),
    "Innkeeper": ((.65, .45, .30), (.95, .90, .80), None, None, "gold", "lantern", {"belly": True}),
    "ArmsDealer": ((.40, .40, .45), (.85, .30, .25), None, None, "iron", "sword", {"beard": True}),
    "SpellVendor": ((.35, .20, .55), (.95, .80, .30), (.35, .20, .55), "point", "book", "book", {}),
    "Chancellor": ((.30, .15, .20), (.95, .80, .30), (.30, .15, .20), "cap", "book", "book", {"beard": True}),
    "Sovereign": ((.20, .30, .60), (.95, .80, .30), (.95, .80, .30), "crown", "gold", "staff", {"cape": (.70, .12, .18)}),
    "Dancer": ((.90, .45, .55), (.95, .80, .30), None, None, None, None, {"hair": (.75, .25, .20)}),
    "Sailor": ((.25, .35, .60), (.95, .95, .95), (.95, .95, .95), "cap", "wood", "tool", {}),
    "Orphan": ((.55, .50, .40), (.40, .35, .30), None, None, None, None, {"hair": (.45, .30, .20)}),
    "OldSage": ((.45, .40, .55), (.85, .80, .60), (.45, .40, .55), "point", "wood", "staff", {"beard": True}),
    "Chocolatier": ((.45, .28, .18), (.95, .90, .80), (1, 1, 1), "wide", None, None, {"belly": True}),
}
PRISM_MOUNT = {"Duneback": lambda s: VC._quadruped(fur=C((.75, .60, .35)), belly=C((.90, .80, .60)), size=1.7 * s, tail="long", ears="up",
                                                     mane=C((.55, .30, .15)), snout=3, spots=C((.55, .40, .20)))}


def folk_plan(row, rng):
    cloth, trim, hat, hstyle, tool, tkind, ex = row
    skin = rng.choice(SKINS)
    j = lambda c: C(tint(c, rng.uniform(.85, 1.12)))  # noqa: E731
    return humanoid(skin, j(cloth), trim=C(trim), hat=j(hat) if hat else None, hat_style=hstyle or "cap",
                    hair=C(ex["hair"]) if "hair" in ex else (C(rng.choice([(.25, .15, .10), (.55, .35, .15), (.85, .70, .35), (.15, .12, .10), (.6, .6, .6)])) if not hat else None),
                    tool=(TOOLS[tool] if isinstance(tool, str) else C(tool)) if tool else None, tool_kind=tkind or "staff",
                    cape=C(ex["cape"]) if "cape" in ex else None, armor=C(ex["armor"]) if "armor" in ex else None,
                    size=rng.uniform(.92, 1.08), belly=ex.get("belly"), beard=C((.85, .85, .85)) if ex.get("beard") else None,
                    shield=C(ex["shield"]) if "shield" in ex else None)


def unicorn_plan(coat, rng):
    mane = rng.choice(MANES)
    p = VC._quadruped(fur=C(tint(coat, rng.uniform(.95, 1.03))), belly=C((1, 1, 1)), size=rng.uniform(1.1, 1.3), tail="bushy", ears="up", mane=C(mane), snout=2)
    return add_horn(p, C((.95, .80, .35)), 5)


def vary(parts, rng, keep=("eye", "eye_w", "nose", "tooth")):
    """Individuals: every non-feature colour nudged by one shared factor (a family that differs, not ten clones)."""
    f = rng.uniform(.82, 1.15)
    hue = rng.uniform(-.06, .06)
    m = {}
    for v in parts.values():
        for *_, c in v:
            if c in m or c in keep:
                continue
            r, g, b = PAL[c]
            m[c] = C((r * f + hue, g * f, b * f - hue))
    return recolor(parts, m)


# ---- naming, registry ------------------------------------------------------------------------------------------
def _camel(t):
    return "".join(w.capitalize() for w in t.lower().split("_")) if "_" in t or t.isupper() else t


ROSTER = {}       # species key -> (family, builder(rng) -> parts, voxel_cm, export name, meta)


def _reg(fam, key, name, fn, cm, meta):
    ROSTER[key] = (fam, fn, cm, name, meta)


for t, fn in PORTAL_ENEMY.items():
    for n in range(1, 11):
        _reg("portal_enemy", "portal_enemy_%s_%02d" % (t.lower(), n), "Mob_Portal_%s_Voxel_%02d" % (t, n),
             (lambda fn=fn, n=n, t=t: lambda rng: vary(fn(rng.uniform(.9, 1.15)), rng))(), PORTAL_ENEMY_CM.get(t, 10),
             {"realm": "Portal Realm", "faction": "enemy", "type": t, "individual": n, "variant_seed": "enemy/%s/%d" % (t, n), "plan_id": "Portal_enemy_%s_%02d" % (t, n)})
for t, row in PORTAL_FRIEND.items():
    for n in range(1, 11):
        _reg("portal_friend", "portal_friend_%s_%02d" % (t.lower(), n), "Mob_Portal_%s_Voxel_%02d" % (t, n),
             (lambda row=row: lambda rng: folk_plan(row, rng))(), 10,
             {"realm": "Portal Realm", "faction": "friendly", "type": t, "individual": n, "variant_seed": "friendly/%s/%d" % (t, n), "plan_id": "Portal_friendly_%s_%02d" % (t, n)})
for t, coat in PORTAL_UNICORNS.items():
    for n in range(1, 11):
        _reg("portal_friend", "portal_friend_%s_%02d" % (t.lower(), n), "Mob_Portal_%s_Voxel_%02d" % (t, n),
             (lambda coat=coat: lambda rng: unicorn_plan(coat, rng))(), 10,
             {"realm": "Portal Realm", "faction": "friendly", "type": t, "individual": n, "variant_seed": "friendly/%s/%d" % (t, n), "plan_id": "Portal_friendly_%s_%02d" % (t, n)})
for t, fn in PORTAL_BOSS.items():
    _reg("portal_boss", "portal_boss_%s" % t.lower(), "Mob_Portal_Boss_%s_Voxel" % t, (lambda fn=fn: lambda rng: fn())(), 10,
         {"realm": "Portal Realm", "faction": "boss", "type": t, "plan_id": "Portal_Boss_%s" % t})
for t, row in PRISM_JOBS.items():
    for n in range(1, 7):
        _reg("prism_hero", "prism_hero_%s_%02d" % (t.lower(), n), "Mob_Prism_Hero_%s_%02d" % (t, n),
             (lambda row=row: lambda rng: folk_plan((row[0], row[1], row[2], row[3], row[4], row[5], row[6]), rng))(), 10,
             {"realm": "Prismheart Realm", "faction": "party", "job": t, "individual": n})
for t, fn in PRISM_MONSTERS.items():
    for n in range(1, 6):
        _reg("prism_monster", "prism_monster_%s_%02d" % (t.lower(), n), "Mob_Prism_%s_%02d" % (t, n),
             (lambda fn=fn: lambda rng: vary(fn(rng.uniform(.9, 1.15)), rng))(), PRISM_MONSTER_CM.get(t, 10),
             {"realm": "Prismheart Realm", "faction": "enemy", "type": t, "individual": n})
for t, fn in PRISM_SUMMONS.items():
    _reg("prism_summon", "prism_summon_%s" % t.lower(), "Mob_Prism_Summon_%s" % t, (lambda fn=fn: lambda rng: fn())(), 10,
         {"realm": "Prismheart Realm", "faction": "summon", "type": t})
for t, row in PRISM_FOLK.items():
    for n in range(1, 5):
        _reg("prism_folk", "prism_folk_%s_%02d" % (t.lower(), n), "Mob_Prism_Folk_%s_%02d" % (t, n), (lambda row=row: lambda rng: folk_plan(row, rng))(), 10,
             {"realm": "Prismheart Realm", "faction": "friendly", "type": t, "individual": n})
for t, fn in PRISM_MOUNT.items():
    for n in range(1, 5):
        _reg("prism_mount", "prism_mount_%s_%02d" % (t.lower(), n), "Mob_Prism_Mount_%s_%02d" % (t, n), (lambda fn=fn: lambda rng: vary(fn(rng.uniform(.95, 1.1)), rng))(), 10,
             {"realm": "Prismheart Realm", "faction": "mount", "type": t, "individual": n})


def plan(key):
    fam, fn, cm, name, meta = ROSTER[key]
    rng = random.Random(sum(ord(c) * (i + 1) for i, c in enumerate(key)))
    return fn(rng)


for fam in sorted({v[0] for v in ROSTER.values()}):
    VC.EXTRA[fam] = (tuple(k for k, v in ROSTER.items() if v[0] == fam), plan)
for k, v in ROSTER.items():
    VC.NAMES[k] = v[3]


def manifest():
    return {v[3]: dict(v[4], family=v[0], species_key=k, voxel_cm=v[2]) for k, v in ROSTER.items()}


if __name__ == "__main__":
    import collections
    import sys
    miss, empty = set(), []
    for k in ROSTER:
        p = plan(k)
        if not sum(len(v) for v in p.values()):
            empty.append(k)
        for v in p.values():
            for *_, c in v:
                if c not in PAL:
                    miss.add(c)
    print(len(ROSTER), dict(collections.Counter(v[0] for v in ROSTER.values())), "empty", empty[:5], "missing", sorted(miss)[:10])
    sys.exit(1 if miss or empty else 0)
