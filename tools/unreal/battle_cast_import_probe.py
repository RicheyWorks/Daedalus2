"""Run inside a private Unreal editor process against copied imported cast assets.

CAST_PROBE_INPUT points to an external-art hash manifest; CAST_PROBE_OUTPUT is the
result file. No assets/maps are saved and the shared editor is never contacted.
"""
import hashlib
import json
import os
from pathlib import Path
import unreal

manifest=json.loads(Path(os.environ['CAST_PROBE_INPUT']).read_text(encoding='utf-8'))
content=Path(unreal.Paths.project_content_dir())
for relative,digest in manifest['files'].items():
    if hashlib.sha256((content/relative).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('Imported art hash mismatch: '+relative)
registry=unreal.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(['/Game/Daedalus/Art/Cast'],True)
unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
stage=actors.spawn_actor_from_class(unreal.DaedalusBattlePresentation,unreal.Vector())
rows=[]
try:
    for asset_id in manifest['cast_ids']:
        package=manifest['mesh_packages'][asset_id]
        mesh=unreal.load_asset(package)
        if not isinstance(mesh,unreal.SkeletalMesh):
            raise RuntimeError('Missing imported skeletal mesh: '+asset_id)
        actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
        try:
            component=actor.get_editor_property('skeletal_mesh_component')
            component.set_skeletal_mesh_asset(mesh)
            found={}
            for role,hurt in [('Attack',False),('Hurt',True)]:
                expected=unreal.load_asset(package+role)
                actual=stage.resolve_cast_animation(actor,hurt)
                if not isinstance(expected,unreal.AnimSequence) or actual!=expected:
                    raise RuntimeError('Imported clip binding mismatch: '+asset_id+'/'+role)
                found[role]=actual.get_path_name()
            rows.append({'id':asset_id,'mesh':mesh.get_path_name(),'clips':found})
        finally:
            actors.destroy_actor(actor)
    if not rows:raise RuntimeError('No imported cast models checked')
    proof={'scope':'Actual copied imported mesh and Attack/Hurt selection through native stage API. No rendered battle or playback claim.',
           'verified':rows,'art_file_count':len(manifest['files']),
           'input_manifest_sha256':hashlib.sha256(Path(os.environ['CAST_PROBE_INPUT']).read_bytes()).hexdigest(),
           'maps_or_assets_saved':False,'shared_editor_contacted':False}
    Path(os.environ['CAST_PROBE_OUTPUT']).write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    unreal.log('BATTLE_IMPORTED_CAST_PASS '+str(len(rows)))
finally:
    actors.destroy_actor(stage)
