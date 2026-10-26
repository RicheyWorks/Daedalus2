# SPDX-License-Identifier: MIT
"""G131 The Graduation Concert (youtube-master 50025, buf-minigame-contest-20261019-youtube-master; PR #348 brew.concert.GraduationConcert,
STORY.md "A stage on the homestead green, a chalk set-list board UI with keys drawn on a circle of fifths"), blender-kit/v1, G66 stall
style (palette read from ytm_g66.stall). Keyed to the code: SOLOS 5 + the choir closer; the three G116 graduates sing; fifths() 0..6 on 12 keys.
  Prop_YTM_GreenStage        3.0 x 2.0 m timber stage, 0.45 m deck, front steps, two back posts with bunting (G66 cloth colours).
                             SOCKET_Solo (front centre: the singer), SOCKET_Choir_0..4 (back row, the closer), SOCKET_Board (front left,
                             where the set-list board stands), SOCKET_String_L/R (post tops: Prop_YTM_LanternString chains from here).
                             UCX deck + steps + posts.
  Prop_YTM_SetListChalkboard REUSES the G18 chalkboard recipe (or_parlay.chalkboard, scaled 0.75 = 0.9 x 0.6 m) on a three-leg easel.
                             Chalk circle-of-fifths ring on the left of the slate: 12 key ticks, C at the top, clockwise by fifths
                             (SOCKET_Key_00..11 at the ticks, key k = k*7 mod 12 semitones), SOCKET_Fifths at the ring centre;
                             SOCKET_Text on the right for the set list (6 lines: 5 solos + choir). UCX easel box. Sidecar.
  Prop_YTM_LanternString     one 1.44 m chain segment (two span the stage): sagging rope + 4 paper lanterns. SOCKET_End_A (-X) and
                             SOCKET_End_B (+X) at the rope ends (B of one = A of the next), SOCKET_Lamp_0..3 at the lantern centres.
                             Lantern glow slot uses the G116 candle setup: one scalar LitCount, lantern k lit while k < LitCount;
                             MI_YTM_LanternString_Lit (4) / _Unlit (0). Overhead decor: no collision.
Usage: python ytm_g131.py --out data/contest/ytm_g131.kit.json [--materials <dir>]"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import ytm_g66, ytm_g116, or_parlay

SEED = 13131
STAGE, BOARD_A, STRING = "Prop_YTM_GreenStage", "Prop_YTM_SetListChalkboard", "Prop_YTM_LanternString"
SOLOS, CHOIR_SPOTS, KEYS, LAMPS = 5, 5, 12, 4
CAPS = {STAGE: 3500, BOARD_A: 2500, STRING: 2500}
SPEC = {"gap": "G131", "ask": "youtube-master 50025", "lod": "LOD0/1", "style": "G66 stall palette (ytm_g66)"}
TIMBER, SIGN, CLOTH = ytm_g116.TIMBER, ytm_g116.BOARD, ytm_g116.CLOTH
SW, SDP, SH = 3.0, 2.0, 0.45            # stage width, depth, deck height
POST_H = 2.6
SEG, SAG = 1.44, 0.22                   # lantern string segment span (two = the stage post spacing), sag
LAMP_X0, LAMP_PITCH = -0.54, 0.36
BS = 0.75                               # chalkboard scale (G18 1.2 x 0.8 -> 0.9 x 0.6)
BOARD_Z = 0.72                          # bottom of the board on the easel
RING_C, RING_R = (-0.2, 0.3), 0.19      # ring centre on the scaled board (x, z above board bottom), radius


def pennants(y, z_top, x0, x1, n, tag):
    P = [K.box("BuntCord%s" % tag, (x1 - x0, 0.008, 0.008), ((x0 + x1) / 2, y, z_top), 2, bevel=False, lod1={"drop": True})]
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n; sag = 0.06 * math.sin(math.pi * (i + 0.5) / n)
        P.append(K.slab("Pennant%s%02d" % (tag, i), [(-0.09, 0.0), (0.09, 0.0), (0.0, -0.22)], 0.006, (x, y, z_top - sag), i % 3, rot=(90, 0, 0)))
    return P


def stage(seed=SEED):
    a = STAGE; P = []
    P += K.plain_lod1(K.box("Deck", (SW, SDP, 0.06), (0, 0, SH - 0.03), 0))
    P.append(K.box("Skirt", (SW - 0.04, SDP - 0.04, SH - 0.06), (0, 0, (SH - 0.06) / 2), 1, bevel=False))
    for i in range(int(SW / 0.25)):
        P.append(K.box("Plank%02d" % i, (0.008, SDP - 0.02, 0.004), (-SW / 2 + 0.25 * (i + 1), 0, SH + 0.002), 0, bevel=False, lod1={"drop": True}))
    for k, (w, h, d) in enumerate(((1.0, 0.15, 0.3), (1.0, 0.3, 0.3))):
        P.append(K.box("Step%d" % k, (w, d, h), (0, -SDP / 2 - 0.45 + 0.3 * k, h / 2), 0, bevel=False))
    for s in (-1, 1):
        x = s * (SW / 2 - 0.06)
        P.append(K.box("Post%s" % ("L" if s < 0 else "R"), (0.1, 0.1, POST_H), (x, SDP / 2 - 0.06, POST_H / 2), 0, bevel=False))
        P.append(K.box("PostCap%s" % ("L" if s < 0 else "R"), (0.14, 0.14, 0.04), (x, SDP / 2 - 0.06, POST_H + 0.02), 0, bevel=False, lod1={"drop": True}))
        P.append(K.box("FrontPost%s" % ("L" if s < 0 else "R"), (0.08, 0.08, 1.1), (x, -SDP / 2 + 0.05, SH + 0.55), 0, bevel=False))
    P.append(K.box("BackRail", (SW - 0.2, 0.06, 0.08), (0, SDP / 2 - 0.06, POST_H - 0.12), 0, bevel=False))
    B = pennants(SDP / 2 - 0.06, POST_H - 0.2, -SW / 2 + 0.1, SW / 2 - 0.1, 12, "Back")
    for s_ in (-1, 1):   # side runs along Y, front post top to back post, pennants turned to face sideways
        x = s_ * (SW / 2 - 0.06); tag = "Side%s" % ("L" if s_ < 0 else "R")
        for q in pennants(0, SH + 1.05, -SDP / 2 + 0.12, SDP / 2 - 0.12, 6, tag):
            if q["shape"] == "slab":
                q = dict(q, centre=[x, q["centre"][0], q["centre"][2]], rot=[90, 0, 90])
            else:
                q = dict(q, centre=[x, 0, q["centre"][2]], size=[0.008, SDP - 0.24, 0.008])
            B.append(q)
    socks = [K.socket("Solo", (0, -SDP / 2 + 0.55, SH), forward=(0, -1, 0))]
    socks += [K.socket("Choir_%d" % i, (round(-1.0 + 0.5 * i, 4), SDP / 2 - 0.45, SH), forward=(0, -1, 0)) for i in range(CHOIR_SPOTS)]
    socks.append(K.socket("Board", (-SW / 2 + 0.45, -SDP / 2 + 0.4, SH), forward=(0.5, -1, 0)))
    socks += [K.socket("String_%s" % ("L" if s < 0 else "R"), (s * (SW / 2 - 0.06), SDP / 2 - 0.06, POST_H), forward=(0, -1, 0)) for s in (-1, 1)]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="3.0 x 2.0 m, deck 0.45 m, posts 2.6 m", tri_cap=CAPS[a], collision="UCX deck + steps + posts",
                                                            sockets=["Solo", "Choir_0..4", "Board", "String_L/R"], code="SOLOS 5 + choir closer"),
         "materials": [K.material(a, 0, "stage timber (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "skirt boards (G66 sign board)", SIGN, 0.8),
                       K.material(a, 2, "bunting cloth A", CLOTH[0], 0.9), K.material(a, 3, "bunting cloth B", CLOTH[1], 0.9), K.material(a, 4, "bunting cloth C", CLOTH[2], 0.9)],
         "objects": [K.obj(a, P), K.obj(a + "_Bunting", [dict(q, slot=q["slot"] + 2) for q in B], parent=a, role="bunting")],
         "sockets": socks,
         "collision": [K.ucx_box(a, 0, (SW, SDP, SH), (0, 0, SH / 2)), K.ucx_box(a, 1, (1.0, 0.6, 0.3), (0, -SDP / 2 - 0.3, 0.15)),
                       K.ucx_box(a, 2, (0.1, 0.1, POST_H), (-SW / 2 + 0.06, SDP / 2 - 0.06, POST_H / 2)), K.ucx_box(a, 3, (0.1, 0.1, POST_H), (SW / 2 - 0.06, SDP / 2 - 0.06, POST_H / 2))],
         "nanite": True, "off_centre_ok": "front steps reach out of the deck (-Y); origin = deck centre on the ground"}
    return K.finish(m)


def key_tick(k):
    ang = math.radians(90 - 30 * k)           # C at the top, clockwise by fifths (viewer side = -Y, so +X is the viewer's right)
    return RING_C[0] + RING_R * math.cos(ang), RING_C[1] + RING_R * math.sin(ang), ang


def board(seed=SEED):
    a = BOARD_A; g = or_parlay.chalkboard(seed)
    P = ytm_g66.shift(g["objects"][0]["parts"], (0, 0, BOARD_Z), scale=BS)
    slate_y = (0.005 - 0.01) * BS - 0.0012     # just proud of the scaled slate face
    for k in range(KEYS):
        x, z, ang = key_tick(k); big = k % 3 == 0
        P.append(K.box("KeyTick%02d" % k, (0.012 if big else 0.008, 0.002, 0.04 if big else 0.026), (round(x, 5), slate_y, round(BOARD_Z + z, 5)), 2, rot=(0, round(90 - math.degrees(ang), 3), 0), bevel=False))
    seg = 24
    for i in range(seg):
        a0 = 2 * math.pi * (i + 0.5) / seg
        P.append(K.box("Ring%02d" % i, (2 * math.pi * (RING_R - 0.03) / seg * 0.9, 0.002, 0.005), (round(RING_C[0] + (RING_R - 0.03) * math.cos(a0), 5), slate_y, round(BOARD_Z + RING_C[1] + (RING_R - 0.03) * math.sin(a0), 5)), 2,
                       rot=(0, round(-math.degrees(a0) + 90 - 90, 3), 0), bevel=False, lod1={"drop": True}))
    for ln in range(SOLOS + 1):
        P.append(K.box("SetLine%d" % ln, (0.3, 0.002, 0.004), (0.2, slate_y, round(BOARD_Z + 0.5 - 0.075 * ln, 5)), 2, bevel=False, lod1={"drop": True}))
    for s in (-1, 1):   # easel: two front legs splayed, one back leg
        P.append(K.box("Leg%s" % ("L" if s < 0 else "R"), (0.04, 0.04, 1.5), (s * 0.36, -0.06, 0.755), 0, rot=(-6, s * -8, 0), bevel=False))
    P.append(K.box("LegBack", (0.04, 0.04, 1.45), (0, 0.32, 0.725), 0, rot=(14, 0, 0), bevel=False))
    P.append(K.box("Ledge", (0.84, 0.08, 0.025), (0, -0.07, BOARD_Z - 0.012), 0, bevel=False))
    socks = [K.socket("Text", (0.2, round(slate_y - 0.002, 5), round(BOARD_Z + 0.32, 5)), forward=(0, -1, 0)),
             K.socket("Fifths", (RING_C[0], round(slate_y - 0.002, 5), round(BOARD_Z + RING_C[1], 5)), forward=(0, -1, 0))]
    socks += [K.socket("Key_%02d" % k, (round(key_tick(k)[0], 5), round(slate_y - 0.002, 5), round(BOARD_Z + key_tick(k)[1], 5)), forward=(0, -1, 0)) for k in range(KEYS)]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="0.9 x 0.6 m board on a 1.45 m easel", tri_cap=CAPS[a], collision="UCX easel",
                                                            reuse="G18 or_parlay.chalkboard x0.75", sockets=["Text", "Fifths", "Key_00..11"],
                                                            keys={"Key_%02d" % k: (k * 7) % 12 for k in range(KEYS)}, key_note="semitones above C: clockwise by fifths, C at the top",
                                                            text_area_m=[round(0.42 * 1, 3), 0.42], code="SOLOS 5 + choir: 6 set lines; fifths() = ring steps 0..6"),
         "materials": [dict(x, asset=a) for x in g["materials"]], "objects": [K.obj(a, P)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (0.95, 0.5, BOARD_Z + 0.62), (0, 0.12, (BOARD_Z + 0.62) / 2))], "nanite": True,
         "off_centre_ok": "easel rear leg reaches back (+Y); origin = under the board face so SOCKET_Board on the stage places the face"}
    return K.finish(m)


def rope_z(x):
    u = x / (SEG / 2)
    return -SAG * (1 - u * u)


def lantern_string(seed=SEED):
    a = STRING; P = []; n = 12
    for i in range(n):
        x0 = -SEG / 2 + SEG * i / n; x1 = x0 + SEG / n; z0, z1 = rope_z(x0), rope_z(x1)
        L = math.hypot(x1 - x0, z1 - z0); ang = math.degrees(math.atan2(z1 - z0, x1 - x0))
        P.append(K.box("Rope%02d" % i, (L + 0.004, 0.012, 0.012), ((x0 + x1) / 2, 0, (z0 + z1) / 2), 0, rot=(0, round(-ang, 4), 0), bevel=False))
    socks = [K.socket("End_A", (-SEG / 2, 0, 0), forward=(-1, 0, 0)), K.socket("End_B", (SEG / 2, 0, 0), forward=(1, 0, 0))]
    for k in range(LAMPS):
        x = LAMP_X0 + k * LAMP_PITCH; zt = rope_z(x); zc = zt - 0.07 - 0.11
        P.append(K.box("Hanger%d" % k, (0.004, 0.004, 0.07), (x, 0, zt - 0.035), 0, bevel=False, lod1={"drop": True}))
        P.append(K.cyl("CapTop%d" % k, "z", 0.035, 0.035, 0.012, (x, 0, zc + 0.104), 0, 8, lod1={"segments": 6}))
        P.append(K.lathe("Lantern%d" % k, [(0.03, -0.1), (0.075, -0.06), (0.085, 0.0), (0.075, 0.06), (0.03, 0.1)], (x, 0, zc), 2, 12, True, True, lod1={"segments": 6}))
        P.append(K.cyl("CapBot%d" % k, "z", 0.032, 0.032, 0.012, (x, 0, zc - 0.104), 0, 8, lod1={"segments": 6}))
        for r_ in (-0.05, 0.05):
            P.append(K.lathe("Rib%d%s" % (k, "a" if r_ < 0 else "b"), [(0.0815, r_ - 0.004), (0.0825, r_), (0.0815, r_ + 0.004)], (x, 0, zc), 1, 12, False, False, lod1={"drop": True}))
        socks.append(K.socket("Lamp_%d" % k, (round(x, 5), 0, round(zc, 5)), forward=(0, 0, -1)))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="1.44 m chain segment, 0.22 m sag, 4 lanterns", tri_cap=CAPS[a], collision="none (overhead decor)",
                                                            sockets=["End_A", "End_B", "Lamp_0..3"], chain="place the next segment's SOCKET_End_A on this SOCKET_End_B; two segments span Prop_YTM_GreenStage SOCKET_String_L..R",
                                                            mi="glow slot 2 driven by LitCount (as G116 candles)"),
         "materials": [K.material(a, 0, "rope / lantern caps (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "lantern ribs", "5A4632", 0.8),
                       K.material(a, 2, "paper lantern glow (emissive, LitCount)", "F2B25C", 0.7, glow=True)],
         "objects": [K.obj(a, P)], "sockets": socks, "collision": [], "nanite": False, "off_centre_ok": "origin = bottom centre (lowest lantern); the chain runs through SOCKET_End_A/B at the rope ends"}
    return K.finish(m)


def ground(m):
    """shift parts, sockets and collision so the lowest predicted vertex is exactly z=0, then re-finish."""
    dz = -m["predicted"]["bounds_min"][2]
    if abs(dz) < 1e-9:
        return m
    for o in m["objects"]:
        for q in o["parts"]:
            q["centre"] = [q["centre"][0], q["centre"][1], round(q["centre"][2] + dz, 6)]
    for s_ in m["sockets"]:
        s_["location"] = [s_["location"][0], s_["location"][1], round(s_["location"][2] + dz, 6)]
    for c in m["collision"]:
        c["centre"] = [c["centre"][0], c["centre"][1], round(c["centre"][2] + dz, 6)]
    for k in ("predicted",):
        m.pop(k, None)
    return K.finish(m)


def materials_manifest():
    base = ytm_g116.materials_manifest()["candles"]
    return {"schema": "bb-material-variants/1", "gap": "G131 (youtube-master 50025, PR #348 brew.concert.GraduationConcert)", "status": "NOT READY",
            "lanterns": {"asset": STRING, "slot": "paper lantern glow (slot 2)", "parent": "M_YTM_CandleFlame (G116 master, reused)",
                         "params": {"LitCount": "scalar 0..4 lanterns lit (from -X)", "CandleX0_cm": round(LAMP_X0 * 100, 3), "CandlePitch_cm": round(LAMP_PITCH * 100, 3),
                                    "FlameColour": "vector, linear", "EmissiveStrength": "scalar"},
                         "graph": base["graph"], "note": "same master and graph as the G116 lesson candles; paper is opaque, so OpacityMask switches the glow to the unlit paper colour instead of hiding it (static switch UnlitShowsBase=1)",
                         "instances": {"MI_YTM_LanternString_Lit": {"LitCount": 4, "EmissiveStrength": 8, "FlameColour_srgb": "F2B25C", "UnlitShowsBase": 1},
                                       "MI_YTM_LanternString_Unlit": {"LitCount": 0, "EmissiveStrength": 0, "FlameColour_srgb": "F2B25C", "UnlitShowsBase": 1}},
                         "sockets": "SOCKET_Lamp_k: warm point light while k < LitCount; light them all when the choir closes"}}


def assets(seed=SEED):
    return [stage(seed), ground(board(seed)), ground(lantern_string(seed))]


SOCKETS = {STAGE: ["SOCKET_Solo"] + ["SOCKET_Choir_%d" % i for i in range(5)] + ["SOCKET_Board", "SOCKET_String_L", "SOCKET_String_R"],
           BOARD_A: ["SOCKET_Text", "SOCKET_Fifths"] + ["SOCKET_Key_%02d" % k for k in range(12)],
           STRING: ["SOCKET_End_A", "SOCKET_End_B"] + ["SOCKET_Lamp_%d" % k for k in range(4)]}


def extra_checks(A):
    S, B, L = A[STAGE], A[BOARD_A], A[STRING]
    ss = {s["name"]: s["location"] for s in S["sockets"]}; bs = {s["name"]: s["location"] for s in B["sockets"]}; ls = {s["name"]: s["location"] for s in L["sockets"]}
    ga = ss["SOCKET_String_R"][0] - ss["SOCKET_String_L"][0]
    keys = [bs["SOCKET_Key_%02d" % k] for k in range(12)]
    d = [math.hypot(k[0] - bs["SOCKET_Fifths"][0], k[2] - bs["SOCKET_Fifths"][2]) for k in keys]
    return [("stage sockets: 1 solo + 5 choir on the deck", all(abs(v[2] - SH) < 1e-9 for n, v in ss.items() if n.startswith(("SOCKET_Solo", "SOCKET_Choir"))) and sum(1 for n in ss if n.startswith("SOCKET_Choir")) == 5),
            ("two lantern segments span the stage posts", abs(2 * SEG - ga) < 0.05, ga),
            ("string end sockets 1.44 m apart, level (chainable)", abs(ls["SOCKET_End_B"][0] - ls["SOCKET_End_A"][0] - SEG) < 1e-9 and ls["SOCKET_End_A"][2] == ls["SOCKET_End_B"][2] > 0.4),
            ("lantern sockets at the LitCount pitch", all(abs(ls["SOCKET_Lamp_%d" % k][0] - (LAMP_X0 + k * LAMP_PITCH)) < 1e-9 for k in range(4))),
            ("12 key sockets on one ring around SOCKET_Fifths", max(d) - min(d) < 1e-4, d[:2]),
            ("C at the top, G (7) clockwise to the viewer's right", keys[0][2] > keys[6][2] and keys[1][0] > keys[0][0] and B["spec"]["keys"]["Key_01"] == 7),
            ("chalkboard reuses the G18 recipe (scaled frame parts)", sum(1 for q in B["objects"][0]["parts"] if q["name"].startswith("Frame")) == 4 and B["materials"][1]["hex"] == or_parlay.SLATE),
            ("text socket on the slate, right of the ring", bs["SOCKET_Text"][0] > bs["SOCKET_Fifths"][0] + RING_R),
            ("G66 palette reused", S["materials"][0]["hex"] == TIMBER and L["materials"][0]["hex"] == TIMBER)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); ap.add_argument("--materials"); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
    if o.materials:
        os.makedirs(o.materials, exist_ok=True)
        with open(os.path.join(o.materials, "YTM_G131.material_variants.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(materials_manifest(), f, indent=1); f.write("\n")
