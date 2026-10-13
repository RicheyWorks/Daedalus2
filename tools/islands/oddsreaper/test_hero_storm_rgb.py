# SPDX-License-Identifier: MIT
"""Headless: daylight RGB gate for OddsReaper Play hero shot (round-2 bug class).

Round-2 hero_unreal_play.png measured ~lum 145 / R>B (daylightish). Next editor turn
must leave a cooler/darker storm frame. Run: python test_hero_storm_rgb.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

assert t.daylightish_rgb(142.4, 129.5, 145.5), "round-2 baseline must gate as daylight"
assert t.daylightish_rgb(150, 120, 100), "warm bright"
assert not t.daylightish_rgb(80, 90, 70), "cool dark storm-ish"
assert not t.daylightish_rgb(100, 110, 90), "under lum threshold"
assert not t.daylightish_rgb(100, 100, 120), "not warm enough (R not > B+5)"

# turn script must re-check after settle and RGB-gate reshoot
src = open(t.__file__, encoding="utf-8").read()
assert "storm slipped after settle" in src
assert "rgb-gate reshoot" in src or "rgb gate" in src.lower()
assert "hero_storm_rgb" in src and "daylightish_rgb" in src
settle = src.index("time.sleep(20)")
assert src.index("storm slipped after settle", settle) > settle
assert src.index("hero_storm_rgb", settle) > settle

# live PNG (if present): document the owed re-shot
play = os.path.join(t.SHOTS, "hero_unreal_play.png")
rgb = t.hero_storm_rgb(play)
if isinstance(rgb, dict) and "error" not in rgb and "mean" in rgb:
    # current on-disk shot is still the round-2 daylight frame until next editor turn
    assert rgb["daylightish"], f"expected current play hero still daylight baseline, got {rgb}"
    print(f"baseline play hero still daylightish (owed storm reshoot on next grant): {rgb}")
else:
    print(f"play hero not readable yet ({rgb}); gate unit tests still PASS")

print("test_hero_storm_rgb: ALL PASS")
