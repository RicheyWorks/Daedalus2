"""Add only the saved Winter4 pair to a qualified owned staging slot.

Reuse the existing world guard, Canal asset inspection and scene snapshots.
Every dispatch is exclusive. A partial/unknown outcome forbids mutation replay.
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import textwrap
import time
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
TASK = REPO.parent
sys.path.insert(0, str(TASK))
sys.path.insert(0, str(REPO / 'tools/unreal'))
import codex_canal_water_delivery as h
from codex_static_intake_delivery import _snap_definition
import build_gallery_dispatch_spur as g

d = h.d
PACKET = TASK / 'native-ingestion/Winter4CanalStream1CoreR2/RecoveryObservedAliasR5'
BASE = PACKET / 'saved-production-baseline.json'
F = PACKET.parent / 'PlacementR1'
HELPER = REPO / 'tools/unreal/codex_canal_water_placement_native.py'
PREFIX = 'CodexStage_Winter4Stream1CoreR1_'
g.MARKER = '# Codex saved Winter4 two-role staging placement R1'
WORLD = '/Game/Daedalus/DaedalusWorld'


def resources():
    return h.resources(SimpleNamespace(minimum_free_physical_mib=1024,
                                      minimum_free_commit_mib=1536))


def exclusive_copy(source, target):
    with Path(source).open('rb') as incoming, Path(target).open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing, length=1024*1024)
        outgoing.flush()
        import os
        os.fsync(outgoing.fileno())


def claim():
    if F.exists():
        raise RuntimeError('retained placement state forbids a fresh claim')
    d._lease(); measured = resources()
    base = d.load(BASE); d.protect(base)
    if (d.fingerprint(BASE)['sha256'] != 'f0b8cd56a858d99dfd35176ab05f314fe5712530fd3661ca8729c2d0cec2efd3'
            or base['package_count'] != 217 or base['actor_records'] != 143):
        raise RuntimeError('exact current saved217/143 baseline required')
    if 'compute' in d.locks():
        raise RuntimeError('another compute owner must finish and release')
    F.mkdir()
    for source, name in [(Path(__file__), 'placement-source-used.py'),
                         (HELPER, 'native-helper-source-used.py'),
                         (TASK / 'build_gallery_dispatch_spur.py', 'existing-world-guard-source-used.py')]:
        shutil.copyfile(source, F / name)
    d.write_new(F / 'preclaim.json', {'utc':d._utc(), 'resources':measured,
        'baseline':d.pin(BASE), 'source':d.pin(Path(__file__)), 'helper':d.pin(HELPER),
        'world_guard':d.pin(TASK / 'build_gallery_dispatch_spur.py'),
        'intake_readback':d.pin(PACKET / 'readback.json')})
    result = d.post('/lock', {'me':d.OWNER, 'name':'compute', 'ttl':600,
        'note':'Winter4 saved2-role staging only: qualify empty owned slot, two decorative unit-scale actors, native fixed views, ONE intended map save+backup/readback; no imports/assets/PIE/tests/render or showcase interference. Preserve217packages143prioractors184sources.'})
    d.write_new(F / 'compute-claim.json', {'utc':d._utc(), 'claim':result})
    if result.get('ok') is not True or not d.same_compute_lease(d.locks().get('compute', {}), result['lock']):
        raise RuntimeError('exact bounded placement claim unconfirmed')
    print(json.dumps({'stage':'placement_compute_claimed','claim':result,'resources':measured}))


def custody():
    d._lease(); resources()
    c = d.load(F / 'compute-claim.json')['claim']['lock']
    if (not d.same_compute_lease(d.locks().get('compute', {}), c)
            or time.time() > c['at'] + c['ttl'] - 100):
        raise RuntimeError('exact placement lease/deadline reserve required')
    value = d.load(F / 'preclaim.json')
    for key in ('baseline','source','helper','world_guard','intake_readback'):
        d._check(value[key])
    return c


def asset_code():
    v = d.load(PACKET / 'prepared.json')
    for p in [v['native_source'], *v['helpers'].values()]:
        d._check(p)
    cfg = h.configuration(v, SimpleNamespace(folder=F), custody())
    return d.module_code(v) + '\nasset_cfg=' + repr(cfg) + '''
packet,nodes,scopes=scope['_config'](asset_cfg)
asset_report,objects=scope['_inspect'](asset_cfg,nodes,scopes,final=True,metadata=True)
if asset_report['issues'] or asset_report['triangles']!=2912 or len(objects)!=6:raise RuntimeError('exact saved Canal six/geometry/raw-alpha proof required')
'''


def dispatch(phase, body, *, dirty=False, assets=False, timeout=100):
    bounded_claim = custody()
    d.write_new(F / (phase+'-dispatch.json'), {'utc':d._utc(),
        'stage':'dispatch_pending_no_replay', 'source':d.pin(__file__),
        'helper':d.pin(HELPER), 'native_mutation_scope':phase,
        'compute_claim':d.load(F / 'compute-claim.json')})
    code = _snap_definition() + '\n' + HELPER.read_text(encoding='utf-8') + '\n'
    code += 'phase_deadline_epoch=' + repr(bounded_claim['at']+bounded_claim['ttl']-100) + '''
def phase_deadline():
    if time.time()>phase_deadline_epoch:raise RuntimeError('absolute placement deadline reserve reached; preserve partial state')
def require_prior_digest(observed,expected,excluded_paths=()):
    if observed.get('excluded_paths')!=sorted(excluded_paths) or expected.get('excluded_paths')!=[]:raise RuntimeError('explicit prior-digest exclusions differ')
    if {k:v for k,v in observed.items() if k!='excluded_paths'}!={k:v for k,v in expected.items() if k!='excluded_paths'}:raise RuntimeError('prior all-world actor/component digest differs')
phase_deadline()
'''
    if assets:
        code += asset_code()
    code += '\nphase_deadline()\n' + body
    d.write_new(F / (phase+'-body-used.json'), code)
    wrapped = ('try:\n' + textwrap.indent(code, '    ')
               + "\nexcept Exception as exc:\n    import traceback\n    result={'stage':'halted_preserve_partial','error':str(exc),'error_type':type(exc).__name__,'traceback':traceback.format_exc()[-5000:]}\n")
    try:
        result = g.native(wrapped, dirty=dirty, timeout=timeout)
    except Exception as exc:
        d.write_new(F / (phase+'-host-error.json'), {'utc':d._utc(), 'error':str(exc),
            'error_type':type(exc).__name__, 'bridge_reply':getattr(exc,'reply',None),
            'outcome':'reconcile_journal_before_any_mutation_retry'})
        raise
    d.write_new(F / (phase+'-return.json'), result)
    if not isinstance(result, dict) or result.get('stage') == 'halted_preserve_partial':
        raise RuntimeError('native phase halted; inspect retained reply/journal; never replay')
    return result


def recipe():
    r = d.load(PACKET / 'readback.json')
    local = {'min':[min(x['geometry']['native_source_bounds_cm']['min'][i] for x in r['native']['items']) for i in range(3)],
             'max':[max(x['geometry']['native_source_bounds_cm']['max'][i] for x in r['native']['items']) for i in range(3)]}
    centre = [(local['min'][i]+local['max'][i])/2 for i in range(3)]
    rows = [{'role':x['source_role'], 'label':PREFIX+('Water' if x['source_role']==h.NAMES[0] else 'FoamCore'),
             'mesh':x['path'], 'material':x['material_path'], 'owned_parent':x['owned_parent']} for x in r['native']['items']]
    slots = [[-292350.,348900.,24000.],[-266750.,348900.,24000.],[-292350.,374500.,24000.]]
    return {'rows':rows, 'candidates':[{'name':'OwnedStagingSlot'+str(n+1),
        'centre_cm':c, 'translation_cm':[c[i]-centre[i] for i in range(3)],
        'local_bounds':local} for n,c in enumerate(slots)],
        'local_bounds':local, 'old_scene':d.load(BASE)['scene'],
        'intent':'NEW owned visual staging allocation; source handoff has no receiving transform/canonical realm. Preserve nested source pair; no invented terrain connection.',
        'collision':'decorative NO_COLLISION; no physics/navigation/fluid claims'}


def prepare():
    custody(); base=d.load(BASE); d.protect(base)
    backup=F/'before-placement.umap'
    if any(p.exists() for p in (backup,F/'prepared.json',F/'prepare-dispatch.json')):
        raise RuntimeError('retained preparation/backup forbids replay or overwrite')
    exclusive_copy(d.MAP_FILE,backup)
    if d.fingerprint(backup)!=d.fp(base['map']):raise RuntimeError('pre-placement map backup differs')
    cfg=recipe()
    body='cfg='+repr(cfg)+'''
scene=snapshot_scene()
assert_old(cfg['old_scene'])
prototype=unreal.get_default_object(unreal.StaticMeshActor).get_component_by_class(unreal.StaticMeshComponent)
defaults={'sort_priority':int(prototype.get_editor_property('translucency_sort_priority')),'sort_distance_offset':float(prototype.get_editor_property('translucency_sort_distance_offset')),'physics':bool(prototype.is_simulating_physics())}
if defaults!={'sort_priority':0,'sort_distance_offset':0.,'physics':False}:raise RuntimeError('unsupported actor defaults; resolve before spawning')
result={'stage':'winter4_empty_staging_qualified','scene':scene,'global_actor_digest':world_existing_actor_digest(),'clearance':clearance(cfg),'asset_report':asset_report,'component_defaults':defaults,'native_mutations':0}
'''
    result=dispatch('prepare',body,assets=True,timeout=120)
    d._same_scene(result['scene'],base['scene']);d.protect(base)
    candidates=result['clearance']['candidates']
    clear=[x for x in candidates if x['blocker_count']==0]
    if not clear:raise RuntimeError('all proposed staging volumes have actual blockers; no placement')
    selected=next(c for c in cfg['candidates'] if c['name']==clear[0]['name'])
    cfg.update(translation_cm=selected['translation_cm'],selected=selected,
               candidates=[selected],global_actor_digest=result['global_actor_digest'])
    d.write_new(F/'prepared.json',{'utc':d._utc(),'stage':'saved_pair_staging_prepared',
        'baseline':d.pin(BASE),'plan':cfg,'qualification':d.pin(F/'prepare-return.json'),
        'map_before_backup':d.pin(backup),'source':d.pin(__file__),'helper':d.pin(HELPER)})
    print(json.dumps({'stage':'saved_pair_staging_prepared','selected':selected,'qualification':result['clearance']}))


def plan():
    p=d.load(F/'prepared.json')
    for k in ('baseline','source','helper','qualification','map_before_backup'):d._check(p[k])
    return p['plan']


def place():
    custody();base=d.load(BASE);d.protect(base);cfg=plan();cfg['journal']=str(F/'native-placement.json')
    body='cfg='+repr(cfg)+'''
assert_old(cfg['old_scene'])
require_prior_digest(world_existing_actor_digest(),cfg['global_actor_digest'])
if clearance(cfg)['candidates'][0]['blocker_count']!=0:raise RuntimeError('staging clearance changed')
if any(a.get_actor_label().startswith('CodexStage_Winter4Stream1CoreR1_') for a in sub.get_all_level_actors()):raise RuntimeError('existing pair; no replay')
j=Path(cfg['journal']);report={'stage':'placement_started','actors':[],'intents':[],'map_saved':False}
def keep():
 with j.open('w',encoding='utf-8') as f:json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
def intent(operation,**values):phase_deadline();report['intents'].append(dict(operation=operation,**values));keep()
phase_deadline()
with j.open('x',encoding='utf-8') as f:json.dump(report,f);f.flush();os.fsync(f.fileno())
for row in cfg['rows']:
 mesh=unreal.load_asset(row['mesh']);mic=unreal.load_asset(row['material'])
 if not isinstance(mesh,unreal.StaticMesh) or not isinstance(mic,unreal.MaterialInstanceConstant) or mesh.get_material(0)!=mic or mic.get_editor_property('parent').get_path_name()!=row['owned_parent']:raise RuntimeError('saved role/material chain differs')
 intent('spawn_saved_role',role=row['role'])
 actor=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*cfg['translation_cm']))
 report['actors'].append({'path':actor.get_path_name(),'role':row['role'],'stage':'spawned_bind_pending'});keep()
 intent('set_new_actor_label',path=actor.get_path_name());actor.set_actor_label(row['label'])
 intent('set_new_actor_folder',path=actor.get_path_name());actor.set_folder_path('CodexContest/Staging/Winter4Stream1CoreR1')
 intent('set_new_actor_rotation',path=actor.get_path_name());actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0),False)
 intent('set_new_actor_scale',path=actor.get_path_name());actor.set_actor_scale3d(unreal.Vector(1,1,1))
 component=actor.get_component_by_class(unreal.StaticMeshComponent)
 intent('bind_saved_mesh',path=component.get_path_name())
 if not component.set_static_mesh(mesh):raise RuntimeError('new role mesh binding failed')
 intent('disable_new_component_collision',path=component.get_path_name());component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
 report['actors'][-1].update(stage='saved_source_layout_bound',label=row['label']);keep()
proof=validate_pair(cfg)
paths=[x['path'] for x in report['actors']]
require_prior_digest(world_existing_actor_digest(paths),cfg['global_actor_digest'],paths)
report.update(stage='two_winter4_roles_placed_unsaved',proof=proof);keep();result=report
'''
    result=dispatch('place',body,timeout=120)
    if result['stage']!='two_winter4_roles_placed_unsaved' or len(result['actors'])!=2:raise RuntimeError('exact placed pair required')
    d.protect(base);print(json.dumps({'stage':result['stage'],'actors':result['actors']}))


def camera(name):
    custody();base=d.load(BASE);d.protect(base);cfg=plan()
    selected=cfg['selected'];centre=selected['centre_cm']
    if name=='wide':
        target=centre;location=[centre[i]+[16000,28000,18000][i] for i in range(3)]
    elif name=='detail':
        target=[centre[0],centre[1],centre[2]+1400];location=[target[i]+[3500,7500,4500][i] for i in range(3)]
    else:
        target=None;location=None
    cfg.update(view=name,location=location,target=target)
    body='cfg='+repr(cfg)+'''
proof=validate_pair(cfg)
paths=[x['path'] for x in proof['new_actors']]
require_prior_digest(world_existing_actor_digest(paths),cfg['global_actor_digest'],paths)
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
phase_deadline()
if cfg['view']=='restore':
 c=cfg['old_scene']['camera'];e.set_level_viewport_camera_info(unreal.Vector(**c['location']),unreal.Rotator(pitch=c['rotation']['pitch'],yaw=c['rotation']['yaw'],roll=c['rotation']['roll']))
else:
 location=unreal.Vector(*cfg['location']);target=unreal.Vector(*cfg['target']);e.set_level_viewport_camera_info(location,unreal.MathLibrary.find_look_at_rotation(location,target))
result={'stage':'winter4_camera_only_set','view':cfg['view'],'scene':snapshot_scene(),'new_actors':proof['new_actors'],'persistent_actor_asset_edits':0,'map_save_calls':0}
'''
    result=dispatch('camera-'+name,body,dirty=True)
    if name=='restore':
        actual=result['scene']['camera'];wanted=base['scene']['camera']
        if any(abs(actual[g][k]-v)>1e-5 for g in wanted for k,v in wanted[g].items()):raise RuntimeError('original camera restoration differs')
    else:
        custody()
        response=d.wire.call(d.wire.UNREAL,'viewport_screenshot',width=1280,height=720,timeout=45,side='Unreal')
        payload=response.get('result',response);raw=base64.b64decode(payload['image_png_base64'],validate=True)
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('native editor PNG required')
        image=F/('UnrealEditor_Winter4_STAGING_'+name+'.png')
        with image.open('xb') as f:f.write(raw)
        d.write_new(F/('camera-'+name+'-image.json'),{'utc':d._utc(),'stage':'actual_unreal_editor_viewport_capture','image':d.pin(image),'scene':result['scene'],'not_gameplay':True,'personal_visual_review':'pending'})
        print(json.dumps(d.pin(image)))
    d.protect(base)


def save():
    custody();base=d.load(BASE);d.protect(base);cfg=plan();cfg['journal']=str(F/'native-map-save.json')
    body='cfg='+repr(cfg)+'''
proof=validate_pair(cfg)
if snapshot_scene()['camera']!=cfg['old_scene']['camera']:raise RuntimeError('restore exact previous camera before map save')
paths=[x['path'] for x in proof['new_actors']]
require_prior_digest(world_existing_actor_digest(paths),cfg['global_actor_digest'],paths)
phase_deadline()
j=Path(cfg['journal']);report={'stage':'map_save_dispatch_pending','save_return':None,'new_actors':proof['new_actors']}
with j.open('x',encoding='utf-8') as f:json.dump(report,f);f.flush();os.fsync(f.fileno())
phase_deadline();start=time.perf_counter();report['save_return']=bool(unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Daedalus/DaedalusWorld'));report['save_s']=round(time.perf_counter()-start,6)
report.update(stage='winter4_map_save_returned',dirty_maps=[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],dirty_content=[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
with j.open('w',encoding='utf-8') as f:json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
result=report
'''
    result=dispatch('save',body,dirty=True,timeout=120)
    if result.get('save_return') is not True or result['dirty_maps'] or result['dirty_content']:raise RuntimeError('true clean intended map save not confirmed; no replay')
    print(json.dumps({k:result[k] for k in ('stage','save_return','save_s','dirty_maps','dirty_content')}))


def readback():
    custody();base=d.load(BASE);cfg=plan();saved=d.load(F/'native-map-save.json')
    if saved.get('save_return') is not True:raise RuntimeError('known saved map required')
    body='cfg='+repr(cfg)+'''
proof=validate_pair(cfg);paths=[x['path'] for x in proof['new_actors']]
digest=world_existing_actor_digest(paths)
require_prior_digest(digest,cfg['global_actor_digest'],paths)
if snapshot_scene()['camera']!=cfg['old_scene']['camera']:raise RuntimeError('saved placement camera differs')
result={'stage':'winter4_pair_saved_native_readback_verified','proof':proof,'global_actor_digest':digest,'asset_report':asset_report,'scene':snapshot_scene()}
'''
    result=dispatch('readback',body,assets=True,timeout=120)
    fresh=d.fingerprint(d.MAP_FILE)
    if fresh==d.fp(base['map']):raise RuntimeError('durable changed map bytes required')
    backup=F/'saved-map.umap';exclusive_copy(d.MAP_FILE,backup)
    if d.fingerprint(backup)!=fresh:raise RuntimeError('saved map backup differs')
    after=copy.deepcopy(base)
    after.update(utc=d._utc(),stage='combined184_saved217_winter4_two_staging_roles_placed_saved',
        map={'path':str(d.MAP_FILE),**fresh},map_backup=str(backup),scene=result['scene'],actor_records=145,
        provenance={'previous_baseline':d.pin(BASE),'placement':d.pin(F/'native-placement.json'),'map_save':d.pin(F/'native-map-save.json')})
    d.protect(after);bp=F/'saved-production-baseline.json';d.write_new(bp,after)
    report={'utc':d._utc(),'stage':'winter4_two_role_staging_saved_independent_readback_complete',
        'issues':[],'baseline':d.pin(bp),'native':d.pin(F/'readback-return.json'),'saved_map':after['map'],
        'actors':145,'prior_actors_preserved':143,'protected_packages':217,'source_files_preserved':184,
        'new_actors':result['proof']['new_actors'],'map_save':saved,
        'cycle_metrics':{'imports':0,'native_created_assets':0,'new_content_packages':0,'new_actors':2,'map_save_calls':1,'new_island_versions':0},
        'limits':'Two-role decorative STAGING display; canonical realm unspecified. No whole Winter island/terrain, fluid, collision, navigation, ecology or gameplay acceptance. All-world digest covers actor poses/static component bindings/transforms/ISMcounts, not every instance transform or serialized property.'}
    d.write_new(F/'readback.json',report);print(json.dumps(report,indent=2))


def release():
    custody();report=d.load(F/'readback.json');base=d.load(report['baseline']['path']);d.protect(base)
    result=d.post('/unlock',{'me':d.OWNER,'name':'compute'})
    if result.get('ok') is not True or result.get('lock') is not None:raise RuntimeError('release unconfirmed')
    d.write_new(F/'compute-release.json',{'utc':d._utc(),'release':result,'locks_after':d.locks()})
    print(json.dumps({'stage':'winter4_placement_compute_released','release':result}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('claim','prepare','place','wide','detail','restore','save','readback','release'))
    phase=p.parse_args().phase
    camera(phase) if phase in ('wide','detail','restore') else globals()[phase]()
