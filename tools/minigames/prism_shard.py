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
import random

GAME_ID = "shardring"
TITLE = "Shardring Resonance"
HOW_TO_PLAY = ("HOW Set each Prism Shard in an empty facet of the sphere ring; "
               "3 or more of one hue in a row resonate and clear. Do not let the ring fill.")
HUES = ("ember", "tide", "verdant", "gale", "umbra")
SPIRITS = {"ember": "Cinder Wisp", "tide": "Mere Sprite", "verdant": "Thornkin",
           "gale": "Sky Lark Spirit", "umbra": "Hollow Moth"}
DIFFICULTY = {
    "easy": {"facets": 12, "hues": 3, "shards": 60},
    "normal": {"facets": 10, "hues": 4, "shards": 50},
    "hard": {"facets": 8, "hues": 5, "shards": 40},
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
