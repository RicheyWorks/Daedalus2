# SPDX-License-Identifier: MIT
"""Fleet Soundings (G551, disk-saver): a daily solitaire-battleship puzzle over the world census.

Python dev tooling only; nothing here runs inside Unreal. Tugmaster Ignatius moored the fleet in
the fog and only took soundings: how many cells of each row and column of the anchorage are
hull. Every island in a world census (tools/world_census output, read-only) is one ship; its
length comes from its cargo (asset definitions): 0 -> 1, 1-9 -> 2, 10-99 -> 3, 100+ -> 4.

Rules (classic solitaire battleship): ships are straight lines of cells, horizontal or vertical;
no two ships touch, not even diagonally; each row and column holds exactly its sounding of hull
cells; revealed cells (hints) must match.

The generator places the fleet by seed, then runs an exact backtracking solver and reveals cells
where two solutions disagree until exactly ONE solution remains, so every puzzle is fair. The
verifier checks a player's grid against the rules and the clues.

  python tools/streaming/fleet_soundings.py CENSUS.json [--seed N] [--solution] [--check GRID.txt] [--json]

A grid file has one line per row, `#` for hull and `.` for water. Verdicts for --check:
  charted   every rule and clue holds (the unique solution),
  short     the fleet is moored legally but a sounding or hint disagrees,
  reefed    a rule is broken (wrong fleet, touching ships, bent ships, bad size or symbols).
Deterministic, stdlib only, no clock. Exit 0 = printed/checked, 2 = refusal.
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

FORMAT = "daedalus-fleet-soundings"
VERDICTS = ("charted", "short", "reefed")
MAX_AREA = 12
SIZES = ((8, 6), (MAX_AREA, 7))


class SoundingsError(ValueError):
    pass


def ship_length(asset_definitions):
    n = asset_definitions
    return 1 if n == 0 else 2 if n < 10 else 3 if n < 100 else 4


def _rng(census_doc, labels, seed):
    key = f"{census_doc.get('snapshot_date')}|{','.join(labels)}|{seed}".encode("utf-8")
    return random.Random(int(hashlib.sha256(key).hexdigest(), 16))


def fleet(census_doc, seed=0):
    """(rng, [(label, length)]) with total area <= MAX_AREA, chosen by seed when the census is big."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise SoundingsError(str(e))
    ships = sorted((f"{w}:{s}", ship_length(n)) for w, isl in worlds for s, n in isl)
    if not ships:
        raise SoundingsError("census has no islands to moor")
    rng = _rng(census_doc, [l for l, _ in ships], seed)
    order = ships[:]
    rng.shuffle(order)
    chosen, area = [], 0
    for label, n in order:
        if area + n <= MAX_AREA:
            chosen.append((label, n))
            area += n
    return rng, sorted(chosen, key=lambda t: (-t[1], t[0]))


def grid_size(area):
    for limit, n in SIZES:
        if area <= limit:
            return n
    raise SoundingsError("fleet too large")


def _cells(r, c, n, vertical):
    return [(r + k, c) if vertical else (r, c + k) for k in range(n)]


def placements(size, n):
    out = []
    for vertical in ((False,) if n == 1 else (False, True)):
        for r in range(size - (n - 1 if vertical else 0)):
            for c in range(size - (0 if vertical else n - 1)):
                out.append(tuple(_cells(r, c, n, vertical)))
    return out


def _halo(cells):
    return {(r + dr, c + dc) for r, c in cells for dr in (-1, 0, 1) for dc in (-1, 0, 1)}


def solve(size, lengths, rows, cols, hints, limit=2):
    """Up to `limit` solutions, each a frozenset of hull cells. lengths sorted descending."""
    ship_hint = {p for p, v in hints.items() if v}
    water_hint = {p for p, v in hints.items() if not v}
    places = {n: [p for p in placements(size, n) if not water_hint.intersection(p)] for n in set(lengths)}
    sols, rc, cc = [], [0] * size, [0] * size
    occupied, blocked = set(), {}

    def rec(k, start):
        if len(sols) >= limit:
            return
        if k == len(lengths):
            if rc == list(rows) and cc == list(cols) and ship_hint <= occupied:
                sols.append(frozenset(occupied))
            return
        left = sum(lengths[k:])
        if any(rows[i] - rc[i] > left for i in range(size)) or any(cols[i] - cc[i] > left for i in range(size)):
            return
        n = lengths[k]
        opts = places[n]
        for idx in range(start if k and lengths[k - 1] == n else 0, len(opts)):
            p = opts[idx]
            if any(blocked.get(q) for q in p):
                continue
            if any(rc[r] + 1 > rows[r] for r, _ in p) or any(cc[c] + 1 > cols[c] for _, c in p):
                if any(rc[r] + sum(1 for rr, _ in p if rr == r) > rows[r] for r, _ in p) or \
                   any(cc[c] + sum(1 for _, x in p if x == c) > cols[c] for _, c in p):
                    continue
            for r, c in p:
                rc[r] += 1
                cc[c] += 1
                occupied.add((r, c))
            halo = _halo(p)
            for q in halo:
                blocked[q] = blocked.get(q, 0) + 1
            rec(k + 1, idx + 1)
            for q in halo:
                blocked[q] -= 1
            for r, c in p:
                rc[r] -= 1
                cc[c] -= 1
                occupied.discard((r, c))

    rec(0, 0)
    return sols


