# SPDX-License-Identifier: MIT
"""Headless checks for daedalus_plots: the free cells within N rings, minus estates and the hub, at the right place."""
import daedalus_land_grid as G
import daedalus_plots as P

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


c1 = P.cells_within(1)
check("ring 1 is the hub plus 8 neighbours, in spiral order", c1 == list(range(9)))
check("ring 6 is a 13 x 13 block", len(P.cells_within(6)) == 169)
est = [(52, 46, 4), (47, 52, 3)]
used = P.taken_by_estates(est)
check("a 4x4 and a 3x3 estate take 25 cells", len(used) == 25)
hub = {G.number(x, y) for x in range(49, 52) for y in range(49, 52)}
p = P.plan(6, est, hub, hub_cm=(14850.0, -9500.0), ground_cm=-250.0)
check("free cells = 169 - 25 - 9", len(p) == 135)
check("no plot on an estate or the hub", not ({q["n"] for q in p} & (used | hub)))
check("plots are in spiral order (low numbers first)", [q["n"] for q in p] == sorted(q["n"] for q in p))
east = next(q for q in p if q["cell"] == (52, 50 - 4) or q["cell"] == (56, 50))
check("a cell 6 east of the hub sits 6 pitches east of it", abs(east["at"][0] - (14850.0 + 6 * 256.0 * 100.0)) < 1e-6 and abs(east["at"][1] - (-9500.0)) < 1e-6 and east["at"][2] == -250.0)
check("every plot knows its district", all(q["district"] == G.district(q["n"]) for q in p))
check("an estate that splits a district takes nothing", P.taken_by_estates([(48, 48, 4)]) == set())
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
