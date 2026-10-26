# SPDX-License-Identifier: MIT
"""G66 Youtube Master Island trader stalls (youtube-master 49274, buf-minigame-contest-20261019-youtube-master), blender-kit/v1.
One modular stall generator, stall(asset, trader, cloth, goods_fn): the same timber frame (1.6 x 0.9 m counter at 0.94 m, four posts,
sloped cloth canopy with a front valance, blank hanging sign board) + one goods module per trader on the counter.
  Prop_YTM_Stall_Rope   Pell          rope coils on the counter + one hanging from a peg
  Prop_YTM_Stall_Stone  Quarry Ida    three blank choir stones = the G53 Prop_YTM_ChoirStone recipe scaled to 0.32 with the
                                      song groove left off (they are blanks: choir_stone_blank) + mallet and chisel
  Prop_YTM_Stall_Eggs   Hen-wife Mora REUSES the WZ egg nest recipe (wz_eggs.nest, Prop_WZ_EggNest) as the egg basket + two groat sacks
  Prop_YTM_Stall_Fish   Fisher Dov    drying rack (A-frame poles, crossbar, five hanging fish) + a fish crate
Sockets: SOCKET_Sign (front face of the sign board: UE puts the trader name there), SOCKET_Goods (counter top centre). UCX counter + posts.
Frame slots M0 timber, M1 canopy cloth (per-trader colour), M2 sign board; goods on child objects with their own slots.
Same kit style as G33 (bevelled kitlib parts, origin bottom centre, sidecars). Usage: python ytm_g66.py --out data/contest/ytm_g66.kit.json"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import wz_eggs, ytm_g53

SEED = 6666
TRADERS = {"Rope": ("Pell", "C98A3A"), "Stone": ("Quarry Ida", "6E7F99"), "Eggs": ("Hen-wife Mora", "E3C25A"), "Fish": ("Fisher Dov", "3F8A8C")}
NAMES = {k: "Prop_YTM_Stall_" + k for k in TRADERS}
CAPS = {n: 4500 for n in NAMES.values()}
SOCKETS = {n: ["SOCKET_Sign", "SOCKET_Goods"] for n in NAMES.values()}
SPEC = {"gap": "G66", "ask": "youtube-master 49274", "lod": "LOD0/1"}
CW, CD, CT = 1.6, 0.9, 0.94                 # counter width, depth, top
SIGN = (0, -CD / 2 - 0.1, 1.78)


def shift(parts, d, slot_map=None, scale=1.0):
    out = []
    for q in parts:
        q = dict(q, centre=[q["centre"][i] * scale + d[i] for i in range(3)])
        if scale != 1.0:
            assert q["shape"] == "box", q["shape"]
            q["size"] = [v * scale for v in q["size"]]
        if slot_map:
            q["slot"] = slot_map[q["slot"]]
        out.append(q)
    return out


def ring(name, R, r, centre, slot, lod1=None):
    prof = [(R + r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in range(-90, 271, 60)]
    return K.lathe(name, prof, centre, slot, 16, cap_bottom=False, cap_top=False, lod1=lod1 if lod1 is not None else {"segments": 8})


def frame(a):
    P = K.plain_lod1(K.box("Counter", (CW, CD, 0.12), (0, 0, CT - 0.06), 0))
    P.append(K.box("CounterFront", (CW - 0.06, 0.04, CT - 0.2), (0, -CD / 2 + 0.03, (CT - 0.2) / 2 + 0.06), 0, bevel=False))
    P.append(K.box("Shelf", (CW - 0.1, CD - 0.1, 0.04), (0, 0, 0.18), 0, bevel=False))
    for i, (x, y, h) in enumerate(((-CW / 2 + 0.05, -CD / 2 + 0.05, 1.98), (CW / 2 - 0.05, -CD / 2 + 0.05, 1.98), (-CW / 2 + 0.05, CD / 2 - 0.05, 2.16), (CW / 2 - 0.05, CD / 2 - 0.05, 2.16))):
        P.append(K.box("Post%d" % i, (0.08, 0.08, h), (x, y, h / 2), 0, bevel=False))   # thin members: plain at both LODs
    tilt = math.degrees(math.atan2(0.18, CD - 0.1))
    P += K.plain_lod1(K.box("Canopy", (CW + 0.2, CD + 0.3, 0.04), (0, -0.02, 2.09), 1, rot=(round(-tilt, 3), 0, 0)))
    P.append(K.box("Valance", (CW + 0.2, 0.02, 0.16), (0, -(CD + 0.3) / 2 - 0.02, 1.93), 1, bevel=False))
    P += K.plain_lod1(K.box("SignBoard", (0.9, 0.04, 0.26), (SIGN[0], SIGN[1] + 0.02 + 0.001, SIGN[2]), 2))
    for s in (-1, 1):
        P.append(K.cyl("SignCord%s" % ("L" if s < 0 else "R"), "z", 0.006, 0.006, 0.1, (s * 0.38, SIGN[1] + 0.02, SIGN[2] + 0.18), 0, 4, lod1={"drop": True}))
    return P


def goods_rope(a, rr):
    mats = [K.material(a, 3, "rope", "9C7A4A", 0.9), K.material(a, 4, "tarred rope", "5E4630", 0.85), K.material(a, 5, "iron peg", "3A3A3E", 0.5, metallic=0.7)]
    P = []
    for c, x in enumerate((-0.45, 0.0, 0.45)):
        for k in range(3):
            P.append(ring("Coil%d_%d" % (c, k), 0.13 - 0.01 * k, 0.022, (x + rr.uniform(-0.01, 0.01), 0.02, CT + 0.022 + 0.04 * k), 3 if c != 1 else 4, lod1={"segments": 8} if k != 1 else {"drop": True}))
    P.append(K.cyl("Peg", "y", 0.012, 0.012, 0.12, (CW / 2 - 0.05, CD / 2 - 0.15, 1.55), 5, 6, lod1={"segments": 4}))
    P.append(ring("HangCoil", 0.11, 0.02, (CW / 2 - 0.05, CD / 2 - 0.17, 1.45), 3, lod1={"segments": 8}))
    P[-1]["rot"] = [90, 0, 0]
    return mats, [(a + "_Goods", P)]


def goods_stone(a, rr):
    mats = [K.material(a, 3, "blank choir stone (YTM_Stone)", "8C8C94", 0.85), K.material(a, 4, "plinth", "6E6E76", 0.9), K.material(a, 5, "mallet / chisel", "5A4028", 0.8)]
    src = [q for q in ytm_g53.stone()["objects"][0]["parts"] if not q["name"].startswith(("Groove", "Note"))]   # blank: no song groove yet
    P = []
    for i, x in enumerate((-0.48, 0.0, 0.48)):
        P += [dict(q, name="Blank%d_%s" % (i, q["name"])) for q in shift(src, (x, 0.05 * (i % 2), CT), {0: 3, 2: 4}, scale=0.32)]
    P += K.plain_lod1(K.box("MalletHead", (0.12, 0.07, 0.07), (0.2, -0.3, CT + 0.035), 5))
    P.append(K.box("MalletShaft", (0.02, 0.22, 0.02), (0.2, -0.2, CT + 0.035), 5, bevel=False))
    P.append(K.box("Chisel", (0.16, 0.018, 0.018), (-0.25, -0.32, CT + 0.009), 5, rot=(0, 0, 20), bevel=False))
    return mats, [(a + "_Goods", P)]


def goods_eggs(a, rr):
    n = wz_eggs.nest()                                          # REUSE: Prop_WZ_EggNest recipe as the egg basket
    nm = [K.material(a, 3 + i, "egg nest " + m["colour"], m["hex"], m["roughness"], m["metallic"]) for i, m in enumerate(n["materials"])]
    mats = nm + [K.material(a, 6, "groat sack", "C8B48C", 0.95), K.material(a, 7, "groats", "D9C27A", 0.9)]
    nest = [dict(q, name="Nest_" + q["name"]) for q in shift(n["objects"][0]["parts"], (-0.32, 0, CT), {0: 3, 1: 4, 2: 5})]
    G = []
    for i, x in enumerate((0.3, 0.6)):
        h = 0.3 - 0.06 * i
        G.append(K.lathe("Sack%d" % i, [(0.12, 0), (0.135, h * 0.3), (0.125, h * 0.7), (0.09, h * 0.9), (0.1, h)], (x, 0.08 - 0.1 * i, CT), 6, 10, cap_bottom=True, cap_top=False, lod1={"segments": 6}))
        G.append(K.cyl("Groats%d" % i, "z", 0.095, 0.08, 0.02, (x, 0.08 - 0.1 * i, CT + h - 0.012), 7, 10, lod1={"segments": 6}))
    return mats, [(a + "_Goods", nest), (a + "_Groats", G)]


def goods_fish(a, rr):
    mats = [K.material(a, 3, "rack poles / crate", "8A6A45", 0.85), K.material(a, 4, "fish", "A9B6BF", 0.35, metallic=0.2), K.material(a, 5, "twine", "D2C29A", 0.9)]
    P = []; top = CT + 0.62
    for s in (-1, 1):
        for d in (-1, 1):
            P.append(K.cyl("Pole%s%s" % ("LR"[s > 0], "FB"[d > 0]), "z", 0.015, 0.015, 0.66, (s * 0.62, d * 0.1, CT + 0.31), 3, 6, rot=(round(d * 9, 2), 0, 0), lod1={"segments": 4}))
    P.append(K.cyl("Crossbar", "x", 0.016, 0.016, 1.34, (0, 0, top), 3, 6, lod1={"segments": 4}))
    for i in range(5):
        x = -0.48 + 0.24 * i; L = 0.2 + rr.uniform(-0.03, 0.03)
        P.append(K.cyl("Line%d" % i, "z", 0.003, 0.003, 0.08, (x, 0, top - 0.04), 5, 4, lod1={"drop": True}))
        P.append(K.lathe("Fish%d" % i, [(0.001, 0), (0.02, 0.03), (0.032, 0.09), (0.028, L * 0.75), (0.008, L * 0.9), (0.03, L)], (x, 0, top - 0.08 - L), 4, 8,
                         cap_bottom=False, cap_top=True, lod1={"segments": 5}))
    P += K.plain_lod1(K.box("Crate", (0.4, 0.28, 0.12), (0.45, -0.22, CT + 0.06), 3))
    for k in range(3):
        P.append(K.box("CrateFish%d" % k, (0.26, 0.05, 0.03), (0.45, -0.3 + 0.07 * k, CT + 0.135), 4, rot=(0, 0, round(rr.uniform(-8, 8), 2)), lod1={"drop": k == 1}))
    return mats, [(a + "_Goods", P)]


GOODS = {"Rope": goods_rope, "Stone": goods_stone, "Eggs": goods_eggs, "Fish": goods_fish}


def stall(key, seed=SEED):
    a = NAMES[key]; trader, cloth = TRADERS[key]; rr = K.rng(seed, a)
    mats = [K.material(a, 0, "stall timber", "7A5A3A", 0.85), K.material(a, 1, "canopy cloth (%s)" % trader, cloth, 0.9), K.material(a, 2, "sign board (blank: name via SOCKET_Sign)", "D8C9A8", 0.8)]
    gm, objs = GOODS[key](a, rr)
    m = {"asset": a, "kind": "Prop", "seed": seed, "trader": trader, "spec": dict(SPEC, size_m="1.6 x 0.9 m counter, ~2.2 m tall", tri_cap=CAPS[a], collision="UCX counter + posts",
         sockets=["Sign", "Goods"], goods=GOODS[key].__name__, trader=trader),
         "materials": mats + gm, "objects": [K.obj(a, frame(a))] + [K.obj(n, p, parent=a, role="goods") for n, p in objs],
         "sockets": [K.socket("Sign", SIGN), K.socket("Goods", (0, 0, CT))],
         "collision": [K.ucx_box(a, 0, (CW, CD, CT), (0, 0, CT / 2))] + [K.ucx_box(a, 1 + i, (0.08, 0.08, h - CT), (x, y, (h + CT) / 2)) for i, (x, y, h) in
                       enumerate(((-CW / 2 + 0.05, -CD / 2 + 0.05, 1.98), (CW / 2 - 0.05, -CD / 2 + 0.05, 1.98), (-CW / 2 + 0.05, CD / 2 - 0.05, 2.16), (CW / 2 - 0.05, CD / 2 - 0.05, 2.16)))],
         "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [stall(k, seed) for k in TRADERS]


def extra_checks(A):
    S = [A[n] for n in NAMES.values()]
    fr = [[(q["name"], q.get("size"), q["centre"]) for q in m["objects"][0]["parts"]] for m in S]
    return [("one modular frame: identical frame parts on all 4 stalls", all(f == fr[0] for f in fr)),
            ("SOCKET_Sign on the sign board front, SOCKET_Goods on the counter", all({s["name"]: s["location"] for s in m["sockets"]} == {"SOCKET_Sign": list(SIGN), "SOCKET_Goods": [0, 0, CT]} for m in S)),
            ("goods sit on or above the counter", all(min(q["centre"][2] for o in m["objects"][1:] for q in o["parts"]) >= CT - 1e-6 for m in S)),
            ("stone blanks have no song groove", not any("Groove" in q["name"] or "Note" in q["name"] for o in A[NAMES["Stone"]]["objects"] for q in o["parts"])),
            ("egg stall reuses the WZ nest recipe", sum(1 for q in A[NAMES["Eggs"]]["objects"][1]["parts"] if q["name"].startswith("Nest_")) == len(wz_eggs.nest()["objects"][0]["parts"])),
            ("stall footprint ~1.6-2.0 m, height 2.0-2.4 m", all(1.6 <= m["predicted"]["dimensions"][0] <= 2.0 and 2.0 <= m["predicted"]["dimensions"][2] <= 2.4 for m in S), [m["predicted"]["dimensions"] for m in S])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
