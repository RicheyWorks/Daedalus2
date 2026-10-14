"""Create a small world-position terrain shader through native Epic MCP.

New asset only; never edits a shared parent. The build journal checkpoints every
tool dispatch and returned reference. Optional --bind-floor changes only the
existing pilot's material override, preserving its geometry and identity.
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


MAT = 'editor_toolset.toolsets.material.MaterialTools'
OBJ = 'editor_toolset.toolsets.object.ObjectTools'
ACTOR = 'editor_toolset.toolsets.actor.ActorTools'
ASSET = 'editor_toolset.toolsets.asset.AssetTools'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-root', required=True)
    parser.add_argument('--content-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--bind-floor', action='store_true')
    parser.add_argument('--resume-graph', action='store_true',
                        help='Resume a known six-node graph; reconcile existing connections without replay')
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = pathlib.Path(args.content_root)
    folder = '/Game/Daedalus/Art/Islands/PilotMaterials'
    name = 'M_WZ_GroveGround_v1'
    if (output.exists() and not args.resume_graph) or (content / 'Daedalus/Art/Islands/PilotMaterials' / (name + '.uasset')).exists():
        raise ValueError('existing shader/journal refused; inspect instead of rebuilding')
    sys.path.insert(0, str(pathlib.Path(args.client_root).resolve()))
    m = importlib.import_module('client').Mcp()
    report = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'asset': folder + '/' + name, 'calls': [], 'status': 'started'}
    prior = None
    if args.resume_graph:
        prior = json.loads(output.read_text(encoding='utf-8'))
        if (prior.get('asset') != report['asset'] or prior.get('pending')
                or prior.get('savedMaterial') or prior.get('floorBefore')
                or len([c for c in prior['calls'] if c['tool'] == 'add_expression']) != 6):
            raise ValueError('journal is not a known six-node graph before asset save/binding')
        report = prior
        report['resumedUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def checkpoint():
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')

    def call(toolset, tool, **arguments):
        with urllib.request.urlopen('http://127.0.0.1:9890/locks', timeout=5) as response:
            if json.load(response).get('unreal', {}).get('holder') != 'team-codex':
                raise ValueError('team-codex editor lease required')
        report['pending'] = {'toolset': toolset, 'tool': tool, 'arguments': arguments}
        checkpoint()
        try:
            result = m.call(toolset, tool, **arguments)
        except Exception as error:
            report['status'], report['error'] = 'outcome-unknown', str(error)
            checkpoint()
            raise
        report['calls'].append({**report['pending'], 'result': result})
        report['pending'] = None
        checkpoint()
        return result

    if call('EditorToolset.EditorAppToolset', 'IsPIERunning') is not False:
        raise ValueError('Play must be stopped')
    if call('editor_toolset.toolsets.scene.SceneTools', 'get_current_level') != '/Game/Daedalus/DaedalusWorld':
        raise ValueError('wrong level')
    material = ([c['result'] for c in prior['calls'] if c['tool'] == 'create_material'][0]
                if prior else call(MAT, 'create_material', folder_path=folder, asset_name=name))
    if not isinstance(material, dict) or not material.get('refPath'):
        raise ValueError('new material was not created')

    def node(kind, x, y, values=None):
        if prior:
            refs = [c['result'] for c in prior['calls'] if c['tool'] == 'add_expression'
                    and c['arguments']['expression_class']['refPath'] == '/Script/Engine.MaterialExpression' + kind]
            if values and 'parameterName' in values:
                refs = [ref for ref in refs if any(c['tool'] == 'set_properties'
                         and c['arguments']['instance'] == ref
                         and json.loads(c['arguments']['values']).get('parameterName') == values['parameterName']
                         for c in prior['calls'])]
            if len(refs) != 1:
                raise ValueError('ambiguous recorded expression')
            if values:
                actual = json.loads(call(OBJ, 'get_properties', instance=refs[0], properties=list(values)))
                def equal(a, b):
                    if isinstance(b, dict):
                        return isinstance(a, dict) and all(k in a and equal(a[k], v) for k, v in b.items())
                    if type(b) in (int, float):
                        return type(a) in (int, float) and abs(a - b) < .000001
                    return a == b
                if not equal(actual, values):
                    raise ValueError('recorded node changed; refuse resume')
            return refs[0]
        ref = call(MAT, 'add_expression', material_or_function=material,
                   expression_class={'refPath': '/Script/Engine.MaterialExpression' + kind}, x=x, y=y)
        if values:
            properties = json.loads(call(OBJ, 'list_properties', instance=ref))
            if not all(key in properties for key in values):
                raise ValueError('required expression properties unavailable: ' + kind)
            if call(OBJ, 'set_properties', instance=ref, values=json.dumps(values)) is not True:
                raise ValueError('expression configuration failed: ' + kind)
            report.setdefault('nodeReadbacks', []).append(call(OBJ, 'get_properties', instance=ref,
                                                              properties=list(values)))
        return ref

    world = node('WorldPosition', -900, 0)
    noise = node('Noise', -650, 0, {'scale': .003, 'quality': 1, 'levels': 2,
                                  'outputMin': 0, 'outputMax': 1})
    dark = node('VectorParameter', -650, 200, {'parameterName': 'ForestColor',
                'defaultValue': {'r': .035, 'g': .12, 'b': .045, 'a': 1}})
    light = node('VectorParameter', -650, 400, {'parameterName': 'MossColor',
                'defaultValue': {'r': .18, 'g': .28, 'b': .075, 'a': 1}})
    blend = node('LinearInterpolate', -300, 150)
    rough = node('ScalarParameter', -300, 450, {'parameterName': 'Roughness', 'defaultValue': .92})

    def connect(source, target, pin):
        names = call(MAT, 'get_expression_input_names', expression=target)
        outputs = call(MAT, 'get_expression_output_names', expression=source)
        if pin not in names or not outputs:
            raise ValueError('expression pin unavailable: ' + pin)
        def current():
            entries = call(MAT, 'get_expression_inputs', material_or_function=material, expression=target)
            matches = [entry for entry in entries if entry['input_name'] == pin]
            if len(matches) != 1:
                raise ValueError('ambiguous expression input')
            return matches[0]
        edge = current()
        if edge['expression'] == source and edge['output_name'] == outputs[0]:
            return
        if edge['expression'] not in (None, 'None'):
            raise ValueError('existing graph connection differs; refuse overwrite')
        call(MAT, 'connect_expressions', from_expression=source, from_output_name=outputs[0],
             to_expression=target, to_input_name=pin)
        edge = current()
        if edge['expression'] != source or edge['output_name'] != outputs[0]:
            raise ValueError('expression connection readback failed')

    connect(world, noise, 'World Position')
    connect(dark, blend, 'A')
    connect(light, blend, 'B')
    connect(noise, blend, 'Alpha')
    for expression, channel in [(blend, 'MP_BaseColor'), (rough, 'MP_Roughness')]:
        outputs = call(MAT, 'get_expression_output_names', expression=expression)
        call(MAT, 'connect_to_output', expression=expression, output_name=outputs[0],
             material_property=channel)
        edge = call(MAT, 'get_property_input', material=material, material_property=channel)
        if edge['expression'] != expression or edge['output_name'] != outputs[0]:
            raise ValueError('material output connection readback failed')
    call(MAT, 'layout_expressions', material_or_function=material)
    call(MAT, 'recompile', material_or_function=material)
    report['savedMaterial'] = call(ASSET, 'save_assets', asset_paths=[report['asset']])
    if report['savedMaterial'] is not True:
        raise ValueError('material save unverified')
    report['status'] = 'material-saved'
    checkpoint()
    if args.bind_floor:
        floor = {'refPath': '/Game/Daedalus/DaedalusWorld.DaedalusWorld:PersistentLevel.StaticMeshActor_1241'}
        component = {'refPath': floor['refPath'] + '.StaticMeshComponent0'}
        transform = call(ACTOR, 'get_actor_transform', actor=floor)
        tags = call(ACTOR, 'get_tags', actor=floor)
        if 'Deed:1' not in tags or 'Realm:WORLD-ZERO' not in tags:
            raise ValueError('pilot floor identity changed')
        report['floorBefore'] = json.loads(call(OBJ, 'get_properties', instance=component,
                                                properties=['staticMesh', 'overrideMaterials']))
        map_file = content / 'Daedalus/DaedalusWorld.umap'
        shutil.copy2(map_file, output.with_suffix('.before.umap'))
        report['mapBeforeSha256'] = hashlib.sha256(map_file.read_bytes()).hexdigest()
        values = {'overrideMaterials': [material]}
        if call(OBJ, 'set_properties', instance=component, values=json.dumps(values)) is not True:
            raise ValueError('pilot binding failed')
        report['floorAfter'] = json.loads(call(OBJ, 'get_properties', instance=component,
                                               properties=['staticMesh', 'overrideMaterials']))
        if report['floorBefore']['staticMesh'] != report['floorAfter']['staticMesh'] or report['floorAfter']['overrideMaterials'] != [material]:
            raise ValueError('mesh/binding readback mismatch')
        if transform != call(ACTOR, 'get_actor_transform', actor=floor) or tags != call(ACTOR, 'get_tags', actor=floor):
            raise ValueError('pilot geometry/identity changed')
        report['savedMap'] = call(ASSET, 'save_assets', asset_paths=['/Game/Daedalus/DaedalusWorld'])
        report['mapAfterSha256'] = hashlib.sha256(map_file.read_bytes()).hexdigest()
        if report['savedMap'] is not True or report['mapAfterSha256'] == report['mapBeforeSha256']:
            raise ValueError('map save unverified')
        report['status'] = 'material-and-pilot-saved'
    checkpoint()
    print(report['status'])


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if '--output' in sys.argv:
            index = sys.argv.index('--output') + 1
            if index < len(sys.argv):
                journal = pathlib.Path(sys.argv[index])
                if journal.exists():
                    state = json.loads(journal.read_text(encoding='utf-8'))
                    if state.get('status') not in ('outcome-unknown', 'material-and-pilot-saved'):
                        state['status'] = 'validation-failed'
                    state['error'] = str(error)
                    journal.write_text(json.dumps(state, indent=2), encoding='utf-8')
        print(str(error), file=sys.stderr)
        sys.exit(1)
