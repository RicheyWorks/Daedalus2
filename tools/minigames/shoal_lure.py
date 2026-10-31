#!/usr/bin/env python3
"""Shoal Lure: steer a lure across a seeded current grid in Prismheart and coax prism-fish home to the Skiff.

The Skiff sits in the middle of the top row. Each cell has a current (N, E, S or W). Moving the lure one cell costs
1 stamina, or 2 when the target cell's current flows straight back at you. `net` a prism-fish where the lure stands to
add it to the shoal; umbra eels scatter the whole shoal when the lure swims onto them. Dock at the Skiff to bank the
shoal: fish of the same hue netted one after another chain, and a run of k scores 1 + 2 + .. + k. Bank at least the
target to win (score = shoal value + stamina left); if a move leaves too little stamina to swim home, the line snaps
and the round is lost. The target comes from the exact best trip (every netting order is searched), and the demo and
hint play the best score, not just the biggest shoal. All rules math is integer.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prism_common as pc  # noqa: E402

GAME_ID, TITLE = "shoal_lure", "Shoal Lure"
DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))  # N E S W: the current flows this way; moves use the same codes
DIR_NAMES = "NESW"
ARROWS = "^>v<"
INF = 10 ** 9
PERCENT = 100
DIFFICULTY = {
    "easy": {"size": 5, "fish": 5, "eels": 2, "hues": 2, "stamina": 24, "target_pct": 60},
    "normal": {"size": 6, "fish": 6, "eels": 3, "hues": 3, "stamina": 26, "target_pct": 75},
    "hard": {"size": 7, "fish": 7, "eels": 5, "hues": 3, "stamina": 28, "target_pct": 85},
}
DEFAULT_DIFFICULTY = "normal"
HOW_TO_PLAY = """Shoal Lure - bring prism-fish home to the Skiff.
1. `n`, `e`, `s`, `w` move the lure one cell: 1 stamina, 2 if that cell's current flows straight back at you.
2. `net` catches the prism-fish under the lure (hues a, b, c) and adds it to the shoal.
3. Swimming onto an umbra eel (X) scatters the whole shoal.
4. `dock` at the Skiff (S) banks the shoal and ends the round: same-hue fish netted in a row chain, a run of k
   scores 1 + 2 + .. + k. Bank at least the target to win; stamina left adds to a win's score.
