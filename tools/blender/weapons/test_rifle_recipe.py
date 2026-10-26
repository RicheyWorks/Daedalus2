# SPDX-License-Identifier: MIT
"""Pure-Python checks of the Wpn_Slice1_Rifle recipe and its pinned manifest (no Blender). Run: python test_rifle_recipe.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rifle_recipe as R  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PINNED = os.path.join(ROOT, "data", "combat", "slice1", "Wpn_Slice1_Rifle.recipe.json")
SPECF = os.path.join(ROOT, "connectors", "claude-asset-pipeline", "specs", "combat-slice-1.json")
passed = total = 0


def check(name, ok):
    global passed, total
    total += 1; passed += bool(ok); print(("PASS " if ok else "FAIL ") + name)


a, b = R.recipe(), R.recipe()
check("same seed gives the same recipe", json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))
check("another seed changes the shape", json.dumps(R.recipe(7)["parts"]) != json.dumps(a["parts"]))
spec = [x for x in json.load(open(SPECF, encoding="utf-8"))["assets"] if x["name"] == R.ASSET][0]
check("recipe caps equal the combat-slice-1 spec", spec["max_triangles"] == R.SPEC["max_triangles"] and spec["sockets"] == R.SPEC["sockets"])
worst = 0; all_ok = True
for s in range(200):
    rc = R.recipe(s); t = sum(q["tris"] for q in rc["parts"]); worst = max(worst, t)
    lo, hi = R.bounds(rc["parts"])
    all_ok &= t <= R.SPEC["max_triangles"] and [k["name"] for k in rc["sockets"]] == ["SOCKET_" + n for n in R.SPEC["sockets"]]
    all_ok &= all(all(lo[k] - 1e-6 <= so["location"][k] <= hi[k] + 1e-6 for k in range(3)) for so in rc["sockets"])
    all_ok &= abs(lo[2]) < 1e-6 and abs(lo[0] + hi[0]) < 1e-6 and abs(lo[1] + hi[1]) < 1e-6
    all_ok &= 0.6 <= hi[1] - lo[1] <= 1.2       # a rifle-length silhouette for every seed
check("200 seeds: <= 40000 tris (worst %d), 4 sockets inside bounds, bottom-centre origin, 0.6-1.2 m long" % worst, all_ok)
mz = {k["name"]: k["location"] for k in a["sockets"]}
check("muzzle is the front-most socket (front = -Y)", mz["SOCKET_Muzzle"][1] == min(v[1] for v in mz.values()))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sockets_sidecar as SS
att = {k["name"]: SS.matrix_to_rotator(SS.desired_frame(k)) for k in a["sockets"]}
check("attach sockets Muzzle/Sight/Grip +X along the barrel (UE [0, 90, 0]), Magazine plain [0, 0, 0] (UEB 48810)",
      att == {"SOCKET_Muzzle": [0.0, 90.0, 0.0], "SOCKET_Sight": [0.0, 90.0, 0.0], "SOCKET_Grip": [0.0, 90.0, 0.0], "SOCKET_Magazine": [0.0, 0.0, 0.0]})
check("triangle formulas: box 44, 16-segment cylinder 60", R.BOX_TRIS == 44 and R.cyl_tris(16) == 60)
check("glTF +Y-up mapping (x, y, z) -> (x, z, -y)", R.to_gltf([1, 2, 3]) == [1, 3, -2])
check("1 to 3 material slots, every part uses one of them", 1 <= len(R.MATERIALS) <= 3 and all(0 <= q["slot"] < len(R.MATERIALS) for q in a["parts"]))
pin = json.load(open(PINNED, encoding="utf-8"))
src = open(os.path.join(HERE, "rifle_recipe.py"), "rb").read()
import hashlib  # noqa: E402
check("pinned manifest matches this recipe file (sha256)", pin["recipe_sha256"] == hashlib.sha256(src.replace(b"\r\n", b"\n")).hexdigest())
check("pinned manifest parts/sockets equal a fresh recipe", pin["parts"] == a["parts"] and [dict((k, v) for k, v in s.items() if k != "location_gltf") for s in pin["sockets"]] == a["sockets"])
check("pinned manifest checks all true and status is source-only", all(pin["checks"].values()) and pin["status"].startswith("SOURCE-ONLY"))
print("%d/%d" % (passed, total))
sys.exit(0 if passed == total else 1)
