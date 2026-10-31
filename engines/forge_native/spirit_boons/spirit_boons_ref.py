# SPDX-License-Identifier: MIT
"""Spirit Boons rules reference (Prismheart Round 2 lane R2-9, hephaestus) and golden-vector writer.

Rules authority for DaedalusSpiritBoonsCore.h. Spirits summoned in Wardens' Accord (its spirit names, in its order)
and in Shardring (one per hue: ember Cinder Wisp, tide Mere Sprite, verdant Thornkin, gale Sky Lark Spirit, umbra
Hollow Moth) are tallied; each spirit grants one small boon in another cabinet, as a change to one of that cabinet's
per-difficulty settings. The table is DATA ONLY and every boon is PROPOSED: nothing here changes another game's
rules until that game's owner ACKs it (PLAN.md R2-9). The Hollow Moth boon also needs the Hollow Moth rival beaten.
Deterministic, integer only, no randomness.
`python spirit_boons_ref.py > spirit_boons_golden.txt`; `--check spirit_boons_golden.txt` verifies it.
"""
import random
import sys

SPIRITS = ["Cinder Wisp", "Mere Sprite", "Thornkin", "Sky Lark Spirit", "Hollow Moth", "Glass Heron", "Lantern Newt"]
SHARDRING_HUES = ["ember", "tide", "verdant", "gale", "umbra"]   # hue i summons SPIRITS[i]
HOLLOW_MOTH = 4
GAMES = ["facetlock", "glimmerloom", "glowmoss", "lumenpath", "prismcairn", "prismvault", "shadewatch", "shardfall",
         "shardring", "spiritkite", "wardens_accord"]            # Prism Satchel game ids, sorted
# spirit -> (game, setting key in that game's DIFFICULTY table, delta per level)
BOONS = [
    ("glowmoss", "light", 1),
    ("spiritkite", "wind", 2),
    ("facetlock", "spare", 1),
    ("lumenpath", "moves", 1),
    ("shardfall", "cracked", -1),
    ("glimmerloom", "satchel", 2),
    ("shadewatch", "hearts", 1),
]
LEVEL2_AT = 5          # summoning a spirit this many times doubles its boon
MAX_COUNT = 999999     # tally ceiling per spirit

OK, NULL_POINTER, BAD_SPIRIT, BAD_COUNT, BAD_TALLY, OVERFLOW, UNKNOWN_GAME = range(7)
STATUS = ["OK", "NULL_POINTER", "BAD_SPIRIT", "BAD_COUNT", "BAD_TALLY", "OVERFLOW", "UNKNOWN_GAME"]

def valid(tally):
    return len(tally) == len(SPIRITS) and all(0 <= c <= MAX_COUNT for c in tally)

def add(tally, spirit, count):
    """Returns (status, tally); refusals return the tally unchanged."""
    if not (0 <= spirit < len(SPIRITS)):
        return BAD_SPIRIT, tally
    if not (1 <= count <= MAX_COUNT):
        return BAD_COUNT, tally
    if not valid(tally):
        return BAD_TALLY, tally
    if tally[spirit] + count > MAX_COUNT:
        return OVERFLOW, tally
    t = list(tally)
    t[spirit] += count
    return OK, t

def level(tally, spirit, moth_freed):
    if spirit == HOLLOW_MOTH and not moth_freed:
        return 0
    c = tally[spirit]
    return 0 if c == 0 else (2 if c >= LEVEL2_AT else 1)

def boons(tally, game, moth_freed):
    """(status, [(spirit, key, delta)]) for one cabinet, in spirit order."""
    if game not in GAMES:
        return UNKNOWN_GAME, []
    if not valid(tally):
        return BAD_TALLY, []
    out = []
    for s, (g, key, d) in enumerate(BOONS):
        lv = level(tally, s, moth_freed)
        if g == game and lv:
            out.append((s, key, d * lv))
    return OK, out

def cases():
    r = random.Random(62850)
    out = []
    edge = [[0] * 7, [1] * 7, [LEVEL2_AT - 1] * 7, [LEVEL2_AT] * 7, [MAX_COUNT] * 7, [0, 0, 0, 0, 9, 0, 0]]
    for t in edge:
        out.append(t)
    for _ in range(300):
        out.append([r.choice([0, 0, 0, 1, 2, 4, 5, 6, r.randint(0, 50)]) for _ in range(7)])
    return out, r

def write(f):
    f.write("# Spirit Boons golden vectors from spirit_boons_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# T <7 counts> | A <spirit> <count> <status> <7 counts> | Q <game> <moth 0/1> <status> <n> [<spirit> <key> <delta>]...\n")
    tallies, r = cases()
    games = GAMES + ["", "Glowmoss", "unknown_cabinet"]
    for t in tallies:
        f.write("T %s\n" % " ".join(map(str, t)))
        for _ in range(3):
            sp = r.choice([0, 1, 2, 3, 4, 5, 6, r.randint(-2, 9)])
            cnt = r.choice([1, 1, 2, 3, 0, -1, MAX_COUNT, r.randint(1, 10)])
            st, t = add(t, sp, cnt)
            f.write("A %d %d %s %s\n" % (sp, cnt, STATUS[st], " ".join(map(str, t))))
        for g in r.sample(games, 4):
            for moth in (0, 1):
                st, b = boons(t, g, moth)
                f.write("Q %s %d %s %d%s\n" % (g if g else "-", moth, STATUS[st], len(b),
                                              "".join(" %d %s %d" % x for x in b)))
    # One tally outside its range: every query refuses.
    bad = [0, 0, -1, 0, 0, 0, 0]
    f.write("T %s\n" % " ".join(map(str, bad)))
    st, _ = add(bad, 0, 1)
    f.write("A 0 1 %s %s\n" % (STATUS[st], " ".join(map(str, bad))))
    st, b = boons(bad, "glowmoss", 1)
    f.write("Q glowmoss 1 %s 0\n" % STATUS[st])

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
