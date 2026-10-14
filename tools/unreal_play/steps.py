# SPDX-License-Identifier: MIT
"""Run any editor generator through daedalus.steps: one bridge round trip, one editor tick per item.

    python tools/unreal_play/steps.py daedalus_districts.steps GALLERY-CITY
    python tools/unreal_play/steps.py daedalus_districts.lay_district_steps PARCELS "list(range(0,100))" "set()"
    python tools/unreal_play/steps.py daedalus_nanite_materials.steps 25

Arguments after the module.function are Python expressions evaluated in the editor (a bare word is a string).
Prints the last 30 yielded lines, the step count, seconds, and the result; exits 1 on an error in a step.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def literal(a):
    try:
        compile(a, "<arg>", "eval")
        return a if any(c in a for c in "()[]{}\"',0123456789.") and not a.isalpha() else repr(a)
    except SyntaxError:
        return repr(a)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    mod, fn = argv[0].rsplit(".", 1)
    args = ", ".join(literal(a) for a in argv[1:])
    code = ("import importlib, %s\nimportlib.reload(%s)\n"
            "def steps():\n    return (yield from %s.%s(%s))\n") % (mod, mod, mod, fn, args)
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        print("stop Play first: editor jobs do not run during Play")
        return 2
    t0 = time.time()
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=argv[0], timeout=7200)
    for line in r.get("yielded", [])[-30:]:
        print("  " + line, flush=True)
    print("steps=%s seconds=%s wall=%.0f error=%s" % (r.get("steps"), r.get("seconds"), time.time() - t0, (r.get("error") or "-")[-600:]), flush=True)
    print("result:", r.get("result"), flush=True)
    return 1 if r.get("error") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
