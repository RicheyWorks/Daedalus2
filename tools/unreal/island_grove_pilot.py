"""Bounded, additive native-MCP grove for World Zero deed 1.

Default: produce a checked plan, no scene writes. --apply uses existing DiskSaver
trees and requires the current team-codex editor lease. Existing labels/journals
are refused; interrupted dispatch is reconciled by readback, never replayed.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import pathlib
import shutil
import sys
import urllib.request


SCENE = 'editor_toolset.toolsets.scene.SceneTools'
ACTOR = 'editor_toolset.toolsets.actor.ActorTools'
MESH = 'editor_toolset.toolsets.static_mesh.StaticMeshTools'
FLOOR = {'refPath': '/Game/Daedalus/DaedalusWorld.DaedalusWorld:PersistentLevel.StaticMeshActor_1241'}


def lease():
    with urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=5) as response:
        if json.load(response).get('unreal', {}).get('holder') != 'team-codex':
            raise ValueError('team-codex editor lease required')


def check_transform(actual, wanted):
    for key in ('location', 'scale'):
        if any(abs(actual[key][axis] - wanted[key][axis]) > .001 for axis in ('x', 'y', 'z')):
            raise ValueError('native placement transform differs from plan')
    for axis in ('pitch', 'yaw', 'roll'):
        delta = (actual['rotation'][axis] - wanted['rotation'][axis] + 180) % 360 - 180
        if abs(delta) > .001:
            raise ValueError('native placement rotation differs from plan')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--map-file', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.apply and output.exists():
        raise ValueError('existing mutation journal refused; reconcile actors before another run')
    sys.path.insert(0, str(pathlib.Path(args.client_root).resolve()))
    m = importlib.import_module('client').Mcp(timeout=20)
    if m.call('EditorToolset.EditorAppToolset', 'IsPIERunning') is not False:
        raise ValueError('Play must be stopped')
    if m.call(SCENE, 'get_current_level') != '/Game/Daedalus/DaedalusWorld':
        raise ValueError('wrong level')
    floor_transform = m.call(ACTOR, 'get_actor_transform', actor=FLOOR)
    tags = m.call(ACTOR, 'get_tags', actor=FLOOR)
    expected = {'location': {'x': 40450, 'y': -9500, 'z': 4620},
                'rotation': {'pitch': 0, 'yaw': 0, 'roll': 0},
                'scale': {'x': 92, 'y': 92, 'z': 12}}
    if floor_transform != expected or 'Deed:1' not in tags or 'Realm:WORLD-ZERO' not in tags:
        raise ValueError('pilot floor identity/geometry changed; re-plan')
    plan = []
    centers = [(-3000, -3000), (-3000, 3000), (3000, -3000), (3000, 3000)]
    for index in range(8):
        variant = (8, 13, 18, 23)[index % 4]
        name = 'Prop_DS_Tree_%02d' % variant
        asset = '/Game/DiskSaver/Art/Prop/' + name + '/' + name + '/StaticMeshes/' + name
        ref = {'refPath': asset + '.' + name}
        bounds = m.call(MESH, 'get_bounds', mesh=ref)
        height = bounds['max']['z'] - bounds['min']['z']
        if not bounds['isValid'] or height <= 0:
            raise ValueError('invalid tree bounds')
        scale = (600 + index % 3 * 80) / height
        dx, dy = centers[index // 2]
        x = expected['location']['x'] + dx + (-450 if index % 2 == 0 else 450)
        y = expected['location']['y'] + dy
        # Keep a 12m central corridor and all canopy bounds inside the floor.
        radius = max(abs(bounds['min']['x']), abs(bounds['max']['x']),
                     abs(bounds['min']['y']), abs(bounds['max']['y'])) * scale * 1.414214
        if abs(x - 40450) - radius < 600 or max(abs(x - 40450), abs(y + 9500)) + radius > 4500:
            raise ValueError('canopy overlaps corridor or plot edge')
        distance = m.call(SCENE, 'trace_world', start={'x': x, 'y': y, 'z': 5520},
                          end={'x': x, 'y': y, 'z': 5020})
        if not isinstance(distance, (int, float)) or abs(distance - 300) > 2:
            raise ValueError('placement is obstructed or ground differs')
        label = 'WZ_GrovePilot_%02d' % (index + 1)
        if m.call(SCENE, 'find_actors', name=label, tag='', collision_channels=[]):
            raise ValueError('existing pilot label refused: ' + label)
        plan.append({'label': label, 'asset': asset, 'bounds': bounds,
                     'triangles': m.call(MESH, 'get_triangle_count', mesh=ref),
                     'xform': {'location': {'x': x, 'y': y, 'z': 5220 - bounds['min']['z'] * scale},
                               'rotation': {'pitch': 0, 'yaw': index * 47 % 360, 'roll': 0},
                               'scale': {'x': scale, 'y': scale, 'z': scale}}})
    report = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'floor': FLOOR, 'floorTransform': floor_transform, 'floorTags': tags,
              'plan': plan, 'actors': [], 'status': 'plan-checked', 'gameplay': 'visual-only'}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not args.apply:
        print('checked plan:', len(plan), 'trees')
        return 0
    lease()
    map_file = pathlib.Path(args.map_file)
    backup = output.with_suffix('.before.umap')
    shutil.copy2(map_file, backup)
    report['beforeMapSha256'] = hashlib.sha256(map_file.read_bytes()).hexdigest()
    for row in plan:
        lease()
        report['pending'] = row['label']
        report['status'] = 'dispatching-outcome-unknown'
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        actor = m.call(SCENE, 'add_to_scene_from_asset', asset_path=row['asset'],
                       name=row['label'], xform=row['xform'], snap_to_ground=False)
        if not isinstance(actor, dict) or not actor.get('refPath'):
            raise ValueError('spawn result unavailable; reconcile label, do not replay')
        entry = {'label': row['label'], 'ref': actor}
        report['actors'].append(entry)
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        entry['transform'] = m.call(ACTOR, 'get_actor_transform', actor=actor)
        check_transform(entry['transform'], row['xform'])
        report['pending'] = None
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('placed', row['label'], flush=True)
    if floor_transform != m.call(ACTOR, 'get_actor_transform', actor=FLOOR) or tags != m.call(ACTOR, 'get_tags', actor=FLOOR):
        raise ValueError('original floor changed')
    lease()
    report['status'] = 'save-dispatching-outcome-unknown'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    try:
        report['saveResult'] = m.call('editor_toolset.toolsets.asset.AssetTools', 'save_assets',
                                     asset_paths=['/Game/Daedalus/DaedalusWorld'])
    except Exception as error:
        report['status'] = 'save-outcome-unknown'
        report['error'] = str(error)
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(report['status'], str(error))
        return 1
    report['afterMapSha256'] = hashlib.sha256(map_file.read_bytes()).hexdigest()
    report['status'] = 'saved' if report['saveResult'] is True and report['afterMapSha256'] != report['beforeMapSha256'] else 'save-unverified'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(report['status'])
    return 0 if report['status'] == 'saved' else 1


if __name__ == '__main__':
    sys.exit(main())
