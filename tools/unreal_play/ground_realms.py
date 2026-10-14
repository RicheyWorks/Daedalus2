# SPDX-License-Identifier: MIT
"""Solid ground under every district of the four 3D realms (no gaps), then save.  python tools/unreal_play/ground_realms.py"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def main(argv):
    while wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        time.sleep(5)
    code = ("import importlib, daedalus_districts\nimportlib.reload(daedalus_districts)\n"
            "def steps():\n    return (yield from daedalus_districts.ground_steps())\n")
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="ground", timeout=1800)
    print("ground: steps=%s seconds=%s error=%s result=%s" % (r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-300:], r.get("result")), flush=True)
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", "status", "--topic", "islands", "--text",
                        "ISLANDS ground restored under every district of the 3D realms (no gaps; World Zero stays floating): %s error=%s" % (r.get("result"), (r.get("error") or "-")[-100:])],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 1 if r.get("error") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
