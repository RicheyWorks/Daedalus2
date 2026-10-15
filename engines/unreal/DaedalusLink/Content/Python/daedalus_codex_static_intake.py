# SPDX-License-Identifier: MIT
"""Deliver ONE qualified retained Bulrush using the existing static FBX route.

No actors, world saves or changes to the historical egg delivery contract. The
host supplies exact source witnesses, current package/scene preservation and a
bounded sole-operator lease. An existing journal forbids another import.
"""
import hashlib
import json
from pathlib import Path
import time

import unreal

LABEL = 'Codex qualified one-static asset-only import-save'
NAME = 'Prop_Aquatic_Marsh_Bulrush_1'
SOURCE_SHA = '1035e10dfad9afc65a5b442a530b2163c82d57cbfefbbf59973751e005ef6cbd'
DESTINATION = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Aquatic_Bulrush_Sprout_1035e10dfad9afc6'


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def _fingerprint(path):
    raw = Path(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _shared(cfg):
    """Use pinned helpers in a private scope; leave old loaded modules untouched.

    Its guard recognizes the caller by LABEL. Set that constant only in this
    fresh execution scope, so our own labelled generator is not a foreign job.
    The old egg validator, metadata and steps are never called or modified.
    """
    source = cfg['shared_source']
    if _fingerprint(source) != cfg['shared_source_fingerprint']:
        raise RuntimeError('pinned existing static import helpers changed')
    scope = {'__name__': '_codex_pinned_static_intake_helpers'}
    exec(compile(Path(source).read_bytes(), source, 'exec'), scope)
    scope['LABEL'] = LABEL
    return scope


def _item(cfg):
    item = cfg['item']
    if (item['name'] != NAME or item['destination'] != DESTINATION
            or item['fingerprint'] != {'bytes': 15100, 'sha256': SOURCE_SHA}
            or _fingerprint(item['fbx']) != item['fingerprint']
            or Path(item['fbx']).suffix.lower() != '.fbx'
            or _fingerprint(item['sidecar']) != item['sidecar_fingerprint']):
        raise ValueError('exact retained Bulrush payload and destination required')
    if (item['triangles'] != 36 or item['rgba_bytes'] != [[111, 168, 117, 255]]
            or item['source_bounds'] != {'min': [-15., -15., 0.], 'max': [20., 20., 25.]}
            or item['source_unit_scale_factor'] != 100
            or item['mesh_geometry_count'] != 1 or item['mesh_model_count'] != 1
            or any(item[k] != 0 for k in
                   ('animations', 'animation_curves', 'deformers', 'textures', 'videos', 'authored_ucx'))):
        raise ValueError('qualified single static Bulrush source contract differs')
    return item


def _metadata(item, shared):
    return {
        'codex_owner': 'codex-contest',
        'codex_sha256': SOURCE_SHA,
        'codex_source_fbx': item['fbx'],
        'codex_author': 'Team Claude current producer; historical exporter author unverified',
        'codex_source_provenance': json.dumps(item['provenance'], sort_keys=True),
        'codex_unit_contract': shared['UNIT_CONTRACT'],
        'codex_required_actor_scale': '0.01,0.01,0.01',
        'codex_intended_dimensions_cm': '35,35,25',
        'codex_world_placement': 'held; asset-only save; native appearance, collision and ecosystem acceptance unverified',
    }


def preflight(cfg):
    shared, item = _shared(cfg), _item(cfg)
    shared['_deadline'](cfg)
    guard = shared['_preflight']()
    eal = unreal.EditorAssetLibrary
    existing = [str(row.package_name) + '.' + str(row.asset_name)
                for row in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game', recursive=True)
                if str(row.asset_name) == NAME]
    if existing or eal.does_directory_exist(DESTINATION) or eal.does_asset_exist(DESTINATION + '/' + NAME):
        raise RuntimeError('source name/destination already exists; no duplicate or overwrite: ' + repr(existing))
    material = eal.load_asset(shared['MATERIAL'])
    if not isinstance(material, unreal.MaterialInterface):
        raise RuntimeError('existing shared vertex-colour material missing')
    return {'guard': guard, 'source': item, 'destination_absent': True,
            'global_name_collisions': existing, 'material': material.get_path_name(),
            'shared_helpers': cfg['shared_source_fingerprint'],
            'shared_guard_label_scope': 'private fresh namespace only; old module unchanged'}


def _inspect_bound(mesh, item, shared):
    observed = shared['inspect_mesh'](mesh, item)
    material_path = shared['MATERIAL'] + '.' + shared['MATERIAL'].rsplit('/', 1)[1]
    if (observed['slots'][0]['material'] != material_path
            or observed['metadata'] != _metadata(item, shared)):
        raise shared['NativeContractError']('saved material/metadata differs', observed)
    return observed


def readback(cfg):
    """Read only the new saved mesh, not the prior 119 asset graphs."""
    shared, item = _shared(cfg), _item(cfg)
    guard = shared['_preflight']()
    expected = DESTINATION + '/' + NAME + '.' + NAME
    eal = unreal.EditorAssetLibrary
    paths = [str(p) for p in eal.list_assets(DESTINATION, recursive=True, include_folder=False)]
    if paths != [expected]:
        raise RuntimeError('saved single destination path differs')
    mesh = eal.load_asset(expected)
    observed = _inspect_bound(mesh, item, shared)
    references = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            if component.get_editor_property('static_mesh') == mesh:
                references.append(actor.get_path_name())
    if references:
        raise RuntimeError('asset-only intake unexpectedly referenced by world actors')
    return {'preflight': guard, 'observed': observed, 'world_references': references,
            'world_placed': 0, 'world_saved': False, 'shared_material_modified': False}


def steps(cfg):
    journal = Path(cfg['journal'])
    if journal.exists():
        raise RuntimeError('retained native journal exists; inspect, never replay')
    admission = preflight(cfg)
    shared, item = _shared(cfg), _item(cfg)
    report = {
        'schema': 'daedalus.codex-qualified-one-static-native.v1',
        'stage': 'one_static_admitted', 'initial_preflight': admission,
        'requested_options': {'backend': 'explicit_InterchangePipelineStackOverride',
            'build_scale3d': [1., 1., 1.], 'vertex_colors': 'REPLACE', 'bake_meshes': True,
            'build_nanite': False, 'generate_lightmap_u_vs': False, 'collision': False,
            'import_materials': False, 'replace_existing': False, 'task_save': False},
        'unexposed_options': 'Animation/texture flags not explicitly set; exact one static output required',
        'unit_contract': shared['UNIT_CONTRACT'], 'required_future_actor_scale': [.01, .01, .01],
        'world_placed': 0, 'world_saved': False, 'shared_material_modified': False,
        'completed_count': 0, 'items': [], 'save_return': None,
        'limits': 'Saved static asset only; source family sheet is not native visual, motion, collision or ecosystem acceptance.',
    }
    with journal.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    row = {'name': NAME, 'source': item, 'stage': 'import_dispatch_pending', 'save_return': None}
    report['items'].append(row)
    try:
        shared['_deadline'](cfg)
        shared['_preflight']()
        _item(cfg)
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = item['fbx'], DESTINATION, NAME
        task.automated, task.replace_existing, task.save = True, False, False
        task.options = shared['_pipeline']()
        report['stage'] = 'item_import_dispatch_pending'
        _write(journal, report)
        started = time.perf_counter()
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        row.update(stage='import_returned', import_s=round(time.perf_counter() - started, 6),
                   imported_object_paths=[str(p) for p in task.imported_object_paths])
        report['stage'] = 'item_import_returned'
        _write(journal, report)
        eal = unreal.EditorAssetLibrary
        expected = DESTINATION + '/' + NAME + '.' + NAME
        row['destination_asset_paths'] = [str(p) for p in eal.list_assets(DESTINATION, recursive=True, include_folder=False)]
        if row['destination_asset_paths'] != [expected] or row['imported_object_paths'] != [expected]:
            raise RuntimeError('exact one returned mesh path required; preserve partial import')
        mesh = eal.load_asset(expected)
        row['observed_before_binding'] = shared['inspect_mesh'](mesh, item)
        row['native_path'] = mesh.get_path_name()
        _write(journal, report)
        shared['_deadline'](cfg)
        shared['_preflight'](allowed_dirty=(expected.split('.')[0],))
        mesh.modify()
        mesh.set_material(0, eal.load_asset(shared['MATERIAL']))
        for key, value in _metadata(item, shared).items():
            eal.set_metadata_tag(mesh, key, value)
        row.update(observed=_inspect_bound(mesh, item, shared), stage='save_dispatch_pending')
        report['stage'] = 'item_save_dispatch_pending'
        _write(journal, report)
        shared['_deadline'](cfg)
        shared['_preflight'](allowed_dirty=(expected.split('.')[0],))
        started = time.perf_counter()
        row['save_return'] = bool(eal.save_loaded_asset(mesh, only_if_is_dirty=False))
        row['save_s'] = round(time.perf_counter() - started, 6)
        row['stage'] = 'asset_saved_world_held' if row['save_return'] else 'save_returned_false'
        report['stage'] = 'item_save_returned'
        _write(journal, report)
        if row['save_return'] is not True:
            raise RuntimeError('owned new asset save returned false')
        report['completed_count'] = 1
        _write(journal, report)
        yield row['native_path']
        row['post_save_preflight'] = shared['_preflight']()
        report.update(stage='one_asset_saved_world_held', save_return=True)
        _write(journal, report)
        return report
    except Exception as exc:
        if isinstance(exc, shared['NativeContractError']):
            row['failed_observation'] = exc.observed
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__,
                      error=str(exc), replay_permitted=False)
        _write(journal, report)
        raise
