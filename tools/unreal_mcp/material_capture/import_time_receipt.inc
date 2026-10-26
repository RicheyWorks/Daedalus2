# SPDX-License-Identifier: MIT
# Inject config before exec into one retained module. Exact scope is one NEW
# isolated M0/source copy. Supported existing pipeline hooks; no new service.
"""Native Python module for one fresh isolated material import observation."""
import hashlib,json
from pathlib import Path
import unreal

events=[]
errors=[]
done=False
imported_paths=[]
copy=None
params=None
pipelines=[]
source_container=None
root_uid=None
live=None
import_native=None

def write(name,value):
    raw=json.dumps(value,indent=2,allow_nan=False).encode('utf-8')
    if len(raw)>524288:raise RuntimeError('Bounded copy-probe receipt exceeded')
    with (Path(config['output'])/name).open('xb') as f:f.write(raw)

def object_info(obj):
    return None if obj is None else {'path':obj.get_path_name(),'class':obj.get_class().get_path_name()}

def connection(container,node,role):
    result=unreal.InterchangeShaderPortsAPI.get_input_connection(node,role)
    if result is None:return None
    if not isinstance(result,(tuple,list)) or len(result)!=2 or not all(type(x)is str for x in result):
        raise RuntimeError('Unexpected public connection result')
    return {'uid':result[0],'output':result[1]}

def capture(container,uid,phase,asset=None):
    factory_uids=list(container.get_nodes(unreal.InterchangeFactoryBaseNode))
    if not 1<=len(factory_uids)<=128:raise RuntimeError('Factory inventory outside bound')
    root=container.get_node(uid)
    row={'phase':phase,'container':object_info(container),'asset':object_info(asset),'root_uid':uid,
         'factory_uids':sorted(factory_uids),'root':object_info(root),'linked_nodes':{}}
    if root is not None:
        row['root_label']=root.get_display_label()
        row['root_targets']=list(root.get_target_node_uids())
        row['root_factory_dependencies']=sorted(root.get_factory_dependencies())
        row['root_connections']={role:connection(container,root,role) for role in ('BaseColor','Metallic','Roughness')}
        pending={v['uid'] for v in row['root_connections'].values() if v is not None}
        if len(pending)>3:raise RuntimeError('Root connection bound exceeded')
        for target in sorted(pending):
            node=container.get_node(target)
            entry={'node':object_info(node)}
            if node is not None:
                entry['label']=node.get_display_label()
                entry['inputs']={role:connection(container,node,role) for role in ('BaseColorFactor_RGB','MetallicFactor','RoughnessFactor')}
                for v in entry['inputs'].values():
                    if v is not None and v['uid'] not in pending:
                        row['linked_nodes'][v['uid']]={'node':object_info(container.get_node(v['uid']))}
            row['linked_nodes'][target]=entry
    write(phase+'.json',row);events.append(phase)
    return row

def copy_metadata(phase):
    obj=unreal.find_object(None,config['copy_path'],follow_redirectors=False)
    if obj is None or obj.get_path_name()!=config['copy_path']:raise RuntimeError('Exact copied material unavailable')
    data=obj.get_editor_property('asset_import_data')
    if data.get_outer()!=obj:raise RuntimeError('Copy import data is not owned by copy')
    row=capture(data.get_node_container(),data.get_editor_property('node_unique_id'),phase,obj)
    return row

def exact_connection(node,role):
    result=connection(None,node,role)
    if result is None:raise RuntimeError('Required actual connection absent: '+role)
    return result

