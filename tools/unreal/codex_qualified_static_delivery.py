# SPDX-License-Identifier: MIT
"""Deliver a bounded qualified static packet through the proven Interchange route.

Preparation is file-only. Each import is dispatched once; uncertain outcomes
require read-only reconciliation. A supplied current baseline protects installed
source, saved packages, scene, map and user saves without replaying old runners.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import time
import urllib.request

from codex_static_intake_delivery import (
    _check, _lease, _resources, _scene_snapshot, _utc, _write,
    fingerprint, write_new, _asset_file, wire, MAP_FILE,
)

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_qualified_static.py'
SHARED = NATIVE.with_name('daedalus_codex_catalogue.py')
HUB = 'http://127.0.0.1:9890'
OWNER = 'codex-play-guard'
PREFIX = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/'


def _same_scene(actual, expected):
    """Protect every record in the supplied increment, including new construction."""
    if (actual['world'] != '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
            or actual['world'] != expected['world']
            or len(actual['actors']) != len(expected['actors'])
            or {row['path']: row for row in actual['actors']} != {row['path']: row for row in expected['actors']}):
        raise RuntimeError('Exact selected-baseline actor records/world differ; preserve current work')
    if any(abs(actual['camera'][group][key] - number) > 1e-5
           for group in ('location', 'rotation') for key, number in expected['camera'][group].items()):
        raise RuntimeError('Selected baseline camera changed; reconcile the explicit viewport witness')


def pin(path):
    return {'path': str(Path(path).resolve()), **fingerprint(path)}


def fp(value):
    return {key: value[key] for key in ('bytes', 'sha256')}


def post(path, value):
    request = urllib.request.Request(HUB + path, data=json.dumps(value).encode(),
                                    headers={'Content-Type': 'application/json'}, method='POST')
    return json.load(urllib.request.urlopen(request, timeout=10))


def locks():
    return json.load(urllib.request.urlopen(HUB + '/locks', timeout=10))


def same_compute_lease(actual, claimed):
    """A shared holder name does not identify this packet's reservation."""
    return (claimed.get('holder') == OWNER and claimed.get('at', 0) > 0
            and claimed.get('ttl', 0) > 0
            and all(actual.get(key) == claimed.get(key) for key in ('holder', 'at', 'ttl')))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def protect(baseline):
    """Verify the explicitly selected installed/saved baseline; never edit it."""
    live = Path(baseline['canonical_plugin'])
    actual = {str(p.relative_to(live)).replace('\\', '/'): fingerprint(p)
              for p in sorted((live / 'Source').rglob('*')) if p.is_file()}
    if actual != baseline['candidate_source'] or len(actual) != 184:
        raise RuntimeError('Current accepted184 source differs')
    for value in baseline['binaries'].values():
        _check(value)
    _check(baseline['module_receipt'])
    if fingerprint(live / 'DaedalusLink.uplugin') != baseline['descriptor']:
        raise RuntimeError('Installed descriptor differs')
    for relative, expected in baseline['runtime_catalogs'].items():
        if fingerprint(live / relative) != expected:
            raise RuntimeError('Runtime catalogue differs: ' + relative)
    for asset, expected in baseline['packages'].items():
        if fingerprint(_asset_file(asset)) != fp(expected):
            raise RuntimeError('Saved package differs: ' + asset)
        if fingerprint(baseline['package_backups'][asset]) != fp(expected):
            raise RuntimeError('Saved package backup differs: ' + asset)
    if fingerprint(MAP_FILE) != fp(baseline['map']):
        raise RuntimeError('Saved production map differs; preserve current work')
    if fingerprint(baseline['map_backup']) != fp(baseline['map']):
        raise RuntimeError('Saved map backup differs')
    for row in baseline['user_saves']:
        path = Path(row['path'])
        if path.exists() != row['exists'] or row['exists'] and fingerprint(path) != row['original']:
            raise RuntimeError('User save differs; preserve current work')
    if Path('C:/Unreal/DaedalusRealm/Saved/DaedalusDesktopGames').exists():
        raise RuntimeError('Original arcade save-directory absence differs')


