# SPDX-License-Identifier: MIT
"""Prismheart cue kits, Ruleset V2 rules reference (mirrors DaedalusCueKitCore.h BuildKit/CueOf).

Draws come from random.Random("cuekit|<game>|<token>").randrange, matching DaedalusPyRandomCore.h.
Usage: python tools/minigames/cue_kit.py --write engines/unreal/core-test/cue_kit_golden_v2.txt
"""
import random
import sys

ROOTS = [165, 175, 196, 220, 247, 262]
NUM = [1, 9, 5, 3, 5, 2]
DEN = [1, 8, 4, 2, 3, 1]
DEGREES = 6
MAX_NOTES = 12
MAX_STREAK = 8
CUES = ["start", "good", "miss", "win"]
GAMES = ["shardsong_crossing", "shardfall", "prismcairn", "wardens_accord", "facetlock", "prismvault", "lumenpath",
         "shardring", "glowmoss", "glimmerloom", "shadewatch", "spiritkite", "prismchime", "gantry_sweep",
         "fog_channel_pilot", "crane_cohorts", "reed_ceiling", "padovan_plinths", "dock_calipers", "lucky_feather"]


def make_kit(game, token):
    r = random.Random("cuekit|%s|%d" % (game, token))
    b = r.randrange
    root = ROOTS[b(6)]
    note = 90 + 10 * b(7)
    gap = 20 + 10 * b(3)
    step = lambda d: root * NUM[d] // DEN[d]
    start = [(step(b(DEGREES - 1)), note, gap) for _ in range(3)]
    gn = 2 + b(2)
    d0 = b(DEGREES - gn + 1)
    good = [(step(d0 + i), note, gap) for i in range(gn)]
    top = 2 + b(3)
    drop = 1 + b(min(top, 3))
    miss = [(step(top), note + 40, gap), (step(top - drop), note + 120, 0)]
    win, wd = [], b(3)
    for _ in range(3):
        win.append((step(wd), note, gap))
        wd = min(wd + 1 + b(2), DEGREES - 2)
    win.append((step(DEGREES - 1), note * 2, 0))
    return {"root": root, "note": note, "gap": gap, "cues": [start, good, miss, win], "step": step}


def streak(kit, days):
    days = max(0, min(MAX_STREAK, days))
    p = [(kit["step"](i % (DEGREES - 1)), kit["note"] // 2 + 30, kit["gap"] // 2) for i in range(days)]
    return (p + kit["cues"][3])[:MAX_NOTES]


def fmt(phrase):
    return "".join(" %d/%d/%d" % n for n in phrase)


def lines():
    out = ["# cue_kit_golden v2 (PyRandom 'cuekit|game|token'): game token root | cue: hz/ms/gap ..."]
    for g in GAMES:
        for t in range(30):
            k = make_kit(g, t)
            s = "%s %d %d |" % (g, t, k["root"])
            for name, ph in zip(CUES, k["cues"]):
                s += " %s:%s |" % (name, fmt(ph))
            s += " streak3:%s | streak8:%s" % (fmt(streak(k, 3)), fmt(streak(k, 8)))
            out.append(s)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--write":
        with open(sys.argv[2], "w", newline="\n") as f:
            f.write("\n".join(lines()) + "\n")
    else:
        print("\n".join(lines()[:3]))
