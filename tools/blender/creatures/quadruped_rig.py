# SPDX-License-Identifier: MIT
"""Reusable quadruped rig + clip recipe (blender-team), pure Python, no Blender. blender-quadruped/v1.
recipe(asset, seed, length, ...) -> one manifest: seeded body params, kitlib parts (each bound to a bone), a 15-bone skeleton
(Root, Hips, Spine, Chest, Neck, Head, Tail, Leg{FL,FR,BL,BR}_{Upper,Lower}), and baked looping clips Idle / Walk / Run as
per-bone keyframes (Euler XYZ radians in bone-local space, plus a Hips bob). build_quadruped.py turns it into a skinned glb:
ARMATURE_AUTO (bone-heat) weights, validated per part against the bone tree, with a rigid per-part fallback; <= 4 influences,
normalised; each clip exported as its own glTF animation (skinned, so clips are allowed: unreal-epic-boss 48497).
Body params (body= dict, all optional; the defaults are the Hornback): ratios body_h / body_w / leg / horn (x length), plates
(ridge count, 0 = none), tail (tail length / length), head_lift (extra neck rise / length) and ornament: "horns" (default), "antlers"
(seeded branching beams via antlers(): antler size / length, tines per side) or "none". Defaults draw exactly the same random numbers.
Axes (blender-kit/v1): metres, Blender Z up, front = Blender -Y = UE +X, origin = ground centre under the body; L = Blender +X
(the animal's own left when it faces -Y)."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SCHEMA = "blender-quadruped/v1"
FPS = 30
LEGS = ("FL", "FR", "BL", "BR")
PAIRS = {"walk_diagonal": [("FL", "BR"), ("FR", "BL")]}


BODY = {"body_h": 0.34, "body_w": 0.34, "leg": 0.32, "horn": 0.17, "plates": None, "tail": 0.18, "head_lift": 0.0,
        "ornament": "horns", "antler": 0.3, "tines": None}


def params(seed, asset, length=1.6, body=None):
    bd = dict(BODY, **(body or {})); unknown = set(body or {}) - set(BODY)
    if unknown:
        raise ValueError("unknown body params: %s" % sorted(unknown))
    if bd["ornament"] not in ("horns", "antlers", "none"):
        raise ValueError("ornament must be horns / antlers / none")
    r = K.rng(seed, asset); u = lambda a, b: round(r.uniform(a, b), 4)
    P = {"length": length, "body_h": round(length * bd["body_h"] * (1 + u(-0.04, 0.04)), 4), "body_w": round(length * bd["body_w"] * (1 + u(-0.05, 0.05)), 4),
         "leg": round(length * bd["leg"] * (1 + u(-0.04, 0.04)), 4), "horn": round(length * bd["horn"] * (1 + u(-0.1, 0.1)), 4),
         "horn_splay": u(30, 42), "plates": r.randint(4, 6), "plate_h": round(length * 0.05 * (1 + u(-0.15, 0.15)), 4),
         "tail_droop": u(25, 40), "stride_walk": u(16, 20), "stride_run": u(32, 38), "idle_look": u(5, 9)}
    if bd["plates"] is not None:
        P["plates"] = bd["plates"]
    if body:                                             # extra keys only when asked, so default manifests stay byte-identical
        rb = K.rng(seed, asset + ":body")
        P.update({"ornament": bd["ornament"], "tail": bd["tail"], "head_lift": round(length * bd["head_lift"], 4)})
        if bd["ornament"] == "antlers":
            P.update({"antler": round(length * bd["antler"] * (1 + rb.uniform(-0.08, 0.08)), 4), "tines": bd["tines"] or rb.randint(5, 6),
                      "antler_spread": round(rb.uniform(28, 36), 3), "antler_seed": rb.randint(0, 10 ** 6)})
    return P


def _lift(P):
    return P.get("head_lift", 0.0)


def skeleton(P):
    L, h, g = P["length"], P["body_h"], P["leg"]; zc = g + h * 0.5; hl = _lift(P)
    b = [("Root", None, (0, 0, 0), (0, -0.15 * L, 0)),
         ("Hips", "Root", (0, 0.2 * L, zc), (0, 0.0, zc)),
         ("Spine", "Hips", (0, 0.0, zc), (0, -0.18 * L, zc)),
         ("Chest", "Spine", (0, -0.18 * L, zc), (0, -0.3 * L, zc + 0.04 * L)),
         ("Neck", "Chest", (0, -0.3 * L, zc + 0.04 * L), (0, -0.38 * L, g + h * 0.85 + hl)),
         ("Head", "Neck", (0, -0.38 * L, g + h * 0.85 + hl), (0, -0.5 * L, g + h * 0.8 + hl)),
         ("Tail", "Hips", (0, 0.3 * L, g + h * 0.75), (0, 0.48 * L, g + h * 0.5) if "tail" not in P else (0, 0.3 * L + P["tail"] * L, g + h * 0.75 - 0.25 * h * P["tail"] / 0.18))]
    for l in LEGS:
        x = (0.13 if l[1] == "L" else -0.13) * L; y = (-0.21 if l[0] == "F" else 0.21) * L
        b += [("Leg%s_Upper" % l, "Chest" if l[0] == "F" else "Hips", (x, y, g), (x, y, g * 0.5)),
              ("Leg%s_Lower" % l, "Leg%s_Upper" % l, (x, y, g * 0.5), (x, y, 0.02 * L))]
    return [{"name": n, "parent": p, "head": [round(v, 5) for v in hd], "tail": [round(v, 5) for v in tl]} for n, p, hd, tl in b]


def parts(P, seed, asset):
    L, h, w, g = P["length"], P["body_h"], P["body_w"], P["leg"]; r = K.rng(seed, asset + ":parts")
    def bp(p, bone): p["bone"] = bone; return p
    hl = _lift(P); orn = P.get("ornament", "horns")
    out = [bp(K.box("Torso", (w, 0.62 * L, h), (0, 0.02 * L, g + h / 2), 0), "Spine"),
           bp(K.box("Neck", (0.2 * L, 0.14 * L, 0.17 * L + hl), (0, -0.33 * L, g + h * 0.78 + hl / 2), 0, rot=(-25, 0, 0)), "Neck"),
           bp(K.box("Head", (0.2 * L, 0.17 * L, 0.16 * L), (0, -0.415 * L, g + h * 0.86 + hl), 0), "Head"),
           bp(K.box("Snout", (0.14 * L, 0.085 * L, 0.1 * L), (0, -0.4575 * L, g + h * 0.8 + hl), 0, lod1={"drop": True}), "Head")]
    if orn == "antlers":
        out += [bp(q, "Head") for q in antlers(P, (0, -0.4 * L, g + h * 0.86 + hl + 0.08 * L))]
    for s in ((1, -1) if orn == "horns" else ()):
        out.append(bp(K.cyl("Horn%s" % ("L" if s > 0 else "R"), "z", 0.035 * L, 0.008 * L, P["horn"],
                            (s * (0.1 * L + math.sin(math.radians(P["horn_splay"])) * P["horn"] / 2), -0.4 * L, g + h * 0.86 + 0.08 * L + math.cos(math.radians(P["horn_splay"])) * P["horn"] / 2 - 0.02 * L),
                            1, 8, rot=(0, s * P["horn_splay"], 0), lod1={"segments": 4}), "Head"))
    n = P["plates"]
    for i in range(n):                                   # the "horn back": a seeded ridge of bony plates along the spine
        y = -0.2 * L + 0.4 * L * i / max(1, n - 1); ph = P["plate_h"] * (1 + r.uniform(-0.2, 0.2))
        out.append(bp(K.box("Plate%d" % i, (0.05 * L, 0.06 * L, ph), (0, y, g + h + ph / 2 - 0.01 * L), 1, rot=(r.uniform(-8, 8), 0, 0), lod1={"drop": True}),
                      "Chest" if y < -0.1 * L else ("Spine" if y < 0.1 * L else "Hips")))
    tlen, tcy = (0.18 * L, 0.39 * L) if "tail" not in P else (P["tail"] * L, 0.3 * L + P["tail"] * L / 2)
    out.append(bp(K.cyl("Tail", "y", 0.025 * L, 0.012 * L, tlen, (0, tcy, g + h * 0.62), 0, 6, rot=(-P["tail_droop"], 0, 0), lod1={"segments": 4}), "Tail"))
    for l in LEGS:
        x = (0.13 if l[1] == "L" else -0.13) * L; y = (-0.21 if l[0] == "F" else 0.21) * L
        out += [bp(K.box("Leg%s_Upper" % l, (0.1 * L, 0.11 * L, g * 0.55), (x, y, g * 0.72), 0), "Leg%s_Upper" % l),
                bp(K.box("Leg%s_Lower" % l, (0.075 * L, 0.085 * L, g * 0.5 - 0.03 * L), (x, y, g * 0.25 + 0.015 * L + 0.015 * L), 0), "Leg%s_Lower" % l),
                bp(K.box("Hoof%s" % l, (0.085 * L, 0.095 * L, 0.03 * L), (x, y, 0.015 * L), 2, lod1={"drop": True}), "Leg%s_Lower" % l)]
    return out


def stick(name, p0, p1, r0, r1, slot, seg=6, lod1=None):
    """Tapered cylinder from p0 to p1 (kitlib cyl on z, Euler XYZ: z -> direction)."""
    d = [p1[i] - p0[i] for i in range(3)]; Ln = math.sqrt(sum(v * v for v in d)); dx, dy, dz = (v / Ln for v in d)
    rot = (round(-math.degrees(math.asin(max(-1.0, min(1.0, dy)))), 4), round(math.degrees(math.atan2(dx, dz)), 4), 0)
    return K.cyl(name, "z", r0, r1, round(Ln, 5), tuple(round((p0[i] + p1[i]) / 2, 5) for i in range(3)), slot, seg, rot=rot,
                 lod1=lod1 if lod1 is not None else {"segments": 4})


def antlers(P, skull, slot=1):
    """Seeded branching antlers on the skull top: per side a 3-segment main beam sweeping out, up and back, with
    P["tines"] tines pointing forward/up along it (the first, brow tine, low and forward). Size = P["antler"] (height)."""
    A, n, sp = P["antler"], P["tines"], math.radians(P["antler_spread"]); r = K.rng(P["antler_seed"], "antlers")
    out = []; jit = [r.uniform(-1, 1) for _ in range(n)]        # one draw per tine, shared by both sides (mirrored)
    for s, nm in ((1, "L"), (-1, "R")):
        pts = [skull]
        for k, (o, b, up) in enumerate(((0.32, 0.1, 0.38), (0.62, 0.3, 0.72), (0.66, 0.22, 1.0))):
            pts.append((skull[0] + s * A * o * math.sin(sp) / math.sin(math.radians(32)), skull[1] + A * b, skull[2] + A * up))
        rad = [0.024 * A / 0.66 * 1.6, 0.018 * A / 0.66 * 1.6, 0.012 * A / 0.66 * 1.6, 0.005 * A / 0.66 * 1.6]
        for k in range(3):
            out.append(stick("Antler%s_Beam%d" % (nm, k), pts[k], pts[k + 1], rad[k], rad[k + 1], slot))
        for t in range(n):
            f = 0.12 + 0.8 * t / max(1, n - 1); seg = min(2, int(f * 3)); ff = f * 3 - seg
            base = tuple(pts[seg][i] + (pts[seg + 1][i] - pts[seg][i]) * ff for i in range(3))
            tl = A * (0.42 if t == 0 else 0.3 + 0.08 * jit[t]) * (1 - 0.35 * f)
            fwd, upf = (0.85, 0.35) if t == 0 else (0.45, 0.85)
            tip = (base[0] + s * tl * 0.12, base[1] - tl * fwd, base[2] + tl * upf)
            out.append(stick("Antler%s_Tine%d" % (nm, t), base, tip, rad[min(3, seg + 1)] * 0.9, 0.003, slot, 6, lod1={"segments": 4} if t % 2 == 0 else {"drop": True}))
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


def recipe(asset, seed, length=1.6, materials=None, spec=None, body=None):
    P = params(seed, asset, length, body); B = skeleton(P); Q = parts(P, seed, asset)
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
