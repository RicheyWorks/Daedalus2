# SPDX-License-Identifier: MIT
"""daedalus_districts: which sublevel each laid-down actor belongs to, and what a move plan skips."""
import daedalus_districts as D

ok = total = 0


def check(name, cond, why=""):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond or not why else "  " + str(why)))


R = "GALLERY-CITY"
check("a land goes to its district sublevel", D.package_for(R, ["Land", "Realm:GALLERY-CITY", "Deed:64", "District:55"]) == "/Game/Daedalus/Realms/GALLERYCITY/D55")
check("district numbers are two digits", D.package_for(R, ["Land", "Realm:GALLERY-CITY", "District:4"]) == "/Game/Daedalus/Realms/GALLERYCITY/D04")
check("hub, kit, talkers and creatures go to the realm's hub sublevel", all(D.package_for(R, [k, "Realm:GALLERY-CITY"]) == "/Game/Daedalus/Realms/GALLERYCITY/GALLERYCITY_Hub" for k in ("Hub", "Kit", "Talker", "Creature", "Gate")))
check("another realm's actor is not touched", D.package_for(R, ["Land", "Realm:PARCELS", "District:55"]) is None)
check("a land without a district is left where it is (malformed)", D.package_for(R, ["Land", "Realm:GALLERY-CITY"]) is None)
rows = [("Land_GALLERYCITY_64", ["Land", "Realm:GALLERY-CITY", "District:55"], "/Game/Daedalus/DaedalusWorld"),
        ("Land_GALLERYCITY_65", ["Land", "Realm:GALLERY-CITY", "District:55"], "/Game/Daedalus/Realms/GALLERYCITY/D55"),
        ("Kit_Prop_Gallery_Ramp", ["Kit", "Ramp", "Realm:GALLERY-CITY"], "/Game/Daedalus/DaedalusWorld"),
        ("Land_PARCELS_9", ["Land", "Realm:PARCELS", "District:55"], "/Game/Daedalus/DaedalusWorld")]
moves, skipped = D.group(R, rows)
check("the plan moves only what is not already in its sublevel", moves == {"/Game/Daedalus/Realms/GALLERYCITY/D55": ["Land_GALLERYCITY_64"], "/Game/Daedalus/Realms/GALLERYCITY/GALLERYCITY_Hub": ["Kit_Prop_Gallery_Ramp"]}, moves)
check("and says what it skipped and why", skipped == {"already there": 1, "not this realm or malformed": 1}, skipped)
cells = D.district_cells(55)
import daedalus_land_grid as G
check("district 55 has 100 cells, all with x,y in 50..59", len(cells) == 100 and all(50 <= G.cell(n)[0] <= 59 and 50 <= G.cell(n)[1] <= 59 for n in cells))
check("district 0 is the far south-west corner", all(G.cell(n)[0] < 10 and G.cell(n)[1] < 10 for n in D.district_cells(0)))
check("the four hub districts cover 400 cells with the hub cell among them", 0 in D.district_cells(55) and len(set(sum((D.district_cells(d) for d in (44, 45, 54, 55)), []))) == 400)
cells33 = D.district_cells(33)
xy = [(float(G.cell(n)[0]) * 25600.0, float(G.cell(n)[1]) * 25600.0) for n in cells33]
plots, rubble, decor = D.dress_plan(cells33, xy, "WORLD-ZERO", 5000.0)
check("World Zero: every island keeps its cell, floats at its own height within +-40 m and is 8..20 m thick",
      len(plots) == 100 and all(abs(p[2] + p[6] * 50.0 - 5000.0) <= 4000.0 and 8.0 <= p[6] <= 20.0 and (p[0], p[1]) == xy[i] for i, p in enumerate(plots)) and len({round(p[2]) for p in plots}) > 50)
under = rubble[::1]
under = [e for e in rubble if e[4] >= 41.0 and e[6] >= 30.0]   # undersides: 41..64 m wide and 33..52 m tall; terraces/rocks are smaller
check("World Zero: a rock underside per island, below the slab, plus its unique extras", len(under) == 100 and len(rubble) > 100 and all(any(e[2] < p[2] and abs(e[0] - p[0]) < 700.0 and abs(e[1] - p[1]) < 700.0 for e in under) for p in plots))
check("about every fourth island gets a prop, deterministically", 10 <= len(decor) <= 45 and decor == D.dress_plan(cells33, xy, "WORLD-ZERO", 5000.0)[2])
plots2, extras2, _ = D.dress_plan(cells33, xy, "PARCELS", 5220.0)
check("a realm's plots keep the ground plane (no floating, no turning) and its extras sit on or above the ground", all(abs(p[2] + p[6] * 50.0 - 5220.0) < 1.0 and p[3] == 0.0 for p in plots2) and all(e[2] - e[6] * 50.0 >= 5220.0 - 101.0 for e in extras2))
shapes = {tuple(round(v) for e in D.island_plan(n, 0.0, 0.0, 5220.0, 12.0, "WORLD-ZERO") for v in e) for n in cells33}
check("every island is unique: 100 deeds give 100 different terrace/rock layouts, deterministically", len(shapes) >= 95 and D.island_plan(7, 0.0, 0.0, 1.0, 1.0, "PARCELS") == D.island_plan(7, 0.0, 0.0, 1.0, 1.0, "PARCELS"), len(shapes))
check("terraces stay on the slab and rocks stay inside the cell", all(abs(e[0]) + e[4] * 50.0 <= 12800.0 and abs(e[1]) + e[5] * 50.0 <= 12800.0 for n in cells33 for e in D.island_plan(n, 0.0, 0.0, 5220.0, 12.0, "WORLD-ZERO")))
check("a realm district gets one 2,560 m ground slab, World Zero none", len(D.district_ground("PARCELS", 33)) == 1 and D.district_ground("PARCELS", 33)[0][4] == 2560.0 and D.district_ground("WORLD-ZERO", 33) == [])
rows = D.ledger_rows("PARCELS", [(33, cells33[:3], [(100.0, 200.0, 4620.0, 12.0), (356.0, 200.0, 4720.0, 10.0), (612.0, 200.0, 4420.0, 16.0)], {cells33[1]: 2}), (0, [5], [(0.0, 0.0, 0.0, 12.0)], {})])
check("the ledger has one row per land, sorted by deed, with top height, thickness and prop count",
      [r["deed"] for r in rows] == sorted([5] + cells33[:3]) and next(r for r in rows if r["deed"] == cells33[1])["props"] == 2
      and next(r for r in rows if r["deed"] == cells33[0])["top_cm"] == 5220 and next(r for r in rows if r["deed"] == cells33[2])["thick_m"] == 16.0, rows[:2])
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
