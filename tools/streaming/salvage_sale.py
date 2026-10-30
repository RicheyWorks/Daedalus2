# SPDX-License-Identifier: MIT
"""Salvage Sale (G563, disk-saver): sealed-bid auction against a hungry rival broker.

Python dev tooling only; nothing here runs inside Unreal. Every census island (tools/world_census
output, read-only; up to six) puts one salvage lot up for sale, and seeded spare lots pad the
sale to five. Lots are sold in label order. Each lot has a value of 3 + its asset count mod 5,
plus a seeded 0-4. You and the Broker each start with a third of the total value in coin.

For each lot you write one sealed bid. The Broker's bid follows a rule Auctioneer Barnaby reads
out before the sale: half the lot's value (rounded down), plus 3 for every lot the Broker has
lost so far, capped by the coin it has left. The higher bid wins and pays its own bid. A tie
goes to the Broker. Your score is the total value of the lots you win; coin left over counts
for nothing.

The par is the best score possible against this rival, found by an exact search over (lot,
your coin, the Broker's coin, lots it has lost). The tests check it against a brute force over
every win-or-pass plan. The trap is winning every lot you can afford, shown as greedy_value.

  verdict   shrewd   par value won,
            fair     at least half of par,
            fleeced  less than half of par.

  python tools/streaming/salvage_sale.py CENSUS.json [--seed N] [--bids 0,7,5,... | --auto] [--json]

Deterministic, stdlib only, no clock. Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import functools
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-salvage-sale"
VERDICTS = ("shrewd", "fair", "fleeced")
MAX_LOTS = 6
MIN_LOTS = 5
HUNGER = 3


class SaleError(ValueError):
    pass


def broker_bid(value, coin, lost):
    return min(coin, value // 2 + HUNGER * lost)


def sale(census_doc, seed=0):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise SaleError(str(e))
    isl = sorted((f"{w}:{s}", a) for w, il in worlds for s, a in il)
    if not isl:
        raise SaleError("census has no islands to sell salvage")
    isl = isl[:MAX_LOTS]
    isl += [(f"spare:{k}", 0) for k in range(1, MIN_LOTS - len(isl) + 1)]
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in isl)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    values = [3 + a % 5 + rng.randrange(5) for _, a in isl]
    coin = sum(values) // 3
    return [l for l, _ in isl], values, coin


def run(values, coin, bids):
    """Play the bids; returns (score, log)."""
    mine, theirs, lost, score, log = coin, coin, 0, 0, []
    for i, (v, b) in enumerate(zip(values, bids)):
        if b > mine:
            raise SaleError(f"lot {i + 1}: bid {b} but only {mine} coin left")
        rb = broker_bid(v, theirs, lost)
        if b > rb:
            mine -= b
            score += v
            lost += 1
            won = "you"
        else:
            theirs -= rb
            won = "broker"
        log.append({"lot": i + 1, "value": v, "bid": b, "broker_bid": rb, "winner": won,
                    "coin_left": mine, "broker_coin": theirs})
    return score, log


def solve(values, coin):
    """(par, bids) by exact search; winning a lot only ever needs the Broker's bid + 1."""
    n = len(values)

    @functools.lru_cache(maxsize=None)
    def best(i, mine, theirs, lost):
        if i == n:
            return 0, ()
        rb = broker_bid(values[i], theirs, lost)
        s, plan = best(i + 1, mine, theirs - rb, lost)
        top = (s, (0,) + plan)
        if rb + 1 <= mine:
            s2, plan2 = best(i + 1, mine - rb - 1, theirs, lost + 1)
            if s2 + values[i] > top[0]:
                top = (s2 + values[i], (rb + 1,) + plan2)
        return top

    s, plan = best(0, coin, coin, 0)
    return s, list(plan)


def greedy(values, coin):
    mine, theirs, lost, score = coin, coin, 0, 0
    for v in values:
        rb = broker_bid(v, theirs, lost)
        if rb + 1 <= mine:
            mine -= rb + 1
            score += v
            lost += 1
        else:
            theirs -= rb
    return score


def play(census_doc, seed=0, bids=None, auto=False):
    lots, values, coin = sale(census_doc, seed)
    par, plan = solve(values, coin)
    r = {"format": FORMAT, "version": 1, "seed": seed, "lots": lots, "values": values,
         "coin": coin, "par": par, "greedy_value": greedy(values, coin)}
    if auto:
        bids = plan
    elif bids is None:
        r["verdict"] = None
        return r
    else:
        toks = [t.strip() for t in bids.split(",")]
        if len(toks) != len(lots) or not all(t.isdigit() for t in toks):
            raise SaleError(f"give {len(lots)} whole-number bids, one per lot")
        bids = [int(t) for t in toks]
    score, log = run(values, coin, bids)
    r.update({"bids": bids, "score": score, "log": log})
    r["verdict"] = "shrewd" if score >= par else ("fair" if 2 * score >= par else "fleeced")
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise SaleError(f"census: {e}")


def text(r):
    lines = [f"salvage sale: {len(r['lots'])} lots, {r['coin']} coin each; par {r['par']} value "
             f"(win-what-you-can habit: {r['greedy_value']}); seed {r['seed']}",
             f"  broker bids value//2 + {HUNGER} per lot it has lost, capped by its coin; ties go to the broker"]
    for k, (l, v) in enumerate(zip(r["lots"], r["values"]), 1):
        lines.append(f"  lot {k} {l}: value {v}")
    if r["verdict"]:
        for e in r["log"]:
            lines.append(f"  lot {e['lot']}: you {e['bid']} vs broker {e['broker_bid']} -> {e['winner']} "
                         f"(coin {e['coin_left']}, broker {e['broker_coin']})")
        lines.append(f"verdict: {r['verdict']} ({r['score']} value won, par {r['par']})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Salvage Sale: sealed bids against a hungry broker.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--bids", help="comma-separated bids, one per lot")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.bids, a.auto)
    except SaleError as e:
        print(f"salvage_sale: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
