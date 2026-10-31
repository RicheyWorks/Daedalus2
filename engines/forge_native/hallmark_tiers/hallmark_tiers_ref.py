# SPDX-License-Identifier: MIT
"""Hallmark Tiers rules reference (Crafting + rewards lane) and golden-vector writer.

Rules authority for DaedalusHallmarkTiersCore.h. A finished piece is stamped with a hallmark. Hallmarks are COSMETIC
ONLY: they pick a stamp and a finish and never change counts, values, marks or any gameplay number.
Inputs come from systems already on main:
  seal    - Prism Satchel's best Warden seal for the game (prism_satchel::SealIndex, 0 none .. 6 heartglass);
  par     - Fair Par's tier for the run (prismpar::Tier: 0 none, 1 bronze, 2 silver, 3 gold);
  quench  - the Quench Window outcome (0 soft, 1 tempered, 2 perfect, 3 cracked).
`python hallmark_tiers_ref.py > hallmark_tiers_golden.txt`; `--check hallmark_tiers_golden.txt` verifies it.
"""
import sys

SEALS = ["none", "ember", "tide", "verdant", "gale", "umbra", "heartglass"]   # prism_satchel::Seals
PARS = ["none", "bronze", "silver", "gold"]                                   # prismpar::Tier
QUENCH = ["soft", "tempered", "perfect", "cracked"]                           # quench::Outcome
TIERS = ["NONE", "PLAIN", "BRONZE", "SILVER", "GOLD", "PRISM"]
SOFT, TEMPERED, PERFECT, CRACKED = range(4)
HEARTGLASS = 6

def hallmark(seal, par, quench):
    """(status, tier, finish) with status OK / BAD_SEAL / BAD_PAR / BAD_QUENCH."""
    if not (0 <= seal < len(SEALS)):
        return "BAD_SEAL", None, None
    if not (0 <= par < len(PARS)):
        return "BAD_PAR", None, None
    if not (0 <= quench < len(QUENCH)):
        return "BAD_QUENCH", None, None
    if quench == CRACKED:
        return "OK", 0, seal          # a cracked piece takes no stamp
    tier = 1 + par                    # PLAIN..GOLD from the par tier
    cap = {SOFT: 2, TEMPERED: 3, PERFECT: 4}[quench]
    tier = min(tier, cap)
    if tier == 4 and quench == PERFECT and seal == HEARTGLASS:
        tier = 5                      # PRISM: gold par, perfect quench, heartglass seal
    return "OK", tier, seal

def write(f):
    f.write("# Hallmark Tiers golden vectors from hallmark_tiers_ref.py (rules authority). Do not hand-edit.\n")
    f.write("# M <seal> <par> <quench> <status> [<tier> <finish>]\n")
    for s in range(-1, len(SEALS) + 1):
        for p in range(-1, len(PARS) + 1):
            for q in range(-1, len(QUENCH) + 1):
                st, t, fin = hallmark(s, p, q)
                f.write("M %d %d %d %s%s\n" % (s, p, q, st, "" if t is None else " %s %s" % (TIERS[t], SEALS[fin])))

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
