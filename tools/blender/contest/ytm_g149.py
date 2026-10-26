# SPDX-License-Identifier: MIT
"""G149 The Guest Lofts (youtube-master 50211, buf-minigame-contest-20261019-youtube-master; PR #370 brew.lofts.GuestLofts, merged af1f534c0),
blender-kit/v1, G66 stall style (palette via ytm_g116 / ytm_g66). Keyed to the code: LOFTS 8, FAMILIES_PER_ISLAND 2 x 4 far islands = 8
families; every loft aired is one set of linen (aired()); arrive = 1 + legs x DAYS_PER_LEG(3) + wait 0..WAIT_MAX(3), stay STAY_MIN 2..STAY_MAX 6
with routes of 1..4 legs, so arrivals fall on days 4..16 and the last possible night is day 21.
  Prop_YTM_LoftBed        2.0 x 1.0 m timber bed (G66 stall timber), linen mattress + pillow, patchwork quilt on its OWN slot (slot 2):
                          patch colours are MI params of M_YTM_Patchwork (PatchA..F, PatchSize_cm, PatchSeed; object-space grid, no UV
                          dependence). SOCKET_Sleep (mattress top, head to +Y), SOCKET_Bags (floor at the foot). UCX bed + headboard.
  Prop_YTM_LinenCupboard  open cupboard 1.0 x 0.42 x 1.8 m, 4 shelf levels x 2 = SOCKET_Linen_0..7 (one per loft: PR #370 counts linen, so
                          stacks are a separate mesh spawned/removed at the sockets: show LOFTS - aired() stacks, remove from _7 down),
                          G66 cloth valance, SOCKET_Brine (where Aunt Brine stands). UCX carcass.
  Prop_YTM_LinenStack     one folded linen set (4 sheets + ribbon tie) for SOCKET_Linen_k. Origin bottom centre. No collision.
  Prop_YTM_StayCalendar   wall board, 18 day columns (days 04..21) x 8 family rows on the G119 peg system: SOCKET_Peg_<dd>_<f>
                          (dd = day 04..21, f = family row 0..7) at each hole; pegs are Prop_Census_Peg (G119) with per-loft colour MIs
                          MI_YTM_LoftPeg_1..8 (a clash = two same-colour pegs in one column). SOCKET_Family_0..7 (name plates),
                          SOCKET_Day_<dd> (column heads), SOCKET_Text (title), SOCKET_Linen (linen counter). Origin bottom centre of the
                          board; hang on a wall. UCX board.
Usage: python ytm_g149.py --out data/contest/ytm_g149.kit.json [--materials <dir>]"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import ytm_g116, sky_g119

SEED = 14949
BED, CUP, STACK, CAL = "Prop_YTM_LoftBed", "Prop_YTM_LinenCupboard", "Prop_YTM_LinenStack", "Prop_YTM_StayCalendar"
# PR #370 / G97 constants
LOFTS, FAMILIES_PER_ISLAND, ISLAND_LEGS, DAYS_PER_LEG, WAIT_MAX, STAY_MIN, STAY_MAX = 8, 2, (1, 2, 3, 4), 3, 3, 2, 6
FAMILIES = FAMILIES_PER_ISLAND * len(ISLAND_LEGS)
DAY0 = 1 + min(ISLAND_LEGS) * DAYS_PER_LEG                         # 4: earliest arrival
DAY1 = 1 + max(ISLAND_LEGS) * DAYS_PER_LEG + WAIT_MAX + STAY_MAX - 1  # 21: last possible night
DAYS = list(range(DAY0, DAY1 + 1))
CAPS = {BED: 3000, CUP: 3000, STACK: 400, CAL: 6000}
SPEC = {"gap": "G149", "ask": "youtube-master 50211", "lod": "LOD0/1", "style": "G66 stall palette (ytm_g66 via ytm_g116)", "code": "PR #370 GuestLofts (af1f534c0)"}
TIMBER, SIGN, CLOTH = ytm_g116.TIMBER, ytm_g116.BOARD, ytm_g116.CLOTH
LINEN, HOLE = "EDE6D6", "2A2018"
PATCHES = ["C2553A", "E0A33A", "5E8A4E", "3E6E9A", "8A4E7A", "E8D8B8"]
LOFT_PEGS = ["C0392B", "E67E22", "F1C40F", "27AE60", "16A085", "2980B9", "8E44AD", "ECF0F1"]
# bed
BW, BL, RAIL_Z, MAT_H = 1.0, 2.0, 0.3, 0.16
MAT_TOP = 0.37 + MAT_H
# cupboard
CW, CD, CH = 1.0, 0.42, 1.8
LEVELS = (1.36, 0.94, 0.52, 0.11)                                    # shelf tops, top level first (SOCKET_Linen_0.. reading order)
STACK_W, STACK_D, SHEET = 0.36, 0.28, 0.035
# calendar
PX, PZ = 0.06, 0.065
LABEL_W, MARGIN, HEAD = 0.26, 0.05, 0.13
CALW = LABEL_W + len(DAYS) * PX + MARGIN
CALH = MARGIN + FAMILIES * PZ + HEAD
CBT = 0.03


def bed(seed=SEED):
    a = BED; P = []
    for sx in (-1, 1):
        for sy, h in ((1, 0.95), (-1, 0.62)):
            P.append(K.box("Post%s%s" % ("L" if sx < 0 else "R", "H" if sy > 0 else "F"), (0.07, 0.07, h), (sx * (BW / 2 - 0.035), sy * (BL / 2 - 0.035), h / 2), 0, bevel=False))
        P.append(K.box("SideRail%s" % ("L" if sx < 0 else "R"), (0.05, BL - 0.14, 0.14), (sx * (BW / 2 - 0.035), 0, RAIL_Z), 0, bevel=False))
    P.append(K.box("Headboard", (BW - 0.14, 0.04, 0.42), (0, BL / 2 - 0.035, 0.66), 0, bevel=False))
    P.append(K.box("HeadCap", (BW + 0.04, 0.09, 0.04), (0, BL / 2 - 0.035, 0.97), 0, bevel=False, lod1={"drop": True}))
    P.append(K.box("Footboard", (BW - 0.14, 0.04, 0.24), (0, -BL / 2 + 0.035, 0.45), 0, bevel=False))
    for i in range(5):
        P.append(K.box("Slat%d" % i, (BW - 0.1, 0.08, 0.02), (0, -0.8 + 0.4 * i, 0.36), 0, bevel=False, lod1={"drop": True}))
    P += K.plain_lod1(K.box("Mattress", (BW - 0.1, BL - 0.1, MAT_H), (0, 0, 0.37 + MAT_H / 2), 1))
    P += K.plain_lod1(K.box("Pillow", (0.62, 0.34, 0.1), (0, BL / 2 - 0.26, MAT_TOP + 0.05), 1))
    Q = [K.box("QuiltTop", (BW - 0.04, 1.42, 0.03), (0, -0.25, MAT_TOP + 0.015), 2, bevel=False),
         K.box("QuiltDropL", (0.025, 1.42, 0.24), (-(BW - 0.04) / 2, -0.25, MAT_TOP - 0.09), 2, bevel=False),
         K.box("QuiltDropR", (0.025, 1.42, 0.24), ((BW - 0.04) / 2, -0.25, MAT_TOP - 0.09), 2, bevel=False),
         K.box("QuiltDropF", (BW - 0.04, 0.025, 0.24), (0, -0.96, MAT_TOP - 0.09), 2, bevel=False)]
    Q += K.plain_lod1(K.box("QuiltFold", (BW - 0.03, 0.2, 0.05), (0, 0.42, MAT_TOP + 0.03), 2))
    socks = [K.socket("Sleep", (0, 0.2, MAT_TOP), forward=(0, 1, 0)), K.socket("Bags", (0, -BL / 2 - 0.25, 0), forward=(0, 1, 0))]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="2.0 x 1.0 m, mattress top 0.53 m", tri_cap=CAPS[a], collision="UCX bed + headboard",
                                                            sockets=["Sleep", "Bags"], quilt="slot 2 M_YTM_Patchwork: patch colours are MI params"),
         "materials": [K.material(a, 0, "bed timber (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "linen", LINEN, 0.9),
                       K.material(a, 2, "patchwork quilt (M_YTM_Patchwork, patch colours = MI params)", PATCHES[0], 0.9)],
         "objects": [K.obj(a, P + Q)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (BW, BL, MAT_TOP), (0, 0, MAT_TOP / 2)), K.ucx_box(a, 1, (BW, 0.07, 0.97), (0, BL / 2 - 0.035, 0.485))], "nanite": True}
    return K.finish(m)


def linen_locs():
    return [(k, (s * 0.24, -0.02, z)) for k, (z, s) in enumerate((z, s) for z in LEVELS for s in (-1, 1))]


def cupboard(seed=SEED):
    a = CUP; P = []
    for s in (-1, 1):
        P.append(K.box("Side%s" % ("L" if s < 0 else "R"), (0.03, CD, CH), (s * (CW / 2 - 0.015), 0, CH / 2), 0, bevel=False))
    P.append(K.box("Top", (CW + 0.04, CD + 0.03, 0.04), (0, -0.015, CH + 0.02), 0, bevel=False))
    P.append(K.box("Plinth", (CW, CD, 0.08), (0, 0, 0.04), 0, bevel=False))
    P.append(K.box("Back", (CW - 0.06, 0.02, CH - 0.08), (0, CD / 2 - 0.01, 0.08 + (CH - 0.08) / 2), 1, bevel=False))
    for i, z in enumerate(LEVELS[:-1]):
        P.append(K.box("Shelf%d" % i, (CW - 0.06, CD - 0.03, 0.025), (0, -0.015, z - 0.0125), 0, bevel=False))
    P.append(K.box("Floor", (CW - 0.06, CD - 0.03, 0.03), (0, -0.015, LEVELS[-1] - 0.015), 0, bevel=False))
    for s in (-1, 1):
        P.append(K.box("Bracket%s" % ("L" if s < 0 else "R"), (0.06, 0.04, 0.12), (s * (CW / 2 + 0.01), -CD / 2 + 0.02, CH - 0.06), 0, bevel=False, lod1={"drop": True}))
    V = [K.box("ValanceRail", (CW, 0.02, 0.03), (0, -CD / 2 - 0.01, CH - 0.015), 2, bevel=False, lod1={"drop": True})]
    n = 7
    for i in range(n):
        x = -CW / 2 + (i + 0.5) * CW / n
        V.append(K.slab("Scallop%d" % i, [(-CW / n / 2, 0.0), (CW / n / 2, 0.0), (CW / n / 2 * 0.7, -0.07), (0.0, -0.1), (-CW / n / 2 * 0.7, -0.07)], 0.006,
                        (x, -CD / 2 - 0.022, CH - 0.03), 2, rot=(90, 0, 0), lod1={"drop": True}))
    socks = [K.socket("Linen_%d" % k, loc, forward=(0, -1, 0)) for k, loc in linen_locs()] + [K.socket("Brine", (0, -CD / 2 - 0.5, 0), forward=(0, 1, 0))]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="1.0 x 0.42 x 1.8 m open cupboard", tri_cap=CAPS[a], collision="UCX carcass",
                                                            sockets=["Linen_0..7", "Brine"], linen="LOFTS 8 stacks; show LOFTS - aired(); Prop_YTM_LinenStack at SOCKET_Linen_k"),
         "materials": [K.material(a, 0, "cupboard timber (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "back boards (G66 sign board)", SIGN, 0.8),
                       K.material(a, 2, "valance cloth (G66)", CLOTH[0], 0.9)],
         "objects": [K.obj(a, P + V)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (CW, CD, CH), (0, 0, CH / 2))], "nanite": True}
    return K.finish(m)


def stack(seed=SEED):
    a = STACK; r = K.rng(seed, a); P = []
    for i in range(4):
        P += K.plain_lod1(K.box("Sheet%d" % i, (STACK_W - 0.01 * (i % 2), STACK_D - 0.008 * (i % 2), SHEET), (round(r.uniform(-0.006, 0.006), 4), round(r.uniform(-0.005, 0.005), 4), SHEET * (i + 0.5)), 0))
    top = SHEET * 4
    P.append(K.box("RibbonV", (0.03, STACK_D + 0.006, 0.004), (0, 0, top + 0.002), 1, bevel=False))
    P.append(K.box("RibbonF", (0.03, 0.004, top), (0, -STACK_D / 2 - 0.002, top / 2), 1, bevel=False))
    P.append(K.box("RibbonB", (0.03, 0.004, top), (0, STACK_D / 2 + 0.002, top / 2), 1, bevel=False))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="0.36 x 0.28 x 0.14 m folded linen set", tri_cap=CAPS[a], collision="none (shelf item)",
                                                            sockets=[], use="spawn at Prop_YTM_LinenCupboard SOCKET_Linen_k, k < LOFTS - aired()"),
         "materials": [K.material(a, 0, "linen", LINEN, 0.9), K.material(a, 1, "ribbon tie (G66 cloth)", CLOTH[1], 0.8)],
         "objects": [K.obj(a, P)], "sockets": [], "collision": [], "nanite": True}
    return K.finish(m)


def cal_hole(day, f):
    """peg system (sky_g119.grid_loc): row f (top down), column = day - DAY0, on the board face."""
    return sky_g119.grid_loc(f, day - DAY0, cols=len(DAYS), pitch_x=PX, pitch_z=PZ, top_z=CALH - HEAD - PZ / 2, face_y=-CBT / 2, x0=(LABEL_W - MARGIN) / 2)


def calendar(seed=SEED):
    a = CAL; P = []
    P += K.plain_lod1(K.box("Board", (CALW, CBT, CALH), (0, 0, CALH / 2), 0))
    for nm, sz, c in (("FrameT", (CALW + 0.04, CBT + 0.02, 0.03), (0, 0, CALH)), ("FrameB", (CALW + 0.04, CBT + 0.02, 0.03), (0, 0, 0.015)),
                      ("FrameL", (0.03, CBT + 0.02, CALH), (-CALW / 2 - 0.005, 0, CALH / 2)), ("FrameR", (0.03, CBT + 0.02, CALH), (CALW / 2 + 0.005, 0, CALH / 2))):
        P.append(K.box(nm, sz, c, 0, bevel=False))
    P.append(K.box("TitlePlate", (0.5, 0.006, 0.07), (0, -CBT / 2 - 0.003, CALH - 0.055), 1, bevel=False))
    P.append(K.box("LinenTally", (0.16, 0.006, 0.07), (CALW / 2 - 0.12, -CBT / 2 - 0.003, CALH - 0.055), 1, bevel=False))
    xl = -CALW / 2 + 0.02 + (LABEL_W - 0.06) / 2
    for f in range(FAMILIES):
        z = cal_hole(DAY0, f)[2]
        P.append(K.box("NamePlate%d" % f, (LABEL_W - 0.06, 0.006, PZ * 0.7), (xl, -CBT / 2 - 0.003, z), 1, bevel=False))
    for d in DAYS:
        x = cal_hole(d, 0)[0]
        P.append(K.box("DayTick%02d" % d, (0.006 if d % 7 else 0.014, 0.004, 0.03), (x, -CBT / 2 - 0.002, CALH - HEAD + 0.02), 1, bevel=False, lod1={"drop": True}))
    locs = [("%02d_%d" % (d, f), cal_hole(d, f)) for f in range(FAMILIES) for d in DAYS]
    H = [dict(h, slot=2) for h in sky_g119.peg_holes(locs, 2)]
    for s in (-1, 1):
        P.append(K.box("Hook%s" % ("L" if s < 0 else "R"), (0.02, 0.02, 0.05), (s * CALW / 3, 0.0, CALH + 0.04), 0, bevel=False, lod1={"drop": True}))
    socks = sky_g119.peg_sockets(locs)
    socks += [K.socket("Family_%d" % f, (xl, -CBT / 2 - 0.006, cal_hole(DAY0, f)[2]), forward=(0, -1, 0)) for f in range(FAMILIES)]
    socks += [K.socket("Day_%02d" % d, (cal_hole(d, 0)[0], -CBT / 2 - 0.004, CALH - HEAD + 0.06), forward=(0, -1, 0)) for d in DAYS]
    socks += [K.socket("Text", (0, -CBT / 2 - 0.006, CALH - 0.055), forward=(0, -1, 0)), K.socket("Linen", (CALW / 2 - 0.12, -CBT / 2 - 0.006, CALH - 0.055), forward=(0, -1, 0))]
    m = {"asset": a, "kind": "Prop", "seed": seed,
         "spec": dict(SPEC, size_m="%.2f x %.2f m wall board" % (CALW, CALH), tri_cap=CAPS[a], collision="UCX board",
                      sockets=["Peg_<dd>_<f> (dd %02d..%02d, f 0..%d)" % (DAY0, DAY1, FAMILIES - 1), "Family_0..7", "Day_<dd>", "Text", "Linen"],
                      pegs="Prop_Census_Peg (G119) at SOCKET_Peg_dd_f, colour MI_YTM_LoftPeg_<loft>", days=[DAY0, DAY1]),
         "materials": [K.material(a, 0, "board timber (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "painted plates (G66 sign board)", SIGN, 0.8),
                       K.material(a, 2, "peg hole rims", HOLE, 0.7)],
         "objects": [K.obj(a, P + H)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (CALW + 0.04, CBT + 0.02, CALH + 0.015), (0, 0, (CALH + 0.015) / 2))], "nanite": True,
         "off_centre_ok": "hanging hooks only; board centred"}
    return K.finish(m)


def materials_manifest():
    return {"schema": "bb-material-variants/1", "gap": "G149 (youtube-master 50211, PR #370 brew.lofts.GuestLofts)", "status": "NOT READY",
            "quilt": {"asset": BED, "slot": "slot 2 patchwork quilt", "master": "M_YTM_Patchwork",
                      "params": {"PatchA..PatchF": "vector, linear (6 patch colours)", "PatchSize_cm": "scalar, default 16", "PatchSeed": "scalar (shuffles which colour lands in which patch)", "Seam": "vector, linear (stitch line colour)", "SeamWidth_cm": "scalar, default 0.6"},
                      "graph": "cell = floor(ObjectLocalPosition.xy / PatchSize); idx = floor(hash(cell + PatchSeed) * 6); BaseColor = lerp(Patch[idx], Seam, seamMask(frac(pos / PatchSize), SeamWidth / PatchSize)); object-space, so it needs no quilt UVs",
                      "instances": {"MI_YTM_Quilt_%d" % i: {"PatchSeed": i, "PatchSize_cm": 16, **{"Patch%s_srgb" % "ABCDEF"[k]: PATCHES[(k + i) % 6] for k in range(6)}, "Seam_srgb": "F4EBD8"} for i in range(1, LOFTS + 1)},
                      "note": "one quilt MI per loft, so each family's bed reads different"},
            "loft_pegs": {"asset": "Prop_Census_Peg (G119)", "slot": "peg head", "instances": {"MI_YTM_LoftPeg_%d" % (i + 1): {"Colour_srgb": LOFT_PEGS[i]} for i in range(LOFTS)},
                          "use": "a peg at SOCKET_Peg_<dd>_<f> means family f sleeps night dd in that loft; two same-colour pegs in one column = CLASH"},
            "linen": {"asset": STACK, "rule": "Prop_YTM_LinenCupboard shows LOFTS - aired() stacks at SOCKET_Linen_0..; remove from the highest index; the calendar SOCKET_Linen counter shows aired()"}}


def assets(seed=SEED):
    return [bed(seed), cupboard(seed), stack(seed), calendar(seed)]


SOCKETS = {BED: ["SOCKET_Sleep", "SOCKET_Bags"], CUP: ["SOCKET_Linen_%d" % k for k in range(LOFTS)] + ["SOCKET_Brine"], STACK: [],
           CAL: ["SOCKET_Peg_%02d_%d" % (d, f) for f in range(FAMILIES) for d in DAYS] + ["SOCKET_Family_%d" % f for f in range(FAMILIES)]
                + ["SOCKET_Day_%02d" % d for d in DAYS] + ["SOCKET_Text", "SOCKET_Linen"]}


def extra_checks(A):
    B, C, S, L = A[BED], A[CUP], A[STACK], A[CAL]
    bs = {s["name"]: s["location"] for s in B["sockets"]}; cs = {s["name"]: s["location"] for s in C["sockets"]}; ls = {s["name"]: s["location"] for s in L["sockets"]}
    quilt = [q for q in B["objects"][0]["parts"] if q["name"].startswith("Quilt")]
    sd = S["predicted"]["dimensions"]
    gaps = [LEVELS[i] - 0.025 - LEVELS[i + 1] for i in range(len(LEVELS) - 1)]
    pegs = [n for n in ls if n.startswith("SOCKET_Peg_")]
    xs = sorted({round(ls["SOCKET_Peg_%02d_0" % d][0], 5) for d in DAYS})
    return [("PR #370 counts: 8 lofts, 8 families, days 4..21", (LOFTS, FAMILIES, DAY0, DAY1) == (8, 8, 4, 21)),
            ("quilt on its own slot (2) and nothing else uses it", all(q["slot"] == 2 for q in quilt) and all(q["slot"] != 2 for q in B["objects"][0]["parts"] if not q["name"].startswith("Quilt"))),
            ("sleep socket on the mattress top", abs(bs["SOCKET_Sleep"][2] - MAT_TOP) < 1e-9),
            ("one linen socket per loft, 2 per shelf level", sum(1 for n in cs if n.startswith("SOCKET_Linen_")) == LOFTS and len({round(v[2], 4) for n, v in cs.items() if n.startswith("SOCKET_Linen_")}) == 4),
            ("a stack fits each shelf gap and two fit side by side", sd[2] < min(gaps) - 0.05 and 2 * sd[0] < CW - 0.06, (sd, gaps)),
            ("calendar: 18 day columns x 8 family rows of pegs", len(pegs) == len(DAYS) * FAMILIES == 144),
            ("calendar columns at the peg pitch, day order left to right", all(abs(b - a - PX) < 1e-6 for a, b in zip(xs, xs[1:])) and ls["SOCKET_Peg_04_0"][0] < ls["SOCKET_Peg_21_0"][0]),
            ("G119 peg fits the pitch (head < column pitch)", 2 * sky_g119.HOLE_R * 1.6 < PX),
            ("family rows top down", all(ls["SOCKET_Peg_04_%d" % f][2] > ls["SOCKET_Peg_04_%d" % (f + 1)][2] for f in range(FAMILIES - 1))),
            ("G66 palette reused", B["materials"][0]["hex"] == TIMBER and C["materials"][0]["hex"] == TIMBER and L["materials"][0]["hex"] == TIMBER)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); ap.add_argument("--materials"); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
    if o.materials:
        os.makedirs(o.materials, exist_ok=True)
        with open(os.path.join(o.materials, "YTM_G149.material_variants.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(materials_manifest(), f, indent=1); f.write("\n")
