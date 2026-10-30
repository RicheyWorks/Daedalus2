# SPDX-License-Identifier: MIT
"""Ebb Tide Eviction (G253, disk-saver): which resident islands to unload first.

Reads a Census Budget Beacons report (tools/streaming/census_budget.py, format
daedalus-census-budget v1). For every world whose islands do not all fit resident in
the RAM budget, it plans the cheapest set of islands to unload so the rest fit.

Objective (exact, lexicographic): minimise the total reload weight of the unloaded
islands, then the number unloaded. Weights come from
data/islands/disk-saver/ebb-eviction-v1.json (default 1 per island); pinned slots
(the home island) are never unloaded. The solver is an exact 0/1 knapsack DP over
(weight, count) maximising freed RAM; tests check it against a brute-force oracle.
For comparison it also reports two greedy orders (heaviest RAM first, and lowest
weight first) and how much worse each one is.

Read-only over the report and the config. Integers only, stdlib only, deterministic.

  python tools/streaming/ebb_eviction.py REPORT.json [--config CFG.json] [-o PLAN.json] [--strict]

Exit 0 = plan printed/written, 1 = --strict and some world cannot fit even after
unloading every unpinned island, 2 = refusal.
"""
import argparse
import json
import os
import sys

FORMAT = "daedalus-ebb-eviction"
ORACLE_LIMIT = 16
MAX_WEIGHT = 1000
MAX_ISLANDS = 512

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_CONFIG = os.path.join(ROOT, "data", "islands", "disk-saver", "ebb-eviction-v1.json")


class EvictionError(ValueError):
    pass


