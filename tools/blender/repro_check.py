# SPDX-License-Identifier: MIT
"""Build a land recipe twice, in two separate processes, and compare every exported GLB byte for byte.

    python repro_check.py RECIPE [--rev rN] [--python PATH_TO_BPY_PYTHON]

RECIPE is a module in tools/blender with build(out_dir[, rev]) (tidepen_shelf, reedwheel_haven, ...). Two fresh
processes catch what one cannot: per-process salts (str hash), and Blender operators whose output order varies run
to run (bmesh create_uvsphere did; see AUTOMATION-LESSONS). FBX is skipped: it embeds a timestamp.
Last line "REPRO n/m PASS|FAIL"; exit 0 only on PASS.
"""
import hashlib
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def digests(d):
    return {f: hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest() for f in sorted(os.listdir(d)) if f.endswith(".glb")}


def main(argv):
    recipe = argv[0]
    py = argv[argv.index("--python") + 1] if "--python" in argv else sys.executable
    rev = ["--rev", argv[argv.index("--rev") + 1]] if "--rev" in argv else []
    runs = []
    with tempfile.TemporaryDirectory() as tmp:
        for k in ("a", "b"):
            out = os.path.join(tmp, k)
            r = subprocess.run([py, os.path.join(HERE, recipe + ".py"), out] + rev, cwd=HERE, capture_output=True, text=True)
            if r.returncode:
                print(r.stdout[-2000:], r.stderr[-2000:])
                print("REPRO 0/1 FAIL (build %s failed)" % k)
                return 1
            runs.append(digests(out))
    a, b = runs
    names = sorted(set(a) | set(b))
    ok = 0
    for n in names:
        same = a.get(n) == b.get(n)
        ok += same
        print(("ok   " if same else "FAIL ") + n + ("" if same else "  %s != %s" % (str(a.get(n))[:12], str(b.get(n))[:12])))
    print("REPRO %d/%d %s" % (ok, len(names), "PASS" if ok == len(names) and names else "FAIL"))
    return 0 if ok == len(names) and names else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
