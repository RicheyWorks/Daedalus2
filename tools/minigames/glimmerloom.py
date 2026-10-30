#!/usr/bin/env python3
"""Glimmerloom Ledger: trade hued Prism Shards at the Glimmerloom market and grow your purse.

Each market day every shard hue has a price that drifts on a seeded tide. Buy
and sell as you like (your satchel holds a limited count), then rest to open
the next day. Each morning a Warden whispers a rumor about one hue's next move;
rumors are usually true. On the last day everything is sold. Finish with a
purse at or above the target to win; score is the final purse. Stdlib only,
deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "glimmerloom"
TITLE = "Glimmerloom Ledger"
HOW_TO_PLAY = ("HOW Buy and sell hued shards as market prices drift, heed the Warden's rumor, "
               "then rest; end the last day with a purse at or above the target.")
DIFFICULTY = {
    "easy": {"hues": 3, "days": 12, "purse": 100, "target": 130, "satchel": 20, "truth": 0.85, "tax": 0},
    "normal": {"hues": 4, "days": 10, "purse": 100, "target": 135, "satchel": 15, "truth": 0.75, "tax": 0},
    "hard": {"hues": 5, "days": 8, "purse": 100, "target": 110, "satchel": 12, "truth": 0.7, "tax": 1},
}
DEFAULT_DIFFICULTY = "normal"
HUES = ("ember", "tide", "verdant", "gale", "umbra")
LOW, HIGH = 3, 20


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("day", "purse", "prices", "satchel", "rumor", "moves")

    def setup(self):
        n = self.cfg["hues"]
        self.day, self.purse = 1, self.cfg["purse"]
        self.prices = [self.rng.randint(6, 14) for _ in range(n)]
        self.satchel = [0] * n
        self._next_moves()

    def _next_moves(self):
        """Roll tomorrow's price moves now, then the rumor about one of them."""
        self.moves = [self.rng.choice((-3, -2, -1, 0, 1, 2, 3)) for _ in self.prices]
        hue = self.rng.randrange(len(self.prices))
        up = self.moves[hue] > 0
        if self.rng.random() >= self.cfg["truth"]:
            up = not up
        self.rumor = [hue, "rise" if up else "fall"]

    def held(self):
        return sum(self.satchel)

    def sale(self, i, q):
        return q * max(0, self.prices[i] - self.cfg["tax"])

    def act(self, action):
        kind, i, q = action
        if kind in ("buy", "sell"):
            if not 0 <= i < len(self.prices) or q < 1:
                raise ValueError("pick a hue index and a count of 1 or more")
            if kind == "buy":
                if q * self.prices[i] > self.purse or self.held() + q > self.cfg["satchel"]:
                    raise ValueError("not enough purse or satchel room")
                self.purse -= q * self.prices[i]
                self.satchel[i] += q
            else:
                if q > self.satchel[i]:
                    raise ValueError("you do not hold that many")
                self.purse += self.sale(i, q)
                self.satchel[i] -= q
            self.score = self.purse
            return f"purse {self.purse}"
        if kind != "rest":
            raise ValueError("use buy <hue> <n>, sell <hue> <n> or rest")
        self.prices = [min(HIGH, max(LOW, p + m)) for p, m in zip(self.prices, self.moves)]
        self.day += 1
        if self.day > self.cfg["days"]:
            for j, q in enumerate(self.satchel):
                self.purse += self.sale(j, q)
            self.satchel = [0] * len(self.prices)
            self.score = self.purse
            self.finish(self.purse >= self.cfg["target"])
            return f"market closes, purse {self.purse}"
        self._next_moves()
        self.score = self.purse
        return f"day {self.day}"

    def demo_action(self):
        for j, q in enumerate(self.satchel):
            if q and not (self.rumor == [j, "rise"]):
                return ("sell", j, q)
        hue, word = self.rumor
        if word == "rise" and self.day < self.cfg["days"]:
            q = min(self.purse // self.prices[hue], self.cfg["satchel"] - self.held())
            if q > 0:
                return ("buy", hue, q)
        return ("rest", 0, 0)

    def render(self):
        names = HUES[: len(self.prices)]
        lines = [f"{TITLE} [{self.difficulty}] day {self.day}/{self.cfg['days']} purse {self.purse}/{self.cfg['target']} "
                 f"satchel {self.held()}/{self.cfg['satchel']}" + (f" tax {self.cfg['tax']}" if self.cfg["tax"] else "")]
        lines += [f"  {i} {h}: price {p}, held {q}" for i, (h, p, q) in enumerate(zip(names, self.prices, self.satchel))]
        if not self.over:
            lines.append(f"rumor: {names[self.rumor[0]]} will {self.rumor[1]}")
        else:
            lines.append("WON: the ledger glows" if self.won else "LOST: the ledger runs dim")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        parts = line.split()
        if parts == ["rest"]:
            return ("rest", 0, 0)
        if parts[0] in ("buy", "sell") and len(parts) == 3:
            return (parts[0], int(parts[1]), int(parts[2]))
        raise ValueError("use buy <hue> <n>, sell <hue> <n> or rest")


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
