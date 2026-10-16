# SPDX-License-Identifier: MIT
"""Check a bounded aquatic habitat proposal (data/ocean/habitat-tidepool-rN.json; default: every revision).

Every reference is read from source, not copied:
  * residents must be exactly tidepen.json's residents, with the same food
  * canon keys must exist in the species canon (species.tsv) with guild MARINE; rarity etc. are printed from it
  * behaviour clips must be clips the voxel creature rig exports (voxel_creatures.py CLIPS)
  * plants must be sea plants (voxel_aquatic.py, family "sea")
Habitat invariants (the point of the design):
  * zones get deeper in order shallow < refuge < deep; water states are ordered low < normal < high
  * no stranding: in EVERY water state, each resident's zones are all wet (depth >= wet_min_m)
  * it can eat: in EVERY water state, one of its zones grows what it eats
  * the refuge stays wet at low water, and the low state really drains the shallow zone (a changing water level)
  * body size (when the proposal has "display"): every zone a resident uses in a state is deeper than the resident
    is tall, height read from the voxel creature itself (r2 added this after r1's art showed a seahorse standing
    out of the water)

    python tools/ocean/habitat_check.py [--self-test] [FILE ...]

Last line "HABITAT n/m PASS|FAIL"; exit 0 only on PASS. --self-test: broken copies must each FAIL.
"""
import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, *a)
CANON = P("daedalus-core", "src", "main", "resources", "com", "daedalus", "world", "ecology", "species.tsv")


