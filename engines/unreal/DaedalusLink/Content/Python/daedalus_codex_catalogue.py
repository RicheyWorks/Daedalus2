# SPDX-License-Identifier: MIT
"""Import and save three retained static eggs, without placing world actors.

This uses the existing explicit Interchange AssetImportTask contract. Raw unit100
geometry remains at build scale1; future actors MUST use scale .01. The host
retains exact source/view witnesses, the operator lease and saved-map witnesses.
An existing journal is a stop condition, including after a partial result.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import unreal

LABEL = 'Codex retained static egg catalogue asset-only import-save'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/'
WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
MATERIAL = '/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour'
UNIT_CONTRACT = 'claude_raw_unit100_build1_actor001_v1'
METADATA_KEYS = (
    'codex_owner', 'codex_sha256', 'codex_source_fbx', 'codex_author',
    'codex_source_provenance', 'codex_unit_contract',
    'codex_required_actor_scale', 'codex_intended_dimensions_cm',
    'codex_world_placement',
)


class NativeContractError(RuntimeError):
    """Carry observed data into the retained journal when a contract fails."""

    def __init__(self, message, observed):
        super().__init__(message)
        self.observed = observed


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def _deadline(cfg):
    if time.time() > cfg['deadline_epoch'] - 90:
        raise RuntimeError('operator lease deadline reached; preserve partial delivery')


def _preflight(allowed_dirty=()):
    bridge = sys.modules.get('claude_unreal_bridge')
    if bridge is None or not all(hasattr(bridge, key) for key in
                                 ('_jobs', '_running', '_job_boxes', '_remote_lock')):
        raise RuntimeError('existing bridge queue fields unavailable; no idle inference')
    running = list(bridge._running)
    own = [req for gen, req, box in running
           if req.get('type') == 'daedalus.steps'
           and (req.get('params') or {}).get('label') == LABEL]
    others = [req.get('type') for gen, req, box in running
              if req.get('type') != 'daedalus.steps'
              or (req.get('params') or {}).get('label') != LABEL]
    unfinished = sum(not box['done'].is_set()
                     for box, stamp in list(bridge._job_boxes.values()))
    if len(own) > 1 or others or bridge._jobs.qsize() or unfinished or bridge._remote_lock.locked():
        raise RuntimeError('conflicting/unfinished bridge operation; preserve work')
    maps = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    content = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    if maps or not set(content).issubset(set(allowed_dirty)):
        raise RuntimeError('unexpected dirty packages; preserve work')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_path_name() != WORLD:
        raise RuntimeError('agreed editor map required')
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE running')
    return {'dirty_map_packages': maps, 'dirty_content_packages': content,
            'other_running_generators': others, 'queued_jobs': bridge._jobs.qsize(),
            'unfinished_async_job_boxes': unfinished, 'pie_running': False,
            'editor_world': world.get_path_name(), 'remote_execution_lock_locked': False,
            'background_compilation': 'not_queried', 'epic_mcp_other_sessions': 'not_queried'}


def _validate_items(items):
    if not isinstance(items, list) or len(items) != 3:
        raise ValueError('exactly three qualified retained static egg entries required')
    names, destinations = set(), set()
    for item in items:
        name, destination = item['name'], item['destination']
        if (not name.startswith('Prop_Egg_') or not name.replace('_', '').isalnum()
                or name in names):
            raise ValueError('three distinct static egg names required')
        if (not destination.startswith(ROOT) or destination.endswith('/')
                or '..' in destination or '//' in destination or '.' in destination
                or destination in destinations):
            raise ValueError('distinct new destinations in owned namespace required')
        if any(destination.startswith(old + '/') or old.startswith(destination + '/')
               for old in destinations):
            raise ValueError('nested delivery destinations are not allowed')
        names.add(name)
        destinations.add(destination)
        fingerprint = item['fingerprint']
        raw = Path(item['fbx']).read_bytes()
        if (len(raw) != fingerprint['bytes']
                or hashlib.sha256(raw).hexdigest() != fingerprint['sha256']):
            raise ValueError('retained FBX fingerprint differs: ' + name)
        if Path(item['fbx']).suffix.lower() != '.fbx':
            raise ValueError('retained FBX required: ' + name)
        if type(item['triangles']) is not int or item['triangles'] <= 0:
            raise ValueError('positive source triangle count required: ' + name)
        palette = item['rgba_bytes']
        if (not palette or any(len(row) != 4 or any(type(v) is not int or not 0 <= v <= 255
                                                   for v in row) for row in palette)):
            raise ValueError('source RGBA-byte palette required: ' + name)
        bounds = item['source_bounds']
        if any(len(bounds[edge]) != 3 or any(not math.isfinite(v) for v in bounds[edge])
               for edge in ('min', 'max')):
            raise ValueError('finite three-axis source bounds required: ' + name)
        dims = [bounds['max'][i] - bounds['min'][i] for i in range(3)]
        if any(abs(a - b) > .001 for a, b in zip(dims, (90., 90., 100.))):
            raise ValueError('qualified 90x90x100cm source envelope required: ' + name)
        if abs(bounds['min'][2]) > .001:
            raise ValueError('source bottom pivot required: ' + name)


def _metadata(item):
    provenance = item.get('provenance', {
        'recipe': 'retained Claude catalogue recipe/current producer',
        'sidecar': item.get('sidecar'), 'historical_author': 'unverified'})
    if not isinstance(provenance, str):
        provenance = json.dumps(provenance, sort_keys=True)
    return {
        'codex_owner': 'codex-contest',
        'codex_sha256': item['fingerprint']['sha256'],
        'codex_source_fbx': str(item['fbx']),
        'codex_author': 'historical author unverified; retained Claude catalogue recipe/current producer',
        'codex_source_provenance': provenance,
        'codex_unit_contract': UNIT_CONTRACT,
        'codex_required_actor_scale': '0.01,0.01,0.01',
        'codex_intended_dimensions_cm': '90,90,100',
        'codex_world_placement':
            'held; scale1 island helper incompatible; appearance/collision/game acceptance unverified',
    }


def _matching_axis_conversions(native_bounds, source_bounds):
    """Allow FBX XY permutation/reflection, never a translation or rescale.

    The source XY footprint is square but its bottom-centre pivot is offset:
    [-40, 50], rather than symmetric about zero. Retain those endpoints through
    the installed FBX axis convention, whose sign conversion is read back here.
    Source Z must stay bottom-up and the unit multiplier is exactly100.
    """
    matches = []
    for axes in ((0, 1), (1, 0)):
        for sign_x in (1, -1):
            for sign_y in (1, -1):
                signs = (sign_x, sign_y)
                expected = {'min': [], 'max': []}
                for native_axis in range(2):
                    source_axis, sign = axes[native_axis], signs[native_axis]
                    endpoints = [source_bounds[edge][source_axis] * 100 * sign
                                 for edge in ('min', 'max')]
                    expected['min'].append(min(endpoints))
                    expected['max'].append(max(endpoints))
                for edge in ('min', 'max'):
                    expected[edge].append(source_bounds[edge][2] * 100)
                if all(abs(native_bounds[edge][i] - expected[edge][i]) <= .1
                       for edge in ('min', 'max') for i in range(3)):
                    matches.append({'native_x_source_axis': 'xy'[axes[0]],
                                    'native_x_sign': sign_x,
                                    'native_y_source_axis': 'xy'[axes[1]],
                                    'native_y_sign': sign_y,
                                    'native_z_source_axis': 'z', 'native_z_sign': 1,
                                    'unit_multiplier': 100,
                                    'expected_native_bounds_cm': expected})
    return matches


def inspect_mesh(mesh, item):
    """Strict source/flag readback only; material/metadata are returned as observed.

    The transient DynamicMesh reads every source triangle with build scale. It
    never changes the imported mesh. Binding acceptance is checked by steps()
    after binding, and the host compares it again during saved-asset readback.
    """
    if not isinstance(mesh, unreal.StaticMesh) or mesh.get_name() != item['name']:
        raise NativeContractError('exact named StaticMesh required', {})
    box = mesh.get_bounding_box()
    bounds = {edge: [getattr(getattr(box, edge), a) for a in ('x', 'y', 'z')]
              for edge in ('min', 'max')}
    dims = [bounds['max'][i] - bounds['min'][i] for i in range(3)]
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    build = subsystem.get_lod_build_settings(mesh, 0)
    import_data = mesh.get_editor_property('asset_import_data')
    slots = mesh.get_editor_property('static_materials')
    report = {
        'native_path': mesh.get_path_name(),
        'native_class': mesh.get_class().get_name(),
        'native_bounds_cm': bounds, 'native_dimensions_cm': dims,
        'source_bounds': item['source_bounds'],
        'expected_native_bounds_cm': {
            edge: [value * 100 for value in item['source_bounds'][edge]]
            for edge in ('min', 'max')},
        'matching_fbx_axis_conversions': _matching_axis_conversions(bounds, item['source_bounds']),
        'axis_conversion_scope':
            'XY permutation/sign only, source Z unchanged, unit100; square XY cannot uniquely identify permutation',
        'projected_dimensions_cm_at_required_actor_scale': [v * .01 for v in dims],
        'required_future_actor_scale': [.01, .01, .01],
        'unit_contract': UNIT_CONTRACT,
        'import_data_class': import_data.get_class().get_name() if import_data else None,
        'observed_build_scale3d': [getattr(build.build_scale3d, a) for a in ('x', 'y', 'z')],
        'observed_generate_lightmap_u_vs': bool(build.generate_lightmap_u_vs),
        'nanite_enabled': bool(mesh.get_editor_property('nanite_settings').enabled),
        'simple_collision_count': subsystem.get_simple_collision_count(mesh),
        'slots': [{'slot': str(slot.material_slot_name),
                   'material': mesh.get_material(i).get_path_name() if mesh.get_material(i) else None}
                  for i, slot in enumerate(slots)],
        'metadata': {key: unreal.EditorAssetLibrary.get_metadata_tag(mesh, key)
                     for key in METADATA_KEYS},
        'persistent_mesh_modified': False,
        'native_appearance': 'unverified; source vertex readback is not a screenshot',
        'collision_game_acceptance': 'unverified; no authored UCX or gameplay run',
    }
    options = unreal.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('use_build_scale', True)
    dynamic = unreal.DynamicMesh()
    copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, dynamic, options, unreal.GeometryScriptMeshReadLOD())
    if isinstance(copied, tuple):
        dynamic = copied[0]
        report['source_copy_outcome'] = str(copied[-1])
    triangles = dynamic.get_triangle_count()
    report['triangles'] = triangles
    if triangles != item['triangles']:
        raise NativeContractError('native source triangle count differs', report)
    unique, points = set(), []
    for triangle in range(triangles):
        row = dynamic.get_triangle_vertex_colors(triangle)
        if len(row) != 5 or row[-1] is not True:
            raise NativeContractError('native triangle colour readback incomplete', report)
        colours = [tuple(round(getattr(c, key), 7) for key in ('r', 'g', 'b', 'a'))
                   for c in row[1:4]]
        if len(set(colours)) != 1:
            raise NativeContractError('source flat face colour changed', report)
        unique.update(colours)
        valid, *vertices = dynamic.get_triangle_positions(triangle)
        if not valid or len(vertices) != 3:
            raise NativeContractError('native source triangle positions incomplete', report)
        points.extend([[getattr(v, axis) for axis in ('x', 'y', 'z')] for v in vertices])
    direct = {tuple(round(v * 255) for v in colour) for colour in unique}
    report['vertex_colours'] = {
        'triangles': triangles, 'all_triangle_corners_valid': True,
        'all_triangle_faces_flat': True, 'unique_rgba': sorted(unique),
        'direct_rgba_bytes': sorted(direct),
        'expected_rgba_bytes': sorted({tuple(row) for row in item['rgba_bytes']}),
        'source_match': 'direct_rgba_bytes' if direct == {tuple(row) for row in item['rgba_bytes']} else None,
        'persistent_mesh_modified': False,
    }
    report['native_source_bounds_with_build_scale'] = {
        'min': [min(p[i] for p in points) for i in range(3)],
        'max': [max(p[i] for p in points) for i in range(3)],
    }
    issues = []
    if report['import_data_class'] != 'InterchangeAssetImportData':
        issues.append('actual importer is not the retained Interchange backend')
    if report['observed_build_scale3d'] != [1., 1., 1.]:
        issues.append('absolute build scale1 differs')
    if report['observed_generate_lightmap_u_vs'] or report['nanite_enabled']:
        issues.append('lightmap UV/Nanite flags differ')
    if report['simple_collision_count'] != 0:
        issues.append('unexpected generated simple collision')
    if len(slots) != 1:
        issues.append('one source material slot required')
    if report['vertex_colours']['source_match'] is None:
        issues.append('direct source RGBA-byte palette differs')
    if not report['matching_fbx_axis_conversions']:
        issues.append('raw native unit100 bounds differ')
    if any(abs(report['native_source_bounds_with_build_scale'][edge][i] - bounds[edge][i]) > .1
           for edge in ('min', 'max') for i in range(3)):
        issues.append('source with build scale and render bounds differ')
    report['issues'] = issues
    if issues:
        raise NativeContractError('; '.join(issues), report)
    return report


def _pipeline():
    pipeline = unreal.InterchangeGenericAssetsPipeline()
    options = pipeline.get_editor_property('mesh_pipeline')
    for key, value in {'build_nanite': False, 'generate_lightmap_u_vs': False,
                       'collision': False, 'build_scale3d': unreal.Vector(1, 1, 1)}.items():
        options.set_editor_property(key, value)
    common = pipeline.get_editor_property('common_meshes_properties')
    common.set_editor_property('vertex_color_import_option',
                              unreal.InterchangeVertexColorImportOption.IVCIO_REPLACE)
    common.set_editor_property('bake_meshes', True)
    pipeline.get_editor_property('material_pipeline').set_editor_property('import_materials', False)
    stack = unreal.InterchangePipelineStackOverride()
    stack.add_pipeline(pipeline)
    return stack


def steps(cfg):
    journal = Path(cfg['journal'])
    if journal.exists():
        raise RuntimeError('retained native journal exists; inspect, never replay')
    items = cfg['items']
    _validate_items(items)
    _deadline(cfg)
    initial = _preflight()
    eal = unreal.EditorAssetLibrary
    names = {item['name'] for item in items}
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    existing = [str(data.package_name) + '.' + str(data.asset_name)
                for data in registry.get_assets_by_path('/Game', recursive=True)
                if str(data.asset_name) in names]
    if existing:
        raise RuntimeError('selected names already exist in /Game; no replay or duplicate: ' + repr(existing))
    for item in items:
        if (eal.does_directory_exist(item['destination'])
                or eal.does_asset_exist(item['destination'] + '/' + item['name'])):
            raise RuntimeError('selected destination exists; no overwrite: ' + item['destination'])
    material = eal.load_asset(MATERIAL)
    if not isinstance(material, unreal.MaterialInterface):
        raise RuntimeError('existing shared vertex-colour material missing')
    report = {
        'schema': 'daedalus.codex-retained-static-egg-catalogue-native.v1',
        'stage': 'all_three_admitted', 'initial_preflight': initial,
        'requested_options': {'backend': 'explicit_InterchangePipelineStackOverride',
            'build_scale3d': [1., 1., 1.], 'vertex_colors': 'REPLACE', 'bake_meshes': True,
            'build_nanite': False, 'generate_lightmap_u_vs': False, 'collision': False,
            'import_materials': False, 'replace_existing': False, 'task_save': False},
        'unit_contract': UNIT_CONTRACT, 'required_future_actor_scale': [.01, .01, .01],
        'world_placed': 0, 'world_saved': False, 'shared_material_modified': False,
        'completed_count': 0, 'items': [], 'save_return': None,
    }
    # Exclusive creation prevents a second invocation from replacing a retained
    # partial result. Every mutation below has a prior written dispatch stage.
    with journal.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    try:
        for item in items:
            _deadline(cfg)
            _preflight()
            raw = Path(item['fbx']).read_bytes()
            if (len(raw) != item['fingerprint']['bytes']
                    or hashlib.sha256(raw).hexdigest() != item['fingerprint']['sha256']):
                raise RuntimeError('retained FBX changed before dispatch: ' + item['name'])
            task = unreal.AssetImportTask()
            task.filename = item['fbx']
            task.destination_path = item['destination']
            task.destination_name = item['name']
            task.automated = True
            task.replace_existing = False
            task.save = False
            task.options = _pipeline()
            row = {'name': item['name'], 'source': item,
                   'stage': 'import_dispatch_pending', 'save_return': None, 'world_placed': 0}
            report['items'].append(row)
            report['stage'] = 'item_import_dispatch_pending'
            _write(journal, report)
            started = time.perf_counter()
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            row.update(stage='import_returned', import_s=round(time.perf_counter() - started, 6),
                       imported_object_paths=[str(p) for p in task.imported_object_paths])
            report['stage'] = 'item_import_returned'
            _write(journal, report)
            paths = list(eal.list_assets(item['destination'], recursive=True, include_folder=False))
            row['destination_asset_paths'] = [str(p) for p in paths]
            expected = item['destination'] + '/' + item['name'] + '.' + item['name']
            if len(paths) != 1 or row['imported_object_paths'] != [expected]:
                raise RuntimeError('exact one returned named mesh path required; inspect retained import')
            mesh = eal.load_asset(paths[0])
            if not isinstance(mesh, unreal.StaticMesh) or mesh.get_path_name() != expected:
                raise RuntimeError('exact one named StaticMesh required; inspect retained import')
            row['observed_before_binding'] = inspect_mesh(mesh, item)
            row['native_path'] = mesh.get_path_name()
            _write(journal, report)
            _deadline(cfg)
            _preflight(allowed_dirty=(expected.split('.')[0],))
            mesh.modify()
            mesh.set_material(0, material)
            tags = _metadata(item)
            for key, value in tags.items():
                eal.set_metadata_tag(mesh, key, value)
            observed = inspect_mesh(mesh, item)
            if (observed['slots'][0]['material'] != material.get_path_name()
                    or observed['metadata'] != tags):
                raise NativeContractError('owned mesh material/metadata binding differs', observed)
            row.update(observed=observed, native_path=mesh.get_path_name(), stage='save_dispatch_pending')
            report['stage'] = 'item_save_dispatch_pending'
            _write(journal, report)
            _deadline(cfg)
            _preflight(allowed_dirty=(expected.split('.')[0],))
            started = time.perf_counter()
            row['save_return'] = bool(eal.save_loaded_asset(mesh, only_if_is_dirty=False))
            row['save_s'] = round(time.perf_counter() - started, 6)
            row['stage'] = 'asset_saved_world_held' if row['save_return'] else 'save_returned_false'
            report['stage'] = 'item_save_returned'
            _write(journal, report)
            if row['save_return'] is not True:
                raise RuntimeError('owned mesh save returned false: ' + item['name'])
            report['completed_count'] += 1
            _write(journal, report)
            yield row['native_path']
            row['post_save_preflight'] = _preflight()
            _write(journal, report)
        report.update(stage='three_assets_saved_world_held', save_return=True)
        _write(journal, report)
        return report
    except Exception as exc:
        if isinstance(exc, NativeContractError) and report['items']:
            report['items'][-1]['failed_observation'] = exc.observed
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__,
                      error=str(exc), replay_permitted=False)
        _write(journal, report)
        raise
