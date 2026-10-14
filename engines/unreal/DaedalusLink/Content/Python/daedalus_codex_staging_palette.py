# SPDX-License-Identifier: MIT
"""Owned staging palette using the existing native MaterialEditingLibrary path.

No prepared mesh/shared material edits and no project, lighting or usage flags.
Invoke through the existing daedalus.steps bridge during the accepted turn.
"""
import hashlib
import json
import math
from pathlib import Path
import unreal

ROOT='/Game/Daedalus/Art/Islands/CodexContest/Palette'


def palette_steps(colours,journal_path,repair_empty_stub=False,profile=None):
    if profile is not None:
        if type(profile) is not str or profile!='aetherflow_linear_pbr_v1':raise ValueError('unknown owned palette profile')
        return (yield from _aetherflow_palette_steps(colours,journal_path,repair_empty_stub))
    journal=Path(journal_path)
    record=json.loads(journal.read_text())
    record['palette_mutations']=[]
    def state(action,target):
        record['palette_mutations'].append({'action':action,'target':target,'state':'pending'})
        journal.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    def responded(**fields):
        record['palette_mutations'][-1].update(state='responded',**fields)
        journal.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    eal,mel=unreal.EditorAssetLibrary,unreal.MaterialEditingLibrary
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    base_path=ROOT+'/M_CodexPalette_v1'
    base=eal.load_asset(base_path)
    created=base is None
    if base is None:
        state('create_base',base_path)
        base=tools.create_asset('M_CodexPalette_v1',ROOT,unreal.Material,unreal.MaterialFactoryNew())
        responded(path=base.get_path_name())
    count=mel.get_num_material_expressions(base)
    completed_stub=count==0
    if count==0:
        if not created and not repair_empty_stub:raise RuntimeError('empty retained base requires explicit inspected-stub repair')
        state('complete_inspected_empty_base',base_path)
        for name,kind,default,prop,y in (
            ('Tint',unreal.MaterialExpressionVectorParameter,unreal.LinearColor(1,1,1,1),unreal.MaterialProperty.MP_BASE_COLOR,0),
            ('Roughness',unreal.MaterialExpressionScalarParameter,.85,unreal.MaterialProperty.MP_ROUGHNESS,200),
            ('Metallic',unreal.MaterialExpressionScalarParameter,0.,unreal.MaterialProperty.MP_METALLIC,400)):
            node=mel.create_material_expression(base,kind,-400,y)
            node.set_editor_property('parameter_name',name)
            node.set_editor_property('default_value',default)
            if not mel.connect_material_property(node,'',prop):raise RuntimeError('owned material connection failed')
        mel.recompile_material(base)
        responded(expressions=mel.get_num_material_expressions(base))
    if mel.get_num_material_expressions(base)!=3:raise RuntimeError('owned palette graph differs')
    dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    state('save_base' if created or completed_stub or base_path in dirty else 'reuse_clean_base',base_path)
    saved=eal.save_loaded_asset(base,False) if created or completed_stub or base_path in dirty else True
    responded(save_return=bool(saved),unchanged_skipped=not (created or completed_stub or base_path in dirty))
    if not saved:raise RuntimeError('owned palette base save failed')
    materials={}
    for key,settings in sorted(colours.items()):
        suffix=hashlib.sha256(json.dumps(settings,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12]
        name='MI_Codex_'+key+'_'+suffix
        path=ROOT+'/'+name
        instance=eal.load_asset(path)
        created_instance=instance is None
        if instance is None:
            state('create_instance',path)
            instance=tools.create_asset(name,ROOT,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
            mel.set_material_instance_parent(instance,base)
            mel.set_material_instance_vector_parameter_value(instance,'Tint',unreal.LinearColor(*settings['linear_rgb'],1))
            mel.set_material_instance_scalar_parameter_value(instance,'Roughness',settings['roughness'])
            mel.set_material_instance_scalar_parameter_value(instance,'Metallic',settings['metallic'])
            responded(path=instance.get_path_name())
        if instance.get_editor_property('parent')!=base:raise RuntimeError('palette instance parent differs')
        tint=mel.get_material_instance_vector_parameter_value(instance,'Tint')
        if any(abs(getattr(tint,axis)-value)>1e-5 for axis,value in zip(('r','g','b'),settings['linear_rgb'])):
            raise RuntimeError('linear palette readback differs')
        for parameter in ('Roughness','Metallic'):
            if abs(mel.get_material_instance_scalar_parameter_value(instance,parameter)-settings[parameter.lower()])>1e-5:
                raise RuntimeError('palette surface readback differs')
        dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        needs_save=created_instance or path in dirty
        if not needs_save:
            native_file=Path(unreal.Paths.project_content_dir())/(path[len('/Game/'):]+'.uasset')
            if not native_file.is_file():raise RuntimeError('existing clean palette instance lacks a disk save')
        state('save_instance' if needs_save else 'reuse_clean_instance',path)
        saved=eal.save_loaded_asset(instance,False) if needs_save else True
        responded(save_return=bool(saved),unchanged_skipped=not needs_save)
        if not saved:raise RuntimeError('owned palette instance save failed')
        materials['CodexVoxel_'+key]={'refPath':instance.get_path_name()}
        yield key
    return materials


def _aetherflow_palette_steps(colours,journal_path,repair_empty_stub=False):
    """Owned linear glTF PBR palette; does not convert already-linear baseColor.

    Only the five life-source slots are admitted. A source may use a subset.
    Optional clearcoat factors retain their explicit values, defaulting to the
    source contract's .25 clearcoat and zero clearcoat roughness. No root, base,
    graph or project settings can be supplied by the caller.
    """
    allowed={'Gold','Turquoise','Petrol','Coral','Ice'}
    fields={'linear_rgb','roughness','metallic','clearcoat','clearcoat_roughness'}
    if not isinstance(colours,dict) or not colours or not set(colours)<=allowed:
        raise ValueError('Aetherflow requires a nonempty subset of the five life-source palette keys')
    normalized={}
    for key,settings in sorted(colours.items()):
        if not isinstance(settings,dict) or not set(settings)<=fields or not {'linear_rgb','roughness','metallic'}<=set(settings):
            raise ValueError('Aetherflow palette settings differ from the linear PBR contract')
        rgb=settings['linear_rgb']
        if not isinstance(rgb,(list,tuple)) or len(rgb)!=3:
            raise ValueError('Aetherflow requires three already-linear baseColor channels')
        values=dict(roughness=settings['roughness'],metallic=settings['metallic'],
                    clearcoat=settings.get('clearcoat',.25),clearcoat_roughness=settings.get('clearcoat_roughness',0.))
        if any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1
               for value in (*rgb,*values.values())):
            raise ValueError('Aetherflow PBR values must be finite numbers in [0,1]')
        normalized[key]=dict(linear_rgb=[float(value) for value in rgb],
                             **{name:float(value) for name,value in values.items()})
    root='/Game/Daedalus/Art/Islands/CodexContest/Aetherflow/Palette'
    base_name='M_Aetherflow_Clearcoat_v1'
    base_path=root+'/'+base_name
    journal=Path(journal_path)
    record=json.loads(journal.read_text())
    record['palette_profile']='aetherflow_linear_pbr_v1'
    record['palette_mutations']=[]
    def state(action,target):
        record['palette_mutations'].append({'action':action,'target':target,'state':'pending'})
        journal.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    def responded(**values):
        record['palette_mutations'][-1].update(state='responded',**values)
        journal.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    def disk_proof(path):
        native_file=Path(unreal.Paths.project_content_dir())/(path[len('/Game/'):]+'.uasset')
        if not native_file.is_file():raise RuntimeError('Aetherflow palette asset lacks a disk save')
        payload=native_file.read_bytes()
        return {'path':str(native_file),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
    eal,mel=unreal.EditorAssetLibrary,unreal.MaterialEditingLibrary
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    base=eal.load_asset(base_path)
    created=base is None
    if created:
        state('create_base',base_path)
        base=tools.create_asset(base_name,root,unreal.Material,unreal.MaterialFactoryNew())
        if base is None:raise RuntimeError('Aetherflow base creation returned no material')
        responded(path=base.get_path_name())
    if not isinstance(base,unreal.Material):raise RuntimeError('Aetherflow base path is not a material')
    count=mel.get_num_material_expressions(base)
    completed_stub=count==0
    if completed_stub:
        if not created and not repair_empty_stub:raise RuntimeError('empty retained Aetherflow base requires explicit inspected-stub repair')
        state('complete_inspected_empty_base',base_path)
        base.set_editor_property('two_sided',True)
        base.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_CLEAR_COAT)
        base.set_editor_property('use_material_attributes',True)
        attributes=mel.create_material_expression(base,unreal.MaterialExpressionMakeMaterialAttributes,-100,0)
        if attributes is None:raise RuntimeError('Aetherflow material attributes expression creation failed')
        input_names=[str(name) for name in mel.get_material_expression_input_names(attributes)]
        pins={}
        for semantic in ('basecolor','roughness','metallic','clearcoat','clearcoatroughness'):
            matches=[name for name in input_names if ''.join(char for char in name.casefold() if char.isalnum())==semantic]
            if len(matches)!=1:
                raise RuntimeError('Aetherflow material attributes input is missing or ambiguous: '+semantic+'; exposed='+repr(input_names))
            pins[semantic]=matches[0]
        for name,kind,default,semantic,y in (
            ('Tint',unreal.MaterialExpressionVectorParameter,unreal.LinearColor(1,1,1,1),'basecolor',0),
            ('Roughness',unreal.MaterialExpressionScalarParameter,.85,'roughness',200),
            ('Metallic',unreal.MaterialExpressionScalarParameter,0.,'metallic',400),
            ('Clearcoat',unreal.MaterialExpressionScalarParameter,.25,'clearcoat',600),
            ('ClearcoatRoughness',unreal.MaterialExpressionScalarParameter,0.,'clearcoatroughness',800)):
            node=mel.create_material_expression(base,kind,-400,y)
            if node is None:raise RuntimeError('Aetherflow parameter expression creation failed')
            node.set_editor_property('parameter_name',name)
            node.set_editor_property('default_value',default)
            if not mel.connect_material_expressions(node,'',attributes,pins[semantic]):
                raise RuntimeError('Aetherflow material attributes connection failed: '+name)
        if not mel.connect_material_property(attributes,'',unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES):
            raise RuntimeError('Aetherflow material attributes output connection failed')
        mel.recompile_material(base)
        responded(expressions=mel.get_num_material_expressions(base),material_attributes_inputs=pins)
    if mel.get_num_material_expressions(base)!=6:raise RuntimeError('Aetherflow palette graph differs')
    if not base.get_editor_property('two_sided') or not base.get_editor_property('use_material_attributes') or base.get_editor_property('shading_model')!=unreal.MaterialShadingModel.MSM_CLEAR_COAT:
        raise RuntimeError('Aetherflow base two-sided, material attributes or clearcoat shading-model readback differs')
    dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    needs_save=created or completed_stub or base_path in dirty
    if not needs_save:disk_proof(base_path)
    state('save_base' if needs_save else 'reuse_clean_base',base_path)
    saved=eal.save_loaded_asset(base,False) if needs_save else True
    proof=disk_proof(base_path) if saved else None
    responded(save_return=bool(saved),unchanged_skipped=not needs_save,disk=proof,
              two_sided=bool(base.get_editor_property('two_sided')),use_material_attributes=bool(base.get_editor_property('use_material_attributes')),
              shading_model=str(base.get_editor_property('shading_model')))
    if not saved:raise RuntimeError('Aetherflow palette base save failed')
    materials={}
    scalar_fields=(('Roughness','roughness'),('Metallic','metallic'),('Clearcoat','clearcoat'),('ClearcoatRoughness','clearcoat_roughness'))
    for key,settings in sorted(normalized.items()):
        suffix=hashlib.sha256(json.dumps(settings,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12]
        slot='SW_Life_'+key
        name='MI_Aetherflow_'+slot+'_'+suffix
        path=root+'/'+name
        instance=eal.load_asset(path)
        created_instance=instance is None
        if created_instance:
            state('create_instance',path)
            instance=tools.create_asset(name,root,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
            if instance is None:raise RuntimeError('Aetherflow instance creation returned no material')
            mel.set_material_instance_parent(instance,base)
            mel.set_material_instance_vector_parameter_value(instance,'Tint',unreal.LinearColor(*settings['linear_rgb'],1))
            for parameter,field in scalar_fields:
                mel.set_material_instance_scalar_parameter_value(instance,parameter,settings[field])
            responded(path=instance.get_path_name())
        if not isinstance(instance,unreal.MaterialInstanceConstant) or instance.get_editor_property('parent')!=base:
            raise RuntimeError('Aetherflow palette instance class or parent differs')
        tint=mel.get_material_instance_vector_parameter_value(instance,'Tint')
        if any(not math.isfinite(getattr(tint,axis)) or abs(getattr(tint,axis)-value)>1e-5
               for axis,value in zip(('r','g','b','a'),(*settings['linear_rgb'],1.))):
            raise RuntimeError('Aetherflow linear baseColor readback differs')
        readback={}
        for parameter,field in scalar_fields:
            actual=mel.get_material_instance_scalar_parameter_value(instance,parameter)
            if not math.isfinite(actual) or abs(actual-settings[field])>1e-5:raise RuntimeError('Aetherflow PBR parameter readback differs')
            readback[field]=actual
        dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        needs_save=created_instance or path in dirty
        if not needs_save:disk_proof(path)
        state('save_instance' if needs_save else 'reuse_clean_instance',path)
        saved=eal.save_loaded_asset(instance,False) if needs_save else True
        proof=disk_proof(path) if saved else None
        responded(save_return=bool(saved),unchanged_skipped=not needs_save,disk=proof,
                  linear_rgb=[getattr(tint,axis) for axis in ('r','g','b')],**readback)
        if not saved:raise RuntimeError('Aetherflow palette instance save failed')
        materials[slot]={'refPath':instance.get_path_name()}
        yield key
    return materials
