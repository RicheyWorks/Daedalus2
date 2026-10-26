# SPDX-License-Identifier: MIT
"""Splice takes into one cut: part 1 up to its end card, part 2, then part 1's end card.

    python combine_takes.py <part1 take> <part2 take> <out dir>
Each take must have frames_jpg/ (make_trailer.ps1 or normalize_frames.py makes it) and captions (part 1's come from
trailer_plan, part 2's from its captions.txt). Writes <out>/frames_jpg and <out>/captions.txt; then
make_trailer.ps1 -Take <out> cuts the video.
"""
import os
import shutil
import sys

import trailer_plan as tp


def captions(take):
    f = os.path.join(take, "captions.txt")
    if os.path.exists(f):
        rows = []
        for line in open(f):
            if line.strip():
                a, n, c = line.rstrip("\n").split("|", 2)
                rows.append((int(a), int(n), c))
        return rows
    return [v for v in tp.shot_starts().values()]


def main(p1, p2, out):
    j1, j2, jo = (os.path.join(p, "frames_jpg") for p in (p1, p2, out))
    os.makedirs(jo, exist_ok=True)
    c1, c2 = captions(p1), captions(p2)
    end = c1[-1]                                   # part 1's end card
    pieces = [(j1, 0, end[0], [c for c in c1 if c[0] < end[0]]),
              (j2, 0, len(os.listdir(j2)), c2),
              (j1, end[0], end[0] + end[1], [end])]
    k, rows = 0, []
    for src, a, b, caps in pieces:
        for c in caps:
            rows.append((k + c[0] - a, c[1], c[2]))
        for i in range(a, b):
            f = os.path.join(src, "f_%05d.jpg" % i)
            if os.path.exists(f):
                shutil.copyfile(f, os.path.join(jo, "f_%05d.jpg" % k))
                k += 1
    with open(os.path.join(out, "captions.txt"), "w") as f:
        for r in rows:
            f.write("%d|%d|%s\n" % r)
    print(k)


if __name__ == "__main__":
    main(*sys.argv[1:4])
