# SPDX-License-Identifier: MIT
"""Contest placement in the background (imports cost 10-19 s each on a loaded PC, past the bridge's 60 s cap):

    python tools/unreal_play/claude_islands.py <start> <stop> [chunk] [realm]      e.g. 250 300 4
    (via engines\\unreal\\pc-job.ps1 -Start -Script tools\\unreal_play\\claude_islands.py -ScriptArgs "250 300")

Each chunk is one daedalus.steps call: place_batch(seeds) then save the island assets; the level is saved once at
the end (one save under memory pressure, not many). Prints the running tally and posts it on the hub.
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
    start, stop = int(argv[0]), int(argv[1])
    chunk = int(argv[2]) if len(argv) > 2 else 4
    realm = argv[3] if len(argv) > 3 else "WORLD-ZERO"
    t0 = time.time()
    placed = 0
    for s in range(start, stop, chunk):
        seeds = list(range(s, min(s + chunk, stop)))
        code = ("import importlib, daedalus_claude_islands as C\nimportlib.reload(C)\n"
                "def steps():\n    r = C.place_batch(%r, realm=%r)\n    yield\n    return {'placed': [p['seed'] for p in r if not p.get('error')], 'errors': [(p['seed'], p['error']) for p in r if p.get('error')], 'count': C.count()['islands']}\n" % (seeds, realm))
        r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="claude islands %d" % s, timeout=1800)
        res = r.get("result") or {}
        placed += len(res.get("placed") or [])
        print("%s..%s: placed=%s errors=%s total=%s %.0fs error=%s" % (seeds[0], seeds[-1], len(res.get("placed") or []), res.get("errors"), res.get("count"), r.get("seconds") or 0, (r.get("error") or "-")[-200:]), flush=True)
        if r.get("error"):
            return 1
    r = wire.call(wire.UNREAL, "daedalus.steps", code="import daedalus_plots\ndef steps():\n    yield\n    return daedalus_plots.save_world()\n", label="save", timeout=900)
    msg = "CONTEST team Claude: %d islands placed (%d..%d) in %.0f s, level saved=%s" % (placed, start, stop - 1, time.time() - t0, (r.get("result"), r.get("error")))
    print(msg, flush=True)
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--me", "unreal-team", "--to", "*", "--type", "status", "--topic", "island-contest", "--text", msg],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
