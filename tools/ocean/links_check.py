# SPDX-License-Identifier: MIT
"""Check data/ocean/links.json and data/ocean/tidepen.json against the code they name. Every rule is read from source,
not copied:

  * realms and their dock flags come from the RealmDefs table in DaedalusRealmSessionCore.h
  * Ocean berths come from OceanTerrain.java boatBerth() and submarineBerth()
  * sea creatures come from voxel_creatures.py SEA; sea plants from voxel_aquatic.py SPECIES (family "sea")
  * the settled_care thresholds must equal TidePenGate.Rule.DEFAULT

    python tools/ocean/links_check.py [--self-test]

The last line printed is "LINKS n/m PASS|FAIL", and the exit code is 0 only on PASS. WARN lines report mismatches in
code this check does not own. They do not fail the run.

--self-test runs the same checks on deliberately broken copies (canaries); each one must FAIL.
"""
import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, *a)
SESSION = P("engines", "unreal", "DaedalusLink", "Source", "DaedalusLink", "Public", "DaedalusRealmSessionCore.h")
TRAVEL = P("engines", "unreal", "DaedalusLink", "Source", "DaedalusLink", "Public", "DaedalusOceanTravelCore.h")
TERRAIN = P("daedalus-core", "src", "main", "java", "com", "daedalus", "world", "ocean", "OceanTerrain.java")
GATE = P("daedalus-core", "src", "main", "java", "com", "daedalus", "world", "ocean", "TidePenGate.java")


def realm_defs():
    """{id: {has_docks, has_sub_dock}} parsed from the RealmDefs initialiser rows."""
    src = open(SESSION, encoding="utf-8").read()
    rows = re.findall(r'\{"([A-Z-]+)",\s*"[^"]*",\s*"[^"]*",\s*(true|false),\s*(true|false),\s*(true|false),\s*(true|false)\}', src)
    return {r[0]: {"is3d": r[1] == "true", "has_docks": r[2] == "true", "has_sub_dock": r[3] == "true"} for r in rows}


def berths():
    src = open(TERRAIN, encoding="utf-8").read()
    get = lambda n: [int(v) for v in re.search(n + r'\(\) \{ return new BlockCoordinate\((-?\d+), (-?\d+), (-?\d+)\)', src).groups()]
    return {"boat": get("boatBerth"), "sub": get("submarineBerth")}


def sea_creatures():
    src = open(P("tools", "blender", "voxel_creatures.py"), encoding="utf-8").read()
    body = re.search(r'^SEA = \(([^)]*)\)', src, re.M | re.S).group(1)
    return set(re.findall(r'"([a-z_]+)"', body))


def sea_plants():
    src = open(P("tools", "blender", "voxel_aquatic.py"), encoding="utf-8").read()
    return set(re.findall(r'^\s+"([A-Za-z]+)":\s+\("sea",', src, re.M))


def gate_rule():
    src = open(GATE, encoding="utf-8").read()
    a = re.search(r'Rule DEFAULT = new Rule\((\d+), (\d+), (\d+), (\d+)\)', src).groups()
    return dict(zip(("feedings_min", "distinct_days_min", "harm_events_max", "habitat_planted_min"), map(int, a)))


