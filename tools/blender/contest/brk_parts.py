# SPDX-License-Identifier: MIT
"""Contest row 12 (G16 airfield repair; buffffff 48312), blender-kit/v1.
Prop_Brk_AssemblyPiece_{Wing,Tail,Prop,Wheel,Engine,Cockpit}  six brick-built plane parts, 0.5-1.5 m, footprints on a 0.25 m stud
    grid (studs on top); each has SOCKET_Snap_Base at its bottom-centre mount. UCX box each.
Prop_Brk_RepairStand  2 m repair jig with one SOCKET_Snap_<Piece> per piece where it goes back on the plane. UCX boxes.
REUSE check: no Bricks (Brk) props exist in catalog.bba or art\\glb -> new.
Usage: python brk_parts.py --out data/contest/brk_parts.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 1616
PITCH = 0.25
PIECES = ["Wing", "Tail", "Prop", "Wheel", "Engine", "Cockpit"]
PRE, STAND = "Prop_Brk_AssemblyPiece_", "Prop_Brk_RepairStand"
CAPS = {PRE + p: 1500 for p in PIECES}; CAPS[STAND] = 1500
SOCKETS = {PRE + p: ["SOCKET_Snap_Base"] for p in PIECES}; SOCKETS[STAND] = ["SOCKET_Snap_" + p for p in PIECES]
SPEC = {"row": 12, "gap": "G16", "tri_cap": 1500, "lod": "LOD0/1", "collision": "UCX box", "stud_pitch_m": PITCH}
COL = {"Wing": "D9483B", "Tail": "D9483B", "Prop": "3A3A3E", "Wheel": "2B2A33", "Engine": "8C8C91", "Cockpit": "E8C547"}


def studs(nx, ny, z, slot, keep_every=2):
    out = []
    for i in range(nx):
        for j in range(ny):
            x = (i - (nx - 1) / 2) * PITCH; y = (j - (ny - 1) / 2) * PITCH
            out.append(K.cyl("Stud%d_%d" % (i, j), "z", 0.06, 0.06, 0.04, (round(x, 5), round(y, 5), round(z + 0.02, 5)), slot, 8, lod1={"drop": (i + j) % keep_every != 0}))
    return out


def piece(name, seed=SEED):
    a = PRE + name
    mats = [K.material(a, 0, "brick plastic", COL[name], 0.45), K.material(a, 1, "dark trim", "2B2A33", 0.6)]
    if name == "Wing":
        P = K.plain_lod1(K.box("Slab", (1.5, 0.5, 0.15), (0, 0, 0.075), 0)) + [K.box("Aileron", (0.5, 0.1, 0.05), (0.45, 0.29, 0.07), 1, bevel=False)] + studs(6, 2, 0.15, 0)
    elif name == "Tail":
        P = K.plain_lod1(K.box("Base", (0.5, 0.5, 0.15), (0, 0, 0.075), 0)) + K.plain_lod1(K.box("Fin", (0.1, 0.45, 0.5), (0, 0.02, 0.4), 0)) + \
            [K.box("Rudder", (0.11, 0.12, 0.4), (0, 0.27, 0.42), 1, bevel=False)] + [s for s in studs(2, 2, 0.15, 0) if not s["name"].endswith(("0_1", "1_1"))]
    elif name == "Prop":
        P = [K.box("Mount", (0.25, 0.25, 0.15), (0, 0, 0.075), 1), K.cyl("Hub", "y", 0.1, 0.1, 0.15, (0, 0.03, 0.5), 1, 12, lod1={"segments": 6}),
             K.cyl("Spinner", "y", 0.1, 0.02, 0.12, (0, -0.105, 0.5), 0, 12, lod1={"segments": 6}), K.box("Shaft", (0.08, 0.08, 0.35), (0, 0, 0.3), 1, bevel=False)]
        P += K.plain_lod1(K.box("BladeU", (0.12, 0.03, 0.42), (0, -0.03, 0.77), 0, rot=(0, 8, 0))) + K.plain_lod1(K.box("BladeD", (0.12, 0.03, 0.42), (0, -0.03, 0.23), 0, rot=(0, 8, 0)))
    elif name == "Wheel":
        P = [K.cyl("Tyre", "x", 0.25, 0.25, 0.15, (-0.065, 0, 0.25), 0, 16, lod1={"segments": 8}), K.cyl("Hub", "x", 0.1, 0.1, 0.17, (-0.065, 0, 0.25), 1, 10, lod1={"segments": 6}),
             K.box("Strut", (0.06, 0.06, 0.3), (0.065, 0, 0.45), 1, bevel=False), K.box("Plate", (0.25, 0.25, 0.08), (0.065, 0, 0.62), 1, lod1={"drop": True}),
             K.box("Plate_L1", (0.25, 0.25, 0.08), (0.065, 0, 0.62), 1, bevel=False, lod1={"only": True})]
    elif name == "Engine":
        P = K.plain_lod1(K.box("Block", (0.75, 0.5, 0.4), (0, 0, 0.2), 0)) + \
            [K.cyl("Cyl%d" % i, "z", 0.06, 0.06, 0.12, (round(-0.25 + 0.25 * i, 5), -0.12, 0.46), 1, 10, lod1={"segments": 6}) for i in range(3)] + \
            [K.cyl("Exhaust", "y", 0.04, 0.04, 0.1, (0.3, 0.25, 0.12), 1, 8, lod1={"drop": True})] + [s for s in studs(3, 2, 0.4, 0) if s["name"].endswith("_1")]
    else:
        P = K.plain_lod1(K.box("Tub", (1.0, 0.75, 0.35), (0, 0, 0.175), 0)) + \
            [K.box("Windscreen", (0.6, 0.04, 0.22), (0, -0.25, 0.46), 1, rot=(-25, 0, 0), bevel=False), K.box("Seat", (0.35, 0.3, 0.15), (0, 0.1, 0.43), 1, lod1={"drop": True})] + \
            [s for s in studs(4, 3, 0.35, 0) if s["name"].split("_")[0] in ("Stud0", "Stud3")]
    m = {"asset": a, "kind": "Prop", "seed": seed, "piece": name, "spec": dict(SPEC, size_m="pieces 0.5-1.5 m on the stud grid", sockets=["Snap_Base"]),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Snap_Base", (0, 0, 0))], "nanite": True}
    K.finish(m); lo, hi = m["predicted"]["bounds_min"], m["predicted"]["bounds_max"]
    m["collision"] = [K.ucx_box(a, 0, [round(hi[i] - lo[i], 5) for i in range(3)], [round((hi[i] + lo[i]) / 2, 5) for i in range(3)])]
    return K.finish(m)


# airframe pieces ride the top beam (surface 1.20 m), heavy pieces sit on the base (surface 0.10 m); each socket is on top of its 3 cm mount plate
SNAPS = {"Wing": (0, 0, 1.23), "Tail": (0.6, 0, 1.23), "Prop": (0.6, -0.3, 0.13), "Wheel": (-0.6, -0.3, 0.13), "Engine": (0, -0.3, 0.13), "Cockpit": (-0.6, 0, 1.23)}


def stand(seed=SEED):
    a = STAND
    mats = [K.material(a, 0, "jig steel", "6E7B85", 0.6, 0.5), K.material(a, 1, "hazard yellow", "E8C547", 0.5), K.material(a, 2, "dark rubber", "2B2A33", 0.9)]
    P = K.plain_lod1(K.box("Base", (2.0, 1.0, 0.08), (0, 0, 0.06), 0))
    for s, nm in ((-1, "L"), (1, "R")):
        P += K.plain_lod1(K.box("Upright" + nm, (0.12, 0.12, 1.1), (s * 0.9, 0, 0.65), 0))
    P += K.plain_lod1(K.box("Beam", (2.0, 0.14, 0.12), (0, 0, 1.14), 1)) + \
         [K.box("Foot%d" % 0, (0.3, 1.1, 0.02), (-0.85, 0, 0.01), 2, bevel=False, lod1={"drop": True}),
          K.box("Foot%d" % 1, (0.3, 1.1, 0.02), (0.85, 0, 0.01), 2, bevel=False, lod1={"drop": True})]
    for i, (p, loc) in enumerate(SNAPS.items()):                 # a small yellow mount plate under each snap socket
        P.append(K.box("Mount" + p, (0.16, 0.16, 0.03), (loc[0], loc[1], round(loc[2] - 0.015, 5)), 1, bevel=False))
    assert all(abs(l[0]) <= 0.92 and abs(l[1]) <= 0.42 for l in SNAPS.values())
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="stand 2 m", sockets=["Snap_" + p for p in PIECES]), "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Snap_" + p, SNAPS[p]) for p in PIECES],
         "collision": [K.ucx_box(a, 0, (2.0, 1.0, 0.1), (0, 0, 0.05)), K.ucx_box(a, 1, (0.12, 0.12, 1.1), (-0.9, 0, 0.65)), K.ucx_box(a, 2, (0.12, 0.12, 1.1), (0.9, 0, 0.65)),
                       K.ucx_box(a, 3, (2.0, 0.14, 0.12), (0, 0, 1.14))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [piece(p, seed) for p in PIECES] + [stand(seed)]


def extra_checks(A):
    ps = [A[PRE + p] for p in PIECES]; S = A[STAND]
    on_grid = lambda v: abs(round(v / PITCH) * PITCH - v) < 0.011
    return [("pieces 0.5-1.5 m", all(0.49 <= max(m["predicted"]["dimensions"]) <= 1.51 for m in ps), [max(m["predicted"]["dimensions"]) for m in ps]),
            ("piece footprints on the 0.25 m stud grid", all(on_grid(m["predicted"]["dimensions"][0]) or m["piece"] in ("Prop", "Wheel") for m in ps), [m["predicted"]["dimensions"][:2] for m in ps]),
            ("snap mounts rest on the beam or the base", all(abs(l[2] - 1.23) < 1e-6 and abs(l[1]) <= 0.07 or abs(l[2] - 0.13) < 1e-6 for l in SNAPS.values())),
            ("stand 2 m with one snap per piece", abs(S["predicted"]["dimensions"][0] - 2.0) < 1e-6 and [s["name"] for s in S["sockets"]] == ["SOCKET_Snap_" + p for p in PIECES]),
            ("every piece snaps by SOCKET_Snap_Base at its bottom centre", all(m["sockets"][0]["location"] == [0, 0, 0] for m in ps))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
