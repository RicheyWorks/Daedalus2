# SPDX-License-Identifier: MIT
"""Offline parity test of ADaedalusSkyDirector's sun math (claim 15). Run: python test_sky_math.py"""
import math

def pitch(h): return 90.0 - ((h % 24) + 24) % 24 * 15.0
def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0); return t * t * (3 - 2 * t)
def daylight(p): return smooth(0.0, 0.25, math.sin(math.radians(-p)))

def test():
    assert pitch(6) == 0 and pitch(12) == -90 and pitch(18) == -180 and pitch(0) == 90
    assert daylight(pitch(12)) == 1.0 and daylight(pitch(0)) == 0.0 and daylight(pitch(3)) == 0.0
    assert daylight(pitch(6)) == 0.0 and daylight(pitch(18)) < 1e-9
    assert 0 < daylight(pitch(6.5)) < 1 and daylight(pitch(9)) == 1.0
    assert all(daylight(pitch(h)) == 0 for h in (19, 21, 23.9, 0.5, 5.9))
    assert abs(daylight(pitch(7)) - daylight(pitch(17))) < 1e-9, "dawn/dusk symmetric"
    print("sky math: PASS")

if __name__ == "__main__": test()
