# SPDX-License-Identifier: MIT
"""Save the known rack using Claude's existing asset/actor unit boundary.

Retain raw native asset dimensions, absolute build scale1 and REQUIRED future
actor scale.01. This exact contract is held from the scale1 island placer.
No import, source-geometry transform or world operation occurs here.
"""
from pathlib import Path
import sys
import time
import unreal

LABEL='Codex known ServerRack existing pipeline unit contract save'
PATH='/Game/Daedalus/Art/Islands/CodexContest/Ingestion/ServerRack_873c11e011876c80/Prop_Sims_Server_Rack.Prop_Sims_Server_Rack'


def steps(cfg,original):
    journal=Path(cfg['journal'])
    if journal.exists():raise RuntimeError('pipeline unit completion journal exists; inspect, never replay')
    bridge=sys.modules['claude_unreal_bridge']
    others=[req.get('type') for gen,req,box in bridge._running if req.get('type')!='daedalus.steps' or (req.get('params') or {}).get('label')!=LABEL]
    if others or bridge._jobs.qsize() or bridge._remote_lock.locked():raise RuntimeError('conflicting bridge operation')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('dirty map; preserve work')
    if [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]!=[PATH.split('.')[0]]:
        raise RuntimeError('only known owned rack may be dirty')
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE running')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()!='/Game/Daedalus/DaedalusWorld.DaedalusWorld':raise RuntimeError('wrong map')
    if time.time()>cfg['deadline_epoch']-90:raise RuntimeError('lease deadline reached')
    eal=unreal.EditorAssetLibrary;mesh=eal.load_asset(PATH)
    subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    settings=subsystem.get_lod_build_settings(mesh,0)
    if any(abs(getattr(settings.build_scale3d,a)-.01)>.000001 for a in ('x','y','z')):raise RuntimeError('known prior settings differ')
    box=mesh.get_bounding_box()
    before={edge:[getattr(getattr(box,edge),a) for a in ('x','y','z')] for edge in ('min','max')}
    if before!=cfg['known_bounds']:raise RuntimeError('known raw bounds changed')
    report={'stage':'restore_absolute_build_scale1_pending','native_path':PATH,'prior_absolute_build_scale':[.01,.01,.01],
        'required_future_actor_scale':[.01,.01,.01],'world_placement':'held; incompatible with existing scale1 island placement helpers',
        'import_repeated':False,'geometry_transformed':False,'world_placed':0,'save_return':None}
    original['_write'](journal,report)
    settings.build_scale3d=unreal.Vector(1,1,1)
    started=time.perf_counter();subsystem.set_lod_build_settings(mesh,0,settings)
    report.update(stage='absolute_build_scale1_set_returned',apply_s=round(time.perf_counter()-started,6))
    original['_write'](journal,report)
    yield 'absolute build_scale1 returned; no import or actor operation'
    build=subsystem.get_lod_build_settings(mesh,0)
    report['observed_build_scale3d']=[getattr(build.build_scale3d,a) for a in ('x','y','z')]
    report['observed_generate_lightmap_u_vs']=bool(build.generate_lightmap_u_vs)
    box=mesh.get_bounding_box()
    report['native_bounds_cm']={edge:[getattr(getattr(box,edge),a) for a in ('x','y','z')] for edge in ('min','max')}
    lo,hi=report['native_bounds_cm']['min'],report['native_bounds_cm']['max']
    report['native_dimensions_cm']=[hi[i]-lo[i] for i in range(3)]
    report['projected_dimensions_cm_at_required_actor_scale']=[value*.01 for value in report['native_dimensions_cm']]
    dynamic=unreal.DynamicMesh();options=unreal.GeometryScriptCopyMeshFromAssetOptions();options.use_build_scale=True
    dynamic,outcome=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,dynamic,options,unreal.GeometryScriptMeshReadLOD())
    points=[]
    for triangle in range(dynamic.get_triangle_count()):
        valid,*vertices=dynamic.get_triangle_positions(triangle)
        if not valid:raise RuntimeError('invalid native source triangle')
        points.extend([[getattr(vertex,a) for a in ('x','y','z')] for vertex in vertices])
    report['native_source_bounds_with_build_scale']={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
    report['vertex_colours']=original['_colours'](mesh)
    report['nanite_enabled']=bool(mesh.get_editor_property('nanite_settings').enabled)
    report['simple_collision_count']=subsystem.get_simple_collision_count(mesh)
    original['_write'](journal,report)
    if (report['observed_build_scale3d']!=[1.,1.,1.] or report['observed_generate_lightmap_u_vs'] or report['nanite_enabled'] or
        any(abs(a-b)>.1 for a,b in zip(sorted(report['native_dimensions_cm']),[5000.,6000.,18000.])) or abs(lo[2])>.1 or
        any(abs(report['native_source_bounds_with_build_scale'][edge][i]-report['native_bounds_cm'][edge][i])>.1 for edge in ('min','max') for i in range(3))):
        raise RuntimeError('exact raw asset/build1/source-colour unit contract differs; hold unsaved')
    slots=mesh.get_editor_property('static_materials');material=eal.load_asset(original['MATERIAL'])
    if len(slots)!=1 or not isinstance(material,unreal.MaterialInterface):raise RuntimeError('shared material/source slot missing')
    mesh.modify();mesh.set_material(0,material)
    tags={'codex_owner':'codex-contest','codex_sha256':original['FBX_SHA'],
        'codex_unit_contract':'claude_raw_unit100_build1_actor001_v1',
        'codex_required_actor_scale':'0.01,0.01,0.01','codex_intended_dimensions_cm':'60,50,180',
        'codex_author':'historical author unverified; current retained Claude recipe exactly matches',
        'codex_world_placement':'held; scale1 island helper incompatible; appearance/collision/integration unverified'}
    for key,value in tags.items():eal.set_metadata_tag(mesh,key,value)
    report.update(stage='save_dispatch_pending',metadata=tags,slots=[{'slot':str(slots[0].material_slot_name),'material':mesh.get_material(0).get_path_name()}])
    original['_write'](journal,report)
    started=time.perf_counter();report['save_return']=bool(eal.save_loaded_asset(mesh,only_if_is_dirty=False))
    report.update(save_s=round(time.perf_counter()-started,6),stage='asset_saved_world_held' if report['save_return'] else 'save_returned_false')
    original['_write'](journal,report)
    if report['save_return'] is not True:raise RuntimeError('rack save returned false')
    yield PATH
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('unexpected dirty packages after asset save')
    return report
