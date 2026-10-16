# SPDX-License-Identifier: MIT
"""Closed Corn alias recovery: existing objects only, no importer branch.

No shared helper is edited. One original joined GLB, four exact first-save
packages, at most one decorative actor. A retained journal forbids replay.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import time
import unreal

ROOT='/Game/Daedalus/Art/SkyFarm/CornPolishR1'
MESH='Harvest3_CornPolish_R1'
SOURCE_MESH='Prop_Harvest3_Corn_Polish_R1'
MATERIALS=tuple('H3C_R1_AFTER_'+name for name in ('stalk','leaf','cob'))
NAMES=(MESH,)+MATERIALS
PATHS=tuple(ROOT+'/'+name+'.'+name for name in NAMES)
HELD=tuple('/Game/Daedalus/Art/SkyFarm/GreenhouseBayR1/'+name for name in ('SFG_R1_glass','SFG_R1_glass_glass'))
WORLD='/Game/Daedalus/DaedalusWorld.DaedalusWorld'
SUPPORT=WORLD+':PersistentLevel.DaedalusLandDistrict_215'
LABEL='Codex SkyFarm CornPolishR1 opaque intake33079'
MARKER='# Codex SkyFarm CornPolishR1 closed33079'
ACTOR='CodexSkyFarm_CornPolishR1_Decorative'
SOURCE_SHA='9925a5462ff97be7c69496c70453a7ff45ea268ea11583902f8dad0cc7301127'
MANIFEST_SHA='0411f227423f33fed0b8b625a1274fef435b1d0fb7369b413b609cd919031bb7'


def _pin(row):
    raw=Path(row['path']).read_bytes()
    if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('pinned input/helper changed')
    return raw


def _context(cfg):
    if os.getpid()!=42564:raise RuntimeError('bridge is not the exact retained editor42564')
    if cfg['source']['sha256']!=SOURCE_SHA or cfg['manifest']['sha256']!=MANIFEST_SHA:raise ValueError('exact accepted AFTER packet required')
    _pin(cfg['source']);_pin(cfg['manifest'])
    packet=json.loads(_pin(cfg['packet']))
    if (packet['mesh']['name']!=SOURCE_MESH or packet['mesh']['triangles']!=2592
            or [m['name'] for m in packet['materials']]!=list(MATERIALS)):
        raise ValueError('one original source node and exact three material roles required')
    scopes={}
    for key,row in cfg['helpers'].items():
        scope={'__name__':'_corn_private_'+key,'__file__':row['path']}
        exec(compile(_pin(row),row['path'],'exec'),scope);scopes[key]=scope
    scopes['inventory'].update(ROOT=ROOT,LABEL=LABEL)
    scopes['direct']['ROOT']=ROOT+'/'
    scopes['graph']['WITNESS_DIRECTORY']=cfg['witness_directory']
    scopes['farm']['FARM_MARKER']=MARKER
    e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world=e.get_editor_world();sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if world is None or world.get_path_name()!=WORLD:raise RuntimeError('existing production world differs')
    w={'__name__':'_corn_world','unreal':unreal,'math':math,'json':json,'hashlib':hashlib,'e':e,'world':world,'sub':sub}
    exec(compile(_pin(cfg['snap']),cfg['snap']['path'],'exec'),w)
    exec(compile(_pin(cfg['world_helper']),cfg['world_helper']['path'],'exec'),w)
    return packet,scopes,w,e,world,sub


def _file(path):
    if path not in PATHS:raise RuntimeError('foreign package path')
    return Path('C:/Unreal/DaedalusRealm/Content')/(path.split('.')[0].removeprefix('/Game/')+'.uasset')


def _guard(cfg,s,own=(),allow_map=False):
    s['farm']['_farm_guard'](cfg,{'catalogue':s['catalogue']},list(HELD)+[p.split('.')[0] for p in own],allow_map)
    content={p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if not set(HELD)<=content or content-set(HELD)-{p.split('.')[0] for p in own}:raise RuntimeError('exact held glass plus declared Corn dirty packages required')
    for path in HELD:
        if (Path('C:/Unreal/DaedalusRealm/Content')/(path.removeprefix('/Game/')+'.uasset')).exists():raise RuntimeError('held glass unexpectedly saved')
    return {'dirty_content':sorted(content),'dirty_maps':[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'pie':False}


def _scene(w):
    return {'scene':w['snapshot_scene'](),'world_digest':w['world_existing_actor_digest'](),
        'actor_paths':sorted(a.get_path_name() for a in w['_world_actors']()),
        'selection':sorted(a.get_path_name() for a in w['sub'].get_selected_level_actors())}


def _old(w,before,new=()):
    actors=w['_world_actors']();now={a.get_path_name():a for a in actors};old=set(before['actor_paths']);extra=set(new)
    if len(now)!=len(actors) or set(now)!=old|extra or old&extra:raise RuntimeError('exact old world plus at most declared actor required')
    original=w['_world_actors'];w['_world_actors']=lambda:[now[p] for p in sorted(old)]
    try:digest=w['world_existing_actor_digest']()
    finally:w['_world_actors']=original
    if digest!=before['world_digest']:raise RuntimeError('old actor/component world digest changed')
    scene=w['snapshot_scene']();prior={r['path']:r for r in before['scene']['actors']};current={r['path']:r for r in scene['actors']}
    if set(current)!=set(prior)|extra or any(current[p]!=r for p,r in prior.items()):raise RuntimeError('old152 selected records changed')
    if sorted(a.get_path_name() for a in w['sub'].get_selected_level_actors())!=before['selection']:raise RuntimeError('original selection changed')
    return {'scene':scene,'old_world_digest':digest,'old_actor_count':len(old),'new_actor_paths':sorted(extra)}


def _inspect(cfg,packet,s):
    objects=s['inventory']['_assets']()
    if set(objects)!=set(PATHS):raise RuntimeError('exact one mesh/three material allowlist required')
    mesh=objects[PATHS[0]]
    if mesh.get_class().get_path_name()!='/Script/Engine.StaticMesh':raise RuntimeError('exact StaticMesh class required')
    slots=list(mesh.get_editor_property('static_materials'))
    if len(slots)!=3 or [mesh.get_material(i).get_path_name() for i in range(3)]!=list(PATHS[1:]):raise RuntimeError('exact stalk/leaf/cob slot order required')
    geo=s['geometry']['_geometry'](mesh,packet['mesh'])
    build=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0)
    if geo['issues'] or geo['simple_collision_count']!=0 or build.recompute_normals:raise RuntimeError('geometry/options/source-normal preservation differs: '+json.dumps(geo))
    materials=[s['direct']['qualify'](objects[path],raw,s['graph']) for path,raw in zip(PATHS[1:],packet['materials'])]
    return {'paths':list(PATHS),'geometry':geo,'materials':materials,'slots':list(PATHS[1:]),
        'recompute_normals':bool(build.recompute_normals),'source_normals':'pinned source NORMAL retained; no recompute/normal repair'},objects


def _clear(w,anchor,bounds,excluded=()):
    half=[(bounds['max'][i]-bounds['min'][i])*.5 for i in (0,1)]
    center=[anchor[i]+(bounds['min'][i]+bounds['max'][i])*.5 for i in (0,1)]
    support=[]
    for dx,dy in ((0,0),(-half[0]-100,-half[1]-100),(-half[0]-100,half[1]+100),(half[0]+100,-half[1]-100),(half[0]+100,half[1]+100)):
        x,y=center[0]+dx,center[1]+dy;z=anchor[2]+bounds['min'][2]
        hit=unreal.SystemLibrary.line_trace_single(w['world'],unreal.Vector(x,y,z+25),unreal.Vector(x,y,z-25),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,True)
        t=hit.to_tuple() if hit is not None else None
        if (not t or len(t)!=18 or not t[0] or t[9] is None or t[10] is None or t[9].get_path_name()!=SUPPORT
                or t[10].get_path_name()!=SUPPORT+'.Ground' or t[13]!=0 or abs(float(t[5].z)-z)>.2 or float(t[7].z)<.999):
            return {'clear':False,'reason':'support/contact unavailable','center_xy':center}
        support.append({'xy':[x,y],'z':float(t[5].z),'actor':SUPPORT,'component':SUPPORT+'.Ground','instance':0})
    box=([anchor[0]+bounds['min'][0]-100,anchor[1]+bounds['min'][1]-100,z+.5],
         [anchor[0]+bounds['max'][0]+100,anchor[1]+bounds['max'][1]+100,anchor[2]+bounds['max'][2]+100])
    blockers=[];instances=0
    for actor in w['_world_actors']():
        if actor.get_path_name() in excluded:continue
        c,r=actor.get_actor_bounds(False)
        if not w['_intersects'](w['_center_box'](c,r),box):continue
        for comp in actor.get_components_by_class(unreal.PrimitiveComponent):
            if not w['_intersects'](w['_component_box'](comp),box):continue
            if isinstance(comp,unreal.InstancedStaticMeshComponent):
                mesh=comp.static_mesh
                if mesh is None:raise RuntimeError('unresolved overlapping ISM')
                b=mesh.get_bounding_box();local=w['_box'](w['_xyz'](b.min),w['_xyz'](b.max));count=comp.get_instance_count();scale=float(comp.get_editor_property('bounds_scale'))
                if type(count)is not int or count<0 or not math.isfinite(scale) or scale<0:raise RuntimeError('invalid actual ISM bounds')
                instances+=count
                if instances>100000:raise RuntimeError('bounded ISM clearance limit')
                for i in range(count):
                    actual=w['_transformed_box'](local,comp.get_instance_transform(i,world_space=True));center3=[(actual[0][k]+actual[1][k])*.5 for k in range(3)];radius=[(actual[1][k]-actual[0][k])*.5*max(1.,scale) for k in range(3)]
                    if w['_intersects'](([center3[k]-radius[k] for k in range(3)],[center3[k]+radius[k] for k in range(3)]),box):blockers.append({'actor':actor.get_path_name(),'component':comp.get_path_name(),'instance':i})
            else:blockers.append({'actor':actor.get_path_name(),'component':comp.get_path_name()})
    return {'clear':not blockers,'box_cm':box,'support':support,'blockers':blockers[:20],'blocker_count':len(blockers),'instances_examined':instances}


def _patch(cfg,s,w,bounds):
    supports=[a for a in w['_world_actors']() if a.get_path_name()==SUPPORT]
    farms=[a for a in w['_world_actors']() if a.get_actor_label().startswith('CodexSkyFarm_GreenhouseBayR1_')]
    if len(supports)!=1 or len(farms)!=7:return None,{'reason':'exact existing platform/greenhouse identity unavailable'}
    components=[c for c in supports[0].get_components_by_class(unreal.InstancedStaticMeshComponent) if c.get_path_name()==SUPPORT+'.Ground']
    if len(components)!=1 or components[0].get_instance_count()<1 or components[0].static_mesh is None:return None,{'reason':'platform instance unavailable'}
    comp=components[0];b=comp.static_mesh.get_bounding_box();local=w['_box'](w['_xyz'](b.min),w['_xyz'](b.max));platform=w['_transformed_box'](local,comp.get_instance_transform(0,world_space=True))
    boxes=[w['_center_box'](*a.get_actor_bounds(False)) for a in farms]
    lo=[min(b[0][i] for b in boxes) for i in range(3)];hi=[max(b[1][i] for b in boxes) for i in range(3)]
    mid=[(lo[i]+hi[i])*.5 for i in range(2)];half=[(bounds['max'][i]-bounds['min'][i])*.5 for i in range(2)]
    centres=[(lo[0]-half[0]-250,mid[1]),(hi[0]+half[0]+250,mid[1]),(mid[0],lo[1]-half[1]-250),(mid[0],hi[1]+half[1]+250)]
    attempts=[]
    for x,y in centres:
        _guard(cfg,s)
        if any(v-half[i]-100<platform[0][i] or v+half[i]+100>platform[1][i] for i,v in enumerate((x,y))):continue
        anchor=[x-(bounds['min'][0]+bounds['max'][0])*.5,y-(bounds['min'][1]+bounds['max'][1])*.5,platform[1][2]-bounds['min'][2]]
        proof=_clear(w,anchor,bounds);attempts.append(proof)
        if proof['clear']:return anchor,{'platform_bounds':platform,'greenhouse_bounds':[lo,hi],'attempts':attempts,'chosen':proof}
    return None,{'platform_bounds':platform,'greenhouse_bounds':[lo,hi],'attempts':attempts,'reason':'no proved free supported patch'}


def _actor(w,path,anchor):
    found=[a for a in w['_world_actors']() if a.get_path_name()==path]
    if len(found)!=1:raise RuntimeError('one owned actor required')
    a=found[0];c=a.static_mesh_component
    if (a.get_class().get_path_name()!='/Script/Engine.StaticMeshActor' or a.get_actor_label()!=ACTOR
            or str(a.get_folder_path())!='Codex/SkyFarm/CornPolishR1' or w['_xyz'](a.get_actor_location())!=anchor
            or w['_xyz'](a.get_actor_scale3d())!=[1.,1.,1.] or any(abs(float(getattr(a.get_actor_rotation(),k)))>1e-6 for k in ('pitch','yaw','roll'))
            or a.get_attach_parent_actor() is not None or a.get_actor_enable_collision() is not False
            or c.static_mesh.get_path_name()!=PATHS[0] or c.get_num_materials()!=3
            or [c.get_material(i).get_path_name() for i in range(3)]!=list(PATHS[1:])
            or c.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION or c.is_simulating_physics()
            or c.get_editor_property('can_ever_affect_navigation')):raise RuntimeError('new actor pose/material/decorative policy differs')
    return {'path':path,'label':ACTOR,'snapshot':w['snap'](a),'anchor_cm':anchor,'materials':list(PATHS[1:]),'collision':'NO_COLLISION','navigation':False}


def run(cfg):
    # The consumed import's exact known terminal is evidence, never replayed.
    original=json.loads(_pin(cfg['original_import']))
    if (cfg['original_import']['sha256']!='69d92bbfe85c5fab610bf003ebc9f2741ff909b199ec8d226844119860754878'
            or original.get('stage')!='CORN_KNOWN_TERMINAL_PARTIAL_HOLD'
            or original.get('error')!='exact four unsaved import outputs required'
            or len(original.get('intents',[]))!=1
            or original['intents'][0].get('operation')!='import_exact_after_glb_once'
            or original.get('saves')!=[] or original.get('new_actor')is not None
            or original.get('map_save_return')is not None
            or len(original.get('imported_object_paths',[]))!=4
            or set(original['imported_object_paths'])!=set(PATHS)):
        raise RuntimeError('exact consumed one-import/zero-save alias boundary required')
    packet,s,w,e,world,sub=_context(cfg);j=Path(cfg['journal'])
    if j.exists():raise RuntimeError('retained recovery journal; no replay')
    guard=_guard(cfg,s,PATHS)
    expected=set(HELD)|{p.split('.')[0] for p in PATHS}
    if set(guard['dirty_content'])!=expected:raise RuntimeError('exact six unsaved Corn/glass packages required')
    if any(_file(path).exists() for path in PATHS):raise RuntimeError('all four Corn first saves must be unattempted')
    before=_scene(w);prior=original['before']
    if (before['world_digest']!=prior['world_digest'] or before['actor_paths']!=prior['actor_paths']
            or before['selection']!=prior['selection']
            or {r['path']:r for r in before['scene']['actors']}!={r['path']:r for r in prior['scene']['actors']}
            or len(before['scene']['actors'])!=152):raise RuntimeError('original current world/152records/selection differ')
    if not s['farm']['_farm_camera_same'](s['farm']['_farm_camera'](e),cfg['original_camera']):raise RuntimeError('original camera differs')
    r={'stage':'CORN_REMAINING_EXISTING_OBJECTS_STARTED','before':before,'intents':[],'saves':[],
        'imported_object_paths':original['imported_object_paths'],'original_import':cfg['original_import'],
        'new_imports':0,'new_actor':None,'map_save_return':None,'replay_permitted':False}
    with j.open('x',encoding='utf-8') as stream:s['inventory']['_flush'](stream,r)
    def keep():s['inventory']['_write'](j,r)
    def intent(op,**fields):
        _guard(cfg,s,PATHS,allow_map=r['new_actor']is not None);r['intents'].append({'utc':s['farm']['_utc'](),'operation':op,**fields});keep()
    try:
        intent('qualify_existing_alias_no_import')
        r['qualified'],objects=_inspect(cfg,packet,s);keep()
        for path,obj in objects.items():
            intent('tag_only_new_corn',path=path)
            tags={'codex_owner':'codex-play-guard','codex_source_producer':'pootscoot','codex_source_glb_sha256':SOURCE_SHA,'codex_source_manifest_sha256':MANIFEST_SHA,'codex_source_role':obj.get_name(),'codex_unit_contract':'identity glTF XZY100 baked; actor scale1','codex_world_binding':'decorative placement only; source provenance anchor UNBOUND','codex_runtime_scope':'no harvest/navigation/realm/deed authority'}
            for k,v in tags.items():unreal.EditorAssetLibrary.set_metadata_tag(obj,k,v)
        for path in PATHS[1:]+PATHS[:1]:
            intent('first_save_only_declared_corn_package',path=path);started=time.perf_counter();saved=bool(unreal.EditorAssetLibrary.save_loaded_asset(objects[path],only_if_is_dirty=False));r['saves'].append({'path':path,'returned':saved,'seconds':time.perf_counter()-started});keep()
            if not saved or not _file(path).exists():raise RuntimeError('first package save unconfirmed; no replay')
        r['saved_readback'],objects=_inspect(cfg,packet,s);_guard(cfg,s);_old(w,before)
        box=objects[PATHS[0]].get_bounding_box();bounds={edge:w['_xyz'](getattr(box,edge)) for edge in ('min','max')}
        anchor,proof=_patch(cfg,s,w,bounds);r['placement_proof']=proof;keep()
        if anchor is None:
            r['preservation']=_old(w,before);r['post_guard']=_guard(cfg,s)
            r.update(stage='CORN_FOUR_ASSETS_SAVED_PLACEMENT_BLOCKED',known_terminal=True);keep();return r
        _old(w,before);intent('spawn_one_decorative_corn',anchor_cm=anchor)
        actor=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*anchor),unreal.Rotator(0,0,0))
        if actor is None:raise RuntimeError('spawn returned none; reconcile without retry')
        r['new_actor']=actor.get_path_name();r['anchor_cm']=anchor;keep();intent('configure_only_new_actor',path=r['new_actor'])
        actor.set_actor_label(ACTOR);actor.set_folder_path('Codex/SkyFarm/CornPolishR1');actor.set_actor_scale3d(unreal.Vector(1,1,1));actor.set_actor_enable_collision(False)
        comp=actor.static_mesh_component;comp.set_static_mesh(objects[PATHS[0]]);comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);comp.set_editor_property('can_ever_affect_navigation',False)
        r['actor_readback']=_actor(w,r['new_actor'],anchor);r['preservation']=_old(w,before,[r['new_actor']])
        r['post_place_clearance']=_clear(w,anchor,bounds,[r['new_actor']])
        if not r['post_place_clearance']['clear']:raise RuntimeError('post-place clearance differs')
        if not s['farm']['_farm_camera_same'](s['farm']['_farm_camera'](e),cfg['original_camera']):raise RuntimeError('camera changed before save')
        intent('one_targeted_map_save');started=time.perf_counter();r['map_save_return']=bool(unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Daedalus/DaedalusWorld'));r['map_save_seconds']=time.perf_counter()-started;keep()
        if r['map_save_return']is not True:raise RuntimeError('map save false; preserve partial without retry')
        r['post_guard']=_guard(cfg,s);r['actor_readback']=_actor(w,r['new_actor'],anchor);r['preservation']=_old(w,before,[r['new_actor']]);r.update(stage='CORN_FOUR_ASSETS_ONE_ACTOR_ONE_MAP_SAVED',known_terminal=True);keep();return r
    except Exception as exc:
        r.update(stage='CORN_KNOWN_TERMINAL_PARTIAL_HOLD',error=str(exc),error_type=type(exc).__name__,known_terminal=True);keep();return r


def readback(cfg):
    packet,s,w,e,world,sub=_context(cfg);r=json.loads(Path(cfg['journal']).read_text());_guard(cfg,s)
    if r['stage']!='CORN_FOUR_ASSETS_ONE_ACTOR_ONE_MAP_SAVED' or r['map_save_return']is not True:raise RuntimeError('exact completed saved Corn required')
    if not s['farm']['_farm_camera_same'](s['farm']['_farm_camera'](e),cfg['original_camera']):raise RuntimeError('original camera not restored')
    inspection,objects=_inspect(cfg,packet,s)
    return {'stage':'CORN_SAVED_INDEPENDENT_READBACK','inspection':inspection,'actor':_actor(w,r['new_actor'],r['anchor_cm']),
        'preservation':_old(w,r['before'],[r['new_actor']]),'guard':_guard(cfg,s),'native_mutations':0}


def camera(cfg,mode):
    packet,s,w,e,world,sub=_context(cfg);r=json.loads(Path(cfg['journal']).read_text());_guard(cfg,s)
    if r['stage']!='CORN_FOUR_ASSETS_ONE_ACTOR_ONE_MAP_SAVED':raise RuntimeError('saved one actor required before camera')
    _actor(w,r['new_actor'],r['anchor_cm']);_old(w,r['before'],[r['new_actor']]);j=Path(cfg['camera_journal'])
    if mode=='frame':
        if j.exists():raise RuntimeError('retained frame; no replay')
        original=s['farm']['_farm_camera'](e)
        if not s['farm']['_farm_camera_same'](original,cfg['original_camera']):raise RuntimeError('original camera differs')
        anchor=r['anchor_cm'];target={'location':[anchor[0]+1300,anchor[1]-2200,anchor[2]+1200],
            'rotation':[math.degrees(math.atan2(-1130,math.hypot(1300,2200))),math.degrees(math.atan2(2200,-1300)),0.]}
        value={'stage':'FRAME_INTENT','original':original,'target':target}
        with j.open('x',encoding='utf-8') as stream:s['inventory']['_flush'](stream,value)
    elif mode=='restore':
        value=json.loads(j.read_text())
        if value['stage']!='FRAMED' or not s['farm']['_farm_camera_same'](s['farm']['_farm_camera'](e),value['observed']):raise RuntimeError('owned frame uncertain/foreign camera; no forced restore')
        target=value['original'];value['stage']='RESTORE_INTENT';s['inventory']['_write'](j,value)
    else:raise ValueError('frame/restore only')
    _guard(cfg,s);e.set_level_viewport_camera_info(unreal.Vector(*target['location']),unreal.Rotator(pitch=target['rotation'][0],yaw=target['rotation'][1],roll=target['rotation'][2]))
    value['observed']=s['farm']['_farm_camera'](e)
    if not s['farm']['_farm_camera_same'](value['observed'],target):raise RuntimeError('camera write/readback differs; retain intent')
    _old(w,r['before'],[r['new_actor']]);_guard(cfg,s);value['stage']='FRAMED' if mode=='frame' else 'RESTORED';s['inventory']['_write'](j,value);return value
