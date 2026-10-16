# SPDX-License-Identifier: MIT
"""One granted Prospector GLB import and readback. No save, bind, placement or replay."""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ASSET = 'Twaker_Prospector'
SHA = '0c47c958e29b590e531c3dc804c10656054d7d6b20f2aa5e182f5cde4f004f14'
ROOT = '/Game/Daedalus/ShardsteadWorkers/Probe_20261016T1628Z/Prospector'
MARKER = '# Codex PR176 Prospector one import33402'
WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
HELD = tuple('/Game/Daedalus/Art/SkyFarm/' + suffix for suffix in (
    'CornPolishR1/Harvest3_CornPolish_R1', 'CornPolishR1/H3C_R1_AFTER_stalk',
    'CornPolishR1/H3C_R1_AFTER_leaf', 'CornPolishR1/H3C_R1_AFTER_cob',
    'GreenhouseBayR1/SFG_R1_glass', 'GreenhouseBayR1/SFG_R1_glass_glass'))


def _pin(row):
    raw = Path(row['path']).read_bytes()
    if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
        raise RuntimeError('pinned source changed: ' + row['path'])
    return raw


def _scope(row, values=None):
    scope = {'__name__': '_worker_private', '__file__': row['path'], **(values or {})}
    exec(compile(_pin(row), row['path'], 'exec'), scope)
    return scope


