#!/usr/bin/env python3
"""Emberkiln: fire a kiln floor of clay tiles to their exact glaze heat before the coals run out.

A seeded S x S kiln floor. Most cells are clay tiles with a firing target of
2, 3 or 4; a few are stone and take no heat. Each turn you set one coal on
any cell: a raw clay tile under it gains 2 heat and each of its four
neighbours gains 1 (a coal on stone or on a finished tile only warms the
neighbours, which is how a tile one short of its target is finished). A tile whose heat reaches its target exactly glazes and
is finished (later heat passes it by); a tile whose heat passes its target
cracks and is lost. Glaze every tile to win; running out of coals with clay
still raw loses. Score 5 per glazed tile, -3 per crack, +2 per coal left on
a win. Stdlib only, deterministic per seed: randrange only at setup, nothing
random after.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "emberkiln"
TITLE = "Emberkiln"
HOW_TO_PLAY = ("HOW Set a coal: the clay under it gains 2 heat and its neighbours gain 1 (stone and finished tiles only "
               "warm neighbours). A tile glazes at exactly its target and cracks past it. Glaze every tile before the coals run out.")
DIFFICULTY = {
    "easy": {"size": 5, "stone": 4, "coals": 19},
    "normal": {"size": 6, "stone": 6, "coals": 27},
    "hard": {"size": 7, "stone": 8, "coals": 36},
}
DEFAULT_DIFFICULTY = "normal"
STONE, GLAZED, CRACKED = 0, -1, -2   # target codes beside the firing targets 2..4
TARGETS = (2, 3, 4)
COAL_HEAT, SPREAD_HEAT = 2, 1
GLAZE_SCORE, CRACK_SCORE, COAL_BONUS = 5, -3, 2
NEIGHBOURS = ((-1, 0), (0, 1), (1, 0), (0, -1))


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("target", "heat", "coals", "glazed", "cracked")

    def setup(self):
        s = self.cfg["size"]
        self.target = [[TARGETS[self.rng.randrange(len(TARGETS))] for _ in range(s)] for _ in range(s)]
        placed = 0
        while placed < self.cfg["stone"]:
            r, c = self.rng.randrange(s), self.rng.randrange(s)
            if self.target[r][c] != STONE:
                self.target[r][c] = STONE
                placed += 1
        self.heat = [[0] * s for _ in range(s)]
        self.coals, self.glazed, self.cracked = self.cfg["coals"], 0, 0

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5)."""
        g = super().from_state(state)
        s = g.cfg["size"]
        grid = lambda v, ok: isinstance(v, list) and len(v) == s and all(isinstance(row, list) and len(row) == s and all(isinstance(x, int) and ok(x) for x in row) for row in v)  # noqa: E731
        ok = (grid(g.target, lambda x: x in TARGETS or x in (STONE, GLAZED, CRACKED))
              and grid(g.heat, lambda x: 0 <= x <= max(TARGETS) + COAL_HEAT)
              and sum(t == STONE for row in g.target for t in row) == g.cfg["stone"]
              and all(h == 0 for row, hrow in zip(g.target, g.heat) for t, h in zip(row, hrow) if t == STONE)
              and all(h < t for row, hrow in zip(g.target, g.heat) for t, h in zip(row, hrow) if t > 0)
              and isinstance(g.coals, int) and 0 <= g.coals <= g.cfg["coals"]
              and g.glazed == sum(t == GLAZED for row in g.target for t in row)
              and g.cracked == sum(t == CRACKED for row in g.target for t in row)
              and g.over == (g.clay() == 0 or g.coals <= 0) and g.won == (g.clay() == 0 and g.cracked == 0))
        if not ok:
            raise ValueError("emberkiln save does not satisfy the rules")
        return g

    def size(self):
        return self.cfg["size"]

    def clay(self):
        """Count of tiles still to glaze."""
        return sum(1 for row in self.target for t in row if t > 0)

    def inside(self, r, c):
        s = self.size()
        return 0 <= r < s and 0 <= c < s

    def parse_cell(self, action):
        parts = action.split(",") if "," in action else action.split()
        if len(parts) != 2:
            raise ValueError("use row,col")
        try:
            r, c = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError("use row,col") from None
        if not self.inside(r, c):
            raise ValueError("off the kiln floor")
        return r, c

    def heat_cell(self, r, c, amount):
        """Adds heat; returns +1 for a glaze, -1 for a crack, 0 otherwise. Stone and finished tiles take none."""
        t = self.target[r][c]
        if t <= 0:
            return 0
        self.heat[r][c] += amount
        if self.heat[r][c] == t:
            self.target[r][c] = GLAZED
            return 1
        if self.heat[r][c] > t:
            self.target[r][c] = CRACKED
            return -1
        return 0

    def act(self, action):
        r, c = self.parse_cell(action)
        self.coals -= 1
        glazes = cracks = 0
        for (dr, dc), amount in (((0, 0), COAL_HEAT),) + tuple((d, SPREAD_HEAT) for d in NEIGHBOURS):
            rr, cc = r + dr, c + dc
            if self.inside(rr, cc):
                result = self.heat_cell(rr, cc, amount)
                glazes += result == 1
                cracks += result == -1
        self.glazed += glazes
        self.cracked += cracks
        self.score += GLAZE_SCORE * glazes + CRACK_SCORE * cracks
        if self.clay() == 0:
            if self.cracked == 0:
                self.score += COAL_BONUS * self.coals
                self.finish(True)
                return f"{r},{c}: {glazes} glazed, the whole floor shines"
            self.finish(False)
            return f"{r},{c}: {glazes} glazed, {cracks} cracked; the firing is spoiled"
        if self.coals <= 0:
            self.finish(False)
            return f"{r},{c}: {glazes} glazed, {cracks} cracked; the coals are spent"
        return f"{r},{c}: {glazes} glazed, {cracks} cracked, {self.clay()} raw"

    def preview(self, r, c):
        """(glazes, cracks, raised) a coal at r,c would cause, without placing it (iteration 8)."""
        if not self.inside(r, c):
            return None
        glazes = cracks = raised = 0
        for (dr, dc), amount in (((0, 0), COAL_HEAT),) + tuple((d, SPREAD_HEAT) for d in NEIGHBOURS):
            rr, cc = r + dr, c + dc
            if not self.inside(rr, cc) or self.target[rr][cc] <= 0:
                continue
            after = self.heat[rr][cc] + amount
            if after == self.target[rr][cc]:
                glazes += 1
            elif after > self.target[rr][cc]:
                cracks += 1
            else:
                raised += 1
        return glazes, cracks, raised

    def demo_action(self):
        """Stoker: the coal that cracks nothing and glazes most, then raises most heat; ties by row, column.

        If every placement cracks something, the one that cracks least and glazes most.
        """
        s = self.size()
        best = None
        for r in range(s):
            for c in range(s):
                p = self.preview(r, c)
                if p is None:
                    continue
                glazes, cracks, raised = p
                key = (cracks, -glazes, -raised, r, c)
                if best is None or key < best[0]:
                    best = (key, (r, c))
        return "%d,%d" % best[1] if best else "0,0"

    def render(self):
        s = self.size()
        rows = []
        for r in range(s):
            row = []
            for c in range(s):
                t = self.target[r][c]
                row.append("##" if t == STONE else "**" if t == GLAZED else "xx" if t == CRACKED else f"{self.heat[r][c]}/{t}")
            rows.append(" ".join(row))
        lines = [f"{TITLE} [{self.difficulty}] coals {self.coals} glazed {self.glazed} cracked {self.cracked} raw {self.clay()} score {self.score}"] + rows
        if self.over:
            lines.append("WON: the whole floor shines" if self.won else "LOST: the firing is spoiled")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        return line.strip().lower().replace(" ", ",")


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
