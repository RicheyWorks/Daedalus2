#!/usr/bin/env python3
"""Glowmoss Delve: climb down a seeded crystal shaft in Prismheart on a light budget and climb out richer.

The shaft is a grid of ledges, row 0 at the top. From the surface you dig down one row at a time onto a ledge in
the next row at most one column left or right of where you stand. Each dig burns light (1 + the ledge's darkness)
and gathers the ledge's crystals; a glowmoss ledge then refills light up to the lamp's capacity. An unstable ledge
crumbles under you and drops you onto the ledge straight below (no dig cost), gathering its crystals and glowmoss
too; the fall never chains and there is nothing below the last row. Climbing out from
row r costs (r + 2) // 2 light, and if a dig leaves too little light to climb out the lamp gutters and the delve
is lost. Climb out with crystals worth at least the target to win (score = crystals + light left, plus a bonus for
a perfect delve that matches the best possible crystal total). Every target is
reachable: it is a share of the best possible delve (exact search). Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "glowmoss"
TITLE = "Glowmoss Delve"
HOW_TO_PLAY = ("HOW Dig down the shaft one ledge at a time to gather crystals; glowmoss refills your lamp and "
               "unstable ledges drop you one row. Climb out before the light is too low to carry you back up.")
DIFFICULTY = {
    "easy": {"cols": 3, "rows": 8, "light": 12, "refill": 4, "moss_pct": 25, "unstable_pct": 10, "target_pct": 75},
    "normal": {"cols": 4, "rows": 10, "light": 11, "refill": 3, "moss_pct": 18, "unstable_pct": 12, "target_pct": 80},
    "hard": {"cols": 5, "rows": 12, "light": 10, "refill": 3, "moss_pct": 12, "unstable_pct": 15, "target_pct": 86},
}
DEFAULT_DIFFICULTY = "normal"
SURFACE = -1
REACH = 1  # a dig lands at most this many columns left or right
MAX_DARK = 2
MIN_GEMS, MAX_GEMS = 1, 5
PERCENT = 100
PERFECT_BONUS = 5  # added to a winning score that gathered the best possible crystal total
CODE_PREFIX = "GLOW"


def seed_code(seed, difficulty):
    """Shareable code for a shaft, e.g. GLOW-N-1337 (difficulty initial, then the seed)."""
    return f"{CODE_PREFIX}-{difficulty[0].upper()}-{seed}"


def parse_seed_code(code):
    """(seed, difficulty) from a seed code; ValueError says what is wrong."""
    parts = code.strip().upper().split("-")
    if len(parts) != 3 or parts[0] != CODE_PREFIX:
        raise ValueError(f"seed codes look like {CODE_PREFIX}-N-1337, not {code!r}")
    names = {name[0].upper(): name for name in DIFFICULTY}
    if parts[1] not in names:
        raise ValueError(f"difficulty letter must be one of {''.join(sorted(names))}")
    if not parts[2].isdigit():
        raise ValueError("the seed must be a whole number")
    return int(parts[2]), names[parts[1]]


def daily_seed(year, month, day):
    """Everyone delves the same shaft on the same day: the date as YYYYMMDD."""
    return year * 10000 + month * 100 + day


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


def land(cfg, shaft, row, col, light):
    """Dig onto (row, col) from above: (final row, light, crystals gathered, glowmoss touched, fell)."""
    gems, dark, moss, unstable = shaft
    light = after_dig(light, cfg, dark[row][col], moss[row][col])
    got, mossy, fell = gems[row][col], moss[row][col], False
    if unstable[row][col] and row + 1 < cfg["rows"]:
        row, fell = row + 1, True
        got += gems[row][col]
        if moss[row][col]:
            light = min(cfg["light"], light + cfg["refill"])
            mossy = True
    return row, light, got, mossy, fell


def best_delve(cfg, shaft, start=None):
    """(best extra crystals, dig columns) over every delve from start (row, col, light; default the surface) that can
    still climb out. Exact DP over (row, col, light).

    A fall lands two rows down, so layers are kept per row and each is expanded once all rows above it are done.
    """
    rows, cols = cfg["rows"], cfg["cols"]
    layers = [dict() for _ in range(rows)]  # row -> {(col, light): (crystals, previous (row, col, light))}
    start = start or (SURFACE, cols // 2, cfg["light"])
    best, best_at = 0, None

    def expand(r0, c, l, v):
        r = r0 + 1
        for u in dig_cols(c, cols):
            fr, nl, got, _, _ = land(cfg, shaft, r, u, l)
            if nl < climb_cost(fr):
                continue
            nv, key = v + got, (u, nl)
            if key not in layers[fr] or nv > layers[fr][key][0]:
                layers[fr][key] = (nv, (r0, c, l))

    if start[0] + 1 < rows:
        expand(*start, 0)
    for r in range(rows):
        for (c, l), (v, _) in sorted(layers[r].items()):
            if v > best:
                best, best_at = v, (r, c, l)
            if r + 1 < rows:
                expand(r, c, l, v)
    plan = []
    at = best_at
    while at and at != start:
        r, c, l = at
        prev = layers[r][(c, l)][1]
        plan.append(c)
        at = prev
    return best, plan[::-1]


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("gems", "dark", "moss", "unstable", "row", "col", "light", "crystals", "best", "target", "plan", "path",
              "perfect")

    def setup(self):
        cfg = self.cfg
        self.gems, self.dark, self.moss, self.unstable = [], [], [], []
        for _ in range(cfg["rows"]):
            g, d, m, u = [], [], [], []
            for _ in range(cfg["cols"]):
                g.append(self.rng.randint(MIN_GEMS, MAX_GEMS))
                d.append(self.rng.randint(0, MAX_DARK))
                m.append(self.rng.randrange(PERCENT) < cfg["moss_pct"])
                u.append(self.rng.randrange(PERCENT) < cfg["unstable_pct"])
            self.gems.append(g)
            self.dark.append(d)
            self.moss.append(m)
            self.unstable.append(u)
        self.best, self.plan = best_delve(cfg, self.shaft())
        self.target = max(1, self.best * cfg["target_pct"] // PERCENT)
        self.row, self.col, self.light, self.crystals, self.path = SURFACE, cfg["cols"] // 2, cfg["light"], 0, []
        self.perfect = False

    def shaft(self):
        return self.gems, self.dark, self.moss, self.unstable

    def act(self, action):
        kind, c = action
        if kind == "climb":
            won = self.crystals >= self.target
            self.light -= climb_cost(self.row)
            self.perfect = won and self.crystals == self.best
            self.score = self.crystals + (self.light if won else 0) + (PERFECT_BONUS if self.perfect else 0)
            self.finish(won)
            return f"climbed out with {self.crystals}" + (" (perfect delve)" if self.perfect else "")
        if kind != "dig":
            raise ValueError(f"unknown action {kind!r}: use dig or climb")
        if self.row + 1 >= self.cfg["rows"]:
            raise ValueError(f"row {self.row} is the shaft floor; nothing left but to climb")
        if not isinstance(c, int) or c not in dig_cols(self.col, self.cfg["cols"]):
            reach = dig_cols(self.col, self.cfg["cols"])
            raise ValueError(f"from column {self.col} you can dig columns {reach.start}-{reach.stop - 1}, not {c!r}")
        self.row, self.light, got, mossy, fell = land(self.cfg, self.shaft(), self.row + 1, c, self.light)
        self.col = c
        self.path.append(c)
        self.crystals += got
        self.score = self.crystals
        if self.light < climb_cost(self.row):
            self.finish(False)
            return "the lamp gutters out"
        return f"+{got}" + (" glowmoss" if mossy else "") + (" crumble" if fell else "")

    def hint(self):
        """Best next move from here: the first dig of the best delve from the current ledge, else climb out."""
        _, plan = best_delve(self.cfg, self.shaft(), (self.row, self.col, self.light))
        return ("dig", plan[0]) if plan else ("climb", 0)

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
                cells.append(f"{here}{self.gems[r][c]}d{self.dark[r][c]}{'m' if self.moss[r][c] else ' '}{'u' if self.unstable[r][c] else ' '}")
            lines.append(f"{r:2d} " + " ".join(cells))
        if self.over:
            lines.append("WON: you climb out into the light, pockets glittering" if self.won else "LOST: the lamp gutters out")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        parts = line.lower().split()
        if parts == ["climb"]:
            return ("climb", 0)
        if len(parts) == 2 and parts[0] == "dig":
            if not parts[1].isdigit():
                raise ValueError(f"dig needs a column number, not {parts[1]!r}")
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
