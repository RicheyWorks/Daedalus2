# SPDX-License-Identifier: MIT
"""Chainmail Weave rules reference (original Prismheart minigame, hephaestus) and golden-vector writer.

Rules authority for DaedalusChainmailWeaveCore.h. A seeded 7x7 mail grid in the Hephaestus Island armory: some rings
are rusted. Place links one at a time; win by joining the left edge to the right edge with orthogonally adjacent
links before the link budget runs out. After each placement that does not win, rust spreads to one seeded empty ring.
All randomness is CPython random seeded "chainmail|<seed>" (DaedalusPyRandomCore.h in C++). Integer only.
`python chainmail_weave_ref.py > chainmail_weave_golden.txt`; `--check chainmail_weave_golden.txt` verifies it.
"""
import random
import sys

N = 7
CELLS = N * N
EMPTY, RUST, LINK = 0, 1, 2
RUST_DRAWS = 9        # initial rust draws (duplicates land on the same ring)
MAX_ROLLS = 20        # rerolls until the grid is crossable; after that the rust is cleared
SLACK = 3             # budget = cheapest crossing + SLACK
INF = 10 ** 6
PLAYING, WON, LOST = range(3)
STATE = ["PLAYING", "WON", "LOST"]
OK, BAD_CELL, OCCUPIED, GAME_OVER = range(4)
NO_LOSS, OUT_OF_LINKS, BLOCKED = range(3)
REASON = ["NONE", "OUT_OF_LINKS", "BLOCKED"]
STATUS = ["OK", "BAD_CELL", "OCCUPIED", "GAME_OVER"]

def nbrs(i):
    r, c = divmod(i, N)
    if r > 0: yield i - N
    if r < N - 1: yield i + N
    if c > 0: yield i - 1
    if c < N - 1: yield i + 1

def cost(g, i):
    return INF if g[i] == RUST else (0 if g[i] == LINK else 1)

def dist_from(g, col):
    """Cheapest cost (empty rings still to link, counting the cell itself) from edge column `col` to each cell."""
    d = [INF] * CELLS
    for r in range(N):
        i = r * N + col
        d[i] = cost(g, i)
    changed = True
    while changed:
        changed = False
        for i in range(CELLS):
            if g[i] == RUST:
                continue
            for j in nbrs(i):
                if d[j] < INF and d[j] + cost(g, i) < d[i]:
                    d[i] = d[j] + cost(g, i)
                    changed = True
    return d

def crossing(g):
    """Cheapest number of empty rings to link for a left-right crossing (INF if none)."""
    d = dist_from(g, 0)
    return min(d[r * N + N - 1] for r in range(N))

def demo_cell(g):
    """The hint: among empty rings on a cheapest crossing, the chokepoint (the one whose rusting would raise the
    cheapest crossing most; a ring whose loss blocks every crossing counts highest), earliest row-major on ties.
    -1 when no crossing exists."""
    a, b = dist_from(g, 0), dist_from(g, N - 1)
    best = crossing(g)
    if best >= INF:
        return -1
    pick, harm = -1, -1
    for i in range(CELLS):
        if g[i] == EMPTY and a[i] + b[i] - cost(g, i) == best:
            h = list(g)
            h[i] = RUST
            hv = crossing(h)
            if hv > harm:
                pick, harm = i, hv
    return pick

class Game:
    def __init__(self, seed):
        self.r = random.Random("chainmail|" + seed)
        for _ in range(MAX_ROLLS):
            g = [EMPTY] * CELLS
            for _ in range(RUST_DRAWS):
                g[self.r.randrange(CELLS)] = RUST
            if crossing(g) < INF:
                break
        else:
            g = [EMPTY] * CELLS
        self.g = g
        self.budget = crossing(g) + SLACK
        self.state = PLAYING
        self.placed = 0
        self.reason = NO_LOSS

    def won(self):
        d = dist_from([x if x == LINK else RUST for x in self.g], 0)
        return any(d[r * N + N - 1] < INF for r in range(N))

    def place(self, i):
        if self.state != PLAYING:
            return GAME_OVER
        if not (0 <= i < CELLS):
            return BAD_CELL
        if self.g[i] != EMPTY:
            return OCCUPIED
        self.g[i] = LINK
        self.budget -= 1
        self.placed += 1
        if self.won():
            self.state = WON
            return OK
        empties = [k for k in range(CELLS) if self.g[k] == EMPTY]
        if empties:
            self.g[empties[self.r.randrange(len(empties))]] = RUST
        need = crossing(self.g)
        if need == INF:
            self.state, self.reason = LOST, BLOCKED
        elif self.budget <= 0 or need > self.budget:
            self.state, self.reason = LOST, OUT_OF_LINKS
        return OK

    def score(self):
        return 10 + 10 * self.budget if self.state == WON else 0

    def demo(self):
        return demo_cell(self.g)

    def text(self):
        return "".join(".#L"[x] for x in self.g)

def seeds():
    out = ["", "0", "1", "armory", "Hephaestus Island", "2026-10-30", "chainmail|nested", "z" * 40]
    r = random.Random(62351)
    for _ in range(300):
        out.append("".join(r.choice("abcdefghijklmnopqrstuvwxyz0123456789 -_") for _ in range(r.randint(1, 16))))
    return out

def write(f):
    f.write("# Chainmail Weave golden vectors from chainmail_weave_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# S <len> <seed> | N <grid 49 chars .#L> <budget> | P <cell> <status> <grid> <budget> <state> <reason> <score> <demo>\n")
    pick = random.Random(62351 + 1)
    for s in seeds():
        g = Game(s)
        f.write("S %d %s\n" % (len(s), s))
        f.write("N %s %d\n" % (g.text(), g.budget))
        style = pick.randrange(3)  # 0 demo player, 1 random player, 2 mixed with bad moves
        for _ in range(60):
            if style == 0:
                mv = g.demo()
            elif style == 1:
                mv = pick.randrange(CELLS)
            else:
                mv = pick.choice([g.demo(), g.demo(), pick.randrange(CELLS), -1, CELLS])
            st = g.place(mv)
            f.write("P %d %s %s %d %s %s %d %d\n" % (mv, STATUS[st], g.text(), g.budget, STATE[g.state], REASON[g.reason], g.score(), g.demo()))
            if g.state != PLAYING and pick.random() < 0.7:
                break

if __name__ == "__main__":
    import io
    buf = io.StringIO()
    write(buf)
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        with open(sys.argv[2], newline="") as gf:
            same = gf.read() == buf.getvalue()
        print("golden current" if same else "golden STALE")
        sys.exit(0 if same else 1)
    sys.stdout.write(buf.getvalue())
