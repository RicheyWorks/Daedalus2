# SPDX-License-Identifier: MIT
"""Ch.8 Rate Dial runtime: dial position 0..1 -> burn rate, mosaic H (cached sim), pass/fail and the forester's line.
Blueprint/Python can call dial_state(pos) when the player turns Prop_Dress_PYT_RateDial."""
import json, os, functools
from fire_keeper import fire_regime
SPEC = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chapter8_fire_keeper.json"), encoding="utf-8-sig"))["dial"]
@functools.lru_cache(maxsize=128)
def _h(rate): return round(fire_regime(rate), 3)
def dial_state(pos):
    pos = min(1.0, max(0.0, pos)); st = SPEC["step"]
    rate = round(round(pos * SPEC["max"] / st) * st, 4); h = _h(rate)
    key = min(SPEC["feedback"], key=lambda k: abs(float(k) - rate))
    return {"rate": rate, "H": h, "pass": h >= SPEC["target_h"], "line": SPEC["feedback"][key]}

def simulate_grid(rate, wet=(), n=12, years=100, seed=0):
    """Stage grid (0-3, 4 = wetland) after `years` of burning at `rate`; the in-editor dial overlay draws exactly this."""
    import random
    from succession_sim import Island
    wet = set(wet); rng = random.Random(seed); I = Island(n, 0); I.dig(list(wet))
    for _ in range(years):
        I.step(1)
        for j in range(n):
            for i in range(n):
                if (i, j) not in wet and rng.random() < rate: I.t[j][i] = 0.0
    return [[4 if (i, j) in wet else min(3, I.stage(i, j)) for i in range(n)] for j in range(n)]
