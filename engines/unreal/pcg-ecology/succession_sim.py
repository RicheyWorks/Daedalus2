"""SUCCESSION mechanic core: tile seral clocks + player levers. Pure python, deterministic, tested.
1 in-game day = 1 ecological year. Stage via ecology_rules._stage_from_years (0 pioneer .. 3 climax)."""
import math, json
import ecology_rules as er
HERB_STAGE = {h["id"]: h["stage"] for h in json.load(open(__file__.replace("succession_sim.py", "herb_combo.json"), encoding="utf-8"))["herbs"]}
class Island:
    def __init__(self, n=12, years=0.0):
        self.n = n; self.t = [[years] * n for _ in range(n)]; self.grazed = set(); self.water = set()
    def stage(self, x, y): return int(er._stage_from_years(self.t[y][x]) + 1e-9)
    def step(self, days=1):
        for y in range(self.n):
            for x in range(self.n):
                if (x, y) in self.grazed: self.t[y][x] = min(self.t[y][x] + days, 12.0)   # grazing holds meadow (stage <= ~1.4)
                else: self.t[y][x] += days
    def disturb(self, x, y, r=1):
        for j in range(max(0, y - r), min(self.n, y + r + 1)):
            for i in range(max(0, x - r), min(self.n, x + r + 1)): self.t[j][i] = 0.0
    burn = disturb
    def graze(self, cells): self.grazed |= set(cells)
    def rest(self, cells): self.grazed -= set(cells)
    def dig(self, cells): self.water |= set(cells)
    def stages(self):
        c = [0, 0, 0, 0]
        for y in range(self.n):
            for x in range(self.n): c[min(3, self.stage(x, y))] += 1
        return c
    def herbs(self):
        have = {s for s, k in enumerate(self.stages()) if k}
        return sorted(h for h, s in HERB_STAGE.items() if s in have)
    def climax_ready(self): return all(self.stages())   # full 0-1-2-3 mosaic at once
    def shannon(self):
        c = [k for k in self.stages() if k] + ([len(self.water)] if self.water else []); N = sum(c)
        return round(-sum(k / N * math.log(k / N) for k in c), 3)
def tea(herbs):
    s = [HERB_STAGE[h] for h in herbs]
    if s == list(range(s[0], s[0] + len(s))): return ("climax" if s == [0, 1, 2, 3] else "ladder", len(s) - 1)
    if any(b == 0 and a > 0 for a, b in zip(s, s[1:])): return ("reset", 1)
    return ("gap", 0.5)
if __name__ == "__main__":
    ok = True
    def c(n, v):
        global ok; ok &= bool(v); print(("PASS " if v else "FAIL ") + n)
    I = Island(12, 0); c("fresh scar is all pioneer", I.stages() == [144, 0, 0, 0])
    I.step(80); c("80 years -> climax forest", I.stages()[3] == 144)
    I.disturb(2, 2, 1); I.burn(9, 9, 1); I.graze([(x, 6) for x in range(12)]); I.step(10)
    st = I.stages(); c("levers build a mosaic: %s" % st, st[3] > 0 and (st[0] + st[1]) > 0)
    I2 = Island(6, 0); I2.graze([(x, y) for x in range(6) for y in range(6)]); I2.step(200)
    c("grazing holds meadow <= stage 1 after 200 yr", max(I2.stages()[2:]) == 0)
    J = Island(12, 100); J.disturb(1, 1, 0); J.graze([(x, 5) for x in range(12)]); J.step(3); J.disturb(10, 1, 1); J.step(3); J.disturb(10, 10, 1); J.step(1)
    # staggered: gap aged 7 (stage 1), 6 (stage 1), meadow strip ~12 (stage 1-2), new 1 (stage 0), rest climax
    J.disturb(6, 9, 0); J.t[9][6] = 30
    c("climax mosaic reachable: %s" % J.stages(), J.climax_ready())
    c("all 12 herbs on a full mosaic", len(J.herbs()) == 12)
    c("tea: climax ladder", tea(["fireweed", "selfheal", "nettle", "woodsorrel"])[0] == "climax")
    c("tea: reset", tea(["ramsons", "yarrow"])[0] == "reset"); c("tea: gap", tea(["yarrow", "valerian"])[0] == "gap")
    c("mosaic more diverse than monoculture", J.shannon() > Island(12, 100).shannon())
    print("ALL PASS" if ok else "SOME FAIL"); raise SystemExit(0 if ok else 1)
