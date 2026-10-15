# SPDX-License-Identifier: MIT
"""Bounded skeletal GLB delivery of the reviewed Miri v2; no world placement."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import codex_catalogue_delivery as catalogue
import codex_catalogue_gems_delivery as gems
from codex_aetherflow_readback import _native_code

BASE = catalogue.BASE
FOLDER = BASE / 'MiriV2'
SOURCE = catalogue.ROOT / 'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_miri.py'
LABEL = 'Codex Miri v2 skeletal GLB asset-only import-save'
CONTRACT_FP = {'bytes': 33017, 'sha256': '11034938cec63a80123b46817aab485a66b603067adc23374efe657f87896d33'}


def protection():
    gems.configure()
    _, local = catalogue.protection()
    baseline = catalogue.load(gems.FOLDER / 'readback.json')
    if (baseline.get('issues') != [] or baseline.get('verified_saved_mesh_files') != 102
            or baseline.get('map_unchanged') is not True):
        raise ValueError('completed clean 102-static-mesh baseline required')
    for path, expected in baseline['outputs'].items():
        if path in local['disk_static_meshes'] or catalogue.fingerprint(catalogue._asset_file(path)) != expected:
            raise RuntimeError('gem output differs: ' + path)
        local['disk_static_meshes'][path] = expected
    if len(local['disk_static_meshes']) != 102:
        raise RuntimeError('exact protected 102 static mesh set required')
    return baseline, local


def prepare():
    contract_path = FOLDER / 'source-contract.json'
    if catalogue.fingerprint(contract_path) != CONTRACT_FP:
        raise ValueError('exact reviewed Miri source contract required')
    contract = catalogue.load(contract_path)
    if contract.get('all_reviewed_pins_match') is not True:
        raise ValueError('all reviewed source pins required')
    for row in [contract['packet'], *contract['source_files']]:
        catalogue._check_file(row)
    original = contract['payload']['glb']
    catalogue._check_file(original)
    target = FOLDER / Path(original['path']).name
    if (FOLDER / 'prepared.json').exists() or target.exists():
        raise RuntimeError('retain Miri preparation; inspect existing stage')
    with target.open('xb') as handle:
        handle.write(Path(original['path']).read_bytes())
    catalogue.write_new(FOLDER / 'prepared.json', {
        'schema': 'daedalus.codex-miri-prepared.v1', 'stage': 'reviewed_skeletal_glb_prepared',
        'glb': str(target), 'glb_fingerprint': catalogue.fingerprint(target), 'original_glb': original,
        'source_contract': str(contract_path), 'source_contract_fingerprint': CONTRACT_FP,
        'native_module': str(SOURCE), 'native_module_fingerprint': catalogue.fingerprint(SOURCE),
        'source_witnesses': [contract['packet'], *contract['source_files']],
        'unit_contract': 'gltf_metres_to_native_centimetres_actor1',
        'scope': 'One skeletal mesh and original three clips/materials, asset-only; no static flattening, actor placement, world save or playback.'})
    print('reviewed_skeletal_glb_prepared')


def prepared():
    value = catalogue.load(FOLDER / 'prepared.json')
    for field in ('glb', 'source_contract', 'native_module'):
        if catalogue.fingerprint(value[field]) != value[field + '_fingerprint']:
            raise RuntimeError('prepared witness changed: ' + field)
    for row in value['source_witnesses']:
        catalogue._check_file(row)
    return value


def module_code(value):
    return '''from pathlib import Path
import hashlib
raw=Path(SOURCE).read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('owned Miri source changed')
scope={'__name__':'_codex_retained_miri_v2'}
exec(compile(raw,SOURCEPATH,'exec'),scope)
'''.replace('SOURCE', repr(str(SOURCE)), 1).replace('EXPECTED', repr(value['native_module_fingerprint']['sha256']), 1).replace('SOURCEPATH', repr(str(SOURCE)), 1)


def config(value, deadline=None):
    return {'glb': value['glb'], 'retainedglb': value['glb'], 'fingerprint': value['glb_fingerprint'],
            'source_contract': value['source_contract'], 'sourcecontractpath': value['source_contract'],
            'journal': str(FOLDER / 'native.json'), 'deadline_epoch': deadline or time.time() + 180}


def ingest():
    value = prepared(); protection(); catalogue.editor(); lease = catalogue._lease()
    dispatch = FOLDER / 'dispatch.json'
    if dispatch.exists():
        raise RuntimeError('Miri dispatch exists; inspect retained known/uncertain result, no replay')
    cfg = config(value, min(time.time() + 600, lease['at'] + lease['ttl'] - 60))
    code = module_code(value) + '\ndef steps():\n    return (yield from scope[\'steps\'](' + repr(cfg) + '))\n'
    catalogue.write_new(dispatch, {'stage': 'native_dispatch_pending',
        'code_sha256': hashlib.sha256(code.encode()).hexdigest(),
        'prepared_fingerprint': catalogue.fingerprint(FOLDER / 'prepared.json'),
        'map_before': catalogue.fingerprint(catalogue.MAP_FILE)})
    reply = catalogue.wire.call(catalogue.wire.UNREAL, 'daedalus.steps', code=code,
                               label=LABEL, budget_ms=1, timeout=180, side='Unreal')
    catalogue.write_new(FOLDER / 'reply.json', reply)
    dispatch_value = catalogue.load(dispatch)
    dispatch_value.update(stage='native_returned_inspect_before_replay', reply_fingerprint=catalogue.fingerprint(FOLDER / 'reply.json'))
    dispatch.write_text(json.dumps(dispatch_value, indent=2) + '\n')
    if reply.get('error'):
        raise RuntimeError('inspect retained Miri journal/reply; never blindly replay import')
    native = catalogue.load(FOLDER / 'native.json')
    if native.get('stage') != 'miri_assets_saved_world_held':
        raise RuntimeError('Miri saves not confirmed; inspect retained journal')
    outputs = {}
    for row in native['outputs']:
        if row.get('save_return') is not True:
            raise RuntimeError('owned Miri asset save not confirmed')
        outputs[row['path']] = {'class': row['class'], **catalogue.fingerprint(catalogue._asset_file(row['path']))}
    dispatch_value.update(stage='miri_assets_saved_world_held', outputs=outputs)
    dispatch.write_text(json.dumps(dispatch_value, indent=2) + '\n')
    protection(); catalogue.editor()
    if catalogue.fingerprint(catalogue.MAP_FILE) != dispatch_value['map_before']:
        raise RuntimeError('world changed during asset-only Miri delivery')
    print(json.dumps({'stage': dispatch_value['stage'], 'outputs': outputs}, indent=2))


def readback(dispatch_name='dispatch.json', inspector_code=None, inspection_config=None):
    value = prepared(); baseline, local = protection(); catalogue.editor()
    dispatch = catalogue.load(FOLDER / dispatch_name)
    if dispatch.get('stage') != 'miri_assets_saved_world_held':
        raise RuntimeError('completed Miri save dispatch required')
    for path, expected in dispatch['outputs'].items():
        if catalogue.fingerprint(catalogue._asset_file(path)) != {key: expected[key] for key in ('sha256', 'bytes')}:
            raise RuntimeError('new Miri output differs: ' + path)
    code = (inspector_code or module_code(value)) + _native_code(local) + "\nresult['miri']=scope['inspect_assets'](" + repr(inspection_config or config(value)) + ')\n'
    result = catalogue.wire.obj(catalogue.wire.call(catalogue.wire.UNREAL, 'execute_python', code=code,
        unattended=False, timeout=90, side='Unreal'), side='Unreal', what='saved Miri skeletal/clips/materials and preserved scene')
    issues = []
    previous = baseline['native_readback']; observed = {row['label']: row for row in result['actors']}
    if len(observed) != 89 or result['all_level_actor_count'] != previous['all_level_actor_count']:
        issues.append('actor count changed')
    for row in previous['actors']:
        if any(observed.get(row['label'], {}).get(field) != row[field]
               for field in ('actor', 'mesh_path', 'transform', 'materials', 'override_materials', 'folder', 'tags')):
            issues.append('prior actor changed: ' + row['label'])
    classes = result['saved_asset_classes']
    if len(classes) != 102 or set(classes) != set(local['disk_static_meshes']) or any(row.get('is_static_mesh') is not True for row in classes.values()):
        issues.append('prior 102 static mesh set differs')
    actual_miri = {row['path']: row['class'] for row in result['miri']['assets']}
    if actual_miri != {path: row['class'] for path, row in dispatch['outputs'].items()} or result['miri'].get('issues') != []:
        issues.append('saved Miri class/contract set differs')
    if result['dirty_map_packages'] or result['dirty_content_packages']:
        issues.append('dirty packages after save')
    protection(); catalogue.editor()
    map_unchanged = catalogue.fingerprint(catalogue.MAP_FILE) == dispatch['map_before']
    if not map_unchanged:
        issues.append('map changed')
    for path, expected in dispatch['outputs'].items():
        if catalogue.fingerprint(catalogue._asset_file(path)) != {key: expected[key] for key in ('sha256', 'bytes')}:
            issues.append('new Miri output changed: ' + path)
    catalogue.write_new(FOLDER / 'readback.json', {
        'schema': 'daedalus.codex-miri-native-readback.v1', 'observed_utc': datetime.now(timezone.utc).isoformat(),
        'stage': 'miri_saved_readback_complete' if not issues else 'inspection_required', 'issues': issues,
        'verified_saved_static_mesh_files': 102, 'measured_actor_rows': 89, 'world_placed': 0,
        'new_saved_assets': len(dispatch['outputs']), 'outputs': dispatch['outputs'], 'native_readback': result,
        'completion_dispatch': dispatch_name,
        'map_fingerprint': catalogue.fingerprint(catalogue.MAP_FILE), 'map_unchanged': map_unchanged,
        'limits': 'Asset-only skeletal/clip/material save; no continuous native playback, planted feet, visual/BAR/gameplay acceptance or world save. No tests/Play/build/restart.'})
    print(json.dumps({'issues': issues, 'new_saved_assets': len(dispatch['outputs']),
                      'verified_saved_static_mesh_files': 102, 'measured_actor_rows': 89, 'map_unchanged': map_unchanged}, indent=2))
    if issues:
        raise RuntimeError('inspect retained final Miri readback')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'ingest', 'readback'))
    globals()[parser.parse_args().stage]()
