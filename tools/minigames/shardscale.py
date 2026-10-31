#!/usr/bin/env python3
"""Shardscale: set a line of prism shards on a balance beam, one at a time, without ever letting it tip.

A seeded line of shards (weights 1-9) comes off the cart in order. Each turn
you set the next shard on the left or right pan, or hold it back on the bench
(a few bench slots); a held shard can be set on either pan on a later turn.
After every placement the beam must stay within the cap: if the pans differ by
more than the cap the beam tips, the shards slide off and the weighing is lost.
When every shard is on the beam the weighing ends: level within the tolerance
wins. Score 10 plus 5 per point of slack under the tolerance plus 2 per bench
slot never used. Every line is solvable (the setup keeps drawing until the
exact search finds a level weighing). Stdlib only, deterministic per seed:
randrange only at setup, nothing random after.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "shardscale"
TITLE = "Shardscale"
HOW_TO_PLAY = ("HOW Set the next shard left (l) or right (r), or hold it on the bench; set a held shard with l<n>/r<n>. "
               "Never let the pans differ by more than the cap; end level within the tolerance.")
DIFFICULTY = {
    "easy": {"shards": 8, "cap": 6, "tolerance": 1, "bench": 2},
    "normal": {"shards": 10, "cap": 5, "tolerance": 1, "bench": 2},
    "hard": {"shards": 12, "cap": 5, "tolerance": 0, "bench": 3},
}
DEFAULT_DIFFICULTY = "normal"
MIN_WEIGHT, MAX_WEIGHT = 1, 9
WIN_SCORE, SLACK_SCORE, BENCH_SCORE = 10, 5, 2
MAX_REDRAWS = 50


def solve(line, index, diff, held, cap, tolerance, bench, memo):
    """First winning action from (index, diff, held) in the rules' action order, or None. Exact search with memo."""
    key = (index, diff, held)
    if key in memo:
        return memo[key]
    result = None
    if index == len(line) and not held:
        result = () if abs(diff) <= tolerance else None
    else:
        for action in candidate_actions(line, index, held, bench):
            kind, source = action
            weight = line[index] if source == "next" else held[source]
            if kind == "hold":
                nxt = (index + 1, diff, tuple(sorted(held + (weight,))))
            else:
                new_diff = diff + (weight if kind == "left" else -weight)
                if abs(new_diff) > cap:
                    continue
                new_held = held if source == "next" else held[:source] + held[source + 1:]
                nxt = (index + (1 if source == "next" else 0), new_diff, new_held)
            if solve(line, nxt[0], nxt[1], nxt[2], cap, tolerance, bench, memo) is not None:
                result = action
                break
    memo[key] = result
    return result


