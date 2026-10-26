# SPDX-License-Identifier: MIT
"""Battle spell effects for the two RPG realms — 17 original effects x 3 tiers = 51 spells, animated pixel strips.

    python tools/blender/rpg_spell_fx.py OUT_ROOT [ROOT_FOR_DATA]

Every effect is an intensity field over the frame (0 = nothing, 1 = hottest), drawn procedurally per frame and
quantised onto the element's colour ramp, so the look is the console one: flat bands, no blur.
  Portal Realm (8-bit):       32 px grid, 8 frames,  3-step ramp (+ transparent), shown x4 = 128 px
  Prismheart Realm (16-bit):  48 px grid, 10 frames, 6-step ramp + a white-hot core, shown x4 = 192 px
Tiers grow the effect: 1 = a single target puff, 2 = bigger with secondary parts, 3 = fills the enemy side.

Outputs OUT_ROOT/claude-battle-kit/<realm>/spells/Spell_<Name>.png (x4 strip) + _1x.png, sheet-spells.png (peak
frame of every spell) and data/rpg/spells.json: name, effect, element (the bestiary's: fire, ice, water, air,
earth, light, dark, none), tier, MP, power, target, status, and the strip paths/frame counts the battle screen reads.
Elements line up with the bestiary so a spell's element meets an enemy's weakness. Pure numpy (no Blender, no PIL).
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402

STYLE = {"portal": {"grid": 32, "frames": 8, "steps": 3, "k": 4}, "prism": {"grid": 48, "frames": 10, "steps": 6, "k": 4}}
RAMPS = {   # dark -> mid -> bright (Prismheart interpolates 6 steps through these; Portal uses the 3 stops)
    "fire": ("#a01808", "#f07018", "#fff070"), "ice": ("#2858b8", "#78c8f8", "#f0fcff"), "air": ("#3070a0", "#a8e0f8", "#ffffff"),
    "bolt": ("#8058d8", "#f8e048", "#ffffff"), "water": ("#103890", "#3888e0", "#b8f0ff"), "earth": ("#583818", "#a07040", "#e0c088"),
    "light": ("#c09020", "#f8e898", "#ffffff"), "dark": ("#100818", "#583080", "#c088f0"), "heal": ("#108048", "#58e098", "#f0fff0"),
    "poison": ("#304010", "#78b020", "#d8f878"), "sleep": ("#3848a0", "#a8a8f0", "#ffffff"), "shield": ("#1868a8", "#68d0e8", "#f0ffff"),
    "haste": ("#a05010", "#f8b838", "#fff8d0"), "slow": ("#405068", "#90a8c0", "#e8f0f8"), "meteor": ("#401810", "#c05018", "#ffd060"),
    "drain": ("#380818", "#a02848", "#f898b8"),
}
SPELLS = [  # effect, ramp, element, names x3, target, status
    ("fire", "fire", "fire", ("Ember", "Blaze", "Inferno"), "enemy", None),
    ("ice", "ice", "ice", ("Frost", "Glacier", "Whiteout"), "enemy", None),
    ("bolt", "bolt", "air", ("Spark", "Thunderhead", "Skyfall"), "enemy", None),
    ("water", "water", "water", ("Splash", "Torrent", "Maelstrom"), "enemy", None),
    ("wind", "air", "air", ("Gust", "Gale", "Cyclone"), "enemy", None),
    ("quake", "earth", "earth", ("Tremor", "Quake", "Cataclysm"), "all_enemies", None),
    ("meteor", "meteor", "earth", ("Rockfall", "Comet", "Skybreaker"), "all_enemies", None),
    ("holy", "light", "light", ("Radiance", "Sunlance", "Dawnbreak"), "enemy", None),
    ("shade", "dark", "dark", ("Gloom", "Umbra", "Eclipse"), "enemy", None),
    ("drain", "drain", "dark", ("Siphon", "Leech", "Devour"), "enemy", "drain_hp"),
    ("poison", "poison", "none", ("Blight", "Venom", "Plague"), "enemy", "poison"),
    ("sleep", "sleep", "none", ("Drowse", "Slumber", "Dreamfall"), "enemy", "sleep"),
    ("prism", "light", "none", ("Glint", "Prismatic", "Heartlight"), "all_enemies", None),
    ("heal", "heal", "light", ("Mend", "Restore", "Renewal"), "ally", "heal"),
    ("shield", "shield", "none", ("Ward", "Bulwark", "Aegis"), "ally", "protect"),
    ("haste", "haste", "none", ("Quicken", "Hasten", "Overdrive"), "ally", "haste"),
    ("slow", "slow", "none", ("Lull", "Slow", "Stasis"), "enemy", "slow"),
]
POWER = (20, 55, 120)
MP = {"enemy": (4, 12, 30), "all_enemies": (8, 20, 44), "ally": (5, 14, 32)}


def ramp(name, steps):
    stops = [np.array(P.hexc(c)) for c in RAMPS[name]]
    if steps == 3:
        return stops
    out = []
    for i in range(steps):
        t = i / (steps - 1) * 2
        a, b = (stops[0], stops[1]) if t <= 1 else (stops[1], stops[2])
        f = t if t <= 1 else t - 1
        out.append(a * (1 - f) + b * f)
    return out


class Field:
    """Coordinates: X in [0,1] left->right, Y in [0,1] bottom->top, per grid cell centre."""

    def __init__(self, g):
        self.g = g
        c = (np.arange(g) + 0.5) / g
        self.X, self.Y = np.meshgrid(c, c[::-1])
        self.I = np.zeros((g, g))

    def blob(self, cx, cy, r, amp=1.0, sx=1.0, sy=1.0):
        d = np.sqrt(((self.X - cx) / sx) ** 2 + ((self.Y - cy) / sy) ** 2)
        self.I = np.maximum(self.I, amp * np.clip(1 - d / max(r, 1e-3), 0, 1))

    def seg(self, x0, y0, x1, y1, w, amp=1.0):
        px, py = self.X - x0, self.Y - y0
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy + 1e-9
        t = np.clip((px * dx + py * dy) / L2, 0, 1)
        d = np.hypot(px - t * dx, py - t * dy)
        self.I = np.maximum(self.I, amp * np.clip(1 - d / max(w, 1e-3), 0, 1))

    def ring(self, cx, cy, r, w, amp=1.0, sy=1.0):
        d = np.abs(np.hypot(self.X - cx, (self.Y - cy) / sy) - r)
        self.I = np.maximum(self.I, amp * np.clip(1 - d / max(w, 1e-3), 0, 1))

    def poly(self, pts, amp=1.0, edge=None):
        """Filled convex-ish polygon (even-odd), intensity amp; optional brighter edge width."""
        x, y = self.X, self.Y
        inside = np.zeros_like(x, bool)
        n = len(pts)
        for i in range(n):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
            cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1)
            inside ^= cond
        self.I = np.where(inside, np.maximum(self.I, amp), self.I)
        if edge:
            for i in range(n):
                self.seg(*pts[i], *pts[(i + 1) % n], edge, 1.0)


def noise(g, rng, cells=6):
    n = rng.random((cells + 1, cells + 1))
    c = np.linspace(0, cells, g)
    i = np.clip(c.astype(int), 0, cells - 1)
    f = c - i
    a = n[i][:, i] * (1 - f)[None, :] + n[i][:, i + 1] * f[None, :]
    b = n[i + 1][:, i] * (1 - f)[None, :] + n[i + 1][:, i + 1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def _targets(tier):
    return [(0.5, 0.42)] if tier == 1 else [(0.5, 0.42), (0.26, 0.55), (0.74, 0.55)] if tier == 2 else \
        [(0.5, 0.40), (0.22, 0.30), (0.78, 0.30), (0.30, 0.68), (0.70, 0.68)]


def fx_fire(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        grow = min(1.0, t * 2.2) * (1 - max(0.0, (t - 0.75) * 4))
        n = noise(F.g, np.random.default_rng(seed * 31 + i * 7 + int(t * 20)), 5)
        h = (0.32 + 0.08 * tier) * grow
        base = cy - 0.18
        z = (F.Y - base) / max(h, 1e-3)
        width = 0.16 * (1 - z * 0.7) * (1 + 0.15 * tier)
        lick = np.sin(F.Y * 22 - t * 30 + i) * 0.03 * z
        d = np.abs(F.X - cx - lick) / np.maximum(width, 1e-3)
        I = np.clip(1 - d, 0, 1) * np.clip(1 - z, 0, 1) * (z > -0.1) * (0.75 + 0.5 * n)
        F.I = np.maximum(F.I, np.clip(I * 1.3, 0, 1))
        if t > 0.55:                                                            # embers drift up
            for k in range(2 + tier):
                F.blob(cx + 0.15 * math.sin(k * 2.3 + t * 9), base + h + 0.08 * k * t, 0.03, 0.8)


def fx_ice(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        r = np.random.default_rng(seed + i)
        g = min(1.0, t * 1.8)
        if t < 0.7:
            for k in range(3 + tier):
                a = k / (3 + tier) * 2 * math.pi + r.random() * 0.4
                L = (0.12 + 0.06 * r.random()) * g * (1 + 0.2 * tier)
                tip = (cx + math.cos(a) * L, cy + math.sin(a) * L)
                side = (math.cos(a + 1.57) * 0.035 * g, math.sin(a + 1.57) * 0.035 * g)
                F.poly([(cx + side[0], cy + side[1]), tip, (cx - side[0], cy - side[1])], 0.55, edge=0.02)
            F.blob(cx, cy, 0.07 * g, 1.0)
        else:                                                                   # shatter: shards fly out and fade
            s = (t - 0.7) / 0.3
            for k in range(6 + 2 * tier):
                a = k * 2.399
                d = 0.08 + 0.25 * s
                F.blob(cx + math.cos(a) * d, cy + math.sin(a) * d, 0.03 * (1 - s) + 0.01, 1 - 0.6 * s)


def fx_bolt(F, t, tier, rng, seed):
    fr = int(t * 10)
    flash = 1.0 if 0.12 < t < 0.6 else 0.45 if t < 0.75 else 0.0
    if flash == 0:
        return
    for i, (cx, cy) in enumerate(_targets(tier)):
        r = np.random.default_rng(seed * 13 + i * 5 + fr)
        x, y = cx + r.uniform(-0.1, 0.1), 1.02
        pts = [(x, y)]
        while y > cy:
            y -= 0.09
            x += r.uniform(-0.07, 0.07)
            pts.append((x, max(y, cy)))
        for a, b in zip(pts, pts[1:]):
            F.seg(*a, *b, 0.03 + 0.008 * tier, flash)
            if tier > 1 and r.random() < 0.3:
                F.seg(*b, b[0] + r.uniform(-0.12, 0.12), b[1] - 0.08, 0.018, flash * 0.7)
        F.blob(cx, cy, 0.09 + 0.03 * tier, flash)


def fx_water(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        rise = min(1.0, t * 1.6)
        top = cy - 0.15 + (0.35 + 0.05 * tier) * rise
        w = 0.07 + 0.02 * tier
        wob = np.sin(F.Y * 25 + t * 25) * 0.015
        col = (np.abs(F.X - cx - wob) < w) & (F.Y > cy - 0.18) & (F.Y < top)
        F.I = np.where(col, np.maximum(F.I, 0.6 + 0.4 * (np.abs(F.X - cx - wob) < w * 0.4)), F.I)
        F.ring(cx, cy - 0.16, 0.06 + 0.25 * t, 0.025, 0.85, sy=0.35)
        if t > 0.5:
            for k in range(3 + tier):
                a = k * 1.9 + t * 3
                F.blob(cx + math.cos(a) * 0.12 * (t - 0.4) * 3, top - 0.05 + math.sin(a) * 0.05 - (t - 0.5) * 0.4, 0.03, 0.9)


def fx_wind(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        for arm in range(2 + tier):
            ph = arm / (2 + tier) * 2 * math.pi + t * 9
            pts = []
            for s in np.linspace(0.02, 0.22 + 0.04 * tier, 10):
                a = ph + s * 16
                pts.append((cx + math.cos(a) * s, cy + math.sin(a) * s * 0.65 + (s - 0.1) * 0.4))
            for a, b in zip(pts, pts[1:]):
                F.seg(*a, *b, 0.018, 0.55 + 0.45 * (1 - abs(t - 0.5) * 2))


def fx_quake(F, t, tier, rng, seed):
    shake = 0.02 * math.sin(t * 50)
    ground = 0.22
    for k in range(4 + 3 * tier):
        r = np.random.default_rng(seed + k)
        x = r.uniform(0.1, 0.9)
        start = r.uniform(0, 0.4)
        s = np.clip((t - start) / 0.4, 0, 1)
        y = 1.05 - s * (1.05 - ground - 0.04) + (0.05 * math.sin(min(1, (t - start - 0.4) / 0.2) * math.pi) if t > start + 0.4 else 0)
        sz = 0.035 + 0.02 * r.random()
        F.poly([(x - sz + shake, y - sz), (x + sz + shake, y - sz * 0.8), (x + sz * 0.8 + shake, y + sz), (x - sz * 0.9 + shake, y + sz * 0.9)], 0.5, edge=0.015)
    for k in range(tier + 1):                                                   # cracks in the ground
        x0 = 0.15 + 0.7 * ((k * 0.37 + 0.2) % 1)
        L = 0.15 * min(1, t * 2)
        F.seg(x0, ground, x0 + L * 0.6, ground - 0.05, 0.015, 0.9)
        F.seg(x0, ground, x0 - L * 0.5, ground - 0.07, 0.015, 0.9)
    if t > 0.4:
        dust = (F.Y < ground + 0.12 * (t - 0.3)) & (F.Y > ground - 0.04)
        F.I = np.where(dust, np.maximum(F.I, 0.35 * noise(F.g, np.random.default_rng(int(t * 30)), 8)), F.I)


def fx_meteor(F, t, tier, rng, seed):
    for k, (cx, cy) in enumerate(_targets(tier)):
        start = k * 0.08
        s = np.clip((t - start) / 0.55, 0, 1)
        if s < 1:
            hx, hy = cx + 0.45 * (1 - s), cy + 0.6 * (1 - s)
            F.seg(hx, hy, hx + 0.22, hy + 0.3, 0.035, 0.6)
            F.blob(hx, hy, 0.06 + 0.015 * tier, 1.0)
        else:
            b = np.clip((t - start - 0.55) / 0.35, 0, 1)
            F.blob(cx, cy, 0.08 + 0.2 * b, 1 - b * 0.7)
            F.ring(cx, cy, 0.05 + 0.28 * b, 0.03, 1 - b)


def fx_holy(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        w = (0.05 + 0.02 * tier) * min(1, t * 2.5) * (1 - max(0, (t - 0.8) * 5))
        F.I = np.maximum(F.I, np.clip(1 - np.abs(F.X - cx) / max(w, 1e-3), 0, 1) * (F.Y > cy - 0.18))
        for k in range(2):
            F.ring(cx, cy - 0.15, ((t * 1.5 + k * 0.5) % 1) * 0.25, 0.02, 0.8, sy=0.3)
        for k in range(3 + tier):
            F.blob(cx + 0.15 * math.sin(k * 2 + t * 6), cy - 0.1 + ((t + k * 0.23) % 1) * 0.6, 0.022, 0.95)


def fx_shade(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        if t < 0.6:
            s = t / 0.6
            for k in range(8 + 4 * tier):
                a = k * 2.399 + s * 2
                d = (0.35 + 0.05 * tier) * (1 - s)
                F.blob(cx + math.cos(a) * d, cy + math.sin(a) * d, 0.03, 0.55)
            F.blob(cx, cy, 0.05 + 0.1 * s, 0.75)
            F.ring(cx, cy, 0.05 + 0.1 * s, 0.015, 1.0)
        else:
            b = (t - 0.6) / 0.4
            F.ring(cx, cy, 0.1 + 0.3 * b, 0.05 * (1 - b) + 0.01, 0.9)
            F.blob(cx, cy, 0.15 * (1 - b), 0.6)


def fx_drain(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        for k in range(6 + 3 * tier):
            ph = (t * 1.5 + k / (6 + 3 * tier)) % 1
            a = k * 2.399 + ph * 5
            d = 0.28 * (1 - ph)
            if t < 0.6:
                F.blob(cx + math.cos(a) * d, cy + math.sin(a) * d, 0.025, 0.95)
            else:                                                               # the stolen life streams off to the caster (left)
                s = (t - 0.6) / 0.4
                F.blob(cx - s * 0.6 + 0.03 * math.sin(k), cy + 0.1 * math.sin(k * 1.7 + s * 6), 0.025, 0.95)
        F.blob(cx, cy, 0.08 * (1 - abs(t - 0.5) * 2) + 0.02, 0.5)


def fx_poison(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        F.blob(cx, cy - 0.12, 0.2, 0.35, sy=0.4)
        for k in range(5 + 3 * tier):
            r = np.random.default_rng(seed + k + i * 50)
            x = cx + r.uniform(-0.15, 0.15)
            ph = (t * 1.3 + r.random()) % 1
            y = cy - 0.12 + ph * 0.45
            rad = 0.02 + 0.03 * ph
            if ph < 0.85:
                F.ring(x, y, rad, 0.012, 0.95)
                F.blob(x, y, rad * 0.6, 0.45)
            else:
                F.ring(x, y, rad * 1.6, 0.01, 0.6)                              # pop


def fx_sleep(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        for k in range(2 + tier):
            ph = (t + k / (2 + tier)) % 1
            x = cx + 0.08 * math.sin(ph * 6 + k) + 0.05 * k
            y = cy + ph * 0.45
            s = 0.04 + 0.03 * ph
            a = 1 - ph * 0.6
            F.seg(x - s, y + s, x + s, y + s, 0.016, a)                         # a "Z"
            F.seg(x + s, y + s, x - s, y - s, 0.016, a)
            F.seg(x - s, y - s, x + s, y - s, 0.016, a)
        F.blob(cx, cy, 0.18, 0.25 + 0.1 * math.sin(t * 6))


def fx_prism(F, t, tier, rng, seed):
    cx, cy = 0.5, 0.45
    n = 6 + 2 * tier
    L = (0.25 + 0.12 * tier) * min(1, t * 2)
    for k in range(n):
        a = k / n * 2 * math.pi + t * 2.5
        F.seg(cx, cy, cx + math.cos(a) * L, cy + math.sin(a) * L, 0.025, 0.85)
    F.blob(cx, cy, 0.08 + 0.03 * math.sin(t * 12), 1.0)
    F.hue = (np.arctan2(F.Y - cy, F.X - cx) / (2 * math.pi) + t * 0.4) % 1          # rainbow by angle


def fx_heal(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        F.blob(cx, cy, 0.22 * min(1, t * 3) * (1 - max(0, t - 0.7) * 3), 0.4)
        for k in range(4 + 2 * tier):
            ph = (t * 1.2 + k / (4 + 2 * tier)) % 1
            x = cx + 0.18 * math.sin(k * 2.1)
            y = cy - 0.15 + ph * 0.5
            s = 0.025 + 0.01 * (k % 2)
            F.seg(x - s, y, x + s, y, 0.012, 1 - ph * 0.5)                       # little plus-sparkles
            F.seg(x, y - s, x, y + s, 0.012, 1 - ph * 0.5)


def fx_shield(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        r = (0.16 + 0.03 * tier) * min(1, t * 3)
        pts = [(cx + r * math.cos(k * math.pi / 3 + math.pi / 6), cy + r * math.sin(k * math.pi / 3 + math.pi / 6)) for k in range(6)]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            F.seg(*a, *b, 0.018, 1.0)
        F.poly(pts, 0.3 + 0.15 * math.sin(t * 14))
        sweep = cy - r + ((t * 2) % 1) * 2 * r
        F.I = np.where((np.abs(F.Y - sweep) < 0.015) & (np.abs(F.X - cx) < r * 0.85), np.maximum(F.I, 0.9), F.I)


def fx_haste(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        for k in range(5 + 2 * tier):
            y = cy - 0.15 + k * 0.3 / (5 + 2 * tier)
            x = cx + 0.25 - ((t * 2 + k * 0.37) % 1) * 0.5
            F.seg(x, y, x + 0.12, y, 0.014, 0.9)                                  # speed streaks
        F.ring(cx, cy, 0.09, 0.015, 0.8)
        a = t * 12
        F.seg(cx, cy, cx + math.cos(a) * 0.07, cy + math.sin(a) * 0.07, 0.014, 1.0)  # a racing clock hand


def fx_slow(F, t, tier, rng, seed):
    for i, (cx, cy) in enumerate(_targets(tier)):
        for k in range(2 + tier):
            r = (0.3 - ((t + k / (2 + tier)) % 1) * 0.28)
            F.ring(cx, cy, r, 0.015, 0.4 + 0.6 * (1 - r / 0.3))
        F.ring(cx, cy, 0.07, 0.012, 0.8)
        a = t * 1.5
        F.seg(cx, cy, cx + math.cos(a) * 0.05, cy + math.sin(a) * 0.05, 0.012, 1.0)


FX = {k[len("fx_"):]: v for k, v in globals().items() if k.startswith("fx_")}


def hsv(h):
    i = (h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    q, t_ = 1 - f, f
    o = np.ones_like(h)
    r = np.choose(i, [o, q, 0 * o, 0 * o, t_, o])
    g = np.choose(i, [t_, o, o, q, 0 * o, 0 * o])
    b = np.choose(i, [0 * o, 0 * o, t_, o, o, q])
    return np.stack([r, g, b], -1)


def render_frame(effect, rname, realm, tier, t, seed):
    st = STYLE[realm]
    F = Field(st["grid"])
    F.hue = None
    FX[effect](F, t, tier, None, seed)
    steps = st["steps"]
    rp = ramp(rname, steps)
    I = np.clip(F.I, 0, 1)
    out = np.zeros((st["grid"], st["grid"], 4), np.float32)
    mask = I > 0.14
    lvl = np.clip(((I - 0.14) / 0.86 * steps).astype(int), 0, steps - 1)
    cols = np.stack(rp)[lvl]
    if F.hue is not None:                                                      # the prism spells take the rainbow
        cols = hsv(F.hue) * (0.55 + 0.45 * (lvl[..., None] / (steps - 1))) + (lvl[..., None] == steps - 1) * 0.45
    if realm == "prism":
        cols = np.where((I > 0.93)[..., None], 1.0, cols)                       # white-hot core
    out[mask, :3] = np.clip(cols[mask], 0, 1)
    out[mask, 3] = 1
    return out


def build(out_root, data_root=None):
    rows, peaks = [], {r: [] for r in STYLE}
    for realm, st in STYLE.items():
        od = os.path.join(out_root, "claude-battle-kit", realm, "spells")
        os.makedirs(od, exist_ok=True)
        for si, (effect, rname, element, names, target, status) in enumerate(SPELLS):
            for tier in (1, 2, 3):
                name = names[tier - 1]
                frames = [render_frame(effect, rname, realm, tier, f / st["frames"], si * 100 + tier) for f in range(st["frames"])]
                strip = np.concatenate(frames, axis=1)
                fn = "Spell_%s" % name.replace(" ", "")
                P.save_png(P.upscale(strip, st["k"]), os.path.join(od, fn + ".png"))
                P.save_png(strip, os.path.join(od, fn + "_1x.png"))
                peaks[realm].append(P.upscale(frames[int(st["frames"] * 0.45)], 2))
                rows.append({"realm": realm, "name": name, "effect": effect, "element": element, "tier": tier, "target": target,
                             "status": status, "mp": MP["ally" if target == "ally" else target][tier - 1],
                             "power": POWER[tier - 1] if status in (None, "drain_hp", "heal") else 0,
                             "strip": "engines/unreal/art/claude-battle-kit/%s/spells/%s.png" % (realm, fn), "frames": st["frames"],
                             "frame_px": st["grid"] * st["k"], "fps": 12})
        P.save_png(P.grid_sheet(peaks[realm], 9), os.path.join(od, "sheet-spells.png"))
    if data_root:
        d = os.path.join(data_root, "data", "rpg")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "spells.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.spells/v1", "source": "tools/blender/rpg_spell_fx.py",
                       "elements": "match data/rpg/*-bestiary.json element names; a weakness doubles power",
                       "spells": rows}, f, indent=1)
    return rows


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    data = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    r = build(out, data)
    print("SPELLS %d strips (%d spells x 2 realms)" % (len(r), len(r) // 2))
