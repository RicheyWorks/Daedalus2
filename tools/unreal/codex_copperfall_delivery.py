"""Sole-operator exact Copperfall delivery; preparation is file-only.

Use prepare --baseline ABSOLUTE_CURRENT_BASELINE, then run/readback/finalize.
Each phase retains evidence. Import is never retried after any dispatch outcome.
The full269-role source is read/pinned as provenance, never an import payload.
"""
import argparse
import ast
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT.parent
REPO = ROOT
sys.path.insert(0, str(REPO / 'tools/unreal'))
import codex_qualified_static_delivery as d

SOURCE = TASK / 'native-ingestion/CopperfallPlinthHeartstoneSubsetR1/Source'
DEFAULT_FOLDER = SOURCE.parent / 'DeliveryR1'
MANIFEST = SOURCE / 'handoff.json'
MANIFEST_FP = {'bytes': 14534, 'sha256': 'cb5ccb733998526308121ebae4c973e4f0ccc8aa4c79130c6d842537b9fc43f9'}
PAYLOAD_FP = {'bytes': 18732, 'sha256': '3a0a9b8a36b8dbf9199f78b9110a8e70742759b61f89b13b49354f43afdfd142'}
NATIVE = REPO / 'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_copperfall_subset.py'
HELPERS = {'sunspool_source': NATIVE.with_name('daedalus_codex_sunspool_subset.py'),
           'miri_source': NATIVE.with_name('daedalus_codex_miri.py'),
           'catalogue_source': NATIVE.with_name('daedalus_codex_catalogue.py')}
DEST = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/CopperfallR1_PlinthHeartstone_3a0a9b8a36b8dbf9'
SAVED = 'copperfall_three_role_assets_saved_readback_complete'
UNIT_CONTRACT = 'gltf_authored_root_world_XZY_cm100_baked_build1_future_actor1_v1'
ROLES = {'CAR_Overlook_Stone_Plinth': (156, 'CAR_rock_light'),
         'CAR_Heartstone_Copper_Base': (116, 'CAR_copper'), 'CAR_Heartstone': (20, 'CAR_heartstone')}


def label():
    tree = ast.parse(NATIVE.read_text(encoding='utf-8'))
    return next(ast.literal_eval(row.value) for row in tree.body if isinstance(row, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'LABEL' for target in row.targets))


def source_pins(packet):
    return [packet['candidate'], packet['source'], packet['plan'], *packet['receipts'],
            packet['source_view']['file'], packet['reproduction']['script']]


def prepare(args):
    if args.baseline is None or not args.baseline.is_absolute():
        raise ValueError('prepare requires --baseline with the explicit current absolute saved baseline')
    if args.folder.exists():
        raise RuntimeError('Retained delivery folder exists; preserve all original evidence')
    if d.fingerprint(MANIFEST) != MANIFEST_FP:
        raise RuntimeError('Exact accepted handoff required')
    packet = d.load(MANIFEST)
    if (packet['stage'] != 'EXPORTED_INDEPENDENTLY_FILE_VERIFIED_NATIVE_PROFILE_PENDING'
            or packet['seed'] != 842401 or packet['realm'] != 'WORLD-ZERO'
            or packet['original_creator'] != 'production_checkpoint_evidence'
            or packet['source_delivery_owner'] != 'pootscoot'
            or packet['publication']['commit'] != 'b4bc16d330308b1849abf9303e732b10c5773936'
            or d.fp(packet['candidate']) != PAYLOAD_FP
            or len(packet['geometry_and_raw_materials']['nodes']) != 3
            or sum(row['triangles'] for row in packet['geometry_and_raw_materials']['nodes']) != 292):
        raise RuntimeError('Exact finished reviewed Copperfall three-role source packet required')
    pins = source_pins(packet)
    for pin in pins:
        d._check(pin)
    payload = SOURCE / Path(packet['candidate']['path']).name
    if d.fingerprint(payload) != PAYLOAD_FP:
        raise RuntimeError('Exact retained subset payload required; never import full assembly')
    d.protect(d.load(args.baseline))
    value = {'schema': 'daedalus.codex-copperfall-subset-prepared.v1', 'utc': d._utc(),
             'stage': 'exact_copperfall_three_roles_prepared', 'baseline': d.pin(args.baseline),
             'manifest': d.pin(MANIFEST), 'glb': d.pin(payload), 'source_pins': pins,
             'native_source': d.pin(NATIVE), **{key: d.pin(path) for key, path in HELPERS.items()},
             'destination': DEST, 'label': label(), 'original_creator': packet['original_creator'],
             'source_delivery_owner': packet['source_delivery_owner'], 'seed': 842401, 'realm': 'WORLD-ZERO',
             'scope': 'Exact18732B GLB only: three static source roles and three owned raw linear PBR MICs; no actors/map/shared changes.',
             'source_view_limit': packet['source_view']['caption'],
             'native_appearance_collision_navigation_runtime': 'unverified'}
    args.folder.mkdir(parents=True)
    d.write_new(args.folder / 'prepared.json', value)
    print(json.dumps({'stage': value['stage'], 'prepared': d.pin(args.folder / 'prepared.json')}, indent=2))


