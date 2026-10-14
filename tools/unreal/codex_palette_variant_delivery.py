# SPDX-License-Identifier: MIT
"""Save the exact retained palette91011 export through the proven PR146 route.

Asset-only delivery: no actor/material/map mutation, no generator, no tests.
The original source experiment and its world-placement/collision limits remain.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from codex_aetherflow_delivery import BASE, MAP, MAP_FILE, REVIEW, editor, load, write_new
from codex_contest_island_delivery import fingerprint
from codex_retained_revision_manifest import PALETTE_CONFIG, PALETTE_REVISION, PALETTE_ROLES, prepare as prepare_manifest
import codex_reviewed_ingestion as runner
from codex_aetherflow_readback import _native_code
from codex_editor_handoff import _asset_file, _witness, wire

NAME=PALETTE_REVISION
SOURCE=BASE/'PaletteVariants/HeroR3/p91011'/ (NAME+'.receipt.json')
FOLDER=BASE/'PaletteVariants/HeroR3/Native91011'
MANIFEST=FOLDER/'codex-palette-p91011.delivery.json'
BASELINE=BASE/'codex-aetherflow-final.native.json'
KEY='palette-p91011'
FP={
 'fbx':{'bytes':1581836,'sha256':'81f6e75d2995fe7a30b10319433de96ade41062157140149c5068aa21fe8678a'},
 'glb':{'bytes':6075480,'sha256':'d57da19df24817d7ae08d4a66b93b7db4049eff94dabb178bca03fdde290ce2f'}}


def source_contract():
    source=load(SOURCE)
    digest=hashlib.sha256(json.dumps(source['config'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
    if (source.get('schema')!='daedalus.codex-palette-variant.v1' or source.get('stage')!='exported' or
        source.get('name')!=NAME or source.get('config_sha256')!=PALETTE_CONFIG or digest!=PALETTE_CONFIG or
        source.get('geometry_and_transforms_unchanged') is not True):raise ValueError('exact retained unchanged-geometry palette91011 export required')
    for kind,row in source['artifacts'].items():
        if fingerprint(row['path'])!=row['fingerprint'] or kind in FP and row['fingerprint']!=FP[kind]:
            raise ValueError('retained source artifact changed: '+kind)
    config=source['config']
    if fingerprint(config['source_glb']['path'])!=config['source_glb']['fingerprint'] or fingerprint(config['source_receipt'])['sha256']!=config['source_receipt_sha256']:
        raise ValueError('retained original HeroR3 geometry/receipt changed')
    objects=source['blender']['objects']
    if len(objects)!=10 or {row['name'] for row in objects}!={NAME+'_'+role for role in PALETTE_ROLES}:
        raise ValueError('exact ten palette role names required')
    views=[BASE/'PaletteVariants/HeroR3/QA91011'/(kind+'.png') for kind in ('overview','route','crown')]
    if any(not path.is_file() for path in views):raise ValueError('retained reviewed source views missing')
    return source,{str(path):fingerprint(path) for path in [SOURCE,*views]}


def protected(baseline):
    for path,value in baseline['local']['protected_files'].items():
        if fingerprint(path)!=_witness(value):raise RuntimeError('protected prior production file changed: '+path)
    for path,value in baseline['local']['disk_static_meshes'].items():
        if fingerprint(_asset_file(path))!=_witness(value):raise RuntimeError('prior saved mesh bytes changed: '+path)
    if fingerprint(MAP_FILE)!=_witness(baseline['map_after_readback']):raise RuntimeError('current map differs from saved89actor baseline')


def prepare():
    source,views=source_contract()
    FOLDER.mkdir(exist_ok=True)
    if (FOLDER/'prepared.json').exists():raise RuntimeError('retain completed preparation; do not replace journal')
    result=prepare_manifest(BASE/'codex-prepared.delivery.json',SOURCE,MANIFEST)
    write_new(FOLDER/'prepared.json',{'stage':'ten_existing_meshes_prepared_asset_only','manifest':result,
        'source_receipt':str(SOURCE),'source_receipt_fingerprint':fingerprint(SOURCE),'source_review_witnesses':views,
        'source_commit':'05736b02ccc4427b95350d5f1d608695aef23f74','personally_inspected_source_views':3,
        'world_placement':'held; no authored UCX and no native palette appearance acceptance',
        'native_palette':'existing importer assigns shared material; source palette recipe retained for future component overrides'})
    print(json.dumps(result,indent=2))


def ingest():
    source_contract();prepared=load(FOLDER/'prepared.json');baseline=load(BASELINE)
    if baseline.get('issues')!=[] or baseline.get('measured_actor_rows')!=89 or baseline.get('verified_saved_mesh_files')!=85:
        raise ValueError('require exact completed89actor/85mesh clean baseline')
    if fingerprint(MANIFEST)['sha256']!=prepared['manifest']['output_sha256'] or fingerprint(SOURCE)!=prepared['source_receipt_fingerprint']:
        raise ValueError('prepared manifest/source receipt changed')
    for path,value in prepared['source_review_witnesses'].items():
        if fingerprint(path)!=value:raise ValueError('reviewed source bytes changed')
    protected(baseline)
    lease=json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks',timeout=10)).get('unreal',{})
    deadline=min(time.time()+900,lease.get('at',0)+lease.get('ttl',0)-60)
    if lease.get('holder')!='codex-play-guard' or deadline<time.time()+180:raise RuntimeError('current sole-operator lease required')
    dispatch=FOLDER/'dispatch.json'
    if dispatch.exists():raise RuntimeError('inspect prior dispatch outcome before any replay')
    editor()
    write_new(dispatch,{'stage':'native_import_dispatch_pending','manifest_fingerprint':fingerprint(MANIFEST),
                        'baseline':str(BASELINE),'baseline_fingerprint':fingerprint(BASELINE),'deadline_epoch':deadline})
    # Register only this exact immutable host candidate in the existing runner;
    # the importer/receipt module bytes and their guards are unchanged.
    runner.CANDIDATES[KEY]=(NAME,MANIFEST)
    try:reply=runner.run(KEY,REVIEW,deadline,prepared['manifest']['output_sha256'])
    except Exception as error:
        value=load(dispatch);value.update(stage='native_outcome_inspection_required',error=str(error))
        dispatch.write_text(json.dumps(value,indent=2)+'\n');raise
    adoption=load(BASE/'codex-palette-p91011.adoption.json')
    result=adoption['passes'][0]['results']
    if len(result)!=1 or result[0]['state']!='saved':raise RuntimeError('require one completed saved admission')
    native_path=Path('C:/Unreal/DaedalusRealm/Saved/Daedalus/Ingestion/CodexContest/receipts')/Path(result[0]['receipt']).name
    receipt=load(native_path)
    if receipt.get('state')!='saved' or receipt.get('save_confirmed') is not True or len(receipt['outputs'])!=10:
        raise RuntimeError('ten native mesh saves not confirmed; inspect prior dispatch')
    if receipt['name']!=NAME or receipt['manifest']['settings']['config_sha256']!=PALETTE_CONFIG:
        raise RuntimeError('saved admission identity differs')
    for path,value in receipt['outputs'].items():
        if fingerprint(_asset_file(path))!=value:raise RuntimeError('new saved mesh differs: '+path)
    copied=FOLDER/native_path.name
    with copied.open('xb') as handle:handle.write(native_path.read_bytes())
    protected(baseline);source_contract()
    value=load(dispatch);value.update(stage='ten_meshes_saved_world_held',native_receipt=str(copied),
        native_receipt_fingerprint=fingerprint(copied),assets=receipt['assets'],map_unchanged=True,world_placed=0,
        new_saved_mesh_files=10,total_expected_saved_mesh_files=95,total_expected_staging_actors=89)
    dispatch.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'stage':value['stage'],'assets':value['assets'],'passes':adoption['passes'],'map_unchanged':True},indent=2))


def readback():
    source,views=source_contract();dispatch=load(FOLDER/'dispatch.json');baseline=load(BASELINE)
    if dispatch.get('stage')!='ten_meshes_saved_world_held':raise ValueError('completed ten-asset dispatch required')
    if fingerprint(dispatch['native_receipt'])!=dispatch['native_receipt_fingerprint']:raise ValueError('native receipt changed')
    receipt=load(dispatch['native_receipt']);protected(baseline);editor()
    def new_outputs_unchanged():
        for path,value in receipt['outputs'].items():
            if fingerprint(_asset_file(path))!=value:raise RuntimeError('new saved mesh bytes changed: '+path)
    new_outputs_unchanged()
    local=copy.deepcopy(baseline['local']);local['disk_static_meshes'].update(receipt['outputs'])
    paths=list(receipt['outputs'])
    code=_native_code(local)+'''\nresult['palette91011_bounds_cm']={}
result['palette91011_asset_slots']={}
new_paths=PATHS
for path in new_paths:
    mesh=unreal.EditorAssetLibrary.load_asset(path);box=mesh.get_bounding_box()
    result['palette91011_bounds_cm'][path]={edge:[getattr(getattr(box,edge),axis) for axis in ('x','y','z')] for edge in ('min','max')}
    result['palette91011_asset_slots'][path]=[{'slot':str(slot.material_slot_name),'material':slot.material_interface.get_path_name() if slot.material_interface else None} for slot in mesh.get_editor_property('static_materials')]
result['palette91011_world_references']=[]
for actor in all_actors:
    component=actor.get_component_by_class(unreal.StaticMeshComponent)
    mesh=component.get_editor_property('static_mesh') if component else None
    if mesh and mesh.get_path_name() in new_paths:result['palette91011_world_references'].append(actor.get_path_name())
'''.replace('PATHS',repr(paths))
    reply=wire.call(wire.UNREAL,'execute_python',code=code,unattended=False,timeout=90,side='Unreal')
    native=wire.obj(reply,side='Unreal',what='palette91011 saved asset and prior scene readback')
    issues=[];observed={row['label']:row for row in native['actors']}
    if len(observed)!=89 or native['all_level_actor_count']!=baseline['native_readback']['all_level_actor_count']:
        issues.append('prior scene actor set/count differs')
    for row in baseline['native_readback']['actors']:
        if any(observed.get(row['label'],{}).get(field)!=row[field] for field in ('actor','mesh_path','transform','materials','override_materials','folder','tags')):
            issues.append('prior actor state differs: '+row['label'])
    classes=native['saved_asset_classes']
    if len(classes)!=95 or set(classes)!=set(local['disk_static_meshes']) or any(row.get('is_static_mesh') is not True for row in classes.values()):
        issues.append('saved95 mesh class/path set differs')
    for obj in source['blender']['objects']:
        path=receipt['assets'][obj['name']]
        box=native['palette91011_bounds_cm'][path]
        actual=sorted([box['max'][i]-box['min'][i] for i in range(3)])
        expected=sorted(value*100 for value in obj['dims'])
        if any(abs(a-b)>max(1.,.01*b) for a,b in zip(actual,expected)):issues.append('saved native dimensions differ: '+obj['name'])
        slots=native['palette91011_asset_slots'][path]
        if (len(slots)!=len(obj['materials']) or {row['slot'] for row in slots}!=set(obj['materials']) or
            any(row['material']!='/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.M_VoxelVertexColour' for row in slots)):
            issues.append('source slot/shared material contract differs: '+obj['name'])
    if native['palette91011_world_references'] or native['dirty_map_packages'] or native['dirty_content_packages']:
        issues.append('world hold or clean-package state differs')
    protected(baseline);new_outputs_unchanged();source_contract();editor()
    result={'schema':'daedalus.palette-variant-asset-delivery-readback.v1','stage':'asset_only_delivery_readback_complete' if not issues else 'inspection_required',
        'issues':issues,'source_receipt':str(SOURCE),'source_receipt_fingerprint':fingerprint(SOURCE),'source_review_witnesses':views,
        'dispatch':str(FOLDER/'dispatch.json'),'dispatch_fingerprint':fingerprint(FOLDER/'dispatch.json'),
        'native_receipt':dispatch['native_receipt'],'native_receipt_fingerprint':dispatch['native_receipt_fingerprint'],
        'native_readback':native,'new_saved_mesh_files':10,'verified_saved_mesh_files':95,'measured_actor_rows':89,
        'map_unchanged':True,'map_fingerprint':fingerprint(MAP_FILE),'world_placed':0,
        'native_palette_appearance':'unverified; importer-shared material unchanged; source-specific sRGB palette/surface recipe retained for future component overrides',
        'collision_navigation_bar':'unverified; no authored UCX in this recolour export','tests':'deferred_by_user'}
    write_new(FOLDER/'readback.json',result)
    print(json.dumps({key:result[key] for key in ('stage','issues','new_saved_mesh_files','verified_saved_mesh_files','measured_actor_rows','map_unchanged','world_placed')},indent=2))
    if issues:raise RuntimeError('inspect retained asset-only readback before another delivery')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('prepare','ingest','readback'))
    args=parser.parse_args();globals()[args.stage]()
