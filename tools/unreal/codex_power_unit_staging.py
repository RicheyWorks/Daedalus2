# SPDX-License-Identifier: MIT
"""Read source footing and native bounds for the retained static PowerUnit.

Uses the saved original cliff island, its unchanged voxel recipe and the exact
five-part admission. This produces a placement proposal, never world mutations,
physics, electrical wiring or runtime acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path

from codex_admitted_asset_assembly import POWER_NAME, plan_admitted
from codex_editor_handoff import APP, MAP, MAP_FILE, Mcp, SCENE, _same_transform, package, wire
from codex_contest_island_delivery import fingerprint
from codex_workshop_terrain import _islands


NATIVE = '''import unreal,json
from pathlib import Path
cfg=CONFIG
def steps():
    bridge=__import__('sys').modules['claude_unreal_bridge']
    others=[req.get('type') for gen,req,box in bridge._running
            if req.get('type')!='daedalus.steps' or (req.get('params') or {}).get('label')!=cfg['label']]
    if others or bridge._jobs.qsize() or bridge._remote_lock.locked():raise RuntimeError('conflicting bridge operation')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('dirty packages; preserve current work')
    low,high=[float('inf')]*3,[float('-inf')]*3
    layer_bounds={}
    for row in cfg['entries']:
        mesh=unreal.EditorAssetLibrary.load_asset(row['mesh_path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('saved PowerUnit mesh missing')
        box=mesh.get_bounding_box()
        a,b=[getattr(box.min,k) for k in ('x','y','z')],[getattr(box.max,k) for k in ('x','y','z')]
        layer_bounds[row['label']]={'min':a,'max':b}
        low=[min(low[i],a[i]) for i in range(3)];high=[max(high[i],b[i]) for i in range(3)]
    expected=cfg['source_bounds_cm']
    if not all(abs(value[i]-expected[key][i])<=.1 for key,value in (('min',low),('max',high)) for i in range(3)):
        raise RuntimeError('native bounds differ from baked source x,-y,z basis')
    states=[dict(row,hits=[]) for row in cfg['proposals']]
    ignored={row['label']:row for row in cfg['source_island_actors']}
    seen_ignored=set(); existing=[];count=0
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        label=actor.get_actor_label()
        if label.startswith(cfg['name']+'_'):existing.append(label)
        if label in ignored:
            row=ignored[label];comp=actor.get_component_by_class(unreal.StaticMeshComponent)
            if actor.get_path_name()!=row['actor']['refPath'] or not comp or comp.get_editor_property('static_mesh').get_path_name()!=row['mesh_path']:
                raise RuntimeError('source-footing island identity changed')
            seen_ignored.add(label)
        elif actor.get_components_by_class(unreal.StaticMeshComponent):
            origin,extent=actor.get_actor_bounds(False)
            amin=[getattr(origin,k)-getattr(extent,k) for k in ('x','y','z')]
            amax=[getattr(origin,k)+getattr(extent,k) for k in ('x','y','z')]
            for state in states:
                centre=state['origin_cm']
                if all(amax[i]>centre[i]+low[i]-.1 and amin[i]<centre[i]+high[i]+.1 for i in range(3)):
                    state['hits'].append({'actor':actor.get_path_name(),'label':label,'min':amin,'max':amax})
        count+=1
        if count%128==0:yield count
    if seen_ignored!=set(ignored):raise RuntimeError('source island layer set missing')
    for state in states:state['placement_preflight_passed']=not state['hits'] and not existing
    return {'stage':'native_source_footing_readback','actors_scanned':count,'proposals':states,
            'native_bounds_cm':{'min':low,'max':high},'layer_bounds_cm':layer_bounds,
            'source_island_layers_verified':sorted(seen_ignored),'existing_candidate_labels':existing,
            'world_mutated':False,'limits':'source cells and static bounding boxes only; collision/navigation unverified'}
'''


def inspect(folder, output):
    folder, output=Path(folder).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('retain previous readback; choose a new output')
    before_path=folder/'codex-power-unit-2205.before.json'
    before=json.loads(before_path.read_text())
    if before.get('stage')!='renewed_production_readback_completed' or before.get('issues')!=[]:
        raise ValueError('require the fresh clean82-row saved baseline')
    map_before=fingerprint(MAP_FILE)
    if map_before!={k:before['map_after_readback'][k] for k in ('sha256','bytes')}:
        raise ValueError('map changed since the fresh82-row readback')
    source_path=folder/'SalvageAssemblies/a86100'/ (POWER_NAME+'.receipt.json')
    source=json.loads(source_path.read_text())
    for artifact in source['artifacts'].values():
        if fingerprint(artifact['path'])!=artifact['fingerprint']:raise ValueError('source payload changed')
    receipt=folder/'NativeReceipts/codex-ingestion-e3f098e65a1dc4ddb1129b79.json'
    plan=plan_admitted(receipt,[-367350,346900,18315.324],MAP,MAP_FILE)
    islands=_islands();_,voxels=islands.plan('cliff-garden',84022)
    voxel_sha=hashlib.sha256(islands._json(voxels).encode()).hexdigest()
    retained=json.loads((folder/'codex-workshop-source-plan.json').read_text())[0]
    if voxel_sha!=retained['source_voxel_sha256']:raise ValueError('original cliff source recipe changed')
    top={}
    for x,y,z,_ in voxels['island']:top[x,y]=max(top.get((x,y),z),z)
    obstacles={(x,y) for layer in ('trees','cottage','rocks','flowers','landmarks','water')
               for x,y,z,_ in voxels[layer] if 1<=z<5}
    proposals=[]
    for x in range(16,29):
        for y in range(10,29):
            cells={(a,b) for a in range(x-2,x+3) for b in range(y-4,y+2)}
            if all(top.get(cell)==0 for cell in cells) and not cells&obstacles:
                proposals.append({'source_centre_metres':[x,y,1],'origin_cm':[-369150+x*100,348900-y*100,18315.324],
                                  'verified_flat_dry_cells':len(cells),'source_voxel_sha256':voxel_sha})
    proposals.sort(key=lambda row:abs(row['source_centre_metres'][0]-20)+abs(row['source_centre_metres'][1]-20))
    if not proposals:raise ValueError('no dry clear source footing')
    original_labels={'CodexIsland_cliff_garden_84022_'+layer for layer,cells in voxels.items() if cells}
    old=[row for row in before['native_readback']['actors'] if row['label'] in original_labels]
    if len(old)!=9:raise ValueError('require exact original nine cliff layers')
    cfg={'label':'Codex retained PowerUnit source footing and native bounds','name':POWER_NAME,
         'entries':plan['entries'],'proposals':proposals[:12],'source_island_actors':old,
         'source_bounds_cm':{'min':[-200,-75,0],'max':[200,400,400]}}
    mcp=Mcp(timeout=45)
    if mcp.call(APP,'IsPIERunning') is not False or package(mcp.call(SCENE,'get_current_level'))!=MAP:
        raise RuntimeError('require DaedalusWorld and PIE stopped')
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=NATIVE.replace('CONFIG',repr(cfg),1),
                    label=cfg['label'],budget_ms=1,timeout=180,side='Unreal')
    result={'schema':'daedalus.codex-power-unit-footing.v1','source_receipt':str(source_path),
            'source_receipt_fingerprint':fingerprint(source_path),'baseline':str(before_path),
            'baseline_fingerprint':fingerprint(before_path),'map_before':map_before,'reply':reply,
            'staging_only':True,'ownership_changes':False}
    result['map_unchanged']=fingerprint(MAP_FILE)==map_before
    with output.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2);handle.write('\n')
    if reply.get('error') or result['map_unchanged'] is not True:raise RuntimeError('inspect retained footprint readback')
    native=wire.obj(reply,side='Unreal',what='PowerUnit footprint readback')
    ready=[row for row in native['proposals'] if row['placement_preflight_passed']]
    if not ready:raise RuntimeError('no native-clear placement proposal')
    print(json.dumps({'ready_proposal':ready[0],'native_bounds_cm':native['native_bounds_cm'],
                      'actors_scanned':native['actors_scanned'],'map_unchanged':True},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    inspect(args.folder,args.out)
