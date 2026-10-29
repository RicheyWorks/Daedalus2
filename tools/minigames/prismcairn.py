#!/usr/bin/env python3
"""Prismcairn Duel: out-think a Warden at the shard cairns; whoever lifts the last shard wins the round.

Seeded cairns of Prism Shards stand between you and a Warden. On your turn take
1 to `take_max` shards from one cairn; the Warden answers. Whoever lifts the
last shard wins the round (+50, plus 5 per round left on a match win). Best
of three rounds wins the match. Every round's opening is winnable; the Warden
errs less on harder settings. Stdlib only, deterministic per seed.
"""
import sys
from functools import reduce

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "prismcairn"
TITLE = "Prismcairn Duel"
HOW_TO_PLAY = ("HOW Take 1 or more shards (up to the limit) from one cairn each turn; "
               "the Warden replies. Lift the last shard to win the round; best of three.")
DIFFICULTY = {
    "easy": {"cairns": 3, "take_max": 3, "max_height": 7, "slip": 0.5, "rounds": 3},
    "normal": {"cairns": 4, "take_max": 3, "max_height": 9, "slip": 0.25, "rounds": 3},
    "hard": {"cairns": 5, "take_max": 4, "max_height": 11, "slip": 0.0, "rounds": 3},
}
DEFAULT_DIFFICULTY = "normal"


def grundy(cairns, take_max):
    return reduce(lambda a, b: a ^ b, (h % (take_max + 1) for h in cairns), 0)


def best_move(cairns, take_max):
    """A move to a zero position if one exists, else the smallest legal move."""
    for i, h in enumerate(cairns):
        for t in range(1, min(take_max, h) + 1):
            nxt = list(cairns)
            nxt[i] -= t
            if grundy(nxt, take_max) == 0:
                return (i, t)
    i = next(i for i, h in enumerate(cairns) if h)
    return (i, 1)


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("round", "cairns", "wins", "losses", "log")

    def setup(self):
        self.round, self.wins, self.losses, self.log = 0, 0, 0, []
        self._deal()

    def _deal(self):
        self.round += 1
        k = self.cfg["take_max"]
        while True:
            cairns = [self.rng.randint(1, self.cfg["max_height"]) for _ in range(self.cfg["cairns"])]
            if grundy(cairns, k):
                break
        self.cairns = cairns

    def _round_over(self, player_won):
        if player_won:
            self.wins += 1
            self.score += 50
        else:
            self.losses += 1
        need = self.cfg["rounds"] // 2 + 1
        if self.wins >= need:
            self.score += 5 * (self.cfg["rounds"] - self.round)
            self.finish(True)
        elif self.losses >= need:
            self.finish(False)
        else:
            self._deal()

    def act(self, action):
        i, t = action
        if not 0 <= i < len(self.cairns) or not 1 <= t <= min(self.cfg["take_max"], self.cairns[i]):
            raise ValueError(f"take 1..{self.cfg['take_max']} from a cairn that has them")
        self.cairns[i] -= t
        if not any(self.cairns):
            self.log.append(["you", i, t, "round"])
            self._round_over(True)
            return "you lift the last shard"
        k = self.cfg["take_max"]
        if self.rng.random() < self.cfg["slip"]:
            j = self.rng.choice([x for x, h in enumerate(self.cairns) if h])
            w = (j, self.rng.randint(1, min(k, self.cairns[j])))
        else:
            w = best_move(self.cairns, k)
        self.cairns[w[0]] -= w[1]
        self.log.append(["you", i, t, "warden", w[0], w[1]])
        if not any(self.cairns):
            self._round_over(False)
            return f"warden takes {w[1]} from {w[0]} and lifts the last shard"
        return f"warden takes {w[1]} from {w[0]}"

    def demo_action(self):
        return best_move(self.cairns, self.cfg["take_max"])

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] round {self.round} wins {self.wins} losses {self.losses} score {self.score}",
                 f"take 1-{self.cfg['take_max']} from one cairn"]
        lines += [f"  cairn {i}: {'*' * h} ({h})" for i, h in enumerate(self.cairns)]
        if self.over:
            lines.append("WON: the Warden yields" if self.won else "LOST: the Warden keeps the cairns")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        i, t = (int(x) for x in line.replace(",", " ").split())
        return (i, t)


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
