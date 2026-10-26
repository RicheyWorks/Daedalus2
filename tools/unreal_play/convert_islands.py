# SPDX-License-Identifier: MIT
"""Convert a realm's old per-plot slab actors into instanced, dressed districts (default GALLERY-CITY).

    python tools/unreal_play/convert_islands.py [REALM]
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
    realm = argv[0] if argv else "GALLERY-CITY"
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        wire.call(wire.UNREAL, "stop", timeout=60)
        time.sleep(3)
    t0 = time.time()
    code = ("import importlib, daedalus_plots, daedalus_districts, daedalus_realm_ground\nimportlib.reload(daedalus_plots)\nimportlib.reload(daedalus_districts)\n"
            "def steps():\n    return (yield from daedalus_districts.convert_steps(%r))\n" % realm)
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="convert " + realm, timeout=3600)
    for line in r.get("yielded", [])[-3:]:
        print("  " + line, flush=True)
    print("%s: steps=%s seconds=%s error=%s result=%s" % (realm, r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-400:], str(r.get("result"))[:400]), flush=True)
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", "status", "--topic", "islands", "--text",
                        "ISLANDS converted %s: %s in %.0f s error=%s" % (realm, str(r.get("result"))[:300], time.time() - t0, (r.get("error") or "-")[-120:])],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 1 if r.get("error") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
