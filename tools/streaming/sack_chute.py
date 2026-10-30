# SPDX-License-Identifier: MIT
"""Sack Chute (G559, disk-saver): a solitaire sowing game. Bank every sack in the hold.

Python dev tooling only; nothing here runs inside Unreal. Every island in a world census
(tools/world_census output, read-only) is a bin on the loading chute, up to six; seeded spare
bins pad the chute to at least four. A seed fills each bin with sacks (twelve at most in all).
The chute runs bin 1 -> bin N -> the hold, then loops back to bin 1.

A move picks up every sack in one bin and sows them one at a time into the bins after it,
dropping one into the hold each time the sowing passes it, and carrying on round the loop.
Hold Master Peregrine wants every sack in the hold in as few moves as possible.

Every move either banks a sack or pushes sacks towards the hold, so a game always ends. The par
is the fewest moves (exact breadth-first search), checked in the tests against an independent
memoised recursion. The trap is "always sow the bin nearest the hold", shown as greedy_moves.

  verdict   stowed   every sack in the hold in par moves,
            slow     every sack in the hold in more moves,
            loose    sacks still in the bins.

  python tools/streaming/sack_chute.py CENSUS.json [--seed N] [--moves 3,1,4 | --auto] [--json]

Bins are numbered from 1. Deterministic, stdlib only, no clock. Exit 0 = printed or graded,
2 = refusal.
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

FORMAT = "daedalus-sack-chute"
VERDICTS = ("stowed", "slow", "loose")
MAX_BINS = 6
MIN_BINS = 4
MAX_SACKS = 12


class ChuteError(ValueError):
    pass


def sow(bins, i):
    """(new bins tuple, sacks banked) after sowing bin i (0-based)."""
    b = list(bins)
    n, k = len(b), b[i]
    if k == 0:
        raise ChuteError(f"bin {i + 1} is empty")
    b[i] = 0
    pos, banked = i, 0
    for _ in range(k):
        pos = (pos + 1) % (n + 1)
        if pos == n:
            banked += 1
        else:
            b[pos] += 1
    return tuple(b), banked


def solve(bins):
    """(par, list of 0-based moves) by BFS to the empty chute."""
    start = tuple(bins)
    goal = tuple(0 for _ in bins)
    prev = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        if s == goal:
            path = []
            while prev[s] is not None:
                s, i = prev[s]
                path.append(i)
            return len(path), path[::-1]
        for i, k in enumerate(s):
            if k:
                t = sow(s, i)[0]
                if t not in prev:
                    prev[t] = (s, i)
                    q.append(t)
    raise ChuteError("chute cannot be cleared")


def greedy(bins):
    """Moves used by 'always sow the non-empty bin nearest the hold'."""
    s, n = tuple(bins), 0
    while any(s):
        i = max(j for j, k in enumerate(s) if k)
        s = sow(s, i)[0]
        n += 1
    return n


def chute(census_doc, seed=0):
    """(bin labels, sack counts)."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise ChuteError(str(e))
    isl = sorted((f"{w}:{s}", a) for w, il in worlds for s, a in il)
    if not isl:
        raise ChuteError("census has no islands to load")
    if len(isl) > MAX_BINS:
        raise ChuteError(f"more than {MAX_BINS} islands")
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in isl)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    labels = [l for l, _ in isl] + [f"spare:{k}" for k in range(1, MIN_BINS - len(isl) + 1)]
    assets = [a for _, a in isl] + [0] * (len(labels) - len(isl))
    sacks = [1 + (a + rng.randrange(3)) % 3 for a in assets]
    while sum(sacks) > MAX_SACKS:
        j = max(range(len(sacks)), key=lambda x: (sacks[x], x))
        sacks[j] -= 1
    return labels, tuple(sacks)


def parse_moves(s, n):
    out = []
    for tok in [t.strip() for t in s.split(",") if t.strip()]:
        if not tok.isdigit() or not 1 <= int(tok) <= n:
            raise ChuteError(f"no bin {tok!r} (bins are 1..{n})")
        out.append(int(tok) - 1)
    return out


def play(census_doc, seed=0, moves=None, auto=False):
    labels, sacks = chute(census_doc, seed)
    par, plan = solve(sacks)
    r = {"format": FORMAT, "version": 1, "seed": seed, "bins": labels, "sacks": list(sacks),
         "total": sum(sacks), "par": par, "greedy_moves": greedy(sacks)}
    if auto:
        moves = plan
    elif moves is None:
        r["verdict"] = None
        return r
    else:
        moves = parse_moves(moves, len(labels))
    s, log, held = sacks, [], 0
    for step, i in enumerate(moves, 1):
        if not any(s):
            raise ChuteError(f"move {step}: the chute is already clear")
        if s[i] == 0:
            raise ChuteError(f"move {step}: bin {i + 1} is empty")
        s, b = sow(s, i)
        held += b
        log.append({"move": step, "bin": i + 1, "banked": b, "after": list(s)})
    r.update({"moves": [i + 1 for i in moves], "log": log, "in_hold": held, "left": list(s)})
    if any(s):
        r["verdict"] = "loose"
    else:
        r["verdict"] = "stowed" if len(moves) <= par else "slow"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise ChuteError(f"census: {e}")


def text(r):
    lines = [f"sack chute: {r['total']} sacks in {len(r['bins'])} bins, par {r['par']} moves "
             f"(nearest-the-hold habit: {r['greedy_moves']}); seed {r['seed']}"]
    for k, (l, n) in enumerate(zip(r["bins"], r["sacks"]), 1):
        lines.append(f"  bin {k} {l}: {n}")
    if r["verdict"]:
        for e in r["log"]:
            lines.append(f"  {e['move']}. sow bin {e['bin']}: +{e['banked']} to hold -> {e['after']}")
        lines.append(f"verdict: {r['verdict']} ({len(r['moves'])} moves, {r['in_hold']}/{r['total']} in hold, par {r['par']})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sack Chute: a solitaire sowing game over the census.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--moves", help="comma-separated bin numbers (1-based)")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.moves, a.auto)
    except ChuteError as e:
        print(f"sack_chute: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
