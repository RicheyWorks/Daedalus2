# SPDX-License-Identifier: MIT
"""Host delivery for exactly one retained Bulrush; the sole operator runs it.

Preparation is file-only. Run/readback use existing connectors and the pinned
one-asset native profile. A dispatch journal forbids replay after any outcome,
including a socket timeout. No actors, map saves or shared settings are changed.
"""
import argparse
import ast
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from codex_aetherflow_delivery import BASE, MAP_FILE, editor, load
from codex_contest_island_delivery import fingerprint
from codex_editor_handoff import _asset_file, wire

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT.parent
FOLDER = BASE / 'AquaticBulrushR1'
QUALIFICATION = FOLDER / 'source-qualification.json'
QUALIFICATION_FP = {'bytes': 11634, 'sha256': 'f3bd021c84cd51af690553ada3050f57d9e00af6423e59d9b163cb783e0cef89'}
NATIVE = ROOT / 'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_static_intake.py'
SHARED = NATIVE.with_name('daedalus_codex_catalogue.py')
MIRI = BASE / 'MiriV2/readback.json'
RESTORED = BASE / 'codex-arcade-acceptance-production-restored.json'
RESTORED_FP = {'bytes': 124281, 'sha256': '24f704803e3d642c2530e304b74017627c059f305ca348445f3a893ac11d764b'}
SNAP_SOURCE = TASK / 'build_visible_garden_landing.py'
MAP_FP = {'bytes': 209329457, 'sha256': '5690b48f9cdc9f50251c08127b161ab4f3afae49754b75316d561da2a3a80933'}
WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
NAME = 'Prop_Aquatic_Marsh_Bulrush_1'
DESTINATION = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Aquatic_Bulrush_Sprout_1035e10dfad9afc6'
NATIVE_PATH = DESTINATION + '/' + NAME + '.' + NAME
LABEL = 'Codex qualified one-static asset-only import-save'


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def _pin(path):
    return {'path': str(path), **fingerprint(path)}


def _check(pin):
    if fingerprint(pin['path']) != {key: pin[key] for key in ('bytes', 'sha256')}:
        raise RuntimeError('retained witness changed: ' + pin['path'])


def _snap_definition():
    """Extract only the established native snap() function, never run its host."""
    tree = ast.parse(SNAP_SOURCE.read_text(encoding='utf-8'))
    original = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'code'
                            for target in node.targets))
    inner = ast.parse(original)
    function = next(node for node in inner.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'snap')
    return ast.get_source_segment(original, function) + '\n'


def _protected_baseline():
    """Reconcile historical saved hashes with the later 102-path class receipt."""
    miri = load(MIRI)
    if (miri.get('stage') != 'miri_saved_readback_complete' or miri.get('issues') != []
            or miri.get('verified_saved_static_mesh_files') != 102
            or len(miri.get('outputs', {})) != 17):
        raise RuntimeError('completed 102-static plus17-Miri receipt required')
    static = dict(load(BASE / 'codex-aetherflow-final.native.json')['local']['disk_static_meshes'])
    palette = load(BASE / 'PaletteVariants/HeroR3/Native91011/20695ee29c31a3d4c630cdad.json')
    static.update(palette['outputs'])
    rack = load(BASE / 'ServerRackR1/readback.json')
    static[rack['native_path']] = rack['output_fingerprint']
    for relative in ('CatalogueEggR1/readback.json', 'CatalogueEggGemsR1/readback.json'):
        receipt = load(BASE / relative)
        if receipt.get('issues') != [] or receipt.get('stage') != 'three_assets_saved_readback_complete':
            raise RuntimeError('completed retained egg readback required: ' + relative)
        static.update(receipt['outputs'])
    classes = miri['native_readback']['saved_asset_classes']
    if (len(static) != 102 or set(static) != set(classes)
            or any(row.get('is_static_mesh') is not True for row in classes.values())):
        raise RuntimeError('exact historical 102-static path/hash set differs')
    packages = {path: {key: value[key] for key in ('bytes', 'sha256')}
                for path, value in static.items()}
    for path, value in miri['outputs'].items():
        if path in packages:
            raise RuntimeError('Miri package overlaps static baseline')
        packages[path] = {key: value[key] for key in ('bytes', 'sha256')}
    if len(packages) != 119:
        raise RuntimeError('exact protected119-package set required')
    if fingerprint(RESTORED) != RESTORED_FP:
        raise RuntimeError('later101-actor restoration witness changed')
    restored = load(RESTORED)
    if (restored.get('issues') != [] or restored.get('actor_records_unchanged') != 101
            or len(restored['native']['actors']) != 101 or restored['map'] != MAP_FP):
        raise RuntimeError('later clean101-actor/map5690 receipt required')
    _protect(packages)
    return packages, restored['native']


