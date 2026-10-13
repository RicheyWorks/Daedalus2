# SPDX-License-Identifier: MIT
"""Offline checks of the island packing. Run: python test_daedalus_layout.py"""
import daedalus_layout as L

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


def rects(boxes, pos):
    r = {}
    for n, w, d in boxes:
        cx, cy = pos[n]
        r[n] = (cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)
    return r


boxes = [("Grok", 54000, 54000), ("Heph", 76100, 60300), ("Orr", 53100, 78000), ("Pyth", 12000, 12000),
         ("AMF", 6000, 6300), ("Disk", 9000, 9000), ("Odds", 40000, 40000), ("Prom", 51000, 48000),
         ("Blender", 36600, 38600), ("Buff", 24200, 24300), ("YTM", 23100, 22500), ("Poot", 9200, 5400)]
pos = L.pack(boxes)
R = rects(boxes, pos)
names = list(R)
gaps = []
for i, a in enumerate(names):
    for b in names[i + 1:]:
        A, B = R[a], R[b]
        dx = max(B[0] - A[2], A[0] - B[2])
        dy = max(B[1] - A[3], A[1] - B[3])
        gaps.append(max(dx, dy))
check("every island placed", set(pos) == set(names))
check("no two islands overlap; each pair is at least the gap apart", min(gaps) >= L.GAP_CM - 1e-6)
check("neighbours are close: some pair is exactly one gap apart", any(abs(g - L.GAP_CM) < 1e-6 for g in gaps))
xs = [v for r in R.values() for v in (r[0], r[2])]
ys = [v for r in R.values() for v in (r[1], r[3])]
check("the whole archipelago fits in about 2 x 2 km", max(xs) - min(xs) <= L.ROW_CM + 80000 and max(ys) - min(ys) <= 250000)
check("everything is north of the lane (south edge at ORIGIN y)", min(ys) >= L.ORIGIN[1] - 1e-6)
check("deterministic", L.pack(list(reversed(boxes))) == pos)
fx = L.footprint([(0, 0, 100, 100), (300, 0, 100, 100), (10_000_000, 0, 50, 50)])
check("a stray far actor doesn't inflate the footprint", fx[2] == 500 and abs(fx[0] - 150) < 1e-6)
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
