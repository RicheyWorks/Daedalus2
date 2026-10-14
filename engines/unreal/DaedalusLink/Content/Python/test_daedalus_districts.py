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
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
