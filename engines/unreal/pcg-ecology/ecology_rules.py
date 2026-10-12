# SPDX-License-Identifier: MIT
"""Rule-based plant ecology for PCG placement (Pythagoras, pcg-ecology).

Pure Python (stdlib only), so it runs in Unreal's embedded Python, in CI and on any bot box.
Units: metres, +Z up. Unreal callers multiply by 100.

Ecology encoded (temperate old-field -> forest catena, the textbook case):
  * Niches   - each species has a Gaussian moisture optimum (realised niche width) and a
               hard slope limit (root anchoring / soil depth on steep ground).
  * Succession - a disturbance (old field / burn) at the origin; time since disturbance grows
               with distance, giving seral bands: herbaceous pioneers -> shrubs -> early
               conifers -> late-successional hardwoods (Clements/Odum relay floristics).
  * Competition - asymmetric: plants are placed tallest-first; each keeps a crown exclusion
               radius (Poisson-disk thinning). Shade-intolerant species may not sit under a
               canopy; shade-tolerant understory may. This gives the regular (Clark-Evans R>1)
               spacing seen in self-thinned stands.
"""
import math, random

DOMAIN = 100.0  # metres, square [0, DOMAIN]^2

# name, stage(0 pioneer..3 climax), moisture optimum, niche sd, max slope deg, crown radius m,
#   height m, shade tolerant, stand-in shape, base attempts per 100 m^2
SPECIES = [
    dict(name="Oak",    stage=3, m_opt=0.50, m_sd=0.18, max_slope=25, r=4.0, h=14, shade_tol=True,  shape="Sphere",   tint=(0.20,0.40,0.15)),
    dict(name="Pine",   stage=2, m_opt=0.25, m_sd=0.15, max_slope=35, r=2.5, h=12, shade_tol=False, shape="Cone",     tint=(0.10,0.30,0.18)),
    dict(name="Willow", stage=2, m_opt=0.90, m_sd=0.10, max_slope=10, r=3.0, h=9,  shade_tol=False, shape="Sphere",   tint=(0.45,0.60,0.25)),
    dict(name="Bramble",stage=1, m_opt=0.40, m_sd=0.20, max_slope=30, r=1.2, h=2,  shade_tol=False,  shape="Cylinder", tint=(0.35,0.45,0.20)),
    dict(name="Sedge",  stage=0, m_opt=0.92, m_sd=0.08, max_slope=8,  r=0.4, h=0.6,shade_tol=False, shape="Cylinder", tint=(0.40,0.55,0.30)),
    dict(name="Grass",  stage=0, m_opt=0.35, m_sd=0.22, max_slope=40, r=0.5, h=0.8,shade_tol=False, shape="Cone",     tint=(0.60,0.65,0.30)),
    dict(name="Fern",   stage=3, m_opt=0.65, m_sd=0.15, max_slope=30, r=0.6, h=0.9,shade_tol=True,  shape="Cone",     tint=(0.25,0.50,0.20)),
]
BY_NAME = {s["name"]: s for s in SPECIES}

# ---- abiotic fields --------------------------------------------------------
def stream_x(y):  # a meandering stream running roughly north-south
    return 70.0 + 8.0 * math.sin(y / 14.0)

def height(x, y):
    """Valley along the stream, ridge to the west, hummocks. Metres."""
    d = abs(x - stream_x(y))
    valley = 6.0 * (1 - math.exp(-(d / 18.0) ** 2))
    ridge = 6.0 * math.exp(-((x - 15.0) / 14.0) ** 2) * (0.7 + 0.3 * math.sin(y / 11.0))
    hum = 0.4 * math.sin(x / 5.3) * math.cos(y / 6.1)
    return valley + ridge + hum

def slope_deg(x, y, e=0.5):
    dx = (height(x + e, y) - height(x - e, y)) / (2 * e)
    dy = (height(x, y + e) - height(x, y - e)) / (2 * e)
    return math.degrees(math.atan(math.hypot(dx, dy)))

def moisture(x, y):
    """0 dry .. 1 saturated: riparian proximity plus topographic position (low = wetter)."""
    d = abs(x - stream_x(y))
    riparian = math.exp(-d / 10.0)
    topo = 1.0 - min(1.0, height(x, y) / 14.0)
    return max(0.0, min(1.0, 0.65 * riparian + 0.35 * topo))

