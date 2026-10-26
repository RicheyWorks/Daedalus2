# SPDX-License-Identifier: MIT
"""G119 Island Biogeography (pythagoras 49944, pyth-g119-assets-20261019; code d54c7c9a com.daedalus.world.battlefield.IslandBiogeography,
quest q_island_census "Forty Species, One Raft at a Time"), blender-kit/v1. Islands reuse the sky-island tiles (not built here).
Keyed to the code: Settings.DEFAULT pool 40 species (40 pegs), goal 18 = THRIVING, FRAGILE at 75% of goal (13.5 -> 14), stones 3 rafts.
  Prop_Sky_Raft      3.0 m stepping-stone raft: 7 lashed logs, 2 cross beams with rope lashings, a 1.7 m mast flying a small diamond
                     kite sail on a tether. SOCKET_Mooring on the bow post (tie line / island anchor), SOCKET_Deck (stand point).
                     UCX deck + mast. Mesh slots M0 logs, M1 rope, M2 kite cloth.
  Prop_Census_Board  1.5 m standing tally board: 40 peg holes in 4 rows of 10 (SOCKET_Peg_00..39, species order row by row from
                     the top left, forward = into the board), a carved goal rail after peg 18 (THRIVING) and a notch after 14
                     (FRAGILE), header plaque SOCKET_Text (Vale's census line). UCX board + legs.
  Prop_Census_Peg    the peg, separate: origin = the tip that seats in the hole = the SOCKET_Peg_NN point; SOCKET_Grip on the head.
Usage: python sky_g119.py --out data/contest/sky_g119.kit.json"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K

SEED = 11919
RAFT, BOARD, PEG = "Prop_Sky_Raft", "Prop_Census_Board", "Prop_Census_Peg"
POOL, GOAL, ROWS, COLS = 40, 18, 4, 10
FRAGILE = math.ceil(0.75 * GOAL)           # 14
CAPS = {RAFT: 3500, BOARD: 4000, PEG: 200}
SPEC = {"gap": "G119", "ask": "pythagoras 49944", "lod": "LOD0/1", "code": "d54c7c9a IslandBiogeography"}
LOG, ROPE, CLOTH, BOARDW, DARK, RED = "7A5232", "D8C79A", "E8DCC4", "9A6B3F", "4A3A2A", "C4281C"
RL, NLOG, LR = 3.0, 7, 0.11                 # raft length (Y), logs, log radius
BW, BH, BT, LEG = 1.0, 0.8, 0.05, 0.7       # board width, height, thickness; legs lift the board bottom to 0.7 m (top 1.5 m)
PITCH_X, PITCH_Z = 0.085, 0.13
HOLE_R, PEG_R, PEG_IN = 0.012, 0.010, 0.03  # hole radius, peg radius, peg depth in the hole


def raft(seed=SEED):
    a = RAFT; r = K.rng(seed, a); P = []
    W = NLOG * 2 * LR
    for i in range(NLOG):
        x = -W / 2 + LR + 2 * LR * i; L = RL - r.uniform(0, 0.18); rr = LR * r.uniform(0.92, 1.0)
        P.append(K.cyl("Log%d" % i, "y", rr, rr * 0.94, L, (round(x, 4), round(r.uniform(-0.04, 0.04), 4), rr), 0, 10, lod1={"segments": 6}))
    for k, y in enumerate((-RL / 2 + 0.35, RL / 2 - 0.35)):
        P.append(K.box("Beam%d" % k, (W + 0.1, 0.12, 0.08), (0, y, 2 * LR + 0.04), 0, bevel=False))
        for i in range(0, NLOG, 2):
            x = -W / 2 + LR + 2 * LR * i
            P.append(K.cyl("Lash%d_%d" % (k, i), "y", 0.125, 0.125, 0.06, (round(x, 4), y, 0.125), 1, 8, lod1={"segments": 5}))
    deck = 2 * LR + 0.08
    P.append(K.cyl("Mast", "z", 0.04, 0.032, 1.7, (0, 0.2, deck + 0.85), 0, 8, lod1={"segments": 5}))
    P.append(K.box("MastFoot", (0.22, 0.22, 0.08), (0, 0.2, deck + 0.04), 0, bevel=False))
    P.append(K.cyl("Tether", "z", 0.006, 0.006, 0.55, (0, 0.38, deck + 1.83), 1, 4, rot=(-28, 0, 0), lod1={"drop": True}))
    kz, ky = deck + 2.25, 0.62
    P.append(K.slab("Kite", [(0, 0.38), (0.26, 0.05), (0, -0.42), (-0.26, 0.05)], 0.012, (0, ky, kz), 2, rot=(62, 0, 0)))
    P.append(K.box("KiteSpar", (0.5, 0.014, 0.014), (0, ky - 0.0, kz + 0.02), 0, rot=(62, 0, 0), bevel=False, lod1={"drop": True}))
    for j in range(3):   # tail bows
        P.append(K.slab("Bow%d" % j, [(-0.05, 0.02), (0.05, 0.02), (0.05, -0.02), (-0.05, -0.02)], 0.006, (0, round(ky - 0.12 - 0.12 * j, 4), round(kz - 0.32 - 0.16 * j, 4)), 2, rot=(62, 0, 25 * (-1) ** j), lod1={"drop": True}))
    by = -RL / 2 + 0.16
    P.append(K.cyl("BowPost", "z", 0.05, 0.045, 0.36, (0, by, deck + 0.18), 0, 8, lod1={"segments": 5}))
    P.append(K.cyl("BowCoil", "z", 0.07, 0.07, 0.05, (0, by, deck + 0.12), 1, 10, lod1={"drop": True}))
    socks = [K.socket("Mooring", (0, by, round(deck + 0.3, 4)), forward=(0, -1, 0)), K.socket("Deck", (0, -0.4, round(deck, 4)), forward=(0, -1, 0))]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="3.0 x 1.54 m raft, kite to 2.6 m", tri_cap=CAPS[a], collision="UCX deck + mast", sockets=["Mooring", "Deck"],
                                                            code_note="Settings.DEFAULT stones 3: the player places up to three rafts"),
         "materials": [K.material(a, 0, "lashed logs", LOG, 0.9), K.material(a, 1, "lashing rope", ROPE, 0.95), K.material(a, 2, "kite cloth", CLOTH, 0.85)],
         "objects": [K.obj(a, P)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (W, RL, deck), (0, 0, deck / 2)), K.ucx_prism(a, 1, "z", 0.05, 1.7, (0, 0.2, deck + 0.85))], "nanite": True,
         "off_centre_ok": "kite flies aft-high on its tether; origin = deck centre on the waterline (log bottoms)"}
    return K.finish(m)


def grid_loc(row, col, cols=COLS, pitch_x=PITCH_X, pitch_z=PITCH_Z, top_z=LEG + BH - 0.2, face_y=-BT / 2, x0=0.0):
    """the peg system (shared with G139 Prop_YTM_VoiceStaff): hole (row, col) on a board face, rows top down, cols left to right."""
    return (round(x0 - (cols - 1) / 2 * pitch_x + col * pitch_x, 5), round(face_y, 5), round(top_z - row * pitch_z, 5))


def peg_holes(locs, slot, prefix="Hole"):
    """countersunk hole rims proud of the face; LOD1 keeps a 4-sided rim."""
    return [K.cyl("%s%s" % (prefix, tag), "y", HOLE_R * 1.6, HOLE_R * 1.6, 0.003, (x, y - 0.0015, z), slot, 8, lod1={"segments": 4}) for tag, (x, y, z) in locs]


def peg_sockets(locs, prefix="Peg_"):
    """SOCKET_<prefix><tag> at the hole on the face, forward = into the board (+Y): seat Prop_Census_Peg's shank axis here."""
    return [K.socket(prefix + tag, loc, forward=(0, 1, 0)) for tag, loc in locs]


