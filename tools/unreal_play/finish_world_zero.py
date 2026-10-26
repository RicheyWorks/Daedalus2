# SPDX-License-Identifier: MIT
"""World Zero's 10k NFT islands (Richey 2026-10-14 00:46: "get all these islands done"): first remove the duplicate
district actors a rerun left in Bricks/Labyrinth, then lay every district 0..99 of World Zero as instanced plot
actors round the live hub (estates and hub cells skipped), 20 districts per daedalus.steps call, a hub status per
batch. Idempotent by label.

    python tools/unreal_play/finish_world_zero.py [--no-dedupe]
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def hub(text):
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", "status", "--topic", "islands", "--text", text],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass


def steps(expr, label, timeout=3600):
    code = ("import importlib, daedalus_plots, daedalus_districts\nimportlib.reload(daedalus_plots)\nimportlib.reload(daedalus_districts)\n"
            "def steps():\n    return (yield from %s)\n" % expr)
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=label, timeout=timeout)
    for line in r.get("yielded", [])[-2:]:
        print("  " + line, flush=True)
    print("%s: steps=%s seconds=%s error=%s result=%s" % (label, r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-300:], r.get("result")), flush=True)
    return r


def main(argv):
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        wire.call(wire.UNREAL, "stop", timeout=60)
        time.sleep(3)
    t0 = time.time()
    if "--no-dedupe" not in argv:
        r = steps("daedalus_districts.dedupe_steps(['GALLERY-CITY','PARCELS','BRICKS','LABYRINTH'])", "dedupe", 900)
        hub("ISLANDS dedupe: %s" % r.get("result"))
    total = 0
    for start in range(0, 100, 20):
        ds = list(range(start, start + 20))
        r = steps("daedalus_districts.lay_district_steps('WORLD-ZERO', %r)" % ds, "WZ districts %d-%d" % (ds[0], ds[-1]), 1800)
        res = r.get("result") or {}
        total += (res.get("plots") or 0) if isinstance(res, dict) else 0
        hub("ISLANDS World Zero districts %d-%d: %s plots so far, %.0f s, error=%s" % (ds[0], ds[-1], total, time.time() - t0, (r.get("error") or "-")[-120:]))
        if r.get("error"):
            return 1
    print("World Zero: %d plots laid in %.0f s" % (total, time.time() - t0), flush=True)
    hub("ISLANDS World Zero done: %d new plots in %.0f s" % (total, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
