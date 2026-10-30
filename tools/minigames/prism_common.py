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
        """Load a save, trusting nothing: shape, RNG state, game rules and score are all checked (ValueError)."""
        if not isinstance(state, dict) or state.get("v") != 1 or state.get("id") != cls.GAME_ID:
            raise ValueError(f"not a {cls.GAME_ID} v1 save")
        if state.get("difficulty") not in cls.DIFFICULTY or not is_count(state.get("seed")):
            raise ValueError(f"{cls.GAME_ID} save has a bad seed or difficulty")
        missing = [k for k in ("score", "over", "won", "rng") + tuple(cls.FIELDS) if k not in state]
        if missing:
            raise ValueError(f"{cls.GAME_ID} save is missing {', '.join(missing)}")
        if not is_count(state["score"]) or not isinstance(state["over"], bool) or not isinstance(state["won"], bool):
            raise ValueError(f"{cls.GAME_ID} save score must be a whole number >= 0 and over/won true or false")
        rng_state = check_rng_state(state["rng"])
        g = cls(state["seed"], state["difficulty"])
        for k in ("score", "over", "won") + tuple(cls.FIELDS):
            setattr(g, k, copy.deepcopy(state[k]))
        try:
            g.restore()
            g.check_rules()
            expected = g.rescore()
        except (TypeError, KeyError, IndexError, AttributeError) as e:
            raise ValueError(f"{cls.GAME_ID} save does not satisfy the rules ({type(e).__name__})") from None
        if expected is not None and expected != g.score:
            raise ValueError(f"{cls.GAME_ID} save score {g.score} does not match its state ({expected})")
        g.rng.setstate(rng_state)
        return g

    def check_rules(self):
        """Hook: raise ValueError when loaded fields break the game's rules (ranges, sizes, over/won)."""

    def rescore(self):
        """Hook: the score the loaded state implies, or None when it cannot be derived from the state alone."""
        return None

    def restore(self):
        """Hook: rebuild derived (non-saved) fields after from_state."""


MT_WORDS = 624  # Mersenne Twister state words; random.getstate() adds the position as word 625
RNG_VERSION = 3


def is_count(x):
    """A whole number >= 0 (bool is not a count)."""
    return isinstance(x, int) and not isinstance(x, bool) and x >= 0


def check_rng_state(rng):
    """Validate a saved [version, internal, gauss] RNG state before setstate (ValueError); returns the setstate tuple."""
    ok = (isinstance(rng, (list, tuple)) and len(rng) == 3 and rng[0] == RNG_VERSION
          and isinstance(rng[1], (list, tuple)) and len(rng[1]) == MT_WORDS + 1
          and all(is_count(w) and w < 2 ** 32 for w in rng[1][:MT_WORDS])
          and is_count(rng[1][MT_WORDS]) and rng[1][MT_WORDS] <= MT_WORDS
          and (rng[2] is None or isinstance(rng[2], float)))
    if not ok:
        raise ValueError("save RNG state is not a valid Mersenne Twister state")
    return rng[0], tuple(rng[1]), rng[2]


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
