# SPDX-License-Identifier: MIT
"""Freeze a reviewed small-static packet for the existing queue; files only."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import re

if __package__:
    from . import unattended_static_adapter as a
else:
    import unattended_static_adapter as a

q = a.q


def checked_native_items(witness, rows):
    """Run only the retained helper's pure data validators, never import unreal."""
    path = q.checked_file(witness)
    if witness['sha256'] != a.HELPER_SHA:
        raise q.Refused('Only retained qualified-static helper supported')
    tree = ast.parse(path.read_bytes())
    wanted = {'_pin', '_fingerprint', '_items'}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in body} != wanted:
        raise q.Refused('Existing helper validators absent')
    scope = dict(Path=Path, hashlib=hashlib, math=math, re=re, json=json,
                 MAX_ITEMS=3, MAX_TRIANGLES=3000,
                 ROOT='/Game/Daedalus/Art/Islands/CodexContest/')
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), scope)
    return scope['_items']({'items': rows})


def prepare(qualification, baseline, dedup, environment, folder):
    folder = Path(folder).resolve()
    if folder.exists():
        raise q.Refused('New folder required; preserve prior preparation/state')
    env, qualified = q.load(environment), q.load(qualification)
    required = {'owner', 'editor', 'engine_version', 'start_by_utc',
                'host', 'wire', 'importer', 'shared', 'dependencies'}
    if set(env) != required:
        raise q.Refused('Exact current owner/editor/dependency environment required')
    rows = checked_native_items(env['importer'], qualified['items'])
    namespace = a.PREFIX + 'CommonsPond20261023'
    if any(not row['destination'].startswith(namespace + '/') for row in rows):
        raise q.Refused('This selected preparation owns only CommonsPond20261023 children')
    cfg = {'schema': a.VERSION, 'owner': env['owner'], 'selected_name': rows[0]['name'],
           'qualification': a.pin(qualification), 'baseline': a.pin(baseline), 'dedup': a.pin(dedup),
           'native': a.pin(Path(a.__file__).with_name('unattended_static_native.inc')),
           'inventory_reader': a.pin(a.inventory.__file__),
           'unit_contract': a.UNIT, 'start_by_utc': env['start_by_utc'],
           **{key: env[key] for key in ('importer', 'shared', 'host', 'wire')}}
    frozen = {'schema': q.VERSION, 'owner': env['owner'], 'owned_destination': namespace,
              'editor': env['editor'], 'engine_version': env['engine_version'],
              'adapter': {'file': a.pin(a.__file__), 'version': a.VERSION},
              'dependencies': env['dependencies'], 'items': []}
    # Validate real source review and current protected files BEFORE any output
    # directory is created. A measured/HELD packet is deliberately refused.
    for row in rows:
        cfg['selected_name'] = row['name']
        item = {'id': row['name'], 'destination': row['destination'],
                'sources': [{'path': row['fbx'], **row['fingerprint']},
                            {'path': row['sidecar'], **row['sidecar_fingerprint']}]}
        a.selected(item, cfg)
        a.protected(cfg, frozen)
    for key in ('importer', 'shared', 'host', 'wire'):
        q.checked_file(cfg[key])
    index = a.inventory.read_index(cfg['dedup'])
    if index['editor'] != env['editor'] or index['reader'] != cfg['native']:
        raise q.Refused('Source pages must bind this editor and native reader')
    if cfg['inventory_reader'] not in frozen['dependencies']:
        frozen['dependencies'] = [*frozen['dependencies'], cfg['inventory_reader']]
    q.utc_seconds(env['start_by_utc'])
    folder.mkdir(parents=True)
    for row in rows:
        cfg['selected_name'] = row['name']
        policy_path = folder / (row['name'] + '-policy.json')
        q.receipts.write_receipt(policy_path, cfg)
        item = {'id': row['name'], 'destination': row['destination'],
                'sources': [{'path': row['fbx'], **row['fingerprint']},
                            {'path': row['sidecar'], **row['sidecar_fingerprint']}],
                'policy': a.pin(policy_path)}
        a.policy(item)
        frozen['items'].append(item)
    # No adapter module/host is imported by queue.prepare.
    selected_manifest = folder / 'selected-source-manifest.json'
    q.receipts.write_receipt(selected_manifest, frozen)
    result = q.prepare(selected_manifest, folder / 'state')
    return {**result, 'imported': 0, 'admitted': 0, 'native_validation': 'NotValidated',
            'native_profile_tested': False, 'state_directory': str(folder / 'state')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('qualification', 'baseline', 'dedup', 'environment', 'folder'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(**vars(args)), indent=2))


if __name__ == '__main__':
    main()
