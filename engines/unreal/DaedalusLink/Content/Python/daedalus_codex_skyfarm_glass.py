# SPDX-License-Identifier: MIT
"""Closed greenhouse transmission receiving contract; no native effects.

This pure module validates decoded source and a later retained public-API graph
observation. It neither collects that observation nor grants runtime admission.
It has no Unreal, transport, import, mutation, compile, save or placement entry.
"""
from copy import deepcopy
import math
import re

ROOT='/Game/Daedalus/Art/SkyFarm/GreenhouseBayR1'
MATERIAL=ROOT+'/SFG_R1_glass.SFG_R1_glass'
MESH=ROOT+'/SFG_R1_glass_glass.SFG_R1_glass_glass'
FUNCTION='/InterchangeAssets/gltf/MaterialBodies/MF_Transmission_Body.MF_Transmission_Body'
FUNCTION_BODY={'bytes':205269,'sha256':'067ea26cba3218c168783b562d5304e3d6fe318bdef676226b4d5d1fdf17d82e'}
RAW={'alphaMode':'BLEND','doubleSided':True,
     'extensions':{'KHR_materials_transmission':{'transmissionFactor':.25}},
     'name':'SFG_R1_glass','pbrMetallicRoughness':{
         'baseColorFactor':[.5199999809265137,.8199999928474426,.7200000286102295,.1599999964237213],
         'metallicFactor':0,'roughnessFactor':.25}}
BOUNDS={'min':[-300.3952741622925,-400.,69.9999988079071],
        'max':[300.3952741622925,400.,371.18585109710693]}
OUTPUTS={'BaseColor':'BaseColor','Metallic':'Metallic','Specular':'Specular',
         'Roughness':'Roughness','EmissiveColor':'EmissiveColor','Opacity':'Opacity',
         'Normal':'Normal','AmbientOcclusion':'Occlusion'}
ROOTS=('BaseColor','Metallic','Specular','Roughness','Anisotropy','Normal','Tangent',
       'EmissiveColor','Opacity','OpacityMask','WorldPositionOffset','Displacement',
       'SubsurfaceColor','ClearCoat','ClearCoatRoughness','AmbientOcclusion','Refraction',
       *(f'CustomizedUVs({i})' for i in range(8)),'MaterialAttributes','PixelDepthOffset',
       'ShadingModelFromMaterialExpression','SurfaceThickness','FrontMaterial')
DEFAULTS={'EmissiveFactor':[0.,0.,0.],'EmissiveStrength':[1.],'AlphaMode':[2.]}


def _numbers(actual,wanted,tolerance):
    return (isinstance(actual,list) and len(actual)==len(wanted)
        and all(type(a) in (int,float) and math.isfinite(a) and abs(a-b)<=tolerance
                for a,b in zip(actual,wanted)))


def source_contract(raw):
    """Preserve the exact raw extension; alpha is independent of transmission."""
    if not isinstance(raw,dict) or raw!=RAW:
        raise ValueError('exact original BLEND/transmission material required; no normalization/fallback')
    # Python equality equates True and1; enforce finite numeric source types too.
    values=raw['pbrMetallicRoughness'];trans=raw['extensions']['KHR_materials_transmission']['transmissionFactor']
    if (not _numbers(values['baseColorFactor'],RAW['pbrMetallicRoughness']['baseColorFactor'],0.)
            or not _numbers([values['metallicFactor'],values['roughnessFactor'],trans],[0.,.25,.25],0.)
            or raw['doubleSided'] is not True):
        raise ValueError('exact finite numeric source factors required')
    return {'raw_material':deepcopy(raw),'material':MATERIAL,'mesh':MESH,'triangles':48,
        'native_bounds_cm':deepcopy(BOUNDS),'function':FUNCTION,'function_body_package':dict(FUNCTION_BODY),
        'factor_inputs':{'BaseColorFactor_RGB':values['baseColorFactor'][:3],
            'BaseColorFactor_A':[values['baseColorFactor'][3]],'MetallicFactor':[values['metallicFactor']],
            'RoughnessFactor':[values['roughnessFactor']],'TransmissionFactor':[trans]},
        'function_defaults':deepcopy(DEFAULTS),'allowed_explicit_default_inputs':{'AlphaMode':[2.]},
        'root_outputs':dict(OUTPUTS),
        'custom_output':{'class':'/Script/Engine.MaterialExpressionThinTranslucentMaterialOutput',
            'TransmittanceColor':'TransmissionColor','SurfaceCoverage':None},
        'physical':{'BlendMode':'BLEND_Translucent','ShadingModel':'MSM_ThinTranslucent',
            'TranslucencyLightingMode':'TLM_SurfacePerPixelLighting','TwoSided':True,'bScreenSpaceReflections':True},
        'actor_recipe_cm':{'location':[-5000.,-19000.,5218.],'rotation':[0.,0.,0.],'scale':[1.,1.,1.],
            'collision':'NO_COLLISION','affect_navigation':False},
        'native_ready':False,'runtime_authorized':False}