def generate(census_doc, seed=0):
    rng, ships = fleet(census_doc, seed)
    lengths = [n for _, n in ships]
    size = grid_size(sum(lengths))
    for _ in range(2000):
        used, blocked, ok, where = set(), set(), True, []
        for n in lengths:
            opts = [p for p in placements(size, n) if not blocked.intersection(p)]
            if not opts:
                ok = False
                break
            p = rng.choice(opts)
            where.append(p)
            used.update(p)
            blocked |= _halo(p)
        if ok:
            break
    else:
        raise SoundingsError("could not moor the fleet")
    rows = [sum(1 for r, _ in used if r == i) for i in range(size)]
    cols = [sum(1 for _, c in used if c == i) for i in range(size)]
    hints = {}
    while True:
        sols = solve(size, lengths, rows, cols, hints, 2)
        if len(sols) == 1:
            break
        diff = sorted(sols[0] ^ sols[1])
        p = rng.choice(diff)
        hints[p] = p in used
    solution = ["".join("#" if (r, c) in used else "." for c in range(size)) for r in range(size)]
    return {"format": FORMAT, "version": 1, "seed": seed, "size": size,
            "fleet": [{"island": l, "length": n} for l, n in ships],
            "rows": rows, "cols": cols,
            "hints": [{"row": r, "col": c, "hull": v} for (r, c), v in sorted(hints.items())],
            "solution": solution}


def _ships_in(grid):
    """Connected hull groups (4-neighbour) as sorted cell lists."""
    seen, groups = set(), []
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == "#" and (r, c) not in seen:
                stack, g = [(r, c)], []
                seen.add((r, c))
                while stack:
                    a, b = stack.pop()
                    g.append((a, b))
                    for q in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= q[0] < len(grid) and 0 <= q[1] < len(grid) and grid[q[0]][q[1]] == "#" and q not in seen:
                            seen.add(q)
                            stack.append(q)
                groups.append(sorted(g))
    return groups


def check(puzzle, grid):
    size = puzzle["size"]
    problems = []
    if len(grid) != size or any(len(row) != size for row in grid):
        return {"verdict": "reefed", "problems": [f"grid must be {size} rows of {size} cells"]}
    if any(ch not in "#." for row in grid for ch in row):
        return {"verdict": "reefed", "problems": ["use only # and ."]}
    groups = _ships_in(grid)
    for g in groups:
        if len({r for r, _ in g}) > 1 and len({c for _, c in g}) > 1:
            problems.append(f"ship at row {g[0][0]} col {g[0][1]} is bent")
    hull = {p for g in groups for p in g}
    for r, c in sorted(hull):
        for dr, dc in ((1, 1), (1, -1)):
            q = (r + dr, c + dc)
            if q in hull and (r + dr, c) not in hull and (r, c + dc) not in hull:
                problems.append(f"ships touch diagonally at row {r} col {c}")
    if not problems and sorted(len(g) for g in groups) != sorted(s["length"] for s in puzzle["fleet"]):
        problems.append("the moored ships are not the fleet")
    if problems:
        return {"verdict": "reefed", "problems": problems}
    short = []
    for i in range(size):
        if grid[i].count("#") != puzzle["rows"][i]:
            short.append(f"row {i} sounds {grid[i].count('#')}, clue {puzzle['rows'][i]}")
        col = sum(1 for r in range(size) if grid[r][i] == "#")
        if col != puzzle["cols"][i]:
            short.append(f"col {i} sounds {col}, clue {puzzle['cols'][i]}")
    for h in puzzle["hints"]:
        if (grid[h["row"]][h["col"]] == "#") != h["hull"]:
            short.append(f"hint at row {h['row']} col {h['col']} not matched")
    return {"verdict": "short" if short else "charted", "problems": short}


def render(p, solution=False):
    hints = {(h["row"], h["col"]): h["hull"] for h in p["hints"]}
    lines = [f"fleet soundings (seed {p['seed']}, {p['size']}x{p['size']}): fleet " +
             ", ".join(str(s["length"]) for s in p["fleet"])]
    lines.append("   " + " ".join(str(c) for c in p["cols"]))
    for r in range(p["size"]):
        cells = []
        for c in range(p["size"]):
            if solution:
                cells.append(p["solution"][r][c])
            else:
                cells.append({True: "#", False: "~"}.get(hints.get((r, c)), "?"))
        lines.append(f"{p['rows'][r]:>2} " + " ".join(cells))
    return "\n".join(lines) + "\n"


def _load_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise SoundingsError(f"census: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fleet Soundings: solitaire battleship over the world census.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--solution", action="store_true")
    ap.add_argument("--check", help="grid file (# hull, . water)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        p = generate(_load_json(a.census), a.seed)
        if a.check:
            try:
                with open(a.check, encoding="utf-8-sig") as f:
                    grid = [l.strip() for l in f.read().splitlines() if l.strip()]
            except OSError as e:
                raise SoundingsError(f"grid: {e}")
            out = dict(check(p, grid), format=FORMAT, seed=a.seed)
            text = f"fleet soundings: {out['verdict']}\n" + "".join(f"  - {x}\n" for x in out["problems"])
        else:
            out = p if a.solution else {k: v for k, v in p.items() if k != "solution"}
            text = render(p, a.solution)
    except SoundingsError as e:
        print(f"fleet_soundings: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n" if a.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
