# SPDX-License-Identifier: MIT
"""Exact Sunspool R4 three-role GLB intake; no actors, rebinding or map saves.

Use preflight(cfg), steps(cfg), readback(cfg) through daedalus.steps with LABEL.
The host supplies a new journal, fresh ownership/preservation witnesses and a
deadline. Retained journals/pending writes forbid replay, including partial saves.
Existing Miri PBR inspection and catalogue queue guards run in pinned private
namespaces; neither original module nor any shared material is modified.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

import unreal

LABEL = 'Codex Sunspool R4 three-role GLB asset-only import-save'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/SunspoolR4_ThreeRoles_abd4fefd3c7bdc2c'
MANIFEST = {'bytes': 19040, 'sha256': '1b23822be0488676588ebcd138fc0c3fd021de1d875bbb7f618d7db43a34a195'}
PAYLOAD = {'bytes': 33440, 'sha256': 'abd4fefd3c7bdc2cc312cb4d5428b0f3e82e61143e08afc0991639a7fd9dca97'}
MIRI = {'bytes': 25647, 'sha256': '5a434e398dcaafc0cb5f66d399aca372f322dcd51a29bf7c3687e78fed05c059'}
CATALOGUE = {'bytes': 22414, 'sha256': '00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03'}
ROLES = {'Bld_Sunspool_BronzeSunRim-0.4': (960, 'SS_bronze'),
         'Bld_Sunspool_DyeHouse_FabricBolt0': (108, 'SS_cloth'),
         'Bld_Sunspool_DyeHouse_FoldedTealRoof': (8, 'SS_roof')}
UNIT_CONTRACT = 'gltf_metres_XZY_to_unreal_cm100_build1_actor1_v1'


def _utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _pin(path, expected):
    raw = Path(path).read_bytes()
    actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if actual != expected:
        raise RuntimeError('exact retained source fingerprint differs: ' + str(path))
    return raw


def _flush(output, report):
    json.dump(report, output, indent=2, allow_nan=False)
    output.write('\n')
    output.flush()
    os.fsync(output.fileno())


def _write(path, report):
    path = Path(path)
    pending = path.with_name(path.name + '.write-pending')
    with pending.open('x', encoding='utf-8', newline='\n') as output:
        _flush(output, report)
    os.replace(pending, path)


def _config(cfg):
    for path_key, fp_key, expected in (('manifest', 'manifest_fingerprint', MANIFEST),
            ('glb', 'fingerprint', PAYLOAD), ('miri_source', 'miri_source_fingerprint', MIRI),
            ('catalogue_source', 'catalogue_source_fingerprint', CATALOGUE)):
        if cfg[fp_key] != expected:
            raise ValueError('exact reviewed fingerprint required: ' + fp_key)
        _pin(cfg[path_key], expected)
    if cfg['destination'] != ROOT or Path(cfg['glb']).suffix.lower() != '.glb':
        raise ValueError('exact fresh owned Sunspool destination and GLB required')
    deadline = cfg['deadline_epoch']
    if type(deadline) not in (float, int) or not math.isfinite(deadline):
        raise ValueError('finite operator deadline_epoch required')
    packet = json.loads(Path(cfg['manifest']).read_text(encoding='utf-8'))
    if (packet['source_owner'] != 'pootscoot' or packet['source_revision'] != 'r4'
            or packet['seed'] != 861503 or packet['mesh_count'] != 3 or packet['total_triangles'] != 1076
            or {row['name'] for row in packet['meshes']} != set(ROLES)):
        raise ValueError('exact reviewed three-role source packet required')
    scope = {}
    for key, expected in (('miri_source', MIRI), ('catalogue_source', CATALOGUE)):
        private = {'__name__': '_codex_sunspool_private_' + key}
        exec(compile(_pin(cfg[key], expected), cfg[key], 'exec'), private)
        private['LABEL'] = LABEL
        scope[key] = private
    return packet, scope['miri_source'], scope['catalogue_source']


def _normal(name):
    return ''.join(c.lower() for c in str(name) if c.isalnum())


def _assets():
    paths = {str(row.package_name) + '.' + str(row.asset_name)
             for row in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(ROOT, recursive=True)}
    paths.update(str(path) for path in unreal.EditorAssetLibrary.list_assets(ROOT, recursive=True, include_folder=False))
    objects = {}
    for path in sorted(paths):
        obj = unreal.EditorAssetLibrary.load_asset(path)
        if obj is None or not obj.get_path_name().startswith(ROOT + '/'):
            raise RuntimeError('owned output unresolved or outside exact namespace: ' + path)
        objects[obj.get_path_name()] = obj
    return objects


def _absent():
    names = set(ROLES) | {row[1] for row in ROLES.values()}
    collisions = [str(row.package_name) + '.' + str(row.asset_name)
                  for row in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game', recursive=True)
                  if any(_normal(row.asset_name).endswith(_normal(name)) for name in names)]
    if collisions or unreal.EditorAssetLibrary.does_directory_exist(ROOT) or _assets():
        raise RuntimeError('fresh destination/role names required; no overwrite: ' + repr(collisions))
    return {'destination_absent': True, 'global_role_name_collisions': collisions}


def _tags(cfg, role):
    return {'codex_owner': 'codex-contest', 'codex_author': 'pootscoot',
            'codex_source_glb': str(cfg['glb']), 'codex_sha256': PAYLOAD['sha256'],
            'codex_reviewed_packet_sha256': MANIFEST['sha256'], 'codex_source_role': role,
            'codex_source_provenance': 'Poot Scoot / Codex; Sunspool Refuge r4; WORLD-ZERO; seed861503; hub31847/31851/31856',
            'codex_unit_contract': UNIT_CONTRACT, 'codex_required_actor_scale': '1,1,1',
            'codex_material_contract': 'source linear PBR unchanged; OPAQUE/doubleSided; no palette gamma transfer',
            'codex_world_placement': 'held; asset-only save; appearance/collision/navigation/gameplay unverified'}


def _geometry(mesh, source):
    expected = {edge: [source['local_bounds_y_up_metres'][edge][axis] * 100 for axis in (0, 2, 1)]
                for edge in ('min', 'max')}
    options = unreal.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('use_build_scale', True)
    copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, unreal.DynamicMesh(), options, unreal.GeometryScriptMeshReadLOD())
    dynamic = copied[0] if isinstance(copied, tuple) else copied
    triangles = int(dynamic.get_triangle_count())
    if triangles != source['triangles']:
        raise RuntimeError('native source triangle count differs: ' + source['name'])
    points = []
    for triangle in range(triangles):
        valid, *vertices = dynamic.get_triangle_positions(triangle)
        if not valid or len(vertices) != 3:
            raise RuntimeError('native source positions unavailable')
        points.extend([[float(getattr(vertex, axis)) for axis in ('x', 'y', 'z')] for vertex in vertices])
    direct = {'min': [min(p[i] for p in points) for i in range(3)],
              'max': [max(p[i] for p in points) for i in range(3)]}
    box = mesh.get_bounding_box()
    render = {edge: [float(getattr(getattr(box, edge), axis)) for axis in ('x', 'y', 'z')]
              for edge in ('min', 'max')}
    build = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_lod_build_settings(mesh, 0)
    scale = [float(getattr(build.build_scale3d, axis)) for axis in ('x', 'y', 'z')]
    if scale != [1., 1., 1.] or any(not math.isfinite(bounds[edge][i])
            or abs(bounds[edge][i] - expected[edge][i]) > .2
            for bounds in (direct, render) for edge in ('min', 'max') for i in range(3)):
        raise RuntimeError('absolute plateau-relative XZY unit100/build1 bounds differ: ' + source['name'])
    import_data = mesh.get_editor_property('asset_import_data')
    return {'triangles': triangles, 'native_source_bounds_cm': direct, 'render_bounds_cm': render,
            'expected_bounds_cm': expected, 'build_scale3d': scale, 'tolerance_cm': .2,
            'copy_outcome': str(copied[-1]) if isinstance(copied, tuple) else 'not_returned',
            'import_data_class': import_data.get_class().get_name() if import_data else None,
            'nanite_enabled': bool(mesh.get_editor_property('nanite_settings').enabled),
            'generate_lightmap_u_vs': bool(build.generate_lightmap_u_vs),
            'simple_collision_count': unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_simple_collision_count(mesh)}


def _observed_role_paths(cfg):
    """Explicit saved-readback evidence may identify an importer-renamed role.

    This never relaxes geometry, material, object-count or provenance checks and
    is deliberately unavailable to first import. A spelling mismatch alone is
    insufficient evidence for accepting or renaming an object.
    """
    witness = cfg.get('observed_role_mapping')
    if witness is None:
        return None
    raw = _pin(witness['path'], {key: witness[key] for key in ('bytes', 'sha256')})
    saved = json.loads(raw)
    if (saved.get('stage') != 'sunspool_three_role_assets_saved_readback_complete'
            or saved.get('issues') != []):
        raise RuntimeError('completed exact saved-role witness required')
    rows = saved['native']['items']
    paths = {row['source_role']: row['path'] for row in rows}
    if (len(rows) != 3 or set(paths) != set(ROLES) or len(set(paths.values())) != 3
            or any(not path.startswith(ROOT + '/') for path in paths.values())):
        raise RuntimeError('saved-role witness must identify exactly three owned source roles')
    return paths


def _inspect(cfg, packet, miri, metadata=False):
    objects = _assets()
    meshes = [obj for obj in objects.values() if isinstance(obj, unreal.StaticMesh)]
    materials = [obj for obj in objects.values() if isinstance(obj, unreal.MaterialInstanceConstant)]
    if len(objects) != 6 or len(meshes) != 3 or len(materials) != 3:
        raise RuntimeError('require exactly three StaticMeshes and three owned MICs; preserve all unexpected outputs')
    source_materials = {row['name']: row['linear_PBR_record'] for row in packet['materials']}
    observed_paths = _observed_role_paths(cfg)
    used_meshes, used_materials, rows = set(), set(), []
    for source in packet['meshes']:
        candidates = [obj for obj in meshes if (
            obj.get_path_name() == observed_paths[source['name']] if observed_paths is not None
            else _normal(obj.get_name()).endswith(_normal(source['name'])))]
        if len(candidates) != 1:
            raise RuntimeError('unambiguous actual sanitized source role required: ' + source['name'])
        mesh = candidates[0]
        if mesh.get_path_name() in used_meshes:
            raise RuntimeError('duplicate native role mapping')
        used_meshes.add(mesh.get_path_name())
        material_name = ROLES[source['name']][1]
        slots = list(mesh.get_editor_property('static_materials'))
        material = mesh.get_material(0) if len(slots) == 1 else None
        if (not isinstance(material, unreal.MaterialInstanceConstant) or material.get_path_name() not in objects
                or not _normal(material.get_name()).endswith(_normal(material_name))
                or material.get_path_name() in used_materials):
            raise RuntimeError('one-to-one unchanged owned source MIC binding required: ' + source['name'])
        used_materials.add(material.get_path_name())
        physical = miri['_material'](material, source_materials[material_name])
        if physical['readback_errors']:
            raise RuntimeError('linear PBR/opaque/double-sided readback differs: ' + repr(physical))
        row = {'source_role': source['name'], 'path': mesh.get_path_name(), 'class': mesh.get_class().get_name(),
               'actual_sanitized_name': mesh.get_name(), 'material_path': material.get_path_name(),
               'source_material': material_name, 'geometry': _geometry(mesh, source), 'material': physical}
        if metadata:
            for obj, role in ((mesh, source['name']), (material, material_name)):
                observed = {key: unreal.EditorAssetLibrary.get_metadata_tag(obj, key) for key in _tags(cfg, role)}
                if observed != _tags(cfg, role):
                    raise RuntimeError('source provenance metadata differs: ' + obj.get_path_name())
        rows.append(row)
    if used_meshes | used_materials != set(objects):
        raise RuntimeError('output mapping did not account for every owned object')
    return {'items': rows, 'assets': [{'path': path, 'class': obj.get_class().get_name()} for path, obj in objects.items()],
            'triangles': sum(row['geometry']['triangles'] for row in rows), 'issues': [],
            'unit_contract': UNIT_CONTRACT, 'required_future_actor_scale': [1., 1., 1.],
            'name_mapping_scope': ('Explicit pinned saved-role witness' if observed_paths is not None else
                                   'Actual case/punctuation-normalized source suffix')
                                  + ' plus exact triangles, absolute bounds, owned material and provenance',
            'observed_role_mapping': cfg.get('observed_role_mapping'),
            'world_placed': 0, 'world_saved': False, 'mesh_bindings_changed': False,
            'shared_material_modified': False, 'appearance_collision_navigation_runtime': 'unverified'}, objects


def preflight(cfg):
    if cfg.get('observed_role_mapping') is not None:
        raise ValueError('saved-role mapping is readback-only; never authorizes another import')
    packet, miri, guard = _config(cfg)
    guard['_deadline'](cfg)
    initial = guard['_preflight']()
    journal = Path(cfg['journal'])
    protected = {Path(cfg[key]).resolve() for key in ('manifest', 'glb', 'miri_source', 'catalogue_source')}
    if (not journal.is_absolute() or journal.suffix.lower() != '.json' or not journal.parent.is_dir()
            or journal.exists() or journal.with_name(journal.name + '.write-pending').exists()
            or journal.resolve() in protected):
        raise RuntimeError('new absolute owned journal required; retained files forbid replay')
    return {'guard': initial, 'destination': ROOT, **_absent(), 'manifest': MANIFEST, 'payload': PAYLOAD,
            'source_owner': packet['source_owner'], 'requested_static_meshes': 3, 'requested_owned_mics': 3,
            'total_triangles': 1076, 'helpers': {'miri': MIRI, 'catalogue': CATALOGUE},
            'requested_options': {'backend': 'existing_cast_AssetImportTask_auto_glTF', 'options_override': None,
                                  'replace_existing': False, 'task_save': False},
            'unexposed_options': 'Default importer profile only; geometry, materials and all actual output classes must pass before any save'}


def readback(cfg):
    packet, miri, guard = _config(cfg)
    guard['_deadline'](cfg)
    initial = guard['_preflight']()
    report, objects = _inspect(cfg, packet, miri, metadata=True)
    report.update(preflight=initial, post_read_preflight=guard['_preflight'](),
                  persistent_assets_modified=False, saved_state='host must independently witness saved package bytes')
    return report


def steps(cfg):
    admission = preflight(cfg)
    packet, miri, guard = _config(cfg)
    journal = Path(cfg['journal'])
    report = {'schema': 'daedalus.codex-sunspool-subset-native.v1', 'utc': _utc(),
              'stage': 'import_dispatch_pending', 'initial_preflight': admission, 'destination': ROOT,
              'outputs': [], 'items': [], 'completed_count': 0, 'save_return': None,
              'mutation_intents': [{'operation': 'import_exact_reviewed_glb', 'utc': _utc(), 'destination': ROOT}],
              'world_placed': 0, 'world_saved': False, 'mesh_bindings_changed': False,
              'shared_material_modified': False, 'replay_permitted': False}
    with journal.open('x', encoding='utf-8', newline='\n') as output:
        _flush(output, report)
    try:
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(cfg['glb']), ROOT
        task.destination_name = 'Sunspool_R4_ThreeRoles'
        task.automated, task.replace_existing, task.save = True, False, False
        task.options = None
        guard['_deadline'](cfg)
        guard['_preflight']()
        _config(cfg)
        _absent()
        started = time.perf_counter()
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        report.update(stage='import_returned', import_s=round(time.perf_counter() - started, 6),
                      imported_object_paths=[str(path) for path in task.imported_object_paths])
        _write(journal, report)
        observed, objects = _inspect(cfg, packet, miri)
        report.update(observed_before_first_save=observed, items=observed['items'])
        _write(journal, report)
        actual = set(report['imported_object_paths'])
        mesh_paths = {row['path'] for row in observed['items']}
        if not mesh_paths.issubset(actual) or not actual.issubset(set(objects)):
            raise RuntimeError('returned import paths differ from exact owned registry outputs')
        allowed_dirty = [path.split('.')[0] for path in objects]
        guard['_deadline'](cfg)
        guard['_preflight'](allowed_dirty)
        role_by_path = {row['path']: row['source_role'] for row in observed['items']}
        role_by_path.update({row['material_path']: row['source_material'] for row in observed['items']})
        for path, obj in sorted(objects.items()):
            report.update(stage='owned_metadata_dispatch_pending')
            report['mutation_intents'].append({'operation': 'set_owned_source_metadata', 'utc': _utc(), 'path': path})
            _write(journal, report)
            guard['_deadline'](cfg)
            guard['_preflight'](allowed_dirty)
            for key, value in _tags(cfg, role_by_path[path]).items():
                unreal.EditorAssetLibrary.set_metadata_tag(obj, key, value)
        observed, objects = _inspect(cfg, packet, miri, metadata=True)
        report['observed_after_metadata_before_first_save'] = observed
        _write(journal, report)
        for path, obj in sorted(objects.items()):
            guard['_deadline'](cfg)
            guard['_preflight'](allowed_dirty)
            row = {'path': path, 'class': obj.get_class().get_name(), 'save_return': None,
                   'save_s': None, 'stage': 'save_dispatch_pending'}
            report['outputs'].append(row)
            report['stage'] = 'owned_save_dispatch_pending'
            report['mutation_intents'].append({'operation': 'save_exact_owned_asset', 'utc': _utc(), 'path': path})
            _write(journal, report)
            started = time.perf_counter()
            row['save_return'] = bool(unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False))
            row['save_s'] = round(time.perf_counter() - started, 6)
            row['stage'] = 'asset_saved' if row['save_return'] else 'save_returned_false'
            if row['save_return']:
                report['completed_count'] += 1
            report['stage'] = 'owned_save_returned'
            report['save_return'] = True if report['completed_count'] == 6 else None
            _write(journal, report)
            if row['save_return'] is not True:
                raise RuntimeError('owned asset save returned false: ' + path)
            yield path
        report['final_preflight'] = guard['_preflight']()
        report['observed_after_saves'], objects = _inspect(cfg, packet, miri, metadata=True)
        report.update(stage='sunspool_subset_assets_saved_world_held', save_return=True)
        _write(journal, report)
        return report
    except Exception as exc:
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__, error=str(exc), failure_utc=_utc())
        if not journal.with_name(journal.name + '.write-pending').exists():
            _write(journal, report)
        raise
