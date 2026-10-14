# SPDX-License-Identifier: MIT
"""Start Play, sample the frame time a few times, stop. Prints fps.

    python tools/unreal_play/fps_probe.py [warmup_s]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

CODE = "import unreal, daedalus_play\nw = daedalus_play.world()\nprint('dt=%.4f' % unreal.GameplayStatics.get_world_delta_seconds(w))\n"


def main(argv):
    warm = int(argv[0]) if argv else 15
    if not wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        wire.call(wire.UNREAL, "play", timeout=30)
    time.sleep(warm)
    dts = []
    for _ in range(5):
        r = wire.call(wire.UNREAL, "execute_python", code=CODE, timeout=30)
        out = r.get("stdout") or ""
        if "dt=" in out:
            dts.append(float(out.split("dt=")[1].split()[0]))
        time.sleep(1.5)
    wire.call(wire.UNREAL, "stop", timeout=30)
    if dts:
        print("fps %.1f (dt %s)" % (len(dts) / sum(dts), " ".join("%.3f" % d for d in dts)))
    else:
        print("no samples: %s" % r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
