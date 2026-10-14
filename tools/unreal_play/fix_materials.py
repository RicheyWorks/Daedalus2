# SPDX-License-Identifier: MIT
"""Move every shipped material instance onto the project's flagged base (ADR-055, daedalus_nanite_materials) until
none is left on the engine plugin's, in batches, through the bridge. Not during Play (saving is an editor op).

    python tools/unreal_play/fix_materials.py [batch=200] [max_batches=200]

2026-10-13: 13,579 instances under /Game/Daedalus/Art were still parented to /InterchangeAssets/.../MI_Default_Opaque_DS,
whose base can't be saved with usage flags: 340 "will recompile every editor launch" warnings per Play and the
default grey material in a packaged game. The tool existed; this runs it to zero and prints the count each pass.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def main(argv):
    batch = int(argv[0]) if argv else 200
    max_batches = int(argv[1]) if len(argv) > 1 else 200
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        print("stop Play first: saving assets is an editor operation")
        return 2
    status = "import daedalus_nanite_materials as n\nprint(n.status())\n"
    r = wire.call(wire.UNREAL, "execute_python", code=status, timeout=600)
    print("before:", (r.get("stdout") or "").strip()[-200:], flush=True)
    for i in range(max_batches):
        r = wire.call(wire.UNREAL, "execute_python", code="import daedalus_nanite_materials as n\nprint(n.run(%d))\n" % batch, timeout=1800)
        out = (r.get("stdout") or "").strip()
        err = r.get("stderr") or r.get("error") or ""
        print("pass %d: %s %s" % (i + 1, out[-200:], ("ERR " + err[:300]) if err else ""), flush=True)
        if err or "'left': 0" in out or "left=0" in out or out.endswith("0}"):
            break
    r = wire.call(wire.UNREAL, "execute_python", code=status, timeout=600)
    after = (r.get("stdout") or "").strip()
    print("after:", after[-200:], flush=True)
    return 0 if "'left': 0" in after or "left=0" in after else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
