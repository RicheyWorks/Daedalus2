# SPDX-License-Identifier: MIT
"""File-only UE5.8 transmission evidence consumer. Never material acceptance.

Only retained UTF-8 T3D is decoded; packages are opaque pinned bytes. Missing
serialized fields stay unknown, including zero-valued FExpressionInput defaults.
Real switch selection has no supported evidence contract in v1. No collector,
engine imports, output writes, or runtime dispatcher exist in this module.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

VERSION = 'skyfarm-glass-closure-v1'
ROOT = '/InterchangeAssets/gltf/MaterialBodies/MF_Transmission_Body.MF_Transmission_Body'
TEMPORAL = '/InterchangeAssets/gltf/MaterialFunctions/MF_Temporal_Blur.MF_Temporal_Blur'
ROOT_PACKAGE = (205269, '067ea26cba3218c168783b562d5304e3d6fe318bdef676226b4d5d1fdf17d82e')
ROOT_EXPORT = (348703, '05cd7a779fd39edc88eb43dc214aa66a426e373c1450d639a84f88274a626641')
TEMPORAL_PACKAGE = (67200, '05526bea6d93a9252a928eb1e1aac4d615bdce09c6d64be15159979f694630b3')
HOLD = 'HOLD_INTRINSIC_TRANSMISSION_MODEL_UNPROVEN'
PREFIX = '/Script/Engine.MaterialExpression'
MASK_FIELDS = ('Mask', 'MaskR', 'MaskG', 'MaskB', 'MaskA')
GUID = re.compile(r'^[0-9A-Fa-f]{32}$')
OBJECT = re.compile(r'^Begin Object (?:Class=(\S+) )?Name="([^"]+)" ExportPath="([^\']+)\x27([^\']+)\x27"$')
REF = re.compile(r'(/Script/Engine\.[A-Za-z0-9_]+)\x27([^\']+)\x27')


class EvidenceError(ValueError):
    """Contradictory/malformed evidence; missing evidence is reported separately."""


def _require(condition, message):
    if not condition:
        raise EvidenceError(message)


def _keys(value, required, optional=()):
    _require(isinstance(value, dict) and set(required) <= set(value)
             and set(value) <= set(required) | set(optional), 'closed envelope fields required')


def _pin(data):
    return len(data), hashlib.sha256(data).hexdigest()


def _field(text, name):
    matches = re.findall(r'(?:^|[,(])\s*' + re.escape(name) + r'\s*=([^,()]*)', text)
    _require(len(matches) <= 1, 'duplicate serialized struct field: ' + name)
    value = matches[0].strip().strip('"') if matches else None
    return value.upper() if value is not None and name in ('ExpressionInputId', 'ExpressionOutputId') else value


def _integer(text, name, missing, label):
    value = _field(text, name)
    if value is None:
        missing.add(label + ':' + name + '-default-witness')
        return None
    _require(re.fullmatch(r'\d+', value) is not None, label + ':invalid ' + name)
    return int(value)


def _blocks(text):
    """Read the exported object grammar, preserving declaration/body separation."""
    stack, declared, bodies = [], {}, {}
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith('Begin Object '):
            match = OBJECT.fullmatch(line)
            _require(match is not None, 'unsupported T3D object header')
            cls, name, export_class, path = match.groups()
            _require(cls is None or cls == export_class, 'object class/export class mismatch')
            _require(path.rsplit(':', 1)[-1].rsplit('.', 1)[-1] == name, 'object name/export path mismatch')
            if cls:
                _require(path not in declared, 'duplicate object declaration: ' + path)
                declared[path] = (cls, name)
            stack.append((path, export_class, name, [], line_number))
        elif line == 'End Object':
            _require(bool(stack), 'unbalanced T3D end')
            path, cls, name, properties, start = stack.pop()
            if properties:
                _require(path not in bodies, 'duplicate object body: ' + path)
                bodies[path] = (cls, name, properties, start)
        elif stack and line:
            stack[-1][3].append((line_number, line))
    _require(not stack, 'unclosed T3D object')
    for path, (cls, name, _, _) in bodies.items():
        _require(declared.get(path) == (cls, name), 'body without matching declaration: ' + path)
    return declared, bodies


def _properties(lines):
    result = {}
    for number, line in lines:
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        _require(key not in result, 'duplicate serialized property: ' + key)
        if key in ('Id', 'VariableGuid', 'DeclarationGuid', 'MaterialExpressionGuid'):
            value = value.upper()
        result[key] = (value, number)
    return result


def _canonical(ref, asset):
    if ref.startswith('/'):
        _require(ref.startswith(asset + ':'), 'foreign expression reference: ' + ref)
        return ref
    short = asset.rsplit('.', 1)[-1]
    _require(ref.startswith(short + ':'), 'foreign relative expression reference: ' + ref)
    return asset + ':' + ref.split(':', 1)[1]


def validate(packet, files):
    """Consume pinned bytes. Return structure/unknowns, never native/quality proof.

    ``files`` maps the envelope's artifact IDs to already-read bytes. Absence is
    PENDING; wrong supplied bytes, duplicate/foreign references and cycles reject.
    Synthetic fixtures cannot be passed off as a real function-family closure.
    """
    _keys(packet, ('version', 'synthetic', 'root', 'artifacts', 'functions', 'black_constants', 'switch_context'))
    _require(packet['version'] == VERSION and type(packet['synthetic']) is bool, 'version/synthetic required')
    synthetic = packet['synthetic']
    _require(isinstance(packet['root'], str) and (synthetic or packet['root'] == ROOT), 'exact real root required')
    _require(isinstance(packet['switch_context'], dict), 'switch context map required')
    _require(synthetic or not packet['switch_context'], 'real active-context contract unavailable in v1')
    _require(isinstance(files, dict) and isinstance(packet['artifacts'], dict), 'artifact map required')
    _require(set(files) <= set(packet['artifacts']), 'undeclared supplied artifact')
    missing, artifacts = set(), {}
    for key, record in packet['artifacts'].items():
        _keys(record, ('kind', 'owner', 'bytes', 'sha256', 'file'))
        _require(record['kind'] in ('package', 't3d', 'class_default'), 'unsupported artifact kind')
        _require(isinstance(record['owner'], str) and type(record['bytes']) is int and record['bytes'] > 0
                 and isinstance(record['sha256'], str) and re.fullmatch('[0-9a-f]{64}', record['sha256']), 'invalid artifact pin')
        _require(isinstance(record['file'], str) and bool(record['file']), 'artifact filename required')
        if key not in files:
            missing.add('artifact:' + key)
            continue
        data = files[key]
        _require(isinstance(data, bytes) and _pin(data) == (record['bytes'], record['sha256']), 'artifact pin mismatch: ' + key)
        artifacts[key] = data

    def artifact(key, kind, owner):
        if key is None:
            missing.add(owner + ':' + kind)
            return None
        _require(isinstance(key, str) and key in packet['artifacts'], 'undeclared artifact reference')
        record = packet['artifacts'][key]
        _require(record['kind'] == kind and record['owner'] == owner, 'artifact owner/kind mismatch')
        return artifacts.get(key)

    _require(isinstance(packet['functions'], list), 'functions array required')
    functions, nodes, declarations = {}, {}, {}
    for function in packet['functions']:
        _keys(function, ('asset', 'class', 'package', 'export'))
        asset = function['asset']
        _require(isinstance(asset, str) and asset.startswith('/') and ':' not in asset, 'function asset path required')
        _require(asset not in functions and function['class'] == '/Script/Engine.MaterialFunction', 'duplicate function or wrong class')
        functions[asset] = function
        artifact(function['package'], 'package', asset)
        body = artifact(function['export'], 't3d', asset)
        if not synthetic:
            for key, expected in ((function['package'], {ROOT: ROOT_PACKAGE, TEMPORAL: TEMPORAL_PACKAGE}.get(asset)),
                                  (function['export'], ROOT_EXPORT if asset == ROOT else None)):
                if key is not None and expected is not None:
                    record = packet['artifacts'][key]
                    _require((record['bytes'], record['sha256']) == expected, 'observed family pin mismatch')
        if body is None:
            missing.add(asset + ':body-export')
            continue
        declared, bodies = _blocks(body.decode('utf-8'))
        _require(declared.get(asset) == (function['class'], asset.rsplit('.', 1)[-1]), 'function export identity mismatch')
        for path, (cls, name) in declared.items():
            if not cls.startswith(PREFIX):
                continue
            _require(path.startswith(asset + ':'), 'foreign declared expression')
            _require(path not in nodes, 'duplicate expression path')
            if cls == PREFIX + 'Comment':
                continue
            properties = _properties(bodies[path][2]) if path in bodies else {}
            node = {'class': cls, 'function': asset, 'properties': properties,
                    'guid': properties.get('MaterialExpressionGuid', (None,))[0], 'edges': [], 'outputs': set()}
            if node['guid'] is None:
                missing.add(path + ':expression-guid')
            else:
                _require(GUID.fullmatch(node['guid']) is not None, 'invalid expression GUID')
            nodes[path] = node
            input_guids, output_guids = set(), set()
            for key, (value, line) in properties.items():
                if key.startswith(('Outputs(', 'FunctionOutputs(')):
                    index = re.fullmatch(r'(?:Outputs|FunctionOutputs)\((\d+)\)', key)
                    _require(index is not None, 'invalid output index')
                    node['outputs'].add(int(index[1]))
                    if key.startswith('FunctionOutputs('):
                        output_guid = _field(value, 'ExpressionOutputId')
                        _require(isinstance(output_guid, str) and GUID.fullmatch(output_guid), 'function output edge GUID required')
                        _require(output_guid not in output_guids, 'duplicate function output GUID')
                        output_guids.add(output_guid)
                edge_guid = _field(value, 'ExpressionInputId')
                if key.startswith('FunctionInputs('):
                    _require(isinstance(edge_guid, str) and GUID.fullmatch(edge_guid), 'function input edge GUID required')
                    _require(edge_guid not in input_guids, 'duplicate function input GUID')
                    input_guids.add(edge_guid)
                if 'Expression=' not in value:
                    continue
                refs = REF.findall(value)
                _require(len(refs) == 1, 'ambiguous serialized edge')
                cls_ref, ref = refs[0]
                target = _canonical(ref, asset)
                index = _integer(value, 'OutputIndex', missing, path + '.' + key)
                mask = [_integer(value, field, missing, path + '.' + key) for field in MASK_FIELDS]
                _require(all(v in (None, 0, 1) for v in mask), 'invalid edge mask')
                if mask[0] == 0:
                    _require(all(v in (None, 0) for v in mask[1:]), 'disabled mask with active channel')
                if mask[0] == 1 and all(v is not None for v in mask[1:]):
                    _require(any(mask[1:]), 'empty active mask')
                node['edges'].append({'input': key, 'input_name': _field(value, 'InputName'),
                    'source': target, 'class': cls_ref, 'output_index': index, 'mask': mask,
                    'input_guid': edge_guid, 'line': line})
            if cls == PREFIX + 'NamedRerouteDeclaration':
                guid = properties.get('VariableGuid', (None,))[0]
                _require(isinstance(guid, str) and GUID.fullmatch(guid), 'reroute declaration GUID required')
                _require((asset, guid) not in declarations, 'ambiguous reroute declaration GUID')
                declarations[asset, guid] = path

    if packet['root'] not in functions:
        missing.add('root-function')
    dependencies, resolved, ports = {}, {}, {}
    for path, node in nodes.items():
        direction = {PREFIX + 'FunctionInput': 'input', PREFIX + 'FunctionOutput': 'output'}.get(node['class'])
        if direction is None:
            continue
        props = node['properties']
        guid = props.get('Id', (None,))[0]
        if guid is None:
            missing.add(path + ':function-port-guid')
            continue
        _require(GUID.fullmatch(guid) is not None, 'invalid function port GUID')
        identity = (node['function'], direction, guid)
        _require(identity not in ports, 'ambiguous function port GUID')
        ports[identity] = props.get('InputName' if direction == 'input' else 'OutputName', (None,))[0]
        if direction == 'input' and props.get('bUsePreviewValueAsDefault', (None,))[0] == 'True' and 'PreviewValue' not in props:
            missing.add(path + ':explicit-preview-default-vector')
    expression_guids = set()
    for path, node in nodes.items():
        identity = (node['function'], node['guid'])
        if node['guid'] is not None:
            _require(identity not in expression_guids, 'duplicate expression GUID')
            expression_guids.add(identity)
        props = node['properties']
        for edge in node['edges']:
            _require(edge['source'] in nodes, 'missing expression edge: ' + edge['source'])
            source = nodes[edge['source']]
            _require(source['class'] == edge['class'], 'edge class mismatch')
            index = edge['output_index']
            if index is not None:
                if source['outputs']:
                    _require(index in source['outputs'], 'output index out of range')
                else:
                    missing.add(edge['source'] + ':output-defaults')
        if node['class'] == PREFIX + 'NamedRerouteUsage':
            guid = props.get('DeclarationGuid', (None,))[0]
            _require(isinstance(guid, str) and GUID.fullmatch(guid), 'reroute usage GUID required')
            target = declarations.get((node['function'], guid))
            _require(target is not None, 'missing reroute declaration')
            if 'Declaration' in props:
                refs = REF.findall(props['Declaration'][0])
                _require(len(refs) == 1 and refs[0][0] == PREFIX + 'NamedRerouteDeclaration'
                         and _canonical(refs[0][1], node['function']) == target, 'foreign/mismatched reroute declaration')
            resolved[path] = target
        if node['class'] == PREFIX + 'MaterialFunctionCall':
            refs = REF.findall(props.get('MaterialFunction', ('',))[0])
            _require(len(refs) == 1 and refs[0][0] == '/Script/Engine.MaterialFunction', 'function dependency identity required')
            dependency = refs[0][1]
            _require(dependency.startswith('/') and ':' not in dependency, 'absolute dependency identity required')
            dependencies[path] = dependency
            if dependency not in functions:
                missing.add(dependency + ':function-package-and-export')
            elif functions[dependency]['export'] in artifacts:
                # Bind serialized call-side port IDs/names to the actual nested
                # export, never merely to its package hash or a caller's label.
                for key, (value, _) in props.items():
                    if not key.startswith(('FunctionInputs(', 'FunctionOutputs(')):
                        continue
                    direction = 'input' if key.startswith('FunctionInputs(') else 'output'
                    field = 'ExpressionInputId' if direction == 'input' else 'ExpressionOutputId'
                    guid = _field(value, field)
                    _require(isinstance(guid, str) and GUID.fullmatch(guid), 'function call port GUID required')
                    identity = (dependency, direction, guid)
                    _require(identity in ports, 'missing/foreign nested function port GUID')
                    label = _field(value, 'InputName' if direction == 'input' else 'OutputName')
                    if label is None or ports[identity] is None:
                        missing.add(path + '.' + key + ':serialized-port-name')
                    else:
                        _require(label == ports[identity].strip('"'), 'nested function port name mismatch')
        if node['class'] in (PREFIX + 'FeatureLevelSwitch', PREFIX + 'PathTracingQualitySwitch'):
            context = packet['switch_context'].get(path)
            branches = {edge['input'] for edge in node['edges']}
            if synthetic and context is not None:
                _keys(context, ('synthetic', 'branch'))
                _require(context['synthetic'] is True and context['branch'] in branches, 'invalid synthetic switch branch')
            else:
                missing.add(path + ':source-supported-active-context')
        if node['class'] == PREFIX + 'Custom':
            missing.add(path + ':custom-scene-color-code-and-include-model')

    _require(isinstance(packet['switch_context'], dict) and set(packet['switch_context']) <= set(nodes), 'unknown switch context node')
    _require(all(nodes[path]['class'] in (PREFIX + 'FeatureLevelSwitch', PREFIX + 'PathTracingQualitySwitch')
                 for path in packet['switch_context']), 'context supplied for non-switch')
    graph = {path: [e['source'] for e in node['edges']] + ([resolved[path]] if path in resolved else []) for path, node in nodes.items()}
    # Functions add edges to all their serialized expressions, preventing hidden
    # recursive dependency cycles even outside the nominated material route.
    for asset in functions:
        graph[asset] = [path for path, node in nodes.items() if node['function'] == asset]
    for path, dependency in dependencies.items():
        if dependency in functions:
            graph[path].append(dependency)
    visiting, visited = set(), set()

    def visit(path):
        _require(path not in visiting, 'cyclic expression/function/reroute dependency')
        if path in visited:
            return
        visiting.add(path)
        for child in graph[path]:
            visit(child)
        visiting.remove(path)
        visited.add(path)
    for path in graph:
        visit(path)

    _require(isinstance(packet['black_constants'], list), 'black constants array required')
    checked_black = set()
    for record in packet['black_constants']:
        _keys(record, ('node', 'value', 'class_default'))
        path, value = record['node'], record['value']
        _require(path in nodes and path not in checked_black and nodes[path]['class'] == PREFIX + 'Constant3Vector', 'exact unique vector constant required')
        checked_black.add(path)
        _require(isinstance(value, list) and len(value) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in value)
                 and value[:3] == [0, 0, 0], 'explicit finite black RGBA required')
        literal = nodes[path]['properties'].get('Constant', (None,))[0]
        if literal is None and record['class_default'] is not None:
            data = artifact(record['class_default'], 'class_default', PREFIX + 'Constant3Vector')
            if data is not None:
                declared, bodies = _blocks(data.decode('utf-8'))
                matches = [p for p, (cls, name) in declared.items() if cls == PREFIX + 'Constant3Vector' and name == 'Default__MaterialExpressionConstant3Vector']
                _require(matches == ['/Script/Engine.Default__MaterialExpressionConstant3Vector']
                         and matches[0] in bodies, 'explicit exact class-default object required')
                literal = _properties(bodies[matches[0]][2]).get('Constant', (None,))[0]
        if literal is None:
            missing.add(path + ':explicit-black-default-vector')
            continue
        components = [_field(literal, c) for c in ('R', 'G', 'B', 'A')]
        _require(all(v is not None for v in components), 'omitted vector component is not zero')
        _require([float(v) for v in components] == value, 'black vector witness mismatch')
    if not synthetic:
        for name in ('MaterialExpressionConstant3Vector_0', 'MaterialExpressionConstant3Vector_1'):
            if ROOT + ':' + name not in checked_black:
                missing.add(ROOT + ':' + name + ':explicit-black-default-vector')
        # v1 intentionally has no real active-context collector/acceptance model.
        missing.add('intrinsic-transmission-transport-model')
    return {'version': VERSION, 'synthetic': synthetic,
            'structural_state': 'PENDING' if missing else 'CLOSED_SYNTHETIC',
            'required_missing_evidence': sorted(missing), 'nodes': len(nodes),
            'serialized_edges': sum(len(n['edges']) for n in nodes.values()),
            'resolved_reroutes': resolved, 'dependencies': dependencies,
            'root_emissive_route': 'scene-color-transmission-composite',
            'intrinsic_emission': 'UNKNOWN', 'material_acceptance': HOLD,
            'native_validation': None, 'quality': None}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--artifact-root', type=Path)
    args = parser.parse_args(argv)
    packet = json.loads(args.packet.read_text(encoding='utf-8'))
    base = (args.artifact_root or args.packet.parent).resolve()
    files = {}
    for key, record in packet['artifacts'].items():
        path = (base / record['file']).resolve()
        _require(path.is_relative_to(base), 'artifact path escapes root')
        if path.is_file():
            files[key] = path.read_bytes()
    print(json.dumps(validate(packet, files), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
