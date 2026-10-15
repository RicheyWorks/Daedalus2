# SPDX-License-Identifier: MIT
"""Released Winter4 two-role source -> existing subset producer -> guarded intake.

No new bridge/exporter. prepare requires an actual semantic owner-release receipt;
run/readback require the exact current saved baseline and operator custody.
Existing dispatches/partial results forbid automatic import/save replay.
"""
import argparse
import ast
import json
import math
from pathlib import Path
import shutil
import time
from types import SimpleNamespace

import codex_qualified_static_delivery as d

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT.parent
NATIVE = ROOT / 'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_canal_water.py'
DEFAULT_FOLDER = TASK / 'native-ingestion/Winter4CanalStream1CoreR1'
ORIGINAL = Path('C:/Users/730ri/projects/D2-build/engines/unreal/art/claude-octets/Octet_Winter_4_Canal.glb')
SUBSET = Path('C:/Users/730ri/Documents/Codex/2026-10-13/task-3/subset-pipeline-source/connectors/claude-asset-pipeline/asset_pipeline/subset.py')
SOURCE = {'bytes': 348216, 'sha256': 'ad06dd2b3b95da8bc98ee07bcd7ff59fadbbc2d08af98cb74c4582b56c1ed5cd'}
LAYOUT = Path('C:/Users/730ri/projects/D2-build/engines/unreal/art/claude-octets/Octet_Winter_4.layout.json')
LAYOUT_FP = {'bytes': 4325, 'sha256': '6871dd71bd755b74e336f032b68ac15d1fc0edf2fc8c95f818b6f628ba1a3868'}
NAMES = ['Octet_Winter_4_Canal_Stream1', 'Octet_Winter_4_Canal_Stream1_Core']
DEST = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Winter4CanalWaterR1_ad06dd2b3b95da8b'
POLICY = 'owned_factor_alpha_parent_v1'
UNIT = 'gltf_authored_root_world_XZY_cm100_baked_build1_future_actor1_v1'
SAVED = 'canal_two_role_six_assets_saved_world_held'


def constants():
    tree = ast.parse(NATIVE.read_text(encoding='utf-8'))
    result = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('LABEL', 'PINS'):
                    result[target.id] = ast.literal_eval(node.value)
    return result


def validate_release(release):
    message = release['hub_message']
    if (release['schema'] != 'daedalus.canal-water-release.v1'
            or release['status'] != 'RELEASED_FOR_IMMUTABLE_TWO_NODE_SUBSET'
            or d.fp(release['original_source']) != SOURCE or release['selected_nodes'] != NAMES
            or release['producer_alias'] != 'unreal-team' or message['from'] != 'unreal-team'
            or type(message['id']) is not int or message['id'] <= 32359
            or message['to'] not in ('codex-play-guard', 'pootscoot-coordination', '*')
            or not message.get('body', {}).get('text')
            or any(release.get(key) is not True for key in
                   ('producer_confirmed_finished', 'producer_confirmed_unclaimed',
                    'producer_confirmed_not_inflight', 'operator_semantic_ack_verified'))):
        raise ValueError('exact actual producer release required; requests/advisory/pass counts cannot grant it')


def helper_paths(args):
    names = {'sunspool_source': 'daedalus_codex_sunspool_subset.py',
             'geometry_source': 'daedalus_codex_copperfall_subset.py',
             'miri_source': 'daedalus_codex_miri.py', 'catalogue_source': 'daedalus_codex_catalogue.py',
             'material_source': 'daedalus_codex_canal_material.py',
             'queue_source': 'daedalus_codex_qualified_static.py'}
    return {**{key: NATIVE.with_name(name) for key, name in names.items()}, 'subset_source': args.subset_source}


