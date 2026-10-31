# SPDX-License-Identifier: MIT
"""Shard Smelter rules reference (Crafting + rewards lane) and golden-vector writer.

The rules authority for DaedalusShardSmelterCore.h. `python shard_smelter_ref.py > shard_smelter_golden.txt`
writes the parity fixture; `--check shard_smelter_golden.txt` verifies an existing one is current.
Integer only. Randomness is only used to pick test inventories (Python random with a fixed seed), never in the rules.
"""
import random
import sys

# Materials: the five Prism Shard hues in Prism Satchel order, then the five ingots.
MATERIALS = ["ember", "tide", "verdant", "gale", "umbra",
             "glowsteel", "tidebrass", "galeiron", "umbral_alloy", "heartglass_ingot"]
M = len(MATERIALS)
MAX_COUNT = 999_999_999   # same 9-digit ceiling as a Satchel count
MAX_BATCH = 1_000_000

def vec(**kw):
    v = [0] * M
    for k, n in kw.items():
        v[MATERIALS.index(k)] = n
    return v

# (name, inputs, outputs); every recipe makes exactly one ingot per batch.
RECIPES = [
    ("glowsteel", vec(ember=3, tide=1), vec(glowsteel=1)),
    ("tidebrass", vec(tide=2, verdant=2), vec(tidebrass=1)),
    ("galeiron", vec(gale=2, umbra=1), vec(galeiron=1)),
    ("umbral_alloy", vec(umbra=3, ember=1), vec(umbral_alloy=1)),
    ("heartglass_ingot", vec(glowsteel=1, tidebrass=1, galeiron=1, umbral_alloy=1), vec(heartglass_ingot=1)),
]

# Shard value of one unit of each material: a shard is 1, an ingot is the value of its inputs, so smelting
# conserves value exactly (Salvage/Reforge will be built on this and may only lose value).
VALUES = [1] * 5 + [0] * 5
for _name, ins, outs in RECIPES:
    VALUES[outs.index(1)] = sum(n * VALUES[i] for i, n in enumerate(ins))

OK, NULL_POINTER, UNKNOWN_RECIPE, BAD_BATCH, BAD_INVENTORY, SHORT, OVERFLOW = range(7)
STATUS = ["OK", "NULL_POINTER", "UNKNOWN_RECIPE", "BAD_BATCH", "BAD_INVENTORY", "SHORT", "OVERFLOW"]

def valid_inventory(inv):
    return len(inv) == M and all(0 <= n <= MAX_COUNT for n in inv)

def smelt(inv, recipe, batches):
    """Returns (status, new inventory). Any refusal returns the inventory unchanged."""
    if not (0 <= recipe < len(RECIPES)):
        return UNKNOWN_RECIPE, list(inv)
    if not (1 <= batches <= MAX_BATCH):
        return BAD_BATCH, list(inv)
    if not valid_inventory(inv):
        return BAD_INVENTORY, list(inv)
    _name, ins, outs = RECIPES[recipe]
    if any(inv[i] < n * batches for i, n in enumerate(ins)):
        return SHORT, list(inv)
    out = [inv[i] - ins[i] * batches + outs[i] * batches for i in range(M)]
    if any(n > MAX_COUNT for n in out):
        return OVERFLOW, list(inv)
    return OK, out

