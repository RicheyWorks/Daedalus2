# SPDX-License-Identifier: MIT
"""Structural prop kit: 24 distinct families, each built from seeded structure params (counts, tiers, proportions), not recolours.
fam(name, rng) -> boxes; materials index 0 main, 1 trim, 2 accent (accent glows when glow=[2])."""
import random
def b(s, c, m=0): return [list(s), list(c), m]
def _lamp(r):
    h = r.uniform(2.2, 3.6); arms = r.randint(1, 3); o = [b((0.25, 0.25, 0.2), (0, 0, 0.1), 1), b((0.1, 0.1, h), (0, 0, h/2), 0)]
    for i in range(arms):
        d = [(1,0),(-1,0),(0,1)][i]; o += [b((0.5*abs(d[0])+0.06, 0.5*abs(d[1])+0.06, 0.06), (0.25*d[0], 0.25*d[1], h-0.1), 0), b((0.2, 0.2, 0.28), (0.5*d[0], 0.5*d[1], h-0.3), 2)]
    return o
def _fence(r):
    n = r.randint(3, 7); w = r.uniform(0.25, 0.45); h = r.uniform(0.8, 1.4); o = []
    for i in range(n): o.append(b((0.1, 0.1, h + (0.15 if i % 2 else 0)), (i*w - n*w/2, 0, h/2), 0))
    for z in ([h*0.35, h*0.8] if r.random() < 0.6 else [h*0.3, h*0.6, h*0.9]): o.append(b((n*w, 0.06, 0.08), (-w/2, 0, z), 1))
    return o
def _barrel(r):
    h = r.uniform(0.7, 1.2); w = r.uniform(0.5, 0.8); o = [b((w, w, h), (0, 0, h/2), 0), b((w*1.08, w*1.08, 0.12), (0, 0, h*0.5), 1)]
    for z in ([0.1, h-0.1] if r.random() < 0.5 else [0.1, h*0.25, h*0.75, h-0.1]): o.append(b((w*1.04, w*1.04, 0.06), (0, 0, z), 1))
    if r.random() < 0.5: o.append(b((0.12, 0.12, 0.12), (w/2, 0, h*0.3), 2))
    return o
def _crate(r):
    n = r.randint(1, 3); o = []; z = 0
    for i in range(n):
        s = r.uniform(0.5, 0.9) * (1 - 0.15*i); o += [b((s, s, s), (r.uniform(-0.1, 0.1), r.uniform(-0.1, 0.1), z + s/2), 0), b((s*1.02, 0.06, s*1.02), (0, s/2, z+s/2), 1)]; z += s
    return o
def _cart(r):
    L = r.uniform(1.4, 2.4); o = [b((L, 1.0, 0.15), (0, 0, 0.7), 0), b((L, 0.08, 0.4), (0, 0.46, 0.95), 0), b((L, 0.08, 0.4), (0, -0.46, 0.95), 0)]
    for x in ([-L/3, L/3] if r.random() < 0.6 else [-L/2.5, 0, L/2.5]):
        for y in (-0.6, 0.6): o.append(b((0.6, 0.1, 0.6), (x, y, 0.35), 1))
    o.append(b((1.2, 0.08, 0.08), (L/2 + 0.6, 0, 0.7), 1))
    if r.random() < 0.5: o.append(b((L*0.8, 0.8, 0.4), (0, 0, 1.0), 2))
    return o
def _well(r):
    w = r.uniform(1.2, 1.8); h = r.uniform(0.6, 1.0); o = [b((w, w, h), (0, 0, h/2), 0), b((w*0.7, w*0.7, 0.05), (0, 0, h+0.01), 2)]
    for x in (-w/2+0.08, w/2-0.08): o.append(b((0.12, 0.12, 1.8), (x, 0, h+0.9), 1))
    o += [b((w*1.3, w*0.9, 0.12), (0, 0, h+1.85), 1), b((w, 0.06, 0.06), (0, 0, h+1.4), 1)]
    return o
