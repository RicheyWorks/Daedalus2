# SPDX-License-Identifier: MIT
"""Combat slice to-do report + sample fixtures: no Blender, no Unreal, no editor.

    python harness/combat_report_test.py      # n/m last; exit 1 on any failure
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from asset_pipeline import combat_fixtures as cf  # noqa: E402
from asset_pipeline import combat_handoff as ch  # noqa: E402
from asset_pipeline import combat_report as cr  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%-4s  %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  " + str(detail)))


SPEC = os.path.join(HERE, "specs", "combat-slice-1.json")
DEFECT_TARGET = {"socket": "Wpn_Slice1_Rifle", "skin": "Enemy_Slice1_Guard", "joints": "Enemy_Slice1_Scout",
                 "lods": "Enemy_Slice1_Guard", "lod-order": "Enemy_Slice1_Brute", "tris": "Enemy_Slice1_Brute",
                 "collision": "Env_Slice1_Arena", "nocollision": "Env_Slice1_Arena", "broken": "Env_Slice1_Arena"}
d = tempfile.mkdtemp()

# 1. nothing built yet (today's real state): every asset MISSING with the export path, exit 1
empty = os.path.join(d, "empty")
os.makedirs(empty)
t = cr.build(SPEC, empty)
check("empty folder: 5 MISSING, not ok", t["counts"] == {"MISSING": 5, "FIX": 0, "READY": 0} and not t["ok"], t["counts"])
check("empty folder: to-do names the exact glb path",
      os.path.join(empty, "glb", "Wpn_Slice1_Rifle.glb") in t["assets"][0]["todo"][0], t["assets"][0]["todo"])
check("cli: exit 1 and files written", cr.main(["--spec", SPEC, "--folder", empty, "--out", os.path.join(d, "o1")]) == 1
      and os.path.exists(os.path.join(d, "o1", "TODO-FOR-BLENDER-TEAM.md")) and os.path.exists(os.path.join(d, "o1", "todo.json")))

# 2. fixtures: the sample slice passes the real harness and the report says READY, exit 0
good = os.path.join(d, "good")
paths = cf.build_slice(SPEC, good)
check("fixtures: 5 glbs written under glb/", len(paths) == 5 and all(os.path.exists(p) for p in paths))
check("fixtures: sample slice PASSes the combat harness", ch.run(SPEC, good)["verdict"] == "PASS")
t = cr.build(SPEC, good)
check("good slice: 5 READY, ok, no to-dos", t["counts"]["READY"] == 5 and t["ok"] and not any(i["todo"] for i in t["assets"]), t["counts"])
check("cli: exit 0 on a ready slice", cr.main(["--spec", SPEC, "--folder", good]) == 0)

# 3. every defect fails exactly its asset, turns it into FIX, and gives an actionable instruction
WANT = {"socket": "SOCKET_Magazine", "skin": "armature", "joints": "hand_r", "lods": "_LOD", "lod-order": "Decimate",
        "tris": "Cut triangles", "collision": "UCX_", "nocollision": "UCX_", "broken": "Re-export"}
for kind, target in DEFECT_TARGET.items():
    p = os.path.join(d, "def-" + kind)
    cf.build_slice(SPEC, p, {target: kind})
    t = cr.build(SPEC, p)
    bad = [i["name"] for i in t["assets"] if i["state"] != "READY"]
    item = [i for i in t["assets"] if i["name"] == target][0]
    check("defect %-11s -> only %s is FIX" % (kind, target), bad == [target] and item["state"] == "FIX", (bad, item["state"]))
    check("defect %-11s -> to-do says what to do" % kind, any(WANT[kind] in x for x in item["todo"]), item["todo"])

# 4. partly delivered: weapon built, the rest missing; the markdown table and per-asset sections
part = os.path.join(d, "part")
cf.build_slice(SPEC, part)
for n in ("Enemy_Slice1_Guard", "Enemy_Slice1_Scout", "Enemy_Slice1_Brute", "Env_Slice1_Arena"):
    os.remove(os.path.join(part, "glb", n + ".glb"))
q = os.path.join(d, "QUEUE.md")
with open(q, "w", encoding="utf-8") as f:
    f.write("# Art queue\n\n| # | Asset | Kind | Size | Status | Notes |\n|---|---|---|---|---|---|\n"
            "| 1 | Tool_Pickaxe | tool | 0.9 m | SHIPPED (440 tris) | x |\n"
            "| 2 | Wpn_Slice1_Rifle | wpn |  | READY | slice 1 |\n"
            "| 3 | Enemy_Slice1_Guard | enemy |  | DOING (blender-team) | rig |\n")
check("queue_rows reads Asset and Status columns, skips the separator",
      cr.queue_rows(q) == {"Tool_Pickaxe": "SHIPPED (440 tris)", "Wpn_Slice1_Rifle": "READY", "Enemy_Slice1_Guard": "DOING (blender-team)"}, cr.queue_rows(q))
check("queue_rows tolerates a missing file", cr.queue_rows(os.path.join(d, "none.md")) == {} and cr.queue_rows(None) == {})
t = cr.build(SPEC, part, q)
md = cr.markdown(t)
check("part: 1 READY, 4 MISSING", t["counts"] == {"MISSING": 4, "FIX": 0, "READY": 1}, t["counts"])
check("markdown: queue status shown, absent row flagged",
      "| Wpn_Slice1_Rifle | weapon | **READY** | READY |" in md and "| Enemy_Slice1_Scout | enemy | **MISSING** | (no row yet) |" in md, md[:900])
check("markdown: requirements spelled out from the spec",
      "SOCKET_Magazine" in md and ">= 20 bones incl. root, pelvis, head, hand_r; 3 LODs" in md and ">= 4 collision hulls" in md)
check("markdown: READY asset gets no to-do section", "## Wpn_Slice1_Rifle" not in md and "## Enemy_Slice1_Guard (MISSING)" in md)
check("json is serializable without the spec copy",
      "spec_assets" not in json.load(open(os.path.join(d, "o1", "todo.json"))))

# 5. bad inputs
check("missing spec file: exit 2", cr.main(["--spec", os.path.join(d, "nope.json"), "--folder", d]) == 2)
bad = os.path.join(d, "bad.json")
json.dump({"schema": "x", "assets": [{}]}, open(bad, "w"))
check("bad spec schema: exit 2", cr.main(["--spec", bad, "--folder", d]) == 2)
try:
    cf.build_slice(SPEC, os.path.join(d, "z"), {"Wpn_Slice1_Rifle": "bogus"})
    check("fixtures: unknown defect refused", False)
except ValueError as e:
    check("fixtures: unknown defect refused", "bogus" in str(e), e)
check("fixtures cli: --defect works", cf.main(["--spec", SPEC, "--out", os.path.join(d, "c"), "--defect", "Wpn_Slice1_Rifle=socket"]) == 0
      and not ch.run(SPEC, os.path.join(d, "c"))["ok"])
shutil.rmtree(d)

n = sum(results)
print("%d/%d" % (n, len(results)))
sys.exit(0 if n == len(results) else 1)