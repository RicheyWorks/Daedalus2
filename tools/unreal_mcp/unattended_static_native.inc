# SPDX-License-Identifier: MIT
# Executed ONLY by the sole writer through the existing retained daedalus.steps.
import copy
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import unreal


def source(witness):
    raw = Path(witness['path']).read_bytes()
    if len(raw) != witness['bytes'] or hashlib.sha256(raw).hexdigest() != witness['sha256']:
        raise RuntimeError('Pinned source/protected witness differs')
    return raw


def memory():
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32)] + [
            (k, ctypes.c_uint64) for k in ('total', 'physical', 'page_total', 'commit', 'virt', 'available', 'extra')]
    state = Memory(); state.length = ctypes.sizeof(state)
    if (not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state))
            or state.physical < 1740800000 or state.commit < 2252800000):
        raise RuntimeError('Native memory floor; preserve work')


def context():
    """Owner captures this exact read-only format immediately before freezing."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    if world is None or len(actors) > 4096:
        raise RuntimeError('Absent/unbounded current context')
    rows = []
    for actor in actors:
        meshes = []
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            meshes.append([component.get_path_name(), mesh.get_path_name() if mesh else None])
        rows.append({'path': actor.get_path_name(), 'class': actor.get_class().get_name(),
                     'transform': str(actor.get_actor_transform()), 'meshes': sorted(meshes)})
    location, rotation = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info()
    return {'world': world.get_path_name(), 'actors': sorted(rows, key=lambda r: r['path']),
            'camera': [location.x, location.y, location.z, rotation.pitch, rotation.yaw, rotation.roll]}


def protected():
    for witness in CFG['baseline']['files']:
        memory()
        digest, size = hashlib.sha256(), 0
        with Path(witness['path']).open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block); size += len(block)
        if digest.hexdigest() != witness['sha256'] or size != witness['bytes']:
            raise RuntimeError('Protected saved file/source changed')
    if context() != CFG['baseline']['context']:
        raise RuntimeError('Exact fresh owner world/actors/camera differs')


def helper(cfg):
    scope = {'__name__': '_pinned_qualified_static_owner_profile'}
    exec(compile(source(cfg['importer']), cfg['importer']['path'], 'exec'), scope)
    original = scope['_shared']
    def current_context(native_cfg):
        shared = original(native_cfg)
        # This is the explicit profile parameter: change only this private
        # dictionary's expected world. The original guard/queue checks still run.
        shared['WORLD'] = CFG['frozen']['editor']['world']
        return shared
    scope['_shared'] = current_context
    return scope


def idle(shared):
    memory()
    guard = shared['_preflight']()
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    tool = unreal.get_default_object(unreal.AutomationTestToolset)
    if (registry.is_loading_assets()
            or json.loads(tool.call_method('GetTestStatus')).get('state') == 'Running'
            or unreal.InterchangeManager.get_interchange_manager_scripted().is_interchange_active()
            or unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_active_executor() is not None):
        raise RuntimeError('Competing native work; preserve state')
    return guard


def deduplicate(item):
    """Read-only scoped source-hash inventory + global registry-name exclusion.

    No directory sweep or unbounded asset load. Missing provenance/coverage holds.
    The sole writer supplies all meshes in the existing ingestion corpus roots;
    the current native registry must prove that inventory complete at dispatch.
    """
    inventory = json.loads(source(CFG['policy']['dedup']))
    roots = ['/Game/Daedalus/Art/Islands']
    if (set(inventory) != {'schema', 'roots', 'assets'}
            or inventory['schema'] != 'daedalus.static-source-inventory.v1'
            or inventory['roots'] != roots or not isinstance(inventory['assets'], dict)
            or not 1 <= len(inventory['assets']) <= 512):
        raise RuntimeError('Explicit bounded existing ingestion source inventory required')
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    all_rows = registry.get_assets_by_path('/Game', recursive=True)
    if len(all_rows) > 100000:
        raise RuntimeError('Global registry name inventory exceeds cap')
    if any(str(row.asset_name).casefold() == item['name'].casefold() for row in all_rows):
        raise RuntimeError('Source asset name already present globally; no new import')
    expected = dict(inventory['assets'])
    expected.update({p: {'sha256': sha} for p, sha in CFG['known_outputs'].items()})
    current = {str(row.package_name) + '.' + str(row.asset_name)
               for root in roots for row in registry.get_assets_by_path(root, recursive=True)
               if str(row.asset_class_path.asset_name) == 'StaticMesh'}
    if current != set(expected):
        raise RuntimeError('Existing ingestion source coverage changed/unknown; reconcile inventory')
    for path, witness in expected.items():
        memory()
        if not isinstance(witness.get('sha256'), str) or len(witness['sha256']) != 64:
            raise RuntimeError('Unknown source hash; no absence inference')
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError('Source inventory object absent/not StaticMesh')
        actual = unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'codex_sha256')
        if actual != witness['sha256']:
            raise RuntimeError('Native source-hash provenance differs/unknown')
        if actual == item['fingerprint']['sha256']:
            raise RuntimeError('Source hash already imported; reuse only after separate admission')
    return {'roots': roots, 'source_hashes_checked': len(expected), 'global_names_checked': len(all_rows),
            'scope': 'All meshes in declared existing ingestion corpus; global names. Untagged external renamed sources are not certified.'}


def steps():
    cfg, item = CFG['policy'], copy.deepcopy(CFG['selected'])
    if os.getpid() != CFG['frozen']['editor']['pid']:
        raise RuntimeError('Editor PID differs')
    if unreal.SystemLibrary.get_engine_version() != CFG['frozen']['engine_version']:
        raise RuntimeError('Exact engine version differs')
    receipt_scope = {'__name__': '_pinned_receipt_primitives'}
    exec(compile(source(CFG['receipts']), CFG['receipts']['path'], 'exec'), receipt_scope)
    write = receipt_scope['write_receipt']
    protected()
    native = helper(cfg)
    if CFG['snapshots']:
        for actual, expected in zip(CFG['snapshots'], CFG['item']['sources']):
            if {k: actual[k] for k in ('sha256', 'bytes')} != {k: expected[k] for k in ('sha256', 'bytes')}:
                raise RuntimeError('Snapshot-to-selected-source binding differs')
            source(actual)
        item['fbx'], item['sidecar'] = [s['path'] for s in CFG['snapshots']]
    native_cfg = {'items': [item], 'journal': str(Path(CFG['folder']) / 'qualified-static.json'),
                  'deadline_epoch': time.time() + 240,
                  'shared_source': cfg['shared']['path'],
                  'shared_source_fingerprint': {k: cfg['shared'][k] for k in ('sha256', 'bytes')}}
    shared = native['_shared'](native_cfg)
    idle(shared)
    phase = CFG['phase']
    if phase == 'admit_execute' or phase == 'execute':
        duplicate_evidence = deduplicate(item)
        native['preflight'](native_cfg)
        if time.time() > datetime.fromisoformat(cfg['start_by_utc'].replace('Z', '+00:00')).timestamp():
            raise RuntimeError('Finite profile start window expired')
    if phase.startswith('admit_'):
        protected()
        return {'engine_version': CFG['frozen']['engine_version'], 'preserved': True,
                'destination_vacant': phase == 'admit_execute'}
    if phase == 'execute':
        # Existing helper owns every import option, source/static gate, save,
        # journal, exact inventory/material/palette/bounds/metadata readback.
        if Path(CFG['stop_path']).exists():
            raise RuntimeError('STOP before new import; preserve queue')
        imported = yield from native['steps'](native_cfg)
        write(Path(CFG['folder']) / 'import-terminal.json', imported)
        if (imported.get('stage') != 'qualified_static_assets_saved_world_held'
                or imported.get('save_return') is not True or imported.get('completed_count') != 1):
            raise RuntimeError('Existing importer did not save exactly one qualified new asset')
    read = native['readback'](native_cfg)
    write(Path(CFG['folder']) / 'readback.json', read)
    paths = [item['destination'] + '/' + item['name'] + '.' + item['name']]
    if [r['native_path'] for r in read['items']] != paths:
        raise RuntimeError('Saved exact single output identity differs')
    outputs = {}
    content = Path(CFG['frozen']['editor']['project']).parent / 'Content'
    for path in paths:
        package = content / (path.split('.')[0][len('/Game/'):] + '.uasset')
        outputs[path] = {'path': str(package), **receipt_scope['fingerprint'](package)}
    if phase == 'verify':
        if outputs != CFG['completion']['outputs']:
            raise RuntimeError('Saved output hashes changed')
        idle(shared); protected()
        return {'qualified_readback': True, 'preserved': True}
    if phase != 'execute':
        raise RuntimeError('Unknown phase; no fallback')
    idle(shared)
    start = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
    raw = unreal.DaedalusEditorAcceptanceLibrary.validate_named_assets(paths, item['destination'], False)
    end = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
    envelope = json.loads(raw)
    write(Path(CFG['folder']) / 'validation-original.json',
          {'envelope': envelope, 'start_utc': start, 'end_utc': end})
    # Exact native status is retained, including NotValidated/Skipped. The
    # unchanged host queue alone decides whether this is complete native Valid.
    idle(shared); protected()
    completion = {'schema': 'daedalus.unattended-ingestion.v1', 'state': 'complete',
                  'operation_id': CFG['operation_id'],
                  'item_key': hashlib.sha256(json.dumps(CFG['item'], sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()).hexdigest(),
                  'destination': item['destination'], 'engine_version': CFG['frozen']['engine_version'],
                  'assets': paths, 'outputs': outputs, 'validation': envelope, 'preserved': True,
                  'capture': {'editor': CFG['frozen']['editor'], 'operation_id': CFG['operation_id'],
                              'start_utc': start, 'end_utc': end,
                              'route': 'existing:daedalus.steps/qualified_static.steps/ValidateNamedAssets'}}
    write(CFG['receipt_path'], completion)  # Durable BEFORE the native reply.
    return {'completion': completion, 'preserved': True}
