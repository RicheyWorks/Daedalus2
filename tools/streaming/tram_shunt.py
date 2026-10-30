# SPDX-License-Identifier: MIT
"""Tram Shunt (G566, disk-saver): marshal the quay tram wagons into order with two sidings.

Python dev tooling only; nothing here runs inside Unreal. Every census island (tools/world_census
output, read-only; up to six) loads one wagon on the quay tramway, numbered in label order, and
spare wagons pad the train to six. A seed jumbles the order in which the wagons stand on the
inbound line, reshuffling until the yardman's habit (below) falls short of par. The outbound line must take them in order 1, 2, 3 ...

Shunter Rosalind has two dead-end sidings, A and B. Only the front wagon of the inbound line and
the top wagon of each siding can move. A move takes one wagon from in, A or B to A, B or out.
Wagons never go back onto the inbound line, and the outbound line only takes the next number.
Get the whole train out in as few moves as possible.

The par is an exact breadth-first search over (wagons left inbound, siding A, siding B, next
wanted). The tests check it against an independent search. The trap is the yardman's habit:
send a wagon out if it can go, otherwise drop the front wagon onto the siding whose top is
the smallest wagon larger than it, else an empty siding, else A. It is shown as greedy_moves
(None if that habit jams the yard).

  verdict   smart     the train out in par moves,
            slow      the train out in more moves,
            jammed    wagons still in the yard.

  python tools/streaming/tram_shunt.py CENSUS.json [--seed N] [--moves inA,Aout,... | --auto] [--json]

Moves are FROM+TO with in, A, B, out (e.g. inA, AB, Bout). Deterministic, stdlib only, no clock.
Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-tram-shunt"
VERDICTS = ("smart", "slow", "jammed")
TRAIN = 6
MOVES = ("inout", "Aout", "Bout", "inA", "inB", "AB", "BA")
MOVE_RE = re.compile(r"^(in|A|B)(A|B|out)$")


class ShuntError(ValueError):
    pass


def step(state, mv):
    """New state or None. state = (inbound tuple front-first, A tuple bottom-first, B, next)."""
    inb, a, b, nxt = state
    src, dst = MOVE_RE.match(mv).groups()
    if src == dst:
        return None
    if src == "in":
        if not inb:
            return None
        w, inb = inb[0], inb[1:]
    elif src == "A":
        if not a:
            return None
        w, a = a[-1], a[:-1]
    else:
        if not b:
            return None
        w, b = b[-1], b[:-1]
    if dst == "out":
        if w != nxt:
            return None
        nxt += 1
    elif dst == "A":
        a = a + (w,)
    else:
        b = b + (w,)
    return (inb, a, b, nxt)


def solve(order):
    """(par, moves list) by BFS."""
    n = len(order)
    s0 = (tuple(order), (), (), 1)
    prev = {s0: None}
    q = deque([s0])
    while q:
        s = q.popleft()
        if s[3] == n + 1:
            path = []
            while prev[s] is not None:
                s, m = prev[s]
                path.append(m)
            return len(path), path[::-1]
        for m in MOVES:
            t = step(s, m)
            if t is not None and t not in prev:
                prev[t] = (s, m)
                q.append(t)
    raise ShuntError("the yard cannot marshal this train")


def greedy(order):
    """Moves used by the yardman's habit, or None if it jams."""
    s, n, count = (tuple(order), (), (), 1), len(order), 0
    while s[3] <= n:
        for m in ("inout", "Aout", "Bout"):
            t = step(s, m)
            if t is not None:
                s, count = t, count + 1
                break
        else:
            if not s[0]:
                return None
            w = s[0][0]
            fits = [(top, m) for top, m in ((s[1][-1] if s[1] else None, "inA"), (s[2][-1] if s[2] else None, "inB"))
                    if top is not None and top > w]
            if fits:
                m = min(fits)[1]
            elif not s[1]:
                m = "inA"
            elif not s[2]:
                m = "inB"
            else:
                m = "inA"
            s, count = step(s, m), count + 1
            if count > 200:
                return None
    return count


def train(census_doc, seed=0):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise ShuntError(str(e))
    isl = sorted(f"{w}:{s}" for w, il in worlds for s, _ in il)
    if not isl:
        raise ShuntError("census has no islands to load wagons")
    names = isl[:TRAIN] + [f"spare:{k}" for k in range(1, TRAIN - min(len(isl), TRAIN) + 1)]
    key = f"{census_doc.get('snapshot_date')}|{','.join(names)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    order = list(range(1, TRAIN + 1))
    for _ in range(100):
        rng.shuffle(order)
        g = greedy(order)
        if g is None or g > solve(order)[0]:
            break
    return names, tuple(order)


def play(census_doc, seed=0, moves=None, auto=False):
    names, order = train(census_doc, seed)
    par, plan = solve(order)
    r = {"format": FORMAT, "version": 1, "seed": seed,
         "wagons": {str(i + 1): l for i, l in enumerate(names)}, "inbound": list(order),
         "par": par, "greedy_moves": greedy(order)}
    if auto:
        moves = plan
    elif moves is None:
        r["verdict"] = None
        return r
    else:
        moves = [m.strip() for m in moves.split(",") if m.strip()]
    s, log = (order, (), (), 1), []
    for k, m in enumerate(moves, 1):
        if not MOVE_RE.match(m):
            raise ShuntError(f"move {k}: {m!r} is not FROM+TO with in, A, B, out")
        if s[3] > len(order):
            raise ShuntError(f"move {k}: the train is already out")
        t = step(s, m)
        if t is None:
            raise ShuntError(f"move {k}: {m} is not possible here")
        s = t
        log.append({"move": m, "in": list(s[0]), "A": list(s[1]), "B": list(s[2]), "out": s[3] - 1})
    done = s[3] > len(order)
    r.update({"moves": moves, "count": len(moves), "log": log, "out": s[3] - 1})
    r["verdict"] = ("smart" if len(moves) <= par else "slow") if done else "jammed"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise ShuntError(f"census: {e}")


def text(r):
    w = ", ".join(f"{k}={v}" for k, v in r["wagons"].items())
    lines = [f"tram shunt: wagons {w}; par {r['par']} moves (yardman's habit: {r['greedy_moves']}); seed {r['seed']}",
             "  inbound (front first): " + " ".join(map(str, r["inbound"]))]
    if r["verdict"]:
        for e in r["log"]:
            lines.append(f"  {e['move']:>5}  in {e['in']}  A {e['A']}  B {e['B']}  out {e['out']}")
        lines.append(f"verdict: {r['verdict']} ({r['count']} moves, {r['out']}/{len(r['inbound'])} out, par {r['par']})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tram Shunt: marshal census wagons with two sidings.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--moves", help="comma-separated moves like inA,Aout,inout")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.moves, a.auto)
    except ShuntError as e:
        print(f"tram_shunt: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
