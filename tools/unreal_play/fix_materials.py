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
    chunk = min(int(argv[0]) if argv else 25, 50)
    limit = int(argv[1]) if len(argv) > 1 else None
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        print("stop Play first: saving assets is an editor operation")
        return 2
    r = wire.call(wire.UNREAL, "execute_python", code="import importlib, daedalus_nanite_materials as n\nimportlib.reload(n)\nprint(n.status())\n", timeout=600)
    print("before:", (r.get("stdout") or "").strip()[-200:], flush=True)
    # One bridge call for the whole run: daedalus.steps advances the generator one editor tick per chunk.
    code = "import daedalus_nanite_materials as n\ndef steps():\n    return (yield from n.steps(chunk=%d, limit=%r))\n" % (chunk, limit)
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="fix_materials", timeout=7200)
    for line in r.get("yielded", [])[-5:]:
        print("  " + line, flush=True)
    print("steps=%s seconds=%s error=%s" % (r.get("steps"), r.get("seconds"), (r.get("error") or "")[-400:]), flush=True)
    print("after:", r.get("result"), flush=True)
    res = r.get("result") or {}
    return 0 if not r.get("error") and res.get("left") == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