def _pin(row):
    return (isinstance(row,dict) and type(row.get('bytes')) is int and row['bytes']>0
        and isinstance(row.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',row['sha256']) is not None)


def _reference(fields,node,index,input_name=''):
    """Normalized complete FExpressionInput proof, from CDO plus T3D delta."""
    expected={'Expression':node,'OutputIndex':index,'InputName':input_name,
              'Mask':0,'MaskR':0,'MaskG':0,'MaskB':0,'MaskA':0}
    return fields==expected and all(type(fields[k]) is int for k in expected if k not in ('Expression','InputName'))


def _default_reference(fields):
    core={'Expression','OutputIndex','InputName','Mask','MaskR','MaskG','MaskB','MaskA'}
    if (not isinstance(fields,dict) or not core<=set(fields)
            or set(fields)-core-{'UseConstant','Constant','ConstantX','ConstantY'}):return False
    return (_reference({k:fields[k] for k in core},None,0)
        and ('UseConstant' not in fields or fields['UseConstant'] is False))


def check_observation(observed):
    """Check a future readback; synthetic records are never native acceptance.

    Evidence must come from the existing guarded operator: public expression
    traversal, actual MF output names, explicit class-default + T3D root proofs
    and separate custom-output CDO/T3D proof. A dictionary-only bridge reply or
    parameter list cannot satisfy this contract. Unknown structures fail closed.
    """
    c=source_contract(deepcopy(RAW))
    if not isinstance(observed,dict):raise ValueError('explicit retained observation required')
    if (observed.get('material')!=MATERIAL or observed.get('mesh')!=MESH
            or observed.get('material_class')!='/Script/Engine.Material'
            or observed.get('mesh_class')!='/Script/Engine.StaticMesh'
            or observed.get('slot_materials')!=[MATERIAL] or observed.get('physical')!=c['physical']
            or type(observed.get('active_customized_uvs')) is not int or observed['active_customized_uvs']!=0
            or observed['physical'].get('TwoSided') is not True
            or observed['physical'].get('bScreenSpaceReflections') is not True):
        raise ValueError('exact held object/slot/ThinTranslucent physical state required')
    geo=observed.get('geometry',{})
    if (type(geo.get('triangles')) is not int or geo['triangles']!=48
            or not _numbers(geo.get('build_scale'),[1.,1.,1.],0.) or geo.get('nanite') is not False
            or geo.get('generate_lightmap_uvs') is not False or type(geo.get('simple_collision_count')) is not int
            or geo['simple_collision_count']!=0
            or geo.get('import_data_class')!='InterchangeAssetImportData'
            or any(not _numbers(geo.get('bounds',{}).get(edge),BOUNDS[edge],.2) for edge in ('min','max'))):
        raise ValueError('exact native48 triangle/baked XZY100/options readback required')
    g=observed.get('graph',{});call=g.get('call');nodes=g.get('nodes',{})
    if not isinstance(call,str) or not call.startswith(MATERIAL+':') or g.get('function')!=FUNCTION:
        raise ValueError('exact owned transmission body call required')
    prefix='/Script/Engine.MaterialExpression'
    if nodes.get(call)!=prefix+'MaterialFunctionCall':raise ValueError('actual function-call expression required')
    factors=g.get('factor_inputs',{})
    wanted_factors=dict(c['factor_inputs'])
    if 'AlphaMode' in factors:wanted_factors['AlphaMode']=[2.]
    if set(factors)!=set(wanted_factors):raise ValueError('five raw factors and optional explicit source-backed AlphaMode2 required')
    names=g.get('function_input_names');table=g.get('function_inputs')
    if (not isinstance(names,list) or not all(isinstance(n,str) and n for n in names)
            or len(set(names))!=len(names) or not isinstance(table,dict) or set(table)!=set(names)
            or set(name for name,row in table.items() if row is not None)!=set(factors)
            or not (set(c['factor_inputs'])|set(DEFAULTS))<=set(names)):
        raise ValueError('complete unique public function input table and exact connected set required')
    used={call}
    for name,wanted in wanted_factors.items():
        row=factors[name];node=row.get('node');cls=prefix+('Constant3Vector' if len(wanted)==3 else 'Constant')
        if (not isinstance(node,str) or not node.startswith(MATERIAL+':') or node in used
                or nodes.get(node)!=cls or not _numbers(row.get('value'),wanted,.0001)
                or not _reference(row.get('reference'),node,0,name) or table[name]!=row['reference']):
            raise ValueError('raw factor constant/identity differs: '+name)
        used.add(node)
    defaults=g.get('omitted_defaults',{})
    wanted_defaults={k:v for k,v in DEFAULTS.items() if k not in factors}
    if set(defaults)!=set(wanted_defaults):raise ValueError('actual omitted emission/strength/AlphaMode defaults required')
    for name,wanted in wanted_defaults.items():
        row=defaults[name]
        if (row.get('use_preview_default') is not True or row.get('preview_connected') is not False
                or not _numbers(row.get('value'),wanted,.0001)):
            raise ValueError('actual disconnected function preview default differs: '+name)
    outputs=g.get('function_outputs',[])
    if (not isinstance(outputs,list) or len(set(outputs))!=len(outputs)
            or any(name not in outputs for name in set(OUTPUTS.values())|{'TransmissionColor'})):
        raise ValueError('actual unambiguous named MF output table required; no guessed indices')
    roots=g.get('roots',{});default_roots=g.get('default_roots',{})
    if set(roots)!=set(ROOTS) or set(default_roots)!=set(ROOTS):raise ValueError('all30 explicit root/default witnesses required')
    for name in ROOTS:
        if not _default_reference(default_roots[name]):
            raise ValueError('actual disconnected class-default input required')
        if name in OUTPUTS:
            expected=dict(default_roots[name]);expected.update(Expression=call,OutputIndex=outputs.index(OUTPUTS[name]))
            core={k:roots[name].get(k) for k in ('Expression','OutputIndex','InputName','Mask','MaskR','MaskG','MaskB','MaskA')}
            if roots[name]!=expected or not _reference(core,call,outputs.index(OUTPUTS[name])):
                raise ValueError('material root connection/index/mask differs: '+name)
        elif roots[name]!=default_roots[name]:raise ValueError('unauthored root differs: '+name)
    custom=g.get('custom_outputs',[])
    if len(custom)!=1:raise ValueError('exact one thin-transmission custom output required')
    row=custom[0];node=row.get('node')
    if (not isinstance(node,str) or not node.startswith(MATERIAL+':') or node in used
            or nodes.get(node)!=prefix+'ThinTranslucentMaterialOutput'
            or not _reference(row.get('TransmittanceColor'),call,outputs.index('TransmissionColor'))
            or row.get('SurfaceCoverage')!=row.get('default_SurfaceCoverage')
            or not _default_reference(row.get('default_SurfaceCoverage'))):
        raise ValueError('custom transmission connection/mask or coverage default differs')
    used.add(node)
    if set(nodes)!=used:raise ValueError('extra/disconnected/unknown expression outside the closed graph')
    proofs=g.get('proofs',{})
    if set(proofs)!={'root_default','root_delta','custom_default','custom_delta','function_body_package'} or any(not _pin(v) for v in proofs.values()):
        raise ValueError('separate auditable root/custom/function witnesses required')
    if any(proofs['function_body_package'][k]!=v for k,v in FUNCTION_BODY.items()):
        raise ValueError('actual installed transmission body package differs from reviewed source')
    return {'stage':'OBSERVATION_CONTRACT_VALID_ADMISSION_PENDING','native_ready':False,
        'runtime_authorized':False,'source_alpha':c['factor_inputs']['BaseColorFactor_A'][0],
        'source_transmission':.25,'triangles':48,'glass_must_remain_held_until_admitted':True,
        'visual_acceptance':'pending native matched front/back/oblique appearance and preserved scene witnesses'}
