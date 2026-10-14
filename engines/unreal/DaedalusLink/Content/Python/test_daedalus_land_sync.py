# SPDX-License-Identifier: MIT
"""daedalus_land_sync: the district DTO read with the C++ reader's refusals, and the five-bucket reconciliation."""
import json

import daedalus_land_grid as G
import daedalus_land_sync as S

ok = total = 0


def check(name, cond, why=""):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond or not why else "  " + str(why)))


sample = {"schemaVersion": 1, "realm": "WORLD-ZERO", "revision": 2, "district": 55, "gridSide": 100, "pitchMetres": 256.0,
          "coordinates": "east-north-realm-metres", "reservedCells": list(range(9)),
          "lands": [{"landNumber": 9, "cellX": 56, "cellY": 52, "size": 4, "seed": "-9223372036854775808", "originEastMetres": 1536.0, "originNorthMetres": 512.0},
                    {"landNumber": 10, "cellX": 52, "cellY": 50, "size": 4, "seed": "42", "originEastMetres": 512.0, "originNorthMetres": 0.0},
                    {"landNumber": 60, "cellX": 54, "cellY": 51, "size": 1, "seed": "7", "originEastMetres": 1024.0, "originNorthMetres": 256.0},
                    {"landNumber": 64, "cellX": 55, "cellY": 55, "size": 1, "seed": "8", "originEastMetres": 1280.0, "originNorthMetres": 1280.0}]}
d, why = S.read_district(json.dumps(sample))
check("the sample district reads", d is not None, why)
check("header and seeds", d["realm"] == "WORLD-ZERO" and d["revision"] == 2 and d["district"] == 55 and d["lands"][0]["seed"] == "-9223372036854775808")
check("nine reserved cells", d["reserved"] == list(range(9)))
check("schema 2 refused", S.read_district(json.dumps(dict(sample, schemaVersion=2)))[0] is None)
check("no lands refused", S.read_district(json.dumps({"schemaVersion": 1, "realm": "X", "district": 1}))[0] is None)
check("broken json refused with a reason", S.read_district("{\"schemaVersion\": 1,")[1].startswith("json:"))
check("size 5 refused", S.read_district(json.dumps(dict(sample, lands=[{"landNumber": 1, "cellX": 1, "cellY": 1, "size": 5}])))[0] is None)
plots = {9: (56, 52, 4), 10: (52, 50, 4), 60: (54, 50, 1), 70: (56, 56, 1), 99: (50, 50, 1), 5000: (10, 10, 1)}
r = S.reconcile(d, plots)
check("two agree", r["agree"] == [9, 10])
check("60 moved to the server's cell", [m[0] for m in r["moved"]] == [60] and r["moved"][0][1]["y"] == 51)
check("64 only on the server", [l["n"] for l in r["only_server"]] == [64])
check("70 and 99 only in the editor; another district's plot ignored", r["only_editor"] == [70, 99])
check("99 stands on a reserved cell", r["reserved_plotted"] == [99])
check("describe matches the C++ wording", S.describe(r) == "rev=2 district=55 agree=2 moved=1 only_server=1 only_editor=2 reserved_plotted=1", S.describe(r))
check("the hub rings 1..6 touch districts 44,45,54,55", S.hub_districts() == [44, 45, 54, 55])
check("district membership", S.in_district(55, 50, 50) and S.in_district(55, 59, 59) and not S.in_district(55, 60, 50) and not S.in_district(55, 50, 49))
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