def requirements(args):
    print(json.dumps({'stage': 'RECEIVING_SOURCE_POLICY_NATIVE_UNVERIFIED', 'source': SOURCE, 'nodes': NAMES,
        'required_release_schema': 'daedalus.canal-water-release.v1',
        'release_is_not_inferred_from': ['advisory54PASS', 'bounded ledger no-match', 'an expired lease', 'a request message'],
        'material_policy': POLICY, 'unit_policy': UNIT, 'source_triangles': 2912,
        'expected_imported': {'StaticMesh': 2, 'MaterialInstanceConstant': 2},
        'expected_created': {'Material': 2}, 'first_saved_packages': 6,
        'guard_policy': 'existing labelled daedalus.steps catalogue guards, immutable pins, exact compute identity/deadline/resources/dirty/world/PIE, no replay',
        'native_ready': False, 'source_preparation': 'prepare requires --baseline ABS --release ABS; exports only to a fresh owned folder through pinned existing subset.py',
        'limitations': 'No global setting/shared-parent/opaque-profile changes. Native shader enum/graph and exact geometry must pass before saves; no world placement or simulation acceptance.'}, indent=2))


def prepare(args):
    if not args.baseline or not args.baseline.is_absolute() or not args.release or not args.release.is_absolute():
        raise ValueError('explicit absolute current --baseline and actual --release receipt required')
    if args.folder.exists():raise RuntimeError('retained packet preparation exists; preserve partial outcomes')
    release = d.load(args.release);validate_release(release)
    if d.fingerprint(args.source) != SOURCE:raise RuntimeError('exact original whole-source bytes required')
    if d.fingerprint(LAYOUT) != LAYOUT_FP:raise RuntimeError('exact layout required for seed/theme provenance')
    layout = d.load(LAYOUT)
    if layout.get('seed') != 4 or layout.get('theme') != 'Winter' or layout.get('name') != 'Octet_Winter_4':
        raise RuntimeError('layout Winter/seed4 evidence differs')
    pins = constants()['PINS'];helpers = helper_paths(args)
    for key, path in helpers.items():
        if d.fingerprint(path) != pins[key]:raise RuntimeError('reviewed helper differs: ' + key)
    base = d.load(args.baseline);d.protect(base)
    producer = {'__name__': '_codex_canal_existing_subset_producer'}
    exec(compile(args.subset_source.read_bytes(), str(args.subset_source), 'exec'), producer)
    plan = producer['make_plan'](str(args.source), NAMES, SOURCE)
    args.folder.mkdir(parents=True)
    d.write_new(args.folder / 'preparation-intent.json', {'utc': d._utc(), 'stage': 'fresh_source_derivative_dispatch_pending',
        'release': d.pin(args.release), 'baseline': d.pin(args.baseline), 'source': d.pin(args.source),
        'subset_source': d.pin(args.subset_source), 'replay_permitted': False, 'native_ready': False})
    plan_file = args.folder / 'source-plan.json';d.write_new(plan_file, plan)
    payload = args.folder / 'Winter4_Canal_Stream1_Core_R1.glb'
    exported = producer['export_subset'](plan, str(payload))
    d.write_new(args.folder / 'source-export.json', exported)
    admitted = producer['admit'](plan, str(payload), d.fingerprint(payload), include_geometry=True)
    d.write_new(args.folder / 'source-admission.json', admitted)
    if admitted['triangles'] != 2912 or admitted['nodes'] != NAMES or len(admitted['geometry']['nodes']) != 2:
        raise RuntimeError('exact two-role actual-file admission required')
    d.protect(base)
    handoff = {'schema': 'daedalus.canal-water-handoff.v1', 'stage': 'DERIVED_FILE_ADMITTED_NATIVE_PENDING',
        'source_team': 'Team Claude', 'original_creator': release.get('original_creator', 'unknown'),
        'seed': 4, 'original_source': d.pin(args.source), 'selected_nodes': NAMES,
        'original_layout': d.pin(LAYOUT),
        'candidate': d.pin(payload), 'plan': d.pin(plan_file),
        'admission': d.pin(args.folder / 'source-admission.json'), 'release': d.pin(args.release),
        'material_policy': POLICY, 'unit_contract': UNIT, 'native_ready': False,
        'narrative_chemistry': {'observed_source': 'Winter/seed4/sky-canal water and foam',
            'canonical_realm': 'unknown', 'story_player_goal': 'unknown', 'chemistry_and_water_simulation': 'unknown',
            'implemented_scope': 'preserve factor-only water/foam rendering on two static meshes; no fluid/survival/quest mechanic',
            'new_rule_change': 'none'},
        'quality_scope': 'Preserve separate water/core silhouette and source alpha/emission contrast; no changed original or claimed visual transfer/BAR acceptance.'}
    manifest = args.folder / 'handoff.json';d.write_new(manifest, handoff)
    value = {'utc': d._utc(), 'stage': 'exact_released_canal_derived_packet_prepared',
        'baseline': d.pin(args.baseline), 'manifest': d.pin(manifest), 'glb': d.pin(payload),
        'native_source': d.pin(NATIVE), 'helpers': {key: d.pin(path) for key, path in helpers.items()},
        'destination': DEST, 'label': constants()['LABEL'], 'material_policy': POLICY,
        'source_pins': [d.pin(args.source), d.pin(LAYOUT), d.pin(args.release), d.pin(plan_file),
                        d.pin(args.folder / 'source-admission.json'), d.pin(args.folder / 'source-export.json')]}
    d.write_new(args.folder / 'prepared.json', value)
    print(json.dumps({'stage': value['stage'], 'candidate': value['glb'], 'native_ready': False}, indent=2))


