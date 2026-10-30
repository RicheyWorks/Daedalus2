#!/usr/bin/env python3
"""Fair Par for the Prismheart cabinets (G603, Prismheart balance lane, Pythagoras; G600/G602 did the marsh).

A seeded casual bot plays each cabinet on every difficulty over many game seeds. These cabinets already have a win
target, so BRONZE is any win (par 1; a lost round scores 0). SILVER and GOLD come from the bot's winning rounds: the
scores reached by at least 40 % and 10 % of them, by the same integer rank rule as FairPar.java. Read-only on the
games' rules: the bot only calls start(), step() and the public helpers each game already exposes.

The bot's choices come from the stateless SplitMix64 hash of (seed, run, pick, salt) used by FairPar.java, so the
choices never touch the game's own RNG. Pars are integers (the games score in integers).

  python tools/minigames/fair_par.py            print the par table
  python tools/minigames/fair_par.py --write    rewrite engines/unreal/core-test/prism_fair_par_parity.txt
  python tools/minigames/fair_par.py --check    fail if that fixture is stale
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glimmerloom  # noqa: E402
import facetlock  # noqa: E402
import glowmoss  # noqa: E402
import lumenpath  # noqa: E402
import prismcairn  # noqa: E402
import prism_shard  # noqa: E402
import prismvault  # noqa: E402
import shadewatch  # noqa: E402
import shardfall  # noqa: E402
import spiritkite  # noqa: E402
import wardens_accord  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "engines", "unreal", "core-test",
                       "prism_fair_par_parity.txt")
WIN_PERCENT = (40, 10)
TIERS = ("NONE", "BRONZE", "SILVER", "GOLD")
DIFFICULTIES = ("easy", "normal", "hard")
SEEDS = 400
BOT_SEED = 600
MASK = (1 << 64) - 1
STEP_LIMIT = 500


def uniform(seed, run, pick, salt):
    """Uniform in [0, 1): SplitMix64 finalizer of (seed, run, pick, salt), bit-identical to FairPar.uniform."""
    z = (seed + 0x9E3779B97F4A7C15 * (run + 1) + 0xBF58476D1CE4E5B9 * (pick + 1)
         + 0x94D049BB133111EB * (salt + 1)) & MASK
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    z ^= z >> 31
    return (z >> 11) * 2.0 ** -53


def pick(seed, run, k, salt, bound):
    """Uniform integer in [0, bound]."""
    return min(bound, int(uniform(seed, run, k, salt) * (bound + 1)))


def glowmoss_bot(g, run, k):
    """Careful casual delver: climbs out once the target is met; otherwise digs a random ledge that still leaves
    light to climb out, and climbs when there is none."""
    if g.crystals >= g.target or g.row + 1 >= g.cfg["rows"]:
        return ("climb", 0)
    safe = []
    for c in glowmoss.dig_cols(g.col, g.cfg["cols"]):
        row, light, _, _, _ = glowmoss.land(g.cfg, g.shaft(), g.row + 1, c, g.light)
        if light >= glowmoss.climb_cost(row):
            safe.append(c)
    if not safe:
        return ("climb", 0)
    return ("dig", safe[pick(BOT_SEED, run, k, 0, len(safe) - 1)])


def spiritkite_bot(g, run, k):
    """Careful casual pilot: flies random lanes that keep a way home; heads home (shortest lane first) once the
    target is met or no safe lane is left, and lands on the anchor."""
    home = g.lanterns() >= g.target
    safe = sorted(j for j, w in g.adj[g.at].items() if g.dist[j][0] <= g.wind - w)
    if not home and safe:
        return ("fly", safe[pick(BOT_SEED, run, k, 1, len(safe) - 1)])
    if g.at == 0:
        return ("land", 0)
    return ("fly", min(g.adj[g.at], key=lambda u: (g.adj[g.at][u] + g.dist[u][0], u)))


def glimmerloom_bot(g, run, k):
    """Casual trader: sells what the rumor does not favour, buys a random amount of the hue rumored to rise,
    then rests."""
    for j, q in enumerate(g.satchel):
        if q and g.rumor != [j, "rise"]:
            return ("sell", j, q)
    hue, word = g.rumor
    if word == "rise" and g.day < g.cfg["days"] and g.satchel[hue] == 0:
        most = min(g.purse // g.prices[hue], g.cfg["satchel"] - g.held())
        q = pick(BOT_SEED, run, k, 2, max(0, most))
        if q > 0:
            return ("buy", hue, q)
    return ("rest", 0, 0)


def mixed(random_move):
    """Casual bot for puzzle cabinets (G604 on): each move, a coin flip (salt 9) either follows the game's own
    demo_action() (a player who sees the right idea) or makes a random legal move."""
    def bot(g, run, k):
        if uniform(BOT_SEED, run, k, 9) < 0.5:
            return g.demo_action()
        return random_move(g, run, k)
    return bot


def lumenpath_random(g, run, k):
    """Toggle a random cell that can hold a mirror (row-major order)."""
    n = len(g.grid)
    cells = [(r, c) for r in range(n) for c in range(n) if g.grid[r][c] not in "*#"]
    return cells[pick(BOT_SEED, run, k, 10, len(cells) - 1)]


def wardens_random(g, run, k):
    """Take one of the three offers or summon any affordable spirit, uniformly."""
    options = [("take", i) for i in range(3)] + [("summon", i) for i in range(len(g.spirits)) if g.affordable(i)]
    return options[pick(BOT_SEED, run, k, 11, len(options) - 1)]


def facetlock_random(g, run, k):
    """Slide a random row or column either way: v in [0, 4n) -> kind by v % 2, index (v // 2) % n, dir by v // 2n."""
    n = g.cfg["size"]
    v = pick(BOT_SEED, run, k, 12, 4 * n - 1)
    return ("r" if v % 2 == 0 else "c", (v // 2) % n, 1 if v // (2 * n) == 0 else -1)


def prismvault_random(g, run, k):
    """Guess early: name a random remaining candidate."""
    c = g.candidates
    return ("name", c[pick(BOT_SEED, run, k, 13, len(c) - 1)])


def shardfall_random(g, run, k):
    """Draw or bank on a fair coin (bank when the seam is empty)."""
    return "bank" if not g.bag or pick(BOT_SEED, run, k, 14, 1) == 1 else "draw"


def prismcairn_random(g, run, k):
    """Any legal take, uniformly: cairns in order, then 1..limit."""
    m = g.cfg["take_max"]
    options = [(i, t) for i, h in enumerate(g.cairns) for t in range(1, min(m, h) + 1)]
    return options[pick(BOT_SEED, run, k, 15, len(options) - 1)]


def shadewatch_random(g, run, k):
    """Flare any lane, kindle, or nova when there is light for it, uniformly."""
    options = [("flare", i) for i in range(len(g.lanes))] + [("kindle", 0)]
    options += [("nova", 0)] if g.light >= shadewatch.NOVA_COST else []
    return options[pick(BOT_SEED, run, k, 16, len(options) - 1)]


class ShardringPlay:
    """Step/demo_action view of prism_shard.ShardringGame (it predates PrismGame): demo = greedy_move."""

    def __init__(self, seed, difficulty):
        self.game = prism_shard.start(seed, difficulty)
        self.rng = self.game.rng

    over = property(lambda self: self.game.over)
    won = property(lambda self: self.game.won)
    score = property(lambda self: self.game.score)

    def step(self, facet):
        return self.game.place(facet)

    def demo_action(self):
        return prism_shard.greedy_move(self.game)


def shardring_random(g, run, k):
    """Set the shard in any empty facet, uniformly."""
    empty = g.game.empty_facets()
    return empty[pick(BOT_SEED, run, k, 17, len(empty) - 1)]


GAMES = (("glowmoss", glowmoss.start, glowmoss_bot), ("spiritkite", spiritkite.start, spiritkite_bot),
         ("glimmerloom", glimmerloom.start, glimmerloom_bot),
         ("lumenpath", lumenpath.start, mixed(lumenpath_random)),
         ("wardens_accord", wardens_accord.start, mixed(wardens_random)),
         ("facetlock", facetlock.start, mixed(facetlock_random)),
         ("prismvault", prismvault.start, mixed(prismvault_random)),
         ("shardfall", shardfall.start, mixed(shardfall_random)),
         ("prismcairn", prismcairn.start, mixed(prismcairn_random)),
         ("shadewatch", shadewatch.start, mixed(shadewatch_random)),
         ("shardring", ShardringPlay, mixed(shardring_random)))


def bot_round(start, bot, seed, difficulty):
    """One bot round: final score if won, else 0."""
    g = start(seed, difficulty)
    for k in range(STEP_LIMIT):
        if g.over:
            break
        g.step(bot(g, seed, k))
    return g.score if g.won else 0


def demo_round(start, seed, difficulty):
    g = start(seed, difficulty)
    for _ in range(STEP_LIMIT):
        if g.over:
            break
        g.step(g.demo_action())
    return g.score if g.won else 0


def calibrate(scores):
    """([bronze, silver, gold], hits per mille of all rounds, median winning score). Bronze is any win (par 1);
    silver and gold use the FairPar integer rank rule on the winning rounds; 0 when the bot never wins."""
    n = len(scores)
    won = sorted(v for v in scores if v > 0)
    w = len(won)
    pars = [1]
    for p in WIN_PERCENT:
        pars.append(won[w - max(1, (w * p + 99) // 100)] if w else 0)
    hits = [sum(1 for v in scores if v >= par and v > 0) * 1000 // n for par in pars]
    return pars, hits, won[(w - 1) // 2] if w else 0


def won_min(scores):
    """Lowest winning score, or 0 when the bot never wins."""
    return min((v for v in scores if v > 0), default=0)


def tier(pars, score):
    """Tier name for a score (a lost round scores 0 and earns NONE)."""
    if score <= 0:
        return "NONE"
    out = "NONE"
    for name, par in zip(TIERS[1:], pars):
        if score >= par:
            out = name
    return out


def table(seeds=SEEDS):
    rows = []
    for game, start, bot in GAMES:
        for d in DIFFICULTIES:
            scores = [bot_round(start, bot, s, d) for s in range(seeds)]
            demo = [demo_round(start, s, d) for s in range(seeds)]
            pars, hits, median = calibrate(scores)
            wins = sum(1 for v in scores if v > 0)
            demo_wins = sum(1 for v in demo if v > 0)
            rows.append({"game": game, "difficulty": d, "seeds": seeds, "bronze": pars[0], "silver": pars[1],
                         "gold": pars[2], "hits": hits, "median": median, "botWin": wins * 1000 // seeds,
                         "demoWin": demo_wins * 1000 // seeds, "demoMedian": sorted(demo)[(seeds - 1) // 2],
                         "separated": 0 < won_min(scores) < pars[1] < pars[2]})
    return rows


def lines(seeds=SEEDS):
    out = ["# Prismheart Fair Par golden vectors: written by tools/minigames/fair_par.py, replayed by "
           "prism_fair_par_core_test.cpp."]
    for r in table(seeds):
        out.append("game=%s difficulty=%s seeds=%d bronze=%d silver=%d gold=%d bronzeHit=%d silverHit=%d goldHit=%d "
                   "winMedian=%d botWin=%d demoWin=%d demoMedian=%d separated=%s" % (
                       r["game"], r["difficulty"], r["seeds"], r["bronze"], r["silver"], r["gold"], r["hits"][0],
                       r["hits"][1], r["hits"][2], r["median"], r["botWin"], r["demoWin"], r["demoMedian"],
                       "true" if r["separated"] else "false"))
    for run in range(4):
        out.append("hash run=%d u=%r pick=%d" % (run, uniform(41, run, 2, 3), pick(41, run, 1, 0, 6)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    body = "\n".join(lines()) + "\n"
    if a.write:
        with open(FIXTURE, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        return 0
    if a.check:
        with open(FIXTURE, encoding="utf-8") as f:
            if f.read() != body:
                print("prism_fair_par_parity.txt is stale: run python tools/minigames/fair_par.py --write")
                return 1
        return 0
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
