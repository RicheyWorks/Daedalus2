# SPDX-License-Identifier: MIT
"""One retained rack, asset-only, using the existing AssetImportTask pattern.

No actors, materials, map saves, shared settings or source FBX are changed.
The installed Interchange stack exposes the one required build-scale boundary.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

import unreal

FBX_SHA='873c11e011876c80d4680a666c4fc397265cc4bb3b80542df83ddff4b04ad6a1'
NAME='Prop_Sims_Server_Rack'
DEST='/Game/Daedalus/Art/Islands/CodexContest/Ingestion/ServerRack_'+FBX_SHA[:16]
MATERIAL='/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour'
SOURCE_RGBA={(108,108,114,255),(224,226,230,255),(148,249,186,255),(255,224,148,255)}
LABEL='Codex retained ServerRack unit and vertex-colour import-save'


def _write(path,value):
    Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def _preflight():
    bridge=sys.modules['claude_unreal_bridge']
    others=[req.get('type') for gen,req,box in bridge._running
            if req.get('type')!='daedalus.steps' or (req.get('params') or {}).get('label')!=LABEL]
    if others or bridge._jobs.qsize() or bridge._remote_lock.locked():raise RuntimeError('conflicting bridge operation; preserve work')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('dirty packages; preserve work')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()!='/Game/Daedalus/DaedalusWorld.DaedalusWorld':
        raise RuntimeError('agreed editor map required')
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE running')


def _colours(mesh):
    """Read every source triangle's split colours on a transient DynamicMesh."""
    dynamic=unreal.DynamicMesh()
    options=unreal.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('use_build_scale',True)
    lod=unreal.GeometryScriptMeshReadLOD()
    copied=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,dynamic,options,lod)
    if isinstance(copied,tuple):dynamic=copied[0]
    if dynamic.get_triangle_count()!=174:raise RuntimeError('rack source triangle count differs')
    unique=set()
    for triangle in range(174):
        row=dynamic.get_triangle_vertex_colors(triangle)
        if len(row)!=5 or row[-1] is not True:raise RuntimeError('native triangle colour readback incomplete')
        colours=[tuple(round(getattr(colour,key),7) for key in ('r','g','b','a')) for colour in row[1:4]]
        if len(set(colours))!=1:raise RuntimeError('source flat face colour changed')
        unique.update(colours)
    direct={tuple(round(value*255) for value in colour) for colour in unique}
    def encode(value):return 12.92*value if value<=.0031308 else 1.055*value**(1/2.4)-.055
    srgb={tuple(round(encode(value)*255) for value in colour[:3])+(round(colour[3]*255),) for colour in unique}
    match='direct_rgba_bytes' if direct==SOURCE_RGBA else 'linear_to_srgb_rgba_bytes' if srgb==SOURCE_RGBA else None
    if match is None:raise RuntimeError('native four-colour set differs from source; inspect before saving')
    return {'triangles':174,'unique_rgba':sorted(unique),'direct_rgba_bytes':sorted(direct),
            'linear_to_srgb_rgba_bytes':sorted(srgb),'source_match':match,'persistent_mesh_modified':False}


