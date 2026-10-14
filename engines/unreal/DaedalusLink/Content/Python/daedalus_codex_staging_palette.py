# SPDX-License-Identifier: MIT
"""Owned staging palette using the existing native MaterialEditingLibrary path.

No prepared mesh/shared material edits and no project, lighting or usage flags.
Invoke through the existing daedalus.steps bridge during the accepted turn.
"""
import hashlib
import json
from pathlib import Path
import unreal

ROOT='/Game/Daedalus/Art/Islands/CodexContest/Palette'


def palette_steps(colours,journal_path,repair_empty_stub=False):
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
