# SPDX-License-Identifier: MIT
"""Contest row 7 (G02 unreliable maps; buffffff 48312), blender-kit/v1.
Prop_Lab_SurveyMap_A / _B  0.6 x 0.4 m paper maps, slightly curled, ink corridors drawn from a seeded maze walk; A and B are
    drawn from different seeds, so they disagree (the 'unreliable' maps). UCX thin box. No sockets (they sit in the table's).
Prop_Lab_SurveyTable  1.5 m cartographer's table (top, legs, apron, inkwell, rolled chart); SOCKET_MapA / SOCKET_MapB on the top.
REUSE check: catalog tables (Prop_BBIsle_Table_*, Prop_Orr_Interior_*_Table, Prop_CraftingTable) carry no sockets and are not
1.5 m cartographer tables; no paper map props exist (Prop_Orr_Interior_Map_Chest is a chest) -> new.
Usage: python lab_g02.py --out data/contest/lab_g02.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 202
MAP, TAB = "Prop_Lab_SurveyMap", "Prop_Lab_SurveyTable"
CAPS = {MAP + "_A": 2500, MAP + "_B": 2500, TAB: 2500}
SOCKETS = {MAP + "_A": [], MAP + "_B": [], TAB: ["SOCKET_MapA", "SOCKET_MapB"]}
PAPER, INK, RED, WOOD, BRASS = "E6D8B0", "2B2A33", "A23B2E", "6B4A2E", "B08D3C"


def survey_map(variant, seed=SEED):
    a = "%s_%s" % (MAP, variant); r = K.rng(seed, a)
    mats = [K.material(a, 0, "paper", PAPER, 0.95), K.material(a, 1, "ink", INK, 0.6), K.material(a, 2, "red ink", RED, 0.6)]
    P = []
    for i, (x, rx) in enumerate(((-0.2, 4), (0.0, 0), (0.2, -4))):        # three panels, edges curled up a little
        P.append(K.box("Sheet%d" % i, (0.2, 0.4, 0.004), (x, 0, 0.002 if i == 1 else round(0.1 * math.sin(math.radians(4)) + 0.002 * math.cos(math.radians(4)), 7)), 0, rot=(0, rx, 0), bevel=False))
    cx, cy = 0, 0; n = 0; cell = 0.05; seen = {(0, 0)}
    for step in range(20):                                               # seeded maze walk on a 0.05 m grid inside the sheet
        dx, dy = r.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        nx, ny = cx + dx, cy + dy
        if abs(nx) > 5 or abs(ny) > 3:
            continue
        P.append(K.box("Ink%02d" % n, (cell + 0.006 if dx else 0.006, cell + 0.006 if dy else 0.006, 0.0015),
                       (round((cx + nx) / 2 * cell, 5), round((cy + ny) / 2 * cell, 5), 0.0095), 1, bevel=False, lod1={"drop": n % 2 == 1}))
        n += 1; cx, cy = nx, ny; seen.add((cx, cy))
    P.append(K.box("XMark", (0.03, 0.006, 0.0015), (round(cx * cell, 5), round(cy * cell, 5), 0.0105), 2, rot=(0, 0, 45), bevel=False))
    P.append(K.box("XMark2", (0.03, 0.006, 0.0015), (round(cx * cell, 5), round(cy * cell, 5), 0.0105), 2, rot=(0, 0, -45), bevel=False))
    m = {"asset": a, "kind": "Prop", "seed": seed, "variant": variant, "spec": {"row": 7, "gap": "G02", "size_m": "map 0.6 x 0.4 m", "tri_cap": 2500, "lod": "LOD0/1",
         "note": "A and B are drawn from different seeds: they disagree on purpose"}, "materials": mats, "objects": [K.obj(a, P)], "sockets": [],
         "collision": [K.ucx_box(a, 0, (0.6, 0.4, 0.012), (0, 0, 0.006))], "nanite": True, "ink_end_cell": [cx, cy], "ink_cells": [list(c) for c in sorted(seen)]}
    return K.finish(m)


def table(seed=SEED):
    a = TAB
    mats = [K.material(a, 0, "oak", WOOD, 0.85), K.material(a, 1, "brass", BRASS, 0.5, 0.6), K.material(a, 2, "paper", PAPER, 0.95)]
    P = [K.box("Top", (1.5, 0.9, 0.05), (0, 0, 0.755), 0)]
    for i, (x, y) in enumerate([(-0.68, -0.38), (0.68, -0.38), (0.68, 0.38), (-0.68, 0.38)]):
        P.append(K.box("Leg%d" % i, (0.07, 0.07, 0.73), (x, y, 0.365), 0))
    P += [K.box("ApronF", (1.3, 0.03, 0.1), (0, -0.4, 0.68), 0, lod1={"drop": True}), K.box("ApronB", (1.3, 0.03, 0.1), (0, 0.4, 0.68), 0, lod1={"drop": True}),
          K.box("Stretcher", (1.3, 0.05, 0.05), (0, 0, 0.18), 0, lod1={"drop": True}),
          K.cyl("Inkwell", "z", 0.035, 0.03, 0.06, (0.62, 0.3, 0.81), 1, 10, lod1={"segments": 6}),
          K.cyl("Chart", "x", 0.035, 0.035, 0.5, (0, 0.33, 0.815), 2, 10, lod1={"segments": 6}),
          K.cyl("Quill", "x", 0.004, 0.004, 0.22, (0.5, 0.3, 0.86), 2, 6, rot=(0, -30, 20), lod1={"drop": True})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": {"row": 7, "gap": "G02", "size_m": "table 1.5 m", "tri_cap": 2500, "lod": "LOD0/1", "collision": "UCX table",
         "sockets": ["MapA", "MapB"]}, "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("MapA", (-0.36, -0.08, 0.78)), K.socket("MapB", (0.36, -0.08, 0.78))],
         "collision": [K.ucx_box(a, 0, (1.5, 0.9, 0.78), (0, 0, 0.39))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [survey_map("A", seed), survey_map("B", seed + 1), table(seed)]


def extra_checks(A):
    a, b, t = A[MAP + "_A"], A[MAP + "_B"], A[TAB]
    return [("maps 0.6 x 0.4 m", all(abs(m["predicted"]["dimensions"][0] - 0.6) < 0.01 and abs(m["predicted"]["dimensions"][1] - 0.4) < 0.01 for m in (a, b)), [a["predicted"]["dimensions"], b["predicted"]["dimensions"]]),
            ("maps A and B disagree (different ink walks)", a["ink_cells"] != b["ink_cells"]),
            ("table 1.5 m, map sockets on the top", abs(t["predicted"]["dimensions"][0] - 1.5) < 1e-6 and all(abs(s["location"][2] - 0.78) < 1e-6 for s in t["sockets"])),
            ("a map fits each table socket side by side", 2 * 0.6 <= 1.5 and abs(t["sockets"][0]["location"][0] - t["sockets"][1]["location"][0]) >= 0.6)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
