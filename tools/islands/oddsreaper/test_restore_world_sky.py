# SPDX-License-Identifier: MIT
"""Headless (no Unreal): restore_world_sky.py must persist Clear sky with an explicit verified save_map,
post-save director re-read, no second sun, and a result JSON for other bots.
Run: python test_restore_world_sky.py"""
import ast
import os

H = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(H, "restore_world_sky.py"), encoding="utf-8").read()
ast.parse(src)

assert "save_map(world, MAP)" in src, "must save persistent DaedalusWorld via save_map"
assert "umap_written" in src and "umap_mtime_before" in src and "umap_mtime_after" in src
assert "_save_verified" in src, "post-save disk check helper required"
assert "after_save" in src, "must re-read director after save"
assert "new_sun" in src and "DirectionalLight" in src, "must count suns and refuse a second sun"
assert "MIN_SUN" in src and "MIN_SKY" in src
assert "young_meadow" in src and "9.4" in src
assert "DaedalusWeather.CLEAR" in src
assert "LevelStreamingAlwaysLoaded" in src
assert "restore_world_sky.json" in src, "write result JSON for other bots"
assert "spawn_actor" not in src.lower(), "must not spawn actors (no second sun)"

r4 = open(os.path.join(H, "r4_pie.py"), encoding="utf-8").read()
assert "restore_world_sky.py" in r4

# hero framing contract still points at verified save + no new sun
hf = open(os.path.join(H, "test_hero_framing.py"), encoding="utf-8").read()
assert "umap_written" in hf

print("test_restore_world_sky: ALL PASS")
