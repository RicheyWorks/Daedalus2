# SPDX-License-Identifier: MIT
"""G590 Gantry Sweep golden fixture: Python writes the layouts and plays that DaedalusDiskSaverGantrySweepCore.h replays.

Gantry Sweep (DiskSaver Island, quest q_gantry_sweep) is a C++ minigame core; this script is only its
fixture generator. A gantry crane rides one quay rail of RAIL berths, like a disk head over cylinders.
Seeded ships ask for the crane: each has a berth and an arrival tick. The crane moves one berth per tick,
waits at a berth until the ship there has arrived, and serves it at once. The player picks the service
order; the score is the total ticks the ships wait (serve tick - arrival). The core also shows four
yard habits (first come first served, nearest arrived ship, the elevator sweep, the one-way sweep) and
the exact best order. Each seed names a tide profile: calm (arrivals over 24 ticks), rush (6: ships pile
up at once) or spread (60: the crane often idles).

The layout comes from random.Random(seed string), the only seeding that DaedalusPyRandomCore.h has, with
draws it supports: randrange(RAIL) and randrange(4) (_randbelow), sample(range(RAIL), n), random() (the
arrival ticks, int(random() * span) for the profile's span) and shuffle (the berth names). Every draw this script makes
is checked against that header's semantics by the C++ test that replays the file.

  python tools/streaming/gantry_sweep_parity.py            # print the golden file
  python tools/streaming/gantry_sweep_parity.py --check    # exit 1 if the checked-in file is stale
  python tools/streaming/gantry_sweep_parity.py --write    # rewrite it

Golden lines: `C name`; `S profile hex` (tide profile, seed string as utf-8 hex) or `H start pos:arrive,...` (a hand layout);
`O L start n`, `O R i label pos arrive` per ship, `O P policy order waits travel` for fcfs, sstf, scan, cscan, best;
then `M order` plays (comma-separated ship indices, `-` for none) answered by `O m waits travel verdict` or
`O refused kind` (short, long, range, repeat).
"""
import itertools
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GOLDEN = os.path.join(ROOT, "engines", "unreal", "core-test", "disksaver_gantry_sweep_parity.txt")
RAIL = 40
PROFILES = {"calm": 24, "rush": 6, "spread": 60}  # arrival span in ticks
MIN_SHIPS, MAX_SHIPS = 5, 8
BERTHS = ("anchor", "bollard", "capstan", "davit", "eyebolt", "fairlead", "gunwale", "hawser",
          "jetty", "keel", "lanyard", "mooring")


def layout(seed, profile="calm"):
    span = PROFILES[profile]
    r = random.Random(seed)
    start = r.randrange(RAIL)
    n = MIN_SHIPS + r.randrange(MAX_SHIPS - MIN_SHIPS + 1)
    pos = r.sample(range(RAIL), n)
    arrive = [int(r.random() * span) for _ in range(n)]
    names = list(BERTHS)
    r.shuffle(names)
    return start, [(names[i], pos[i], arrive[i]) for i in range(n)]


def run(start, ships, order):
    t, x, waits, travel = 0, start, 0, 0
    for i in order:
        _, p, a = ships[i]
        travel += abs(p - x)
        t += abs(p - x)
        x = p
        t = max(t, a)
        waits += t - a
    return waits, travel


def _fallback(ships, left, x):
    return min(left, key=lambda i: (ships[i][2], abs(ships[i][1] - x), i))


def fcfs(start, ships):
    return sorted(range(len(ships)), key=lambda i: (ships[i][2], ships[i][1], i))


def sstf(start, ships):
    t, x, left, out = 0, start, set(range(len(ships))), []
    while left:
        ready = [i for i in left if ships[i][2] <= t]
        i = min(ready, key=lambda i: (abs(ships[i][1] - x), ships[i][1], i)) if ready else _fallback(ships, left, x)
        t = max(t + abs(ships[i][1] - x), ships[i][2])
        x = ships[i][1]
        left.discard(i)
        out.append(i)
    return out


def scan(start, ships):
    t, x, d, left, out = 0, start, 1, set(range(len(ships))), []
    while left:
        ready = [i for i in left if ships[i][2] <= t]
        if ready:
            ahead = [i for i in ready if (ships[i][1] - x) * d >= 0]
            if not ahead:
                d = -d
                ahead = ready
            i = min(ahead, key=lambda i: (abs(ships[i][1] - x), i))
        else:
            i = _fallback(ships, left, x)
            if ships[i][1] != x:
                d = 1 if ships[i][1] > x else -1
        t = max(t + abs(ships[i][1] - x), ships[i][2])
        x = ships[i][1]
        left.discard(i)
        out.append(i)
    return out


