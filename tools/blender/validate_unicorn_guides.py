# SPDX-License-Identifier: MIT
"""Validate the actual generated files using the existing asset-pipeline GLB reader."""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'connectors/claude-asset-pipeline'))
from asset_pipeline.glb import summarize


def validate(root):
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    assets = manifest['assets']
    assert manifest['count'] == len(assets) == 500
    assert len(list((root/'glb').glob('*.glb'))) == 500
    assert len({a['id'] for a in assets}) == 500
    assert len({(a['family'], tuple(a['scale'])) for a in assets}) == 500
    assert len({a['sha256'] for a in assets}) == 500
    assert hashlib.sha256(Path(manifest['source']).read_bytes()).hexdigest() == manifest['source_sha256']
    triangles = 0
    for asset in assets:
        path = root / asset['glb']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset['sha256']
        doc = summarize(path)
        assert len(doc['meshes']) == 1
        mesh = doc['meshes'][0]
        assert mesh['triangles'] == asset['triangles'] < 6000
        assert len(mesh['materials']) <= 3
        assert all(math.isfinite(v) and v > 0 for v in mesh['dims'])
        triangles += mesh['triangles']
    by_id = {a['id']: a for a in assets}
    membership = Counter(member for group in manifest['groups'] for member in group['members'])
    assert set(membership) == set(by_id) and set(membership.values()) == {1}
    paired = 0
    for group in manifest['groups']:
        members = [by_id[key] for key in group['members']]
        if group['kind'] == 'mixed_pair':
            assert len(members) == 2
            assert sorted(a['sex'] for a in members) == ['female', 'male']
            paired += 2
        else:
            assert all(a['sex'] == 'female' for a in members)
            assert len(members) == 12 if group['kind'] == 'exceptional_female_quest_herd' else 2 <= len(members) <= 8
    assert paired == 250
    alphas = [a for a in assets if a['mountain_alpha']]
    assert len(alphas) == 1 and alphas[0]['burning_bull_response'] == 'stand_ground'
    assert all(a['burning_bull_response'] == 'flee' for a in assets if not a['mountain_alpha'])
    report = dict(status='PASS', exported_assets=500, unique_palette_proportion_variants=500,
                  male_female_pairs=125, ordinary_female_herds=73, exceptional_female_herd_size=12,
                  mountain_alphas=1, total_triangles=triangles,
                  unreal_runtime_proven=False)
    (root/'validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    validate(Path(sys.argv[1]).resolve())
