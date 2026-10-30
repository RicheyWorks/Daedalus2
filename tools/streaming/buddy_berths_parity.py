# SPDX-License-Identifier: MIT
"""G597 Buddy Berths golden fixture: Python writes the layouts and plays that DaedalusDiskSaverBuddyBerthsCore.h replays.

Buddy Berths (DiskSaver Island, quest q_buddy_berths) is a C++ minigame core; this script is only its
fixture generator. The long quay is QUAY berth units split buddy-style: a ship of size 2^k may only moor
on an aligned run of 2^k free units (offset % size == 0), the way a buddy allocator hands out blocks.
Seeded ships arrive one by one; each stays for a few later arrivals and then sails, freeing its run.
For every arrival the player names an offset or turns the ship away (`-`); a ship that finds no aligned
run must be turned away. Score: ships turned away. The core also shows three dock habits (lowest offset,
tightest fit, highest offset) and the exact best plan (search over every choice, memoised).

The layout comes from random.Random(seed string) (string seeding through DaedalusPyRandomCore.h), with draws
it supports: randrange(4) for the ship count, per ship int(random() * 4) for the size exponent and
randrange(5) for the stay, then shuffle (the ship names; CPython's _randbelow loop).

  python tools/streaming/buddy_berths_parity.py            # print the golden file
  python tools/streaming/buddy_berths_parity.py --check    # exit 1 if the checked-in file is stale
  python tools/streaming/buddy_berths_parity.py --write    # rewrite it

Golden lines: `C name`; `S hex` (seed string, utf-8 hex) or `H size:stay,...` (a hand layout); `O L n`,
`O R k name size stay` per ship, `O P habit plan turned` for lowest, tightest, highest and best; then
`M plan` (comma-separated offsets or `-`; `none` for an empty plan) answered by `O m turned verdict` or `O refused kind`.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GOLDEN = os.path.join(ROOT, "engines", "unreal", "core-test", "disksaver_buddy_berths_parity.txt")
QUAY = 16
MIN_SHIPS = 7
NAMES = ("albatross", "brigantine", "coracle", "dhow", "felucca", "galleon", "junk", "ketch",
         "lugger", "pinnace", "schooner", "yawl")


def layout(seed):
    r = random.Random(seed)
    n = MIN_SHIPS + r.randrange(4)
    ships = []
    for _ in range(n):
        size = 1 << int(r.random() * 4)
        stay = 1 + r.randrange(5)
        ships.append((size, stay))
    names = list(NAMES)
    r.shuffle(names)
    return [(names[k], s, t) for k, (s, t) in enumerate(ships)]


def leaving(ships, j):
    """Ships that sail just before arrival j (ship k leaves before arrival k + stay)."""
    return [k for k, (_, _, t) in enumerate(ships) if k + t == j]


def free_at(occ, o, s):
    return o % s == 0 and o + s <= QUAY and not any(occ[o:o + s])


def options(occ, s):
    return [o for o in range(0, QUAY, s) if free_at(occ, o, s)]


def sail(ships, plan, j, occ, live):
    for k in leaving(ships, j):
        if k in live:
            o = live.pop(k)
            for c in range(o, o + ships[k][1]):
                occ[c] = 0


def simulate(ships, plan):
    """(turned, error kind or None) of a full plan: offsets or None per arrival."""
    if len(plan) != len(ships):
        return None, "length"
    occ, live, turned = [0] * QUAY, {}, 0
    for j, o in enumerate(plan):
        sail(ships, plan, j, occ, live)
        s = ships[j][1]
        if o is None:
            turned += 1
            continue
        if not (0 <= o < QUAY and o % s == 0 and o + s <= QUAY):
            return None, "align"
        if any(occ[o:o + s]):
            return None, "busy"
        for c in range(o, o + s):
            occ[c] = 1
        live[j] = o
    return turned, None


def habit(ships, pick):
    occ, live, plan = [0] * QUAY, {}, []
    for j in range(len(ships)):
        sail(ships, plan, j, occ, live)
        s = ships[j][1]
        opts = options(occ, s)
        o = pick(occ, s, opts) if opts else None
        plan.append(o)
        if o is not None:
            for c in range(o, o + s):
                occ[c] = 1
            live[j] = o
    return plan


def lowest(occ, s, opts):
    return opts[0]


def highest(occ, s, opts):
    return opts[-1]


def room(occ, o, s):
    """Size of the largest aligned free run holding [o, o+s)."""
    while s < QUAY and free_at(occ, o - o % (2 * s), 2 * s):
        o, s = o - o % (2 * s), 2 * s
    return s


def tightest(occ, s, opts):
    return min(opts, key=lambda o: (room(occ, o, s), o))


def best(ships):
    """Fewest turned away; ties go to the first choice in offset order, `-` last. Memo key: per unit, the
    arrival before which its ship sails (0 = free), so ships that free the same units at the same time merge."""
    n = len(ships)
    memo = {}

    def go(j, cells):
        if j == n:
            return 0, ()
        key = (j, cells)
        if key in memo:
            return memo[key]
        occ = [1 if d > j else 0 for d in cells]
        free = tuple(d if d > j else 0 for d in cells)
        s, t = ships[j][1], ships[j][2]
        top = None
        for o in options(occ, s) + [None]:
            nc = list(free)
            if o is not None:
                for c in range(o, o + s):
                    nc[c] = j + t
            r, rest = go(j + 1, tuple(nc))
            r += o is None
            if top is None or r < top[0]:
                top = (r, (o,) + rest)
        memo[key] = top
        return top

    return list(go(0, (0,) * QUAY)[1])


def j(plan):
    return ",".join("-" if o is None else str(o) for o in plan) if plan else "none"


def play_line(ships, plan):
    t, e = simulate(ships, plan)
    if e:
        return f"O refused {e}"
    opt = simulate(ships, best(ships))[0]
    hab = min(simulate(ships, habit(ships, f))[0] for f in (lowest, tightest, highest))
    return f"O m {t} " + ("snug" if t == opt else "fair" if t <= hab else "crowded")


def plays_for(ships, rng):
    n = len(ships)
    rnd = [rng.randrange(QUAY) for _ in range(n)]  # a fixture-only Random: random offsets, often refused
    b = best(ships)
    mis = list(b)
    k = next((i for i in range(n) if ships[i][1] > 1), 0)
    mis[k] = (QUAY - 1) if ships[k][1] == 1 else (b[k] or 0) + 1
    clash = [0] * n
    return [b, habit(ships, lowest), habit(ships, tightest), habit(ships, highest), [None] * n, rnd,
            b[:-1], b + [None], mis, clash]


def case(out, name, head, ships, rng):
    out += [f"C {name}", head, f"O L {len(ships)}"]
    for k, (nm, s, t) in enumerate(ships):
        out.append(f"O R {k} {nm} {s} {t}")
    for nm, plan in (("lowest", habit(ships, lowest)), ("tightest", habit(ships, tightest)),
                     ("highest", habit(ships, highest)), ("best", best(ships))):
        out.append(f"O P {nm} {j(plan)} {simulate(ships, plan)[0]}")
    for p in plays_for(ships, rng):
        out.append(f"M {j(p)}")
        out.append(play_line(ships, p))


def lines():
    out = ["# disksaver buddy_berths parity v1: written by tools/streaming/buddy_berths_parity.py; do not edit"]
    rng = random.Random("buddy-berths fixture plays")
    seeds = [f"buddy-berths|2026-10-26|{s}" for s in (0, 1, 7, 42, -3)] + ["", "b", "buddy-berths|keel",
                                                                          "unicode:\u00e9\u03bb\u2603"]
    seeds += [f"buddy-berths|bulk|{k}" for k in range(27)]
    for k, s in enumerate(seeds):
        case(out, f"seed{k}", "S x" + s.encode("utf-8").hex(), layout(s), rng)
    hands = {"one_dinghy": [(1, 1)], "whole_quay": [(16, 1), (1, 1)], "four_eights": [(8, 4)] * 4,
             "halves_then_whole": [(8, 2), (8, 2), (16, 1), (1, 4)],
             "fragmenting_ones": [(1, 4)] * 5 + [(8, 1), (4, 2), (8, 1)],
             "ten_long_stays": [(4, 4), (2, 4), (8, 4), (1, 4), (4, 4), (2, 4), (8, 4), (1, 4), (4, 4), (2, 4)]}
    for name, hs in hands.items():
        ships = [(f"ship{k}", s, t) for k, (s, t) in enumerate(hs)]
        case(out, name, "H " + ",".join(f"{s}:{t}" for s, t in hs), ships, rng)
    return out


def main(argv):
    text = "\n".join(lines()) + "\n"
    if "--write" in argv:
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return 0
    if "--check" in argv:
        try:
            with open(GOLDEN, encoding="utf-8") as f:
                ok = f.read() == text
        except OSError:
            ok = False
        print("buddy berths parity " + ("up to date" if ok else "STALE (rerun --write)"))
        return 0 if ok else 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
