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
g = L.groups({"AMF": (4000000, 2000000, 6000, 6300), "AMF_Pets": (3999800, 2000200, 3100, 5100),
              "Disk": (4000000, 4000000, 9000, 9000)})
check("a level sitting on another island moves with it", any(set(m) == {"AMF", "AMF_Pets"} for m, _ in g.values()))
check("separate islands stay separate groups", len(g) == 2)

# ---- ADR-065 spiral placement (Richey 2026-10-13: 'why are the islands so far apart') ----
import daedalus_land_grid as G
hub = (-1000000.0, 500000.0)
sp = L.spiral_targets([(n, w, d) for n, w, d in boxes] + [("Big", 60000, 78000)], hub, (30000, 30000))
check("spiral: every island placed", set(sp) == set(names) | {"Big"})
allcells = {}
for n, t in sp.items():
    x, y = t["cell"]; s = t["size"]
    cs = []
    check("spiral: %s estate is whole and inside one district" % n, G.estate(x, y, s, cs) == t["deed"] and t["deed"] >= 0)
    for c in cs:
        check("spiral: cell %s used once" % (c,), c not in allcells); allcells[c] = n
hubc = L.hub_cells(30000, 30000)
check("spiral: the hub island's cells are reserved", not (set(allcells) & hubc) and (G.HUB, G.HUB) in hubc)
check("spiral: a 780 m island takes a 4x4 estate", sp["Big"]["size"] == 4 and G.size_for(600, 780) == 4)
check("spiral: small islands are single cells", all(sp[n]["size"] == 1 for n in names if max(dict((b[0], b[1:]) for b in boxes)[n]) < 17000))
dists = [max(abs(t["to"][0] - hub[0]), abs(t["to"][1] - hub[1])) for t in sp.values()]
check("spiral: everything sits within 6 cells of the hub", max(dists) <= 6 * G.PITCH_M * 100)
check("spiral: lowest deeds go to the biggest islands", sp["Big"]["deed"] <= min(t["deed"] for n, t in sp.items() if n != "Big") or sp["Big"]["size"] == 4)

print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
