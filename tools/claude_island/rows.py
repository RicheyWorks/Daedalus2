# SPDX-License-Identifier: MIT
"""Append a READY row to QUEUE.md for every Claude Island item that has its .blend and no row yet.

    python rows.py <art folder>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import artqueue  # noqa: E402

import types  # noqa: E402
sys.modules.setdefault("bpy", types.ModuleType("bpy"))
sys.modules.setdefault("bmesh", types.ModuleType("bmesh"))
import orr_build  # noqa: E402

SIZE = {"Prop": "0.1-5 m", "Item": "0.1-0.5 m", "Mob": "0.2-1 m", "Bld": "4-15 m", "Tool": "0.5-1 m",
        "Wpn": "0.5-2 m", "Veh": "3-6 m", "Sky": "5-20 m"}


def main(art):
    q = os.path.join(art, "QUEUE.md")
    text = open(q, encoding="utf-8").read()
    have = {r["asset"] for r in artqueue.parse(text)[0]}
    added = 0
    for asset, kind, family, p in orr_build.catalogue():
        if asset in have or not os.path.exists(os.path.join(art, kind, asset + ".blend")):
            continue
        text = artqueue.add_row(text, asset, "READY", "Claude Island (The Orrery Reach)")
        added += 1
    tmp = q + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, q)
    print("rows added: %d" % added)


if __name__ == "__main__":
    main(sys.argv[1])