def candidate_actions(line, index, held, bench):
    """Legal actions in the rules' order: left/right the next shard, hold it, then left/right each held shard."""
    out = []
    if index < len(line):
        out += [("left", "next"), ("right", "next")]
        if len(held) < bench:
            out.append(("hold", "next"))
    for h in range(len(held)):
        out += [("left", h), ("right", h)]
    return out


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("line", "index", "left", "right", "held", "bench_used", "tipped")

    def setup(self):
        cfg = self.cfg
        for _ in range(MAX_REDRAWS):
            self.line = [MIN_WEIGHT + self.rng.randrange(MAX_WEIGHT - MIN_WEIGHT + 1) for _ in range(cfg["shards"])]
            if solve(tuple(self.line), 0, 0, (), cfg["cap"], cfg["tolerance"], cfg["bench"], {}) is not None:
                break
        self.index, self.left, self.right, self.held, self.bench_used, self.tipped = 0, 0, 0, [], 0, False

    @classmethod
    def from_state(cls, state):
        """A save is checked against the rules before it is trusted (iteration 5)."""
        g = super().from_state(state)
        cfg = g.cfg
        ok = (isinstance(g.line, list) and len(g.line) == cfg["shards"] and all(isinstance(w, int) and MIN_WEIGHT <= w <= MAX_WEIGHT for w in g.line)
              and isinstance(g.index, int) and 0 <= g.index <= cfg["shards"]
              and isinstance(g.held, list) and len(g.held) <= cfg["bench"] and all(isinstance(w, int) and MIN_WEIGHT <= w <= MAX_WEIGHT for w in g.held)
              and g.held == sorted(g.held)
              and isinstance(g.bench_used, int) and len(g.held) <= g.bench_used <= g.index
              and isinstance(g.left, int) and isinstance(g.right, int) and g.left >= 0 and g.right >= 0
              and g.left + g.right + sum(g.held) == sum(g.line[:g.index])
              and isinstance(g.tipped, bool) and (abs(g.left - g.right) <= cfg["cap"] or g.tipped)
              and g.over == (g.tipped or (g.index == cfg["shards"] and not g.held))
              and g.won == (g.over and not g.tipped and abs(g.left - g.right) <= cfg["tolerance"]))
        if not ok:
            raise ValueError("shardscale save does not satisfy the rules")
        return g

    def diff(self):
        return self.left - self.right

    def remaining(self):
        return self.cfg["shards"] - self.index + len(self.held)

    def actions(self):
        return candidate_actions(self.line, self.index, tuple(self.held), self.cfg["bench"])

    def act(self, action):
        if action not in self.actions():
            raise ValueError("use l, r, hold, or l<n>/r<n> for a bench shard")
        kind, source = action
        if source == "next":
            weight = self.line[self.index]
            self.index += 1
        else:
            weight = self.held.pop(source)
        if kind == "hold":
            self.held.append(weight)
            self.held.sort()
            self.bench_used += 1
            return f"hold {weight}: bench {self.held}"
        if kind == "left":
            self.left += weight
        else:
            self.right += weight
        side = f"{kind} {weight}: pans {self.left}/{self.right}"
        if abs(self.diff()) > self.cfg["cap"]:
            self.tipped = True
            self.finish(False)
            return side + "; the beam tips and the shards slide off"
        if self.remaining() == 0:
            level = abs(self.diff()) <= self.cfg["tolerance"]
            if level:
                slack = self.cfg["tolerance"] - abs(self.diff())
                self.score = WIN_SCORE + SLACK_SCORE * slack + BENCH_SCORE * (self.cfg["bench"] - self.bench_used)
            self.finish(level)
            return side + ("; the beam rests level" if level else "; the beam settles askew")
        return side

    def preview(self, action):
        """(legal, diff after, tips, ends) for an action without taking it (iteration 8)."""
        if action not in self.actions():
            return (False, self.diff(), False, False)
        kind, source = action
        weight = self.line[self.index] if source == "next" else self.held[source]
        if kind == "hold":
            return (True, self.diff(), False, False)
        after = self.diff() + (weight if kind == "left" else -weight)
        return (True, after, abs(after) > self.cfg["cap"], self.remaining() == 1)

    def demo_action(self):
        """Weigher: the first action of an exact winning line from here; the lighter pan if none is left."""
        cfg = self.cfg
        found = solve(tuple(self.line), self.index, self.diff(), tuple(self.held), cfg["cap"], cfg["tolerance"], cfg["bench"], {})
        if found:
            return found
        acts = self.actions()
        return ("left", "next") if self.diff() <= 0 and ("left", "next") in acts else acts[1] if len(acts) > 1 else acts[0]

    def tutorial(self):
        """First-turn teaching rows for the screen (iteration 7)."""
        return ["SET    l / r sets the next shard on a pan; hold keeps it on the bench (%d slots)" % self.cfg["bench"],
                "CAP    if the pans ever differ by more than %d the beam tips and you lose" % self.cfg["cap"],
                "LEVEL  place every shard and end within %d to win" % self.cfg["tolerance"]]

    def fresh(self):
        return self.index == 0 and not self.over

    def render(self):
        cfg = self.cfg
        coming = " ".join(str(w) for w in self.line[self.index:self.index + 5])
        lines = [f"{TITLE} [{self.difficulty}] left {self.left} right {self.right} diff {self.diff():+d} cap {cfg['cap']} tol {cfg['tolerance']} score {self.score}",
                 f"next: {coming or '-'}   bench: {' '.join(str(w) for w in self.held) or '-'} ({len(self.held)}/{cfg['bench']})   left to place: {self.remaining()}"]
        tilt = max(-cfg["cap"], min(cfg["cap"], self.diff()))
        lines.append("beam: " + "L" + "=" * (cfg["cap"] + tilt) + "^" + "=" * (cfg["cap"] - tilt) + "R")
        if not self.over and self.index < cfg["shards"]:   # iteration 9: where the next shard may safely go
            safe = [side for side, a in (("left", ("left", "next")), ("right", ("right", "next"))) if not self.preview(a)[2]]
            lines.append("next shard %d fits: %s" % (self.line[self.index], " and ".join(safe) if safe else "neither pan (bench it)"))
        if self.fresh():
            lines += self.tutorial()
        if self.over:
            lines.append("WON: the beam rests level" if self.won else "LOST: " + ("the beam tips" if self.tipped else "the beam settles askew"))
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        text = line.strip().lower()
        if text in ("l", "left"):
            return ("left", "next")
        if text in ("r", "right"):
            return ("right", "next")
        if text in ("h", "hold"):
            return ("hold", "next")
        if len(text) >= 2 and text[0] in "lr" and text[1:].isdigit():
            return ("left" if text[0] == "l" else "right", int(text[1:]))
        raise ValueError("use l, r, hold, or l<n>/r<n> for a bench shard")


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
