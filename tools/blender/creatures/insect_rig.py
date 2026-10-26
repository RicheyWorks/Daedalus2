# SPDX-License-Identifier: MIT
"""Reusable flying-insect rig (blender-insect/v1): a small moth/butterfly-style skeleton, rigid-bound parts and baked clips,
built by the same creatures/build_quadruped.py builder (it builds any bones/parts/clips recipe). First use: Mob_Moth_Peppered
(G103 Soot Moths, pythagoras 49770). Sizes in metres; front = -Y (lands on UE +Y), up = +Z, L = +X (the insect's own left).

Skeleton (10 bones): Root (on the perch surface, z=0) > Thorax > {Abdomen, Head > Antenna_L/R, WingF_L/R, WingH_L/R}.
Wing bones lie exactly along +-X from the wing roots, so a rotation about the bone's local X is a clean flap about the body
axis (+ = wing tip up on both sides) and local Z sweeps the wing fore/aft.
Parts: lathe/cyl body, slab wings (kitlib.slab: flat outline polygons), stick antennae and legs (feet touch z=0).
Every part is rigid-bound to its bone (bind_mode "rigid"): bone heat is unreliable at insect scale and wings must not bend.
Clips: Idle (rest on bark: wings flat in the bind pose, antennae sway, abdomen breathes) and Flutter (in-place flutter:
wings flap +-, hindwings lag, body bobs). FPS 30, looping (first key == last key).
Body params (body=...): span (wingspan at rest, m), body_len (fraction of span), wing ("moth" delta or "butterfly" broad),
antenna ("feathered" | "thread" | "clubbed"), flutter_deg, flutter_frames."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SCHEMA = "blender-insect/v1"
FPS = 30
SIDES = (("L", 1), ("R", -1))
BODY = {"span": 0.045, "body_len": 0.44, "wing": "moth", "antenna": "feathered", "flutter_deg": 55.0, "flutter_frames": 6, "perch_h": 0.0028}
# wing outlines in units of the half-span, root at x=0 (relative to the wing root), +y = back; left side (mirrored for R)
WINGS = {"moth": {"F": [(0.0, -0.08), (0.3, -0.06), (0.62, 0.05), (1.0, 0.24), (0.9, 0.44), (0.72, 0.6), (0.36, 0.62), (0.08, 0.5), (0.0, 0.22)],
                  "H": [(0.0, 0.0), (0.32, 0.06), (0.62, 0.22), (0.68, 0.46), (0.52, 0.66), (0.26, 0.68), (0.06, 0.52)]},
         "butterfly": {"F": [(0.0, -0.1), (0.35, -0.16), (0.75, -0.1), (1.0, 0.06), (0.88, 0.3), (0.55, 0.42), (0.2, 0.36), (0.0, 0.18)],
                       "H": [(0.0, 0.1), (0.4, 0.2), (0.72, 0.4), (0.7, 0.7), (0.45, 0.86), (0.18, 0.8), (0.02, 0.5)]}}


def params(seed, asset, body=None):
    P = dict(BODY)
    if body:
        bad = set(body) - set(BODY)
        if bad:
            raise ValueError("unknown insect body params: %s" % sorted(bad))
        P.update(body)
    if P["wing"] not in WINGS or P["antenna"] not in ("feathered", "thread", "clubbed"):
        raise ValueError("bad wing/antenna style")
    r = K.rng(seed, asset + ":insect")
    P["L"] = P["span"] * P["body_len"]; P["half"] = P["span"] / 2 - 0.06 * P["L"]; P["zc"] = P["perch_h"]   # half = wing length; apex to apex = span
    P["antenna_sway"] = round(r.uniform(4, 8), 3); P["hind_lag"] = round(r.uniform(0.25, 0.4), 3)
    return P


def _geom(P):
    L, zc, hf = P["L"], P["zc"], P["half"]
    g = {"head": -0.42 * L, "thorax0": -0.34 * L, "thorax1": 0.04 * L, "abd1": 0.58 * L, "rootF": (0.06 * L, -0.24 * L), "rootH": (0.06 * L, -0.02 * L),
         "wz": zc + 0.05 * L}
    return g


def skeleton(P):
    L, zc = P["L"], P["zc"]; g = _geom(P); hf = P["half"]
    B = [{"name": "Root", "parent": None, "head": [0, 0, 0], "tail": [0, 0.2 * L, 0]},
         {"name": "Thorax", "parent": "Root", "head": [0, g["thorax0"], zc], "tail": [0, g["thorax1"], zc]},
         {"name": "Abdomen", "parent": "Thorax", "head": [0, g["thorax1"], zc], "tail": [0, g["abd1"], zc]},
         {"name": "Head", "parent": "Thorax", "head": [0, g["thorax0"], zc], "tail": [0, g["head"], zc]}]
    for nm, s in SIDES:
        B.append({"name": "Antenna_" + nm, "parent": "Head", "head": [s * 0.03 * L, g["head"], zc + 0.04 * L], "tail": [s * 0.2 * L, g["head"] - 0.32 * L, zc + 0.08 * L]})
    for w in ("F", "H"):
        rx, ry = g["root" + w]
        for nm, s in SIDES:
            B.append({"name": "Wing%s_%s" % (w, nm), "parent": "Thorax", "head": [s * rx, ry, g["wz"]], "tail": [s * (rx + 0.5 * hf), ry, g["wz"]]})
    for b in B:
        b["head"] = [round(v, 6) + 0.0 for v in b["head"]]; b["tail"] = [round(v, 6) + 0.0 for v in b["tail"]]
    return B


def _stick(name, p0, p1, r0, r1, slot, seg=4, lod1=None):
    d = [p1[i] - p0[i] for i in range(3)]; Ln = math.sqrt(sum(v * v for v in d)); dx, dy, dz = (v / Ln for v in d)
    rot = (round(-math.degrees(math.asin(max(-1.0, min(1.0, dy)))), 4), round(math.degrees(math.atan2(dx, dz)), 4), 0)
    return K.cyl(name, "z", r0, r1, round(Ln, 6), tuple(round((p0[i] + p1[i]) / 2, 6) for i in range(3)), slot, seg, rot=rot, lod1=lod1)


def parts(P):
    L, zc, hf = P["L"], P["zc"], P["half"]; g = _geom(P); out = []
    def bp(p, bone):
        p["bone"] = bone; p["rigid"] = True; out.append(p)
    bp(K.cyl("Thorax", "y", 0.11 * L, 0.12 * L, g["thorax1"] - g["thorax0"], (0, (g["thorax0"] + g["thorax1"]) / 2, zc), 0, 8, lod1={"segments": 5}), "Thorax")
    bp(K.cyl("Abdomen", "y", 0.1 * L, 0.035 * L, g["abd1"] - g["thorax1"], (0, (g["thorax1"] + g["abd1"]) / 2, zc - 0.01 * L), 0, 8, lod1={"segments": 5}), "Abdomen")
    bp(K.cyl("Head", "y", 0.085 * L, 0.095 * L, 0.09 * L, (0, g["head"] + 0.045 * L, zc), 0, 8, lod1={"segments": 5}), "Head")
    for nm, s in SIDES:
        bp(K.cyl("Eye_" + nm, "x", 0.04 * L, 0.04 * L, 0.03 * L, (s * 0.085 * L, g["head"] + 0.04 * L, zc + 0.01 * L), 1, 6, lod1={"drop": True}), "Head")
    for nm, s in SIDES:                                     # antennae
        a0 = (s * 0.03 * L, g["head"], zc + 0.04 * L); a1 = (s * 0.2 * L, g["head"] - 0.32 * L, zc + 0.08 * L)
        r0 = 0.012 * L * (2.2 if P["antenna"] == "feathered" else 1.0)
        bp(_stick("Antenna_" + nm, a0, a1, r0, 0.005 * L, 1, 4, lod1={"segments": 3}), "Antenna_" + nm)
        if P["antenna"] == "clubbed":
            bp(K.cyl("AntennaClub_" + nm, "y", 0.02 * L, 0.02 * L, 0.05 * L, a1, 1, 6, lod1={"drop": True}), "Antenna_" + nm)
    for w, z_off, slot in (("F", 0.0, 0), ("H", -0.012 * L, 0)):   # wings: forewing over hindwing, flat, morph slot
        rx, ry = g["root" + w]
        for nm, s in SIDES:
            pts = [(s * (rx + u * hf), ry + v * hf) for u, v in WINGS[P["wing"]][w]]
            cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
            bp(K.slab("Wing%s_%s" % (w, nm), [(x - cx, y - cy) for x, y in pts], 0.004 * L, (cx, cy, g["wz"] + z_off), slot, lod1={"segments": (len(pts) + 1) // 2}),
               "Wing%s_%s" % (w, nm))
    for i, (yy, spread) in enumerate(((-0.3, 0.22), (-0.16, 0.26), (-0.02, 0.24))):   # 3 leg pairs, feet on z=0
        for nm, s in SIDES:
            bp(_stick("Leg%d_%s" % (i, nm), (s * 0.08 * L, yy * L, zc - 0.06 * L), (s * spread * L, (yy + (0.08 * (i - 1))) * L, 0.006 * L), 0.012 * L, 0.006 * L, 1, 4,
                      lod1={"segments": 3} if i != 1 else {"drop": True}), "Thorax")
    return out


def _keys(n, fn, step=2):
    fs = list(range(0, n, step)) + [n]
    return [[f, [round(v, 5) + 0.0 for v in fn(2 * math.pi * f / n)]] for f in fs]


def clips(P):
    d = math.radians; out = {}
    sw = P["antenna_sway"]
    out["Idle"] = {"frames": 90, "tracks": {
        "Antenna_L": {"rot": _keys(90, lambda t: (d(2) * math.sin(2 * t), 0, d(sw) * math.sin(t)))},
        "Antenna_R": {"rot": _keys(90, lambda t: (d(2) * math.sin(2 * t + 0.6), 0, -d(sw) * math.sin(t + 0.4)))},
        "Abdomen": {"rot": _keys(90, lambda t: (d(1.5) * math.sin(2 * t), 0, 0))}}}
    n = 2 * P["flutter_frames"]; A = P["flutter_deg"]; lag = P["hind_lag"]
    tr = {}
    for nm, s in SIDES:
        tr["WingF_" + nm] = {"rot": _keys(n, lambda t: (d(12 + A * math.sin(2 * t)), 0, -s * d(8)), step=1)}
        tr["WingH_" + nm] = {"rot": _keys(n, lambda t: (d(10 + 0.9 * A * math.sin(2 * t - lag)), 0, -s * d(4)), step=1)}
        tr["Antenna_" + nm] = {"rot": _keys(n, lambda t: (d(-10), 0, s * d(6)), step=1)}
    tr["Root"] = {"loc": _keys(n, lambda t: (0, 0, P["L"] * (0.25 + 0.08 * math.sin(2 * t + math.pi / 2))), step=1)}
    tr["Abdomen"] = {"rot": _keys(n, lambda t: (d(6) * math.sin(2 * t + 1.2), 0, 0), step=1)}
    out["Flutter"] = {"frames": n, "tracks": tr}
    for c in out.values():
        c["fps"] = FPS; c["loop"] = True; c["seconds"] = round(c["frames"] / FPS, 4)
    return out


def recipe(asset, seed, materials=None, spec=None, body=None):
    P = params(seed, asset, body); B = skeleton(P); Q = parts(P)
    mats = materials or [K.material(asset, 0, "wing / body", "D8D2C2", 0.85), K.material(asset, 1, "eyes / legs / antennae", "2A2622", 0.7)]
    lo, hi = K.bounds(Q); lo1, hi1 = K.bounds(Q, 1)
    t0 = sum(K.part_tris(p) for p in Q if K.in_lod(p, 0)); t1 = sum(K.part_tris(p, 1) for p in Q if K.in_lod(p, 1))
    return {"asset": asset, "kind": "Mob", "schema": SCHEMA, "seed": seed, "params": P, "materials": mats, "bones": B, "parts": Q, "clips": clips(P),
            "bind_mode": "rigid", "spec": spec or {}, "axes": K.AXES + "; L = Blender +X (the insect's own left)", "status": "STAGED NOT READY",
            "bind": "rigid per part (bind_mode rigid): every part 100% on its bone; wings never bend",
            "unreal": {"type": "skeletal mesh + anim sequences (Idle, Flutter), root bone 'Root' on the perch surface", "nanite": "skeletal: Nanite off/not applicable",
                       "collision": "none / tiny sphere in UE", "sockets": "none (bone attach in UE)"},
            "predicted": {"triangles": t0, "lod1_triangles": t1, "lod1_ratio": round(t1 / t0, 3), "bounds_min": lo, "bounds_max": hi,
                          "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)], "bones": len(B)}}


def hops(B, a, b):
    par = {x["name"]: x["parent"] for x in B}
    def chain(n):
        c = []
        while n:
            c.append(n); n = par[n]
        return c
    ca, cb = chain(a), chain(b)
    for i, x in enumerate(ca):
        if x in cb:
            return i + cb.index(x)
    return 99
