# SPDX-License-Identifier: MIT
"""Finish the known returned rack import; never imports or multiplies scale.

The first task stored .01 build settings but left source-sized render bounds.
Apply those exact existing settings through the installed editor API, read back
the result, then save only this owned mesh if its full source contract passes.
"""
import json
from pathlib import Path
import sys
import time
import unreal

LABEL='Codex known ServerRack apply stored build settings and save'
PATH='/Game/Daedalus/Art/Islands/CodexContest/Ingestion/ServerRack_873c11e011876c80/Prop_Sims_Server_Rack.Prop_Sims_Server_Rack'


def steps(cfg,original):
    journal=Path(cfg['journal'])
    if journal.exists():raise RuntimeError('known completion journal exists; inspect, never replay')
    b=sys.modules['claude_unreal_bridge']
    others=[req.get('type') for gen,req,box in b._running if req.get('type')!='daedalus.steps' or (req.get('params') or {}).get('label')!=LABEL]
    if others or b._jobs.qsize() or b._remote_lock.locked():raise RuntimeError('conflicting bridge operation')
    dirty_map=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    dirty_content=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    if dirty_map or dirty_content!=[PATH.split('.')[0]]:raise RuntimeError('only known owned imported rack may be dirty')
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE running')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()!='/Game/Daedalus/DaedalusWorld.DaedalusWorld':raise RuntimeError('wrong editor map')
    if time.time()>cfg['deadline_epoch']-90:raise RuntimeError('current sole-operator lease deadline reached')
    eal=unreal.EditorAssetLibrary;mesh=eal.load_asset(PATH)
    if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('known imported rack missing')
    subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    settings=subsystem.get_lod_build_settings(mesh,0)
    scale=[getattr(settings.build_scale3d,axis) for axis in ('x','y','z')]
    if any(abs(v-.01)>.000001 for v in scale) or settings.generate_lightmap_u_vs:raise RuntimeError('known stored build settings differ')
    box=mesh.get_bounding_box()
    before={edge:[getattr(getattr(box,edge),axis) for axis in ('x','y','z')] for edge in ('min','max')}
    if before!=cfg['known_bounds']:raise RuntimeError('imported bounds changed since readback; inspect before completion')
    colours=original['_colours'](mesh)
    report={'stage':'apply_existing_build_settings_pending','native_path':PATH,'bounds_before_cm':before,
        'existing_absolute_build_scale3d':scale,'scale_multiplied':False,'import_repeated':False,
        'vertex_colours_before':colours,'world_placed':0,'save_return':None}
    original['_write'](journal,report)
    started=time.perf_counter()
    subsystem.set_lod_build_settings(mesh,0,settings)
    report.update(stage='existing_build_settings_apply_returned',apply_s=round(time.perf_counter()-started,6))
    box=mesh.get_bounding_box()
    report['native_bounds_cm']={edge:[getattr(getattr(box,edge),axis) for axis in ('x','y','z')] for edge in ('min','max')}
    lo,hi=report['native_bounds_cm']['min'],report['native_bounds_cm']['max']
    report['native_dimensions_cm']=[hi[i]-lo[i] for i in range(3)]
    original['_write'](journal,report)
    if any(abs(a-b)>.1 for a,b in zip(sorted(report['native_dimensions_cm']),[50.,60.,180.])) or abs(lo[2])>.1:
        raise RuntimeError('stored build-setting application did not establish unit contract; hold unsaved')
    report['vertex_colours']=original['_colours'](mesh)
    if report['vertex_colours']!=colours:raise RuntimeError('existing-settings application changed source colours')
    report['nanite_enabled']=bool(mesh.get_editor_property('nanite_settings').enabled)
    report['simple_collision_count']=subsystem.get_simple_collision_count(mesh)
    if report['nanite_enabled']:raise RuntimeError('Nanite unexpectedly enabled')
    slots=mesh.get_editor_property('static_materials')
    if len(slots)!=1:raise RuntimeError('one source material slot required')
    material=eal.load_asset(original['MATERIAL'])
    if not isinstance(material,unreal.MaterialInterface):raise RuntimeError('existing shared material missing')
    mesh.modify();mesh.set_material(0,material)
    for key,value in {'codex_owner':'codex-contest','codex_sha256':original['FBX_SHA'],
            'codex_unit_boundary':'existing absolute LOD build_scale3d=.01 applied once; actor scale1',
            'codex_author':'historical author unverified; retained Claude source recipe matches',
            'codex_world_placement':'held; native appearance/collision/integration unverified'}.items():eal.set_metadata_tag(mesh,key,value)
    report.update(stage='save_dispatch_pending',slots=[{'slot':str(slots[0].material_slot_name),'material':mesh.get_material(0).get_path_name()}])
    original['_write'](journal,report)
    started=time.perf_counter();report['save_return']=bool(eal.save_loaded_asset(mesh,only_if_is_dirty=False))
    report.update(save_s=round(time.perf_counter()-started,6),stage='asset_saved_world_held' if report['save_return'] else 'save_returned_false')
    original['_write'](journal,report)
    if report['save_return'] is not True:raise RuntimeError('owned rack save returned false')
    yield PATH
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('unexpected dirty packages after save')
    return report