def check(links, pen, out):
    R, B, SEA, PLANTS, RULE = realm_defs(), berths(), sea_creatures(), sea_plants(), gate_rule()
    res = []

    def ok(name, cond, info=""):
        res.append(bool(cond))
        out.append(("ok   " if cond else "FAIL ") + name + ("  " + str(info) if info != "" and not cond else ""))
    ok("RealmDefs parsed from the session core (WORLD-ZERO and OCEAN present)", "WORLD-ZERO" in R and "OCEAN" in R, sorted(R))
    docks = {d["id"]: d for d in links["docks"]}
    ok("dock ids are unique", len(docks) == len(links["docks"]))
    for d in links["docks"]:
        ok("dock %s: realm %s is a session realm" % (d["id"], d["realm"]), d["realm"] in R, d["realm"])
        if d["realm"] in R and d["realm"] != "OCEAN":
            ok("dock %s: %s has docks" % (d["id"], d["realm"]), R[d["realm"]]["has_docks"])
            if d.get("underwater"):
                ok("dock %s: underwater only where an underwater dock exists" % d["id"], R[d["realm"]]["has_sub_dock"])
        ok("dock %s: vessels are boat/sub and match underwater" % d["id"],
           set(d["vessels"]) <= {"boat", "sub"} and (("boat" not in d["vessels"]) or not d.get("underwater")), d["vessels"])
        a = d.get("anchor", {})
        if a.get("source", "").startswith("daedalus-core OceanTerrain."):
            kind = "boat" if "boatBerth" in a["source"] else "sub"
            ok("dock %s: anchor equals OceanTerrain.%s() %s" % (d["id"], "boatBerth" if kind == "boat" else "submarineBerth", B[kind]), a.get("xyz") == B[kind], a.get("xyz"))
    for c in links["connections"]:
        a, b = docks.get(c["departure"]), docks.get(c["destination"])
        ok("connection %s -> %s: both docks exist" % (c["departure"], c["destination"]), a and b)
        flags_are_bool = all(type(c.get(flag)) is bool for flag in ("boats", "submarines"))
        ok("connection %s -> %s: boats and submarines must be JSON booleans" % (c["departure"], c["destination"]),
           flags_are_bool, {flag: type(c[flag]).__name__ if flag in c else "missing" for flag in ("boats", "submarines")})
        if not flags_are_bool:
            continue
        if a and b:
            ok("connection %s -> %s: one end is the Ocean (session core: docks lead to the Ocean)" % (a["id"], b["id"]),
               (a["realm"] == "OCEAN") != (b["realm"] == "OCEAN"))
            ok("connection %s -> %s: every enabled vessel kind is supported at both ends" % (a["id"], b["id"]),
               (c["boats"] or c["submarines"])
               and (not c["boats"] or ("boat" in a["vessels"] and "boat" in b["vessels"]))
               and (not c["submarines"] or ("sub" in a["vessels"] and "sub" in b["vessels"])))
            if a["realm"] == "OCEAN" and b["realm"] != "OCEAN":
                ok("connection %s -> %s: Ocean to a realm needs a sub and an underwater dock" % (a["id"], b["id"]),
                   c["submarines"] and not c["boats"] and b["realm"] in R and R[b["realm"]]["has_sub_dock"])
    ok("tide-pen landing is an Ocean dock", docks.get(pen["landing"], {}).get("realm") == "OCEAN", pen["landing"])
    ok("tide-pen landing is reachable from World-Zero", any(c["destination"] == pen["landing"] and docks.get(c["departure"], {}).get("realm") == "WORLD-ZERO" for c in links["connections"]))
    for r in pen["residents"]:
        ok("resident %s is a voxel_creatures SEA species" % r["species"], r["species"] in SEA, r["species"])
        ok("resident %s: food and habitat are sea plants" % r["species"], set(r["food"]) | set(r["habitat"]) <= PLANTS, sorted(set(r["food"]) | set(r["habitat"]) - PLANTS))
    ok("settled_care thresholds equal TidePenGate.Rule.DEFAULT", pen["settled_care"]["requires"] == dict(RULE, right_food=True), (pen["settled_care"]["requires"], RULE))
    ok("leaving wild is always allowed", pen["actions"]["leave_wild"].startswith("always ALLOW"))
    return res


def warnings():
    """Mismatches in code this check does not own (team-codex's OceanTravelCore): reported, never failed."""
    w = []
    t = open(TRAVEL, encoding="utf-8").read() if os.path.exists(TRAVEL) else ""
    if '"Ocean Realm"' in t:
        w.append('WARN OceanTravelCore compares realm names to "Ocean Realm"/"Portal Realm"; the session core and links.json use OCEAN/PORTAL')
    if 'destination.Realm != "Portal Realm"' in t:
        w.append("WARN OceanTravelCore.Land allows an ordinary (non-underwater) shore landing only into the Portal realm; "
                 "the session core allows OCEAN --shore--> the realm you sailed from (World-Zero boats could not come home by shore)")
    return w


