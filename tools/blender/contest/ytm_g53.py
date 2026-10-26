# SPDX-License-Identifier: MIT
"""G53 Choir Stones (youtube-master 49161, ytm-g53-assets-20261019; code main 77814390 brew.stones.ChoirStones / BridgeLedger), blender-kit/v1.
Prop_YTM_ChoirStone            waist-high carved standing stone (~1.0 m) on a plinth. The serpentine song groove is its own slot
                               (M1) so the hum is an MI swap: variants/choir_groove.py writes Humming / Quiet params. SOCKET_Hum (top,
                               VFX/audio), SOCKET_Carve (front, carve interaction). UCX.
Prop_YTM_RopeBridge_Seg_S3/S2/S1  modular 2 m rope-bridge segment = BridgeLedger strength 3/2/1: planks + under-ropes + hangers +
                               handrails; worse fray per step (thinner, saggier handrails, missing/tilted/split planks, fibre tufts).
Prop_YTM_RopeBridge_Seg_Snapped strength 0: the span broke in the middle, both halves hang from their anchor ends. No collision
                               (BridgeLedger refuses crossing at 0).
Prop_YTM_RopeBridge_Anchor     end post pair with rope wraps and guy ropes; SOCKET_Segment takes a segment's SOCKET_Anchor_A.
Chaining: every segment has SOCKET_Anchor_A (-X end) and SOCKET_Anchor_B (+X end) at deck height; seg n's B = seg n+1's A.
Origins are bottom centre (Snapped: bottom of the hanging halves), so always place by socket, not by origin.
REUSE check: Bld_Orr_Bridge_Rope is a 10 m Orr building; Prop_YTM_Rock_*/Boulder_* are 0.1 m flat placeholder tiles;
Prop_BUF_Landmark_DeedStone is a 0.45 m slab (buffffff); Prop_Dress_PYT_ColonistCairn_* are cairn piles (pythagoras) -> all new.
Usage: python ytm_g53.py --out data/contest/ytm_g53.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 5353
STONE, SEG, ANCHOR = "Prop_YTM_ChoirStone", "Prop_YTM_RopeBridge_Seg_", "Prop_YTM_RopeBridge_Anchor"
STATES = {3: "S3", 2: "S2", 1: "S1", 0: "Snapped"}             # BridgeLedger.MAX_STRENGTH = 3, snaps at 0
CAPS = {STONE: 1500, ANCHOR: 1500}; CAPS.update({SEG + s: 2500 for s in STATES.values()})
SOCKETS = {STONE: ["SOCKET_Hum", "SOCKET_Carve"], ANCHOR: ["SOCKET_Segment"]}; SOCKETS.update({SEG + s: ["SOCKET_Anchor_A", "SOCKET_Anchor_B"] for s in STATES.values()})
SPEC = {"gap": "G53", "ask": "youtube-master 49161", "lod": "LOD0/1"}
HALF, R_UNDER, Y_UNDER, Y_RAIL, RAIL_Z = 1.0, 0.018, 0.42, 0.5, 0.95
PLANK_T = 0.035; PLANK_Z = 2 * R_UNDER + PLANK_T / 2; DECK = round(2 * R_UNDER + PLANK_T, 4)
FRAY = {3: {"r": 0.016, "sag": 0.05, "missing": 0, "tilt": 0, "tilt_deg": 0, "split": 0, "tufts": 0, "hangers_lost": 0},
        2: {"r": 0.013, "sag": 0.09, "missing": 1, "tilt": 2, "tilt_deg": 6, "split": 0, "tufts": 4, "hangers_lost": 0},
        1: {"r": 0.010, "sag": 0.15, "missing": 3, "tilt": 3, "tilt_deg": 12, "split": 1, "tufts": 10, "hangers_lost": 1},
        0: {"r": 0.010, "sag": 0.0, "missing": 3, "tilt": 3, "tilt_deg": 12, "split": 1, "tufts": 6, "hangers_lost": 1}}
SNAP_DEG = 72


def rope(name, p0, p1, r, slot, seg=6, lod1=None):
    dx, dy, dz = (p1[i] - p0[i] for i in range(3)); L = math.sqrt(dx * dx + dy * dy + dz * dz)
    yaw = math.degrees(math.atan2(dy, dx)); pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    c = tuple(round((p0[i] + p1[i]) / 2, 5) for i in range(3))
    return K.cyl(name, "x", r, r, round(L, 5), c, slot, seg, rot=(0, round(-pitch, 3), round(yaw, 3)), lod1=lod1 if lod1 is not None else {"segments": 4})


def seat_dz():
    """Cyl facets leave the under-ropes a hair above z=0; intact segments drop by this, so their deck sits at DECK - seat_dz()."""
    return K.bounds([rope("probe", (-HALF, -Y_UNDER, R_UNDER), (HALF, -Y_UNDER, R_UNDER), R_UNDER, 1)])[0][2]


def tuft(name, at, rr, slot=2):
    out = []
    for k in range(3):
        a = rr.uniform(0, 360); e = rr.uniform(-40, 40)
        out.append(K.box("%s_%d" % (name, k), (0.035, 0.005, 0.005), tuple(round(at[i] + (0.012 * math.cos(math.radians(a)) if i == 0 else 0.012 * math.sin(math.radians(a)) if i == 1 else 0), 5) for i in range(3)),
                         slot, rot=(0, round(e, 2), round(a, 2)), bevel=False, lod1=None if k == 0 else {"drop": True}))
    return out


def stone(seed=SEED):
    a = STONE
    mats = [K.material(a, 0, "choir stone (YTM_Stone)", "8C8C94", 0.85), K.material(a, 1, "song groove (MI: Humming / Quiet)", "2A2A30", 0.6, glow=True),
            K.material(a, 2, "plinth", "6E6E76", 0.9)]
    P = K.plain_lod1(K.box("Plinth", (0.78, 0.52, 0.07), (0, 0, 0.035), 2))
    P += K.plain_lod1(K.box("Body", (0.56, 0.34, 0.5), (0, 0, 0.32), 0))
    P += K.plain_lod1(K.box("Upper", (0.5, 0.3, 0.3), (0, 0, 0.72), 0))
    P += K.plain_lod1(K.box("Cap", (0.4, 0.25, 0.12), (0, 0, 0.93), 0))
    pts = []
    for i in range(17):                                         # serpentine seed-song line down the front face
        z = 0.15 + 0.69 * i / 16; pts.append((0.16 * math.sin(2 * math.pi * (z - 0.15) / 0.35), z))
    for i, ((x0, z0), (x1, z1)) in enumerate(zip(pts, pts[1:])):
        zm = (z0 + z1) / 2; yf = -(0.17 if zm < 0.57 else 0.15) - 0.003
        P.append(K.box("Groove%02d" % i, (round(math.hypot(x1 - x0, z1 - z0) + 0.012, 4), 0.008, 0.022), (round((x0 + x1) / 2, 5), yf, round(zm, 5)), 1,
                       rot=(0, round(-math.degrees(math.atan2(z1 - z0, x1 - x0)), 3), 0), bevel=False))
    for i, (x, z) in enumerate(((-0.17, 0.3), (0.17, 0.48), (-0.15, 0.68), (0.14, 0.8))):   # four "notes" beside the line
        P.append(K.box("Note%d" % i, (0.03, 0.008, 0.03), (x, -(0.17 if z < 0.57 else 0.15) - 0.003, z), 1, bevel=False, lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="waist-high ~1.0 m", tri_cap=1500, collision="UCX plinth + stone", sockets=["Hum", "Carve"],
         groove_slot="M1 Prop_YTM_ChoirStone_M1 (MI Humming / Quiet)"),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Hum", (0, 0, 0.99)), K.socket("Carve", (0, -0.2, 0.5))],
         "collision": [K.ucx_box(a, 0, (0.78, 0.52, 0.07), (0, 0, 0.035)), K.ucx_box(a, 1, (0.56, 0.34, 0.92), (0, 0, 0.53))], "nanite": True}
    return K.finish(m)


def _seg_parts(st, rr):
    F = FRAY[st]; P = []
    xs = [round(-0.9 + 0.2 * i, 4) for i in range(10)]
    missing = set(rr.sample(range(1, 9), F["missing"])); left = [i for i in range(10) if i not in missing]
    tilted = set(rr.sample(left, F["tilt"])); split = set(rr.sample(sorted(tilted), F["split"])) if F["split"] else set()
    for i, x in enumerate(xs):
        if i in missing:
            continue
        rx = rr.uniform(-F["tilt_deg"], F["tilt_deg"]) / 4 if i in tilted else 0; rz = rr.uniform(-F["tilt_deg"], F["tilt_deg"]) if i in tilted else 0
        if i in split:                                          # cracked plank: two halves, one dropped a little
            for k, (yc, dz) in enumerate(((-0.24, 0.0), (0.24, -0.01))):
                P += [(dict(q), "plank") for q in K.plain_lod1(K.box("Plank%02d_%d" % (i, k), (0.17, 0.42, PLANK_T), (x, yc, PLANK_Z + dz), 0, rot=(round(rx, 2), 0, round(rz, 2))))]
        else:
            P += [(dict(q), "plank") for q in K.plain_lod1(K.box("Plank%02d" % i, (0.17, 0.9, PLANK_T), (x, 0, PLANK_Z), 0, rot=(round(rx, 2), 0, round(rz, 2))))]
    for s, nm in ((-1, "L"), (1, "R")):
        P.append(((-HALF, s * Y_UNDER, R_UNDER), (HALF, s * Y_UNDER, R_UNDER), R_UNDER, "Under" + nm))
        rail = [(-HALF + 2 * HALF * k / 4, s * Y_RAIL, RAIL_Z - F["sag"] * math.sin(math.pi * k / 4)) for k in range(5)]
        for k in range(4):
            P.append((rail[k], rail[k + 1], F["r"], "Rail%s%d" % (nm, k)))
        lost = set(rr.sample(range(4), F["hangers_lost"]))
        for k, x in enumerate((-0.75, -0.25, 0.25, 0.75)):
            if k in lost:
                continue
            zr = RAIL_Z - F["sag"] * math.sin(math.pi * (x + HALF) / (2 * HALF))
            P.append(((x, s * Y_UNDER, R_UNDER), (x, s * Y_RAIL, zr), 0.007, "Hanger%s%d" % (nm, k)))
    tufts = []
    for t in range(F["tufts"]):
        s = rr.choice((-1, 1)); x = rr.uniform(-0.9, 0.9); zr = RAIL_Z - F["sag"] * math.sin(math.pi * (x + HALF) / (2 * HALF))
        tufts.append((round(x, 4), s * Y_RAIL, round(zr, 4)))
    return P, tufts


def _xf_snap(p):
    """Snapped: the span broke at x=0; every rope/plank hangs from its own anchor end at its own height, SNAP_DEG down."""
    x, y, z = p; a = math.radians(SNAP_DEG); h = 1 if x > 0 else -1; u = HALF - abs(x)
    return (h * HALF - h * u * math.cos(a), y, z - u * math.sin(a))


def _snap_rope(p0, p1, gap=0.04):
    """Split a rope at the break: returns [(q0, q1, broken_end or None)] in unsnapped coordinates."""
    if p0[0] > p1[0]:
        p0, p1 = p1, p0
    def at(x):
        t = (x - p0[0]) / (p1[0] - p0[0]); return (x, p0[1] + t * (p1[1] - p0[1]), p0[2] + t * (p1[2] - p0[2]))
    if p0[0] < 0 < p1[0]:
        return [(p0, at(-gap), at(-gap)), (at(gap), p1, at(gap))]
    if p1[0] <= 0:
        return [(p0, at(-gap), at(-gap))] if p1[0] > -gap else [(p0, p1, None)]
    return [(at(gap), p1, at(gap))] if p0[0] < gap else [(p0, p1, None)]


def segment(st, seed=SEED):
    a = SEG + STATES[st]; rr = K.rng(seed, a)
    mats = [K.material(a, 0, "bridge planks", "7A5A3A", 0.85), K.material(a, 1, "rope", "9C7A4A", 0.9), K.material(a, 2, "frayed fibre", "C9B48A", 0.95)]
    raw, tufts = _seg_parts(st, rr); P = []; snap = st == 0
    for e in raw:
        if isinstance(e[0], dict):
            q = e[0]
            if snap:
                c = q["centre"]; h = 1 if c[0] > 0 else -1
                q = dict(q, centre=[round(v, 5) for v in _xf_snap(c)], rot=[q["rot"][0], round(-h * SNAP_DEG, 3), q["rot"][2]] if q.get("rot") else [0, round(-h * SNAP_DEG, 3), 0])
            P.append(q)
        else:
            p0, p1, r, nm = e
            if not snap:
                P.append(rope(nm, p0, p1, r, 1)); continue
            if abs(p1[0] - p0[0]) < 1e-9:                       # hangers: vertical, no break
                P.append(rope(nm, _xf_snap(p0), _xf_snap(p1), r, 1)); continue
            for k, (q0, q1, end) in enumerate(_snap_rope(p0, p1)):
                P.append(rope("%s_%s" % (nm, "ab"[k]), _xf_snap(q0), _xf_snap(q1), r, 1))
                if end and nm.startswith(("Under", "Rail")):
                    tufts.append(end)
    for i, t in enumerate(tufts):
        P += tuft("Fray%02d" % i, _xf_snap(t) if snap else t, rr)
    socks = [K.socket("Anchor_A", (-HALF, 0, DECK), forward=(-1, 0, 0)), K.socket("Anchor_B", (HALF, 0, DECK), forward=(1, 0, 0))]
    col = [] if snap else [K.ucx_box(a, 0, (2 * HALF, 0.9, DECK), (0, 0, DECK / 2)), K.ucx_box(a, 1, (2 * HALF, 0.04, RAIL_Z - DECK), (0, -Y_RAIL, (RAIL_Z + DECK) / 2)),
                           K.ucx_box(a, 2, (2 * HALF, 0.04, RAIL_Z - DECK), (0, Y_RAIL, (RAIL_Z + DECK) / 2))]
    if not snap:                                                # cyl facets leave the under-ropes a hair above z=0: same offset for S3/S2/S1
        dz = seat_dz()
        P = [dict(q, centre=[q["centre"][0], q["centre"][1], q["centre"][2] - dz]) for q in P]
        socks = [K.socket("Anchor_A", (-HALF, 0, round(DECK - dz, 5)), forward=(-1, 0, 0)), K.socket("Anchor_B", (HALF, 0, round(DECK - dz, 5)), forward=(1, 0, 0))]
    if snap:                                                    # seat on z=0 (the hanging halves), keep sockets at deck height relative to the mesh
        lo, hi = K.bounds(P); dz = lo[2]
        P = [dict(q, centre=[q["centre"][0], q["centre"][1], q["centre"][2] - dz]) for q in P]
        socks = [K.socket("Anchor_A", (-HALF, 0, round(DECK - dz, 5)), forward=(-1, 0, 0)), K.socket("Anchor_B", (HALF, 0, round(DECK - dz, 5)), forward=(1, 0, 0))]
    m = {"asset": a, "kind": "Prop", "seed": seed, "strength": st, "spec": dict(SPEC, size_m="2 m segment, 1 m wide, handrail 0.95 m", tri_cap=2500,
         collision="none (strength 0: impassable)" if snap else "UCX deck + 2 handrail walls", sockets=["Anchor_A", "Anchor_B"],
         chain="seg n SOCKET_Anchor_B = seg n+1 SOCKET_Anchor_A; ends on Prop_YTM_RopeBridge_Anchor SOCKET_Segment", state="BridgeLedger strength %d" % st),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": socks, "collision": col, "nanite": True}
    if snap:
        m["off_centre_ok"] = "halves hang from their own anchor ends; place by SOCKET_Anchor_A/B (deck height %.3f m above the origin)" % (DECK - dz)
    return K.finish(m)


def anchor(seed=SEED):
    a = ANCHOR
    mats = [K.material(a, 0, "anchor posts", "6B4A2E", 0.85), K.material(a, 1, "rope", "9C7A4A", 0.9), K.material(a, 2, "footing stone (YTM_Stone)", "8C8C94", 0.9)]
    P = K.plain_lod1(K.box("Footing", (0.5, 1.4, 0.1), (-0.12, 0, 0.05), 2))
    for s, nm in ((-1, "L"), (1, "R")):
        P += K.plain_lod1(K.box("Post" + nm, (0.14, 0.14, 1.25), (0, s * 0.56, 0.725), 0))
        for k, z in enumerate((RAIL_Z, DECK + 0.03)):
            P.append(K.cyl("Wrap%s%d" % (nm, k), "z", 0.085, 0.085, 0.06, (0, s * 0.56, z), 1, 8, lod1={"segments": 5}))
        P.append(rope("Guy" + nm, (-0.02, s * 0.56, 1.25), (-0.7, s * 0.7, 0.02), 0.012, 1))
        P.append(K.box("Stake" + nm, (0.05, 0.05, 0.12), (-0.7, s * 0.7, 0.06), 0, bevel=False))
        P.append(rope("Tie%s" % nm, (0, s * 0.56, RAIL_Z), (0.12, s * Y_RAIL, RAIL_Z), 0.014, 1, lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="post pair 1.25 m", tri_cap=1500, collision="UCX posts + footing", sockets=["Segment"]),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Segment", (0.12, 0, round(DECK - seat_dz(), 5)), forward=(1, 0, 0))],
         "collision": [K.ucx_box(a, 0, (0.5, 1.4, 0.1), (-0.12, 0, 0.05)), K.ucx_box(a, 1, (0.14, 0.14, 1.25), (0, -0.56, 0.725)), K.ucx_box(a, 2, (0.14, 0.14, 1.25), (0, 0.56, 0.725))],
         "off_centre_ok": "footing and guy ropes run back (-X) from the posts; origin = post line so SOCKET_Segment sits at the bridge end", "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [stone(seed)] + [segment(s, seed) for s in (3, 2, 1, 0)] + [anchor(seed)]


def extra_checks(A):
    S = A[STONE]; segs = [A[SEG + STATES[s]] for s in (3, 2, 1, 0)]
    def sk(m, n):
        return next(s["location"] for s in m["sockets"] if s["name"] == n)
    out = [("choir stone waist-high (0.9-1.1 m)", 0.9 <= S["predicted"]["dimensions"][2] <= 1.1, S["predicted"]["dimensions"]),
           ("groove is its own slot (M1) and only groove parts use it", all((q["name"].startswith(("Groove", "Note"))) == (q["slot"] == 1) for q in S["objects"][0]["parts"])),
           ("intact segments chain: A=(-1,0,deck), B=(+1,0,deck), same deck", all(sk(m, "SOCKET_Anchor_A") == sk(segs[0], "SOCKET_Anchor_A") and sk(m, "SOCKET_Anchor_B") == sk(segs[0], "SOCKET_Anchor_B") and sk(m, "SOCKET_Anchor_A")[0] == -HALF and sk(m, "SOCKET_Anchor_B")[0] == HALF and abs(sk(m, "SOCKET_Anchor_A")[2] - DECK) < 0.005 for m in segs[:3])),
           ("snapped keeps A/B 2 m apart at one height", abs(sk(segs[3], "SOCKET_Anchor_B")[0] - sk(segs[3], "SOCKET_Anchor_A")[0] - 2 * HALF) < 1e-9 and sk(segs[3], "SOCKET_Anchor_A")[2] == sk(segs[3], "SOCKET_Anchor_B")[2]),
           ("snapped halves hang (> 0.6 m drop below the deck)", sk(segs[3], "SOCKET_Anchor_A")[2] > 0.6, sk(segs[3], "SOCKET_Anchor_A")),
           ("snapped has no collision", segs[3]["collision"] == []),
           ("fray worsens 3 -> 1 (fibre tufts up, planks down)", [sum(1 for q in m["objects"][0]["parts"] if q["slot"] == 2) for m in segs[:3]] == sorted([sum(1 for q in m["objects"][0]["parts"] if q["slot"] == 2) for m in segs[:3]]) and
            [sum(1 for q in m["objects"][0]["parts"] if q["name"].startswith("Plank") and not q["name"].endswith("_L1")) for m in segs[:3]][0] >
            [sum(1 for q in m["objects"][0]["parts"] if q["name"].startswith("Plank") and not q["name"].endswith("_L1")) for m in segs[:3]][2]),
           ("anchor SOCKET_Segment at the segments' deck height", sk(A[ANCHOR], "SOCKET_Segment")[2] == sk(segs[0], "SOCKET_Anchor_A")[2])]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
