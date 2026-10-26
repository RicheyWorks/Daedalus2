# Explicit host-owned callbacks; never run outside the existing protected route.
# Required: unreal, sys, json, Path, before, snapshot/qualify/record, HOST_CONFIG,
# POLICY_SOURCE/POLICY_PATH. No production actor/graph mutation or map save.
import types,datetime

def install_fixture_state():
    alias='_codex_private_pcg_fixture_20261021_r1'
    if alias in sys.modules:raise RuntimeError('Retained PCG attempt; reconcile, no replay')
    state=types.ModuleType(alias);sys.modules[alias]=state
    policy=types.ModuleType('_codex_private_pcg_policy_r1');exec(compile(POLICY_SOURCE,POLICY_PATH,'exec'),policy.__dict__)
    state.policy=policy;state.config=HOST_CONFIG;state.baseline=before;state.round=0;state.events=[];state.errors=[];state.actor=None;state.component=None;state.graph=None
    def original_pcg():
        component=unreal.find_object(None,'/Game/Daedalus/DaedalusWorld.DaedalusWorld:PersistentLevel.PCGVolume_4.PCG Component',follow_redirectors=False)
        if component is None:raise RuntimeError('Protected original PCG component absent')
        return {'path':component.get_path_name(),'graph':component.get_graph().get_path_name(),'seed':component.get_editor_property('seed'),'generated':component.get_editor_property('generated')}
    state.original_pcg=original_pcg;state.original_before=original_pcg()
    def event(kind,data):
        row={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':kind,'round':state.round,'data':data}
        state.events.append(row)
        with Path(state.config['journal']).open('a',encoding='utf-8') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
    state.event=event
    def on_generated(component):
        try:
            if component!=state.component:raise RuntimeError('Foreign PCG callback')
            state.callback_count+=1
            if state.callback_count!=1:raise RuntimeError('Repeated PCG generation callback')
            event('generated',{'component':component.get_path_name(),'callback_count':state.callback_count})
        except Exception as exc:state.errors.append(str(exc));event('callback_error',{'error':str(exc)})
    state.on_generated=on_generated
    return state


def prepare_graph(state):
    p=state.policy
    if unreal.EditorAssetLibrary.does_asset_exist(p.GRAPH.split('.')[0]):raise RuntimeError('Private graph destination occupied')
    willow=unreal.find_object(None,p.MESH,follow_redirectors=False)
    if willow is None:
        state.event('named_Blender_mesh_load_intent',{'asset':p.MESH});willow=unreal.load_asset(p.MESH)
    if willow is None or willow.get_path_name()!=p.MESH:raise RuntimeError('Exact Blender Willow unavailable')
    shape=unreal.load_asset('/Engine/BasicShapes/Cone.Cone')
    if shape is None:raise RuntimeError('Private descriptor baseline unavailable')
    graph=unreal.AssetToolsHelpers.get_asset_tools().create_asset('PCG_WillowFixture','/Game/CodexToolEvaluation/PCGMinimal/R1',unreal.PCGGraph,unreal.PCGGraphFactory())
    if graph is None or graph.get_path_name()!=p.GRAPH:raise RuntimeError('Exact private graph not created')
    state.graph=graph
    create,settings=graph.add_node_of_type(unreal.PCGCreatePointsSettings)
    points=[]
    for index,position in enumerate(p.POINTS):
        point=unreal.PCGPoint();point.set_editor_property('transform',unreal.Transform(unreal.Vector(*position),unreal.Rotator(0,0,0),unreal.Vector(1,1,1)));point.set_editor_property('seed',index+1);points.append(point)
    settings.set_editor_property('points_to_create',points);settings.set_editor_property('coordinate_space',unreal.PCGCoordinateSpace.WORLD)
    spawn,spawner=graph.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
    selector=spawner.get_editor_property('mesh_selector_parameters')
    if selector.get_class().get_path_name()!='/Script/PCG.PCGMeshSelectorWeighted':raise RuntimeError('Unexpected selector type')
    entry=unreal.PCGMeshSelectorWeightedEntry();descriptor=entry.get_editor_property('descriptor')
    descriptor.set_editor_property('static_mesh',shape);entry.set_editor_property('descriptor',descriptor);entry.set_editor_property('weight',1)
    selector.set_editor_property('mesh_entries',[entry])
    state.event('private_descriptor_change_intent',{'selector':selector.get_path_name(),'entry_index':0,'before':shape.get_path_name(),'after':p.MESH,'soft_read':'Explicit own entry current target/dependencies admitted'})
    entries=list(selector.get_editor_property('mesh_entries'));entry=entries[0];descriptor=entry.get_editor_property('descriptor')
    if descriptor.get_editor_property('static_mesh')!=shape or entry.get_editor_property('weight')!=1:raise RuntimeError('Private baseline descriptor mismatch')
    descriptor.set_editor_property('static_mesh',willow);entry.set_editor_property('descriptor',descriptor);selector.set_editor_property('mesh_entries',[entry])
    graph.add_edge(create,'Out',spawn,'In');graph.add_edge(spawn,'Out',graph.get_output_node(),'Out')
    return graph


def start_round(state,graph,fresh_snapshot,fresh_qualify):
    if state.round>=2:raise RuntimeError('Two-generation fixture bound consumed')
    if not callable(fresh_snapshot) or not callable(fresh_qualify):raise RuntimeError('Current callback guards required')
    if state.actor is not None or state.component is not None:raise RuntimeError('Previous fixture still retained')
    library=unreal.DaedalusPCGFixtureOwnerLibrary
    state.event('create_fixture_intent',{'round':state.round+1})
    created=json.loads(library.create_owned_fixture());state.owner_receipt=created
    if created.get('ok') is not True:raise RuntimeError('Native fixture refused: '+str(created))
    actor=unreal.find_object(None,created['actor_path'],follow_redirectors=False);component=unreal.find_object(None,created['component_path'],follow_redirectors=False)
    state.actor=actor;state.component=component
    duplicate=json.loads(library.create_owned_fixture())
    if duplicate.get('ok') is not False:raise RuntimeError('Native duplicate fixture was not refused')
    state.duplicate_refused=True
    if actor is None or component is None or component.get_owner()!=actor:raise RuntimeError('Exact owned fixture binding failed')
    if component.get_editor_property('seed')!=state.policy.SEED:raise RuntimeError('Actual owned component seed differs')
    # Standard per-component preview mode makes generated ISMs transient. This
    # affects only this new fixture, not project settings or production owners.
    component.set_editing_mode(unreal.PCGEditorDirtyMode.PREVIEW,unreal.PCGEditorDirtyMode.PREVIEW)
    if component.get_editing_mode()!=unreal.PCGEditorDirtyMode.PREVIEW:raise RuntimeError('Owned preview mode not observed')
    state.round+=1;state.callback_count=0
    component.on_pcg_graph_generated_external.add_callable_unique(state.on_generated)
    component.set_graph(graph)
    if state.callback_count:raise RuntimeError('Unexpected implicit generation during graph binding; no explicit replay')
    state.graph=graph
    fresh=fresh_snapshot();fresh_qualify(fresh)
    for field in ('project','world','pie','game_world','dirty_maps','scene','selection','camera'):
        if fresh[field]!=state.baseline[field]:raise RuntimeError('Protected state changed before generation: '+field)
    state.event('generate_local_intent',{'graph':graph.get_path_name(),'component':component.get_path_name(),'seed':component.get_editor_property('seed'),'local_only':True})
    component.generate_local(True)
    state.event('generate_local_returned',{'completion_not_inferred':True})
    return {'dispatched':True,'completed':False,'round':state.round,'owner':created,'duplicate_refused':True}


def collect_round(state):
    if state.errors or state.callback_count!=1:raise RuntimeError('Actual unique generation callback absent/errors: '+str(state.errors))
    component=state.component;actor=state.actor;live=json.loads(unreal.DaedalusPCGFixtureOwnerLibrary.describe_owned_fixture())
    if live.get('ok') is not True or live.get('busy') is not False:raise RuntimeError('Owned component not known idle')
    instances=[]
    components=list(actor.get_components_by_class(unreal.InstancedStaticMeshComponent))
    if len(components)>4:raise RuntimeError('Unexpected generated component count')
    for ism in components:
        mesh=ism.get_editor_property('static_mesh');count=ism.get_instance_count()
        if count>3:raise RuntimeError('Unexpected instance count')
        for index in range(count):
            transform=ism.get_instance_transform(index,world_space=True);position=transform.translation;rotation=transform.rotation;scale=transform.scale3d
            instances.append({'mesh':mesh.get_path_name(),'position':[position.x,position.y,position.z],'quaternion_xyzw':[rotation.x,rotation.y,rotation.z,rotation.w],'scale':[scale.x,scale.y,scale.z]})
    receipt={'graph':component.get_graph().get_path_name(),'mesh':state.policy.MESH,'seed':component.get_editor_property('seed'),'callback_count':state.callback_count,
             'generated':component.get_editor_property('generated'),'busy':live['busy'],'instances':instances,'round':state.round,'duplicate_fixture_refused':state.duplicate_refused,'mode':'Owned per-component preview, generated ISMs transient'}
    state.policy.qualify_output(receipt);return receipt


def remove_fixture(state):
    if state.component is None:raise RuntimeError('Exact owned component missing; no cleanup guess')
    state.component.on_pcg_graph_generated_external.remove_callable(state.on_generated)
    outcome=json.loads(unreal.DaedalusPCGFixtureOwnerLibrary.destroy_owned_fixture())
    state.event('fixture_cleanup',outcome)
    if outcome.get('ok') is not True:raise RuntimeError('Owned cleanup not accepted: '+str(outcome))
    state.actor=None;state.component=None
    return outcome