def prepared(args):
    value = d.load(args.folder / 'prepared.json')
    for pin in [value['baseline'], value['manifest'], value['glb'], value['native_source'],
                *value['helpers'].values(), *value['source_pins']]:d._check(pin)
    validate_release(d.load(d.load(value['manifest']['path'])['release']['path']))
    return value


def resources(args):
    return d._resources(args)


def configuration(value, args, claim=None):
    lease = d._lease();deadline = min(time.time()+600, lease['at']+lease['ttl']-30)
    if claim is not None:deadline = min(deadline, claim['at']+claim['ttl']-30)
    cfg = {'destination': DEST, 'material_policy': POLICY, 'journal': str(args.folder / 'native.json'),
        'manifest': value['manifest']['path'], 'manifest_fingerprint': d.fp(value['manifest']),
        'glb': value['glb']['path'], 'candidate_sha256': value['glb']['sha256'], 'deadline_epoch': deadline}
    for key, pin in value['helpers'].items():cfg[key], cfg[key+'_fingerprint'] = pin['path'], d.fp(pin)
    return cfg


def native(value, args, operation, claim=None):
    if operation not in ('preflight','steps','readback'):raise ValueError('known exact phase required')
    code = d.module_code(value);cfg = configuration(value, args, claim)
    if operation == 'steps':code += '\ndef steps():\n    return (yield from scope[\'steps\'](' + repr(cfg) + '))\n'
    else:code += '\ndef steps():\n    if False: yield\n    return scope[' + repr(operation) + '](' + repr(cfg) + ')\n'
    return d.wire.obj(d.wire.call(d.wire.UNREAL, 'daedalus.steps', code=code, label=value['label'],
        budget_ms=1, timeout=180, side='Unreal'), side='Unreal', what='exact Canal '+operation)