def _guard(unreal, allow_new=False):
    bridge = sys.modules['claude_unreal_bridge']
    others = [r.get('type') for g, r, box in bridge._running
              if r.get('type') != 'execute_python'
              or not (r.get('params') or {}).get('code', '').startswith(MARKER)]
    if (others or len(bridge._running) != 1 or bridge._jobs.qsize()
            or bridge._remote_lock.locked()
            or any(not box['done'].is_set() for box, stamp in bridge._job_boxes.values())):
        raise RuntimeError('conflicting/unfinished native work; preserve without replay')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name() != WORLD or unreal.get_editor_subsystem(
            unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('world/PIE differs')
    maps = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    dirty = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    old = [p for p in dirty if not p.startswith(ROOT + '/')]
    if maps or set(old) != set(HELD) or (not allow_new and set(dirty) != set(HELD)):
        raise RuntimeError('dirty-package boundary differs: ' + repr((maps, dirty)))
    return {'world': WORLD, 'pie': False, 'dirty_maps': maps, 'dirty_content': sorted(dirty),
            'queued': 0, 'other_running': [], 'unfinished_async': 0}


def _scene(world_scope):
    scene = world_scope['snapshot_scene']()
    scene['actors'] = sorted(scene['actors'], key=lambda row: row['path'])
    return {'scene': scene, 'digest': world_scope['world_existing_actor_digest'](),
            'selection': sorted(a.get_path_name() for a in world_scope['sub'].get_selected_level_actors())}


def _clip_provenance(clip, source, expected):
    data = clip.get_editor_property('asset_import_data')
    filename = data.script_get_first_filename()
    if Path(filename).resolve() != Path(source['path']).resolve():
        raise RuntimeError('animation source filename differs')
    _pin({**source, 'path': filename})
    uid = str(data.get_editor_property('node_unique_id'))
    factory = data.get_stored_factory_node(uid)
    if factory is None:
        raise RuntimeError('missing stored animation factory')
    targets = [str(value) for value in factory.get_target_node_uids()]
    tracks = []
    for target in targets:
        node = data.get_stored_node(target)
        if node is not None and node.get_class().get_name() == 'InterchangeSkeletalAnimationTrackNode':
            tracks.append({'uid': target, 'label': str(node.get_display_label())})
    if len(tracks) != 1:
        raise RuntimeError('ambiguous/missing translated animation track: ' + repr(tracks))
    track = tracks[0]
    names = list(expected['clips'])
    if (track['label'] not in expected['clips']
            or not track['uid'].startswith('\\SkeletalAnimation\\')
            or not track['uid'].endswith('_' + str(names.index(track['label'])))):
        raise RuntimeError('translated source clip label/index differs: ' + repr(track))
    return {'source_name': track['label'], 'source_filename': filename,
            'factory_uid': uid, 'translated_tracks': tracks}


def run(cfg):
    import unreal
    if (cfg.get('asset_id') != ASSET or cfg.get('root') != ROOT
            or cfg['source']['bytes'] != 212424 or cfg['source']['sha256'] != SHA
            or cfg['expected']['root'] != ROOT):
        raise ValueError('closed granted Prospector source/root required')
    if time.time() > cfg['start_by_epoch'] or time.time() > cfg['stop_by_epoch'] - 300:
        raise RuntimeError('finite import admission expired; no import')
    _pin(cfg['source'])
    journal = Path(cfg['journal'])
    if journal.exists():
        raise RuntimeError('retained native journal; reconcile, never replay')
    miri = _scope(cfg['miri'], {'ROOT': ROOT})
    # Constants in the existing module are private to this execution dictionary.
    miri['ROOT'] = ROOT
    contract = _scope(cfg['contract'])
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world_scope = {'unreal': unreal, 'math': math, 'json': json, 'hashlib': hashlib,
                   'e': editor, 'world': editor.get_editor_world(),
                   'sub': unreal.get_editor_subsystem(unreal.EditorActorSubsystem)}
    world_scope = _scope(cfg['snap'], world_scope)
    exec(compile(_pin(cfg['world_helper']), cfg['world_helper']['path'], 'exec'), world_scope)
    disk_root = Path('C:/Unreal/DaedalusRealm/Content') / ROOT[6:]
    initial = _guard(unreal)
    if disk_root.exists() or unreal.EditorAssetLibrary.does_directory_exist(ROOT) or miri['_assets']():
        raise RuntimeError('exact destination is not fresh; no import/replacement')
    before = _scene(world_scope)
    report = {'version': 'worker176-prospector-intake-v1', 'stage': 'PRE_IMPORT_READY',
              'root': ROOT, 'source': cfg['source'], 'imports': 0, 'saves': 0,
              'bindings': 0, 'actors': 0, 'maps_saved': 0, 'camera_actions': 0,
              'before': before, 'pre_guard': initial, 'imported_object_paths': [],
              'observed': {}, 'issues': [], 'known_terminal': False, 'replay_permitted': False}
    def keep():
        journal.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    with journal.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    try:
        _guard(unreal)
        if time.time() > cfg['start_by_epoch'] or time.time() > cfg['stop_by_epoch'] - 270:
            raise RuntimeError('deadline reserve reached before import')
        task = unreal.AssetImportTask()
        task.filename = cfg['source']['path']
        task.destination_path = ROOT
        task.destination_name = ASSET
        task.automated, task.replace_existing, task.save = True, False, False
        report.update(stage='ONE_IMPORT_DISPATCH_INTENT', import_intent_utc=time.time(),
                      requested_options={'automated': True, 'replace_existing': False,
                                         'save': False, 'options_override': None})
        keep()
        started = time.perf_counter()
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        report.update(stage='ONE_IMPORT_RETURNED', imports=1, import_seconds=time.perf_counter() - started,
                      imported_object_paths=[str(path) for path in task.imported_object_paths])
        keep()
        objects = miri['_assets']()
        observed = {'objects': [{'path': path, 'class': obj.get_class().get_name()}
                                for path, obj in objects.items()], 'clips': [], 'bones': [], 'saved_files': []}
        report['observed'] = observed
        for path in objects:
            asset_file = Path('C:/Unreal/DaedalusRealm/Content') / (path.split('.')[0][6:] + '.uasset')
            if asset_file.exists():
                observed['saved_files'].append(str(asset_file))
        if (len(report['imported_object_paths']) != len(set(report['imported_object_paths']))
                or set(report['imported_object_paths']) != set(objects)):
            raise RuntimeError('returned paths differ from complete owned inventory')
        meshes = [o for o in objects.values() if isinstance(o, unreal.SkeletalMesh)]
        skeletons = [o for o in objects.values() if isinstance(o, unreal.Skeleton)]
        clips = [o for o in objects.values() if isinstance(o, unreal.AnimSequence)]
        if (len(meshes), len(skeletons), len(clips)) != (1, 1, 7):
            raise RuntimeError('require one mesh/skeleton/seven clips; observed ' + repr((len(meshes), len(skeletons), len(clips))))
        mesh, skeleton = meshes[0], skeletons[0]
        actual = mesh.get_editor_property('skeleton')
        observed.update(mesh_path=mesh.get_path_name(), skeleton_path=skeleton.get_path_name(),
                        mesh_skeleton_path=actual.get_path_name() if actual else None)
        for clip in clips:
            row = {**_clip_provenance(clip, cfg['source'], cfg['expected']),
                   'path': clip.get_path_name(), 'length_s': float(clip.get_play_length()),
                   'skeleton_path': clip.get_skeleton().get_path_name() if clip.get_skeleton() else None}
            observed['clips'].append(row)
        for bone in cfg['expected']['bones']:
            native = bone['native_name']
            parent = str(mesh.get_bone_parent(native))
            observed['bones'].append({'source_name': bone['source_name'], 'native_name': native,
                                     'parent': None if parent in ('None', '') else parent,
                                     'exists_in_all_clips': all(unreal.AnimationLibrary.does_bone_name_exist(c, native) for c in clips)})
        names, pending = set(), ['root']
        while pending:
            name = pending.pop()
            if name in names or len(names) >= 64:
                raise RuntimeError('native bone traversal is cyclic/excessive')
            names.add(name)
            pending.extend(str(value) for value in mesh.get_bone_children(name))
        observed['native_bone_names'] = sorted(names)
        if names != {b['native_name'] for b in cfg['expected']['bones']}:
            raise RuntimeError('actual reference bone set differs from fourteen source joints')
        for clip, row in zip(clips, observed['clips']):
            row['local_pose_samples'] = {b['native_name']: [miri['_pose'](
                unreal.AnimationLibrary.get_bone_pose_for_time(clip, b['native_name'], stamp, False))
                for stamp in (0., min(row['length_s'] * .5, .625))] for b in cfg['expected']['bones']}
        report['qualified_mapping'] = contract['qualify'](cfg['expected'], observed)
        report['post_guard'] = _guard(unreal, True)
        report['after'] = _scene(world_scope)
        if report['after'] != before:
            raise RuntimeError('world/scene/selection/camera differs; preserve without repair')
        report['stage'] = 'ONE_UNSAVED_WORKER_IMPORT_MAPPINGS_QUALIFIED'
    except Exception as exc:
        report['stage'] = 'KNOWN_HOLD_PRESERVE_UNSAVED_OUTPUTS'
        report['issues'].append(str(exc))
    if 'after' not in report:
        try:
            report['post_guard'] = _guard(unreal, True)
            report['after'] = _scene(world_scope)
            if report['after'] != before:
                report['issues'].append('world/scene/selection/camera differs after held import')
        except Exception as exc:
            report['issues'].append('post-import preservation readback unavailable: ' + str(exc))
    report['known_terminal'] = True
    keep()
    return report
