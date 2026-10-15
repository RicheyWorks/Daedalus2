"""Reconcile the exact imported, unsaved Copperfall six; never import again."""
import argparse
import json
from pathlib import Path
import shutil
import time
from types import SimpleNamespace
import codex_copperfall_delivery as h
from codex_static_intake_delivery import _snap_definition

d=h.d;ORIGINAL=h.DEFAULT_FOLDER;F=ORIGINAL.parent/'RecoveryNaniteOffR1'
OBS=ORIGINAL/'reconciliation-before-first-saves.json'
args=SimpleNamespace(folder=ORIGINAL,baseline=None,minimum_free_physical_mib=1024,minimum_free_commit_mib=1536)


def state():
    value=h.prepared(args);native=d.load(ORIGINAL/'native.json');dispatch=d.load(ORIGINAL/'dispatch.json')
    if native['stage']!='halted_preserve_partial' or native['completed_count']!=0 or native['outputs'] or native['world_saved'] or native['world_placed']:
        raise RuntimeError('Only the exact retained imported-but-unsaved six may be reconciled')
    observation=native['failed_contract_observation'];paths={row['path'] for row in observation['assets']}
    if len(paths)!=6 or set(native['imported_object_paths'])!=paths:
        raise RuntimeError('Exact six imported objects required')
    for path in paths:
        if d._asset_file(path).exists():raise RuntimeError('Unexpected prior disk save; stop and reconcile')
    d._lease();h.resources(args)
    claim=dispatch['compute_claim']['lock']
    if not d.same_compute_lease(d.locks().get('compute',{}),claim):raise RuntimeError('Original exact packet compute lease required')
    cfg=h.config(value,args)
    cfg['deadline_epoch']=min(cfg['deadline_epoch'],time.time()+180,claim['at']+claim['ttl']-30)
    return value,native,dispatch,cfg,sorted(paths)


CHECK=r'''
packet,nodes,helper,miri,guard=scope['_config'](cfg)
guard['_deadline'](cfg);initial=guard['_preflight'](allowed)
try:
 observed,objects=scope['_inspect'](cfg,nodes,helper,miri)
except scope['ContractError'] as exc:
 observed=exc.observed;objects=helper['_assets']()
if set(objects)!=set(expected_paths) or len(observed['items'])!=3 or observed['triangles']!=292:raise RuntimeError('Exact six known imported outputs required')
expected_issue='bounded accepted profile requires observed Nanite/lightmap generation false'
if len(observed['issues'])!=3 or any(not s.endswith(expected_issue) for s in observed['issues']):raise RuntimeError('Only observed Nanite-on mismatch may be corrected')
for row in observed['items']:
 geometry=row['geometry']
 if geometry['issues']!=[expected_issue] or geometry['nanite_enabled'] is not True or geometry['generate_lightmap_u_vs'] is not False or row['material']['readback_errors']:raise RuntimeError('Unrelated native mismatch; preserve state')
for path in expected_disk_paths:
 if Path(path).exists():raise RuntimeError('Unexpected saved output; no blind firstsave')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
p,r=e.get_level_viewport_camera_info()
scene={'world':e.get_editor_world().get_path_name(),'actors':[snap(a) for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label().startswith('Codex')],'camera':{'location':{'x':p.x,'y':p.y,'z':p.z},'rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll}}}
if scene['world']!=expected_scene['world'] or {r['path']:r for r in scene['actors']}!={r['path']:r for r in expected_scene['actors']} or scene['camera']!=expected_scene['camera']:raise RuntimeError('Saved actors/camera/world changed')
'''


