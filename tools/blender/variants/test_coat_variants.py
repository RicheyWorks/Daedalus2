# SPDX-License-Identifier: MIT
"""Pure-Python checks for coat_variants.py. python test_coat_variants.py [--java <Coat.java>]"""
import json, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coat_variants as V
java = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--java"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
            "daedalus-core", "src", "main", "java", "com", "daedalus", "world", "odds", "breeding", "Coat.java"))
d = tempfile.mkdtemp(); p, m = V.write(d); p2, m2 = V.write(tempfile.mkdtemp())
C = V.colours(); checks = []
add = lambda n, ok: checks.append((n, bool(ok)))
if os.path.exists(java):
    src = open(java, encoding="utf-8").read()
    add("coat keys = Coat.Pattern.coatKey() in Coat.java", re.findall(r'[A-Z]+\("(\w+)"\)', src) == V.COAT_KEYS)
    add("colours = Coat.Colour", re.search(r"enum Colour \{ ([A-Z, ]+) \}", src).group(1).split(", ") == V.COLOURS)
else:
    add("Coat.java not found (skipped)", True)
add("deterministic (manifest + mask)", m == m2 and open(os.path.join(d, m["mask"]["file"]), "rb").read() == open(os.path.join(os.path.dirname(p2), m2["mask"]["file"]), "rb").read())
add("SMOKE = desaturated 50/50 linear mix of EMBER and ASH", all(abs(a - b) < 0.004 for k in ("base", "pattern") for a, b in zip(V.lin(C["SMOKE"][k]), V.smoke_mix(V.lin(C["EMBER"][k]), V.lin(C["ASH"][k])))))
add("SMOKE sits between EMBER and ASH in luminance", all(min(V.lin(C["EMBER"][k])[1], V.lin(C["ASH"][k])[1]) <= V.lin(C["SMOKE"][k])[1] <= max(V.lin(C["EMBER"][k])[1], V.lin(C["ASH"][k])[1]) + 0.02 for k in ("base", "pattern")))
add("6 MIs (3 colours x storm on/off)", len(m["variants"]) == 6 and len({v["name"] for v in m["variants"]}) == 6)
add("each MI has exactly CoatBase, CoatPattern, StormStreakMask, StormStreakAmount", all(set(v["params"]) == {"CoatBase", "CoatPattern", "StormStreakMask", "StormStreakAmount"} for v in m["variants"]))
add("storm fade 1 only on storm-marked", all(v["params"]["StormStreakAmount"]["value"] == (1.0 if v["storm_marked"] else 0.0) for v in m["variants"]))
add("lookup keyed by every coat key x colour x storm (24)", len(m["lookup"]) == 24 and all(any(k.startswith(c + "/") for k in m["lookup"]) for c in V.COAT_KEYS))
add("lookup targets exist", set(m["lookup"].values()) == {v["name"] for v in m["variants"]})
add("Dark/Accent untouched, Coat slot only", m["slot"] == "Coat" and m["untouched_slots"] == ["Dark", "Accent"])
add("linear values in 0..1", all(0 <= x <= 1 for v in m["variants"] for k in ("CoatBase", "CoatPattern") for x in v["params"][k]["linear_rgba"]))
raw = open(os.path.join(d, m["mask"]["file"]), "rb").read()
add("mask is an 8-bit greyscale PNG 256x512", raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[16:24] == bytes.fromhex("0000010000000200") and raw[24] == 8 and raw[25] == 0)
w, h, rows = V.streak_mask()
cov = sum(sum(1 for b in r if b > 127) for r in rows) / (w * h)
add("streak covers 8-20 %% of the projection (%.1f %%)" % (cov * 100), 0.08 <= cov <= 0.20)
add("streak stays on the back (u 0.3..0.7)", all(b == 0 for r in rows for x, b in enumerate(r) if not (0.3 * w <= x <= 0.7 * w)))
add("mask projection matches the pup Coat bounds (cm)", m["mask"]["u"] == {"axis": "X", "min_cm": -11.0, "size_cm": 22.0} and m["mask"]["v"] == {"axis": "Y", "min_cm": -38.5, "size_cm": 70.0})
ok = 0
for n, r in checks:
    ok += r; print(("ok   " if r else "FAIL ") + n)
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
