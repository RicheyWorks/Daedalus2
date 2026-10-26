# SPDX-License-Identifier: MIT
# SOURCE ONLY. Embed once in main's CURRENT protected callback after discovery.
# Required bindings: unreal, snapshot, qualify, process_generation, operation_id,
# policy_id, OUT, original_package_pins. OUT is a fresh admitted existing folder;
# original_package_pins is exactly three {path,bytes,sha256,role} real host rows.
# Additional required binding: canonical_project_path from material_capture_paths.py.
# Result: material_imported_capture_result. This body does NOT run the assembler
# or consumer, and cannot convert HELD native/provider results into complete.
import copy as _ic_copy
import datetime as _ic_dt
import hashlib as _ic_hash
import json as _ic_json
import math as _ic_math
import os as _ic_os
import re as _ic_re
from pathlib import Path as _ic_Path

_IC_PROJECT = 'C:/Unreal/DaedalusRealm/DaedalusRealm.uproject'
_IC_WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
_IC_ROOT = '/Game/CodexToolEvaluation/EpicIntegrationR1/Import/Prop_PracticeCrate'
_IC_NAMES = ('Prop_PracticeCrate_M0', 'Prop_PracticeCrate_M1')
_IC_MATS = [_IC_ROOT + '/' + name + '.' + name for name in _IC_NAMES]
_IC_PACKAGE_ROOT = 'C:/Unreal/DaedalusRealm/Content/CodexToolEvaluation/EpicIntegrationR1/Import/Prop_PracticeCrate/'
_IC_FILES = {'original_mesh': _IC_PACKAGE_ROOT + 'Prop_PracticeCrate.uasset',
             'original_material_M0': _IC_PACKAGE_ROOT + 'Prop_PracticeCrate_M0.uasset',
             'original_material_M1': _IC_PACKAGE_ROOT + 'Prop_PracticeCrate_M1.uasset'}
_IC_FIELDS = ('project', 'world', 'pie', 'game_world', 'dirty_maps', 'dirty_content', 'scene', 'selection', 'camera')
_IC_COUNTERS = ('explicit_asset_load_requests', 'authored_material_write_requests',
                'material_cache_refreshes', 'evaluations', 'compilations')


def _ic_need(ok, message):
    if not ok:
        raise RuntimeError(message)


def _ic_encode(value):
    return _ic_json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def _ic_sha(raw):
    return _ic_hash.sha256(raw).hexdigest()


def _ic_utc():
    return _ic_dt.datetime.now(_ic_dt.timezone.utc).isoformat(timespec='microseconds')


def _ic_sha_value(value):
    return type(value) is str and _ic_re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _ic_time(value):
    _ic_need(type(value) is str and _ic_re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3,7}(?:Z|\+00:00)', value), 'Actual explicit UTC timestamp required')
    # Preserve seven-digit source text; parsing checks validity, not a rewritten
    # timestamp. This body does not use a public clock override or add tolerance.
    _ic_dt.datetime.fromisoformat(value[:26] + '+00:00' if len(value.split('.')[1].split('Z')[0].split('+')[0]) == 7 else value.replace('Z', '+00:00'))
    return value


def _ic_path_id(value):
    _ic_need(type(value) is str and value and '\x00' not in value, 'Saved absolute path required')
    value = value.replace('\\', '/')
    _ic_need(_ic_re.fullmatch(r'[A-Za-z]:/[^:]+', value) and all(x not in ('', '.', '..') for x in value[3:].split('/')), 'Noncanonical file path refused')
    return value.casefold()


def _ic_pairs(items):
    obj = {}
    for key, value in items:
        _ic_need(key not in obj, 'Duplicate native JSON key')
        obj[key] = value
    return obj


def _ic_shape(value, depth=0):
    _ic_need(depth <= 30, 'Native JSON depth bound exceeded')
    if type(value) is dict:
        _ic_need(len(value) <= 128, 'Native JSON object bound exceeded')
        for key, child in value.items():
            _ic_need(type(key) is str and len(key) <= 2048, 'Native JSON key bound exceeded')
            _ic_shape(child, depth + 1)
    elif type(value) is list:
        _ic_need(len(value) <= 128, 'Native JSON array bound exceeded')
        for child in value:
            _ic_shape(child, depth + 1)
    elif type(value) is str:
        _ic_need(len(value) <= 2048, 'Native JSON text bound exceeded')
    elif type(value) is float:
        _ic_need(_ic_math.isfinite(value), 'Nonfinite native JSON number')
    else:
        _ic_need(value is None or type(value) in (int, bool), 'Unsupported native JSON type')


