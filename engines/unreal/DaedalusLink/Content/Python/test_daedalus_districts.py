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
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
