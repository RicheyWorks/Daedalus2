# SPDX-License-Identifier: MIT
"""32998 one bounded read-only observation of the two existing held glass assets.

Caller supplies the established exact execute_python queue/world/dirty guard.
Only evidence files and ordinary public text-export tasks are created here.
No asset creation, setters, recompilation, import, selection, camera or saves.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import time
import unreal


def _pin(row):
    raw=Path(row['path']).read_bytes()
    if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
        raise RuntimeError('pinned source/evidence changed: '+row['path'])
    return raw


def _module(row,name):
    scope={'__name__':name,'__file__':row['path']}
    exec(compile(_pin(row),row['path'],'exec'),scope);return scope


def _write(path,value):
    import os
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())


def _shape(value):
    return {'type':type(value).__name__,'repr':repr(value)[:1800]}


def _file_pin(path):
    raw=Path(path).read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def _export(obj,label,cfg):
    file=Path(cfg['folder'])/(label+'.t3d')
    if file.exists():raise RuntimeError('retained witness; no replay')
    task=unreal.AssetExportTask()
    for key,value in {'object':obj,'filename':str(file),'exporter':unreal.ObjectExporterT3D(),
        'automated':True,'prompt':False,'replace_identical':False,'selected':False,
        'use_file_archive':False,'write_empty_files':False,'ignore_object_list':[]}.items():task.set_editor_property(key,value)
    returned=unreal.Exporter.run_asset_export_task(task)
    if returned is not True or list(task.errors) or not file.is_file():raise RuntimeError('normal public text export failed')
    if not 0<file.stat().st_size<=8*1024*1024:raise RuntimeError('bounded public text witness exceeded')
    return file.read_text(encoding='utf-8-sig'),_file_pin(file)


def _flat(obj,label,cfg):
    text,proof=_export(obj,label,cfg);lines=[r.strip() for r in text.splitlines() if r.strip()]
    cls=obj.get_class().get_path_name();name=obj.get_name();path=obj.get_path_name()
    header='Begin Object Class='+cls+' Name="'+name+'" ExportPath="'+cls+"'"+path+"'\""
    if not lines or lines[0]!=header or lines[-1]!='End Object':raise RuntimeError('exact CDO/default-archetype text identity differs: '+label)
    properties={}
    for line in lines[1:-1]:
        key,separator,value=line.partition('=')
        if not separator or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\([0-9]+\))?',key) or key in properties:
            raise RuntimeError('unsupported nested/ambiguous text property: '+label)
        properties[key]=value
    return properties,proof


def _reference(fields,mat,nodes,graph):
    row={}
    for key,value in fields.items():
        if key=='Expression':
            if value=='None':row[key]=None
            else:
                found=[node.get_path_name() for node in nodes if graph['_node_ref'](value,node,mat)]
                if len(found)!=1:raise RuntimeError('serialized expression is not one exact observed owned node')
                row[key]=found[0]
        elif key in ('OutputIndex','Mask','MaskR','MaskG','MaskB','MaskA'):row[key]=int(value)
        elif key=='InputName':row[key]=json.loads(value)
        elif key=='UseConstant':
            if value not in ('True','False'):raise RuntimeError('actual typed bool differs')
            row[key]=value=='True'
        elif key in ('Constant','ConstantX','ConstantY'):row[key]=value
        else:raise RuntimeError('unknown input serialization field: '+key)
    return row


def _state(cfg,e,world,sub,policy,world_scope):
    import sys
    import ctypes
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in
            ('physical_total','physical_available','commit_total','commit_available','virtual_total','virtual_available','reserved')]
    memory=Memory();memory.length=ctypes.sizeof(memory)
    if (not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
            or memory.physical_available<1700000*1024 or memory.commit_available<2200000*1024):
        raise RuntimeError('fresh numeric memory floor not met')
    if time.time()>cfg['deadline_epoch']-90:raise RuntimeError('absolute readonly reserve reached')
    b=sys.modules['claude_unreal_bridge'];running=list(b._running)
    if (len(running)!=1 or any(req.get('type')!='execute_python' or not(req.get('params') or {}).get('code','').startswith(cfg['marker']) for gen,req,box in running)
            or b._jobs.qsize() or b._remote_lock.locked() or any(not box['done'].is_set() for box,t in b._job_boxes.values())):
        raise RuntimeError('conflicting/unfinished bridge operation')
    if world.get_path_name()!='/Game/Daedalus/DaedalusWorld.DaedalusWorld' or unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('world/PIE differs')
    maps=[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    content=sorted(p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    held=sorted(p.split('.')[0] for p in (policy['MATERIAL'],policy['MESH']))
    if maps or content!=held:raise RuntimeError('exact clean map/two held dirty-content packages required')
    for path in held:
        if (Path('C:/Unreal/DaedalusRealm/Content')/(path.removeprefix('/Game/')+'.uasset')).exists():raise RuntimeError('held package unexpectedly saved')
    return {'scene':world_scope['snapshot_scene'](),'world_digest':world_scope['world_existing_actor_digest'](),
        'dirty_maps':maps,'dirty_content':content,'queue_empty':True,'pie':False}


def collect(cfg):
    policy=_module(cfg['policy'],'_codex_glass_policy_frozen')
    graph=_module(cfg['graph_helper'],'_codex_glass_graph_frozen');graph['WITNESS_DIRECTORY']=cfg['folder']
    e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);world=e.get_editor_world()
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    w={'__name__':'_codex_glass_world_frozen','unreal':unreal,'math':math,'json':json,'hashlib':hashlib,'e':e,'world':world,'sub':sub}
    exec(compile(_pin(cfg['snap_source']),cfg['snap_source']['path'],'exec'),w)
    exec(compile(_pin(cfg['world_helper']),cfg['world_helper']['path'],'exec'),w)
    terminal=Path(cfg['folder'])/'native-terminal.json'
    if terminal.exists():raise RuntimeError('retained native terminal; no replay')
    report={'stage':'READONLY_STARTED','raw':{},'native_mutations':0,'saved':False,'placed':False}
    started=time.perf_counter();before=_state(cfg,e,world,sub,policy,w);report['before']=before
    baseline=json.loads(_pin(cfg['baseline']))
    old={r['path']:r for r in baseline['scene']['actors']};now={r['path']:r for r in before['scene']['actors']}
    if now!=old or len(now)!=152:raise RuntimeError('exact saved152 selected actors differ')
    try:
        mat=unreal.find_object(None,policy['MATERIAL']);mesh=unreal.find_object(None,policy['MESH'])
        if mat is None or mesh is None:raise RuntimeError('existing loaded held objects missing; no asset load/import fallback')
        mel=unreal.MaterialEditingLibrary;nodes=list(mel.get_material_expressions(mat))
        report['raw']['objects']={'material':mat.get_class().get_path_name(),'mesh':mesh.get_class().get_path_name(),
            'expressions':[{'path':n.get_path_name(),'class':n.get_class().get_path_name()} for n in nodes]}
        calls=[n for n in nodes if n.get_class().get_path_name()=='/Script/Engine.MaterialExpressionMaterialFunctionCall']
        customs=[n for n in nodes if n.get_class().get_path_name()=='/Script/Engine.MaterialExpressionThinTranslucentMaterialOutput']
        if len(calls)!=1 or len(customs)!=1:raise RuntimeError('expected one actual transmission call/custom output missing; see expression inventory')
        call,custom=calls[0],customs[0];function=call.get_editor_property('material_function')
        custom_cdo=unreal.get_default_object(custom.get_class())
        cdo_fields,cdo_proof=_flat(custom_cdo,'custom-class-default',cfg)
        delta_fields,delta_proof=_flat(custom,'held-custom-delta',cfg)
        cd={name:graph['_split_fields'](cdo_fields[name]) for name in ('TransmittanceColor','SurfaceCoverage')}
        required={'Expression','OutputIndex','InputName','Mask','MaskR','MaskG','MaskB','MaskA'}
        if any(set(row)!=required or row['Expression']!='None' for row in cd.values()):raise RuntimeError('complete explicit actual FExpressionInput CDO defaults required')
        custom_fields={name:{**cd[name],**graph['_split_fields'](delta_fields[name])} if name in delta_fields else dict(cd[name]) for name in cd}
        call_fields,call_proof=_flat(call,'held-call-input-output',cfg)
        outputs={int(k[8:-1]):json.loads(graph['_split_fields'](v)['OutputName']) for k,v in call_fields.items() if re.fullmatch(r'Outputs\([0-9]+\)',k)}
        if set(outputs)!=set(range(len(outputs))):raise RuntimeError('complete actual output table required')
        output_names=[outputs[i] for i in range(len(outputs))]
        names=[str(v) for v in mel.get_material_expression_input_names(call)]
        input_nodes=list(mel.get_inputs_for_material_expression(mat,call))
        report['raw']['input_return_shapes']={'names':_shape(names),'nodes':_shape(input_nodes)}
        table={};factors={}
        for key,value in call_fields.items():
            if not re.fullmatch(r'FunctionInputs\([0-9]+\)',key):continue
            fields=graph['_split_fields'](value);inputs=graph['_split_fields'](fields['Input'])
            merged={**cd['TransmittanceColor'],**inputs};name=json.loads(merged['InputName'])
            if name in table:raise RuntimeError('duplicate actual function input')
            ref=_reference(merged,mat,nodes,graph);table[name]=ref if ref['Expression'] is not None else None
        if len(names)!=len(input_nodes) or set(table)!=set(names) or len(names)!=len(set(names)):raise RuntimeError('public/serialized full function-input table differs')
        by_path={n.get_path_name():n for n in nodes}
        for name,node in zip(names,input_nodes):
            ref=table[name]
            if (node.get_path_name() if node else None)!=(ref['Expression'] if ref else None):raise RuntimeError('public function input binding differs')
            if node is None:continue
            cls=node.get_class().get_path_name()
            if cls=='/Script/Engine.MaterialExpressionConstant3Vector':
                value=node.get_editor_property('constant');values=[float(value.r),float(value.g),float(value.b)]
            elif cls=='/Script/Engine.MaterialExpressionConstant':value=node.get_editor_property('r');values=[float(value)]
            else:raise RuntimeError('actual factor input is not a raw constant: '+name)
            report['raw'].setdefault('factor_return_shapes',{})[name]=_shape(value)
            factors[name]={'node':node.get_path_name(),'value':values,'reference':ref}
        fn_inputs=[n for n in mel.get_material_function_expressions(function) if n.get_class().get_path_name()=='/Script/Engine.MaterialExpressionFunctionInput']
        report['raw']['complete_function_input_names']=names
        report['raw']['complete_function_input_bindings']=table
        report['raw']['actual_factor_values']=factors
        report['raw']['actual_function_default_input_names']=[str(n.get_editor_property('input_name')) for n in fn_inputs]
        body_text,body_proof=_export(function,'referenced-transmission-function',cfg)
        report['raw']['referenced_function_text']=body_proof
        defaults={}
        for name,wanted in policy['DEFAULTS'].items():
            if name in factors:continue
            found=[n for n in fn_inputs if str(n.get_editor_property('input_name'))==name]
            if len(found)!=1:
                defaults[name]={'missing_function_input':True,'matches':len(found)}
                report['raw'].setdefault('missing_function_defaults',[]).append({'name':name,'matches':len(found)})
                continue
            n=found[0];value=n.get_editor_property('preview_value')
            preview_nodes=list(mel.get_inputs_for_material_function_expression(function,n))
            values=[float(value.get_editor_property(k)) for k in ('X','Y','Z','W')]
            defaults[name]={'value':values[:len(wanted)],'use_preview_default':bool(n.get_editor_property('use_preview_value_as_default')),
                'preview_connected':any(item is not None for item in preview_nodes)}
            report['raw'].setdefault('default_return_shapes',{})[name]={'value':_shape(value),'preview_nodes':_shape(preview_nodes),'all4values':values}
        cdo,root_defaults,other,root_default_proof=graph['_default_inputs'](mat.get_editor_property('EditorOnlyData'))
        root_delta,root_other,root_proof=graph['_export_inputs'](mat.get_editor_property('EditorOnlyData'),'held-root-delta')
        roots={name:_reference({**fields,**root_delta.get(name,{})},mat,nodes,graph) for name,fields in root_defaults.items()}
        normalized_defaults={name:_reference(fields,mat,nodes,graph) for name,fields in root_defaults.items()}
        collection={**graph['_split_fields'](other['ExpressionCollection']),**graph['_split_fields'](root_other['ExpressionCollection'])}
        refs=collection['Expressions'][1:-1].split(',')
        if (len(refs)!=len(nodes) or len(set(refs))!=len(refs)
                or any(sum(graph['_node_ref'](ref,n,mat) for n in nodes)!=1 for ref in refs)
                or any(sum(graph['_node_ref'](ref,n,mat) for ref in refs)!=1 for n in nodes)):
            raise RuntimeError('serialized/public complete expression collection differs')
        if collection['EditorComments'] or collection['ExpressionExecBegin']!='None' or collection['ExpressionExecEnd']!='None':raise RuntimeError('unexpected editor execution/comments')
        raw_physical={key:mat.get_editor_property(key) for key in ('BlendMode','ShadingModel','TranslucencyLightingMode','TwoSided','bScreenSpaceReflections')}
        report['raw']['physical_return_shapes']={k:_shape(v) for k,v in raw_physical.items()}
        physical={k:v for k,v in raw_physical.items() if isinstance(v,bool)}
        enums={'BlendMode':(unreal.BlendMode.BLEND_TRANSLUCENT,'BLEND_Translucent'),
               'ShadingModel':(unreal.MaterialShadingModel.MSM_THIN_TRANSLUCENT,'MSM_ThinTranslucent'),
               'TranslucencyLightingMode':(unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,'TLM_SurfacePerPixelLighting')}
        for key,(enum,text) in enums.items():physical[key]=text if raw_physical[key]==enum else str(raw_physical[key])
        subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem);build=subsystem.get_lod_build_settings(mesh,0)
        box=mesh.get_bounding_box();triangles=mesh.get_num_triangles(0)
        geometry={'triangles':int(triangles),'build_scale':[float(getattr(build.build_scale3d,k)) for k in ('x','y','z')],
            'nanite':bool(mesh.get_editor_property('nanite_settings').enabled),'generate_lightmap_uvs':bool(build.generate_lightmap_u_vs),
            'simple_collision_count':int(subsystem.get_simple_collision_count(mesh)),
            'import_data_class':mesh.get_editor_property('asset_import_data').get_class().get_name(),
            'bounds':{edge:[float(getattr(getattr(box,edge),k)) for k in ('x','y','z')] for edge in ('min','max')}}
        _pin(cfg['function_body'])
        report['observation']={'material':mat.get_path_name(),'mesh':mesh.get_path_name(),'material_class':mat.get_class().get_path_name(),
            'mesh_class':mesh.get_class().get_path_name(),'slot_materials':[mesh.get_material(i).get_path_name() for i in range(len(mesh.get_editor_property('static_materials')))],
            'physical':physical,'active_customized_uvs':int(mat.get_editor_property('NumCustomizedUVs')),'geometry':geometry,
            'graph':{'call':call.get_path_name(),'function':function.get_path_name(),'nodes':{p:n.get_class().get_path_name() for p,n in by_path.items()},
                'factor_inputs':factors,'function_input_names':names,'function_inputs':table,'omitted_defaults':defaults,'function_outputs':output_names,
                'roots':roots,'default_roots':normalized_defaults,'custom_outputs':[{'node':custom.get_path_name(),
                    'TransmittanceColor':_reference(custom_fields['TransmittanceColor'],mat,nodes,graph),
                    'SurfaceCoverage':_reference(custom_fields['SurfaceCoverage'],mat,nodes,graph),
                    'default_SurfaceCoverage':_reference(cd['SurfaceCoverage'],mat,nodes,graph)}],
                'proofs':{'root_default':root_default_proof,'root_delta':root_proof,'custom_default':cdo_proof,'custom_delta':delta_proof,'function_body_package':cfg['function_body']}}}
        report['raw']['call_text_proof']=call_proof;report['raw']['triangle_return_shape']=_shape(triangles)
        try:
            report['qualification']=policy['check_observation'](report['observation']);report['stage']='QUALIFIED_READONLY_ADMISSION_PENDING'
        except Exception as exc:report.update(stage='HOLD_ACTUAL_GRAPH_CONTRACT_DIFFERS',contract_error=str(exc),contract_error_type=type(exc).__name__)
    except Exception as exc:
        report.update(stage='KNOWN_TERMINAL_READONLY_SHAPE_REFUSAL',error=str(exc),error_type=type(exc).__name__)
    after=_state(cfg,e,world,sub,policy,w);report['after']=after
    if before!=after:raise RuntimeError('readonly before/after state changed; preserve custody and reconcile')
    report['elapsed_seconds']=time.perf_counter()-started
    report['preservation']='exact before/after selected scene/camera/world digest and clean map/two held dirty packages equal'
    _write(terminal,report);return report
