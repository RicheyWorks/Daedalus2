# SPDX-License-Identifier: MIT
"""Pure-Python checks for the contest / G01 / G03 kit recipes against BOARD\\BLENDER-ASKS-CONTEST-20261019.md (no Blender).
python test_contest_kits.py   (also checks the pinned data/contest/*.kit.json manifests match the recipes)"""
import importlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "kit"))
import kitlib as K
DATA = os.path.join(HERE, "..", "..", "..", "data", "contest")
MODULES = {"wz_fishing": "wz_fishing.kit.json", "wz_eggs": "wz_eggs.kit.json"}
for extra in ("lab_echo", "lab_fold", "g03_hornback", "or_parlay"):
    if os.path.exists(os.path.join(HERE, extra + ".py")):
        MODULES[extra] = extra + ".kit.json"
CAPS = {"Tool_WZ_FishingRod": 2000, "Prop_WZ_FishingFloat_Rest": 400, "Prop_WZ_FishingFloat_Dip": 400, "Prop_WZ_EggNest": 3000, "Prop_WZ_EggIncubator": 3000}
SOCKETS = {"Tool_WZ_FishingRod": ["SOCKET_Grip", "SOCKET_Reel", "SOCKET_Tip"], "Prop_WZ_FishingFloat_Rest": ["SOCKET_Line"], "Prop_WZ_FishingFloat_Dip": ["SOCKET_Line"],
           "Prop_WZ_EggNest": ["SOCKET_Egg", "SOCKET_Glow"], "Prop_WZ_EggIncubator": ["SOCKET_Egg", "SOCKET_Glow"]}
checks = []
add = lambda n, ok, d="": checks.append((n, bool(ok), d))
allassets = {}
for mod, fn in MODULES.items():
    M = importlib.import_module(mod); A = M.assets()
    add("%s deterministic" % mod, M.assets() == A)
    pin = os.path.join(DATA, fn)
    add("%s pinned manifest matches" % mod, os.path.exists(pin) and json.load(open(pin, encoding="utf-8")) == {"schema": K.SCHEMA + "/set", "assets": A})
    for m in A:
        allassets[m["asset"]] = m
        cap = getattr(M, "CAPS", {}).get(m["asset"], CAPS.get(m["asset"]))
        for c in K.check_asset(m, cap):
            add(*c)
        want = getattr(M, "SOCKETS", {}).get(m["asset"], SOCKETS.get(m["asset"]))
        add("%s sockets %s" % (m["asset"], want), sorted(s["name"] for s in m["sockets"]) == sorted(want), [s["name"] for s in m["sockets"]])
        add("%s collision names Unreal-prefixed and unique" % m["asset"], all(c["name"].startswith(("UCX_", "USP_", "UCP_", "UBX_")) and m["asset"] in c["name"] for c in m["collision"]) and len({c["name"] for c in m["collision"]}) == len(m["collision"]))
        add("%s Kind_Name" % m["asset"], m["asset"].split("_")[0] in ("Prop", "Tool", "Bld", "Mob", "Item", "Wpn", "Veh", "Sky"))
        add("%s axes recorded (front -Y = UE +X)" % m["asset"], "Unreal +X" in m["axes"])
        add("%s Nanite note" % m["asset"], "nanite" in m["unreal"])
        add("%s status staged NOT READY" % m["asset"], "NOT READY" in m["status"])
        add("%s seeded" % m["asset"], isinstance(m["seed"], int))
R, F, D = allassets["Tool_WZ_FishingRod"], allassets["Prop_WZ_FishingFloat_Rest"], allassets["Prop_WZ_FishingFloat_Dip"]
add("rod is 1.8 m long", R["predicted"]["dimensions"][2] == 1.8, R["predicted"]["dimensions"])
grip = next(p for p in R["objects"][0]["parts"] if p["name"] == "Grip")
add("rod grip 3 cm diameter", grip["r1"] * 2 == 0.03 and grip["r2"] * 2 == 0.03)
add("rod UCX prism on the grip (covers it)", R["collision"][0]["shape"] == "cyl" and R["collision"][0]["r1"] >= grip["r1"] and R["collision"][0]["length"] >= grip["length"] and R["collision"][0]["centre"] == grip["centre"])
add("float 8 cm diameter", F["predicted"]["dimensions"][:2] == [0.08, 0.08], F["predicted"]["dimensions"])
add("float states share sockets/collision names and materials", [s["name"] for s in F["sockets"]] == [s["name"] for s in D["sockets"]] and [m["hex"] for m in F["materials"]] == [m["hex"] for m in D["materials"]])
add("float LOD0 only", F["predicted"]["lod1_triangles"] is None and D["predicted"]["lod1_triangles"] is None)
add("float sphere collision (USP_)", F["collision"][0]["shape"] == "sphere" and F["collision"][0]["name"].startswith("USP_"))
add("float states share the triangle count (same mesh, tilted)", F["predicted"]["triangles"] == D["predicted"]["triangles"])
N, I = allassets["Prop_WZ_EggNest"], allassets["Prop_WZ_EggIncubator"]
add("nest ~0.6 m (0.5-0.65)", 0.5 <= max(N["predicted"]["dimensions"][:2]) <= 0.65, N["predicted"]["dimensions"])
add("incubator 0.8 m tall", I["predicted"]["dimensions"][2] == 0.8, I["predicted"]["dimensions"])
add("incubator lamp is a child node", [o["parent"] for o in I["objects"]] == [None, "Prop_WZ_EggIncubator"])
add("UCX box on nest and incubator", all(m["collision"][0]["shape"] == "box" and m["collision"][0]["name"].startswith("UCX_") for m in (N, I)))
if "lab_echo" in MODULES:
    import lab_echo as L
    for c in L.extra_checks(allassets):
        add(*c)
for extra in ("lab_fold", "or_parlay"):
    if extra in MODULES:
        for c in importlib.import_module(extra).extra_checks(allassets):
            add(*c)
if "g03_hornback" in MODULES:
    import g03_hornback as H
    for c in H.extra_checks(allassets):
        add(*c)
ok = 0
for n, r, d in checks:
    ok += r
    if not r: print("FAIL %s %s" % (n, d))
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
