"""Targeted HUD foreground acceptance; SOURCE ONLY until the sole operator runs.

One unsaved blank map and cabinet. Each effect has an exclusive receipt before
dispatch; failed/uncertain actions are never replayed. check-restore is a new,
read-only observation after a slow original load, not another load_map call.
"""
import argparse
import ast
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import time
import urllib.request

TASK = Path(__file__).parent
ROOT = TASK / 'contest-island-production'
sys.path.insert(0, str(ROOT / 'tools/unreal'))
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'connectors/claude-asset-pipeline'))
from asset_pipeline import wire
from unreal_mcp.client import Mcp
from codex_static_intake_delivery import _scene_snapshot, _same_scene, fingerprint
from arcade_acceptance_steps import COMMON

BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
FOLDER = BASE / 'HudForegroundR1'
JOURNAL = FOLDER / 'journal.json'
MAP = Path('C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap')
SAVED = Path('C:/Unreal/DaedalusRealm/Saved')
ARCADE_DIR = SAVED / 'DaedalusDesktopGames'
APP = 'EditorToolset.EditorAppToolset'
SLATE = 'SlateInspectorToolset.SlateInspectorToolset'
MARKER = '# Codex HUD foreground targeted'
LABEL = 'CodexTransientHudForeground_Arcade'


def now(): return datetime.now(timezone.utc).isoformat()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def put(p, value, exclusive=False):
    with Path(p).open('x' if exclusive else 'w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2); f.write('\n')
def keep(d): put(JOURNAL, d)
def require(ok, message):
    if not ok: raise RuntimeError(message)
def lease():
    value = json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=10)).get('unreal', {})
    require(value.get('holder') == 'codex-play-guard' and value.get('at', 0) + value.get('ttl', 0) - time.time() > 120,
            'current sole-operator lease required')


def literal(filename, prefix):
    """Read a literal native string only; never execute an old host script."""
    tree = ast.parse((TASK / filename).read_text(encoding='utf-8'))
    return next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                and n.value.value.startswith(prefix))


def native(tail, pie=False, timeout=30):
    common = COMMON.replace('# Codex bounded arcade acceptance phase', MARKER) if pie else '''
import unreal,sys
b=sys.modules['claude_unreal_bridge']
other=[r.get('type') for g,r,box in b._running if r.get('type')!='execute_python' or not (r.get('params') or {}).get('code','').startswith('# Codex HUD foreground targeted')]
if other or b._jobs.qsize() or b._remote_lock.locked() or any(not box['done'].is_set() for box,stamp in b._job_boxes.values()):raise RuntimeError('conflicting native operation')
'''
    if pie:
        common += '''
h=unreal.GameplayStatics.get_player_character(w,0)
if not isinstance(h,unreal.DaedalusHero):raise RuntimeError('possessed Hero required')
pc=h.get_controller()
if not isinstance(pc,unreal.PlayerController) or unreal.GameplayStatics.get_player_controller(w,0)!=pc:raise RuntimeError('actual Hero/controller relation required')
if len(bridge._running)>1:raise RuntimeError('another generator is running')
'''
    code = MARKER + '\nCFG=' + repr({'phase': 'hud-foreground', 'actor_label': LABEL}) + '\n' + common + tail
    return wire.obj(wire.call(wire.UNREAL, 'execute_python', code=code, unattended=False,
                             timeout=timeout, side='Unreal'), side='Unreal', what='targeted HUD acceptance')


def phase(name, action):
    lease(); d = load(JOURNAL); path = FOLDER / (name + '.json')
    require(not path.exists(), 'retained phase exists; inspect instead of replay: ' + name)
    row = {'utc': now(), 'phase': name, 'stage': 'dispatch_pending', 'replay_permitted': False}
    put(path, row, True); d.update(stage=name + '_dispatch_pending', inflight=name); keep(d)
    try:
        row.update(result=action(d), stage='returned', returned_utc=now())
        put(path, row); d = load(JOURNAL)
        d.update(stage=name + '_returned', inflight=None); d['steps'].append({'phase': name, 'receipt': str(path)}); keep(d)
        if name.startswith('capture-'):
            print(json.dumps({'phase': name, 'stage': row['stage'], 'receipt': str(path),
                              'image': row['result']['image']}, indent=2))
        else:
            print(json.dumps(row, indent=2))
    except Exception as exc:
        row.update(stage='failed_or_uncertain_inspect_before_replay', error=str(exc)); put(path, row); raise


