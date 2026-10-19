# SPDX-License-Identifier: MIT
"""G01 Echo Bell gate art (contest rows 4, 5, 14; prometheus 48418 prom-g01-handoff-1, answers 48492), blender-kit/v1.
The EBG 1 contract (Daedalus2 9fbeef02, docs/contracts/echo-bell-v1) wins over the board: one bell per EBG pitch.
  Prop_Lab_EchoBell_S00..S15  7 bells, semitones 0,3,5,7,10,12,15 (hz = 146.832 * 2^(s/12)), height 0.9 m (S00) -> 0.5 m (S15),
                              warm weathered dark bronze (rough, low metallic: no shiny highlights), iron clapper, verdigris crown.
                              SOCKET_Bell (hang point, crown top), SOCKET_Strike (front lip), SOCKET_Sound (inside). UCX prism.
  Prop_Lab_EchoBell_Frame     2.2 m dark-oak frame, SOCKET_Bell under the beam; UCX per post + beam.
  Bld_Lab_EchoGate_Closed/Open  3 m wide x 4 m tall stone arch; leaves are child nodes <asset>_LeafL/_LeafR pivoted at their hinges
                              (Open = swung 90 deg back, away from the front). SOCKET_Bell_L/_R; UCX per pillar, lintel and leaf.
  Prop_Lab_EchoCorridor_Straight/_Corner/_DeadEnd/_CricketNook  4 m cell, 4 m tall stone; SOCKET_Bell (iron bracket) in each,
                              SOCKET_Cricket in the nook; UCX per wall + floor.
Rigid props: no clips in the glb; Unreal drives bell swing / gate open (unreal-epic-boss 48497). Front = Blender -Y = UE +X.
REUSE (labyrinth-cast, picks posted to prometheus): style only (antique brass / weathered teal, blocky stone); no glb fits as-is.
Usage: python lab_echo.py [--seed N] --out data/contest/lab_echo.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 101
SEMIS = (0, 3, 5, 7, 10, 12, 15)
BASE_HZ = 146.832
CONTRACT = "Daedalus2 9fbeef02 docs/contracts/echo-bell-v1 (EBG 1)"
BRONZE, VERDIGRIS, IRON, OAK, STONE, FLOOR = "5E4630", "4F7A6A", "3A3A3E", "4A3324", "6E6A73", "56535B"
SPEC_BELL = {"rows": [4, 14], "gap": "G01", "contract": CONTRACT, "size_m": "0.9 (S00) to 0.5 (S15) tall", "tri_cap": 2500, "lod": "LOD0/1",
             "collision": "UCX", "sockets": ["Bell", "Strike", "Sound"]}
SPEC_FRAME = {"rows": [4], "gap": "G01", "size_m": "2.2 m frame", "tri_cap": 4000, "lod": "LOD0/1", "collision": "UCX frame", "sockets": ["Bell"]}
SPEC_GATE = {"rows": [5], "gap": "G01", "size_m": "3 m wide x 4 m tall", "tri_cap": 6000, "lod": "LOD0/1", "collision": "UCX per leaf (+ pillars, lintel)",
             "sockets": ["Bell_L", "Bell_R"], "states": ["Closed", "Open"]}
SPEC_COR = {"rows": [14], "gap": "G01", "size_m": "4 m cell, 4 m tall", "tri_cap": 2500, "lod": "LOD0/1", "collision": "UCX per wall",
            "sockets": ["Bell", "Cricket (nook)"]}
CAPS = {}
SOCKETS = {}


def height(s):
    return round(0.9 - 0.4 * s / 15.0, 4)


def bell(s, seed=SEED):
    a = "Prop_Lab_EchoBell_S%02d" % s; Ht = height(s); H = Ht / 0.97; r = K.rng(seed, a)   # profile in units of H; crown top = 0.97 H = Ht
    mats = [K.material(a, 0, "dark bronze (weathered)", BRONZE, 0.85, 0.35), K.material(a, 1, "iron", IRON, 0.8, 0.3),
            K.material(a, 2, "verdigris", VERDIGRIS, 0.9, 0.1)]
    flare = 1.0 + r.uniform(-0.02, 0.02)              # seeded, tiny: bells read as a hand-cast set, not clones
    inner = [(0.05, 0.80), (0.24, 0.73), (0.27, 0.56), (0.30, 0.36), (0.35, 0.18), (0.42 * flare, 0.03)]
    outer = [(0.475 * flare, 0.0), (0.48 * flare, 0.05), (0.41, 0.18), (0.36, 0.38), (0.335, 0.58), (0.30, 0.74), (0.20, 0.84), (0.06, 0.87)]
    prof = [(rr * H, zz * H) for rr, zz in inner + outer]
    P = [K.lathe("Body", prof, (0, 0, 0), 0, 24, True, True, lod1={"segments": 12}),
         K.box("Crown", (0.12 * H, 0.05 * H, 0.1 * H), (0, 0, 0.92 * H), 2),
         K.cyl("Clapper", "z", 0.03 * H, 0.03 * H, 0.45 * H, (0, 0, 0.5 * H), 1, 12, lod1={"drop": True}),
         K.lathe("ClapperBall", [(0.02 * H, -0.05 * H), (0.07 * H, 0.0), (0.02 * H, 0.05 * H)], (0, 0, 0.24 * H), 1, 12, lod1={"drop": True})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": SPEC_BELL, "materials": mats, "objects": [K.obj(a, P)],
         "pitch": {"semis": s, "hz": round(BASE_HZ * 2 ** (s / 12.0), 3), "height_m": Ht},
         "sockets": [K.socket("Bell", (0, 0, 0.97 * H), forward=(0, 0, 1)), K.socket("Strike", (0, -0.475 * H, 0.1 * H), forward=(0, 1, 0)),
                     K.socket("Sound", (0, 0, 0.45 * H), forward=(0, -1, 0))],
         "collision": [K.ucx_prism(a, 0, "z", round(0.49 * H, 4), round(0.97 * H, 4), (0, 0, round(0.485 * H, 4)))],
         "nanite": True, "motion": "Unreal drives swing (pivot = SOCKET_Bell)"}
    CAPS[a] = 2500; SOCKETS[a] = ["SOCKET_Bell", "SOCKET_Sound", "SOCKET_Strike"]
    return K.finish(m)


def frame(seed=SEED):
    a = "Prop_Lab_EchoBell_Frame"
    mats = [K.material(a, 0, "dark oak", OAK, 0.9), K.material(a, 1, "iron", IRON, 0.8, 0.3)]
    P = []
    for i, x in enumerate((-0.7, 0.7)):
        P += [K.box("Post%d" % i, (0.16, 0.16, 2.02), (x, 0, 1.01), 0), K.box("Foot%d" % i, (0.24, 0.5, 0.1), (x, 0, 0.05), 0),
              K.box("Brace%d" % i, (0.08, 0.08, 0.5), (x * 0.82, 0, 1.86), 0, rot=(0, 45 if x < 0 else -45, 0), lod1={"drop": True})]
    P += [K.box("Beam", (1.6, 0.18, 0.18), (0, 0, 2.11), 0),
          K.box("Hanger", (0.1, 0.1, 0.1), (0, 0, 1.97), 1, lod1={"drop": True}),
          K.box("Strap0", (0.04, 0.2, 0.18), (-0.3, 0, 2.11), 1, lod1={"drop": True}), K.box("Strap1", (0.04, 0.2, 0.18), (0.3, 0, 2.11), 1, lod1={"drop": True})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": SPEC_FRAME, "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Bell", (0, 0, 1.92), forward=(0, 0, -1))],
         "collision": [K.ucx_box(a, 0, (0.24, 0.5, 2.02), (-0.7, 0, 1.01)), K.ucx_box(a, 1, (0.24, 0.5, 2.02), (0.7, 0, 1.01)),
                       K.ucx_box(a, 2, (1.6, 0.22, 0.22), (0, 0, 2.11))], "nanite": True}
    CAPS[a] = 4000; SOCKETS[a] = ["SOCKET_Bell"]
    return K.finish(m)


def _rotz(c, piv, deg):
    t = math.radians(deg); x, y = c[0] - piv[0], c[1] - piv[1]
    return [round(piv[0] + x * math.cos(t) - y * math.sin(t), 5), round(piv[1] + x * math.sin(t) + y * math.cos(t), 5), c[2]]


def gate(state, seed=SEED):
    base = "Bld_Lab_EchoGate"; a = "%s_%s" % (base, state); op = state == "Open"
    mats = [K.material(a, 0, "labyrinth stone", STONE, 0.95), K.material(a, 1, "iron", IRON, 0.8, 0.3), K.material(a, 2, "dark bronze", BRONZE, 0.85, 0.35)]
    S = []
    for i, x in enumerate((-1.25, 1.25)):
        S += [K.box("Pillar%d" % i, (0.5, 0.6, 3.25), (x, 0, 1.775), 0), K.box("Plinth%d" % i, (0.5, 0.7, 0.3), (x, 0, 0.15), 0),
              K.box("Capital%d" % i, (0.5, 0.7, 0.15), (x, 0, 3.325), 0, lod1={"drop": True}),
              K.box("BracketF%d" % i, (0.06, 0.2, 0.06), (x, -0.4, 2.9), 1, lod1={"drop": True}),
              K.box("BracketB%d" % i, (0.06, 0.2, 0.06), (x, 0.4, 2.9), 1, lod1={"drop": True})]
    S += [K.box("Lintel", (3.0, 0.6, 0.6), (0, 0, 3.7), 0), K.box("Keystone", (0.4, 0.7, 0.5), (0, 0, 3.7), 0)]
    objs = [K.obj(a, S)]; col = [K.ucx_box(a, 0, (0.5, 0.7, 3.4), (-1.25, 0, 1.7)), K.ucx_box(a, 1, (0.5, 0.7, 3.4), (1.25, 0, 1.7)),
                                 K.ucx_box(a, 2, (3.0, 0.6, 0.6), (0, 0, 3.7))]
    for side, hx, ang in (("L", -1.0, 90.0), ("R", 1.0, -90.0)):
        n = "%s_Leaf%s" % (a, side); piv = (hx, 0.0, 0.0); cx = hx / 2
        parts = [K.box("Slab", (0.98, 0.15, 3.35), (cx, 0, 1.7), 0)] + \
                [K.box("Band%d" % k, (0.98, 0.17, 0.08), (cx, 0, z), 1, lod1={"drop": True}) for k, z in enumerate((0.5, 1.7, 2.9))] + \
                [K.cyl("Boss", "y", 0.14, 0.14, 0.2, (cx * 0.55, 0, 1.7), 2, 12, lod1={"segments": 6})]
        csize, ccent = [0.98, 0.15, 3.35], [cx, 0, 1.7]
        if op:
            for p in parts:
                p["centre"] = _rotz(p["centre"], piv, ang); p["rot"] = [0, 0, ang]
            csize, ccent = [0.15, 0.98, 3.35], _rotz(ccent, piv, ang)
        objs.append(K.obj(n, parts, parent=a, pivot=piv, role="leaf %s (hinge pivot; Unreal may swing it)" % side))
        col.append(K.ucx_box(a, len(col), csize, ccent, parent=n))
    m = {"asset": a, "kind": "Bld", "seed": seed, "state": state, "state_of": base, "spec": SPEC_GATE, "materials": mats, "objects": objs,
         "sockets": [K.socket("Bell_L", (-1.25, -0.48, 2.84), forward=(0, 0, -1)), K.socket("Bell_R", (1.25, -0.48, 2.84), forward=(0, 0, -1))],
         "collision": col, "nanite": True}
    if op:
        m["off_centre_ok"] = "Open leaves swing 1 m back (+Y); pivot stays the Closed gate's bottom centre so both states line up"
    CAPS[a] = 6000; SOCKETS[a] = ["SOCKET_Bell_L", "SOCKET_Bell_R"]
    return K.finish(m)


def corridor(kind, seed=SEED):
    a = "Prop_Lab_EchoCorridor_" + kind
    mats = [K.material(a, 0, "labyrinth stone", STONE, 0.95), K.material(a, 1, "flagstone", FLOOR, 0.95), K.material(a, 2, "iron", IRON, 0.8, 0.3)]
    P = [K.box("Floor", (4.0, 4.0, 0.1), (0, 0, 0.05), 1)]; col = [K.ucx_box(a, 0, (4.0, 4.0, 0.1), (0, 0, 0.05))]

    def wall(name, size, centre, pil_axis, inward):
        P.append(K.box(name, size, centre, 0)); col.append(K.ucx_box(a, len(col), size, centre))
        P.append(K.box(name + "Coping", (size[0], size[1], 0.15), (centre[0], centre[1], 3.925), 0))
        L = size[1] if pil_axis == "y" else size[0]
        for k, t in enumerate((-0.4 * L, 0.4 * L)):
            if pil_axis == "y":
                P.append(K.box("%sPilaster%d" % (name, k), (0.2, 0.4, 3.8), (centre[0] + inward * (size[0] / 2 + 0.1), centre[1] + t, 2.0), 0, lod1={"drop": True}))
            else:
                P.append(K.box("%sPilaster%d" % (name, k), (0.4, 0.2, 3.8), (centre[0] + t, centre[1] + inward * (size[1] / 2 + 0.1), 2.0), 0, lod1={"drop": True}))

    wall("WallL", (0.4, 4.0, 3.75), (-1.8, 0, 1.975), "y", 1)
    if kind in ("Straight", "DeadEnd", "CricketNook"):
        wall("WallR", (0.4, 4.0, 3.75), (1.8, 0, 1.975), "y", -1)
    if kind == "Corner":
        wall("WallB", (3.6, 0.4, 3.75), (0.2, 1.8, 1.975), "x", -1)
        P.append(K.box("CornerPost", (0.4, 0.4, 3.9), (1.8, -1.8, 2.05), 0)); col.append(K.ucx_box(a, len(col), (0.4, 0.4, 3.9), (1.8, -1.8, 2.05)))
    if kind == "DeadEnd":
        wall("WallB", (3.2, 0.4, 3.75), (0, 1.8, 1.975), "x", -1)
    socks = [K.socket("Bell", (-1.38, 0, 3.3), forward=(0, 0, -1))]
    P.append(K.box("BellBracket", (0.4, 0.06, 0.06), (-1.4, 0, 3.4), 2, lod1={"drop": True}))
    if kind == "CricketNook":   # back wall with a 0.8 m niche, sill at 0.6 m: the cricket sits in it facing the corridor
        for k, x in enumerate((-1.0, 1.0)):
            P.append(K.box("Back%d" % k, (1.2, 0.4, 3.75), (x, 1.8, 1.975), 0, lod1={"drop": True})); col.append(K.ucx_box(a, len(col), (1.2, 0.4, 3.75), (x, 1.8, 1.975)))
        P += [K.box("NicheBack", (0.8, 0.15, 3.75), (0, 1.925, 1.975), 0, lod1={"drop": True}), K.box("NicheSill", (0.8, 0.25, 0.5), (0, 1.725, 0.35), 0, lod1={"drop": True}),
              K.box("NicheLintel", (0.8, 0.25, 2.65), (0, 1.725, 2.525), 0, lod1={"drop": True}),
              K.box("BackLOD1", (3.2, 0.4, 3.75), (0, 1.8, 1.975), 0, lod1={"only": True}), K.box("BackCoping", (3.2, 0.4, 0.15), (0, 1.8, 3.925), 0)]
        col += [K.ucx_box(a, len(col), (0.8, 0.4, 0.5), (0, 1.8, 0.35)), K.ucx_box(a, len(col) + 1, (0.8, 0.4, 2.65), (0, 1.8, 2.525))]
        socks.append(K.socket("Cricket", (0, 1.75, 0.6), forward=(0, -1, 0)))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": SPEC_COR, "materials": mats, "objects": [K.obj(a, P)], "sockets": socks,
         "collision": col, "nanite": True, "kit": {"cell_m": 4.0, "height_m": 4.0, "open_sides": {"Straight": "-Y,+Y", "Corner": "-Y,+X", "DeadEnd": "-Y", "CricketNook": "-Y"}[kind]}}
    CAPS[a] = 2500; SOCKETS[a] = [s["name"] for s in socks]
    return K.finish(m)


def assets(seed=SEED):
    return [bell(s, seed) for s in SEMIS] + [frame(seed)] + [gate(st, seed) for st in ("Closed", "Open")] + \
           [corridor(k, seed) for k in ("Straight", "Corner", "DeadEnd", "CricketNook")]


def extra_checks(A):
    out = []; bells = [A["Prop_Lab_EchoBell_S%02d" % s] for s in SEMIS]
    out.append(("7 bells, one per EBG pitch", [b["pitch"]["semis"] for b in bells] == list(SEMIS)))
    out.append(("bells 0.9 m (S00) -> 0.5 m (S15), shrinking with pitch", abs(bells[0]["predicted"]["dimensions"][2] - 0.9) < 0.002 and abs(bells[-1]["predicted"]["dimensions"][2] - 0.5) < 0.002
                and all(bells[i]["predicted"]["dimensions"][2] > bells[i + 1]["predicted"]["dimensions"][2] for i in range(6))))
    out.append(("hz per contract (146.832 * 2^(s/12), max 360)", all(b["pitch"]["hz"] == round(146.832 * 2 ** (b["pitch"]["semis"] / 12.0), 3) and b["pitch"]["hz"] <= 360 for b in bells)))
    out.append(("bronze rough, low metallic (no shiny highlights)", all(b["materials"][0]["roughness"] >= 0.8 and b["materials"][0]["metallic"] <= 0.4 for b in bells)))
    out.append(("frame 2.2 m", abs(A["Prop_Lab_EchoBell_Frame"]["predicted"]["dimensions"][2] - 2.2) < 0.005, A["Prop_Lab_EchoBell_Frame"]["predicted"]["dimensions"]))
    out.append(("largest bell fits under the frame beam", height(0) * 0.97 < 1.92 and 0.475 * 0.9 * 1.02 < 0.62))
    C, O = A["Bld_Lab_EchoGate_Closed"], A["Bld_Lab_EchoGate_Open"]
    out.append(("gate 3 m x 4 m", C["predicted"]["dimensions"][0] == 3.0 and C["predicted"]["dimensions"][2] == 4.0, C["predicted"]["dimensions"]))
    out.append(("gate states: same nodes, sockets, pivots, tris", [o["name"].replace("_Open", "_Closed") for o in O["objects"]] == [o["name"] for o in C["objects"]]
                and [o["pivot"] for o in O["objects"]] == [o["pivot"] for o in C["objects"]] and [s["location"] for s in O["sockets"]] == [s["location"] for s in C["sockets"]]
                and O["predicted"]["triangles"] == C["predicted"]["triangles"]))
    out.append(("UCX per leaf, parented to the leaf", all(sum(1 for c in g["collision"] if c["parent"] == g["asset"] + "_Leaf" + s) == 1 for g in (C, O) for s in "LR")))
    out.append(("open leaves swing back (+Y), clear of the doorway", O["predicted"]["bounds_max"][1] > 0.9 and O["predicted"]["bounds_max"][1] > C["predicted"]["bounds_max"][1] + 0.4))
    for k in ("Straight", "Corner", "DeadEnd", "CricketNook"):
        m = A["Prop_Lab_EchoCorridor_" + k]; d = m["predicted"]["dimensions"]
        out.append(("corridor %s fills the 4 m cell, 4 m tall" % k, abs(d[0] - 4.0) < 0.11 and abs(d[1] - 4.0) < 0.11 and abs(d[2] - 4.0) < 0.001, d))
        out.append(("corridor %s has a UCX per wall + floor" % k, len(m["collision"]) >= 3, len(m["collision"])))
    out.append(("cricket socket only in the nook", ["SOCKET_Cricket" in [s["name"] for s in A["Prop_Lab_EchoCorridor_" + k]["sockets"]] for k in ("Straight", "Corner", "DeadEnd", "CricketNook")] == [False, False, False, True]))
    return [(n, ok, d[0] if d else "") for n, ok, *d in out]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