def validate_items(items):
    if not isinstance(items, list) or not 1 <= len(items) <= 3:
        raise ValueError('One to three individually qualified static items required')
    names, destinations = set(), set()
    for item in items:
        name, destination = item['name'], item['destination']
        if (not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,100}', name) or name in names
                or not destination.startswith(PREFIX) or destination.endswith('/')
                or any(token in destination for token in ('..', '//', '.'))
                or item['fingerprint']['sha256'][:16] not in destination
                or destination in destinations):
            raise ValueError('Distinct qualified identity and fresh owned hash destination required')
        names.add(name); destinations.add(destination)
        for path_key, fingerprint_key in (('fbx', 'fingerprint'), ('sidecar', 'sidecar_fingerprint')):
            if fingerprint(item[path_key]) != item[fingerprint_key]:
                raise ValueError('Qualified payload changed: ' + name)
        if (Path(item['fbx']).suffix.lower() != '.fbx' or not 1 <= item['triangles'] <= 3000
                or item['source_unit_scale_factor'] != 100
                or item['mesh_geometry_count'] != 1 or item['mesh_model_count'] != 1
                or any(item[key] != 0 for key in ('animations', 'animation_curves', 'deformers',
                                                'textures', 'videos', 'authored_ucx'))):
            raise ValueError('Qualified bounded static source profile differs: ' + name)
        if not item.get('provenance') or not item.get('rgba_bytes'):
            raise ValueError('Exact palette and evidence provenance required')


def label():
    tree = ast.parse(NATIVE.read_text(encoding='utf-8'))
    return next(ast.literal_eval(row.value) for row in tree.body if isinstance(row, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'LABEL' for target in row.targets))


def prepared(args):
    value = load(args.folder / 'prepared.json')
    for key in ('qualification', 'baseline', 'native_source', 'shared_source'):
        _check(value[key])
    for value_pin in value['source_pins']:
        _check(value_pin)
    validate_items(value['items'])
    protect(load(value['baseline']['path']))
    return value


def prepare(args):
    if args.folder.exists():
        raise RuntimeError('Retained delivery folder exists; never replace preparation')
    qualification, baseline = load(args.qualification), load(args.baseline)
    if qualification.get('stage') != 'qualified_static_candidates_source_only':
        raise RuntimeError('Qualified finished source packet required')
    if qualification.get('source_views_personally_inspected_by_operator') is not True:
        raise RuntimeError('Operator must inspect exact retained source views before preparation')
    validate_items(qualification['items'])
    for value in qualification['source_pins']:
        _check(value)
    protect(baseline)
    value = {'schema': 'daedalus.codex-qualified-static-prepared.v1',
             'stage': 'qualified_static_packet_prepared', 'utc': _utc(),
             'items': qualification['items'], 'source_pins': qualification['source_pins'],
             'qualification': pin(args.qualification), 'baseline': pin(args.baseline),
             'native_source': pin(NATIVE), 'shared_source': pin(SHARED), 'label': label(),
             'scope': 'New static packages only; placement and playability separate.'}
    args.folder.mkdir(parents=True)
    write_new(args.folder / 'prepared.json', value)
    print(json.dumps({'stage': value['stage'], 'items': [item['name'] for item in value['items']],
                      'prepared': pin(args.folder / 'prepared.json')}, indent=2))


def config(value, args, lease):
    return {'items': value['items'], 'journal': str(args.folder / 'native.json'),
            'deadline_epoch': min(time.time() + 480, lease['at'] + lease['ttl'] - 60),
            'shared_source': value['shared_source']['path'],
            'shared_source_fingerprint': fp(value['shared_source'])}


def module_code(value):
    return ("from pathlib import Path\nimport hashlib\nsource=" + repr(value['native_source']['path'])
            + "\nraw=Path(source).read_bytes()\nif hashlib.sha256(raw).hexdigest()!="
            + repr(value['native_source']['sha256']) + ":raise RuntimeError('pinned qualified-static module changed')\n"
            + "scope={'__name__':'_codex_qualified_static_delivery'}\nexec(compile(raw,source,'exec'),scope)\n")


def read_native(value, cfg, operation):
    if operation not in ('preflight', 'readback'):
        raise ValueError('Read-only native entry required')
    code = (module_code(value) + '\ndef steps():\n    if False: yield\n    return scope['
            + repr(operation) + '](' + repr(cfg) + ')\n')
    return wire.obj(wire.call(wire.UNREAL, 'daedalus.steps', code=code, label=value['label'],
                             budget_ms=1, timeout=90, side='Unreal'),
                    side='Unreal', what='qualified-static ' + operation)


