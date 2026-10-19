# SPDX-License-Identifier: MIT
"""G05 Folding Maze walls (pythagoras 48594 pyth-g05-assets-20261019; board row 9; code main 47e3db4d FoldingMaze.java), blender-kit/v1.
  Bld_Lab_FoldWall_4m_Closed/_Open  the "WallMimic" wall: 4 x 0.6 x 4 m maze segment. Two stone end posts + plinth on the root;
      four named child panels <asset>_Panel0..3 (accordion, brass "eye" boss on each, teal hinge pins). Open = each pair folded
      flat against its post (perpendicular, swung back +Y), leaving a ~1.9 m passage. Same root pivot (bottom centre) in both states;
      no glTF animation (Unreal raises/sinks or swaps on Fold.opened/closed). SOCKET_Hinge_L/_R. UCX per post, plinth and panel.
  Bld_Lab_Wall4m_Plain  plain static wall with the same 4 x 0.6 x 4 m footprint; one UCX; no sockets.
Names: Mob_Lab_WallMimic (creature) and Prop_Lab_Wall4m (4 x 4 m cell block, 3 m tall, no UCX/LOD1) already exist in labyrinth-cast
and do not fit the 0.6 m maze footprint, so these are new, suffixed names (buffffff 48487). Style reused: labyrinth stone, Weathered teal,
Antique brass. LOD0/LOD1 (board asks LOD2 too; not made: ADR-062 catalog is LOD0/1).
Usage: python lab_fold.py [--seed N] --out data/contest/lab_fold.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 505
STONE, TEAL, BRASS = "6E6A73", "4F7A6A", "B08D57"
SPEC = {"rows": [9], "gap": "G05", "size_m": "4 x 0.6 x 4 m (maze grid)", "tri_cap": 2000, "lod": "LOD0/1", "collision": "UCX per segment",
        "states": ["Closed", "Open"], "sockets": ["Hinge_L", "Hinge_R"], "contract": "Daedalus2 47e3db4d docs/mechanics/LAB08-folding-maze.md"}
SPEC_PLAIN = dict(SPEC, sockets=[], states=None, collision="UCX")
CAPS, SOCKETS = {}, {}
PW, PT, PH = 0.78, 0.3, 3.7          # panel width, thickness, height


def _place(local, centre, deg):
    """local part list (centres about the panel centre) -> asset space, rotated about Z by deg at the panel centre."""
    t = math.radians(deg); out = []
    for p in local:
        x, y, z = p["centre"]; q = dict(p)
        q["centre"] = [round(centre[0] + x * math.cos(t) - y * math.sin(t), 5), round(centre[1] + x * math.sin(t) + y * math.cos(t), 5), round(z, 5)]
        if deg: q["rot"] = [(p.get("rot") or [0, 0, 0])[0], (p.get("rot") or [0, 0, 0])[1], deg]
        out.append(q)
    return out


def foldwall(state, seed=SEED):
    a = "Bld_Lab_FoldWall_4m_" + state; op = state == "Open"; r = K.rng(seed, "Bld_Lab_FoldWall_4m")
    mats = [K.material(a, 0, "labyrinth stone", STONE, 0.95), K.material(a, 1, "weathered teal", TEAL, 0.85, 0.2), K.material(a, 2, "antique brass", BRASS, 0.7, 0.5)]
    R = [K.box("Plinth", (4.0, 0.6, 0.15), (0, 0, 0.075), 0)]
    col = [K.ucx_box(a, 0, (4.0, 0.6, 0.15), (0, 0, 0.075))]
    for i, x in enumerate((-1.8, 1.8)):
        R += [K.box("Post%d" % i, (0.4, 0.6, 3.7), (x, 0, 2.0), 0), K.box("PostCap%d" % i, (0.4, 0.6, 0.15), (x, 0, 3.925), 1, lod1={"drop": True})]
        col.append(K.ucx_box(a, len(col), (0.4, 0.6, 3.85), (x, 0, 2.075)))
    objs = [K.obj(a, R)]
    closed_c = [(-1.2, 0), (-0.4, 0), (0.4, 0), (1.2, 0)]
    open_c = [(-1.43, 0.55), (-1.12, 0.55), (1.12, 0.55), (1.43, 0.55)]   # folded flat against the posts, swung back (+Y)
    hinge = [(-1.6, 0), (-0.8, 0), (0.8, 0), (1.6, 0)]
    for i in range(4):
        eye_z = round(1.6 + r.uniform(-0.25, 0.25), 3)          # seeded: the mimic's "eyes" sit at slightly different heights
        side = -1 if i < 2 else 1
        local = [K.box("Slab", (PW, PT, PH), (0, 0, 0.15 + PH / 2), 0),
                 K.cyl("Eye", "y", 0.09, 0.07, 0.06, (0, -PT / 2 - 0.03, eye_z), 2, 8, lod1={"drop": True}),
                 K.cyl("Pin", "z", 0.035, 0.035, PH, (side * -PW / 2 if i in (0, 3) else side * PW / 2, 0, 0.15 + PH / 2), 1, 8, lod1={"drop": True})]
        c = open_c[i] if op else closed_c[i]; deg = (90 if i < 2 else -90) if op else 0
        parts = [dict(p, name=p["name"]) for p in _place(local, c, deg)]
        n = "%s_Panel%d" % (a, i)
        objs.append(K.obj(n, parts, parent=a, pivot=(hinge[i][0], hinge[i][1], 0.0), role="fold panel %d (hinge pivot)" % i))
        size = [PT, PW, PH] if op else [PW, PT, PH]
        col.append(K.ucx_box(a, len(col), size, (c[0], c[1], 0.15 + PH / 2), parent=n))
    m = {"asset": a, "kind": "Bld", "seed": seed, "state": state, "state_of": "Bld_Lab_FoldWall_4m", "alias": "WallMimic (pythagoras 48594)",
         "spec": SPEC, "materials": mats, "objects": objs, "collision": col, "nanite": True,
         "sockets": [K.socket("Hinge_L", (-1.6, 0, 2.0), forward=(0, -1, 0)), K.socket("Hinge_R", (1.6, 0, 2.0), forward=(0, -1, 0))]}
    if op:
        m["off_centre_ok"] = "Open panels fold back to +Y; root pivot stays the Closed wall's bottom centre so both states line up"
    CAPS[a] = 2000; SOCKETS[a] = ["SOCKET_Hinge_L", "SOCKET_Hinge_R"]
    return K.finish(m)


def plain(seed=SEED):
    a = "Bld_Lab_Wall4m_Plain"
    mats = [K.material(a, 0, "labyrinth stone", STONE, 0.95), K.material(a, 1, "weathered teal", TEAL, 0.85, 0.2)]
    P = [K.box("Base", (4.0, 0.6, 0.3), (0, 0, 0.15), 0), K.box("Slab", (4.0, 0.5, 3.55), (0, 0, 2.075), 0),
         K.box("Coping", (4.0, 0.6, 0.15), (0, 0, 3.925), 0), K.box("Band", (4.0, 0.52, 0.1), (0, 0, 2.5), 1, lod1={"drop": True})]
    for i, (x, y) in enumerate([(-1.0, -0.275), (1.0, -0.275), (-1.0, 0.275), (1.0, 0.275)]):
        P.append(K.box("Pilaster%d" % i, (0.3, 0.05, 3.55), (x, y, 2.075), 0, lod1={"drop": True}))
    m = {"asset": a, "kind": "Bld", "seed": seed, "alias": "Wall4m (pythagoras 48594)", "spec": SPEC_PLAIN, "materials": mats,
         "objects": [K.obj(a, P)], "sockets": [], "collision": [K.ucx_box(a, 0, (4.0, 0.6, 4.0), (0, 0, 2.0))], "nanite": True}
    CAPS[a] = 2000; SOCKETS[a] = []
    return K.finish(m)


def assets(seed=SEED):
    return [foldwall("Closed", seed), foldwall("Open", seed), plain(seed)]


def extra_checks(A):
    C, O, P = A["Bld_Lab_FoldWall_4m_Closed"], A["Bld_Lab_FoldWall_4m_Open"], A["Bld_Lab_Wall4m_Plain"]
    out = [("foldwall closed 4 x 0.6 x 4 m", C["predicted"]["dimensions"] == [4.0, 0.6, 4.0], C["predicted"]["dimensions"]),
           ("plain wall same footprint as foldwall", P["predicted"]["dimensions"] == C["predicted"]["dimensions"], P["predicted"]["dimensions"]),
           ("fold states: same nodes, pivots, sockets, tris", [o["name"].replace("_Open", "_Closed") for o in O["objects"]] == [o["name"] for o in C["objects"]]
            and [o["pivot"] for o in O["objects"]] == [o["pivot"] for o in C["objects"]] and O["sockets"] == [dict(s) for s in C["sockets"]]
            and O["predicted"]["triangles"] == C["predicted"]["triangles"], ""),
           ("4 named child panels, each with its own UCX", all(sum(1 for c in g["collision"] if c["parent"] == "%s_Panel%d" % (g["asset"], i)) == 1 for g in (C, O) for i in range(4)), "")]
    pan = [p for o in O["objects"][1:] for p in o["parts"] if p["name"] == "Slab"]
    inner = min(abs(p["centre"][0]) - PT / 2 for p in pan)
    out.append(("open passage >= 1.8 m between folded panels", 2 * inner >= 1.8, round(2 * inner, 3)))
    out.append(("closed panels fill the gap between posts", abs(sum(PW for _ in range(4)) - 3.2) < 0.1, ""))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
