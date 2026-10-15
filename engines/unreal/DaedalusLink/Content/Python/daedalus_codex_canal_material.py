# SPDX-License-Identifier: MIT
"""Closed Winter4 factor-only alpha material policy; never imports or saves.

Policy: owned_factor_alpha_parent_v1. Source is one raw glTF material definition
for HD_SkyWater_frost or HD_SkyFoam. No texture, UV, extension or gamma route.
The caller admits ownership/resources/queue/current baseline and provides
intent(operation, **details), a generator which cooperatively services the
caller's existing guards and durably flushes before returning. Every write
routine below is a generator: callers MUST consume it with ``yield from``.

yield from build_parent(package_path, source, intent) -> (unsaved Material, report)
yield from bind_instance(new_unsaved_mic, parent, source, intent) -> inspect report
inspect_partial_parent(parent, source, objects) -> read-only exact R4 partial proof
yield from resume_parent(parent, source, intent, objects) -> (unsaved Material, report)
inspect(mic, expected_parent, source, miri_scope=None) -> read-only report

Only the two new source-named MICs beneath ROOT may be rebound. Existing shared
parents, settings, actors and all save operations are outside this module.
API availability is source-supported; production must retain actual observations
and preserve any partial result. Importing this module performs no native work.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import time
import uuid
from types import GeneratorType

import unreal

POLICY = 'owned_factor_alpha_parent_v1'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Winter4CanalWaterR1_ad06dd2b3b95da8b'
PARTIAL_WATER = ROOT + '/OwnedParents/M_Codex_Winter4_Water_RawAlpha_R1'
PARTIAL_NODES = {'BaseColorFactor': 'MaterialExpressionVectorParameter_0',
                 'EmissiveFactor': 'MaterialExpressionVectorParameter_1',
                 'RoughnessFactor': 'MaterialExpressionScalarParameter_0',
                 'MetallicFactor': 'MaterialExpressionScalarParameter_1'}
SOURCE_VALUES = {
    'HD_SkyWater_frost': {
        'base': [0.44999998807907104, 0.699999988079071, 0.8999999761581421, 0.800000011920929],
        'roughness': 0.11999999731779099, 'metallic': 0,
        'emissive': [0.0675000008940696, 0.10500000238418572, 0.1350000017881392]},
    'HD_SkyFoam': {
        'base': [0.8500000238418579, 0.949999988079071, 1, 0.6000000238418579],
        'roughness': 0.30000001192092896, 'metallic': 0,
        'emissive': [0.5100000345706945, 0.5700000154972074, 0.6000000238418579]},
}
VECTORS = ('BaseColorFactor', 'EmissiveFactor')
SCALARS = ('RoughnessFactor', 'MetallicFactor', 'EmissiveStrength')
TOLERANCE = .0001
TLM = 'TLM_SURFACE_PER_PIXEL_LIGHTING'
# The caller supplies an absolute retained directory beside its durable journal.
# Each inspection emits fresh public text witnesses; no default cache survives it.
WITNESS_DIRECTORY = None
INPUT_ROOTS = (
    'BaseColor', 'Metallic', 'Specular', 'Roughness', 'Anisotropy', 'Normal',
    'Tangent', 'EmissiveColor', 'Opacity', 'OpacityMask', 'WorldPositionOffset',
    'Displacement', 'SubsurfaceColor', 'ClearCoat', 'ClearCoatRoughness',
    'AmbientOcclusion', 'Refraction', *(f'CustomizedUVs({i})' for i in range(8)),
    'MaterialAttributes', 'PixelDepthOffset', 'ShadingModelFromMaterialExpression',
    'SurfaceThickness', 'FrontMaterial')


class MaterialContractError(RuntimeError):
    def __init__(self, message, observed):
        super().__init__(message)
        self.observed = observed


def _normal(value):
    return ''.join(char.lower() for char in str(value) if char.isalnum())


def _finite(value):
    return type(value) in (float, int) and math.isfinite(value)


def _source(source):
    allowed = {'name', 'alphaMode', 'doubleSided', 'emissiveFactor', 'pbrMetallicRoughness'}
    if (not isinstance(source, dict) or set(source) - allowed
            or source.get('name') not in SOURCE_VALUES or source.get('alphaMode') != 'BLEND'
            or source.get('doubleSided') is not True):
        raise ValueError('exact Winter4 BLEND/two-sided factor-only source definition required')
    pbr = source.get('pbrMetallicRoughness')
    if not isinstance(pbr, dict) or set(pbr) != {'baseColorFactor', 'roughnessFactor', 'metallicFactor'}:
        raise ValueError('only explicit raw base/roughness/metallic factors are supported')
    values = {'base': pbr['baseColorFactor'], 'roughness': pbr['roughnessFactor'],
              'metallic': pbr['metallicFactor'], 'emissive': source.get('emissiveFactor')}
    for key, wanted in SOURCE_VALUES[source['name']].items():
        actual = values[key]
        a, b = (actual, wanted) if isinstance(wanted, list) else ([actual], [wanted])
        if (not isinstance(a, list) or len(a) != len(b)
                or any(not _finite(number) or abs(number - expected) > 1e-9
                       for number, expected in zip(a, b))):
            raise ValueError('exact finite retained Winter4 source factor differs: ' + key)
    return {'BaseColorFactor': list(values['base']), 'EmissiveFactor': [*values['emissive'], 1.],
            'RoughnessFactor': values['roughness'], 'MetallicFactor': values['metallic'],
            'EmissiveStrength': 1.}


def _source_sha(source):
    return hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _metadata(source):
    return {'codex_owner': 'codex-contest', 'codex_material_policy': POLICY,
            'codex_source_material': source['name'], 'codex_raw_material_sha256': _source_sha(source),
            'codex_material_route': 'raw linear factors; BaseColorFactor RGB/base and A/opacity; EmissiveFactor RGB times Strength1; no gamma/UV/textures'}


def _intent(callback, operation, **details):
    if not callable(callback):
        raise ValueError('caller-provided cooperative durable write-intent generator required')
    pending = callback(operation, policy=POLICY, **details)
    if not isinstance(pending, GeneratorType):
        raise ValueError('intent callback must return a generator; synchronous callbacks are unsupported')
    # The caller owns deadline/queue/resource checks, cooperative ticks and the
    # durable append. Completion must recheck its original guards after yields.
    yield from pending


def _package(path):
    if (not isinstance(path, str) or not path.startswith(ROOT + '/')
            or re.fullmatch(r'/[A-Za-z0-9_/]+', path) is None or path.endswith('/') or '//' in path):
        raise ValueError('exact owned Winter4 namespace package path required')
    return path, path.rsplit('/', 1)[1]


def _owned(obj, unsaved=False):
    path = obj.get_path_name()
    package, dot, name = path.rpartition('.')
    _package(package)
    if not dot or name != obj.get_name():
        raise RuntimeError('unexpected owned object path shape')
    if unsaved:
        content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
        if not content.is_absolute():
            raise RuntimeError('absolute native project content path unavailable; cannot prove unsaved')
        file = content / (package[len('/Game/'):] + '.uasset')
        if file.exists():
            raise RuntimeError('only new unsaved owned objects may be changed: ' + path)
    return path


def _values(material):
    mel = unreal.MaterialEditingLibrary
    vectors, scalars = {}, {}
    for name in mel.get_vector_parameter_names(material):
        text = str(name)
        if text in vectors:
            raise RuntimeError('duplicate native vector parameter name')
        value = mel.get_material_instance_vector_parameter_value(material, name)
        vectors[text] = [float(getattr(value, key)) for key in ('r', 'g', 'b', 'a')]
    for name in mel.get_scalar_parameter_names(material):
        text = str(name)
        if text in scalars:
            raise RuntimeError('duplicate native scalar parameter name')
        scalars[text] = float(mel.get_material_instance_scalar_parameter_value(material, name))
    if set(vectors) != set(VECTORS) or set(scalars) != set(SCALARS):
        raise MaterialContractError('exact unambiguous effective factor parameter names required',
                                    {'vectors': vectors, 'scalars': scalars})
    return {**vectors, **scalars}


def _matches(actual, expected):
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(actual) == len(expected)
                and all(_finite(a) and abs(a - b) <= TOLERANCE for a, b in zip(actual, expected)))
    return _finite(actual) and abs(actual - expected) <= TOLERANCE


def _extra_properties():
    """Crosscheck only visible entries supported by Material.cpp's getter.

    Hidden entries are covered by the full text/default proof, never enum casts.
    Deprecated unsupported native getter cases remain deliberately excluded.
    """
    names = ['MP_NORMAL', 'MP_OPACITY_MASK', 'MP_SPECULAR', 'MP_AMBIENT_OCCLUSION',
             'MP_REFRACTION', 'MP_WORLD_POSITION_OFFSET', 'MP_PIXEL_DEPTH_OFFSET',
             'MP_MATERIAL_ATTRIBUTES', 'MP_ANISOTROPY', 'MP_TANGENT', 'MP_SUBSURFACE_COLOR',
             'MP_CUSTOM_DATA_0', 'MP_CUSTOM_DATA_1', 'MP_SHADING_MODEL', 'MP_FRONT_MATERIAL',
             'MP_SURFACE_THICKNESS', 'MP_DISPLACEMENT']
    result = []
    for name in names:
        prop = getattr(unreal.MaterialProperty, name, None)
        if prop is not None:
            result.append((name, prop))
    return result


def _split_fields(text):
    """Split one ordinary T3D tuple without losing nested constants or quotes."""
    if not text.startswith('(') or not text.endswith(')'):
        raise RuntimeError('unsupported material input tuple shape')
    parts, start, depth, quoted, escaped = [], 1, 0, False, False
    for index, char in enumerate(text[1:-1], 1):
        if escaped:
            escaped = False
        elif quoted and char == '\\':
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth < 0:
                    raise RuntimeError('unbalanced material text tuple')
            elif char == ',' and depth == 0:
                parts.append(text[start:index])
                start = index + 1
    if quoted or escaped or depth:
        raise RuntimeError('unbalanced material text quotes/tuple')
    parts.append(text[start:-1])
    fields = {}
    for part in parts:
        key, separator, value = part.partition('=')
        if not separator or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', key) is None or key in fields:
            raise RuntimeError('ambiguous material text field')
        fields[key] = value
    return fields


def _export_inputs(obj, label):
    """Normal public exporter only; protected reflection and flags are unused."""
    if WITNESS_DIRECTORY is None:
        raise RuntimeError('caller must provide absolute retained WITNESS_DIRECTORY')
    directory = Path(WITNESS_DIRECTORY)
    if not directory.is_absolute():
        raise RuntimeError('absolute retained material witness directory required')
    directory.mkdir(parents=True, exist_ok=True)
    file = directory / (label + '-' + uuid.uuid4().hex + '.t3d')
    if file.exists():
        raise RuntimeError('retained material witness may never be overwritten')
    task = unreal.AssetExportTask()
    for key, value in {
            'object': obj, 'filename': str(file), 'exporter': unreal.ObjectExporterT3D(),
            'automated': True, 'prompt': False, 'replace_identical': False,
            'selected': False, 'use_file_archive': False, 'write_empty_files': False,
            'ignore_object_list': []}.items():
        task.set_editor_property(key, value)
    returned = unreal.Exporter.run_asset_export_task(task)
    errors = [str(error) for error in task.get_editor_property('errors')]
    if returned is not True or errors or not file.is_file():
        raise MaterialContractError('fresh public material text export failed; preserve witness',
                                    {'file': str(file), 'return': returned, 'errors': errors})
    size = file.stat().st_size
    if not 0 < size <= 8 * 1024 * 1024:
        raise RuntimeError('material text witness outside bounded 8 MiB')
    raw = file.read_bytes()
    if len(raw) != size:
        raise RuntimeError('material text witness changed while reading')
    text = raw.decode('utf-8-sig')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cls, name, path = obj.get_class().get_path_name(), obj.get_name(), obj.get_path_name()
    if (cls != '/Script/Engine.MaterialEditorOnlyData'
            or any('"' in value or '\n' in value or '\r' in value for value in (cls, name, path))):
        raise RuntimeError('exact MaterialEditorOnlyData text identity required')
    header = 'Begin Object Class=' + cls + ' Name="' + name + '" ExportPath="' + cls + "'" + path + "'\""
    # EmitBeginObject suppresses Archetype only for a CDO or an object whose
    # actual archetype is a CDO. Exact class/identity and the caller's CDO test
    # establish which case applies. Any custom archetype/inner block is rejected.
    if len(lines) < 2 or lines[0] != header or lines[-1] != 'End Object':
        raise RuntimeError('material text identity/default archetype header differs')
    roots, others = {}, {}
    for line in lines[1:-1]:
        key, separator, value = line.partition('=')
        if not separator or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\([0-9]+\))?', key) is None:
            raise RuntimeError('unsupported material text property or nested object')
        if key in roots or key in others:
            raise RuntimeError('duplicate/ambiguous material text property')
        if key in INPUT_ROOTS:
            fields = _split_fields(value)
            allowed = {'UseConstant', 'Constant', 'ConstantX', 'ConstantY', 'Expression',
                       'OutputIndex', 'InputName', 'Mask', 'MaskR', 'MaskG', 'MaskB', 'MaskA'}
            if set(fields) - allowed:
                raise RuntimeError('unsupported material input fields: ' + key)
            roots[key] = fields
        else:
            if re.search(r'(?:^|[,(])Expression=', value):
                raise RuntimeError('unexpected material Expression root: ' + key)
            others[key] = value
    return roots, others, {'file': str(file), 'bytes': len(raw),
                           'sha256': hashlib.sha256(raw).hexdigest(), 'object': path,
                           'class': cls, 'default_archetype_header_verified': True,
                           'export_return': returned, 'errors': errors}


def _default_inputs(data=None):
    cls = data.get_class() if data is not None else unreal.load_class(None, '/Script/Engine.MaterialEditorOnlyData')
    cdo = unreal.get_default_object(cls)
    if (cdo is None or cdo.get_path_name() != '/Script/Engine.Default__MaterialEditorOnlyData'
            or (data is not None and data == cdo)):
        raise RuntimeError('actual MaterialEditorOnlyData class CDO required')
    roots, others, evidence = _export_inputs(cdo, 'class-default')
    if set(roots) != set(INPUT_ROOTS) or any(value.get('Expression') != 'None' for value in roots.values()):
        raise RuntimeError('all thirty class-default inputs must explicitly serialize Expression=None')
    required = {'Expression', 'OutputIndex', 'InputName', 'Mask', 'MaskR', 'MaskG', 'MaskB', 'MaskA'}
    for name, fields in roots.items():
        if (not required <= set(fields) or fields['InputName'] != '""'
                or any(fields[key] != '0' for key in required - {'Expression', 'InputName'})):
            raise RuntimeError('explicit class-default input fields differ: ' + name)
    collection = _split_fields(others.get('ExpressionCollection', ''))
    if collection != {'Expressions': '', 'EditorComments': '', 'ExpressionExecBegin': 'None', 'ExpressionExecEnd': 'None'}:
        raise RuntimeError('class-default expression collection is not explicitly empty')
    return cdo, roots, others, evidence


def _node_ref(value, node, parent):
    """Bind an exporter reference to one exact already-inspected parent node."""
    if not isinstance(value, str) or len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return False
    cls = node.get_class().get_path_name()
    paths = {node.get_path_name(), parent.get_name() + ':' + node.get_name()}
    return value[1:-1] in {cls + "'" + path + "'" for path in paths}


def _input_proof(parent, intended, nodes):
    data = parent.get_editor_property('EditorOnlyData')
    if data is None or not data.get_path_name().startswith(parent.get_path_name() + ':'):
        raise RuntimeError('owned parent editor-only data identity required')
    cdo, defaults, default_other, default_evidence = _default_inputs(data)
    delta, other, delta_evidence = _export_inputs(data, 'owned-input-delta')
    if data.get_class() != cdo.get_class():
        raise RuntimeError('owned input delta and explicit class defaults differ in class')
    merged = {name: {**defaults[name], **delta.get(name, {})} for name in INPUT_ROOTS}
    for name, fields in merged.items():
        if fields['InputName'] != '""':
            raise RuntimeError('unexpected material input name: ' + name)
        if name in intended:
            if not _node_ref(fields['Expression'], intended[name], parent) or fields.get('UseConstant') != 'False':
                raise RuntimeError('material text intended raw-factor root differs: ' + name)
            # VectorParameter RGB and A are distinct masked outputs (indices
            # zero/four). MEL's output-name getter alone does not verify masks.
            expected = ((0, 1, 1, 1, 1, 0) if name == 'BaseColor' else
                        (4, 1, 0, 0, 0, 1) if name == 'Opacity' else
                        (0, 0, 0, 0, 0, 0))
            keys = ('OutputIndex', 'Mask', 'MaskR', 'MaskG', 'MaskB', 'MaskA')
            if tuple(fields[key] for key in keys) != tuple(str(number) for number in expected):
                raise RuntimeError('material text intended output index/mask differs: ' + name)
        elif fields != defaults[name]:
            raise RuntimeError('material text nonauthored input differs from explicit class defaults: ' + name)
    collection = {**_split_fields(default_other['ExpressionCollection']),
                  **_split_fields(other['ExpressionCollection'])} if 'ExpressionCollection' in other else _split_fields(default_other['ExpressionCollection'])
    if (set(collection) != {'Expressions', 'EditorComments', 'ExpressionExecBegin', 'ExpressionExecEnd'}
            or collection['EditorComments'] != '' or collection['ExpressionExecBegin'] != 'None'
            or collection['ExpressionExecEnd'] != 'None'):
        raise RuntimeError('unexpected editor comments or execution graph')
    entries = collection['Expressions']
    if not entries.startswith('(') or not entries.endswith(')'):
        raise RuntimeError('exact known expression collection references required')
    refs = entries[1:-1].split(',')
    if (len(refs) != len(nodes) or len(set(refs)) != len(nodes)
            or any(sum(_node_ref(ref, node, parent) for node in nodes) != 1 for ref in refs)
            or any(sum(_node_ref(ref, node, parent) for ref in refs) != 1 for node in nodes)):
        raise RuntimeError('serialized expression collection does not match exact known nodes')
    mel = unreal.MaterialEditingLibrary
    properties = _extra_properties()
    for name, prop in properties:
        if mel.get_material_property_input_node(parent, prop) is not None:
            raise RuntimeError('unexpected extra material property graph: ' + name)
    active = parent.get_editor_property('NumCustomizedUVs')
    if type(active) is not int or active != 0:
        raise RuntimeError('factor-only parent requires zero active customized UVs')
    return {'disconnected_property_roots': [name for name, prop in properties],
            'active_customized_uvs': active, 'all_eight_customized_uv_compile_paths_inactive': True,
            'raw_customized_uv_connections_inspected': True,
            'root_count': len(merged), 'disconnected_root_count': len(merged) - len(intended),
            'input_expression_references': {name: fields['Expression'] for name, fields in merged.items()},
            'default_inputs': default_evidence, 'owned_input_delta': delta_evidence,
            'merge_contract': 'Fresh explicit thirty-root class CDO plus exact CDO-archetyped owned EOD delta; no absent-field null guess.',
            'raw_uv_field_access': 'normal public T3D serialization; no protected getter/flags/enum cast',
            'limits': 'Text/default graph proof and visible MEL crosschecks; shader execution and native appearance remain separate.'}


def _disconnected_properties(parent, named, multiply, nodes):
    return _input_proof(parent, {
        'BaseColor': named['BaseColorFactor'], 'Opacity': named['BaseColorFactor'],
        'Roughness': named['RoughnessFactor'], 'Metallic': named['MetallicFactor'],
        'EmissiveColor': multiply}, nodes)


def _parent_graph(parent, source):
    if not isinstance(parent, unreal.Material):
        raise RuntimeError('explicit owned base Material required')
    path = _owned(parent)
    wanted = _source(source)
    mel = unreal.MaterialEditingLibrary
    mode = getattr(unreal.TranslucencyLightingMode, TLM, None)
    if mode is None:
        raise RuntimeError('installed surface-per-pixel translucency lighting enum unavailable')
    flags = {'material_domain': unreal.MaterialDomain.MD_SURFACE,
             'shading_model': unreal.MaterialShadingModel.MSM_DEFAULT_LIT,
             'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT, 'two_sided': True,
             'use_material_attributes': False, 'translucency_lighting_mode': mode,
             'NumCustomizedUVs': 0}
    observed_flags = {key: parent.get_editor_property(key) for key in flags}
    if observed_flags != flags:
        raise MaterialContractError('owned parent flags differ; no enum widening or shared repair',
                                    {key: str(value) for key, value in observed_flags.items()})
    nodes = list(mel.get_material_expressions(parent))
    vectors = [node for node in nodes if node.get_class().get_name() == 'MaterialExpressionVectorParameter']
    scalars = [node for node in nodes if node.get_class().get_name() == 'MaterialExpressionScalarParameter']
    multiply = [node for node in nodes if node.get_class().get_name() == 'MaterialExpressionMultiply']
    if len(nodes) != 6 or len(vectors) != 2 or len(scalars) != 3 or len(multiply) != 1:
        raise MaterialContractError('exact six-node factor-only parent graph required',
                                    {'nodes': [{'path': node.get_path_name(), 'class': node.get_class().get_name()} for node in nodes]})
    named = {str(node.get_editor_property('parameter_name')): node for node in vectors + scalars}
    if len(named) != 5 or set(named) != set(wanted):
        raise RuntimeError('exact distinct source parameter graph nodes required')
    defaults = {}
    for name, node in named.items():
        if bool(node.get_editor_property('use_custom_primitive_data')):
            raise RuntimeError('custom primitive parameter overrides are outside factor-only policy')
        value = node.get_editor_property('default_value')
        defaults[name] = ([float(getattr(value, key)) for key in ('r', 'g', 'b', 'a')]
                          if name in VECTORS else float(value))
        if not _matches(defaults[name], wanted[name]):
            raise MaterialContractError('raw source parent default differs: ' + name, defaults)
    mul = multiply[0]
    roots = ((unreal.MaterialProperty.MP_BASE_COLOR, named['BaseColorFactor'], 'RGB'),
             (unreal.MaterialProperty.MP_OPACITY, named['BaseColorFactor'], 'A'),
             (unreal.MaterialProperty.MP_ROUGHNESS, named['RoughnessFactor'], ''),
             (unreal.MaterialProperty.MP_METALLIC, named['MetallicFactor'], ''),
             (unreal.MaterialProperty.MP_EMISSIVE_COLOR, mul, ''))
    links = []
    for prop, node, output in roots:
        actual_node = mel.get_material_property_input_node(parent, prop)
        actual_output = mel.get_material_property_input_node_output_name(parent, prop)
        if actual_node != node or not isinstance(actual_output, str) or actual_output != output:
            raise RuntimeError('actual connected parent property node/output differs: ' + str(prop))
        links.append({'property': str(prop), 'node': node.get_path_name(), 'output': actual_output})
    disconnected = _disconnected_properties(parent, named, mul, nodes)
    input_names = [str(name) for name in mel.get_material_expression_input_names(mul)]
    inputs = list(mel.get_inputs_for_material_expression(parent, mul))
    if input_names != ['A', 'B'] or inputs != [named['EmissiveFactor'], named['EmissiveStrength']]:
        raise RuntimeError('exact EmissiveFactor/Strength Multiply inputs required')
    for node, expected in ((named['EmissiveFactor'], 'RGB'), (named['EmissiveStrength'], '')):
        output = mel.get_input_node_output_name_for_material_expression(mul, node)
        # Actual installed UE5.8 palette production established str-or-None.
        if not isinstance(output, str) or output != expected:
            raise RuntimeError('unsupported or differing Multiply input output-name readback')
    metadata = {key: unreal.EditorAssetLibrary.get_metadata_tag(parent, key) for key in _metadata(source)}
    if metadata != _metadata(source):
        raise RuntimeError('owned raw material policy/source metadata differs')
    return {'parent': path, 'policy': POLICY, 'source_material': source['name'],
            'source_definition_sha256': _source_sha(source), 'node_count': len(nodes),
            'flags': {key: str(value) for key, value in observed_flags.items()},
            'defaults': defaults, 'property_links': links,
            'multiply_inputs': [node.get_path_name() for node in inputs],
            'multiply_input_outputs': ['RGB', ''], 'metadata': metadata,
            'disconnected_properties': disconnected,
            'graph_verified': True, 'compile_state_rechecked': False, 'issues': []}


def inspect(mic, expected_parent, source, miri_scope=None):
    """Read only; require actual graph, effective values, mode and two-sided."""
    wanted = _source(source)
    if not isinstance(mic, unreal.MaterialInstanceConstant):
        raise RuntimeError('exact owned new MaterialInstanceConstant required')
    path = _owned(mic)
    if not _normal(mic.get_name()).endswith(_normal(source['name'])):
        raise RuntimeError('source-named owned material instance required')
    if isinstance(expected_parent, str):
        package = expected_parent.split('.')[0]
        package, name = _package(package)
        expected_parent = unreal.find_object(None, package + '.' + name)
        if expected_parent is None and unreal.EditorAssetLibrary.does_asset_exist(package):
            expected_parent = unreal.EditorAssetLibrary.load_asset(package)
    graph = _parent_graph(expected_parent, source)
    actual_parent = mic.get_editor_property('parent')
    if actual_parent != expected_parent or mic.get_base_material() != expected_parent:
        raise RuntimeError('exact immediate and effective owned parent required')
    overrides = mic.get_editor_property('base_property_overrides')
    observed = {key: overrides.get_editor_property(key) for key in
                ('override_blend_mode', 'blend_mode', 'override_two_sided', 'two_sided')}
    expected = {'override_blend_mode': True, 'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                'override_two_sided': True, 'two_sided': True}
    if observed != expected or mic.get_blend_mode() != unreal.BlendMode.BLEND_TRANSLUCENT:
        raise MaterialContractError('exact effective translucent/two-sided instance overrides required',
                                    {key: str(value) for key, value in observed.items()})
    shading_override = bool(overrides.get_editor_property('override_shading_model'))
    shading_model = overrides.get_editor_property('shading_model')
    if shading_override and shading_model != unreal.MaterialShadingModel.MSM_DEFAULT_LIT:
        raise RuntimeError('unexpected instance shading-model override; no automatic repair')
    physical = {'chain': [{'path': path, 'class': mic.get_class().get_name()},
                          {'path': expected_parent.get_path_name(), 'class': expected_parent.get_class().get_name()}],
                'two_sided': True, 'blend_mode': str(mic.get_blend_mode()), 'errors': [],
                'override_shading_model': shading_override, 'instance_shading_model': str(shading_model)}
    if miri_scope is not None:
        if not isinstance(miri_scope, dict) or not callable(miri_scope.get('_physical')):
            raise RuntimeError('provided read-only Miri physical inspector unavailable')
        physical = miri_scope['_physical'](mic)
        if (not isinstance(physical, dict) or physical.get('errors') != []
                or physical.get('two_sided') is not True
                or physical.get('blend_mode') != str(unreal.BlendMode.BLEND_TRANSLUCENT)):
            raise MaterialContractError('read-only Miri effective physical crosscheck differs', physical)
    actual = _values(mic)
    if any(not _matches(actual[name], number) for name, number in wanted.items()):
        raise MaterialContractError('effective raw RGBA/PBR/emission/strength differs; no factor repair', actual)
    return {'path': path, 'class': mic.get_class().get_name(), 'policy': POLICY,
            'source_material': source['name'], 'expected_parent': expected_parent.get_path_name(),
            'effective_parameters': actual, 'physical': physical, 'graph': graph,
            'raw_alpha': actual['BaseColorFactor'][3], 'issues': [], 'mutations': 0,
            'limits': 'Source graph/factor/mode readback only; native appearance, sorting, collision/navigation/runtime and saved bytes remain separate.'}


def _new_parameter(parent, path, parameter, index, wanted, intent):
    """Cooperative creation of one new parameter; never reuses a partial node."""
    mel = unreal.MaterialEditingLibrary
    cls = unreal.MaterialExpressionVectorParameter if parameter in VECTORS else unreal.MaterialExpressionScalarParameter
    yield from _intent(intent, 'create_owned_parameter_node', path=path, parameter=parameter, class_name=cls.__name__)
    node = mel.create_material_expression(parent, cls, -600, index * 140)
    if node is None:
        raise RuntimeError('owned parameter node creation returned None')
    for key, value in (('parameter_name', parameter), ('use_custom_primitive_data', False),
                       ('default_value', unreal.LinearColor(*wanted[parameter]) if parameter in VECTORS else wanted[parameter])):
        yield from _intent(intent, 'set_owned_parameter_property', node=node.get_path_name(), property=key, value=str(value))
        node.set_editor_property(key, value)
    return node


def _finish_parent(parent, source, nodes, intent):
    """Cooperative common unattempted tail after exactly five named parameters."""
    path = _owned(parent, unsaved=True).split('.')[0]
    mel = unreal.MaterialEditingLibrary
    yield from _intent(intent, 'create_owned_emissive_multiply', path=path)
    multiply = mel.create_material_expression(parent, unreal.MaterialExpressionMultiply, -250, 200)
    if multiply is None:
        raise RuntimeError('owned Multiply creation returned None')
    for parameter, output, target in (('EmissiveFactor', 'RGB', 'A'), ('EmissiveStrength', '', 'B')):
        yield from _intent(intent, 'connect_owned_emissive_input', path=path, parameter=parameter, output=output, input=target)
        if mel.connect_material_expressions(nodes[parameter], output, multiply, target) is not True:
            raise RuntimeError('owned emissive Multiply connection not confirmed')
    for node, output, prop in ((nodes['BaseColorFactor'], 'RGB', unreal.MaterialProperty.MP_BASE_COLOR),
            (nodes['BaseColorFactor'], 'A', unreal.MaterialProperty.MP_OPACITY),
            (nodes['RoughnessFactor'], '', unreal.MaterialProperty.MP_ROUGHNESS),
            (nodes['MetallicFactor'], '', unreal.MaterialProperty.MP_METALLIC),
            (multiply, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
        yield from _intent(intent, 'connect_owned_material_property', node=node.get_path_name(), output=output, property=str(prop))
        if mel.connect_material_property(node, output, prop) is not True:
            raise RuntimeError('owned material property connection not confirmed')
    for key, value in _metadata(source).items():
        yield from _intent(intent, 'tag_owned_parent_source', path=path, key=key, value=value)
        unreal.EditorAssetLibrary.set_metadata_tag(parent, key, value)
    graph = _parent_graph(parent, source)
    yield from _intent(intent, 'compile_owned_factor_alpha_parent', path=path)
    started = time.perf_counter()
    returned = mel.recompile_material(parent)
    if not isinstance(returned, (list, tuple, unreal.Array)):
        raise MaterialContractError('unsupported owned parent compile return shape; preserve partial parent',
                                    {'return_type': type(returned).__name__, 'return_value': str(returned)})
    errors = [str(error) for error in returned]
    report = {'parent': parent.get_path_name(), 'policy': POLICY, 'source_material': source['name'],
              'graph': graph, 'compile_errors': errors, 'compile_call_s': round(time.perf_counter() - started, 6),
              'saved': False, 'native_appearance_validated': False,
              'compile_limit': 'Empty errors mean no reported errors; this API can also return empty without a material resource. Shader/native appearance acceptance is separate.'}
    if errors:
        raise MaterialContractError('owned material compile returned errors; no retry or save', report)
    report['graph'] = _parent_graph(parent, source)
    return parent, report


def build_parent(path, source, intent):
    """Generator: create/compile a fresh parent; yield-from returns it UNSAVED."""
    wanted = _source(source)
    path, name = _package(path)
    if not callable(intent):
        raise ValueError('durable cooperative intent generator required before any mutation')
    if (unreal.find_object(None, path + '.' + name) is not None
            or unreal.EditorAssetLibrary.does_asset_exist(path)):
        raise RuntimeError('fresh owned parent required; preserve existing object without reuse/repair')
    mode = getattr(unreal.TranslucencyLightingMode, TLM, None)
    if mode is None:
        raise RuntimeError('installed surface-per-pixel translucency lighting enum unavailable')
    _default_inputs()  # Fresh explicit defaults/export support before first mutation.
    yield from _intent(intent, 'create_owned_factor_alpha_parent', path=path, source_material=source['name'])
    parent = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, path.rsplit('/', 1)[0], unreal.Material, unreal.MaterialFactoryNew())
    if not isinstance(parent, unreal.Material) or _owned(parent, unsaved=True) != path + '.' + name:
        raise RuntimeError('fresh Material creation did not return exact owned object')
    flags = {'material_domain': unreal.MaterialDomain.MD_SURFACE,
             'shading_model': unreal.MaterialShadingModel.MSM_DEFAULT_LIT,
             'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT, 'two_sided': True,
             'use_material_attributes': False, 'translucency_lighting_mode': mode,
             'NumCustomizedUVs': 0}
    for key, value in flags.items():
        yield from _intent(intent, 'set_owned_parent_property', path=path, property=key, value=str(value))
        parent.set_editor_property(key, value)
    nodes = {}
    for index, parameter in enumerate((*VECTORS, *SCALARS)):
        nodes[parameter] = yield from _new_parameter(parent, path, parameter, index, wanted, intent)
    return (yield from _finish_parent(parent, source, nodes, intent))


def inspect_partial_parent(parent, source, objects):
    """Read-only closed R4 boundary: one Water parent plus four unchanged imports.

    ``objects`` must be the caller's fresh complete native namespace inventory,
    not a reconstructed journal. Caller separately preserves geometry/baseline.
    This function never treats the R4 intent record as proof of current state.
    """
    wanted = _source(source)
    if source['name'] != 'HD_SkyWater_frost' or not isinstance(parent, unreal.Material):
        raise RuntimeError('only exact known R4 Water partial parent is resumable')
    path = _owned(parent, unsaved=True)
    if path != PARTIAL_WATER + '.' + PARTIAL_WATER.rsplit('/', 1)[1]:
        raise RuntimeError('exact canonical R4 partial Water parent required')
    imported = ROOT + '/Winter4_Canal_Stream1_Core_R1/'
    expected = {
        imported + 'Materials/HD_SkyFoam.HD_SkyFoam': 'MaterialInstanceConstant',
        imported + 'Materials/HD_SkyWater_frost.HD_SkyWater_frost': 'MaterialInstanceConstant',
        imported + 'StaticMeshes/Octet_Winter_4_Canal_Stream1.Octet_Winter_4_Canal_Stream1': 'StaticMesh',
        imported + 'StaticMeshes/Octet_Winter_4__al_Stream1_Core.Octet_Winter_4__al_Stream1_Core': 'StaticMesh',
        path: 'Material'}
    if not isinstance(objects, dict) or set(objects) != set(expected) or objects[path] != parent:
        raise RuntimeError('fresh exact five-object partial inventory required; no extra/Foam parent')
    for key, obj in objects.items():
        if obj is None or obj.get_class().get_name() != expected[key] or _owned(obj, unsaved=True) != key:
            raise RuntimeError('partial inventory identity/class/unsaved state differs')
    mode = getattr(unreal.TranslucencyLightingMode, TLM, None)
    if mode is None:
        raise RuntimeError('installed surface-per-pixel translucency lighting enum unavailable')
    flags = {'material_domain': unreal.MaterialDomain.MD_SURFACE,
             'shading_model': unreal.MaterialShadingModel.MSM_DEFAULT_LIT,
             'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT, 'two_sided': True,
             'use_material_attributes': False, 'translucency_lighting_mode': mode,
             'NumCustomizedUVs': 0}
    actual_flags = {key: parent.get_editor_property(key) for key in flags}
    if actual_flags != flags:
        raise RuntimeError('exact seven completed R4 parent flags differ')
    mel = unreal.MaterialEditingLibrary
    nodes = list(mel.get_material_expressions(parent))
    named = {}
    for node in nodes:
        cls = node.get_class().get_name()
        if cls not in ('MaterialExpressionVectorParameter', 'MaterialExpressionScalarParameter'):
            raise RuntimeError('R4 partial permits only the four original parameter nodes')
        name = str(node.get_editor_property('parameter_name'))
        if name not in PARTIAL_NODES or name in named or node.get_path_name() != path + ':' + PARTIAL_NODES[name]:
            raise RuntimeError('exact R4 parameter node identity/name differs')
        expected_class = 'MaterialExpressionVectorParameter' if name in VECTORS else 'MaterialExpressionScalarParameter'
        if cls != expected_class or node.get_editor_property('use_custom_primitive_data') is not False:
            raise RuntimeError('partial parameter class/CPD state differs')
        if list(mel.get_material_expression_input_names(node)) or list(mel.get_inputs_for_material_expression(parent, node)):
            raise RuntimeError('unexpected partial parameter input edges')
        named[name] = node
    if len(nodes) != 4 or set(named) != set(PARTIAL_NODES):
        raise RuntimeError('exact original two-vector/two-scalar R4 partial required')
    defaults = {}
    for name, node in named.items():
        value = node.get_editor_property('default_value')
        defaults[name] = ([float(getattr(value, key)) for key in ('r', 'g', 'b', 'a')]
                          if name in VECTORS else float(value))
        if not _matches(defaults[name], wanted[name]) or (name == 'MetallicFactor' and defaults[name] != 0.):
            raise RuntimeError('completed R4 raw defaults or untouched Metallic zero differ')
    metadata = {str(key): str(value) for key, value in unreal.EditorAssetLibrary.get_metadata_tag_values(parent).items()}
    if metadata:
        raise RuntimeError('R4 partial parent must have no source/policy metadata yet')
    imports = []
    for key, obj in objects.items():
        if expected[key] != 'MaterialInstanceConstant':
            continue
        immediate, base = obj.get_editor_property('parent'), obj.get_base_material()
        if (immediate is None or base is None
                or immediate.get_path_name() != '/InterchangeAssets/gltf/MaterialInstances/MI_Default_Blend_DS.MI_Default_Blend_DS'
                or base.get_path_name() != '/InterchangeAssets/gltf/M_Default.M_Default'):
            raise RuntimeError('R4 imported MIC binding changed or already bound to owned parent')
        vector_names = [str(name) for name in mel.get_vector_parameter_names(obj)]
        scalar_names = [str(name) for name in mel.get_scalar_parameter_names(obj)]
        if any(vector_names.count(name) != 1 for name in VECTORS) or any(scalar_names.count(name) != 1 for name in SCALARS):
            raise RuntimeError('unambiguous original imported raw factor names required')
        source_values = SOURCE_VALUES[obj.get_name()]
        raw = {}
        for name in VECTORS:
            value = mel.get_material_instance_vector_parameter_value(obj, name)
            raw[name] = [float(getattr(value, channel)) for channel in ('r', 'g', 'b', 'a')]
        for name in SCALARS:
            raw[name] = float(mel.get_material_instance_scalar_parameter_value(obj, name))
        raw_expected = {'BaseColorFactor': source_values['base'], 'EmissiveFactor': [*source_values['emissive'], 1.],
                        'RoughnessFactor': source_values['roughness'], 'MetallicFactor': source_values['metallic'],
                        'EmissiveStrength': 1.}
        if any(not _matches(raw[name], number) for name, number in raw_expected.items()):
            raise RuntimeError('original imported raw factors changed before partial resume')
        imports.append({'path': key, 'parent': immediate.get_path_name(), 'base': base.get_path_name(),
                        'raw_factors': raw, 'parameter_names': {'vector': vector_names, 'scalar': scalar_names}})
    proof = _input_proof(parent, {}, nodes)
    return {'stage': 'exact_r4_water_four_node_partial_verified', 'parent': path, 'policy': POLICY,
            'source_material': source['name'], 'flags': {key: str(value) for key, value in actual_flags.items()},
            'nodes': {name: node.get_path_name() for name, node in named.items()}, 'defaults': defaults,
            'input_proof': proof, 'parent_metadata': metadata, 'unchanged_imports': imports,
            'assets': [{'path': key, 'class': expected[key]} for key in sorted(expected)],
            'saved': False, 'bindings_completed': 0, 'mutations': 0, 'issues': [],
            'limits': 'Exact owned partial graph/raw-binding proof; caller separately guards baseline, geometry and namespace inventory freshness.'}


def resume_parent(parent, source, intent, objects):
    """Generator: complete ONLY the unattempted suffix of the exact R4 partial."""
    if not callable(intent):
        raise ValueError('durable cooperative intent generator required')
    partial = inspect_partial_parent(parent, source, objects)
    wanted = _source(source)
    nodes = {str(node.get_editor_property('parameter_name')): node
             for node in unreal.MaterialEditingLibrary.get_material_expressions(parent)}
    metallic = nodes['MetallicFactor']
    # These are precisely the two unattempted writes after R4's final durable
    # MetallicFactor parameter_name. No earlier property/name/create is replayed.
    for key, value in (('use_custom_primitive_data', False), ('default_value', wanted['MetallicFactor'])):
        yield from _intent(intent, 'set_owned_parameter_property', node=metallic.get_path_name(),
                           property=key, value=str(value), resume_boundary='R4_after_MetallicFactor_name')
        metallic.set_editor_property(key, value)
    nodes['EmissiveStrength'] = yield from _new_parameter(parent, PARTIAL_WATER, 'EmissiveStrength', 4, wanted, intent)
    parent, report = yield from _finish_parent(parent, source, nodes, intent)
    report.update(resumed_from=partial, completed_boundary='R4_after_MetallicFactor_name',
                  earlier_construction_replayed=False)
    return parent, report


def bind_instance(mic, parent, source, intent):
    """Generator: reparent a new unsaved MIC; yield-from returns inspect report."""
    wanted = _source(source)
    if not callable(intent) or not isinstance(mic, unreal.MaterialInstanceConstant):
        raise ValueError('new owned MIC and durable intent callback required')
    path = _owned(mic, unsaved=True)
    _owned(parent, unsaved=True)
    if not _normal(mic.get_name()).endswith(_normal(source['name'])):
        raise RuntimeError('exact new source-named MIC required')
    _parent_graph(parent, source)
    original = mic.get_editor_property('parent')
    original_path = original.get_path_name() if original else None
    mel = unreal.MaterialEditingLibrary
    yield from _intent(intent, 'bind_new_unsaved_mic_owned_parent', instance=path, original_parent=original_path,
            owned_parent=parent.get_path_name(), source_material=source['name'])
    mel.set_material_instance_parent(mic, parent)
    if mic.get_editor_property('parent') != parent:
        raise RuntimeError('owned instance parent setter not confirmed')
    yield from _intent(intent, 'set_new_unsaved_mic_translucent_two_sided_overrides', instance=path,
            blend_mode=str(unreal.BlendMode.BLEND_TRANSLUCENT), two_sided=True)
    overrides = mic.get_editor_property('base_property_overrides')
    for key, value in (('override_blend_mode', True), ('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT),
                       ('override_two_sided', True), ('two_sided', True)):
        overrides.set_editor_property(key, value)
    mic.set_editor_property('base_property_overrides', overrides)
    setter_returns = {}
    for parameter in (*VECTORS, *SCALARS):
        yield from _intent(intent, 'set_new_unsaved_mic_raw_source_parameter', instance=path, parameter=parameter,
                value=wanted[parameter])
        setter_returns[parameter] = bool(
            mel.set_material_instance_vector_parameter_value(mic, parameter, unreal.LinearColor(*wanted[parameter]))
            if parameter in VECTORS else mel.set_material_instance_scalar_parameter_value(mic, parameter, wanted[parameter]))
        # Installed setters update the instance but return unchanged False.
        # No retry: exact effective readback below decides acceptance.
    observed = inspect(mic, parent, source)
    observed.update(original_parent_before_binding=original_path, setter_return_values=setter_returns,
                    setter_return_limit='Installed setter False is not evidence of zero mutation; no write was retried.',
                    saved=False, mutations='journalled owned parent/overrides/source parameters only')
    return observed
