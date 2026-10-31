# SPDX-License-Identifier: MIT
"""Prismheart hall chord, rules reference (mirrors DaedalusHallChordCore.h).

A slow ambient chord for the arcade hall from the cabinets being played. Input: (cabinet id, token) pairs.
Usage: python tools/minigames/hall_chord.py --write engines/unreal/core-test/hall_chord_golden.txt
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cue_kit  # noqa: E402

MAX_VOICES = 8
MAX_CANDIDATES = 32  # only the 32 lowest (id, token) keys are considered
GAIN_BUDGET = 600      # thousandths of full scale, summed over voices
GAIN_CAP = 200
LOW_CEIL = 330         # voice notes fold down to at most this
LOW_FLOOR = 82
HIGH_LIMIT = 700
CHORD_DEGREES = [0, 3, 2]  # root, fifth, third of the cabinet's kit scale
DRONE = (110, 120)


def clashes(hz, notes):
    """True when hz sits within about a semitone (under 6 %) of a different note."""
    return any(hz != n and 100 * abs(hz - n) < 6 * min(hz, n) for n in notes)


def low_note(game, token):
    k = cue_kit.make_kit(game, token)
    deg = CHORD_DEGREES[random.Random("hall|%s|%d" % (game, token)).randrange(3)]
    hz = k["step"](deg)
    while hz > LOW_CEIL:
        hz //= 2
    return hz


def chord(pairs):
    keys = sorted(set((g, int(t)) for g, t in pairs))[:MAX_CANDIDATES]
    hz_list, weight, dropped, over_cap = [], [], 0, 0
    for g, t in keys:
        hz = low_note(g, t)
        placed = False
        for cand in (hz, hz // 2 if hz // 2 >= LOW_FLOOR else None, hz * 2 if hz * 2 < HIGH_LIMIT else None):
            if cand is None:
                continue
            if cand in hz_list:
                weight[hz_list.index(cand)] += 1
                placed = True
                break
            if not clashes(cand, hz_list):
                if len(hz_list) >= MAX_VOICES:
                    over_cap += 1
                else:
                    hz_list.append(cand)
                    weight.append(1)
                placed = True
                break
        if not placed:
            dropped += 1
    if not hz_list:
        return {"voices": [DRONE], "attack": 6000, "release": 4000, "swell": 16000, "dropped": dropped, "over_cap": over_cap}
    total = sum(weight)
    voices = sorted((h, min(GAIN_CAP, GAIN_BUDGET * w // total)) for h, w in zip(hz_list, weight))
    return {"voices": voices, "attack": 3000 + 400 * len(voices), "release": 4000, "swell": 12000,
            "dropped": dropped, "over_cap": over_cap}


def cases():
    out = []
    for i in range(300):
        r = random.Random("hallcase|%d" % i)
        n = r.randrange(13) if i < 280 else 30 + r.randrange(20)
        out.append([(r.choice(cue_kit.GAMES), r.randrange(5)) for _ in range(n)])
    return out


def fmt(pairs, c):
    ins = ",".join("%s:%d" % p for p in pairs) or "-"
    vs = " ".join("%d/%d" % v for v in c["voices"])
    return "in %s | voices %s | env %d/%d/%d | dropped %d over %d" % (
        ins, vs, c["attack"], c["release"], c["swell"], c["dropped"], c["over_cap"])


def lines():
    out = ["# hall_chord_golden v1 (cue kit V2 + PyRandom 'hall|id|token'): in id:token,... | voices hz/gain ... | env attack/release/swell ms | dropped clashes, over cap"]
    for i, pairs in enumerate(cases()):
        out.append("%d %s" % (i, fmt(pairs, chord(pairs))))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--write":
        with open(sys.argv[2], "w", newline="\n") as f:
            f.write("\n".join(lines()) + "\n")
    else:
        print("\n".join(lines()[:6]))