def main(argv):
    links = json.load(open(P("data", "ocean", "links.json"), encoding="utf-8"))
    pen = json.load(open(P("data", "ocean", "tidepen.json"), encoding="utf-8"))
    if "--self-test" in argv:
        baseline_out = []
        baseline = check(links, pen, baseline_out)
        baseline_ok = all(baseline)
        print("LINKS-BASELINE %d/%d %s" % (sum(baseline), len(baseline), "PASS" if baseline_ok else "FAIL"))
        if not baseline_ok:
            print("\n".join(baseline_out))
            return 1
        canaries = []
        L = copy.deepcopy(links); L["docks"][0]["realm"] = "LABYRINTH"; canaries.append(("dock from a realm with no docks", L, pen))
        L = copy.deepcopy(links); L["docks"][1]["anchor"]["xyz"] = [0, 1, 9]; canaries.append(("berth drifted from OceanTerrain", L, pen))
        L = copy.deepcopy(links); L["connections"].append({"departure": "ocean-pier-boat", "destination": "wz-rim-tidepen", "boats": True, "submarines": False}); canaries.append(("boat from the Ocean into a realm", L, pen))
        L = copy.deepcopy(links); L["connections"][0]["submarines"] = True
        canaries.append(("boat support cannot authorize an unsupported submarine", L, pen))
        L = copy.deepcopy(links)
        departure = next(d for d in L["docks"] if d["id"] == L["connections"][0]["departure"])
        departure["vessels"].append("sub")
        L["connections"][0]["destination"] = "ocean-pier-sub"
        L["connections"][0]["submarines"] = True
        canaries.append(("submarine support cannot authorize an unsupported boat", L, pen))
        L = copy.deepcopy(links); L["connections"][0].update(boats=False, submarines=False)
        canaries.append(("connection with neither vessel enabled", L, pen))
        Q = copy.deepcopy(pen); Q["residents"][0]["species"] = "griffin"; canaries.append(("resident not a sea species", links, Q))
        Q = copy.deepcopy(pen); Q["settled_care"]["requires"]["feedings_min"] = 1; canaries.append(("threshold drifted from TidePenGate", links, Q))
        n = 0
        for name, L, Q in canaries:
            out = []
            failed = not all(check(L, Q, out))
            print(("ok   " if failed else "FAIL ") + "canary FAILs: " + name)
            n += failed
        print("LINKS-CANARIES %d/%d %s" % (n, len(canaries), "PASS" if n == len(canaries) else "FAIL"))
        flag_canaries = []
        for flag in ("boats", "submarines"):
            for label, value in (("string", "false"), ("integer", 1), ("null", None), ("missing", None)):
                L = copy.deepcopy(links)
                if label == "missing":
                    del L["connections"][0][flag]
                else:
                    L["connections"][0][flag] = value
                flag_canaries.append((flag + " " + label, L))
        flags_ok = 0
        for name, L in flag_canaries:
            out = []
            rejected = not all(check(L, pen, out))
            failures = [line for line in out if line.startswith("FAIL ")]
            right_reason = (rejected and len(failures) == 1
                            and "boats and submarines must be JSON booleans" in failures[0])
            print(("ok   " if right_reason else "FAIL ") + "flag type rejected for boolean diagnostic: " + name)
            if not right_reason:
                print("\n".join(out))
            flags_ok += right_reason
        print("LINKS-FLAGS %d/%d %s" % (flags_ok, len(flag_canaries), "PASS" if flags_ok == len(flag_canaries) else "FAIL"))
        L = copy.deepcopy(links)
        return_destination = next(d for d in L["docks"] if d["id"] == "wz-rim-tidepen")
        return_destination["vessels"].append("sub")
        L["connections"].append({"departure": "ocean-pier-sub", "destination": return_destination["id"],
                                 "boats": False, "submarines": True})
        return_destination["realm"] = "MISSING-SESSION"
        out = []
        unknown_rejected = not all(check(L, pen, out))
        failures = [line for line in out if line.startswith("FAIL ")]
        # This canonical dock also supplies the World-Zero tide-pen route; preserve its reachability failure.
        expected_failures = (
            "FAIL dock wz-rim-tidepen: realm MISSING-SESSION is a session realm",
            "FAIL connection ocean-pier-sub -> wz-rim-tidepen: Ocean to a realm needs a sub and an underwater dock",
            "FAIL tide-pen landing is reachable from World-Zero")
        unknown_ok = (unknown_rejected and len(failures) == len(expected_failures)
                      and all(any(line.startswith(reason) for line in failures) for reason in expected_failures))
        print(("ok   " if unknown_ok else "FAIL ") + "unknown return realm fails with realm, connection and reachability diagnostics")
        if not unknown_ok:
            print("\n".join(out))
        print("LINKS-RETURN-REALM %d/1 %s" % (int(unknown_ok), "PASS" if unknown_ok else "FAIL"))
        return 0 if n == len(canaries) and flags_ok == len(flag_canaries) and unknown_ok else 1
    out = []
    res = check(links, pen, out)
    print("\n".join(out + warnings()))
    ok = sum(res)
    print("LINKS %d/%d %s" % (ok, len(res), "PASS" if ok == len(res) else "FAIL"))
    return 0 if ok == len(res) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