def call(value,cfg,paths,body,timeout=60):
    base=d.load(value['baseline']['path'])
    code=d.module_code(value)+ '\nimport unreal,time\n'+_snap_definition()+'\n'
    data={'cfg':cfg,'expected_paths':paths,'expected_disk_paths':[str(d._asset_file(p)) for p in paths],
          'allowed':[p.split('.')[0] for p in paths],'expected_scene':base['scene']}
    for name,value in data.items():code+=name+'='+repr(value)+'\n'
    code+='\ndef steps():\n'+''.join('    '+line+'\n' for line in body.splitlines())
    reply=d.wire.call(d.wire.UNREAL,'daedalus.steps',code=code,label=h.label(),budget_ms=1,timeout=timeout,side='Unreal')
    return d.wire.obj(reply,side='Unreal',what='Copperfall existing-unsaved reconciliation')


def observe():
    if OBS.exists():raise RuntimeError('Retain existing read-only reconciliation')
    value,native,dispatch,cfg,paths=state()
    result=call(value,cfg,paths,CHECK+"\nif False:yield\nreturn {'stage':'exact_six_imported_unsaved_nanite_only_observed','observed':observed,'guard':initial,'scene':scene,'native_mutations':0}\n")
    if not isinstance(result,dict) or result.get('stage')!='exact_six_imported_unsaved_nanite_only_observed':raise RuntimeError('Explicit current observation required')
    d.protect(d.load(value['baseline']['path']))
    report={'utc':d._utc(),'stage':'exact_six_imported_unsaved_nanite_only_reconciled','original_native':d.pin(ORIGINAL/'native.json'),'original_dispatch':d.pin(ORIGINAL/'dispatch.json'),'observed':result,'imports_replayed':0,'native_mutations':0}
    d.write_new(OBS,report)
    print(json.dumps({'stage':report['stage'],'observation':d.pin(OBS)},indent=2))