def _ic_native_json(raw):
    _ic_need(type(raw) is bytes and 0 < len(raw) <= 524288, 'Exact bounded native UTF-8 bytes required')
    value = _ic_json.loads(raw.decode('utf-8'), object_pairs_hook=_ic_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('Nonfinite native JSON')))
    _ic_need(type(value) is dict, 'Native response must be a JSON object')
    _ic_shape(value)
    return value


def _ic_file(row):
    path = _ic_Path(row['path'])
    _ic_need(path.is_file() and not path.is_symlink() and not (getattr(path.lstat(), 'st_file_attributes', 0) & 0x400), 'Original saved file missing/reparse')
    first = path.stat()
    _ic_need(0 < first.st_size <= 8 * 1024 * 1024, 'Original saved file exceeds finite bound')
    raw = path.read_bytes()
    last = path.stat()
    _ic_need(len(raw) == first.st_size == last.st_size and first.st_mtime_ns == last.st_mtime_ns, 'Original saved file changed during read')
    return {'path': row['path'], 'bytes': len(raw), 'sha256': _ic_sha(raw), 'role': row['role']}


def _ic_run():
    for binding in ('unreal', 'snapshot', 'qualify', 'process_generation', 'operation_id', 'policy_id', 'OUT', 'original_package_pins'):
        _ic_need(binding in globals(), 'Required actual operator binding absent: ' + binding)
    _ic_need(callable(snapshot) and callable(qualify), 'Current callback protection helpers required')
    generation = _ic_copy.deepcopy(process_generation)
    _ic_need(type(generation) is dict and set(generation) == {'editor_pid', 'process_started_utc'}
             and type(generation['editor_pid']) is int and generation['editor_pid'] == _ic_os.getpid(), 'Actual current process generation differs')
    _ic_time(generation['process_started_utc'])
    _ic_need(type(operation_id) is str and _ic_re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', operation_id), 'New host operation UUID required')
    _ic_need(_ic_sha_value(policy_id), 'Actual frozen policy ID required')
    folder = _ic_Path(OUT)
    _ic_need(folder.is_absolute() and folder.is_dir() and not folder.is_symlink() and not (getattr(folder.lstat(), 'st_file_attributes', 0) & 0x400), 'Fresh admitted output folder required')
    names = ('capture-intent.json', 'scene-before.json', 'protection-before.raw.json',
             'native-fragment.raw.json', 'protection-after.raw.json', 'scene-after.json',
             'host-observation.json', 'provider-evidence.json', 'capture-summary.json')
    _ic_need(all(not (folder / n).exists() for n in names), 'Retained attempt exists; no overwrite/replay')
    rows = _ic_copy.deepcopy(original_package_pins)
    _ic_need(type(rows) is list and len(rows) == 3, 'Exactly three original saved-file pin rows required')
    roles = set()
    for row in rows:
        _ic_need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256', 'role'}, 'Exact original saved-file pin schema required')
        _ic_need(row['role'] in _IC_FILES and row['role'] not in roles and _ic_path_id(row['path']) == _ic_path_id(_IC_FILES[row['role']]), 'Original package role/path mismatch')
        _ic_need(type(row['bytes']) is int and row['bytes'] > 0 and _ic_sha_value(row['sha256']), 'Real original package size/SHA256 required')
        roles.add(row['role'])
    _ic_need(roles == set(_IC_FILES), 'All three original roles required')
    actual_before_files = [_ic_file(row) for row in rows]
    _ic_need(actual_before_files == rows, 'Original admitted package bytes differ before native work')
    library = getattr(unreal, 'DaedalusImportedFactorReadLibrary', None)
    _ic_need(library is not None and callable(getattr(library, 'read_imported_factor_protection', None))
             and callable(getattr(library, 'read_imported_factor_bindings', None)), 'Actual admitted reader discovery missing')
    errors, receipts, pins, calls = [], {}, {}, []

    def error(stage, exc):
        _ic_need(len(errors) < 16, 'Capture error count exceeded; retain existing artifacts')
        errors.append({'stage': stage, 'error': str(exc)[:1024]})

    def write_bytes(name, raw, maximum=524288):
        _ic_need(type(raw) is bytes and 0 < len(raw) <= maximum, 'Bounded raw artifact required')
        with (folder / name).open('xb') as stream:
            stream.write(raw)
        pin = {'path': str(folder / name), 'bytes': len(raw), 'sha256': _ic_sha(raw)}
        pins[name] = pin
        return pin

    def write_json(name, value, maximum=524288):
        return write_bytes(name, _ic_encode(value), maximum)

    def observe_response(name, value):
        # Preserve the original FString encoded once to UTF-8. No strip,
        # newline conversion, reserialization, observation/error replacement.
        _ic_need(type(value) is str, 'Native reader did not return FString text')
        raw = value.encode('utf-8')
        write_bytes(name, raw)
        parsed = _ic_native_json(raw)
        receipts[name] = parsed
        return parsed

    def observation(value):
        obs = value.get('native_observation')
        _ic_need(type(obs) is dict and type(obs.get('editor_pid')) is int and obs['editor_pid'] == generation['editor_pid'], 'Native observation PID differs')
        _ic_need(type(obs.get('project_path')) is str and _ic_path_id(obs['project_path']) == _ic_path_id(_IC_PROJECT), 'Native project observation differs')
        _ic_need(type(obs.get('capture_id')) is str and bool(obs['capture_id']), 'Native capture ID absent')
        _ic_time(obs.get('observed_at_utc'))
        return obs

    def provider(value):
        _ic_need(value.get('schema') == 'daedalus.imported-factor-protection.v1'
                 and value.get('native_invoked') is True and value.get('state') == 'complete'
                 and value.get('errors') == [] and value.get('dirty_before') == [] and value.get('dirty_after') == [], 'Protection provider is HELD/incomplete/dirty; original response retained')
        observation(value)
        _ic_need(type(value.get('official_import_getter_invocations')) is int and value['official_import_getter_invocations'] == 0, 'Protection provider unexpectedly invoked import metadata')
        for key in _IC_COUNTERS:
            _ic_need(type(value.get(key)) is int and value[key] == 0, 'Protection provider effect counter differs: ' + key)
        projection = value.get('snapshot')
        _ic_need(type(projection) is dict and projection.get('schema') == 'daedalus.imported-factor-current-projection.v1'
                 and type(projection.get('materials')) is list and len(projection['materials']) == 2, 'Complete criterion-scoped material projection required')
        _ic_need([r.get('material', {}).get('path') for r in projection['materials']] == _IC_MATS, 'Protection material ordering/identity differs')
        _ic_need(all(r.get('material', {}).get('class') == '/Script/Engine.Material' for r in projection['materials']), 'Protection material class differs')
        return _ic_sha(_ic_encode(projection))

    def host_snapshot(scene, files, graph_hash, phase, observed):
        # Exact source fields are copied; only project separators are normalized.
        _ic_need(type(scene) is dict and all(k in scene for k in _IC_FIELDS), 'Actual nine-field snapshot incomplete')
        project = canonical_project_path(scene['project'], unreal.Paths.convert_relative_path_to_full)
        _ic_need(project == _IC_PROJECT and scene['world'] == _IC_WORLD, 'Actual project/world snapshot differs')
        return {'phase': phase, 'operation_id': operation_id, 'process_generation': generation,
                'evidence_kind': 'native_capture', 'observed_at_utc': observed,
                'state': {'project_path': project, 'world_path': scene['world'],
                          'pie': scene['pie'], 'game_world': scene['game_world'],
                          'dirty_maps': _ic_copy.deepcopy(scene['dirty_maps']),
                          'dirty_content': _ic_copy.deepcopy(scene['dirty_content']),
                          'scene': _ic_copy.deepcopy(scene['scene']),
                          'selection': _ic_copy.deepcopy(scene['selection']),
                          'camera': _ic_copy.deepcopy(scene['camera']),
                          'original_files': files,
                          'original_graph_factors_parameters_sha256': graph_hash}}

    write_json('capture-intent.json', {'operation_id': operation_id, 'policy_id': policy_id,
               'process_generation': generation, 'started_utc': _ic_utc(),
               'call_order': ['protection_before', 'bindings_once', 'protection_after'],
               'scope': 'Criterion-scoped current-call/roster/three-factor and applicable parameter projection; not arbitrary serialized graph or unused parameter values'})
    before_scene = snapshot()
    qualify(before_scene)
    write_json('scene-before.json', before_scene)
    before_projection_sha = after_projection_sha = None
    native = None
    before_observed = None
    # Each exact call is attempted at most once. Held JSON is retained, not
    # promoted; collection of the independent after boundary still proceeds.
    try:
        calls.append('protection_before')
        value = library.read_imported_factor_protection(_IC_MATS, _IC_ROOT)
        parsed = observe_response('protection-before.raw.json', value)
        before_projection_sha = provider(parsed)
    except Exception as exc:
        error('protection_before', exc)
    before_observed = _ic_utc()  # Actual end of this fresh before-observation boundary.
    try:
        calls.append('bindings_once')
        value = library.read_imported_factor_bindings(_IC_MATS, _IC_ROOT, policy_id)
        native = observe_response('native-fragment.raw.json', value)
        observation(native)
        _ic_need(native.get('schema') == 'daedalus.imported-factor-native-fragment.v1'
                 and native.get('native_fields_state') == 'complete'
                 and native.get('state') == 'native_fields_complete_host_evidence_pending'
                 and native.get('errors') == [] and native.get('dirty_before') == [] and native.get('dirty_after') == [], 'Native fragment is HELD/incomplete/dirty; original bytes/errors retained')
    except Exception as exc:
        error('bindings_once', exc)
    try:
        calls.append('protection_after')
        value = library.read_imported_factor_protection(_IC_MATS, _IC_ROOT)
        parsed = observe_response('protection-after.raw.json', value)
        after_projection_sha = provider(parsed)
    except Exception as exc:
        error('protection_after', exc)
    after_scene = snapshot()
    write_json('scene-after.json', after_scene)
    try:
        qualify(after_scene)
    except Exception as exc:
        error('scene_after_qualification', exc)
    after_files = [_ic_file(row) for row in rows]
    if after_files != rows:
        error('original_files', 'Original package bytes differ after native read')
    if any(before_scene[k] != after_scene.get(k) for k in _IC_FIELDS):
        error('protected_scene', 'At least one original nine-field snapshot value changed')
    if before_projection_sha is None or after_projection_sha is None or before_projection_sha != after_projection_sha:
        error('protected_material_projection', 'Two complete criterion-scoped protection snapshots are unavailable or unequal')
    after_observed = _ic_utc()
    provider_ids = [r.get('native_observation', {}).get('capture_id') for r in receipts.values()]
    if len(provider_ids) != 3 or None in provider_ids or len(set(provider_ids)) != 3:
        error('native_capture_ids', 'Three distinct original native capture identities required')
    native_id = native.get('native_observation', {}).get('capture_id') if native else None
    fragment_pin = pins.get('native-fragment.raw.json')
    host = {'schema': 'daedalus.imported-factor-host-observation.v1', 'evidence_kind': 'native_capture',
            'operation_id': operation_id, 'process_generation': generation,
            'normal_terminal': len(receipts) == 3, 'errors': _ic_copy.deepcopy(errors),
            'native_fragment': {'bytes': fragment_pin['bytes'], 'sha256': fragment_pin['sha256'], 'capture_id': native_id} if fragment_pin else None,
            'before': host_snapshot(before_scene, actual_before_files, before_projection_sha, 'before', before_observed),
            'after': host_snapshot(after_scene, after_files, after_projection_sha, 'after', after_observed)}
    write_json('host-observation.json', host, 131072)
    provider_evidence = {'operation_id': operation_id, 'process_generation': generation,
                         'before': {'raw': pins.get('protection-before.raw.json'), 'projection_sha256': before_projection_sha,
                                    'native_observation': receipts.get('protection-before.raw.json', {}).get('native_observation')},
                         'after': {'raw': pins.get('protection-after.raw.json'), 'projection_sha256': after_projection_sha,
                                   'native_observation': receipts.get('protection-after.raw.json', {}).get('native_observation')},
                         'hash_method': 'sha256(sorted compact UTF-8 snapshot object only; ensure_ascii=False,allow_nan=False; array order unchanged)',
                         'hash_coverage': 'Criterion-scoped current-call/complete named roster/three factors and applicable parameter proof; not serialized whole graph or every unused parameter value',
                         'raw_providers_retained_externally': True}
    write_json('provider-evidence.json', provider_evidence, 131072)
    result = {'schema': 'daedalus.imported-factor-callback-result.v1', 'operation_id': operation_id,
              'state': 'READY_FOR_PURE_ASSEMBLER_NOT_ACCEPTED' if not errors else 'HELD',
              'errors': errors, 'native_calls': calls, 'artifacts': _ic_copy.deepcopy(pins),
              'protected_nine_fields_equal': all(before_scene[k] == after_scene.get(k) for k in _IC_FIELDS),
              'original_three_files_equal': actual_before_files == after_files,
              'criterion_projection_equal': before_projection_sha is not None and before_projection_sha == after_projection_sha,
              'raw_fragment_preserved_without_newline_conversion': fragment_pin is not None,
              'assembler_invoked': False, 'consumer_invoked': False,
              'base_color_admitted': False, 'all_pbr_factors_qualified': False,
              'root_output_equivalence_proven': False, 'native_runtime_qualified': False}
    write_json('capture-summary.json', result, 131072)
    return result


material_imported_capture_result = _ic_run()
