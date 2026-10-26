# SPDX-License-Identifier: MIT
"""G33 Seed-Song Spring (youtube-master 48984, ytm-g33-assets-20261019; code main 325f5655 com.daedalus.world.brew.story), blender-kit/v1.
Prop_YTM_RecordPlayer  small hand-crank gramophone for the brew bench: walnut cabinet, felt platter, brass tonearm and horn.
    Frame glb (UEB 48812 split): root hulls only. SOCKET_Hinge_Crank (crank axle, spins about X), SOCKET_Spin (spindle top on
    the platter; the record attaches here and spins about Z, 78 rpm), SOCKET_Needle (stylus tip, inner grooves where the
    cadence used to be), SOCKET_Sound (horn mouth).
Prop_YTM_RecordPlayer_Crank  mover glb, origin at the axle, own UCX. Turns about the axle (sidecar hinge.motion = spin).
Prop_YTM_Record_Whole / _Scratched  the record, two glbs, origin at bottom centre = SOCKET_Spin, own UCX prism. Scratched has
    a visible pale gouge across the INNER grooves (ScratchedRecord: the scratch eats the cadence, the end of the tune).
Prop_YTM_RecordPlayer_Whole / _Scratched  assembled static snapshots (crank + record as child nodes) for previews and set dressing.
REUSE check: catalog Prop_Jukebox_* are 0.40 m single meshes (176 tris) with no crank, record or sockets -> new.
Usage: python ytm_g33.py --out data/contest/ytm_g33.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 3333
BASE = "Prop_YTM_RecordPlayer"; CRANK = BASE + "_Crank"; REC = "Prop_YTM_Record"
CAPS = {}; SOCKETS = {}
SPEC = {"gap": "G33", "ask": "youtube-master 48984", "size_m": "cabinet 0.36 m, ~0.58 m to the horn top; record 10 in (0.254 m)",
        "tri_cap": 3000, "lod": "LOD0/1", "collision": "UCX cabinet + horn; crank and record own UCX"}
PIVOT = (0.182, 0.0, 0.09)                 # crank axle on the +X side of the cabinet
SPIN = (0.0, 0.0, 0.175)                   # platter top = record bottom centre
NEEDLE = (0.05, -0.06, 0.178)
H0 = (0.0, 0.155, 0.235); HDIR = (0.0, -0.6, 0.8); HLEN = 0.32; HR = 0.15     # horn neck, axis (front-up), length, mouth radius
MOUTH = tuple(round(H0[i] + HDIR[i] * HLEN, 5) for i in range(3))
REC_R, REC_T = 0.127, 0.003


def mats(a):
    return [K.material(a, 0, "walnut", "6B4226", 0.7), K.material(a, 1, "green felt", "2E4A3A", 0.95), K.material(a, 2, "brass", "B08D3C", 0.45, 0.8)]


def rec_mats(a):
    return [K.material(a, 0, "black shellac", "16161A", 0.35), K.material(a, 1, "cream label / bare gouge", "E8DCC0", 0.8),
            K.material(a, 2, "groove sheen", "3A3A40", 0.4)]


def frame_parts():
    P = K.plain_lod1(K.box("Plinth", (0.36, 0.36, 0.02), (0, 0, 0.01), 0)) + K.plain_lod1(K.box("Cabinet", (0.34, 0.34, 0.14), (0, 0, 0.09), 0)) + [
        K.cyl("Platter", "z", 0.14, 0.14, 0.015, (0, 0, 0.1675), 1, 24, lod1={"segments": 12}),
        K.cyl("Spindle", "z", 0.004, 0.004, 0.02, (0, 0, 0.185), 2, 8, lod1={"drop": True}),
        K.cyl("ArmBase", "z", 0.022, 0.022, 0.03, (0, 0.155, 0.175), 2, 12, lod1={"segments": 6}),
        K.cyl("Neck", "z", 0.013, 0.013, 0.045, (0, 0.155, 0.2125), 2, 8, lod1={"segments": 6}),
        K.cyl("AxleBoss", "x", 0.018, 0.018, 0.012, (0.176, 0, 0.09), 2, 10, lod1={"drop": True})]
    dx, dy = NEEDLE[0] - 0.0, NEEDLE[1] - 0.155; L = math.hypot(dx, dy); ang = round(math.degrees(math.atan2(dy, dx)), 4)
    P += [K.box("Tonearm", (round(L, 4), 0.012, 0.012), (round(dx / 2, 5), round(0.155 + dy / 2, 5), 0.196), 2, rot=(0, 0, ang), bevel=False),
          K.box("Head", (0.03, 0.02, 0.012), (NEEDLE[0], NEEDLE[1], 0.19), 2, rot=(0, 0, ang), bevel=False),
          K.cyl("Stylus", "z", 0.0015, 0.0015, 0.008, (NEEDLE[0], NEEDLE[1], 0.182), 2, 6, lod1={"drop": True})]
    th = math.degrees(math.atan2(-HDIR[1], HDIR[2]))      # Rx(th) takes local +Z to HDIR
    prof = [(0.013 + (HR - 0.013) * (t / 6.0) ** 2.2, HLEN * t / 6.0) for t in range(7)]
    P.append(K.lathe("Horn", prof, H0, 2, 20, cap_bottom=False, cap_top=False, rot=(round(th, 4), 0, 0), lod1={"segments": 10}))
    return P


def crank_parts():                                          # absolute coordinates; the mover shifts them by PIVOT
    x0 = PIVOT[0]
    return [K.cyl("Shaft", "x", 0.006, 0.006, 0.03, (x0 + 0.015, 0, 0.09), 2, 8, lod1={"segments": 4})] + \
        K.plain_lod1(K.box("Arm", (0.012, 0.014, 0.08), (x0 + 0.03, 0, 0.125), 2)) + [
            K.cyl("Knob", "x", 0.011, 0.011, 0.03, (x0 + 0.051, 0, 0.158), 0, 10, lod1={"segments": 6})]


def record_parts(scratched, seed=SEED):
    """Record at the origin (bottom centre). Grooves = 3 thin raised rings; the gouge crosses the inner grooves."""
    P = [K.cyl("Disc", "z", REC_R, REC_R, REC_T, (0, 0, REC_T / 2), 0, 32, lod1={"segments": 16}),
         K.cyl("Label", "z", 0.045, 0.045, 0.0006, (0, 0, REC_T + 0.0003), 1, 16, lod1={"segments": 8})]
    for i, r in enumerate((0.06, 0.085, 0.11)):
        P.append(K.lathe("Groove%d" % i, [(r - 0.0012, REC_T), (r, REC_T + 0.0004), (r + 0.0012, REC_T)], (0, 0, 0), 2, 24,
                         cap_bottom=False, cap_top=False, lod1={"segments": 12}))
    if scratched:                                           # jagged pale gouge from r 0.048 to 0.092, three seeded kinks
        rr = K.rng(seed, REC + "_Scratched"); a0 = 35.0; r0 = 0.048
        for i in range(3):
            r1 = r0 + 0.0147; a1 = a0 + rr.uniform(-9, 9)
            x0, y0 = r0 * math.cos(math.radians(a0)), r0 * math.sin(math.radians(a0)); x1, y1 = r1 * math.cos(math.radians(a1)), r1 * math.sin(math.radians(a1))
            P.append(K.box("Gouge%d" % i, (round(math.hypot(x1 - x0, y1 - y0) + 0.002, 5), 0.0035, 0.0008), (round((x0 + x1) / 2, 5), round((y0 + y1) / 2, 5), REC_T + 0.0005), 1,
                           rot=(0, 0, round(math.degrees(math.atan2(y1 - y0, x1 - x0)), 4)), bevel=False))
            r0, a0 = r1, a1
        P.append(K.box("Burr", (0.006, 0.006, 0.0012), (round(r0 * math.cos(math.radians(a0)), 5), round(r0 * math.sin(math.radians(a0)), 5), REC_T + 0.0006), 1,
                       rot=(0, 0, 20), bevel=False, lod1={"drop": True}))
    return P


def shift(parts, d):
    return [dict(q, centre=[round(q["centre"][i] - d[i], 5) + 0.0 for i in range(3)]) for q in parts]


SPIN_HINGE = {"socket": "SOCKET_Spin", "mover": REC + "_Whole", "alt_movers": [REC + "_Scratched"], "pivot_m": list(SPIN), "motion": "spin",
              "spin_axis_blender": [0, 0, 1], "spin_axis_ue": [0, 0, 1], "rpm": 78, "open_blender_euler_deg": None, "open_ue_rotator": None}
CRANK_HINGE = {"socket": "SOCKET_Hinge_Crank", "mover": CRANK, "pivot_m": list(PIVOT), "motion": "spin", "spin_axis_blender": [1, 0, 0],
               "spin_axis_ue": [1, 0, 0], "open_blender_euler_deg": None, "open_ue_rotator": None}


def frame_sockets():
    return [K.socket("Hinge_Crank", PIVOT), K.socket("Spin", SPIN), K.socket("Needle", NEEDLE), K.socket("Sound", MOUTH, forward=list(HDIR))]


def frame_collision(a):
    return [K.ucx_box(a, 0, (0.36, 0.36, 0.175), (0, 0, 0.0875)), K.ucx_box(a, 1, (0.3, 0.32, 0.37), (0, -0.005, 0.39))]


def frame(seed=SEED):
    a = BASE
    m = {"asset": a, "kind": "Prop", "seed": seed, "frame_of": [CRANK, REC + "_Whole", REC + "_Scratched"], "hinges": [CRANK_HINGE, SPIN_HINGE],
         "spec": dict(SPEC, split="frame glb (UEB 48812): root hulls only; crank at SOCKET_Hinge_Crank, record at SOCKET_Spin"),
         "materials": mats(a), "objects": [K.obj(a, frame_parts())], "sockets": frame_sockets(), "collision": frame_collision(a), "nanite": True}
    CAPS[a] = 3000; SOCKETS[a] = [s["name"] for s in m["sockets"]]
    return K.finish(m)


def crank(seed=SEED):
    a = CRANK; ms = mats(a)
    m = {"asset": a, "kind": "Prop", "seed": seed, "mover_of": BASE, "hinge": CRANK_HINGE, "spec": dict(SPEC, split="mover glb (UEB 48812): origin = crank axle"),
         "materials": [ms[0], ms[2]], "objects": [K.obj(a, [dict(q, slot={0: 0, 2: 1}[q["slot"]]) for q in shift(crank_parts(), PIVOT)], role="mover; origin at the axle (frame SOCKET_Hinge_Crank)")],
         "sockets": [], "collision": [K.ucx_box(a, 0, (0.08, 0.026, 0.1), (0.04, 0, 0.042))],
         "off_centre_ok": "origin is the crank axle (attach at %s SOCKET_Hinge_Crank)" % BASE, "nanite": True}
    m["materials"] = [dict(x, slot=i, name="%s_M%d" % (a, i)) for i, x in enumerate(m["materials"])]
    CAPS[a] = 3000; SOCKETS[a] = []
    return K.finish(m)


def record(scratched, seed=SEED):
    a = REC + ("_Scratched" if scratched else "_Whole")
    m = {"asset": a, "kind": "Prop", "seed": seed, "mover_of": BASE, "hinge": SPIN_HINGE, "record_state": "Scratched" if scratched else "Whole",
         "spec": dict(SPEC, split="mover glb: origin = record bottom centre = frame SOCKET_Spin", note="scratch eats the cadence: gouge across the inner grooves"),
         "materials": rec_mats(a), "objects": [K.obj(a, record_parts(scratched, seed), role="record; spins about Z at SOCKET_Spin")],
         "sockets": [K.socket("Spin", (0, 0, 0))], "collision": [K.ucx_prism(a, 0, "z", REC_R, REC_T + 0.001, (0, 0, (REC_T + 0.001) / 2), 12)], "nanite": True}
    CAPS[a] = 1000; SOCKETS[a] = ["SOCKET_Spin"]
    return K.finish(m)


def snapshot(scratched, seed=SEED):
    a = BASE + ("_Scratched" if scratched else "_Whole"); ms = mats(a); rm = rec_mats(a)
    allm = ms + [dict(x, slot=3 + x["slot"], name="%s_M%d" % (a, 3 + x["slot"])) for x in rm]
    cn, rn = a + "_Crank", a + "_Record"
    m = {"asset": a, "kind": "Prop", "seed": seed, "state_of": BASE, "record_state": "Scratched" if scratched else "Whole",
         "spec": dict(SPEC, state="assembled snapshot; ship the frame + movers for gameplay"), "materials": allm,
         "objects": [K.obj(a, frame_parts()), K.obj(cn, crank_parts(), parent=a, pivot=PIVOT, role="crank (child; turns about X at the axle)"),
                     K.obj(rn, [dict(q, centre=[q["centre"][0], q["centre"][1], round(q["centre"][2] + SPIN[2], 5)], slot=q["slot"] + 3) for q in record_parts(scratched, seed)],
                           parent=a, pivot=SPIN, role="record (child; spins about Z at SOCKET_Spin)")],
         "sockets": frame_sockets(),
         "collision": frame_collision(a) + [K.ucx_box(a, 2, (0.08, 0.026, 0.1), (PIVOT[0] + 0.04, 0, PIVOT[2] + 0.042), parent=cn),
                                            K.ucx_prism(a, 3, "z", REC_R, REC_T + 0.001, (0, 0, SPIN[2] + (REC_T + 0.001) / 2), 12, parent=rn)], "nanite": True}
    CAPS[a] = 3500; SOCKETS[a] = [s["name"] for s in m["sockets"]]
    return K.finish(m)


def assets(seed=SEED):
    return [frame(seed), crank(seed), record(False, seed), record(True, seed), snapshot(False, seed), snapshot(True, seed)]


def extra_checks(A):
    F, C, W, S = A[BASE], A[CRANK], A[REC + "_Whole"], A[REC + "_Scratched"]
    sk = {s["name"]: s["location"] for s in F["sockets"]}
    return [("record player frame: crank hinge + spin + needle + sound sockets", set(sk) == {"SOCKET_Hinge_Crank", "SOCKET_Spin", "SOCKET_Needle", "SOCKET_Sound"}),
            ("record is 10 in and sits on the platter top", abs(W["predicted"]["dimensions"][0] - 0.254) < 0.002 and sk["SOCKET_Spin"] == [0.0, 0.0, 0.175]),
            ("needle rests on the record's inner grooves", 0.04 <= math.hypot(*sk["SOCKET_Needle"][:2]) <= 0.1 and abs(sk["SOCKET_Needle"][2] - (SPIN[2] + REC_T)) < 0.001),
            ("scratched record has a visible gouge across the inner grooves; whole has none",
             any(p["name"].startswith("Gouge") for p in S["objects"][0]["parts"]) and not any(p["name"].startswith("Gouge") for p in W["objects"][0]["parts"]) and
             all(0.045 <= math.hypot(*p["centre"][:2]) <= 0.1 for p in S["objects"][0]["parts"] if p["name"].startswith("Gouge"))),
            ("whole and scratched records share size, origin and socket", W["predicted"]["dimensions"][:2] == S["predicted"]["dimensions"][:2] and W["sockets"] == S["sockets"]),
            ("crank mover origin at the axle; spins about X", C["hinge"]["motion"] == "spin" and C["hinge"]["spin_axis_ue"] == [1, 0, 0] and C["predicted"]["bounds_min"][0] >= -0.001),
            ("player stays small for the brew bench (<= 0.6 m)", max(F["predicted"]["dimensions"]) <= 0.6, F["predicted"]["dimensions"])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
