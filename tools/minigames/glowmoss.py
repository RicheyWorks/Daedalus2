#!/usr/bin/env python3
"""Glowmoss Delve: climb down a seeded crystal shaft in Prismheart on a light budget and climb out richer.

The shaft is a grid of ledges, row 0 at the top. From the surface you dig down one row at a time onto a ledge in
the next row at most one column left or right of where you stand. Each dig burns light (1 + the ledge's darkness)
and gathers the ledge's crystals; a glowmoss ledge then refills light up to the lamp's capacity. Climbing out from
row r costs (r + 2) // 2 light, and if a dig leaves too little light to climb out the lamp gutters and the delve
is lost. Climb out with crystals worth at least the target to win (score = crystals + light left). Every target is
reachable: it is a share of the best possible delve (exact search). Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "glowmoss"
TITLE = "Glowmoss Delve"
HOW_TO_PLAY = ("HOW Dig down the shaft one ledge at a time to gather crystals; glowmoss refills your lamp. "
               "Climb out before the light is too low to carry you back up.")
DIFFICULTY = {
    "easy": {"cols": 3, "rows": 8, "light": 12, "refill": 4, "moss_pct": 25, "target_pct": 60},
    "normal": {"cols": 4, "rows": 10, "light": 11, "refill": 3, "moss_pct": 18, "target_pct": 75},
    "hard": {"cols": 5, "rows": 12, "light": 10, "refill": 3, "moss_pct": 12, "target_pct": 90},
}
DEFAULT_DIFFICULTY = "normal"
SURFACE = -1
REACH = 1  # a dig lands at most this many columns left or right
MAX_DARK = 2
MIN_GEMS, MAX_GEMS = 1, 5


def climb_cost(row):
    """Light needed to climb out from row (0 from the surface)."""
    return (row + 2) // 2


def dig_cols(col, cols):
    return range(max(0, col - REACH), min(cols, col + REACH + 1))


def after_dig(light, cfg, dark, moss):
    """Light after digging onto a ledge (burn first, then the glowmoss refill, capped)."""
    light -= 1 + dark
    if moss:
        light = min(cfg["light"], light + cfg["refill"])
    return light


def best_delve(cfg, gems, dark, moss):
    """(best crystals, dig columns) over every delve that can still climb out. Exact DP over (row, col, light)."""
    rows, cols, cap = cfg["rows"], cfg["cols"], cfg["light"]
    start = (cols // 2, cap)
    layer = {start: (0, None)}  # (col, light) -> (crystals, previous (col, light))
    history = []
    best, best_key = 0, None
    for r in range(rows):
        nxt = {}
        for (c, l), (v, _) in sorted(layer.items()):
            for u in dig_cols(c, cols):
                nl = after_dig(l, cfg, dark[r][u], moss[r][u])
                if nl < climb_cost(r):
                    continue
                nv = v + gems[r][u]
                if (u, nl) not in nxt or nv > nxt[(u, nl)][0]:
                    nxt[(u, nl)] = (nv, (c, l))
        history.append(nxt)
        for key, (v, _) in sorted(nxt.items()):
            if v > best:
                best, best_key = v, (r, key)
        layer = nxt
        if not layer:
            break
    plan = []
    if best_key:
        r, key = best_key
        while r >= 0:
            plan.append(key[0])
            key = history[r][key][1]
            r -= 1
    return best, plan[::-1]


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("gems", "dark", "moss", "row", "col", "light", "crystals", "target", "plan", "path")

    def setup(self):
        cfg = self.cfg
        self.gems, self.dark, self.moss = [], [], []
        for _ in range(cfg["rows"]):
            g, d, m = [], [], []
            for _ in range(cfg["cols"]):
                g.append(self.rng.randint(MIN_GEMS, MAX_GEMS))
                d.append(self.rng.randint(0, MAX_DARK))
                m.append(self.rng.randrange(100) < cfg["moss_pct"])
            self.gems.append(g)
            self.dark.append(d)
            self.moss.append(m)
        best, self.plan = best_delve(cfg, self.gems, self.dark, self.moss)
        self.target = max(1, best * cfg["target_pct"] // 100)
        self.row, self.col, self.light, self.crystals, self.path = SURFACE, cfg["cols"] // 2, cfg["light"], 0, []

    def act(self, action):
        kind, c = action
        if kind == "climb":
            won = self.crystals >= self.target
            self.light -= climb_cost(self.row)
            self.score = self.crystals + (self.light if won else 0)
            self.finish(won)
            return f"climbed out with {self.crystals}"
        if kind != "dig" or self.row + 1 >= self.cfg["rows"] or c not in dig_cols(self.col, self.cfg["cols"]):
            raise ValueError(f"no ledge {c} below column {self.col}")
        self.row, self.col = self.row + 1, c
        self.path.append(c)
        moss = self.moss[self.row][c]
        self.light = after_dig(self.light, self.cfg, self.dark[self.row][c], moss)
        got = self.gems[self.row][c]
        self.crystals += got
        self.score = self.crystals
        if self.light < climb_cost(self.row):
            self.finish(False)
            return "the lamp gutters out"
        return f"+{got}" + (" glowmoss" if moss else "")

    def demo_action(self):
        if len(self.path) < len(self.plan):
            return ("dig", self.plan[len(self.path)])
        return ("climb", 0)

    def render(self):
        cfg = self.cfg
        lines = [f"{TITLE} [{self.difficulty}] row {self.row} col {self.col} light {self.light}/{cfg['light']} "
                 f"crystals {self.crystals}/{self.target} climb {climb_cost(self.row)}"]
        for r in range(cfg["rows"]):
            cells = []
            for c in range(cfg["cols"]):
                here = "@" if (r, c) == (self.row, self.col) else " "
                cells.append(f"{here}{self.gems[r][c]}d{self.dark[r][c]}{'m' if self.moss[r][c] else ' '}")
            lines.append(f"{r:2d} " + " ".join(cells))
        if self.over:
            lines.append("WON: you climb out into the light, pockets glittering" if self.won else "LOST: the lamp gutters out")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        parts = line.split()
        if parts[0] == "climb":
            return ("climb", 0)
        if parts[0] == "dig" and len(parts) == 2:
            return ("dig", int(parts[1]))
        raise ValueError("use dig <column> or climb")


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