def _bridge(r):
    L = r.uniform(3, 6); n = int(L/0.5); o = []
    for i in range(n): o.append(b((0.45, 1.6, 0.1), (i*0.5 - L/2, 0, 0.3 + 0.25*(1 - (2*i/n - 1)**2)), 0))
    for y in (-0.8, 0.8): o.append(b((L, 0.06, 0.06), (0, y, 1.1), 1))
    for i in range(0, n, max(2, n//4)):
        for y in (-0.8, 0.8): o.append(b((0.08, 0.08, 0.9), (i*0.5 - L/2, y, 0.75), 1))
    return o
def _sign(r):
    h = r.uniform(1.2, 2.2); o = [b((0.1, 0.1, h), (0, 0, h/2), 1)]
    for i in range(r.randint(1, 3)):
        d = r.choice((-1, 1)); o.append(b((0.8, 0.05, 0.25), (0.35*d, 0, h - 0.2 - 0.32*i), 0))
    o.append(b((0.12, 0.12, 0.12), (0, 0, h+0.06), 2)); return o
def _bench(r):
    L = r.uniform(1.2, 2.2); o = [b((L, 0.45, 0.08), (0, 0, 0.45), 0)]
    for x in (-L/2+0.1, L/2-0.1): o.append(b((0.08, 0.4, 0.45), (x, 0, 0.22), 1))
    if r.random() < 0.6: o += [b((L, 0.06, 0.4), (0, -0.22, 0.75), 0)]
    if r.random() < 0.4: o += [b((0.1, 0.45, 0.25), (x, 0, 0.6), 1) for x in (-L/2, L/2)]
    return o
def _table(r):
    w = r.uniform(0.9, 1.8); d = r.uniform(0.6, 1.0); o = [b((w, d, 0.07), (0, 0, 0.75), 0)]
    for x in (-w/2+0.07, w/2-0.07):
        for y in (-d/2+0.07, d/2-0.07): o.append(b((0.07, 0.07, 0.72), (x, y, 0.36), 1))
    for i in range(r.randint(0, 4)): o.append(b((0.12, 0.12, r.uniform(0.08, 0.25)), (r.uniform(-w/3, w/3), r.uniform(-d/3, d/3), 0.85), 2))
    return o
def _shelf(r):
    n = r.randint(2, 5); w = r.uniform(0.8, 1.6); h = 0.4*n; o = [b((0.06, 0.4, h), (x, 0, h/2), 1) for x in (-w/2, w/2)]
    for i in range(n + 1):
        o.append(b((w, 0.4, 0.05), (0, 0, i*0.4), 0))
        for j in range(r.randint(0, 3)): o.append(b((0.12, 0.15, 0.2), (r.uniform(-w/2.5, w/2.5), 0, i*0.4+0.12), 2))
    return o[:40]
def _banner(r):
    h = r.uniform(2.5, 4.5); o = [b((0.1, 0.1, h), (0, 0, h/2), 1), b((0.9, 0.08, 0.08), (0.4, 0, h-0.1), 1)]
    L = r.uniform(1.0, 2.0); o.append(b((0.7, 0.03, L), (0.45, 0, h - 0.15 - L/2), 0))
    if r.random() < 0.5: o.append(b((0.3, 0.04, 0.3), (0.45, 0, h - 0.15 - L/2), 2))
    return o
def _totem(r):
    n = r.randint(3, 6); o = []; z = 0
    for i in range(n):
        s = r.uniform(0.4, 0.7); hh = r.uniform(0.35, 0.6); o.append(b((s, s, hh), (0, 0, z+hh/2), i % 2)); 
        if r.random() < 0.4: o.append(b((s*1.6, 0.12, 0.12), (0, 0, z+hh*0.6), 2))
        z += hh
    return o
def _windmill(r):
    h = r.uniform(3, 5); w = r.uniform(1.4, 2.2); o = [b((w, w, h), (0, 0, h/2), 0), b((w*1.2, w*1.2, 0.6), (0, 0, h+0.3), 1)]
    n = r.choice((3, 4, 6))
    import math
    for i in range(n):
        a = i*6.283/n; o.append(b((0.25, 0.06, 2.2), (2.2/2*math.sin(a)*0.5, -w/2-0.2, h + 1.1*math.cos(a)), 2))
    return o
def _planter(r):
    L = r.uniform(0.8, 2.4); o = [b((L, 0.6, 0.4), (0, 0, 0.2), 1), b((L*0.95, 0.55, 0.05), (0, 0, 0.41), 0)]
    for i in range(r.randint(2, 6)): o.append(b((0.15, 0.15, r.uniform(0.2, 0.5)), (r.uniform(-L/2.3, L/2.3), r.uniform(-0.2, 0.2), 0.6), 2))
    return o
def _beehive(r):
    n = r.randint(2, 4); o = [b((0.5, 0.5, 0.4), (0, 0, 0.2), 1)]
    for i in range(n): s = 0.6 - 0.08*i; o.append(b((s, s, 0.22), (0, 0, 0.5 + 0.22*i), 0))
    o.append(b((0.12, 0.04, 0.05), (0, 0.3, 0.45), 2)); return o
def _trough(r):
    L = r.uniform(1.2, 2.5); return [b((L, 0.6, 0.45), (0, 0, 0.3), 1), b((L*0.9, 0.5, 0.05), (0, 0, 0.5), 2)] + [b((0.1, 0.5, 0.2), (x, 0, 0.1), 0) for x in (-L/2.4, L/2.4)]
def _coop(r):
    w = r.uniform(1.2, 2.0); o = [b((w, 1.0, 0.9), (0, 0, 0.8), 0), b((w*1.15, 1.2, 0.1), (0, 0, 1.3), 1)]
    for x in (-w/2+0.1, w/2-0.1): o.append(b((0.08, 0.08, 0.4), (x, 0, 0.2), 1))
    o.append(b((0.3, 0.05, 0.4), (0, 0.5, 0.75), 2)); return o
def _tent(r):
    w = r.uniform(1.6, 3.0); h = r.uniform(1.2, 2.0); o = []
    for i in range(5): o.append(b((w*(1 - i*0.18), 2.0, h/5), (0, 0, h/10 + i*h/5), 0))
    o += [b((0.06, 0.06, h+0.3), (0, y, (h+0.3)/2), 1) for y in (-1.05, 1.05)]; o.append(b((0.3, 0.1, 0.3), (0, 1.0, 0.2), 2)); return o
def _statue(r):
    pl = r.uniform(0.8, 1.4); o = [b((pl, pl, 0.5), (0, 0, 0.25), 1), b((pl*0.5, pl*0.4, 1.2), (0, 0, 1.1), 0), b((0.35, 0.35, 0.35), (0, 0, 1.9), 0)]
    if r.random() < 0.5: o.append(b((0.8, 0.12, 0.12), (0, 0, 1.4), 0))
    o.append(b((0.18, 0.18, 0.18), (0, 0, 2.2), 2)); return o
def _arch(r):
    w = r.uniform(2, 4); h = r.uniform(2.5, 4); t = r.uniform(0.3, 0.6)
    o = [b((t, t, h), (x, 0, h/2), 0) for x in (-w/2, w/2)] + [b((w+t, t, t), (0, 0, h+t/2), 1)]
    if r.random() < 0.6: o.append(b((t*0.8, t*0.8, t*0.8), (0, 0, h+t), 2))
    return o
def _bell(r):
    h = r.uniform(2.0, 3.0); return [b((0.12, 0.12, h), (x, 0, h/2), 1) for x in (-0.6, 0.6)] + [b((1.4, 0.12, 0.12), (0, 0, h), 1), b((0.5, 0.5, 0.5), (0, 0, h-0.4), 2), b((0.6, 0.6, 0.08), (0, 0, h-0.66), 2)]
def _scarecrow(r):
    return [b((0.08, 0.08, 1.9), (0, 0, 0.95), 1), b((1.3, 0.08, 0.08), (0, 0, 1.45), 1), b((0.45, 0.3, 0.6), (0, 0, 1.3), 0), b((0.3, 0.3, 0.3), (0, 0, 1.8), 2), b((0.5, 0.5, 0.08), (0, 0, 1.97), 0)]
def _sundial(r):
    s = r.uniform(0.6, 1.0); return [b((s*0.5, s*0.5, 0.9), (0, 0, 0.45), 1), b((s, s, 0.08), (0, 0, 0.94), 0), b((0.04, s*0.4, 0.25), (0, 0, 1.08), 2)]
def _obelisk(r):
    n = r.randint(3, 5); o = []; z = 0
    for i in range(n): s = 1.0 - 0.17*i; hh = r.uniform(0.6, 1.2); o.append(b((s, s, hh), (0, 0, z+hh/2), 0 if i else 1)); z += hh
    o.append(b((0.3, 0.3, 0.4), (0, 0, z+0.2), 2)); return o
FAM = {f[1:].capitalize(): g for f, g in list(globals().items()) if f.startswith("_") and callable(g) and not f.startswith("__")}
def build(fam, seed): return FAM[fam](random.Random(seed))
