"""Read the newly activated HUD binary and restore only the saved camera pose."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

TASK = Path(__file__).parent
ROOT = TASK / 'contest-island-production'
BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
OUT = BASE / 'codex-hud-loaded-readback.json'
sys.path.insert(0, str(TASK))
import activate_hud_native as a

if OUT.exists():
    raise RuntimeError('retained HUD load readback exists; inspect it')
record = a.load(a.OUT)
assert record['stage'] == 'normal_visible_reopen_dispatched'
preflight = a.load(a.PREFLIGHT)
prepared = a.load(a.SHADOW / 'prepared.json')
assert len(record['installations']) == 5
for row in record['installations']:
    assert row['state'] == 'installed_and_verified' and a.fp(row['target']) == row['expected']
expected_source = dict(preflight['live_source_baseline'])
for row in record['payloads']:
    relative = str(Path(row['target']).relative_to(a.LIVE)).replace('\\', '/')
    if relative.startswith('Source/'):
        expected_source[relative] = row['expected']
assert a.source_snapshot() == expected_source
assert a.fp(a.MODULE) == a.fingerprint(record['unchanged_module_receipt'])
a.check_packages(a.package_rows(preflight))
a.check_map_backup(preflight)
native, compare = a.native_snapshot()
comparison = compare(preflight['scene']['actors'], native['actors'])
assert comparison['equivalent'], comparison['issues']
for key in ('submit_arcade_source_key', 'submit_arcade_source_controller_button'):
    assert native['reflection']['methods'][key]['present']
pong = [row for row in native['arcade_actors'] if row['label'] == 'CodexAcceptance_Pong']
assert len(pong) == 1
registry = a.LIVE / 'Source/DaedalusLink/Public/DesktopGames/DaedalusDesktopGameRegistry.h'
catalog = [dict(zip(('id', 'title', 'controls'), values)) for values in
           re.findall(r'\{"([^"\n]+)","([^"\n]+)","([^"\n]+)"\}', registry.read_text())]
assert len(catalog) == 12 and pong[0]['catalog'] == catalog
desired = preflight['scene']['camera']
code = '''# Codex HUD activation restore recorded viewport camera only
import unreal
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if e.get_editor_world().get_path_name()!='/Game/Daedalus/DaedalusWorld.DaedalusWorld':raise RuntimeError('different world')
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE running')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('dirty packages')
camera=CAMERA
p=camera['location'];r=camera['rotation']
e.set_level_viewport_camera_info(unreal.Vector(x=p['x'],y=p['y'],z=p['z']),unreal.Rotator(pitch=r['pitch'],yaw=r['yaw'],roll=r['roll']))
p,r=e.get_level_viewport_camera_info()
result={'location':{'x':p.x,'y':p.y,'z':p.z},'rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll}}
'''.replace('CAMERA', repr(desired), 1)
camera = a.wire.obj(a.wire.call(a.wire.UNREAL, 'execute_python', code=code, unattended=False,
                                timeout=30, side='Unreal'), side='Unreal', what='restore HUD activation camera')
for group in ('location', 'rotation'):
    assert all(abs(camera[group][key] - value) < 1e-5 for key, value in desired[group].items())
after, _ = a.native_snapshot()
assert compare(preflight['scene']['actors'], after['actors'])['equivalent']
a.same_camera(after, preflight['scene'])
a.check_packages(a.package_rows(preflight))
a.check_map_backup(preflight)
result = {'schema': 'daedalus.codex-hud-loaded-readback.v1',
    'utc': datetime.now(timezone.utc).isoformat(), 'stage': 'hud_loaded_reflection_and_preservation_complete',
    'native': after, 'actor_comparison': comparison, 'preserved_actor_records': 101,
    'preserved_package_files': 120, 'installed_source_files': 140,
    'changed_source_files': 3, 'unchanged_module_receipt': a.fp(a.MODULE),
    'installed_dll': a.fp(a.LIVE / 'Binaries/Win64/UnrealEditor-DaedalusLink.dll'),
    'installed_pdb': a.fp(a.LIVE / 'Binaries/Win64/UnrealEditor-DaedalusLink.pdb'),
    'source_catalog_matches_all12': True, 'map': a.fp(a.MAP),
    'camera_runtime_restore_only': camera, 'world_saved': False, 'issues': [],
    'limits': 'Loaded reflection/preservation only; targeted HUD/input pixels and lifecycle still pending.'}
OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({key: result[key] for key in ('stage', 'preserved_actor_records', 'preserved_package_files',
    'installed_dll', 'source_catalog_matches_all12', 'issues')}, indent=2))
