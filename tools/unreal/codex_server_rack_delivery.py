# SPDX-License-Identifier: MIT
"""Prepare, save and read back the exact existing server rack, without placement."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from codex_aetherflow_delivery import BASE,MAP_FILE,editor,load,write_new
from codex_contest_island_delivery import fingerprint
from codex_editor_handoff import _asset_file,_witness,wire
from codex_palette_variant_delivery import protected,BASELINE as PRIOR_BASELINE
from codex_aetherflow_readback import _native_code

ROOT=Path(__file__).resolve().parents[2]
FOLDER=BASE/'ServerRackR1'
SOURCE=ROOT/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_server_rack.py'
ORIGINAL=Path('C:/Users/730ri/projects/D2-build/engines/unreal/art/claude-sims/Prop_Sims_Server_Rack.fbx')
FBX_SHA='873c11e011876c80d4680a666c4fc397265cc4bb3b80542df83ddff4b04ad6a1'
LABEL='Codex retained ServerRack unit and vertex-colour import-save'
PALETTE=BASE/'PaletteVariants/HeroR3/Native91011/readback.json'
FINISH=SOURCE.with_name('daedalus_codex_server_rack_finish.py')
PIPELINE_UNITS=SOURCE.with_name('daedalus_codex_server_rack_pipeline_units.py')


def protection():
    prior=load(PRIOR_BASELINE);protected(prior)
    palette=load(PALETTE)
    if palette.get('issues')!=[] or palette.get('verified_saved_mesh_files')!=95:raise ValueError('completed95mesh baseline required')
    receipt=load(palette['native_receipt'])
    for path,value in receipt['outputs'].items():
        if fingerprint(_asset_file(path))!=value:raise RuntimeError('prior palette output changed')
    local=prior['local'];local['disk_static_meshes'].update(receipt['outputs'])
    return palette,local


def prepare():
    if fingerprint(ORIGINAL)!={'sha256':FBX_SHA,'bytes':16428}:raise ValueError('original FBX differs')
    FOLDER.mkdir(exist_ok=True)
    if (FOLDER/'prepared.json').exists():raise RuntimeError('retain preparation')
    target=FOLDER/ORIGINAL.name
    with target.open('xb') as handle:handle.write(ORIGINAL.read_bytes())
    resolution=BASE/'codex-server-rack-source-resolution-2330.json'
    write_new(FOLDER/'prepared.json',{'stage':'existing_rack_prepared_asset_only','fbx':str(target),'fbx_fingerprint':fingerprint(target),
        'source_resolution':str(resolution),'source_resolution_fingerprint':fingerprint(resolution),
        'source_module':str(SOURCE),'source_module_fingerprint':fingerprint(SOURCE),
        'unit_contract':'60x50x180cm; explicit per-task Interchange build_scale3d=.01 once, native bounds required',
        'colour_contract':'exact four source RGBA; all174 native triangles read before save',
        'world_placement':'held; no authored UCX/native appearance/app integration acceptance'})
    print(json.dumps(load(FOLDER/'prepared.json'),indent=2))


def ingest():
    prepared=load(FOLDER/'prepared.json');baseline,local=protection();editor()
    for field in ('fbx','source_resolution','source_module'):
        if fingerprint(prepared[field])!=prepared[field+'_fingerprint']:raise ValueError('prepared witness changed: '+field)
    lease=json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks',timeout=10)).get('unreal',{})
    if lease.get('holder')!='codex-play-guard' or lease.get('at',0)+lease.get('ttl',0)-time.time()<180:
        raise RuntimeError('current sole-operator lease required')
    dispatch=FOLDER/'dispatch.json'
    if dispatch.exists():raise RuntimeError('retain prior dispatch; inspect outcome before any replay')
    cfg={'fbx':prepared['fbx'],'journal':str(FOLDER/'native.json'),'deadline_epoch':min(time.time()+600,lease['at']+lease['ttl']-60)}
    code='''from pathlib import Path
import hashlib
source=SOURCE
raw=Path(source).read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('owned rack module changed')
scope={'__name__':'_codex_existing_rack_delivery'}
exec(compile(raw,source,'exec'),scope)
def steps():
    return (yield from scope['steps'](CONFIG))
'''.replace('SOURCE',repr(str(SOURCE)),1).replace('EXPECTED',repr(prepared['source_module_fingerprint']['sha256']),1).replace('CONFIG',repr(cfg),1)
    write_new(dispatch,{'stage':'native_dispatch_pending','code_sha256':hashlib.sha256(code.encode()).hexdigest(),
        'prepared_fingerprint':fingerprint(FOLDER/'prepared.json'),'map_before':fingerprint(MAP_FILE)})
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=code,label=LABEL,budget_ms=1,timeout=180,side='Unreal')
    write_new(FOLDER/'reply.json',reply)
    value=load(dispatch);value.update(stage='native_returned_inspect_before_replay',reply_fingerprint=fingerprint(FOLDER/'reply.json'))
    dispatch.write_text(json.dumps(value,indent=2)+'\n')
    if reply.get('error'):raise RuntimeError('inspect retained native journal/reply; never replay import blindly')
    native=load(FOLDER/'native.json')
    if native.get('stage')!='asset_saved_world_held' or native.get('save_return') is not True:raise RuntimeError('native save not confirmed')
    value.update(stage='one_rack_saved_world_held',native_path=native['native_path'],output_fingerprint=fingerprint(_asset_file(native['native_path'])))
    dispatch.write_text(json.dumps(value,indent=2)+'\n');protection();editor()
    if fingerprint(MAP_FILE)!=value['map_before']:raise RuntimeError('unexpected map change')
    print(json.dumps(native,indent=2))


def finish(pipeline_units=False):
    prepared=load(FOLDER/'prepared.json');protection();editor()
    initial=load(FOLDER/'native.json');known=load(FOLDER/'known-import-readback.json');basis=load(FOLDER/'build-basis-readback.json')
    if initial.get('stage')!='import_returned' or initial.get('save_return') is not None or known.get('save_called') is not False:
        raise RuntimeError('exact known returned unsaved import required')
    if known['build_scale3d']!=[.01,.01,.01] or known['native_bounds_cm']!=initial['native_bounds_cm']:
        raise RuntimeError('known stored scale/bounds differs')
    if basis['build_basis']['True']['bounds_cm']['max'][2]!=180.:raise RuntimeError('source with stored scale does not establish180cm intention')
    for field in ('fbx','source_resolution','source_module'):
        if fingerprint(prepared[field])!=prepared[field+'_fingerprint']:raise ValueError('original prepared witness changed')
    lease=json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks',timeout=10)).get('unreal',{})
    if lease.get('holder')!='codex-play-guard' or lease.get('at',0)+lease.get('ttl',0)-time.time()<180:raise RuntimeError('current sole-operator lease required')
    if pipeline_units:
        failed=load(FOLDER/'finished-native.json');fresh=load(FOLDER/'after-build-tick-readback.json')
        if failed.get('stage')!='existing_build_settings_apply_returned' or failed.get('save_return') is not None or fresh.get('save_called') is not False:
            raise RuntimeError('exact known unsaved completion and fresh read required')
        if fresh['native_bounds_cm']!=known['native_bounds_cm']:raise RuntimeError('raw native bounds no longer match known import')
    stem='pipeline-units' if pipeline_units else 'finish'
    dispatch=FOLDER/(stem+'-dispatch.json')
    if dispatch.exists():raise RuntimeError('retain known-completion dispatch; inspect before replay')
    cfg={'journal':str(FOLDER/('pipeline-units-native.json' if pipeline_units else 'finished-native.json')),'known_bounds':known['native_bounds_cm'],
         'deadline_epoch':min(time.time()+600,lease['at']+lease['ttl']-60)}
    sources=[{'path':str(path),'fingerprint':fingerprint(path)} for path in (SOURCE,PIPELINE_UNITS if pipeline_units else FINISH)]
    code='''from pathlib import Path
import hashlib
scopes=[]
for item in SOURCES:
    raw=Path(item['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=item['fingerprint']['sha256']:raise RuntimeError('known completion source changed')
    scope={'__name__':'_codex_known_rack_completion'}
    exec(compile(raw,item['path'],'exec'),scope);scopes.append(scope)
def steps():
    return (yield from scopes[1]['steps'](CONFIG,scopes[0]))
'''.replace('SOURCES',repr(sources),1).replace('CONFIG',repr(cfg),1)
    write_new(dispatch,{'stage':'known_completion_dispatch_pending','sources':sources,'map_before':fingerprint(MAP_FILE),
        'known_import_fingerprint':fingerprint(FOLDER/'known-import-readback.json'),'build_basis_fingerprint':fingerprint(FOLDER/'build-basis-readback.json')})
    label='Codex known ServerRack existing pipeline unit contract save' if pipeline_units else 'Codex known ServerRack apply stored build settings and save'
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=code,label=label,budget_ms=1,timeout=180,side='Unreal')
    write_new(FOLDER/(stem+'-reply.json'),reply)
    if reply.get('error'):raise RuntimeError('inspect retained known-completion journal and reply; no replay')
    native=load(cfg['journal'])
    if native.get('stage')!='asset_saved_world_held' or native.get('save_return') is not True:raise RuntimeError('rack save not confirmed')
    value=load(dispatch);value.update(stage='one_rack_saved_world_held',native_path=native['native_path'],output_fingerprint=fingerprint(_asset_file(native['native_path'])))
    dispatch.write_text(json.dumps(value,indent=2)+'\n');protection();editor()
    if fingerprint(MAP_FILE)!=value['map_before']:raise RuntimeError('unexpected map change')
    print(json.dumps(native,indent=2))


def readback():
    baseline,local=protection();editor()
    pipeline_units=(FOLDER/'pipeline-units-dispatch.json').is_file();finished=(FOLDER/'finish-dispatch.json').is_file()
    dispatch=load(FOLDER/('pipeline-units-dispatch.json' if pipeline_units else 'finish-dispatch.json' if finished else 'dispatch.json'))
    native=load(FOLDER/('pipeline-units-native.json' if pipeline_units else 'finished-native.json' if finished else 'native.json'))
    if dispatch['stage']!='one_rack_saved_world_held':raise ValueError('completed save required')
    path=dispatch['native_path']
    if fingerprint(_asset_file(path))!=dispatch['output_fingerprint']:raise RuntimeError('saved rack bytes changed')
    local['disk_static_meshes'][path]=dispatch['output_fingerprint']
    code=_native_code(local)+'''\nmesh=unreal.EditorAssetLibrary.load_asset(RACK)
box=mesh.get_bounding_box()
result['rack_bounds_cm']={edge:[getattr(getattr(box,edge),axis) for axis in ('x','y','z')] for edge in ('min','max')}
result['rack_material']=mesh.get_material(0).get_path_name()
build=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0)
result['rack_build_scale3d']=[getattr(build.build_scale3d,a) for a in ('x','y','z')]
result['rack_unit_contract']=unreal.EditorAssetLibrary.get_metadata_tag(mesh,'codex_unit_contract')
result['rack_required_actor_scale']=unreal.EditorAssetLibrary.get_metadata_tag(mesh,'codex_required_actor_scale')
result['rack_world_references']=[a.get_path_name() for a in all_actors if a.get_component_by_class(unreal.StaticMeshComponent) and a.get_component_by_class(unreal.StaticMeshComponent).get_editor_property('static_mesh')==mesh]
'''.replace('RACK',repr(path))
    result=wire.obj(wire.call(wire.UNREAL,'execute_python',code=code,unattended=False,timeout=90,side='Unreal'),side='Unreal',what='saved rack and preserved95asset scene readback')
    issues=[];observed={r['label']:r for r in result['actors']}
    if len(observed)!=89 or result['all_level_actor_count']!=baseline['native_readback']['all_level_actor_count']:issues.append('prior actor count changed')
    for row in baseline['native_readback']['actors']:
        if any(observed.get(row['label'],{}).get(field)!=row[field] for field in ('actor','mesh_path','transform','materials','override_materials','folder','tags')):
            issues.append('prior actor changed: '+row['label'])
    classes=result['saved_asset_classes']
    if set(classes)!=set(local['disk_static_meshes']) or len(classes)!=96 or any(r.get('is_static_mesh') is not True for r in classes.values()):issues.append('96mesh path/class set differs')
    if result['rack_bounds_cm']!=native['native_bounds_cm'] or result['rack_material']!=native['slots'][0]['material']:issues.append('rack saved bounds/material differs')
    if pipeline_units and (result['rack_build_scale3d']!=[1.,1.,1.] or result['rack_unit_contract']!='claude_raw_unit100_build1_actor001_v1' or result['rack_required_actor_scale']!='0.01,0.01,0.01'):
        issues.append('saved raw unit/build1/required actor scale contract differs')
    if result['rack_world_references'] or result['dirty_map_packages'] or result['dirty_content_packages']:issues.append('world hold/clean packages differs')
    protection();editor()
    if fingerprint(_asset_file(path))!=dispatch['output_fingerprint']:issues.append('new rack file changed')
    map_unchanged=fingerprint(MAP_FILE)==dispatch['map_before']
    if not map_unchanged:issues.append('saved map bytes changed')
    write_new(FOLDER/'readback.json',{'stage':'rack_asset_only_readback_complete' if not issues else 'inspection_required','issues':issues,
        'native_readback':result,'new_saved_mesh_files':1,'verified_saved_mesh_files':96,'measured_actor_rows':89,'world_placed':0,
        'native_path':path,'save_return':True,'output_fingerprint':dispatch['output_fingerprint'],'map_fingerprint':fingerprint(MAP_FILE),
        'unit_contract':'claude_raw_unit100_build1_actor001_v1' if pipeline_units else 'requested_asset_scaled_contract',
        'required_future_actor_scale':[.01,.01,.01] if pipeline_units else [1.,1.,1.],
        'map_unchanged':map_unchanged,'native_palette_appearance':'unverified; vertex data readback is not a screenshot',
        'collision_app_runtime':'unverified; no UCX/worldplacement/Play/tests'})
    print(json.dumps({'issues':issues,'verified_saved_mesh_files':96,'measured_actor_rows':89,'new_saved_mesh_files':1,'map_unchanged':True},indent=2))
    if issues:raise RuntimeError('inspect readback before continuing')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('prepare','ingest','finish','pipeline-units','readback'))
    args=parser.parse_args()
    if args.stage=='pipeline-units':finish(pipeline_units=True)
    else:globals()[args.stage]()
