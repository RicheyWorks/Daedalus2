#!/usr/bin/env python3
"""Shardring Resonance: a prism sphere shard-setting puzzle for Prismheart.

A cracked prism sphere has a ring of empty facets. Each turn one seeded Prism
Shard of a hue arrives (the next is previewed). Set it in any empty facet. A
circular run of 3+ same-hue facets resonates: the run clears and scores
run^2 x chain. Every 3 resonances of one hue summon that Warden's spirit
(+bonus and the spirit clears one more facet). The game ends when every facet
is full (the sphere shatters, lost) or the shard pouch is empty (won).

Pure Python, stdlib only, deterministic per seed.
"""
import argparse
import json
import random
import sys

try:
    from .prism_common import check_rng_state, is_count
except ImportError:
    from prism_common import check_rng_state, is_count

GAME_ID = "shardring"
TITLE = "Shardring Resonance"
HOW_TO_PLAY = ("HOW Set each Prism Shard in an empty facet of the sphere ring; "
               "3 or more of one hue in a row resonate and clear. Do not let the ring fill.")
HUES = ("ember", "tide", "verdant", "gale", "umbra")
SPIRITS = {"ember": "Cinder Wisp", "tide": "Mere Sprite", "verdant": "Thornkin",
           "gale": "Sky Lark Spirit", "umbra": "Hollow Moth"}
DIFFICULTY = {
    "easy": {"facets": 14, "hues": 3, "shards": 60},
    "normal": {"facets": 10, "hues": 3, "shards": 50},
    "hard": {"facets": 8, "hues": 3, "shards": 40},
}
DEFAULT_DIFFICULTY = "normal"
RUN = 3
SPIRIT_EVERY = 3
SPIRIT_BONUS = 25