def seral_stage(x, y, rng=None):
    """Continuous succession age 0..3 from distance to the disturbance at (0, 0), with a ragged edge."""
    d = math.hypot(x, y)
    edge = 3.0 * math.sin(x / 7.0) * math.cos(y / 9.0)
    return max(0.0, min(3.0, (d + edge - 15.0) / 30.0))

# ---- placement -------------------------------------------------------------
def suitability(sp, m, s, age):
    if s > sp["max_slope"]:
        return 0.0
    niche = math.exp(-0.5 * ((m - sp["m_opt"]) / sp["m_sd"]) ** 2)
    # relay floristics: a species peaks when the site reaches its stage, and early species
    # fade (but don't vanish) once the canopy closes over them
    gap = age - sp["stage"]
    seral = math.exp(-0.5 * (gap / 0.6) ** 2) if gap < 0 else math.exp(-0.5 * (gap / (1.6 if sp["shade_tol"] else 0.9)) ** 2)
    if sp["name"] in ("Willow", "Sedge"):   # riparian specialists are azonal: water, not time, decides
        seral = max(seral, 0.8)
    return niche * seral * (1 - 0.6 * s / sp["max_slope"])

class Grid:
    def __init__(self, cell):
        self.c = cell; self.g = {}
    def add(self, p):
        self.g.setdefault((int(p["x"] // self.c), int(p["y"] // self.c)), []).append(p)
    def near(self, x, y, r):
        k = int(math.ceil(r / self.c)); cx, cy = int(x // self.c), int(y // self.c)
        for i in range(cx - k, cx + k + 1):
            for j in range(cy - k, cy + k + 1):
                yield from self.g.get((i, j), ())

def generate(seed=7, domain=DOMAIN, candidates_per_m2=0.9):
    rng = random.Random(seed)
    order = sorted(SPECIES, key=lambda s: -s["h"])   # asymmetric competition: tallest first
    grid = Grid(4.0); placed = []; rejected = {"slope": 0, "niche": 0, "competition": 0, "shade": 0}
    for sp in order:
        # trees: dart-throw to saturation (many tries) -> self-thinned regular stand; herbs: sparser tries
        tries = 12.0 if sp["h"] >= 8 else 2.0
        n = int(domain * domain * candidates_per_m2 / (math.pi * sp["r"] ** 2) * tries)
        for _ in range(n):
            x, y = rng.uniform(0, domain), rng.uniform(0, domain)
            s, m, age = slope_deg(x, y), moisture(x, y), seral_stage(x, y)
            if s > sp["max_slope"]:
                rejected["slope"] += 1; continue
            if rng.random() > suitability(sp, m, s, age):
                rejected["niche"] += 1; continue
            ok = True
            for q in grid.near(x, y, 8.0):
                d = math.hypot(q["x"] - x, q["y"] - y)
                qs = BY_NAME[q["species"]]
                if qs["h"] > sp["h"] * 1.5:          # q overtops sp
                    if not sp["shade_tol"] and d < qs["r"]:
                        rejected["shade"] += 1; ok = False; break
                    if d < sp["r"] * 0.5:            # trunk/root zone still excluded
                        rejected["competition"] += 1; ok = False; break
                elif d < (qs["r"] + sp["r"]) * 0.8:  # peers: crowns may touch, not overlap
                    rejected["competition"] += 1; ok = False; break
            if not ok:
                continue
            sc = rng.uniform(0.75, 1.25)
            p = dict(species=sp["name"], x=x, y=y, z=height(x, y), yaw=rng.uniform(0, 360), scale=sc,
                     moisture=m, slope=s, age=age)
            placed.append(p); grid.add(p)
    return placed, rejected

# ---- verification ----------------------------------------------------------
def clark_evans(points, area):
    """R = observed mean NN distance / expected under CSR. R>1 regular (competition), <1 clumped."""
    n = len(points)
    if n < 3: return None
    g = Grid(5.0)
    for p in points: g.add(p)
    tot = 0.0
    for p in points:
        r, best = 5.0, None
        while best is None:
            ds = [math.hypot(q["x"] - p["x"], q["y"] - p["y"]) for q in g.near(p["x"], p["y"], r) if q is not p]
            if ds: best = min(ds)
            else: r *= 2
        tot += best
    return (tot / n) / (0.5 / math.sqrt(n / area))

def stats(placed, domain=DOMAIN):
    out = {"total": len(placed), "species": {}}
    for sp in SPECIES:
        pts = [p for p in placed if p["species"] == sp["name"]]
        if not pts:
            out["species"][sp["name"]] = {"n": 0}; continue
        mean = lambda k: sum(p[k] for p in pts) / len(pts)
        out["species"][sp["name"]] = dict(n=len(pts), moisture=round(mean("moisture"), 3), slope_max=round(max(p["slope"] for p in pts), 1),
                                          age=round(mean("age"), 2), clark_evans_R=round(clark_evans(pts, domain * domain), 2))
    # minimum spacing among peers (same layer) - must never be below 0.8*(ri+rj)
    viol = 0; g = Grid(4.0)
    for p in placed: g.add(p)
    for p in placed:
        sp = BY_NAME[p["species"]]
        for q in g.near(p["x"], p["y"], 8.0):
            if q is p: continue
            qs = BY_NAME[q["species"]]
            if max(qs["h"], sp["h"]) <= 1.5 * min(qs["h"], sp["h"]) and math.hypot(q["x"]-p["x"], q["y"]-p["y"]) < (qs["r"]+sp["r"])*0.8 - 1e-9:
                viol += 1
    out["spacing_violations"] = viol
    # niche bands
    def band(p):
        if p["moisture"] > 0.7: return "riparian"
        return ["pioneer", "shrub", "early_forest", "late_forest"][min(3, int(p["age"] + 0.5))]
    bands = {}
    for p in placed:
        b = bands.setdefault(band(p), {}); b[p["species"]] = b.get(p["species"], 0) + 1
    out["bands"] = bands
    return out

def checks(placed):
    st = stats(placed); sp = st["species"]; res = []
    def c(label, ok, detail=""): res.append((label, bool(ok), detail))
    c("every species placed", all(sp[s["name"]]["n"] > 0 for s in SPECIES), str({k: v["n"] for k, v in sp.items()}))
    c("no slope limit broken", all(sp[s["name"]].get("slope_max", 0) <= s["max_slope"] for s in SPECIES))
    c("no peer crown overlap", st["spacing_violations"] == 0, str(st["spacing_violations"]))
    c("trees regularly spaced (Clark-Evans R>1.2)", all(sp[n]["clark_evans_R"] > 1.2 for n in ("Oak", "Pine")), str({n: sp[n]["clark_evans_R"] for n in ("Oak","Pine")}))
    c("willow/sedge wetter than pine/grass", min(sp["Willow"]["moisture"], sp["Sedge"]["moisture"]) > max(sp["Pine"]["moisture"], sp["Grass"]["moisture"]) + 0.2)
    c("succession order grass<bramble<pine<oak by mean age", sp["Grass"]["age"] < sp["Bramble"]["age"] < sp["Pine"]["age"] < sp["Oak"]["age"],
      str({n: sp[n]["age"] for n in ("Grass","Bramble","Pine","Oak")}))
    b = st["bands"]
    top = lambda k, layer: max((v, s) for s, v in b.get(k, {}).items() if BY_NAME[s]["h"] >= layer)[1] if any(BY_NAME[s]["h"] >= layer for s in b.get(k, {})) else None
    c("pioneer band dominated by herbs", top("pioneer", 0) in ("Grass", "Sedge"), str(b.get("pioneer")))
    c("late band canopy is Oak", top("late_forest", 8) == "Oak", str(b.get("late_forest")))
    c("riparian canopy is Willow", top("riparian", 8) == "Willow", str(b.get("riparian")))
    c("deterministic for a seed", generate(7)[0][:50] == generate(7)[0][:50])
    return res, st

if __name__ == "__main__":
    import json, sys
    placed, rej = generate(7)
    res, st = checks(placed)
    for label, ok, d in res: print(("PASS " if ok else "FAIL ") + label + ("  " + d if d and not ok else ""))
    print(json.dumps({"rejected": rej, **st}, indent=1))
    n = sum(ok for _, ok, _ in res); print(f"{n}/{len(res)}"); sys.exit(0 if n == len(res) else 1)
