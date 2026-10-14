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
check("World Zero: a rock underside per island, below the slab", len(rubble) == 100 and all(r[2] < p[2] for r, p in zip(rubble, plots)))
check("about every fourth island gets a prop, deterministically", 10 <= len(decor) <= 45 and decor == D.dress_plan(cells33, xy, "WORLD-ZERO", 5000.0)[2])
plots2, rubble2, _ = D.dress_plan(cells33, xy, "PARCELS", 5220.0)
check("a realm's plots keep the terrain plane (no floating) and no rubble", not rubble2 and all(abs(p[2] + p[6] * 50.0 - 5220.0) < 1.0 for p in plots2))
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
