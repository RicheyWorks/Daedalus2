# SPDX-License-Identifier: MIT
"""The ADR-065 land grid in Python: the twin of DaedalusLandGrid.h (100 x 100 cells, a square spiral out from the
hub cell (50, 50), districts of 10 x 10, estates of 1..4 cells a side that never split a district, pitch 256 m).
land_grid_test.cpp prints the first cells; test_daedalus_land_grid.py checks this module gives the same ones.

    cell(n) -> (x, y)        number(x, y) -> n        district(n)        estate(x, y, size) -> deed number or -1
    metres(n) -> (mx, my)    centre of the cell in realm metres, the hub cell at (0, 0), +x east, +y north
    place_estates(sizes, taken) -> {name: (x, y, size, deed)}   greedy: lowest free estate for each, largest first
"""
SIDE = 100
COUNT = SIDE * SIDE
HUB = SIDE // 2
DISTRICT = 10
PITCH_M = 256.0

_table = None
_inv = None


def _build():
    global _table, _inv
    out = [(HUB, HUB)]
    r = 1
    while len(out) < COUNT:
        ring = []
        for y in range(HUB - r + 1, HUB + r + 1):          # east side, north
            ring.append((HUB + r, y))
        for x in range(HUB + r - 1, HUB - r - 1, -1):      # north side, west
            ring.append((x, HUB + r))
        for y in range(HUB + r - 1, HUB - r - 1, -1):      # west side, south
            ring.append((HUB - r, y))
        for x in range(HUB - r + 1, HUB + r + 1):          # south side, east
            ring.append((x, HUB - r))
        for c in ring:
            if 0 <= c[0] < SIDE and 0 <= c[1] < SIDE and len(out) < COUNT:
                out.append(c)
        r += 1
    _table = out
    _inv = {c: i for i, c in enumerate(out)}


def cell(n):
    if _table is None:
        _build()
    return _table[n] if 0 <= n < COUNT else (-1, -1)


def number(x, y):
    if _table is None:
        _build()
    return _inv.get((x, y), -1)


def ring(n):
    x, y = cell(n)
    return -1 if x < 0 else max(abs(x - HUB), abs(y - HUB))


def district_of(x, y):
    return (y // DISTRICT) * DISTRICT + x // DISTRICT


def district(n):
    x, y = cell(n)
    return -1 if x < 0 else district_of(x, y)


def estate(x, y, size, cells=None):
    """Deed number (the lowest cell) of a size x size block with its south-west corner at (x, y); -1 off the grid
    or across a district line."""
    if size < 1 or size > 4 or x < 0 or y < 0 or x + size > SIDE or y + size > SIDE:
        return -1
    d = district_of(x, y)
    lowest = COUNT
    for j in range(size):
        for i in range(size):
            if district_of(x + i, y + j) != d:
                return -1
            n = number(x + i, y + j)
            lowest = min(lowest, n)
            if cells is not None:
                cells.append(n)
    return lowest


def metres(n, pitch=PITCH_M):
    x, y = cell(n)
    return (0.0, 0.0) if x < 0 else ((x - HUB) * pitch, (y - HUB) * pitch)


def estate_centre_m(x, y, size, pitch=PITCH_M):
    """Centre of a size x size block whose south-west cell is (x, y), in realm metres."""
    return ((x - HUB + (size - 1) / 2.0) * pitch, (y - HUB + (size - 1) / 2.0) * pitch)


def size_for(width_m, depth_m, pitch=PITCH_M, margin_m=40.0):
    """Cells a side for a footprint: the island plus a margin of sky, 1..4."""
    need = max(width_m, depth_m) + 2 * margin_m
    s = 1
    while s * pitch < need and s < 4:
        s += 1
    return s


def place_estates(sizes, taken=frozenset(), start=0):
    """sizes: {name: cells a side}. Largest first, then by name; each takes the lowest-numbered free estate
    (its south-west corner's cell scanned in spiral order from `start`) that fits in one district and overlaps
    no taken cell. Returns {name: (x, y, size, deed)}; the taken set grows."""
    used = set(taken)
    out = {}
    for name, size in sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0])):
        placed = None
        for n in range(start, COUNT):
            x, y = cell(n)
            # the block may extend any way from this cell: try it as each corner
            for (sx, sy) in ((x, y), (x - size + 1, y), (x, y - size + 1), (x - size + 1, y - size + 1)):
                cells = []
                deed = estate(sx, sy, size, cells)
                if deed < 0 or any(c in used for c in cells):
                    continue
                placed = (sx, sy, size, deed)
                used.update(cells)
                break
            if placed:
                break
        if not placed:
            raise ValueError("no free estate of %d for %s" % (size, name))
        out[name] = placed
    return out
