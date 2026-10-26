# SPDX-License-Identifier: MIT
"""Export the land ledger from the live editor (every laid island per realm) and copy it into the repo under
docs/production/lands/<realm>.json for Sol's mint row / server. Posts a hub status with counts and hashes.

    python tools/realm/export_ledger.py [WORLD-ZERO,GALLERY-CITY,...]
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

OUT = os.path.join(REPO, "docs", "production", "lands")


def main(argv):
    realms = (argv[0] if argv else "WORLD-ZERO,GALLERY-CITY,PARCELS,BRICKS,LABYRINTH").split(",")
    while wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        time.sleep(10)
    code = ("import importlib, daedalus_districts\nimportlib.reload(daedalus_districts)\n"
            "def steps():\n    return (yield from daedalus_districts.export_ledger_steps(%r))\n" % realms)
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="ledger", timeout=1800)
    res = r.get("result") or {}
    print("ledger: steps=%s seconds=%s error=%s" % (r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-300:]), flush=True)
    os.makedirs(OUT, exist_ok=True)
    parts = []
    for realm, info in res.items():
        dst = os.path.join(OUT, os.path.basename(info["path"]))
        shutil.copyfile(info["path"], dst)
        parts.append("%s %d (sha %s)" % (realm, info["rows"], info["sha256"]))
        print("%s: %d lands, %d districts + %d single actors -> %s" % (realm, info["rows"], info["districts"], info["single_actors"], dst), flush=True)
    index = {"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "realms": {k: {"rows": v["rows"], "sha256": v["sha256"]} for k, v in res.items()}}
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    msg = "LAND LEDGER exported (docs/production/lands/<realm>.json, fields deed/realm/district/cell/x_cm/y_cm/top_cm/thick_m/props): %s" % "; ".join(parts)
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "team-codex", "--type", "request", "--topic", "mint", "--text",
                        msg + ". Sol: this is the mint row's input (BASE-LAYER row 4) — please read it from the repo for /api/v1/realms/{R}/lands and tell me any field the contract needs that is missing."],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 1 if r.get("error") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
