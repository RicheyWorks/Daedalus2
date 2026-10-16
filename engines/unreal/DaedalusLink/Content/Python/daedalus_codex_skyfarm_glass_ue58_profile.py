# SPDX-License-Identifier: MIT
"""Pinned UE5.8 transmission-composite ABI review, offline only.

This version recognizes the observed importer ABI, not intrinsic transport
correctness. It cannot clear the glass: nested function/default/render-path
proof has no supported receiving schema yet. Flags, hashes alone and fabricated
zero-emission defaults cannot satisfy that missing proof. No Unreal imports.
The historical generic policy is loaded byte-for-byte and never modified.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

PROFILE = 'ue58-transmission-composite-v1'
GENERIC_SHA = '76a6937750ea8592abf150fb8acc62394d5906ea306802856d5c889090dcf2a9'
_path = Path(__file__).with_name('daedalus_codex_skyfarm_glass.py')
_raw = _path.read_bytes()
if hashlib.sha256(_raw).hexdigest() != GENERIC_SHA:
    raise ValueError('reviewed historical glass policy changed')
_generic = {'__name__': '_skyfarm_glass_generic_frozen'}
exec(compile(_raw, str(_path), 'exec'), _generic)

BODY_TEXT = {'bytes': 348703,
    'sha256': '05cd7a779fd39edc88eb43dc214aa66a426e373c1450d639a84f88274a626641'}
SOURCE_PINS = {
    'qualification': {'bytes': 9928, 'sha256': '9e8d1a397d0eb607951ffd5ae3c936bca1ef88511a5bef5476c2fb63b1129ac8'},
    'source': {'bytes': 88052, 'sha256': '1e208959d249b8b781027ad2bae69dbb70bb4472db01e9bf12da707d93ad7d0a'},
    'manifest': {'bytes': 5639, 'sha256': '7082cd07018dfa21254023ab5e715645e11e099a455a13cd81d59e2ad4f62a96'},
}
INPUTS = (
    'AlphaMode', 'BaseColorTexture', 'BaseColorFactor_RGB', 'BaseColorFactor_A',
    'BaseColorTexture_Offset_X', 'BaseColorTexture_Offset_Y', 'BaseColorTexture_Scale_X',
    'BaseColorTexture_Scale_Y', 'BaseColorTexture_Rotation', 'BaseColorTexture_TexCoord',
    'BaseColorTexture_TilingMethod', 'AlphaCutoff', 'MetallicRoughnessTexture', 'MetallicFactor',
    'RoughnessFactor', 'MetallicRoughnessTexture_Offset_X', 'MetallicRoughnessTexture_Offset_Y',
    'MetallicRoughnessTexture_Scale_X', 'MetallicRoughnessTexture_Scale_Y',
    'MetallicRoughnessTexture_Rotation', 'MetallicRoughnessTexture_TexCoord',
    'MetallicRoughnessTexture_TilingMethod', 'NormalTexture', 'NormalScale',
    'NormalTexture_Offset_X', 'NormalTexture_Offset_Y', 'NormalTexture_Scale_X',
    'NormalTexture_Scale_Y', 'NormalTexture_Rotation', 'NormalTexture_TexCoord',
    'NormalTexture_TilingMethod', 'OcclusionTexture', 'OcclusionStrength',
    'OcclusionTexture_Offset_X', 'OcclusionTexture_Offset_Y', 'OcclusionTexture_Scale_X',
    'OcclusionTexture_Scale_Y', 'OcclusionTexture_Rotation', 'OcclusionTexture_TexCoord',
    'OcclusionTexture_TilingMethod', 'SpecularTexture', 'SpecularFactor',
    'SpecularTexture_Offset_X', 'SpecularTexture_Offset_Y', 'SpecularTexture_Scale_X',
    'SpecularTexture_Scale_Y', 'SpecularTexture_Rotation', 'SpecularTexture_TexCoord',
    'SpecularTexture_TilingMethod', 'IOR', 'TransmissionTexture', 'TransmissionFactor',
    'TransmissionTexture_Offset_X', 'TransmissionTexture_Offset_Y', 'TransmissionTexture_Scale_X',
    'TransmissionTexture_Scale_Y', 'TransmissionTexture_Rotation', 'TransmissionTexture_TexCoord',
    'TransmissionTexture_TilingMethod', 'IridescenceIOR', 'IridescenceTexture',
    'IridescenceThicknessTexture', 'IridescenceFactor', 'IridescenceThicknessMinimum',
    'IridescenceThicknessMaximum', 'IridescenceTexture_Offset_X', 'IridescenceTexture_Offset_Y',
    'IridescenceTexture_Scale_X', 'IridescenceTexture_Scale_Y', 'IridescenceTexture_Rotation',
    'IridescenceTexture_TexCoord', 'IridescenceTexture_TilingMethod',
    'IridescenceThicknessTexture_Offset_X', 'IridescenceThicknessTexture_Offset_Y',
    'IridescenceThicknessTexture_Scale_X', 'IridescenceThicknessTexture_Scale_Y',
    'IridescenceThicknessTexture_Rotation', 'IridescenceThicknessTexture_TexCoord',
    'IridescenceThicknessTexture_TilingMethod', 'AnisotropyTexture', 'AnisotropyStrength',
    'AnisotropyRotation', 'AnisotropyTexture_Offset_X', 'AnisotropyTexture_Offset_Y',
    'AnisotropyTexture_Scale_X', 'AnisotropyTexture_Scale_Y', 'AnisotropyTexture_Rotation',
    'AnisotropyTexture_TexCoord', 'AnisotropyTexture_TilingMethod')
OUTPUTS = ('TransmissionColor', 'BaseColor', 'Metallic', 'Specular', 'Roughness',
           'Anisotropy', 'EmissiveColor', 'Opacity', 'Normal', 'Tangent', 'Occlusion')
MISSING = ('nested-temporal-blur-scene-color-closure', 'active-render-and-feature-level-path',
           'explicit-black-constant-defaults')


def _same_pin(actual, expected):
    return (_generic['_pin'](actual)
            and all(actual.get(k) == v for k, v in expected.items()))


def intrinsic_transport(body_text):
    """Evidence request, never an evidence-of-success flag."""
    if not _same_pin(body_text, BODY_TEXT):
        raise ValueError('exact retained transmission T3D witness required')
    return {'model': PROFILE, 'body_text': deepcopy(body_text),
            'missing_evidence': list(MISSING), 'intrinsic_proof': None}


def future_witness_plan():
    """Declarative source plan only; it contains no native dispatcher.

    No active-render-path getter is inferred from material flags. Resolve its
    public source/API and exact return shape before requesting an editor turn.
    """
    root = _generic['FUNCTION']
    return {'profile': PROFILE, 'executable': False, 'native_authorized': False,
        'body_package': deepcopy(_generic['FUNCTION_BODY']), 'body_text': dict(BODY_TEXT),
        'root_function': root,
        'known_route': ['FunctionOutput_6.EmissiveColor', 'BreakMaterialAttributes_0[5]',
            'PathTracingQualitySwitch_0.Normal', 'GetMaterialAttributes_0',
            'MakeMaterialAttributes_0.EmissiveColor', 'FeatureLevelSwitch_0.Default/Inputs3/4',
            'Multiply_0', 'Multiply_5', 'Multiply_4', 'MaterialFunctionCall_23.MF_Temporal_Blur'],
        'nested_reference': '/InterchangeAssets/gltf/MaterialFunctions/MF_Temporal_Blur.MF_Temporal_Blur',
        'nested_package': {'bytes': 67200,
            'sha256': '05526bea6d93a9252a928eb1e1aac4d615bdce09c6d64be15159979f694630b3'},
        'nested_inputs': ['ior', 'BlurIntensity', 'Normals', 'DisableRefraction'],
        'nested_outputs': ['BluredScene', 'BluredDepth'],
        'black_candidates': [root + ':MaterialExpressionConstant3Vector_0',
                             root + ':MaterialExpressionConstant3Vector_1'],
        'api_source_pins': {
            'Engine/Source/Editor/MaterialEditor/Public/MaterialEditingLibrary.h': {'bytes': 34869,
                'sha256': '5201a2be4ed754246bca79d115626dd3b59471989366f87cd7110a206047375f'},
            'Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionConstant3Vector.h': {'bytes': 1058,
                'sha256': '09f0bd423e8b4c091f790c29ce72d79d40f82af25268d1ccc4202803ab6b3566'},
            'Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionNamedReroute.h': {'bytes': 5684,
                'sha256': 'c49ef5d53aaf6cae1ec23ce3b0d27042d53a133a4c0f941499f194cbec347e39'}},
        'reads': ['find_object on exact already-referenced/loaded function; no load fallback',
            'MaterialEditingLibrary.get_material_function_expressions; exact class/path inventory',
            'MaterialFunctionCall.material_function; normal public get_editor_property',
            'get_material_expression_input_names and get_inputs_for_material_function_expression',
            'ObjectExporterT3D plus get_default_object for exact class-default/delta input witnesses',
            'Constant3Vector.constant (LinearColor r/g/b/a) plus explicit class default; no omitted-value inference'],
        'closure_requirements': ['Resolve NamedReroute Declaration/VariableGuid through T3D; no protected property reflection.',
            'Follow Usage14->Declaration4 InverseFresnel, Usage24->Declaration7 Transmission, Usage6->Declaration0 BaseColor.',
            'Retain exact nested function objects/package pins/exports, edge masks/output indices/GUIDs, custom scene-color code/includes and defaults.'],
        'active_context_gap': 'UWorld.GetFeatureLevel and FEditorViewportClient.GetViewMode are not Python-reflected; material-quality/pathtracing CVars alone do not prove the active viewport/compiler branch.',
        'unresolved_before_native': ['Source-confirm and pin active render-path/feature-level public getter; flags alone cannot select branch.',
            'Pin each actually referenced nested body and serialized dependency edge; no foreign/unknown closure.',
            'Source-confirm scene-color dependency and every switch/default/black value before defining acceptance schema.'],
        'guards': ['New explicit bounded READONLY scope; consumed32998 cannot run this plan.',
            'Sole existing editor/custody, producer actual terminal+normal release, no competing compute/queue/PIE.',
            'Fresh numeric resource floors, exact source/input pins, absolute reserve; no lease renewal/replay.',
            'Preserve231packages/152actors/184sources/mapf8887fde and exact2helddirty-unsaved/unplaced; before==after.',
            'Evidence files only; no loads/asset setters/recompile/import/save/placement/selection/camera/Play/build.']}


def check_observation(observed, body_text, source_proof):
    """Validate the closed top-level ABI, then retain the intrinsic-model HOLD.

    Even a complete synthetic top-level record stays held. This version does
    not accept nested proof flags or pretend a missing proof collector exists.
    """
    request = intrinsic_transport(body_text)
    if (not isinstance(source_proof, dict) or set(source_proof) != set(SOURCE_PINS)
            or any(not _same_pin(source_proof[k], v) for k, v in SOURCE_PINS.items())):
        raise ValueError('exact source qualification/GLB/manifest provenance required')
    p = _generic
    c = p['source_contract'](deepcopy(p['RAW']))
    if not isinstance(observed, dict):
        raise ValueError('retained observation required')
    if (observed.get('material') != p['MATERIAL'] or observed.get('mesh') != p['MESH']
            or observed.get('material_class') != '/Script/Engine.Material'
            or observed.get('mesh_class') != '/Script/Engine.StaticMesh'
            or observed.get('slot_materials') != [p['MATERIAL']] or observed.get('physical') != c['physical']
            or type(observed.get('active_customized_uvs')) is not int or observed['active_customized_uvs'] != 0
            or observed['physical'].get('TwoSided') is not True
            or observed['physical'].get('bScreenSpaceReflections') is not True):
        raise ValueError('exact held object/slot/physical state required')
    geo = observed.get('geometry', {})
    if (type(geo.get('triangles')) is not int or geo['triangles'] != 48
            or not p['_numbers'](geo.get('build_scale'), [1., 1., 1.], 0.)
            or geo.get('nanite') is not False or geo.get('generate_lightmap_uvs') is not False
            or type(geo.get('simple_collision_count')) is not int or geo['simple_collision_count'] != 0
            or geo.get('import_data_class') != 'InterchangeAssetImportData'
            or any(not p['_numbers'](geo.get('bounds', {}).get(edge), p['BOUNDS'][edge], .2) for edge in ('min', 'max'))):
        raise ValueError('exact48tri/baked bounds/unit scale/import readback required')
    g = observed.get('graph', {}); call = g.get('call'); nodes = g.get('nodes', {})
    prefix = '/Script/Engine.MaterialExpression'
    if (not isinstance(call, str) or not call.startswith(p['MATERIAL'] + ':')
            or g.get('function') != p['FUNCTION'] or nodes.get(call) != prefix + 'MaterialFunctionCall'):
        raise ValueError('exact owned transmission call required')
    if g.get('function_input_names') != list(INPUTS) or g.get('function_outputs') != list(OUTPUTS):
        raise ValueError('exact installed89input/11output ABI required')
    factors = g.get('factor_inputs', {}); table = g.get('function_inputs', {})
    wanted = {**c['factor_inputs'], 'AlphaMode': [2.]}
    if (set(factors) != set(wanted) or set(table) != set(INPUTS)
            or {k for k, v in table.items() if v is not None} != set(wanted)):
        raise ValueError('exact six connected factors and complete disconnected input table required')
    used = {call}
    for name, value in wanted.items():
        row = factors[name]; node = row.get('node'); ref = row.get('reference')
        cls = prefix + ('Constant3Vector' if name == 'BaseColorFactor_RGB' else 'Constant')
        expected = {'Expression': node, 'OutputIndex': 0, 'InputName': name,
                    'Mask': 0, 'MaskR': 0, 'MaskG': 0, 'MaskB': 0, 'MaskA': 0}
        if name == 'BaseColorFactor_RGB':
            expected.update(Mask=1, MaskR=1, MaskG=1, MaskB=1)
        if (set(row) != {'node', 'value', 'reference'}
                or not isinstance(node, str) or not node.startswith(p['MATERIAL'] + ':') or node in used
                or nodes.get(node) != cls or not p['_numbers'](row.get('value'), value, .0001)
                or ref != expected or table[name] != ref
                or any(type(ref[k]) is not int for k in ('OutputIndex', 'Mask', 'MaskR', 'MaskG', 'MaskB', 'MaskA'))):
            raise ValueError('exact typed raw constant/output0 mask required: ' + name)
        used.add(node)
    if g.get('omitted_defaults') != {name: {'missing_function_input': True, 'matches': 0}
                                     for name in ('EmissiveFactor', 'EmissiveStrength')}:
        raise ValueError('missing direct emission inputs must stay explicit; no invented defaults')
    if any(row['missing_function_input'] is not True or type(row['matches']) is not int
           for row in g['omitted_defaults'].values()):
        raise ValueError('typed missing-input observation required')
    roots = g.get('roots', {}); defaults = g.get('default_roots', {})
    if set(roots) != set(p['ROOTS']) or set(defaults) != set(p['ROOTS']):
        raise ValueError('all30ordinary roots/defaults required')
    for name in p['ROOTS']:
        if not p['_default_reference'](defaults[name]):
            raise ValueError('complete typed disconnected root default required')
        expected = dict(defaults[name])
        if name in p['OUTPUTS']:
            index = OUTPUTS.index(p['OUTPUTS'][name]); expected.update(Expression=call, OutputIndex=index)
            core = {k: roots[name].get(k) for k in ('Expression', 'OutputIndex', 'InputName', 'Mask', 'MaskR', 'MaskG', 'MaskB', 'MaskA')}
            if not p['_reference'](core, call, index):
                raise ValueError('root mask/index differs: ' + name)
        if roots[name] != expected:
            raise ValueError('root/default override differs: ' + name)
    custom = g.get('custom_outputs', [])
    if len(custom) != 1:
        raise ValueError('one separate ThinTranslucent custom output required')
    row = custom[0]; node = row.get('node')
    if (not isinstance(node, str) or not node.startswith(p['MATERIAL'] + ':') or node in used
            or nodes.get(node) != prefix + 'ThinTranslucentMaterialOutput'
            or not p['_reference'](row.get('TransmittanceColor'), call, 0)
            or row.get('SurfaceCoverage') != row.get('default_SurfaceCoverage')
            or not p['_default_reference'](row.get('default_SurfaceCoverage'))):
        raise ValueError('exact custom transmission/default coverage required')
    used.add(node)
    if set(nodes) != used:
        raise ValueError('extra/foreign/disconnected expression in closed graph')
    proofs = g.get('proofs', {})
    if (set(proofs) != {'root_default', 'root_delta', 'custom_default', 'custom_delta', 'function_body_package'}
            or any(not p['_pin'](v) for v in proofs.values())
            or not _same_pin(proofs['function_body_package'], p['FUNCTION_BODY'])):
        raise ValueError('separate root/custom witnesses and exact installed body pin required')
    if 'intrinsic_transport' in g and g['intrinsic_transport'] != request:
        raise ValueError('unsupported/repointed intrinsic proof; no evidence flags accepted')
    return {'stage': 'HOLD_INTRINSIC_TRANSMISSION_MODEL_UNPROVEN', 'profile': PROFILE,
        'top_level_abi': 'VALID', 'intrinsic_transport': request, 'native_ready': False,
        'runtime_authorized': False, 'glass_must_remain_held_until_admitted': True,
        'source_alpha': c['factor_inputs']['BaseColorFactor_A'][0], 'source_transmission': .25,
        'limits': ['No intrinsic emission-zero claim; Normal includes temporal-blur scene-color composition.',
            'Source qualification pins POSITION/NORMAL and no UV; native normal vectors were not observed.',
            'No branch accepted, saves/placement/appearance remain unadmitted.']}
