"""Five-leaf HUD activation after a successful isolated build.

The sole operator runs prepare, request-close, then install. Normal visible
reopen is a separate main-operator PowerShell action; this file never launches
or kills an editor. Rollback is explicit and requires zero editor processes.
All historical arcade journals remain untouched.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

TASK = Path(__file__).resolve().parent
ROOT = TASK / 'contest-island-production'
BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
LIVE = Path('C:/Unreal/DaedalusRealm/Plugins/DaedalusLink')
SHADOW = TASK / 'native-hud157'
PLUGIN = SHADOW / 'Plugins/DaedalusLink'
SAVED = SHADOW / 'Saved'
PREFLIGHT = SAVED / 'hud-build-preflight.json'
TERMINAL = SAVED / 'hud-build-terminal.json'
OUT = BASE / 'codex-hud-normal-activation.json'
MAP = Path('C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap')
WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
MODULE = LIVE / 'Binaries/Win64/UnrealEditor.modules'
METADATA = SHADOW / 'Intermediate/Build/Win64/x64/UnrealEditor/Development/TargetMetadata.json'
EXPECTED_MAP = {'bytes': 209329457, 'sha256': '5690b48f9cdc9f50251c08127b161ab4f3afae49754b75316d561da2a3a80933'}
HUD_FILES = {'Source/DaedalusLink/Private/' + name for name in (
    'DaedalusDesktopArcade.cpp', 'SDaedalusDesktopArcade.cpp', 'SDaedalusDesktopArcade.h')}
sys.path.insert(0, str(ROOT / 'connectors/claude-asset-pipeline'))
sys.path.insert(0, str(ROOT / 'tools/unreal'))
from asset_pipeline import wire
from codex_editor_handoff import _asset_file


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def fp(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            size += len(chunk)
            digest.update(chunk)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def fingerprint(value):
    if isinstance(value, dict) and 'fingerprint' in value:
        value = value['fingerprint']
    return {'bytes': int(value['bytes']), 'sha256': str(value['sha256']).lower()}


def retain(record):
    OUT.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def source_snapshot():
    return {str(p.relative_to(LIVE)).replace('\\', '/'): fp(p)
            for p in sorted((LIVE / 'Source').rglob('*')) if p.is_file()}


def processes():
    command = ("$p=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe'}); "
               "ConvertTo-Json -InputObject @($p | Select-Object ProcessId,CommandLine) -Compress")
    completed = subprocess.run(['powershell', '-NoProfile', '-Command', command],
                               capture_output=True, text=True, check=True)
    result = json.loads(completed.stdout)
    if not isinstance(result, list):
        raise RuntimeError('unsupported editor process inventory; preserve')
    return result


def require_zero_editors():
    observed = processes()
    if observed:
        raise RuntimeError('editor remains active; no install/rollback: ' + repr(observed))
    return {'utc': now(), 'unreal_editor_processes': observed}


def package_rows(preflight):
    """Accept an explicit path->fingerprint map or explicit path-bearing rows."""
    keys = [key for key in ('packages', 'package_files', 'tracked_packages') if key in preflight]
    if len(keys) != 1:
        raise RuntimeError('preflight needs exactly one packages/package_files/tracked_packages collection')
    value = preflight[keys[0]]
    if isinstance(value, dict):
        rows = [{'asset_path': path, 'path': str(_asset_file(path)),
                 'backup': preflight['package_backups'][path], **fingerprint(expected)}
                for path, expected in value.items()]
    elif isinstance(value, list):
        rows = [{'path': row['path'], **fingerprint(row)} for row in value]
    else:
        raise RuntimeError('unsupported explicit package collection')
    if len(rows) != 120 or len({str(Path(row['path']).resolve()).lower() for row in rows}) != 120:
        raise RuntimeError('require exactly 120 distinct tracked package files')
    return rows


def check_packages(rows):
    drift = [row['path'] for row in rows if fp(row['path']) != fingerprint(row)
             or fp(row['backup']) != fingerprint(row)]
    if drift:
        raise RuntimeError('tracked package changed; preserve: ' + repr(drift))


def check_map_backup(preflight):
    if fp(MAP) != EXPECTED_MAP:
        raise RuntimeError('current saved map differs from map5690; preserve')
    value = preflight['map_backup']
    path = Path(value['path'] if isinstance(value, dict) else value)
    if fp(path) != EXPECTED_MAP:
        raise RuntimeError('main operator current map backup missing or changed')
    if isinstance(value, dict) and fp(path) != fingerprint(value):
        raise RuntimeError('map backup differs from preflight fingerprint')
    return {'path': str(path), **fp(path)}


def native_snapshot():
    # Import only guarded, read-only generator/comparison functions. No main().
    spec = importlib.util.spec_from_file_location('hud_activation_read_helpers', TASK / 'read_activated_arcade_native.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    code = helper.native_code() + '''
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
p,r=e.get_level_viewport_camera_info()
result['camera']={'location':{'x':p.x,'y':p.y,'z':p.z},'rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll}}
'''
    native = wire.obj(wire.call(wire.UNREAL, 'execute_python', code=code, unattended=False,
                                timeout=60, side='Unreal'), side='Unreal', what='HUD activation clean preservation gate')
    if native.get('hold_reason'):
        raise RuntimeError(native['hold_reason'])
    own_hash = hashlib.sha256(code.encode()).hexdigest()
    for name in ('gate_before', 'gate_after'):
        gate = native[name]
        if gate['world'] != WORLD or gate['pie'] or gate['dirty_maps'] or gate['dirty_content']:
            raise RuntimeError('native clean saved-world boundary changed')
    for name in ('queue_before', 'queue_after'):
        queue = native[name]
        own = [r for r in queue.get('running_generators', []) if r.get('code_sha256') == own_hash]
        if (not queue.get('supported') or len(own) != 1 or len(queue['running_generators']) != 1
                or queue['queued_jobs'] or queue['unfinished_async_job_boxes'] != 0
                or queue['remote_execution_lock_locked']):
            raise RuntimeError('queue verification unsupported or conflicting current work')
    if len(native['actors']) != 101:
        raise RuntimeError('require 101 preserved Codex actors')
    return native, helper.compare_actors


def candidate_metadata(prepared):
    metadata = load(METADATA)
    receipt = metadata['Receipt']
    version = receipt['Version']
    if (receipt['TargetName'] != 'UnrealEditor' or receipt['Platform'] != 'Win64'
            or receipt['Configuration'] != 'Development' or receipt['TargetType'] != 1
            or receipt['Architectures']['Architectures'] != ['x64']
            or (version['MajorVersion'], version['MinorVersion'], version['PatchVersion']) != (5, 8, 3)
            or str(version['BuildId']) != '55116800'):
        raise RuntimeError('candidate target/version/build-id incompatible')
    expected_manifest = str((PLUGIN / 'Binaries/Win64/UnrealEditor.modules').resolve()).lower()
    matches = [v for path, v in metadata['FileToManifest'].items()
               if str(Path(path).resolve()).lower() == expected_manifest]
    if len(matches) != 1 or matches[0]['ModuleNameToFileName'] != {'DaedalusLink': 'UnrealEditor-DaedalusLink.dll'}:
        raise RuntimeError('candidate target metadata module filename mapping differs')
    installed = load(MODULE)
    if installed != {'BuildId': '55116800', 'Modules': {'DaedalusLink': 'UnrealEditor-DaedalusLink.dll'}}:
        raise RuntimeError('existing canonical module receipt incompatible; never rewrite')
    if fp(MODULE) != fingerprint(prepared['current_module_receipt']):
        raise RuntimeError('canonical module receipt changed')
    return {'target_metadata': {'path': str(METADATA), **fp(METADATA)},
            'target': receipt['TargetName'], 'platform': receipt['Platform'],
            'configuration': receipt['Configuration'], 'version': version,
            'prepared_module_mapping': matches[0], 'retained_installed_modules': {'path': str(MODULE), **fp(MODULE)}}


def payloads(prepared):
    rows = prepared['source_items']
    if len(rows) != 3 or {r['plugin_relative_path'] for r in rows} != HUD_FILES:
        raise RuntimeError('only exact three HUD source leaves allowed')
    result = []
    for row in rows:
        relative = row['plugin_relative_path']
        before = fingerprint(prepared['live_source_baseline'][relative])
        after = fp(PLUGIN / relative)
        if before['sha256'] != row['expected_before_sha256'].lower() or after['sha256'] != row['after_sha256'].lower():
            raise RuntimeError('HUD source before/after packet differs')
        result.append({'target': str(LIVE / relative), 'source': str(PLUGIN / relative),
                       'backup': str(SHADOW / 'original-installed' / relative), 'before': before, 'expected': after})
    for suffix in ('dll', 'pdb'):
        name = 'UnrealEditor-DaedalusLink.' + suffix
        source = PLUGIN / 'Binaries/Win64' / name
        expected = fp(source)
        if not expected['bytes']:
            raise RuntimeError('empty candidate binary')
        result.append({'target': str(LIVE / 'Binaries/Win64' / name), 'source': str(source),
                       'backup': str(SHADOW / 'original-installed/Binaries/Win64' / name),
                       'before': fingerprint(prepared['current_live_' + suffix]), 'expected': expected})
    if len(result) != 5:
        raise RuntimeError('require five payload leaves')
    for row in result:
        if not Path(row['target']).resolve().is_relative_to(LIVE.resolve()) or fp(row['backup']) != row['before']:
            raise RuntimeError('install scope or original backup differs')
    module_backup = SHADOW / 'original-installed/Binaries/Win64/UnrealEditor.modules'
    if fp(module_backup) != fingerprint(prepared['current_module_receipt']):
        raise RuntimeError('original module receipt backup changed')
    return result


def unchanged(prepared, rows, packages):
    if source_snapshot() != prepared['live_source_baseline']:
        raise RuntimeError('canonical source baseline changed; preserve')
    for row in rows:
        if fp(row['target']) != row['before'] or fp(row['backup']) != row['before'] or fp(row['source']) != row['expected']:
            raise RuntimeError('source/candidate/backup leaf changed: ' + row['target'])
    for relative, expected in prepared['runtime_catalogs'].items():
        if fp(LIVE / relative) != fingerprint(expected):
            raise RuntimeError('runtime catalog changed: ' + relative)
    if fp(MODULE) != fingerprint(prepared['current_module_receipt']):
        raise RuntimeError('canonical .modules receipt changed')
    check_packages(packages)


def check_preflight(prepared, preflight):
    if preflight.get('issues') != [] or preflight.get('canonical_mutated') is not False:
        raise RuntimeError('build preflight reports issues or canonical mutation')
    for key in ('live_source_baseline', 'source_items', 'runtime_catalogs'):
        if preflight[key] != prepared[key]:
            raise RuntimeError('fresh build preflight differs from prepared source: ' + key)
    for current, old in (('live_dll', 'current_live_dll'), ('live_pdb', 'current_live_pdb'),
                         ('module_receipt', 'current_module_receipt')):
        if fingerprint(preflight[current]) != fingerprint(prepared[old]):
            raise RuntimeError('fresh preflight binary baseline differs')
    if fingerprint(preflight['map']) != EXPECTED_MAP or fp(LIVE / 'DaedalusLink.uplugin') != fingerprint(preflight['descriptor']):
        raise RuntimeError('fresh map/descriptor baseline differs')
    if len(preflight['live_source_baseline']) != 140 or len(preflight['scene']['actors']) != 101:
        raise RuntimeError('require current 140 source files and 101 actor records')


def same_camera(native, expected):
    if any(abs(native['camera'][group][key] - value) > 1e-5
           for group in ('location', 'rotation') for key, value in expected['camera'][group].items()):
        raise RuntimeError('saved construction camera changed; preserve current work')


def atomic_copy(source, target, expected, event, record, suffix):
    target, source = Path(target), Path(source)
    temp = target.with_name(target.name + suffix)
    if temp.exists():
        raise RuntimeError('existing staged leaf: inspect uncertain prior outcome: ' + str(temp))
    with source.open('rb') as src, temp.open('xb') as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    if fp(temp) != expected:
        raise RuntimeError('staged leaf hash mismatch; retain partial outcome')
    event['state'] = 'atomic_replace_pending'
    retain(record)
    os.replace(temp, target)
    event.update(state='installed_and_verified', actual=fp(target))
    retain(record)
    if event['actual'] != expected:
        raise RuntimeError('installed leaf hash mismatch; do not reopen')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'request-close', 'install', 'rollback'))
    parser.add_argument('--old-editor-pid', type=int, required=True)
    args = parser.parse_args()
    prepared, preflight = load(SHADOW / 'prepared.json'), load(PREFLIGHT)
    check_preflight(prepared, preflight)
    packages = package_rows(preflight)
    rows = payloads(prepared)
    if args.phase == 'prepare':
        if OUT.exists():
            raise RuntimeError('retained HUD activation journal exists; inspect, never replay')
        terminal = load(TERMINAL)
        exits = [terminal[key] for key in ('exit_code', 'returncode', 'return_code') if key in terminal]
        if len(exits) != 1 or exits[0] != 0:
            raise RuntimeError('require one actual successful build terminal exit code')
        metadata = candidate_metadata(prepared)
        unchanged(prepared, rows, packages)
        backup = check_map_backup(preflight)
        observed = processes()
        if len(observed) != 1 or observed[0]['ProcessId'] != args.old_editor_pid:
            raise RuntimeError('current single editor identity differs')
        native, compare = native_snapshot()
        before = preflight['scene']
        comparison = compare(before['actors'], native['actors'])
        if not comparison['equivalent']:
            raise RuntimeError('saved actor records drifted: ' + repr(comparison['issues']))
        same_camera(native, before)
        record = {'schema': 'daedalus.codex-controlled-hud-normal-activation.v1',
                  'stage': 'prepared_clean_boundary_normal_close_pending', 'utc': now(),
                  'old_editor_pid': args.old_editor_pid, 'native_before': native,
                  'preflight': {'path': str(PREFLIGHT), **fp(PREFLIGHT)},
                  'build_terminal': {'path': str(TERMINAL), **fp(TERMINAL), 'actual': terminal},
                  'prepared': {'path': str(SHADOW / 'prepared.json'), **fp(SHADOW / 'prepared.json')},
                  'candidate_metadata': metadata, 'payloads': rows, 'tracked_packages': packages,
                  'map_before': fp(MAP), 'map_backup': backup,
                  'unchanged_module_receipt': {'path': str(MODULE), **fp(MODULE)},
                  'normal_close_requested': False, 'forced_close': False, 'settings_changed': False,
                  'reopen_dispatched': False, 'installations': [], 'rollback': []}
        with OUT.open('x', encoding='utf-8') as handle:
            json.dump(record, handle, indent=2, allow_nan=False)
            handle.write('\n')
    else:
        record = load(OUT)
        if record['old_editor_pid'] != args.old_editor_pid or fp(PREFLIGHT) != fingerprint(record['preflight']):
            raise RuntimeError('editor/preflight identity changed')
        if record['payloads'] != rows or record['tracked_packages'] != packages:
            raise RuntimeError('prepared payload/package pins changed')
        check_map_backup(preflight)
        check_packages(packages)
        if args.phase == 'request-close':
            if record['stage'] != 'prepared_clean_boundary_normal_close_pending' or record['normal_close_requested']:
                raise RuntimeError('normal close already dispatched or unsupported state; inspect')
            unchanged(prepared, rows, packages)
            native, compare = native_snapshot()
            if not compare(record['native_before']['actors'], native['actors'])['equivalent']:
                raise RuntimeError('new saved actor drift; preserve')
            same_camera(native, record['native_before'])
            observed = processes()
            if len(observed) != 1 or observed[0]['ProcessId'] != args.old_editor_pid:
                raise RuntimeError('single current editor changed')
            code = '''# Codex authorized HUD NORMAL editor close, never forced
import unreal,sys
b=sys.modules['claude_unreal_bridge']
others=[req.get('type') for gen,req,box in b._running if req.get('type')!='execute_python' or not (req.get('params') or {}).get('code','').startswith('# Codex authorized HUD NORMAL editor close')]
if others or b._jobs.qsize() or b._remote_lock.locked():raise RuntimeError('new conflicting native work')
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE running')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('new unsaved work; preserve')
unreal.SystemLibrary.execute_console_command(None,'CLOSE_SLATE_MAINFRAME')
result={'normal_close_requested':True,'forced':False}
'''
            record.update(stage='normal_close_dispatched_outcome_requires_process_readback',
                          normal_close_requested=True, normal_close_utc=now())
            retain(record)
            try:
                record['normal_close_reply'] = wire.call(wire.UNREAL, 'execute_python', code=code,
                                                          unattended=False, timeout=15, side='Unreal')
            except Exception as exc:
                record['normal_close_transport_observation'] = str(exc)
            retain(record)
        elif args.phase == 'install':
            if record['stage'] != 'normal_close_dispatched_outcome_requires_process_readback' or record['installations']:
                raise RuntimeError('install cannot be replayed; inspect outcome and journal')
            record['zero_editor_witness'] = require_zero_editors()
            unchanged(prepared, rows, packages)
            candidate_metadata(prepared)
            record['stage'] = 'normal_editor_exited_five_leaf_install_in_progress'
            retain(record)
            for row in rows:
                event = {**row, 'state': 'stage_pending'}
                record['installations'].append(event)
                retain(record)
                atomic_copy(row['source'], row['target'], row['expected'], event, record, '.codex-hud-staged')
            if fp(MODULE) != fingerprint(record['unchanged_module_receipt']):
                raise RuntimeError('canonical .modules changed; do not forge/reopen')
            check_map_backup(preflight)
            check_packages(packages)
            record.update(stage='five_exact_leaves_installed_normal_visible_reopen_pending', installed_utc=now())
            retain(record)
        else:
            if record['reopen_dispatched'] or record['rollback']:
                raise RuntimeError('rollback requires separate normal exit/journal reconciliation or is already dispatched')
            record['rollback_zero_editor_witness'] = require_zero_editors()
            for row in rows:
                if fp(row['target']) not in (row['before'], row['expected']) or fp(row['backup']) != row['before']:
                    raise RuntimeError('rollback leaf has unknown bytes; preserve and inspect')
            if fp(MODULE) != fingerprint(record['unchanged_module_receipt']):
                raise RuntimeError('module receipt drift; no rollback overwrite')
            record['stage'] = 'explicit_five_leaf_rollback_in_progress'
            retain(record)
            for row in reversed(rows):
                if fp(row['target']) == row['before']:
                    continue
                event = {'target': row['target'], 'source': row['backup'], 'expected': row['before'], 'state': 'stage_pending'}
                record['rollback'].append(event)
                retain(record)
                atomic_copy(row['backup'], row['target'], row['before'], event, record, '.codex-hud-rollback-staged')
            unchanged(prepared, [{**row, 'expected': fp(row['source'])} for row in rows], packages)
            check_map_backup(preflight)
            record.update(stage='original_five_leaves_restored_normal_visible_reopen_pending', rollback_utc=now())
            retain(record)
    print(json.dumps({'stage': record['stage'], 'journal': str(OUT), 'journal_fingerprint': fp(OUT),
                      'installed_leaves': len(record['installations']), 'tracked_packages': len(packages)}, indent=2))


if __name__ == '__main__':
    main()