def validate_native(report, paths=None, value=None):
    if (not isinstance(report, dict) or report.get('issues') != [] or report.get('triangles') != 2912
            or report.get('unit_contract') != UNIT or report.get('material_policy') != POLICY
            or report.get('world_placed') != 0 or report.get('world_saved') is not False
            or report.get('imported_object_count') != 4 or report.get('created_parent_count') != 2
            or len(report.get('assets', [])) != 6 or len(report.get('items', [])) != 2
            or report.get('provenance_metadata_verified') is not True
            or report.get('source_admission_verified') is not True
            or report.get('shared_material_modified') is not False
            or report.get('original_source_sha256') != SOURCE['sha256']):
        raise RuntimeError('explicit exact six-object/geometry/material native readback required')
    actual = {row['path']: row['class'] for row in report['assets']}
    if len(actual) != 6 or sorted(actual.values()) != ['Material','Material','MaterialInstanceConstant','MaterialInstanceConstant','StaticMesh','StaticMesh']:
        raise RuntimeError('exact class accounting differs')
    if paths is not None and set(actual) != set(paths):raise RuntimeError('native paths differ from six first-save outputs')
    if {row['source_role'] for row in report['items']} != set(NAMES):raise RuntimeError('exact two roles required')
    for path in actual:
        if not path.startswith(DEST+'/'):raise RuntimeError('native output outside exact owned namespace')
    if value is None or report.get('source_payload_sha256') != value['glb']['sha256'] or report.get('handoff_sha256') != value['manifest']['sha256']:
        raise RuntimeError('exact native payload/handoff identity witnesses required')
    for key in ('preflight','post_read_preflight'):
        guard = report.get(key)
        if (not isinstance(guard, dict) or guard.get('editor_world') != '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
                or any(guard.get(k) != [] for k in ('dirty_map_packages','dirty_content_packages','other_running_generators'))
                or any(guard.get(k) != 0 for k in ('queued_jobs','unfinished_async_job_boxes'))
                or guard.get('pie_running') is not False or guard.get('remote_execution_lock_locked') is not False):
            raise RuntimeError('explicit clean pre/post native guard witnesses required')
    used = set()
    for row in report['items']:
        if (row['geometry']['issues'] or row['geometry']['triangles'] != 1456
                or row['material'].get('issues') != [] or actual.get(row['path']) != 'StaticMesh'
                or actual.get(row['material_path']) != 'MaterialInstanceConstant'
                or actual.get(row['owned_parent']) != 'Material'):
            raise RuntimeError('strict geometry/opacity/material witness differs')
        graph = row['material'].get('graph', {})
        proof = graph.get('disconnected_properties', {})
        if (graph.get('node_count') != 6 or graph.get('graph_verified') is not True
                or proof.get('root_count') != 30 or proof.get('disconnected_root_count') != 25
                or proof.get('raw_customized_uv_connections_inspected') is not True
                or proof.get('active_customized_uvs') != 0
                or proof.get('all_eight_customized_uv_compile_paths_inactive') is not True
                or len(proof.get('input_expression_references', {})) != 30):
            raise RuntimeError('explicit complete native text/default graph witness required')
        for key in ('default_inputs', 'owned_input_delta'):
            evidence = proof.get(key, {})
            file = Path(evidence.get('file', ''))
            if (not file.is_absolute() or file.suffix != '.t3d'
                    or evidence.get('class') != '/Script/Engine.MaterialEditorOnlyData'
                    or evidence.get('default_archetype_header_verified') is not True
                    or evidence.get('export_return') is not True or evidence.get('errors') != []
                    or type(evidence.get('bytes')) is not int or not 0 < evidence['bytes'] <= 8 * 1024 * 1024
                    or d.fingerprint(file) != d.fp(evidence)):
                raise RuntimeError('exact retained native graph text bytes required')
        triple = {row['path'],row['material_path'],row['owned_parent']}
        if len(triple) != 3 or used & triple:raise RuntimeError('role mappings must be disjoint one-to-one triples')
        used.update(triple)
    if used != set(actual):raise RuntimeError('all six exact objects must be accounted by role triples')