def cscan(start, ships):
    """The one-way sweep (C-SCAN): serve the nearest arrived ship at or above the crane; when none is
    above, run back to the lowest arrived ship and sweep up again; idle, go to the next arrival."""
    t, x, left, out = 0, start, set(range(len(ships))), []
    while left:
        ready = [i for i in left if ships[i][2] <= t]
        if ready:
            ahead = [i for i in ready if ships[i][1] >= x]
            i = min(ahead, key=lambda i: (ships[i][1], i)) if ahead else min(ready, key=lambda i: (ships[i][1], i))
        else:
            i = _fallback(ships, left, x)
        t = max(t + abs(ships[i][1] - x), ships[i][2])
        x = ships[i][1]
        left.discard(i)
        out.append(i)
    return out


HABITS = (("fcfs", fcfs), ("sstf", sstf), ("scan", scan), ("cscan", cscan))


def best(start, ships):
    top = None
    for p in itertools.permutations(range(len(ships))):
        w = run(start, ships, p)[0]
        if top is None or w < top[0]:
            top = (w, list(p))
    return top[1]


def play(start, ships, order):
    n = len(ships)
    if len(order) < n:
        return "O refused short"
    if len(order) > n:
        return "O refused long"
    if any(not 0 <= i < n for i in order):
        return "O refused range"
    if len(set(order)) != n:
        return "O refused repeat"
    w, tr = run(start, ships, order)
    opt = run(start, ships, best(start, ships))[0]
    habit = min(run(start, ships, f(start, ships))[0] for _, f in HABITS)
    verdict = "sweet" if w == opt else "fair" if w <= habit else "jammed"
    return f"O m {w} {tr} {verdict}"


def j(order):
    return ",".join(map(str, order)) if order else "-"


def case(out, name, head, start, ships, plays):
    out.append(f"C {name}")
    out.append(head)
    out.append(f"O L {start} {len(ships)}")
    for i, (l, p, a) in enumerate(ships):
        out.append(f"O R {i} {l} {p} {a}")
    for nm, f in HABITS + (("best", best),):
        o = f(start, ships)
        w, tr = run(start, ships, o)
        out.append(f"O P {nm} {j(o)} {w} {tr}")
    for o in plays:
        out.append(f"M {j(o)}")
        out.append(play(start, ships, o))


def plays_for(start, ships, rng):
    n = len(ships)
    ident = list(range(n))
    rev = ident[::-1]
    shuffled = ident[:]
    rng.shuffle(shuffled)  # a fixture-only Random: picks a play, not part of the layout
    return [best(start, ships), ident, rev, shuffled, fcfs(start, ships), sstf(start, ships), scan(start, ships), cscan(start, ships), ident[:-1], ident + [0], ident[:-1] + [n],
            ident[:-1] + [0], []]


def lines():
    out = ["# disksaver gantry_sweep parity v2: written by tools/streaming/gantry_sweep_parity.py; do not edit"]
    pick = random.Random("gantry-sweep fixture plays")
    seeds = [f"gantry-sweep|2026-10-26|{s}" for s in (0, 1, 7, 42, -3)] + ["", "a", "gantry-sweep|keel",
                                                                          "unicode:\u00e9\u03bb\u2603"]
    seeds += [f"gantry-sweep|bulk|{k}" for k in range(24)]
    tides = [(s, "calm") for s in seeds]
    tides += [(f"gantry-sweep|rush|{k}", "rush") for k in range(8)] + [(f"gantry-sweep|spread|{k}", "spread") for k in range(8)]
    tides += [("gantry-sweep|2026-10-26|42", "rush"), ("gantry-sweep|2026-10-26|42", "spread")]  # one seed, three tides
    for k, (s, prof) in enumerate(tides):
        start, ships = layout(s, prof)
        case(out, f"seed{k}", f"S {prof} x" + s.encode("utf-8").hex(), start, ships, plays_for(start, ships, pick))
    hands = {"one_ship_waiting": (0, [(0, 5)]), "already_there": (7, [(7, 0), (7, 3)]),
             "far_rail": (0, [(1000000, 0), (0, 1000000000), (500000, 999999999)]),
             "all_at_once": (20, [(p, 0) for p in (3, 39, 21, 19, 0, 38, 2, 22)]),
             "staggered": (10, [(i * 5, 30 - 3 * i) for i in range(8)]),
             "scan_turns": (20, [(25, 0), (15, 0), (30, 1), (5, 2), (35, 9)])}
    for name, (start, hs) in hands.items():
        ships = [(f"berth{i}", p, a) for i, (p, a) in enumerate(hs)]
        head = f"H {start} " + ",".join(f"{p}:{a}" for p, a in hs)
        case(out, name, head, start, ships, plays_for(start, ships, pick))
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
        print("gantry sweep parity " + ("up to date" if ok else "STALE (rerun --write)"))
        return 0 if ok else 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
