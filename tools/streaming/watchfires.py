# SPDX-License-Identifier: MIT
"""Watchfires (G555, disk-saver): light every island with the fewest watchfires.

Python dev tooling only; nothing here runs inside Unreal. Every island in a world census
(tools/world_census output, read-only) is a node of the DiskSaver ferry chart. Ferry routes:
the islands of each world are chained in slot order, the worlds are joined in a seeded order,
and a seed adds one extra crossing per island. A watchfire on an island lights that island and
every island one ferry route away. Firekeeper Leofric must light the whole chart with as few
fires as possible (a minimum dominating set).

The par comes from an exact branch-and-bound search (pick the first unlit island; one of it or
its neighbours must burn), checked against trying every set in the tests. The greedy
"light the most new islands" plan is shown as the trap.

  verdict   blazing  every island lit, with the par number of fires,
            smoky    every island lit, with more fires than par,
            dark     some island is unlit (listed).

  python tools/streaming/watchfires.py CENSUS.json [--seed N] [--fires a:1,b:4 | --auto] [--json]

Deterministic, stdlib only, no clock. Exit 0 = printed or graded, 2 = refusal.
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

FORMAT = "daedalus-watchfires"
VERDICTS = ("blazing", "smoky", "dark")
MAX_ISLANDS = 40


class WatchfireError(ValueError):
    pass


def chart(census_doc, seed=0):
    """(labels, sorted edge list of (i, j) with i < j)."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise WatchfireError(str(e))
    labels = sorted(f"{w}:{s}" for w, isl in worlds for s, _ in isl)
    if not labels:
        raise WatchfireError("census has no islands to chart")
    if len(labels) > MAX_ISLANDS:
        raise WatchfireError(f"more than {MAX_ISLANDS} islands")
    idx = {l: i for i, l in enumerate(labels)}
    key = f"{census_doc.get('snapshot_date')}|{','.join(labels)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    edges = set()

    def link(a, b):
        if a != b:
            edges.add((min(a, b), max(a, b)))

    chains = []
    for w, isl in worlds:
        nodes = [idx[f"{w}:{s}"] for s, _ in sorted(isl)]
        if nodes:
            chains.append(nodes)
        for a, b in zip(nodes, nodes[1:]):
            link(a, b)
    rng.shuffle(chains)
    for c1, c2 in zip(chains, chains[1:]):
        link(rng.choice(c1), rng.choice(c2))
    if len(labels) > 2:
        for i in range(len(labels)):
            link(i, rng.randrange(len(labels)))
    return labels, sorted(edges)


def closed_neighbourhoods(n, edges):
    nb = [1 << i for i in range(n)]
    for a, b in edges:
        nb[a] |= 1 << b
        nb[b] |= 1 << a
    return nb


def par(n, edges):
    """(minimum number of fires, one optimal set as sorted indexes)."""
    nb = closed_neighbourhoods(n, edges)
    full = (1 << n) - 1
    best = [n + 1, None]
    order = sorted(range(n), key=lambda v: -bin(nb[v]).count("1"))

    def rec(lit, chosen):
        if lit == full:
            if len(chosen) < best[0]:
                best[0], best[1] = len(chosen), sorted(chosen)
            return
        if len(chosen) + 1 >= best[0]:
            return
        u = next(i for i in range(n) if not lit >> i & 1)
        cands = [v for v in order if nb[u] >> v & 1]
        for v in cands:
            chosen.append(v)
            rec(lit | nb[v], chosen)
            chosen.pop()

    rec(0, [])
    return best[0], best[1]


def greedy(n, edges):
    nb = closed_neighbourhoods(n, edges)
    lit, fires, full = 0, [], (1 << n) - 1
    while lit != full:
        v = max(range(n), key=lambda v: (bin(nb[v] & ~lit).count("1"), -v))
        fires.append(v)
        lit |= nb[v]
    return sorted(fires)


def game(census_doc, seed=0, fires=None, auto=False):
    labels, edges = chart(census_doc, seed)
    n = len(labels)
    k, best = par(n, edges)
    g = greedy(n, edges)
    out = {"format": FORMAT, "version": 1, "seed": seed, "islands": labels,
           "routes": [[labels[a], labels[b]] for a, b in edges], "par": k,
           "greedy_fires": [labels[i] for i in g]}
    if fires is None and not auto:
        return out
    if auto:
        chosen = best
    else:
        idx = {l: i for i, l in enumerate(labels)}
        unknown = [f for f in fires if f not in idx]
        if unknown:
            raise WatchfireError(f"no island {unknown[0]!r} on the chart")
        chosen = sorted({idx[f] for f in fires})
    nb = closed_neighbourhoods(n, edges)
    lit = 0
    for v in chosen:
        lit |= nb[v]
    unlit = [labels[i] for i in range(n) if not lit >> i & 1]
    verdict = "dark" if unlit else "blazing" if len(chosen) <= k else "smoky"
    return dict(out, fires=[labels[i] for i in chosen], unlit=unlit, verdict=verdict)


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise WatchfireError(f"census: {e}")


def text(r):
    lines = [f"watchfires (seed {r['seed']}): {len(r['islands'])} islands, {len(r['routes'])} ferry routes, par {r['par']} "
             f"(greedy lights {len(r['greedy_fires'])})"]
    lines += [f"  {a} -- {b}" for a, b in r["routes"]]
    if "verdict" in r:
        head = f"watchfires: {r['verdict']} ({len(r['fires'])} fires: {', '.join(r['fires']) or 'none'}; par {r['par']})"
        if r["unlit"]:
            head += f"; unlit: {', '.join(r['unlit'])}"
        lines.insert(0, head)
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Watchfires: light every island of the ferry chart with the fewest fires.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fires", help="comma-separated world:slot islands to light")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        fires = [f.strip() for f in a.fires.split(",") if f.strip()] if a.fires is not None else None
        r = game(_load(a.census), a.seed, fires, a.auto)
    except WatchfireError as e:
        print(f"watchfires: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
