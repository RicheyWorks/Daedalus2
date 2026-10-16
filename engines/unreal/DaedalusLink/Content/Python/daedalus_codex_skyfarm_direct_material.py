# SPDX-License-Identifier: MIT
"""Read-only closed qualifier for the observed greenhouse direct Materials.

The caller supplies the pinned Canal helper's private graph scope with an
absolute WITNESS_DIRECTORY. This module has no import-time native effects and
does not import, create, compile, repair, bind or save any Unreal object.
"""
import math

import unreal

ROOT = '/Game/Daedalus/Art/SkyFarm/GreenhouseBayR1/'
FUNCTION = '/InterchangeAssets/gltf/MaterialBodies/MF_Default_Body.MF_Default_Body'
OUTPUTS = {'BaseColor': (0, 'BaseColor'), 'Metallic': (1, 'Metallic'),
           'Specular': (2, 'Specular'), 'Roughness': (3, 'Roughness'),
           'EmissiveColor': (5, 'EmissiveColor'), 'Normal': (8, 'Normal'),
           'AmbientOcclusion': (10, 'Occlusion')}


def _close(actual, expected):
    return (len(actual) == len(expected) and all(math.isfinite(float(a))
            and abs(float(a)-float(b)) <= .0001 for a, b in zip(actual, expected)))


def _path(obj):
    return obj.get_path_name() if obj is not None else None


