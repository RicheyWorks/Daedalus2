#!/usr/bin/env python3
"""Prismvault Weigh: find the one hollow Prism Shard with a Warden's balance and few weighings.

One shard in the vault is hollow (lighter). Each weighing puts two equal,
disjoint groups on the balance and tells you which side is lighter (or that it
balances). When you are sure, name the hollow shard. A correct name scores
100 + 50 per unused weighing; a wrong name loses. Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "prismvault"
TITLE = "Prismvault Weigh"
HOW_TO_PLAY = ("HOW Weigh equal groups of shards on the balance to find the hollow one, "
               "then name it before the weighings run out.")
DIFFICULTY = {
    "easy": {"shards": 8, "weighings": 3},
    "normal": {"shards": 12, "weighings": 3},
    "hard": {"shards": 27, "weighings": 3},
}
DEFAULT_DIFFICULTY = "normal"


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("weighings", "log", "candidates")

    def setup(self):
        self.hollow = self.rng.randrange(self.cfg["shards"])
        self.weighings = self.cfg["weighings"]
        self.log = []
        self.candidates = list(range(self.cfg["shards"]))

    def to_state(self):
        st = super().to_state()
        st["hollow"] = self.hollow
        return st

    @classmethod
    def from_state(cls, state):
        g = super().from_state(state)
        g.hollow = state["hollow"]
        return g

    def act(self, action):
        kind = action[0]
        n = self.cfg["shards"]
        if kind == "weigh":
            left, right = sorted(set(action[1])), sorted(set(action[2]))
            if self.weighings <= 0:
                raise ValueError("no weighings left; name a shard")
            if not left or len(left) != len(right) or set(left) & set(right) or not all(0 <= x < n for x in left + right):
                raise ValueError("weigh two equal, disjoint groups")
            res = "<" if self.hollow in left else ">" if self.hollow in right else "="
            self.weighings -= 1
            self.log.append([left, right, res])
            keep = set(left if res == "<" else right if res == ">" else set(range(n)) - set(left) - set(right))
            self.candidates = [c for c in self.candidates if c in keep]
            return res
        if kind == "name":
            if not 0 <= action[1] < n:
                raise ValueError("no such shard")
            if action[1] == self.hollow:
                gained = 100 + 50 * self.weighings
                self.score += gained
                self.finish(True)
                return gained
            self.finish(False)
            return 0
        raise ValueError("use weigh <a,b> <c,d> or name <i>")

    def demo_action(self):
        c = self.candidates
        if len(c) == 1 or self.weighings == 0:
            return ("name", c[0])
        k = (len(c) + 2) // 3
        left, right = c[:k], c[k:2 * k]
        if len(right) < k:
            pad = [x for x in range(self.cfg["shards"]) if x not in c][: k - len(right)]
            right = right + pad
        return ("weigh", left, right)

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] score {self.score} shards 0-{self.cfg['shards'] - 1} weighings left {self.weighings}"]
        for l, r, res in self.log:
            lines.append(f"  {l} {res} {r}")
        if self.over:
            lines.append(("WON: shard %d was hollow" if self.won else "LOST: shard %d was the hollow one") % self.hollow)
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        parts = line.split()
        if parts[0] == "name":
            return ("name", int(parts[1]))
        if parts[0] == "weigh" and len(parts) == 3:
            return ("weigh", [int(x) for x in parts[1].split(",")], [int(x) for x in parts[2].split(",")])
        raise ValueError("use weigh <a,b> <c,d> or name <i>")


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
