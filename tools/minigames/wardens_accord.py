#!/usr/bin/env python3
"""Wardens' Accord: draft Prism Shards from the Warden altar and spend them to summon spirits.

Each round the altar offers three seeded shards; take one into your pouch
(costs the round). Any time, spend shards matching a spirit's cost to summon it
for its value; a new spirit takes its place. Reach the target score before the
rounds run out. Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "wardens_accord"
TITLE = "Wardens' Accord"
HOW_TO_PLAY = ("HOW Take one of three altar shards each round, then spend matching shards "
               "to summon spirits; reach the target score before the rounds end.")
DIFFICULTY = {
    "easy": {"hues": 3, "rounds": 16, "target": 40, "spirits": 4},
    "normal": {"hues": 4, "rounds": 14, "target": 50, "spirits": 4},
    "hard": {"hues": 5, "rounds": 12, "target": 55, "spirits": 3},
}
DEFAULT_DIFFICULTY = "normal"
HUES = ("ember", "tide", "verdant", "gale", "umbra")
NAMES = ("Cinder Wisp", "Mere Sprite", "Thornkin", "Sky Lark Spirit", "Hollow Moth", "Glass Heron", "Lantern Newt")


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("rounds", "pouch", "offer", "spirits", "summoned")

    def setup(self):
        self.hues = list(HUES[: self.cfg["hues"]])
        self.rounds = self.cfg["rounds"]
        self.pouch = {h: 0 for h in self.hues}
        self.summoned = []
        self.spirits = [self._spirit() for _ in range(self.cfg["spirits"])]
        self.offer = self._offer()

    def restore(self):
        self.hues = list(HUES[: self.cfg["hues"]])

    def _offer(self):
        return [self.rng.choice(self.hues) for _ in range(3)]

    def _spirit(self):
        size = self.rng.randint(2, 4)
        cost = {}
        for h in self.rng.sample(self.hues, self.rng.randint(1, 2)):
            cost[h] = 0
        keys = sorted(cost)
        for i in range(size):
            cost[keys[i % len(keys)]] += 1
        value = size * 5 + (5 if len(keys) == 2 else 0)
        return {"name": self.rng.choice(NAMES), "cost": cost, "value": value}

    def check_rules(self):
        """Every summon is worth 10-25 in steps of 5, so the score must fit the summon count (Round 2 finding, prometheus 1).
        The save keeps names only, so this bounds the score rather than replaying it."""
        n = len(self.summoned) if isinstance(self.summoned, list) else -1
        if n < 0 or not all(isinstance(x, str) and x in NAMES for x in self.summoned):
            raise ValueError("wardens summoned list has unknown spirits")
        if self.score % 5 or not 10 * n <= self.score <= 25 * n:
            raise ValueError("wardens score does not fit the spirits summoned")
        if self.won != (self.score >= self.cfg["target"]) or (self.won and not self.over):
            raise ValueError("wardens result does not match the score")

    def affordable(self, i):
        return all(self.pouch[h] >= n for h, n in self.spirits[i]["cost"].items())

    def act(self, action):
        kind, i = action
        if kind == "take":
            if not 0 <= i < 3:
                raise ValueError("take 0, 1 or 2")
            self.pouch[self.offer[i]] += 1
            self.rounds -= 1
            self.offer = self._offer()
            gained = 0
        elif kind == "summon":
            if not 0 <= i < len(self.spirits) or not self.affordable(i):
                raise ValueError(f"cannot summon spirit {i}")
            sp = self.spirits[i]
            for h, n in sp["cost"].items():
                self.pouch[h] -= n
            gained = sp["value"]
            self.score += gained
            self.summoned.append(sp["name"])
            self.spirits[i] = self._spirit()
        else:
            raise ValueError("use take <i> or summon <i>")
        if self.score >= self.cfg["target"]:
            self.finish(True)
        elif self.rounds <= 0 and not any(self.affordable(j) for j in range(len(self.spirits))):
            self.finish(False)
        return gained

    def demo_action(self):
        ok = [i for i in range(len(self.spirits)) if self.affordable(i)]
        if ok:
            return ("summon", max(ok, key=lambda i: (self.spirits[i]["value"], -i)))
        def missing(i, extra=None):
            return sum(max(0, n - self.pouch[h] - (1 if h == extra else 0)) for h, n in self.spirits[i]["cost"].items())
        best = min(range(3), key=lambda k: (min(missing(i, self.offer[k]) for i in range(len(self.spirits))), k))
        return ("take", best)

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] score {self.score}/{self.cfg['target']} rounds {self.rounds}",
                 "pouch  " + " ".join(f"{h}:{n}" for h, n in self.pouch.items()),
                 "altar  " + " ".join(f"{i}:{h}" for i, h in enumerate(self.offer))]
        for i, s in enumerate(self.spirits):
            cost = "+".join(f"{n} {h}" for h, n in s["cost"].items())
            lines.append(f"spirit {i}: {s['name']} ({cost}) = {s['value']}" + (" *" if self.affordable(i) else ""))
        if self.over:
            lines.append("WON: the Wardens answer" if self.won else "LOST: the altar goes dark")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        kind, i = line.split()
        if kind not in ("take", "summon"):
            raise ValueError("use take <i> or summon <i>")
        return (kind, int(i))


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
