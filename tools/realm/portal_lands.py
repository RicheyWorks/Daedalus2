# SPDX-License-Identifier: MIT
"""Lay down the 8-bit realm's lands (BASE-LAYER.md PORTAL row 3): every 4x4 block of open ground on the FIELD map
becomes a `land <n> FIELD <x> <y> 4 4 -` row in realm-7.drr, numbered outward from the hero's spawn block
(nearest first, so low numbers are near the start, like ADR-065's spiral). Rows that exist keep their numbers
and owners. Idempotent: running twice changes nothing.

    python tools/realm/portal_lands.py            # rewrite the land rows in place, print the count
    python tools/realm/portal_lands.py --check    # exit 1 if the file is not already laid down

Pure functions (blocks, number) are tested by test_portal_lands.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRR = os.path.join(HERE, "..", "..", "engines", "unreal", "DaedalusLink", "Content", "Realm", "realm-7.drr")
OPEN = ".:"          # grass, sand: a plot stands here; forest/hills/swamp/water/towns do not
SIZE = 4


def read_map(lines, name="FIELD"):
    """The rows of one map as a list of strings."""
    rows, inside = [], False
    for l in lines:
        if l.startswith("map "):
            inside = l.split()[1] == name
            continue
        if inside and l.startswith("row "):
            rows.append(l[4:].rstrip("\n"))
        elif inside and rows and not l.startswith("row "):
            break
    return rows


def blocks(rows, size=SIZE, open_tiles=OPEN):
    """[(x, y)] south-west corners of every size x size block of open tiles, on a size-aligned grid."""
    h = len(rows)
    w = min(len(r) for r in rows) if rows else 0
    out = []
    for y in range(0, h - size + 1, size):
        for x in range(0, w - size + 1, size):
            if all(rows[y + j][x + i] in open_tiles for j in range(size) for i in range(size)):
                out.append((x, y))
    return out


def ordered(blocks_, origin):
    """Nearest the origin block first (Chebyshev, then angle-stable by (dy, dx))."""
    ox, oy = origin
    return sorted(blocks_, key=lambda b: (max(abs(b[0] - ox), abs(b[1] - oy)), b[1] - oy, b[0] - ox))


def lay(text):
    """New file text with every open block a land row; existing rows keep number/owner. Returns (text, n_rows)."""
    lines = text.splitlines()
    rows = read_map(lines)
    existing = [l for l in lines if l.startswith("land ")]
    kept = {}
    for l in existing:
        f = l.split()
        kept[(f[2], int(f[3]), int(f[4]))] = l
    origin = (26, 32)   # land 1 HERO: the hero's own plot
    for l in existing:
        f = l.split()
        if f[-1] == "HERO":
            origin = (int(f[3]), int(f[4]))
    new = []
    used = {int(l.split()[1]) for l in existing}
    n = max(used) + 1 if used else 0
    taken_cells = set()
    for key, l in kept.items():
        f = l.split()
        for j in range(int(f[6])):
            for i in range(int(f[5])):
                taken_cells.add((int(f[3]) + i, int(f[4]) + j))
    for (x, y) in ordered(blocks(rows), origin):
        if ("FIELD", x, y) in kept:
            continue
        if any((x + i, y + j) in taken_cells for j in range(SIZE) for i in range(SIZE)):
            continue
        while n in used:
            n += 1
        new.append("land %d FIELD %d %d %d %d -" % (n, x, y, SIZE, SIZE))
        used.add(n)
        n += 1
    body = [l for l in lines if not l.startswith("land ")]
    while body and not body[-1].strip():
        body.pop()
    # RetroCodec's canonical DRR writer emits deeds before spawn, portal and news.
    # Keep that ordering so the strict Java/native fixture parity check still holds.
    land_at = next((i for i, l in enumerate(body) if l.startswith("spawn ")), len(body))
    out = body[:land_at] + existing + new + body[land_at:]
    return "\n".join(out) + "\n", len(existing) + len(new)


def main(argv):
    with open(DRR, encoding="utf-8") as f:
        text = f.read()
    new_text, n = lay(text)
    if "--check" in argv:
        print("%d land rows; %s" % (n, "laid down" if new_text == text else "NOT laid down"))
        return 0 if new_text == text else 1
    if new_text != text:
        with open(DRR, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
    print("%d land rows in %s" % (n, os.path.relpath(DRR)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