def window(m):
    rows = m.call(SLATE, 'Windows', action='list')
    rows = json.loads(rows) if isinstance(rows, str) else rows
    matching = [r for r in rows if r['title'] == 'DaedalusRealm - Unreal Editor']
    require(len(matching) == 1, 'exact one actual main Unreal window required')
    main = matching[0]; m.call(SLATE, 'Windows', action='select', index=main['index'])
    roots = m.call(SLATE, 'Snapshot', ref='', maxDepth=1)
    pattern = r'^window "' + re.escape(main['title']) + r'"[^\n]*\[ref=(w\d+)\]'
    refs = re.findall(pattern, roots, re.MULTILINE)
    require(len(refs) == 1, 'fresh main-window root ref unavailable; never assume w1')
    observer = FOLDER / 'slate-observer.json'
    if not observer.exists():
        identifier = m.call(SLATE, 'Observe', ref=refs[0], maxDepth=40)
        put(observer, {'identifier': identifier, 'root_ref': refs[0], 'selected_title': main['title']}, True)
    return {'windows': rows, 'selected': main, 'ref': refs[0], 'root_snapshot': roots}


def press(m, key, row):
    row.append({'key': key, 'stage': 'dispatch_pending'}); put(FOLDER / 'current-key-dispatch.json', row)
    result = m.call(SLATE, 'PressKey', key=key)
    row[-1].update(stage='returned', return_value=result); put(FOLDER / 'current-key-dispatch.json', row)
    require(result is True, 'Slate key dispatch returned false: ' + key)


def prepare():
    lease(); require(not FOLDER.exists(), 'retained HudForegroundR1 exists; never overwrite')
    before = _scene_snapshot(); require(before['world'] == '/Game/Daedalus/DaedalusWorld.DaedalusWorld', 'saved production world required')
    require(len(before['actors']) == 101, 'exact101 production actor snapshots required')
    require(not ARCADE_DIR.exists(), 'arcade directory already exists; preserve and inspect')
    FOLDER.mkdir(); (FOLDER / 'backups').mkdir(); (FOLDER / 'QA').mkdir()
    backups = []
    for name in ('DaedalusHero.json', 'DaedalusRealm.sav'):
        p = SAVED / 'Config' / name; row = {'path': str(p), 'exists': p.exists()}
        if p.exists():
            require(p.is_file(), 'original save is not a regular file')
            stat = p.stat(); b = FOLDER / 'backups' / name; shutil.copy2(p, b)
            row.update(original=fingerprint(p), backup=str(b), mtime_ns=stat.st_mtime_ns, atime_ns=stat.st_atime_ns)
            require(fingerprint(b) == row['original'], 'backup differs')
        backups.append(row)
    d = {'schema': 'daedalus.codex-targeted-hud-foreground.v1', 'utc': now(), 'stage': 'backups_retained',
         'production_before': before, 'production_map_before': fingerprint(MAP), 'save_backups': backups,
         'arcade_directory_existed': False, 'steps': [], 'inflight': None,
         'production_world_saved': False, 'temporary_world_saved': False,
         'limits': 'Targeted synthetic Slate/native checks, not full suite/physical hardware/visual acceptance.'}
    put(JOURNAL, d, True)
    def build(record):
        code = literal('prepare_bounded_arcade_level.py', '# Codex prepare minimal unsaved arcade acceptance world')
        code = code.replace('CodexTransientAcceptance_', 'CodexTransientHudForeground_')
        out = native(code, timeout=60); record['temporary_world'] = out; keep(record)
        require(fingerprint(MAP) == record['production_map_before'], 'production map changed')
        return out
    phase('prepare', build)


def start_pie(d):
    m = Mcp(timeout=40); require(m.call(APP, 'IsPIERunning') is False, 'PIE already active; do not replay')
    gate = native("result={'world':unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()}\n")
    require(gate['world'] == d['temporary_world']['world'], 'owned temporary map required')
    result = m.call(APP, 'StartPIE', options={'bSimulate': False, 'playMode': 'PlayMode_InViewPort', 'warmupSeconds': 1.0})
    return {'start_return': result, 'pie_running': m.call(APP, 'IsPIERunning')}


