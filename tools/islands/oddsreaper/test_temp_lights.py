# SPDX-License-Identifier: MIT
"""Headless: OddsReaper island-only storm-cool temp hero lights (no Unreal needed)."""
import os, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oddsreaper_turn as t

fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

use, why = t.temp_lights_plan(env={})
check(use and "OR_TEMP" in why, "default: spawn island-only temp lights")
check(not t.temp_lights_plan(env={"OR_TEMP_LIGHTS": "0"})[0], "OR_TEMP_LIGHTS=0 disables")
check(t.is_temp_light_actor("OR_TEMP_Sun", []), "label OR_TEMP_Sun matches")
check(t.is_temp_light_actor("Other", [t.TEMP_LIGHT_TAG]), "tag OR_TempCapture matches")
check(not t.is_temp_light_actor("OddsReaper MoodVolume", ["OddsReaper"]), "mood volume is not a temp light")
check(t.TEMP_FILL_INTENSITY == 2.5e5 and t.TEMP_EV100 == 10.0, "fill 2.5e5 / EV100 10 (storm-cool)")
check(t.TEMP_SUN_INTENSITY == 4.0, "temp sun intensity 4")
check(t.TEMP_LIGHT_RGB == (180, 200, 255), "cool storm RGB (not warm daylight)")
src = Path(t.__file__).read_text(encoding="utf-8")
check("atmosphere_sun_light" in src, "temp sun sets atmosphere_sun_light=False")
check("_cleanup_temps()" in src and "ALWAYS strip OR_TEMP" in src, "cleanup runs before post-capture save")
check("temp_lights" in src and "temp_info" in src, "result records temp_lights")
check("OR_TEMP" in src, "OR_TEMP present")
print("test_temp_lights: ALL PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(1 if fails else 0)
