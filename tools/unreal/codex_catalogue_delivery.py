# SPDX-License-Identifier: MIT
"""Deliver three qualified existing static eggs without actors or a world save.

Uses the existing Rack/Interchange contract and retained journal. An existing
dispatch is always an inspection stop, including after a transport timeout.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from codex_aetherflow_delivery import BASE, MAP_FILE, editor, load, write_new
from codex_aetherflow_readback import _native_code
from codex_contest_island_delivery import fingerprint
from codex_editor_handoff import _asset_file, wire
from codex_server_rack_delivery import protection as prior_protection

ROOT = Path(__file__).resolve().parents[2]
FOLDER = BASE / 'CatalogueEggR1'
SOURCE = ROOT / 'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_catalogue.py'
LABEL = 'Codex retained static egg catalogue asset-only import-save'
NAMES = ('Prop_Egg_Heartstone_Intact', 'Prop_Egg_Gold_Shiny', 'Prop_Egg_Amethyst_Intact')
RACK = BASE / 'ServerRackR1/readback.json'
MATERIAL = '/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.M_VoxelVertexColour'
QUALIFICATION_FP = {'sha256': '635e313be835a1d967cdd1badfca4b2438d57b6b4991f555a8acd80dddbbbb27', 'bytes': 24182}
PRIOR_CATALOGUE = None


def protection():
    _, local = prior_protection()
    rack = load(RACK)
    if rack.get('issues') != [] or rack.get('verified_saved_mesh_files') != 96 or rack.get('map_unchanged') is not True:
        raise ValueError('completed clean 96-mesh baseline required')
    local['disk_static_meshes'][rack['native_path']] = rack['output_fingerprint']
    if len(local['disk_static_meshes']) != 96:
        raise ValueError('exact prior 96 paths required')
    for path, expected in local['disk_static_meshes'].items():
        if fingerprint(_asset_file(path)) != {key: expected[key] for key in ('sha256', 'bytes')}:
            raise RuntimeError('protected saved mesh differs: ' + path)
    if fingerprint(MAP_FILE) != rack['map_fingerprint']:
        raise RuntimeError('preserve current saved map; baseline differs')
    if PRIOR_CATALOGUE is not None:
        prior = load(PRIOR_CATALOGUE)
        if (prior.get('stage') != 'three_assets_saved_readback_complete' or prior.get('issues') != []
                or prior.get('verified_saved_mesh_files') != 99 or prior.get('map_unchanged') is not True
                or fingerprint(MAP_FILE) != prior['map_fingerprint']):
            raise ValueError('completed clean 99-mesh catalogue baseline required')
        for path, expected in prior['outputs'].items():
            if path in local['disk_static_meshes'] or fingerprint(_asset_file(path)) != expected:
                raise RuntimeError('prior catalogue output differs: ' + path)
            local['disk_static_meshes'][path] = expected
        if len(local['disk_static_meshes']) != 99:
            raise ValueError('exact 99 prior paths required')
        return prior, local
    return rack, local


def _lease():
    lease = json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=10)).get('unreal', {})
    if lease.get('holder') != 'codex-play-guard' or lease.get('at', 0) + lease.get('ttl', 0) - time.time() < 240:
        raise RuntimeError('current sole-operator lease with bounded time required')
    return lease


def _check_file(row):
    if fingerprint(row['path']) != {key: row[key] for key in ('sha256', 'bytes')}:
        raise RuntimeError('retained source witness changed: ' + row['path'])


def prepare():
    qualification_path = FOLDER / 'source-qualification.json'
    if fingerprint(qualification_path) != QUALIFICATION_FP:
        raise ValueError('exact independently qualified source receipt required')
    qualification = load(qualification_path)
    if tuple(row['name'] for row in qualification['items']) != NAMES:
        raise ValueError('exact reviewed three egg identities required')
    if (FOLDER / 'prepared.json').exists():
        raise RuntimeError('retain preparation; inspect existing stage')
    items = []
    for row in qualification['items']:
        item = {key: row[key] for key in ('name', 'triangles', 'rgba_bytes', 'source_bounds')}
        for field in ('fbx', 'sidecar'):
            _check_file(row[field])
            target = FOLDER / Path(row[field]['path']).name
            with target.open('xb') as handle:
                handle.write(Path(row[field]['path']).read_bytes())
            item[field] = str(target)
            item[field + '_fingerprint'] = fingerprint(target)
            item['original_' + field] = row[field]
        item['fingerprint'] = item['fbx_fingerprint']
        item['destination'] = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Egg_' + item['name'].removeprefix('Prop_Egg_') + '_' + item['fingerprint']['sha256'][:16]
        items.append(item)
    for row in qualification['source_witnesses']:
        _check_file(row)
    for row in qualification['source_views']:
        _check_file(row)
    write_new(FOLDER / 'prepared.json', {
        'schema': 'daedalus.codex-static-catalogue-prepared.v1',
        'stage': 'three_existing_static_eggs_prepared', 'items': items,
        'source_qualification': str(qualification_path), 'source_qualification_fingerprint': fingerprint(qualification_path),
        'source_module': str(SOURCE), 'source_module_fingerprint': fingerprint(SOURCE),
        'source_witnesses': qualification['source_witnesses'],
        'source_views': qualification['source_views'],
        'unit_contract': 'claude_raw_unit100_build1_actor001_v1', 'required_future_actor_scale': [.01, .01, .01],
        'limits': 'Static asset delivery only; no actors, world save, hatching, economy, collision or native appearance acceptance.'})
    print(json.dumps({'stage': 'three_existing_static_eggs_prepared', 'items': list(NAMES)}, indent=2))


def _prepared():
    prepared = load(FOLDER / 'prepared.json')
    for field in ('source_qualification', 'source_module'):
        if fingerprint(prepared[field]) != prepared[field + '_fingerprint']:
            raise RuntimeError('prepared witness changed: ' + field)
    for item in prepared['items']:
        for field in ('fbx', 'sidecar'):
            if fingerprint(item[field]) != item[field + '_fingerprint']:
                raise RuntimeError('prepared payload changed: ' + item[field])
            _check_file(item['original_' + field])
    for row in prepared['source_witnesses']:
        _check_file(row)
    for row in prepared['source_views']:
        _check_file(row)
    return prepared


def _module_code(prepared):
    return '''from pathlib import Path
import hashlib
source=SOURCE
raw=Path(source).read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('owned catalogue module changed')
scope={'__name__':'_codex_existing_static_catalogue'}
exec(compile(raw,source,'exec'),scope)
'''.replace('SOURCE', repr(str(SOURCE)), 1).replace('EXPECTED', repr(prepared['source_module_fingerprint']['sha256']), 1)


def ingest():
    prepared = _prepared()
    protection(); editor(); lease = _lease()
    dispatch = FOLDER / 'dispatch.json'
    if dispatch.exists():
        raise RuntimeError('retained dispatch exists; inspect known/uncertain outcome before any replay')
    cfg = {'items': prepared['items'], 'journal': str(FOLDER / 'native.json'),
           'deadline_epoch': min(time.time() + 600, lease['at'] + lease['ttl'] - 60)}
    code = _module_code(prepared) + '\ndef steps():\n    return (yield from scope[\'steps\'](' + repr(cfg) + '))\n'
    write_new(dispatch, {'stage': 'native_dispatch_pending', 'observed_utc': datetime.now(timezone.utc).isoformat(),
        'code_sha256': hashlib.sha256(code.encode()).hexdigest(), 'map_before': fingerprint(MAP_FILE),
        'prepared_fingerprint': fingerprint(FOLDER / 'prepared.json')})
    reply = wire.call(wire.UNREAL, 'daedalus.steps', code=code, label=LABEL, budget_ms=1, timeout=180, side='Unreal')
    write_new(FOLDER / 'reply.json', reply)
    value = load(dispatch)
    value.update(stage='native_returned_inspect_before_replay', reply_fingerprint=fingerprint(FOLDER / 'reply.json'))
    dispatch.write_text(json.dumps(value, indent=2) + '\n')
    if reply.get('error'):
        raise RuntimeError('inspect retained native journal/reply; no blind replay')
    native = load(FOLDER / 'native.json')
    if native.get('stage') != 'three_assets_saved_world_held' or len(native.get('items', [])) != 3:
        raise RuntimeError('three native saves not confirmed; inspect journal')
    outputs = {}
    for item in native['items']:
        if item.get('save_return') is not True or item.get('stage') != 'asset_saved_world_held':
            raise RuntimeError('item save not confirmed')
        outputs[item['native_path']] = fingerprint(_asset_file(item['native_path']))
    value.update(stage='three_assets_saved_world_held', outputs=outputs)
    dispatch.write_text(json.dumps(value, indent=2) + '\n')
    protection(); editor()
    if fingerprint(MAP_FILE) != value['map_before']:
        raise RuntimeError('map changed during asset-only delivery')
    print(json.dumps({'stage': value['stage'], 'outputs': outputs}, indent=2))


def readback():
    prepared = _prepared()
    baseline, local = protection(); editor()
    expected_count = len(local['disk_static_meshes']) + 3
    dispatch = load(FOLDER / 'dispatch.json'); native = load(FOLDER / 'native.json')
    if dispatch.get('stage') != 'three_assets_saved_world_held':
        raise RuntimeError('completed asset save dispatch required')
    for path, expected in dispatch['outputs'].items():
        if fingerprint(_asset_file(path)) != expected:
            raise RuntimeError('new saved file differs')
        local['disk_static_meshes'][path] = expected
    paths = {row['name']: row['native_path'] for row in native['items']}
    code = _module_code(prepared) + _native_code(local) + '''
result['catalogue_assets']={}
for item in ITEMS:
    path=PATHS[item['name']]
    mesh=unreal.EditorAssetLibrary.load_asset(path)
    data=scope['inspect_mesh'](mesh,item)
    data['material']=mesh.get_material(0).get_path_name()
    data['unit_contract']=unreal.EditorAssetLibrary.get_metadata_tag(mesh,'codex_unit_contract')
    data['required_actor_scale']=unreal.EditorAssetLibrary.get_metadata_tag(mesh,'codex_required_actor_scale')
    data['source_sha256']=unreal.EditorAssetLibrary.get_metadata_tag(mesh,'codex_sha256')
    data['world_references']=[a.get_path_name() for a in all_actors if a.get_component_by_class(unreal.StaticMeshComponent) and a.get_component_by_class(unreal.StaticMeshComponent).get_editor_property('static_mesh')==mesh]
    result['catalogue_assets'][item['name']]=data
'''.replace('ITEMS', repr(prepared['items']), 1).replace('PATHS', repr(paths), 1)
    result = wire.obj(wire.call(wire.UNREAL, 'execute_python', code=code, unattended=False, timeout=90, side='Unreal'),
                      side='Unreal', what='saved three static eggs and preserved scene readback')
    issues = []
    observed = {row['label']: row for row in result['actors']}
    prior = baseline['native_readback']
    if len(observed) != 89 or result['all_level_actor_count'] != prior['all_level_actor_count']:
        issues.append('actor count changed')
    for row in prior['actors']:
        if any(observed.get(row['label'], {}).get(field) != row[field]
               for field in ('actor', 'mesh_path', 'transform', 'materials', 'override_materials', 'folder', 'tags')):
            issues.append('prior actor changed: ' + row['label'])
    classes = result['saved_asset_classes']
    if len(classes) != expected_count or set(classes) != set(local['disk_static_meshes']) or any(row.get('is_static_mesh') is not True for row in classes.values()):
        issues.append('exact saved mesh path/class set differs: ' + str(expected_count))
    for item in prepared['items']:
        actual = result['catalogue_assets'][item['name']]
        if actual['material'] != MATERIAL or actual['unit_contract'] != 'claude_raw_unit100_build1_actor001_v1' or actual['required_actor_scale'] != '0.01,0.01,0.01' or actual['source_sha256'] != item['fingerprint']['sha256']:
            issues.append('saved material/metadata contract differs: ' + item['name'])
        if actual['world_references']:
            issues.append('unexpected egg world reference: ' + item['name'])
    if result['dirty_map_packages'] or result['dirty_content_packages']:
        issues.append('dirty packages after save')
    protection(); editor()
    for path, expected in dispatch['outputs'].items():
        if fingerprint(_asset_file(path)) != expected:
            issues.append('new output changed: ' + path)
    map_unchanged = fingerprint(MAP_FILE) == dispatch['map_before']
    if not map_unchanged:
        issues.append('saved map changed')
    write_new(FOLDER / 'readback.json', {'schema': 'daedalus.codex-static-catalogue-readback.v1',
        'stage': 'three_assets_saved_readback_complete' if not issues else 'inspection_required',
        'observed_utc': datetime.now(timezone.utc).isoformat(), 'issues': issues, 'native_readback': result,
        'outputs': dispatch['outputs'], 'native_receipt_fingerprint': fingerprint(FOLDER / 'native.json'),
        'new_saved_mesh_files': 3, 'verified_saved_mesh_files': expected_count, 'measured_actor_rows': 89,
        'world_placed': 0, 'map_unchanged': map_unchanged, 'map_fingerprint': fingerprint(MAP_FILE),
        'limits': 'Static saved assets only. Required future actor scale .01; no native visual/hatching/economy/collision/runtime acceptance. No Play/tests/worldsave.'})
    print(json.dumps({'issues': issues, 'new_saved_mesh_files': 3, 'verified_saved_mesh_files': expected_count,
                      'measured_actor_rows': 89, 'world_placed': 0, 'map_unchanged': map_unchanged}, indent=2))
    if issues:
        raise RuntimeError('inspect retained final readback before continuing')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'ingest', 'readback'))
    globals()[parser.parse_args().stage]()