def peg_loc(i):
    return grid_loc(*divmod(i, COLS))


def board(seed=SEED):
    a = BOARD; P = []
    zc = LEG + BH / 2
    P += K.plain_lod1(K.box("Board", (BW, BT, BH), (0, 0, zc), 0))
    P.append(K.box("Header", (BW * 0.8, 0.012, 0.11), (0, -BT / 2 - 0.006, LEG + BH - 0.07), 1, bevel=False))
    for s in (-1, 1):
        P.append(K.box("Leg%s" % ("L" if s < 0 else "R"), (0.07, 0.07, LEG + BH * 0.9), (s * (BW / 2 - 0.08), BT / 2 + 0.035, (LEG + BH * 0.9) / 2), 0, bevel=False))
        P.append(K.box("Foot%s" % ("L" if s < 0 else "R"), (0.08, 0.5, 0.06), (s * (BW / 2 - 0.08), 0.06, 0.03), 0, bevel=False))
    locs = [("%02d" % i, peg_loc(i)) for i in range(POOL)]
    P += peg_holes(locs, 2)
    def mark(after, name, h):    # carved rail on the right of peg `after`
        row, col = divmod(after - 1, COLS); x, _, z = peg_loc(after - 1)
        return K.box(name, (0.008, 0.006, h), (round(x + PITCH_X / 2, 5), -BT / 2 - 0.003, z), 2 if name == "GoalRail" else 1, bevel=False)
    P.append(mark(GOAL, "GoalRail", PITCH_Z * 0.85)); P.append(mark(FRAGILE, "FragileNotch", PITCH_Z * 0.45))
    socks = peg_sockets(locs)
    socks.append(K.socket("Text", (0, round(-BT / 2 - 0.0125, 5), round(LEG + BH - 0.07, 5)), forward=(0, -1, 0)))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="1.0 x 0.8 m board, 1.5 m tall", tri_cap=CAPS[a], collision="UCX board + legs",
                                                            sockets=["Peg_00..39", "Text"], code_note="pool 40, goal 18 THRIVING (rail after peg 18), FRAGILE >= 14 (notch after peg 14)",
                                                            peg_order="row by row from the top left; peg i = i-th species present in the refuge census"),
         "materials": [K.material(a, 0, "board timber", BOARDW, 0.85), K.material(a, 1, "header plaque / fragile notch", "E4DDCF", 0.8), K.material(a, 2, "holes / goal rail", DARK, 0.9)],
         "objects": [K.obj(a, P)], "sockets": socks,
         "collision": [K.ucx_box(a, 0, (BW, BT + 0.08, BH), (0, 0.03, zc)), K.ucx_box(a, 1, (BW, 0.5, LEG), (0, 0.06, LEG / 2))], "nanite": True,
         "off_centre_ok": "feet reach back (+Y) for balance; origin = under the board face"}
    return K.finish(m)


