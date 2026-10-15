# SPDX-License-Identifier: MIT
"""First saves for the exact returned, unsaved Miri import; never reimport.

The original source and failed-before-save journal remain immutable. Its strict
inspection is reused with one in-memory change: absent legacy data_model track
names are reported as unavailable. Named clips, bone hierarchy, local pose
samples, geometry, units and all source PBR checks remain mandatory.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import unreal

LABEL = 'Codex Miri v2 known unsaved skeletal completion'
ORIGINAL = {'bytes': 25647, 'sha256': '5a434e398dcaafc0cb5f66d399aca372f322dcd51a29bf7c3687e78fed05c059'}
KNOWN = {'bytes': 196435, 'sha256': '1aa5c82ca9ddb865bd33fbf061cbffdeab54dd6591ce6236e1a33b7db8bccdc9'}
EXPECTED_CLASSES = {'SkeletalMesh': 1, 'Skeleton': 1, 'AnimSequence': 3,
                    'MaterialInstanceConstant': 11, 'PhysicsAsset': 1}
ABSENT_MODEL_ERROR = "native readback unsupported: AttributeError: 'NoneType' object has no attribute 'get_bone_track_names'"
BEFORE = """            model = clip.get_editor_property('data_model')
            row['track_names'] = [str(name) for name in model.get_bone_track_names()]
"""
AFTER = """            model = clip.get_editor_property('data_model')
            if model is None:
                row['track_names'] = None
                row['track_names_readback'] = 'legacy data_model absent; named clips, skeleton and local pose samples remain strict'
            else:
                row['track_names'] = [str(name) for name in model.get_bone_track_names()]
                row['track_names_readback'] = 'legacy data_model track names available'