def steps(cfg):
    journal=Path(cfg['journal'])
    if journal.exists():raise RuntimeError('retained native journal exists; inspect, never replay')
    raw=Path(cfg['fbx']).read_bytes()
    if len(raw)!=16428 or hashlib.sha256(raw).hexdigest()!=FBX_SHA:raise RuntimeError('exact retained rack FBX required')
    _preflight()
    if time.time()>cfg['deadline_epoch']-90:raise RuntimeError('delivery lease deadline reached before admission')
    eal=unreal.EditorAssetLibrary
    if eal.does_directory_exist(DEST) or eal.does_asset_exist(DEST+'/'+NAME):raise RuntimeError('destination exists; no overwrite')
    material=eal.load_asset(MATERIAL)
    if not isinstance(material,unreal.MaterialInterface):raise RuntimeError('existing shared material missing')
    # Same explicit Interchange stack pattern as the installed Claude importer;
    # local task only. Correct unit100 at build time once; actor scale stays one.
    pipeline=unreal.InterchangeGenericAssetsPipeline()
    mesh_options=pipeline.get_editor_property('mesh_pipeline')
    for key,value in {'build_nanite':False,'generate_lightmap_u_vs':False,'collision':False,
                      'build_scale3d':unreal.Vector(.01,.01,.01)}.items():mesh_options.set_editor_property(key,value)
    common=pipeline.get_editor_property('common_meshes_properties')
    common.set_editor_property('vertex_color_import_option',unreal.InterchangeVertexColorImportOption.IVCIO_REPLACE)
    common.set_editor_property('bake_meshes',True)
    pipeline.get_editor_property('material_pipeline').set_editor_property('import_materials',False)
    stack=unreal.InterchangePipelineStackOverride();stack.add_pipeline(pipeline)
    task=unreal.AssetImportTask();task.filename=cfg['fbx'];task.destination_path=DEST
    task.destination_name=NAME;task.automated=True;task.replace_existing=False;task.save=False;task.options=stack
    report={'schema':'daedalus.codex-existing-rack-native.v1','stage':'import_dispatch_pending',
            'source_fbx_sha256':FBX_SHA,'source_bytes':16428,'destination':DEST,'world_placed':0,
            'requested_options':{'backend':'explicit_InterchangePipelineStackOverride','build_scale3d':[.01,.01,.01],
                'vertex_colors':'REPLACE','bake_meshes':True,'build_nanite':False,'generate_lightmap_u_vs':False,
                'collision':False,'import_materials':False,'replace_existing':False},'save_return':None}
    _write(journal,report)
    started=time.perf_counter();unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    report.update(stage='import_returned',import_s=round(time.perf_counter()-started,6),
                  imported_object_paths=[str(path) for path in task.imported_object_paths]);_write(journal,report)
    paths=eal.list_assets(DEST,recursive=True,include_folder=False)
    meshes=[eal.load_asset(path) for path in paths]
    if len(meshes)!=1 or not isinstance(meshes[0],unreal.StaticMesh) or meshes[0].get_name()!=NAME:
        raise RuntimeError('exact one named rack StaticMesh required; inspect import_returned journal')
    mesh=meshes[0];box=mesh.get_bounding_box()
    bounds={edge:[getattr(getattr(box,edge),axis) for axis in ('x','y','z')] for edge in ('min','max')}
    dims=[bounds['max'][i]-bounds['min'][i] for i in range(3)]
    report.update(native_path=mesh.get_path_name(),native_bounds_cm=bounds,native_dimensions_cm=dims,
        import_data_class=mesh.get_editor_property('asset_import_data').get_class().get_name(),
        nanite_enabled=bool(mesh.get_editor_property('nanite_settings').enabled))
    _write(journal,report)
    if any(abs(a-b)>.1 for a,b in zip(sorted(dims),[50.,60.,180.])) or abs(bounds['min'][2])>.1:
        raise RuntimeError('actual unit/pivot contract differs; inspect import, do not rescale twice')
    if report['nanite_enabled'] is not False:raise RuntimeError('Nanite observed enabled; hold unsaved import')
    build=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0)
    report['observed_build_scale3d']=[getattr(build.build_scale3d,axis) for axis in ('x','y','z')]
    report['observed_generate_lightmap_u_vs']=bool(build.generate_lightmap_u_vs)
    report['simple_collision_count']=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_simple_collision_count(mesh)
    if any(abs(value-.01)>.000001 for value in report['observed_build_scale3d']) or report['observed_generate_lightmap_u_vs']:
        raise RuntimeError('observed task build-scale/lightmap-UV contract differs')
    report['vertex_colours']=_colours(mesh)
    slots=mesh.get_editor_property('static_materials')
    if len(slots)!=1:raise RuntimeError('rack one-material source contract differs')
    mesh.modify();mesh.set_material(0,material)
    for key,value in {'codex_owner':'codex-contest','codex_sha256':FBX_SHA,'codex_unit_boundary':'Interchange build_scale3d=.01 exactly once',
                      'codex_author':'historical author unverified; retained Claude source recipe matches',
                      'codex_world_placement':'held; native appearance/collision/integration unverified'}.items():eal.set_metadata_tag(mesh,key,value)
    report.update(stage='save_dispatch_pending',slots=[{'slot':str(slots[0].material_slot_name),'material':mesh.get_material(0).get_path_name()}])
    _write(journal,report)
    started=time.perf_counter();report['save_return']=bool(eal.save_loaded_asset(mesh,only_if_is_dirty=False))
    report['save_s']=round(time.perf_counter()-started,6)
    report['stage']='asset_saved_world_held' if report['save_return'] else 'save_returned_false'
    _write(journal,report)
    if report['save_return'] is not True:raise RuntimeError('rack save returned false')
    yield report['native_path']
    _preflight()
    return report
