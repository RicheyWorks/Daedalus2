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


def memory(reserve=0):
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32)] + [
            (k, ctypes.c_uint64) for k in ('total', 'physical', 'page_total', 'commit', 'virt', 'available', 'extra')]
    state = Memory(); state.length = ctypes.sizeof(state)
    if (not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state))
            or state.physical < 1740800000 + reserve or state.commit < 2252800000 + reserve):
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


def inventory_reader(witness):
    scope = {'__name__': '_pinned_static_source_inventory'}
    exec(compile(source(witness), witness['path'], 'exec'), scope)
    return scope


def registry_paths(registry, root, stop_path=None, candidate_name=None):
    """Supported directory enumeration, not fictional native offset pagination.

    GetSubPaths and each direct-folder TArray are materialized by Unreal. Refuse
    an oversized response explicitly; never take a cap-sized prefix as coverage.
    """
    started = time.monotonic()
    memory(128 * 1024**2)
    folders = [root] + [str(p) for p in registry.get_sub_paths(root, True)]
    if len(folders) > 16384 or len({p.casefold() for p in folders}) != len(folders):
        raise RuntimeError('Unsupported/inconsistent registry folder response')
    if any(p != root and not p.startswith(root + '/') for p in folders):
        raise RuntimeError('Registry returned an outside folder')
    paths, seen, largest, text_bytes, asset_rows = [], set(), 0, 0, 0
    for number, folder in enumerate(sorted(folders)):
        memory(128 * 1024**2)
        if time.monotonic() - started > 30 or (stop_path and Path(stop_path).exists()):
            raise RuntimeError('Incomplete registry enumeration: time/STOP boundary')
        rows = registry.get_assets_by_path(folder, recursive=False)
        if len(rows) > 4096:
            raise RuntimeError('Unsupported direct-folder array exceeds 4096; no native paging API')
        asset_rows += len(rows)
        if asset_rows > 100000:
            raise RuntimeError('Unsupported registry asset-row resource bound; incomplete')
        largest = max(largest, len(rows))
        for row in rows:
            if candidate_name and str(row.asset_name).casefold() == candidate_name.casefold():
                raise RuntimeError('Source asset name already present globally; no new import')
            if str(row.asset_class_path.asset_name) != 'StaticMesh': continue
            path = str(row.package_name) + '.' + str(row.asset_name)
            if not str(row.package_name).rsplit('/', 1)[0] == folder:
                raise RuntimeError('Registry returned a recursive/outside folder row')
            if path.casefold() in seen: raise RuntimeError('Duplicate registry object path')
            seen.add(path.casefold()); paths.append(path); text_bytes += len(path.encode())
            if len(paths) > 100000 or text_bytes > 16 * 1024**2:
                raise RuntimeError('Unsupported registry identity/byte resource bound; incomplete')
        if number % 8 == 7: yield None
    return sorted(paths), {'complete': True, 'folder_count': len(folders), 'asset_rows': asset_rows,
                           'largest_direct_response': largest,
                           'native_api': 'GetSubPaths + GetAssetsByPath(recursive=False); full folder arrays'}


def inventory_admission(config):
    memory(128 * 1024**2)
    baseline = json.loads(source(config['baseline']))
    if (baseline['editor'] != config['editor'] or os.getpid() != config['editor']['pid']
            or context() != baseline['context']
            or unreal.SystemLibrary.get_engine_version() != config['engine_version']):
        raise RuntimeError('Inventory editor/current protected context differs')
    if (unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
            or unreal.AssetRegistryHelpers.get_asset_registry().is_loading_assets()
            or unreal.InterchangeManager.get_interchange_manager_scripted().is_interchange_active()
            or unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_active_executor() is not None
            or json.loads(unreal.get_default_object(unreal.AutomationTestToolset).call_method('GetTestStatus')).get('state') == 'Running'):
        raise RuntimeError('Inventory read requires clean idle native state')


def capture_registry_steps(config):
    """Optional sole-writer read helper; existing exact R1 path capture also fits."""
    inventory_admission(config)
    reader = inventory_reader(config['inventory_reader'])
    paths, evidence = yield from registry_paths(unreal.AssetRegistryHelpers.get_asset_registry(),
                                               reader['ROOT'], config.get('stop_path'))
    inventory_admission(config)
    return {'root': reader['ROOT'], 'count': len(paths), 'paths': paths,
            'path_digest': reader['path_digest'](paths), 'enumeration': evidence,
            'source_hashes_verified': False}