def _nat(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise EvictionError(f"{what}: expected a nonnegative integer")
    return v


def solve(items, need):
    """Exact plan. items = [(slot, ram_kib, weight)] (unpinned only); need = KiB to free.

    Returns (weight, count, sorted slots) of the lexicographically cheapest set freeing
    >= need, or None if even unloading all items cannot free enough.
    """
    if need <= 0:
        return (0, 0, [])
    if sum(r for _, r, _ in items) < need:
        return None
    items = sorted(items)
    n, wmax = len(items), sum(w for _, _, w in items)
    # best[w][c] = (freed, chosen-bitmask-as-tuple) max freed RAM using total weight w, count c
    NEG = None
    best = [[NEG] * (n + 1) for _ in range(wmax + 1)]
    best[0][0] = (0, ())
    for idx, (slot, ram, wt) in enumerate(items):
        for w in range(wmax, wt - 1, -1):
            for c in range(n, 0, -1):
                prev = best[w - wt][c - 1]
                if prev is None:
                    continue
                cand = (prev[0] + ram, prev[1] + (idx,))
                cur = best[w][c]
                # max freed; ties -> lexicographically smallest index tuple (deterministic)
                if cur is None or cand[0] > cur[0] or (cand[0] == cur[0] and cand[1] < cur[1]):
                    best[w][c] = cand
    for w in range(wmax + 1):
        for c in range(n + 1):
            b = best[w][c]
            if b is not None and b[0] >= need:
                return (w, c, sorted(items[i][0] for i in b[1]))
    return None  # unreachable: all-items set frees enough


def solve_oracle(items, need):
    """Brute force over every subset (tests only); returns (weight, count) or None."""
    n = len(items)
    if n > ORACLE_LIMIT:
        raise EvictionError("oracle: too many islands")
    best = None
    for mask in range(1 << n):
        pick = [items[i] for i in range(n) if mask >> i & 1]
        if sum(r for _, r, _ in pick) >= need:
            key = (sum(w for _, _, w in pick), len(pick))
            if best is None or key < best:
                best = key
    return best


def greedy(items, need, key):
    """Unload in `key` order until enough RAM is freed; (weight, count, slots) or None."""
    if need <= 0:
        return (0, 0, [])
    freed, w, slots = 0, 0, []
    for slot, ram, wt in sorted(items, key=key):
        if freed >= need:
            break
        freed += ram
        w += wt
        slots.append(slot)
    if freed < need:
        return None
    return (w, len(slots), sorted(slots))


HEAVIEST_FIRST = lambda it: (-it[1], it[0])  # noqa: E731
LIGHTEST_WEIGHT_FIRST = lambda it: (it[2], -it[1], it[0])  # noqa: E731


def load_config(cfg):
    if not isinstance(cfg, dict) or cfg.get("v") != 1:
        raise EvictionError("config: v must be 1")
    pinned = cfg.get("pinned_slots", [])
    if not isinstance(pinned, list):
        raise EvictionError("config: pinned_slots must be a list")
    pinned = {_nat(s, "pinned slot") for s in pinned}
    dw = _nat(cfg.get("default_weight", 1), "default_weight")
    weights = cfg.get("weights", {})
    if not isinstance(weights, dict):
        raise EvictionError("config: weights must be an object")
    out = {}
    for wid, m in weights.items():
        if not isinstance(m, dict):
            raise EvictionError(f"config: weights[{wid}] must be an object")
        for k, v in m.items():
            if not str(k).isdigit():
                raise EvictionError(f"config: weights[{wid}] slot key {k!r}")
            out[(wid, int(k))] = _nat(v, f"weight {wid}/{k}")
    for v in [dw, *out.values()]:
        if not 1 <= v <= MAX_WEIGHT:
            raise EvictionError(f"config: weights must be 1..{MAX_WEIGHT}")
    return pinned, dw, out


def read_report(doc):
    if not isinstance(doc, dict) or doc.get("format") != "daedalus-census-budget" or doc.get("version") != 1:
        raise EvictionError("report: format must be daedalus-census-budget v1")
    b = doc.get("budget")
    if not isinstance(b, dict):
        raise EvictionError("report: missing budget")
    budget = _nat(b.get("ram_budget_kib"), "ram_budget_kib")
    worlds = doc.get("worlds")
    if not isinstance(worlds, list):
        raise EvictionError("report: worlds must be a list")
    out, seen = [], set()
    for w in worlds:
        wid = w.get("id") if isinstance(w, dict) else None
        if not isinstance(wid, str) or wid in seen:
            raise EvictionError("report: bad or duplicate world id")
        seen.add(wid)
        isl = w.get("islands")
        if not isinstance(isl, list) or len(isl) > MAX_ISLANDS:
            raise EvictionError(f"report: world {wid} islands")
        rows, slots = [], set()
        for i in isl:
            if not isinstance(i, dict):
                raise EvictionError(f"report: world {wid} bad island")
            s = _nat(i.get("slot"), "slot")
            if s in slots:
                raise EvictionError(f"report: world {wid} duplicate slot {s}")
            slots.add(s)
            rows.append((s, _nat(i.get("ram_kib"), "ram_kib")))
        out.append((wid, sorted(rows)))
    return budget, sorted(out)


def _view(res):
    return None if res is None else {"weight": res[0], "count": res[1], "unload_slots": res[2]}


def plan(report_doc, cfg):
    budget, worlds = read_report(report_doc)
    pinned, dw, weights = load_config(cfg)
    out, summary = [], {"worlds": 0, "over_budget": 0, "cannot_fit": 0, "unloads": 0,
                        "greedy_heaviest_worse": 0, "greedy_weight_worse": 0}
    for wid, rows in worlds:
        total = sum(r for _, r in rows)
        need = total - budget
        items = [(s, r, weights.get((wid, s), dw)) for s, r in rows if s not in pinned]
        opt = solve(items, need)
        gh = greedy(items, need, HEAVIEST_FIRST)
        gw = greedy(items, need, LIGHTEST_WEIGHT_FIRST)
        summary["worlds"] += 1
        summary["over_budget"] += need > 0
        if opt is None:
            summary["cannot_fit"] += 1
        else:
            summary["unloads"] += opt[1]
            summary["greedy_heaviest_worse"] += gh[:2] > opt[:2]
            summary["greedy_weight_worse"] += gw[:2] > opt[:2]
        tide = "slack" if need <= 0 else ("stranded" if opt is None else "ebb")
        out.append({"id": wid, "total_ram_kib": total, "need_kib": max(0, need),
                    "pinned_slots": sorted(s for s, _ in rows if s in pinned),
                    "tide": tide, "optimal": _view(opt),
                    "greedy_heaviest_first": _view(gh), "greedy_lowest_weight_first": _view(gw)})
    return {"format": FORMAT, "version": 1, "ram_budget_kib": budget,
            "snapshot_date": report_doc.get("snapshot_date"),
            "objective": "min total reload weight, then min islands unloaded; pinned never unloaded",
            "summary": summary, "worlds": out}


def dumps(p):
    return json.dumps(p, sort_keys=True, indent=2) + "\n"


def _load(path):
    try:
        with open(path, "rb") as f:
            raw = f.read(4 * 1024 * 1024 + 1)
    except OSError as e:
        raise EvictionError(f"{path}: {e.strerror}")
    if len(raw) > 4 * 1024 * 1024:
        raise EvictionError(f"{path}: larger than 4 MiB")
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise EvictionError(f"{path}: not JSON ({e})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Plan which resident islands to unload first when RAM is over budget.")
    ap.add_argument("report")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("-o", "--output", help="new plan file (never overwritten)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when a world cannot fit at all")
    a = ap.parse_args(argv)
    try:
        p = plan(_load(a.report), _load(a.config))
        text = dumps(p)
        if a.output:
            try:
                with open(a.output, "x", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            except OSError as e:
                raise EvictionError(f"{a.output}: {e.strerror}")
    except EvictionError as e:
        print(f"ebb_eviction: refused: {e}", file=sys.stderr)
        return 2
    s = p["summary"]
    print(f"{s['worlds']} worlds: {s['over_budget']} over budget, {s['unloads']} islands to unload, "
          f"{s['cannot_fit']} stranded")
    if not a.output:
        sys.stdout.write(text)
    return 1 if a.strict and s["cannot_fit"] else 0


if __name__ == "__main__":
    sys.exit(main())