def prepared(args):
    value = d.load(args.folder / 'prepared.json')
    for key in ('baseline', 'manifest', 'glb', 'native_source', *HELPERS):
        d._check(value[key])
    for pin in value['source_pins']:
        d._check(pin)
    if (value['destination'] != DEST or d.fp(value['manifest']) != MANIFEST_FP
            or d.fp(value['glb']) != PAYLOAD_FP or value['label'] != label()):
        raise RuntimeError('Retained exact identity differs')
    if args.baseline is not None and args.baseline.resolve() != Path(value['baseline']['path']).resolve():
        raise RuntimeError('Prepared baseline is immutable; do not silently select another increment')
    d.protect(d.load(value['baseline']['path']))
    return value


def config(value, args):
    lease = d._lease()
    cfg = {'destination': DEST, 'journal': str(args.folder / 'native.json'),
           'deadline_epoch': min(time.time() + 480, lease['at'] + lease['ttl'] - 60)}
    for key in ('manifest', 'glb', *HELPERS):
        cfg[key], cfg[key + '_fingerprint'] = value[key]['path'], d.fp(value[key])
    return cfg


def call_native(value, args, operation, timeout=120):
    if operation not in ('preflight', 'steps', 'readback'):
        raise ValueError('Known bounded exact-packet phase required')
    code = d.module_code(value)
    if operation == 'steps':
        code += '\ndef steps():\n    return (yield from scope[\'steps\'](' + repr(config(value, args)) + '))\n'
    else:
        code += '\ndef steps():\n    if False: yield\n    return scope[' + repr(operation) + '](' + repr(config(value, args)) + ')\n'
    reply = d.wire.call(d.wire.UNREAL, 'daedalus.steps', code=code, label=value['label'],
                        budget_ms=1, timeout=timeout, side='Unreal')
    return d.wire.obj(reply, side='Unreal', what='Copperfall three-role ' + operation)


def resources(args):
    return d._resources(args)