def run(args):
    path = args.folder / 'dispatch.json'
    if path.exists() or (args.folder / 'native.json').exists():
        raise RuntimeError('Retained dispatch exists; inspect outcome, never replay')
    value = prepared(args); baseline = load(value['baseline']['path'])
    lease, resources = _lease(), _resources(args)
    current = locks()
    if current.get('compute', {}).get('holder') is not None:
        raise RuntimeError('Current compute owner must finish its bounded resource window')
    scene = _scene_snapshot(); _same_scene(scene, baseline['scene'])
    admission = read_native(value, config(value, args, lease), 'preflight')
    d = {'schema': 'daedalus.codex-qualified-static-dispatch.v1', 'utc': _utc(),
         'stage': 'compute_claim_dispatch_pending', 'replay_permitted': False,
         'resources': resources, 'scene_before': scene, 'native_preflight': admission,
         'prepared': pin(args.folder / 'prepared.json')}
    write_new(path, d)
    d['compute_claim'] = post('/lock', {'me': OWNER, 'name': 'compute', 'ttl': 600,
        'note': 'Sole-operator qualified static1-3asset import/save, explicit Interchange existing profile, no build/render/PIE; fresh OS floors and saved baseline'})
    _write(path, d)
    claimed = d['compute_claim'].get('lock', {})
    if d['compute_claim'].get('ok') is not True or not same_compute_lease(locks().get('compute', {}), claimed):
        raise RuntimeError('Compute reservation not confirmed; no import dispatched')
    cfg = config(value, args, _lease())
    code = module_code(value) + '\ndef steps():\n    return (yield from scope[\'steps\'](' + repr(cfg) + '))\n'
    d.update(stage='native_dispatch_pending', resources_at_dispatch=_resources(args),
             code_sha256=hashlib.sha256(code.encode()).hexdigest())
    _write(path, d)
    try:
        reply = wire.call(wire.UNREAL, 'daedalus.steps', code=code, label=value['label'],
                          budget_ms=1, timeout=180, side='Unreal')
        write_new(args.folder / 'reply.json', reply)
        d.update(stage='native_returned_inspect_saved_journal', reply=pin(args.folder / 'reply.json'))
        native = load(args.folder / 'native.json')
        rows = native.get('items', [])
        if len(rows) != len(value['items']) or any(row.get('save_return') is not True for row in rows):
            raise RuntimeError('Not every first asset save confirmed; inspect retained journal')
        outputs = {row['native_path']: fingerprint(_asset_file(row['native_path'])) for row in rows}
        protect(baseline)
        d.update(stage='qualified_static_assets_saved_world_held', outputs=outputs,
                 native=pin(args.folder / 'native.json'))
        _write(path, d)
        print(json.dumps({'stage': d['stage'], 'outputs': outputs,
              'measurements': [{key: row.get(key) for key in ('name', 'import_s', 'save_s', 'save_return')} for row in rows]}, indent=2))
    except Exception as exc:
        d.update(stage='outcome_requires_inspection_no_replay', error_type=type(exc).__name__, error=str(exc))
        _write(path, d)
        raise


def readback(args):
    output = args.folder / 'native-readback.json'
    if output.exists():
        raise RuntimeError('Retained native readback exists; use filesystem-only finalize')
    value = prepared(args); baseline = load(value['baseline']['path'])
    d = load(args.folder / 'dispatch.json'); native = load(args.folder / 'native.json')
    rows = native.get('items', [])
    selected = args.readback_names or [item['name'] for item in value['items']]
    known = {item['name']: item for item in value['items']}
    saved = {row['name']: row for row in rows if row.get('save_return') is True}
    if (not selected or len(selected) != len(set(selected))
            or not set(selected).issubset(known) or not set(selected).issubset(saved)):
        raise RuntimeError('Explicit saved subset required for partial read-only reconciliation; no mutation fallback')
    expected_paths = {known[name]['destination'] + '/' + name + '.' + name for name in selected}
    if {saved[name]['native_path'] for name in selected} != expected_paths:
        raise RuntimeError('Saved output identities differ')
    lease = _lease(); _resources(args)
    scene = _scene_snapshot(); _same_scene(scene, baseline['scene'])
    original_receipts = {name: pin(args.folder / name) for name in ('dispatch.json', 'native.json')}
    outputs = {path: fingerprint(_asset_file(path)) for path in expected_paths}
    cfg = config(value, args, lease)
    cfg['readback_names'] = selected
    observed = read_native(value, cfg, 'readback')
    after = _scene_snapshot(); _same_scene(after, baseline['scene'])
    protect(baseline)
    for path, expected in outputs.items():
        if fingerprint(_asset_file(path)) != expected:
            raise RuntimeError('New saved package changed during readback')
    for value_pin in original_receipts.values():
        _check(value_pin)
    report = {'schema': 'daedalus.codex-qualified-static-readback.v1', 'utc': _utc(),
              'stage': 'qualified_static_assets_saved_readback_complete', 'issues': [],
              'native_readback': observed, 'outputs': outputs, 'scene': after,
              'map': fingerprint(MAP_FILE), 'prior_packages_preserved': len(baseline['packages']),
              'total_tracked_packages': len(baseline['packages']) + len(outputs),
              'source_files_preserved': 184, 'world_placed': 0, 'world_saved': False,
              'readback_names': selected,
              'not_read_back_names': [name for name in known if name not in selected],
              'original_receipts': original_receipts,
              'import_replayed': False, 'save_replayed': False,
              'limits': 'Saved static geometry/material readback only. Appearance, collision and playable acceptance separate.'}
    write_new(output, report)
    finalize(args)


