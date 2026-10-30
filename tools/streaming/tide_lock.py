# SPDX-License-Identifier: MIT
"""Tide Lock (G554, disk-saver): a lock-scheduling puzzle over the world census.

Python dev tooling only; nothing here runs inside Unreal. Every island in a world census
(tools/world_census output, read-only) sends one boat up the DiskSaver canal. A boat's length
is its island's RAM cost in the G206 model (census_budget.island_cost); a seed gives the boats
their arrival minutes and their queue order. Lockkeeper Wilhelmina's single lock chamber holds
boats whose lengths add up to at most the chamber size (default: the G206 RAM budget), and one
lock cycle takes a fixed number of minutes.

Boats go through strictly in arrival order. The player chooses how to group them: a plan like
`2,1,3` means the first two boats lock through together, then one, then three. A group leaves
when its last boat has arrived and the lock is free; every boat waits from its arrival until
its group leaves. The goal is the least total waiting.

An exact search over (next boat, minute the lock is free), memoised, finds the least total wait
(checked against trying every grouping in the tests). Greedy "fill the chamber" is shown too.

  verdict   smooth   the plan's total wait equals the optimum,
            slow     a legal plan with more waiting than needed,
            jammed   an illegal plan (sizes do not add up, or a group overfills the chamber).

  python tools/streaming/tide_lock.py CENSUS.json [--seed N] [--chamber-kib K] [--cycle-min M]
         [--plan 2,1,3 | --auto] [--json]

Deterministic, stdlib only, no clock. Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import sys
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-tide-lock"
VERDICTS = ("smooth", "slow", "jammed")
MAX_BOATS = 60
DEFAULT_CYCLE = 30


class LockError(ValueError):
    pass


def boats(census_doc, seed):
    """[(label, length_kib, arrival_minute)] in queue order."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise LockError(str(e))
    fleet = sorted((f"{w}:{s}", cb.island_cost(n)[0]) for w, isl in worlds for s, n in isl)
    if not fleet:
        raise LockError("census has no islands to send boats")
    if len(fleet) > MAX_BOATS:
        raise LockError(f"more than {MAX_BOATS} boats")
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in fleet)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    rng.shuffle(fleet)
    t, out = 0, []
    for label, length in fleet:
        t += rng.randint(0, 25)
        out.append((label, length, t))
    return out


def run_plan(queue, sizes, chamber, cycle):
    """(total_wait, groups) for a legal plan; raises LockError naming why it jams."""
    if sum(sizes) != len(queue) or any(s < 1 for s in sizes):
        raise LockError(f"plan must split all {len(queue)} boats into groups of at least 1")
    free, i, total, groups = 0, 0, 0, []
    for s in sizes:
        g = queue[i:i + s]
        load = sum(b[1] for b in g)
        if load > chamber:
            raise LockError(f"group {len(groups) + 1} needs {load} KiB, chamber holds {chamber}")
        leave = max(free, g[-1][2])
        wait = sum(leave - b[2] for b in g)
        total += wait
        groups.append({"boats": [b[0] for b in g], "load_kib": load, "leaves": leave, "wait": wait})
        free = leave + cycle
        i += s
    return total, groups


def optimum(queue, chamber, cycle):
    """(least total wait, plan sizes)."""
    n = len(queue)
    if any(b[1] > chamber for b in queue):
        raise LockError("a boat is longer than the chamber")

    @lru_cache(maxsize=None)
    def best(i, free):
        if i == n:
            return 0, ()
        result = None
        load = 0
        for j in range(i, n):
            load += queue[j][1]
            if load > chamber:
                break
            leave = max(free, queue[j][2])
            wait = sum(leave - queue[k][2] for k in range(i, j + 1))
            rest, plan = best(j + 1, leave + cycle)
            cand = (wait + rest, (j - i + 1,) + plan)
            if result is None or cand < result:
                result = cand
        return result

    cost, plan = best(0, 0)
    return cost, list(plan)


def greedy(queue, chamber):
    sizes, load, count = [], 0, 0
    for b in queue:
        if count and load + b[1] > chamber:
            sizes.append(count)
            load, count = 0, 0
        load += b[1]
        count += 1
    sizes.append(count)
    return sizes


def puzzle(census_doc, seed=0, chamber=None, cycle=DEFAULT_CYCLE, cfg=None, plan=None, auto=False):
    if chamber is None:
        try:
            chamber = cb.load_budget(cfg)[0]
        except cb.CensusBudgetError as e:
            raise LockError(str(e))
    for name, v in (("chamber-kib", chamber), ("cycle-min", cycle)):
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= cb.MAX_KIB:
            raise LockError(f"{name} must be a positive integer")
    queue = boats(census_doc, seed)
    best_wait, best_plan = optimum(queue, chamber, cycle)
    g = greedy(queue, chamber)
    out = {"format": FORMAT, "version": 1, "seed": seed, "chamber_kib": chamber, "cycle_min": cycle,
           "queue": [{"boat": l, "length_kib": k, "arrives": t} for l, k, t in queue],
           "optimal_wait": best_wait, "greedy_plan": g, "greedy_wait": run_plan(queue, g, chamber, cycle)[0]}
    if plan is None and not auto:
        return out
    sizes = best_plan if auto else plan
    try:
        wait, groups = run_plan(queue, sizes, chamber, cycle)
    except LockError as e:
        return dict(out, plan=sizes, verdict="jammed", problem=str(e))
    return dict(out, plan=sizes, wait=wait, groups=groups, optimal_plan=best_plan,
                verdict="smooth" if wait == best_wait else "slow")


def _load(path, what):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise LockError(f"{what}: {e}")


def text(r):
    lines = [f"tide lock (seed {r['seed']}): chamber {r['chamber_kib']} KiB, cycle {r['cycle_min']} min; "
             f"optimal wait {r['optimal_wait']} min, greedy {r['greedy_wait']} min"]
    lines += [f"  {i + 1}. {b['boat']} {b['length_kib']} KiB arrives {b['arrives']}" for i, b in enumerate(r["queue"])]
    if "verdict" in r:
        if r["verdict"] == "jammed":
            lines.insert(0, f"tide lock: jammed ({r['problem']})")
        else:
            lines.insert(0, f"tide lock: {r['verdict']} (plan {','.join(map(str, r['plan']))} waits {r['wait']} min, optimal {r['optimal_wait']})")
            lines += [f"  group {k + 1}: {' + '.join(g['boats'])} leaves {g['leaves']} (wait {g['wait']})" for k, g in enumerate(r["groups"])]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tide Lock: group boats through one lock with the least waiting.")
    ap.add_argument("census")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--chamber-kib", type=int)
    ap.add_argument("--cycle-min", type=int, default=DEFAULT_CYCLE)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", help="group sizes in queue order, e.g. 2,1,3")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = None if a.chamber_kib is not None else _load(a.config, "config")
        plan = None
        if a.plan is not None:
            try:
                plan = [int(x) for x in a.plan.split(",") if x.strip()]
            except ValueError:
                raise LockError("plan must be comma-separated whole numbers")
        r = puzzle(_load(a.census, "census"), a.seed, a.chamber_kib, a.cycle_min, cfg, plan, a.auto)
    except LockError as e:
        print(f"tide_lock: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
