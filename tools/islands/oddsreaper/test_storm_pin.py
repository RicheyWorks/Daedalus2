# SPDX-License-Identifier: MIT
"""Headless check (no Unreal): the PIE storm snippet pins the Mood Volume before apply_now, so its view Tick
(player camera on the main island) cannot Restore() daylight before the hero shot. Also checks OddsReaper
sublevel streaming + materials_mpc storm MPC push before the volume search, and post-settle re-pin + RGB gate.
Run: python test_storm_pin.py"""
import ast, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

ast.parse(t.STORM_CODE); ast.parse(t.STORM_CHECK_CODE)
c = t.STORM_CODE
assert "get_streaming_levels" in c, "must ensure OddsReaperIsland streaming before volume search"
assert "streamed" in c and "mpc_set" in c and "MPC_OR_SkyWeather" in c
assert "Wetness" in c and "StormPulse" in c and "WindStrength" in c
# pin before apply_now (double or single quotes depending on patch)
pin = '"trigger_on_view", False' if '"trigger_on_view", False' in c else "'trigger_on_view', False"
apply = "apply_now(True)"
assert c.index(pin) < c.index(apply), "view trigger must be off before apply_now"
assert ("'restore_on_exit', False" in c) or ('"restore_on_exit", False' in c)
marker_dq = 'if v and hasattr(v[0], "apply_now"):'
marker_sq = "if v and hasattr(v[0], 'apply_now'):"
assert (c.count(marker_dq) + c.count(marker_sq)) == 1, "director re-force marker missing"
marker = marker_dq if marker_dq in c else marker_sq
ast.parse(c.replace(marker, "if False:"))
assert "clock_running" in c.split("elif d:")[1], "director fallback must hold the clock"
assert t.storm_held({"weather": "DaedalusWeather.STORM", "mood": "oddsreaper_storm", "hour": 18.75})
assert not t.storm_held({"weather": "DaedalusWeather.CLEAR", "mood": "young_meadow", "hour": 9.25})
assert not t.storm_held(None)
src = open(t.__file__, encoding="utf-8").read()
assert "Play start (storm then 20s settle)" in src, "Play must force storm before the 20s settle"
play_i = src.index("Play start (storm then 20s settle)")
assert src.index("force_storm_in_pie()", play_i) < src.index("time.sleep(20)", play_i)
# post-settle re-pin before shot (storm can slip during the 20s wait)
assert "storm slipped after settle" in src
assert src.index("time.sleep(20)", play_i) < src.index("storm slipped after settle", play_i)
assert "hero_storm_rgb" in src and "daylightish" in src
# volumes=0 fix: flush streaming before the search, fall back to the mood row when PIE labels miss
assert "flush_level_streaming" in c and c.index("flush_level_streaming") < c.index("get_all_actors_of_class(w, unreal.DaedalusMoodVolume)")
assert '== "oddsreaper_storm"' in c and '"vmatch": vmatch' in c
print("test_storm_pin: ALL PASS")
