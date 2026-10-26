"""Owned-level placement, called only during a verified editor grant.

Imports are handled by the existing art queue. This module never imports/replaces art,
deletes existing actors, starts Play, patches the harness, or saves unrelated levels.
"""
import datetime
import json
import math
import pathlib

SUBLEVEL = '/Game/Codex/SolIsland/Maps/SolIsland'
TAG = 'SOL_ISLAND_V1'

def layout(assets):
    kinds = list(dict.fromkeys(a['archetype'] for a in assets))
    rows=[]
    for a in assets:
        group=kinds.index(a['archetype']); v=a['variant']-1
        x=(group%4-1.5)*40+(v%5-2)*3
        y=(group//4-2)*40+(v//5-2)*3
        if math.hypot(x,y)+4 > 120: raise ValueError('asset outside island')
        rows.append({'asset':a['asset'],'kind':a['kind'],'archetype':a['archetype'],
                     'position_cm':[2000000+x*100,y*100,1000]})
    return rows

def adventure_layout(assets):
    positions={'ShadowGuideStone':[1999400,-1600,1000],
               'BrokenRingMural':[1994000,-8600,1000],
               'HiddenCisternStair':[1999800,-1600,1000],
               'Keeper':[1993400,-8300,1000], 'KeeperHearth':[1997400,-3900,1000]}
    if len(assets)!=5 or {a['archetype'] for a in assets}!=set(positions):
        raise ValueError('Need the exact five-piece adventure kit')
    return [{**{k:a[k] for k in ('asset','kind','archetype')},
             'position_cm':positions[a['archetype']]} for a in assets]

def build(manifest_path, grant, adventure_manifest_path=None):
    import unreal
    now=datetime.datetime.now(datetime.timezone.utc)
    start=datetime.datetime.fromisoformat(grant['start_utc']); end=datetime.datetime.fromisoformat(grant['end_utc'])
    if start.tzinfo is None or end.tzinfo is None or not start<=now<end:
        raise RuntimeError('No current editor grant')
    if grant['team']!='team-codex' or not grant['handoff_id'] or not grant['watcher_held']:
        raise RuntimeError('Exact owner handoff and held watcher required')
    if (end-start).total_seconds()>1200: raise ValueError('Turn cannot exceed 20 minutes')
    engine=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world=engine.get_editor_world()
    if unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()).replace('\\','/').rstrip('/').lower()!='c:/unreal/daedalusrealm':
        raise RuntimeError('Wrong project')
    if world.get_name()!='DaedalusWorld' or engine.get_game_world() is not None:
        raise RuntimeError('Require DaedalusWorld and Play stopped')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if any(a.actor_has_tag(TAG) for a in actors.get_all_level_actors()):
        raise RuntimeError('Owned actors already exist: inspect before resume')
    assets=json.loads(pathlib.Path(manifest_path).read_text())['assets']
    plan=layout(assets)
    if adventure_manifest_path:
        kit=json.loads(pathlib.Path(adventure_manifest_path).read_text())['assets']
        plan.extend(adventure_layout(kit))
    loaded=[]
    for row in plan:
        base=f"/Game/Daedalus/Art/{row['kind']}/{row['asset']}"
        candidates=unreal.EditorAssetLibrary.list_assets(base,recursive=True)
        meshes=[unreal.EditorAssetLibrary.load_asset(p) for p in candidates]
        meshes=[m for m in meshes if isinstance(m,unreal.StaticMesh)]
        if len(meshes)!=1: raise RuntimeError('Need exactly one imported mesh: '+row['asset'])
        loaded.append(meshes[0])
    if (end-datetime.datetime.now(datetime.timezone.utc)).total_seconds()<180:
        raise RuntimeError('Keep three minutes for placement/save/handoff')
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    previous=levels.get_current_level()
    if unreal.EditorAssetLibrary.does_asset_exist(SUBLEVEL):
        raise RuntimeError('Owned sublevel exists: inspect before resume')
    unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,SUBLEVEL,False)
    if levels.get_current_level().get_outer().get_name()!='SolIsland':
        levels.set_current_level_by_name('SolIsland')
    if levels.get_current_level().get_outer().get_name()!='SolIsland': raise RuntimeError('Owned level not current')
    owned=levels.get_current_level()
    saved=False
    try:
        ground=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(2000000,0,600))
        ground.static_mesh_component.set_static_mesh(unreal.EditorAssetLibrary.load_asset('/Engine/BasicShapes/Cylinder'))
        ground.set_actor_scale3d(unreal.Vector(240,240,8))
        ground.set_actor_label('SOL_Island_Ground'); ground.tags=[TAG]
        for row,mesh in zip(plan,loaded):
            if (end-datetime.datetime.now(datetime.timezone.utc)).total_seconds()<60:
                raise RuntimeError('Handoff reserve reached; partial owned level saved for inspection')
            actor=actors.spawn_actor_from_object(mesh,unreal.Vector(*row['position_cm']),
                                                unreal.Rotator(pitch=0,yaw=0,roll=0))
            if actor is None: raise RuntimeError('Spawn failed: '+row['asset'])
            actor.set_actor_label(row['asset']); actor.set_folder_path('Codex/SolIsland/'+row['archetype'])
            actor.tags=[TAG,row['archetype']]
    finally:
        try:
            if levels.get_current_level()==owned: saved=bool(levels.save_current_level())
        finally:
            levels.set_current_level_by_name(previous.get_outer().get_name())
    observed=[a for a in actors.get_all_level_actors() if a.actor_has_tag(TAG)]
    if not saved or len(observed)!=len(plan)+1: raise RuntimeError('Owned save/count verification failed')
    return {'saved':saved,'placed_assets':len(plan),'support_ground':1,'sublevel':SUBLEVEL,
            'play_started':False,'gameplay_integrated':False,
            'parent_streaming_reference_needs_owner_save':True}

if __name__=='__main__':
    import sys
    manifest=json.loads(pathlib.Path(sys.argv[1]).read_text())
    result=layout(manifest['assets'])
    dest=pathlib.Path(sys.argv[1]).parent/'layout.json'
    dest.write_text(json.dumps(result,indent=2))
    print('Prepared',len(result),'owned placements:',dest)
