# SPDX-License-Identifier: MIT
"""Reusable small-bird rig (blender-bird/v1): a gull/pigeon-scale low-poly skeleton, rigid-bound parts and baked clips, built by
creatures/build_quadruped.py like insect_rig.py (same conventions). First use: Char_YTM_Gull (G139 Harbour Round, youtube-master 50117).
Sizes in metres; front = -Y (lands on UE +Y), up = +Z, L = +X (the bird's own left). Feet on z=0.
Skeleton (10 bones): Root (ground) > Body > {Neck > Head > Beak_Lower, Wing_L/R (folded along the flanks, bone along -Y..+Y
from the shoulder so local Y rotation lifts the wing), Tail, Leg_L/R}.
Parts: lathe body and head, cone beak (upper on Head, lower on Beak_Lower), slab wings / tail / webbed feet, stick legs.
Every part is rigid-bound (bind_mode "rigid"): low-poly faceted birds read best with hard part breaks, and beaks must not bend.
Clips (FPS 30, looping): Idle (breathing, slow head turns, a tail flick) and Squawk (head up and forward, beak opens wide,
wings half-lift, body leans; the HarbourRound "gulls answer back" on a clash).
Body params (body=...): length (beak tip to tail tip, m), height_frac (standing height / length), squawk_deg (beak gape),
squawk_frames, wing_lift_deg; raptors (G504 hawk) add beak_style "hook" (deep base, downward-curved hooked tip), feet "talons"
(3 forward + 1 hind toe, each ending in a down-curved claw), wing_tips "fingered" (5 splayed primaries) and tail_bands N (dark bars);
long-legged birds (G142 crane) add leg_frac (leg / length, default 0.2), neck_r (neck radius scale)
and head_scale (written into params only when given, so the gull pin stays byte-identical).
More clips via recipe(clip_names=...): Walk (alternating leg swing, the stance foot kept planted by a body drop, head pump),
Fly (wings spread out sideways and flapping, neck stretched forward, legs trailing) and Dance (crane courtship: hops with the
wings half open, bowing between hops). Wing bones point +Y from the shoulder (roll 0, local axes = world): Euler X raises the
wing, Euler Z swings it out sideways (-85 deg for the left wing spreads it), applied X then Z.
Bone sockets via recipe(sockets=[(name, bone, location)]): bone-bound attach points (UE skeleton sockets; build_quadruped writes
<asset>.sockets.json with the bone and the offset from the bone head)."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SCHEMA = "blender-bird/v1"
FPS = 30
SIDES = (("L", 1), ("R", -1))
BODY = {"length": 0.6, "height_frac": 0.62, "squawk_deg": 38.0, "squawk_frames": 36, "wing_lift_deg": 28.0}
EXTRA = {"leg_frac": 0.2, "neck_r": 1.0, "head_scale": 1.0, "tail_off": 0.18,
         # raptor options (2026-10-29, G504 marsh hawk); absent = the original gull/crane parts, byte-identical pins
         "beak_style": "straight", "feet": "webbed", "wing_tips": "plain", "tail_bands": 0}
CLIPS = ("Idle", "Squawk", "Walk", "Fly", "Dance")


def params(seed, asset, body=None):
    P = dict(BODY)
    if body:
        bad = set(body) - set(BODY) - set(EXTRA)
        if bad:
            raise ValueError("unknown bird body params: %s" % sorted(bad))
        P.update(body)
    r = K.rng(seed, asset + ":bird"); L = P["length"]
    P["L"] = L; P["leg"] = round(P.get("leg_frac", 0.2) * L, 6); P["bz"] = round(P["leg"] + 0.12 * L, 6)        # body centre height
    P["head_turn"] = round(r.uniform(18, 30), 3); P["tail_flick"] = round(r.uniform(6, 10), 3)
    return P


def _g(P):
    L, bz = P["L"], P["bz"]
    b0 = -0.355 * L if "head_scale" not in P else -0.3 * L - 0.055 * P["head_scale"] * L     # beak root at the face
    return {"neck0": (-0.2 * L, bz + 0.06 * L), "head": (-0.3 * L, P["height_frac"] * L - 0.06 * L), "beak0": b0, "beak1": b0 - 0.145 * L,
            "tail0": 0.2 * L, "tail1": 0.5 * L, "shoulder": (0.11 * L, -0.12 * L, bz + 0.05 * L), "hip": (0.06 * L, 0.04 * L)}


def skeleton(P):
    L, bz = P["L"], P["bz"]; g = _g(P); hy, hz = g["head"]
    B = [{"name": "Root", "parent": None, "head": [0, 0, 0], "tail": [0, 0.2 * L, 0]},
         {"name": "Body", "parent": "Root", "head": [0, -0.15 * L, bz], "tail": [0, 0.2 * L, bz]},
         {"name": "Neck", "parent": "Body", "head": [0, g["neck0"][0], g["neck0"][1]], "tail": [0, hy + 0.03 * L, hz - 0.04 * L]},
         {"name": "Head", "parent": "Neck", "head": [0, hy + 0.03 * L, hz - 0.04 * L], "tail": [0, g["beak0"], hz]},
         {"name": "Beak_Lower", "parent": "Head", "head": [0, g["beak0"], hz - 0.02 * L], "tail": [0, g["beak1"], hz - 0.03 * L]},
         {"name": "Tail", "parent": "Body", "head": [0, g["tail0"], bz + 0.02 * L], "tail": [0, g["tail1"], bz + 0.08 * L]}]
    sx, sy, sz = g["shoulder"]
    for nm, s in SIDES:
        B.append({"name": "Wing_" + nm, "parent": "Body", "head": [s * sx, sy, sz], "tail": [s * sx, sy + 0.5 * L, sz + 0.02 * L]})
    for nm, s in SIDES:
        B.append({"name": "Leg_" + nm, "parent": "Body", "head": [s * g["hip"][0], g["hip"][1], P["leg"] + 0.04 * L], "tail": [s * g["hip"][0], g["hip"][1], 0.01 * L]})
    for b in B:
        b["head"] = [round(v, 6) + 0.0 for v in b["head"]]; b["tail"] = [round(v, 6) + 0.0 for v in b["tail"]]
    return B


def _stick(name, p0, p1, r0, r1, slot, seg=4, lod1=None):
    d = [p1[i] - p0[i] for i in range(3)]; Ln = math.sqrt(sum(v * v for v in d)); dx, dy, dz = (v / Ln for v in d)
    rot = (round(-math.degrees(math.asin(max(-1.0, min(1.0, dy)))), 4), round(math.degrees(math.atan2(dx, dz)), 4), 0)
    return K.cyl(name, "z", r0, r1, round(Ln, 6), tuple(round((p0[i] + p1[i]) / 2, 6) for i in range(3)), slot, seg, rot=rot, lod1=lod1)


def parts(P):
    L, bz = P["L"], P["bz"]; g = _g(P); hy, hz = g["head"]; out = []
    def bp(p, bone):
        p["bone"] = bone; p["rigid"] = True; out.append(p)
    prof = [(0.0, -0.17), (0.06, -0.14), (0.1, -0.06), (0.11, 0.04), (0.09, 0.14), (0.05, 0.22), (0.0, 0.26)]   # body along Y (lathe on its side)
    bp(K.lathe("Body", [(r * L, z * L) for r, z in prof], (0, 0.0, bz), 0, 8, False, False, rot=(-90, 0, 0), lod1={"segments": 6}), "Body")
    nr = P.get("neck_r", 1.0); hs = P.get("head_scale", 1.0)
    bp(_stick("Neck", (0, g["neck0"][0], g["neck0"][1] - 0.02 * L), (0, hy + 0.02 * L, hz - 0.04 * L), 0.055 * L * nr, 0.045 * L * nr, 0, 6, lod1={"segments": 4}), "Neck")
    hp = [(r * hs, z * hs) for r, z in [(0.0, -0.06), (0.045, -0.04), (0.06, 0.0), (0.045, 0.045), (0.0, 0.06)]]
    bp(K.lathe("Head", [(r * L, z * L) for r, z in hp], (0, hy, hz), 0, 8, False, False, rot=(90, 0, 0), lod1={"segments": 5}), "Head")
    for nm, s in SIDES:
        bp(K.cyl("Eye_" + nm, "x", 0.012 * L, 0.012 * L, 0.006 * L, (s * 0.05 * L * hs, hy - 0.015 * L * hs, hz + 0.012 * L * hs), 3, 6, lod1={"drop": True}), "Head")
    if P.get("beak_style", "straight") == "hook":     # raptor: deep base, curved culmen, tip hooks down past the lower mandible
        b0, bl = g["beak0"], (g["beak0"] - g["beak1"]) * 0.75
        bp(_stick("Beak_Upper", (0, b0 + 0.01 * L, hz + 0.002 * L), (0, b0 - 0.45 * bl, hz - 0.002 * L), 0.026 * L * hs, 0.019 * L * hs, 1, 6, lod1={"segments": 4}), "Head")
        bp(_stick("Beak_Curve", (0, b0 - 0.45 * bl, hz - 0.002 * L), (0, b0 - 0.85 * bl, hz - 0.022 * L), 0.019 * L * hs, 0.011 * L * hs, 1, 6, lod1={"segments": 4}), "Head")
        bp(_stick("Beak_Hook", (0, b0 - 0.85 * bl, hz - 0.022 * L), (0, b0 - 0.93 * bl, hz - 0.058 * L), 0.011 * L * hs, 0.002 * L, 1, 5, lod1={"segments": 3}), "Head")
        bp(K.cyl("Cere", "y", 0.028 * L * hs, 0.027 * L * hs, 0.02 * L, (0, b0 + 0.004 * L, hz + 0.004 * L), 1, 6, lod1={"drop": True}), "Head")
        bp(_stick("Beak_Lower", (0, b0, hz - 0.02 * L), (0, b0 - 0.62 * bl, hz - 0.03 * L), 0.015 * L * hs, 0.004 * L, 1, 5, lod1={"segments": 3}), "Beak_Lower")
    else:
        bp(K.cyl("Beak_Upper", "y", 0.016 * L, 0.004 * L, g["beak0"] - g["beak1"], (0, (g["beak0"] + g["beak1"]) / 2, hz - 0.004 * L), 1, 6, lod1={"segments": 4}), "Head")
        bp(K.cyl("Beak_Lower", "y", 0.012 * L, 0.003 * L, (g["beak0"] - g["beak1"]) * 0.85, (0, g["beak0"] - (g["beak0"] - g["beak1"]) * 0.425, hz - 0.024 * L), 1, 6, lod1={"segments": 4}), "Beak_Lower")
    sx, sy, sz = g["shoulder"]
    wing = [(0.0, -0.02), (0.02, 0.12), (0.02, 0.36), (0.0, 0.6), (-0.03, 0.42), (-0.05, 0.16), (-0.04, 0.0)]   # (z, y) along the flank
    for nm, s in SIDES:   # folded wing: a slab standing on its edge against the flank (outline in the YZ plane)
        pts = [(y * L, z * L) for z, y in wing]; cy = sum(p[0] for p in pts) / len(pts); cz = sum(p[1] for p in pts) / len(pts)
        bp(K.slab("Wing_" + nm, [(y - cy, z - cz) for y, z in pts], 0.012 * L, (s * (sx + 0.006 * L), sy + cy, sz + cz), 2, rot=(90, 0, 90),
                  lod1={"segments": 4}), "Wing_" + nm)
        if P.get("wing_tips", "plain") == "fingered":   # 5 splayed primaries ("fingers") past the wing tip, fanning down
            for k in range(5):
                a_ = math.radians(-10 - 9 * k); y0, z0 = sy + 0.52 * L, sz - 0.01 * L * k; ln = (0.13 - 0.012 * abs(k - 1)) * L
                bp(K.slab("Primary%d_%s" % (k, nm), [(0.0, -0.008 * L), (ln, -0.005 * L), (ln + 0.012 * L, 0.0), (ln, 0.005 * L), (0.0, 0.008 * L)], 0.006 * L,
                          (s * (sx + 0.004 * L + 0.002 * L * k), y0 + 0.5 * ln * math.cos(a_), z0 + 0.5 * ln * math.sin(a_)), 3, rot=(90 + math.degrees(a_), 0, 90),
                          lod1={"drop": True} if k % 2 else None), "Wing_" + nm)
        else:
            bp(K.slab("WingTip_" + nm, [(-0.05 * L, 0.0), (0.05 * L, 0.0), (0.0, 0.03 * L)], 0.01 * L, (s * (sx + 0.004 * L), sy + 0.5 * L, sz + 0.0), 3, rot=(90, 0, 90),
                      lod1={"drop": True}), "Wing_" + nm)
    bp(K.slab("Tail", [(-0.06 * L, -0.06 * L), (0.06 * L, -0.06 * L), (0.055 * L, 0.12 * L), (-0.055 * L, 0.12 * L)], 0.01 * L, (0, g["tail0"] + P.get("tail_off", 0.18) * L, bz + 0.03 * L), 0,
              rot=(8, 0, 0)), "Tail")   # 4-point slabs keep their outline at LOD1 (halving leaves 2 points)
    for k in range(int(P.get("tail_bands", 0))):     # dark bars across the top of the tail (slot 3), sharing the tail's 8 deg tilt
        ty = g["tail0"] + P.get("tail_off", 0.18) * L - 0.03 * L + 0.05 * L * k
        bp(K.box("TailBand%d" % k, (0.112 * L - 0.002 * L * k, 0.016 * L, 0.004 * L), (0, ty, bz + 0.03 * L + 0.006 * L + (ty - g["tail0"] - P.get("tail_off", 0.18) * L) * math.tan(math.radians(8))), 3,
                     rot=(8, 0, 0), bevel=False, lod1={"drop": True}), "Tail")
    for nm, s in SIDES:
        x = s * g["hip"][0]
        bp(_stick("Leg_" + nm, (x, g["hip"][1], P["leg"] + 0.04 * L), (x, g["hip"][1] - 0.01 * L, 0.012 * L), 0.012 * L, 0.009 * L, 1, 4, lod1={"segments": 3}), "Leg_" + nm)
        if P.get("feet", "webbed") == "talons":   # 3 forward toes + 1 hind toe, each ending in a down-curved black claw (slot 3)
            fy = g["hip"][1] - 0.01 * L; tz = 0.012 * L
            for k, (dx, dy) in enumerate(((0.0, -1.0), (0.55, -0.85), (-0.55, -0.85), (0.0, 1.0))):
                ln = (0.05 if k < 3 else 0.035) * L; e = (x + dx * ln, fy + dy * ln, tz * 0.6)
                bp(_stick("Toe%d_%s" % (k, nm), (x, fy, tz), e, 0.007 * L, 0.006 * L, 1, 4, lod1={"segments": 3}), "Leg_" + nm)
                bp(_stick("Claw%d_%s" % (k, nm), e, (e[0] + dx * 0.012 * L, e[1] + dy * 0.012 * L, 0.0005 * L), 0.006 * L, 0.0008 * L, 3, 4, lod1={"drop": True}), "Leg_" + nm)
        else:
            bp(K.slab("Foot_" + nm, [(0.0, 0.01 * L), (0.035 * L, -0.07 * L), (0.0, -0.05 * L), (-0.035 * L, -0.07 * L)], 0.006 * L, (x, g["hip"][1], 0.003 * L), 1), "Leg_" + nm)
    return out


def _keys(n, fn, step=2):
    fs = list(range(0, n, step)) + [n]
    return [[f, [round(v, 5) + 0.0 for v in fn(2 * math.pi * f / n)]] for f in fs]


def _pulse(t):
    """0 -> 1 -> 0 over one loop, held open in the middle (a squawk)."""
    return max(0.0, min(1.0, 1.6 * math.sin(t / 2) ** 2 - 0.25)) / 1.35 if t else 0.0


def clips(P):
    d = math.radians; out = {}
    ht, tf = P["head_turn"], P["tail_flick"]
    out["Idle"] = {"frames": 120, "tracks": {
        "Body": {"rot": _keys(120, lambda t: (d(1.5) * math.sin(2 * t), 0, 0))},
        "Neck": {"rot": _keys(120, lambda t: (d(2) * math.sin(2 * t + 0.4), 0, 0))},
        "Head": {"rot": _keys(120, lambda t: (0, 0, d(ht) * math.sin(t)))},
        "Tail": {"rot": _keys(120, lambda t: (d(tf) * max(0.0, math.sin(3 * t)) ** 4, 0, 0))}}}
    n = P["squawk_frames"]; gape = P["squawk_deg"]; lift = P["wing_lift_deg"]
    tr = {"Neck": {"rot": _keys(n, lambda t: (d(-34) * _pulse(t), 0, 0), step=1)},
          "Head": {"rot": _keys(n, lambda t: (d(-22) * _pulse(t), 0, 0), step=1)},
          "Beak_Lower": {"rot": _keys(n, lambda t: (d(gape) * _pulse(t) * (1 + 0.15 * math.sin(6 * t)), 0, 0), step=1)},
          "Body": {"rot": _keys(n, lambda t: (d(-8) * _pulse(t), 0, 0), step=1)},
          "Tail": {"rot": _keys(n, lambda t: (d(14) * _pulse(t), 0, 0), step=1)}}
    for nm, s in SIDES:
        tr["Wing_" + nm] = {"rot": _keys(n, lambda t: (0, -s * d(lift) * _pulse(t), 0), step=1)}
    out["Squawk"] = {"frames": n, "tracks": tr}
    L = P["L"]; leg = P["leg"] + 0.04 * L
    # Walk: 40 frames; single-bone legs swing about the hip, the body drops by leg x (1 - cos swing) so the stance foot stays down.
    amp = d(22)
    out["Walk"] = {"frames": 40, "tracks": {
        "Leg_L": {"rot": _keys(40, lambda t: (amp * math.sin(t), 0, 0))},
        "Leg_R": {"rot": _keys(40, lambda t: (-amp * math.sin(t), 0, 0))},
        "Body": {"loc": _keys(40, lambda t: (0, 0, -leg * (1 - math.cos(amp * math.sin(t)))))},
        "Neck": {"rot": _keys(40, lambda t: (d(9) * math.sin(2 * t), 0, 0))},
        "Head": {"rot": _keys(40, lambda t: (-d(9) * math.sin(2 * t), 0, 0))},
        "Tail": {"rot": _keys(40, lambda t: (d(3) * math.sin(2 * t), 0, 0))}}}
    # Fly: 24-frame wingbeat, wings spread sideways (Z) and flapping (X), neck forward, head level, legs trailing back.
    tr = {"Neck": {"rot": _keys(24, lambda t: (d(40), 0, 0))}, "Head": {"rot": _keys(24, lambda t: (-d(40), 0, 0))},
          "Body": {"loc": _keys(24, lambda t: (0, 0, -0.03 * L * math.sin(t)))}, "Tail": {"rot": _keys(24, lambda t: (d(-6), 0, 0))}}
    for nm, s in SIDES:
        tr["Wing_" + nm] = {"rot": _keys(24, lambda t, s=s: (d(10) + d(50) * math.sin(t), 0, -s * d(85)))}
        tr["Leg_" + nm] = {"rot": _keys(24, lambda t: (d(75), 0, 0))}
    out["Fly"] = {"frames": 24, "tracks": tr}
    # Dance: 48 frames, two hops; wings half open and fluttering, legs tuck in the air, a bow on each landing.
    hop = 0.22 * L
    up = lambda t: max(0.0, math.sin(2 * t))
    tr = {"Body": {"loc": _keys(48, lambda t: (0, 0, hop * up(t)), step=1)},
          "Neck": {"rot": _keys(48, lambda t: (d(35) * max(0.0, -math.sin(2 * t)) - d(10) * up(t), 0, 0), step=1)},
          "Head": {"rot": _keys(48, lambda t: (-d(20) * max(0.0, -math.sin(2 * t)) + d(10) * up(t), 0, 0), step=1)},
          "Tail": {"rot": _keys(48, lambda t: (d(10) * up(t), 0, 0), step=1)}}
    for nm, s in SIDES:
        tr["Wing_" + nm] = {"rot": _keys(48, lambda t, s=s: (d(30) + d(18) * math.sin(4 * t), 0, -s * d(55)), step=1)}
        tr["Leg_" + nm] = {"rot": _keys(48, lambda t: (-d(25) * up(t), 0, 0), step=1)}
    out["Dance"] = {"frames": 48, "tracks": tr}
    for c in out.values():
        c["fps"] = FPS; c["loop"] = True; c["seconds"] = round(c["frames"] / FPS, 4)
    return out


def bone_sockets(B, sockets):
    """[(name, bone, location)] -> socket records: rest location (model space) and the offset from the bone head (model axes)."""
    bb = {b["name"]: b for b in B}; out = []
    for name, bone, loc in sockets:
        if bone not in bb:
            raise ValueError("socket %s on unknown bone %s" % (name, bone))
        h = bb[bone]["head"]
        out.append({"name": name if name.startswith("SOCKET_") else "SOCKET_" + name, "bone": bone, "location": [round(v, 6) + 0.0 for v in loc],
                    "offset_from_bone_head": [round(loc[i] - h[i], 6) + 0.0 for i in range(3)], "rotation": [0, 0, 0]})
    return out


def recipe(asset, seed, materials=None, spec=None, body=None, clip_names=None, sockets=None):
    P = params(seed, asset, body); B = skeleton(P); Q = parts(P)
    names = tuple(clip_names or ("Idle", "Squawk"))
    if set(names) - set(CLIPS):
        raise ValueError("unknown clips: %s" % sorted(set(names) - set(CLIPS)))
    C = {k: v for k, v in clips(P).items() if k in names}
    mats = materials or [K.material(asset, 0, "white plumage", "F2F2EE", 0.85), K.material(asset, 1, "beak / legs (yellow-orange)", "E8A93A", 0.6),
                         K.material(asset, 2, "grey mantle (wings)", "9AA3AD", 0.85), K.material(asset, 3, "black wingtips / eyes", "1E1E22", 0.7)]
    lo, hi = K.bounds(Q); lo1, hi1 = K.bounds(Q, 1)
    t0 = sum(K.part_tris(p) for p in Q if K.in_lod(p, 0)); t1 = sum(K.part_tris(p, 1) for p in Q if K.in_lod(p, 1))
    m = {"asset": asset, "kind": "Char", "schema": SCHEMA, "seed": seed, "params": P, "materials": mats, "bones": B, "parts": Q, "clips": C,
            "bind_mode": "rigid", "spec": spec or {}, "axes": K.AXES + "; L = Blender +X (the bird's own left)", "status": "STAGED NOT READY",
            "bind": "rigid per part (bind_mode rigid): every part 100% on its bone; beaks and wings never bend",
            "unreal": {"type": "skeletal mesh + anim sequences (%s), root bone 'Root' on the ground" % ", ".join(names), "nanite": "skeletal: Nanite off/not applicable",
                       "collision": "capsule in UE", "sockets": "none (bone attach in UE)"},
            "predicted": {"triangles": t0, "lod1_triangles": t1, "lod1_ratio": round(t1 / t0, 3), "bounds_min": lo, "bounds_max": hi,
                          "dimensions": [round(hi[i] - lo[i], 4) for i in range(3)], "bones": len(B)}}
    if sockets:
        m["sockets"] = bone_sockets(B, sockets)
        m["unreal"]["sockets"] = "skeleton sockets from <asset>.sockets.json: " + ", ".join("%s on %s" % (x["name"], x["bone"]) for x in m["sockets"])
    return m
