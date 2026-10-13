# SPDX-License-Identifier: MIT
"""Chapter 8 'Fire Keeper': intermediate-disturbance hypothesis. Each tile burns with probability p per year;
mosaic diversity (Shannon H over seral stages) is low with no fire (all climax), low with constant fire (all pioneer),
and peaks in between. The player sets the burn rate at the Fire Altar; the chapter passes when H >= target."""
import random
from succession_sim import Island
def fire_regime(p, years=120, n=12, seed=0, tail=20):
    rng = random.Random(seed); I = Island(n, 0); hs = []
    for y in range(years):
        I.step(1)
        for j in range(n):
            for i in range(n):
                if rng.random() < p: I.t[j][i] = 0.0
        if y >= years - tail: hs.append(I.shannon())
    return sum(hs) / len(hs)
def best_rate(rates=(0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32), seed=0):
    return max(rates, key=lambda p: fire_regime(p, seed=seed))
if __name__ == "__main__":
    for p in (0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32): print(p, round(fire_regime(p), 3))