def capture_inventory_page(config):
    """ONE read-only page per existing owner-guard call; never import/save/GC.

    The writer persists each return as a new page. Partial/unknown pages stay
    evidence, never enter a complete index. Another read can address that page;
    this is independent of the runner's never-replay import checkpoints.
    """
    inventory_admission(config)
    reader = inventory_reader(config['inventory_reader'])
    source(config['reader'])
    paths = reader['capture'](config['registry'])
    offset = config['offset']
    if type(offset) is not int or offset < 0 or offset >= len(paths) or offset % reader['PAGE_ROWS']:
        raise RuntimeError('Exact aligned inventory page offset required')
    requested = min(reader['PAGE_ROWS'], len(paths) - offset)
    rows, issues, started = [], [], time.monotonic()
    content = Path(config['editor']['project']).parent / 'Content'
    for path in paths[offset:offset + requested]:
        memory(128 * 1024**2)
        if time.monotonic() - started > 30 or (config.get('stop_path') and Path(config['stop_path']).exists()):
            issues.append({'reason': 'partial_time_or_stop', 'next_offset': offset + len(rows)})
            break
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        sha = unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'codex_sha256') if isinstance(mesh, unreal.StaticMesh) else ''
        if not isinstance(sha, str) or not reader['SHA'].fullmatch(sha):
            issues.append({'asset': path, 'reason': 'unknown_native_source_sha256'})
            continue
        package = reader['pin'](content / (path.split('.')[0][len('/Game/'):] + '.uasset'))
        reader['witness'](package)
        rows.append({'asset': path, 'source_sha256': sha, 'package': package})
        del mesh  # Drop this Python reference; never force GC/unload other work.
    inventory_admission(config)
    state = ('complete' if not issues and len(rows) == requested else
             'partial' if any(r.get('reason') == 'partial_time_or_stop' for r in issues) else 'unsupported')
    return {'schema': reader['PAGE'], 'state': state,
            'editor': config['editor'], 'registry_sha256': config['registry']['sha256'],
            'reader_sha256': config['reader']['sha256'], 'offset': offset, 'requested': requested,
            'rows': rows, 'issues': issues}


def deduplicate(item):
    """Stream complete native page evidence and saved-package hashes, no loads."""
    memory(128 * 1024**2)
    reader = inventory_reader(CFG['policy']['inventory_reader'])
    index = reader['read_index'](CFG['policy']['dedup'])
    if index['editor'] != CFG['frozen']['editor'] or index['reader'] != CFG['policy']['native']:
        raise RuntimeError('Inventory editor/native reader differs')
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    current, enumeration = yield from registry_paths(registry, reader['ROOT'], CFG['stop_path'])
    expected = set(reader['capture'](index['registry']))
    if expected.intersection(CFG['known_outputs']):
        raise RuntimeError('Conflicting original and DONE output inventory identities')
    expected.update(CFG['known_outputs'])
    if current != sorted(expected):
        raise RuntimeError('Existing ingestion source coverage changed/unknown; reconcile inventory')
    _, global_enumeration = yield from registry_paths(registry, '/Game', CFG['stop_path'],
                                                     candidate_name=item['name'])
    global_count = global_enumeration['asset_rows']
    started, checked, page_count = time.monotonic(), 0, 0
    content = Path(CFG['frozen']['editor']['project']).parent / 'Content'
    def check(row):
        memory(128 * 1024**2)
        if time.monotonic() - started > 60 or Path(CFG['stop_path']).exists():
            raise RuntimeError('Incomplete source coverage: time/STOP boundary')
        if row['source_sha256'] == item['fingerprint']['sha256']:
            raise RuntimeError('Source hash already imported; reuse only after separate admission')
        file = reader['witness'](row['package'])
        expected_file = content / (row['asset'].split('.')[0][len('/Game/'):] + '.uasset')
        if file.resolve() != expected_file.resolve() or reader['fingerprint'](file) != {k: row['package'][k] for k in ('sha256', 'bytes')}:
            raise RuntimeError('Saved package changed since native source page; recollect read evidence')
    for page in reader['pages'](index):
        for row in page: check(row); checked += 1
        page_count += 1
        yield None
    for path, row in CFG['known_outputs'].items():
        check({'asset': path, **row}); checked += 1
    after, _ = yield from registry_paths(registry, reader['ROOT'], CFG['stop_path'])
    if after != current or checked != len(current):
        raise RuntimeError('Corpus changed during page verification; incomplete coverage')
    return {'roots': [reader['ROOT']], 'complete': True, 'source_hashes_verified': True,
            'source_hashes_checked': checked, 'pages_verified': page_count,
            'registry_path_count': len(current), 'registry_path_digest': reader['path_digest'](current),
            'global_names_checked': global_count, 'enumeration': enumeration,
            'global_name_enumeration': global_enumeration,
            'scope': 'All declared corpus meshes: native source pages bound to unchanged saved packages and clean current editor. Global names only outside corpus.'}


def steps():
    cfg, item = CFG['policy'], copy.deepcopy(CFG['selected'])
    CFG['baseline'] = json.loads(source(CFG['baseline']))  # Pinned file, not a huge embedded request.
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
        duplicate_evidence = yield from deduplicate(item)
        write(Path(CFG['folder']) / 'dedup-coverage.json', duplicate_evidence)
        native['preflight'](native_cfg)
        if time.time() > datetime.fromisoformat(cfg['start_by_utc'].replace('Z', '+00:00')).timestamp():
            raise RuntimeError('Finite profile start window expired')
    if phase.startswith('admit_'):
        protected()
        return {'engine_version': CFG['frozen']['engine_version'], 'preserved': True,
                'destination_vacant': phase == 'admit_execute',
                'source_coverage': duplicate_evidence if phase == 'admit_execute' else None}
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
