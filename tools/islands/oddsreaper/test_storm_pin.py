# SPDX-License-Identifier: MIT
"""Headless check (no Unreal): the PIE storm snippet pins the Mood Volume before apply_now, so its view Tick
(player camera on the main island) cannot Restore() daylight before the hero shot. Run: python test_storm_pin.py"""
import ast, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

ast.parse(t.STORM_CODE); ast.parse(t.STORM_CHECK_CODE)
c = t.STORM_CODE
assert c.index("'trigger_on_view', False") < c.index("apply_now(True)"), "view trigger must be off before apply_now"
assert "'restore_on_exit', False" in c
assert c.count("if v and hasattr(v[0], 'apply_now'):") == 1, "director re-force marker missing"
ast.parse(c.replace("if v and hasattr(v[0], 'apply_now'):", "if False:"))
assert "clock_running" in c.split("elif d:")[1], "director fallback must hold the clock"
assert t.storm_held({"weather": "DaedalusWeather.STORM", "mood": "oddsreaper_storm", "hour": 18.75})
assert not t.storm_held({"weather": "DaedalusWeather.CLEAR", "mood": "young_meadow", "hour": 9.25})
assert not t.storm_held(None)
print("test_storm_pin: ALL PASS")
