# SPDX-License-Identifier: MIT
"""Move a realm's district actors into streamed D<dd> sublevels (ADR-063), save each, write islands.json.

    python tools/unreal_play/stream_realm.py LABYRINTH
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def main(argv):
    realms = (argv[0] if argv else "LABYRINTH").split(",")
    for realm in realms:
        rc = one(realm)
        if rc:
            return rc
    return 0


def one(realm):
    while wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        time.sleep(5)
    t0 = time.time()
    code = ("import importlib, daedalus_plots, daedalus_districts, daedalus_islands\nimportlib.reload(daedalus_districts)\nimportlib.reload(daedalus_islands)\n"
            "def steps():\n    return (yield from daedalus_districts.steps(%r))\n" % realm)
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="stream " + realm, timeout=3600)
    for line in r.get("yielded", [])[-3:]:
        print("  " + line, flush=True)
    print("%s: steps=%s seconds=%s error=%s result=%s" % (realm, r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-400:], str(r.get("result"))[:300]), flush=True)
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", "status", "--topic", "streaming", "--text",
                        "STREAMING %s: %s in %.0f s error=%s" % (realm, str(r.get("result"))[:200], time.time() - t0, (r.get("error") or "-")[-120:])],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 1 if r.get("error") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
