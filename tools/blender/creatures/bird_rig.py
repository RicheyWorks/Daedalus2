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
         "beak_style": "straight", "feet": "webbed", "wing_tips": "plain", "tail_bands": 0,
         # proportion pass (2026-10-29): neck_len = head rise above the neck root / length, head pulled back to 0.75 x that ahead of the root
         # (absent = head at height_frac, 0.3 L forward: the old rule);
         # proportions = preset that fills leg_frac / neck_len / head_scale unless given explicitly
         "neck_len": None, "proportions": None,
         # perch posture + owl face (2026-10-29): posture "perch" pitches everything above the legs nose-up by perch_deg about the hip
         # (legs and feet stay planted); beak_style "owl" = short, gently hooked beak; facial_disc = flat disc on the face, eyes forward
         "posture": "standing", "perch_deg": 35.0, "facial_disc": False,
         # ear_tufts (2026-10-29): two feather tufts on top of the head (owls), slot 0
         "ear_tufts": False}
PROPORTIONS = {"raptor": {"leg_frac": 0.1, "neck_len": 0.08, "head_scale": 1.05},      # hawk / kestrel: short tarsus, head sunk into the shoulders
               "owl": {"leg_frac": 0.08, "neck_len": 0.05, "head_scale": 1.35},         # owl: barely any visible neck, big round head
               "small": {"leg_frac": 0.09, "neck_len": 0.07, "head_scale": 1.15}}        # songbird-sized: stubby legs, short neck
CLIPS = ("Idle", "Squawk", "Walk", "Fly", "Dance")


def params(seed, asset, body=None):
    P = dict(BODY)
    if body:
        bad = set(body) - set(BODY) - set(EXTRA)
        if bad:
            raise ValueError("unknown bird body params: %s" % sorted(bad))
        P.update(body)
        pr = P.pop("proportions", None)
        if pr is not None:
            if pr not in PROPORTIONS:
                raise ValueError("unknown bird proportions: %s" % pr)
            for k, v in PROPORTIONS[pr].items():
                if k not in body:
                    P[k] = v
        if P.get("neck_len", 0) is None:
            P.pop("neck_len")
    r = K.rng(seed, asset + ":bird"); L = P["length"]
    P["L"] = L; P["leg"] = round(P.get("leg_frac", 0.2) * L, 6); P["bz"] = round(P["leg"] + 0.12 * L, 6)        # body centre height
    P["head_turn"] = round(r.uniform(18, 30), 3); P["tail_flick"] = round(r.uniform(6, 10), 3)
    return P


def _g(P):
    L, bz = P["L"], P["bz"]
    b0 = -0.355 * L if "head_scale" not in P else -0.3 * L - 0.055 * P["head_scale"] * L     # beak root at the face
    if "neck_len" in P:     # head (and the face) pulled back with the shorter neck
        b0 = -0.2 * L - 0.75 * P["neck_len"] * L - 0.055 * P.get("head_scale", 1.0) * L
    if P.get("beak_style") == "owl":     # short owl beak: hinge sits on the face disc
        hy0 = -0.3 * L if "neck_len" not in P else -0.2 * L - 0.75 * P["neck_len"] * L
        return dict(_g_base(P, b0), beak0=hy0 - 0.05 * L * P.get("head_scale", 1.0), beak1=hy0 - 0.05 * L * P.get("head_scale", 1.0) - 0.018 * L)
    return _g_base(P, b0)