def actual_chain(container,uid,asset):
    root=container.get_node(uid);targets=list(root.get_target_node_uids())
    if len(targets)!=1:raise RuntimeError('Exactly one source material graph target required')
    graph=container.get_node(targets[0])
    if not isinstance(graph,unreal.InterchangeShaderGraphNode):raise RuntimeError('Exact translated material graph unavailable')
    roles={'base_color':('BaseColor','BaseColorFactor_RGB'),'metallic':('Metallic','MetallicFactor'),'roughness':('Roughness','RoughnessFactor')}
    graph_connections={lane:exact_connection(graph,output) for lane,(output,role) in roles.items()}
    shader_ids={x['uid'] for x in graph_connections.values()}
    if len(shader_ids)!=1:raise RuntimeError('Source properties do not share exact function')
    shader=container.get_node(next(iter(shader_ids)))
    if not isinstance(shader,unreal.InterchangeFunctionCallShaderNode):raise RuntimeError('Exact translated function unavailable')
    root_connections={lane:exact_connection(root,output) for lane,(output,role) in roles.items()}
    factory_ids={x['uid'] for x in root_connections.values()}
    if len(factory_ids)!=1:raise RuntimeError('Factory properties do not share exact function')
    factory=container.get_node(next(iter(factory_ids)))
    if not isinstance(factory,unreal.InterchangeMaterialFunctionCallExpressionFactoryNode):raise RuntimeError('Exact factory function unavailable')
    attributes={};factor_factories={};inputs={}
    for lane,(output,role) in roles.items():
        key=unreal.InterchangeShaderPortsAPI.make_input_value_key(role)
        if lane=='base_color':
            value=shader.get_linear_color_attribute(key)
            if value is None:raise RuntimeError('Typed source RGB attribute unavailable')
            value=[value.r,value.g,value.b,value.a];kind='LinearColor'
        else:
            value=shader.get_float_attribute(key);kind='Float'
            if value is None:raise RuntimeError('Typed source scalar attribute unavailable')
        attributes[lane]={'role':role,'kind':kind,'value':value}
        inputs[lane]=exact_connection(factory,role)
        leaf=container.get_node(inputs[lane]['uid'])
        if not isinstance(leaf,unreal.InterchangeMaterialExpressionFactoryNode):raise RuntimeError('Exact factor factory unavailable')
        factor_factories[lane]={'uid':leaf.get_unique_id(),'class':leaf.get_class().get_path_name(),'expression_class':leaf.call_method('GetCustomExpressionClassName',args=()),'expression_path':leaf.get_string_attribute('MaterialExpressionPath')}
    return {'source_sha256':config['source_sha256'],'root_uid':uid,'container_path':container.get_path_name(),'root_targets':targets,'root_connections':root_connections,
            'shader_graph':{'uid':graph.get_unique_id(),'class':graph.get_class().get_path_name(),'label':graph.get_display_label(),'connections':graph_connections},
            'function_shader':{'uid':shader.get_unique_id(),'class':shader.get_class().get_path_name(),'function_path':shader.call_method('GetCustomMaterialFunction',args=()),'attributes':attributes},
            'factory_function':{'uid':factory.get_unique_id(),'class':factory.get_class().get_path_name(),'expression_class':factory.call_method('GetCustomExpressionClassName',args=()),'expression_path':factory.get_string_attribute('MaterialExpressionPath'),'inputs':inputs},'factor_factories':factor_factories}

