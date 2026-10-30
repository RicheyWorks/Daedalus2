# SPDX-License-Identifier: MIT
"""Boom Defence (G562, disk-saver): place boom posts to stop smuggler skiffs (tower-defence lite).

Python dev tooling only; nothing here runs inside Unreal. A seed winds a channel across a 7x9
chart from the open sea (west) to the harbour (east) and marks up to twelve post sites, lettered
A-L, beside it. Every census island (tools/world_census output, read-only; up to six) sends one
smuggler skiff, sorted by label, two ticks apart. A skiff's hull is 4 + its asset count mod 3,
plus a seeded 0-1.

Each tick every skiff on the chart moves one cell along the channel, a new skiff enters, and
then each boom post snags the skiff in reach (the eight cells round it) that is furthest along,
taking one off its hull. A skiff with no hull left sinks. A skiff that runs off the harbour
end gets through. Boom-master Leopold has two posts. Place them so the fewest skiffs get through.

The par is the fewest skiffs through over every pair of sites (exhaustive). The tests check
it against an independent simulator. The trap is placing posts where they reach the most
channel cells, shown as greedy_through.

  verdict   watertight  as few through as par,
            leaky       more than par, but not all,
            overrun     every skiff through.

  python tools/streaming/boom_defence.py CENSUS.json [--seed N] [--posts A,C | --auto] [--json]

Deterministic, stdlib only, no clock. Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import hashlib
import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-boom-defence"
VERDICTS = ("watertight", "leaky", "overrun")
ROWS, COLS = 7, 9
MAX_SKIFFS = 6
MAX_SITES = 12
POSTS = 2
GAP = 2


class BoomError(ValueError):
    pass


def reach(site, cell):
    return max(abs(site[0] - cell[0]), abs(site[1] - cell[1])) == 1


def simulate(path, hulls, posts):
    """(number through, per-skiff fate list) for posts (list of cells)."""
    n = len(hulls)
    hp = list(hulls)
    at = [None] * n          # index along path, None = not yet entered
    fate = [None] * n
    tick = 0
    while any(f is None for f in fate):
        for i in range(n):
            if fate[i] is None and at[i] is not None:
                at[i] += 1
                if at[i] >= len(path):
                    fate[i] = "through"
        if tick % GAP == 0 and tick // GAP < n:
            at[tick // GAP] = 0
        for p in posts:
            live = [i for i in range(n) if fate[i] is None and at[i] is not None and reach(p, path[at[i]])]
            if live:
                j = max(live, key=lambda i: (at[i], -i))
                hp[j] -= 1
                if hp[j] <= 0:
                    fate[j] = "sunk"
        tick += 1
    return sum(f == "through" for f in fate), fate


def chart(census_doc, seed=0):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise BoomError(str(e))
    isl = sorted((f"{w}:{s}", a) for w, il in worlds for s, a in il)
    if not isl:
        raise BoomError("census has no islands to send skiffs")
    isl = isl[:MAX_SKIFFS]
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in isl)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    row, path = rng.randrange(ROWS), []
    for c in range(COLS):
        target = rng.randrange(ROWS) if c % 2 == 0 else row
        step = 1 if target >= row else -1
        for r in range(row, target + step, step):
            path.append((r, c))
        row = target
    cells = set(path)
    sites = sorted({(r + dr, c + dc) for r, c in path for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if 0 <= r + dr < ROWS and 0 <= c + dc < COLS} - cells)
    sites = sorted(rng.sample(sites, min(MAX_SITES, len(sites))))
    hulls = [4 + a % 3 + rng.randrange(2) for _, a in isl]
    return {"skiffs": [l for l, _ in isl], "hulls": hulls, "path": path, "sites": sites}


def best(c):
    """(par, best site indices) over every pair of sites."""
    k = min(POSTS, len(c["sites"]))
    top = None
    for combo in itertools.combinations(range(len(c["sites"])), k):
        n = simulate(c["path"], c["hulls"], [c["sites"][i] for i in combo])[0]
        if top is None or n < top[0]:
            top = (n, combo)
    return top


def greedy(c):
    k = min(POSTS, len(c["sites"]))
    cover = [sum(reach(s, p) for p in c["path"]) for s in c["sites"]]
    pick = sorted(range(len(c["sites"])), key=lambda i: (-cover[i], i))[:k]
    return simulate(c["path"], c["hulls"], [c["sites"][i] for i in pick])[0], tuple(sorted(pick))


def draw(c, posts=()):
    g = [["~"] * COLS for _ in range(ROWS)]
    for r, col in c["path"]:
        g[r][col] = "="
    for i, (r, col) in enumerate(c["sites"]):
        g[r][col] = "ABCDEFGHIJKL"[i] if i in posts else "abcdefghijkl"[i]
    return ["".join(row) for row in g]


def play(census_doc, seed=0, posts=None, auto=False):
    c = chart(census_doc, seed)
    par, combo = best(c)
    gthrough, _ = greedy(c)
    r = {"format": FORMAT, "version": 1, "seed": seed, "skiffs": c["skiffs"], "hulls": c["hulls"],
         "channel_length": len(c["path"]), "sites": len(c["sites"]), "posts_allowed": min(POSTS, len(c["sites"])),
         "par": par, "greedy_through": gthrough, "chart": draw(c)}
    if auto:
        chosen = list(combo)
    elif posts is None:
        r["verdict"] = None
        return r
    else:
        toks = [t.strip().upper() for t in posts.split(",") if t.strip()]
        letters = "ABCDEFGHIJKL"[:len(c["sites"])]
        chosen = []
        for t in toks:
            if len(t) != 1 or t not in letters:
                raise BoomError(f"no post site {t!r} (sites are {letters[0]}-{letters[-1]})")
            if letters.index(t) in chosen:
                raise BoomError(f"site {t} named twice")
            chosen.append(letters.index(t))
        if len(chosen) > r["posts_allowed"]:
            raise BoomError(f"only {r['posts_allowed']} posts")
    through, fate = simulate(c["path"], c["hulls"], [c["sites"][i] for i in chosen])
    r.update({"posts": ["ABCDEFGHIJKL"[i] for i in sorted(chosen)], "through": through,
              "fates": dict(zip(c["skiffs"], fate)), "chart": draw(c, set(chosen))})
    if through <= par:
        r["verdict"] = "watertight"
    elif through < len(c["skiffs"]):
        r["verdict"] = "leaky"
    else:
        r["verdict"] = "overrun"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise BoomError(f"census: {e}")


def text(r):
    sk = ", ".join(f"{s} (hull {h})" for s, h in zip(r["skiffs"], r["hulls"]))
    lines = [f"boom defence: skiffs {sk}; {r['posts_allowed']} posts; par {r['par']} through "
             f"(most-reach habit: {r['greedy_through']}); seed {r['seed']}"]
    lines += ["  " + row for row in r["chart"]]
    if r["verdict"]:
        lines.append("  " + ", ".join(f"{k} {v}" for k, v in r["fates"].items()))
        lines.append(f"verdict: {r['verdict']} (posts {','.join(r['posts']) or '-'}; {r['through']} through, par {r['par']})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Boom Defence: place boom posts to stop the census skiffs.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--posts", help="comma-separated site letters, e.g. A,C")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.posts, a.auto)
    except BoomError as e:
        print(f"boom_defence: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
