#!/usr/bin/env python3
"""Fogbell Ferry: steer a ferry over a tidal flat, collect lantern passengers from the docks, and make harbour before the tide takes your cell.

A seeded S x S flat of integer heights (1..S, the higher of two draws). The ferry starts in the
north-west corner; the harbour is the south-east corner; both sit on the
highest ground. Passengers wait on dock cells. Each turn the ferry moves one
cell (n/e/s/w) or waits; then the fog bell tolls and the tide stands at
turn // 3, flooding every cell at or below it for good. Entering a dock takes
its passenger aboard. Entering the harbour ends the voyage: it is won when at
least `need` passengers are aboard. A flooded ferry cell ends it lost. Score
10 per passenger landed plus 2 per tide step still to come at landing. Stdlib
only, deterministic per seed, randrange only.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "fogbell"
TITLE = "Fogbell Ferry"
HOW_TO_PLAY = ("HOW Move the ferry one cell a turn across the tidal flat, pick up the lantern passengers from their "
               "docks and reach the harbour before the rising tide floods your cell.")
DIFFICULTY = {
    "easy": {"size": 7, "passengers": 3, "need": 2},
    "normal": {"size": 8, "passengers": 4, "need": 3},
    "hard": {"size": 9, "passengers": 5, "need": 4},
}
DEFAULT_DIFFICULTY = "normal"
MOVES = {"n": (-1, 0), "e": (0, 1), "s": (1, 0), "w": (0, -1), "wait": (0, 0)}
ORDER = ("n", "e", "s", "w")
PASSENGER_SCORE, TIDE_SCORE = 10, 2
TIDE_EVERY = 3   # the bell tolls every third turn; tide = turn // TIDE_EVERY


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("heights", "ferry", "harbour", "passengers", "aboard", "turn")

    def setup(self):
        s = self.cfg["size"]
        # two draws per cell, the higher wins: a flat that is mostly firm with scattered low channels
        self.heights = [[1 + max(self.rng.randrange(s), self.rng.randrange(s)) for _ in range(s)] for _ in range(s)]
        self.ferry, self.harbour = [0, 0], [s - 1, s - 1]
        self.heights[0][0] = self.heights[s - 1][s - 1] = s
        self.passengers = []
        while len(self.passengers) < self.cfg["passengers"]:
            r, c = self.rng.randrange(s), self.rng.randrange(s)
            if [r, c] in ([0, 0], [s - 1, s - 1]) or [r, c] in self.passengers:
                continue
            self.passengers.append([r, c])
            self.heights[r][c] = max(self.heights[r][c], 2)
        self.aboard, self.turn = 0, 0

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5): the flat is fixed by the seed."""
        g = super().from_state(state)
        fresh = cls(g.seed, g.difficulty)
        s = g.cfg["size"]
        in_flat = lambda cell: isinstance(cell, list) and len(cell) == 2 and all(isinstance(v, int) and 0 <= v < s for v in cell)  # noqa: E731
        ok = (g.heights == fresh.heights and g.harbour == fresh.harbour and in_flat(g.ferry)
              and all(in_flat(p) and p in fresh.passengers for p in g.passengers)
              and len({tuple(p) for p in g.passengers}) == len(g.passengers)
              and isinstance(g.aboard, int) and isinstance(g.turn, int) and 0 <= g.turn <= TIDE_EVERY * s
              and g.aboard + len(g.passengers) == g.cfg["passengers"]
              and (g.over or not g.flooded(*g.ferry)))
        if not ok:
            raise ValueError("fogbell save does not satisfy the rules")
        return g

    @property
    def tide(self):
        return self.turn // TIDE_EVERY

    def tide_at(self, turn):
        return turn // TIDE_EVERY

    def flooded(self, r, c, turn=None):
        return self.heights[r][c] <= self.tide_at(self.turn if turn is None else turn)

    def size(self):
        return self.cfg["size"]

    def act(self, action):
        if action not in MOVES:
            raise ValueError("use n, e, s, w or wait")
        dr, dc = MOVES[action]
        r, c = self.ferry[0] + dr, self.ferry[1] + dc
        s = self.size()
        if not (0 <= r < s and 0 <= c < s):
            raise ValueError("off the flat")
        if self.flooded(r, c):
            raise ValueError("that cell is under water")
        self.ferry = [r, c]
        picked = False
        if [r, c] in self.passengers:
            self.passengers.remove([r, c])
            self.aboard += 1
            picked = True
        self.turn += 1
        if [r, c] == self.harbour:
            left = TIDE_EVERY * s - self.turn
            self.score = PASSENGER_SCORE * self.aboard + TIDE_SCORE * max(0, left)
            self.finish(self.aboard >= self.cfg["need"])
            return f"{action}: harbour with {self.aboard} aboard, {'the bell rings clear' if self.won else 'too few lanterns'}"
        if self.flooded(r, c):
            self.finish(False)
            return f"{action}: the tide takes the ferry"
        return f"{action}: {'lantern aboard' if picked else 'open water'}, tide {self.tide}"

    def _bfs(self, goals):
        """Shortest flood-aware path (n/e/s/w order) from the ferry to the first goal reached; None if none."""
        s = self.size()
        start = tuple(self.ferry)
        goal_set = {tuple(g) for g in goals}
        prev = {start: None}
        frontier = [start]
        step = 0
        while frontier:
            step += 1
            nxt = []
            for cell in frontier:
                for name in ORDER:
                    dr, dc = MOVES[name]
                    r, c = cell[0] + dr, cell[1] + dc
                    if not (0 <= r < s and 0 <= c < s) or (r, c) in prev:
                        continue
                    if self.heights[r][c] <= self.tide_at(self.turn + step):
                        continue
                    prev[(r, c)] = (cell, name)
                    if (r, c) in goal_set:
                        path = []
                        cur = (r, c)
                        while prev[cur] is not None:
                            cur, name2 = prev[cur]
                            path.append(name2)
                        return list(reversed(path))
                    nxt.append((r, c))
            frontier = nxt
        return None

    def demo_action(self):
        """Nearest reachable passenger until enough are aboard, then the harbour; wait when nothing is reachable."""
        if self.aboard < self.cfg["need"] and self.passengers:
            path = self._bfs(self.passengers)
            if path:
                return path[0]
        path = self._bfs([self.harbour])
        if path:
            return path[0]
        if self.passengers:
            path = self._bfs(self.passengers)
            if path:
                return path[0]
        return "wait"

    def render(self):
        s = self.size()
        rows = []
        for r in range(s):
            row = ""
            for c in range(s):
                if [r, c] == self.ferry:
                    row += "F"
                elif [r, c] == self.harbour:
                    row += "H"
                elif [r, c] in self.passengers:
                    row += "L"
                elif self.flooded(r, c):
                    row += "~"
                else:
                    row += str(self.heights[r][c])
            rows.append(row)
        lines = [f"{TITLE} [{self.difficulty}] turn {self.turn} tide {self.tide} aboard {self.aboard}/{self.cfg['need']} score {self.score}"] + rows
        if self.over:
            lines.append("WON: the bell rings clear" if self.won else "LOST: the tide takes the ferry")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        line = line.strip().lower()
        if line not in MOVES:
            raise ValueError("use n, e, s, w or wait")
        return line


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