def finalize(args):
    """Finish local backups/baseline/release without any native import/save call."""
    value = prepared(args); baseline = load(value['baseline']['path'])
    output = args.folder / 'native-readback.json'
    report = load(output)
    if report['stage'] != 'qualified_static_assets_saved_readback_complete' or report['issues']:
        raise RuntimeError('Completed native read-only witness required')
    for value_pin in report['original_receipts'].values():
        _check(value_pin)
    outputs = report['outputs']
    for asset, expected in outputs.items():
        if fingerprint(_asset_file(asset)) != expected:
            raise RuntimeError('Saved output changed before local finalization')
    backups = dict(baseline['package_backups'])
    backup_folder = args.folder / 'saved-package-backups'
    backup_folder.mkdir(exist_ok=True)
    for asset, expected in outputs.items():
        target = backup_folder / (_asset_file(asset).name)
        if not target.exists():
            shutil.copy2(_asset_file(asset), target)
        if fingerprint(target) != expected:
            raise RuntimeError('New saved package backup differs')
        backups[asset] = str(target)
    extended = dict(baseline)
    extended.update(utc=_utc(), stage='combined184_preserved_qualified_static_increment_saved',
                    packages={**baseline['packages'], **outputs},
                    package_backups=backups,
                    package_count=len(baseline['packages']) + len(outputs),
                    provenance={'previous_baseline': value['baseline'], 'increment': pin(output)})
    baseline_path = args.folder / 'saved-production-baseline.json'
    if baseline_path.exists():
        existing = load(baseline_path)
        if any(existing[key] != extended[key] for key in ('candidate_source', 'packages', 'package_backups', 'map', 'scene', 'provenance')):
            raise RuntimeError('Retained extended baseline differs; preserve')
    else:
        write_new(baseline_path, extended)
    protect(load(baseline_path))
    current = locks().get('compute', {})
    claimed = load(args.folder / 'dispatch.json').get('compute_claim', {}).get('lock', {})
    release_status = 'no_current_packet_lease'
    if current.get('holder') == OWNER and not same_compute_lease(current, claimed):
        release_status = 'different_own_lease_preserved'
    elif same_compute_lease(current, claimed):
        release = args.folder / 'compute-release.json'
        if release.exists() and load(release).get('stage') == 'released_verified':
            raise RuntimeError('A later own compute lease exists; do not release it')
        _write(release, {'utc': _utc(), 'stage': 'unlock_dispatch_pending'})
        unlock = post('/unlock', {'me': OWNER, 'name': 'compute'})
        after = locks()
        if after.get('compute', {}).get('holder') == OWNER:
            raise RuntimeError('Compute unlock not confirmed')
        _write(release, {'utc': _utc(), 'stage': 'released_verified', 'reply': unlock, 'locks_after': after})
        release_status = 'packet_lease_released_verified'
    marker = args.folder / 'readback.json'
    final = {**report, 'native_readback_receipt': pin(output), 'baseline': pin(baseline_path),
             'local_finalization_utc': _utc(), 'native_mutations_in_finalize': 0,
             'compute_release_status': release_status}
    if not marker.exists():
        write_new(marker, final)
    print(json.dumps({'stage': report['stage'], 'outputs': outputs,
                      'total_tracked_packages': report['total_tracked_packages'], 'world_placed': 0,
                      'baseline': pin(args.folder / 'saved-production-baseline.json')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run', 'readback', 'finalize'))
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--qualification', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--readback-names', nargs='+', help='Explicit known saved subset after a partial outcome; never resumes imports')
    parser.add_argument('--minimum-free-physical-mib', type=float, default=1024)
    parser.add_argument('--minimum-free-commit-mib', type=float, default=1536)
    options = parser.parse_args()
    globals()[options.phase](options)
