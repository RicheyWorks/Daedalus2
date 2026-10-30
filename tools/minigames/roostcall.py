#!/usr/bin/env python3
"""Roostcall: whistle the glimmer-birds home. Walk the grid so every bird flees into the roost before dusk.

A seeded S x S yard. The whistler starts in the north-west corner; the roost
is the 2 x 2 south-east corner. Each turn the whistler moves one cell
(n/e/s/w) or waits. Then every bird within two cells (Chebyshev) of the
whistler takes the open neighbouring cell farthest from the whistler
(Chebyshev, then Manhattan, then n/e/s/w order), and only if it is strictly
farther than where it stands. So standing beside a cornered bird sends it
along the edge. A bird that steps into the roost perches: it
leaves the yard and counts as settled. Every bird settled wins; running out
of turns loses.
Score 10 per settled bird plus the turns left on a win. Stdlib only,
deterministic per seed: randrange only at setup, nothing random after.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "roostcall"
TITLE = "Roostcall"
HOW_TO_PLAY = ("HOW Walk up behind the glimmer-birds so they flee one step at a time; drive every bird into the "
               "roost corner before your turns run out.")
DIFFICULTY = {
    "easy": {"size": 6, "birds": 3, "turns": 16},
    "normal": {"size": 7, "birds": 4, "turns": 30},
    "hard": {"size": 8, "birds": 5, "turns": 48},
}
DEFAULT_DIFFICULTY = "normal"
MOVES = {"n": (-1, 0), "e": (0, 1), "s": (1, 0), "w": (0, -1), "wait": (0, 0)}
ORDER = ("n", "e", "s", "w")
SCARE_RANGE, ROOST = 2, 2
BIRD_SCORE = 10


def sign(v):
    return (v > 0) - (v < 0)


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("whistler", "birds", "turns", "settled")

    def setup(self):
        s = self.cfg["size"]
        self.whistler = [0, 0]
        self.birds = []
        while len(self.birds) < self.cfg["birds"]:
            r, c = self.rng.randrange(s), self.rng.randrange(s)
            if [r, c] == self.whistler or self.in_roost(r, c) or [r, c] in self.birds:
                continue
            if max(abs(r - 0), abs(c - 0)) <= SCARE_RANGE:
                continue   # birds start out of the whistler's reach
            self.birds.append([r, c])
        self.turns, self.settled = self.cfg["turns"], 0

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5)."""
        g = super().from_state(state)
        s = g.cfg["size"]
        in_yard = lambda cell: isinstance(cell, list) and len(cell) == 2 and all(isinstance(v, int) and 0 <= v < s for v in cell)  # noqa: E731
        ok = (in_yard(g.whistler) and all(in_yard(b) for b in g.birds)
              and len({tuple(b) for b in g.birds}) == len(g.birds)
              and g.whistler not in g.birds
              and all(not g.in_roost(*b) for b in g.birds)
              and isinstance(g.turns, int) and 0 <= g.turns <= g.cfg["turns"]
              and isinstance(g.settled, int) and g.settled + len(g.birds) == g.cfg["birds"]
              and g.over == (not g.birds or g.turns <= 0) and g.won == (not g.birds))
        if not ok:
            raise ValueError("roostcall save does not satisfy the rules")
        return g

    def size(self):
        return self.cfg["size"]

    def in_roost(self, r, c):
        s = self.size()
        return r >= s - ROOST and c >= s - ROOST

    def occupied(self, r, c):
        return [r, c] == self.whistler or [r, c] in self.birds

    def flee_step(self, i, whistler=None):
        """Where bird i steps with the whistler at `whistler` (default: where it stands), or None if it stays.

        Scared birds (within SCARE_RANGE) take the open neighbour farthest from the whistler: Chebyshev distance
        first, Manhattan second, n/e/s/w order third, and only if that is strictly farther than where they stand.
        """
        br, bc = self.birds[i]
        pr, pc_ = whistler or self.whistler
        if max(abs(br - pr), abs(bc - pc_)) > SCARE_RANGE:
            return None
        s = self.size()
        best, best_key = None, (max(abs(br - pr), abs(bc - pc_)), abs(br - pr) + abs(bc - pc_))
        for name in ORDER:
            dr, dc = MOVES[name]
            r, c = br + dr, bc + dc
            if not (0 <= r < s and 0 <= c < s) or [r, c] in self.birds or [r, c] == list((pr, pc_)):
                continue
            key = (max(abs(r - pr), abs(c - pc_)), abs(r - pr) + abs(c - pc_))
            if key > best_key:   # strictly farther; the first direction in n/e/s/w order wins a tie
                best, best_key = [r, c], key
        return best

    def act(self, action):
        if action not in MOVES:
            raise ValueError("use n, e, s, w or wait")
        dr, dc = MOVES[action]
        r, c = self.whistler[0] + dr, self.whistler[1] + dc
        s = self.size()
        if not (0 <= r < s and 0 <= c < s):
            raise ValueError("off the yard")
        if [r, c] in self.birds:
            raise ValueError("a bird is there")
        self.whistler = [r, c]
        moved, perched = 0, 0
        for i in range(len(self.birds)):
            to = self.flee_step(i)
            if to is not None:
                self.birds[i] = to
                moved += 1
        remaining = []
        for b in self.birds:
            if self.in_roost(*b):
                perched += 1
            else:
                remaining.append(b)
        self.birds = remaining
        self.settled += perched
        self.turns -= 1
        if not self.birds:
            self.score = BIRD_SCORE * self.settled + self.turns
            self.finish(True)
            return f"{action}: {moved} flew, every bird is home"
        if self.turns <= 0:
            self.score = BIRD_SCORE * self.settled
            self.finish(False)
            return f"{action}: {moved} flew, dusk falls with {self.settled} home"
        return f"{action}: {moved} flew, {perched} perched, {self.settled} home"

    def _path_first_step(self, goal):
        """First move of the shortest walk (n/e/s/w order) to `goal` avoiding birds; None if unreachable."""
        s = self.size()
        start = tuple(self.whistler)
        if start == goal:
            return "wait"
        prev = {start: None}
        frontier = [start]
        blocked = {tuple(b) for b in self.birds}
        while frontier:
            nxt = []
            for cell in frontier:
                for name in ORDER:
                    dr, dc = MOVES[name]
                    r, c = cell[0] + dr, cell[1] + dc
                    if not (0 <= r < s and 0 <= c < s) or (r, c) in prev or (r, c) in blocked:
                        continue
                    prev[(r, c)] = (cell, name)
                    if (r, c) == goal:
                        cur = (r, c)
                        while prev[cur][0] != start:
                            cur = prev[cur][0]
                        return prev[cur][1]
                    nxt.append((r, c))
            frontier = nxt
        return None

    def roost_distance(self, r, c):
        """Manhattan distance from (r, c) to the nearest roost cell."""
        s = self.size()
        return max(0, (s - ROOST) - r) + max(0, (s - ROOST) - c)

    def preview(self, action):
        """Which birds would fly and where if the whistler made `action` now (iteration 8); None if illegal."""
        dr, dc = MOVES.get(action, (None, None))
        if dr is None:
            return None
        s = self.size()
        w = [self.whistler[0] + dr, self.whistler[1] + dc]
        if not (0 <= w[0] < s and 0 <= w[1] < s) or w in self.birds:
            return None
        flights = {}
        birds = [list(b) for b in self.birds]
        original = self.birds
        try:
            self.birds = birds
            for i in range(len(birds)):
                to = self.flee_step(i, w)
                if to is not None:
                    flights[i] = to
                    birds[i] = to
        finally:
            self.birds = original
        return flights

    def tutorial(self):
        """First-turn teaching rows for the screen (iteration 7)."""
        return ["WALK   n/e/s/w move the whistler one cell a turn; wait stands still",
                "SCARE  birds within %d cells fly one step to the open cell farthest from you" % SCARE_RANGE,
                "ROOST  a bird that lands in the # corner perches; settle all %d before dusk" % self.cfg["birds"]]

    def fresh(self):
        return self.turns == self.cfg["turns"] and not self.over

    def _walk_distances(self):
        """Breadth-first walking distance from the whistler to every cell, avoiding birds (None = unreachable)."""
        s = self.size()
        dist = {tuple(self.whistler): 0}
        frontier = [tuple(self.whistler)]
        blocked = {tuple(b) for b in self.birds}
        while frontier:
            nxt = []
            for cell in frontier:
                for name in ORDER:
                    dr, dc = MOVES[name]
                    r, c = cell[0] + dr, cell[1] + dc
                    if 0 <= r < s and 0 <= c < s and (r, c) not in dist and (r, c) not in blocked:
                        dist[(r, c)] = dist[cell] + 1
                        nxt.append((r, c))
            frontier = nxt
        return dist

    def demo_action(self):
        """Herd the bird nearest the roost: stand where its flight brings it nearer still, then let it fly.

        Birds are taken nearest-to-roost first (index breaks ties) so a clump is unpicked from the roost side.
        Spots are every reachable cell within scare range of the bird, ranked by the bird's roost distance after the
        flight it would cause, then walking distance, then row, then column. Flights that bring the bird nearer are
        tried first, then flights along an edge toward the roost side (east or south); otherwise the whistler waits.
        """
        s = self.size()
        dist = self._walk_distances()
        order = sorted(range(len(self.birds)), key=lambda i: (self.roost_distance(*self.birds[i]), i))
        # pass 1: a flight that brings the bird nearer; pass 2: a flight along an edge toward the roost side
        for allow_slide in (False, True):
            for i in order:
                br, bc = self.birds[i]
                now = self.roost_distance(br, bc)
                best = None
                for r in range(max(0, br - SCARE_RANGE), min(s, br + SCARE_RANGE + 1)):
                    for c in range(max(0, bc - SCARE_RANGE), min(s, bc + SCARE_RANGE + 1)):
                        if (r, c) not in dist:
                            continue
                        to = self.flee_step(i, [r, c])
                        if to is None:
                            continue
                        after = self.roost_distance(*to)
                        nearer = after < now
                        slide = after == now and (to[0] > br or to[1] > bc)
                        if not (nearer or (allow_slide and slide)):
                            continue
                        key = (after, dist[(r, c)], r, c)
                        if best is None or key < best[0]:
                            best = (key, (r, c))
                if best is None:
                    continue
                spot = best[1]
                if tuple(self.whistler) == spot:
                    return "wait"
                return self._path_first_step(spot)
        return "wait"

    def render(self):
        s = self.size()
        # birds that would fly if the whistler simply waited are drawn lower-case (iteration 9)
        skittish = [] if self.over else [self.birds[i] for i in self.preview("wait")]
        rows = []
        for r in range(s):
            row = ""
            for c in range(s):
                if [r, c] == self.whistler:
                    row += "W"
                elif [r, c] in self.birds:
                    row += "b" if [r, c] in skittish else "B"
                elif self.in_roost(r, c):
                    row += "#"
                else:
                    row += "."
            rows.append(row)
        lines = [f"{TITLE} [{self.difficulty}] turns {self.turns} home {self.settled}/{self.cfg['birds']} score {self.score}"] + rows
        if self.fresh():
            lines += self.tutorial()
        if self.over:
            lines.append("WON: every bird is home" if self.won else "LOST: dusk falls")
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
