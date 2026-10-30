"""Shared plumbing for the Prismheart campaign minigames (stdlib only).

PrismGame gives every game the same contract as Shardring: seeded RNG from
"<game_id>:<seed>:<difficulty>", start(), score/over/won, status(),
to_state()/from_state() (JSON-safe, RNG included) and a --play/--demo CLI.
A game subclass sets GAME_ID, TITLE, DIFFICULTY, FIELDS and implements
setup(), act(action), demo_action(), render() and parse(line).
"""
import argparse
import copy
import json
import random
import sys


class PrismGame:
    GAME_ID = ""
    TITLE = ""
    HOW_TO_PLAY = ""
    DIFFICULTY = {}
    DEFAULT_DIFFICULTY = "normal"
    FIELDS = ()

    def __init__(self, seed=0, difficulty=None):
        difficulty = difficulty or self.DEFAULT_DIFFICULTY
        if difficulty not in self.DIFFICULTY:
            raise ValueError(f"unknown difficulty '{difficulty}'")
        self.seed, self.difficulty = seed, difficulty
        self.start()

    def start(self):
        self.cfg = dict(self.DIFFICULTY[self.difficulty])
        self.rng = random.Random(f"{self.GAME_ID}:{self.seed}:{self.difficulty}")
        self.score, self.over, self.won = 0, False, False
        self.setup()
        return self

    def setup(self):
        raise NotImplementedError

    def act(self, action):
        raise NotImplementedError

    def demo_action(self):
        raise NotImplementedError

    def render(self):
        raise NotImplementedError

    @staticmethod
    def parse(line):
        raise NotImplementedError

    def step(self, action):
        if self.over:
            raise RuntimeError("game over")
        return self.act(action)

    def finish(self, won):
        self.over, self.won = True, bool(won)

    def status(self):
        out = {"id": self.GAME_ID, "score": self.score, "over": self.over, "won": self.won}
        for k in self.FIELDS:
            out[k] = copy.deepcopy(getattr(self, k))
        return out

    def to_state(self):
        st = self.status()
        st.update({"v": 1, "seed": self.seed, "difficulty": self.difficulty})
        v, internal, gauss = self.rng.getstate()
        st["rng"] = [v, list(internal), gauss]
        return json.loads(json.dumps(st))

    @classmethod
    def from_state(cls, state):
        if state.get("v") != 1 or state.get("id") != cls.GAME_ID:
            raise ValueError(f"not a {cls.GAME_ID} v1 save")
        g = cls(state["seed"], state["difficulty"])
        for k in ("score", "over", "won") + tuple(cls.FIELDS):
            setattr(g, k, copy.deepcopy(state[k]))
        g.restore()
        v, internal, gauss = state["rng"]
        g.rng.setstate((v, tuple(internal), gauss))
        return g

    def restore(self):
        """Hook: rebuild derived (non-saved) fields after from_state."""


def demo(cls, seed=0, difficulty=None, out=None, limit=10000):
    g = cls(seed, difficulty)
    for _ in range(limit):
        if g.over:
            break
        a = g.demo_action()
        res = g.step(a)
        if out:
            print(f"> {a} -> {res}", file=out)
    if out:
        print(g.render(), file=out)
    return g


def play(cls, seed, difficulty, inp=sys.stdin, out=sys.stdout):
    g = cls(seed, difficulty)
    print(cls.HOW_TO_PLAY, file=out)
    while not g.over:
        print(g.render(), file=out)
        print("> ", end="", file=out, flush=True)
        line = inp.readline()
        if not line or line.strip().lower() in ("q", "quit"):
            break
        try:
            print(g.step(cls.parse(line.strip())), file=out)
        except (ValueError, IndexError, KeyError) as e:
            print(f"? {e}", file=out)
    print(g.render(), file=out)
    return g


def main(cls, argv=None):
    ap = argparse.ArgumentParser(prog=cls.GAME_ID, description=cls.TITLE)
    ap.add_argument("--play", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--difficulty", default=cls.DEFAULT_DIFFICULTY, choices=sorted(cls.DIFFICULTY))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    if a.play:
        play(cls, a.seed, a.difficulty)
    else:
        g = demo(cls, a.seed, a.difficulty, sys.stdout)
        print(json.dumps({"score": g.score, "won": g.won}))
    return 0
