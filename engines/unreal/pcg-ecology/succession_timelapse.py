# SPDX-License-Identifier: MIT
"""SUCCESSION time-lapse: renders the 0-1-2-3 stage mosaic of a 24x24 island under three fire rates over 100 years
into succession_timelapse.png (rows = burn rate, columns = year) for the contest board."""
import random
from PIL import Image, ImageDraw
from succession_sim import Island
COL = [(214, 196, 120), (120, 190, 80), (60, 130, 70), (30, 80, 40)]
def run(p, years, n=24, seed=1):
    rng = random.Random(seed); I = Island(n, 0); snaps = {}
    for y in range(1, years + 1):
        I.step(1)
        for j in range(n):
            for i in range(n):
                if rng.random() < p: I.t[j][i] = 0.0
        if y in (5, 15, 30, 60, 100): snaps[y] = ([[min(3, I.stage(i, j)) for i in range(n)] for j in range(n)], I.shannon())
    return snaps
def render(path="succession_timelapse.png", rates=(0.0, 0.03, 0.32), cell=6):
    n = 24; W = n * cell + 10; img = Image.new("RGB", (5 * W + 90, len(rates) * (W + 20) + 20), "white"); d = ImageDraw.Draw(img)
    for r, p in enumerate(rates):
        d.text((4, 20 + r * (W + 20) + W // 2), "p=%.2f" % p, fill="black")
        for c, (yr, (g, h)) in enumerate(sorted(run(p, 100).items())):
            ox, oy = 80 + c * W, 20 + r * (W + 20)
            if r == 0: d.text((ox, 4), "year %d" % yr, fill="black")
            for j in range(n):
                for i in range(n): d.rectangle([ox + i * cell, oy + j * cell, ox + i * cell + cell - 1, oy + j * cell + cell - 1], fill=COL[g[j][i]])
            d.text((ox, oy + n * cell + 2), "H=%.2f" % abs(h), fill="black")
    img.save(path); return path
if __name__ == "__main__": print(render())

