# SPDX-License-Identifier: MIT
"""Exact Copperfall plinth/heartstone GLB intake, assets only.

Reuse the pinned Sunspool asset inventory/journal helpers, Miri raw-PBR
inspection and catalogue ownership/queue/deadline guards in private namespaces.
The translated source roots must be observed baked into absolute XZY centimetre
vertices before the first save. No actor, map, shared material or setting edits.
Retained dispatch/journal files forbid mutation replay, including partial saves.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import time

import unreal

LABEL = 'Codex Copperfall R1 plinth heartstone GLB asset-only import-save'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/CopperfallR1_PlinthHeartstone_3a0a9b8a36b8dbf9'
MANIFEST = {'bytes': 14534, 'sha256': 'cb5ccb733998526308121ebae4c973e4f0ccc8aa4c79130c6d842537b9fc43f9'}
PAYLOAD = {'bytes': 18732, 'sha256': '3a0a9b8a36b8dbf9199f78b9110a8e70742759b61f89b13b49354f43afdfd142'}
SUNSPOOL = {'bytes': 19965, 'sha256': 'b571284f8d7b13fb1b135072c7f438e4ae036711d3b0bab053dc751844f2e047'}
MIRI = {'bytes': 25647, 'sha256': '5a434e398dcaafc0cb5f66d399aca372f322dcd51a29bf7c3687e78fed05c059'}
CATALOGUE = {'bytes': 22414, 'sha256': '00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03'}
ROLES = {'CAR_Overlook_Stone_Plinth': (156, 'CAR_rock_light', 'Cylinder'),
         'CAR_Heartstone_Copper_Base': (116, 'CAR_copper', 'Cylinder.001'),
         'CAR_Heartstone': (20, 'CAR_heartstone', 'Icosphere.020')}
UNIT_CONTRACT = 'gltf_authored_root_world_XZY_cm100_baked_build1_future_actor1_v1'


class ContractError(RuntimeError):
    def __init__(self, message, observed):
        super().__init__(message)
        self.observed = observed


def _pin(path, expected):
    raw = Path(path).read_bytes()
    if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != expected:
        raise RuntimeError('exact Copperfall source/helper fingerprint differs: ' + str(path))
    return raw


def _utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _config(cfg):
    scope = {}
    for key, expected in (('manifest', MANIFEST), ('glb', PAYLOAD),
                          ('sunspool_source', SUNSPOOL), ('miri_source', MIRI),
                          ('catalogue_source', CATALOGUE)):
        if cfg[key + '_fingerprint'] != expected:
            raise ValueError('exact reviewed Copperfall pin required: ' + key)
        raw = _pin(cfg[key], expected)
        if key.endswith('_source'):
            private = {'__name__': '_codex_copperfall_private_' + key}
            exec(compile(raw, cfg[key], 'exec'), private)
            private.update(LABEL=LABEL, ROOT=ROOT, ROLES=ROLES)
            scope[key] = private
    if cfg['destination'] != ROOT or Path(cfg['glb']).suffix.lower() != '.glb':
        raise ValueError('exact fresh owned Copperfall destination and GLB required')
    if (type(cfg['deadline_epoch']) not in (float, int)
            or not math.isfinite(cfg['deadline_epoch'])):
        raise ValueError('finite current operator deadline required')
    packet = json.loads(Path(cfg['manifest']).read_text(encoding='utf-8'))
    nodes = packet['geometry_and_raw_materials']['nodes']
    if (packet['stage'] != 'EXPORTED_INDEPENDENTLY_FILE_VERIFIED_NATIVE_PROFILE_PENDING'
            or packet['original_creator'] != 'production_checkpoint_evidence'
            or packet['source_delivery_owner'] != 'pootscoot'
            or packet['seed'] != 842401 or packet['realm'] != 'WORLD-ZERO'
            or packet['publication']['commit'] != 'b4bc16d330308b1849abf9303e732b10c5773936'
            or len(nodes) != 3 or {node['name'] for node in nodes} != set(ROLES)
            or any(node['triangles'] != ROLES[node['name']][0]
                   or node['mesh_name'] != ROLES[node['name']][2]
                   or node['source_material_slots'] != 1
                   or len(node['materials']) != 1
                   or node['materials'][0]['name'] != ROLES[node['name']][1]
                   or node['transform']['rotation'] != [0, 0, 0, 1]
                   or node['transform']['scale'] != [1, 1, 1]
                   for node in nodes)):
        raise ValueError('exact reviewed translated three-role Copperfall contract required')
    raw = _pin(cfg['glb'], PAYLOAD)
    magic, version, length = struct.unpack_from('<4sII', raw)
    size, kind = struct.unpack_from('<I4s', raw, 12)
    gltf = json.loads(raw[20:20 + size])
    if (magic != b'glTF' or version != 2 or length != len(raw) or kind != b'JSON'
            or len(gltf.get('nodes', [])) != 3 or len(gltf.get('meshes', [])) != 3
            or len(gltf.get('materials', [])) != 3
            or gltf['scenes'][gltf.get('scene', 0)]['nodes'] != [0, 1, 2]
            or len(gltf.get('buffers', [])) != 1 or gltf['buffers'][0].get('uri')
            or gltf['buffers'][0]['byteLength'] != 14488
            or any(gltf.get(key) for key in ('images', 'textures', 'animations', 'skins',
                                            'cameras', 'extensionsUsed', 'extensionsRequired'))
            or any(node.get('children') for node in gltf['nodes'])):
        raise ValueError('only exact embedded three-root static GLB may be dispatched')
    return packet, nodes, scope['sunspool_source'], scope['miri_source'], scope['catalogue_source']


def _tags(cfg, role):
    return {'codex_owner': 'codex-contest', 'codex_author': 'production_checkpoint_evidence',
            'codex_delivery_owner': 'pootscoot', 'codex_source_glb': str(cfg['glb']),
            'codex_sha256': PAYLOAD['sha256'], 'codex_reviewed_packet_sha256': MANIFEST['sha256'],
            'codex_source_role': role,
            'codex_source_provenance': 'Copperfall Ark Rest retained baseline subset r1; creator production_checkpoint_evidence; delivery pootscoot; WORLD-ZERO; seed842401; PR166 b4bc16d330308b1849abf9303e732b10c5773936; hub32221',
            'codex_unit_contract': UNIT_CONTRACT, 'codex_required_actor_scale': '1,1,1',
            'codex_pivot_contract': 'authored root translations baked into absolute mesh vertices; do not recenter or apply translation again',
            'codex_material_contract': 'unchanged raw linear glTF PBR and emissive factors; emissiveStrength default1; OPAQUE/doubleSided; no palette/gamma substitution',
            'codex_world_placement': 'held; asset-only save; appearance/collision/navigation/gameplay unverified'}


def _geometry(mesh, source):
    """Established GeometryScript inspection, reporting observations on failure."""
    expected = {edge: [source['world_bounds'][edge][axis] * 100 for axis in (0, 2, 1)]
                for edge in ('min', 'max')}
    local = {edge: [source['local_bounds'][edge][axis] * 100 for axis in (0, 2, 1)]
             for edge in ('min', 'max')}
    report = {'expected_absolute_world_bounds_cm': expected, 'unbaked_local_bounds_cm': local,
              'source_root_transform': source['transform'], 'tolerance_cm': .2, 'issues': []}
    options = unreal.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('use_build_scale', True)
    copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, unreal.DynamicMesh(), options, unreal.GeometryScriptMeshReadLOD())
    dynamic = copied[0] if isinstance(copied, tuple) else copied
    triangles = int(dynamic.get_triangle_count())
    points = []
    for triangle in range(triangles):
        valid, *vertices = dynamic.get_triangle_positions(triangle)
        if not valid or len(vertices) != 3:
            raise ContractError('native triangle positions unavailable', report)
        points.extend([[float(getattr(vertex, axis)) for axis in ('x', 'y', 'z')] for vertex in vertices])
    if not points:
        raise ContractError('native mesh has no readable vertices', report)
    direct = {'min': [min(p[i] for p in points) for i in range(3)],
              'max': [max(p[i] for p in points) for i in range(3)]}
    box = mesh.get_bounding_box()
    render = {edge: [float(getattr(getattr(box, edge), axis)) for axis in ('x', 'y', 'z')]
              for edge in ('min', 'max')}
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    build = subsystem.get_lod_build_settings(mesh, 0)
    scale = [float(getattr(build.build_scale3d, axis)) for axis in ('x', 'y', 'z')]
    import_data = mesh.get_editor_property('asset_import_data')
    report.update(triangles=triangles, native_source_bounds_cm=direct, render_bounds_cm=render,
                  build_scale3d=scale,
                  copy_outcome=str(copied[-1]) if isinstance(copied, tuple) else 'not_returned',
                  import_data_class=import_data.get_class().get_name() if import_data else None,
                  nanite_enabled=bool(mesh.get_editor_property('nanite_settings').enabled),
                  generate_lightmap_u_vs=bool(build.generate_lightmap_u_vs),
                  simple_collision_count=subsystem.get_simple_collision_count(mesh))
    if triangles != source['triangles']:
        report['issues'].append('exact referenced source triangle count differs')
    if scale != [1., 1., 1.] or any(not math.isfinite(value) for point in points for value in point):
        report['issues'].append('finite source vertices and unchanged build scale1 required')
    if any(not math.isfinite(bounds[edge][i]) or abs(bounds[edge][i] - expected[edge][i]) > .2
           for bounds in (direct, render) for edge in ('min', 'max') for i in range(3)):
        report['issues'].append('absolute translated world XZY cm100 bounds differ; no automatic unit/pivot repair')
    if report['nanite_enabled'] or report['generate_lightmap_u_vs']:
        report['issues'].append('bounded accepted profile requires observed Nanite/lightmap generation false')
    if report['import_data_class'] != 'InterchangeAssetImportData':
        report['issues'].append('actual Interchange import-data class not observed')
    report['observed_authored_translation_baked'] = not report['issues']
    report['backend_flags'] = 'not exposed or assumed; actual class, names and baked bounds are read back'
    return report


def _material(material, source, miri, helper):
    report = miri['_material'](material, source)
    factor = source.get('emissiveFactor', [0., 0., 0.])
    strength = source.get('extensions', {}).get('KHR_materials_emissive_strength', {}).get('emissiveStrength', 1.)
    for semantic, table, wanted in (('EmissiveFactor', report['vectors'], factor),
                                     ('EmissiveStrength', report['scalars'], strength)):
        candidates = {key: value for key, value in table.items()
                      if helper['_normal'](key) == helper['_normal'](semantic)}
        matching = []
        for key, value in candidates.items():
            if isinstance(wanted, list):
                valid = (isinstance(value, list) and len(value) == 4
                         and all(math.isfinite(v) for v in value)
                         and all(abs(value[i] - wanted[i]) <= .0001 for i in range(3)))
            else:
                valid = math.isfinite(value) and abs(value - wanted) <= .0001
            if valid:
                matching.append(key)
        report['matches'][semantic] = {'source_value': wanted, 'candidates': candidates,
                                       'matching_parameters': matching, 'parameter_presence_required': True}
        if len(candidates) != 1 or len(matching) != 1:
            report['readback_errors'].append('missing, ambiguous or differing explicit named native ' + semantic)
    return report


def _inspect(cfg, nodes, helper, miri, metadata=False):
    objects = helper['_assets']()
    report = {'assets': [{'path': path, 'class': obj.get_class().get_name()} for path, obj in objects.items()],
              'items': [], 'issues': [], 'triangles': 0, 'unit_contract': UNIT_CONTRACT,
              'required_future_actor_scale': [1., 1., 1.], 'world_placed': 0, 'world_saved': False,
              'provenance_metadata_verified': bool(metadata),
              'source_payload_sha256': PAYLOAD['sha256'], 'handoff_sha256': MANIFEST['sha256'],
              'mesh_bindings_changed': False, 'shared_material_modified': False,
              'name_mapping_scope': 'actual unique node-or-mesh suffix plus exact per-role triangles, absolute baked bounds, material and metadata',
              'limits': 'Symmetric bounds do not prove handedness; native visual, collision, navigation and runtime acceptance remain separate.'}
    meshes = [obj for obj in objects.values() if isinstance(obj, unreal.StaticMesh)]
    materials = [obj for obj in objects.values() if isinstance(obj, unreal.MaterialInstanceConstant)]
    if len(objects) != 6 or len(meshes) != 3 or len(materials) != 3:
        raise ContractError('exactly three owned StaticMeshes and three owned MICs required; preserve unexpected outputs', report)
    used = set()
    for source in nodes:
        role, material_name = source['name'], ROLES[source['name']][1]
        candidates = [obj for obj in meshes if any(helper['_normal'](obj.get_name()).endswith(helper['_normal'](name))
                                                   for name in (role, source['mesh_name']))]
        if len(candidates) != 1 or candidates[0].get_path_name() in used:
            raise ContractError('unambiguous observed node-or-mesh role identity required: ' + role, report)
        mesh = candidates[0]
        slots = list(mesh.get_editor_property('static_materials'))
        material = mesh.get_material(0) if len(slots) == 1 else None
        if (not isinstance(material, unreal.MaterialInstanceConstant)
                or material.get_path_name() not in objects or material.get_path_name() in used
                or not helper['_normal'](material.get_name()).endswith(helper['_normal'](material_name))):
            raise ContractError('one-to-one unchanged owned raw material binding required: ' + role, report)
        used.update((mesh.get_path_name(), material.get_path_name()))
        geometry = _geometry(mesh, source)
        physical = _material(material, source['materials'][0]['definition'], miri, helper)
        row = {'source_role': role, 'source_mesh_name': source['mesh_name'], 'path': mesh.get_path_name(),
               'class': mesh.get_class().get_name(), 'actual_sanitized_name': mesh.get_name(),
               'material_path': material.get_path_name(), 'source_material': material_name,
               'geometry': geometry, 'material': physical}
        report['items'].append(row)
        report['triangles'] += geometry['triangles']
        report['issues'].extend(role + ': ' + issue for issue in geometry['issues'] + physical['readback_errors'])
        if metadata:
            for obj, source_name in ((mesh, role), (material, material_name)):
                observed = {key: unreal.EditorAssetLibrary.get_metadata_tag(obj, key) for key in _tags(cfg, source_name)}
                if observed != _tags(cfg, source_name):
                    report['issues'].append('exact source provenance metadata differs: ' + obj.get_path_name())
    if used != set(objects) or report['triangles'] != 292:
        report['issues'].append('every exact owned object and all292 source triangles must be accounted')
    if report['issues']:
        raise ContractError('Copperfall native contract differs; preserve unsaved/partial outputs', report)
    return report, objects


def preflight(cfg):
    packet, nodes, helper, miri, guard = _config(cfg)
    guard['_deadline'](cfg)
    initial = guard['_preflight']()
    journal = Path(cfg['journal'])
    protected = {Path(cfg[key]).resolve() for key in ('manifest', 'glb', 'sunspool_source', 'miri_source', 'catalogue_source')}
    if (not journal.is_absolute() or journal.suffix.lower() != '.json' or not journal.parent.is_dir()
            or journal.exists() or journal.with_name(journal.name + '.write-pending').exists()
            or journal.resolve() in protected):
        raise RuntimeError('new absolute owned journal required; retained outcome forbids mutation replay')
    return {'guard': initial, 'destination': ROOT, **helper['_absent'](), 'manifest': MANIFEST, 'payload': PAYLOAD,
            'original_creator': packet['original_creator'], 'delivery_owner': packet['source_delivery_owner'],
            'requested_static_meshes': 3, 'requested_owned_mics': 3, 'total_triangles': 292,
            'helpers': {'sunspool': SUNSPOOL, 'miri': MIRI, 'catalogue': CATALOGUE},
            'requested_options': {'backend': 'existing_AssetImportTask_auto_glTF', 'options_override': None,
                                  'replace_existing': False, 'task_save': False},
            'unexposed_options': 'No assumed Interchange bake/naming flags; require actual absolute root-world vertices and raw linear PBR/emission before first save'}


def readback(cfg):
    packet, nodes, helper, miri, guard = _config(cfg)
    guard['_deadline'](cfg)
    initial = guard['_preflight']()
    report, objects = _inspect(cfg, nodes, helper, miri, metadata=True)
    report.update(preflight=initial, post_read_preflight=guard['_preflight'](),
                  persistent_assets_modified=False, saved_state='host must independently witness all six saved package bytes')
    return report


def steps(cfg):
    admission = preflight(cfg)
    packet, nodes, helper, miri, guard = _config(cfg)
    journal = Path(cfg['journal'])
    report = {'schema': 'daedalus.codex-copperfall-subset-native.v1', 'utc': _utc(),
              'stage': 'import_dispatch_pending', 'initial_preflight': admission, 'destination': ROOT,
              'outputs': [], 'items': [], 'completed_count': 0, 'save_return': None,
              'mutation_intents': [{'operation': 'import_exact_reviewed_glb', 'utc': _utc(), 'destination': ROOT}],
              'world_placed': 0, 'world_saved': False, 'mesh_bindings_changed': False,
              'shared_material_modified': False, 'replay_permitted': False}
    with journal.open('x', encoding='utf-8', newline='\n') as output:
        helper['_flush'](output, report)
    try:
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(cfg['glb']), ROOT
        task.destination_name = 'Copperfall_R1_PlinthHeartstone'
        task.automated, task.replace_existing, task.save = True, False, False
        task.options = None
        guard['_deadline'](cfg); guard['_preflight'](); _config(cfg); helper['_absent']()
        started = time.perf_counter()
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        report.update(stage='import_returned', import_s=round(time.perf_counter() - started, 6),
                      imported_object_paths=[str(path) for path in task.imported_object_paths])
        helper['_write'](journal, report)
        observed, objects = _inspect(cfg, nodes, helper, miri)
        report.update(observed_before_first_save=observed, items=observed['items'])
        helper['_write'](journal, report)
        actual = set(report['imported_object_paths'])
        if len(report['imported_object_paths']) != 6 or actual != set(objects):
            raise ContractError('returned import paths differ from exact six owned registry outputs', observed)
        allowed_dirty = [path.split('.')[0] for path in objects]
        roles = {row['path']: row['source_role'] for row in observed['items']}
        roles.update({row['material_path']: row['source_material'] for row in observed['items']})
        for path, obj in sorted(objects.items()):
            guard['_deadline'](cfg); guard['_preflight'](allowed_dirty)
            report['stage'] = 'owned_metadata_dispatch_pending'
            report['mutation_intents'].append({'operation': 'set_owned_source_metadata', 'utc': _utc(), 'path': path})
            helper['_write'](journal, report)
            for key, value in _tags(cfg, roles[path]).items():
                unreal.EditorAssetLibrary.set_metadata_tag(obj, key, value)
        report['observed_after_metadata_before_first_save'], objects = _inspect(cfg, nodes, helper, miri, metadata=True)
        helper['_write'](journal, report)
        for path, obj in sorted(objects.items()):
            guard['_deadline'](cfg); guard['_preflight'](allowed_dirty)
            row = {'path': path, 'class': obj.get_class().get_name(), 'save_return': None,
                   'save_s': None, 'stage': 'save_dispatch_pending'}
            report['outputs'].append(row)
            report['stage'] = 'owned_save_dispatch_pending'
            report['mutation_intents'].append({'operation': 'save_exact_owned_asset', 'utc': _utc(), 'path': path})
            helper['_write'](journal, report)
            started = time.perf_counter()
            row['save_return'] = bool(unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False))
            row['save_s'] = round(time.perf_counter() - started, 6)
            row['stage'] = 'asset_saved' if row['save_return'] else 'save_returned_false'
            if row['save_return']:
                report['completed_count'] += 1
            report.update(stage='owned_save_returned', save_return=True if report['completed_count'] == 6 else None)
            helper['_write'](journal, report)
            if row['save_return'] is not True:
                raise RuntimeError('owned asset save returned false: ' + path)
            yield path
        guard['_deadline'](cfg)
        report['final_preflight'] = guard['_preflight']()
        report['observed_after_saves'], objects = _inspect(cfg, nodes, helper, miri, metadata=True)
        report.update(stage='copperfall_subset_assets_saved_world_held', save_return=True)
        helper['_write'](journal, report)
        return report
    except Exception as exc:
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__, error=str(exc), failure_utc=_utc())
        if hasattr(exc, 'observed'):
            report['failed_contract_observation'] = exc.observed
        if not journal.with_name(journal.name + '.write-pending').exists():
            helper['_write'](journal, report)
        raise
