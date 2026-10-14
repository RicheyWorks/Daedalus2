# SPDX-License-Identifier: MIT
"""Deliver only three retained reviewed Sol plants using the proven FBX route.

Original Sol GLBs and shared importer stay unchanged. Preparation, import/save,
owned PBR materials and additive placement are separate retained stages.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import urllib.request

from codex_contest_island_delivery import DEST, Mcp, SCENE, fingerprint, package
from codex_reviewed_ingestion import HEAD, HASHES, IMPORTER_SHA, NATIVE
from codex_saved_asset_assembly import execute_plan
from codex_admitted_asset_assembly import plan_admitted
from codex_workshop_terrain import _islands
from asset_pipeline import wire

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
FOLDER=BASE/'AetherflowR2'
KINDS=('ribbon_reeds','star_lilies','glasskelp')
NAMES=tuple('CodexAetherflow_'+kind+'_617024' for kind in KINDS)
MAP='/Game/Daedalus/DaedalusWorld'
MAP_FILE=Path('C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap')
REVIEW=Path('C:/Users/730ri/Documents/Codex/2026-10-13/task-3/ingestion-upgrade-audit/engines/unreal/DaedalusLink/Content/Python')
MATERIAL_SOURCE=ROOT/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_staging_palette.py'


def write_new(path,value):
    with path.open('x',encoding='utf-8') as handle:json.dump(value,handle,indent=2);handle.write('\n')


def load(path):return json.loads(Path(path).read_text())


def witness(value):return {key:value[key] for key in ('sha256','bytes')}


def source_contract():
    batch=load(FOLDER/'Aetherflow_Dropin_Receipt.json')
    if batch.get('stage')!='three_retained_fbx_exported' or batch.get('original_payloads_unchanged') is not True:
        raise ValueError('require completed unchanged-geometry source conversion')
    for row in batch['source_witnesses'].values():
        if fingerprint(row['path'])!=witness(row):raise ValueError('original source/review changed')
    if tuple(row['name'] for row in batch['artifacts'])!=NAMES:raise ValueError('exact three source identities required')
    receipts=[]
    for row in batch['artifacts']:
        for field in ('receipt','fbx'):
            if fingerprint(row[field]['path'])!=witness(row[field]):raise ValueError('retained conversion bytes changed')
        receipt=load(row['receipt']['path'])
        if receipt['preservation']['geometry_and_materials_preserved'] is not True:raise ValueError('conversion preservation missing')
        receipts.append(receipt)
    return batch,receipts


def prepare():
    batch,receipts=source_contract()
    original=BASE/'codex-prepared.delivery.json'
    manifest=load(original)
    configs={}
    for index,receipt in enumerate(receipts,3):
        config={'version':1,'seed':617024,'plant':receipt['plant'],'source_author':'SolUltra',
                'source_commit':receipt['source_commit'],'source_glb':witness(receipt['source_witnesses']['modules/Life_'+receipt['plant']+'.glb']),
                'converter':witness(batch['converter_source']),'waterline_local_z':0.0,
                'materials_linear_gltf':receipt['source_gltf_contract']['materials_linear_gltf']}
        digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        info=receipt['after_merge'];fbx=receipt['artifacts']['fbx']
        entry={'name':receipt['name'],'kind':'module','stage':'exported','seed':617024,'config_sha256':digest,
               'fbx':dict(path=fbx['path'],**witness(fbx['fingerprint'])),
               'destination':DEST+'/Prepared/module/'+fbx['fingerprint']['sha256'][:16],
               'objects':[{'name':receipt['name'],'dims':info['dimensions_metres'],'triangles':info['triangles'],'materials':info['material_slots']}],
               'world_placement':'held pending fresh native bounds/pond-footing readback'}
        manifest['assets'][index]=entry
        configs[receipt['name']]={'config':config,'config_sha256':digest,'source_receipt':str(FOLDER/(receipt['name']+'.receipt.json')),
                                  'source_receipt_fingerprint':fingerprint(FOLDER/(receipt['name']+'.receipt.json')),'entry':entry}
    target=FOLDER/'codex-aetherflow.delivery.json'
    manifest['aetherflow_scope']={'selected_names':list(NAMES),'original_manifest':str(original),
                                 'original_manifest_fingerprint':fingerprint(original),'other_context_entries_not_submitted':21}
    write_new(target,manifest)
    result={'schema':'daedalus.codex-aetherflow-native-inputs.v1','stage':'three_source_dropins_prepared',
            'prepared_manifest':str(target),'prepared_manifest_fingerprint':fingerprint(target),'candidates':configs,
            'source_batch':str(FOLDER/'Aetherflow_Dropin_Receipt.json'),'source_batch_fingerprint':fingerprint(FOLDER/'Aetherflow_Dropin_Receipt.json')}
    write_new(FOLDER/'native-inputs.json',result)
    print(json.dumps({'manifest':result['prepared_manifest_fingerprint'],'configs':{name:value['config_sha256'] for name,value in configs.items()}},indent=2))


def editor():
    mcp=Mcp(timeout=45)
    if mcp.call('EditorToolset.EditorAppToolset','IsPIERunning') is not False or package(mcp.call(SCENE,'get_current_level'))!=MAP:
        raise RuntimeError('require clean owned DaedalusWorld turn with PIE stopped')
    return mcp


def ingest():
    source_contract();inputs=load(FOLDER/'native-inputs.json');manifest=Path(inputs['prepared_manifest'])
    if fingerprint(manifest)!=inputs['prepared_manifest_fingerprint']:raise ValueError('prepared manifest changed')
    report,reply_path=FOLDER/'adoption.json',FOLDER/'adoption.reply.json'
    if report.exists() or reply_path.exists():raise RuntimeError('retain prior dispatch; inspect before any replay')
    lease=json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks',timeout=10)).get('unreal',{})
    deadline=min(time.time()+600,lease.get('at',0)+lease.get('ttl',0)-60)
    if lease.get('holder')!='codex-play-guard' or deadline<=time.time()+120:raise RuntimeError('current sole-operator lease required')
    mcp=editor();label='Codex reviewed Sol Aetherflow three static plants'
    cfg=dict(name='Aetherflow_three_plants',names=list(NAMES),manifest=str(manifest),manifest_sha256=fingerprint(manifest)['sha256'],
             review=str(REVIEW),reviewed_head=HEAD,module_hashes=HASHES,
             importer=str(ROOT/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_prepared_assets.py'),
             importer_sha256=IMPORTER_SHA,report=str(report),deadline=deadline,label=label,
             editor_preflight={'server':mcp.server,'pie_running':False,'current_map':MAP})
    code=NATIVE.replace("[cfg['name']]","cfg['names']",1).replace('CONFIG',repr(cfg),1)
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=code,label=label,budget_ms=1,timeout=180,side='Unreal')
    write_new(reply_path,reply)
    if reply.get('error'):raise RuntimeError('inspect retained import response and native outcomes before replay')
    outcome=load(report)
    native=FOLDER/'NativeReceipts';native.mkdir()
    copies=[]
    for row in outcome['passes'][0]['results']:
        receipt=Path('C:/Unreal/DaedalusRealm/Saved/Daedalus/Ingestion/CodexContest/receipts')/Path(row['receipt']).name
        value=load(receipt)
        if value.get('state')!='saved' or value.get('save_confirmed') is not True:raise RuntimeError('native asset save not confirmed')
        for path,expected in value['outputs'].items():
            actual=Path('C:/Unreal/DaedalusRealm/Content')/(package(path)[6:]+'.uasset')
            if fingerprint(actual)!=expected:raise RuntimeError('saved asset bytes differ')
        target=native/receipt.name
        with target.open('xb') as handle:handle.write(receipt.read_bytes())
        copies.append({'name':row['name'],'receipt':str(target),'fingerprint':fingerprint(target),'assets':value['assets']})
    write_new(FOLDER/'native-saved.json',{'stage':'three_assets_saved','receipts':copies,'map_after':fingerprint(MAP_FILE)})
    print(json.dumps({'stage':'three_assets_saved','passes':outcome['passes'],'saved_receipts':copies},indent=2))


def materials():
    from asset_pipeline import wire
    source_contract();editor();journal=FOLDER/'materials.json'
    if journal.exists():raise RuntimeError('retain earlier palette attempt; inspect before replay')
    _,receipts=source_contract();settings={}
    for receipt in receipts:
        for material in receipt['source_gltf_contract']['materials_linear_gltf']:
            pbr=material['pbrMetallicRoughness'];coat=material['extensions']['KHR_materials_clearcoat']
            key=material['name'].removeprefix('SW_Life_')
            value={'linear_rgb':pbr['baseColorFactor'][:3],'metallic':pbr['metallicFactor'],'roughness':pbr['roughnessFactor'],
                   'clearcoat':coat['clearcoatFactor'],'clearcoat_roughness':coat.get('clearcoatRoughnessFactor',0.)}
            if key in settings and settings[key]!=value:raise ValueError('source PBR values disagree')
            settings[key]=value
    before=fingerprint(MAP_FILE);digest=fingerprint(MATERIAL_SOURCE)['sha256']
    write_new(journal,{'stage':'owned_material_creation_preflight','source_settings':settings,'map_before':before,'source_sha256':digest})
    code='''from pathlib import Path
import hashlib
raw=Path(SOURCE).read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('owned palette source changed')
scope={'__name__':'_codex_aetherflow_pbr'}
exec(compile(raw,SOURCE,'exec'),scope)
def steps():
    return (yield from scope['palette_steps'](SETTINGS,JOURNAL,profile='aetherflow_linear_pbr_v1'))
'''.replace('SOURCE',repr(str(MATERIAL_SOURCE))).replace('EXPECTED',repr(digest)).replace('SETTINGS',repr(settings)).replace('JOURNAL',repr(str(journal)))
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=code,label='Codex Aetherflow retained linear PBR materials',budget_ms=1,timeout=180,side='Unreal')
    record=load(journal);record['reply']=reply
    if reply.get('error'):
        record['stage']='owned_material_inspection_required';journal.write_text(json.dumps(record,indent=2)+'\n');raise RuntimeError('inspect owned material attempt before replay')
    record.update(stage='owned_materials_saved',materials=wire.obj(reply,side='Unreal',what='Aetherflow PBR materials'),map_unchanged=fingerprint(MAP_FILE)==before)
    journal.write_text(json.dumps(record,indent=2)+'\n')
    if record['map_unchanged'] is not True:raise RuntimeError('unexpected map write during material assets save')
    print(json.dumps({'stage':record['stage'],'materials':record['materials'],'map_unchanged':True},indent=2))


def footing():
    _,sources=source_contract();editor();saved=load(FOLDER/'native-saved.json')
    baseline=load(BASE/'codex-aetherflow-before.native.json')
    if baseline.get('issues')!=[] or baseline.get('measured_actor_rows')!=87:raise ValueError('require clean87actor baseline')
    source_map={row['name']:row for row in sources};admissions={row['name']:row for row in saved['receipts']}
    islands=_islands();_,voxels=islands.plan('cliff-garden',84022)
    voxel_sha=hashlib.sha256(islands._json(voxels).encode()).hexdigest()
    if voxel_sha!='697a86c68688759bac1588b496920c3589a99ddeed32fa7c5aefaa137a32629c':raise ValueError('original pond source changed')
    terrain={(x,y,z) for x,y,z,c in voxels['island']}
    water={(x,y) for x,y,z,c in voxels['water'] if z==-1}
    obstacles={(x,y,z) for layer in ('trees','cottage','rocks','flowers','landmarks') for x,y,z,c in voxels[layer]}
    states=[]
    for kind,xy in (('ribbon_reeds',[-24,-18]),('star_lilies',[-19,-12])):
        name='CodexAetherflow_'+kind+'_617024';row=source_map[name];bounds=row['after_merge']['bounds_metres'];lo,hi=bounds['min'],bounds['max']
        cells={(x,y,z) for x in range(math.floor(xy[0]+lo[0]),math.ceil(xy[0]+hi[0]))
               for y in range(math.floor(xy[1]+lo[1]),math.ceil(xy[1]+hi[1])) for z in range(math.floor(lo[2]),math.ceil(hi[2]))}
        if not {(x,y) for x,y,z in cells}<=water or cells&(terrain|obstacles):raise ValueError('source pond footing clips terrain or dressing')
        native=load(admissions[name]['receipt']);path=native['assets'][name]
        states.append({'name':name,'mesh_path':path,'source_position_metres':xy+[0],
                       'origin_cm':[-369150+xy[0]*100,348900-xy[1]*100,18215.324],
                       'source_clear_pond_cells':len(cells),'source_voxel_sha256':voxel_sha,
                       'expected_bounds_cm':{'min':[lo[0]*100,-hi[1]*100,lo[2]*100],'max':[hi[0]*100,-lo[1]*100,hi[2]*100]}})
    labels={'CodexIsland_cliff_garden_84022_'+layer for layer,cells in voxels.items() if cells}
    ignored=[row for row in baseline['native_readback']['actors'] if row['label'] in labels]
    if len(ignored)!=9:raise ValueError('exact nine source-footing layers required')
    cfg={'states':states,'source_actors':ignored,'label':'Codex Aetherflow pond source and native footprint'}
    code='''import unreal,sys
cfg=CONFIG
def steps():
    bridge=sys.modules['claude_unreal_bridge']
    others=[req.get('type') for gen,req,box in bridge._running if req.get('type')!='daedalus.steps' or (req.get('params') or {}).get('label')!=cfg['label']]
    if others or bridge._jobs.qsize() or bridge._remote_lock.locked():raise RuntimeError('conflicting native bridge job')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('dirty packages; preserve work')
    states=cfg['states'];existing=[]
    for state in states:
        mesh=unreal.EditorAssetLibrary.load_asset(state['mesh_path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('saved plant missing')
        box=mesh.get_bounding_box()
        state['native_bounds_cm']={edge:[getattr(getattr(box,edge),axis) for axis in ('x','y','z')] for edge in ('min','max')}
        if any(abs(state['native_bounds_cm'][edge][i]-state['expected_bounds_cm'][edge][i])>.1 for edge in ('min','max') for i in range(3)):raise RuntimeError('source metre/native centimetre basis differs')
        state['native_slots']=[str(slot.material_slot_name) for slot in mesh.get_editor_property('static_materials')]
        state['hits']=[]
    ignore={row['label']:row for row in cfg['source_actors']};seen=set();count=0
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        label=actor.get_actor_label()
        if label in {state['name'] for state in states}:existing.append(label)
        if label in ignore:
            row=ignore[label];comp=actor.get_component_by_class(unreal.StaticMeshComponent)
            if actor.get_path_name()!=row['actor']['refPath'] or not comp or comp.get_editor_property('static_mesh').get_path_name()!=row['mesh_path']:raise RuntimeError('pond source actor identity changed')
            loc=actor.get_actor_location();rot=actor.get_actor_rotation();scale=actor.get_actor_scale3d()
            if any(abs(getattr(loc,a)-v)>.01 for a,v in zip(('x','y','z'),(-369150,348900,18215.324))) or any(abs(getattr(rot,a))>.01 for a in ('pitch','yaw','roll')) or any(abs(getattr(scale,a)-1)>.001 for a in ('x','y','z')):raise RuntimeError('source pond transform changed')
            seen.add(label)
        elif actor.get_components_by_class(unreal.StaticMeshComponent):
            centre,extent=actor.get_actor_bounds(False)
            for state in states:
                lo,hi=state['native_bounds_cm']['min'],state['native_bounds_cm']['max'];origin=state['origin_cm']
                if all(getattr(centre,a)+getattr(extent,a)>origin[i]+lo[i] and getattr(centre,a)-getattr(extent,a)<origin[i]+hi[i] for i,a in enumerate(('x','y','z'))):state['hits'].append(label)
        count+=1
        if count%128==0:yield count
    if seen!=set(ignore):raise RuntimeError('source pond layers missing')
    for state in states:state['placement_preflight_passed']=not state['hits'] and not existing
    return {'states':states,'actors_scanned':count,'existing_labels':existing,'world_mutated':False}
'''.replace('CONFIG',repr(cfg),1)
    before=fingerprint(MAP_FILE)
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=code,label=cfg['label'],budget_ms=1,timeout=180,side='Unreal')
    record={'stage':'pond_footing_readback','map_before':before,'map_unchanged':fingerprint(MAP_FILE)==before,'reply':reply}
    write_new(FOLDER/'footing.json',record)
    result=wire.obj(reply,side='Unreal',what='Aetherflow source/native pond footing')
    if record['map_unchanged'] is not True or any(not row['placement_preflight_passed'] for row in result['states']):raise RuntimeError('inspect retained footprint before any placement')
    print(json.dumps(result,indent=2))


def place():
    source_contract();editor();inputs=load(FOLDER/'native-inputs.json');saved=load(FOLDER/'native-saved.json');palette=load(FOLDER/'materials.json')
    footprint=load(FOLDER/'footing.json')
    states=wire.obj(footprint['reply'],side='Unreal',what='retained source/native footing')['states']
    if footprint['map_unchanged'] is not True or fingerprint(MAP_FILE)!=footprint['map_before'] or any(not row['placement_preflight_passed'] for row in states):raise RuntimeError('fresh source/native pond footprint required')
    if palette.get('stage')!='owned_materials_saved' or palette.get('map_unchanged') is not True:raise ValueError('saved source PBR palette required')
    positions={row['name']:row['origin_cm'] for row in states}
    plans={};entries=[];outputs={};overrides={}
    for row in saved['receipts']:
        if fingerprint(row['receipt'])!=row['fingerprint']:raise ValueError('saved admission changed')
        name=row['name'];plan=plan_admitted(row['receipt'],positions.get(name,[0,0,0]),MAP,MAP_FILE)
        if plan['config_sha256']!=inputs['candidates'][name]['config_sha256']:raise ValueError('admission differs from source config')
        plans[name]={'receipt':row['receipt'],'fingerprint':row['fingerprint'],'canonical_plan':plan}
        outputs.update(plan['native_output_fingerprints'])
        if name in positions:
            entries+=plan['entries'];slots=inputs['candidates'][name]['entry']['objects'][0]['materials']
            overrides[name]={slot:palette['materials'][slot]['refPath'] for slot in slots}
    plan={'schema':'daedalus.codex-aetherflow-assembly.v1','manifest':inputs['prepared_manifest'],
          'manifest_fingerprint':inputs['prepared_manifest_fingerprint'],'saved_receipt':str(FOLDER/'native-saved.json'),
          'saved_receipt_fingerprint':fingerprint(FOLDER/'native-saved.json'),'map_package':MAP,'map_file':str(MAP_FILE),
          'placements_cm':positions,'source_admissions':plans,'native_output_fingerprints':outputs,'entries':entries,
          'component_overrides':overrides,'held_from_world':{NAMES[2]:'intentionally submerged; retained asset-only pending native transparent water'}}
    result=execute_plan(plan,FOLDER/'world.json',timeout=120)
    print(json.dumps({key:result[key] for key in ('stage','created_actors','save_return','map_after','assembly_s','component_override_s','map_save_s')},indent=2))


def reconcile():
    """Verify the known list-response failure, then perform its first map save.

    Never repeat a spawn or material assignment. A retained save attempt blocks
    this route even when its outcome is uncertain; inspect that outcome instead.
    """
    from datetime import datetime, timezone
    from codex_aetherflow_readback import _local, _native_code, _pbr_same, BASE_MATERIAL
    from codex_editor_handoff import _same_transform, _witness
    from codex_saved_asset_assembly import ASSET
    source_contract()
    journal=FOLDER/'world.json'; original=journal.read_bytes(); report=load(journal)
    local=_local(BASE,before_first_save=True)
    if fingerprint(MAP_FILE)!=local['expected_latest_saved_map']:raise RuntimeError('disk map changed before first save')
    lease=json.load(urllib.request.urlopen('http://127.0.0.1:9890/locks',timeout=10)).get('unreal',{})
    if lease.get('holder')!='codex-play-guard' or lease.get('at',0)+lease.get('ttl',0)<time.time()+180:
        raise RuntimeError('require current sole-operator lease for bounded map save')
    mcp=editor()
    code=_native_code(local)+'''\nimport sys,hashlib
b=sys.modules['claude_unreal_bridge']
result['bridge_queue']={'queued':b._jobs.qsize(),
    'running':[{'type':req.get('type'),'code_sha256':hashlib.sha256((req.get('params') or {}).get('code','').encode()).hexdigest()} for gen,req,box in b._running],
    'unfinished_async_jobs':[key for key,(box,at) in b._job_boxes.items() if not box['done'].is_set()],
    'queue_unfinished_tasks_informational_only':b._jobs.unfinished_tasks,'remote_locked':b._remote_lock.locked(),
    'bridge_source':b.__file__}
'''
    reply=wire.call(wire.UNREAL,'execute_python',code=code,unattended=False,timeout=90,side='Unreal')
    native=wire.obj(reply,side='Unreal',what='known-outcome reconciliation before first map save')
    issues=[];observed={row['label']:row for row in native['actors']}
    if len(observed)!=89 or len(native['actors'])!=89:issues.append('exact89 actor set differs')
    for row in local['prior_native']['actors']:
        if any(observed.get(row['label'],{}).get(field)!=row[field] for field in
               ('actor','mesh_path','transform','materials','override_materials','folder','tags')):
            issues.append('prior actor changed: '+row['label'])
    for row in local['new_actors']:
        actual=observed.get(row['label'],{});desired=local['new_component_materials'][row['label']]
        if (actual.get('actor')!=row['actor'] or actual.get('mesh_path')!=row['mesh_path'] or
            not actual.get('transform') or not _same_transform(actual['transform'],row['transform']) or
            actual.get('materials')!=desired or actual.get('override_materials')!=desired or
            actual.get('folder')!=local['folder'] or actual.get('tags')):
            issues.append('new plant state differs: '+row['label'])
    classes=native['saved_asset_classes']
    if set(classes)!=set(local['disk_static_meshes']) or len(classes)!=85 or any(
        row.get('class')!='StaticMesh' or row.get('is_static_mesh') is not True for row in classes.values()):
        issues.append('exact85 saved mesh classes differ')
    refs={(row['actor'],row['label'],row['mesh_path']) for row in native['aetherflow_actor_references']}
    if len(native['aetherflow_actor_references'])!=2 or refs!={(row['actor']['refPath'],row['label'],row['mesh_path']) for row in local['new_actors']}:
        issues.append('plant/kelp world references differ')
    if (native['power_unit_actor_references']!=local['prior_native']['power_unit_actor_references'] or
        native['hero_r2_actor_labels'] or native['hero_r2_mesh_references']):issues.append('prior held/reference state differs')
    if native['all_level_actor_count']!=local['prior_native']['all_level_actor_count']+2:issues.append('loaded level actor count differs')
    for slot,expected in local['expected_pbr'].items():
        value=native['aetherflow_materials'].get(slot,{})
        if value.get('parent')!=BASE_MATERIAL or value.get('path')!=local['material_paths'][slot] or not _pbr_same(value,expected,alpha=True):
            issues.append('saved source PBR differs: '+slot)
    if native['dirty_map_packages']!=[MAP] or native['dirty_content_packages']:issues.append('unexpected dirty packages')
    queue=native['bridge_queue']
    # execute_python is itself a cooperative generator. Identify this exact
    # read by code hash. Queue.unfinished_tasks is not an inflight counter in
    # this bridge: pump() consumes jobs without calling task_done().
    own_read={'type':'execute_python','code_sha256':hashlib.sha256(code.encode()).hexdigest()}
    if queue['queued'] or queue['running']!=[own_read] or queue['unfinished_async_jobs'] or queue['remote_locked']:
        issues.append('conflicting bridge work')
    for path,value in local['protected_files'].items():
        if fingerprint(path)!=_witness(value):issues.append('protected production file changed: '+path)
    if fingerprint(MAP_FILE)!=report['map_before'] or journal.read_bytes()!=original:issues.append('map/journal changed during readback')
    editor()
    readback=FOLDER/('reconciliation-before-first-save-'+str(time.time_ns())+'.json')
    write_new(readback,{'collected_utc':datetime.now(timezone.utc).isoformat(),'native':native,'issues':issues,
                        'original_journal_fingerprint':fingerprint(journal),'read_only':True})
    if issues:raise RuntimeError('inspect retained reconciliation: '+str(issues))
    retained=FOLDER/'world.first-response-shape.json'
    with retained.open('xb') as handle:handle.write(original)
    report['reconciled_from']={'path':str(retained),'fingerprint':fingerprint(retained),'error':report.pop('error')}
    report['reconciliation_readback']={'path':str(readback),'fingerprint':fingerprint(readback)}
    report['applied_component_overrides']=report['native_mutations'][-1]['result']['result']
    report['component_override_s']='not_retained_before_parser_failure'
    action={'toolset':ASSET,'tool':'save_assets','arguments':{'asset_paths':[MAP]},'state':'pending'}
    report['native_mutations'].append(action);report['stage']='native_mutation_pending'
    journal.write_text(json.dumps(report,indent=2)+'\n')
    started=time.perf_counter()
    try:result=mcp.call(ASSET,'save_assets',asset_paths=[MAP])
    except Exception as error:
        action.update(state='uncertain',error=str(error));report['stage']='native_outcome_uncertain'
        journal.write_text(json.dumps(report,indent=2)+'\n');raise
    action.update(state='responded',result=result)
    report.update(save_return=result,map_save_s=round(time.perf_counter()-started,6),map_after=fingerprint(MAP_FILE))
    report['saved_unreal']=result is True and report['map_after']!=report['map_before']
    report['stage']='placed_and_saved' if report['saved_unreal'] else 'inspection_required'
    journal.write_text(json.dumps(report,indent=2)+'\n')
    if report['saved_unreal'] is not True:raise RuntimeError('map save not confirmed; inspect before any further mutation')
    print(json.dumps({key:report[key] for key in ('stage','created_actors','save_return','map_after','map_save_s')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('prepare','ingest','materials','footing','place','reconcile'))
    args=parser.parse_args();globals()[args.stage]()