def canon():
    rows = {}
    for line in open(CANON, encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            f = line.rstrip("\n").split("\t")
            rows[f[0]] = {"name": f[1], "rarity": f[2], "temperament": f[3], "guild": f[4], "size": f[5], "strategy": f[6]}
    return rows


def clips():
    src = open(P("tools", "blender", "voxel_creatures.py"), encoding="utf-8").read()
    return set(re.findall(r'\("([A-Za-z]+)", \d+\)', re.search(r"^CLIPS = (.*)$", src, re.M).group(1)))


def sea_plants():
    src = open(P("tools", "blender", "voxel_aquatic.py"), encoding="utf-8").read()
    return set(re.findall(r'^\s+"([A-Za-z]+)":\s+\("sea",', src, re.M))


def heights(h):
    """species -> body height in metres at the proposal's display scale, from the voxel plan (feet at z=0)."""
    if "display" not in h:
        return {}
    sys.path.insert(0, P("tools", "blender"))
    import voxel_creatures as VC
    cm = h["display"]["voxel_cm"]
    return {r["species"]: (max(v[2] for part in VC.plan(r["species"]).values() for v in part) + 1) * cm / 100.0 for r in h["residents"]}


def check(h, pen, out, cn, cl, plants):
    res = []
    def ok(name, cond, info=""):
        res.append(bool(cond))
        out.append(("ok   " if cond else "FAIL ") + name + (" " + info if info else ""))
    zones = {z["id"]: z for z in h["zones"]}
    states = h["water_states"]
    depth = lambda z, s: zones[z]["base_depth_m"] + s["offset_m"]
    wet = lambda z, s: depth(z, s) >= h["wet_min_m"]
    ok("zones shallow < refuge < deep", zones["shallow"]["base_depth_m"] < zones["refuge"]["base_depth_m"] < zones["deep"]["base_depth_m"])
    offs = [s["offset_m"] for s in states]
    ok("states low < normal < high", [s["id"] for s in states] == ["low", "normal", "high"] and offs == sorted(offs) and len(set(offs)) == 3)
    ok("refuge has cover and stays wet at low water", zones["refuge"]["cover"] and wet("refuge", states[0]))
    ok("low water drains the shallows (level really changes)", not wet("shallow", states[0]) and wet("shallow", states[1]))
    bad = sorted(set(p for z in zones.values() for p in z["plants"]) - plants)
    ok("zone plants are sea plants", not bad, ", ".join(bad))
    tall = heights(h)
    pr = {r["species"]: r for r in pen["residents"]}
    hr = {r["species"]: r for r in h["residents"]}
    ok("residents are exactly tidepen.json's", set(pr) == set(hr), str(sorted(set(pr) ^ set(hr))))
    for sp, r in hr.items():
        if r["canon"] is None:
            ok("%s canon gap stated" % sp, bool(r.get("canon_gap")))
        else:
            row = cn.get(r["canon"])
            ok("%s canon row is MARINE" % sp, row and row["guild"] == "MARINE",
               "%s %s %s %s r/K=%s" % (r["canon"], row["rarity"], row["temperament"], row["size"], row["strategy"]) if row else "missing " + r["canon"])
        st = r["stats"]
        ok("%s stats in range" % sp, 1 <= st["health"] <= 100 and 0 <= st["wariness"] <= 5)
        bclips = [b["clip"] for b in r["behaviours"]]
        ok("%s behaviours idle/swim/feed on real clips" % sp, [b["id"] for b in r["behaviours"]] == ["idle", "swim", "feed"] and set(bclips) <= cl)
        eats = [b.get("eats") for b in r["behaviours"] if b["id"] == "feed"][0]
        ok("%s eats its tidepen food" % sp, sp in pr and eats in pr[sp]["food"])
        for s in states:
            zs = r["zones"].get(s["id"], [])
            dry = [z for z in zs if z not in zones or not wet(z, s)]
            ok("%s not stranded at %s" % (sp, s["id"]), zs and not dry, ("dry: " + ", ".join(dry)) if dry else "")
            ok("%s can eat at %s" % (sp, s["id"]), any(z in zones and eats in zones[z]["plants"] for z in zs))
            if sp in tall:
                low = [z for z in zs if z in zones and depth(z, s) < tall[sp]]
                ok("%s (%.2f m tall) covered at %s" % (sp, tall[sp], s["id"]), not low, ("sticks out in: " + ", ".join(low)) if low else "")
    return res


def main(argv):
    files = [a for a in argv if a.endswith(".json")] or sorted(os.path.join(P("data", "ocean"), f) for f in os.listdir(P("data", "ocean")) if re.match(r"habitat-tidepool-r\d+\.json$", f))
    pen = json.load(open(P("data", "ocean", "tidepen.json"), encoding="utf-8"))
    cn, cl, plants = canon(), clips(), sea_plants()
    if "--self-test" not in argv:
        total = []
        for f in files:
            out = ["== " + os.path.relpath(f, ROOT)]
            res = check(json.load(open(f, encoding="utf-8")), pen, out, cn, cl, plants)
            print("\n".join(out))
            total += res
        k = sum(total)
        print("HABITAT %d/%d %s" % (k, len(total), "PASS" if k == len(total) else "FAIL"))
        return 0 if k == len(total) else 1
    h = json.load(open(files[-1], encoding="utf-8"))
    if "--self-test" in argv:
        cans = []
        H = copy.deepcopy(h); H["residents"][1]["zones"]["low"] = ["shallow"]; cans.append(("seahorse stranded in drained shallows", H))
        H = copy.deepcopy(h); H["zones"][2]["plants"] = ["RedDulse"]; H["residents"][1]["zones"]["low"] = ["refuge"]; cans.append(("refuge without seahorse food", H))
        H = copy.deepcopy(h); H["water_states"][0]["offset_m"] = -0.1; cans.append(("low water no longer drains", H))
        H = copy.deepcopy(h); H["residents"][2]["canon"] = "turtle"; cans.append(("canon row not MARINE", H))
        H = copy.deepcopy(h); H["residents"][0]["behaviours"][1]["clip"] = "Swim"; cans.append(("clip the rig does not export", H))
        H = copy.deepcopy(h); H["residents"][3]["behaviours"][2]["eats"] = "Seagrass"; cans.append(("eats something not its food", H))
        H = copy.deepcopy(h); H["residents"].pop(); cans.append(("resident dropped", H))
        H = copy.deepcopy(h); H["residents"][1]["zones"]["normal"] = ["refuge", "shallow"]; cans.append(("seahorse sticks out of the shallows", H))
        H = copy.deepcopy(h); H["display"]["voxel_cm"] = 25; cans.append(("r1 art scale (25 cm voxel) in the pen", H))
        n = 0
        for name, H in cans:
            failed = not all(check(H, pen, [], cn, cl, plants))
            print(("ok   " if failed else "FAIL ") + "canary FAILs: " + name)
            n += failed
        print("HABITAT-CANARIES %d/%d %s" % (n, len(cans), "PASS" if n == len(cans) else "FAIL"))
        return 0 if n == len(cans) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
