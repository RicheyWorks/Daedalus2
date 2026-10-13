# SPDX-License-Identifier: MIT
"""Headless: Hephaestus sky gate before the hero capture (no Unreal needed).

Stubs `unreal`, imports heph_island_ue, and checks sky_restore_plan: runs oddsreaper's restore_world_sky only when the
world probe reads dark (the 23:44 storm save: sun 0 lux, skylight 0.017), never when lit, never twice in a turn, never
when HEPH_RESTORE_SKY=0 or the shared script is missing; and that RESTORE_SKY_SCRIPT points at the real oddsreaper file.
Prints PASS/FAIL; exits 1 on failure.
"""
import os, sys, types
from pathlib import Path

_ue = types.ModuleType("unreal")
_ue.__getattr__ = lambda name: type(name, (), {})
sys.modules.setdefault("unreal", _ue)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import heph_island_ue as h  # noqa: E402

fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

dark = h.world_light_verdict([0.0], [0.017])
lit = h.world_light_verdict([10.0], [1.1])
check(h.sky_restore_plan(dark, env={})[0], "storm-dark world (sun 0 lux, sky 0.017) -> run restore")
check(not h.sky_restore_plan(lit, env={})[0], "Clear world (sun 10 lux, sky 1.1) -> no restore")
check(not h.sky_restore_plan(dark, env={"HEPH_RESTORE_SKY": "0"})[0], "HEPH_RESTORE_SKY=0 disables restore")
check(not h.sky_restore_plan(dark, env={}, attempted=True)[0], "at most one restore attempt per turn")
check(not h.sky_restore_plan(dark, env={}, script_exists=False)[0], "missing restore script -> skip, no crash")
check(not h.sky_restore_plan(None, env={})[0], "no probe result -> no restore")
check(os.path.isfile(h.RESTORE_SKY_SCRIPT), "RESTORE_SKY_SCRIPT resolves to tools/islands/oddsreaper/restore_world_sky.py")
src = Path(h.RESTORE_SKY_SCRIPT).read_text(encoding="utf-8")
# it may count DirectionalLights (_count_suns verifies no second sun); it must never spawn one
check("spawn_actor" not in src and "spawn_actor_from_class" not in src, "shared restore adds no new sun (referee rule)")
check("save_map" in src and "umap_written" in src, "shared restore saves the persistent map and checks the umap")
print("PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(1 if fails else 0)