@unreal.uclass()
class DaedalusImportReceiptObserverV1(unreal.InterchangePythonPipelineBase):
    @unreal.ufunction(override=True)
    def scripted_execute_pipeline(self,base_node_container,source_datas,content_base_path):
        global source_container
        source_container=base_node_container
        try:
            if len(source_datas)!=1:raise RuntimeError('Exactly one copied source is required')
            if Path(source_datas[0].get_filename()).resolve()!=Path(config['source']).resolve():raise RuntimeError('Import source escaped exact copied file')
            raw=Path(config['source']).read_bytes()
            if len(raw)!=18576 or hashlib.sha256(raw).hexdigest()!=config['source_sha256']:raise RuntimeError('Copied source differs')
            root=base_node_container.get_node(root_uid)
            if not isinstance(root,unreal.InterchangeMaterialFactoryNode):raise RuntimeError('Selected root factory absent')
            if content_base_path.rstrip('/')!=config['destination']:raise RuntimeError('Fresh import destination differs')
            if not root.is_enabled():raise RuntimeError('Fresh material factory unexpectedly disabled')
            reference=root.get_custom_reference_object()
            if reference is not None and unreal.get_default_object(unreal.SystemLibrary).call_method('BreakSoftObjectPath',args=(reference,)):raise RuntimeError('Fresh factory already references an existing object')
            capture(base_node_container,root_uid,'job_after_generic_before_isolation')
            disabled=[]
            for uid in base_node_container.get_nodes(unreal.InterchangeFactoryBaseNode):
                node=base_node_container.get_node(uid)
                if uid!='CommonPipelineDataFactoryNode' and not isinstance(node,(unreal.InterchangeBaseMaterialFactoryNode,unreal.InterchangeMaterialExpressionFactoryNode)):
                    raise RuntimeError('Unexpected nonmaterial asset factory; refuse creation')
                if isinstance(node,unreal.InterchangeBaseMaterialFactoryNode) and uid!=root_uid:
                    node.set_enabled(False)
                    if node.is_enabled():raise RuntimeError('Other asset factory remains enabled')
                    disabled.append(uid)
            write('isolation.json',{'selected_root':root_uid,'copy_path':config['copy_path'],'disabled_other_asset_factories':disabled,'expression_factory_nodes_preserved':True,'source_container':object_info(base_node_container)})
        except Exception as exc:
            errors.append('pre_pipeline: '+str(exc))
            for uid in base_node_container.get_nodes(unreal.InterchangeFactoryBaseNode):
                node=base_node_container.get_node(uid)
                if not isinstance(node,unreal.InterchangeMaterialExpressionFactoryNode):node.set_enabled(False)
            write('pre-pipeline-error.json',{'error':str(exc),'all_asset_roots_disabled':True})

    @unreal.ufunction(override=True)
    def scripted_execute_post_factory_pipeline(self,base_node_container,factory_node_key,created_asset,is_reimport):
        try:
            if created_asset.get_path_name()!=config['copy_path'] or factory_node_key!=root_uid or is_reimport:
                raise RuntimeError('PostFactory identity escaped exact fresh import')
            if base_node_container!=source_container:raise RuntimeError('PostFactory supplied a different job container')
            capture(base_node_container,factory_node_key,'post_factory_job',created_asset)
            global live
            live=actual_chain(base_node_container,factory_node_key,created_asset)
            live['boundaries']=[{'phase':'post_factory','container_path':base_node_container.get_path_name(),'asset_path':created_asset.get_path_name(),'is_reimport':is_reimport}]
            write('post-factory-chain.json',live)
        except Exception as exc:
            errors.append('post_factory: '+str(exc));write('post-factory-error.json',{'error':str(exc)})

    @unreal.ufunction(override=True)
    def scripted_execute_post_import_pipeline(self,base_node_container,factory_node_key,created_asset,is_reimport):
        try:
            if created_asset.get_path_name()!=config['copy_path'] or factory_node_key!=root_uid or is_reimport:
                raise RuntimeError('PostImport identity escaped exact fresh import')
            capture(base_node_container,factory_node_key,'post_import_job',created_asset)
            current=actual_chain(base_node_container,factory_node_key,created_asset)
            if live is None or current!={k:v for k,v in live.items() if k!='boundaries'}:raise RuntimeError('Same-job post-import chain changed')
            live['boundaries'].append({'phase':'post_import','container_path':base_node_container.get_path_name(),'asset_path':created_asset.get_path_name(),'is_reimport':is_reimport})
            write('import-live-chain.json',live)
        except Exception as exc:
            errors.append('post_import: '+str(exc));write('post-import-error.json',{'error':str(exc)})

def on_done(objects):
    global done,imported_paths,import_native
    imported_paths=[obj.get_path_name() for obj in objects]
    try:
        if imported_paths!=[config['copy_path']]:raise RuntimeError('Unexpected fresh import completion outputs')
        copy_metadata('completed_new_asset_metadata')
        if live is None or len(live['boundaries'])!=2:raise RuntimeError('Actual import-time boundaries incomplete')
        import_native=json.loads(unreal.DaedalusImportedFactorReadLibrary.read_fresh_imported_factor_current(config['copy_path'],config['destination']))
        write('import-native-current.json',import_native)
        if import_native.get('state')!='complete' or import_native.get('errors'):raise RuntimeError('Import-time native current witness held')
    except Exception as exc:errors.append('completion: '+str(exc))
    done=True
    write('import-terminal.json',{'done':True,'paths':imported_paths,'events':events,'errors':errors,'source_sha256':config['source_sha256']})