def run():
    if F.exists():raise RuntimeError('Retained recovery exists; never replay settings or saves')
    value,native,dispatch,cfg,paths=state();observation=d.load(OBS)
    d._check(observation['original_native']);d._check(observation['original_dispatch'])
    if observation['stage']!='exact_six_imported_unsaved_nanite_only_reconciled':raise RuntimeError('Explicit read-only reconciliation required')
    F.mkdir();shutil.copy2(__file__,F/'recovery-source-used.py')
    prepared=dict(value,recovery={'original_delivery':str(ORIGINAL),'read_only_reconciliation':d.pin(OBS),'scope':'Only disable Nanite on the three new unsaved meshes, revalidate full source/material contract, add own metadata, then six firstsaves; never import.'})
    d.write_new(F/'prepared.json',prepared)
    record={'utc':d._utc(),'stage':'bounded_nanite_correction_firstsave_dispatch_pending','compute_claim':dispatch['compute_claim'],'prepared':d.pin(F/'prepared.json'),'original_native':d.pin(ORIGINAL/'native.json'),'read_only_reconciliation':d.pin(OBS),'replay_permitted':False}
    d.write_new(F/'dispatch.json',record);cfg['journal']=str(F/'native.json')
    body=CHECK+r'''
journal=Path(cfg['journal'])
report={'schema':'daedalus.codex-copperfall-nanite-recovery.v1','utc':scope['_utc'](),'stage':'bounded_owned_nanite_correction_pending','outputs':[],'items':[],'completed_count':0,'save_return':None,'mutation_intents':[],'corrections':[],'world_placed':0,'world_saved':False,'mesh_bindings_changed':False,'shared_material_modified':False,'replay_permitted':False,'imports_replayed':0,'observed_before_correction':observed}
with journal.open('x',encoding='utf-8') as output:helper['_flush'](output,report)
try:
 subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
 for row in observed['items']:
  guard['_deadline'](cfg);guard['_preflight'](allowed)
  mesh=objects[row['path']];settings=subsystem.get_nanite_settings(mesh)
  if not settings.enabled:raise RuntimeError('Initial Nanite state changed')
  report['mutation_intents'].append({'operation':'disable_nanite_only_on_new_unsaved_owned_mesh','path':row['path'],'utc':scope['_utc']()});helper['_write'](journal,report)
  settings.enabled=False;started=time.perf_counter();subsystem.set_nanite_settings(mesh,settings,True)
  report['corrections'].append({'path':row['path'],'before_enabled':True,'after_enabled':bool(subsystem.get_nanite_settings(mesh).enabled),'apply_s':round(time.perf_counter()-started,6)})
  helper['_write'](journal,report)
 checked,objects=scope['_inspect'](cfg,nodes,helper,miri)
 report['observed_after_correction_before_metadata']=checked;helper['_write'](journal,report)
 roles={row['path']:row['source_role'] for row in checked['items']};roles.update({row['material_path']:row['source_material'] for row in checked['items']})
 for path,obj in sorted(objects.items()):
  guard['_deadline'](cfg);guard['_preflight'](allowed)
  report['mutation_intents'].append({'operation':'set_owned_source_metadata','path':path,'utc':scope['_utc']()});helper['_write'](journal,report)
  for key,val in scope['_tags'](cfg,roles[path]).items():unreal.EditorAssetLibrary.set_metadata_tag(obj,key,val)
 report['observed_after_metadata_before_first_save'],objects=scope['_inspect'](cfg,nodes,helper,miri,metadata=True)
 helper['_write'](journal,report)
 for path,obj in sorted(objects.items()):
  guard['_deadline'](cfg);guard['_preflight'](allowed)
  row={'path':path,'class':obj.get_class().get_name(),'save_return':None,'save_s':None,'stage':'first_save_dispatch_pending'}
  report['outputs'].append(row);report['mutation_intents'].append({'operation':'first_save_exact_owned_asset','path':path,'utc':scope['_utc']()});helper['_write'](journal,report)
  started=time.perf_counter();row['save_return']=bool(unreal.EditorAssetLibrary.save_loaded_asset(obj,only_if_is_dirty=False));row['save_s']=round(time.perf_counter()-started,6)
  row['stage']='asset_saved' if row['save_return'] else 'save_returned_false'
  if row['save_return']:report['completed_count']+=1
  helper['_write'](journal,report)
  if row['save_return'] is not True:raise RuntimeError('Firstsave returned false; preserve partial')
  yield path
 report['final_preflight']=guard['_preflight']()
 report['observed_after_saves'],objects=scope['_inspect'](cfg,nodes,helper,miri,metadata=True)
 report.update(stage='copperfall_subset_assets_saved_world_held',save_return=True,items=checked['items']);helper['_write'](journal,report)
 return report
except Exception as exc:
 report.update(stage='halted_preserve_partial',error=str(exc),error_type=type(exc).__name__)
 if hasattr(exc,'observed'):report['failed_contract_observation']=exc.observed
 if not journal.with_name(journal.name+'.write-pending').exists():helper['_write'](journal,report)
 raise
'''
    try:
        result=call(value,cfg,paths,body,timeout=180);d.write_new(F/'reply.json',result)
    except Exception as error:
        record.update(stage='inspect_recovery_outcome_never_replay',error=str(error));d._write(F/'dispatch.json',record);raise
    saved=d.load(F/'native.json')
    if saved['stage']!='copperfall_subset_assets_saved_world_held' or saved['completed_count']!=6 or saved['save_return'] is not True or len(saved['outputs'])!=6 or any(row['save_return'] is not True for row in saved['outputs']):raise RuntimeError('Six complete firstsave records required')
    outputs={row['path']:{'class':row['class'],**d.fingerprint(d._asset_file(row['path']))} for row in saved['outputs']}
    d.protect(d.load(value['baseline']['path']))
    record.update(stage='six_copperfall_packages_saved_world_held',outputs=outputs,native=d.pin(F/'native.json'));d._write(F/'dispatch.json',record)
    print(json.dumps({'stage':record['stage'],'outputs':outputs},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('observe','run'));globals()[parser.parse_args().phase]()
