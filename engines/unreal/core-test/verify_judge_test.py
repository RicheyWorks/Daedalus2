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
        "unmaterialed": 0, "ark": True, "plugin": True,
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
expect("a material missing", dict(GOOD, materials=["M_DaedalusOpaque"]), ["materials"])
expect("a chunk missing", dict(GOOD, chunk_actors=2), ["chunk meshes"])
expect("a chunk too many (stacked re-import)", dict(GOOD, chunk_actors=6), ["chunk meshes"])
expect("a chunk with an empty material slot", dict(GOOD, unmaterialed=1), ["materials on every chunk"])
expect("no ark", dict(GOOD, ark=False), ["ark mesh"])
expect("live actor on the wrong server", dict(GOOD, live=[{"server_url": "http://elsewhere:8088", "world_id": "world-zero"}]), ["live actor"])
expect("two live actors", dict(GOOD, live=GOOD["live"] * 2), ["live actor"])
expect("no live actor", dict(GOOD, live=[]), ["live actor"])
expect("plugin not compiled: live actor skipped, not failed", dict(GOOD, plugin=False, live=[]), [])
expect("--live: no chunks expected", dict(GOOD, chunk_actors=0), [], live_only=True)
expect("an empty world: zero chunks is right", dict(GOOD, chunk_actors=0), [],
       manifest=dict(MANIFEST, geometry={"chunks": 0}))

print("%d/%d" % (passed, total))
sys.exit(0 if passed == total else 1)
