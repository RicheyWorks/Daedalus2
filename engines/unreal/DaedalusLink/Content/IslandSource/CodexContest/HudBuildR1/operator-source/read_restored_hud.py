"""Final readback after normal restoration of the rejected HUD candidate."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).parent
sys.path.insert(0, str(TASK))
import activate_hud_native as a
import rollback_rejected_hud as r

OUT = a.BASE / 'codex-hud-restored-readback.json'
if OUT.exists():
    raise RuntimeError('retained restored-state readback exists')
journal = a.load(r.OUT)
assert journal['stage'] == 'normal_visible_restored_reopen_dispatched'
prepared, preflight, original, rows, packages = r.inputs()
r.preserve(prepared, preflight, rows, packages, restored=True)
pid = int(journal['restored_editor_pid'])
r.single_editor(pid)
command = "$p=Get-Process -Id " + str(pid) + ";ConvertTo-Json -InputObject @($p.Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-DaedalusLink.dll'} | Select-Object ModuleName,FileName,ModuleMemorySize) -Compress"
modules = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', command]))
assert len(modules) == 1 and Path(modules[0]['FileName']).resolve() == (a.LIVE / 'Binaries/Win64/UnrealEditor-DaedalusLink.dll').resolve()
assert a.fp(modules[0]['FileName']) == prepared['current_live_dll']
native, compare = a.native_snapshot()
assert compare(preflight['scene']['actors'], native['actors'])['equivalent']
desired = preflight['scene']['camera']
code = '''# Codex rejected HUD restoration camera pose only
import unreal
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if e.get_editor_world().get_path_name()!='/Game/Daedalus/DaedalusWorld.DaedalusWorld':raise RuntimeError('different world')
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE running')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('dirty work')
camera=CAMERA
p=camera['location'];r=camera['rotation']
e.set_level_viewport_camera_info(unreal.Vector(x=p['x'],y=p['y'],z=p['z']),unreal.Rotator(pitch=r['pitch'],yaw=r['yaw'],roll=r['roll']))
result={'runtime_camera_restored':True,'world_saved':False}
'''.replace('CAMERA', repr(desired), 1)
camera = a.wire.obj(a.wire.call(a.wire.UNREAL, 'execute_python', code=code, unattended=False,
    timeout=30, side='Unreal'), side='Unreal', what='restore recorded production camera after normal rollback reopen')
after, _ = a.native_snapshot()
comparison = compare(preflight['scene']['actors'], after['actors'])
assert comparison['equivalent']
a.same_camera(after, preflight['scene'])
for name in ('submit_arcade_source_key', 'submit_arcade_source_controller_button'):
    assert after['reflection']['methods'][name]['present']
pong = [row for row in after['arcade_actors'] if row['label'] == 'CodexAcceptance_Pong']
assert len(pong) == 1 and len(pong[0]['catalog']) == 12 and any(e['id'] == 'minesweeper' for e in pong[0]['catalog'])
r.preserve(prepared, preflight, rows, packages, restored=True)
saves = a.load(a.BASE / 'HudForegroundR1/journal.json')['save_backups']
for row in saves:
    path = Path(row['path'])
    assert path.exists() == row['exists']
    if row['exists']:
        assert a.fp(path) == row['original']
assert not Path('C:/Unreal/DaedalusRealm/Saved/DaedalusDesktopGames').exists()
record = {'schema': 'daedalus.codex-rejected-hud-restored-readback.v1',
    'utc': datetime.now(timezone.utc).isoformat(), 'stage': 'prior_working_binary_restored_loaded_and_preserved',
    'editor_pid': pid, 'os_loaded_modules': modules, 'loaded_backing_file': a.fp(modules[0]['FileName']),
    'native': after, 'actor_comparison': comparison, 'actor_records_unchanged': 101,
    'package_files_and_backups_unchanged': 120, 'canonical_source_files_restored': 140,
    'module_receipt': a.fp(a.MODULE), 'map': a.fp(a.MAP), 'camera': camera,
    'hero_realm_save_bytes_and_arcade_absence_restored': True,
    'rollback': {'path': str(r.OUT), **a.fp(r.OUT)}, 'world_saved': False, 'issues': [],
    'hud_candidate_accepted': False, 'hud_candidate_retained': str(a.SHADOW),
    'limits': 'HUD candidate compiled/loaded but failed targeted overlay lifecycle. Original HUD overlap remains unresolved on restored baseline; no new pass or physical controller acceptance claimed.'}
OUT.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({key: record[key] for key in ('stage', 'editor_pid', 'loaded_backing_file',
    'actor_records_unchanged', 'package_files_and_backups_unchanged', 'hud_candidate_accepted', 'issues')}, indent=2))
