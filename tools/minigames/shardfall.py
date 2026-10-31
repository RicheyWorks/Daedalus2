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

    def check_rules(self):
        """A loaded bag must be what this round's draws left (Round 2 finding, art-master-flex 1)."""
        cfg = self.cfg
        full = sorted(list(cfg["values"]) + [0] * cfg["cracked"])
        if not (isinstance(self.bag, list) and all(pc.is_count(v) for v in self.bag) and isinstance(self.history, list)
                and all(pc.is_count(v) for v in self.history) and pc.is_count(self.round) and pc.is_count(self.pot)
                and pc.is_count(self.cracks)):
            raise ValueError("shardfall save fields have the wrong shape")
        drawn = list(full)
        for v in self.bag:
            if v not in drawn:
                raise ValueError("shardfall bag holds shards the seam never had")
            drawn.remove(v)
        if self.cracks != drawn.count(0) or self.pot != sum(drawn) or self.cracks >= BUST_AT and not self.over:
            raise ValueError("shardfall pot and cracks do not match the shards drawn")
        if not 1 <= self.round <= cfg["rounds"] or len(self.history) != self.round - (0 if self.over else 1):
            raise ValueError("shardfall round does not match the banked history")
        if self.won != (self.over and self.score >= cfg["target"]):
            raise ValueError("shardfall result does not match the score")

    def rescore(self):
        return sum(self.history)

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