def open_pong(d):
    out = native("""
if state()['open'] or state()['save_pending']:raise RuntimeError('existing overlay/pending save; inspect')
baseline={'cursor':pc.get_editor_property('show_mouse_cursor'),'paused':unreal.GameplayStatics.is_game_paused(w)}
if not a.start_game('pong',730):raise RuntimeError('Pong selection failed')
h.set_actor_location(a.get_actor_location()+unreal.Vector(x=150,y=0,z=100),False,False)
h.aim_at(a.get_actor_location())
interaction=h.interact()
result={'baseline':baseline,'interaction':interaction,'state':state(),'hero':h.get_path_name(),'controller':pc.get_path_name(),'world_paused':unreal.GameplayStatics.is_game_paused(w)}
""", True)
    require(out['state']['open'] and out['state']['id'] == 'pong' and out['world_paused'], 'actual Hero Interact did not open paused Pong overlay')
    return out


def keys(d):
    m = Mcp(timeout=30); focus = window(m); actions = []; checks = []
    require(native("result={'state':state()}\n", True)['state']['open'], 'open overlay required')
    for expected in (True, False):
        press(m, 'P', actions); out = native("result={'state':state()}\n", True)
        checks.append({'key': 'P', 'expected_paused': expected, 'observed': out})
        require(out['state']['paused'] is expected, 'focused Slate P pause/resume differs')
    progressed = native("step(up=True)\nresult={'state':state()}\n", True)
    require(progressed['state']['steps'] > 0, 'manual single clock did not advance Pong')
    press(m, 'R', actions); restarted = native("result={'state':state()}\n", True)
    require(restarted['state']['steps'] == 0, 'focused Slate R did not restart')
    return {'focus': focus, 'actions': actions, 'checks': checks, 'progressed': progressed, 'restarted': restarted}


def contra(d):
    m = Mcp(timeout=30); focus = window(m); actions = []
    title = native("a.start_game('contra',730)\nresult={'state':state()}\n", True)
    require(title['state']['open'] and 'TITLE' in title['state']['note'], 'Contra title required')
    press(m, 'Enter', actions); active = native("result={'state':state()}\n", True)
    require(active['state']['id'] == 'contra' and 'TITLE' not in active['state']['note'], 'focused Slate Enter did not start Contra')
    return {'focus': focus, 'actions': actions, 'title': title, 'active': active}


def capture(d, name):
    m = Mcp(timeout=40); selected = window(m)
    snapshot = m.call(SLATE, 'Snapshot', ref=selected['ref'], maxDepth=40)
    result = m.call(SLATE, 'Screenshot', ref=selected['ref'])
    raw = base64.b64decode(result['data'], validate=True)
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'actual Slate image is not complete PNG data')
    image = FOLDER / 'QA' / (name + '.png')
    with image.open('xb') as f: f.write(raw)
    return {'selected': selected, 'snapshot': snapshot, 'image': {'path': str(image), **fingerprint(image),
            'pixels': list(struct.unpack('>II', raw[16:24]))}, 'personally_inspected': False,
            'inspection_required': 'Main operator must inspect actual pixels for Hero HUD/prompt/logbook overlap, text fit and canvas readability.'}


def close(d):
    m = Mcp(timeout=25); focus = window(m); actions = []
    require(native("result={'state':state()}\n", True)['state']['open'], 'owned overlay is not open')
    press(m, 'Escape', actions)
    return {'focus': focus, 'actions': actions, 'deferred_close': 'check-close in a later command; never block the editor ticker'}


def check_close(d):
    out = native("result={'state':state(),'paused':unreal.GameplayStatics.is_game_paused(w),'cursor':pc.get_editor_property('show_mouse_cursor'),'pie':unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(),'hero':h.get_path_name(),'controller':pc.get_path_name(),'controller_has_hero':h.get_controller()==pc}\n", True)
    opened = load(FOLDER / 'open-pong.json')['result']
    require(not out['state']['open'] and out['pie'] and out['controller_has_hero'], 'Escape close/PIE/Hero relation differs')
    require(out['paused'] == opened['baseline']['paused'] and out['cursor'] == opened['baseline']['cursor'], 'pause/cursor not restored')
    require(out['hero'] == opened['hero'] and out['controller'] == opened['controller'], 'possessed Hero/controller changed')
    return out


def stop(d):
    require(load(FOLDER / 'check-close.json')['stage'] == 'returned', 'close/readback first')
    m = Mcp(timeout=40); require(m.call(APP, 'IsPIERunning') is True, 'PIE already stopped; inspect, do not replay')
    result = {'stop_return': m.call(APP, 'StopPIE'), 'pie_running_after_return': m.call(APP, 'IsPIERunning'), 'next': 'restore performs a separate EndPlay/queue gate'}
    observer = FOLDER / 'slate-observer.json'
    if observer.exists():
        result['owned_observer_removed'] = m.call(SLATE, 'Unobserve', identifier=load(observer)['identifier'])
    return result


