"""Read-only local delivery lookup for the sole editor operator. Never imports or grants a lease."""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import subprocess

REALMS = {
    'GALLERY-CITY': ('gallery', 'gallery-buildout', 'WORLD_V1 / GALLERY style'),
    'PARCELS': ('parcels', 'parcels-buildout', 'WORLD_V1 / PARCELS style'),
    'BRICKS': ('bricks', 'bricks-buildout', 'WORLD_V1 / BRICKS style'),
    'LABYRINTH': ('labyrinth', 'labyrinth-full', 'LABYRINTH style / separate Maze API'),
    'PORTAL': ('portal', 'portal-buildout', 'Retro data API; no chunk-provider entry'),
    'OCEAN': ('ocean', 'ocean-vessels-2', 'Optional OCEAN_V1; separate bounded chunk host'),
}


def asset_row(row, root):
    relative = Path(row['file'])
    # A manifest is data, never permission to read arbitrary files outside its delivery root.
    source = (root / relative).resolve()
    try:
        source.relative_to(root.resolve())
    except ValueError:
        raise ValueError('Manifest file leaves delivery root') from None
    expected = row['sha256']
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('Invalid expected SHA256')
    actual = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
    return {'id': row['id'], 'group': relative.parts[0] if len(relative.parts) > 1 else 'vessel-kit',
            'file': str(source), 'triangles': row.get('triangles'), 'expected_sha256': expected,
            'actual_sha256': actual, 'status': 'Missing' if actual is None else
            'Hash matched' if actual == expected else 'Hash mismatch',
            'role': row.get('role', ''), 'runtime_acceptance': 'Not established by file inventory'}


def inventory(repo, deliveries):
    style_path=repo/'daedalus-core/src/main/java/com/daedalus/world/WorldStyle.java'
    styles={key:value=='true' for key,value in re.findall(r'^\s+([A-Z_]+)\((true|false),',style_path.read_text(),re.M)}
    session_path=repo/'engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusRealmSessionCore.h'
    sessions=re.findall(r'^\s+\{"([A-Z-]+)",',session_path.read_text(),re.M)
    if set(sessions) != set(REALMS)|{'WORLD-ZERO'}:
        raise ValueError('Native realm roster changed; reconcile the construction inventory')
    realms = {'WORLD-ZERO': {
        'terrain_source': 'WORLD_V1 / SKY_ISLANDS; actual mounted provider is runtime configuration',
        'reuse': 'Existing 14 team sublevels; inspect current saved editor state before changing them',
        'source_reference': str(repo/'docs/production/BASE-LAYER.md'),
        'asset_census': 'Team island assets are outside the six inspected production manifests'}}
    for canonical, (stem, folder, terrain) in REALMS.items():
        manifest = repo/'data/art'/stem/('manifest.json' if stem == 'ocean' else 'production-manifest.json')
        raw = manifest.read_bytes()
        rows = json.loads(raw)
        if stem == 'ocean': rows = rows['assets']
        ids = [row['id'] for row in rows]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate IDs in realm manifest: '+canonical)
        assets = [asset_row(row, deliveries/folder) for row in rows]
        realms[canonical] = {'manifest': str(manifest), 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                             'delivery_root': str(deliveries/folder), 'terrain_source': terrain,
                             'status_counts': dict(Counter(row['status'] for row in assets)),
                             'group_counts': dict(Counter(row['group'] for row in assets)), 'assets': assets}
    return {'source_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
            'scope': 'Exact local file availability and hashes, not import, collision, possession, Play or hosting proof',
            'reuse_tools': [str(repo/'engines/unreal/DaedalusLink/Content/Python'/name) for name in
                           ('daedalus_realm_ground.py','daedalus_plots.py','daedalus_land_grid.py')],
            'operator_constraints': 'Current editor lease, RAM guard, current level assertion, bounded import/save batches',
            'source_world_style_ready': styles, 'native_session_ids': sessions,
            'capability_source_sha256': {str(path.relative_to(repo)):hashlib.sha256(path.read_bytes()).hexdigest()
                                         for path in (style_path,session_path)},
            'mounted_hosts_verified': False,
            'realms': realms}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deliveries', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args=parser.parse_args()
    result=inventory(Path(__file__).resolve().parents[2], args.deliveries.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({realm: data.get('status_counts', data.get('reuse')) for realm,data in result['realms'].items()}))
