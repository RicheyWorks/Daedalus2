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
RULES_VERSION = 2  # bumped when a save from older rules would replay differently (2: unstable ledges)
DARK_GLYPHS = " .:"  # darkness 0, 1, 2
LIGHT_BAR = 12  # characters in the rendered lamp gauge
TUTORIAL = """Glowmoss Delve - how to play
1. You start on the surface above the shaft, lamp full. Row 0 is the top ledge row.
2. `dig C` drops you onto column C of the next row; C may be your column or one either side.
3. Each dig burns 1 light plus the ledge's darkness (. is 1, : is 2) and picks up its crystals.
4. Glowmoss (*) refills your lamp. Unstable ledges (!) crumble and drop you one more row for free.
5. Climbing out from row r costs (r + 2) // 2 light. If a dig leaves less than that, the lamp gutters: you lose.
6. `climb` ends the delve. Bring up at least the target to win; leftover light adds to your score,
   and matching the best possible haul earns a perfect-delve bonus.
Type `hint` for the best next move, `help` for this text, `q` to quit."""


SEED_CODE_MAX = 999_999_999  # 9 ASCII digits, the same limit as the native ParseSeedCode


def seed_code(seed, difficulty):
    """Shareable code for a shaft, e.g. GLOW-N-1337 (difficulty initial, then the seed). Seeds are 0..999999999 so
    every code parses back here and in DaedalusGlowmossCore.h::ParseSeedCode (Round 2 finding, art-master-flex 2)."""
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= SEED_CODE_MAX:
        raise ValueError(f"seed codes hold seeds 0..{SEED_CODE_MAX}")
    return f"{CODE_PREFIX}-{difficulty[0].upper()}-{seed}"


def parse_seed_code(code):
    """(seed, difficulty) from a seed code; ValueError says what is wrong."""
    parts = code.strip().upper().split("-")
    if len(parts) != 3 or parts[0] != CODE_PREFIX:
        raise ValueError(f"seed codes look like {CODE_PREFIX}-N-1337, not {code!r}")
    names = {name[0].upper(): name for name in DIFFICULTY}
    if parts[1] not in names:
        raise ValueError(f"difficulty letter must be one of {''.join(sorted(names))}")
    if not (1 <= len(parts[2]) <= 9 and all("0" <= ch <= "9" for ch in parts[2])):
        raise ValueError("the seed must be a whole number of 1 to 9 digits (0-9)")
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
    best, best_at, best_left = 0, None, -1

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
            left = l - climb_cost(r)  # ties keep the most light left after climbing out (it adds to a win's score)
            if v > best or (v == best and v > 0 and left > best_left):
                best, best_at, best_left = v, (r, c, l), left
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
        if kind == "hint":
            return self.hint_text()
        if kind == "climb":
            if not self.path and self.best > 0:
                raise ValueError("dig first: climbing out now ends the delve with nothing")
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

    def rescore(self):
        """Crystals while delving or after a loss; a win adds the light left and any perfect-delve bonus."""
        if not self.won:
            return self.crystals
        return self.crystals + self.light + (PERFECT_BONUS if self.perfect else 0)

    def hint_text(self):
        kind, c = self.hint()
        return "hint: climb out now" if kind == "climb" else f"hint: dig {c}"

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
        filled = LIGHT_BAR * max(0, self.light) // cfg["light"]
        lines = [f"{TITLE} [{self.difficulty}] {seed_code(self.seed, self.difficulty)}",
                 f"lamp [{'#' * filled}{'.' * (LIGHT_BAR - filled)}] {self.light}/{cfg['light']}  "
                 f"climb-out cost {climb_cost(self.row)}  crystals {self.crystals}/{self.target}",
                 "legend: @ you  v can dig  digit crystals  . : darkness  * glowmoss  ! unstable"]
        reach = dig_cols(self.col, cfg["cols"]) if not self.over and self.row + 1 < cfg["rows"] else range(0)
        lines.append("surface " + ("@" if self.row == SURFACE else ""))
        for r in range(cfg["rows"]):
            cells = []
            for c in range(cfg["cols"]):
                mark = "@" if (r, c) == (self.row, self.col) else "v" if r == self.row + 1 and c in reach else " "
                cells.append(mark + str(self.gems[r][c]) + DARK_GLYPHS[self.dark[r][c]]
                             + ("*" if self.moss[r][c] else " ") + ("!" if self.unstable[r][c] else " "))
            lines.append(f"row {r:2d}  " + " ".join(cells))
        if self.over:
            badge = " (perfect delve)" if self.perfect else ""
            lines.append(f"WON{badge}: you climb out into the light, pockets glittering" if self.won
                         else "LOST: the lamp gutters out" if self.light < climb_cost(self.row) else
                         "LOST: you climbed out short of the target")
        return "\n".join(lines)

    def to_state(self):
        st = super().to_state()
        st["rules"] = RULES_VERSION
        return st

    @classmethod
    def from_state(cls, state):
        check_save(state)
        return super().from_state(state)

    @staticmethod
    def parse(line):
        parts = line.lower().split()
        if parts == ["help"]:
            raise ValueError(TUTORIAL)
        if parts == ["hint"]:
            return ("hint", 0)
        if parts == ["climb"]:
            return ("climb", 0)
        if len(parts) == 2 and parts[0] == "dig":
            if not parts[1].isdigit():
                raise ValueError(f"dig needs a column number, not {parts[1]!r}")
            return ("dig", int(parts[1]))
        raise ValueError("use dig <column> or climb")