def run(args):
    if (args.folder/'dispatch.json').exists() or (args.folder/'native.json').exists():
        raise RuntimeError('retained dispatch; reconcile, never repeat import')
    value = prepared(args);base = d.load(value['baseline']['path']);d.protect(base)
    d._lease();measured = resources(args)
    if d.locks().get('compute', {}).get('holder'):raise RuntimeError('compute owner active')
    before = d._scene_snapshot();d._same_scene(before, base['scene'])
    admission = native(value, args, 'preflight')
    if not isinstance(admission, dict) or admission.get('expected_saved_objects') != 6:
        raise RuntimeError('explicit native admission required')
    dispatch = {'utc': d._utc(), 'stage': 'compute_claim_dispatch_pending', 'resources': measured,
        'native_admission': admission, 'scene_before': before, 'replay_permitted': False}
    d.write_new(args.folder/'dispatch.json', dispatch)
    claim = d.post('/lock', {'me': d.OWNER, 'name': 'compute', 'ttl': 600,
        'note': 'Exact released Winter4 two-role water asset intake:4imports+2ownedrawalpha parents,6firstsaves/readback. Preserve143actors211packages184sources/map72cb/camera. NoPIE/placement/map-save/restart.'})
    dispatch['compute_claim'] = claim;d._write(args.folder/'dispatch.json', dispatch)
    if claim.get('ok') is not True or not d.same_compute_lease(d.locks().get('compute', {}), claim['lock']):
        raise RuntimeError('exact compute claim not confirmed')
    try:
        reply = native(value, args, 'steps', claim['lock']);d.write_new(args.folder/'reply.json', reply)
        report = d.load(args.folder/'native.json')
        rows = report.get('outputs', [])
        if (report.get('stage') != SAVED or report.get('save_return') is not True
                or report.get('completed_count') != 6 or len(rows) != 6
                or any(row['save_return'] is not True for row in rows)):
            raise RuntimeError('six true first saves required; preserve partial state')
        validate_native(report['final_observed'], [row['path'] for row in rows], value)
    except Exception as exc:
        d.write_new(args.folder/'run-failure.json', {'utc': d._utc(), 'stage': 'hold_preserve_partial_no_replay',
            'error': str(exc), 'error_type': type(exc).__name__})
        raise
    print(json.dumps({'stage': report['stage'], 'completed_count': report['completed_count'], 'world_placed': 0}, indent=2))


def readback(args):
    value = prepared(args);base = d.load(value['baseline']['path']);d.protect(base)
    d._lease();resources(args)
    claim = d.load(args.folder/'dispatch.json')['compute_claim']['lock']
    if not d.same_compute_lease(d.locks().get('compute', {}), claim):raise RuntimeError('exact compute custody required')
    report = d.load(args.folder/'native.json');rows = report['outputs']
    if report.get('stage') != SAVED or report.get('save_return') is not True or len(rows) != 6 or any(r['save_return'] is not True for r in rows):
        raise RuntimeError('exact complete first-save journal required')
    attempt = args.folder/('readback-attempt-'+str(time.time_ns())+'.json')
    witness = {'utc': d._utc(), 'stage': 'read_only_dispatch_pending',
               'prepared': d.pin(args.folder/'prepared.json'), 'native_journal': d.pin(args.folder/'native.json')}
    d.write_new(attempt, witness)
    try:
        observed = native(value, args, 'readback', claim)
        witness.update(stage='read_only_reply_returned', native=observed)
        d._write(attempt, witness)
        validate_native(observed, [r['path'] for r in rows], value)
        if observed['source_payload_sha256'] != value['glb']['sha256']:raise RuntimeError('actual payload identity differs')
        after = d._scene_snapshot();d._same_scene(after, base['scene']);d.protect(base)
        witness.update(utc=d._utc(), stage='exact_six_native_readback_verified', scene=after,
                       unchanged_map=base['map'])
        d._write(attempt, witness)
    except Exception as exc:
        witness.update(stage='read_only_failed_preserve_outcome', error=str(exc), error_type=type(exc).__name__)
        d._write(attempt, witness)
        raise
    print(json.dumps({'stage': witness['stage'], 'readback_receipt': d.pin(attempt)}, indent=2))