5. If a move leaves less stamina than the swim home, the line snaps: you lose.
Type `hint` for the best next move, `help` for this text, `q` to quit."""


def chain_value(hues):
    """Shoal value: each run of k same-hue fish scores k * (k + 1) / 2."""
    total, run, last = 0, 0, None
    for h in hues:
        run = run + 1 if h == last else 1
        total += run
        last = h
    return total


def step_cost(current, r, c, d):
    """Stamina to move into cell (r, c) heading d: 1, or 2 when its current flows straight back (opposite of d)."""
    return 2 if current[r][c] == (d + 2) % 4 else 1


def distances(size, current, eels):
    """All-pairs least stamina between cells (index r * size + c), never entering an eel. Floyd-Warshall."""
    n = size * size
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
        if i in eels:
            continue
        r, c = divmod(i, size)
        for d, (dr, dc) in enumerate(DIRS):
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and nr * size + nc not in eels:
                dist[i][nr * size + nc] = step_cost(current, nr, nc, d)
    for k in range(n):
        dk = dist[k]
        for i in range(n):
            dik = dist[i][k]
            if dik >= INF:
                continue
            di = dist[i]
            for j in range(n):
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
    return dist


def best_trip(dist, fish, home, start, stamina, held, target=None):
    """(best shoal value, netting order) over every order of the fish not yet held, from cell start with stamina,
    ending docked at home. fish: list of [cell, hue]; held: hues already in the shoal (in netting order).

    Depth-first in ascending fish index, each prefix scored before its extensions, strict comparisons (first wins
    ties). With a target, the order returned is the best score instead (value + stamina left, value >= target).
    """
    best, best_order = -1, []
    top, top_order = -1, None
    taken = set()
    order = []

    def visit(at, used, hues):
        nonlocal best, best_order, top, top_order
        back = used + dist[at][home]
        if back <= stamina:
            v = chain_value(hues)
            if v > best:
                best, best_order = v, list(order)
            if target is not None and v >= target and v + stamina - back > top:
                top, top_order = v + stamina - back, list(order)
        for i, (cell, hue) in enumerate(fish):
            if i in taken:
                continue
            nu = used + dist[at][cell]
            if nu + dist[cell][home] > stamina:
                continue
            taken.add(i)
            order.append(i)
            visit(cell, nu, hues + [hue])
            order.pop()
            taken.discard(i)

    visit(start, 0, list(held))
    if best < 0:
        return 0, []
    return best, (top_order if top_order is not None else best_order)


class Game(pc.PrismGame):
    GAME_ID, TITLE, HOW_TO_PLAY = GAME_ID, TITLE, HOW_TO_PLAY
    DIFFICULTY, DEFAULT_DIFFICULTY = DIFFICULTY, DEFAULT_DIFFICULTY
    FIELDS = ("current", "fish", "eels", "at", "stamina", "netted", "shoal", "moves", "target", "best", "plan")

    def setup(self):
        cfg = self.cfg
        size = cfg["size"]
        self.current = [[self.rng.randrange(4) for _ in range(size)] for _ in range(size)]
        home = self.home()
        cells = [i for i in range(size * size) if i != home]
        picks = [cells[i] for i in self.rng.sample(range(len(cells)), cfg["fish"] + cfg["eels"])]
        self.fish = [[cell, self.rng.randint(1, cfg["hues"])] for cell in picks[:cfg["fish"]]]
        self.eels = sorted(picks[cfg["fish"]:])
        self.restore()
        self.best, _ = best_trip(self.dist, self.fish, home, home, cfg["stamina"], [])
        self.target = max(1, (self.best * cfg["target_pct"] + PERCENT - 1) // PERCENT)
        self.plan = best_trip(self.dist, self.fish, home, home, cfg["stamina"], [], self.target)[1]
        self.at, self.stamina, self.netted, self.shoal, self.moves = home, cfg["stamina"], [], [], 0

    def home(self):
        return self.cfg["size"] // 2

    def restore(self):
        self.dist = distances(self.cfg["size"], self.current, set(self.eels))

    def shoal_hues(self):
        return [self.fish[i][1] for i in self.shoal]

    def rescore(self):
        """Shoal value while swimming or after a loss; a win adds the stamina left."""
        v = chain_value(self.shoal_hues())
        return v + self.stamina if self.won else v

    def check_rules(self):
        cfg, size = self.cfg, self.cfg["size"]
        n = size * size
        if (len(self.current) != size or any(len(row) != size or any(x not in range(4) for x in row)
                                             for row in self.current)):
            raise ValueError("shoal_lure save current grid is malformed")
        if len(self.fish) != cfg["fish"] or len(self.eels) != cfg["eels"]:
            raise ValueError("shoal_lure save has the wrong number of fish or eels")
        cells = [f[0] for f in self.fish] + list(self.eels)
        if (any(not pc.is_count(c) or c >= n or c == self.home() for c in cells) or len(set(cells)) != len(cells)
                or any(not pc.is_count(f[1]) or not 1 <= f[1] <= cfg["hues"] for f in self.fish)):
            raise ValueError("shoal_lure save fish or eels are out of range")
        if not pc.is_count(self.at) or self.at >= n or not pc.is_count(self.moves):
            raise ValueError("shoal_lure save lure position is out of range")
        if not pc.is_count(self.stamina) or self.moves > cfg["stamina"] or self.stamina > cfg["stamina"] - self.moves:
            raise ValueError("shoal_lure save stamina does not fit the moves made")  # every move costs 1 or more
        if (len(set(self.netted)) != len(self.netted) or any(not pc.is_count(i) or i >= cfg["fish"] for i in self.netted)
                or any(i not in self.netted for i in self.shoal) or len(set(self.shoal)) != len(self.shoal)):
            raise ValueError("shoal_lure save netted fish are not consistent")
        best, _ = best_trip(self.dist, self.fish, self.home(), self.home(), cfg["stamina"], [])
        if self.best != best or self.target != max(1, (best * cfg["target_pct"] + PERCENT - 1) // PERCENT):
            raise ValueError("shoal_lure save best or target does not match the grid")
        if self.won and (not self.over or self.at != self.home() or chain_value(self.shoal_hues()) < self.target):
            raise ValueError("shoal_lure save claims a win the shoal does not reach")

    def act(self, action):
        kind, d = action
        size, home = self.cfg["size"], self.home()
        if kind == "dock":
            if self.at != home:
                raise ValueError("dock only at the Skiff")
            if self.moves == 0:
                raise ValueError("swim first: the lure has not left the Skiff")
            v = chain_value(self.shoal_hues())
            won = v >= self.target
            self.score = v + (self.stamina if won else 0)
            self.finish(won)
            return f"docked with a shoal worth {v}"
        if kind == "net":
            hit = next((i for i, f in enumerate(self.fish) if f[0] == self.at and i not in self.netted), None)
            if hit is None:
                raise ValueError("no prism-fish here to net")
            self.netted.append(hit)
            self.shoal.append(hit)
            self.score = chain_value(self.shoal_hues())
            return f"netted a {'abc'[self.fish[hit][1] - 1]} fish"
        if kind != "move" or d not in range(4):
            raise ValueError("use n, e, s, w, net or dock")
        r, c = divmod(self.at, size)
        nr, nc = r + DIRS[d][0], c + DIRS[d][1]
        if not (0 <= nr < size and 0 <= nc < size):
            raise ValueError("the lure cannot leave the water")
        self.stamina -= step_cost(self.current, nr, nc, d)
        self.at = nr * size + nc
        self.moves += 1
        res = "swam " + DIR_NAMES[d]
        if self.at in self.eels and self.shoal:
            self.shoal = []
            res += ": an umbra eel scatters the shoal"
        self.score = chain_value(self.shoal_hues())
        if self.stamina < 0 or self.dist[self.at][home] > self.stamina:
            self.stamina = max(0, self.stamina)
            self.finish(False)
            return res + ": the line snaps"
        return res

    def toward(self, goal):
        """First move on a least-stamina eel-free path to goal (lowest direction code on ties)."""
        size = self.cfg["size"]
        r, c = divmod(self.at, size)
        best, best_d = INF, None
        for d, (dr, dc) in enumerate(DIRS):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < size and 0 <= nc < size):
                continue
            cell = nr * size + nc
            if cell in self.eels:
                continue
            cost = step_cost(self.current, nr, nc, d) + self.dist[cell][goal]
            if cost < best:
                best, best_d = cost, d
        return ("move", best_d)

    def next_from(self, plan):
        goal = next((self.fish[i][0] for i in plan if i not in self.netted), None)
        here = next((i for i in plan if i not in self.netted), None)
        if here is not None and self.fish[here][0] == self.at:
            return ("net", 0)
        if goal is None:
            return ("dock", 0) if self.at == self.home() and self.moves else self.toward(self.home())
        return self.toward(goal)

    def demo_action(self):
        return self.next_from(self.plan)

    def hint(self):
        """Best next move from here: the best-score trip over the fish not yet netted, else the biggest shoal."""
        left = [i for i in range(len(self.fish)) if i not in self.netted]
        sub = [self.fish[i] for i in left]
        _, order = best_trip(self.dist, sub, self.home(), self.at, self.stamina, self.shoal_hues(), self.target)
        return self.next_from([left[i] for i in order])

    def hint_text(self):
        kind, d = self.hint()
        return f"hint: {kind}" if kind != "move" else f"hint: swim {DIR_NAMES[d].lower()}"

    def render(self):
        size, home = self.cfg["size"], self.home()
        hues = {f[0]: "abc"[f[1] - 1] for i, f in enumerate(self.fish) if i not in self.netted}
        lines = [f"{TITLE} ({self.difficulty}, seed {self.seed}) stamina {self.stamina} shoal "
                 f"{chain_value(self.shoal_hues())} target {self.target}"]
        for r in range(size):
            row = []
            for c in range(size):
                i = r * size + c
                mark = "S" if i == home else "X" if i in self.eels else hues.get(i, ARROWS[self.current[r][c]])
                row.append(f"[{mark}]" if i == self.at else f" {mark} ")
            lines.append("".join(row))
        if self.over:
            lines.append(f"WON: the shoal glitters home, score {self.score}" if self.won else
                         f"LOST: score {self.score}")
        else:
            lines.append("moves: n e s w, net, dock, hint")
        return "\n".join(lines)

    @staticmethod
    def parse(line):
        word = line.strip().lower()
        if word in ("n", "e", "s", "w"):
            return ("move", "nesw".index(word))
        if word in ("net", "dock"):
            return (word, 0)
        raise ValueError("use n, e, s, w, net or dock")


def start(seed=0, difficulty=DEFAULT_DIFFICULTY):
    return Game(seed, difficulty)


if __name__ == "__main__":
    sys.exit(pc.main(Game))
