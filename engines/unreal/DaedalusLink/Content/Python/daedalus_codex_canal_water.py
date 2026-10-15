# SPDX-License-Identifier: MIT
"""Exact Winter4 Stream1/Core receiving profile; asset-only, no automatic replay.

Opaque profiles remain unchanged. Four imported objects are reconciled before
two private factor-alpha Material parents are created. All six objects require
geometry, connected opacity/PBR/emission and provenance readback before saves.
Producer release and an independently admitted immutable subset are mandatory.
"""
import hashlib
import json
import math
from pathlib import Path
import time

import unreal

LABEL = 'Codex Winter4 Canal exact two-root factor-alpha asset intake R1'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Winter4CanalWaterR1_ad06dd2b3b95da8b'
SOURCE = {'bytes': 348216, 'sha256': 'ad06dd2b3b95da8bc98ee07bcd7ff59fadbbc2d08af98cb74c4582b56c1ed5cd'}
LAYOUT = {'bytes': 4325, 'sha256': '6871dd71bd755b74e336f032b68ac15d1fc0edf2fc8c95f818b6f628ba1a3868'}
ROLES = {'Octet_Winter_4_Canal_Stream1': (1456, 'HD_SkyWater_frost'),
         'Octet_Winter_4_Canal_Stream1_Core': (1456, 'HD_SkyFoam')}
UNIT_CONTRACT = 'gltf_authored_root_world_XZY_cm100_baked_build1_future_actor1_v1'
MATERIAL_POLICY = 'owned_factor_alpha_parent_v1'
# Actual first import retained this exact Core name. Its unique 1456-triangle
# bounds/material/raw factors were reconciled without renaming or reimporting.
OBSERVED_CORE_MESH_ALIAS = 'Octet_Winter_4__al_Stream1_Core'
ALIAS_OBSERVATION_SHA256 = 'e7172ea7a2399ba4bf60d3de6b509cefc08f745235f852fc76499a98c52a23cf'
PINS = {
    'subset_source': {'bytes': 31115, 'sha256': 'dc57e2c98ec2a8bc71fb7d517150c068b583737b524b01044574991b70cfdfe3'},
    'sunspool_source': {'bytes': 19965, 'sha256': 'b571284f8d7b13fb1b135072c7f438e4ae036711d3b0bab053dc751844f2e047'},
    'geometry_source': {'bytes': 22174, 'sha256': 'e3012aa9819ae60b90adcbcb6f6b37428e35daa5747313c9964918b485428dac'},
    'miri_source': {'bytes': 25647, 'sha256': '5a434e398dcaafc0cb5f66d399aca372f322dcd51a29bf7c3687e78fed05c059'},
    'catalogue_source': {'bytes': 22414, 'sha256': '00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03'},
    'material_source': {'bytes': 47565, 'sha256': '75c6d1eecef4d2c42d47db0b3a52033024f8bc7ac67efa58aeff83ad00f62000'},
    'queue_source': {'bytes': 28818, 'sha256': 'ff67f266fa45b276d287d69d5fa750b445353960d7213234dede15bc1f135df0'},
}


def _pin(path, expected):
    if (not isinstance(expected, dict) or type(expected.get('bytes')) is not int
            or not 0 < expected['bytes'] <= 64 * 1024 * 1024
            or not isinstance(expected.get('sha256'), str) or len(expected['sha256']) != 64):
        raise ValueError('bounded exact file fingerprint required')
    raw = Path(path).read_bytes()
    if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise RuntimeError('exact Canal source fingerprint differs: ' + str(path))
    return raw


def _fp(value):
    return {key: value[key] for key in ('bytes', 'sha256')}


