# SPDX-License-Identifier: MIT
"""Twin Pilots (G557, disk-saver): a cooperative two-boat harbour round.

Python dev tooling only; nothing here runs inside Unreal. Every island in a world census
(tools/world_census output, read-only) is a berth on the DiskSaver pilot chart, plus a few
seeded channel buoys. Two pilot boats leave the harbour together. Every bell, each boat moves
one channel (or holds). Between them they must call at every berth and buoy, and both must be
back in the harbour. Pilotmaster Cuthbert wants the round done in as few bells as possible.

The two boats cooperate, so the par is the fewest bells for the pair, found by an exact
breadth-first search over (boat A, boat B, calls made). The tests check it against an
independent oracle: every split of the calls between the boats, each half toured by brute
force over shortest-path distances. The trap is sending one boat to do everything.

  verdict   in_step  every call made, both boats home, in par bells,
            late     every call made, both home, more bells than par,
            adrift   a call missed or a boat not home.

  python tools/streaming/twin_pilots.py CENSUS.json [--seed N] [--plan 'a>b>harbour;c>harbour' | --auto] [--json]

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

FORMAT = "daedalus-twin-pilots"
VERDICTS = ("in_step", "late", "adrift")
HARBOUR = "harbour"
MAX_CALLS = 8
MAX_BUOYS = 3


class PilotError(ValueError):
    pass


def chart(census_doc, seed=0):
    """(nodes, sorted edges (i, j), i < j). Node 0 is the harbour."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise PilotError(str(e))
    labels = sorted(f"{w}:{s}" for w, isl in worlds for s, _ in isl)
    if not labels:
        raise PilotError("census has no islands to chart")
    if len(labels) > MAX_CALLS:
        raise PilotError(f"more than {MAX_CALLS} islands")
    buoys = [f"buoy:{k}" for k in range(1, min(MAX_BUOYS, MAX_CALLS - len(labels)) + 1)]
    nodes = [HARBOUR] + labels + buoys
    idx = {l: i for i, l in enumerate(nodes)}
    key = f"{census_doc.get('snapshot_date')}|{','.join(labels)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    edges = set()

    def link(a, b):
        if a != b:
            edges.add((min(a, b), max(a, b)))

    chains = []
    for w, isl in worlds:
        c = [idx[f"{w}:{s}"] for s, _ in sorted(isl)]
        if c:
            chains.append(c)
        for a, b in zip(c, c[1:]):
            link(a, b)
    rng.shuffle(chains)
    for c in chains:
        link(0, rng.choice(c))
    for b in buoys:
        placed = list(range(idx[b]))
        for p in rng.sample(placed, min(2, len(placed))):
            link(idx[b], p)
    if len(nodes) > 3:
        for i in range(1, len(nodes)):
            link(i, rng.randrange(len(nodes)))
    return nodes, sorted(edges)


