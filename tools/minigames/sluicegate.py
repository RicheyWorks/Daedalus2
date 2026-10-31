#!/usr/bin/env python3
"""Sluicegate: steer the flood through the channel field into every cistern and away from the mill wheel.

A seeded S x S field of channels and rock. Water enters at the headgate on the
north edge; each turn the headgate pushes FLOW more cells of water into the
nearest dry open channels (wet cells in the order they were wetted, neighbours
north, east, south, west), and the headgate closes after `turns` turns. Before
each push you may drop one gate on a dry channel cell (a limited stock) or
wait: gates block a branch so the water goes somewhere else. Water reaching a
cistern fills it; water reaching the mill wheel floods the mill and loses. Fill
every cistern to win; when the headgate closes, or the flow has nowhere to go,
with a cistern still dry the channel has run dry and you lose. Score 10 per
cistern plus 3 per gate left and 1 per turn left on a win. Stdlib only, deterministic per seed: randrange only at
setup, nothing random after.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "sluicegate"
TITLE = "Sluicegate"
HOW_TO_PLAY = ("HOW Each turn the headgate pushes a few cells of water into the nearest open channels. Drop a gate (r,c) "
               "on a dry channel to block a branch, or wait. Fill every cistern before the headgate closes; keep the "
               "water off the mill wheel.")
DIFFICULTY = {
    "easy": {"size": 7, "cisterns": 3, "gates": 4, "flow": 2, "turns": 9, "channel_pct": 70},
    "normal": {"size": 8, "cisterns": 4, "gates": 5, "flow": 2, "turns": 12, "channel_pct": 68},
    "hard": {"size": 9, "cisterns": 5, "gates": 6, "flow": 2, "turns": 15, "channel_pct": 66},
}
DEFAULT_DIFFICULTY = "normal"
ROCK, CHANNEL = 0, 1
CISTERN_SCORE, GATE_BONUS, TURN_BONUS = 10, 3, 1
NEIGHBOURS = ((-1, 0), (0, 1), (1, 0), (0, -1))
MIN_CISTERN_DISTANCE, MIN_MILL_DISTANCE = 2, 3
CISTERN_SLACK = 3   # cisterns sit at least this many turns (or a third of the budget) inside the headgate's budget


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("field", "head", "cisterns", "mill", "wet", "gates", "gates_left", "filled", "turns")

    def setup(self):
        s = self.cfg["size"]
        pct = self.cfg["channel_pct"]
        self.field = [[CHANNEL if self.rng.randrange(100) < pct else ROCK for _ in range(s)] for _ in range(s)]
        self.head = [0, s // 2]
        self.field[0][s // 2] = CHANNEL
        self.wet = [list(self.head)]
        self.gates, self.gates_left, self.turns = [], self.cfg["gates"], self.cfg["turns"]
        self.cisterns, self.filled, self.mill = [], 0, None
        dist = self._distances(set())
        while len(dist) < self.min_reach():   # a cramped field gets a wandering channel carved from the headgate
            r, c = self.head
            for _ in range(2 * s):
                dr, dc = NEIGHBOURS[self.rng.randrange(4)]
                if self.inside(r + dr, c + dc):
                    r, c = r + dr, c + dc
                    self.field[r][c] = CHANNEL
            dist = self._distances(set())
        far = sorted(cell for cell, d in dist.items() if MIN_CISTERN_DISTANCE <= d <= self.cfg["turns"] - self.cistern_slack())
        while len(self.cisterns) < min(self.cfg["cisterns"], len(far)):
            cell = list(far[self.rng.randrange(len(far))])
            if cell not in self.cisterns:
                self.cisterns.append(cell)
        self.mill = self._place_mill(dist)

    def _place_mill(self, dist):
        """The mill wheel sits in a dead end: a channel cell with exactly one channel neighbour, three or more steps from
        the headgate, whose neighbour is neither cistern nor headgate and can be gated without cutting any cistern
        off. If the field offers none, one is carved out of the rock beside such a neighbour. So every field can be
        won: one gate on the mill's throat keeps the wheel dry, the rest of the stock routes the water.
        """
        s = self.size()
        cisterns = {tuple(c) for c in self.cisterns}
        head = tuple(self.head)

        def throat_ok(throat):
            if throat in cisterns or throat == head:
                return False
            reach = self._distances({throat})
            return all(c in reach for c in cisterns)

        candidates = []
        for (r, c), d in sorted(dist.items()):
            if d < MIN_MILL_DISTANCE or (r, c) in cisterns:
                continue
            around = [(r + dr, c + dc) for dr, dc in NEIGHBOURS if self.inside(r + dr, c + dc) and self.field[r + dr][c + dc] == CHANNEL]
            if len(around) == 1 and throat_ok(around[0]):
                candidates.append((r, c))
        if not candidates:   # carve: a rock cell touching exactly one channel cell that works as a throat
            for r in range(s):
                for c in range(s):
                    if self.field[r][c] != ROCK:
                        continue
                    around = [(r + dr, c + dc) for dr, dc in NEIGHBOURS if self.inside(r + dr, c + dc) and self.field[r + dr][c + dc] == CHANNEL]
                    if len(around) == 1 and around[0] in dist and dist[around[0]] >= MIN_MILL_DISTANCE - 1 and throat_ok(around[0]):
                        candidates.append((r, c))
        if not candidates:   # last resort: a rock cell with two channel neighbours, both gateable without cutting a cistern off
            for r in range(s):
                for c in range(s):
                    if self.field[r][c] != ROCK:
                        continue
                    around = [(r + dr, c + dc) for dr, dc in NEIGHBOURS if self.inside(r + dr, c + dc) and self.field[r + dr][c + dc] == CHANNEL]
                    if len(around) == 2 and all(a in dist for a in around) and all(throat_ok(a) for a in around):
                        candidates.append((r, c))
        if not candidates:   # a field with no dry corner for a wheel: pure routing, nothing to flood
            return None
        mill = candidates[self.rng.randrange(len(candidates))]
        self.field[mill[0]][mill[1]] = CHANNEL
        return list(mill)

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5)."""
        g = super().from_state(state)
        s = g.cfg["size"]
        cell = lambda v: isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) and 0 <= x < s for x in v)  # noqa: E731
        channel = lambda v: cell(v) and g.field[v[0]][v[1]] == CHANNEL  # noqa: E731
        ok = (isinstance(g.field, list) and len(g.field) == s and all(isinstance(row, list) and len(row) == s and all(x in (ROCK, CHANNEL) for x in row) for row in g.field)
              and channel(g.head) and g.head[0] == 0
              and all(channel(c) for c in g.cisterns) and len({tuple(c) for c in g.cisterns}) == len(g.cisterns)
              and (g.mill is None or (channel(g.mill) and g.mill not in g.cisterns))
              and g.wet and g.wet[0] == g.head and all(channel(w) for w in g.wet) and len({tuple(w) for w in g.wet}) == len(g.wet)
              and all(channel(x) and x not in g.wet and x not in g.cisterns and x != g.mill and x != g.head for x in g.gates)
              and len({tuple(x) for x in g.gates}) == len(g.gates)
              and isinstance(g.gates_left, int) and g.gates_left + len(g.gates) == g.cfg["gates"]
              and isinstance(g.turns, int) and 0 <= g.turns <= g.cfg["turns"] and g.cfg["turns"] - g.turns >= len(g.gates)
              and g.filled == sum(1 for c in g.cisterns if c in g.wet))
        if ok:
            mill_wet = g.mill is not None and g.mill in g.wet
            done = g.filled == len(g.cisterns)
            ok = g.won == (done and not mill_wet) and (g.over or not (mill_wet or done or g.turns <= 0))
        if not ok:
            raise ValueError("sluicegate save does not satisfy the rules")
        return g

    def size(self):
        return self.cfg["size"]

    def cistern_slack(self):
        return max(CISTERN_SLACK, self.cfg["turns"] // 3)

    def min_reach(self):
        """Channel cells the headgate must reach before cisterns and mill are placed: a third of the field."""
        return self.size() * self.size() // 3

    def inside(self, r, c):
        s = self.size()
        return 0 <= r < s and 0 <= c < s

    def _distances(self, gated):
        """Breadth-first distance from the wet cells through open channels; gated cells block. Wet cells are 0."""
        frontier = [tuple(w) for w in self.wet]
        dist = {cell: 0 for cell in frontier}
        while frontier:
            nxt = []
            for r, c in frontier:
                for dr, dc in NEIGHBOURS:
                    rr, cc = r + dr, c + dc
                    if (self.inside(rr, cc) and (rr, cc) not in dist and self.field[rr][cc] == CHANNEL
                            and (rr, cc) not in gated):
                        dist[(rr, cc)] = dist[(r, c)] + 1
                        nxt.append((rr, cc))
            frontier = nxt
        return dist

    def gateable(self, r, c):
        """A dry channel cell that is not the headgate, a cistern, the mill or already gated."""
        return (self.inside(r, c) and self.field[r][c] == CHANNEL and [r, c] not in self.wet
                and [r, c] not in self.gates and [r, c] not in self.cisterns and [r, c] != self.mill
                and [r, c] != self.head)

    def parse_cell(self, action):
        parts = action.split(",")
        if len(parts) != 2:
            raise ValueError("use row,col or wait")
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError("use row,col or wait") from None

    def act(self, action):
        if action != "wait":
            r, c = self.parse_cell(action)
            if self.gates_left <= 0:
                raise ValueError("no gates left")
            if not self.gateable(r, c):
                raise ValueError("gates go on dry open channel")
            self.gates.append([r, c])
            self.gates_left -= 1
        reached = self.push(self.gates)
        self.wet.extend(reached)
        self.turns -= 1
        newly = sum(1 for cell in reached if cell in self.cisterns)
        self.filled += newly
        self.score += CISTERN_SCORE * newly
        head = f"{action}: {len(reached)} cells wet, {newly} filled"
        if self.mill is not None and self.mill in reached:
            self.finish(False)
            return head + "; the mill wheel floods"
        if self.filled == len(self.cisterns):
            self.score += GATE_BONUS * self.gates_left + TURN_BONUS * self.turns
            self.finish(True)
            return head + "; every cistern brims"
        if not reached or self.turns <= 0:
            self.finish(False)
            return head + ("; the channel runs dry" if not reached else "; the headgate closes")
        return head

    def push(self, gates):
        """The cells one turn's flow would wet with `gates` in place: at most FLOW, nearest first, wet-list order."""
        gated = {tuple(g) for g in gates}
        wet = {tuple(w) for w in self.wet}
        reached = []
        frontier = list(self.wet)
        flow = self.cfg["flow"]
        while frontier and len(reached) < flow:
            nxt = []
            for r, c in frontier:
                for dr, dc in NEIGHBOURS:
                    rr, cc = r + dr, c + dc
                    if (self.inside(rr, cc) and (rr, cc) not in wet and self.field[rr][cc] == CHANNEL
                            and (rr, cc) not in gated):
                        wet.add((rr, cc))
                        reached.append([rr, cc])
                        nxt.append([rr, cc])
                        if len(reached) == flow:
                            return reached
            frontier = nxt
        return reached

    def dry_cisterns(self):
        return [c for c in self.cisterns if c not in self.wet]

    def preview(self, action):
        """(legal, cells that would get wet, cisterns filled, mill flooded) for `action` now (iteration 8)."""
        gates = self.gates
        if action != "wait":
            try:
                r, c = self.parse_cell(action)
            except ValueError:
                return (False, [], 0, False)
            if self.gates_left <= 0 or not self.gateable(r, c):
                return (False, [], 0, False)
            gates = self.gates + [[r, c]]
        reached = self.push(gates)
        return (True, reached, sum(1 for x in reached if x in self.cisterns), self.mill is not None and self.mill in reached)

    def rollout(self, extra_gate=None):
        """Play the rest of the flow with no more gates after `extra_gate`: (won, mill flooded, filled, turns used)."""
        gates = self.gates + ([extra_gate] if extra_gate is not None else [])
        saved = (self.wet, self.turns)
        wet = list(self.wet)
        filled, turns, flooded, won = self.filled, self.turns, False, False
        try:
            self.wet = wet
            while turns > 0:
                reached = self.push(gates)
                wet.extend(reached)
                turns -= 1
                filled += sum(1 for cell in reached if cell in self.cisterns)
                if self.mill is not None and self.mill in reached:
                    flooded = True
                    break
                if filled == len(self.cisterns):
                    won = True
                    break
                if not reached:
                    break
        finally:
            self.wet, self.turns = saved
        return won, flooded, filled, self.turns - turns

    def demo_action(self):
        """Gatekeeper: try every gate (and waiting) with a no-more-gates rollout; keep the one that ends best.

        Key: won first, then mill not flooded, then more cisterns filled, then fewer turns used; ties by row, column
        with waiting as the baseline, so gates are only spent when one improves the ending.
        """
        best_key, best = self._key(self.rollout()), "wait"
        s = self.size()
        if self.gates_left > 0:
            for r in range(s):
                for c in range(s):
                    if not self.gateable(r, c):
                        continue
                    key = self._key(self.rollout([r, c]))
                    if key < best_key:
                        best_key, best = key, f"{r},{c}"
        return best

    @staticmethod
    def _key(result):
        won, flooded, filled, used = result
        return (0 if won else 1, 1 if flooded else 0, -filled, used)

    def render(self):
        s = self.size()
        rows = []
        for r in range(s):
            row = ""
            for c in range(s):
                cell = [r, c]
                if cell == self.mill:
                    row += "M"
                elif cell in self.cisterns:
                    row += "C" if cell in self.wet else "c"
                elif cell in self.gates:
                    row += "|"
                elif cell == self.head:
                    row += "H"
                elif cell in self.wet:
                    row += "~"
                elif self.field[r][c] == CHANNEL:
                    row += "."
                else:
                    row += "#"
            rows.append(row)
        lines = [f"{TITLE} [{self.difficulty}] turns {self.turns} gates {self.gates_left} filled {self.filled}/{len(self.cisterns)} score {self.score}"] + rows
        if self.over:
            lines.append("WON: every cistern brims" if self.won else "LOST: " + ("the mill wheel floods" if self.mill is not None and self.mill in self.wet else "the water never came"))
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
