# SPDX-License-Identifier: MIT
"""Quench Window rules reference (Crafting + rewards lane) and golden-vector writer.

Rules authority for DaedalusQuenchWindowCore.h. A crafted piece leaves the fire hot and cools each tick by a seeded
amount; the player stops (quenches) it at one tick. Inside the temper band it is Tempered, within 10 of the band's
middle it is Perfect, above the band it stays Soft, below it Cracked. The curve comes from Python's random seeded with
the string "quench|<seed>" (reproduced in C++ by DaedalusPyRandomCore.h). Integer only.
`python quench_window_ref.py > quench_window_golden.txt`; `--check quench_window_golden.txt` verifies it.
"""
import random
import sys

TICKS = 12                 # cooling steps; heat[0..12]
HEAT0_BASE, HEAT0_SPAN = 900, 101      # start heat 900..1000
COOL_BASE, COOL_SPAN = 40, 41          # each tick cools 40..80
LO_BASE, LO_SPAN = 521, 81             # band low 521..601
BAND = 90                              # band high = low + 90 (wider than any one tick's cooling)
PERFECT = 10                           # within 10 of the band middle

SOFT, TEMPERED, PERFECT_Q, CRACKED = range(4)
OUTCOME = ["SOFT", "TEMPERED", "PERFECT", "CRACKED"]

def curve(seed):
    r = random.Random("quench|" + seed)
    heat = [HEAT0_BASE + r.randrange(HEAT0_SPAN)]
    for _ in range(TICKS):
        heat.append(heat[-1] - (COOL_BASE + r.randrange(COOL_SPAN)))
    lo = LO_BASE + r.randrange(LO_SPAN)
    return heat, lo, lo + BAND

def grade(heat, lo, hi, tick):
    """Outcome at a stop tick, or None for a tick outside 0..TICKS."""
    if not (0 <= tick <= TICKS):
        return None
    h = heat[tick]
    if h > hi:
        return SOFT
    if h < lo:
        return CRACKED
    mid = (lo + hi) // 2
    return PERFECT_Q if abs(h - mid) <= PERFECT else TEMPERED

def best_tick(heat, lo, hi):
    """Earliest tick whose heat is closest to the band middle."""
    mid = (lo + hi) // 2
    best = 0
    for t in range(TICKS + 1):
        if abs(heat[t] - mid) < abs(heat[best] - mid):
            best = t
    return best

def seeds():
    out = ["", "0", "1", "forge", "Hephaestus Island", "2026-10-30", "quench|nested", "a" * 64]
    r = random.Random(60695 + 2)
    for k in range(600):
        n = r.randint(1, 24)
        out.append("".join(r.choice("abcdefghijklmnopqrstuvwxyz0123456789-_ |") for _ in range(n)))
    return out

def write(f):
    f.write("# Quench Window golden vectors from quench_window_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# K <ticks> <band> <perfect> | Q <seed_len> <seed> | H <heat x13> <lo> <hi> <best_tick> | G <outcome per tick x13>\n")
    f.write("K %d %d %d\n" % (TICKS, BAND, PERFECT))
    for s in seeds():
        heat, lo, hi = curve(s)
        f.write("Q %d %s\n" % (len(s), s))
        f.write("H %s %d %d %d\n" % (" ".join(map(str, heat)), lo, hi, best_tick(heat, lo, hi)))
        f.write("G %s\n" % " ".join(OUTCOME[grade(heat, lo, hi, t)] for t in range(TICKS + 1)))

if __name__ == "__main__":
    import io
    buf = io.StringIO()
    write(buf)
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        with open(sys.argv[2], newline="") as g:
            same = g.read() == buf.getvalue()
        print("golden current" if same else "golden STALE")
        sys.exit(0 if same else 1)
    sys.stdout.write(buf.getvalue())