def validate_readback(observed, outputs):
    """A null/truncated bridge reply never becomes a completed native witness."""
    if (not isinstance(observed, dict) or observed.get('issues') != []
            or observed.get('triangles') != 292 or observed.get('unit_contract') != UNIT_CONTRACT
            or observed.get('world_placed') != 0 or observed.get('world_saved') is not False
            or observed.get('mesh_bindings_changed') is not False
            or observed.get('shared_material_modified') is not False
            or observed.get('provenance_metadata_verified') is not True
            or observed.get('source_payload_sha256') != PAYLOAD_FP['sha256']
            or observed.get('handoff_sha256') != MANIFEST_FP['sha256']
            or observed.get('persistent_assets_modified') is not False):
        raise RuntimeError('Native readback is missing/incomplete; preserve six saves and reconcile read-only')
    assets, items = observed.get('assets'), observed.get('items')
    if (not isinstance(assets, list) or len(assets) != 6 or not isinstance(items, list) or len(items) != 3
            or len(outputs) != 6 or len({row.get('path') for row in assets}) != 6
            or {row.get('path'): row.get('class') for row in assets}
               != {path: pin['class'] for path, pin in outputs.items()}
            or {row.get('source_role') for row in items} != set(ROLES)):
        raise RuntimeError('Exact six saved paths/classes and three reviewed role readbacks required')
    used = set()
    for row in items:
        role = row['source_role']
        geometry, material = row.get('geometry', {}), row.get('material', {})
        if (row.get('path') in used or row.get('material_path') in used
                or row.get('class') != 'StaticMesh' or outputs.get(row.get('path'), {}).get('class') != 'StaticMesh'
                or outputs.get(row.get('material_path'), {}).get('class') != 'MaterialInstanceConstant'
                or row.get('source_material') != ROLES[role][1]
                or geometry.get('issues') != [] or geometry.get('triangles') != ROLES[role][0]
                or geometry.get('observed_authored_translation_baked') is not True
                or geometry.get('build_scale3d') != [1., 1., 1.]
                or geometry.get('import_data_class') != 'InterchangeAssetImportData'
                or geometry.get('nanite_enabled') is not False
                or geometry.get('generate_lightmap_u_vs') is not False
                or material.get('readback_errors') != []):
            raise RuntimeError('Complete saved unit/material/source-role native witness required: ' + role)
        used.update((row['path'], row['material_path']))
    if used != set(outputs):
        raise RuntimeError('Every saved mesh/material must be accounted by the three role witnesses')
    for key in ('preflight', 'post_read_preflight'):
        guard = observed.get(key, {})
        if (guard.get('pie_running') is not False or guard.get('dirty_map_packages') != []
                or guard.get('dirty_content_packages') != [] or guard.get('queued_jobs') != 0
                or guard.get('other_running_generators') != [] or guard.get('unfinished_async_job_boxes') != 0
                or guard.get('remote_execution_lock_locked') is not False
                or guard.get('editor_world') != '/Game/Daedalus/DaedalusWorld.DaedalusWorld'):
            raise RuntimeError('Fresh clean native pre/post readback guard witness required')


def run(args):
    if any((args.folder / name).exists() for name in ('dispatch.json', 'dispatch.json.write-pending',
                                                     'native.json', 'native.json.write-pending')):
        raise RuntimeError('Retained dispatch/journal/pending write exists; reconcile without reimport')
    value = prepared(args); baseline = d.load(value['baseline']['path'])
    d._lease(); measured = resources(args)
    if d.locks().get('compute', {}).get('holder') is not None:
        raise RuntimeError('Compute owner active; no native mutation dispatched')
    before = d._scene_snapshot(); d._same_scene(before, baseline['scene'])
    admission = call_native(value, args, 'preflight')
    dispatch = {'utc': d._utc(), 'stage': 'compute_claim_dispatch_pending',
                'prepared': d.pin(args.folder / 'prepared.json'), 'scene_before': before,
                'resources': measured, 'native_admission': admission, 'replay_permitted': False}
    d.write_new(args.folder / 'dispatch.json', dispatch)
    claim = d.post('/lock', {'me': d.OWNER, 'name': 'compute', 'ttl': 600,
        'note': 'Sole-operator exact Copperfall3static roles292tri plus3rawPBR/emission MIC freshGLB import-save; no actors/map/render/build/PIE'})
    dispatch['compute_claim'] = claim
    d._write(args.folder / 'dispatch.json', dispatch)
    if claim.get('ok') is not True or not d.same_compute_lease(d.locks().get('compute', {}), claim.get('lock', {})):
        raise RuntimeError('Exact packet compute reservation not confirmed')
    dispatch.update(stage='native_dispatch_pending', resources_at_dispatch=resources(args))
    d._write(args.folder / 'dispatch.json', dispatch)
    try:
        result = call_native(value, args, 'steps', timeout=180)
        d.write_new(args.folder / 'reply.json', result)
        native = d.load(args.folder / 'native.json')
        rows = native.get('outputs', [])
        if (native.get('stage') != 'copperfall_subset_assets_saved_world_held'
                or native.get('save_return') is not True or len(rows) != 6
                or any(row.get('save_return') is not True for row in rows)):
            raise RuntimeError('All six exact owned first saves not confirmed; preserve partial state')
        outputs = {row['path']: {'class': row['class'], **d.fingerprint(d._asset_file(row['path']))} for row in rows}
        if len(outputs) != 6:
            raise RuntimeError('Six distinct native output packages required')
        d.protect(baseline)
        dispatch.update(stage='six_copperfall_packages_saved_world_held', outputs=outputs,
                        native=d.pin(args.folder / 'native.json'))
        d._write(args.folder / 'dispatch.json', dispatch)
        print(json.dumps({'stage': dispatch['stage'], 'outputs': outputs}, indent=2))
    except Exception as error:
        dispatch.update(stage='inspect_outcome_never_replay', error=str(error), error_type=type(error).__name__)
        d._write(args.folder / 'dispatch.json', dispatch)
        raise


