# SPDX-License-Identifier: MIT
"""Small offline evidence tests: no engine, network, process or asset writes."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

import codex_skyfarm_glass_closure_contract as contract


ASSET = '/Synthetic/MF_Test.MF_Test'
P = contract.PREFIX


def node(name, kind, *properties):
    return name, P + kind, list(properties)


def export(nodes, asset=ASSET):
    short = asset.rsplit('.', 1)[-1]
    result = [f'Begin Object Class=/Script/Engine.MaterialFunction Name="{short}" ExportPath="/Script/Engine.MaterialFunction\'{asset}\'"']
    for name, cls, _ in nodes:
        result += [f'Begin Object Class={cls} Name="{name}" ExportPath="{cls}\'{asset}:{name}\'"', 'End Object']
    for i, (name, cls, properties) in enumerate(nodes):
        result += [f'Begin Object Name="{name}" ExportPath="{cls}\'{asset}:{name}\'"',
                   f'MaterialExpressionGuid={i + 1:032X}', *properties, 'End Object']
    return ('\n'.join(result + ['End Object']) + '\n').encode()


def edge(name='Input', target='Black', kind='Constant3Vector', index=0, mask=(1, 1, 1, 1, 0)):
    fields = ','.join(f'{key}={value}' for key, value in zip(contract.MASK_FIELDS, mask))
    return (f'{name}=(Expression="{P}{kind}\'MF_Test:{target}\'",OutputIndex={index},'
            f'InputName="{name}",{fields})')


def packet(nodes=None):
    if nodes is None:
        nodes = [node('Black', 'Constant3Vector', 'Constant=(R=0,G=0,B=0,A=1)', 'Outputs(0)=(Mask=1,MaskR=1,MaskG=1,MaskB=1)'),
                 node('Output', 'FunctionOutput', edge(), 'Id=' + 'E' * 32, 'OutputName="EmissiveColor"')]
    data = export(nodes)
    artifacts = {'package': b'opaque synthetic package', 'body': data}
    envelope = {'version': contract.VERSION, 'synthetic': True, 'root': ASSET,
                'artifacts': {}, 'functions': [{'asset': ASSET, 'class': '/Script/Engine.MaterialFunction', 'package': 'package', 'export': 'body'}],
                'black_constants': [{'node': ASSET + ':Black', 'value': [0, 0, 0, 1], 'class_default': None}], 'switch_context': {}}
    for name, payload in artifacts.items():
        envelope['artifacts'][name] = {'kind': 'package' if name == 'package' else 't3d', 'owner': ASSET,
            'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'file': name + '.bin'}
    return envelope, artifacts


def replace_body(envelope, files, data):
    files['body'] = data
    envelope['artifacts']['body'].update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


class ClosureTests(unittest.TestCase):
    def test_synthetic_closed_never_native_or_zero_emission(self):
        result = contract.validate(*packet())
        self.assertEqual(result['structural_state'], 'CLOSED_SYNTHETIC')
        self.assertTrue(result['synthetic'])
        self.assertEqual(result['root_emissive_route'], 'scene-color-transmission-composite')
        self.assertEqual(result['intrinsic_emission'], 'UNKNOWN')
        self.assertEqual(result['material_acceptance'], contract.HOLD)
        self.assertIsNone(result['native_validation'])
        self.assertIsNone(result['quality'])

    def assert_bad(self, envelope, files, message):
        with self.assertRaisesRegex(contract.EvidenceError, message):
            contract.validate(envelope, files)

    def test_exact_pin_mismatch(self):
        e, f = packet(); f['body'] += b'changed'
        self.assert_bad(e, f, 'pin mismatch')

    def test_unknown_envelope_field_and_artifact(self):
        e, f = packet(); e['accepted'] = True
        self.assert_bad(e, f, 'closed envelope')
        e, f = packet(); f['unowned'] = b'x'
        self.assert_bad(e, f, 'undeclared supplied')

    def test_missing_export_stays_pending(self):
        e, f = packet(); del f['body']; e['black_constants'] = []
        self.assertIn('artifact:body', contract.validate(e, f)['required_missing_evidence'])

    def test_duplicate_function_and_body(self):
        e, f = packet(); e['functions'].append(deepcopy(e['functions'][0]))
        self.assert_bad(e, f, 'duplicate function')
        e, f = packet(); data = f['body'].replace(b'End Object\nEnd Object\n', b'End Object\nBegin Object Name="Output" ExportPath="/Script/Engine.MaterialExpressionFunctionOutput\'/Synthetic/MF_Test.MF_Test:Output\'"\nX=1\nEnd Object\nEnd Object\n')
        replace_body(e, f, data); self.assert_bad(e, f, 'duplicate object body')

    def test_foreign_edge_missing_edge_and_class(self):
        for old, new, message in [(b'MF_Test:Black', b'Foreign:Black', 'foreign'),
                                  (b'MF_Test:Black', b'MF_Test:Absent', 'missing expression'),
                                  (b'ExpressionConstant3Vector\'MF_Test:Black', b'ExpressionConstant\'MF_Test:Black', 'class mismatch')]:
            e, f = packet()
            # Mutate the input reference only, preserving declaration identities.
            replace_body(e, f, f['body'].replace(edge().encode(), edge().encode().replace(old, new)))
            self.assert_bad(e, f, message)

    def test_duplicate_input_property(self):
        e, f = packet(); line = edge().encode()
        replace_body(e, f, f['body'].replace(line, line + b'\n' + line))
        self.assert_bad(e, f, 'duplicate serialized property')

    def test_duplicate_nested_edge_fields_conflicting_and_identical(self):
        for name, original, conflict in [('OutputIndex', '0', '9'), ('Mask', '1', '0'),
                                         ('MaskR', '1', '0'), ('MaskG', '1', '0'),
                                         ('MaskB', '1', '0'), ('MaskA', '0', '1'),
                                         ('InputName', '"Input"', '"Other"')]:
            for repeated in (original, conflict):
                with self.subTest(field=name, repeated=repeated):
                    e, f = packet()
                    old = f'{name}={original}'.encode()
                    changed = edge().encode().replace(old, old + f', {name}={repeated}'.encode())
                    replace_body(e, f, f['body'].replace(edge().encode(), changed))
                    self.assert_bad(e, f, 'duplicate serialized struct field: ' + name)

    def test_duplicate_nested_call_guids_conflicting_and_identical(self):
        for direction, field in [('Inputs', 'ExpressionInputId'), ('Outputs', 'ExpressionOutputId')]:
            for repeated in ('A' * 32, 'B' * 32):
                with self.subTest(direction=direction, repeated=repeated):
                    nodes = [node('Call', 'MaterialFunctionCall',
                                  f'MaterialFunction="/Script/Engine.MaterialFunction\'{contract.TEMPORAL}\'"',
                                  f'Function{direction}(0)=({field}=' + 'A' * 32 + f',{field}={repeated},Input=(InputName="ior"))')]
                    e, f = packet(nodes); e['black_constants'] = []
                    self.assert_bad(e, f, 'duplicate serialized struct field: ' + field)

    def test_duplicate_empty_nested_field_is_not_omission(self):
        e, f = packet()
        replace_body(e, f, f['body'].replace(b'OutputIndex=0', b'OutputIndex=0,OutputIndex='))
        self.assert_bad(e, f, 'duplicate serialized struct field: OutputIndex')

    def test_duplicate_nested_vector_components_conflicting_and_identical(self):
        for component, original, conflict in [('R', '0', '1'), ('G', '0', '1'),
                                               ('B', '0', '1'), ('A', '1', '0')]:
            for repeated in (original, conflict):
                with self.subTest(component=component, repeated=repeated):
                    e, f = packet()
                    old = b'Constant=(R=0,G=0,B=0,A=1)'
                    changed = old.replace(f'{component}={original}'.encode(),
                                          f'{component}={original},{component}={repeated}'.encode())
                    replace_body(e, f, f['body'].replace(old, changed))
                    self.assert_bad(e, f, 'duplicate serialized struct field: ' + component)

    def test_output_index_and_masks(self):
        for old, new, message in [(b'OutputIndex=0', b'OutputIndex=9', 'out of range'),
                                  (b'MaskA=0', b'MaskA=2', 'invalid edge mask'),
                                  (b'Mask=1,MaskR=1', b'Mask=0,MaskR=1', 'disabled mask')]:
            e, f = packet(); replace_body(e, f, f['body'].replace(old, new)); self.assert_bad(e, f, message)

    def test_omitted_edge_values_are_unknown_not_zero(self):
        e, f = packet(); replace_body(e, f, f['body'].replace(b',OutputIndex=0', b'').replace(b',MaskA=0', b''))
        result = contract.validate(e, f)
        self.assertEqual(result['structural_state'], 'PENDING')
        self.assertTrue(any('OutputIndex-default-witness' in item for item in result['required_missing_evidence']))
        self.assertTrue(any('MaskA-default-witness' in item for item in result['required_missing_evidence']))

    def test_omitted_black_and_hash_flag_do_not_prove_zero(self):
        e, f = packet(); replace_body(e, f, f['body'].replace(b'Constant=(R=0,G=0,B=0,A=1)\n', b''))
        self.assertIn(ASSET + ':Black:explicit-black-default-vector', contract.validate(e, f)['required_missing_evidence'])
        e['black_constants'][0]['zero_proven'] = True
        self.assert_bad(e, f, 'closed envelope')

    def test_partial_vector_and_wrong_vector_rejected(self):
        for value in [b'Constant=(R=0,G=0,B=0)', b'Constant=(R=1,G=0,B=0,A=1)']:
            e, f = packet(); replace_body(e, f, f['body'].replace(b'Constant=(R=0,G=0,B=0,A=1)', value))
            self.assert_bad(e, f, 'omitted vector|vector witness mismatch')

    def test_explicit_class_default_vector(self):
        e, f = packet(); replace_body(e, f, f['body'].replace(b'Constant=(R=0,G=0,B=0,A=1)\n', b''))
        cls = P + 'Constant3Vector'
        f['default'] = (f'Begin Object Class={cls} Name="Default__MaterialExpressionConstant3Vector" ExportPath="{cls}\'/Script/Engine.Default__MaterialExpressionConstant3Vector\'"\nConstant=(R=0,G=0,B=0,A=1)\nEnd Object\n').encode()
        e['artifacts']['default'] = {'kind': 'class_default', 'owner': cls, 'bytes': len(f['default']), 'sha256': hashlib.sha256(f['default']).hexdigest(), 'file': 'default.t3d'}
        e['black_constants'][0]['class_default'] = 'default'
        self.assertEqual(contract.validate(e, f)['structural_state'], 'CLOSED_SYNTHETIC')
        f['default'] = f['default'].replace(b'/Script/Engine.Default__', b'/Game/Foreign.Default__')
        e['artifacts']['default'].update(bytes=len(f['default']), sha256=hashlib.sha256(f['default']).hexdigest())
        self.assert_bad(e, f, 'exact class-default object required')

    def reroutes(self):
        return [node('Black', 'Constant3Vector', 'Constant=(R=0,G=0,B=0,A=1)', 'Outputs(0)=(Mask=1)'),
                node('Declaration', 'NamedRerouteDeclaration', 'VariableGuid=' + 'A' * 32, edge()),
                node('Usage', 'NamedRerouteUsage', 'DeclarationGuid=' + 'A' * 32,
                     f'Declaration="{P}NamedRerouteDeclaration\'MF_Test:Declaration\'"')]

    def test_resolve_reroute_exact_guid(self):
        result = contract.validate(*packet(self.reroutes()))
        self.assertEqual(result['resolved_reroutes'], {ASSET + ':Usage': ASSET + ':Declaration'})

    def test_guid_case_does_not_change_identity(self):
        nodes = self.reroutes(); nodes[2][2][0] = 'DeclarationGuid=' + 'a' * 32
        self.assertEqual(contract.validate(*packet(nodes))['resolved_reroutes'][ASSET + ':Usage'], ASSET + ':Declaration')
        nodes.append(node('Declaration2', 'NamedRerouteDeclaration', 'VariableGuid=' + 'a' * 32))
        e, f = packet(nodes); self.assert_bad(e, f, 'ambiguous reroute declaration GUID')

    def test_reroute_missing_foreign_ambiguous_cycle(self):
        for variant in ('missing', 'foreign', 'ambiguous', 'cycle'):
            nodes = self.reroutes()
            if variant == 'missing': nodes[2][2][0] = 'DeclarationGuid=' + 'B' * 32
            if variant == 'foreign': nodes[2][2][1] = nodes[2][2][1].replace('MF_Test:', 'Other:')
            if variant == 'ambiguous': nodes.append(node('Declaration2', 'NamedRerouteDeclaration', 'VariableGuid=' + 'A' * 32))
            if variant == 'cycle': nodes[1][2][1] = edge(target='Usage', kind='NamedRerouteUsage')
            e, f = packet(nodes); self.assert_bad(e, f, 'missing reroute|foreign|ambiguous|cyclic')

    def test_expression_cycle(self):
        nodes = [node('A', 'Multiply', edge(target='B', kind='Multiply'), 'Outputs(0)=(Mask=1)'),
                 node('B', 'Multiply', edge(target='A', kind='Multiply'), 'Outputs(0)=(Mask=1)')]
        e, f = packet(nodes); e['black_constants'] = []
        self.assert_bad(e, f, 'cyclic')

    def test_nested_package_is_not_body(self):
        nodes = [node('Call', 'MaterialFunctionCall', f'MaterialFunction="/Script/Engine.MaterialFunction\'{contract.TEMPORAL}\'"')]
        e, f = packet(nodes); e['black_constants'] = []
        e['functions'].append({'asset': contract.TEMPORAL, 'class': '/Script/Engine.MaterialFunction', 'package': None, 'export': None})
        result = contract.validate(e, f)
        self.assertIn(contract.TEMPORAL + ':body-export', result['required_missing_evidence'])

    def test_switch_unknown_and_explicit_synthetic_selection(self):
        e, f = packet([node('Black', 'Constant3Vector', 'Constant=(R=0,G=0,B=0,A=1)', 'Outputs(0)=(Mask=1)'),
                       node('Switch', 'PathTracingQualitySwitch', edge('Normal'), edge('PathTraced'))])
        self.assertEqual(contract.validate(e, f)['structural_state'], 'PENDING')
        e['switch_context'][ASSET + ':Switch'] = {'synthetic': True, 'branch': 'Normal'}
        self.assertEqual(contract.validate(e, f)['structural_state'], 'CLOSED_SYNTHETIC')
        e['switch_context'][ASSET + ':Switch']['branch'] = 'all'
        self.assert_bad(e, f, 'invalid synthetic switch')

    def test_real_retained_body_remains_pending(self):
        capture = Path(__file__).resolve().parents[3] / 'native-ingestion/SkyFarmGreenhouseBayR1/GlassGraphR1/CompatibilityR2/referenced-transmission-function.t3d'
        if not capture.is_file():
            self.skipTest('retained production evidence is not part of portable source checkout')
        data = capture.read_bytes()
        self.assertEqual(contract._pin(data), contract.ROOT_EXPORT)
        e = {'version': contract.VERSION, 'synthetic': False, 'root': contract.ROOT,
             'artifacts': {'body': {'kind': 't3d', 'owner': contract.ROOT, 'file': 'referenced-transmission-function.t3d',
                                    'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()},
                           'package': {'kind': 'package', 'owner': contract.ROOT, 'file': 'opaque.uasset',
                                       'bytes': contract.ROOT_PACKAGE[0], 'sha256': contract.ROOT_PACKAGE[1]}},
             'functions': [{'asset': contract.ROOT, 'class': '/Script/Engine.MaterialFunction', 'package': 'package', 'export': 'body'}],
             'black_constants': [], 'switch_context': {}}
        result = contract.validate(e, {'body': data})
        self.assertEqual(result['structural_state'], 'PENDING')
        self.assertEqual(result['material_acceptance'], contract.HOLD)
        self.assertTrue(any(contract.TEMPORAL in item for item in result['required_missing_evidence']))
        self.assertTrue(any('active-context' in item for item in result['required_missing_evidence']))
        self.assertTrue(any('black-default' in item for item in result['required_missing_evidence']))
        self.assertIsNone(result['native_validation'])

    def test_schema_closed_and_has_no_acceptance_override(self):
        path = Path(__file__).resolve().parents[2] / 'docs/contracts/skyfarm/glass-closure-v1.schema.json'
        schema = json.loads(path.read_text(encoding='utf-8'))
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']), set(packet()[0]))
        self.assertNotIn('accepted', schema['properties'])

    def test_function_call_input_output_guid_requirements(self):
        nodes = [node('Black', 'Constant3Vector', 'Constant=(R=0,G=0,B=0,A=1)', 'Outputs(0)=(Mask=1)'),
                 node('Call', 'MaterialFunctionCall', f'MaterialFunction="/Script/Engine.MaterialFunction\'{contract.TEMPORAL}\'"',
                      edge('FunctionInputs(0)'), 'FunctionOutputs(0)=(Output=(OutputName="Scene"))')]
        e, f = packet(nodes)
        self.assert_bad(e, f, 'input edge GUID required')
        nodes[1][2][1] = nodes[1][2][1].replace('=(Expression=', '=(ExpressionInputId=' + 'A' * 32 + ',Expression=')
        e, f = packet(nodes)
        self.assert_bad(e, f, 'output edge GUID required')
        nodes[1][2][2] = 'FunctionOutputs(0)=(ExpressionOutputId=' + 'B' * 32 + ',Output=(OutputName="Scene"))'
        e, f = packet(nodes)
        self.assertEqual(contract.validate(e, f)['structural_state'], 'PENDING')

    def test_nested_call_port_guid_and_name_bind_to_export(self):
        nested = '/Synthetic/MF_Child.MF_Child'
        nodes = [node('Call', 'MaterialFunctionCall', f'MaterialFunction="/Script/Engine.MaterialFunction\'{nested}\'"',
                      'FunctionOutputs(0)=(ExpressionOutputId=' + 'B' * 32 + ',Output=(OutputName="Scene"))')]
        e, f = packet(nodes); e['black_constants'] = []
        f['child'] = export([node('Result', 'FunctionOutput', 'Id=' + 'B' * 32, 'OutputName="Scene"')], nested)
        e['artifacts']['child'] = {'kind': 't3d', 'owner': nested, 'bytes': len(f['child']), 'sha256': hashlib.sha256(f['child']).hexdigest(), 'file': 'child.t3d'}
        e['functions'].append({'asset': nested, 'class': '/Script/Engine.MaterialFunction', 'package': None, 'export': 'child'})
        self.assertEqual(contract.validate(e, f)['dependencies'][ASSET + ':Call'], nested)
        replace_body(e, f, f['body'].replace(b'OutputName="Scene"', b'OutputName="Invented"'))
        self.assert_bad(e, f, 'port name mismatch')
        replace_body(e, f, f['body'].replace(b'ExpressionOutputId=' + b'B' * 32, b'ExpressionOutputId=' + b'C' * 32))
        self.assert_bad(e, f, 'foreign nested function port GUID')

    def test_duplicate_expression_guid(self):
        e, f = packet(); replace_body(e, f, f['body'].replace(b'MaterialExpressionGuid=' + b'0' * 31 + b'2', b'MaterialExpressionGuid=' + b'0' * 31 + b'1'))
        self.assert_bad(e, f, 'duplicate expression GUID')

    def test_serialized_name_path_mismatch(self):
        e, f = packet(); replace_body(e, f, f['body'].replace(b'Name="Black"', b'Name="Alias"'))
        self.assert_bad(e, f, 'name/export path mismatch')

    def test_disconnected_call_inputs_still_require_unique_guids(self):
        nodes = [node('Call', 'MaterialFunctionCall', f'MaterialFunction="/Script/Engine.MaterialFunction\'{contract.TEMPORAL}\'"',
                      'FunctionInputs(0)=(ExpressionInputId=' + 'A' * 32 + ',Input=(InputName="ior"))',
                      'FunctionInputs(1)=(ExpressionInputId=' + 'A' * 32 + ',Input=(InputName="BlurIntensity"))')]
        e, f = packet(nodes); e['black_constants'] = []
        self.assert_bad(e, f, 'duplicate function input GUID')

    def test_real_context_claim_and_wrong_family_pin(self):
        e, f = packet(); e['synthetic'] = False; e['root'] = contract.ROOT
        e['switch_context'] = {'fake': {'cvar': 1}}
        self.assert_bad(e, f, 'real active-context contract unavailable')
        e, f = packet(); e['synthetic'] = False; e['root'] = contract.ROOT
        e['functions'][0]['asset'] = contract.ROOT
        e['artifacts']['package']['owner'] = contract.ROOT
        e['artifacts']['body']['owner'] = contract.ROOT
        self.assert_bad(e, f, 'family pin mismatch')

    def test_import_has_no_native_collector_or_process_boundary(self):
        tree = ast.parse(Path(contract.__file__).read_text(encoding='utf-8'))
        imports = {alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names}
        self.assertEqual(imports, {'argparse', 'hashlib', 'json', 'math', 're'})
        self.assertEqual({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}, {'pathlib'})
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ('write_bytes', 'write_text', 'unlink', 'rename', 'system', 'spawn', 'exec') for n in ast.walk(tree)))


if __name__ == '__main__':
    unittest.main()
