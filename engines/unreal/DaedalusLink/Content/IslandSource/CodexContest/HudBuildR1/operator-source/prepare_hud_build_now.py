"""Fresh source/native preservation and backups for the authorized HUD build."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request

TASK = Path(__file__).parent
ROOT = TASK / 'contest-island-production'
SHADOW = TASK / 'native-hud157'
LIVE = Path('C:/Unreal/DaedalusRealm/Plugins/DaedalusLink')
BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
OUT = SHADOW / 'Saved/hud-build-preflight.json'
sys.path.insert(0, str(ROOT / 'tools/unreal'))
import codex_static_intake_delivery as intake


def fp(path):
    h = hashlib.sha256()
    size = 0
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            size += len(chunk)
            h.update(chunk)
    return {'bytes': size, 'sha256': h.hexdigest()}


if OUT.exists() or (SHADOW / 'Saved/build-hud-bcfb.log').exists():
    raise RuntimeError('retained build preparation/log exists; inspect, never replay')
prepared = json.loads((SHADOW / 'prepared.json').read_text())
changed = {r['plugin_relative_path']: r for r in prepared['source_items']}
assert len(changed) == 3 and len(prepared['live_source_baseline']) == 140
assert prepared['build']['normal_shared_pch'] and prepared['build']['default_mutex']
assert '-MaxParallelActions=1' in prepared['build']['arguments']
assert '-NoSharedPCH' not in prepared['build']['arguments']
for rel, expected in prepared['live_source_baseline'].items():
    assert fp(LIVE / rel) == expected, 'current live source drift: ' + rel
    desired = (changed[rel]['after_sha256'] if rel in changed else expected['sha256']).lower()
    assert fp(SHADOW / 'Plugins/DaedalusLink' / rel)['sha256'] == desired, 'shadow drift: ' + rel
    assert fp(ROOT / 'engines/unreal/DaedalusLink' / rel)['sha256'] == desired, 'owned drift: ' + rel
for name, key in [('UnrealEditor-DaedalusLink.dll', 'current_live_dll'),
                  ('UnrealEditor-DaedalusLink.pdb', 'current_live_pdb'),
                  ('UnrealEditor.modules', 'current_module_receipt')]:
    assert fp(LIVE / 'Binaries/Win64' / name) == prepared[key]
    assert fp(SHADOW / 'original-installed/Binaries/Win64' / name) == prepared[key]
for rel, expected in prepared['runtime_catalogs'].items():
    assert fp(LIVE / rel) == expected and fp(SHADOW / 'Plugins/DaedalusLink' / rel) == expected
assert fp(LIVE / 'DaedalusLink.uplugin') == fp(SHADOW / 'Plugins/DaedalusLink/DaedalusLink.uplugin')
app = Path(prepared['app_host']['path'])
manifest = app / 'source-manifest.json'
assert fp(manifest) == prepared['app_host']['manifest']
appdata = json.loads(manifest.read_text())
assert len(appdata['files']) == 230 and appdata['source_head'] == prepared['app_host']['source_head']
for rel, sha in appdata['files'].items():
    assert fp(app / 'Plugins/DaedalusLink' / rel.removeprefix('engines/unreal/DaedalusLink/'))['sha256'] == sha.lower()
bulrush = json.loads((BASE / 'AquaticBulrushR1/known-save-readback.json').read_text())
old = json.loads((BASE / 'AquaticBulrushR1/prepared.json').read_text())
packages = dict(old['protected_packages'])
packages.update(bulrush['outputs'])
assert len(packages) == 120 and bulrush['issues'] == []
assert fp(intake.MAP_FILE) == prepared['saved_map'] == bulrush['map_fingerprint']
leases = json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=10))
for name in ('unreal', 'compute'):
    assert leases.get(name, {}).get('holder') == 'codex-play-guard'
intake.editor()
scene = intake._scene_snapshot()
intake._same_scene(scene, bulrush['scene_readback'])
backup = SHADOW / 'activation-backup'
backup.mkdir(exist_ok=False)
backups = {}
for path, expected in packages.items():
    source = intake._asset_file(path)
    assert fp(source) == expected, 'protected package drift: ' + path
    target = backup / 'Content' / source.relative_to(Path('C:/Unreal/DaedalusRealm/Content'))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert fp(target) == expected
    backups[path] = str(target)
map_backup = backup / 'DaedalusWorld.umap'
shutil.copy2(intake.MAP_FILE, map_backup)
assert fp(map_backup) == prepared['saved_map']
result = {'schema': 'daedalus.codex-hud-build-preflight.v1',
    'utc': datetime.now(timezone.utc).isoformat(), 'stage': 'fresh_source_native_backups_complete',
    'source_files_verified': 140, 'hud_source_files': 3, 'unrelated_source_files_preserved': 137,
    'live_source_baseline': prepared['live_source_baseline'], 'source_items': prepared['source_items'],
    'live_dll': prepared['current_live_dll'], 'live_pdb': prepared['current_live_pdb'],
    'module_receipt': prepared['current_module_receipt'], 'descriptor': fp(LIVE / 'DaedalusLink.uplugin'),
    'runtime_catalogs': prepared['runtime_catalogs'], 'app_host_files_verified': 230,
    'packages': packages, 'package_backups': backups, 'map': prepared['saved_map'],
    'map_backup': str(map_backup), 'scene': scene, 'leases': leases,
    'build': prepared['build'], 'canonical_mutated': False, 'issues': []}
with OUT.open('x', encoding='utf-8', newline='\n') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps({'preflight': str(OUT), 'fingerprint': fp(OUT), 'packages_backed_up': len(backups),
                  'actor_records': len(scene['actors']), 'source_files': 140, 'app_files': 230}, indent=2))
