# SPDX-License-Identifier: MIT
"""The Unreal import verifier's judgement (import_world_package.judge), tested outside the editor.

A good project passes every check, and each way a project can be wrong fails exactly the check that
names it. That way the verifier can be shown able to say no. Prints n/m last; exits 1 on a failure.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "iwp", os.path.join(HERE, "..", "DaedalusLink", "Content", "Python", "import_world_package.py"))
iwp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iwp)

MANIFEST = {
    "world": {"id": "world-zero", "title": "World Zero", "revision": 7},
    "geometry": {"chunks": 3},
    "assets": [{"name": "ark", "file": "assets/ark.glb"}],
    "live": {"api": "http://localhost:8088/api/v1/world/world-zero"},
}
GOOD = {"level": True, "materials": ["M_DaedalusOpaque", "M_DaedalusTranslucent"], "chunk_actors": 3,
        "unmaterialed": 0, "ark": True, "plugin": True, "view": True,
        "sky": ["DirectionalLight", "SkyAtmosphere", "SkyLight", "ExponentialHeightFog"],
        "live": [{"server_url": "http://localhost:8088", "world_id": "world-zero"}]}

passed = total = 0


def expect(label, facts, failing, live_only=False, manifest=MANIFEST):
    global passed, total
    total += 1
    checks = iwp.judge(manifest, facts, live_only=live_only)
    got = sorted(c["name"] for c in checks if not c["ok"])
    if got == sorted(failing):
        passed += 1
        print("PASS", label)
    else:
        print("FAIL", label, "expected failing", sorted(failing), "got", got, checks)


expect("a complete import passes every check", GOOD, [])
expect("no level", dict(GOOD, level=False), ["level"])
expect("no sun (a new level renders every mesh black)", dict(GOOD, sky=["SkyAtmosphere", "SkyLight"]), ["lit"])
expect("no sky light", dict(GOOD, sky=["DirectionalLight"]), ["lit"])
expect("a material missing", dict(GOOD, materials=["M_DaedalusOpaque"]), ["materials"])
expect("a chunk missing", dict(GOOD, chunk_actors=2), ["chunk meshes"])
expect("a chunk too many (stacked re-import)", dict(GOOD, chunk_actors=6), ["chunk meshes"])
expect("a chunk with an empty material slot", dict(GOOD, unmaterialed=1), ["materials on every chunk"])
expect("no ark", dict(GOOD, ark=False), ["ark mesh"])
expect("no view (Play would open on empty sky)", dict(GOOD, view=False), ["view"])
expect("live actor on the wrong server", dict(GOOD, live=[{"server_url": "http://elsewhere:8088", "world_id": "world-zero"}]), ["live actor"])
expect("two live actors", dict(GOOD, live=GOOD["live"] * 2), ["live actor"])
expect("no live actor", dict(GOOD, live=[]), ["live actor"])
expect("plugin not compiled: live actor skipped, not failed", dict(GOOD, plugin=False, live=[]), [])
expect("--live: no chunks expected", dict(GOOD, chunk_actors=0), [], live_only=True)
expect("an empty world: zero chunks is right, and no view is needed", dict(GOOD, chunk_actors=0, view=False), [],
       manifest=dict(MANIFEST, geometry={"chunks": 0}))

# The report lands where setup-unreal.ps1 reads it: <Saved>/Daedalus/verify-<world id>.json, id unchanged.
import json
import tempfile
total += 1
with tempfile.TemporaryDirectory() as saved:
    ok = iwp.report(MANIFEST, iwp.judge(MANIFEST, GOOD), saved)
    where = os.path.join(saved, "Daedalus", "verify-world-zero.json")
    if ok and os.path.isfile(where) and json.load(open(where))["ok"] is True:
        passed += 1
        print("PASS the report is written as verify-world-zero.json, the name setup-unreal.ps1 reads")
    else:
        print("FAIL the report is not at", where, os.listdir(os.path.join(saved, "Daedalus")))

# The view point looks at the middle of the world from outside it, above it, from the south-west.
spec2 = importlib.util.spec_from_file_location(
    "dv", os.path.join(HERE, "..", "DaedalusLink", "Content", "Python", "daedalus_view.py"))
dv = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(dv)
total += 1
lo, hi = (10000.0, -5000.0, 2000.0), (30000.0, 15000.0, 8000.0)
(x, y, z), (pitch, yaw) = dv.view_point(lo, hi)
cx, cy, cz = 20000.0, 5000.0, 5000.0
import math
look = (math.cos(math.radians(pitch)) * math.cos(math.radians(yaw)),
        math.cos(math.radians(pitch)) * math.sin(math.radians(yaw)), math.sin(math.radians(pitch)))
to = (cx - x, cy - y, cz - z)
n = math.sqrt(sum(t * t for t in to))
aim = sum(a * b / n for a, b in zip(look, to))
outside = not (lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1])
if aim > 0.999 and outside and z > hi[2] and x < cx and y < cy:
    passed += 1
    print("PASS the view point is outside the world, above it, and aimed at its middle (cos %.4f)" % aim)
else:
    print("FAIL view point", (x, y, z), (pitch, yaw), "aim", aim)

print("%d/%d" % (passed, total))
sys.exit(0 if passed == total else 1)