def readback(args):
    if (args.folder / 'native-readback.json').exists() or (args.folder / 'readback.json').exists():
        raise RuntimeError('Retained successful readback exists; use file-only finalize without replay')
    value = prepared(args); baseline = d.load(value['baseline']['path'])
    dispatch = d.load(args.folder / 'dispatch.json')
    if dispatch['stage'] != 'six_copperfall_packages_saved_world_held':
        raise RuntimeError('Confirmed complete first-save journal required; reconcile partial separately')
    d._check(dispatch['native'])
    outputs = dispatch['outputs']
    for path, pin in outputs.items():
        if d.fingerprint(d._asset_file(path)) != d.fp(pin):
            raise RuntimeError('Saved output changed')
    current = d.locks().get('compute', {})
    if current.get('holder') and not d.same_compute_lease(current, dispatch['compute_claim']['lock']):
        raise RuntimeError('Another compute reservation active; preserve it')
    resources(args); d._lease()
    before = d._scene_snapshot(); d._same_scene(before, baseline['scene'])
    attempt_path = args.folder / ('readback-attempt-' + str(time.time_ns()) + '.json')
    attempt = {'utc': d._utc(), 'stage': 'read_only_dispatch_pending', 'persistent_mutation_requested': False,
               'native_source': value['native_source'], 'saved_outputs': outputs}
    d.write_new(attempt_path, attempt)
    try:
        observed = call_native(value, args, 'readback')
        attempt.update(stage='read_only_reply_returned', native=observed)
        d._write(attempt_path, attempt)
        validate_readback(observed, outputs)
        attempt['stage'] = 'read_only_reply_contract_verified'
        d._write(attempt_path, attempt)
    except Exception as error:
        attempt.update(stage='read_only_outcome_requires_reconciliation', error=str(error),
                       error_type=type(error).__name__, import_or_save_replay_permitted=False)
        d._write(attempt_path, attempt)
        raise
    after = d._scene_snapshot(); d._same_scene(after, baseline['scene']); d.protect(baseline)
    report = {'utc': d._utc(), 'stage': SAVED, 'issues': [], 'native': observed, 'outputs': outputs,
              'scene': after, 'map': d.fingerprint(d.MAP_FILE), 'prior_packages_preserved': len(baseline['packages']),
              'world_placed': 0, 'world_saved': False, 'source_files_preserved': len(baseline['candidate_source']),
              'original_receipts': {name: d.pin(args.folder / name) for name in ('dispatch.json', 'native.json', 'reply.json')},
              'limits': 'Three baseline source roles only; source symmetric bounds do not prove handedness. Native appearance/collision/navigation/gameplay remain separate.'}
    report['original_receipts']['verified_readback_attempt'] = d.pin(attempt_path)
    d.write_new(args.folder / 'native-readback.json', report)
    finalize(args)


