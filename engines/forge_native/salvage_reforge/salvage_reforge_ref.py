# SPDX-License-Identifier: MIT
"""Salvage and Reforge rules reference (Crafting + rewards lane) and golden-vector writer.

Rules authority for DaedalusSalvageReforgeCore.h. Builds on the Shard Smelter rules (../shard_smelter/shard_smelter_ref.py).
`python salvage_reforge_ref.py > salvage_reforge_golden.txt`; `--check salvage_reforge_golden.txt` verifies it.

Salvage breaks ingots into scrap at a loss; Reforge spends scrap at full value to make a chosen ingot. Ledger value
(inventory value + scrap) never rises under Smelt, Salvage or Reforge, so no loop of operations can gain value.
Randomness only picks test scripts (Python random, fixed seed), never inside the rules.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shard_smelter"))
import shard_smelter_ref as sm  # noqa: E402

MAX_SCRAP = 999_999_999
MAX_OPS = 1_000_000
FIRST_INGOT = 5
# Scrap from one ingot: floor(3 * value / 4), so salvage always loses at least a quarter (rounded up).
SCRAP = [0] * sm.M
for i in range(FIRST_INGOT, sm.M):
    SCRAP[i] = (3 * sm.VALUES[i]) // 4
# Scrap to reforge one ingot: its full shard value.
COST = [0] * sm.M
for i in range(FIRST_INGOT, sm.M):
    COST[i] = sm.VALUES[i]

OK, NULL_POINTER, NOT_AN_INGOT, BAD_COUNT, BAD_LEDGER, SHORT, OVERFLOW = range(7)
STATUS = ["OK", "NULL_POINTER", "NOT_AN_INGOT", "BAD_COUNT", "BAD_LEDGER", "SHORT", "OVERFLOW"]

def valid_ledger(inv, scrap):
    return sm.valid_inventory(inv) and 0 <= scrap <= MAX_SCRAP

def ledger_value(inv, scrap):
    return sm.value(inv) + scrap

def salvage(inv, scrap, material, count):
    if not (FIRST_INGOT <= material < sm.M):
        return NOT_AN_INGOT, list(inv), scrap
    if not (1 <= count <= MAX_OPS):
        return BAD_COUNT, list(inv), scrap
    if not valid_ledger(inv, scrap):
        return BAD_LEDGER, list(inv), scrap
    if inv[material] < count:
        return SHORT, list(inv), scrap
    if scrap + SCRAP[material] * count > MAX_SCRAP:
        return OVERFLOW, list(inv), scrap
    out = list(inv)
    out[material] -= count
    return OK, out, scrap + SCRAP[material] * count

def reforge(inv, scrap, material, count):
    if not (FIRST_INGOT <= material < sm.M):
        return NOT_AN_INGOT, list(inv), scrap
    if not (1 <= count <= MAX_OPS):
        return BAD_COUNT, list(inv), scrap
    if not valid_ledger(inv, scrap):
        return BAD_LEDGER, list(inv), scrap
    if scrap < COST[material] * count:
        return SHORT, list(inv), scrap
    if inv[material] + count > sm.MAX_COUNT:
        return OVERFLOW, list(inv), scrap
    out = list(inv)
    out[material] += count
    return OK, out, scrap - COST[material] * count

def smelt(inv, scrap, recipe, batches):
    if not (0 <= scrap <= MAX_SCRAP):
        return BAD_LEDGER, list(inv), scrap
    st, out = sm.smelt(inv, recipe, batches)
    # Smelter statuses map onto this ledger's: UNKNOWN_RECIPE -> NOT_AN_INGOT, BAD_BATCH -> BAD_COUNT.
    mapped = {sm.OK: OK, sm.UNKNOWN_RECIPE: NOT_AN_INGOT, sm.BAD_BATCH: BAD_COUNT, sm.BAD_INVENTORY: BAD_LEDGER,
              sm.SHORT: SHORT, sm.OVERFLOW: OVERFLOW}[st]
    return mapped, out, scrap

OPS = {"smelt": smelt, "salvage": salvage, "reforge": reforge}

def scripts():
    r = random.Random(60695 + 1)
    out = []
    # Hand-set edges and the headline loops.
    out.append(("salvage_reforge_loop", [0] * 5 + [4, 0, 0, 0, 0], 0,
                [("salvage", 5, 4), ("reforge", 5, 3), ("salvage", 5, 3), ("reforge", 5, 2), ("reforge", 5, 1)]))
    out.append(("heartglass_round_trip", [0] * 5 + [1, 1, 1, 1, 0], 0,
                [("smelt", 4, 1), ("salvage", 9, 1), ("reforge", 9, 1), ("reforge", 7, 3), ("reforge", 7, 1)]))
    out.append(("refusals", [3, 1, 0, 0, 0, 0, 0, 0, 0, 0], 5,
                [("salvage", 0, 1), ("salvage", 5, 1), ("reforge", 4, 1), ("reforge", 5, 0), ("reforge", 5, MAX_OPS + 1),
                 ("salvage", 10, 1), ("smelt", 0, 1), ("reforge", 5, 1), ("reforge", 7, 1), ("smelt", 9, 1)]))
    out.append(("scrap_ceiling", [0] * 5 + [0, 0, 0, 0, 2], MAX_SCRAP - 11,
                [("salvage", 9, 1), ("salvage", 9, 1), ("reforge", 9, 1)]))
    out.append(("ingot_ceiling", [0] * 5 + [sm.MAX_COUNT, 0, 0, 0, 0], 40, [("reforge", 5, 1), ("salvage", 5, 1), ("reforge", 5, 1)]))
    out.append(("bad_ledger", [0] * 5 + [1, 0, 0, 0, 0], -1, [("salvage", 5, 1), ("reforge", 5, 1), ("smelt", 0, 1)]))
    out.append(("bad_ledger_count", [0] * 9 + [-2], 10, [("salvage", 5, 1), ("reforge", 6, 1)]))
    # Seeded scripts: mixed operations from varied starts, including deliberate bad arguments.
    for k in range(400):
        scale = r.choice([3, 20, 500, sm.MAX_COUNT // 2])
        inv = [r.randint(0, scale) for _ in range(sm.M)]
        scrap = r.randint(0, min(scale * 10, MAX_SCRAP))
        if k % 16 == 0:
            scrap = MAX_SCRAP - r.randint(0, 40)
        ops = []
        for _ in range(r.randint(1, 25)):
            kind = r.choice(["smelt", "salvage", "reforge", "salvage", "reforge"])
            if kind == "smelt":
                arg = r.choice([0, 1, 2, 3, 4, 4, -1, 5])
            else:
                arg = r.choice([5, 6, 7, 8, 9, 5, 9, 0, 4, 10])
            count = r.choice([1, 1, 2, 3, r.randint(1, 50), r.randint(1, MAX_OPS), 0, -2])
            ops.append((kind, arg, count))
        out.append(("seeded_%03d" % k, inv, scrap, ops))
    return out

def write(f):
    f.write("# Salvage and Reforge golden vectors from salvage_reforge_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# K <max_scrap> <max_ops> | Y <scrap per unit x10> | Z <reforge cost per unit x10>\n")
    f.write("# P <name> <inv x10> <scrap> <value> starts a script; O <op> <arg> <count> <STATUS> <inv x10> <scrap> <value>\n")
    f.write("# E <name> <ops> <start_value> <end_value> ends it\n")
    f.write("K %d %d\n" % (MAX_SCRAP, MAX_OPS))
    f.write("Y %s\n" % " ".join(map(str, SCRAP)))
    f.write("Z %s\n" % " ".join(map(str, COST)))
    for name, inv, scrap, ops in scripts():
        v0 = ledger_value(inv, scrap) if valid_ledger(inv, scrap) else -1
        f.write("P %s %s %d %d\n" % (name, " ".join(map(str, inv)), scrap, v0))
        cur_inv, cur_scrap = list(inv), scrap
        for kind, arg, count in ops:
            st, cur_inv, cur_scrap = OPS[kind](cur_inv, cur_scrap, arg, count)
            v = ledger_value(cur_inv, cur_scrap) if valid_ledger(cur_inv, cur_scrap) else -1
            if v0 >= 0:
                assert v <= v0, "conservation broken in " + name
            f.write("O %s %d %d %s %s %d %d\n" % (kind, arg, count, STATUS[st], " ".join(map(str, cur_inv)), cur_scrap, v))
        ve = ledger_value(cur_inv, cur_scrap) if valid_ledger(cur_inv, cur_scrap) else -1
        f.write("E %s %d %d %d\n" % (name, len(ops), v0, ve))

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
