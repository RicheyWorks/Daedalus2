#!/usr/bin/env python3
"""Glowmoss Delve balance simulation: win rates per difficulty for three scripted players.

  demo    the built-in demo (digs the exact best delve, so it always wins)
  greedy  a decent player: digs the safe ledge below that gathers the most crystals (lowest column on ties),
          climbs out as soon as the target is met or no safe dig is left
  random  digs a seeded random ledge below (safe or not), climbs out once the target is met or the floor is reached

Difficulty is tuned so the greedy player wins about 80% on easy, 50% on normal and 25% on hard.
Run `python tools/minigames/glowmoss_sim.py [--seeds N]`.
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glowmoss as gm  # noqa: E402


def safe_digs(g):
    """(crystals gathered, column) for every dig that keeps enough light to climb out."""
    out = []
    if g.row + 1 >= g.cfg["rows"]:
        return out
    for c in gm.dig_cols(g.col, g.cfg["cols"]):
        row, light, got, _, _ = gm.land(g.cfg, g.shaft(), g.row + 1, c, g.light)
        if light >= gm.climb_cost(row):
            out.append((got, c))
    return out


def greedy_action(g, _rng):
    options = safe_digs(g)
    if g.crystals >= g.target or not options:
        return ("climb", 0)
    best = max(got for got, _ in options)
    return ("dig", min(c for got, c in options if got == best))


def random_action(g, rng):
    if g.crystals >= g.target or g.row + 1 >= g.cfg["rows"]:
        return ("climb", 0)
    return ("dig", rng.choice(list(gm.dig_cols(g.col, g.cfg["cols"]))))


def demo_action(g, _rng):
    return g.demo_action()


PLAYERS = {"demo": demo_action, "greedy": greedy_action, "random": random_action}


def win_rate(player, difficulty, seeds):
    rng = random.Random("glowmoss-sim:%s:%s" % (player, difficulty))
    wins = 0
    for seed in range(seeds):
        g = gm.start(seed, difficulty)
        while not g.over:
            g.step(PLAYERS[player](g, rng))
        wins += g.won
    return wins / seeds


def table(seeds):
    return {d: {p: win_rate(p, d, seeds) for p in PLAYERS} for d in ("easy", "normal", "hard")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=400)
    a = ap.parse_args(argv)
    for d, row in table(a.seeds).items():
        print("%-6s " % d + "  ".join("%s %3.0f%%" % (p, 100 * r) for p, r in row.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
