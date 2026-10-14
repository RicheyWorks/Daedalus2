# SPDX-License-Identifier: MIT
"""Use the existing owned palette helper for staging component overrides only.

Run during an accepted editor turn, with PIE stopped. Prepared mesh packages,
the shared vertex-colour material, lighting and project settings stay untouched.
Unknown native outcomes are retained for inspection instead of automatic replay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'connectors/claude-asset-pipeline'))
from asset_pipeline import wire
from codex_contest_island_delivery import ASSET,Mcp,fingerprint,package
from codex_admitted_asset_assembly import POWER_NAME, _retained_contract
from codex_workshop_terrain import _islands
APP='EditorToolset.EditorAppToolset'


def _linear(value):
    return value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4


def apply(folder,islands,journal,repair_empty_base=False,assembly=None,source_receipt=None):
    folder,journal=Path(folder).resolve(),Path(journal).resolve()
    if journal.exists():raise RuntimeError('retain existing palette journal; inspect it before another native run')
    if (assembly is None)!=(source_receipt is None):raise ValueError('additional assembly requires its exact exported source receipt')
    candidate=None
    candidate_inputs={}
    if assembly is not None:
        assembly,source_receipt=Path(assembly).resolve(),Path(source_receipt).resolve()
        placed=json.loads(assembly.read_text())
        candidate=json.loads(source_receipt.read_text())
        config=candidate.get('config',{})
        settings={'name':candidate.get('name'),'seed':config.get('seed'),'config_sha256':candidate.get('config_sha256'),'config':config}
        expected=_retained_contract(settings,{})
        name=candidate['name']
        plan=placed.get('plan',{})
        source_schema='daedalus.codex-salvage-assembly.v1' if name==POWER_NAME else 'daedalus.codex-island.v1'
        if islands!={name} or candidate.get('stage')!='exported' or candidate.get('schema')!=source_schema:
            raise ValueError('select one exact exported retained candidate for its own palette')
        if placed.get('stage')!='placed_and_saved' or placed.get('save_return') is not True or plan.get('schema')!='daedalus.codex-admitted-assembly.v1':
            raise ValueError('additional retained candidate must have a saved admitted assembly')
        if plan.get('config_sha256')!=candidate['config_sha256'] or plan.get('seed')!=config['seed'] or set(plan.get('placements_cm',{}))!={name}:
            raise ValueError('saved assembly identity differs from its source palette receipt')
        source_objects=candidate.get('blender',{}).get('objects',[])
        actors=placed.get('actors',[])
        entries=plan.get('entries',[])
        if len(source_objects)!=len(expected) or {row.get('name') for row in source_objects}!=expected or len(actors)!=len(expected) or {row.get('label') for row in actors}!=expected:
            raise ValueError('candidate source/actor roles differ from the exact retained contract')
        if len(entries)!=len(expected) or {row.get('label') for row in entries}!=expected or any(row.get('group')!=name for row in actors+entries):
            raise ValueError('saved assembly entries leave the exact retained identity')
        if {(row['label'],row['mesh_path']) for row in actors}!={(row['label'],row['mesh_path']) for row in entries}:
            raise ValueError('saved actor mesh mapping differs from the admitted assembly plan')
        fbx=candidate.get('artifacts',{}).get('fbx',{})
        if fbx.get('fingerprint')!=plan.get('source_fingerprint') or fingerprint(fbx['path'])!=plan['source_fingerprint']:
            raise ValueError('candidate source FBX differs from its saved assembly witness')
        candidate_inputs={'assembly':str(assembly),'assembly_fingerprint':fingerprint(assembly),
                          'source_receipt':str(source_receipt),'source_receipt_fingerprint':fingerprint(source_receipt)}
    groups=[]
    for name in ('codex-cliff-staging.world.json','codex-remaining-staging.world.json','codex-workshop.world.json'):
        report=json.loads((folder/name).read_text())
        if report.get('stage')!='placed_and_saved' or report.get('save_return') is not True:
            raise ValueError('require saved staging actors before material polish')
        groups+=report['actors']
    hero='CodexIsland_summit_rim_84011_HeroR3'
    if hero in islands and candidate is None:
        report=json.loads((folder/'codex-hero-r3.world.json').read_text())
        if report.get('stage')!='placed_and_saved' or report.get('save_return') is not True:raise ValueError('require saved admitted hero actors')
        groups+=report['actors']
    if candidate is not None:groups+=placed['actors']
    selected=[r for r in groups if r.get('group',r.get('island')) in islands]
    counts={'CodexIsland_cliff_garden_84022':18,'CodexIsland_river_canyon_84033':18,'CodexIsland_summit_rim_84011':17,hero:10}
    if candidate is not None:counts[candidate['name']]=len(expected)
    if not islands.issubset(counts) or len(selected)!=sum(counts[n] for n in islands):
        raise ValueError('staging selection differs from the exact island plus workshop actors')
    saved=json.loads((folder/'codex-prepared.unreal.json').read_text())
    witnesses={row['path']:fingerprint(Path('C:/Unreal/DaedalusRealm/Content')/(package(row['path'])[6:]+'.uasset')) for group in saved['results'] for row in group['meshes']}
    additional={}
    for path in (folder/'NativeReceipts').glob('codex-ingestion-*.json'):
        admitted=json.loads(path.read_text())
        if admitted.get('state')!='saved' or admitted.get('save_confirmed') is not True:raise ValueError('retained admission receipt is not saved')
        for mesh_path,witness in admitted['outputs'].items():
            if fingerprint(Path('C:/Unreal/DaedalusRealm/Content')/(package(mesh_path)[6:]+'.uasset'))!=witness:raise ValueError('admitted saved mesh changed before polish')
            additional[mesh_path]=witness
    if candidate is not None:
        outputs=plan.get('native_output_fingerprints',{})
        if set(outputs)!={row['mesh_path'] for row in placed['actors']}:raise ValueError('candidate output witnesses differ from its saved actors')
        for mesh_path,output in outputs.items():
            witness={key:output[key] for key in ('sha256','bytes')}
            if fingerprint(Path('C:/Unreal/DaedalusRealm/Content')/(package(mesh_path)[6:]+'.uasset'))!=witness:
                raise ValueError('candidate saved mesh changed before polish')
            if mesh_path in additional and additional[mesh_path]!=witness:raise ValueError('candidate and retained native witnesses disagree')
            additional[mesh_path]=witness
    shared=Path('C:/Unreal/DaedalusRealm/Content/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.uasset')
    record={'stage':'preflight','actors':selected,'prepared_meshes_before':witnesses,'additional_meshes_before':additional,'shared_material_before':fingerprint(shared),
            'map_before':fingerprint('C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap'),'ownership_tags_added':False,'world_placed_new':0}
    if candidate_inputs:record['candidate_inputs']=candidate_inputs
    def write():journal.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    write()
    code='''import unreal,json
rows=ROWS
actors={}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    label=actor.get_actor_label()
    if label in {row['label'] for row in rows}:
        if label in actors:raise RuntimeError('ambiguous actor label')
        actors[label]=actor
result=[]
for row in rows:
    actor=actors[row['label']]
    if actor.get_path_name()!=row['actor']['refPath']:raise RuntimeError('actor reference differs')
    component=actor.get_component_by_class(unreal.StaticMeshComponent)
    mesh=component.get_editor_property('static_mesh')
    if mesh.get_path_name()!=row['mesh_path']:raise RuntimeError('actor mesh differs')
    result.append({'label':row['label'],'slots':[str(slot.material_slot_name) for slot in mesh.get_editor_property('static_materials')],
                   'previous_materials':[component.get_material(i).get_path_name() for i in range(component.get_num_materials())]})
'''.replace('ROWS',repr(selected))
    m=Mcp(timeout=120)
    if m.call(APP,'IsPIERunning'):raise RuntimeError('PIE running')
    reply=wire.call(wire.UNREAL,'execute_python',code=code,unattended=False,timeout=30,side='Unreal')
    if reply.get('error'):raise RuntimeError(str(reply))
    record['preflight']=reply['result'];write()
    palette,surfaces={},{}
    profile=_islands().SURFACES
    record['surface_profile_source_sha256']=hashlib.sha256((ROOT/'tools/blender/codex_contest_island.py').read_bytes()).hexdigest()
    palette_rows=([candidate] if candidate is not None else json.loads((folder/'codex-islands.batch.json').read_text())+json.loads((folder/'SkyHarborModules/skyharbor-modules.batch.json').read_text()))
    for row in palette_rows:
        for key,rgb in row['palette_rgb'].items():
            if key in palette and palette[key]!=rgb:raise ValueError('source palette differs')
            palette[key]=rgb
            surfaces[key]=row.get('palette_surface',profile)[key]
    slots={slot for row in record['preflight'] for slot in row['slots']}
    if not slots.issubset({'CodexVoxel_'+key for key in palette}):raise ValueError('native palette slots differ')
    record['stage']='owned_palette_creation_pending';write()
    settings={key:dict(linear_rgb=[_linear(v) for v in rgb],**surfaces[key]) for key,rgb in palette.items() if 'CodexVoxel_'+key in slots}
    source=ROOT/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_staging_palette.py'
    record['palette_source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();write()
    code='''from pathlib import Path
scope={'__name__':'_codex_owned_staging_palette'}
raw=Path(SOURCE).read_bytes()
import hashlib
if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('palette source changed')
exec(compile(raw,SOURCE,'exec'),scope)
def steps():
    return (yield from scope['palette_steps'](SETTINGS,JOURNAL,REPAIR))
'''.replace('SOURCE',repr(str(source))).replace('EXPECTED',repr(record['palette_source_sha256'])).replace('SETTINGS',repr(settings)).replace('JOURNAL',repr(str(journal))).replace('REPAIR',repr(repair_empty_base))
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=code,label='Codex native owned palette assets',budget_ms=1,timeout=180,side='Unreal')
    record=json.loads(journal.read_text())
    record['palette_reply']={k:v for k,v in reply.items() if k!='stdout'}
    if reply.get('error'):record['stage']='owned_palette_inspection_required';write();raise RuntimeError(str(reply))
    materials=reply['result']
    record.update(stage='owned_palette_created',materials=materials);write()
    record['stage']='component_overrides_pending';write()
    code='''import unreal,json
from pathlib import Path
rows=ROWS
materials=MATERIALS
journal=Path(JOURNAL)
def steps():
    report=json.loads(journal.read_text())
    actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() in {r['label'] for r in rows}}
    report['applied']=[]
    for row in rows:
        actor=actors[row['label']]
        if actor.get_path_name()!=row['actor']['refPath']:raise RuntimeError('actor changed before polish')
        component=actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh=component.get_editor_property('static_mesh')
        if mesh.get_path_name()!=row['mesh_path']:raise RuntimeError('mesh changed before polish')
        desired=[unreal.EditorAssetLibrary.load_asset(materials[str(slot.material_slot_name)]['refPath']) for slot in mesh.get_editor_property('static_materials')]
        if any(not isinstance(material,unreal.MaterialInterface) for material in desired):raise RuntimeError('saved palette material could not be loaded; no override cleared')
        report['stage']='component_override_pending'
        report['pending_actor']=row['label']
        journal.write_text(json.dumps(report,indent=2)+'\\n',encoding='utf-8')
        actor.modify()
        component.modify()
        for i,material in enumerate(desired):
            component.set_material(i,material)
            if component.get_material(i)!=material:raise RuntimeError('component material readback differs')
        report['applied'].append({'label':row['label'],'materials':[component.get_material(i).get_path_name() for i in range(component.get_num_materials())]})
        report['stage']='component_override_responded'
        journal.write_text(json.dumps(report,indent=2)+'\\n',encoding='utf-8')
        yield row['label']
    return {'applied_actors':len(report['applied'])}
'''.replace('ROWS',repr(selected)).replace('MATERIALS',repr(materials)).replace('JOURNAL',repr(str(journal)))
    reply=wire.call(wire.UNREAL,'daedalus.steps',code=code,label='Codex own staging palette component polish',budget_ms=1,timeout=180,side='Unreal')
    record=json.loads(journal.read_text())
    record['native_reply']={k:v for k,v in reply.items() if k!='stdout'}
    if reply.get('error'):record['stage']='native_outcome_inspection_required';write();raise RuntimeError(str(reply))
    record['stage']='map_save_pending';write()
    started=time.perf_counter()
    record['save_return']=m.call(ASSET,'save_assets',asset_paths=['/Game/Daedalus/DaedalusWorld'])
    record['map_save_s']=round(time.perf_counter()-started,6)
    record['map_after']=fingerprint('C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap')
    unchanged=all(fingerprint(Path('C:/Unreal/DaedalusRealm/Content')/(package(path)[6:]+'.uasset'))==witness for path,witness in witnesses.items())
    record['prepared_meshes_unchanged']=unchanged
    record['additional_saved_meshes_unchanged']=all(fingerprint(Path('C:/Unreal/DaedalusRealm/Content')/(package(path)[6:]+'.uasset'))==witness for path,witness in additional.items())
    record['shared_material_unchanged']=fingerprint(shared)==record['shared_material_before']
    if record['save_return'] is not True or record['map_after']==record['map_before'] or not unchanged or not record['additional_saved_meshes_unchanged'] or not record['shared_material_unchanged']:
        record['stage']='saved_outcome_inspection_required';write();raise RuntimeError('native save/input preservation differs')
    record['stage']='component_palette_saved';write()
    return {key:record[key] for key in ('stage','save_return','map_after','prepared_meshes_unchanged','shared_material_unchanged','map_save_s')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--island',action='append',required=True)
    parser.add_argument('--journal',type=Path,required=True)
    parser.add_argument('--repair-inspected-empty-base',action='store_true',help='only after native inspection confirms the known failed owned stub has zero expressions')
    parser.add_argument('--assembly',type=Path,help='saved admitted HeroR3/HeroR4/GardenGateR1/PowerUnit assembly journal; pair with --source-receipt')
    parser.add_argument('--source-receipt',type=Path,help='exact exported candidate receipt supplying its own palette/config/FBX witnesses')
    args=parser.parse_args()
    print(json.dumps(apply(args.folder,set(args.island),args.journal,args.repair_inspected_empty_base,args.assembly,args.source_receipt),indent=2))
