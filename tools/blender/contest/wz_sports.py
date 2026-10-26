# SPDX-License-Identifier: MIT
"""Contest row 10 (G11 festival sports; buffffff 48312), blender-kit/v1.
Prop_WZ_SportsHoop  basketball hoop: base plate, pole, arm, backboard, rim at 3.05 m (8 tangent boxes) + open net cone;
    SOCKET_Rim at the rim centre; UCX base/pole/board + 8 rim boxes (board: 'rim torus as 8 boxes'). Origin = base plate centre.
Prop_WZ_Bat     0.85 m bat (lathe), held prop: SOCKET_Grip + SOCKET_Tip attach (+X up the bat). UCX prism.
Prop_WZ_Glove   0.3 m catcher's glove, fingers up, pocket facing front (-Y); SOCKET_Hand attach (+X along the fingers, +Z out of
    the pocket). UCX box.
Prop_WZ_GoalNet 3 x 2 m goal: posts, crossbar, back frame, rope-strand net (opaque thin strands, no masked material). UCX posts/bar/net.
REUSE check: Daedalus2 tools/blender/voxel_props.py defines voxel Basketball_Hoop / Baseball_Bat / Baseball_Glove / Soccer_Goal,
but they are voxel-style recipes with no exported glb in art\\glb, no sockets and no UCX -> new kit versions (names per the board).
Usage: python wz_sports.py --out data/contest/wz_sports.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 1111
HOOP, BAT, GLOVE, GOAL = "Prop_WZ_SportsHoop", "Prop_WZ_Bat", "Prop_WZ_Glove", "Prop_WZ_GoalNet"
CAPS = {HOOP: 2500, BAT: 2500, GLOVE: 2500, GOAL: 2500}
SOCKETS = {HOOP: ["SOCKET_Rim"], BAT: ["SOCKET_Grip", "SOCKET_Tip"], GLOVE: ["SOCKET_Hand"], GOAL: []}
SPEC = {"row": 10, "gap": "G11", "tri_cap": 2500, "lod": "LOD0/1"}
RIM_Z, RIM_R = 3.05, 0.23


plain_lod1 = K.plain_lod1


def hoop(seed=SEED):
    a = HOOP
    mats = [K.material(a, 0, "painted steel", "2F5D8C", 0.6, 0.5), K.material(a, 1, "backboard white", "EDEDE8", 0.5), K.material(a, 2, "rim orange", "E0662B", 0.5, 0.4)]
    by = -0.8; ry = by - 0.025 - 0.15 - RIM_R
    P = plain_lod1(K.box("Base", (0.8, 0.8, 0.1), (0, 0, 0.05), 0)) + [K.cyl("Pole", "z", 0.06, 0.06, 3.3, (0, 0, 1.75), 0, 12, lod1={"segments": 6})] + \
        plain_lod1(K.box("Arm", (0.08, 0.8, 0.08), (0, by / 2, 3.35), 0)) + plain_lod1(K.box("Board", (1.8, 0.05, 1.05), (0, by, 3.43), 1)) + [
         K.box("Square", (0.6, 0.06, 0.45), (0, by - 0.002, 3.2), 2, bevel=False, lod1={"drop": True}),
         K.box("RimBracket", (0.12, 0.17, 0.04), (0, by - 0.11, RIM_Z), 2, bevel=False)]
    col = [K.ucx_box(a, 0, (0.8, 0.8, 0.1), (0, 0, 0.05)), K.ucx_prism(a, 1, "z", 0.06, 3.3, (0, 0, 1.75)), K.ucx_box(a, 2, (1.8, 0.05, 1.05), (0, by, 3.43))]
    for i in range(8):
        t = 2 * math.pi * i / 8; x, y = RIM_R * math.cos(t), ry + RIM_R * math.sin(t)
        P.append(K.box("Rim%d" % i, (0.19, 0.02, 0.02), (round(x, 5), round(y, 5), RIM_Z), 2, rot=(0, 0, round(math.degrees(t) + 90, 4)), bevel=False))
        col.append(K.ucx_box(a, 3 + i, (0.07, 0.07, 0.03), (round(x, 5), round(y, 5), RIM_Z)))
    P.append(K.lathe("Net", [(RIM_R, RIM_Z), (0.17, RIM_Z - 0.22), (0.14, RIM_Z - 0.4)], (0, ry, 0), 1, 12, False, False, lod1={"segments": 6}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="hoop 3.05 m rim", collision="UCX; rim torus as 8 boxes", sockets=["Rim"]),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Rim", (0, round(ry, 5), RIM_Z))], "collision": col, "nanite": True,
         "off_centre_ok": "origin = base plate centre; the board and rim overhang the front (-Y)"}
    return K.finish(m)


def bat(seed=SEED):
    a = BAT
    mats = [K.material(a, 0, "ash wood", "C9A46E", 0.7), K.material(a, 1, "grip tape", "2B2A33", 0.9)]
    P = [K.lathe("Bat", [(0.005, 0.0), (0.03, 0.0), (0.03, 0.02), (0.014, 0.04), (0.014, 0.35), (0.024, 0.55), (0.033, 0.7), (0.033, 0.83), (0.02, 0.85), (0.005, 0.85)],
                 (0, 0, 0), 0, 12, True, True, lod1={"segments": 6}),
         K.cyl("Tape", "z", 0.0155, 0.0155, 0.22, (0, 0, 0.15), 1, 12, lod1={"segments": 6})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="bat 0.85 m", collision="UCX prism", sockets=["Grip", "Tip"], held="attach sockets +X up the bat"),
         "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Grip", (0, 0, 0.15), forward=(0, 0, 1), attach=((0, 0, 1), (0, 1, 0))), K.socket("Tip", (0, 0, 0.85), forward=(0, 0, 1), attach=((0, 0, 1), (0, 1, 0)))],
         "collision": [K.ucx_prism(a, 0, "z", 0.034, 0.85, (0, 0, 0.425))], "nanite": True}
    return K.finish(m)


def glove(seed=SEED):
    a = GLOVE
    mats = [K.material(a, 0, "tan leather", "A8692F", 0.8), K.material(a, 1, "dark lacing", "4A2E1A", 0.9)]
    P = [K.box("Palm", (0.18, 0.08, 0.16), (0, 0, 0.1), 0), K.cyl("Cuff", "z", 0.06, 0.065, 0.05, (0, 0.01, 0.025), 0, 12, lod1={"segments": 6})]
    for i, x in enumerate((-0.06, -0.02, 0.02, 0.06)):
        h = (0.11, 0.125, 0.12, 0.1)[i]
        P += plain_lod1(K.box("Finger%d" % i, (0.042, 0.06, h), (x, 0.005, 0.18 + h / 2), 0, rot=(-6, 0, 0)))
    P += [K.box("Thumb", (0.05, 0.06, 0.11), (-0.115, -0.01, 0.15), 0, rot=(0, 30, 0)), K.box("Web", (0.07, 0.015, 0.09), (-0.09, -0.04, 0.2), 1, rot=(0, 25, 0), bevel=False),
          K.box("Lace", (0.17, 0.012, 0.012), (0, -0.045, 0.18), 1, bevel=False, lod1={"drop": True})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="glove 0.3 m", collision="UCX box", sockets=["Hand"], held="attach socket +X along the fingers, +Z out of the pocket (-Y)"),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Hand", (0, 0.03, 0.06), forward=(0, 0, 1), attach=((0, 0, 1), (0, -1, 0)))],
         "collision": [K.ucx_box(a, 0, (0.26, 0.1, 0.31), (-0.01, 0, 0.155))], "nanite": True}
    return K.finish(m)


def goal(seed=SEED):
    a = GOAL
    mats = [K.material(a, 0, "white posts", "EDEDE8", 0.5, 0.2), K.material(a, 1, "net rope", "D9D2BF", 0.95)]
    P = [K.cyl("PostL", "z", 0.05, 0.05, 2.0, (-1.5, -0.45, 1.0), 0, 12, lod1={"segments": 6}), K.cyl("PostR", "z", 0.05, 0.05, 2.0, (1.5, -0.45, 1.0), 0, 12, lod1={"segments": 6}),
         K.cyl("Crossbar", "x", 0.05, 0.05, 3.1, (0, -0.45, 2.0), 0, 12, lod1={"segments": 6}),
         K.cyl("BackBar", "x", 0.03, 0.03, 3.0, (0, 0.45, 0.03), 0, 8, lod1={"segments": 4}),
         K.cyl("TopBack", "x", 0.03, 0.03, 3.0, (0, 0.2, 1.75), 0, 8, lod1={"segments": 4})]
    for s, nm in ((-1, "L"), (1, "R")):
        P += [K.cyl("Ground" + nm, "y", 0.03, 0.03, 0.9, (s * 1.5, 0, 0.03), 0, 8, lod1={"segments": 4}),
              K.cyl("Stay" + nm, "y", 0.025, 0.025, 0.72, (s * 1.5, -0.13, 1.88), 0, 8, rot=(-20, 0, 0), lod1={"drop": True})]
    for i in range(11):                                         # back net strands, sloped from the top-back bar to the ground bar
        x = -1.5 + 0.3 * i
        P.append(K.box("NetV%02d" % i, (0.012, 0.012, 1.8), (round(x, 5), 0.325, 0.8925), 1, rot=(-8, 0, 0), bevel=False, lod1={"drop": i % 2 == 1}))
    for j in range(7):
        z = 0.15 + 0.25 * j
        P.append(K.box("NetH%d" % j, (3.0, 0.012, 0.012), (0, round(0.45 - (z / 1.75) * 0.25, 5), round(z, 5)), 1, bevel=False, lod1={"drop": j % 2 == 1}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="goal 3 x 2 m", collision="UCX posts, crossbar, net"),
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [],
         "collision": [K.ucx_prism(a, 0, "z", 0.05, 2.0, (-1.5, -0.45, 1.0)), K.ucx_prism(a, 1, "z", 0.05, 2.0, (1.5, -0.45, 1.0)),
                       K.ucx_box(a, 2, (3.1, 0.1, 0.1), (0, -0.45, 2.0)), K.ucx_box(a, 3, (3.0, 0.3, 1.8), (0, 0.33, 0.9))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [hoop(seed), bat(seed), glove(seed), goal(seed)]


def extra_checks(A):
    H, B, G, N = A[HOOP], A[BAT], A[GLOVE], A[GOAL]
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import sockets_sidecar as SS
    rot = lambda m: {s["name"]: SS.matrix_to_rotator(SS.desired_frame(s)) for s in m["sockets"]}
    return [("hoop rim at 3.05 m", abs(H["sockets"][0]["location"][2] - 3.05) < 1e-9),
            ("hoop UCX: base, pole, board + rim as 8 boxes", len(H["collision"]) == 11),
            ("bat 0.85 m", abs(B["predicted"]["dimensions"][2] - 0.85) < 1e-6, B["predicted"]["dimensions"]),
            ("bat Grip + Tip attach [90, 0, -90] (held-prop rule)", rot(B) == {"SOCKET_Grip": [90.0, 0.0, -90.0], "SOCKET_Tip": [90.0, 0.0, -90.0]}, rot(B)),
            ("glove ~0.3 m", 0.28 <= G["predicted"]["dimensions"][2] <= 0.32, G["predicted"]["dimensions"]),
            ("glove Hand attach: +X up the fingers, +Z out of the pocket", rot(G) == {"SOCKET_Hand": [90.0, 0.0, 90.0]}, rot(G)),
            ("goal 3 x 2 m mouth", abs(N["predicted"]["dimensions"][0] - 3.1) < 1e-6 and 2.0 <= N["predicted"]["dimensions"][2] <= 2.1, N["predicted"]["dimensions"]),
            ("no masked/translucent materials (opaque net strands)", all(not mt.get("alpha") for m in (H, N) for mt in m["materials"]))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
