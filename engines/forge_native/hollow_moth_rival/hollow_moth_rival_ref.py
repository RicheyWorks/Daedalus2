# SPDX-License-Identifier: MIT
"""Hollow Moth rival rules reference (Prismheart Round 2 lane R2-9, hephaestus) and golden-vector writer.

Rules authority for DaedalusHollowMothRivalCore.h. Once the Prism Satchel holds 3 Heartglass seals (heartglass()),
the secret Hollow Moth rival appears. Each round it challenges you in one cabinet where you do not hold Heartglass yet
(any cabinet once you hold all 11), drawn with Python's random seeded "hollow_moth|<seed>|<round>". Its mark is that
cabinet's Heartglass par plus a seeded margin of 0..max(1, par // 10); for a "perfect" par cabinet (glowmoss) you need
a perfect hard win at or above its Umbra par plus the margin. You get 3 tries per round; a hard win at or above the
mark beats the moth (frees the Hollow Moth boon in Spirit Boons). Out of tries, the moth flies off and the next round
draws a fresh challenge. Satchel PAYOUTS are read-only here.
`python hollow_moth_rival_ref.py > hollow_moth_rival_golden.txt`; `--check hollow_moth_rival_golden.txt` verifies it.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "minigames"))
from prism_satchel import PAYOUTS  # noqa: E402  (read-only)

GAMES = sorted(PAYOUTS)
UNLOCK_AT = 3
TRIES = 3
MAX_ROUND = 9999

OK, LOCKED, ALREADY_BEATEN, BAD_MASK, NO_CHALLENGE, WRONG_GAME, BAD_DIFFICULTY, BAD_SCORE, BEATEN, FELL_SHORT, \
    FLEW_OFF, ROUND_LIMIT = range(12)
STATUS = ["OK", "LOCKED", "ALREADY_BEATEN", "BAD_MASK", "NO_CHALLENGE", "WRONG_GAME", "BAD_DIFFICULTY", "BAD_SCORE",
          "BEATEN", "FELL_SHORT", "FLEW_OFF", "ROUND_LIMIT"]
DIFFS = ["easy", "normal", "hard"]


def new_state():
    return {"round": 0, "tries": 0, "beaten": False, "game": -1, "mark": 0, "perfect": False}


def mark_for(game, r):
    _, _, umbra, heart = PAYOUTS[GAMES[game]]
    base = umbra if heart == "perfect" else heart
    return base + r.randrange(max(1, base // 10) + 1), heart == "perfect"


def begin(st, seed, heart_mask):
    """Draw the next round's challenge. heart_mask bit i = Heartglass held in GAMES[i]."""
    if not (0 <= heart_mask < (1 << len(GAMES))):
        return BAD_MASK, st
    if bin(heart_mask).count("1") < UNLOCK_AT:
        return LOCKED, st
    if st["beaten"]:
        return ALREADY_BEATEN, st
    if st["game"] >= 0 and st["tries"] > 0:
        return OK, st                      # challenge still open: nothing to draw
    if st["round"] >= MAX_ROUND:
        return ROUND_LIMIT, st
    cand = [i for i in range(len(GAMES)) if not heart_mask >> i & 1] or list(range(len(GAMES)))
    s = dict(st)
    s["round"] += 1
    r = random.Random("hollow_moth|%d|%d" % (seed, s["round"]))
    s["game"] = cand[r.randrange(len(cand))]
    s["mark"], s["perfect"] = mark_for(s["game"], r)
    s["tries"] = TRIES
    return OK, s


def attempt(st, game, diff, score, won, perfect):
    if st["beaten"]:
        return ALREADY_BEATEN, st
    if st["game"] < 0 or st["tries"] == 0:
        return NO_CHALLENGE, st
    if game != st["game"]:
        return WRONG_GAME, st
    if not (0 <= diff < 3):
        return BAD_DIFFICULTY, st
    if score < 0:
        return BAD_SCORE, st
    s = dict(st)
    if diff == 2 and won and score >= s["mark"] and (perfect or not s["perfect"]):
        s["beaten"], s["tries"] = True, 0
        return BEATEN, s
    s["tries"] -= 1
    if s["tries"] == 0:
        s["game"] = -1
        return FLEW_OFF, s
    return FELL_SHORT, s


def fmt(s):
    return "%d %d %d %d %d %d" % (s["round"], s["tries"], int(s["beaten"]), s["game"], s["mark"], int(s["perfect"]))


def write(f):
    f.write("# Hollow Moth rival golden vectors from hollow_moth_rival_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# N <seed> <mask> (new rival) | B <status> <state> | X <game> <diff> <score> <won> <perfect> <status> <state>\n")
    f.write("# state = round tries beaten game mark perfect\n")
    rng = random.Random(62850)
    full = (1 << len(GAMES)) - 1
    masks = [0, 0b11, 0b111, 0b1011000, full, full ^ (1 << 2), 1 << 11, -1]
    for c in range(160):
        seed = rng.randrange(1 << 31)
        mask = masks[c] if c < len(masks) else rng.choice(
            [rng.randrange(1 << 11), rng.randrange(1 << 11) | 0b10101, full, 0b11])
        st = new_state()
        f.write("N %d %d\n" % (seed, mask))
        for _ in range(rng.randint(2, 9)):
            if st["game"] < 0 and rng.random() < 0.6:
                code, st = begin(st, seed, mask)
                f.write("B %s %s\n" % (STATUS[code], fmt(st)))
                continue
            g = st["game"] if st["game"] >= 0 and rng.random() < 0.85 else rng.randrange(-1, 12)
            d = rng.choice([2, 2, 2, 1, 0, 3])
            base = st["mark"] if st["game"] >= 0 else 100
            sc = rng.choice([base, base - 1, base + rng.randrange(20), rng.randrange(base + 1), -1])
            won, pf = rng.random() < 0.8, rng.random() < 0.6
            code, st = attempt(st, g, d, sc, won, pf)
            f.write("X %d %d %d %d %d %s %s\n" % (g, d, sc, int(won), int(pf), STATUS[code], fmt(st)))


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
