# SPDX-License-Identifier: MIT
"""Offline checks of island population placement. Run: python test_daedalus_populate.py"""
import random

import daedalus_populate as P

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


rng = random.Random(1)
pts = P.spread((1000.0, 2000.0), (800.0, 400.0), 6, rng)
check("spread gives one point per animal", len(pts) == 6)
check("every point stays inside the zone, off its edge",
      all(abs(x - 1000) <= 800 * 0.85 + 1e-6 and abs(y - 2000) <= 400 * 0.85 + 1e-6 for x, y in pts))
d = min(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for i, a in enumerate(pts) for b in pts[i + 1:])
check("a herd doesn't stack in one spot", d > 20)
check("deterministic for a seed", P.spread((0, 0), (500, 500), 4, random.Random(7)) ==
      P.spread((0, 0), (500, 500), 4, random.Random(7)))
(c, e) = P.zone_box([(0, 0, 100, 100), (1000, 0, 100, 200)])
check("zone box covers its actors", c == (500.0, 0.0) and e == (600.0, 200.0))
spec = P.GROK_ARKISLE
check("every Grok pen and wild zone has animals",
      {z for z, _, _ in spec["zones"]} >= {"pen_cattle", "pen_pigs", "pen_stable", "pen_sheep_goats", "pen_poultry",
                                           "meadow", "grove", "pond", "shoreline"})
check("pen stock is leashed tighter than wild animals",
      max(l for z, _, l in spec["zones"] if z.startswith("pen_")) < min(l for z, _, l in spec["zones"]
                                                                          if not z.startswith("pen_")))
check("only shipped Mob_ species", all(s.startswith("Mob_") for _, h, _ in spec["zones"] for s, _ in h))
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