def max_batches(inv, recipe):
    """Largest batch count Smelt accepts (0 when none); -1 for an unknown recipe or bad inventory."""
    if not (0 <= recipe < len(RECIPES)) or not valid_inventory(inv):
        return -1
    _name, ins, outs = RECIPES[recipe]
    best = MAX_BATCH
    for i in range(M):
        net = outs[i] - ins[i]
        if ins[i] > 0:
            best = min(best, inv[i] // ins[i])
        if net > 0:
            best = min(best, (MAX_COUNT - inv[i]) // net)
    return best

def value(inv):
    return sum(n * VALUES[i] for i, n in enumerate(inv))

def cases():
    r = random.Random(60695)
    out = []
    def add(inv, recipe, batches):
        out.append((list(inv), recipe, batches))
    # Hand-set edges.
    zero = [0] * M
    full = [MAX_COUNT] * M
    add(vec(ember=3, tide=1), 0, 1)
    add(vec(ember=2, tide=1), 0, 1)
    add(vec(ember=6, tide=2), 0, 2)
    add(vec(ember=6, tide=2), 0, 3)
    add(zero, 0, 1)
    add(vec(ember=3, tide=1), -1, 1)
    add(vec(ember=3, tide=1), 5, 1)
    add(vec(ember=3, tide=1), 0, 0)
    add(vec(ember=3, tide=1), 0, -1)
    add(vec(ember=3, tide=1), 0, MAX_BATCH + 1)
    add(full, 0, MAX_BATCH)
    add(vec(ember=MAX_COUNT, tide=MAX_COUNT, glowsteel=MAX_COUNT), 0, 1)
    add(vec(ember=MAX_COUNT, tide=MAX_COUNT, glowsteel=MAX_COUNT - 1), 0, 1)
    add(vec(ember=MAX_COUNT, tide=MAX_COUNT, glowsteel=MAX_COUNT - 2), 0, 3)
    bad_neg = vec(ember=3, tide=1); bad_neg[9] = -1
    add(bad_neg, 0, 1)
    bad_big = vec(ember=3, tide=1); bad_big[4] = MAX_COUNT + 1
    add(bad_big, 0, 1)
    add(vec(glowsteel=1, tidebrass=1, galeiron=1, umbral_alloy=1), 4, 1)
    add(vec(glowsteel=1, tidebrass=1, galeiron=1), 4, 1)
    add(vec(glowsteel=5, tidebrass=5, galeiron=5, umbral_alloy=5), 4, 5)
    for rid in range(len(RECIPES)):
        ins = RECIPES[rid][1]
        exact = [n * 7 for n in ins]
        add(exact, rid, 7)
        add(exact, rid, 8)
    for rid in range(len(RECIPES)):
        ins, outs = RECIPES[rid][1], RECIPES[rid][2]
        o = outs.index(1)
        for room in (0, 1, 2):
            inv = [n * 3 for n in ins]
            inv[o] = MAX_COUNT - room
            add(inv, rid, 1)
            add(inv, rid, 3)
    # Seeded sweep: small, medium and near-ceiling inventories, valid and invalid recipes and batch counts.
    for k in range(2500):
        scale = r.choice([5, 50, 5000, MAX_COUNT])
        inv = [r.randint(0, scale) for _ in range(M)]
        if k % 97 == 0:
            inv[r.randrange(M)] = r.choice([-1, MAX_COUNT + 1, -MAX_COUNT])
        recipe = r.choice([0, 1, 2, 3, 4, 0, 1, 2, 3, 4, -1, 5, 99])
        mb = max_batches(inv, recipe)
        batches = r.choice([1, 2, 3, r.randint(1, 40), r.randint(1, MAX_BATCH), mb if mb > 0 else 1,
                            mb + 1 if mb >= 0 else 2, 0, -3, MAX_BATCH + 7])
        add(inv, recipe, batches)
    return out

def write(f):
    f.write("# Shard Smelter golden vectors from shard_smelter_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# M <materials> | C <max_count> <max_batch> | N <names> | V <values> | R <id> <name> <in x10> <out x10>\n")
    f.write("# S <inv x10> <recipe> <batches> <STATUS> <after x10> <max_batches> <value_before> <value_after>\n")
    f.write("M %d\n" % M)
    f.write("C %d %d\n" % (MAX_COUNT, MAX_BATCH))
    f.write("N %s\n" % " ".join(MATERIALS))
    f.write("V %s\n" % " ".join(map(str, VALUES)))
    for i, (name, ins, outs) in enumerate(RECIPES):
        f.write("R %d %s %s %s\n" % (i, name, " ".join(map(str, ins)), " ".join(map(str, outs))))
    for inv, recipe, batches in cases():
        st, after = smelt(inv, recipe, batches)
        vb = value(inv) if valid_inventory(inv) else -1
        va = value(after) if valid_inventory(after) else -1
        f.write("S %s %d %d %s %s %d %d %d\n" % (" ".join(map(str, inv)), recipe, batches, STATUS[st],
                                              " ".join(map(str, after)), max_batches(inv, recipe), vb, va))

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
