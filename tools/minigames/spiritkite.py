#!/usr/bin/env python3
"""Spiritkite Weave: fly a spirit kite across Prismheart's sky isles, gather lanterns and return to the anchor.

The sky isles form a seeded graph; each wind lane between two isles costs wind.
Fly lane by lane from the anchor isle (0), gathering each isle's spirit lantern
the first time you land there, then land back at the anchor. If the kite can no
longer reach the anchor with the wind left, it is lost. Land with lanterns worth
at least the target to win (score = lanterns + unused wind). Every target is
reachable: it is a share of the best possible round trip. Stdlib only, deterministic per seed.
"""
import math
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "spiritkite"
TITLE = "Spiritkite Weave"
HOW_TO_PLAY = ("HOW Fly the kite along wind lanes between sky isles to gather lanterns, "
               "then land on the anchor isle before the wind runs out.")
DIFFICULTY = {
    "easy": {"isles": 7, "wind": 30, "share": 0.6},
    "normal": {"isles": 8, "wind": 28, "share": 0.75},
    "hard": {"isles": 10, "wind": 26, "share": 0.9},
}
DEFAULT_DIFFICULTY = "normal"
INF = 10 ** 9


def shortest(n, lanes):
    d = [[0 if i == j else INF for j in range(n)] for i in range(n)]
    for a, b, w in lanes:
        d[a][b] = d[b][a] = min(d[a][b], w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


def best_tour(dist, values, wind):
    """(best lantern total, visit order) for a round trip from isle 0 within wind."""
    n = len(values)
    full = 1 << n
    cost = [[INF] * n for _ in range(full)]
    prev = [[-1] * n for _ in range(full)]
    cost[1][0] = 0
    best, best_key = 0, (1, 0)
    for s in range(full):
        if not s & 1:
            continue
        for v in range(n):
            c = cost[s][v]
            if c >= INF or not (s >> v) & 1:
                continue
            if c + dist[v][0] <= wind:
                val = sum(values[i] for i in range(n) if (s >> i) & 1)
                if val > best:
                    best, best_key = val, (s, v)
            for u in range(n):
                if (s >> u) & 1:
                    continue
                nc = c + dist[v][u]
                t = s | (1 << u)
                if nc < cost[t][u] and nc <= wind:
                    cost[t][u], prev[t][u] = nc, v
    order, (s, v) = [], best_key
    while v > 0:
        order.append(v)
        s, v = s & ~(1 << v), prev[s][v]
    return best, order[::-1]


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("lanes", "values", "at", "wind", "gathered", "target", "plan", "trail")

    def setup(self):
        n = self.cfg["isles"]
        pts = [(self.rng.randint(0, 9), self.rng.randint(0, 9)) for _ in range(n)]
        lanes = set()
        for i in range(1, n):
            lanes.add((self.rng.randrange(i), i))
        while len(lanes) < n - 1 + n // 2:
            a, b = sorted(self.rng.sample(range(n), 2))
            lanes.add((a, b))
        self.lanes = [[a, b, 1 + round(math.dist(pts[a], pts[b]) / 2)] for a, b in sorted(lanes)]
        self.values = [0] + [self.rng.randint(1, 6) for _ in range(n - 1)]
        self.restore()
        best, order = best_tour(self.dist, self.values, self.cfg["wind"])
        self.target = max(1, math.ceil(best * self.cfg["share"]))
        self.plan = order
        self.at, self.wind, self.gathered, self.trail = 0, self.cfg["wind"], [0], [0]

    def restore(self):
        n = self.cfg["isles"]
        self.dist = shortest(n, self.lanes)
        self.adj = {i: {} for i in range(n)}
        for a, b, w in self.lanes:
            self.adj[a][b] = self.adj[b][a] = w

    def rescore(self):
        """Lanterns gathered; a win adds the unused wind."""
        return self.lanterns() + (self.wind if self.won else 0)

    def lanterns(self):
        return sum(self.values[i] for i in self.gathered)

    def act(self, action):
        kind, j = action
        if kind == "land":
            if self.at != 0:
                raise ValueError("land only on the anchor isle 0")
            if len(self.trail) == 1:
                raise ValueError("fly first: the kite has not left the anchor isle")
            self.score = self.lanterns() + (self.wind if self.lanterns() >= self.target else 0)
            self.finish(self.lanterns() >= self.target)
            return f"landed with {self.lanterns()}"
        if kind != "fly" or j not in self.adj[self.at]:
            raise ValueError(f"no wind lane from {self.at} to {j}")
        self.wind -= self.adj[self.at][j]
        self.at = j
        self.trail.append(j)
        got = 0
        if j not in self.gathered:
            self.gathered.append(j)
            got = self.values[j]
        self.score = self.lanterns()
        if self.dist[j][0] > self.wind:
            self.finish(False)
            return "the kite is lost"
        return f"+{got}"

    def demo_action(self):
        goal = next((v for v in self.plan if v not in self.gathered), 0)
        if goal == 0 and self.at == 0:
            return ("land", 0)
        step = min(self.adj[self.at], key=lambda u: (self.adj[self.at][u] + self.dist[u][goal], u))
        return ("fly", step)

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] at isle {self.at} wind {self.wind} lanterns {self.lanterns()}/{self.target}"]
        for i in range(self.cfg["isles"]):
            lanes = ", ".join(f"{j}({w})" for j, w in sorted(self.adj[i].items()))
            mark = "*" if i == self.at else " "
            lines.append(f"{mark} isle {i} lantern {self.values[i]}{' (taken)' if i in self.gathered and i else ''}: {lanes}")
        if self.over:
            lines.append("WON: the kite lands heavy with light" if self.won else "LOST: the kite drifts away")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        parts = line.split()
        if parts[0] == "land":
            return ("land", 0)
        if parts[0] == "fly" and len(parts) == 2:
            return ("fly", int(parts[1]))
        raise ValueError("use fly <isle> or land")


def start(seed=0, difficulty=DEFAULT_DIFFICULTY):
    return Game(seed, difficulty)


def demo(seed=0, difficulty=DEFAULT_DIFFICULTY, out=None):
    return pc.demo(Game, seed, difficulty, out)


def play(seed, difficulty, inp=sys.stdin, out=sys.stdout):
    return pc.play(Game, seed, difficulty, inp, out)


def main(argv=None):
    return pc.main(Game, argv)


if __name__ == "__main__":
    sys.exit(main())
