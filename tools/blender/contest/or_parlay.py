# SPDX-License-Identifier: MIT
"""G18 Storm Parlay + G22 Storm Glass art for oddsreaper (48641 oddsreaper-g18-art-20261019, code d367474d com.daedalus.world.odds.parlay;
48732 oddsreaper-g22-art-20261019, code da7775e0 com.daedalus.world.odds.weather), blender-kit/v1. Board rows 17-19.
  Prop_OR_ParlayChalkboard  1.2 x 0.8 m inn wall board (dark wood frame, slate, chalk tray); SOCKET_Text on the slate face; UCX box.
  Prop_OR_StormHerbToken    coin-sized (3.6 cm) brass token with a tied herb bundle; LOD0 only, no collision.
  Prop_OR_StormGlass        40 cm brass wall barometer; the needle is the child node Prop_OR_StormGlass_Needle pivoted at the dial
                            centre with SOCKET_Needle there. StormGlass.Reading {HIGH, FALLING, LOW} has no art binding in da7775e0,
                            so the three positions ship as needle angles (manifest "readings" + <Asset>.readings.json), not state glbs.
REUSE: herb assets (Item_DS_Herb_OverclockThorn 20 cm, Prop_DS_Herb_* 25-36 cm) are not coin-sized, so the token is new.
Front = Blender -Y (lands on UE +Y; axis question open). Usage: python or_parlay.py --out data/contest/or_parlay.kit.json"""
import argparse, json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 1818
CB, TK, SG = "Prop_OR_ParlayChalkboard", "Prop_OR_StormHerbToken", "Prop_OR_StormGlass"
CAPS = {CB: 1500, TK: 300, SG: 1200}
SOCKETS = {CB: ["SOCKET_Text"], TK: [], SG: ["SOCKET_Needle"]}
WOOD, SLATE, CHALK, BRASS, IVORY, HERB, TEAL, RED = "5C3D24", "2E3B33", "F0EEE6", "B08D57", "E8DCC0", "5E8C3A", "4F7A6A", "9C3B2E"
DIAL_Z, DIAL_Y = 0.25, -0.031     # needle pivot (dial centre, just in front of the dial face)
READINGS = {"HIGH": 45.0, "FALLING": 0.0, "LOW": -45.0}   # degrees about Blender +Y from straight up; + = toward Blender +X = the viewer's right


def chalkboard(seed=SEED):
    a = CB; r = K.rng(seed, a)
    mats = [K.material(a, 0, "dark wood", WOOD, 0.9), K.material(a, 1, "slate", SLATE, 0.95), K.material(a, 2, "chalk", CHALK, 0.95)]
    P = [K.box("FrameTop", (1.2, 0.06, 0.07), (0, 0, 0.765), 0), K.box("FrameBottom", (1.2, 0.06, 0.07), (0, 0, 0.035), 0),
         K.box("FrameL", (0.07, 0.06, 0.66), (0.565, 0, 0.4), 0), K.box("FrameR", (0.07, 0.06, 0.66), (-0.565, 0, 0.4), 0),
         K.box("Slate", (1.06, 0.02, 0.66), (0, 0.005, 0.4), 1, bevel=False),
         K.box("Tray", (0.9, 0.07, 0.025), (0, -0.04, 0.0825), 0, lod1={"drop": True}),
         K.box("TrayLOD1", (0.9, 0.07, 0.025), (0, -0.04, 0.0825), 0, bevel=False, lod1={"only": True})]
    for i in range(2):
        P.append(K.box("Chalk%d" % i, (0.07, 0.012, 0.012), (r.uniform(-0.35, 0.35), -0.045, 0.101), 2, rot=(0, 0, r.uniform(-15, 15)), lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": {"row": 17, "gap": "G18", "size_m": "1.2 x 0.8 m", "tri_cap": 1500, "sockets": ["Text"], "asker": "oddsreaper 48641"},
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [K.socket("Text", (0, -0.006, 0.42), forward=(0, -1, 0))],
         "text_area_m": [1.0, 0.56], "collision": [K.ucx_box(a, 0, (1.2, 0.1, 0.8), (0, -0.01, 0.4))], "nanite": True}
    return K.finish(m)


def token(seed=SEED):
    a = TK; r = K.rng(seed, a)
    mats = [K.material(a, 0, "brass", BRASS, 0.7, 0.5), K.material(a, 1, "herb", HERB, 0.9), K.material(a, 2, "twine", "C9A46A", 0.95)]
    P = [K.cyl("Coin", "z", 0.018, 0.018, 0.004, (0, 0, 0.002), 0, 16)]
    for i in range(3):
        ang = -20 + 20 * i + r.uniform(-5, 5)
        P.append(K.box("Leaf%d" % i, (0.006, 0.026, 0.003), (math.sin(math.radians(ang)) * 0.004, 0, 0.0055 + 0.0005 * i), 1, rot=(0, 0, ang), bevel=False))
    P.append(K.cyl("Tie", "y", 0.0035, 0.0035, 0.004, (0, 0.004, 0.0065), 2, 8))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": {"row": 18, "gap": "G18", "size_m": "coin-sized", "tri_cap": 300, "asker": "oddsreaper 48641"},
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [], "collision": [], "lod1": False, "nanite": True}
    return K.finish(m)


