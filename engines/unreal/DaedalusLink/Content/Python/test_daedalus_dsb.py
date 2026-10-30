# SPDX-License-Identifier: MIT
"""Offline test of daedalus_dsb (island costs + DSB 1 writer). Run: python test_daedalus_dsb.py
With a Java/C++ DSB parser available, the written text is also checked against the real grammar (see tools)."""
import re

import daedalus_dsb as d


def test():
    ok = total = 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        ok += bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    taken = set()
    check("id from the package leaf", d.island_id("/Game/Claude/ClaudeIsland_Sub", taken) == "ClaudeIsland_Sub")
    check("same leaf twice gets a suffix", d.island_id("/Other/ClaudeIsland_Sub", taken) == "ClaudeIsland_Sub_2")
    check("bad characters become _", d.island_id("/Game/Bufff-ff Isle.v2", set()) == "Bufff_ff_Isle_v2")
    long_id = d.island_id("/Game/" + "x" * 80, {"x" * 64})
    check("ids stay within 64 even with a suffix", len(long_id) == 64 and long_id.endswith("_2"))

    graph = {"/Game/A/Map": ["/Game/A/Rock", "/Game/Shared/Tex", "/Script/Engine"],
             "/Game/A/Rock": ["/Game/Shared/Tex", "/Game/A/Map"], "/Game/Shared/Tex": []}
    sizes = {"/Game/A/Map": 1000, "/Game/A/Rock": 5000, "/Game/Shared/Tex": 4096, "/Script/Engine": 10 ** 9}
    total_b, n = d.package_cost("/Game/A/Map", graph.get, sizes.get)
    check("cost walks /Game deps once each, skips /Script, survives cycles", (total_b, n) == (10096, 3))
    check("KiB rounds up and is at least 1", d.kib(10096) == 10 and d.kib(0) == 1 and d.kib(10 ** 15) == d.MAX_KIB)

    rows = [{"package": "/Game/Zed/Isle", "x": 1.6, "y": -2.4, "ram_kib": 300, "disk_kib": 300},
            {"package": "/Game/Claude/ClaudeIsland_Sub", "x": 400000, "y": 0, "ram_kib": 0, "disk_kib": 5e9},
            {"package": "/Game/A/a", "x": 3e12, "y": 0}]
    text = d.write_dsb(rows)
    lines = text.splitlines()
    check("header first, LF endings", lines[0] == "DSB 1" and text.endswith("\n") and "\r" not in text)
    check("sorted by id in byte order", [l.split()[1] for l in lines[1:]] == ["ClaudeIsland_Sub", "Isle", "a"])
    grammar = re.compile(r"^island [A-Za-z0-9_]{1,64} x (0|-?[1-9][0-9]*) y (0|-?[1-9][0-9]*) ram [1-9][0-9]* disk [1-9][0-9]*$")
    check("every line matches DSB 1's grammar", all(grammar.match(l) for l in lines[1:]))
    check("ram/disk clamped to 1..1e8, cm to +-1e9", "ram 1 disk 100000000" in text and "x 1000000000" in text)
    check("x/y rounded to whole cm", "x 2 y -2 " in text)
    print("%d/%d" % (ok, total))
    return ok == total


if __name__ == "__main__":
    raise SystemExit(0 if test() else 1)