def finalize(args):
    value = prepared(args); baseline = d.load(value['baseline']['path'])
    report = d.load(args.folder / 'native-readback.json')
    if report['stage'] != SAVED or report['issues']:
        raise RuntimeError('Completed native saved/readback witness required')
    validate_readback(report['native'], report['outputs'])
    for pin in report['original_receipts'].values():
        d._check(pin)
    if set(report['outputs']) & set(baseline['packages']):
        raise RuntimeError('New outputs overlap the protected prior baseline')
    backups = dict(baseline['package_backups'])
    folder = args.folder / 'saved-package-backups'; folder.mkdir(exist_ok=True)
    for path, pin in report['outputs'].items():
        source = d._asset_file(path)
        if d.fingerprint(source) != d.fp(pin):
            raise RuntimeError('Saved output changed before backup')
        if not path.startswith(DEST + '/'):
            raise RuntimeError('New package outside exact Copperfall destination')
        relative = path.split('.')[0][len(DEST) + 1:]
        target = folder / (relative + '.uasset')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        if d.fingerprint(target) != d.fp(pin):
            raise RuntimeError('New package backup differs')
        backups[path] = str(target)
    baseline.update(utc=d._utc(), stage='combined184_preserved_copperfall_three_roles_saved',
        packages={**baseline['packages'], **report['outputs']}, package_backups=backups,
        package_count=len(baseline['packages']) + len(report['outputs']),
        provenance={'previous_baseline': value['baseline'], 'increment': d.pin(args.folder / 'native-readback.json')})
    bp = args.folder / 'saved-production-baseline.json'
    if not bp.exists():
        d.write_new(bp, baseline)
    elif any(d.load(bp)[key] != baseline[key] for key in ('packages', 'package_backups', 'scene', 'map', 'provenance')):
        raise RuntimeError('Retained baseline differs')
    d.protect(d.load(bp))
    claim = d.load(args.folder / 'dispatch.json')['compute_claim']['lock']
    current = d.locks().get('compute', {})
    release = 'other_or_absent_lease_preserved'
    if d.same_compute_lease(current, claim):
        rp = args.folder / 'compute-release.json'
        if rp.exists() and d.load(rp).get('stage') == 'released_verified':
            raise RuntimeError('Retained release contradicts current packet lease')
        d._write(rp, {'utc': d._utc(), 'stage': 'unlock_dispatch_pending'})
        reply = d.post('/unlock', {'me': d.OWNER, 'name': 'compute'})
        if d.same_compute_lease(d.locks().get('compute', {}), claim):
            raise RuntimeError('Packet compute release unconfirmed')
        d._write(rp, {'utc': d._utc(), 'stage': 'released_verified', 'reply': reply})
        release = 'packet_lease_released_verified'
    marker = args.folder / 'readback.json'
    if not marker.exists():
        d.write_new(marker, {**report, 'baseline': d.pin(bp), 'compute_release': release})
    print(json.dumps({'stage': SAVED, 'packages': len(baseline['packages']), 'baseline': d.pin(bp)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run', 'readback', 'finalize'))
    parser.add_argument('--baseline', type=Path, help='Explicit current absolute saved baseline; mandatory for prepare.')
    parser.add_argument('--folder', type=Path, default=DEFAULT_FOLDER)
    parser.add_argument('--minimum-free-physical-mib', type=int, default=1024)
    parser.add_argument('--minimum-free-commit-mib', type=int, default=1536)
    args = parser.parse_args()
    if not args.folder.is_absolute():
        parser.error('--folder must be absolute')
    if args.minimum_free_physical_mib < 1024 or args.minimum_free_commit_mib < 1536:
        parser.error('Existing resource floors cannot be lowered')
    globals()[args.phase](args)