def _protect(packages):
    if len(packages) != 119:
        raise RuntimeError('protected119-package set required')
    for path, expected in packages.items():
        if fingerprint(_asset_file(path)) != expected:
            raise RuntimeError('protected native package changed: ' + path)
    if fingerprint(MAP_FILE) != MAP_FP:
        raise RuntimeError('current map5690 witness differs; preserve work, do not relax old guards')


def prepare():
    if (FOLDER / 'prepared.json').exists() or (FOLDER / 'dispatch.json').exists():
        raise RuntimeError('retained preparation/dispatch exists; inspect, never overwrite')
    if fingerprint(QUALIFICATION) != QUALIFICATION_FP:
        raise RuntimeError('exact retained Bulrush source qualification required')
    qualification = load(QUALIFICATION)
    item = dict(qualification['item'])
    if item['name'] != NAME or item['triangles'] != 36:
        raise RuntimeError('exact one qualified static Bulrush required')
    source_pins = [copy[side] for copy in qualification['copies'] for side in ('original', 'retained')]
    source_pins.extend(qualification['source_recipe_pins'])
    source_pins.extend([qualification['catalogue_manifest'], qualification['prior_raw_fbx_audit']])
    for pin in source_pins:
        _check(pin)
    item['destination'] = DESTINATION
    packages, scene = _protected_baseline()
    value = {'schema': 'daedalus.codex-one-static-prepared.v1',
        'stage': 'one_retained_bulrush_prepared', 'observed_utc': _utc(), 'item': item,
        'qualification': _pin(QUALIFICATION), 'native_source': _pin(NATIVE),
        'shared_source': _pin(SHARED), 'snapshot_source': _pin(SNAP_SOURCE),
        'snapshot_definition_sha256': hashlib.sha256(_snap_definition().encode()).hexdigest(),
        'source_pins': source_pins, 'protected_packages': packages,
        'baseline_miri_receipt': _pin(MIRI), 'baseline_scene_receipt': _pin(RESTORED),
        'baseline_scene': scene, 'map_fingerprint': MAP_FP,
        'shared_helpers_scope': 'Pinned old file executes in private fresh dict; only that dict LABEL changes. Old source/loaded module/egg validator untouched.',
        'limits': 'Asset-only save. No world/material changes, placement, native appearance, ecosystem, collision or runtime acceptance.'}
    write_new(FOLDER / 'prepared.json', value)
    print(json.dumps({'stage': value['stage'], 'prepared': _pin(FOLDER / 'prepared.json'),
                      'protected_packages': len(packages), 'actor_records': 101}, indent=2))


def _prepared():
    value = load(FOLDER / 'prepared.json')
    if value.get('stage') != 'one_retained_bulrush_prepared' or value['item']['destination'] != DESTINATION:
        raise RuntimeError('exact prepared one-Bulrush packet required')
    for key in ('qualification', 'native_source', 'shared_source', 'snapshot_source',
                'baseline_miri_receipt', 'baseline_scene_receipt'):
        _check(value[key])
    for pin in value['source_pins']:
        _check(pin)
    if hashlib.sha256(_snap_definition().encode()).hexdigest() != value['snapshot_definition_sha256']:
        raise RuntimeError('established actor snapshot definition changed')
    _protect(value['protected_packages'])
    return value


