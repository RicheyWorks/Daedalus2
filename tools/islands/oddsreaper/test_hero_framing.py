# SPDX-License-Identifier: MIT
"""Headless: Play hero shot frames OddsReaper Island and the sublevel streams in Play. python test_hero_framing.py"""
import json, math, os, re
H = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(H, "..", "..", ".."))
lay = json.load(open(os.path.join(REPO, "data", "islands", "oddsreaper", "layout.json"), encoding="utf-8"))
ox, oy, oz = lay["origin_cm"]
assert (ox, oy) == (400000, -400000), "island origin must be ~(4000 m, -4000 m)"
c, t = lay["hero_cam_m"], lay["hero_target_m"]
cam = (ox + c[0] * 100, oy + c[1] * 100); tgt = (ox + t[0] * 100, oy + t[1] * 100)
assert math.hypot(tgt[0] - ox, tgt[1] - oy) < 13000, "target inside the 130 m island"
v = (tgt[0] - cam[0], tgt[1] - cam[1]); w = (ox - cam[0], oy - cam[1])
cos = (v[0] * w[0] + v[1] * w[1]) / (math.hypot(*v) * math.hypot(*w))
assert cos > 0.95, f"camera must look toward the island centre (cos={cos:.3f})"
turn = open(os.path.join(H, "oddsreaper_turn.py"), encoding="utf-8").read()
assert "get_game_world()\nworld = gw or" in turn and "begin_deferred_actor_spawn_from_class(gw" in turn, "capture must render the PIE world"
assert 'get_streaming_level(w, "OddsReaperIsland")' in turn, "PIE must stream OddsReaperIsland"
assert "LevelStreamingAlwaysLoaded" in open(os.path.join(H, "place_oddsreaper_island.py"), encoding="utf-8").read()
r4 = open(os.path.join(H, "r4_pie.py"), encoding="utf-8").read()
assert "take_hero_shot(CAM, TGT" in r4 and "restore_world_sky.py" in r4, "r4 must aim at the island and restore world sky first"
rw = open(os.path.join(H, "restore_world_sky.py"), encoding="utf-8").read()
assert "save_map(world, MAP)" in rw and "umap_written" in rw and "spawn_actor" not in rw.lower() and "new_sun" in rw, "explicit verified save, no second sun"
print("hero framing + streaming + world sky: PASS")
