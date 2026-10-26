# SPDX-License-Identifier: MIT
"""Contest row 6 (G04 riddle doors; BOARD\\BLENDER-ASKS-CONTEST-20261019.md, buffffff 48312), blender-kit/v1.
Bld_Lab_TwinDoors_Closed/_Open  5.6 m stone wall, two arched doorways (2 x 3.5 m each) with wooden leaves Door_A (left) and
    Door_B (right) as child nodes on outer-edge hinges; Open = swung 90 deg back (+Y). SOCKET_Door_A / SOCKET_Door_B at each
    doorway's front threshold (interaction point). Split per UEB 48812: Bld_Lab_TwinDoors (frame, wall hulls + SOCKET_Hinge_*)
    + Bld_Lab_TwinDoors_DoorA / _DoorB (origin at the hinge, own UCX). States stay as static snapshots.
Prop_Lab_GateRiddler  2 m robed riddle statue on a plinth, bronze mask, glowing eyes; SOCKET_Speak at the mouth. UCX plinth + body.
REUSE check: labyrinth-cast has door/gate *code* (Door.java, GateOps) but no door or statue art; catalog Prop_Door_Wood is
1.4 x 2 m (too small, square), Prop_BBIsle_Statue_* / Prop_Decor_Statue_* have no sockets -> new.
Front = Blender -Y (lands on UE +Y; yaw -90 at placement). Usage: python lab_g04.py --out data/contest/lab_g04.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 404
TD, RID = "Bld_Lab_TwinDoors", "Prop_Lab_GateRiddler"
STONE, IRON, WOOD, BRONZE, GLOW = "6E6A63", "3A3A3E", "6B4A2E", "5A4630", "9FE3FF"
CAPS = {RID: 6000}
SOCKETS = {RID: ["SOCKET_Speak"]}
XC = {"A": -1.3, "B": 1.3}                      # doorway centres
SPEC_TD = {"row": 6, "gap": "G04", "size_m": "doors 2 x 3.5 m each", "tri_cap": 6000, "lod": "LOD0/1", "collision": "UCX per door",
           "sockets": ["Door_A", "Door_B"], "states": ["Closed", "Open"]}


def _rotz(c, piv, deg):
    t = math.radians(deg); x, y = c[0] - piv[0], c[1] - piv[1]
    return [round(piv[0] + x * math.cos(t) - y * math.sin(t), 5), round(piv[1] + x * math.sin(t) + y * math.cos(t), 5), c[2]]


def twindoors(state, seed=SEED):
    a = "%s_%s" % (TD, state); op = state == "Open"
    mats = [K.material(a, 0, "labyrinth stone", STONE, 0.95), K.material(a, 1, "door wood", WOOD, 0.85), K.material(a, 2, "iron", IRON, 0.8, 0.3)]
    W = [K.box("PillarL", (0.5, 0.8, 4.2), (-2.55, 0, 2.1), 0), K.box("PillarM", (0.6, 0.8, 4.2), (0, 0, 2.1), 0),
         K.box("PillarR", (0.5, 0.8, 4.2), (2.55, 0, 2.1), 0), K.box("TopBand", (5.6, 0.8, 0.6), (0, 0, 3.9), 0),
         K.box("Cornice", (5.8, 0.9, 0.15), (0, 0, 4.275), 0, lod1={"drop": True})]
    for d, xc in XC.items():
        for i in range(7):                                    # arch ring of voussoirs, radius 1.06 about (xc, 2.5)
            t = math.pi * (i + 0.5) / 7
            W.append(K.box("Arch%s%d" % (d, i), (0.5, 0.82, 0.16), (round(xc - 1.06 * math.cos(t), 5), 0, round(2.5 + 1.06 * math.sin(t), 5)), 0,
                           rot=(0, round(90 - math.degrees(t), 4), 0), bevel=False, lod1={"drop": i not in (0, 3, 6)}))
        for s in (-1, 1):                                     # spandrels between the arch and the top band
            W.append(K.box("Spandrel%s%d" % (d, (s + 1) // 2), (0.36, 0.8, 0.62), (round(xc + s * 0.83, 5), 0, 3.29), 0, bevel=False, lod1={"drop": True}))
    objs = [K.obj(a, W)]
    col = [K.ucx_box(a, 0, (0.5, 0.8, 4.2), (-2.55, 0, 2.1)), K.ucx_box(a, 1, (0.6, 0.8, 4.2), (0, 0, 2.1)),
           K.ucx_box(a, 2, (0.5, 0.8, 4.2), (2.55, 0, 2.1)), K.ucx_box(a, 3, (5.6, 0.8, 0.85), (0, 0, 3.775))]
    for d, xc in XC.items():
        hx = xc - 1.0 if d == "A" else xc + 1.0; piv = (hx, 0.0, 0.0); ang = 90.0 if d == "A" else -90.0
        n = "%s_Door%s" % (a, d)
        parts = [K.box("Slab", (1.96, 0.12, 2.5), (xc, 0, 1.25), 1), K.cyl("Crown", "y", 0.98, 0.98, 0.12, (xc, 0, 2.5), 1, 16, lod1={"segments": 8})] + \
                [K.box("Band%d" % k, (1.96, 0.14, 0.08), (xc, 0, z), 2, bevel=False, lod1={"drop": True}) for k, z in enumerate((0.45, 1.6, 2.6))] + \
                [K.cyl("Ring", "y", 0.09, 0.09, 0.16, (round(xc - 0.55 if d == "B" else xc + 0.55, 5), 0, 1.25), 2, 8, lod1={"segments": 6})]
        csize, ccent = [1.96, 0.12, 3.48], [xc, 0, 1.74]
        if op:
            for p in parts:
                p["centre"] = _rotz(p["centre"], piv, ang); p["rot"] = [0, 0, ang] if p["shape"] == "box" else [p.get("rot", [0, 0, 0])[0], 0, ang]
            csize, ccent = [0.12, 1.96, 3.48], _rotz(ccent, piv, ang)
        objs.append(K.obj(n, parts, parent=a, pivot=piv, role="door %s (hinge pivot; Unreal may swing it)" % d))
        col.append(K.ucx_box(a, len(col), csize, ccent, parent=n))
    m = {"asset": a, "kind": "Bld", "seed": seed, "state": state, "state_of": TD, "spec": SPEC_TD, "materials": mats, "objects": objs,
         "sockets": [K.socket("Door_A", (XC["A"], -0.6, 0.0)), K.socket("Door_B", (XC["B"], -0.6, 0.0))], "collision": col, "nanite": True}
    if op:
        m["off_centre_ok"] = "Open doors swing 2 m back (+Y); pivot stays the Closed wall's bottom centre so both states line up"
    CAPS[a] = 6000; SOCKETS[a] = ["SOCKET_Door_A", "SOCKET_Door_B"]
    return K.finish(m)


def riddler(seed=SEED):
    a = RID; r = K.rng(seed, a)
    mats = [K.material(a, 0, "weathered stone", "8A857C", 0.95), K.material(a, 1, "dark bronze mask", BRONZE, 0.85, 0.35),
            K.material(a, 2, "riddle glow", GLOW, 0.4, 0.0, glow=True)]
    P = [K.box("Plinth", (0.8, 0.8, 0.4), (0, 0, 0.2), 0), K.box("PlinthCap", (0.9, 0.9, 0.08), (0, 0, 0.44), 0, lod1={"drop": True}),
         K.lathe("Robe", [(0.34, 0.48), (0.3, 0.8), (0.24, 1.2), (0.2, 1.45), (0.16, 1.55), (0.05, 1.58)], (0, 0, 0), 0, 16, True, True, lod1={"segments": 8}),
         K.lathe("Hood", [(0.05, 1.56), (0.19, 1.6), (0.21, 1.78), (0.16, 1.93), (0.04, 2.0)], (0, 0, 0), 0, 14, False, True, lod1={"segments": 7}),
         K.box("Mask", (0.22, 0.04, 0.26), (0, -0.19, 1.75), 1),
         K.box("EyeL", (0.04, 0.02, 0.025), (-0.05, -0.215, 1.8), 2, bevel=False), K.box("EyeR", (0.04, 0.02, 0.025), (0.05, -0.215, 1.8), 2, bevel=False),
         K.box("Mouth", (0.08, 0.02, 0.012), (0, -0.215, 1.69), 2, bevel=False, lod1={"drop": True})]
    for s, nm in ((-1, "L"), (1, "R")):                          # arms folded over a riddle tablet
        P.append(K.box("Arm" + nm, (0.12, 0.42, 0.12), (s * 0.17, -0.18, 1.25), 0, rot=(0, 0, s * 25)))
    P.append(K.box("Tablet", (0.36, 0.05, 0.26), (0, -0.33, 1.16), 1, rot=(-10, 0, 0)))
    for i in range(3):
        P.append(K.box("Rune%d" % i, (0.06, 0.012, 0.05), (round(-0.1 + 0.1 * i, 5), -0.36, round(1.16 + r.uniform(-0.05, 0.05), 5)), 2, rot=(-10, 0, 0), bevel=False, lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": {"row": 6, "gap": "G04", "size_m": "statue 2 m", "tri_cap": 6000, "lod": "LOD0/1",
         "collision": "UCX plinth + body", "sockets": ["Speak"]}, "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Speak", (0, -0.23, 1.69))],
         "collision": [K.ucx_box(a, 0, (0.9, 0.9, 0.48), (0, 0, 0.24)), K.ucx_prism(a, 1, "z", 0.36, 1.52, (0, 0, 1.24))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    c, o = twindoors("Closed", seed), twindoors("Open", seed)
    return [c, o] + K.split_into(CAPS, SOCKETS, 6000, c, o) + [riddler(seed)]


def extra_checks(A):
    C, O, F, R = A[TD + "_Closed"], A[TD + "_Open"], A[TD], A[RID]
    da, db = A[TD + "_DoorA"], A[TD + "_DoorB"]
    return [("twin doors: each leaf 2 x 3.5 m (1.96 + crown)", all(abs(d["predicted"]["dimensions"][0] - 1.96) < 0.01 and abs(d["predicted"]["dimensions"][2] - 3.48) < 0.01 for d in (da, db)), [da["predicted"]["dimensions"], db["predicted"]["dimensions"]]),
            ("twin doors frame keeps wall hulls only + SOCKET_Door_A/B + hinge sockets", {s["name"] for s in F["sockets"]} == {"SOCKET_Door_A", "SOCKET_Door_B", "SOCKET_Hinge_DoorA", "SOCKET_Hinge_DoorB"} and len(F["collision"]) == 4),
            ("twin doors open = A yaw -90, B yaw +90 in UE", [h["open_ue_rotator"] for h in F["hinges"]] == [[0.0, -90.0, 0.0], [0.0, 90.0, 0.0]], [h["open_ue_rotator"] for h in F["hinges"]]),
            ("twin doors states same tris", C["predicted"]["triangles"] == O["predicted"]["triangles"]),
            ("riddler 2 m tall", abs(R["predicted"]["dimensions"][2] - 2.0) < 1e-6, R["predicted"]["dimensions"]),
            ("riddler SOCKET_Speak in front of the mask", R["sockets"][0]["location"][1] < -0.2 and 1.6 < R["sockets"][0]["location"][2] < 1.8),
            ("riddler eyes glow slot", any(mt["glow"] for mt in R["materials"]))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