def _lease():
    lease = json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=10)).get('unreal', {})
    if (lease.get('holder') != 'codex-play-guard'
            or lease.get('at', 0) + lease.get('ttl', 0) - time.time() < 240):
        raise RuntimeError('current sole-operator lease with240seconds remaining required')
    return lease


def _resources(args):
    """Fresh read-only OS memory data; no universal safe-RAM threshold claimed."""
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ('total_physical', 'available_physical',
             'total_commit_limit', 'available_commit', 'total_virtual', 'available_virtual', 'reserved')]
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise RuntimeError('fresh OS memory sample unavailable')
    result = {key: int(getattr(memory, key)) for key, kind in memory._fields_}
    result.update(observed_utc=_utc(), available_commit_note='OS ullAvailPageFile; process virtual address space is separately recorded',
                  minimum_free_physical_mib=args.minimum_free_physical_mib,
                  minimum_free_commit_mib=args.minimum_free_commit_mib,
                  safety_limit='Measured data only; optional floors are explicit operator choices, not a measured general safe ceiling.')
    if (memory.available_physical <= 0 or memory.available_commit <= 0
            or memory.available_physical < args.minimum_free_physical_mib * 1024 ** 2
            or memory.available_commit < args.minimum_free_commit_mib * 1024 ** 2):
        raise RuntimeError('fresh memory headroom fails explicit operator floor')
    return result


def _scene_snapshot():
    code = '''# Codex one-static read-only preservation snapshot
import unreal,sys,hashlib
b=sys.modules['claude_unreal_bridge']
if not all(hasattr(b,k) for k in ('_jobs','_running','_job_boxes','_remote_lock')):raise RuntimeError('bridge queue fields unavailable')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
p,r=e.get_level_viewport_camera_info()
''' + _snap_definition() + '''
result={'world':e.get_editor_world().get_path_name(),'pie':unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(),
 'actors':[snap(a) for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label().startswith('Codex')],
 'dirty_maps':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
 'dirty_content':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
 'queued':b._jobs.qsize(),'remote_locked':b._remote_lock.locked(),
 'running':[{'type':req.get('type'),'code_sha256':hashlib.sha256(str((req.get('params') or {}).get('code','')).encode()).hexdigest()} for gen,req,box in list(b._running)],
 'unfinished_async_job_boxes':sum(not box['done'].is_set() for box,stamp in list(b._job_boxes.values())),
 'camera':{'location':{'x':p.x,'y':p.y,'z':p.z},'rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll}}}
'''
    result = wire.obj(wire.call(wire.UNREAL, 'execute_python', code=code, unattended=False,
                               timeout=45, side='Unreal'), side='Unreal', what='one-static scene preservation snapshot')
    own = {'type': 'execute_python', 'code_sha256': hashlib.sha256(code.encode()).hexdigest()}
    if (len(result['running']) > 1 or any(row != own for row in result['running'])
            or any(result[key] for key in ('pie', 'dirty_maps', 'dirty_content', 'queued',
                                          'remote_locked', 'unfinished_async_job_boxes'))):
        raise RuntimeError('fresh scene/queue check conflicts; preserve work')
    return result


def _same_scene(actual, expected):
    if (actual['world'] != WORLD or actual['world'] != expected['world']
            or len(actual['actors']) != 101
            or {a['path']: a for a in actual['actors']} != {a['path']: a for a in expected['actors']}):
        raise RuntimeError('exact101 actor snapshots/world differ; preserve current work')
    if any(abs(actual['camera'][group][key] - value) > 1e-5
           for group in ('location', 'rotation') for key, value in expected['camera'][group].items()):
        raise RuntimeError('saved construction camera changed; do not overwrite it')