class ShardringGame:
    def __init__(self, seed=0, difficulty=DEFAULT_DIFFICULTY):
        if difficulty not in DIFFICULTY:
            raise ValueError(f"unknown difficulty '{difficulty}'")
        self.seed, self.difficulty = seed, difficulty
        self.start()

    def start(self):
        cfg = DIFFICULTY[self.difficulty]
        self.rng = random.Random(f"{GAME_ID}:{self.seed}:{self.difficulty}")
        self.hues = HUES[: cfg["hues"]]
        self.ring = [None] * cfg["facets"]
        self.pouch = cfg["shards"]
        self.score = 0
        self.chain = 0
        self.resonance = {h: 0 for h in self.hues}
        self.spirits = []
        self.over = False
        self.won = False
        self.current = self._draw()
        self.next = self._draw()
        return self

    def _draw(self):
        return self.rng.choice(self.hues)

    def empty_facets(self):
        return [i for i, h in enumerate(self.ring) if h is None]

    def _run_at(self, i):
        n, hue = len(self.ring), self.ring[i]
        run = {i}
        for step in (1, -1):
            j = (i + step) % n
            while self.ring[j] == hue and j not in run:
                run.add(j)
                j = (j + step) % n
        return run

    def place(self, facet):
        """Set the current shard in `facet`. Returns points scored this turn."""
        if self.over:
            raise RuntimeError("game over")
        if not 0 <= facet < len(self.ring) or self.ring[facet] is not None:
            raise ValueError(f"facet {facet} is not empty")
        hue = self.current
        self.ring[facet] = hue
        self.pouch -= 1
        gained = 0
        run = self._run_at(facet)
        if len(run) >= RUN:
            self.chain += 1
            gained = len(run) ** 2 * self.chain
            for j in run:
                self.ring[j] = None
            self.resonance[hue] += 1
            if self.resonance[hue] % SPIRIT_EVERY == 0:
                self.spirits.append(SPIRITS[hue])
                gained += SPIRIT_BONUS
                filled = [j for j, h in enumerate(self.ring) if h is not None]
                if filled:
                    self.ring[self.rng.choice(filled)] = None
        else:
            self.chain = 0
        self.score += gained
        self.current, self.next = self.next, self._draw()
        if not self.empty_facets():
            self.over, self.won = True, False
        elif self.pouch <= 0:
            self.over, self.won = True, True
        return gained

    def to_state(self):
        """JSON-serializable snapshot for a host save slot."""
        return {"v": 1, "id": GAME_ID, "seed": self.seed, "difficulty": self.difficulty,
                "ring": list(self.ring), "pouch": self.pouch, "score": self.score, "chain": self.chain,
                "resonance": dict(self.resonance), "spirits": list(self.spirits), "over": self.over,
                "won": self.won, "current": self.current, "next": self.next,
                "rng": [self.rng.getstate()[0], list(self.rng.getstate()[1]), self.rng.getstate()[2]]}

    @classmethod
    def from_state(cls, state):
        """Load a save checked against the rules (ValueError): shapes, hues, counts, over/won, a score floor, RNG state."""
        if not isinstance(state, dict) or state.get("v") != 1 or state.get("id") != GAME_ID:
            raise ValueError("not a shardring v1 save")
        if state.get("difficulty") not in DIFFICULTY or not is_count(state.get("seed")):
            raise ValueError("shardring save has a bad seed or difficulty")
        g = cls(state["seed"], state["difficulty"])
        keys = ("ring", "pouch", "score", "chain", "resonance", "spirits", "over", "won", "current", "next")
        if any(k not in state for k in keys + ("rng",)):
            raise ValueError("shardring save is missing fields")
        if not isinstance(state["ring"], list) or len(state["ring"]) != len(g.ring):
            raise ValueError("ring size does not match difficulty")
        rng_state = check_rng_state(state["rng"])
        for k in keys:
            setattr(g, k, state[k] if not isinstance(state[k], (list, dict)) else type(state[k])(state[k]))
        if not g.follows_rules():
            raise ValueError("shardring save does not satisfy the rules")
        g.rng.setstate(rng_state)
        return g

    def follows_rules(self):
        """The loaded fields must be a state play can reach. The score has no move log to replay, so it is held to
        its floor: every resonance scores at least RUN**2 and every summoned spirit SPIRIT_BONUS."""
        cfg = DIFFICULTY[self.difficulty]
        res = self.resonance
        if not (isinstance(res, dict) and set(res) == set(self.hues) and all(is_count(n) for n in res.values())):
            return False
        expected_spirits = sorted(SPIRITS[h] for h in self.hues for _ in range(res[h] // SPIRIT_EVERY))
        empty = sum(h is None for h in self.ring)
        return (all(h is None or h in self.hues for h in self.ring)
                and self.current in self.hues and self.next in self.hues
                and is_count(self.pouch) and self.pouch <= cfg["shards"] and is_count(self.chain)
                and self.chain <= sum(res.values()) and is_count(self.score)
                and isinstance(self.spirits, list) and sorted(self.spirits) == expected_spirits
                and self.score >= RUN ** 2 * sum(res.values()) + SPIRIT_BONUS * len(self.spirits)
                and isinstance(self.over, bool) and isinstance(self.won, bool)
                and self.over == (empty == 0 or self.pouch <= 0) and self.won == (self.over and empty > 0))

    def render(self):
        mark = {h: h[0].upper() for h in self.hues}
        ring = " ".join(f"{i}:{mark[h] if h else '.'}" for i, h in enumerate(self.ring))
        lines = [f"{TITLE} [{self.difficulty}] score {self.score} chain {self.chain} pouch {self.pouch}",
                 f"ring  {ring}", f"shard {self.current}  next {self.next}"]
        if self.spirits:
            lines.append("spirits " + ", ".join(self.spirits))
        if self.over:
            lines.append("WON: the sphere is whole" if self.won else "LOST: the sphere shattered")
        return "\n".join(lines)

    def status(self):
        return {"id": GAME_ID, "score": self.score, "over": self.over, "won": self.won,
                "pouch": self.pouch, "current": self.current, "next": self.next,
                "ring": list(self.ring), "spirits": list(self.spirits)}


def start(seed=0, difficulty=DEFAULT_DIFFICULTY):
    return ShardringGame(seed, difficulty)


def greedy_move(game):
    """Simple helper policy: prefer a facet that resonates, else next to the same hue."""
    best, best_key = None, None
    n = len(game.ring)
    for i in game.empty_facets():
        game.ring[i] = game.current
        size = len(game._run_at(i))
        game.ring[i] = None
        key = (size >= RUN, size, -i)
        if best_key is None or key > best_key:
            best, best_key = i, key
    return best


def demo(seed=0, difficulty=DEFAULT_DIFFICULTY, out=None):
    """Play a full seeded game with greedy_move; returns the final game. Deterministic."""
    g = start(seed, difficulty)
    while not g.over:
        f = greedy_move(g)
        pts = g.place(f)
        if out:
            print(f"set {f} +{pts}", file=out)
    if out:
        print(g.render(), file=out)
    return g


def play(seed, difficulty, inp=sys.stdin, out=sys.stdout):
    g = start(seed, difficulty)
    print(HOW_TO_PLAY, file=out)
    while not g.over:
        print(g.render(), file=out)
        print("facet (q quits)> ", end="", file=out, flush=True)
        line = inp.readline()
        if not line or line.strip().lower() == "q":
            break
        try:
            g.place(int(line.strip()))
        except ValueError as e:
            print(f"? {e}", file=out)
    print(g.render(), file=out)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prism_shard", description=TITLE)
    ap.add_argument("--play", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--difficulty", default=DEFAULT_DIFFICULTY, choices=sorted(DIFFICULTY))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    if a.play:
        play(a.seed, a.difficulty)
    else:
        g = demo(a.seed, a.difficulty, sys.stdout)
        print(json.dumps({"score": g.score, "won": g.won}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
