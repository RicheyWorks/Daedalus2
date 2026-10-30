# SPDX-License-Identifier: MIT
"""Rope Run (G564, disk-saver): draw one mooring rope across the quay through the best cleats.

Python dev tooling only; nothing here runs inside Unreal. A seed lays out a 5x6 quay with a few
stacked crates, a bollard where the rope starts (S) and the dock post where it must end (D).
Every census island (tools/world_census output, read-only; up to five) has a brass cleat on the
quay worth 3 + its asset count mod 3; every other open square has an iron ring worth 1.
Ropewalker Theodora lays the rope square by square (N, S, E, W). It may never cross itself or
pass a crate, and it must finish on the dock post. Each cleat or ring it passes holds it fast.

The score is the total grip of every square the rope covers, start and dock included. The par
is the best score over every possible rope (an exact search over simple paths), checked in the
tests against an independent recursive search. The trap is always heading for the best
neighbouring square, shown as greedy_grip (0 if that habit strands the rope).

  verdict   taut     the rope reaches the dock with par grip,
            slack    it reaches the dock with less,
            loose    it ends short of the dock.

  python tools/streaming/rope_run.py CENSUS.json [--seed N] [--route EESN... | --auto] [--json]

Map: # crate, S start, D dock, digits = grip. Deterministic, stdlib only, no clock.
Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-rope-run"
VERDICTS = ("taut", "slack", "loose")
ROWS, COLS = 5, 6
MAX_CLEATS = 5
STEP = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


class RopeError(ValueError):
    pass


def neighbours(cell, open_cells):
    r, c = cell
    for d in "NSEW":
        n = (r + STEP[d][0], c + STEP[d][1])
        if n in open_cells:
            yield d, n


def solve(grip, start, dock):
    """(par, route) by exhaustive search over simple paths start -> dock."""
    open_cells = set(grip)
    best = [-1, ""]
    seen = {start}

    def dfs(cell, score, route):
        if cell == dock:
            if score > best[0]:
                best[0], best[1] = score, route
            return
        for d, n in neighbours(cell, open_cells):
            if n not in seen:
                seen.add(n)
                dfs(n, score + grip[n], route + d)
                seen.discard(n)

    dfs(start, grip[start], "")
    return (best[0], best[1]) if best[0] >= 0 else (None, None)


def greedy(grip, start, dock):
    """Always step to the unvisited neighbour with the most grip (ties N, S, E, W); 0 if stranded."""
    open_cells = set(grip)
    cell, seen, score = start, {start}, grip[start]
    while cell != dock:
        opts = [(grip[n], -"NSEW".index(d), n) for d, n in neighbours(cell, open_cells) if n not in seen]
        if not opts:
            return 0
        _, _, cell = max(opts)
        seen.add(cell)
        score += grip[cell]
    return score


def quay(census_doc, seed=0):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise RopeError(str(e))
    isl = sorted((f"{w}:{s}", a) for w, il in worlds for s, a in il)
    if not isl:
        raise RopeError("census has no islands to cleat")
    isl = isl[:MAX_CLEATS]
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in isl)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    cells = [(r, c) for r in range(ROWS) for c in range(COLS)]
    for _ in range(100):
        crates = set(rng.sample(cells, rng.randint(3, 5)))
        free = [p for p in cells if p not in crates]
        pick = rng.sample(free, len(isl) + 2)
        start, dock, cleats = pick[0], pick[1], pick[2:]
        grip = {p: 1 for p in free}
        for p, (_, a) in zip(cleats, isl):
            grip[p] = 3 + a % 3
        par, route = solve(grip, start, dock)
        if par is not None and len(route) >= 4:
            return {"labels": [l for l, _ in isl], "cleats": cleats, "crates": crates, "grip": grip,
                    "start": start, "dock": dock, "par": par, "route": route}
    raise RopeError("could not lay out a quay for this seed")


def draw(q, path=()):
    on = set(path)
    rows = []
    for r in range(ROWS):
        row = ""
        for c in range(COLS):
            p = (r, c)
            if p in q["crates"]:
                row += "#"
            elif p == q["start"]:
                row += "S"
            elif p == q["dock"]:
                row += "D"
            elif p in on:
                row += "*"
            else:
                row += str(q["grip"][p])
        rows.append(row)
    return rows


def play(census_doc, seed=0, route=None, auto=False):
    q = quay(census_doc, seed)
    r = {"format": FORMAT, "version": 1, "seed": seed, "cleats": q["labels"], "par": q["par"],
         "greedy_grip": greedy(q["grip"], q["start"], q["dock"]), "chart": draw(q)}
    if auto:
        route = q["route"]
    if route is None:
        r["verdict"] = None
        return r
    route = route.strip().upper()
    cell, seen, score = q["start"], [q["start"]], q["grip"][q["start"]]
    for i, d in enumerate(route, 1):
        if d not in STEP:
            raise RopeError(f"step {i}: {d!r} is not N, S, E or W")
        if cell == q["dock"]:
            raise RopeError(f"step {i}: the rope is already on the dock post")
        n = (cell[0] + STEP[d][0], cell[1] + STEP[d][1])
        if n not in q["grip"]:
            raise RopeError(f"step {i}: {d} runs off the quay or into a crate")
        if n in seen:
            raise RopeError(f"step {i}: the rope would cross itself")
        cell = n
        seen.append(n)
        score += q["grip"][n]
    r.update({"route": route, "grip": score, "on_dock": cell == q["dock"], "chart": draw(q, seen)})
    if cell != q["dock"]:
        r["verdict"] = "loose"
    else:
        r["verdict"] = "taut" if score >= q["par"] else "slack"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise RopeError(f"census: {e}")


def text(r):
    lines = [f"rope run: {len(r['cleats'])} cleats ({', '.join(r['cleats'])}); par {r['par']} grip "
             f"(best-neighbour habit: {r['greedy_grip']}); seed {r['seed']}"]
    lines += ["  " + row for row in r["chart"]]
    if r["verdict"]:
        lines.append(f"verdict: {r['verdict']} ({r['grip']} grip over {len(r['route'])} steps, "
                     f"{'on' if r['on_dock'] else 'short of'} the dock, par {r['par']})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Rope Run: lay one rope across the quay through the best cleats.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--route", help="steps as a string of N S E W")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.route, a.auto)
    except RopeError as e:
        print(f"rope_run: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