def _config(value, lease):
    return {'item': value['item'], 'journal': str(FOLDER / 'native.json'),
            'deadline_epoch': min(time.time() + 600, lease['at'] + lease['ttl'] - 60),
            'shared_source': value['shared_source']['path'],
            'shared_source_fingerprint': {key: value['shared_source'][key] for key in ('bytes', 'sha256')}}


def _module_code(value):
    return ("from pathlib import Path\nimport hashlib\nsource=" + repr(value['native_source']['path'])
            + "\nraw=Path(source).read_bytes()\nif hashlib.sha256(raw).hexdigest()!="
            + repr(value['native_source']['sha256']) + ":raise RuntimeError('pinned one-static native module changed')\n"
            + "scope={'__name__':'_codex_qualified_one_static_delivery'}\nexec(compile(raw,source,'exec'),scope)\n")


def _read_native(value, cfg, operation):
    if operation not in ('preflight', 'readback'):
        raise ValueError('read-only native entry required')
    code = (_module_code(value) + '\ndef steps():\n    if False: yield\n    return scope['
            + repr(operation) + '](' + repr(cfg) + ')\n')
    reply = wire.call(wire.UNREAL, 'daedalus.steps', code=code, label=LABEL,
                      budget_ms=1, timeout=90, side='Unreal')
    return wire.obj(reply, side='Unreal', what='one-static ' + operation)


def run(args):
    if not args.operator_no_inflight:
        raise RuntimeError('sole operator must declare current no-inflight state; native checks independently verify it')
    dispatch = FOLDER / 'dispatch.json'
    if dispatch.exists() or (FOLDER / 'native.json').exists() or (FOLDER / 'reply.json').exists():
        raise RuntimeError('retained dispatch/native result exists; inspect known/uncertain outcome, never replay')
    value = _prepared()
    lease, resources = _lease(), _resources(args)
    editor()
    before = _scene_snapshot()
    _same_scene(before, value['baseline_scene'])
    cfg = _config(value, lease)
    admission = _read_native(value, cfg, 'preflight')
    _protect(value['protected_packages'])
    lease = _lease()
    cfg = _config(value, lease)
    code = _module_code(value) + '\ndef steps():\n    return (yield from scope[\'steps\'](' + repr(cfg) + '))\n'
    record = {'schema': 'daedalus.codex-one-static-dispatch.v1', 'stage': 'native_dispatch_pending',
        'observed_utc': _utc(), 'operator': 'codex-play-guard', 'operator_no_inflight_declaration': True,
        'lease': lease, 'resources': resources, 'native_preflight': admission, 'scene_before': before,
        'map_before': fingerprint(MAP_FILE), 'prepared_fingerprint': fingerprint(FOLDER / 'prepared.json'),
        'code_sha256': hashlib.sha256(code.encode()).hexdigest(), 'replay_permitted': False}
    write_new(dispatch, record)
    try:
        reply = wire.call(wire.UNREAL, 'daedalus.steps', code=code, label=LABEL,
                          budget_ms=1, timeout=180, side='Unreal')
        write_new(FOLDER / 'reply.json', reply)
        record.update(stage='native_returned_inspect_before_replay', reply_fingerprint=fingerprint(FOLDER / 'reply.json'))
        _write(dispatch, record)
        native = load(FOLDER / 'native.json')
        if (native.get('stage') != 'one_asset_saved_world_held' or native.get('completed_count') != 1
                or native.get('save_return') is not True or len(native.get('items', [])) != 1):
            raise RuntimeError('exact one native save not confirmed; inspect retained journal')
        row = native['items'][0]
        if (row.get('stage') != 'asset_saved_world_held' or row.get('save_return') is not True
                or row.get('native_path') != NATIVE_PATH or native.get('world_placed') != 0
                or native.get('world_saved') is not False):
            raise RuntimeError('one-static result contract differs; inspect retained journal')
        outputs = {NATIVE_PATH: fingerprint(_asset_file(NATIVE_PATH))}
        _protect(value['protected_packages'])
        record.update(stage='one_asset_saved_world_held', outputs=outputs,
                      native_receipt_fingerprint=fingerprint(FOLDER / 'native.json'))
        _write(dispatch, record)
        print(json.dumps({'stage': record['stage'], 'outputs': outputs,
                          'import_s': row['import_s'], 'save_s': row['save_s'], 'save_return': True}, indent=2))
    except Exception as exc:
        record.update(stage='outcome_requires_inspection_no_replay', error_type=type(exc).__name__, error=str(exc))
        try:
            _protect(value['protected_packages'])
            record['protected119_and_map_unchanged_at_error_read'] = True
        except Exception as preservation:
            record['preservation_error'] = str(preservation)
        _write(dispatch, record)
        raise


