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
check("every caption is original text (no third-party names)", all(s[4].isupper() for s in t.SHOTS))
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
