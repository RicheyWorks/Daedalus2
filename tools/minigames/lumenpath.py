#!/usr/bin/env python3
"""Lumenpath Refraction: bend a Prismheart light beam with shard mirrors to wake every crystal.

A beam of prism light enters the lattice from the west edge. Each move toggles
one cell's shard mirror (empty -> / -> \\ -> empty). The beam reflects off
mirrors, passes through crystals (lighting them) and stops at cracked stone.
Light every crystal before the moves run out. Each newly lit crystal scores 10;
a win adds 20 per unused move. Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "lumenpath"
TITLE = "Lumenpath Refraction"
HOW_TO_PLAY = ("HOW Toggle shard mirrors in the lattice to bend the prism beam "
               "through every crystal before your moves run out.")
DIFFICULTY = {
    "easy": {"size": 5, "crystals": 2, "stones": 0, "moves": 12},
    "normal": {"size": 6, "crystals": 3, "stones": 2, "moves": 10},
    "hard": {"size": 7, "crystals": 4, "stones": 4, "moves": 9},
}
DEFAULT_DIFFICULTY = "normal"
CYCLE = {".": "/", "/": "\\", "\\": "."}
TURN = {"/": {"E": "N", "N": "E", "W": "S", "S": "W"},
        "\\": {"E": "S", "S": "E", "W": "N", "N": "W"}}
STEP = {"E": (0, 1), "W": (0, -1), "N": (-1, 0), "S": (1, 0)}


def trace(grid, source_row):
    """Cells the beam visits (in order) from the west edge at source_row."""
    n = len(grid)
    r, c, d = source_row, 0, "E"
    seen, path = set(), []
    while 0 <= r < n and 0 <= c < n and (r, c, d) not in seen:
        seen.add((r, c, d))
        cell = grid[r][c]
        if cell == "#":
            break
        path.append((r, c))
        if cell in TURN:
            d = TURN[cell][d]
        dr, dc = STEP[d]
        r, c = r + dr, c + dc
    return path


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("grid", "source_row", "crystals", "moves", "lit", "best", "solution")

    def setup(self):
        n = self.cfg["size"]
        while True:
            grid = [["."] * n for _ in range(n)]
            src = self.rng.randrange(n)
            r, c, d, mirrors, path = src, 0, "E", [], []
            while 0 <= r < n and 0 <= c < n and (r, c) not in path:
                path.append((r, c))
                if c > 0 and self.rng.random() < 0.35 and len(mirrors) < n:
                    m = self.rng.choice("/\\")
                    grid[r][c] = m
                    mirrors.append([r, c, m])
                    d = TURN[m][d]
                dr, dc = STEP[d]
                r, c = r + dr, c + dc
            if not (0 <= r < n and 0 <= c < n):
                free = [p for p in path if grid[p[0]][p[1]] == "."]
                if len(free) >= self.cfg["crystals"] and mirrors:
                    break
        crystals = sorted(self.rng.sample(free, self.cfg["crystals"]))
        clean = [["."] * n for _ in range(n)]
        for cr, cc in crystals:
            clean[cr][cc] = "*"
        others = [(i, j) for i in range(n) for j in range(n) if (i, j) not in path]
        for sr, sc in self.rng.sample(others, min(self.cfg["stones"], len(others))):
            clean[sr][sc] = "#"
        self.grid = ["".join(row) for row in clean]
        self.source_row = src
        self.crystals = [list(p) for p in crystals]
        self.solution = mirrors
        self.moves = max(self.cfg["moves"], sum(1 if m[2] == "/" else 2 for m in mirrors))
        self.lit = self._lit()
        self.best = self.lit
        if self.lit == len(self.crystals):
            self.setup()  # already solved without mirrors: draw again

    def _lit(self):
        on = set(trace(self.grid, self.source_row))
        return sum(1 for r, c in self.crystals if (r, c) in on)

    def act(self, action):
        r, c = action
        n = len(self.grid)
        if not (0 <= r < n and 0 <= c < n) or self.grid[r][c] in "*#":
            raise ValueError(f"cell {r},{c} cannot hold a mirror")
        row = list(self.grid[r])
        row[c] = CYCLE[row[c]]
        self.grid[r] = "".join(row)
        self.moves -= 1
        self.lit = self._lit()
        gained = 10 * max(0, self.lit - self.best)
        self.best = max(self.best, self.lit)
        if self.lit == len(self.crystals):
            gained += 20 * self.moves
            self.score += gained
            self.finish(True)
        else:
            self.score += gained
            if self.moves <= 0:
                self.finish(False)
        return gained

    def rescore(self):
        """10 per crystal lit past the mirror-free start; a win adds 20 per move left (Round 2 finding, prometheus 1)."""
        bare = ["".join(ch if ch in "*#" else "." for ch in row) for row in self.grid]
        on = set(trace(bare, self.source_row))
        start = sum(1 for r, c in self.crystals if (r, c) in on)
        return 10 * (self.best - start) + (20 * self.moves if self.won else 0)

    def demo_action(self):
        for r, c, m in self.solution:
            if self.grid[r][c] != m:
                return (r, c)
        n = len(self.grid)
        return next((i, j) for i in range(n) for j in range(n) if self.grid[i][j] in CYCLE)

    def render(self):
        on = set(trace(self.grid, self.source_row))
        rows = []
        for i, row in enumerate(self.grid):
            cells = "".join(("o" if ch == "*" and (i, j) in on else ch) for j, ch in enumerate(row))
            rows.append(("> " if i == self.source_row else "  ") + f"{i} " + cells)
        head = f"{TITLE} [{self.difficulty}] score {self.score} lit {self.lit}/{len(self.crystals)} moves {self.moves}"
        tail = ["WON: every crystal glows" if self.won else "LOST: the light fades"] if self.over else []
        return "\n".join([head, "    " + "".join(str(j % 10) for j in range(len(self.grid)))] + rows + tail)

    @staticmethod
    def parse(line):
        r, c = (int(x) for x in line.replace(",", " ").split())
        return (r, c)


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
