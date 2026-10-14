"""Import or inspect a bounded island pool through the existing Epic MCP client.

Default mode only verifies. Imports require the team's current editor lease and
refuse existing mesh packages. Every completed observation is checkpointed;
transport failure stops the batch without replaying an uncertain import.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import pathlib
import sys
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-root', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--last', type=int)
    parser.add_argument('--special-pool', action='store_true', help='Verify the separate six-asset crater/rift batch')
    parser.add_argument('--content-root', help='Native project Content directory; required for importing the separate special batch')
    parser.add_argument('--owner', default='team-codex', help='Explicit current editor lease holder; acquires no lease')
    parser.add_argument('--import-new', action='store_true')
    parser.add_argument('--save-verified', action='store_true')
    args = parser.parse_args()
    count = 6 if args.special_pool else 18
    if args.last is None: args.last = count
    if not 1 <= args.first <= args.last <= count:
        parser.error('require a bounded selection within the chosen pool')
    if args.special_pool and args.import_new and not args.content_root:
        parser.error('special imports require explicit native --content-root')
    source = pathlib.Path(args.source).resolve()
    assets = json.loads((source / 'island-mesh-pool.json').read_text())['assets']
    selected = assets[args.first - 1:args.last]
    ids = ([f'Island_Frag_Special_{i:02d}' for i in range(1,7)] if args.special_pool else
           [f'Island_Frag_{i:02d}' for i in range(1,13)] + [f'Island_Pad_{i:02d}' for i in range(1,7)])
    if len(assets) != count or {a['id'] for a in assets} != set(ids):
        raise ValueError('expected the complete unique selected pool identity set')
    if args.special_pool and any(asset.get('collision_hulls') != 24 or asset.get('kind') not in
            ('crater-fragment','split-top-fragment') for asset in assets):
        raise ValueError('special surface/collision contract missing')
    native_folder = (pathlib.Path(args.content_root).resolve() / 'Daedalus/Art/Islands/NativePool'
                     if args.content_root else source / 'NativePool')
    for asset in selected:
        file = source / asset['fbx']
        if file.resolve().parent != source:
            raise ValueError('source escapes pool')
        if hashlib.sha256(file.read_bytes()).hexdigest() != asset['fbx_sha256']:
            raise ValueError('FBX hash mismatch: ' + asset['id'])
        if args.import_new and (native_folder / (asset['id'] + '.uasset')).exists():
            raise ValueError('existing mesh refused: ' + asset['id'])
    sys.path.insert(0, str(pathlib.Path(args.client_root).resolve()))
    mcp = importlib.import_module('client').Mcp(timeout=45)
    if mcp.call('EditorToolset.EditorAppToolset', 'IsPIERunning') is not False:
        raise ValueError('Play state is not stopped')
    folder = '/Game/Daedalus/Art/Islands/NativePool'
    mesh_ts = 'editor_toolset.toolsets.static_mesh.StaticMeshTools'
    object_ts = 'editor_toolset.toolsets.object.ObjectTools'
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.import_new and output.exists():
        raise ValueError('existing import journal refused; reconcile with verify mode before another import')
    rows, saves = [], set()
    for asset in selected:
        row = {'asset': asset['id'], 'sourceSha256': asset['fbx_sha256'],
               'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        started = time.monotonic()
        try:
            if args.import_new:
                with urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=5) as response:
                    locks = json.load(response)
                if locks.get('unreal', {}).get('holder') != args.owner:
                    raise ValueError('explicit current editor owner lease required')
                output.write_text(json.dumps(rows + [{**row, 'status': 'dispatching-outcome-unknown'}],
                                             indent=2), encoding='utf-8')
                row['importResult'] = mcp.call(mesh_ts, 'import_file', folder_path=folder,
                    asset_name=asset['id'], source_file=str(source / asset['fbx']),
                    import_materials=True, import_textures=False, combine_meshes=True)
            ref = {'refPath': folder + '/' + asset['id'] + '.' + asset['id']}
            row['bounds'] = bounds = mcp.call(mesh_ts, 'get_bounds', mesh=ref)
            properties = json.loads(mcp.call(object_ts, 'list_properties', instance=ref))
            keys = ['bodySetup', 'staticMaterials', 'bCustomizedCollision']
            if not all(key in properties for key in keys):
                raise ValueError('mesh inspection properties unavailable')
            values = json.loads(mcp.call(object_ts, 'get_properties', instance=ref, properties=keys))
            body = values['bodySetup']
            body_properties = json.loads(mcp.call(object_ts, 'list_properties', instance=body))
            if 'aggGeom' not in body_properties:
                raise ValueError('collision inspection unavailable')
            row['collision'] = json.loads(mcp.call(object_ts, 'get_properties',
                instance=body, properties=['aggGeom', 'collisionTraceFlag']))
            row['materials'] = values['staticMaterials']
            expected = asset['expected_native_bounds_cm']
            actual = [bounds['max'][axis] - bounds['min'][axis] for axis in ('x', 'y', 'z')]
            if (not bounds['isValid'] or any(abs(a - b) > 1 for a, b in zip(actual, expected))
                    or abs(bounds['max']['z']) > .01 or not values['bCustomizedCollision']
                    or len(row['collision']['aggGeom']['convexElems']) != (24 if args.special_pool else 1)
                    or len(row['materials']) != (2 if asset['kind'] == 'terrace-pad' else 3)):
                raise ValueError('native bounds/collision/material acceptance failed')
            saves.add(folder + '/' + asset['id'])
            for slot in row['materials']:
                material = slot.get('materialInterface')
                if not isinstance(material, dict) or not material.get('refPath'):
                    raise ValueError('unassigned material')
                saves.add(material['refPath'].split('.')[0])
            row['status'] = 'verified'
        except Exception as error:
            row['status'], row['error'] = 'failed-or-unknown', str(error)
        row['elapsedSeconds'] = round(time.monotonic() - started, 3)
        rows.append(row)
        output.write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(asset['id'], row['status'], flush=True)
        if row['status'] != 'verified':
            return 1
    if args.import_new or args.save_verified:
        with urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=5) as response:
            locks = json.load(response)
        if locks.get('unreal', {}).get('holder') != args.owner:
            raise ValueError('explicit current editor owner lease required for save')
        saved = mcp.call('editor_toolset.toolsets.asset.AssetTools', 'save_assets', asset_paths=sorted(saves))
        output.with_suffix('.save.json').write_text(json.dumps({'saved': saved, 'paths': sorted(saves)}))
        if saved is not True:
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