def _utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _config(cfg):
    if (cfg['destination'] != ROOT or cfg['material_policy'] != MATERIAL_POLICY
            or type(cfg['deadline_epoch']) not in (int, float)
            or not math.isfinite(cfg['deadline_epoch'])):
        raise ValueError('exact destination, explicit material policy and finite deadline required')
    packet = json.loads(_pin(cfg['manifest'], cfg['manifest_fingerprint']))
    if (packet['schema'] != 'daedalus.canal-water-handoff.v1'
            or packet['stage'] != 'DERIVED_FILE_ADMITTED_NATIVE_PENDING'
            or packet['source_team'] != 'Team Claude' or packet['seed'] != 4
            or packet['selected_nodes'] != list(ROLES)
            or packet['material_policy'] != MATERIAL_POLICY
            or packet['unit_contract'] != UNIT_CONTRACT
            or _fp(packet['original_source']) != SOURCE
            or packet['native_ready'] is not False):
        raise ValueError('exact released Winter4 two-role handoff required')
    if _fp(packet['original_layout']) != LAYOUT:
        raise ValueError('exact layout provenance required for seed/theme claims')
    layout = json.loads(_pin(packet['original_layout']['path'], LAYOUT))
    if layout.get('name') != 'Octet_Winter_4' or layout.get('theme') != 'Winter' or type(layout.get('seed')) is not int or layout['seed'] != 4:
        raise ValueError('Winter/seed4 must be evidenced by pinned layout, not inferred from filename')
    release = json.loads(_pin(packet['release']['path'], _fp(packet['release'])))
    message = release['hub_message']
    if (release['schema'] != 'daedalus.canal-water-release.v1'
            or release['status'] != 'RELEASED_FOR_IMMUTABLE_TWO_NODE_SUBSET'
            or _fp(release['original_source']) != SOURCE
            or release['selected_nodes'] != list(ROLES)
            or release['producer_alias'] != 'unreal-team'
            or message['from'] != release['producer_alias']
            or type(message['id']) is not int or message['id'] <= 32359
            or message['to'] not in ('codex-play-guard', 'pootscoot-coordination', '*')
            or not message.get('body', {}).get('text')
            or any(release.get(key) is not True for key in
                   ('producer_confirmed_finished', 'producer_confirmed_unclaimed',
                    'producer_confirmed_not_inflight', 'operator_semantic_ack_verified'))):
        raise ValueError('actual producer release and semantic acknowledgment required; requests are not release')
    scopes = {}
    for key, expected in PINS.items():
        if cfg[key + '_fingerprint'] != expected:
            raise ValueError('exact reviewed helper required: ' + key)
        private = {'__name__': '_codex_canal_private_' + key}
        exec(compile(_pin(cfg[key], expected), cfg[key], 'exec'), private)
        private.update(LABEL=LABEL, ROOT=ROOT, ROLES=ROLES)
        scopes[key] = private
    guard = scopes['queue_source']['_shared']({
        'shared_source': cfg['catalogue_source'],
        'shared_source_fingerprint': cfg['catalogue_source_fingerprint']})
    guard.update(LABEL=LABEL, ROOT=ROOT, ROLES=ROLES)
    scopes['catalogue_source'] = guard
    journal = Path(cfg['journal'])
    if not journal.is_absolute() or journal.name != 'native.json':
        raise ValueError('absolute owned native journal required for retained graph evidence')
    scopes['material_source']['WITNESS_DIRECTORY'] = journal.parent / 'material-graph-evidence'
    for key in ('plan', 'admission', 'candidate'):
        _pin(packet[key]['path'], _fp(packet[key]))
    if str(Path(cfg['glb']).resolve()) != str(Path(packet['candidate']['path']).resolve()):
        raise ValueError('only exact separately admitted derived GLB may be imported')
    if cfg['candidate_sha256'] != packet['candidate']['sha256']:
        raise ValueError('candidate metadata fingerprint differs')
    plan = json.loads(Path(packet['plan']['path']).read_text(encoding='utf-8'))
    if _fp(plan['source']) != SOURCE or plan['nodes'] != list(ROLES):
        raise ValueError('whole source pin and exact two-root selection required')
    admission = scopes['subset_source']['admit'](plan, cfg['glb'], _fp(packet['candidate']), include_geometry=True)
    previous = json.loads(Path(packet['admission']['path']).read_text(encoding='utf-8'))
    if admission != previous or admission['admitted'] is not True or admission['native_ready'] is not False:
        raise ValueError('fresh actual-file admission differs from retained source witness')
    nodes = admission['geometry']['nodes']
    if (len(nodes) != 2 or admission['triangles'] != 2912
            or {row['name'] for row in nodes} != set(ROLES)
            or any(row['triangles'] != 1456 or row['source_material_slots'] != 1
                   or row['attributes'] != ['NORMAL', 'POSITION']
                   or row['transform'] != {'translation': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]}
                   or len(row['materials']) != 1
                   or row['materials'][0]['name'] != ROLES[row['name']][1]
                   for row in nodes)):
        raise ValueError('exact identity-root factor-only no-UV geometry required')
    return packet, nodes, scopes


