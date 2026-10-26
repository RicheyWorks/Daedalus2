# SPDX-License-Identifier: MIT
"""Ch.8 x ch.9 visual: 24x24 island at burn p=0.08 for 100 years, without and with two beaver-dam wetlands (blue = wetland, never burns)."""
import random
from PIL import Image, ImageDraw
from succession_sim import Island
COL = [(214, 196, 120), (120, 190, 80), (60, 130, 70), (30, 80, 40)]; WET = (70, 140, 210)
def run(p, wet, n=24, years=100, seed=1):
    rng = random.Random(seed); I = Island(n, 0); I.dig(list(wet))
    for _ in range(years):
        I.step(1)
        for j in range(n):
            for i in range(n):
                if (i, j) not in wet and rng.random() < p: I.t[j][i] = 0.0
    return I
def render(path="wetland_firebreak.png", cell=8):
    n = 24; wet = {(i, j) for c in (14, 20) for i in range(c - 2, c + 3) for j in range(10, 15)}
    img = Image.new("RGB", (2 * (n * cell + 20) + 20, n * cell + 50), "white"); d = ImageDraw.Draw(img)
    for k, (title, w) in enumerate((("burn p=0.08, no dams", set()), ("burn p=0.08, two beaver dams", wet))):
        I = run(0.08, w); ox = 20 + k * (n * cell + 20)
        for j in range(n):
            for i in range(n):
                c = WET if (i, j) in w else COL[min(3, I.stage(i, j))]
                d.rectangle([ox + i * cell, 20 + j * cell, ox + i * cell + cell - 1, 20 + j * cell + cell - 1], fill=c)
        d.text((ox, 4), title, fill="black"); d.text((ox, 24 + n * cell), "H=%.2f" % abs(I.shannon()), fill="black")
    img.save(path); return path
if __name__ == "__main__": print(render())