def finalize(args):
    if not args.readback_receipt or not args.readback_receipt.is_absolute():
        raise ValueError('explicit absolute --readback-receipt for the verified unique read-only attempt required')
    if args.readback_receipt.resolve().parent != args.folder.resolve():
        raise ValueError('readback receipt must belong to this exact delivery folder')
    value = prepared(args);base = d.load(value['baseline']['path']);d.protect(base)
    d._lease();resources(args)
    claim = d.load(args.folder/'dispatch.json')['compute_claim']['lock']
    if not d.same_compute_lease(d.locks().get('compute', {}), claim):raise RuntimeError('exact compute custody required')
    report = d.load(args.folder/'native.json');rows = report['outputs']
    witness = d.load(args.readback_receipt)
    if (witness.get('stage') != 'exact_six_native_readback_verified'
            or report.get('stage') != SAVED or report.get('save_return') is not True
            or len(rows) != 6 or any(r['save_return'] is not True for r in rows)):
        raise RuntimeError('exact saved journal and explicit verified native readback required')
    d._check(witness['prepared']);d._check(witness['native_journal'])
    observed = witness['native'];validate_native(observed, [r['path'] for r in rows], value)
    if observed['source_payload_sha256'] != value['glb']['sha256']:raise RuntimeError('actual payload identity differs')
    after = witness['scene'];d._same_scene(after, base['scene'])
    backups = args.folder/'saved-package-backups';backups.mkdir()
    for row in rows:
        path = row['path'];file = d._asset_file(path)
        if path in base['packages']:raise RuntimeError('saved path already in prior preservation ledger')
        relative = file.relative_to(Path('C:/Unreal/DaedalusRealm/Content'))
        target = backups/relative;target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():raise RuntimeError('retained backup; reconcile instead of overwriting')
        shutil.copy2(file, target);fp = d.fingerprint(file)
        if d.fingerprint(target) != fp:raise RuntimeError('saved package backup mismatch')
        base['packages'][path] = {'path': str(file), **fp};base['package_backups'][path] = str(target)
    base.update(utc=d._utc(), stage='saved'+str(len(base['packages']))+'_canal_water_six_assets_world_held', scene=after,
        package_count=len(base['packages']),
        provenance={'previous_baseline': value['baseline'], 'packet': value['manifest'], 'native': d.pin(args.folder/'native.json')})
    d.protect(base);bp = args.folder/'saved-production-baseline.json';d.write_new(bp, base)
    finished = {'utc': d._utc(), 'stage': 'canal_two_role_asset_saves_independently_readback_complete',
        'issues': [], 'native': observed, 'outputs': rows, 'baseline': d.pin(bp), 'saved_map': base['map'],
        'native_readback_receipt': d.pin(args.readback_receipt),
        'protected_packages': len(base['packages']), 'actors': len(after['actors']),
        'cycle_metrics': {'imported_assets': 4, 'native_created_assets': 2, 'new_saved_packages': 6,
                         'world_placed': 0, 'map_save_calls': 0, 'new_island_versions': 0},
        'limits': 'Asset-only saves; native appearance, whole46assembly, world placement, flow/fluid/chemistry/survival and runtime acceptance remain separate.'}
    d.write_new(args.folder/'readback.json', finished)
    if not d.same_compute_lease(d.locks().get('compute', {}), claim):raise RuntimeError('custody changed before release; do not unlock another turn')
    released = d.post('/unlock', {'me': d.OWNER, 'name': 'compute'})
    if d.same_compute_lease(d.locks().get('compute', {}), claim):raise RuntimeError('compute release unconfirmed')
    d.write_new(args.folder/'compute-release.json', {'utc': d._utc(), 'reply': released})
    print(json.dumps({k: finished[k] for k in ('stage','baseline','protected_packages','actors','cycle_metrics')}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('requirements','prepare','run','readback','finalize'))
    p.add_argument('--folder', type=Path, default=DEFAULT_FOLDER)
    p.add_argument('--source', type=Path, default=ORIGINAL)
    p.add_argument('--subset-source', type=Path, default=SUBSET)
    p.add_argument('--baseline', type=Path);p.add_argument('--release', type=Path)
    p.add_argument('--readback-receipt', type=Path)
    p.add_argument('--minimum-free-physical-mib', type=float, default=1024)
    p.add_argument('--minimum-free-commit-mib', type=float, default=1536)
    args = p.parse_args()
    if (not math.isfinite(args.minimum_free_physical_mib) or not math.isfinite(args.minimum_free_commit_mib)
            or args.minimum_free_physical_mib < 1024 or args.minimum_free_commit_mib < 1536):
        p.error('do not lower the existing resource floors')
    globals()[args.phase](args)
