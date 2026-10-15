"""Fresh read only after the first candidate HUD closed; do not replay input."""
import json
from pathlib import Path
import sys

TASK = Path(__file__).parent
sys.path.insert(0, str(TASK))
import hud_targeted_acceptance as h

out = h.FOLDER / 'closed-overlay-readback.json'
if out.exists():
    raise RuntimeError('retained readback exists')
record = h.native("""
result={'state':state(),'world_paused':unreal.GameplayStatics.is_game_paused(w),
 'hero':h.get_path_name(),'controller':pc.get_path_name(),'cursor':pc.get_editor_property('show_mouse_cursor'),
 'hero_location':str(h.get_actor_location()),'cabinet_location':str(a.get_actor_location()),
 'hero_settings':h.is_settings_open(),'hero_field':h.is_field_open(),'hero_realm':h.is_realm_open()}
""", True)
h.put(out, record, True)
print(json.dumps(record, indent=2))