def readback(args):
    if (FOLDER / 'readback.json').exists():
        raise RuntimeError('retained readback exists; inspect, never overwrite')
    value = _prepared()
    dispatch = load(FOLDER / 'dispatch.json')
    if (dispatch.get('stage') != 'one_asset_saved_world_held'
            or fingerprint(FOLDER / 'prepared.json') != dispatch['prepared_fingerprint']
            or set(dispatch['outputs']) != {NATIVE_PATH}):
        raise RuntimeError('known completed one-asset dispatch required; uncertain outcomes need independent inspection')
    for path, expected in dispatch['outputs'].items():
        if fingerprint(_asset_file(path)) != expected:
            raise RuntimeError('new saved native file changed')
    lease, resources = _lease(), _resources(args)
    editor()
    scene = _scene_snapshot()
    _same_scene(scene, value['baseline_scene'])
    native = _read_native(value, _config(value, lease), 'readback')
    if native.get('world_references') != [] or native.get('world_placed') != 0 or native.get('world_saved') is not False:
        raise RuntimeError('new asset world hold differs')
    after = _scene_snapshot()
    _same_scene(after, value['baseline_scene'])
    _protect(value['protected_packages'])
    for path, expected in dispatch['outputs'].items():
        if fingerprint(_asset_file(path)) != expected:
            raise RuntimeError('new output changed after native readback')
    report = {'schema': 'daedalus.codex-one-static-readback.v1',
        'stage': 'one_asset_saved_readback_complete', 'observed_utc': _utc(), 'issues': [],
        'native_readback': native, 'scene_readback': after, 'resources': resources,
        'outputs': dispatch['outputs'], 'protected_prior_packages': 119,
        'verified_saved_static_mesh_files': 103, 'preserved_miri_assets': 17,
        'verified_total_package_files': 120, 'measured_actor_records': 101,
        'all101_actor_snapshots_unchanged': True, 'camera_unchanged_tolerance': 1e-5,
        'world_placed': 0, 'world_saved': False, 'map_unchanged': True,
        'map_fingerprint': fingerprint(MAP_FILE), 'save_return': True,
        'native_receipt_fingerprint': fingerprint(FOLDER / 'native.json'),
        'shared_helper_scope': value['shared_helpers_scope'],
        'limits': 'Saved static asset only. Native appearance/collision/ecosystem/runtime unverified; no tests/PIE/world save/all-old-asset graph loads.'}
    write_new(FOLDER / 'readback.json', report)
    print(json.dumps({key: report[key] for key in ('stage', 'verified_saved_static_mesh_files',
        'preserved_miri_assets', 'verified_total_package_files', 'measured_actor_records', 'map_unchanged')}, indent=2))


