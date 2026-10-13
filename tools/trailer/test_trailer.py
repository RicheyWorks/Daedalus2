# SPDX-License-Identifier: MIT
"""Offline checks of the trailer plan. Run: python test_trailer.py"""
import math
import trailer_plan as t

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


fr = t.frames()
starts = t.shot_starts()
check("frame count is the sum of the shots", len(fr) == sum(int(round(s[1] * t.FPS)) for s in t.SHOTS))
check("indices run 0..n-1", [f[0] for f in fr] == list(range(len(fr))))
check("shots are contiguous", all(starts[n][0] + starts[n][1] == starts[m][0]
                                  for (n, *_), (m, *_) in zip(t.SHOTS, t.SHOTS[1:])))
check("pitch looks down at the ground from above", all(f[3][0] < 0 for f in fr))
check("easing starts and ends still", t.smooth(0) == 0 and t.smooth(1) == 1 and abs(t.smooth(0.5) - 0.5) < 1e-9)
p, y = t.rotation((0, 0, 0), (100, 0, 0))
check("rotation: +X is yaw 0, level", abs(p) < 1e-9 and abs(y) < 1e-9)
p, y = t.rotation((0, 0, 100), (0, 100, 0))
check("rotation: down-left is yaw 90, pitch -45", abs(y - 90) < 1e-9 and abs(p + 45) < 1e-9)
e0, _ = t.camera("orbit", t.SHOTS[0][3], 0)
check("orbit keeps its radius", abs(math.hypot(e0[0] - 20000, e0[1] + 9000) - 32000) < 1e-6)
e1, tg = t.camera("follow", {"c": (10, 20, 30), "r": 100, "h": 50, "a0": 0, "a1": 0, "lz": 30}, 0.5)
check("follow orbits its centre like an orbit", abs(e1[0] - 110) < 1e-6 and abs(e1[2] - 80) < 1e-6 and tg == (10, 20, 30))
check("both herd shots follow live animals", [s[2] for s in t.SHOTS if s[0].startswith("herd")] == ["follow", "follow"])
check("every caption is original text (no third-party names)", all(s[4].isupper() for s in t.SHOTS))
rs = t.gate_row_shots([(4800, -21000, 7200), (14400, -21000, 7200), (24000, -21000, 7200)])
e, tg = t.camera("dolly", rs["through"], 1.0)
check("fly-through ends just in front of gate 0, looking through it", e[1] > -21000 and tg[1] < -21000)
e, _ = t.camera("dolly", rs["rainbows"], 0.0)
check("wide shot starts on the islands' side of the gate row", e[1] > -21000 and e[2] > 7200)
o = t.realm_orbit((0, 0, 0), (10000, 6000, 2000))
check("realm orbit frames the larger half-extent", o["r"] == 12500 and o["h"] > 2000)
check("part 2 starts past the rainbows and ends healing the planet",
      t.REALM_SEGMENTS[0][0] == "rainbows" and t.REALM_SEGMENTS[-1][0] == "heal")
check("part 2 lasts 30-45 s", 30 <= sum(s[1] for s in t.REALM_SEGMENTS) <= 45)
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
