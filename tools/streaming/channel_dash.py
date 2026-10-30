# SPDX-License-Identifier: MIT
"""Channel Dash (G561, disk-saver): row a dinghy across lanes of drifting barges.

Python dev tooling only; nothing here runs inside Unreal. The DiskSaver channel has one barge
lane for each census island (tools/world_census output, read-only; up to five, padded to three
with spare lanes). A seed fills each lane with barges that drift east or west one or two cells
every tick and wrap round the 9-cell channel. Courier Isadora starts on the near quay (bottom)
and must reach the dock on the far quay (top) without a barge ever sitting on her cell.

Each tick she moves U, D, L, R or waits (.), then the barges drift. She is swamped if a barge is
on her cell after that tick. The quays are always clear. The par is the fewest ticks, found by
an exact breadth-first search over (row, column, tick mod the lanes' period). The tests check
it against an independent search that steps real time with no modular trick.

  verdict   swift    on the dock in par ticks,
            safe     on the dock in more ticks,
            swamped  hit by a barge, or not on the dock yet.

  python tools/streaming/channel_dash.py CENSUS.json [--seed N] [--moves UU.LU... | --auto] [--json]

Deterministic, stdlib only, no clock. Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-channel-dash"
VERDICTS = ("swift", "safe", "swamped")
WIDTH = 9
MAX_LANES = 5
MIN_LANES = 3
STEP = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1), ".": (0, 0)}


class DashError(ValueError):
    pass


def lanes_for(census_doc, seed=0):
    """(lane labels top to bottom, [(cells at tick 0, velocity)], dock column, start column)."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise DashError(str(e))
    isl = sorted((f"{w}:{s}", a) for w, il in worlds for s, a in il)
    if not isl:
        raise DashError("census has no islands for the channel")
    isl = isl[:MAX_LANES]
    isl += [(f"lane:{k}", 0) for k in range(1, MIN_LANES - len(isl) + 1)]
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in isl)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    for _ in range(200):
        lanes = []
        for _, a in isl:
            cells = set()
            for _ in range(1 + a % 3):
                start, length = rng.randrange(WIDTH), rng.randint(1, 3)
                cells |= {(start + k) % WIDTH for k in range(length)}
            if len(cells) > WIDTH - 3:
                cells = set(sorted(cells)[:WIDTH - 3])
            lanes.append((frozenset(cells), rng.choice((-2, -1, 1, 2))))
        dock, start = rng.randrange(WIDTH), rng.randrange(WIDTH)
        if solve(lanes, dock, start)[0] is not None:
            return [l for l, _ in isl], lanes, dock, start
    raise DashError("could not lay out a channel for this seed")


def busy(lanes, row, col, t):
    """True if a barge sits on (row, col) at tick t. Row 0 = far quay, row len+1 = near quay."""
    if row == 0 or row == len(lanes) + 1:
        return False
    cells, v = lanes[row - 1]
    return (col - v * t) % WIDTH in cells


def solve(lanes, dock, start):
    """(par, moves) by BFS over (row, col, t mod WIDTH); every velocity divides into WIDTH ticks."""
    home = len(lanes) + 1
    s0 = (home, start, 0)
    prev = {s0: None}
    q = deque([s0])
    while q:
        s = q.popleft()
        r, c, t = s
        if r == 0 and c == dock:
            path = []
            while prev[s] is not None:
                s, m = prev[s]
                path.append(m)
            return len(path), "".join(reversed(path))
        for m, (dr, dc) in STEP.items():
            nr, nc = r + dr, c + dc
            if not (0 <= nr <= home and 0 <= nc < WIDTH):
                continue
            nt = (t + 1) % WIDTH
            if busy(lanes, nr, nc, nt):
                continue
            k = (nr, nc, nt)
            if k not in prev:
                prev[k] = (s, m)
                q.append(k)
    return None, None


def draw(lanes, dock, t, pos=None):
    rows = ["".join("D" if c == dock else "=" for c in range(WIDTH))]
    for i in range(len(lanes)):
        rows.append("".join("#" if busy(lanes, i + 1, c, t) else "~" for c in range(WIDTH)))
    rows.append("=" * WIDTH)
    if pos is not None:
        r, c = pos
        rows[r] = rows[r][:c] + "@" + rows[r][c + 1:]
    return rows


def play(census_doc, seed=0, moves=None, auto=False):
    labels, lanes, dock, start = lanes_for(census_doc, seed)
    par, plan = solve(lanes, dock, start)
    home = len(lanes) + 1
    r = {"format": FORMAT, "version": 1, "seed": seed, "lanes": labels, "par": par,
         "velocities": [v for _, v in lanes], "dock": dock, "start_col": start,
         "start": draw(lanes, dock, 0, (home, start))}
    if auto:
        moves = plan
    if moves is None:
        r["verdict"] = None
        return r
    moves = moves.strip().upper()
    pos, hit = (home, start), None
    for t, m in enumerate(moves, 1):
        if m not in STEP:
            raise DashError(f"tick {t}: {m!r} is not U, D, L, R or .")
        if pos == (0, dock):
            raise DashError(f"tick {t}: already on the dock")
        nr, nc = pos[0] + STEP[m][0], pos[1] + STEP[m][1]
        if not (0 <= nr <= home and 0 <= nc < WIDTH):
            raise DashError(f"tick {t}: {m} leaves the channel")
        pos = (nr, nc)
        if busy(lanes, nr, nc, t):
            hit = t
            break
    used = hit if hit else len(moves)
    r.update({"moves": moves[:used], "ticks": used, "hit_tick": hit, "row": pos[0], "col": pos[1],
              "final": draw(lanes, dock, used, pos)})
    if hit is None and pos == (0, dock):
        r["verdict"] = "swift" if used <= par else "safe"
    else:
        r["verdict"] = "swamped"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise DashError(f"census: {e}")


def text(r):
    lines = [f"channel dash: {len(r['lanes'])} lanes ({', '.join(r['lanes'])}), par {r['par']} ticks; seed {r['seed']}"]
    lines += ["  " + row for row in (r["final"] if r["verdict"] else r["start"])]
    if r["verdict"]:
        extra = f"; swamped at tick {r['hit_tick']}" if r["hit_tick"] else ""
        lines.append(f"verdict: {r['verdict']} ({r['ticks']} ticks, par {r['par']}{extra})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Channel Dash: cross lanes of drifting barges.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--moves", help="one of U D L R . per tick")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.moves, a.auto)
    except DashError as e:
        print(f"channel_dash: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