def reconcile(args):
    """Read a known true save after a later guard failure; NEVER import or save.

    Preserve the initial dispatch/native/reply, including their failure. A new
    receipt establishes only the saved asset and current clean preservation.
    """
    output = FOLDER / 'known-save-readback.json'
    if output.exists():
        raise RuntimeError('retained known-save reconciliation exists; inspect it')
    value = _prepared()
    dispatch = load(FOLDER / 'dispatch.json')
    native = load(FOLDER / 'native.json')
    if (dispatch.get('stage') != 'outcome_requires_inspection_no_replay'
            or dispatch.get('prepared_fingerprint') != fingerprint(FOLDER / 'prepared.json')
            or native.get('stage') != 'halted_preserve_partial'
            or native.get('completed_count') != 1 or len(native.get('items', [])) != 1):
        raise RuntimeError('exact retained completed-save/late-failure journals required')
    row = native['items'][0]
    if (row.get('save_return') is not True or row.get('stage') != 'asset_saved_world_held'
            or row.get('native_path') != NATIVE_PATH or row.get('imported_object_paths') != [NATIVE_PATH]
            or row.get('observed', {}).get('issues') != []):
        raise RuntimeError('successful original first save not established; no completion mutation allowed')
    originals = {name: _pin(FOLDER / name) for name in ('dispatch.json', 'native.json', 'reply.json')}
    lease, resources = _lease(), _resources(args)
    editor()
    before = _scene_snapshot()
    _same_scene(before, value['baseline_scene'])
    saved_file = fingerprint(_asset_file(NATIVE_PATH))
    observed = _read_native(value, _config(value, lease), 'readback')
    if (observed.get('world_references') != [] or observed.get('world_placed') != 0
            or observed.get('world_saved') is not False):
        raise RuntimeError('asset-only saved readback differs')
    after = _scene_snapshot()
    _same_scene(after, value['baseline_scene'])
    _protect(value['protected_packages'])
    if fingerprint(_asset_file(NATIVE_PATH)) != saved_file:
        raise RuntimeError('new saved file changed during read-only reconciliation')
    for pin in originals.values():
        _check(pin)
    report = {'schema': 'daedalus.codex-one-static-known-save-readback.v1',
        'stage': 'one_asset_saved_readback_complete', 'observed_utc': _utc(), 'issues': [],
        'native_readback': observed, 'scene_readback': after, 'resources': resources,
        'outputs': {NATIVE_PATH: saved_file}, 'protected_prior_packages': 119,
        'verified_saved_static_mesh_files': 103, 'preserved_miri_assets': 17,
        'verified_total_package_files': 120, 'measured_actor_records': 101,
        'all101_actor_snapshots_unchanged': True, 'camera_unchanged_tolerance': 1e-5,
        'world_placed': 0, 'world_saved': False, 'map_unchanged': True,
        'map_fingerprint': fingerprint(MAP_FILE), 'save_return': True,
        'import_s': row['import_s'], 'save_s': row['save_s'],
        'original_outcome': {'stage': native['stage'], 'error': native['error'],
            'completed_count': native['completed_count'], 'receipts': originals},
        'reconciliation_native_mutations': 0, 'import_replayed': False, 'save_replayed': False,
        'limits': 'Saved static asset only. Original post-save guard failure retained; current clean queue is a later snapshot. Native appearance/collision/ecosystem/runtime unverified.'}
    write_new(output, report)
    print(json.dumps({key: report[key] for key in ('stage', 'outputs', 'save_return', 'import_s',
        'save_s', 'verified_saved_static_mesh_files', 'preserved_miri_assets',
        'verified_total_package_files', 'measured_actor_records', 'map_unchanged')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run', 'readback', 'reconcile'))
    parser.add_argument('--operator-no-inflight', action='store_true', help='Factual sole-writer declaration; not a substitute for native queue checks')
    parser.add_argument('--minimum-free-physical-mib', type=float, default=0)
    parser.add_argument('--minimum-free-commit-mib', type=float, default=0)
    arguments = parser.parse_args()
    if arguments.minimum_free_physical_mib < 0 or arguments.minimum_free_commit_mib < 0:
        parser.error('explicit resource floors cannot be negative')
    if arguments.stage == 'prepare':
        prepare()
    else:
        globals()[arguments.stage](arguments)
