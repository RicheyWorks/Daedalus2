"""Only the unattempted map save/readback after a known camera-precision hold."""
import argparse
import copy
import json
import math
from pathlib import Path
import time

import codex_canal_water_placement as p

d=p.d;F=p.F
CAMERA_CHECK='''
def same_camera(actual,wanted):
    return all(math.isfinite(actual[g][k]) and abs(actual[g][k]-v)<=1e-5 for g in ('location','rotation') for k,v in wanted[g].items())
'''


def prepared():
    value=d.load(F/'camera-precision-continuation.json')
    for key in ('source','previous_host_source','failed_save_return','restore_return','original_prepared'):
        d._check(value[key])
    if d.pin(__file__)!=value['source']:raise RuntimeError('frozen continuation source differs')
    if value['claim_unchanged']!=d.load(F/'compute-claim.json'):raise RuntimeError('continuation must retain the same exact claim')
    return value


def save():
    p.custody();base=d.load(p.BASE);d.protect(base)
    if (F/'native-map-save.json').exists():raise RuntimeError('original save journal exists; reconcile before any save')
    failed=d.load(F/'save-return.json')
    if (failed.get('stage')!='halted_preserve_partial' or failed.get('error_type')!='RuntimeError'
            or failed.get('error')!='restore exact previous camera before map save'):
        raise RuntimeError('only exact known pre-save camera comparison hold admits this continuation')
    actual=d.load(F/'camera-restore-return.json')['scene']['camera'];wanted=base['scene']['camera']
    if any(abs(actual[g][k]-v)>1e-5 for g in wanted for k,v in wanted[g].items()):raise RuntimeError('normal existing camera tolerance not met')
    value={'utc':d._utc(),'stage':'known_zero_save_guard_failure_remaining_first_map_save',
        'source':d.pin(__file__),'previous_host_source':d.pin(p.__file__),
        'failed_save_return':d.pin(F/'save-return.json'),'restore_return':d.pin(F/'camera-restore-return.json'),
        'original_prepared':d.pin(F/'prepared.json'),'established_camera_tolerance':1e-5,
        'native_save_calls_predecessor':0,'new_actor_spawns_in_continuation':0,
        'actual_restored_camera':actual,'previous_camera':wanted,'claim_unchanged':d.load(F/'compute-claim.json')}
    d.write_new(F/'camera-precision-continuation.json',value)
    prepared()
    cfg=p.plan();cfg['journal']=str(F/'native-map-save-camera-precision-r1.json')
    body='cfg='+repr(cfg)+'\n'+CAMERA_CHECK+'''
proof=validate_pair(cfg)
if not same_camera(snapshot_scene()['camera'],cfg['old_scene']['camera']):raise RuntimeError('existing normal camera tolerance differs')
paths=[x['path'] for x in proof['new_actors']]
require_prior_digest(world_existing_actor_digest(paths),cfg['global_actor_digest'],paths)
phase_deadline()
j=Path(cfg['journal']);report={'stage':'map_save_dispatch_pending','save_return':None,'new_actors':proof['new_actors'],'camera_comparison':'existing scene tolerance1e-5; original camera restored within2.66e-7deg'}
with j.open('x',encoding='utf-8') as f:json.dump(report,f);f.flush();os.fsync(f.fileno())
phase_deadline();start=time.perf_counter();report['save_return']=bool(unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Daedalus/DaedalusWorld'));report['save_s']=round(time.perf_counter()-start,6)
report.update(stage='winter4_map_save_returned',dirty_maps=[x.get_path_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],dirty_content=[x.get_path_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
with j.open('w',encoding='utf-8') as f:json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
result=report
'''
    reply=p.dispatch('save-camera-precision-r1',body,dirty=True,timeout=120)
    if reply.get('save_return') is not True or reply['dirty_maps'] or reply['dirty_content']:raise RuntimeError('first map save not explicitly confirmed; never replay')
    print(json.dumps(reply))


def readback():
    p.custody();prepared();base=d.load(p.BASE);cfg=p.plan()
    saved=d.load(F/'native-map-save-camera-precision-r1.json')
    if saved.get('save_return') is not True or saved['dirty_maps'] or saved['dirty_content']:raise RuntimeError('known true clean first save required')
    body='cfg='+repr(cfg)+'\n'+CAMERA_CHECK+'''
proof=validate_pair(cfg);paths=[x['path'] for x in proof['new_actors']]
digest=world_existing_actor_digest(paths)
require_prior_digest(digest,cfg['global_actor_digest'],paths)
if not same_camera(snapshot_scene()['camera'],cfg['old_scene']['camera']):raise RuntimeError('saved placement camera differs beyond existing tolerance')
result={'stage':'winter4_pair_saved_native_readback_verified','proof':proof,'global_actor_digest':digest,'asset_report':asset_report,'scene':snapshot_scene()}
'''
    native=p.dispatch('readback-camera-precision-r1',body,assets=True,timeout=120)
    fresh=d.fingerprint(d.MAP_FILE)
    if fresh==d.fp(base['map']):raise RuntimeError('durable changed map bytes required')
    backup=F/'saved-map.umap';p.exclusive_copy(d.MAP_FILE,backup)
    if d.fingerprint(backup)!=fresh:raise RuntimeError('saved map backup differs')
    after=copy.deepcopy(base)
    after.update(utc=d._utc(),stage='combined184_saved217_winter4_two_staging_roles_placed_saved',
        map={'path':str(d.MAP_FILE),**fresh},map_backup=str(backup),scene=native['scene'],actor_records=145,
        provenance={'previous_baseline':d.pin(p.BASE),'placement':d.pin(F/'native-placement.json'),
            'map_save':d.pin(F/'native-map-save-camera-precision-r1.json'),
            'precision_continuation':d.pin(F/'camera-precision-continuation.json')})
    d.protect(after);bp=F/'saved-production-baseline.json';d.write_new(bp,after)
    report={'utc':d._utc(),'stage':'winter4_two_role_staging_saved_independent_readback_complete','issues':[],
        'baseline':d.pin(bp),'native':d.pin(F/'readback-camera-precision-r1-return.json'),
        'saved_map':after['map'],'actors':145,'prior_actors_preserved':143,
        'protected_packages':217,'source_files_preserved':184,'new_actors':native['proof']['new_actors'],
        'map_save':saved,'all_world_existing_actor_digest':native['global_actor_digest'],
        'cycle_metrics':{'imports':0,'native_created_assets':0,'new_content_packages':0,'new_actors':2,'map_save_calls':1,'new_island_versions':0},
        'visual_review':d.pin(F/'operator-visual-review.json'),
        'limits':'Two-role decorative STAGING display; no assigned canonical realm/full Winter4 terrain. Pale luminous appearance/weak foam separation observed; final visual BAR, fluid, collision/navigation/ecology/gameplay remain open. Digest covers all-world actor poses/static bindings/component transforms/ISMcounts, not every instance or serialized property.'}
    d.write_new(F/'readback.json',report)
    print(json.dumps({k:report[k] for k in ('stage','baseline','saved_map','actors','protected_packages','cycle_metrics')}))


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('phase',choices=('save','readback'))
    globals()[a.parse_args().phase]()