def restore(d):
    gate = native("""
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
result={'pie':unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(),'game_world_present':e.get_game_world() is not None,'world':e.get_editor_world().get_path_name(),'dirty_maps':[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'dirty_content':[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
""")
    temp = d['temporary_world']['world']
    require(not gate['pie'] and not gate['game_world_present'] and not gate['dirty_content'] and gate['world'] == temp, 'EndPlay not complete or other dirty work; preserve saves')
    require(all(p == temp.split('.')[0] for p in gate['dirty_maps']), 'unexpected dirty map; preserve')
    restored = []
    for row in d['save_backups']:
        p = Path(row['path']); require(p.resolve() in {(SAVED / 'Config' / n).resolve() for n in ('DaedalusHero.json', 'DaedalusRealm.sav')}, 'save target escaped exact scope')
        if row['exists']:
            require(fingerprint(row['backup']) == row['original'], 'original backup changed')
            shutil.copyfile(row['backup'], p); os.utime(p, ns=(row['atime_ns'], row['mtime_ns']))
            require(fingerprint(p) == row['original'], 'restored save differs')
        elif p.exists():
            require(p.is_file(), 'unexpected save target type'); shutil.copy2(p, FOLDER / 'backups' / ('generated-' + p.name)); p.unlink()
        restored.append({'path': str(p), 'exists': p.exists(), 'fingerprint': fingerprint(p) if p.exists() else None})
    if ARCADE_DIR.exists():
        require(ARCADE_DIR.resolve() == Path('C:/Unreal/DaedalusRealm/Saved/DaedalusDesktopGames').resolve() and ARCADE_DIR.is_dir() and not any(ARCADE_DIR.iterdir()), 'unexpected arcade output: preserve, do not remove')
        ARCADE_DIR.rmdir()
    require(fingerprint(MAP) == d['production_map_before'], 'production map bytes changed')
    d.update(stage='saves_restored_load_dispatch_pending', save_restoration=restored, endplay_gate=gate); keep(d)
    camera = d['production_before']['camera']
    out = native("if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE restarted')\ne=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)\nif e.get_editor_world().get_path_name()!=" + repr(temp) + ":raise RuntimeError('unexpected world before original load')\nw=unreal.EditorLoadingAndSavingUtils.load_map(" + repr(str(MAP)) + ")\nif not w:raise RuntimeError('original map load failed')\ncamera=" + repr(camera) + "\np=camera['location'];r=camera['rotation']\ne.set_level_viewport_camera_info(unreal.Vector(x=p['x'],y=p['y'],z=p['z']),unreal.Rotator(pitch=r['pitch'],yaw=r['yaw'],roll=r['roll']))\nresult={'world':w.get_path_name(),'loaded_once':True,'camera_restoration_dispatched':True}\n", timeout=90)
    return {'saves': restored, 'map_load': out, 'next': 'check-restore; if timeout, no replay—only that read-only companion'}


def check_restore(d):
    scene = _scene_snapshot(); _same_scene(scene, d['production_before'])
    require(fingerprint(MAP) == d['production_map_before'] and not ARCADE_DIR.exists(), 'map/arcade absence changed')
    for row in d['save_backups']:
        p = Path(row['path']); require(p.exists() == row['exists'], 'original save presence differs')
        if row['exists']: require(fingerprint(p) == row['original'], 'original save bytes differ')
    return {'all101_actor_records_unchanged': True, 'camera_unchanged_tolerance': 1e-5, 'map': fingerprint(MAP), 'saves_and_arcade_absence_restored': True, 'scene': scene, 'world_saved': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'start-pie', 'open-pong', 'keys', 'contra', 'mines', 'capture', 'close', 'check-close', 'stop', 'restore', 'check-restore'))
    parser.add_argument('--name', default='foreground')
    args = parser.parse_args(); require(re.fullmatch(r'[A-Za-z0-9-]+', args.name) is not None, 'simple owned label required')
    if args.stage == 'prepare': prepare()
    elif args.stage == 'capture': phase('capture-' + args.name, lambda d: capture(d, args.name))
    elif args.stage == 'mines': phase('mines', lambda d: native("a.start_game('minesweeper',730)\nresult={'state':state()}\n", True))
    elif args.stage == 'check-restore': phase('check-restore-' + args.name, check_restore)
    else: phase(args.stage, globals()[args.stage.replace('-', '_')])
