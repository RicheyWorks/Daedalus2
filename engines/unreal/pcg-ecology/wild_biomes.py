"""Wild Biomes recipes (Team Grok): five distinct biomes from the same ecology rules.
Each biome = (years since disturbance, seed, target species). We run the full rule model,
then pick the 30 m window where the target community is strongest (a real site-selection step)."""
import ecology_rules as er, island_flora
W = 30.0
BIOMES = [  # name, years, seed, target species weights
    ("YoungMeadow", 4, 11, {"Grass": 1, "Sedge": 1}),
    ("BrambleScrub", 15, 12, {"Bramble": 3, "Grass": -0.3}),
    ("PineStand", 45, 13, {"Pine": 3, "Oak": -1}),
    ("OldGrowthOak", 240, 14, {"Oak": 3, "Pine": -1}),
    ("WillowRiverbank", 90, 15, {"Willow": 6, "Sedge": 2})]
CAP = {"Fern": 110, "Grass": 150, "Sedge": 110}
def sp(p): return p["species"]
def biome(name, years, seed, wts):
    pts = er.generate(seed=seed, years=years)
    pts = pts[0] if isinstance(pts, tuple) else pts
    best = None
    for x0 in range(0, 71, 5):
        for y0 in range(0, 71, 5):
            win = [p for p in pts if x0 <= p["x"] < x0 + W and y0 <= p["y"] < y0 + W]
            m = island_flora.mix(win); n = max(len(win), 1)
            s = sum(w * m.get(k, 0) for k, w in wts.items()) / n ** 0.5
            if best is None or s > best[0]: best = (s, x0, y0, win)
    _, x0, y0, win = best
    keep, cnt = [], {}
    for p in win:
        cnt[sp(p)] = cnt.get(sp(p), 0) + 1
        if cnt[sp(p)] <= CAP.get(sp(p), 10**9):
            keep.append(dict(p, x=p["x"] - x0, y=p["y"] - y0))
    return keep
def all_biomes(): return {b[0]: biome(*b[1:]) and biome(*b) if False else biome(b[0], *b[1:]) for b in BIOMES}
if __name__ == "__main__":
    for k, v in all_biomes().items(): print(k, len(v), island_flora.mix(v))