def qualify(mat, source, graph):
    """Return a substantive readback or raise before any receiving mutation.

    The exact factory graph has four owned nodes, seven named output roots and
    only three connected function inputs. Omitted alpha/emission inputs are
    accepted only after reading the actual built-in function's default values
    and proving that its preview inputs are disconnected.
    """
    mel = unreal.MaterialEditingLibrary
    if (mat.get_class().get_path_name() != '/Script/Engine.Material'
            or not mat.get_path_name().startswith(ROOT)
            or mat.get_name() != source['name']
            or source.get('alphaMode', 'OPAQUE') != 'OPAQUE'
            or source.get('doubleSided') is not True or source.get('extensions')
            or any('Texture' in key for key in source)
            or any('Texture' in key for key in source['pbrMetallicRoughness'])):
        raise RuntimeError('exact owned opaque factor-only raw material required')
    pbr = source['pbrMetallicRoughness']
    rgba = pbr['baseColorFactor']
    if (not _close(rgba[3:], [1.])
            or not _close(source.get('emissiveFactor', [0., 0., 0.]), [0., 0., 0.])
            or mat.get_editor_property('blend_mode') != unreal.BlendMode.BLEND_OPAQUE
            or mat.get_editor_property('two_sided') is not True
            or mat.get_editor_property('NumCustomizedUVs') != 0):
        raise RuntimeError('raw opaque/double-sided/zero-emission/UV contract differs')
    nodes = list(mel.get_material_expressions(mat))
    classes = [node.get_class().get_path_name() for node in nodes]
    prefix = '/Script/Engine.MaterialExpression'
    if (len(nodes) != 4 or len({_path(n) for n in nodes}) != 4
            or sorted(classes) != sorted([prefix+'MaterialFunctionCall',
                prefix+'Constant3Vector', prefix+'Constant', prefix+'Constant'])
            or any(not node.get_path_name().startswith(mat.get_path_name()+':') for node in nodes)):
        raise RuntimeError('exact four owned factory expressions required')
    call = next(node for node in nodes if node.get_class().get_path_name() == prefix+'MaterialFunctionCall')
    function = call.get_editor_property('material_function')
    if _path(function) != FUNCTION:
        raise RuntimeError('observed default glTF body function differs')
    names = [str(name) for name in mel.get_material_expression_input_names(call)]
    inputs = list(mel.get_inputs_for_material_expression(mat, call))
    if len(names) != 89 or len(inputs) != 89 or len(set(names)) != 89:
        raise RuntimeError('exact 89 unique glTF function inputs required')
    connected = {name: node for name, node in zip(names, inputs) if node is not None}
    if set(connected) != {'BaseColorFactor_RGB', 'MetallicFactor', 'RoughnessFactor'}:
        raise RuntimeError('only three authored raw-factor function inputs may connect')
    rgb = connected['BaseColorFactor_RGB']
    color = rgb.get_editor_property('constant') if rgb.get_class().get_path_name() == prefix+'Constant3Vector' else None
    if color is None or not _close([color.r, color.g, color.b], rgba[:3]):
        raise RuntimeError('direct linear BaseColor RGB constant differs')
    for name, expected in (('MetallicFactor', pbr['metallicFactor']),
                           ('RoughnessFactor', pbr['roughnessFactor'])):
        node = connected[name]
        if node.get_class().get_path_name() != prefix+'Constant' or not _close([node.get_editor_property('r')], [expected]):
            raise RuntimeError('direct scalar constant differs: '+name)
    if {_path(call)} | {_path(node) for node in connected.values()} != {_path(node) for node in nodes}:
        raise RuntimeError('every factory node must be uniquely used')
    omitted = {}
    function_inputs = [node for node in mel.get_material_function_expressions(function)
                       if node.get_class().get_path_name() == prefix+'FunctionInput']
    for name, wanted in (('BaseColorFactor_A', [1.]),
                          ('EmissiveFactor', [0., 0., 0.]), ('EmissiveStrength', [1.])):
        found = [node for node in function_inputs if str(node.get_editor_property('input_name')) == name]
        if len(found) != 1:
            raise RuntimeError('unambiguous actual function default required: '+name)
        node = found[0]
        preview = node.get_editor_property('preview_value')
        values = [float(preview.get_editor_property(key)) for key in ('X', 'Y', 'Z', 'W')]
        if len(values) != 4 or any(not math.isfinite(number) for number in values):
            raise RuntimeError('actual finite four-component function preview required')
        preview_nodes = list(mel.get_inputs_for_material_expression(mat, node))
        if (node.get_editor_property('use_preview_value_as_default') is not True
                or len(preview_nodes) != 1 or any(item is not None for item in preview_nodes)
                or not _close(values[:len(wanted)], wanted)):
            raise RuntimeError('actual disconnected preview default differs: '+name)
        omitted[name] = {'node': _path(node), 'preview_value': values,
                         'use_preview_value_as_default': True, 'preview_connected': False}
    data = mat.get_editor_property('EditorOnlyData')
    if data is None or not data.get_path_name().startswith(mat.get_path_name()+':'):
        raise RuntimeError('owned material editor data required')
    cdo, defaults, default_other, default_evidence = graph['_default_inputs'](data)
    delta, other, evidence = graph['_export_inputs'](data, mat.get_name()+'-direct-inputs')
    if data.get_class() != cdo.get_class():
        raise RuntimeError('material inputs and explicit CDO class differ')
    merged = {name: {**fields, **delta.get(name, {})} for name, fields in defaults.items()}
    for name, fields in merged.items():
        if name in OUTPUTS:
            index, output_name = OUTPUTS[name]
            expected = dict(defaults[name]); expected['OutputIndex'] = str(index)
            expected['Expression'] = fields['Expression']
            if fields != expected or not graph['_node_ref'](fields['Expression'], call, mat):
                raise RuntimeError('exact factory output root/index/default fields differ: '+name)
            prop_name = {'BaseColor':'MP_BASE_COLOR','Metallic':'MP_METALLIC','Specular':'MP_SPECULAR',
                'Roughness':'MP_ROUGHNESS','EmissiveColor':'MP_EMISSIVE_COLOR','Normal':'MP_NORMAL',
                'AmbientOcclusion':'MP_AMBIENT_OCCLUSION'}[name]
            prop = getattr(unreal.MaterialProperty, prop_name, None)
            if (prop is None or mel.get_material_property_input_node(mat, prop) != call
                    or str(mel.get_material_property_input_node_output_name(mat, prop)) != output_name):
                raise RuntimeError('public factory output name/node crosscheck differs: '+name)
        elif fields != defaults[name]:
            raise RuntimeError('nonauthored input differs from explicit CDO: '+name)
    split = graph['_split_fields']
    collection = {**split(default_other['ExpressionCollection']),
                  **split(other['ExpressionCollection'])} if 'ExpressionCollection' in other else split(default_other['ExpressionCollection'])
    if (set(collection) != {'Expressions','EditorComments','ExpressionExecBegin','ExpressionExecEnd'}
            or collection['EditorComments'] != '' or collection['ExpressionExecBegin'] != 'None'
            or collection['ExpressionExecEnd'] != 'None'):
        raise RuntimeError('unexpected material execution/comment collection')
    refs = collection['Expressions']
    if not refs.startswith('(') or not refs.endswith(')'):
        raise RuntimeError('exact four serialized expression references required')
    refs = refs[1:-1].split(',')
    if (len(refs) != 4 or len(set(refs)) != 4
            or any(sum(graph['_node_ref'](ref, node, mat) for node in nodes) != 1 for ref in refs)
            or any(sum(graph['_node_ref'](ref, node, mat) for ref in refs) != 1 for node in nodes)):
        raise RuntimeError('exact public/T3D expression collection differs')
    return {'path':mat.get_path_name(),'class':'Material','source_name':source['name'],
        'readback_errors':[],'raw_linear_factors':dict(baseColorFactor=rgba,
            metallicFactor=pbr['metallicFactor'],roughnessFactor=pbr['roughnessFactor'],
            emissiveFactor=[0.,0.,0.],emissiveStrength=1.),
        'physical':{'opaque':True,'two_sided':True,'errors':[]},
        'graph':{'material_function':FUNCTION,'node_count':4,'function_input_count':89,
            'connected_inputs':{name:_path(node) for name,node in connected.items()},
            'omitted_defaults':omitted,'root_count':len(merged),'connected_root_count':7,
            'outputs':{name:list(value) for name,value in OUTPUTS.items()},
            'default_evidence':default_evidence,'owned_input_evidence':evidence,
            'all_other_roots_equal_explicit_cdo':True,'graph_verified':True},
        'native_mutations':0,'limits':'Factory graph and raw factors qualified; shader execution/appearance/gameplay remain separate.'}
