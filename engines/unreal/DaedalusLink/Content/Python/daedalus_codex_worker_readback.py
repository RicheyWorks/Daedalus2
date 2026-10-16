# SPDX-License-Identifier: MIT
"""One read-only continuation over the fifteen retained Prospector objects."""
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import time

MARKER = '# Codex PR176 existing Prospector readback33421'


def run(cfg):
    import unreal
    raw = Path(cfg['original_native']['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != cfg['original_native']['sha256']:
        raise RuntimeError('original receiver pin changed')
    prior = {'__name__': '_worker_readback_original'}
    exec(compile(raw, cfg['original_native']['path'], 'exec'), prior)
    prior['MARKER'] = MARKER
    pin, scope = prior['_pin'], prior['_scope']
    old = json.loads(pin(cfg['original_journal']))
    if (old.get('known_terminal') is not True or old.get('imports') != 1
            or old.get('saves') != 0 or len(old['observed']['objects']) != 15):
        raise RuntimeError('known original fifteen-object import required')
    source = pin(cfg['source'])
    if source[:4] != b'glTF' or struct.unpack_from('<I', source, 16)[0] != 0x4e4f534a:
        raise RuntimeError('pinned GLB JSON chunk required')
    gltf = json.loads(source[20:20 + struct.unpack_from('<I', source, 12)[0]])
    animations = gltf['animations']
    if [a['name'] for a in animations] != list(cfg['expected']['clips']):
        raise RuntimeError('frozen source animation order differs')
    if time.time() > cfg['start_by_epoch'] or time.time() > cfg['stop_by_epoch'] - 180:
        raise RuntimeError('read-only continuation admission expired')
    journal = Path(cfg['journal'])
    if journal.exists():
        raise RuntimeError('retained continuation; reconcile without replay')
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    ws = {'unreal': unreal, 'math': math, 'json': json, 'hashlib': hashlib,
          'e': editor, 'world': editor.get_editor_world(),
          'sub': unreal.get_editor_subsystem(unreal.EditorActorSubsystem)}
    ws = scope(cfg['snap'], ws)
    exec(compile(pin(cfg['world_helper']), cfg['world_helper']['path'], 'exec'), ws)
    miri = scope(cfg['miri']); miri['ROOT'] = prior['ROOT']
    contract = scope(cfg['contract'])
    report = {'version': 'worker176-owned-readback-v1', 'stage': 'READONLY_COLLECTING',
              'imports': 0, 'saves': 0, 'bindings': 0, 'actors': 0, 'maps_saved': 0,
              'camera_actions': 0, 'known_terminal': False, 'issues': [], 'field_errors': [],
              'original_journal': cfg['original_journal'], 'observed': {}}
    def keep():
        journal.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    def read(label, fn):
        try:
            return fn()
        except Exception as exc:
            report['field_errors'].append({'field': label, 'error': str(exc)})
            return None
    def guard():
        result = prior['_guard'](unreal, True)
        expected_dirty = set(prior['HELD']) | {o['path'].split('.')[0] for o in old['observed']['objects']}
        if set(result['dirty_content']) != expected_dirty:
            raise RuntimeError('exact old six plus fifteen held packages required')
        return result
    report['pre_guard'] = guard()
    before = prior['_scene'](ws)
    if before != old['after']:
        raise RuntimeError('protected world differs from original terminal')
    report['before'] = before
    with journal.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, allow_nan=False)
    try:
        # Existing retained assets only. No AssetImportTask, asset save, setter or actor API.
        objects = miri['_assets']()
        inventory = [{'path': p, 'class': o.get_class().get_name()} for p, o in objects.items()]
        if sorted(inventory, key=lambda r: r['path']) != sorted(old['observed']['objects'], key=lambda r: r['path']):
            raise RuntimeError('retained fifteen-object inventory changed')
        obs = {'objects': inventory, 'clips': [], 'bones': [], 'saved_files': []}
        report['observed'] = obs
        for p in objects:
            saved = Path('C:/Unreal/DaedalusRealm/Content') / (p.split('.')[0][6:] + '.uasset')
            if saved.exists(): obs['saved_files'].append(str(saved))
        mesh = objects[old['observed']['mesh_path']]
        skeleton = objects[old['observed']['skeleton_path']]
        obs.update(mesh_path=mesh.get_path_name(), skeleton_path=skeleton.get_path_name())
        actual = read('mesh.skeleton', lambda: mesh.get_editor_property('skeleton'))
        obs['mesh_skeleton_path'] = actual.get_path_name() if actual else None
        clips = [o for o in objects.values() if isinstance(o, unreal.AnimSequence)]
        for clip in clips:
            path = clip.get_path_name()
            row = {'path': path}
            row['length_s'] = read(path + '.length', lambda: float(clip.get_play_length()))
            sk = read(path + '.skeleton', lambda: clip.get_editor_property('skeleton'))
            row['skeleton_path'] = sk.get_path_name() if sk else None
            row['same_skeleton_object'] = sk == skeleton if sk else None
            data = read(path + '.import_data', lambda: clip.get_editor_property('asset_import_data'))
            if data:
                row['source_filename'] = read(path + '.source', lambda: data.script_get_first_filename())
                row['factory_uid'] = read(path + '.factory_uid', lambda: str(data.get_editor_property('node_unique_id')))
                factory = read(path + '.factory', lambda: data.get_stored_factory_node(row['factory_uid']))
                if factory:
                    row['factory_class'] = read(path + '.factory_class', lambda: factory.get_class().get_name())
                    row['stored_factory_uid'] = read(path + '.stored_factory_uid', lambda: str(factory.get_unique_id()))
                    row['target_uids'] = read(path + '.target_uids', lambda: [str(v) for v in factory.get_target_node_uids()])
                    payloads = read(path + '.payload_map', lambda: factory.get_scene_node_animation_payload_keys())
                    row['payloads'] = []
                    if payloads is not None:
                        for scene_uid, payload in payloads.items():
                            row['payloads'].append({'scene_uid': str(scene_uid),
                                'unique_id': read(path + '.payload.uid', lambda: str(payload.get_editor_property('unique_id'))),
                                'type': read(path + '.payload.type', lambda: str(payload.get_editor_property('type'))),
                                'baked': read(path + '.payload.baked', lambda: payload.get_editor_property('type') == unreal.InterchangeAnimationPayLoadType.BAKED)})
            # Bone evidence is independent of import metadata and is always attempted.
            row['bone_presence'] = {b['native_name']: read(path + '.bone.' + b['native_name'],
                lambda b=b: bool(unreal.AnimationLibrary.does_bone_name_exist(clip, b['native_name'])))
                for b in cfg['expected']['bones']}
            row['local_pose_samples'] = {b['native_name']: read(path + '.pose.' + b['native_name'],
                lambda b=b: [miri['_pose'](unreal.AnimationLibrary.get_bone_pose_for_time(
                    clip, b['native_name'], stamp, False)) for stamp in (0., min((row['length_s'] or 0.) * .5, .625))])
                for b in cfg['expected']['bones']}
            obs['clips'].append(row)
            keep()
        for bone in cfg['expected']['bones']:
            parent = read('parent.' + bone['native_name'], lambda: str(mesh.get_bone_parent(bone['native_name'])))
            obs['bones'].append({**bone, 'parent': None if parent in ('None', '') else parent,
                'exists_in_all_clips': all(c['bone_presence'][bone['native_name']] is True for c in obs['clips'])})
        def hierarchy():
            names, pending = set(), ['root']
            while pending:
                name = pending.pop()
                if name in names or len(names) >= 64: raise RuntimeError('cyclic/excessive bones')
                names.add(name)
                pending.extend(str(n) for n in mesh.get_bone_children(name))
            return sorted(names)
        obs['native_bone_names'] = read('native_bone_names', hierarchy)
        # Apply strict acceptance only after all independent facts have been retained.
        for row in obs['clips']:
            def provenance():
                if Path(row['source_filename']).resolve() != Path(cfg['source']['path']).resolve():
                    raise ValueError('source filename differs')
                pin({**cfg['source'], 'path': row['source_filename']})
                entries = row.get('payloads', [])
                if not entries or any(p['baked'] is not True or not re.fullmatch(r'\d+(?::\d+)+', p['unique_id'] or '') for p in entries):
                    raise ValueError('nonempty numeric BAKED payload map required')
                indices = {int(p['unique_id'].split(':')[0]) for p in entries}
                if len(indices) != 1: raise ValueError('ambiguous source animation index')
                index = indices.pop()
                if not 0 <= index < len(animations): raise ValueError('source animation index out of range')
                channels = [int(v) for p in entries for v in p['unique_id'].split(':')[1:]]
                if (len(channels) != len(set(channels)) or set(channels) != set(range(len(animations[index]['channels'])))):
                    raise ValueError('payload channels do not bijectively cover source animation')
                uid = row['factory_uid']
                if (uid != row['stored_factory_uid'] or not uid.startswith('\\AnimSequence\\SkeletalAnimation\\')
                        or not uid.endswith('_' + str(index))):
                    raise ValueError('factory UID/source animation index differs')
                return animations[index]['name']
            row['source_name'] = read(row['path'] + '.qualified_provenance', provenance)
        if report['field_errors']: raise RuntimeError('one or more read-only fields unsupported; see field_errors')
        if obs['native_bone_names'] != sorted(b['native_name'] for b in cfg['expected']['bones']):
            raise RuntimeError('reference skeleton differs from exact fourteen source joints')
        if any(c['same_skeleton_object'] is not True for c in obs['clips']):
            raise RuntimeError('actual Skeleton UObject identity differs')
        report['qualified_mapping'] = contract['qualify'](cfg['expected'], obs)
        report['stage'] = 'EXISTING_UNSAVED_WORKER_MAPPING_QUALIFIED'
    except Exception as exc:
        report['stage'] = 'KNOWN_READONLY_HOLD_PRESERVE_UNSAVED_OUTPUTS'
        report['issues'].append(str(exc))
    try:
        report['post_guard'] = guard()
        report['after'] = prior['_scene'](ws)
        if report['after'] != before: raise RuntimeError('protected scene changed')
    except Exception as exc:
        report['stage'] = 'KNOWN_READONLY_HOLD_PRESERVE_UNSAVED_OUTPUTS'
        report['issues'].append('preservation readback: ' + str(exc))
    report['known_terminal'] = True
    keep()
    return report
