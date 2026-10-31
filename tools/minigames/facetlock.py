#!/usr/bin/env python3
"""Facetlock Lattice: shift rows and columns of a prism lattice until every facet row glows one hue.

The Prismheart vault lock is a square lattice of coloured facets, scrambled by
seeded shifts. Each move slides one row left/right or one column up/down
(wrapping). Restore the pattern (row r all hue r) within the move budget.
A win scores 100 + 10 per unused move. Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "facetlock"
TITLE = "Facetlock Lattice"
HOW_TO_PLAY = ("HOW Slide lattice rows and columns (they wrap) until each row shows a single hue; "
               "finish inside the move budget.")
DIFFICULTY = {
    "easy": {"size": 3, "scramble": 3, "spare": 4},
    "normal": {"size": 4, "scramble": 5, "spare": 4},
    "hard": {"size": 5, "scramble": 7, "spare": 3},
}
DEFAULT_DIFFICULTY = "normal"
MARKS = "ETVGU"


def shift(board, kind, i, d):
    b = [list(r) for r in board]
    n = len(b)
    if kind == "r":
        b[i] = [b[i][(j - d) % n] for j in range(n)]
    else:
        col = [b[r][i] for r in range(n)]
        for r in range(n):
            b[r][i] = col[(r - d) % n]
    return ["".join(r) for r in b]


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    BOON = ("spare", 1, "Thornkin")  # Spirit Boon (hephaestus R2-9, accepted Oct 31, 2026)
    FIELDS = ("board", "moves", "solution")

    def target(self):
        n = self.cfg["size"]
        return [MARKS[r] * n for r in range(n)]

    def setup(self):
        n = self.cfg["size"]
        while True:
            board, sol, last = self.target(), [], None
            for _ in range(self.cfg["scramble"]):
                while True:
                    m = [self.rng.choice("rc"), self.rng.randrange(n), self.rng.choice((1, -1))]
                    if last is None or not (m[0] == last[0] and m[1] == last[1] and m[2] == -last[2]):
                        break
                board = shift(board, *m)
                sol.insert(0, [m[0], m[1], -m[2]])
                last = m
            if board != self.target():
                break
        self.board, self.solution = board, sol
        self.moves = self.cfg["scramble"] + self.cfg["spare"]

    def act(self, action):
        kind, i, d = action
        n = self.cfg["size"]
        if kind not in ("r", "c") or not 0 <= i < n or d not in (1, -1):
            raise ValueError("use r|c <index> +1|-1")
        self.board = shift(self.board, kind, i, d)
        self.moves -= 1
        if self.solution and self.solution[0] == [kind, i, d]:
            self.solution.pop(0)
        else:
            self.solution.insert(0, [kind, i, -d])
        if self.board == self.target():
            gained = 100 + 10 * self.moves
            self.score += gained
            self.finish(True)
            return gained
        if self.moves <= 0:
            self.finish(False)
        return 0

    def demo_action(self):
        return tuple(self.solution[0])

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] score {self.score} moves {self.moves}",
                 "   " + " ".join(str(j) for j in range(len(self.board)))]
        lines += [f"{i}  " + " ".join(r) for i, r in enumerate(self.board)]
        if self.over:
            lines.append("WON: the vault lock opens" if self.won else "LOST: the lock seals")
        else:
            lines.append("goal: row 0 all %s, row 1 all %s ... | move: r <row> +1|-1 or c <col> +1|-1" % (MARKS[0], MARKS[1]))
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        """r|c <index> +1|-1; anything else gets the move syntax back, never a Python error (Round 2 self-test)."""
        parts = line.split()
        if len(parts) == 3 and parts[0] in ("r", "c") and parts[1].isascii() and parts[1].isdigit() and parts[2] in ("1", "+1", "-1"):
            return (parts[0], int(parts[1]), int(parts[2]))
        raise ValueError("use r|c <index> +1|-1")


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