def _g_base(P, b0):
    L, bz = P["L"], P["bz"]
    return {"neck0": (-0.2 * L, bz + 0.06 * L), "head": ((-0.3 * L, P["height_frac"] * L - 0.06 * L) if "neck_len" not in P else (-0.2 * L - 0.75 * P["neck_len"] * L, bz + 0.06 * L + P["neck_len"] * L)), "beak0": b0, "beak1": b0 - 0.145 * L,
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
    if P.get("ear_tufts"):     # owl ear tufts: thin tilted wedges rising from the crown, mirrored
        for nm, s in SIDES:
            bp(K.slab("EarTuft_" + nm, [(-0.012 * L * hs, 0.0), (0.012 * L * hs, 0.0), (0.004 * L * hs, 0.05 * L * hs)], 0.008 * L, (s * 0.03 * L * hs, hy - 0.005 * L * hs, hz + 0.05 * L * hs), 0,
                      rot=(0, s * -20, 0), lod1={"drop": True}), "Head")
    if P.get("facial_disc"):     # owl: a flat buff disc (slot 2) on the face, both eyes on it looking forward
        for nm, s in SIDES:
            bp(K.cyl("FaceDisc_" + nm, "y", 0.036 * L * hs, 0.036 * L * hs, 0.008 * L, (s * 0.026 * L * hs, hy - 0.052 * L * hs, hz + 0.006 * L * hs), 2, 8, lod1={"segments": 5}), "Head")
            bp(K.cyl("Eye_" + nm, "y", 0.013 * L * hs, 0.013 * L * hs, 0.006 * L, (s * 0.026 * L * hs, hy - 0.058 * L * hs, hz + 0.01 * L * hs), 3, 6, lod1={"drop": True}), "Head")
    else:
        for nm, s in SIDES:
            bp(K.cyl("Eye_" + nm, "x", 0.012 * L, 0.012 * L, 0.006 * L, (s * 0.05 * L * hs, hy - 0.015 * L * hs, hz + 0.012 * L * hs), 3, 6, lod1={"drop": True}), "Head")
    if P.get("beak_style", "straight") == "owl":     # owl: short, mostly hidden in the disc, a small down-curved tip
        b0 = hy - 0.05 * L * hs; bl = 0.045 * L
        bp(_stick("Beak_Upper", (0, b0, hz - 0.004 * L), (0, b0 - 0.6 * bl, hz - 0.012 * L), 0.013 * L * hs, 0.009 * L * hs, 1, 5, lod1={"segments": 3}), "Head")
        bp(_stick("Beak_Hook", (0, b0 - 0.6 * bl, hz - 0.012 * L), (0, b0 - 0.75 * bl, hz - 0.03 * L), 0.009 * L * hs, 0.002 * L, 1, 4, lod1={"segments": 3}), "Head")
        bp(_stick("Beak_Lower", (0, b0, hz - 0.018 * L), (0, b0 - 0.4 * bl, hz - 0.024 * L), 0.008 * L * hs, 0.003 * L, 1, 4, lod1={"segments": 3}), "Beak_Lower")
    elif P.get("beak_style", "straight") == "hook":     # raptor: deep base, curved culmen, tip hooks down past the lower mandible
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
                bp(_stick("Claw%d_%s" % (k, nm), e, (e[0] + dx * 0.012 * L, e[1] + dy * 0.012 * L, 0.001 * L), 0.006 * L, 0.0008 * L, 3, 4, lod1={"drop": True}), "Leg_" + nm)
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


def _m3(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _euler_of(M):
    """3x3 -> Blender XYZ euler degrees (R = Rz Ry Rx), the inverse of kitlib.rot_matrix."""
    ry = math.asin(max(-1.0, min(1.0, -M[2][0]))); rx = math.atan2(M[2][1], M[2][2]); rz = math.atan2(M[1][0], M[0][0])
    return [round(math.degrees(v), 4) + 0.0 for v in (rx, ry, rz)]


def perch(P, B, Q, sockets):
    """Upright perch: pitch every non-leg bone, part and socket nose-up by perch_deg about the hip (rest pose; clips stay local)."""
    L = P["L"]; g = _g(P); piv = (0.0, g["hip"][1], P["leg"] + 0.04 * L); a = -float(P.get("perch_deg", 35.0))
    R = K.rot_matrix((a, 0, 0))
    up = lambda b: not b.startswith("Leg_") and b != "Root"

    def tp(v):
        d = [v[i] - piv[i] for i in range(3)]
        return [round(piv[i] + sum(R[i][k] * d[k] for k in range(3)), 6) + 0.0 for i in range(3)]
    B2 = []
    for b in B:
        b = dict(b)
        if up(b["name"]):
            b["head"], b["tail"] = tp(b["head"]), tp(b["tail"])
        B2.append(b)
    Q2 = []
    for p in Q:
        p = dict(p)
        if up(p["bone"]):
            p["centre"] = [round(v, 6) + 0.0 for v in tp(p["centre"])]
            p["rot"] = _euler_of(_m3(R, K.rot_matrix(p.get("rot", (0, 0, 0)))))
        Q2.append(p)
    # level the face again: Head (+ beak) swing back by the same angle about the head joint, so the bird looks forward, not skyward
    hb = [b for b in B2 if b["name"] == "Head"][0]; hr = hb["head"]; H = K.rot_matrix((-a, 0, 0))

    def th(v):
        d = [v[i] - hr[i] for i in range(3)]
        return [round(hr[i] + sum(H[i][j] * d[j] for j in range(3)), 6) + 0.0 for i in range(3)]
    for b in B2:
        if b["name"] in ("Head", "Beak_Lower"):
            b["head"], b["tail"] = th(b["head"]), th(b["tail"])
    for p in Q2:
        if p["bone"] in ("Head", "Beak_Lower"):
            p["centre"] = th(p["centre"]); p["rot"] = _euler_of(_m3(H, K.rot_matrix(p["rot"])))
    _tp = tp
    tp = lambda v, b=None: th(_tp(v)) if b in ("Head", "Beak_Lower") else _tp(v)
    # the tail and folded wing tips hang below the perch line on an upright bird: swing each back up about its root until it clears the ground
    for bn in ("Tail", "Wing_L", "Wing_R"):
        tb = [b for b in B2 if b["name"] == bn][0]; tr = tb["head"]; T = K.rot_matrix((5.0, 0, 0))

        def tt(v, tr=tr, T=T):
            d = [v[i] - tr[i] for i in range(3)]
            return [round(tr[i] + sum(T[i][j] * d[j] for j in range(3)), 6) + 0.0 for i in range(3)]
        for k in range(12):
            if min(q[2] for p in Q2 if p["bone"] == bn for q in K.part_points(p)) >= 0.01 * L:
                break
            tb["tail"] = tt(tb["tail"])
            for p in Q2:
                if p["bone"] == bn:
                    p["centre"] = tt(p["centre"]); p["rot"] = _euler_of(_m3(T, K.rot_matrix(p["rot"])))
    S2 = [(n, b, tuple(tp(loc, b)) if up(b) else loc) for n, b, loc in (sockets or [])] or sockets
    return B2, Q2, S2


def recipe(asset, seed, materials=None, spec=None, body=None, clip_names=None, sockets=None):
    P = params(seed, asset, body); B = skeleton(P); Q = parts(P)
    if P.get("posture", "standing") == "perch":
        B, Q, sockets = perch(P, B, Q, sockets)
    elif P.get("posture", "standing") != "standing":
        raise ValueError("unknown bird posture: %s" % P["posture"])
    names = tuple(clip_names or ("Idle", "Squawk"))
    if set(names) - set(CLIPS):
        raise ValueError("unknown clips: %s" % sorted(set(names) - set(CLIPS)))
    C = {k: v for k, v in clips(P).items() if k in names}
    if P.get("posture", "standing") == "perch" and "Fly" in C:     # level out in flight: pitch the body back to horizontal
        fr = sorted({k[0] for tr in C["Fly"]["tracks"].values() for ch in tr.values() for k in ch})
        C["Fly"]["tracks"].setdefault("Body", {})["rot"] = [[f, [round(math.radians(float(P.get("perch_deg", 35.0))), 5), 0.0, 0.0]] for f in fr]
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