def _parent_path(role):
    suffix = 'Water' if role == list(ROLES)[0] else 'Foam'
    return ROOT + '/OwnedParents/M_Codex_Winter4_' + suffix + '_RawAlpha_R1'


def _inspect(cfg, nodes, scopes, final=False, metadata=False, partial=False):
    if metadata and not final:raise ValueError('metadata inspection requires final owned graph state')
    if partial and (final or metadata):raise ValueError('partial Water-parent inspection is a separate unsaved state')
    helper = scopes['sunspool_source']; objects = helper['_assets']()
    meshes = [obj for obj in objects.values() if isinstance(obj, unreal.StaticMesh)]
    mics = [obj for obj in objects.values() if isinstance(obj, unreal.MaterialInstanceConstant)]
    parents = [obj for obj in objects.values() if isinstance(obj, unreal.Material)]
    if len(objects) != (6 if final else 5 if partial else 4) or len(meshes) != 2 or len(mics) != 2 or len(parents) != (2 if final else 1 if partial else 0):
        raise RuntimeError('exact2 imported meshes+2MICs and declared0/2 private parents required')
    used = set(); items = []
    for source in nodes:
        role = source['name']; definition = source['materials'][0]['definition']
        candidates = [m for m in meshes if helper['_normal'](m.get_name()).endswith(helper['_normal'](role))
                      or (role == list(ROLES)[1] and m.get_name() == OBSERVED_CORE_MESH_ALIAS)]
        if len(candidates) != 1 or candidates[0].get_path_name() in used:
            raise RuntimeError('unambiguous actual two-role mesh mapping required')
        mesh = candidates[0]; slots = list(mesh.get_editor_property('static_materials'))
        mic = mesh.get_material(0) if len(slots) == 1 else None
        if (not isinstance(mic, unreal.MaterialInstanceConstant) or mic.get_path_name() not in objects
                or mic.get_path_name() in used
                or not helper['_normal'](mic.get_name()).endswith(helper['_normal'](ROLES[role][1]))):
            raise RuntimeError('exact one-to-one owned imported material binding required')
        geometry = scopes['geometry_source']['_geometry'](mesh, source)
        if geometry['issues'] or geometry['simple_collision_count'] != 0:
            raise RuntimeError('Canal native geometry/units/build/profile mismatch: ' + json.dumps(geometry))
        used.update((mesh.get_path_name(), mic.get_path_name()))
        row = {'source_role': role, 'path': mesh.get_path_name(), 'material_path': mic.get_path_name(), 'geometry': geometry}
        if final:
            parent = unreal.load_asset(_parent_path(role))
            if not isinstance(parent, unreal.Material) or parent.get_path_name() not in objects or parent.get_path_name() in used:
                raise RuntimeError('exact new owned per-role parent required')
            row['material'] = scopes['material_source']['inspect'](mic, parent, definition, scopes['miri_source'])
            if row['material'].get('issues') != []:
                raise RuntimeError('strict water graph/PBR/opacity readback differs: ' + json.dumps(row['material']))
            row['owned_parent'] = parent.get_path_name(); used.add(parent.get_path_name())
        if metadata:
            for obj, name in ((mesh, role), (mic, ROLES[role][1]), (parent, role + ':owned-parent')):
                if {key: unreal.EditorAssetLibrary.get_metadata_tag(obj, key) for key in _tags(cfg, name)} != _tags(cfg, name):
                    raise RuntimeError('exact Canal source metadata differs')
        items.append(row)
    partial_parent = None
    if partial:
        parent = parents[0]
        if parent.get_path_name() != _parent_path(list(ROLES)[0]) + '.' + _parent_path(list(ROLES)[0]).rsplit('/', 1)[1]:
            raise RuntimeError('only the exact unsaved Water parent may be partially resumed')
        definition = next(node for node in nodes if node['name'] == list(ROLES)[0])['materials'][0]['definition']
        partial_parent = scopes['material_source']['inspect_partial_parent'](parent, definition, objects)
        used.add(parent.get_path_name())
    if used != set(objects):raise RuntimeError('every owned output must be accounted')
    return {'assets': [{'path': path, 'class': obj.get_class().get_name()} for path, obj in objects.items()],
            'items': items, 'issues': [], 'triangles': 2912, 'unit_contract': UNIT_CONTRACT,
            'material_policy': MATERIAL_POLICY, 'world_placed': 0, 'world_saved': False,
            'imported_object_count': 4, 'created_parent_count': len(parents),
            'partial_parent': partial_parent,
            'required_future_actor_scale': [1, 1, 1], 'source_payload_sha256': cfg['candidate_sha256'],
            'original_source_sha256': SOURCE['sha256'], 'handoff_sha256': cfg['manifest_fingerprint']['sha256'],
            'provenance_metadata_verified': bool(metadata), 'source_admission_verified': True,
            'observed_mesh_alias_proof_sha256': ALIAS_OBSERVATION_SHA256,
            'shared_material_modified': False}, objects


