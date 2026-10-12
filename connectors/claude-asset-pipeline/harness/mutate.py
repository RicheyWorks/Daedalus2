# SPDX-License-Identifier: MIT
"""Break the pipeline on purpose; the suites must notice every break.

    python3 harness/mutate.py [--e2e] [--list]

Each mutant swaps one anchor (which must match exactly once) in a copy of the package, then runs
judge_test (and e2e, with --e2e) against the copy. A mutant is killed when a suite fails. The results go to
ledgers/mutants.json. Prints n/m killed last; exits 1 if any mutant survived or was inconclusive.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHIP = "asset_pipeline/ship.py"
GLB = "asset_pipeline/glb.py"
SIDES = "asset_pipeline/sides.py"

MUTANTS = [
    ("triangle check always passes", SHIP, 'check("triangles: Blender = file", st == ft,',
     'check("triangles: Blender = file", True,'),
    ("Unreal triangle check always passes", SHIP, 'check("triangles: file = Unreal, mesh by mesh", want == got,',
     'check("triangles: file = Unreal, mesh by mesh", True,'),
    ("an empty shipment passes", SHIP, "len(sent[\"objects\"]) == len(nodes) and len(nodes) > 0",
     "len(sent[\"objects\"]) == len(nodes)"),
    ("units: centimetres not converted", SHIP, "CM_PER_M = 100.0", "CM_PER_M = 1.0"),
    ("size tolerance far too loose", SHIP, "def _close(a, b, rel=0.01,", "def _close(a, b, rel=0.5,"),
    ("slots: bare-mesh default slot ignored", SHIP, 'fslots = sorted(max(1, len(m["materials"])) for m in meshes)',
     'fslots = sorted(len(m["materials"]) for m in meshes)'),
    ("materials check skipped", SHIP, 'check("materials: Blender = file", sm == fm,',
     'check("materials: Blender = file", True,'),
    ("material assets never counted", SHIP, 'len(made["materials"]) >= len(used)', "True"),
    ("glb: non-indexed prims count vertices as triangles", GLB,
     'return acc[prim["attributes"]["POSITION"]]["count"] // 3', 'return acc[prim["attributes"]["POSITION"]]["count"]'),
    ("glb: indexed prims miscounted", GLB, 'return acc[prim["indices"]]["count"] // 3',
     'return acc[prim["indices"]]["count"] // 2'),
    ("export without modifiers", SIDES, "export_apply=True", "export_apply=False"),
    ("Unreal import not automated (dialog)", SIDES, 'task.set_editor_property("automated", True)',
     'task.set_editor_property("automated", False)'),
]


def run(copy, e2e, extra):
    suites = [[sys.executable, os.path.join(copy, "harness", t)] for t in ("glb_test.py", "judge_test.py")]
    if e2e:
        suites.append([sys.executable, os.path.join(copy, "harness", "e2e.py")] + extra)
    for cmd in suites:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if p.returncode != 0:
            fails = [ln for ln in p.stdout.splitlines() if ln.startswith("FAIL")]
            return os.path.basename(cmd[1]), (fails[0] if fails else (p.stdout + p.stderr).strip()[-200:])
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2e", action="store_true", help="also run e2e (needs Blender's bpy and both connectors)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--blender-connector")
    ap.add_argument("--unreal-connector")
    a = ap.parse_args()
    extra = []
    if a.blender_connector:
        extra += ["--blender-connector", os.path.abspath(a.blender_connector)]
    extra += ["--unreal-connector", os.path.abspath(a.unreal_connector or os.path.join(ROOT, "..", "claude-unreal-connector"))]
    if a.list:
        for i, m in enumerate(MUTANTS):
            print(i, m[0])
        return 0
    rows = []
    for name, rel, old, new in MUTANTS:
        copy = os.path.join(tempfile.mkdtemp(prefix="mut-"), "pipe")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", "ledgers"))
        path = os.path.join(copy, rel)
        src = open(path).read()
        n = src.count(old)
        if n != 1:
            rows.append({"mutant": name, "state": "inconclusive", "why": "anchor matches %d times" % n})
        else:
            open(path, "w").write(src.replace(old, new))
            suite, why = run(copy, a.e2e, extra)
            rows.append({"mutant": name, "state": "killed" if suite else "SURVIVED",
                         "by": suite, "why": why if suite else "every suite stayed green"})
        shutil.rmtree(os.path.dirname(copy), ignore_errors=True)
        r = rows[-1]
        print("%-12s %-50s %s" % (r["state"], name, r.get("by") or r["why"]), flush=True)
    killed = sum(r["state"] == "killed" for r in rows)
    os.makedirs(os.path.join(ROOT, "ledgers"), exist_ok=True)
    with open(os.path.join(ROOT, "ledgers", "mutants.json"), "w") as f:
        json.dump({"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "e2e": a.e2e, "killed": killed,
                   "total": len(rows), "mutants": rows}, f, indent=2)
    print("%d/%d" % (killed, len(rows)))
    return 0 if killed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
