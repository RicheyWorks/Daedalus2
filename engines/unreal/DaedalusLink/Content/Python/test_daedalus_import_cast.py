# SPDX-License-Identifier: MIT
"""Offline checks of the cast importer's pure parts. Run: python test_daedalus_import_cast.py"""
import json
import os
import tempfile

import daedalus_import_cast as C

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


check("Curator Vell is Mob_Gallery_CuratorVell (Sol's convention)", C.talker_asset_id("gallery-city", "Curator Vell") == "Mob_Gallery_CuratorVell")
check("dashes and apostrophes drop out", C.talker_asset_id("gallery-city", "Frame-Hanger Twins") == "Mob_Gallery_FrameHangerTwins"
      and C.talker_asset_id("labyrinth", "The Architect's Apprentice") == "Mob_Labyrinth_TheArchitectSApprentice")
check("the Brick Realm is Brick, the Parcels is Parcels", C.talker_asset_id("bricks", "Foreman Kip") == "Mob_Brick_ForemanKip"
      and C.talker_asset_id("parcels", "Postmaster Grue") == "Mob_Parcels_PostmasterGrue")
d = tempfile.mkdtemp()
for n in ("Mob_Gallery_CuratorVell.glb", "Mob_Gallery_EchoChoir.glb", "notes.txt", "Prop_Frame.glb"):
    with open(os.path.join(d, n), "wb") as f:
        f.write(n.encode())
with open(os.path.join(d, "manifest.json"), "w") as f:
    json.dump({"assets": [{"id": "Mob_Gallery_CuratorVell", "sha256": "abc"}]}, f)
p = C.plan(d)
check("plan lists only Mob_*.glb, sorted", [x[0] for x in p] == ["Mob_Gallery_CuratorVell", "Mob_Gallery_EchoChoir"])
check("the manifest's sha wins, a missing one is computed from the file", p[0][2] == "abc" and len(p[1][2]) == 64)
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
