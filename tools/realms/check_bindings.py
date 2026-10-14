# SPDX-License-Identifier: MIT
"""Audit a read-only night-run binding dump. Asset availability is not actor binding proof."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = '/Game/Daedalus/Art/Cast'


def text(value, label):
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError('Invalid '+label)
    return value


def analyze(dump, expected=None):
    if not isinstance(dump, dict) or type(dump.get('schema')) is not int or dump['schema'] != 1:
        raise ValueError('Expected binding dump schema1')
    if dump.get('loaded_only') is not True or dump.get('atomic') is not False or dump.get('registry_root') != ROOT:
        raise ValueError('Unsupported observation scope')
    text(dump.get('world_path'), 'world path')
    text(dump.get('captured_utc'), 'capture timestamp')
    assets, roles, errors = (dump.get(key) for key in ('assets', 'roles', 'errors'))
    if not all(isinstance(value, list) for value in (assets, roles, errors)):
        raise ValueError('Assets, roles and observation errors must be arrays')
    if len(assets) > 100000 or len(roles) > 10000 or len(errors) > 10000:
        raise ValueError('Dump exceeds audit limits')
    by_id, paths = {}, set()
    for asset in assets:
        path = text(asset.get('path'), 'asset path')
        cls = text(asset.get('class'), 'asset class')
        if not path.startswith(ROOT+'/') or path in paths:
            raise ValueError('Duplicate or out-of-root asset path')
        paths.add(path)
        asset_id = path[len(ROOT)+1:].split('/')[0]
        by_id.setdefault(asset_id, []).append((path, cls))
    results, actors, seen_roles = [], set(), set()
    for role in roles:
        path = text(role.get('path'), 'actor path')
        if path in actors:
            raise ValueError('Duplicate actor path')
        actors.add(path)
        cast, who = text(role.get('cast'), 'cast'), text(role.get('who'), 'who')
        seen_roles.add((cast.lower(), who))
        candidates = role.get('candidate_ids')
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= 64 or len(set(candidates)) != len(candidates):
            raise ValueError('Expected unique native candidate IDs')
        for candidate in candidates:
            if not isinstance(candidate, str) or not re.fullmatch(r'Mob_[A-Za-z0-9_]+', candidate):
                raise ValueError('Unsafe candidate ID')
        if type(role.get('has_art')) is not bool or not isinstance(role.get('art_found'), str):
            raise ValueError('Missing native binding observation')
        mesh = role.get('mesh')
        if mesh is not None:
            text(mesh, 'bound mesh')
        # Native resolver stops at the first candidate folder containing ANY assets.
        # Do not claim a later alias fixes an earlier folder with only materials.
        selected = next((candidate for candidate in candidates if by_id.get(candidate)), None)
        available = [p for p, cls in by_id.get(selected, []) if cls == 'SkeletalMesh']
        bound = bool(role['has_art'] and mesh in available and role['art_found'] == selected)
        if bound:
            status = 'bound-observed'
        elif not selected:
            status = 'missing-art'
        elif not available:
            status = 'selected-folder-has-no-skeletal-mesh'
        elif role['has_art']:
            status = 'binding-inconsistent'
        else:
            status = 'art-available-not-bound'
        results.append({'path': path, 'cast': cast, 'who': who, 'status': status,
                        'selected_id': selected, 'candidate_ids': candidates,
                        'skeletal_meshes': available, 'observed_mesh': mesh,
                        'observed_art_found': role['art_found']})
    missing_roles = []
    if expected:
        for cast, who in sorted(set(expected)-seen_roles):
            missing_roles.append({'cast': cast, 'who': who, 'status': 'not-observed-in-loaded-world'})
    counts = {}
    for row in results:
        counts[row['status']] = counts.get(row['status'], 0)+1
    return {'schema': 1, 'world_path': dump['world_path'], 'captured_utc': dump['captured_utc'],
            'scope': 'Loaded actors and registry availability; no animation, visual or whole-world proof',
            'passed': bool(results) and not errors and not missing_roles and all(r['status']=='bound-observed' for r in results),
            'counts': counts, 'roles': results, 'not_observed': missing_roles, 'observation_errors': errors}


def expected_roles(folder):
    roles = []
    for source in sorted(Path(folder).glob('*.dcs')):
        for line in source.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('who '):
                roles.append((source.stem.lower(), text(line[4:].strip(), 'DCS role')))
    if not roles:
        raise ValueError('Expected-cast folder contains no roles')
    return roles


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate JSON field: '+key)
        out[key] = value
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dump', required=True)
    parser.add_argument('--expected-casts', help='Optional scoped DCS folder; absent roles become explicit gaps')
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    source = Path(args.dump)
    if source.stat().st_size > 64*1024*1024:
        raise ValueError('Dump exceeds64MiB')
    raw = source.read_bytes()
    if len(raw) > 64*1024*1024:
        raise ValueError('Dump exceeds64MiB')
    dump = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON '+value)))
    report = analyze(dump, expected_roles(args.expected_casts) if args.expected_casts else None)
    report['input_sha256'] = hashlib.sha256(raw).hexdigest()
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': report['passed'], 'counts': report['counts'],
                      'not_observed': len(report['not_observed']), 'errors': len(report['observation_errors'])}))
    return 0 if report['passed'] else 2


if __name__ == '__main__':
    sys.exit(main())
