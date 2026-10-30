# SPDX-License-Identifier: MIT
"""Quayside Shove (G558, disk-saver): push each island's crate onto its berth mark.

Python dev tooling only; nothing here runs inside Unreal. Every island in a world census
(tools/world_census output, read-only) ships one crate (up to three, the islands with the
largest RAM cost in the G206 model). A seed lays out a walled 7x7 quay yard with a few stacked
bollards, chalks one berth mark per crate, and scatters the crates by pulling them backwards
off the marks, so every yard is solvable. Yardmaster Hamish walks the yard and can only push a
crate, never pull it, and only one at a time. Get every crate onto a mark in as few steps as
possible.

The par is the fewest steps (walks and pushes both count), found by an exact breadth-first
search over (Hamish, crate cells). The tests check it against an independent layered search.

  verdict   tidy      every crate on a mark in par steps,
            shuffled  every crate on a mark in more steps,
            stuck     crates still off the marks (deadlocked says whether the yard can
                      still be cleared from here).

  python tools/streaming/quayside_shove.py CENSUS.json [--seed N] [--moves UDLR... | --auto] [--json]

Map: # wall, . mark, $ crate, * crate on a mark, @ Hamish, + Hamish on a mark.
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

FORMAT = "daedalus-quayside-shove"
VERDICTS = ("tidy", "shuffled", "stuck")
SIZE = 7
MAX_CRATES = 3
DIRS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


class ShoveError(ValueError):
    pass


def crates_for(census_doc):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise ShoveError(str(e))
    isl = [(f"{w}:{s}", cb.island_cost(a)[0]) for w, il in worlds for s, a in il]
    if not isl:
        raise ShoveError("census has no islands to ship")
    isl.sort(key=lambda t: (-t[1], t[0]))
    return sorted(l for l, _ in isl[:MAX_CRATES])


def step(pos, d):
    return (pos[0] + DIRS[d][0], pos[1] + DIRS[d][1])


def move(walls, player, crates, d):
    """(player, crates) after one step, or None if blocked."""
    nxt = step(player, d)
    if nxt in walls:
        return None
    if nxt in crates:
        beyond = step(nxt, d)
        if beyond in walls or beyond in crates:
            return None
        crates = frozenset(crates - {nxt} | {beyond})
    return nxt, crates


def solve(walls, marks, player, crates):
    """(par, moves string) or (None, None) when the yard cannot be cleared."""
    start = (player, frozenset(crates))
    prev = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        if s[1] == marks:
            path = []
            while prev[s] is not None:
                s, d = prev[s]
                path.append(d)
            return len(path), "".join(reversed(path))
        for d in "UDLR":
            t = move(walls, s[0], s[1], d)
            if t is not None and t not in prev:
                prev[t] = (s, d)
                q.append(t)
    return None, None


def yard(census_doc, seed=0):
    labels = crates_for(census_doc)
    key = f"{census_doc.get('snapshot_date')}|{','.join(labels)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    border = {(r, c) for r in range(SIZE) for c in range(SIZE) if r in (0, SIZE - 1) or c in (0, SIZE - 1)}
    inner = sorted({(r, c) for r in range(SIZE) for c in range(SIZE)} - border)
    for _ in range(200):
        walls = set(border) | set(rng.sample(inner, rng.randint(2, 5)))
        floor = [p for p in inner if p not in walls]
        marks = frozenset(rng.sample(floor, len(labels)))
        crates = set(marks)
        player = rng.choice([p for p in floor if p not in crates])
        for _ in range(60):
            d = rng.choice("UDLR")
            back = step(player, {"U": "D", "D": "U", "L": "R", "R": "L"}[d])
            nxt = step(player, d)
            if nxt in walls or nxt in crates:
                continue
            if back in crates and rng.random() < 0.7:
                crates = (crates - {back}) | {player}
            player = nxt
        crates = frozenset(crates)
        if crates == marks:
            continue
        par, plan = solve(frozenset(walls), marks, player, crates)
        if par is not None and par >= 6:
            return {"labels": labels, "walls": frozenset(walls), "marks": marks,
                    "player": player, "crates": crates, "par": par, "plan": plan}
    raise ShoveError("could not lay out a yard for this seed")


def draw(walls, marks, player, crates):
    rows = []
    for r in range(SIZE):
        row = ""
        for c in range(SIZE):
            p = (r, c)
            if p in walls:
                row += "#"
            elif p == player:
                row += "+" if p in marks else "@"
            elif p in crates:
                row += "*" if p in marks else "$"
            else:
                row += "." if p in marks else " "
        rows.append(row.rstrip())
    return rows


def play(census_doc, seed=0, moves=None, auto=False):
    y = yard(census_doc, seed)
    r = {"format": FORMAT, "version": 1, "seed": seed, "crates": y["labels"], "par": y["par"],
         "start": draw(y["walls"], y["marks"], y["player"], y["crates"])}
    if auto:
        moves = y["plan"]
    if moves is None:
        r["verdict"] = None
        return r
    moves = moves.strip().upper()
    player, crates, pushes = y["player"], y["crates"], 0
    for i, d in enumerate(moves, 1):
        if d not in DIRS:
            raise ShoveError(f"step {i}: {d!r} is not U, D, L or R")
        if crates == y["marks"]:
            raise ShoveError(f"step {i}: the yard is already clear")
        t = move(y["walls"], player, crates, d)
        if t is None:
            raise ShoveError(f"step {i}: {d} is blocked")
        pushes += t[1] != crates
        player, crates = t
    on = len(crates & y["marks"])
    r.update({"moves": moves, "steps": len(moves), "pushes": pushes, "on_marks": on,
              "final": draw(y["walls"], y["marks"], player, crates)})
    if crates == y["marks"]:
        r["verdict"] = "tidy" if len(moves) <= y["par"] else "shuffled"
        r["deadlocked"] = False
    else:
        r["verdict"] = "stuck"
        r["deadlocked"] = solve(y["walls"], y["marks"], player, crates)[0] is None
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise ShoveError(f"census: {e}")


def text(r):
    lines = [f"quayside shove: {len(r['crates'])} crates ({', '.join(r['crates'])}), par {r['par']} steps; seed {r['seed']}"]
    lines += ["  " + row for row in (r["final"] if r["verdict"] else r["start"])]
    if r["verdict"]:
        extra = "; deadlocked" if r["deadlocked"] else ""
        lines.append(f"verdict: {r['verdict']} ({r['steps']} steps, {r['pushes']} pushes, "
                     f"{r['on_marks']}/{len(r['crates'])} on marks, par {r['par']}{extra})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Quayside Shove: a crate-pushing yard over the census.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--moves", help="steps as a string of U D L R")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.moves, a.auto)
    except ShoveError as e:
        print(f"quayside_shove: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
