# SPDX-License-Identifier: MIT
"""Great detail in chunks (Richey 09:00: "chunks of 10 at first then scale up").

    python tools/unreal_play/detail_islands.py WORLD-ZERO <start> <limit> [chunk]
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

GROUND = "/Game/Daedalus/Art/Islands/PilotMaterials/M_WZ_GroveGround_v1.M_WZ_GroveGround_v1"


def main(argv):
    realm, start, limit = argv[0], int(argv[1]), int(argv[2])
    chunk = int(argv[3]) if len(argv) > 3 else 100
    t0 = time.time()
    done = 0
    while done < limit:
        n = min(chunk, limit - done)
        code = ("import importlib, daedalus_plots, daedalus_districts\nimportlib.reload(daedalus_districts)\n"
                "def steps():\n    return (yield from daedalus_districts.detail_islands_steps(%r, limit=%d, start=%d, ground_material=%r))\n" % (realm, n, start + done, GROUND if realm == "WORLD-ZERO" else None))
        r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="detail %s %d" % (realm, start + done), timeout=3600)
        res = r.get("result") or {}
        print("%s %d..%d: islands=%s props=%s actors=%s %.0fs error=%s" % (realm, start + done, start + done + n, res.get("islands"), res.get("props"), res.get("actors"), r.get("seconds") or 0, (r.get("error") or "-")[-200:]), flush=True)
        if r.get("error") or not res.get("islands"):
            return 1
        done += res["islands"]
        if res["islands"] < n:
            break
    msg = "DETAIL %s: %d islands from %d in %.0f s" % (realm, done, start, time.time() - t0)
    print(msg, flush=True)
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", "status", "--topic", "islands", "--text", msg],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
