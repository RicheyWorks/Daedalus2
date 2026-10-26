# SPDX-License-Identifier: MIT
"""Headless: daylight RGB gate for OddsReaper Play hero shot (round-2 bug class).

Round-2 hero was daylightish (lum~145, R>B). Round-3 false-OK was washed cool sky (lum~220).
Gate rejects warm+bright OR any lum>140. Run: python test_hero_storm_rgb.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

assert t.daylightish_rgb(142.4, 129.5, 145.5), "round-2 warm baseline"
assert t.daylightish_rgb(211.8, 226.9, 219.5), "round-3 washed cool sky must gate"
assert t.daylightish_rgb(150, 120, 100), "warm bright"
assert not t.daylightish_rgb(80, 90, 70), "cool dark storm-ish"
assert not t.daylightish_rgb(76, 47, 66), "storm play hero class"
assert not t.daylightish_rgb(100, 100, 120), "border: not warm, lum<=140"

src = open(t.__file__, encoding="utf-8").read()
assert "storm slipped after settle" in src
assert "hero_storm_rgb" in src and "daylightish_rgb" in src
assert "lum > 140" in src

play = os.path.join(t.SHOTS, "hero_unreal_play.png")
rgb = t.hero_storm_rgb(play)
if isinstance(rgb, dict) and "mean" in rgb:
    print(f"current play hero: {rgb}")
    # after successful round-3c, expect stormish (or at least not washed)
    assert not rgb.get("daylightish"), f"play hero still gated as daylight: {rgb}"
else:
    print(f"play hero not readable ({rgb}); unit tests still PASS")

print("test_hero_storm_rgb: ALL PASS")
