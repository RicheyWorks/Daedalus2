# SPDX-License-Identifier: MIT
"""Reusable quadruped rig + clip recipe (blender-team), pure Python, no Blender. blender-quadruped/v1.
recipe(asset, seed, length, ...) -> one manifest: seeded body params, kitlib parts (each bound to a bone), a 15-bone skeleton
(Root, Hips, Spine, Chest, Neck, Head, Tail, Leg{FL,FR,BL,BR}_{Upper,Lower}), and baked looping clips Idle / Walk / Run as
per-bone keyframes (Euler XYZ radians in bone-local space, plus a Hips bob). build_quadruped.py turns it into a skinned glb:
ARMATURE_AUTO (bone-heat) weights, validated per part against the bone tree, with a rigid per-part fallback; <= 4 influences,
normalised; each clip exported as its own glTF animation (skinned, so clips are allowed: unreal-epic-boss 48497).
Axes (blender-kit/v1): metres, Blender Z up, front = Blender -Y = UE +X, origin = ground centre under the body; L = Blender +X
(the animal's own left when it faces -Y)."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SCHEMA = "blender-quadruped/v1"
FPS = 30
LEGS = ("FL", "FR", "BL", "BR")
PAIRS = {"walk_diagonal": [("FL", "BR"), ("FR", "BL")]}


def params(seed, asset, length=1.6):
    r = K.rng(seed, asset); u = lambda a, b: round(r.uniform(a, b), 4)
    return {"length": length, "body_h": round(length * 0.34 * (1 + u(-0.04, 0.04)), 4), "body_w": round(length * 0.34 * (1 + u(-0.05, 0.05)), 4),
            "leg": round(length * 0.32 * (1 + u(-0.04, 0.04)), 4), "horn": round(length * 0.17 * (1 + u(-0.1, 0.1)), 4),
            "horn_splay": u(30, 42), "plates": r.randint(4, 6), "plate_h": round(length * 0.05 * (1 + u(-0.15, 0.15)), 4),
            "tail_droop": u(25, 40), "stride_walk": u(16, 20), "stride_run": u(32, 38), "idle_look": u(5, 9)}


def skeleton(P):
    L, h, g = P["length"], P["body_h"], P["leg"]; zc = g + h * 0.5
    b = [("Root", None, (0, 0, 0), (0, -0.15 * L, 0)),
         ("Hips", "Root", (0, 0.2 * L, zc), (0, 0.0, zc)),
         ("Spine", "Hips", (0, 0.0, zc), (0, -0.18 * L, zc)),
         ("Chest", "Spine", (0, -0.18 * L, zc), (0, -0.3 * L, zc + 0.04 * L)),
         ("Neck", "Chest", (0, -0.3 * L, zc + 0.04 * L), (0, -0.38 * L, g + h * 0.85)),
         ("Head", "Neck", (0, -0.38 * L, g + h * 0.85), (0, -0.5 * L, g + h * 0.8)),
         ("Tail", "Hips", (0, 0.3 * L, g + h * 0.75), (0, 0.48 * L, g + h * 0.5))]
    for l in LEGS:
        x = (0.13 if l[1] == "L" else -0.13) * L; y = (-0.21 if l[0] == "F" else 0.21) * L
        b += [("Leg%s_Upper" % l, "Chest" if l[0] == "F" else "Hips", (x, y, g), (x, y, g * 0.5)),
              ("Leg%s_Lower" % l, "Leg%s_Upper" % l, (x, y, g * 0.5), (x, y, 0.02 * L))]
    return [{"name": n, "parent": p, "head": [round(v, 5) for v in hd], "tail": [round(v, 5) for v in tl]} for n, p, hd, tl in b]


def parts(P, seed, asset):
    L, h, w, g = P["length"], P["body_h"], P["body_w"], P["leg"]; r = K.rng(seed, asset + ":parts")
    def bp(p, bone): p["bone"] = bone; return p
    out = [bp(K.box("Torso", (w, 0.62 * L, h), (0, 0.02 * L, g + h / 2), 0), "Spine"),
           bp(K.box("Neck", (0.2 * L, 0.14 * L, 0.17 * L), (0, -0.33 * L, g + h * 0.78), 0, rot=(-25, 0, 0)), "Neck"),
           bp(K.box("Head", (0.2 * L, 0.17 * L, 0.16 * L), (0, -0.415 * L, g + h * 0.86), 0), "Head"),
           bp(K.box("Snout", (0.14 * L, 0.085 * L, 0.1 * L), (0, -0.4575 * L, g + h * 0.8), 0, lod1={"drop": True}), "Head")]
    for s in (1, -1):
        out.append(bp(K.cyl("Horn%s" % ("L" if s > 0 else "R"), "z", 0.035 * L, 0.008 * L, P["horn"],
                            (s * (0.1 * L + math.sin(math.radians(P["horn_splay"])) * P["horn"] / 2), -0.4 * L, g + h * 0.86 + 0.08 * L + math.cos(math.radians(P["horn_splay"])) * P["horn"] / 2 - 0.02 * L),
                            1, 8, rot=(0, s * P["horn_splay"], 0), lod1={"segments": 4}), "Head"))
    n = P["plates"]
    for i in range(n):                                   # the "horn back": a seeded ridge of bony plates along the spine
        y = -0.2 * L + 0.4 * L * i / max(1, n - 1); ph = P["plate_h"] * (1 + r.uniform(-0.2, 0.2))
        out.append(bp(K.box("Plate%d" % i, (0.05 * L, 0.06 * L, ph), (0, y, g + h + ph / 2 - 0.01 * L), 1, rot=(r.uniform(-8, 8), 0, 0), lod1={"drop": True}),
                      "Chest" if y < -0.1 * L else ("Spine" if y < 0.1 * L else "Hips")))
    out.append(bp(K.cyl("Tail", "y", 0.025 * L, 0.012 * L, 0.18 * L, (0, 0.39 * L, g + h * 0.62), 0, 6, rot=(-P["tail_droop"], 0, 0), lod1={"segments": 4}), "Tail"))
    for l in LEGS:
        x = (0.13 if l[1] == "L" else -0.13) * L; y = (-0.21 if l[0] == "F" else 0.21) * L
        out += [bp(K.box("Leg%s_Upper" % l, (0.1 * L, 0.11 * L, g * 0.55), (x, y, g * 0.72), 0), "Leg%s_Upper" % l),
                bp(K.box("Leg%s_Lower" % l, (0.075 * L, 0.085 * L, g * 0.5 - 0.03 * L), (x, y, g * 0.25 + 0.015 * L + 0.015 * L), 0), "Leg%s_Lower" % l),
                bp(K.box("Hoof%s" % l, (0.085 * L, 0.095 * L, 0.03 * L), (x, y, 0.015 * L), 2, lod1={"drop": True}), "Leg%s_Lower" % l)]
    return out


def _keys(n, fn, step=2):
    fs = list(range(0, n, step)) + [n]
    return [[f, [round(v, 5) + 0.0 for v in fn(2 * math.pi * f / n)]] for f in fs]


def clips(P):
    d = math.radians; out = {}
    # Idle: 2 s breathing loop, slow look left/right, tail flick; legs still.
    out["Idle"] = {"frames": 60, "tracks": {
        "Chest": {"rot": _keys(60, lambda t: (d(1.5) * math.sin(t), 0, 0))},
        "Neck": {"rot": _keys(60, lambda t: (d(2) * math.sin(t + 1), 0, 0))},
        "Head": {"rot": _keys(60, lambda t: (0, 0, d(P["idle_look"]) * math.sin(t)))},
        "Tail": {"rot": _keys(60, lambda t: (0, 0, d(12) * math.sin(2 * t)))}}}
    for name, n, amp, bob, phase in (("Walk", 32, P["stride_walk"], 0.015, {"FL": 0.0, "BR": 0.0, "FR": math.pi, "BL": math.pi}),
                                     ("Run", 18, P["stride_run"], 0.05, {"FL": 0.0, "FR": 0.35, "BL": math.pi, "BR": math.pi + 0.35})):
        tr = {}
        for l in LEGS:
            ph = phase[l]
            tr["Leg%s_Upper" % l] = {"rot": _keys(n, lambda t, ph=ph: (d(amp) * math.sin(t + ph), 0, 0))}
            tr["Leg%s_Lower" % l] = {"rot": _keys(n, lambda t, ph=ph: (d(amp * 1.2) * max(0.0, math.sin(t + ph + math.pi / 2)), 0, 0))}
        tr["Hips"] = {"loc": _keys(n, lambda t: (0, 0, bob * abs(math.sin(t)) if name == "Run" else bob * math.sin(2 * t)))}
        tr["Chest"] = {"rot": _keys(n, lambda t: (d(6 if name == "Run" else 1.5) * math.sin(t), 0, 0))}
        tr["Neck"] = {"rot": _keys(n, lambda t: (d(4 if name == "Walk" else 7) * math.sin(2 * t), 0, 0))}
        tr["Tail"] = {"rot": _keys(n, lambda t: (d(10 if name == "Run" else 4) * math.sin(t), 0, d(6) * math.sin(t)))}
        out[name] = {"frames": n, "tracks": tr}
    for c in out.values():
        c["fps"] = FPS; c["loop"] = True; c["seconds"] = round(c["frames"] / FPS, 4)
    return out


def recipe(asset, seed, length=1.6, materials=None, spec=None):
    P = params(seed, asset, length); B = skeleton(P); Q = parts(P, seed, asset)
    mats = materials or [K.material(asset, 0, "dusty hide", "8A6A4A", 0.9), K.material(asset, 1, "horn ivory", "E8DCC0", 0.7),
                         K.material(asset, 2, "hoof", "3A3030", 0.8)]
    lo, hi = K.bounds(Q); lo1, hi1 = K.bounds(Q, 1)
    t0 = sum(K.part_tris(p) for p in Q if K.in_lod(p, 0)); t1 = sum(K.part_tris(p, 1) for p in Q if K.in_lod(p, 1))
    m = {"asset": asset, "kind": "Mob", "schema": SCHEMA, "seed": seed, "params": P, "materials": mats, "bones": B, "parts": Q, "clips": clips(P),
         "spec": spec or {}, "axes": K.AXES + "; L = Blender +X (the animal's own left)", "status": "STAGED NOT READY",
         "bind": "ARMATURE_AUTO bone-heat weights, validated per part (dominant bone within 2 hops of the part's bone), rigid per-part fallback; <=4 influences, normalised",
         "unreal": {"type": "skeletal mesh + 3 anim sequences (Idle, Walk, Run), root bone 'Root'", "nanite": "skeletal: Nanite off/not applicable",
                    "collision": "capsule/physics asset in UE (no UCX on skeletal meshes)", "sockets": "none (bone attach in UE)"},
         "predicted": {"triangles": t0, "lod1_triangles": t1, "lod1_ratio": round(t1 / t0, 3), "bounds_min": lo, "bounds_max": hi,
                       "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)], "bones": len(B)}}
    return m


def hops(B, a, b):
    par = {x["name"]: x["parent"] for x in B}
    def chain(n):
        c = [];
        while n: c.append(n); n = par[n]
        return c
    ca, cb = chain(a), chain(b)
    for i, x in enumerate(ca):
        if x in cb: return i + cb.index(x)
    return 99
