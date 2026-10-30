#!/usr/bin/env python3
"""Prismchime Ring: tap crystal chimes so their charge hops the ring, peals chain, and every chime rings once.

A ring of N chimes. Each starts with a seeded charge (1-2) and a facing
(clockwise or counter). Tap a chime: it rings, sending one pulse to each of
the next `charge` chimes in its facing (one hop per point of charge, +1 each),
and the rung chime itself gains one from the resonance. A chime that reaches
PEAL (4) peals: it scores, lights, resets to 0 and pushes one charge to each
neighbour, which can peal in turn (processed in the order they fill). Light
every chime before the taps run out to win; score 5 per peal plus 3 per tap
left on a win. Stdlib only, deterministic per seed: randrange only, so the
Unreal port is bit-exact.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "prismchime"
TITLE = "Prismchime Ring"
HOW_TO_PLAY = ("HOW Tap a chime to ring it: its charge pulses along its facing and it gains one; a chime that fills to "
               "four peals and charges both neighbours. Light every chime before your taps run out.")
DIFFICULTY = {
    "easy": {"chimes": 6, "taps": 8},
    "normal": {"chimes": 8, "taps": 8},
    "hard": {"chimes": 10, "taps": 8},
}
DEFAULT_DIFFICULTY = "normal"
PEAL = 4
PEAL_SCORE, TAP_BONUS = 5, 3


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("charge", "facing", "lit", "taps", "peals")

    def setup(self):
        n = self.cfg["chimes"]
        self.charge = [1 + self.rng.randrange(2) for _ in range(n)]
        self.facing = [1 if self.rng.randrange(2) else -1 for _ in range(n)]
        self.lit = [False] * n
        self.taps, self.peals = self.cfg["taps"], 0

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5)."""
        g = super().from_state(state)
        n = g.cfg["chimes"]
        ok = (len(g.charge) == n and len(g.facing) == n and len(g.lit) == n
              and all(isinstance(c, int) and 0 <= c < PEAL for c in g.charge)
              and all(f in (-1, 1) for f in g.facing)
              and all(isinstance(x, bool) for x in g.lit)
              and isinstance(g.taps, int) and 0 <= g.taps <= g.cfg["taps"]
              and isinstance(g.peals, int) and g.peals >= 0
              and g.over == (all(g.lit) or g.taps <= 0) and g.won == all(g.lit))
        if not ok:
            raise ValueError("prismchime save does not satisfy the rules")
        return g

    def _peal(self, i, queue):
        """Chime i peals: score, light, reset, and charge both neighbours (queued in order)."""
        n = len(self.charge)
        self.charge[i] = 0
        self.lit[i] = True
        self.peals += 1
        self.score += PEAL_SCORE
        for j in ((i - 1) % n, (i + 1) % n):
            self.charge[j] += 1
            if self.charge[j] >= PEAL:
                queue.append(j)

    def act(self, i):
        n = len(self.charge)
        if not 0 <= i < n:
            raise ValueError("no such chime")
        queue = []
        hops, cur = self.charge[i], i
        for _ in range(hops):
            cur = (cur + self.facing[i]) % n
            self.charge[cur] += 1
            if self.charge[cur] >= PEAL:
                queue.append(cur)
        self.charge[i] += 1          # the rung chime resonates
        if self.charge[i] >= PEAL:
            queue.append(i)
        pealed = 0
        while queue:
            j = queue.pop(0)
            if self.charge[j] >= PEAL:   # a neighbour's peal may already have drained it
                self._peal(j, queue)
                pealed += 1
        self.taps -= 1
        if all(self.lit):
            self.score += TAP_BONUS * self.taps
            self.finish(True)
            return f"tap {i}: {pealed} peal(s), every chime rings"
        if self.taps <= 0:
            self.finish(False)
            return f"tap {i}: {pealed} peal(s), the ring falls silent"
        return f"tap {i}: {pealed} peal(s)"

    def preview(self, i):
        """Peals and newly lit chimes a tap on chime i would produce, without changing the game (iteration 8)."""
        trial = self._copy()
        before = sum(trial.lit)
        res = trial.act(i)
        pealed = int(res.split(": ", 1)[1].split(" ", 1)[0])
        return pealed, sum(trial.lit) - before

    def demo_action(self):
        """Try every chime on a copy; most newly lit, then most score, then lowest index (iteration 9: no JSON copy)."""
        best = None
        for i in range(len(self.charge)):
            trial = self._copy()
            trial.act(i)
            key = (sum(trial.lit) - sum(self.lit), trial.score - self.score, -i)
            if best is None or key > best[0]:
                best = (key, i)
        return best[1]

    def _copy(self):
        """A playable copy for look-ahead: act() never draws, so the RNG is shared, not copied."""
        c = self.__class__.__new__(self.__class__)
        c.cfg, c.rng, c.seed, c.difficulty = self.cfg, self.rng, self.seed, self.difficulty
        c.score, c.over, c.won = self.score, self.over, self.won
        c.charge, c.facing, c.lit = list(self.charge), list(self.facing), list(self.lit)
        c.taps, c.peals = self.taps, self.peals
        return c

    def tutorial(self):
        """First-ring teaching rows for the screen (iteration 7)."""
        return ["TAP   a chime rings: its charge pulses along its arrow, one chime per point, and it gains one",
                "PEAL  a chime at %d peals: +%d, it lights, resets, and charges both neighbours" % (PEAL, PEAL_SCORE),
                "WIN   light every chime before the taps run out; +%d per tap left" % TAP_BONUS]

    def render(self):
        row = " ".join(f"{'*' if l else '.'}{c}{'>' if f > 0 else '<'}" for c, f, l in zip(self.charge, self.facing, self.lit))
        lines = [f"{TITLE} [{self.difficulty}] taps {self.taps} score {self.score} lit {sum(self.lit)}/{len(self.lit)}", row,
                 "peal at %d: %s" % (PEAL, "  ".join("[%s]" % ("#" * c + "." * (PEAL - c)) for c in self.charge))]
        if self.taps == self.cfg["taps"] and not self.over:
            lines += self.tutorial()
        if self.over:
            lines.append("WON: every chime rings" if self.won else "LOST: the ring falls silent")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        try:
            return int(line)
        except ValueError:
            raise ValueError("enter a chime number") from None


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