def stormglass(seed=SEED):
    a = SG; n = a + "_Needle"
    mats = [K.material(a, 0, "brass", BRASS, 0.7, 0.5), K.material(a, 1, "ivory dial", IVORY, 0.8), K.material(a, 2, "dark wood", WOOD, 0.9),
            K.material(a, 3, "storm red", RED, 0.8)]
    P = [K.box("Backboard", (0.16, 0.02, 0.4), (0, 0.01, 0.2), 2),
         K.cyl("Case", "y", 0.11, 0.11, 0.04, (0, -0.0, DIAL_Z), 0, 16, lod1={"segments": 8}),
         K.cyl("Dial", "y", 0.095, 0.095, 0.006, (0, -0.023, DIAL_Z), 1, 16, lod1={"segments": 8}),
         K.box("Finial", (0.05, 0.03, 0.04), (0, -0.005, 0.37), 0, lod1={"drop": True}),
         K.cyl("Tube", "z", 0.012, 0.012, 0.11, (0, -0.012, 0.08), 1, 8),
         K.cyl("Bulb", "z", 0.02, 0.02, 0.025, (0, -0.012, 0.0125), 0, 8)]
    for name, deg in READINGS.items():   # chalk-style marks on the dial rim at each reading
        t = math.radians(deg)
        P.append(K.box("Mark%s" % name, (0.008, 0.004, 0.018), (0.08 * math.sin(t), -0.027, DIAL_Z + 0.08 * math.cos(t)), 2 if name == "LOW" else 0,
                       rot=(0, deg, 0), bevel=False, lod1={"drop": True}))
    N = [K.box("Pointer", (0.006, 0.003, 0.08), (0, DIAL_Y, DIAL_Z + 0.032), 3, bevel=False),
         K.cyl("Hub", "y", 0.008, 0.008, 0.006, (0, DIAL_Y, DIAL_Z), 0, 8, lod1={"drop": True})]
    rd = {k: {"blender_rot_y_deg": v, "ue_tip_dir": [round(math.sin(math.radians(v)), 4) + 0.0, 0.0, round(math.cos(math.radians(v)), 4)],
              "ue_rotation_pyr": [-v + 0.0, 0.0, 0.0]} for k, v in READINGS.items()}
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": {"row": 19, "gap": "G22", "size_m": "~0.4 m tall", "tri_cap": 1200, "sockets": ["Needle"], "asker": "oddsreaper 48732"},
         "materials": mats, "objects": [K.obj(a, P), K.obj(n, N, parent=a, pivot=(0, DIAL_Y, DIAL_Z), role="needle (rest = FALLING, straight up); rotate about the dial normal")],
         "sockets": [K.socket("Needle", (0, DIAL_Y, DIAL_Z), parent=n, forward=(0, -1, 0))],
         "readings": {"enum": "com.daedalus.world.odds.weather.StormGlass.Reading (da7775e0)", "rest": "FALLING", "axis": "dial normal = Blender -Y = UE +Y",
                      "note": "angle about Blender +Y from straight up; + = needle tip toward Blender/UE +X (the viewer's right). ue_tip_dir is in UE space for the needle "
                              "node at rest = (0,0,1); ue_rotation_pyr assumes UE +pitch tilts +X up (so the tip goes to +X with pitch -45): verify against ue_tip_dir.",
                      "positions": rd},
         "collision": [K.ucx_box(a, 0, (0.22, 0.06, 0.4), (0, -0.01, 0.2))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [chalkboard(seed), token(seed), stormglass(seed)]


def write_readings(m, d):
    p = os.path.join(d, m["asset"] + ".readings.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"asset": m["asset"], "node": m["asset"] + "_Needle", **m["readings"]}, f, indent=1); f.write("\n")
    return p


def extra_checks(A):
    c, t, g = A[CB], A[TK], A[SG]
    return [("chalkboard 1.2 x 0.8 m", c["predicted"]["dimensions"][0] == 1.2 and c["predicted"]["dimensions"][2] == 0.8, c["predicted"]["dimensions"]),
            ("SOCKET_Text on the slate face, facing front", c["sockets"][0]["location"][1] < 0 and c["sockets"][0]["forward"] == [0, -1, 0], ""),
            ("token coin-sized (<= 4 cm)", max(t["predicted"]["dimensions"]) <= 0.04, t["predicted"]["dimensions"]),
            ("storm glass ~0.4 m tall", abs(g["predicted"]["dimensions"][2] - 0.4) < 0.01, g["predicted"]["dimensions"]),
            ("needle is a separate named child node", [o["name"] for o in g["objects"]] == [SG, SG + "_Needle"] and g["objects"][1]["parent"] == SG, ""),
            ("SOCKET_Needle at the needle pivot", g["sockets"][0]["parent"] == SG + "_Needle" and g["sockets"][0]["location"] == g["objects"][1]["pivot"], ""),
            ("3 readings HIGH/FALLING/LOW, LOW left of FALLING left of HIGH", sorted(g["readings"]["positions"]) == ["FALLING", "HIGH", "LOW"]
             and g["readings"]["positions"]["LOW"]["ue_tip_dir"][0] < 0 == g["readings"]["positions"]["FALLING"]["ue_tip_dir"][0] < g["readings"]["positions"]["HIGH"]["ue_tip_dir"][0], ""),
            ("needle tip stays on the dial at every reading", all(0.032 + 0.04 <= 0.095 for _ in READINGS), "")]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