def peg(seed=SEED):
    a = PEG; L = 0.09
    HR = PEG_R * 1.7; AZ = round(HR * math.cos(math.pi / 10), 6)   # 10-sided head: its flat edge rests on z=0
    P = [K.cyl("Shank", "y", PEG_R * 0.85, PEG_R, L, (0, round(PEG_IN - L / 2, 5), AZ), 0, 8, lod1={"segments": 6}),
         K.cyl("Head", "y", HR, HR, 0.018, (0, round(-(L - PEG_IN) - 0.009, 5), AZ), 1, 10, lod1={"segments": 6})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="9 cm peg + 3.4 cm head", tri_cap=CAPS[a], collision="none (UI-scale prop)", sockets=["Grip"],
                                                            seat="the shank runs PEG_IN = 3 cm past the origin along +Y (into the hole) and 6 cm out to the head; the shank axis is at z = 1.617 cm: put the axis point (0, 0, 0.01617) on SOCKET_Peg_NN with +Y along its forward"),
         "materials": [K.material(a, 0, "peg wood", "C9A46A", 0.8), K.material(a, 1, "peg head (species colour MI)", RED, 0.7)],
         "objects": [K.obj(a, P)], "sockets": [K.socket("Grip", (0, round(-(L - PEG_IN) - 0.018, 5), AZ), forward=(0, -1, 0))], "collision": [], "nanite": False,
         "off_centre_ok": "lies on its side on z=0; origin under the seat point (board face) of the shank axis"}
    return K.finish(m)


def assets(seed=SEED):
    return [raft(seed), board(seed), peg(seed)]


SOCKETS = {RAFT: ["SOCKET_Mooring", "SOCKET_Deck"], BOARD: ["SOCKET_Peg_%02d" % i for i in range(POOL)] + ["SOCKET_Text"], PEG: ["SOCKET_Grip"]}


def extra_checks(A):
    R, B, G = A[RAFT], A[BOARD], A[PEG]
    pegs = [s for s in B["sockets"] if s["name"].startswith("SOCKET_Peg_")]
    d = R["predicted"]["dimensions"]
    return [("raft about 3 m long", 2.9 <= d[1] <= 3.1, d), ("raft mooring socket on the bow", [s for s in R["sockets"] if s["name"] == "SOCKET_Mooring"][0]["location"][1] < -RL / 2 + 0.3),
            ("40 peg sockets = pool 40", len(pegs) == POOL and [s["name"] for s in pegs] == ["SOCKET_Peg_%02d" % i for i in range(POOL)]),
            ("pegs on the board face, inside the board", all(abs(s["location"][1] + BT / 2) < 1e-9 and abs(s["location"][0]) < BW / 2 - 0.05 and LEG < s["location"][2] < LEG + BH - 0.12 for s in pegs)),
            ("pegs do not touch (pitch > head diameter)", PITCH_X > 2 * 1.7 * PEG_R + 0.01),
            ("board about 1.5 m tall", abs(B["predicted"]["dimensions"][2] - 1.5) < 0.02, B["predicted"]["dimensions"]),
            ("goal rail after peg 18, fragile notch after peg 14", FRAGILE == 14 and any(q["name"] == "GoalRail" for q in B["objects"][0]["parts"])),
            ("peg shank fits the hole", PEG_R < HOLE_R), ("peg: 3 cm in, head outside", abs(G["predicted"]["bounds_max"][1] - PEG_IN) < 1e-6 and G["predicted"]["bounds_min"][1] < -0.06, G["predicted"]["bounds_min"])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
