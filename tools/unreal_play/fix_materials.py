# SPDX-License-Identifier: MIT
"""Run daedalus_fix_materials.fix inside the open editor through the bridge (not during Play).

    python tools/unreal_play/fix_materials.py [/Game/Daedalus/Art]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def main(argv):
    root = argv[0] if argv else "/Game/Daedalus/Art"
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        print("stop Play first: saving assets is an editor operation")
        return 2
    code = "import importlib, daedalus_fix_materials as M\nimportlib.reload(M)\nprint(M.fix(%r))\n" % root
    r = wire.call(wire.UNREAL, "execute_python", code=code, timeout=1800)
    print((r.get("stdout") or "")[-3000:])
    err = r.get("stderr") or r.get("error") or ""
    if err:
        print("ERR", err[:1000])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
