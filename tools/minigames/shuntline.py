#!/usr/bin/env python3
"""Shuntline: sort a seeded train onto the outbound track with a few short sidings and a move budget.

Carriages tagged for destinations 1..K arrive on the inbound track in a seeded
order. Each turn you send the front carriage straight out, shunt it onto one of
the sidings (a stack with a limited length), or pull the top carriage of a
siding out. The outbound train must leave in non-decreasing destination order;
a carriage that would break the order is refused. Every carriage out within the
move budget wins; running out of moves, or no legal move, loses. Score 10 per
destination group plus 2 per move left. Every train is solvable (the setup
redraws until the exact search finds a line within budget). Stdlib only,
deterministic per seed: randrange only at setup, nothing random after.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "shuntline"
TITLE = "Shuntline"
HOW_TO_PLAY = ("HOW out sends the front carriage to the outbound track; s<n> shunts it onto siding n; p<n> pulls siding n's "
               "top carriage out. The outbound order may never go down. Clear the inbound track within the moves.")
DIFFICULTY = {
    "easy": {"cars": 7, "destinations": 3, "sidings": 2, "length": 3, "moves": 16},
    "normal": {"cars": 9, "destinations": 4, "sidings": 2, "length": 3, "moves": 20},
    "hard": {"cars": 11, "destinations": 5, "sidings": 3, "length": 3, "moves": 24},
}
DEFAULT_DIFFICULTY = "normal"
GROUP_SCORE, MOVE_BONUS = 10, 2
SEARCH_NODES = 20000   # yardmaster search budget per pick (same in the C++ core)
MAX_REDRAWS = 50


def candidate_actions(inbound, sidings, out_last, length):
    """Legal actions in the rules' order: out, shunt onto each siding, pull from each siding."""
    acts = []
    if inbound:
        front = inbound[0]
        if front >= out_last:
            acts.append("out")
        for i, s in enumerate(sidings):
            if len(s) < length:
                acts.append("s%d" % i)
    for i, s in enumerate(sidings):
        if s and s[-1] >= out_last:
            acts.append("p%d" % i)
    return acts


def apply(inbound, sidings, out_last, action):
    """The state after `action` (tuples in, tuples out)."""
    if action == "out":
        return inbound[1:], sidings, inbound[0]
    kind, idx = action[0], int(action[1:])
    if kind == "s":
        new = list(sidings)
        new[idx] = sidings[idx] + (inbound[0],)
        return inbound[1:], tuple(new), out_last
    new = list(sidings)
    car = sidings[idx][-1]
    new[idx] = sidings[idx][:-1]
    return inbound, tuple(new), car


