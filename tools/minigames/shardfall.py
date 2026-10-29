#!/usr/bin/env python3
"""Shardfall Gamble: draw glowing shards from the Prismheart seam and bank them before it cracks.

Each round opens a seeded seam bag of valued shards and a few cracked ones.
Draw to grow the round's pot; drawing the second cracked shard collapses the
seam and loses the pot. Bank to add the pot to your score and open the next
round. Reach the target by the last round. The bag's remaining counts are
always shown. Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "shardfall"
TITLE = "Shardfall Gamble"
HOW_TO_PLAY = ("HOW Draw shards to grow the pot or bank it; a second cracked shard collapses the seam "
               "and loses the pot. Reach the target by the last round.")
DIFFICULTY = {
    "easy": {"rounds": 6, "target": 40, "cracked": 2, "values": [1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5]},
    "normal": {"rounds": 5, "target": 40, "cracked": 3, "values": [1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5]},
    "hard": {"rounds": 4, "target": 32, "cracked": 4, "values": [1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5]},
}
DEFAULT_DIFFICULTY = "normal"
BUST_AT = 2


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("round", "pot", "cracks", "bag", "history")

    def setup(self):
        self.round, self.history = 0, []
        self._open()

    def _open(self):
        self.round += 1
        self.pot, self.cracks = 0, 0
        self.bag = list(self.cfg["values"]) + [0] * self.cfg["cracked"]
        self.rng.shuffle(self.bag)

    def _end_round(self, banked):
        self.history.append(banked)
        self.score += banked
        if self.score >= self.cfg["target"]:
            self.finish(True)
        elif self.round >= self.cfg["rounds"]:
            self.finish(False)
        else:
            self._open()

    def act(self, action):
        if action == "draw":
            if not self.bag:
                raise ValueError("the seam is empty; bank")
            v = self.bag.pop()
            if v == 0:
                self.cracks += 1
                if self.cracks >= BUST_AT:
                    self._end_round(0)
                    return "collapse"
                return "cracked"
            self.pot += v
            return f"+{v}"
        if action == "bank":
            pot = self.pot
            self._end_round(pot)
            return f"banked {pot}"
        raise ValueError("use draw or bank")

    def risk(self):
        cracked = self.bag.count(0)
        return cracked / len(self.bag) if self.bag and self.cracks >= BUST_AT - 1 else 0.0

    def demo_action(self):
        if not self.bag or self.pot >= 12 or (self.pot >= 5 and self.risk() > 0.15):
            return "bank"
        return "draw"

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] round {self.round}/{self.cfg['rounds']} score {self.score}/{self.cfg['target']}",
                 f"pot {self.pot} cracks {self.cracks}/{BUST_AT} bag {len(self.bag)} shards ({self.bag.count(0)} cracked)"]
        if self.over:
            lines.append("WON: the seam's light is yours" if self.won else "LOST: the seam closes")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        if line not in ("draw", "bank"):
            raise ValueError("use draw or bank")
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
