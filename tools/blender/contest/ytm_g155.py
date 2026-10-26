# SPDX-License-Identifier: MIT
"""G155 The Apprentices (youtube-master 50345, buf-minigame-contest-20261019-youtube-master; PR #380 brew.apprentice.Apprenticeships,
STORY.md "A lantern board in the homestead yard (four child pins, four master hooks, rankings shown as ribbons)"), blender-kit/v1,
G66 stall style (palette read from ytm_g66 / ytm_g116). Keyed to the code: 4 children (G116 SongSchool.fromFarIslands), 4 masters
Apprenticeships.MASTERS = mason, keeper, brine, dov; lantern night = announce().
  Prop_YTM_LanternBoard  1.6 m wide yard board, 2.3 m posts: a 1.4 x 1.0 m timber board with 4 child pin holes on the left
                         (SOCKET_Pin_0..3, top down, forward +Y into the board: seat Prop_YTM_RibbonPin's origin here) and 4 iron
                         hooks on the right (SOCKET_Hook_0..3 in the hook crook, hook k = MASTERS[k]), blank name plaques beside
                         each, header plaque (SOCKET_Text). A top beam carries 4 paper lanterns (the G131 lantern) at the G131
                         LitCount pitch, so MI_YTM_LanternString_Lit / _Unlit apply unchanged (SOCKET_Lamp_0..3 at the lantern
                         centres; light them for lantern night). SOCKET_Wick: Old Wick's stand point in front. UCX board + posts.
  Prop_YTM_RibbonPin     one 4 cm ribbon rosette pin with two 11 cm tails. Origin = the point where the pin enters the board, shaft
                         along +Y: put the origin on SOCKET_Pin_k with +Y along its forward. Ribbon slot 1 takes one of four colour
                         MIs, MI_YTM_RibbonPin_0..3 (PR #380 names no glbs, so it is one mesh): the ribbon shows how that child
                         ranks the master it is pinned to (0 = first choice). UI-scale: no collision.
Usage: python ytm_g155.py --out data/contest/ytm_g155.kit.json [--materials <dir>]"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import ytm_g116, ytm_g131

SEED = 15555
BOARD_A, PIN = "Prop_YTM_LanternBoard", "Prop_YTM_RibbonPin"
CAPS = {BOARD_A: 4500, PIN: 600}
SPEC = {"gap": "G155", "ask": "youtube-master 50345", "lod": "LOD0/1", "style": "G66 stall palette (ytm_g66)", "code": "PR #380"}
TIMBER, SIGN = ytm_g116.TIMBER, ytm_g116.BOARD
IRON, PAPERRIB = "3A3A3E", "5A4632"
MASTERS = ["mason", "keeper", "brine", "dov"]          # Apprenticeships.MASTERS order (ChoirStones.MASON, SeedSongSpring.KEEPER, RootCellar.BRINE, DOV)
N = 4
BW, BT, BH, BZ = 1.4, 0.03, 1.0, 0.8                 # board width, thickness, height, bottom
PX = 0.75                                           # post x
POST_H, BEAM_Z = 2.3, 2.25
ROW_Z0, ROW_PITCH = BZ + BH - 0.28, 0.2             # row 0 (top) .. row 3
PIN_X, HOOK_X = -0.3, 0.3
FACE_Y = -BT / 2
RIBBON = [ytm_g131.CLOTH[i] for i in range(4)]      # G66 trader cloth colours (Rope, Stone, Eggs, Fish)


def row_z(k):
    return round(ROW_Z0 - k * ROW_PITCH, 5)


def lantern(k, zt):
    x = ytm_g131.LAMP_X0 + k * ytm_g131.LAMP_PITCH; zc = zt - 0.07 - 0.11
    P = [K.box("Hanger%d" % k, (0.004, 0.004, 0.07), (x, 0, zt - 0.035), 0, bevel=False, lod1={"drop": True}),
         K.cyl("CapTop%d" % k, "z", 0.035, 0.035, 0.012, (x, 0, zc + 0.104), 0, 8, lod1={"segments": 6}),
         K.lathe("Lantern%d" % k, [(0.03, -0.1), (0.075, -0.06), (0.085, 0.0), (0.075, 0.06), (0.03, 0.1)], (x, 0, zc), 2, 12, True, True, lod1={"segments": 6}),
         K.cyl("CapBot%d" % k, "z", 0.032, 0.032, 0.012, (x, 0, zc - 0.104), 0, 8, lod1={"segments": 6})]
    for r_ in (-0.05, 0.05):
        P.append(K.lathe("Rib%d%s" % (k, "a" if r_ < 0 else "b"), [(0.0815, r_ - 0.004), (0.0825, r_), (0.0815, r_ + 0.004)], (x, 0, zc), 1, 12, False, False, lod1={"drop": True}))
    return P, (round(x, 5), 0, round(zc, 5))


def board(seed=SEED):
    a = BOARD_A; P = []
    P += K.plain_lod1(K.box("Board", (BW, BT, BH), (0, 0, BZ + BH / 2), 0))
    P.append(K.box("Header", (0.7, 0.012, 0.12), (0, FACE_Y - 0.006, BZ + BH - 0.09), 1, bevel=False))
    for s in (-1, 1):
        t = "L" if s < 0 else "R"
        P.append(K.box("Post" + t, (0.09, 0.09, POST_H), (s * PX, 0.045 + BT / 2, POST_H / 2), 0, bevel=False))
        P.append(K.box("PostCap" + t, (0.13, 0.13, 0.04), (s * PX, 0.045 + BT / 2, POST_H + 0.02), 0, bevel=False, lod1={"drop": True}))
        P.append(K.box("Foot" + t, (0.1, 0.6, 0.07), (s * PX, 0.05, 0.035), 0, bevel=False))
        P.append(K.box("Rail" + t, (0.06, 0.03, BH), (s * (BW / 2 - 0.03), FACE_Y - 0.015, BZ + BH / 2), 0, bevel=False, lod1={"drop": True}))
    P.append(K.box("Beam", (2 * PX + 0.2, 0.08, 0.08), (0, 0.045 + BT / 2, BEAM_Z), 0, bevel=False))
    P.append(K.box("Divider", (0.02, 0.008, N * ROW_PITCH), (0, FACE_Y - 0.004, row_z(0) - (N - 1) * ROW_PITCH / 2), 1, bevel=False, lod1={"drop": True}))
    for k in range(N):
        z = row_z(k)
        P += pin_rim(k, z)
        P.append(K.box("ChildPlate%d" % k, (0.26, 0.008, 0.08), (PIN_X - 0.24, FACE_Y - 0.004, z), 1, bevel=False))
        P.append(K.box("MasterPlate%d" % k, (0.26, 0.008, 0.08), (HOOK_X + 0.24, FACE_Y - 0.004, z), 1, bevel=False))
        P.append(K.box("HookPlate%d" % k, (0.04, 0.006, 0.06), (HOOK_X, FACE_Y - 0.003, z + 0.01), 2, bevel=False, lod1={"drop": True}))
        P.append(K.box("HookArm%d" % k, (0.012, 0.055, 0.012), (HOOK_X, FACE_Y - 0.0275, z), 2, bevel=False))
        P.append(K.box("HookTip%d" % k, (0.012, 0.012, 0.03), (HOOK_X, FACE_Y - 0.049, z + 0.015), 2, bevel=False))
    L = []; lamps = []
    for k in range(N):
        q, c = lantern(k, BEAM_Z - 0.04); L += q; lamps.append(c)
    socks = [K.socket("Pin_%d" % k, (PIN_X, FACE_Y, row_z(k)), forward=(0, 1, 0)) for k in range(N)]
    socks += [K.socket("Hook_%d" % k, (HOOK_X, round(FACE_Y - 0.04, 5), round(row_z(k) + 0.006, 5)), forward=(0, -1, 0)) for k in range(N)]
    socks += [K.socket("Lamp_%d" % k, c, forward=(0, 0, -1)) for k, c in enumerate(lamps)]
    socks += [K.socket("Text", (0, round(FACE_Y - 0.0125, 5), round(BZ + BH - 0.09, 5)), forward=(0, -1, 0)), K.socket("Wick", (-0.5, -1.0, 0), forward=(0, 1, 0))]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="1.4 x 1.0 m board on 2.3 m posts, 1.6 m wide", tri_cap=CAPS[a], collision="UCX board + posts",
                                                            sockets=["Pin_0..3", "Hook_0..3", "Lamp_0..3", "Text", "Wick"], hooks={"Hook_%d" % k: MASTERS[k] for k in range(N)},
                                                            pins="Pin_k = the k-th child (Apprenticeships children order); seat Prop_YTM_RibbonPin's origin, +Y along forward",
                                                            mi="lantern glow slot 4 = the G131 lantern (MI_YTM_LanternString_Lit / _Unlit, same LitCount pitch)"),
         "materials": [K.material(a, 0, "board timber (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "plaques (G66 sign board)", SIGN, 0.8),
                       K.material(a, 2, "iron hooks / pin rims", IRON, 0.6, 0.6), K.material(a, 3, "lantern ribs", PAPERRIB, 0.8),
                       K.material(a, 4, "paper lantern glow (emissive, LitCount)", "F2B25C", 0.7, glow=True)],
         "objects": [K.obj(a, P), K.obj(a + "_Lanterns", [dict(q, slot={0: 0, 1: 3, 2: 4}[q["slot"]]) for q in L], parent=a, role="paper lanterns (G131 lantern, LitCount glow)")],
         "sockets": socks,
         "collision": [K.ucx_box(a, 0, (BW, BT + 0.06, BH), (0, -0.015, BZ + BH / 2))] +
                      [K.ucx_box(a, 1 + i, (0.1, 0.6, POST_H), (s * PX, 0.05, POST_H / 2)) for i, s in enumerate((-1, 1))], "nanite": True,
         "off_centre_ok": "feet reach back (+Y) for balance; origin = under the board face"}
    return K.finish(m)


def pin_rim(k, z):
    return [K.cyl("PinRim%d" % k, "y", 0.012, 0.012, 0.004, (PIN_X, FACE_Y - 0.002, z), 2, 8, lod1={"segments": 4})]


def pin(seed=SEED):
    a = PIN; P = []
    P.append(K.cyl("Shaft", "y", 0.0025, 0.0015, 0.03, (0, 0.015, 0), 0, 6, lod1={"segments": 4}))
    P.append(K.lathe("Rosette", [(0.008, -0.002), (0.035, -0.002), (0.038, 0.0), (0.035, 0.002), (0.008, 0.002)], (0, -0.008, 0), 1, 16, False, False, rot=(90, 0, 0), lod1={"segments": 8}))
    for i in range(8):
        a0 = 2 * math.pi * i / 8
        P.append(K.box("Pleat%d" % i, (0.006, 0.004, 0.03), (round(0.024 * math.cos(a0), 5), -0.0105, round(0.024 * math.sin(a0), 5)), 1, rot=(0, round(90 - math.degrees(a0), 3), 0), bevel=False, lod1={"drop": True}))
    P.append(K.lathe("Button", [(0.0, -0.006), (0.012, -0.004), (0.014, 0.0), (0.012, 0.004), (0.0, 0.006)], (0, -0.013, 0), 2, 10, False, False, rot=(90, 0, 0), lod1={"segments": 6}))
    for s in (-1, 1):
        tail = [(-0.011, 0.0), (0.011, 0.0), (0.011, -0.11), (0.0, -0.095), (-0.011, -0.11)]
        P.append(K.slab("Tail%s" % ("L" if s < 0 else "R"), tail, 0.002, (s * 0.012, -0.004, -0.012), 1, rot=(90, s * -14, 0), lod1={"segments": 5}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="7.6 cm rosette, tails to 12 cm below the pin", tri_cap=CAPS[a], collision="none (UI-scale prop)",
                                                            seat="origin = where the pin enters the board; the shaft runs 3 cm along +Y: put the origin on SOCKET_Pin_k with +Y along its forward",
                                                            mi="ribbon slot 1: MI_YTM_RibbonPin_0..3 (rank 0 = first choice)"),
         "materials": [K.material(a, 0, "brass pin", "B08D57", 0.4, 0.8), K.material(a, 1, "ribbon (rank colour MI)", RIBBON[0], 0.7), K.material(a, 2, "rosette button (G66 sign board)", SIGN, 0.6)],
         "objects": [K.obj(a, P)], "sockets": [], "collision": [], "nanite": False,
         "off_centre_ok": "rosette hangs off its pin; origin = the pin's entry point on the board face",
         "origin_is_attach": "seats on Prop_YTM_LanternBoard SOCKET_Pin_k"}
    return K.finish(m)


def materials_manifest():
    lan = ytm_g131.materials_manifest()["lanterns"]
    return {"schema": "bb-material-variants/1", "gap": "G155 (youtube-master 50345, PR #380 brew.apprentice.Apprenticeships)", "status": "NOT READY",
            "lanterns": {"asset": BOARD_A, "slot": "paper lantern glow (slot 4, object Prop_YTM_LanternBoard_Lanterns)", "reuse": "G131 MI_YTM_LanternString_Lit / _Unlit unchanged",
                         "params": lan["params"], "instances": lan["instances"],
                         "sockets": "SOCKET_Lamp_k: warm point light while k < LitCount; Lit on lantern night (announce()), Unlit while pinning"},
            "ribbons": {"asset": PIN, "slot": "ribbon (slot 1)", "parent": "the G116 card-tab material (PupilColour vector, one MI per colour)",
                        "instances": {"MI_YTM_RibbonPin_%d" % r: {"PupilColour_srgb": RIBBON[r], "rank": r} for r in range(4)},
                        "rule": "the pin in SOCKET_Pin_k carries MI_YTM_RibbonPin_<r>, r = rank (0-based) of the paired master in child k's list; colours are the G66 trader cloths (Rope, Stone, Eggs, Fish)"},
            "hooks": {"Hook_%d" % k: MASTERS[k] for k in range(N)}}


def assets(seed=SEED):
    return [board(seed), pin(seed)]


SOCKETS = {BOARD_A: ["SOCKET_Pin_%d" % k for k in range(N)] + ["SOCKET_Hook_%d" % k for k in range(N)] + ["SOCKET_Lamp_%d" % k for k in range(N)] + ["SOCKET_Text", "SOCKET_Wick"],
           PIN: []}


def extra_checks(A):
    B, R = A[BOARD_A], A[PIN]
    bs = {s["name"]: s["location"] for s in B["sockets"]}
    pins = [bs["SOCKET_Pin_%d" % k] for k in range(N)]; hooks = [bs["SOCKET_Hook_%d" % k] for k in range(N)]
    lamps = [bs["SOCKET_Lamp_%d" % k] for k in range(N)]
    rp = R["predicted"]
    return [("4 pins left, 4 hooks right, rows top down", all(p[0] < 0 < h[0] for p, h in zip(pins, hooks)) and all(pins[k][2] > pins[k + 1][2] and hooks[k][2] > hooks[k + 1][2] for k in range(N - 1))),
            ("pins on the board face, forward into it", all(abs(p[1] - FACE_Y) < 1e-9 for p in pins) and all(s["forward"] == [0, 1, 0] for s in B["sockets"] if s["name"].startswith("SOCKET_Pin_"))),
            ("hooks in front of the face, inside the board", all(h[1] < FACE_Y and BZ < h[2] < BZ + BH for h in hooks)),
            ("hook order = Apprenticeships.MASTERS", B["spec"]["hooks"] == {"Hook_0": "mason", "Hook_1": "keeper", "Hook_2": "brine", "Hook_3": "dov"}),
            ("lanterns at the G131 LitCount pitch (same MIs)", all(abs(lamps[k][0] - (ytm_g131.LAMP_X0 + k * ytm_g131.LAMP_PITCH)) < 1e-9 for k in range(N))),
            ("lanterns between the board top and the beam", all(BZ + BH < l[2] - 0.11 and l[2] + 0.11 < BEAM_Z for l in lamps)),
            ("ribbon pin hangs below its tails' pin, shaft into +Y", rp["bounds_max"][1] > 0.029 and rp["bounds_min"][2] < -0.1 and rp["bounds_max"][2] < 0.05, rp["bounds_min"]),
            ("4 ribbon MIs, distinct colours", len(set(RIBBON)) == 4 and len(materials_manifest()["ribbons"]["instances"]) == 4),
            ("ribbon fits a pin row (no overlap with the next row)", -rp["bounds_min"][2] < ROW_PITCH - 0.04),
            ("G66 palette reused", B["materials"][0]["hex"] == TIMBER and R["materials"][2]["hex"] == SIGN)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); ap.add_argument("--materials"); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
    if o.materials:
        os.makedirs(o.materials, exist_ok=True)
        with open(os.path.join(o.materials, "YTM_G155.material_variants.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(materials_manifest(), f, indent=1); f.write("\n")
