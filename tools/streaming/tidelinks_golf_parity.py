# SPDX-License-Identifier: MIT
"""G598 Tidelinks Golf golden fixture: Python writes the courses and cards that DaedalusDiskSaverTidelinksGolfCore.h replays.

Tidelinks Golf (DiskSaver Island, quest q_tidelinks_golf) is a C++ minigame core; this script is only its
fixture generator. A seeded links course has a few holes laid out on a straight line: each hole has a
length (a multiple of 10 m), a par (3 up to 220 m, 4 up to 400 m, else 5), a wind and an optional water
band. Each shot picks a club; the ball flies the club's carry plus 10 m per wind step (at least 10 m)
toward the pin, possibly past it. Landing in the water or more than 50 m beyond either end of the hole
costs a penalty stroke and the ball stays where it was. A ball landing on the pin is holed; the putter
holes out from 10 m or less and otherwise rolls 10 m toward the pin, ignoring the wind. A hole is
capped at 10 strokes, penalties included. The score is total strokes against par.

The core also plays three caddie habits (safe, bold, lay-up) and the exact best card (fewest strokes per
hole; ties go to the first club in club order, shot by shot).

The course comes from random.Random(seed string) through DaedalusPyRandomCore.h's string seeding, with
draws it supports: randrange(3) for the hole count; per hole randrange(41) for the length,
randrange(7) for the wind, random() < 0.7 for water and randrange(k) for its place; then shuffle (the
hole names; CPython's _randbelow loop).

  python tools/streaming/tidelinks_golf_parity.py            # print the golden file
  python tools/streaming/tidelinks_golf_parity.py --check    # exit 1 if the checked-in file is stale
  python tools/streaming/tidelinks_golf_parity.py --write    # rewrite it

Golden lines: `C name`; `S hex` (seed string, utf-8 hex) or `H len:wind:water,...` (a hand course, water
0 = none); `O L holes par`, `O R k name len par wind water` per hole, `O P habit card strokes` for safe,
bold, layup and best; then `M card` (holes split by `/`, clubs by `,`, `-` for an empty hole) answered by
`O m strokes topar verdict` or `O refused kind hole`. A hand course the core refuses is answered by
`O hand_refused kind` and has no plays.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GOLDEN = os.path.join(ROOT, "engines", "unreal", "core-test", "disksaver_tidelinks_golf_parity.txt")
CLUBS = (("D", 220), ("W", 190), ("5", 160), ("7", 130), ("9", 100), ("S", 60), ("C", 20), ("P", 0))
CODES = [c for c, _ in CLUBS]
CARRY = dict(CLUBS)
CAP = 10
OOB = 50
WATER = 20
HAND_MAX_HOLES = 9
NAMES = ("Anchor Reach", "Bellbuoy", "Capstan Rise", "Dunes", "Eelgrass", "Foghorn", "Gullwing",
         "Harbour Mouth", "Inkwell", "Jetty End", "Kelp Bed", "Lantern Point")


def par_of(length):
    return 3 if length <= 220 else 4 if length <= 400 else 5


def course(seed):
    r = random.Random(seed)
    n = 4 + r.randrange(3)
    holes = []
    for _ in range(n):
        length = 100 + 10 * r.randrange(41)
        wind = r.randrange(7) - 3
        wet = r.random() < 0.7
        spot = 30 + 10 * r.randrange((length - 70) // 10)
        holes.append((length, wind, spot if wet else 0))
    names = list(NAMES)
    r.shuffle(names)
    return [(names[k],) + h for k, h in enumerate(holes)]


def hand_error(hs):
    if not hs:
        return "no_holes"
    if len(hs) > HAND_MAX_HOLES:
        return "too_many_holes"
    for length, wind, water in hs:
        if not (30 <= length <= 600 and length % 10 == 0):
            return "length"
        if not -5 <= wind <= 5:
            return "wind"
        if water and not (water % 10 == 0 and 10 <= water <= length - 30):
            return "water"
    return None


def shot(hole, p, club):
    """(new position, penalty, holed) of one shot from p."""
    _, length, wind, water = hole
    d = length - p
    if club == "P":
        if abs(d) <= 10:
            return length, False, True
        return p + (10 if d > 0 else -10), False, False
    carry = max(10, CARRY[club] + 10 * wind)
    q = p + (carry if d > 0 else -carry)
    if q == length:
        return q, False, True
    if q < -OOB or q > length + OOB or (water and water <= q < water + WATER):
        return p, True, False
    return q, False, False


def play_hole(hole, clubs):
    """(strokes, error or None)."""
    p, strokes = 0, 0
    for k, c in enumerate(clubs):
        if c not in CARRY:
            return None, "club"
        q, pen, holed = shot(hole, p, c)
        strokes += 1 + pen
        if strokes > CAP:
            return None, "cap"
        p = q
        if holed:
            return (strokes, None) if k == len(clubs) - 1 else (None, "extra")
    return None, "short"


def best_hole(hole):
    length = hole[1]
    pos = list(range(-OOB, length + OOB + 1, 10))
    INF = 10 ** 9
    g = {p: INF for p in pos}
    changed = True
    while changed:
        changed = False
        for p in pos:
            for c in CODES:
                q, pen, holed = shot(hole, p, c)
                if pen:
                    continue
                v = 1 if holed else 1 + g[q]
                if v < g[p]:
                    g[p], changed = v, True
    plan, p = [], 0
    while True:
        for c in CODES:
            q, pen, holed = shot(hole, p, c)
            if not pen and (1 if holed else 1 + g[q]) == g[p]:
                break
        plan.append(c)
        if holed:
            return plan
        p = q


def habit_hole(hole, kind):
    length, water = hole[1], hole[3]
    p, plan, wet = 0, [], False
    while True:
        d = abs(length - p)
        pick = "P"
        if d > 10:
            for c in CODES[:-1]:
                carry = max(10, CARRY[c] + 10 * hole[2])
                if carry > (d if kind == "layup" else d + 10):
                    continue
                q = p + (carry if length > p else -carry)
                if (kind != "bold" or wet) and water and water <= q < water + WATER:
                    continue
                pick = c
                break
        q, pen, holed = shot(hole, p, pick)
        plan.append(pick)
        wet = wet or pen
        p = q
        if holed:
            return plan


def card_str(card):
    return "/".join(",".join(h) if h else "-" for h in card)


def play(holes, card):
    if len(card) != len(holes):
        return None, ("holes", 0)
    total = 0
    for k, (h, clubs) in enumerate(zip(holes, card)):
        s, e = play_hole(h, clubs)
        if e:
            return None, (e, k)
        total += s
    return total, None


def topar(n):
    return "E" if n == 0 else f"{n:+d}"


def plans(holes):
    return {"safe": [habit_hole(h, "safe") for h in holes], "bold": [habit_hole(h, "bold") for h in holes],
            "layup": [habit_hole(h, "layup") for h in holes], "best": [best_hole(h) for h in holes]}


def strokes_raw(holes, card):
    """Strokes of a card that always holes out, ignoring the cap (habits can go over it)."""
    t = 0
    for h, clubs in zip(holes, card):
        p = 0
        for c in clubs:
            p, pen, _ = shot(h, p, c)
            t += 1 + pen
    return t


def case(out, name, head, holes, rng):
    par = sum(par_of(h[1]) for h in holes)
    out += [f"C {name}", head, f"O L {len(holes)} {par}"]
    for k, (nm, length, wind, water) in enumerate(holes):
        out.append(f"O R {k} {nm.replace(' ', '_')} {length} {par_of(length)} {wind} {water}")
    pl = plans(holes)
    for nm in ("safe", "bold", "layup", "best"):
        out.append(f"O P {nm} {card_str(pl[nm])} {strokes_raw(holes, pl[nm])}")
    opt = strokes_raw(holes, pl["best"])
    hab = min(strokes_raw(holes, pl[k]) for k in ("safe", "bold", "layup"))
    b = pl["best"]
    rnd = [[rng.choice(CODES) for _ in range(rng.randrange(1, 6))] for _ in holes]
    cards = [b, pl["safe"], pl["bold"], pl["layup"], [["P"] * 12 for _ in holes], rnd,
             [["X"] + b[0]] + b[1:], [b[0][:-1]] + b[1:], [b[0] + ["P"]] + b[1:], b[:-1], b + [["P"]],
             [[]] + b[1:]]
    for c in cards:
        out.append(f"M {card_str(c) if c else 'none'}")
        t, e = play(holes, c)
        if e:
            out.append(f"O refused {e[0]} {e[1]}")
        else:
            v = "masterful" if t == opt else "steady" if t <= hab else "rough"
            out.append(f"O m {t} {topar(t - par)} {v}")


def lines():
    out = ["# disksaver tidelinks_golf parity v1: written by tools/streaming/tidelinks_golf_parity.py; do not edit"]
    rng = random.Random("tidelinks-golf fixture cards")
    seeds = [f"tidelinks-golf|2026-10-30|{s}" for s in (0, 1, 7, 42, -3)] + ["", "g", "tidelinks-golf|links",
                                                                            "unicode:\u00e9\u03bb\u2603"]
    seeds += [f"tidelinks-golf|bulk|{k}" for k in range(27)]
    for k, s in enumerate(seeds):
        case(out, f"seed{k}", "S x" + s.encode("utf-8").hex(), course(s), rng)
    hands = {"one_short_hole": [(30, 0, 0)], "ace_hole": [(220, 0, 0)], "ace_in_wind": [(250, 3, 0)],
             "headwind_long": [(600, -5, 300), (600, 5, 0)], "water_at_carry": [(400, 0, 220), (300, 0, 190)],
             "water_just_short": [(240, 0, 210)], "nine_holes": [(100 + 50 * k, (k % 11) - 5 if k < 11 else 0, 0) for k in range(9)],
             "putter_only": [(40, 0, 0)], "past_the_pin": [(200, 2, 0)]}
    for name, hs in hands.items():
        holes = [(f"Hand {k}", l, w, z) for k, (l, w, z) in enumerate(hs)]
        assert hand_error(hs) is None, name
        case(out, name, "H " + ",".join(f"{l}:{w}:{z}" for l, w, z in hs), holes, rng)
    bad = {"no_holes": [], "ten_holes": [(100, 0, 0)] * 10, "length_short": [(20, 0, 0)], "length_odd": [(105, 0, 0)],
           "wind_strong": [(200, 6, 0)], "headwind_strong": [(200, -6, 0)], "water_late": [(200, 0, 180)], "water_odd": [(200, 0, 55)]}
    for name, hs in bad.items():
        out += [f"C {name}", "H " + (",".join(f"{l}:{w}:{z}" for l, w, z in hs) or "-"), f"O hand_refused {hand_error(hs)}"]
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
        print("tidelinks golf parity " + ("up to date" if ok else "STALE (rerun --write)"))
        return 0 if ok else 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
