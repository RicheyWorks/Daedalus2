# SPDX-License-Identifier: MIT
"""Forgemaster's Commission Board rules reference (Crafting + rewards lane) and golden-vector writer.

Rules authority for DaedalusCommissionBoardCore.h. Each calendar day the board posts three commissions for three
different ingots, seeded from the string "commission|YYYY-MM-DD" with CPython's random (DaedalusPyRandomCore.h in
C++). Delivering a commission takes its ingots from the Smelter inventory and pays Forge Marks; filling all three on
one board pays a board bonus. Integer only. Marks are a reward currency, not shard value; they cannot buy shards or
ingots, so they do not touch the Smelter/Salvage conservation property.
`python commission_board_ref.py > commission_board_golden.txt`; `--check commission_board_golden.txt` verifies it.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shard_smelter"))
import shard_smelter_ref as sm  # noqa: E402

SLOTS = 3
FIRST_INGOT = 5
INGOTS = 5
MAX_QTY = 3          # quantity 1..3; a heartglass ingot is always 1
MARK_BONUS = 2       # per commission, on top of the ingots' shard value
BOARD_BONUS = 5      # for filling all three
MAX_MARKS = 999999999

OK, NULL_POINTER, BAD_DATE, BAD_SLOT, DONE, BAD_INVENTORY, SHORT, OVERFLOW = range(8)
STATUS = ["OK", "NULL_POINTER", "BAD_DATE", "BAD_SLOT", "ALREADY_DONE", "BAD_INVENTORY", "SHORT", "OVERFLOW"]

def valid_date(d):
    if len(d) != 10 or d[4] != "-" or d[7] != "-":
        return False
    digits = d[0:4] + d[5:7] + d[8:10]
    if not all("0" <= ch <= "9" for ch in digits):
        return False
    y, m, day = int(d[0:4]), int(d[5:7]), int(d[8:10])
    if y < 1 or not (1 <= m <= 12):
        return False
    leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
    dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return 1 <= day <= dim

def board(date):
    """[(material, qty, marks)] x3, or None for a bad date. Draws: sample(range(5), 3), then qty per slot."""
    if not valid_date(date):
        return None
    r = random.Random("commission|" + date)
    picks = r.sample(range(INGOTS), SLOTS)
    out = []
    for p in picks:
        m = FIRST_INGOT + p
        q = 1 if m == 9 else 1 + r.randrange(MAX_QTY)
        out.append((m, q, q * sm.VALUES[m] + MARK_BONUS))
    return out

def deliver(inv, b, done, marks, slot):
    """Returns (status, inv, done, marks); a refusal returns the inputs unchanged."""
    if not (0 <= slot < SLOTS):
        return BAD_SLOT, inv, done, marks
    if done[slot]:
        return DONE, inv, done, marks
    if any(c < 0 or c > sm.MAX_COUNT for c in inv) or not (0 <= marks <= MAX_MARKS):
        return BAD_INVENTORY, inv, done, marks
    m, q, pay = b[slot]
    if inv[m] < q:
        return SHORT, inv, done, marks
    nd = list(done)
    nd[slot] = True
    gain = pay + (BOARD_BONUS if all(nd) else 0)
    if marks + gain > MAX_MARKS:
        return OVERFLOW, inv, done, marks
    ni = list(inv)
    ni[m] -= q
    return OK, ni, nd, marks + gain

def dates():
    out = ["2026-10-30", "2026-10-31", "2024-02-29", "2000-02-29", "0001-01-01", "9999-12-31",
           "2026-02-29", "1900-02-29", "2026-13-01", "2026-00-10", "2026-04-31", "2026-4-01", "2026/10/30",
           "20261030xx", "", "0000-01-01", "2026-10-3a"]
    r = random.Random(60695 + 3)
    for _ in range(500):
        y, m, d = r.randint(1990, 2099), r.randint(1, 12), r.randint(1, 31)
        out.append("%04d-%02d-%02d" % (y, m, d))
    return out

def write(f):
    f.write("# Commission Board golden vectors from commission_board_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# D <date_len> <date> | B BAD_DATE or B <material qty marks> x3 | I <10 counts> <marks> | "
            "X <slot> <status> <10 counts> <marks> <done mask>\n")
    r = random.Random(60695 + 4)
    for d in dates():
        f.write("D %d %s\n" % (len(d), d))
        b = board(d)
        if b is None:
            f.write("B BAD_DATE\n")
            continue
        f.write("B %s\n" % " ".join("%d %d %d" % t for t in b))
        inv = [r.randint(0, 4) for _ in range(sm.MATERIALS.__len__())]
        marks = r.choice([0, 0, 7, MAX_MARKS - 3, MAX_MARKS, r.randint(0, 1000)])
        if r.random() < 0.05:
            inv[r.randrange(10)] = r.choice([-1, sm.MAX_COUNT + 1])
        f.write("I %s %d\n" % (" ".join(map(str, inv)), marks))
        done = [False] * SLOTS
        for _ in range(r.randint(1, 7)):
            slot = r.choice([0, 1, 2, 0, 1, 2, -1, 3])
            st, inv, done, marks = deliver(inv, b, done, marks, slot)
            mask = sum(1 << i for i in range(SLOTS) if done[i])
            f.write("X %d %s %s %d %d\n" % (slot, STATUS[st], " ".join(map(str, inv)), marks, mask))

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
