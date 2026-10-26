# SPDX-License-Identifier: MIT
"""Island costs for streaming, with no Unreal import, so it runs and tests offline (test_daedalus_dsb.py).

daedalus_islands.write() uses it to give every islands.json row a `ram_kib` and to write the same islands as a DSB 1
manifest (disk-saver's ADR-063 format), so the C++ streamer and the Java budget planner read one set of numbers.

Cost of an island = the bytes on disk of its level package plus every /Game package it depends on, walked once
(shared assets counted once per island). RAM is estimated 1:1 from disk until a turn measures the real number;
cooked textures and meshes load at about their on-disk size, and the estimate errs high, which is the safe side
for a budget.
"""
import math
import re

GAME = "/Game/"
RAM_PER_DISK = 1.0          # estimate; replaced by measured RAM when a turn reports it
MAX_KIB = 100_000_000       # DSB 1's limit
MAX_CM = 1_000_000_000
_ID_BAD = re.compile(r"[^A-Za-z0-9_]")


def island_id(package, taken):
    """A DSB id from a package path: its last segment, letters/digits/_ only, at most 64, unique within `taken`."""
    leaf = package.rstrip("/").split("/")[-1] or "island"
    base = _ID_BAD.sub("_", leaf)[:64] or "island"
    out, n = base, 2
    while out in taken:
        tail = "_%d" % n
        out = base[:64 - len(tail)] + tail
        n += 1
    taken.add(out)
    return out


def package_cost(package, deps, size):
    """Bytes of `package` and everything under /Game it reaches. deps(pkg) -> [pkg], size(pkg) -> bytes or 0."""
    seen, todo, total = {package}, [package], 0
    while todo:
        p = todo.pop()
        total += max(0, int(size(p) or 0))
        for d in deps(p) or ():
            d = str(d)
            if d.startswith(GAME) and d not in seen:
                seen.add(d)
                todo.append(d)
    return total, len(seen)


def kib(nbytes):
    """Bytes to KiB, rounded up, within DSB's 1..1e8."""
    return min(MAX_KIB, max(1, math.ceil(nbytes / 1024)))


def ram_kib(disk_kib):
    return min(MAX_KIB, max(1, math.ceil(disk_kib * RAM_PER_DISK)))


def _cm(v):
    return max(-MAX_CM, min(MAX_CM, int(round(v))))


def _clamp_kib(v):
    return min(MAX_KIB, max(1, int(v)))


def write_dsb(rows):
    """DSB 1 text for islands.json rows that carry package, x, y, ram_kib, disk_kib. Canonical: sorted by id."""
    taken, lines = set(), []
    for r in rows:
        iid = island_id(r["package"], taken)
        lines.append((iid, "island %s x %d y %d ram %d disk %d" % (
            iid, _cm(r["x"]), _cm(r["y"]), _clamp_kib(r.get("ram_kib", 1)), _clamp_kib(r.get("disk_kib", 1)))))
    lines.sort(key=lambda t: t[0].encode())
    return "DSB 1\n" + "".join(line + "\n" for _, line in lines)
