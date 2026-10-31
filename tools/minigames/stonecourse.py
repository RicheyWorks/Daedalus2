#!/usr/bin/env python3
"""Stonecourse: lay a seeded supply of stones into a dry-stone wall, course by course, with no overhang.

The wall is `width` cells across and `courses` high. Stones (widths 1-3) come
off the supply in order; each turn you set the next stone at a column of the
lowest course that can take it there: every cell under the stone must be
filled (or be the footing) and the cells it covers must be empty. A course
with no gaps locks and scores. You may skip a stone a few times (it goes to
the rubble). The wall is finished when every course locks; the build fails
when the supply runs out or the next stone fits nowhere and no skips are left.
Score 10 per locked course, 2 per stone left in the supply on a finish, 3 per
skip unused. Stdlib only, deterministic per seed: randrange only at setup,
nothing random after.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "stonecourse"
TITLE = "Stonecourse"
HOW_TO_PLAY = ("HOW Set the next stone at a column (it lands on the lowest course that supports it fully) or skip it. "
               "Lock every course with no gaps before the supply runs out.")
DIFFICULTY = {
    "easy": {"width": 7, "courses": 4, "supply": 20, "skips": 3},
    "normal": {"width": 8, "courses": 5, "supply": 26, "skips": 3},
    "hard": {"width": 9, "courses": 6, "supply": 34, "skips": 3},
}
DEFAULT_DIFFICULTY = "normal"
MIN_WIDTH, MAX_WIDTH = 1, 3
COURSE_SCORE, STONE_BONUS, SKIP_BONUS = 10, 2, 3
SEARCH_NODES = 20000   # mason search budget per pick (same in the C++ core)
MAX_REDRAWS = 50       # supplies drawn before setup keeps the last one


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("stones", "index", "wall", "locked", "skips_left")

    def setup(self):
        """Draw supplies until the mason's bounded search can finish the wall, so every build is solvable."""
        cfg = self.cfg
        for _ in range(MAX_REDRAWS):
            self.stones = [MIN_WIDTH + self.rng.randrange(MAX_WIDTH - MIN_WIDTH + 1) for _ in range(cfg["supply"])]
            self.wall = [[0] * cfg["width"] for _ in range(cfg["courses"])]   # 0 empty, 1 stone
            self.index, self.locked, self.skips_left = 0, 0, cfg["skips"]
            if self.search() is not None:
                break

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5)."""
        g = super().from_state(state)
        cfg = g.cfg
        w, h = cfg["width"], cfg["courses"]
        ok = (isinstance(g.stones, list) and len(g.stones) == cfg["supply"] and all(isinstance(s, int) and MIN_WIDTH <= s <= MAX_WIDTH for s in g.stones)
              and isinstance(g.index, int) and 0 <= g.index <= cfg["supply"]
              and isinstance(g.wall, list) and len(g.wall) == h and all(isinstance(row, list) and len(row) == w and all(x in (0, 1) for x in row) for row in g.wall)
              and all(g.wall[k][c] == 0 or k == 0 or g.wall[k - 1][c] == 1 for k in range(h) for c in range(w))
              and isinstance(g.locked, int) and g.locked == sum(1 for row in g.wall if all(row))
              and isinstance(g.skips_left, int) and 0 <= g.skips_left <= cfg["skips"]
              and sum(sum(row) for row in g.wall) <= sum(g.stones[:g.index])
              and g.won == (g.locked == h) and (g.over or not (g.won or g.index >= cfg["supply"]))
              and (not g.over or g.won or g.index >= cfg["supply"] or (g.skips_left == 0 and not g.placements())))
        if not ok:
            raise ValueError("stonecourse save does not satisfy the rules")
        return g

    def width(self):
        return self.cfg["width"]

    def next_stone(self):
        return self.stones[self.index] if self.index < len(self.stones) else 0

    def landing(self, col, size=None):
        """The course the next stone (or `size`) would occupy at `col`, or None when it fits nowhere there.

        The stone rests on the lowest course whose cells under it are all filled (the footing counts) and whose own
        cells are all empty; a cell that is empty with a filled cell above it never arises, so this is the first
        course where the cells are empty.
        """
        size = size or self.next_stone()
        w = self.width()
        if size <= 0 or col < 0 or col + size > w:
            return None
        for k in range(self.cfg["courses"]):
            cells = self.wall[k][col:col + size]
            if all(x == 0 for x in cells):
                below = [1] * size if k == 0 else self.wall[k - 1][col:col + size]
                return k if all(x == 1 for x in below) else None
        return None

    def placements(self, size=None):
        """Legal columns for the next stone (or `size`), left to right."""
        return [c for c in range(self.width()) if self.landing(c, size) is not None]

    def act(self, action):
        if action == "skip":
            if self.skips_left <= 0:
                raise ValueError("no skips left")
            if self.index >= len(self.stones):
                raise ValueError("the supply is empty")
            self.skips_left -= 1
            self.index += 1
            return self._settle(f"skip: stone to the rubble, {self.skips_left} skips left")
        try:
            col = int(action)
        except (TypeError, ValueError):
            raise ValueError("use a column number or skip") from None
        k = self.landing(col)
        if k is None:
            raise ValueError(f"a {self.next_stone()}-stone does not rest at column {col}")
        size = self.next_stone()
        for c in range(col, col + size):
            self.wall[k][c] = 1
        self.index += 1
        newly = 1 if all(self.wall[k]) else 0
        self.locked += newly
        self.score += COURSE_SCORE * newly
        return self._settle(f"{col}: {size}-stone on course {k}" + ("; the course locks" if newly else ""))

    def _settle(self, text):
        if self.locked == self.cfg["courses"]:
            self.score += STONE_BONUS * (len(self.stones) - self.index) + SKIP_BONUS * self.skips_left
            self.finish(True)
            return text + "; the wall stands"
        if self.index >= len(self.stones):
            self.finish(False)
            return text + "; the supply runs out"
        if not self.placements() and self.skips_left <= 0:
            self.finish(False)
            return text + "; the stone fits nowhere"
        return text

    def preview(self, action):
        """(legal, course, locks) for setting the next stone at `action`, without setting it (iteration 8)."""
        if action == "skip":
            return (self.skips_left > 0 and self.index < len(self.stones), None, False)
        try:
            col = int(action)
        except (TypeError, ValueError):
            return (False, None, False)
        k = self.landing(col)
        if k is None:
            return (False, None, False)
        size = self.next_stone()
        row = self.wall[k][:]
        for c in range(col, col + size):
            row[c] = 1
        return (True, k, all(row))

    # --- the mason (demo) -------------------------------------------------------------------------------------
    def demo_action(self):
        """Mason: the first action of a bounded exact search that finishes the wall; a greedy pick when none is found.

        Search order per state: columns left to right for the next stone, then skip. Greedy: the placement on the
        lowest course that leaves no gap narrower than the smallest stone still coming (ties: leftmost), else skip
        when allowed, else the leftmost placement.
        """
        found = self.search()
        if found is not None:
            return found
        return self.greedy_pick()

    def gaps(self, row):
        """Lengths of the empty runs in a course row."""
        out, run = [], 0
        for x in row:
            if x == 0:
                run += 1
            elif run:
                out.append(run)
                run = 0
        if run:
            out.append(run)
        return out

    def greedy_pick(self):
        cols = self.placements()
        if not cols:
            return "skip" if self.skips_left > 0 else "0"
        coming = set(self.stones[self.index + 1:]) or {MIN_WIDTH}
        smallest = min(coming)
        best = None
        for col in cols:
            k = self.landing(col)
            row = self.wall[k][:]
            for c in range(col, col + self.next_stone()):
                row[c] = 1
            bad = sum(1 for gap in self.gaps(row) if gap < smallest)
            key = (bad, k, col)
            if best is None or key < best[0]:
                best = (key, col)
        if best[0][0] > 0 and self.skips_left > 0:
            return "skip"
        return str(best[1])

    def search(self):
        """First action of a line that locks every course within the supply and skips, or None (bounded)."""
        cfg = self.cfg
        w, h = cfg["width"], cfg["courses"]
        stones = self.stones
        memo = {}
        nodes = [0]

        def land(wall, col, size):
            if col + size > w:
                return None
            for k in range(h):
                if all(wall[k][c] == 0 for c in range(col, col + size)):
                    if k == 0 or all(wall[k - 1][c] == 1 for c in range(col, col + size)):
                        return k
                    return None
            return None

        def rec(wall, index, skips):
            key = (wall, index, skips)
            if key in memo:
                return memo[key]
            nodes[0] += 1
            if nodes[0] > SEARCH_NODES:
                return None
            if all(all(row) for row in wall):
                memo[key] = True
                return True
            empty = sum(1 for row in wall for x in row if x == 0)
            if index >= len(stones) or sum(stones[index:]) < empty:
                memo[key] = False
                return False
            size = stones[index]
            for col in range(w):
                k = land(wall, col, size)
                if k is None:
                    continue
                row = list(wall[k])
                for c in range(col, col + size):
                    row[c] = 1
                nxt = wall[:k] + (tuple(row),) + wall[k + 1:]
                sub = rec(nxt, index + 1, skips)
                if sub:
                    memo[key] = True
                    return True
                if nodes[0] > SEARCH_NODES:
                    return None
            if skips > 0:
                sub = rec(wall, index + 1, skips - 1)
                if sub:
                    memo[key] = True
                    return True
                if nodes[0] > SEARCH_NODES:
                    return None
            memo[key] = False
            return False

        wall = tuple(tuple(row) for row in self.wall)
        if self.index >= len(stones):
            return None
        size = stones[self.index]
        for col in range(w):
            k = land(wall, col, size)
            if k is None:
                continue
            row = list(wall[k])
            for c in range(col, col + size):
                row[c] = 1
            if rec(wall[:k] + (tuple(row),) + wall[k + 1:], self.index + 1, self.skips_left):
                return str(col)
            if nodes[0] > SEARCH_NODES:
                return None
        if self.skips_left > 0 and rec(wall, self.index + 1, self.skips_left - 1):
            return "skip"
        return None

    def tutorial(self):
        """First-turn teaching rows for the screen (iteration 7)."""
        return ["SET    a column sets the next stone on the lowest course that holds it fully (no overhang)",
                "LOCK   a course with no gaps locks (+%d); %d courses finish the wall" % (COURSE_SCORE, self.cfg["courses"]),
                "SKIP   skip sends a stone to the rubble (%d skips); the build fails when the supply runs out" % self.cfg["skips"]]

    def fresh(self):
        return self.index == 0 and not self.over

    def render(self):
        cfg = self.cfg
        lines = [f"{TITLE} [{self.difficulty}] locked {self.locked}/{cfg['courses']} supply {len(self.stones) - self.index} skips {self.skips_left} score {self.score}",
                 "next: " + (" ".join(str(s) for s in self.stones[self.index:self.index + 6]) or "-")]
        cols = set(self.placements()) if not self.over else set()
        for k in reversed(range(cfg["courses"])):
            lines.append(f"course {k}  |" + "".join("#" if x else "." for x in self.wall[k]) + "|" + ("  locked" if all(self.wall[k]) else ""))
        lines.append("           " + "".join("^" if c in cols else " " for c in range(cfg["width"])))
        if not self.over and cols:   # iteration 9: where the next stone lands and which columns lock a course
            locking = [c for c in sorted(cols) if self.preview(str(c))[2]]
            lines.append("next %d-stone rests at %s%s" % (self.next_stone(), ",".join(str(c) for c in sorted(cols)),
                                                          ("; locks from " + ",".join(str(c) for c in locking)) if locking else ""))
        if self.fresh():
            lines += self.tutorial()
        if self.over:
            lines.append("WON: the wall stands" if self.won else "LOST: " + ("the supply runs out" if self.index >= len(self.stones) else "the stone fits nowhere"))
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        text = line.strip().lower()
        if text in ("s", "skip"):
            return "skip"
        if text.isdigit():
            return text
        raise ValueError("use a column number or skip")


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
