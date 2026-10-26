# SPDX-License-Identifier: MIT
"""portal_lands: open 4x4 blocks on a map, nearest-first numbering, idempotent rewrite that keeps owners."""
import portal_lands as P

ok = total = 0


def check(name, cond, why=""):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond or not why else "  " + str(why)))


rows = ["........", "...:....", "........", "........", "........", ".....T..", "........", "........"]
b = P.blocks(rows)
check("only fully open, grid-aligned 4x4 blocks count (the T spoils one of four)", b == [(0, 0), (4, 0), (0, 4)], b)
rows2 = ["." * 12] * 12
b2 = P.blocks(rows2)
check("a 12x12 open field holds nine blocks", len(b2) == 9)
o = P.ordered(b2, (4, 4))
check("the origin block is numbered first, then its ring", o[0] == (4, 4) and all(max(abs(x - 4), abs(y - 4)) == 4 for x, y in o[1:]))
text = "DRR 1\nmap FIELD 12 12 FIELD 0 - 0 0 FIELD\n" + "".join("row %s\n" % r for r in rows2) + "land 1 FIELD 4 4 4 4 HERO\n"
t1, n1 = P.lay(text)
t2, n2 = P.lay(t1)
check("every block becomes a land row; the hero's keeps its number and owner", n1 == 9 and "land 1 FIELD 4 4 4 4 HERO" in t1 and n2 == 9)
check("laying twice changes nothing", t1 == t2)
check("new numbers never reuse an existing one", t1.count("land 1 ") == 1)
tail = "spawn FIELD 4 4\nportal FIELD 4 3\nnews THE ARKS SAIL AT DUSK.\n"
t3, n3 = P.lay(text + tail)
check("deeds precede spawn, portal and news like the canonical Java DRR writer",
      t3.index("land ") < t3.index("spawn ") and t3.endswith(tail))
check("canonical deed ordering remains idempotent", P.lay(t3) == (t3, n3))
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
