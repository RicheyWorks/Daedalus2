# SPDX-License-Identifier: MIT
"""Bounded, fresh-namespace Miri v2 skeletal GLB delivery.

Reuse the installed cast AssetImportTask route without an options override.
Inspect every owned output before its first save. An existing journal always
requires reconciliation; this entry point never replays or replaces an import.
No actors, world saves, material changes, playback or runtime claims are made.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import unreal

LABEL = 'Codex Miri v2 skeletal GLB asset-only import-save'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Characters/MiriV2_33b8c1a8a5a3bd51'
WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
SOURCE_SHA = '33b8c1a8a5a3bd513648faf56822b250b7b8254efb55f668031124c7f47d22bc'
CONTRACT_SHA = '11034938cec63a80123b46817aab485a66b603067adc23374efe657f87896d33'
PACKET_SHA = '900b0a42073a6adb23a2120c31d68f7d92f8952fa593241bad659b79fdaf4f44'
CLIPS = {'Miri_Idle': 2., 'Miri_LetterReaction': 1.5, 'Miri_Walk_InPlace': 1.}
UNIT_CONTRACT = 'gltf_metres_to_unreal_cm100_actor1_v1'


class NativeContractError(RuntimeError):
    def __init__(self, message, observed):
        super().__init__(message)
        self.observed = observed


def _write(path, report):
    Path(path).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def _pin(path, expected):
    raw = Path(path).read_bytes()
    actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if any(actual[key] != expected[key] for key in ('bytes', 'sha256')):
        raise RuntimeError('retained source fingerprint differs: ' + str(path))
    return actual


def _config(cfg):
    glb = cfg.get('retainedglb', cfg.get('glb'))
    if not glb or Path(glb).suffix.lower() != '.glb':
        raise ValueError('retainedglb must identify the reviewed GLB')
    expected = {'bytes': 202220, 'sha256': SOURCE_SHA}
    if cfg['fingerprint'] != expected:
        raise ValueError('exact reviewed Miri v2 fingerprint required')
    _pin(glb, expected)
    path = Path(cfg.get('sourcecontractpath', cfg.get('source_contract', '')))
    if hashlib.sha256(path.read_bytes()).hexdigest() != CONTRACT_SHA:
        raise RuntimeError('exact independently inspected source contract required')
    contract = json.loads(path.read_text(encoding='utf-8'))
    if contract['packet']['sha256'] != PACKET_SHA or not contract['all_reviewed_pins_match']:
        raise RuntimeError('reviewed packet identity differs')
    _pin(contract['packet']['path'], contract['packet'])
    for source in contract['source_files']:
        _pin(source['path'], source)
    payload = contract['payload']
    if (payload['triangle_count'] != 1320 or payload['skin_count'] != 1
            or len(payload['authored_joints']) != 17 or payload['material_count'] != 11
            or {row['name'] for row in payload['clips']} != set(CLIPS)):
        raise RuntimeError('fixed reviewed Miri payload contract differs')
    return str(glb), contract


def _deadline(cfg):
    deadline = cfg.get('deadline_epoch', cfg.get('deadline'))
    if not isinstance(deadline, (float, int)) or not math.isfinite(deadline):
        raise ValueError('finite operator deadline_epoch required')
    if time.time() > deadline - 90:
        raise RuntimeError('operator deadline reached; preserve partial delivery')


def _preflight(allowed_dirty=()):
    bridge = sys.modules.get('claude_unreal_bridge')
    if bridge is None or not all(hasattr(bridge, key) for key in
                                 ('_jobs', '_running', '_job_boxes', '_remote_lock')):
        raise RuntimeError('existing bridge queue fields unavailable; hold mutation')
    running = list(bridge._running)
    own = [req for gen, req, box in running if req.get('type') == 'daedalus.steps'
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
        raise RuntimeError('unexpected dirty packages; preserve work: ' + repr((maps, content)))
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


def _assets():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    paths = {str(data.package_name) + '.' + str(data.asset_name)
             for data in registry.get_assets_by_path(ROOT, recursive=True)}
    paths.update(str(path) for path in unreal.EditorAssetLibrary.list_assets(
        ROOT, recursive=True, include_folder=False))
    objects = {}
    for path in sorted(paths):
        obj = unreal.EditorAssetLibrary.load_asset(path)
        if obj is None or not obj.get_path_name().startswith(ROOT + '/'):
            raise RuntimeError('owned native asset could not be resolved: ' + path)
        objects[obj.get_path_name()] = obj
    return objects


def _normal(name):
    return ''.join(c.lower() for c in str(name) if c.isalnum())


def _rgba(colour):
    return [float(getattr(colour, key)) for key in ('r', 'g', 'b', 'a')]


def _physical(material):
    """Read effective instance overrides/parent values, never change them."""
    report = {'chain': [], 'two_sided': None, 'blend_mode': None, 'opaque': None, 'errors': []}
    current, seen = material, set()
    try:
        while current is not None:
            path = current.get_path_name()
            if path in seen or len(seen) >= 12:
                raise RuntimeError('cyclic or excessive material parent chain')
            seen.add(path)
            entry = {'path': path, 'class': current.get_class().get_name()}
            report['chain'].append(entry)
            if isinstance(current, unreal.Material):
                if report['two_sided'] is None:
                    report['two_sided'] = bool(current.get_editor_property('two_sided'))
                if report['blend_mode'] is None:
                    mode = current.get_editor_property('blend_mode')
                    report['blend_mode'] = str(mode)
                    report['opaque'] = mode == unreal.BlendMode.BLEND_OPAQUE
                break
            overrides = current.get_editor_property('base_property_overrides')
            entry['override_two_sided'] = bool(overrides.get_editor_property('override_two_sided'))
            entry['override_blend_mode'] = bool(overrides.get_editor_property('override_blend_mode'))
            if report['two_sided'] is None and entry['override_two_sided']:
                report['two_sided'] = bool(overrides.get_editor_property('two_sided'))
            if report['blend_mode'] is None and entry['override_blend_mode']:
                mode = overrides.get_editor_property('blend_mode')
                report['blend_mode'], report['opaque'] = str(mode), mode == unreal.BlendMode.BLEND_OPAQUE
            current = current.get_editor_property('parent')
    except Exception as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc))
    return report


def _material(material, source):
    library = unreal.MaterialEditingLibrary
    report = {'path': material.get_path_name(), 'class': material.get_class().get_name(),
              'source_name': source['name'], 'source_pbr': source['pbrMetallicRoughness'],
              'vectors': {}, 'scalars': {}, 'readback_errors': [], 'matches': {}}
    try:
        instance = isinstance(material, unreal.MaterialInstanceConstant)
        for name in library.get_vector_parameter_names(material):
            value = (library.get_material_instance_vector_parameter_value(material, name) if instance
                     else library.get_material_default_vector_parameter_value(material, name))
            report['vectors'][str(name)] = _rgba(value)
        for name in library.get_scalar_parameter_names(material):
            value = (library.get_material_instance_scalar_parameter_value(material, name) if instance
                     else library.get_material_default_scalar_parameter_value(material, name))
            report['scalars'][str(name)] = float(value)
    except Exception as exc:
        report['readback_errors'].append(type(exc).__name__ + ': ' + str(exc))
    expected = source['pbrMetallicRoughness']
    for semantic, names, table, wanted in (
            ('baseColorFactor', ('basecolorfactor', 'basecolor'), report['vectors'], expected['baseColorFactor']),
            ('roughnessFactor', ('roughnessfactor', 'roughness'), report['scalars'], expected['roughnessFactor']),
            ('metallicFactor', ('metallicfactor', 'metallic'), report['scalars'], expected['metallicFactor'])):
        candidates = [(key, value) for key, value in table.items() if _normal(key) in names]
        matches = [key for key, value in candidates
                   if (all(abs(a - b) <= .0001 for a, b in zip(value, wanted))
                       if isinstance(wanted, list) else abs(value - wanted) <= .0001)]
        report['matches'][semantic] = {'candidates': dict(candidates), 'matching_parameters': matches,
                                       'source_value': wanted}
        if not matches:
            report['readback_errors'].append('unsupported or differing named native PBR parameter: ' + semantic)
    report['physical'] = _physical(material)
    if report['physical']['two_sided'] is not True or report['physical']['opaque'] is not True:
        report['readback_errors'].append('effective opaque/double-sided properties not verified')
    report['readback_errors'].extend(report['physical']['errors'])
    return report


def _pose(transform):
    return {'translation': [float(getattr(transform.translation, axis)) for axis in ('x', 'y', 'z')],
            'rotation_xyzw': [float(getattr(transform.rotation, axis)) for axis in ('x', 'y', 'z', 'w')],
            'scale': [float(getattr(transform.scale3d, axis)) for axis in ('x', 'y', 'z')]}


def _pose_delta(a, b):
    # q and -q encode the same rotation; do not mistake a sign flip for motion.
    rotation = min(max(abs(x - y) for x, y in zip(a['rotation_xyzw'], b['rotation_xyzw'])),
                   max(abs(x + y) for x, y in zip(a['rotation_xyzw'], b['rotation_xyzw'])))
    return max(rotation, *(abs(x - y) for key in ('translation', 'scale')
                           for x, y in zip(a[key], b[key])))


def _inspect(contract):
    objects = _assets()
    report = {'root': ROOT, 'assets': [{'path': path, 'class': obj.get_class().get_name()}
                                     for path, obj in objects.items()],
              'mesh': None, 'clips': [], 'issues': [], 'world_placed': 0, 'world_saved': False,
              'required_future_actor_scale': [1., 1., 1.], 'unit_contract': UNIT_CONTRACT,
              'native_continuous_playback': 'unverified', 'authored_collision': 'not delivered or accepted'}
    issues = report['issues']
    skeletal = [obj for obj in objects.values() if isinstance(obj, unreal.SkeletalMesh)]
    skeletons = [obj for obj in objects.values() if isinstance(obj, unreal.Skeleton)]
    clips = [obj for obj in objects.values() if isinstance(obj, unreal.AnimSequence)]
    for obj in objects.values():
        if not isinstance(obj, (unreal.SkeletalMesh, unreal.Skeleton, unreal.AnimSequence,
                                unreal.MaterialInterface, unreal.PhysicsAsset)):
            issues.append('unexpected output class: ' + obj.get_path_name() + ' ' + obj.get_class().get_name())
    if len(skeletal) != 1 or len(skeletons) != 1 or len(clips) != 3:
        issues.append('require one SkeletalMesh, one Skeleton and three AnimSequences; observed '
                      + repr((len(skeletal), len(skeletons), len(clips))))
        return report, objects
    mesh, skeleton = skeletal[0], skeletons[0]
    mesh_report = {'path': mesh.get_path_name(), 'skeleton': None, 'rig': [], 'materials': [], 'geometry': {}}
    report['mesh'] = mesh_report
    try:
        import_data = mesh.get_editor_property('asset_import_data')
        mesh_report['import_data_class'] = import_data.get_class().get_name() if import_data else None
        actual_skeleton = mesh.get_editor_property('skeleton')
        mesh_report['skeleton'] = actual_skeleton.get_path_name() if actual_skeleton else None
        if actual_skeleton != skeleton:
            issues.append('mesh bound to a different skeleton')
        mapping = {}
        for bone in contract['payload']['authored_joints']:
            name = bone['name']
            native = name if unreal.AnimationLibrary.does_bone_name_exist(clips[0], name) else name.replace('.', '_')
            exists = all(unreal.AnimationLibrary.does_bone_name_exist(clip, native) for clip in clips)
            mapping[name] = native
            parent = str(mesh.get_bone_parent(native)) if exists else None
            mesh_report['rig'].append({'source_name': name, 'native_name': native,
                                       'exists_on_all_clip_skeletons': exists, 'parent': parent})
            if not exists:
                issues.append('authored bone missing: ' + name)
        for source, observed in zip(contract['payload']['authored_joints'], mesh_report['rig']):
            if source['parent'] in mapping and observed['parent'] != mapping[source['parent']]:
                issues.append('authored bone parent differs: ' + source['name'])
        copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
            mesh, unreal.DynamicMesh(), unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        dynamic = copied[0] if isinstance(copied, tuple) else copied
        geometry = mesh_report['geometry']
        geometry['copy_outcome'] = str(copied[-1]) if isinstance(copied, tuple) else 'not_returned'
        geometry['triangles'] = int(dynamic.get_triangle_count())
        if geometry['triangles'] != 1320:
            issues.append('native source triangle count differs from1320')
        points = []
        for triangle in range(geometry['triangles']):
            valid, *vertices = dynamic.get_triangle_positions(triangle)
            if not valid or len(vertices) != 3:
                raise RuntimeError('native source triangle positions unavailable')
            points.extend([[float(getattr(vertex, axis)) for axis in ('x', 'y', 'z')] for vertex in vertices])
        geometry['source_bounds_cm'] = {'min': [min(p[i] for p in points) for i in range(3)],
                                        'max': [max(p[i] for p in points) for i in range(3)]}
        geometry['source_dimensions_cm'] = [geometry['source_bounds_cm']['max'][i] - geometry['source_bounds_cm']['min'][i]
                                             for i in range(3)]
        bounds = mesh.get_imported_bounds()
        geometry['imported_bounds_origin_cm'] = [float(getattr(bounds.origin, axis)) for axis in ('x', 'y', 'z')]
        geometry['imported_dimensions_cm'] = [float(getattr(bounds.box_extent, axis)) * 2 for axis in ('x', 'y', 'z')]
        for dims in (geometry['source_dimensions_cm'], geometry['imported_dimensions_cm']):
            if any(abs(a - b) > .2 for a, b in zip(sorted(dims), (99., 141., 227.))):
                issues.append('native unit-scale rest dimensions differ from99,141,227cm')
        source_materials = contract['payload']['materials']
        used = []
        slots = list(mesh.get_editor_property('materials'))
        if len(slots) != 11:
            issues.append('native skeletal material slot count differs from11')
        for index, slot in enumerate(slots):
            material = slot.get_editor_property('material_interface')
            row = {'index': index, 'slot': str(slot.get_editor_property('material_slot_name')),
                   'material': material.get_path_name() if material else None}
            mesh_report['materials'].append(row)
            if not isinstance(material, unreal.MaterialInterface) or material.get_path_name() not in objects:
                issues.append('new owned MaterialInterface binding required atslot' + str(index))
                continue
            candidates = [source for source in source_materials
                          if any(_normal(value).endswith(_normal(source['name']))
                                 for value in (row['slot'], material.get_name()))]
            if len(candidates) != 1:
                issues.append('unambiguous source material name mapping unavailable atslot' + str(index))
                continue
            source = candidates[0]
            used.append(source['name'])
            row['pbr'] = _material(material, source)
            issues.extend(material.get_path_name() + ': ' + value for value in row['pbr']['readback_errors'])
        if sorted(used) != sorted(source['name'] for source in source_materials):
            issues.append('eleven source PBR material mappings not retained one-to-one')
        for clip in clips:
            names = [name for name in CLIPS if _normal(clip.get_name()).endswith(_normal(name))]
            row = {'path': clip.get_path_name(), 'source_name': names[0] if len(names) == 1 else None,
                   'length_s': float(clip.get_play_length()),
                   'skeleton': clip.get_skeleton().get_path_name() if clip.get_skeleton() else None,
                   'pose_samples': [], 'changing_sampled_bones': []}
            report['clips'].append(row)
            if len(names) != 1 or abs(row['length_s'] - CLIPS[names[0]]) > 1 / 30 + .0001:
                issues.append('named source clip/duration differs: ' + clip.get_path_name())
            if clip.get_skeleton() != skeleton:
                issues.append('clip skeleton binding differs: ' + clip.get_path_name())
            model = clip.get_editor_property('data_model')
            row['track_names'] = [str(name) for name in model.get_bone_track_names()]
            row['pose_sampling_scope'] = 'Three local native pose readbacks at .125/.375/.625 seconds; no playback or world plant claim'
            for source_name, native_name in mapping.items():
                if not unreal.AnimationLibrary.does_bone_name_exist(clip, native_name):
                    continue
                samples = [{'time_s': stamp, 'pose': _pose(unreal.AnimationLibrary.get_bone_pose_for_time(
                    clip, native_name, stamp, False))} for stamp in (.125, .375, .625)]
                delta = max(_pose_delta(samples[0]['pose'], sample['pose']) for sample in samples[1:])
                row['pose_samples'].append({'source_bone': source_name, 'native_bone': native_name,
                                            'samples': samples, 'maximum_component_delta': delta})
                if delta > .000001:
                    row['changing_sampled_bones'].append(source_name)
            if names == ['Miri_Walk_InPlace'] and not any(name in row['changing_sampled_bones']
                    for name in ('thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R')):
                issues.append('native sampled Walk leg poses are constant or unavailable')
        if sorted(row['source_name'] or '' for row in report['clips']) != sorted(CLIPS):
            issues.append('three distinct named source clips not retained')
    except Exception as exc:
        issues.append('native readback unsupported: ' + type(exc).__name__ + ': ' + str(exc))
    return report, objects


def inspect_assets(cfg):
    """JSON readback of the existing owned root; never import, bind or save."""
    glb, contract = _config(cfg)
    report, objects = _inspect(contract)
    return report


def steps(cfg):
    journal = Path(cfg['journal'])
    if journal.exists():
        raise RuntimeError('retained native journal exists; inspect, never replay')
    glb, contract = _config(cfg)
    _deadline(cfg)
    initial = _preflight()
    eal = unreal.EditorAssetLibrary
    if eal.does_directory_exist(ROOT) or _assets():
        raise RuntimeError('owned Miri destination already exists; no import replay or overwrite')
    report = {'schema': 'daedalus.codex-miri-v2-native.v1', 'stage': 'import_dispatch_pending',
              'root': ROOT, 'source_glb': glb, 'source_sha256': SOURCE_SHA,
              'source_contract_sha256': CONTRACT_SHA, 'reviewed_packet_sha256': PACKET_SHA,
              'initial_preflight': initial, 'unit_contract': UNIT_CONTRACT,
              'required_future_actor_scale': [1., 1., 1.],
              'requested_options': {'backend': 'existing_cast_AssetImportTask_auto_glTF',
                                    'options_override': None, 'replace_existing': False, 'task_save': False},
              'world_placed': 0, 'world_saved': False, 'material_data_changed': False,
              'outputs': [], 'save_return': None, 'replay_permitted': False}
    with journal.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    try:
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = glb, ROOT
        task.destination_name = 'Miri_ActionPack_V2'
        task.automated, task.replace_existing, task.save = True, False, False
        _deadline(cfg)
        _preflight()
        started = time.perf_counter()
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        report.update(stage='import_returned', import_s=round(time.perf_counter() - started, 6),
                      imported_object_paths=[str(path) for path in task.imported_object_paths])
        _write(journal, report)
        observed, objects = _inspect(contract)
        report['observed_before_first_save'] = observed
        _write(journal, report)
        if observed['issues']:
            raise NativeContractError('; '.join(observed['issues']), observed)
        allowed_dirty = [path.split('.')[0] for path in objects]
        _deadline(cfg)
        _preflight(allowed_dirty)
        _config(cfg)
        mesh = objects[observed['mesh']['path']]
        tags = {'codex_owner': 'codex-contest', 'codex_sha256': SOURCE_SHA,
                'codex_source_glb': glb, 'codex_unit_contract': UNIT_CONTRACT,
                'codex_required_actor_scale': '1,1,1',
                'codex_source_provenance': 'release_slice_review; Emberthread courier Miri; seed160814; reviewed additive walk-v2',
                'codex_reviewed_packet_sha256': PACKET_SHA,
                'codex_world_placement': 'held; continuous playback/controller/collision/game acceptance unverified'}
        report.update(stage='owned_mesh_metadata_dispatch_pending', metadata=tags)
        _write(journal, report)
        for key, value in tags.items():
            eal.set_metadata_tag(mesh, key, value)
        if any(eal.get_metadata_tag(mesh, key) != value for key, value in tags.items()):
            raise RuntimeError('owned mesh provenance metadata readback differs')
        for path, obj in sorted(objects.items()):
            _deadline(cfg)
            _preflight(allowed_dirty)
            row = {'path': path, 'class': obj.get_class().get_name(),
                   'save_return': None, 'save_s': None, 'stage': 'save_dispatch_pending'}
            report['outputs'].append(row)
            report['stage'] = 'owned_asset_save_dispatch_pending'
            _write(journal, report)
            started = time.perf_counter()
            row['save_return'] = bool(eal.save_loaded_asset(obj, only_if_is_dirty=False))
            row['save_s'] = round(time.perf_counter() - started, 6)
            row['stage'] = 'asset_saved' if row['save_return'] else 'save_returned_false'
            report['stage'] = 'owned_asset_save_returned'
            _write(journal, report)
            if row['save_return'] is not True:
                raise RuntimeError('owned Miri asset save returned false: ' + path)
            yield path
        report['final_preflight'] = _preflight()
        final, objects = _inspect(contract)
        report['observed_after_saves'] = final
        if final['issues']:
            raise NativeContractError('post-save native contract differs', final)
        report.update(stage='miri_assets_saved_world_held', save_return=True)
        _write(journal, report)
        return report
    except Exception as exc:
        if isinstance(exc, NativeContractError):
            report['failed_observation'] = exc.observed
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__, error=str(exc))
        _write(journal, report)
        raise
