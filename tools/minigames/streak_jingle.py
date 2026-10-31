# SPDX-License-Identifier: MIT
"""Prismheart streak jingle, rules reference (mirrors DaedalusStreakJingleCore.h).

Usage: python tools/minigames/streak_jingle.py --write engines/unreal/core-test/streak_jingle_golden.txt
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cue_kit  # noqa: E402

TOKENS = 10


def ladder(game, token):
    r = random.Random("jingle|%s|%d" % (game, token))
    prev = r.randrange(5)
    out = [prev]
    for _ in range(cue_kit.MAX_STREAK - 1):
        prev = (prev + 1 + r.randrange(4)) % 5
        out.append(prev)
    return out


def jingle(game, token, days):
    k = cue_kit.make_kit(game, token)
    days = max(0, min(cue_kit.MAX_STREAK, days))
    added = [(k["step"](d), k["note"] // 2 + 30, k["gap"] // 2) for d in ladder(game, token)[:days]]
    return added + k["cues"][3]


def lines():
    out = ["# streak_jingle_golden v1 (PyRandom 'jingle|game|token' over cue kit V2): game token days | hz/ms/gap ..."]
    for g in cue_kit.GAMES:
        for t in range(TOKENS):
            for d in range(10):
                out.append("%s %d %d |%s" % (g, t, d, cue_kit.fmt(jingle(g, t, d))))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--write":
        with open(sys.argv[2], "w", newline="\n") as f:
            f.write("\n".join(lines()) + "\n")
    else:
        print("\n".join(lines()[:4]))