def _tags(cfg, role):
    return {'codex_owner': 'codex-contest', 'codex_source_team': 'Team Claude',
            'codex_source_role': role, 'codex_original_source_sha256': SOURCE['sha256'],
            'codex_sha256': cfg['candidate_sha256'], 'codex_unit_contract': UNIT_CONTRACT,
            'codex_material_contract': MATERIAL_POLICY,
            'codex_pivot_contract': 'global vertex coordinates baked; unit actor scale; no recenter/reapply root',
            'codex_story_chemistry': 'Winter/seed4 source; visual sky-canal water+foam only; canonical realm narrative/physics unknown; no flow/fluid/survival/quest authority accepted',
            'codex_world_placement': 'held; asset-only; appearance/runtime/collision/navigation unaccepted'}


def preflight(cfg):
    packet, nodes, scopes = _config(cfg); guard = scopes['catalogue_source']
    guard['_deadline'](cfg); initial = guard['_preflight']()
    journal = Path(cfg['journal'])
    if not journal.is_absolute() or journal.exists() or journal.with_name(journal.name + '.write-pending').exists() or not journal.parent.is_dir():
        raise RuntimeError('new absolute owned journal required; retained outcomes forbid replay')
    return {'guard': initial, **scopes['sunspool_source']['_absent'](),
            'source': SOURCE, 'candidate': packet['candidate'], 'nodes': list(ROLES),
            'requested_imports': 4, 'requested_created_parents': 2, 'expected_saved_objects': 6,
            'material_policy': MATERIAL_POLICY, 'unit_contract': UNIT_CONTRACT,
            'no_uv_policy': 'POSITION/NORMAL factor-only shader; no texture/UV sampling or generated lightmap UVs',
            'world_placed': 0, 'world_saved': False}


def readback(cfg):
    packet, nodes, scopes = _config(cfg); guard = scopes['catalogue_source']
    guard['_deadline'](cfg); before = guard['_preflight']()
    report, objects = _inspect(cfg, nodes, scopes, final=True, metadata=True)
    report.update(preflight=before, post_read_preflight=guard['_preflight'](), persistent_assets_modified=False)
    return report


