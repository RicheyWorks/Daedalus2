# SPDX-License-Identifier: MIT
"""Measure a floating island's real footprint by ray probes (no hardcoded sizes).
bounds(world, x, y, z_ref) -> dict(minx,maxx,miny,maxy,cx,cy,span_x,span_y,area_m2,ground_frac)
Grows a probe grid outward from (x, y) until a full ring misses (the island edge), so it keeps working
when the islands are scaled up."""
import unreal
def probe(world, x, y, z, up=30000, down=60000):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z + up), unreal.Vector(x, y, z - down),
        unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple(); return t[4].z if t[0] else None
def bounds(world, x, y, z, step=1000.0, max_r=200000.0):
    hits, r = [], step
    if probe(world, x, y, z) is not None: hits.append((x, y))
    while r <= max_r:
        ring, n = [], max(8, int(6.283 * r / step))
        for k in range(n):
            import math
            a = 6.283185 * k / n; px, py = x + r * math.cos(a), y + r * math.sin(a)
            if probe(world, px, py, z) is not None: ring.append((px, py))
        if not ring: break
        hits += ring; r += step if r < 20 * step else step * 2
    if not hits: return None
    xs, ys = [p[0] for p in hits], [p[1] for p in hits]
    b = dict(minx=min(xs), maxx=max(xs), miny=min(ys), maxy=max(ys))
    b.update(cx=(b["minx"] + b["maxx"]) / 2, cy=(b["miny"] + b["maxy"]) / 2,
             span_x=b["maxx"] - b["minx"], span_y=b["maxy"] - b["miny"])
    b["area_m2"] = len(hits) * (step / 100) ** 2  # rough
    return b