def solve(inbound, sidings, out_last, moves, length, memo, nodes):
    """First winning action from the state within `moves`, or None; exact search with memo and a node budget."""
    key = (inbound, sidings, out_last, moves)
    if key in memo:
        return memo[key]
    nodes[0] += 1
    if nodes[0] > SEARCH_NODES:
        return None
    if not inbound and all(not s for s in sidings):
        memo[key] = "done"
        return "done"
    remaining = len(inbound) + sum(len(s) for s in sidings)
    if moves <= 0 or remaining > moves:   # every carriage still needs at least one move to leave
        memo[key] = None
        return None
    if any(v < out_last for v in inbound) or any(v < out_last for s in sidings for v in s):   # a carriage that can never leave
        memo[key] = None
        return None
    for s in sidings:   # a siding is pulled top first, so a lower tag under a higher one can never leave
        for below, above in zip(s, s[1:]):
            if below < above:
                memo[key] = None
                return None

    result = None
    for action in candidate_actions(inbound, sidings, out_last, length):
        nxt = apply(inbound, sidings, out_last, action)
        sub = solve(nxt[0], nxt[1], nxt[2], moves - 1, length, memo, nodes)
        if nodes[0] > SEARCH_NODES:
            return None
        if sub is not None:
            result = action
            break
    memo[key] = result
    return result


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("train", "index", "sidings", "outbound", "moves")

    def setup(self):
        """Draw trains until the exact search sorts one within the budget, so every train is solvable."""
        cfg = self.cfg
        for _ in range(MAX_REDRAWS):
            self.train = [1 + self.rng.randrange(cfg["destinations"]) for _ in range(cfg["cars"])]
            self.index, self.sidings, self.outbound, self.moves = 0, [[] for _ in range(cfg["sidings"])], [], cfg["moves"]
            if self._search() is not None:
                break

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5)."""
        g = super().from_state(state)
        cfg = g.cfg
        tag = lambda v: isinstance(v, int) and 1 <= v <= cfg["destinations"]  # noqa: E731
        ok = (isinstance(g.train, list) and len(g.train) == cfg["cars"] and all(tag(v) for v in g.train)
              and isinstance(g.index, int) and 0 <= g.index <= cfg["cars"]
              and isinstance(g.sidings, list) and len(g.sidings) == cfg["sidings"]
              and all(isinstance(s, list) and len(s) <= cfg["length"] and all(tag(v) for v in s) for s in g.sidings)
              and isinstance(g.outbound, list) and all(tag(v) for v in g.outbound)
              and all(a <= b for a, b in zip(g.outbound, g.outbound[1:]))
              and sorted(g.outbound + [v for s in g.sidings for v in s]) == sorted(g.train[:g.index])
              and isinstance(g.moves, int) and 0 <= g.moves <= cfg["moves"]
              and g.index <= cfg["moves"] - g.moves <= g.index + len(g.outbound)
              and g.won == (len(g.outbound) == cfg["cars"])
              and g.over == (g.won or g.moves <= 0 or not g.actions()))
        if not ok:
            raise ValueError("shuntline save does not satisfy the rules")
        return g

    def inbound(self):
        return tuple(self.train[self.index:])

    def out_last(self):
        return self.outbound[-1] if self.outbound else 0

    def remaining(self):
        return len(self.train) - self.index + sum(len(s) for s in self.sidings)

    def actions(self):
        return candidate_actions(self.inbound(), tuple(tuple(s) for s in self.sidings), self.out_last(), self.cfg["length"])

    def act(self, action):
        if action not in self.actions():
            raise ValueError("use out, s<n> or p<n> (a legal one)")
        self.moves -= 1
        if action == "out":
            car = self.train[self.index]
            self.index += 1
            self.outbound.append(car)
            text = f"out: carriage {car} leaves"
        elif action[0] == "s":
            car = self.train[self.index]
            self.index += 1
            self.sidings[int(action[1:])].append(car)
            text = f"{action}: carriage {car} onto siding {action[1:]}"
        else:
            car = self.sidings[int(action[1:])].pop()
            self.outbound.append(car)
            text = f"{action}: carriage {car} pulled out"
        if self.remaining() == 0:
            self.score = GROUP_SCORE * len(set(self.outbound)) + MOVE_BONUS * self.moves
            self.finish(True)
            return text + "; the train is made up"
        if self.moves <= 0:
            self.score = GROUP_SCORE * len(set(self.outbound))
            self.finish(False)
            return text + "; the shift ends"
        if not self.actions():
            self.score = GROUP_SCORE * len(set(self.outbound))
            self.finish(False)
            return text + "; the yard is blocked"
        return text

    def preview(self, action):
        """(legal, carriage moved, leaves the yard) for `action` without taking it (iteration 8)."""
        if action not in self.actions():
            return (False, 0, False)
        if action == "out":
            return (True, self.train[self.index], True)
        if action[0] == "s":
            return (True, self.train[self.index], False)
        return (True, self.sidings[int(action[1:])][-1], True)

    def _search(self):
        return solve(self.inbound(), tuple(tuple(s) for s in self.sidings), self.out_last(), self.moves, self.cfg["length"], {}, [0])

    def demo_action(self):
        """Yardmaster: the first action of an exact line that makes up the train within the moves; else the first legal action.

        The search tries actions in the rules' order (out, shunt onto each siding, pull from each siding), prunes
        states with more carriages left than moves, memoises and stops after SEARCH_NODES nodes.
        """
        found = self._search()
        if found is not None and found != "done":
            return found
        acts = self.actions()
        return acts[0] if acts else "out"

    def tutorial(self):
        """First-turn teaching rows for the screen (iteration 7)."""
        return ["OUT    out sends the front carriage to the outbound track; its tag may never be lower than the last",
                "SIDE   s<n> parks the front carriage on siding n (%d long); p<n> pulls that siding's top carriage out" % self.cfg["length"],
                "SHIFT  clear the inbound track and the sidings within %d moves" % self.cfg["moves"]]

    def fresh(self):
        return self.index == 0 and not self.over

    def render(self):
        cfg = self.cfg
        lines = [f"{TITLE} [{self.difficulty}] moves {self.moves} out {len(self.outbound)}/{cfg['cars']} score {self.score}",
                 "inbound:  " + (" ".join(str(v) for v in self.inbound()) or "-") + "   (front first)"]
        for i, s in enumerate(self.sidings):
            lines.append(f"siding {i}: " + (" ".join(str(v) for v in s) or "-") + ("   (top last)" if s else ""))
        lines.append("outbound: " + (" ".join(str(v) for v in self.outbound) or "-"))
        if not self.over:
            lines.append("legal: " + " ".join(self.actions()))
        if self.fresh():
            lines += self.tutorial()
        if self.over:
            lines.append("WON: the train is made up" if self.won else "LOST: " + ("the shift ends" if self.moves <= 0 else "the yard is blocked"))
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        text = line.strip().lower()
        if text in ("o", "out"):
            return "out"
        if len(text) >= 2 and text[0] in "sp" and text[1:].isdigit():
            return text
        raise ValueError("use out, s<n> or p<n>")


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