def check_save(state):
    """Raise ValueError naming the first thing wrong with a Glowmoss save, before any of it is loaded."""
    if not isinstance(state, dict) or state.get("id") != GAME_ID or state.get("v") != 1:
        raise ValueError(f"not a {GAME_ID} v1 save")
    if state.get("rules") != RULES_VERSION:
        raise ValueError(f"save is for rules version {state.get('rules')}, this game is version {RULES_VERSION}")
    cfg = DIFFICULTY.get(state.get("difficulty"))
    if cfg is None:
        raise ValueError(f"unknown difficulty {state.get('difficulty')!r}")
    for name, low, high in (("gems", MIN_GEMS, MAX_GEMS), ("dark", 0, MAX_DARK), ("moss", 0, 1), ("unstable", 0, 1)):
        rows = state.get(name)
        if (not isinstance(rows, list) or len(rows) != cfg["rows"]
                or any(not isinstance(row, list) or len(row) != cfg["cols"] for row in rows)
                or any(not isinstance(x, int) or not low <= x <= high for row in rows for x in row)):
            raise ValueError(f"save grid {name!r} is not {cfg['rows']} rows of {cfg['cols']} values in {low}-{high}")
    row, col, light, path = state.get("row"), state.get("col"), state.get("light"), state.get("path")
    if not (isinstance(row, int) and SURFACE <= row < cfg["rows"] and isinstance(col, int) and 0 <= col < cfg["cols"]):
        raise ValueError(f"save position row {row!r} col {col!r} is outside the shaft")
    if not isinstance(light, int) or light > cfg["light"]:
        raise ValueError(f"save light {light!r} is not a whole number up to the lamp's {cfg['light']}")
    if not isinstance(path, list) or len(path) > row + 1 or (path and path[-1] != col):
        raise ValueError("save path does not end at the saved column")


def start(seed=0, difficulty=DEFAULT_DIFFICULTY):
    return Game(seed, difficulty)


def demo(seed=0, difficulty=DEFAULT_DIFFICULTY, out=None):
    return pc.demo(Game, seed, difficulty, out)


def play(seed, difficulty, inp=sys.stdin, out=sys.stdout):
    return pc.play(Game, seed, difficulty, inp, out)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--tutorial" in argv:
        print(TUTORIAL)
        return 0
    return pc.main(Game, argv)


if __name__ == "__main__":
    sys.exit(main())
