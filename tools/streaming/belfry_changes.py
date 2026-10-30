# SPDX-License-Identifier: MIT
"""Belfry Changes (G565, disk-saver): ring the census bells in changes, lead each one, come round.

Python dev tooling only; nothing here runs inside Unreal. Every census island (tools/world_census
output, read-only; up to six) gives the harbour belfry one bell, numbered in label order, and
spare bells pad the ring to five. The tenor is the island bell with the largest RAM cost in the
G206 model. After a ragged practice the bells stand in a seeded jumbled row.

Each change swaps one or more neighbouring pairs of bells at once (the pairs may not overlap),
written as the 1-based places where each swapped pair starts: "1+3" swaps places 1-2 and 3-4.
The heavy tenor must rest for a change after every change in which it moves. Ringer Agatha
wants every island bell to have rung at lead (place 1) at some point, and the ring to finish in
rounds (1 2 3 ...), in as few changes as possible.

The par is an exact breadth-first search over (row, island bells led, tenor resting). The tests
check it against an independent search. The single_swap_par shows how many changes it would
take if only one pair could swap at a time.

  verdict   rung        rounds with every island bell led, in par changes,
            clattered   the same, in more changes,
            unfinished  not in rounds, or an island bell never led.

  python tools/streaming/belfry_changes.py CENSUS.json [--seed N] [--changes 1+3,2,... | --auto] [--json]

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

FORMAT = "daedalus-belfry-changes"
VERDICTS = ("rung", "clattered", "unfinished")
MAX_BELLS = 6
MIN_BELLS = 5


class BellError(ValueError):
    pass


def all_changes(n, single=False):
    """Every legal change: non-empty sets of non-overlapping pair starts (0-based)."""
    out = []

    def rec(i, cur):
        if i >= n - 1:
            if cur:
                out.append(tuple(cur))
            return
        rec(i + 1, cur)
        if not single or not cur:
            rec(i + 2, cur + [i])

    rec(0, [])
    return sorted(out)


def apply(row, change):
    r = list(row)
    for p in change:
        r[p], r[p + 1] = r[p + 1], r[p]
    return tuple(r)


def ring(census_doc, seed=0):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise BellError(str(e))
    isl = sorted((f"{w}:{s}", a) for w, il in worlds for s, a in il)
    if not isl:
        raise BellError("census has no islands to cast bells")
    isl = isl[:MAX_BELLS]
    names = [l for l, _ in isl] + [f"spare:{k}" for k in range(1, MIN_BELLS - len(isl) + 1)]
    islands = frozenset(range(1, len(isl) + 1))
    tenor = 1 + max(range(len(isl)), key=lambda i: (cb.island_cost(isl[i][1])[0], -i))
    key = f"{census_doc.get('snapshot_date')}|{','.join(names)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    rounds = tuple(range(1, len(names) + 1))
    row = list(rounds)
    while tuple(row) == rounds:
        rng.shuffle(row)
    return names, islands, tenor, tuple(row)


def solve(start, islands, tenor, single=False):
    """(par, list of changes) by BFS over (row, led-mask, tenor resting)."""
    n = len(start)
    rounds = tuple(range(1, n + 1))
    changes = all_changes(n, single)
    bit = {b: 1 << (b - 1) for b in islands}
    full = sum(bit.values())
    led0 = bit.get(start[0], 0)
    s0 = (start, led0, False)
    prev = {s0: None}
    q = deque([s0])
    while q:
        s = q.popleft()
        row, led, rest = s
        if row == rounds and led == full:
            path = []
            while prev[s] is not None:
                s, c = prev[s]
                path.append(c)
            return len(path), path[::-1]
        ti = row.index(tenor)
        for c in changes:
            moves = any(p == ti or p + 1 == ti for p in c)
            if rest and moves:
                continue
            nr = apply(row, c)
            t = (nr, led | bit.get(nr[0], 0), moves)
            if t not in prev:
                prev[t] = (s, c)
                q.append(t)
    raise BellError("no way to come round")


def parse_changes(s, n):
    out = []
    for k, tok in enumerate([t.strip() for t in s.split(",") if t.strip()], 1):
        try:
            places = sorted(int(x) for x in tok.split("+"))
        except ValueError:
            raise BellError(f"change {k}: {tok!r} is not places like 1+3")
        if not all(1 <= p <= n - 1 for p in places):
            raise BellError(f"change {k}: places run 1..{n - 1}")
        if any(b - a < 2 for a, b in zip(places, places[1:])):
            raise BellError(f"change {k}: swapped pairs overlap")
        out.append(tuple(p - 1 for p in places))
    return out


def play(census_doc, seed=0, changes=None, auto=False):
    names, islands, tenor, start = ring(census_doc, seed)
    par, plan = solve(start, islands, tenor)
    r = {"format": FORMAT, "version": 1, "seed": seed, "bells": {str(i + 1): l for i, l in enumerate(names)},
         "tenor": tenor, "start": list(start), "par": par,
         "single_swap_par": solve(start, islands, tenor, single=True)[0]}
    if auto:
        changes = plan
    elif changes is None:
        r["verdict"] = None
        return r
    else:
        changes = parse_changes(changes, len(start))
    row, led, rest, rows = start, {start[0]} & islands, False, []
    for k, c in enumerate(changes, 1):
        moves = any(p == row.index(tenor) or p + 1 == row.index(tenor) for p in c)
        if rest and moves:
            raise BellError(f"change {k}: the tenor (bell {tenor}) must rest this change")
        row, rest = apply(row, c), moves
        led |= {row[0]} & islands
        rows.append(list(row))
    done = row == tuple(range(1, len(start) + 1)) and led == islands
    r.update({"changes": ["+".join(str(p + 1) for p in c) for c in changes], "rows": rows,
              "count": len(changes), "led": sorted(led), "final": list(row)})
    r["verdict"] = ("rung" if len(changes) <= par else "clattered") if done else "unfinished"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise BellError(f"census: {e}")


def text(r):
    bells = ", ".join(f"{k}={v}" for k, v in r["bells"].items())
    lines = [f"belfry changes: bells {bells}; tenor {r['tenor']}; par {r['par']} changes "
             f"(one pair at a time: {r['single_swap_par']}); seed {r['seed']}",
             "  start " + " ".join(map(str, r["start"]))]
    if r["verdict"]:
        for c, row in zip(r["changes"], r["rows"]):
            lines.append(f"  {c:>5}  " + " ".join(map(str, row)))
        lines.append(f"verdict: {r['verdict']} ({r['count']} changes, led {r['led']}, par {r['par']})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Belfry Changes: ring the census bells round.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--changes", help="comma-separated changes, each the places that swap, e.g. 1+3,2")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.changes, a.auto)
    except BellError as e:
        print(f"belfry_changes: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