def adjacency(n, edges):
    adj = [{i} for i in range(n)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return [sorted(s) for s in adj]


def solve(n, edges):
    """(par bells, route A, route B) by BFS over (a, b, calls mask); routes exclude the start."""
    adj = adjacency(n, edges)
    full = (1 << n) - 2
    start = (0, 0, 0)
    prev = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        a, b, m = s
        if a == 0 and b == 0 and m == full:
            ra, rb = [], []
            while prev[s] is not None:
                ra.append(s[0])
                rb.append(s[1])
                s = prev[s]
            return len(ra), ra[::-1], rb[::-1]
        for x in adj[a]:
            for y in adj[b]:
                t = (x, y, (m | (1 << x) | (1 << y)) & full)
                if t not in prev:
                    prev[t] = s
                    q.append(t)
    raise PilotError("chart is not connected")


def distances(n, edges):
    d = [[0 if i == j else n * 9 for j in range(n)] for i in range(n)]
    for a, b in edges:
        d[a][b] = d[b][a] = 1
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


def solo_bells(n, edges):
    """Bells for one boat doing every call alone (Held-Karp over shortest paths)."""
    d = distances(n, edges)
    calls = list(range(1, n))
    if not calls:
        return 0
    best = {(1 << i, c): d[0][c] for i, c in enumerate(calls)}
    for m in range(1, 1 << len(calls)):
        for i, c in enumerate(calls):
            if (m >> i) & 1 and (m, c) in best:
                for j, e in enumerate(calls):
                    if not (m >> j) & 1:
                        k = (m | (1 << j), e)
                        v = best[(m, c)] + d[c][e]
                        if v < best.get(k, 1 << 30):
                            best[k] = v
    f = (1 << len(calls)) - 1
    return min(best[(f, c)] + d[c][0] for c in calls)


def parse_plan(s, nodes):
    idx = {l: i for i, l in enumerate(nodes)}
    routes = [r.strip() for r in s.split(";")] if s.strip() else []
    if len(routes) > 2:
        raise PilotError("at most two boats")
    out = []
    for r in routes:
        steps = [x.strip() for x in r.split(">") if x.strip()] if r else []
        for x in steps:
            if x not in idx:
                raise PilotError(f"no such berth {x!r}")
        out.append([idx[x] for x in steps])
    while len(out) < 2:
        out.append([])
    return out


def grade(nodes, edges, routes):
    adj = adjacency(len(nodes), edges)
    seen = {0}
    for bi, r in enumerate(routes):
        at = 0
        for step, x in enumerate(r, 1):
            if x not in adj[at]:
                raise PilotError(f"boat {'AB'[bi]} bell {step}: no channel {nodes[at]} -> {nodes[x]}")
            at = x
            seen.add(x)
    bells = max(len(r) for r in routes)
    missed = [nodes[i] for i in range(1, len(nodes)) if i not in seen]
    home = all((r[-1] if r else 0) == 0 for r in routes)
    return bells, missed, home


def play(census_doc, seed=0, plan=None, auto=False):
    nodes, edges = chart(census_doc, seed)
    par, ra, rb = solve(len(nodes), edges)
    if auto:
        routes = [ra, rb]
    elif plan is None:
        routes = None
    else:
        routes = parse_plan(plan, nodes)
    r = {"format": FORMAT, "version": 1, "seed": seed, "nodes": nodes,
         "channels": [[nodes[a], nodes[b]] for a, b in edges], "par": par,
         "solo_bells": solo_bells(len(nodes), edges)}
    if routes is None:
        r["verdict"] = None
        return r
    bells, missed, home = grade(nodes, edges, routes)
    r.update({"routes": [[nodes[x] for x in rt] for rt in routes], "bells": bells,
              "missed": missed, "home": home})
    if missed or not home:
        r["verdict"] = "adrift"
    else:
        r["verdict"] = "in_step" if bells <= par else "late"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise PilotError(f"census: {e}")


def text(r):
    lines = [f"twin pilots: {len(r['nodes']) - 1} calls, par {r['par']} bells for two boats "
             f"(one boat alone: {r['solo_bells']}); seed {r['seed']}"]
    for a, b in r["channels"]:
        lines.append(f"  channel {a} -- {b}")
    if r["verdict"] is not None:
        for name, rt in zip("AB", r["routes"]):
            lines.append(f"  boat {name}: {HARBOUR} > " + " > ".join(rt) if rt else f"  boat {name}: holds in {HARBOUR}")
        extra = f"; missed {', '.join(r['missed'])}" if r["missed"] else ""
        extra += "" if r["home"] else "; a boat is not home"
        lines.append(f"verdict: {r['verdict']} ({r['bells']} bells, par {r['par']}{extra})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Twin Pilots: a cooperative two-boat round over the census.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", help="boat A route ; boat B route, berths joined by '>' (start omitted)")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.plan, a.auto)
    except PilotError as e:
        print(f"twin_pilots: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
