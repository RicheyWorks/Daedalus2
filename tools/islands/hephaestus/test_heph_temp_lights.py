# SPDX-License-Identifier: MIT
"""Headless: Hephaestus island-only temp hero lights (no Unreal needed).

Stubs `unreal`, imports heph_island_ue, and checks temp_lights_plan / is_temp_light_actor:
default on, HEPH_TEMP_LIGHTS=0 disables, labels and tags match HEPH_TEMP_*, tuned fill/EV match
disk-saver's good v5 shot, and hero_capture source still destroys HEPH_TEMP before save.
Prints PASS/FAIL; exits 1 on failure.
"""
import sys, types
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

use, why = h.temp_lights_plan(env={})
check(use and "HEPH_TEMP" in why, "default: spawn island-only temp lights")
check(not h.temp_lights_plan(env={"HEPH_TEMP_LIGHTS": "0"})[0], "HEPH_TEMP_LIGHTS=0 disables")
check(h.is_temp_light_actor("HEPH_TEMP_Sun", []), "label HEPH_TEMP_Sun matches")
check(h.is_temp_light_actor("Other", [h.TEMP_LIGHT_TAG]), "tag HEPH_TempCapture matches")
check(not h.is_temp_light_actor("Hephaestus Forge Glow", ["Hephaestus"]), "forge glow is not a temp light")
check(h.TEMP_FILL_INTENSITY == 5.0e5 and h.TEMP_EV100 == 9.0, "fill 5e5 / EV100 9 match disk-saver v5")
check(h.TEMP_SUN_INTENSITY == 8.0, "temp sun intensity 8")
src = Path(h.__file__).read_text(encoding="utf-8")
check("atmosphere_sun_light" in src, "temp sun sets atmosphere_sun_light=False (no world sky drive)")
check("_cleanup_temps()" in src and "ALWAYS strip HEPH_TEMP" in src, "cleanup runs before post-capture save")
check("temp_lights" in src and "temp_info" in src, "hero_capture.json records temp_lights")
check('origin=unreal.Vector(ox, oy, oz)' in src, "run() passes island origin into hero_capture")
print("PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(1 if fails else 0)
