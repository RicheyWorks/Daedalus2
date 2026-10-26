# SPDX-License-Identifier: MIT
"""G139 The Harbour Round (youtube-master 50117, buf-minigame-contest-20261019-youtube-master; PR #360 brew.round.HarbourRound,
STORY.md "Harbour jetty at the ark dock, a voice-entry staff UI (one row per voice: entry beat, interval, live clash marks)"),
blender-kit/v1 in the G66 stall style (palette via ytm_g116 / ytm_g66). The gull is a rigged character: gull_g139.py (bird_rig).
  Prop_YTM_Jetty      3.0 m chain section, 1.6 m wide, deck top 1.2 m above the pile feet. SOCKET_End_A (-Y) / SOCKET_End_B (+Y) at
                      the deck-top ends: the next section's End_A goes on this End_B. Two mooring posts (one per side) with cleats:
                      SOCKET_Mooring_L / _R, the G119 raft convention (a SOCKET_Mooring point on a post, 0.3 m above the deck it stands
                      on, forward = the side a line leaves from): tie Prop_Sky_Raft SOCKET_Mooring to either. UCX deck + piles + posts.
  Prop_YTM_VoiceStaff 1.2 x 0.62 m standing staff board: 4 rows (HarbourRound.MAX_VOICES; row 0 = the lead, HARBOUR_VOICES 3
                      needed) x 8 entry-beat columns, REUSING the G119 census-board peg system (sky_g119.grid_loc / peg_holes /
                      peg_sockets; peg mesh = Prop_Census_Peg): SOCKET_Peg_<r>_<c> (r 0-3 voice, c 0-7 entry delay in beats).
                      Interval per voice = the peg head MI colour (one per INTERVALS 0,3,4,5,7,8,9) + SOCKET_Row_<r> label at the
                      row's left (UE text: interval name). Stave lines behind each row; SOCKET_Clash (top strip, live clash marks).
Usage: python ytm_g139.py --out data/contest/ytm_g139.kit.json"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import ytm_g116, sky_g119 as S

SEED = 13939
JETTY, STAFF = "Prop_YTM_Jetty", "Prop_YTM_VoiceStaff"
VOICES, BEATS = 4, 8                       # HarbourRound.MAX_VOICES, entry-beat columns
INTERVALS = [0, 3, 4, 5, 7, 8, 9]          # HarbourRound.INTERVALS (semitones)
CAPS = {JETTY: 3500, STAFF: 3000}
SPEC = {"gap": "G139", "ask": "youtube-master 50117", "lod": "LOD0/1", "style": "G66 stall palette (ytm_g66)"}
TIMBER, BOARD, CLOTH = ytm_g116.TIMBER, ytm_g116.BOARD, ytm_g116.CLOTH
JL, JW, DECK = 3.0, 1.6, 1.2               # jetty length (Y), width, deck top
MOOR_UP = 0.3                              # G119: SOCKET_Mooring sits 0.3 m above the deck it stands on
SW, SH, ST, SLEG = 1.2, 0.62, 0.05, 0.75   # staff board width, height, thickness, leg lift
PX, PZ = 0.115, 0.12


def jetty(seed=SEED):
    a = JETTY; r = K.rng(seed, a); P = []
    n = 12
    for i in range(n):
        y = -JL / 2 + (i + 0.5) * JL / n
        P.append(K.box("Plank%02d" % i, (JW + r.uniform(-0.03, 0.03), JL / n - 0.02, 0.05), (round(r.uniform(-0.01, 0.01), 4), round(y, 4), DECK - 0.025), 0, bevel=False))
    for s in (-1, 1):
        P.append(K.box("Stringer%s" % ("L" if s < 0 else "R"), (0.1, JL, 0.14), (s * (JW / 2 - 0.15), 0, DECK - 0.12), 1, bevel=False))
        for k, y in enumerate((-JL / 2 + 0.25, JL / 2 - 0.25)):
            P.append(K.cyl("Pile%s%d" % ("L" if s < 0 else "R", k), "z", 0.1, 0.11, DECK - 0.05, (s * (JW / 2 - 0.15), y, (DECK - 0.05) / 2), 1, 8, lod1={"segments": 5}))
        P.append(K.box("Brace%s" % ("L" if s < 0 else "R"), (0.05, JL - 0.6, 0.08), (s * (JW / 2 - 0.08), 0, 0.55), 1, rot=(round(math.degrees(math.atan2(0.5, JL - 0.6)), 3), 0, 0), bevel=False))
    for s in (-1, 1):   # mooring posts on the deck edge, mid-section, with a cleat
        x = s * (JW / 2 - 0.06)
        P.append(K.cyl("MoorPost%s" % ("L" if s < 0 else "R"), "z", 0.075, 0.07, 0.55, (x, 0.0, DECK + 0.275), 0, 8, lod1={"segments": 5}))
        P.append(K.cyl("MoorCap%s" % ("L" if s < 0 else "R"), "z", 0.085, 0.085, 0.04, (x, 0.0, DECK + 0.57), 0, 8, lod1={"drop": True}))
        P.append(K.box("Cleat%s" % ("L" if s < 0 else "R"), (0.05, 0.26, 0.035), (x + s * 0.085, 0.0, DECK + MOOR_UP), 2, bevel=False))
        P.append(K.cyl("Coil%s" % ("L" if s < 0 else "R"), "z", 0.1, 0.1, 0.05, (x - s * 0.22, 0.35, DECK + 0.025), 3, 10, lod1={"drop": True}))
    socks = [K.socket("End_A", (0, -JL / 2, DECK), forward=(0, -1, 0)), K.socket("End_B", (0, JL / 2, DECK), forward=(0, 1, 0))]
    socks += [K.socket("Mooring_%s" % ("L" if s < 0 else "R"), (round(s * (JW / 2 - 0.06 + 0.11), 4), 0.0, DECK + MOOR_UP), forward=(s, 0, 0)) for s in (-1, 1)]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="3.0 x 1.6 m section, deck top 1.2 m", tri_cap=CAPS[a], collision="UCX deck + piles + posts",
                                                            sockets=["End_A", "End_B", "Mooring_L", "Mooring_R"], chain="End_A of the next section on End_B",
                                                            mooring="G119 convention: tie Prop_Sky_Raft SOCKET_Mooring to SOCKET_Mooring_L/R (0.3 m above the deck, forward = outboard)"),
         "materials": [K.material(a, 0, "jetty planks / posts (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "piles / stringers (wet timber)", "4E3A28", 0.9),
                       K.material(a, 2, "iron cleats", "3A3A3E", 0.5, metallic=0.7), K.material(a, 3, "rope coil", "C98A3A", 0.9)],
         "objects": [K.obj(a, [q for q in P if q["slot"] in (0, 1, 2)]), K.obj(a + "_Rope", [dict(q, slot=3) for q in P if q["slot"] == 3], parent=a, role="rope coils")],
         "sockets": socks,
         "collision": [K.ucx_box(a, 0, (JW, JL, 0.2), (0, 0, DECK - 0.1))] + [K.ucx_prism(a, 1 + i, "z", 0.11, DECK - 0.2, (s * (JW / 2 - 0.15), y, (DECK - 0.2) / 2))
                                                                               for i, (s, y) in enumerate((s, y) for s in (-1, 1) for y in (-JL / 2 + 0.25, JL / 2 - 0.25))]
                      + [K.ucx_prism(a, 5 + i, "z", 0.085, 0.59, (s * (JW / 2 - 0.06), 0.0, DECK + 0.295)) for i, s in enumerate((-1, 1))], "nanite": True,
         "off_centre_ok": "rope coils and brace sit off the axis; origin = deck centre under the pile feet"}
    m["objects"][0]["parts"] = [q for q in P if q["slot"] in (0, 1, 2)]
    return K.finish(m)


def staff_loc(r, c):
    return S.grid_loc(r, c, cols=BEATS, pitch_x=PX, pitch_z=PZ, top_z=SLEG + SH - 0.16, face_y=-ST / 2, x0=0.08)


def staff(seed=SEED):
    a = STAFF; P = []
    zc = SLEG + SH / 2
    P += K.plain_lod1(K.box("Board", (SW, ST, SH), (0, 0, zc), 0))
    for rr in range(VOICES):
        _, _, z = staff_loc(rr, 0)
        P.append(K.box("Stave%d" % rr, (SW - 0.32, 0.003, 0.006), (0.08, -ST / 2 - 0.0015, z), 2, bevel=False, lod1={"drop": True}))
        P.append(K.box("RowLabel%d" % rr, (0.16, 0.008, 0.07), (-SW / 2 + 0.11, -ST / 2 - 0.004, z), 1, bevel=False))
    P.append(K.box("ClashStrip", (SW - 0.32, 0.008, 0.05), (0.08, -ST / 2 - 0.004, SLEG + SH - 0.05), 1, bevel=False))
    for c in range(BEATS):    # beat ticks along the bottom edge
        x, _, _ = staff_loc(0, c)
        P.append(K.box("BeatTick%d" % c, (0.006, 0.003, 0.03 if c % 4 == 0 else 0.018), (x, -ST / 2 - 0.0015, SLEG + 0.04), 2, bevel=False, lod1={"drop": True}))
    locs = [("%d_%d" % (rr, c), staff_loc(rr, c)) for rr in range(VOICES) for c in range(BEATS)]
    P += S.peg_holes(locs, 2)
    for s in (-1, 1):
        P.append(K.box("Leg%s" % ("L" if s < 0 else "R"), (0.07, 0.07, SLEG + SH * 0.9), (s * (SW / 2 - 0.08), ST / 2 + 0.035, (SLEG + SH * 0.9) / 2), 0, bevel=False))
        P.append(K.box("Foot%s" % ("L" if s < 0 else "R"), (0.08, 0.5, 0.06), (s * (SW / 2 - 0.08), 0.06, 0.03), 0, bevel=False))
    socks = S.peg_sockets(locs)
    socks += [K.socket("Row_%d" % rr, (round(-SW / 2 + 0.11, 5), round(-ST / 2 - 0.0085, 5), staff_loc(rr, 0)[2]), forward=(0, -1, 0)) for rr in range(VOICES)]
    socks.append(K.socket("Clash", (0.08, round(-ST / 2 - 0.0085, 5), round(SLEG + SH - 0.05, 5)), forward=(0, -1, 0)))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="1.2 x 0.62 m board, 1.37 m tall", tri_cap=CAPS[a], collision="UCX board + legs",
                                                            sockets=["Peg_<r>_<c> x32", "Row_0..3", "Clash"], reuse="G119 peg system (sky_g119) + peg mesh Prop_Census_Peg",
                                                            code="MAX_VOICES 4 rows (row 0 lead), entry delay 0-7 beats by column; interval = peg MI colour",
                                                            peg_colours={str(iv): CLOTH[i % 4] if i < 4 else ["E8DCC4", "7FE3FF", "C4281C"][i - 4] for i, iv in enumerate(INTERVALS)}),
         "materials": [K.material(a, 0, "staff board (G66 stall timber)", TIMBER, 0.85), K.material(a, 1, "label strips (G66 sign board)", BOARD, 0.8), K.material(a, 2, "holes / stave ink", "2A2420", 0.85)],
         "objects": [K.obj(a, P)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (SW, ST + 0.08, SH), (0, 0.03, zc)), K.ucx_box(a, 1, (SW, 0.5, SLEG), (0, 0.06, SLEG / 2))], "nanite": True,
         "off_centre_ok": "feet reach back (+Y) for balance (as Prop_Census_Board); origin = under the board face"}
    return K.finish(m)


def assets(seed=SEED):
    return [jetty(seed), staff(seed)]


SOCKETS = {JETTY: ["SOCKET_End_A", "SOCKET_End_B", "SOCKET_Mooring_L", "SOCKET_Mooring_R"],
           STAFF: ["SOCKET_Peg_%d_%d" % (r, c) for r in range(4) for c in range(8)] + ["SOCKET_Row_%d" % r for r in range(4)] + ["SOCKET_Clash"]}


def extra_checks(A):
    J, V = A[JETTY], A[STAFF]; js = {s["name"]: s["location"] for s in J["sockets"]}; vs = {s["name"]: s for s in V["sockets"]}
    raft = S.raft(); rm = [s for s in raft["sockets"] if s["name"] == "SOCKET_Mooring"][0]["location"]; rdeck = 2 * S.LR + 0.08
    pegs = [vs["SOCKET_Peg_%d_%d" % (r, c)] for r in range(4) for c in range(8)]
    return [("jetty chains: End_A/B 3.0 m apart, level", abs(js["SOCKET_End_B"][1] - js["SOCKET_End_A"][1] - JL) < 1e-9 and js["SOCKET_End_A"][2] == js["SOCKET_End_B"][2] == DECK),
            ("mooring posts follow the G119 convention (0.3 m above own deck)", abs((rm[2] - rdeck) - MOOR_UP) < 1e-6 and all(abs(js[n][2] - DECK - MOOR_UP) < 1e-9 for n in ("SOCKET_Mooring_L", "SOCKET_Mooring_R"))),
            ("mooring sockets outboard of the deck edge", js["SOCKET_Mooring_L"][0] < -JW / 2 + 0.2 and js["SOCKET_Mooring_R"][0] > JW / 2 - 0.2),
            ("staff: 4 x 8 peg sockets via the G119 peg system", len(pegs) == 32 and all(p["forward"] == [0, 1, 0] or tuple(p["forward"]) == (0, 1, 0) for p in pegs)),
            ("pegs fit (pitch > peg head)", PX > 2 * 1.7 * S.PEG_R + 0.01 and PZ > 2 * 1.7 * S.PEG_R + 0.01),
            ("pegs on the face, clear of labels", all(abs(p["location"][1] + ST / 2) < 1e-9 and p["location"][0] > -SW / 2 + 0.2 and p["location"][0] < SW / 2 - 0.05 for p in pegs)),
            ("row 0 (lead) is the top row", vs["SOCKET_Peg_0_0"]["location"][2] > vs["SOCKET_Peg_3_0"]["location"][2]),
            ("7 interval colours (HarbourRound.INTERVALS)", len(V["spec"]["peg_colours"]) == 7)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