def steps(cfg):
    initial = preflight(cfg); packet, nodes, scopes = _config(cfg)
    helper = scopes['sunspool_source']; guard = scopes['catalogue_source']; journal = Path(cfg['journal'])
    report = {'schema': 'daedalus.canal-water-native.v1', 'utc': _utc(), 'stage': 'import_dispatch_pending',
              'initial_preflight': initial, 'mutation_intents': [], 'outputs': [], 'completed_count': 0,
              'save_return': None, 'world_placed': 0, 'world_saved': False, 'replay_permitted': False}
    with journal.open('x', encoding='utf-8', newline='\n') as f:helper['_flush'](f, report)
    def intent(operation, **fields):
        guard['_deadline'](cfg)
        current = helper['_assets']()
        allowed = set(report.get('imported_object_paths', [])) | {
            _parent_path(role) + '.' + _parent_path(role).rsplit('/', 1)[1] for role in ROLES}
        if not set(current).issubset(allowed):raise RuntimeError('unexpected owned object; preserve partial intake')
        def on_wait(row):
            report.setdefault('guard_waits', []).append(row)
            helper['_write'](journal, report)
        yield from scopes['queue_source']['_preflight_steps'](
            guard, cfg, [path.split('.')[0] for path in current], on_wait=on_wait)
        report['mutation_intents'].append({'utc': _utc(), 'operation': operation, **fields})
        helper['_write'](journal, report)
    try:
        yield from intent('import_exact_released_derived_glb', path=cfg['glb'])
        _config(cfg); helper['_absent']()
        task = unreal.AssetImportTask();task.filename = cfg['glb'];task.destination_path = ROOT
        task.destination_name = 'Winter4_Canal_Stream1_Core_R1';task.automated = True
        task.replace_existing = False;task.save = False;task.options = None
        start = time.perf_counter();unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        report.update(stage='import_returned', import_s=round(time.perf_counter()-start, 6),
                      imported_object_paths=[str(path) for path in task.imported_object_paths])
        helper['_write'](journal, report)
        objects = helper['_assets']()
        if (len(objects) != 4 or len(report['imported_object_paths']) != 4
                or set(report['imported_object_paths']) != set(objects)
                or sum(isinstance(o, unreal.StaticMesh) for o in objects.values()) != 2
                or sum(isinstance(o, unreal.MaterialInstanceConstant) for o in objects.values()) != 2):
            raise RuntimeError('exact four fresh imported outputs required before corrections/parents')
        subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        for mesh in (o for o in objects.values() if isinstance(o, unreal.StaticMesh)):
            settings = mesh.get_editor_property('nanite_settings')
            if settings.enabled:
                yield from intent('set_new_owned_mesh_nanite_false', path=mesh.get_path_name(), observed_before=True)
                settings.enabled = False;subsystem.set_nanite_settings(mesh, settings, True)
            build = subsystem.get_lod_build_settings(mesh, 0)
            if build.generate_lightmap_u_vs:raise RuntimeError('unexpected generated UVs; preserve unsaved output for source review')
        geometry_report, objects = _inspect(cfg, nodes, scopes)
        report['before_parent_creation'] = geometry_report;helper['_write'](journal, report)
        for source in nodes:
            row = next(r for r in geometry_report['items'] if r['source_role'] == source['name'])
            mic = objects[row['material_path']]; definition = source['materials'][0]['definition']
            parent, graph = yield from scopes['material_source']['build_parent'](_parent_path(source['name']), definition, intent)
            yield from scopes['material_source']['bind_instance'](mic, parent, definition, intent)
        observed, objects = _inspect(cfg, nodes, scopes, final=True)
        report['before_first_save'] = observed;helper['_write'](journal, report)
        roles = {}
        for row in observed['items']:
            roles.update({row['path']: row['source_role'], row['material_path']: ROLES[row['source_role']][1],
                          row['owned_parent']: row['source_role'] + ':owned-parent'})
        for path, obj in objects.items():
            yield from intent('set_new_owned_source_metadata', path=path)
            for key, value in _tags(cfg, roles[path]).items():unreal.EditorAssetLibrary.set_metadata_tag(obj, key, value)
        report['after_metadata_before_first_save'], objects = _inspect(cfg, nodes, scopes, final=True, metadata=True)
        helper['_write'](journal, report)
        # Parent packages precede instances/meshes; all six are validated first.
        ordered = sorted(objects.items(), key=lambda pair: (0 if isinstance(pair[1], unreal.Material) else 1, pair[0]))
        for path, obj in ordered:
            yield from intent('first_save_exact_owned_object', path=path)
            row = {'path': path, 'class': obj.get_class().get_name(), 'save_return': None}
            report['outputs'].append(row);helper['_write'](journal, report)
            start = time.perf_counter();row['save_return'] = bool(unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False))
            row['save_s'] = round(time.perf_counter()-start, 6)
            if row['save_return']:report['completed_count'] += 1
            helper['_write'](journal, report)
            if row['save_return'] is not True:raise RuntimeError('first save returned false; preserve partial state')
            yield path
        guard['_deadline'](cfg)
        final_before = yield from scopes['queue_source']['_preflight_steps'](guard, cfg)
        report['final_observed'], objects = _inspect(cfg, nodes, scopes, final=True, metadata=True)
        final_after = yield from scopes['queue_source']['_preflight_steps'](guard, cfg)
        report['final_observed'].update(preflight=final_before, post_read_preflight=final_after)
        final_guard = yield from scopes['queue_source']['_preflight_steps'](guard, cfg)
        report.update(stage='canal_two_role_six_assets_saved_world_held', save_return=True,
                      final_preflight=final_guard)
        helper['_write'](journal, report);return report
    except Exception as exc:
        report.update(stage='halted_preserve_partial', error=str(exc), error_type=type(exc).__name__, failure_utc=_utc())
        if not journal.with_name(journal.name + '.write-pending').exists():helper['_write'](journal, report)
        raise
