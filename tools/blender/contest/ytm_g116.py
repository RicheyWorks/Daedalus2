# SPDX-License-Identifier: MIT
"""G116 The Song School (youtube-master 49939, buf-minigame-contest-20261019-youtube-master; PR #337 brew.school.SongSchool,
STORY.md "Schoolroom in the homestead loft, a five-box card shelf"), blender-kit/v1, in the G66 stall style: same timber /
sign-board / cloth palette (read from ytm_g66.stall), plain thin members, bevelled boards with plain LOD1 copies.
Keyed to the code: TOP_BOX 5 boxes (review after INTERVALS 1/2/4/8/16 days), LESSONS_PER_DAY 6 candles, GRADUATES_NEEDED 3 seats.
  Prop_YTM_CardShelf         1.2 m loft shelf; 5 open card boxes on top, each with a label plaque (pips = box number;
                             SOCKET_Label_<k> on the plaque face for the UE text "1 day" .. "16 days"); 4 card slots per box
                             SOCKET_Box<k>_Card<j> (k 1-5, j 0-3, front to back); SOCKET_Deck on the lower shelf (new songs
                             waiting to be introduced). Cards move box to box, so they are a separate mesh:
  Prop_YTM_SongCard          0.15 x 0.13 m card standing on its bottom edge: pupil-colour tab (slot 1, MI PupilColour), ink note.
                             Origin = bottom centre = the slot socket. SOCKET_Grip on the tab (Wick holds it up).
  Prop_YTM_CardShelf_Filled  static snapshot with 16 cards in the slots (4/4/4/3/1 by box) for set dressing.
  Prop_YTM_SchoolBench       1.4 m pupil bench + desk (3 seats: SOCKET_Seat_0..2, SOCKET_Slate_0..2 on the desk ledge).
  Prop_YTM_Slate             framed writing slate + chalk; SOCKET_Grip (attach), SOCKET_Write (slate face centre, chalk text).
  Prop_YTM_LessonCandles     tray of 6 candles (one per lesson of the day), SOCKET_Flame_0..5 at the wicks (VFX / light).
                             Flame slot (emissive, masked) driven by one MI scalar LitCount = SongSchool.lessonsLeft():
                             candle k (from -X) is lit while k < LitCount. MI_YTM_LessonCandles_Lit (6) / _Unlit (0).
Usage: python ytm_g116.py --out data/contest/ytm_g116.kit.json [--materials <dir>]"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import ytm_g66

SEED = 11616
SHELF, CARD, FILLED, BENCH, SLATE, CANDLES = ("Prop_YTM_CardShelf", "Prop_YTM_SongCard", "Prop_YTM_CardShelf_Filled", "Prop_YTM_SchoolBench",
                                              "Prop_YTM_Slate", "Prop_YTM_LessonCandles")
BOXES, SLOTS, LESSONS, SEATS = 5, 4, 6, 3                     # SongSchool.TOP_BOX, cards per box, LESSONS_PER_DAY, GRADUATES_NEEDED
INTERVALS = [1, 2, 4, 8, 16]
FILL = [4, 4, 4, 3, 1]                                          # 16 cards in the filled snapshot
CAPS = {SHELF: 4000, CARD: 300, FILLED: 9000, BENCH: 2500, SLATE: 600, CANDLES: 2500}
SPEC = {"gap": "G116", "ask": "youtube-master 49939", "lod": "LOD0/1", "style": "G66 stall palette (ytm_g66)"}
_G66 = ytm_g66.stall("Rope")["materials"]
TIMBER, BOARD = _G66[0]["hex"], _G66[2]["hex"]                  # stall timber, sign board
CLOTH = [ytm_g66.TRADERS[k][1] for k in ("Rope", "Stone", "Eggs", "Fish")]
SW, SD, SH = 1.2, 0.32, 0.86                                   # shelf width, depth, top height
BX_W, BX_D, BX_H, BX_T = 0.2, 0.16, 0.1, 0.012                 # card box outer size, wall
PITCH = 0.235
CW_, CT_, CH_ = 0.15, 0.004, 0.13                              # card
CAND_PITCH, CAND_X0 = 0.11, -0.275


def wood(a, i=0, name="loft timber (G66 stall timber)"):
    return K.material(a, i, name, TIMBER, 0.85)


def box_x(k):
    return (k - 3) * PITCH                                      # k = 1..5


def slot_loc(k, j):
    return (round(box_x(k), 5), round(-BX_D / 2 + BX_T + 0.022 + j * 0.03, 5), round(SH + BX_T, 5))


def shelf_parts():
    P = []
    for s in (-1, 1):
        P += K.plain_lod1(K.box("Side%s" % ("L" if s > 0 else "R"), (0.03, SD, SH), (s * (SW / 2 - 0.015), 0, SH / 2), 0))
    P += K.plain_lod1(K.box("Top", (SW, SD, 0.03), (0, 0, SH - 0.015), 0))
    P.append(K.box("MidShelf", (SW - 0.06, SD - 0.02, 0.025), (0, 0, 0.42), 0, bevel=False))
    P.append(K.box("Base", (SW - 0.06, SD - 0.02, 0.025), (0, 0, 0.08), 0, bevel=False))
    P.append(K.box("Back", (SW - 0.06, 0.012, SH - 0.1), (0, SD / 2 - 0.006, SH / 2), 0, bevel=False))
    P.append(K.box("Kick", (SW - 0.06, 0.02, 0.07), (0, -SD / 2 + 0.03, 0.035), 0, bevel=False, lod1={"drop": True}))
    for k in range(1, BOXES + 1):
        x = box_x(k); z0 = SH
        P.append(K.box("Box%d_Floor" % k, (BX_W, BX_D, BX_T), (x, 0, z0 + BX_T / 2), 0, bevel=False))
        for s in (-1, 1):
            P.append(K.box("Box%d_Side%d" % (k, (s + 1) // 2), (BX_T, BX_D, BX_H), (x + s * (BX_W - BX_T) / 2, 0, z0 + BX_H / 2), 0, bevel=False))
        P.append(K.box("Box%d_Front" % k, (BX_W, BX_T, BX_H * 0.7), (x, -BX_D / 2 + BX_T / 2, z0 + BX_H * 0.35), 0, bevel=False))
        P.append(K.box("Box%d_BackWall" % k, (BX_W, BX_T, BX_H), (x, BX_D / 2 - BX_T / 2, z0 + BX_H / 2), 0, bevel=False))
        P.append(K.box("Box%d_Plaque" % k, (0.11, 0.005, 0.04), (x, -BX_D / 2 - 0.0025, z0 + BX_H * 0.35), 1, bevel=False))
        for p in range(k):                                     # pips = box number
            P.append(K.cyl("Box%d_Pip%d" % (k, p), "y", 0.004, 0.004, 0.003, (x - 0.04 + 0.02 * p, -BX_D / 2 - 0.0062, z0 + BX_H * 0.35 - 0.012), 2, 6, lod1={"drop": True}))
    for i in range(3):                                        # the deck: blank song cards waiting on the lower shelf
        P.append(K.box("DeckCard%d" % i, (CW_, CH_, 0.004), (0.32 + 0.004 * i, -0.02 + 0.003 * i, 0.4325 + 0.004 * i + 0.002), 1, bevel=False, lod1={"drop": True} if i else None))
    return P


def shelf_sockets():
    S = [K.socket("Box%d_Card%d" % (k, j), slot_loc(k, j), forward=(0, -1, 0)) for k in range(1, BOXES + 1) for j in range(SLOTS)]
    S += [K.socket("Label_%d" % k, (round(box_x(k), 5), round(-BX_D / 2 - 0.005, 5), round(SH + BX_H * 0.35, 5)), forward=(0, -1, 0)) for k in range(1, BOXES + 1)]
    S.append(K.socket("Deck", (0.32, -0.02, 0.4325), forward=(0, 0, 1)))
    return S


def shelf_mats(a):
    return [wood(a), K.material(a, 1, "label plaque / card stock (G66 sign board)", BOARD, 0.8), K.material(a, 2, "ink pips", "2A2420", 0.7)]


def shelf(seed=SEED):
    a = SHELF
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="1.2 x 0.32 m, 0.96 m to the box rims", tri_cap=CAPS[a], collision="UCX body + box row",
                                                            sockets=["Box<k>_Card<j> x20", "Label_1..5", "Deck"], code="TOP_BOX 5, INTERVALS 1/2/4/8/16 d",
                                                            labels={"Label_%d" % (k + 1): "%d day%s" % (d, "" if d == 1 else "s") for k, d in enumerate(INTERVALS)}),
         "materials": shelf_mats(a), "objects": [K.obj(a, shelf_parts())], "sockets": shelf_sockets(),
         "collision": [K.ucx_box(a, 0, (SW, SD, SH), (0, 0, SH / 2)), K.ucx_box(a, 1, (BOXES * PITCH, BX_D + 0.01, BX_H), (0, 0, SH + BX_H / 2))], "nanite": True}
    return K.finish(m)


def card_parts(dx=0.0, dy=0.0, dz=0.0, tag="", pupil_slot=1):
    return [K.box("Card%s" % tag, (CW_, CT_, CH_), (dx, dy, dz + CH_ / 2), 0, bevel=False),
            K.box("Tab%s" % tag, (0.04, CT_ + 0.001, 0.018), (dx - 0.045, dy, dz + CH_ + 0.009), pupil_slot, bevel=False),
            K.cyl("NoteHead%s" % tag, "y", 0.009, 0.009, 0.0012, (dx - 0.01, dy - CT_ / 2 - 0.0006, dz + 0.05), 2, 8, lod1={"drop": True}),
            K.box("NoteStem%s" % tag, (0.0025, 0.0012, 0.04), (dx - 0.0015, dy - CT_ / 2 - 0.0006, dz + 0.07), 2, bevel=False, lod1={"drop": True})]


def card(seed=SEED):
    a = CARD
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="0.15 x 0.13 m song card", tri_cap=CAPS[a], collision="UCX card", sockets=["Grip"],
                                                            mi="slot 1 tab: MI param PupilColour (one per pupil), slot 0 card stock, slot 2 ink"),
         "materials": [K.material(a, 0, "card stock", BOARD, 0.85), K.material(a, 1, "pupil tab (MI PupilColour)", CLOTH[0], 0.8), K.material(a, 2, "ink note", "2A2420", 0.7)],
         "objects": [K.obj(a, card_parts())], "sockets": [K.socket("Grip", (-0.045, 0, CH_ + 0.009), forward=(0, 0, 1), attach=((0, 0, 1), (0, -1, 0)))],
         "collision": [K.ucx_box(a, 0, (CW_, 0.006, CH_ + 0.018), (0, 0, (CH_ + 0.018) / 2))], "nanite": False}
    return K.finish(m)


def filled(seed=SEED):
    a = FILLED; C = []
    for k, n in enumerate(FILL, 1):
        for j in range(n):
            x, y, z = slot_loc(k, j)
            C += card_parts(x, y, z, "_B%d_%d" % (k, j))
    for q in C:
        if q["name"].startswith(("NoteHead", "NoteStem")):
            q["lod1"] = {"drop": True}
    cm = [K.material(a, 3, "card stock", BOARD, 0.85), K.material(a, 4, "pupil tabs", CLOTH[2], 0.8), K.material(a, 5, "ink notes", "2A2420", 0.7)]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="as Prop_YTM_CardShelf + 16 cards", tri_cap=CAPS[a], collision="as the shelf", state="static set dressing; gameplay uses shelf + SongCard",
                                                            cards="by box %s" % FILL),
         "materials": shelf_mats(a) + cm, "objects": [K.obj(a, shelf_parts()), K.obj(a + "_Cards", [dict(q, slot=q["slot"] + 3) for q in C], parent=a, role="16 song cards in the slots")],
         "sockets": [s for s in shelf_sockets() if not s["name"].startswith("SOCKET_Box")], "collision": shelf(seed)["collision"], "nanite": True}
    m["collision"] = [dict(c, name=c["name"].replace(SHELF, a)) for c in m["collision"]]
    return K.finish(m)


BL, SEAT_Z, DESK_Z = 1.4, 0.38, 0.62


def bench(seed=SEED):
    a = BENCH; P = []
    P += K.plain_lod1(K.box("Seat", (BL, 0.26, 0.035), (0, 0.18, SEAT_Z - 0.0175), 0))
    P += K.plain_lod1(K.box("Desk", (BL, 0.34, 0.03), (0, -0.16, DESK_Z), 0, rot=(-6, 0, 0)))
    P.append(K.box("Ledge", (BL, 0.03, 0.02), (0, -0.33, DESK_Z + 0.005), 0, bevel=False))
    for s in (-1, 1):
        x = s * (BL / 2 - 0.05)
        P.append(K.box("SeatLegs%s" % ("L" if s > 0 else "R"), (0.05, 0.22, SEAT_Z - 0.035), (x, 0.18, (SEAT_Z - 0.035) / 2), 0, bevel=False))
        P.append(K.box("DeskLegs%s" % ("L" if s > 0 else "R"), (0.05, 0.05, DESK_Z - 0.03), (x, -0.27, (DESK_Z - 0.03) / 2), 0, bevel=False))
        P.append(K.box("Runner%s" % ("L" if s > 0 else "R"), (0.05, 0.5, 0.05), (x, -0.04, 0.025), 0, bevel=False))
    P.append(K.box("Stretcher", (BL - 0.1, 0.04, 0.04), (0, 0.05, 0.2), 0, bevel=False))
    P.append(K.box("InkWellRail", (BL - 0.2, 0.06, 0.015), (0, -0.03, DESK_Z + 0.02), 1, bevel=False, lod1={"drop": True}))
    xs = [(i - 1) * 0.45 for i in range(SEATS)]
    socks = [K.socket("Seat_%d" % i, (x, 0.18, SEAT_Z), forward=(0, -1, 0)) for i, x in enumerate(xs)]
    socks += [K.socket("Slate_%d" % i, (x, -0.2, round(DESK_Z + 0.015 + 0.2 * math.tan(math.radians(6)) * 0.2, 4)), forward=(0, -1, 0)) for i, x in enumerate(xs)]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="1.4 m bench + desk, seat 0.38 m, desk 0.62 m", tri_cap=CAPS[a], collision="UCX seat + desk",
                                                            sockets=["Seat_0..2", "Slate_0..2"], code="GRADUATES_NEEDED 3"),
         "materials": [wood(a), K.material(a, 1, "worn rail (G66 sign board)", BOARD, 0.8)], "objects": [K.obj(a, P)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (BL, 0.3, SEAT_Z), (0, 0.18, SEAT_Z / 2)), K.ucx_box(a, 1, (BL, 0.36, DESK_Z + 0.03), (0, -0.16, (DESK_Z + 0.03) / 2))], "nanite": True}
    return K.finish(m)


def slate(seed=SEED):
    a = SLATE; W, D, T, F = 0.28, 0.2, 0.012, 0.018
    P = [K.box("Slate", (W - 2 * F + 0.004, D - 2 * F + 0.004, T * 0.6), (0, 0, T * 0.3), 1, bevel=False)]
    for i, (sx, sy, cx, cy) in enumerate(((W, F, 0, D / 2 - F / 2), (W, F, 0, -D / 2 + F / 2), (F, D - 2 * F, W / 2 - F / 2, 0), (F, D - 2 * F, -W / 2 + F / 2, 0))):
        P.append(K.box("Frame%d" % i, (sx, sy, T), (cx, cy, T / 2), 0, bevel=False))
    P.append(K.cyl("Chalk", "x", 0.005, 0.005, 0.06, (0.03, -D / 2 - 0.012, 0.005), 2, 6, lod1={"segments": 4}))
    P.append(K.cyl("CordHole", "y", 0.004, 0.004, F + 0.002, (0, D / 2 - F / 2, T / 2), 2, 6, lod1={"drop": True}))
    P.append(K.box("ChalkScrawl", (0.12, 0.003, 0.0006), (-0.02, 0.02, T * 0.6 + 0.0003), 2, bevel=False, lod1={"drop": True}))
    P.append(K.box("ChalkScrawl2", (0.08, 0.003, 0.0006), (-0.04, -0.01, T * 0.6 + 0.0003), 2, bevel=False, lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="0.28 x 0.2 m slate + chalk", tri_cap=CAPS[a], collision="UCX slate", sockets=["Grip", "Write"]),
         "materials": [wood(a, 0, "slate frame (G66 stall timber)"), K.material(a, 1, "slate", "2F3538", 0.75), K.material(a, 2, "chalk", "EEEBE2", 0.95)],
         "objects": [K.obj(a, P)],
         "sockets": [K.socket("Grip", (W / 2 - F / 2, 0, T / 2), forward=(1, 0, 0), attach=((0, 1, 0), (0, 0, 1))), K.socket("Write", (0, 0, T * 0.6), forward=(0, 0, 1))],
         "collision": [K.ucx_box(a, 0, (W, D + 0.03, T), (0, -0.012, T / 2))], "nanite": False,
         "off_centre_ok": "chalk lies against the front edge (-Y); origin = slate bottom centre"}
    return K.finish(m)


def candles(seed=SEED):
    a = CANDLES; r = K.rng(seed, a); P = []
    TW, TD, TT = 0.72, 0.14, 0.03
    P += K.plain_lod1(K.box("Tray", (TW, TD, TT), (0, 0, TT / 2), 0))
    for s in (-1, 1):
        P.append(K.box("Handle%s" % ("L" if s > 0 else "R"), (0.04, 0.06, 0.05), (s * (TW / 2 + 0.015), 0, 0.03), 0, bevel=False))
    flames = []
    for k in range(LESSONS):
        x = CAND_X0 + k * CAND_PITCH; h = round(0.11 + 0.06 * r.random(), 4); z0 = TT
        P.append(K.cyl("Holder%d" % k, "z", 0.032, 0.026, 0.018, (x, 0, z0 + 0.009), 0, 10, lod1={"segments": 6}))
        P.append(K.cyl("Wax%d" % k, "z", 0.019, 0.018, h, (x, 0, z0 + 0.018 + h / 2), 1, 10, lod1={"segments": 6}))
        P.append(K.lathe("Drip%d" % k, [(0.0195, z0 + 0.018 + h - 0.03), (0.022, z0 + 0.018 + h - 0.012), (0.0185, z0 + 0.018 + h)], (0, 0, 0), 1, 10, False, False, lod1={"drop": True}))
        P[-1]["centre"] = [round(x, 5), 0.0, 0.0]
        wick_z = z0 + 0.018 + h
        P.append(K.cyl("Wick%d" % k, "z", 0.0015, 0.0012, 0.01, (x, 0, wick_z + 0.005), 0, 4, lod1={"drop": True}))
        P.append(K.lathe("Flame%d" % k, [(0.001, wick_z + 0.006), (0.007, wick_z + 0.014), (0.005, wick_z + 0.026), (0.0006, wick_z + 0.04)], (0, 0, 0), 2, 8, True, False, lod1={"segments": 4}))
        P[-1]["centre"] = [round(x, 5), 0.0, 0.0]
        flames.append(K.socket("Flame_%d" % k, (round(x, 5), 0, round(wick_z + 0.012, 5)), forward=(0, 0, 1)))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="0.75 m tray, 6 candles", tri_cap=CAPS[a], collision="UCX tray + candle row", sockets=["Flame_0..5"],
                                                            code="LESSONS_PER_DAY 6: candle k lit while k < lessonsLeft()"),
         "materials": [wood(a), K.material(a, 1, "beeswax", "EFE2BE", 0.6), K.material(a, 2, "flame (emissive, masked by LitCount)", "FFB347", 0.4, glow=True)],
         "objects": [K.obj(a, P)], "sockets": flames,
         "collision": [K.ucx_box(a, 0, (TW + 0.07, TD, TT), (0, 0, TT / 2)), K.ucx_box(a, 1, (LESSONS * CAND_PITCH, 0.065, 0.2), (CAND_X0 + 2.5 * CAND_PITCH, 0, TT + 0.1))], "nanite": False}
    return K.finish(m)


def materials_manifest():
    lit = {"LitCount": "scalar 0..6 = SongSchool.lessonsLeft()", "CandleX0_cm": round(CAND_X0 * 100, 3), "CandlePitch_cm": round(CAND_PITCH * 100, 3),
           "FlameColour": "vector, linear", "EmissiveStrength": "scalar (nits-ish, 20 default)"}
    return {"schema": "bb-material-variants/1", "gap": "G116 (youtube-master 49939, PR #337 brew.school.SongSchool)", "status": "NOT READY",
            "candles": {"asset": CANDLES, "slot": "flame (slot 2)", "parent": "M_YTM_CandleFlame (UE: Masked, unlit/emissive)", "params": lit,
                        "graph": "k = floor((LocalPosition.X - CandleX0_cm) / CandlePitch_cm + 0.5); OpacityMask = (k < LitCount) ? 1 : 0; Emissive = FlameColour * EmissiveStrength * flicker(Time + k)",
                        "instances": {"MI_YTM_LessonCandles_Lit": {"LitCount": 6, "EmissiveStrength": 20, "FlameColour_srgb": "FFB347"},
                                      "MI_YTM_LessonCandles_Unlit": {"LitCount": 0, "EmissiveStrength": 0, "FlameColour_srgb": "FFB347"}},
                        "sockets": "SOCKET_Flame_k: spawn a small point light / ember VFX while k < LitCount; snuff from the highest k down as lessons are used"},
            "cards": {"asset": CARD, "slot": "tab (slot 1)", "params": {"PupilColour": "vector, one MI per pupil"},
                      "suggested_pupil_colours_srgb": CLOTH, "slots": "Prop_YTM_CardShelf SOCKET_Box<k>_Card<j>: k = SongSchool Card.box(), j = order in the box"}}


def assets(seed=SEED):
    return [shelf(seed), card(seed), filled(seed), bench(seed), slate(seed), candles(seed)]


SOCKETS = {SHELF: ["SOCKET_Box%d_Card%d" % (k, j) for k in range(1, 6) for j in range(4)] + ["SOCKET_Label_%d" % k for k in range(1, 6)] + ["SOCKET_Deck"],
           CARD: ["SOCKET_Grip"], FILLED: ["SOCKET_Label_%d" % k for k in range(1, 6)] + ["SOCKET_Deck"],
           BENCH: ["SOCKET_Seat_%d" % i for i in range(3)] + ["SOCKET_Slate_%d" % i for i in range(3)], SLATE: ["SOCKET_Grip", "SOCKET_Write"],
           CANDLES: ["SOCKET_Flame_%d" % k for k in range(6)]}


def extra_checks(A):
    S, C, F, Bn, Sl, Cd = (A[n] for n in (SHELF, CARD, FILLED, BENCH, SLATE, CANDLES))
    ss = {s["name"]: s["location"] for s in S["sockets"]}
    cards_in_filled = sum(1 for q in F["objects"][1]["parts"] if q["name"].startswith("Card_"))
    fl = sorted(s["location"][0] for s in Cd["sockets"])
    return [("5 boxes (TOP_BOX), 4 slots each", sum(1 for q in S["objects"][0]["parts"] if q["name"].endswith("_Floor")) == 5 and sum(1 for n in ss if n.startswith("SOCKET_Box")) == 20),
            ("box k plaque carries k pips", all(sum(1 for q in S["objects"][0]["parts"] if q["name"].startswith("Box%d_Pip" % k)) == k for k in range(1, 6))),
            ("card slots sit on the box floors, inside the walls", all(abs(v[2] - (SH + BX_T)) < 1e-9 and abs(v[1]) < BX_D / 2 - BX_T for n, v in ss.items() if n.startswith("SOCKET_Box"))),
            ("card fits the box (width) and shows above the rim", CW_ < BX_W - 2 * BX_T and CH_ > BX_H),
            ("filled snapshot holds 16 cards", cards_in_filled == 16, cards_in_filled),
            ("6 candles (LESSONS_PER_DAY), flames at the CandlePitch spacing from CandleX0", len(fl) == 6 and all(abs(fl[k] - (CAND_X0 + k * CAND_PITCH)) < 1e-9 for k in range(6))),
            ("3 seats (GRADUATES_NEEDED)", sum(1 for s in Bn["sockets"] if s["name"].startswith("SOCKET_Seat")) == 3),
            ("G66 palette reused (stall timber)", all(m["materials"][0]["hex"] == TIMBER for m in (S, Bn, Sl, Cd)))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); ap.add_argument("--materials"); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
    if o.materials:
        os.makedirs(o.materials, exist_ok=True)
        with open(os.path.join(o.materials, "YTM_G116.material_variants.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(materials_manifest(), f, indent=1); f.write("\n")
