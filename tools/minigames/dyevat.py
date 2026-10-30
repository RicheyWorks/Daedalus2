#!/usr/bin/env python3
"""Dyevat: pour pigment layers between vats until every vat holds one hue (G601, art-master-flex).

A seeded rack of vats for the fresco painters. Each hue has CAPACITY (4)
layers, shuffled into the first HUES vats; EMPTY more vats start empty. A
pour moves the top run of one vat (all touching layers of its top hue) onto
another vat whose top is the same hue, or onto an empty vat, as many layers
as fit. A vat full of one hue seals: +5, and it is locked for the rest of the
game. Seal every hue to win (+3 per pour left). Running out of pours, or
being left with no legal pour, loses. Stdlib only, deterministic per seed:
randrange only at setup (a Fisher-Yates shuffle from the back), nothing
random after.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "dyevat"
TITLE = "Dyevat"
HOW_TO_PLAY = ("HOW Pour the top run of one vat onto an empty vat or a matching top hue; a vat full of one hue seals. "
               "Seal every hue before the pours run out.")
DIFFICULTY = {
    "easy": {"hues": 3, "empty": 2, "pours": 30},
    "normal": {"hues": 4, "empty": 2, "pours": 40},
    "hard": {"hues": 5, "empty": 2, "pours": 50},
}
DEFAULT_DIFFICULTY = "normal"
CAPACITY = 4
SEAL_SCORE, POUR_BONUS = 5, 3


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("vats", "sealed", "pours", "last")

    def setup(self):
        hues, empty = self.cfg["hues"], self.cfg["empty"]
        layers = [h for h in range(1, hues + 1) for _ in range(CAPACITY)]
        for i in range(len(layers) - 1, 0, -1):
            j = self.rng.randrange(i + 1)
            layers[i], layers[j] = layers[j], layers[i]
        self.vats = [layers[v * CAPACITY:(v + 1) * CAPACITY] for v in range(hues)] + [[] for _ in range(empty)]
        self.sealed = [False] * (hues + empty)
        self.pours = self.cfg["pours"]
        self.last = [-1, -1]
        # A vat dealt full of one hue seals at once (no score; nothing was poured).
        for v in range(len(self.vats)):
            self.sealed[v] = self.full_one_hue(v)

    def full_one_hue(self, v):
        vat = self.vats[v]
        return len(vat) == CAPACITY and all(x == vat[0] for x in vat)

    def count(self):
        return len(self.vats)

    def sealed_count(self):
        return sum(self.sealed)

    def run(self, v):
        """Length of the top run of vat v (0 when empty)."""
        vat = self.vats[v]
        n = 0
        while n < len(vat) and vat[-1 - n] == vat[-1]:
            n += 1
        return n

    def legal(self, a, b):
        if a == b or not (0 <= a < self.count() and 0 <= b < self.count()):
            return False
        if self.sealed[a] or self.sealed[b] or not self.vats[a] or len(self.vats[b]) >= CAPACITY:
            return False
        return not self.vats[b] or self.vats[b][-1] == self.vats[a][-1]

    def any_legal(self):
        n = self.count()
        return any(self.legal(a, b) for a in range(n) for b in range(n))

    def parse_pour(self, action):
        parts = action.split(",") if "," in action else action.split()
        if len(parts) != 2:
            raise ValueError("use from,to")
        try:
            a, b = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError("use from,to") from None
        if not (0 <= a < self.count() and 0 <= b < self.count()):
            raise ValueError("no such vat")
        if not self.legal(a, b):
            raise ValueError("that pour is not allowed")
        return a, b

    def act(self, action):
        a, b = self.parse_pour(action)
        moved = min(self.run(a), CAPACITY - len(self.vats[b]))
        for _ in range(moved):
            self.vats[b].append(self.vats[a].pop())
        self.pours -= 1
        self.last = [a, b]
        seals = 0
        if self.full_one_hue(b):
            self.sealed[b] = True
            seals = 1
            self.score += SEAL_SCORE
        if self.sealed_count() == self.cfg["hues"]:
            self.score += POUR_BONUS * self.pours
            self.finish(True)
            return f"{a},{b}: {moved} poured, every hue sealed"
        if self.pours <= 0:
            self.finish(False)
            return f"{a},{b}: {moved} poured; the pours are spent"
        if not self.any_legal():
            self.finish(False)
            return f"{a},{b}: {moved} poured; no pour is left"
        return f"{a},{b}: {moved} poured, {seals} sealed, {self.sealed_count()}/{self.cfg['hues']} hues"

    def preview(self, a, b):
        """(moved, seals, onto_empty) a pour would give, or None when it is not allowed."""
        if not self.legal(a, b):
            return None
        moved = min(self.run(a), CAPACITY - len(self.vats[b]))
        after = len(self.vats[b]) + moved
        onto_empty = not self.vats[b]
        seals = int(after == CAPACITY and (onto_empty or all(x == self.vats[a][-1] for x in self.vats[b])))
        return moved, seals, int(onto_empty)

    def demo_action(self):
        """Dyer: never undo the last pour or move a whole one-hue vat into an empty one; prefer a seal, then a
        matching top over an empty vat, then the most layers moved, then the pour that leaves the source empty;
        ties by from, to. Falls back to any legal pour (lowest from, to)."""
        best = None
        fallback = None
        n = self.count()
        for a in range(n):
            for b in range(n):
                p = self.preview(a, b)
                if p is None:
                    continue
                if fallback is None:
                    fallback = (a, b)
                moved, seals, onto_empty = p
                if [b, a] == self.last:
                    continue
                if onto_empty and moved == len(self.vats[a]):
                    continue
                empties_source = int(moved == len(self.vats[a]))
                key = (-seals, onto_empty, -moved, -empties_source, a, b)
                if best is None or key < best[0]:
                    best = (key, (a, b))
        pick = best[1] if best else fallback
        return "%d,%d" % pick if pick else "0,1"

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] pours {self.pours} sealed {self.sealed_count()}/{self.cfg['hues']} score {self.score}"]
        for v, vat in enumerate(self.vats):
            body = "".join(str(x) for x in vat).ljust(CAPACITY, ".")
            lines.append(f"{v}: |{body}|" + (" sealed" if self.sealed[v] else ""))
        if self.over:
            lines.append("WON: every hue sealed" if self.won else "LOST: the dye has set")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        return line.strip().lower().replace(" ", ",")


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
