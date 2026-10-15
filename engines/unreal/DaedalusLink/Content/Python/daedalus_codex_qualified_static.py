# SPDX-License-Identifier: MIT
"""Deliver one to three source-qualified static meshes, with world placement held.

The existing egg and Bulrush entry points remain unchanged. This adapter only
reuses the exact retained catalogue pipeline, inspector, deadline and queue guard
in a private namespace. The host owns source qualification, current preservation
witnesses and the sole-operator lease. A retained journal forbids another import.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

import unreal

LABEL = 'Codex qualified small-static packet asset-only import-save'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/'
SHARED_FINGERPRINT = {
    'bytes': 22414,
    'sha256': '00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03',
}
MAX_ITEMS = 3
MAX_TRIANGLES = 3000


def _utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _fingerprint(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            size += len(chunk)
            digest.update(chunk)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def _pin(value):
    if (not isinstance(value, dict) or type(value.get('bytes')) is not int or value['bytes'] <= 0
            or not isinstance(value.get('sha256'), str)
            or re.fullmatch(r'[0-9a-fA-F]{64}', value['sha256']) is None):
        raise ValueError('positive byte count and exact SHA256 required')
    return {'bytes': value['bytes'], 'sha256': value['sha256'].lower()}


def _flush(output, value):
    json.dump(value, output, indent=2, allow_nan=False)
    output.write('\n')
    output.flush()
    os.fsync(output.fileno())


def _write(path, value):
    """Keep the previous receipt intact until the next complete receipt is durable.

    A leftover write-pending file is also a stop condition; it is never removed or
    reused automatically, including after a successful save with an uncertain reply.
    """
    path = Path(path)
    pending = path.with_name(path.name + '.write-pending')
    with pending.open('x', encoding='utf-8', newline='\n') as output:
        _flush(output, value)
    os.replace(pending, path)


def _shared(cfg):
    source = Path(cfg['shared_source'])
    raw = source.read_bytes()
    actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if (source.name != 'daedalus_codex_catalogue.py'
            or _pin(cfg['shared_source_fingerprint']) != SHARED_FINGERPRINT
            or actual != SHARED_FINGERPRINT):
        raise RuntimeError('exact pinned catalogue helpers required; old module must remain untouched')
    scope = {'__name__': '_codex_qualified_static_private_catalogue_helpers'}
    exec(compile(raw, str(source), 'exec'), scope)
    scope['LABEL'] = LABEL
    return scope


def _items(cfg):
    values = cfg['items']
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_ITEMS:
        raise ValueError('one to three independently qualified static items required')
    result, names, destinations, payloads = [], set(), set(), set()
    for value in values:
        item = dict(value)
        name, destination = item['name'], item['destination']
        if (not isinstance(name, str) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) is None
                or name.casefold() in names):
            raise ValueError('distinct legal static asset names required')
        if (not isinstance(destination, str) or not destination.startswith(ROOT)
                or destination == ROOT or destination.endswith('/') or '..' in destination
                or '//' in destination or '.' in destination or '\\' in destination
                or re.fullmatch(r'/[A-Za-z0-9_/]+', destination) is None):
            raise ValueError('fresh destination below the owned namespace required')
        folded = destination.casefold()
        if (folded in destinations or any(folded.startswith(old + '/') or old.startswith(folded + '/')
                                          for old in destinations)):
            raise ValueError('distinct non-nested destinations required')
        names.add(name.casefold())
        destinations.add(folded)
        item['fingerprint'] = _pin(item['fingerprint'])
        item['sidecar_fingerprint'] = _pin(item['sidecar_fingerprint'])
        fbx, sidecar = Path(item['fbx']), Path(item['sidecar'])
        if (fbx.suffix.lower() != '.fbx' or not fbx.is_file() or not sidecar.is_file()
                or fbx.resolve() == sidecar.resolve()
                or _fingerprint(fbx) != item['fingerprint']
                or _fingerprint(sidecar) != item['sidecar_fingerprint']):
            raise ValueError('exact qualified FBX and sidecar bytes required: ' + name)
        if item['fingerprint']['sha256'] in payloads:
            raise ValueError('duplicate FBX payload in one packet: ' + name)
        payloads.add(item['fingerprint']['sha256'])
        if type(item['triangles']) is not int or not 1 <= item['triangles'] <= MAX_TRIANGLES:
            raise ValueError('source triangle count must be within1..3000: ' + name)
        if (item['source_unit_scale_factor'] != 100 or item['mesh_geometry_count'] != 1
                or item['mesh_model_count'] != 1
                or any(type(item[key]) is not int or item[key] != 0 for key in
                       ('animations', 'animation_curves', 'deformers', 'textures', 'videos', 'authored_ucx'))):
            raise ValueError('single static mesh/model, unit100, no motion/UCX/textures required: ' + name)
        palette = item['rgba_bytes']
        if (not isinstance(palette, list) or not palette or len(palette) > item['triangles']
                or any(not isinstance(row, (list, tuple)) or len(row) != 4
                       or any(type(v) is not int or not 0 <= v <= 255 for v in row) for row in palette)):
            raise ValueError('exact source RGBA-byte palette required: ' + name)
        bounds = item['source_bounds']
        if (not isinstance(bounds, dict) or any(not isinstance(bounds.get(edge), (list, tuple))
                or len(bounds[edge]) != 3
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds[edge])
                for edge in ('min', 'max'))):
            raise ValueError('finite three-axis source bounds required: ' + name)
        dimensions = [bounds['max'][i] - bounds['min'][i] for i in range(3)]
        if any(v < 0 for v in dimensions) or not any(v > 0 for v in dimensions):
            raise ValueError('nonempty ordered source bounds required: ' + name)
        if not item.get('provenance') or not isinstance(item['provenance'], (str, dict)):
            raise ValueError('evidenced source provenance required; unknown author remains unknown')
        if not isinstance(item.get('author', 'unverified'), str):
            raise ValueError('author must be an evidenced string or unverified')
        json.dumps(item, allow_nan=False)
        result.append(item)
    return result


def _path(item):
    return item['destination'] + '/' + item['name'] + '.' + item['name']


def _absent(item):
    eal = unreal.EditorAssetLibrary
    existing = [str(row.package_name) + '.' + str(row.asset_name)
                for row in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game', recursive=True)
                if str(row.asset_name).casefold() == item['name'].casefold()]
    if (existing or eal.does_directory_exist(item['destination'])
            or eal.does_asset_exist(item['destination'] + '/' + item['name'])):
        raise RuntimeError('asset name/destination already exists; no overwrite or duplicate: ' + repr(existing))
    return {'name': item['name'], 'destination_absent': True, 'global_name_collisions': existing}


def _metadata(item, shared):
    provenance = item['provenance']
    if not isinstance(provenance, str):
        provenance = json.dumps(provenance, sort_keys=True, allow_nan=False)
    dimensions = [item['source_bounds']['max'][i] - item['source_bounds']['min'][i] for i in range(3)]
    return {'codex_owner': 'codex-contest', 'codex_sha256': item['fingerprint']['sha256'],
            'codex_source_fbx': str(item['fbx']), 'codex_author': item.get('author', 'unverified'),
            'codex_source_provenance': provenance, 'codex_unit_contract': shared['UNIT_CONTRACT'],
            'codex_required_actor_scale': '0.01,0.01,0.01',
            'codex_intended_dimensions_cm': ','.join(format(v, '.12g') for v in dimensions),
            'codex_world_placement': 'held; asset-only save; native appearance, collision and runtime acceptance unverified'}


def _inspect_bound(mesh, item, shared):
    observed = shared['inspect_mesh'](mesh, item)
    material_path = shared['MATERIAL'] + '.' + shared['MATERIAL'].rsplit('/', 1)[1]
    if (observed['slots'][0]['material'] != material_path or observed['metadata'] != _metadata(item, shared)):
        raise shared['NativeContractError']('bound material/source provenance metadata differs', observed)
    return observed


def preflight(cfg):
    shared, items = _shared(cfg), _items(cfg)
    shared['_deadline'](cfg)
    guard = shared['_preflight']()
    journal = Path(cfg['journal'])
    if (not journal.is_absolute() or journal.suffix.lower() != '.json' or not journal.parent.is_dir()
            or journal.exists() or journal.with_name(journal.name + '.write-pending').exists()
            or journal.resolve() in {Path(item[key]).resolve() for item in items for key in ('fbx', 'sidecar')}
            or journal.resolve() == Path(cfg['shared_source']).resolve()):
        raise RuntimeError('new owned absolute journal path with existing parent required; retained files forbid replay')
    destinations = [_absent(item) for item in items]
    material = unreal.EditorAssetLibrary.load_asset(shared['MATERIAL'])
    if not isinstance(material, unreal.MaterialInterface):
        raise RuntimeError('existing shared vertex-colour material missing')
    return {'guard': guard, 'items': items, 'destinations': destinations, 'material': material.get_path_name(),
            'shared_helpers': SHARED_FINGERPRINT, 'shared_guard_label_scope': 'private fresh namespace only',
            'requested_count': len(items), 'max_source_triangles_per_asset': MAX_TRIANGLES}


def readback(cfg):
    """Read saved outputs only; optional readback_names explicitly selects a saved subset.

    The subset is useful after a partial packet. It never resumes imports/saves or
    changes the retained original journal, and missing expected assets remain errors.
    """
    shared, items = _shared(cfg), _items(cfg)
    shared['_deadline'](cfg)
    guard = shared['_preflight']()
    selected = cfg.get('readback_names', [item['name'] for item in items])
    if (not isinstance(selected, list) or not selected or len(set(selected)) != len(selected)
            or not set(selected).issubset({item['name'] for item in items})):
        raise ValueError('readback_names must explicitly select distinct qualified packet items')
    eal, observations = unreal.EditorAssetLibrary, []
    for item in items:
        if item['name'] not in selected:
            continue
        shared['_deadline'](cfg)
        expected = _path(item)
        paths = [str(p) for p in eal.list_assets(item['destination'], recursive=True, include_folder=False)]
        if paths != [expected]:
            raise RuntimeError('saved destination must contain exactly the one expected asset: ' + item['name'])
        mesh = eal.load_asset(expected)
        observations.append({'name': item['name'], 'native_path': expected, 'observed': _inspect_bound(mesh, item, shared)})
    paths = {row['native_path'] for row in observations}
    references = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            if mesh and mesh.get_path_name() in paths:
                references.append({'actor': actor.get_path_name(), 'mesh': mesh.get_path_name()})
    if references:
        raise RuntimeError('held intake asset unexpectedly referenced by world actors')
    after = shared['_preflight']()
    return {'preflight': guard, 'post_read_preflight': after, 'items': observations,
            'requested_packet_count': len(items), 'readback_count': len(observations),
            'not_read_back_names': [item['name'] for item in items if item['name'] not in selected],
            'world_references': references, 'world_placed': 0, 'world_saved': False,
            'shared_material_modified': False, 'persistent_mesh_modified': False}


def steps(cfg):
    journal = Path(cfg['journal'])
    if journal.exists() or journal.with_name(journal.name + '.write-pending').exists():
        raise RuntimeError('retained native journal exists; inspect, never replay')
    admission = preflight(cfg)
    shared, items = _shared(cfg), _items(cfg)
    eal = unreal.EditorAssetLibrary
    report = {'schema': 'daedalus.codex-qualified-static-packet-native.v1', 'utc': _utc(),
              'stage': 'qualified_static_packet_admitted', 'initial_preflight': admission,
              'requested_count': len(items), 'completed_count': 0, 'items': [], 'save_return': None,
              'requested_options': {'backend': 'explicit_InterchangePipelineStackOverride',
                                    'build_scale3d': [1., 1., 1.], 'vertex_colors': 'REPLACE', 'bake_meshes': True,
                                    'build_nanite': False, 'generate_lightmap_u_vs': False, 'collision': False,
                                    'import_materials': False, 'replace_existing': False, 'task_save': False},
              'unexposed_options': 'Animation/texture flags not explicitly set; qualified source and exact single-static output required',
              'unit_contract': shared['UNIT_CONTRACT'], 'required_future_actor_scale': [.01, .01, .01],
              'world_placed': 0, 'world_saved': False, 'shared_material_modified': False, 'replay_permitted': False,
              'limits': 'Source/asset-save acceptance only; appearance, collision and runtime acceptance remain unverified.'}
    with journal.open('x', encoding='utf-8', newline='\n') as output:
        _flush(output, report)
    row = None
    try:
        for item in items:
            expected = _path(item)
            shared['_deadline'](cfg)
            shared['_preflight']()
            _items(cfg)
            _absent(item)
            row = {'name': item['name'], 'source': item, 'stage': 'import_dispatch_pending',
                   'native_path': None, 'save_return': None, 'mutation_intents': []}
            report['items'].append(row)
            task = unreal.AssetImportTask()
            task.filename, task.destination_path, task.destination_name = item['fbx'], item['destination'], item['name']
            task.automated, task.replace_existing, task.save = True, False, False
            task.options = shared['_pipeline']()
            row['mutation_intents'].append({'operation': 'import_exact_one_static', 'utc': _utc(), 'expected_path': expected})
            report['stage'] = 'item_import_dispatch_pending'
            _write(journal, report)
            started = time.perf_counter()
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            row.update(stage='import_returned', import_s=round(time.perf_counter() - started, 6),
                       imported_object_paths=[str(p) for p in task.imported_object_paths])
            report['stage'] = 'item_import_returned'
            _write(journal, report)
            row['destination_asset_paths'] = [str(p) for p in eal.list_assets(item['destination'], recursive=True, include_folder=False)]
            if row['destination_asset_paths'] != [expected] or row['imported_object_paths'] != [expected]:
                raise RuntimeError('exact one returned mesh path required; preserve partial import')
            mesh = eal.load_asset(expected)
            row['native_path'] = mesh.get_path_name()
            row['observed_before_binding'] = shared['inspect_mesh'](mesh, item)
            row.update(stage='binding_dispatch_pending', expected_metadata=_metadata(item, shared))
            row['mutation_intents'].append({'operation': 'bind_existing_material_and_source_metadata', 'utc': _utc(), 'path': expected})
            report['stage'] = 'item_binding_dispatch_pending'
            _write(journal, report)
            shared['_deadline'](cfg)
            shared['_preflight'](allowed_dirty=(expected.split('.')[0],))
            mesh.modify()
            mesh.set_material(0, eal.load_asset(shared['MATERIAL']))
            for key, value in row['expected_metadata'].items():
                eal.set_metadata_tag(mesh, key, value)
            row.update(observed=_inspect_bound(mesh, item, shared), stage='save_dispatch_pending')
            row['mutation_intents'].append({'operation': 'save_exact_owned_asset', 'utc': _utc(), 'path': expected})
            report['stage'] = 'item_save_dispatch_pending'
            _write(journal, report)
            shared['_deadline'](cfg)
            shared['_preflight'](allowed_dirty=(expected.split('.')[0],))
            started = time.perf_counter()
            row['save_return'] = bool(eal.save_loaded_asset(mesh, only_if_is_dirty=False))
            row['save_s'] = round(time.perf_counter() - started, 6)
            row['stage'] = 'asset_saved_world_held' if row['save_return'] else 'save_returned_false'
            if row['save_return']:
                report['completed_count'] += 1
            report['stage'] = 'item_save_returned'
            report['save_return'] = True if report['completed_count'] == len(items) else None
            _write(journal, report)
            if row['save_return'] is not True:
                raise RuntimeError('owned new asset save returned false')
            yield row['native_path']
            row['post_save_preflight'] = shared['_preflight']()
            _write(journal, report)
        report.update(stage='qualified_static_assets_saved_world_held', save_return=True)
        _write(journal, report)
        return report
    except Exception as exc:
        if row is not None and isinstance(exc, shared['NativeContractError']):
            row['failed_observation'] = exc.observed
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__, error=str(exc),
                      replay_permitted=False, failure_utc=_utc())
        # Never erase a complete prior receipt or a pending write after an uncertain write.
        if not journal.with_name(journal.name + '.write-pending').exists():
            _write(journal, report)
        raise