"""


def _read_pin(path, expected):
    raw = Path(path).read_bytes()
    actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if actual != expected:
        raise RuntimeError('retained known-state fingerprint differs: ' + str(path))
    return raw


def _load(cfg):
    source = str(cfg['original_source'])
    raw = _read_pin(source, ORIGINAL)
    text = raw.decode('utf-8')
    if text.count(BEFORE) != 1:
        raise RuntimeError('exact single legacy track-enumeration patch location required')
    patched = text.replace(BEFORE, AFTER, 1)
    scope = {'__name__': '_codex_known_miri_v2_completion'}
    exec(compile(patched, source + '#known-unsaved-completion', 'exec'), scope)
    # Expose no import-capable entry point in the completion scope.
    del scope['steps']
    scope['LABEL'] = LABEL
    glb, contract = scope['_config'](cfg)
    if cfg['known_journal_fingerprint'] != KNOWN:
        raise RuntimeError('exact known original journal fingerprint required')
    known = json.loads(_read_pin(cfg['known_journal'], KNOWN).decode('utf-8'))
    observed = known.get('observed_before_first_save') or {}
    assets = observed.get('assets') or []
    paths = known.get('imported_object_paths') or []
    if (known.get('stage') != 'halted_preserve_partial' or known.get('outputs') != []
            or known.get('save_return') is not None or known.get('source_sha256') != scope['SOURCE_SHA']
            or known.get('root') != scope['ROOT'] or known.get('error') != ABSENT_MODEL_ERROR
            or observed.get('issues') != [ABSENT_MODEL_ERROR]
            or len(paths) != 17 or len(set(paths)) != 17 or len(assets) != 17
            or set(paths) != {row['path'] for row in assets}
            or dict(Counter(row['class'] for row in assets)) != EXPECTED_CLASSES
            or any(not path.startswith(scope['ROOT'] + '/') for path in paths)):
        raise RuntimeError('original import is not the exact known seventeen-asset unsaved state')
    return scope, glb, contract, known, assets, hashlib.sha256(patched.encode('utf-8')).hexdigest()


def _disk_asset(path):
    package = path.split('.')[0]
    if not package.startswith('/Game/'):
        raise RuntimeError('owned /Game package required')
    return Path(unreal.Paths.project_content_dir()) / (package[len('/Game/'):] + '.uasset')


def _inspect(scope, contract, known_assets):
    observed, objects = scope['_inspect'](contract)
    expected = {row['path']: row['class'] for row in known_assets}
    actual = {row['path']: row['class'] for row in observed['assets']}
    if actual != expected:
        observed['issues'].append('fresh owned path/class set differs from exact returned import')
    observed['known_import_reconciliation'] = {
        'original_journal_fingerprint': KNOWN, 'original_module_fingerprint': ORIGINAL,
        'known_asset_count': 17, 'path_classes_match_original_import': actual == expected,
        'import_replayed': False,
        'track_names_limit': 'Legacy data_model may be absent; original clip, rig, pose and PBR checks remain strict'}
    return observed, objects


def inspect_assets(cfg):
    """Read the exact retained import through the narrow patched inspection."""
    scope, glb, contract, known, assets, patched_sha = _load(cfg)
    observed, objects = _inspect(scope, contract, assets)
    observed['patched_inspection_source_sha256'] = patched_sha
    observed['existing_owned_asset_files'] = [str(_disk_asset(path)) for path in objects
                                               if _disk_asset(path).exists()]
    return observed


def steps(cfg):
    journal = Path(cfg.get('newjournal', cfg.get('journal', '')))
    if journal.exists():
        raise RuntimeError('retained completion journal exists; inspect, never replay a save')
    if journal.resolve() == Path(cfg['known_journal']).resolve():
        raise RuntimeError('new completion journal must preserve original import journal')
    scope, glb, contract, known, assets, patched_sha = _load(cfg)
    scope['_deadline'](cfg)
    allowed_dirty = [row['path'].split('.')[0] for row in assets]
    initial = scope['_preflight'](allowed_dirty)
    observed, objects = _inspect(scope, contract, assets)
    if observed['issues']:
        raise scope['NativeContractError']('; '.join(observed['issues']), observed)
    existing = [str(_disk_asset(path)) for path in objects if _disk_asset(path).exists()]
    if existing:
        raise RuntimeError('owned package already saved; inspect, no first-save replay: ' + repr(existing))
    report = {'schema': 'daedalus.codex-miri-v2-known-completion.v1',
              'stage': 'known_unsaved_import_strictly_inspected', 'root': scope['ROOT'],
              'known_journal': str(cfg['known_journal']), 'known_journal_fingerprint': KNOWN,
              'original_source': str(cfg['original_source']), 'original_source_fingerprint': ORIGINAL,
              'patched_inspection_source_sha256': patched_sha,
              'source_glb': glb, 'source_sha256': scope['SOURCE_SHA'],
              'source_contract_sha256': scope['CONTRACT_SHA'],
              'reviewed_packet_sha256': scope['PACKET_SHA'],
              'original_import_s': known['import_s'], 'import_called': False,
              'initial_preflight': initial, 'observed_before_first_save': observed,
              'unit_contract': scope['UNIT_CONTRACT'], 'required_future_actor_scale': [1., 1., 1.],
              'world_placed': 0, 'world_saved': False, 'material_data_changed': False,
              'outputs': [], 'save_return': None, 'replay_permitted': False}
    with journal.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    write = scope['_write']
    eal = unreal.EditorAssetLibrary
    try:
        scope['_deadline'](cfg)
        scope['_preflight'](allowed_dirty)
        # Recheck immutable dispatch evidence and every source pin immediately
        # before the first owned mutation. This never invokes original steps().
        _read_pin(cfg['known_journal'], KNOWN)
        _read_pin(cfg['original_source'], ORIGINAL)
        scope['_config'](cfg)
        mesh = objects[observed['mesh']['path']]
        tags = {'codex_owner': 'codex-contest', 'codex_sha256': scope['SOURCE_SHA'],
                'codex_source_glb': glb, 'codex_unit_contract': scope['UNIT_CONTRACT'],
                'codex_required_actor_scale': '1,1,1',
                'codex_source_provenance': 'release_slice_review; Emberthread courier Miri; seed160814; reviewed additive walk-v2',
                'codex_reviewed_packet_sha256': scope['PACKET_SHA'],
                'codex_world_placement': 'held; continuous playback/controller/collision/game acceptance unverified'}
        report.update(stage='owned_mesh_metadata_dispatch_pending', metadata=tags)
        write(journal, report)
        for key, value in tags.items():
            eal.set_metadata_tag(mesh, key, value)
        if any(eal.get_metadata_tag(mesh, key) != value for key, value in tags.items()):
            raise RuntimeError('owned mesh provenance metadata readback differs')
        for path, obj in sorted(objects.items()):
            scope['_deadline'](cfg)
            scope['_preflight'](allowed_dirty)
            if _disk_asset(path).exists():
                raise RuntimeError('package appeared before first save; preserve: ' + path)
            row = {'path': path, 'class': obj.get_class().get_name(),
                   'save_return': None, 'save_s': None, 'stage': 'save_dispatch_pending'}
            report['outputs'].append(row)
            report['stage'] = 'owned_asset_first_save_dispatch_pending'
            write(journal, report)
            started = time.perf_counter()
            row['save_return'] = bool(eal.save_loaded_asset(obj, only_if_is_dirty=False))
            row['save_s'] = round(time.perf_counter() - started, 6)
            row['stage'] = 'asset_saved' if row['save_return'] else 'save_returned_false'
            report['stage'] = 'owned_asset_first_save_returned'
            write(journal, report)
            if row['save_return'] is not True:
                raise RuntimeError('owned asset first save returned false: ' + path)
            yield path
        report['final_preflight'] = scope['_preflight']()
        final, objects = _inspect(scope, contract, assets)
        report['observed_after_saves'] = final
        if final['issues']:
            raise scope['NativeContractError']('post-save Miri contract differs', final)
        report.update(stage='miri_assets_saved_world_held', save_return=True)
        write(journal, report)
        return report
    except Exception as exc:
        if isinstance(exc, scope['NativeContractError']):
            report['failed_observation'] = exc.observed
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__, error=str(exc))
        write(journal, report)
        raise
