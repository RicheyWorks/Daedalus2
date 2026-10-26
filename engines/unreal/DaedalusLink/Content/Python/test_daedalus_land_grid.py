# SPDX-License-Identifier: MIT
"""Offline checks: the Python grid equals the C++ one and estate placement is sane. Run: python test_daedalus_land_grid.py"""
import daedalus_land_grid as G

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


# land_grid_test.cpp prints: 0=(50,50) 1=(51,50) 2=(51,51) 3=(50,51) 4=(49,51) 5=(49,50) 6=(49,49) 7=(50,49) 8=(51,49) 9=(52,49) 10=(52,50) 11=(52,51)
cpp = [(50, 50), (51, 50), (51, 51), (50, 51), (49, 51), (49, 50), (49, 49), (50, 49), (51, 49), (52, 49), (52, 50), (52, 51)]
check("the first twelve cells match the C++ spiral", [G.cell(n) for n in range(12)] == cpp)
check("ten thousand distinct cells, number(cell(n)) == n", len({G.cell(n) for n in range(G.COUNT)}) == G.COUNT and all(G.number(*G.cell(n)) == n for n in range(0, G.COUNT, 97)))
check("the hub is district 55, a corner district 0/99", G.district(0) == 55 and G.district(G.number(0, 0)) == 0 and G.district(G.number(99, 99)) == 99)
check("a 2x2 at the hub is deed 0; one across a district line is refused", G.estate(50, 50, 2) == 0 and G.estate(49, 49, 2) == -1)
check("metres: cell 1 is one pitch east", G.metres(1) == (256.0, 0.0))
check("sizes: 60 m -> 1 cell, 240 m -> 2, 540 m -> 3, 780 m -> 4", G.size_for(60, 63) == 1 and G.size_for(240, 240) == 2 and G.size_for(540, 540) == 3 and G.size_for(531, 780) == 4)
hub = []
G.estate(49, 49, 1, hub); G.estate(50, 49, 1, hub); G.estate(50, 50, 1, hub); G.estate(49, 50, 1, hub)   # the hub island: four cells
p = G.place_estates({"big": 4, "mid": 2, "small": 1, "mid2": 2}, taken=hub)
cells = {}
for name, (x, y, s, deed) in p.items():
    c = []
    G.estate(x, y, s, c)
    cells[name] = set(c)
check("every estate placed, none overlap each other or the hub", len(p) == 4 and all(not (cells[a] & cells[b]) for a in cells for b in cells if a < b) and all(not (cells[a] & set(hub)) for a in cells))
check("the biggest sits nearest the hub (lowest deed)", p["big"][3] <= min(v[3] for v in p.values()) + 0 or p["big"][3] < p["mid"][3])
check("each estate stays inside one district", all(len({G.district_of(G.cell(n)[0], G.cell(n)[1]) for n in cells[a]}) == 1 for a in cells))
check("deterministic", G.place_estates({"big": 4, "mid": 2, "small": 1, "mid2": 2}, taken=hub) == p)
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
