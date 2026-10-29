#!/usr/bin/env python3
"""Shadewatch Vigil: hold the Prismheart's lanes against creeping shades with shard flares and a nova.

Shades spawn at the far end of seeded lanes and creep one step toward the
heart each turn. Each turn choose one: flare a lane (burns its front shade),
kindle (store one light, up to 5), or nova (spend 3 light to burn every shade
within 2 steps of the heart). A shade that reaches the heart costs a heart.
Survive every turn to win. Score: 5 per shade burned, 1 per turn survived,
10 per heart left on a win. Stdlib only, deterministic per seed.
"""
import sys

try:
    from . import prism_common as pc
except ImportError:
    import prism_common as pc

GAME_ID = "shadewatch"
TITLE = "Shadewatch Vigil"
HOW_TO_PLAY = ("HOW Each turn flare one lane, kindle light or spend 3 light on a nova; "
               "keep the creeping shades from reaching the heart until the vigil ends.")
DIFFICULTY = {
    "easy": {"lanes": 2, "length": 6, "spawn": 0.45, "turns": 20, "hearts": 3},
    "normal": {"lanes": 3, "length": 6, "spawn": 0.33, "turns": 24, "hearts": 3},
    "hard": {"lanes": 4, "length": 6, "spawn": 0.28, "turns": 28, "hearts": 3},
}
DEFAULT_DIFFICULTY = "normal"
LIGHT_MAX, NOVA_COST, NOVA_REACH = 5, 3, 2


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("lanes", "hearts", "light", "turn", "burned")

    def setup(self):
        self.lanes = [[] for _ in range(self.cfg["lanes"])]
        self.hearts, self.light, self.turn, self.burned = self.cfg["hearts"], 1, 0, 0
        self._spawn()

    def _spawn(self):
        for lane in self.lanes:
            if self.rng.random() < self.cfg["spawn"] and (not lane or max(lane) < self.cfg["length"] - 1):
                lane.append(self.cfg["length"] - 1)

    def act(self, action):
        kind, i = action
        burned = 0
        if kind == "flare":
            if not 0 <= i < len(self.lanes):
                raise ValueError("no such lane")
            if self.lanes[i]:
                self.lanes[i].remove(min(self.lanes[i]))
                burned = 1
        elif kind == "kindle":
            self.light = min(LIGHT_MAX, self.light + 1)
        elif kind == "nova":
            if self.light < NOVA_COST:
                raise ValueError(f"a nova needs {NOVA_COST} light")
            self.light -= NOVA_COST
            for lane in self.lanes:
                keep = [p for p in lane if p > NOVA_REACH]
                burned += len(lane) - len(keep)
                lane[:] = keep
        else:
            raise ValueError("use flare <lane>, kindle or nova")
        self.burned += burned
        self.score += 5 * burned
        hits = 0
        for lane in self.lanes:
            lane[:] = [p - 1 for p in lane]
            hits += sum(1 for p in lane if p < 0)
            lane[:] = sorted(p for p in lane if p >= 0)
        self.hearts -= hits
        self.turn += 1
        if self.hearts <= 0:
            self.finish(False)
            return "the heart dims"
        self.score += 1
        if self.turn >= self.cfg["turns"]:
            self.score += 10 * self.hearts
            self.finish(True)
            return "dawn: the vigil holds"
        self._spawn()
        return f"burned {burned}" + (f", {hits} shade(s) struck the heart" if hits else "")

    def demo_action(self):
        fronts = [(min(l), i) for i, l in enumerate(self.lanes) if l]
        near = [f for f in fronts if f[0] == 0]
        if len(near) >= 2 and self.light >= NOVA_COST:
            return ("nova", 0)
        if near:
            return ("flare", near[0][1])
        close = sum(1 for p, _ in fronts if p <= NOVA_REACH)
        if close >= 2 and self.light >= NOVA_COST:
            return ("nova", 0)
        if fronts and (min(fronts)[0] <= 1 or self.light >= LIGHT_MAX):
            return ("flare", min(fronts)[1])
        return ("kindle", 0)

    def render(self):
        lines = [f"{TITLE} [{self.difficulty}] turn {self.turn}/{self.cfg['turns']} hearts {self.hearts} light {self.light} score {self.score}"]
        for i, lane in enumerate(self.lanes):
            cells = "".join("s" if p in lane else "." for p in range(self.cfg["length"]))
            lines.append(f"lane {i}: <3 {cells}")
        if self.over:
            lines.append("WON: dawn breaks over the heart" if self.won else "LOST: the shades reach the heart")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        parts = line.split()
        if parts[0] == "flare" and len(parts) == 2:
            return ("flare", int(parts[1]))
        if parts[0] in ("kindle", "nova") and len(parts) == 1:
            return (parts[0], 0)
        raise ValueError("use flare <lane>, kindle or nova")


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
