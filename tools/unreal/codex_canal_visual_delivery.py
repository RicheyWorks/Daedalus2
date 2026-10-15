"""A single local Winter4 sort-order comparison, with retained baseline and views.

No import, material change, global renderer change or automatic mutation replay.
The operator reviews both matching views before explicitly keeping or reverting.
"""
import argparse
import base64
import copy
import json
from pathlib import Path
import textwrap
import time
from types import SimpleNamespace

import codex_canal_water_placement as p

d = p.d
BASE = p.F / 'saved-production-baseline.json'
F = p.F / 'VisualPolishR1'
HELPER = Path(__file__).with_name('codex_canal_visual_native.py')
WORLD = '/Game/Daedalus/DaedalusWorld'
FOAM_ACTOR = WORLD + '.DaedalusWorld:PersistentLevel.StaticMeshActor_4019'
p.g.MARKER = '# Codex Winter4 local foam order visual comparison R1'


def prepare():
    """Freeze sources and retain exact map bytes before reserving native work."""
    d._lease(); measured = p.resources(); base = d.load(BASE); d.protect(base)
    if F.exists():
        raise RuntimeError('retained visual phase; reconcile rather than replay')
    if base['actor_records'] != 145 or base['package_count'] != 217:
        raise RuntimeError('exact saved Winter4 baseline required')
    F.mkdir()
    before = F / 'before-visual.umap'; p.exclusive_copy(d.MAP_FILE, before)
    if d.fingerprint(before) != d.fp(base['map']):
        raise RuntimeError('exclusive retained map backup differs')
    source_pins = {'host': d.pin(__file__), 'visual_helper': d.pin(HELPER),
                   'placement_helper': d.pin(p.HELPER),
                   'world_guard': d.pin(p.TASK / 'build_gallery_dispatch_spur.py')}
    for name, pin in source_pins.items():
        p.exclusive_copy(pin['path'], F / (name + '-source-used.py'))
    value = {'utc': d._utc(), 'stage': 'local_sort_comparison_source_prepared',
             'baseline': d.pin(BASE), 'map_before': d.pin(before),
             'sources': source_pins, 'resources': measured,
             'previous_placement': d.pin(p.F / 'readback.json'),
             'candidate': {'Water': 0, 'FoamCore': 1, 'sort_distance_offset': 0},
             'scope': 'Only exact saved FoamCore component sort priority; unchanged raw factors, geometry, assets, lighting and global settings.',
             'limits': 'Forced component order may whiten the centre or break distance ordering; retain only after matching and reverse views. No fluid or gameplay acceptance.'}
    d.write_new(F / 'prepared.json', value)
    print(json.dumps(value))


def claim():
    value = d.load(F / 'prepared.json'); d._lease(); p.resources()
    d.protect(d.load(BASE)); d._check(value['baseline']); d._check(value['map_before'])
    for pin in value['sources'].values(): d._check(pin)
    if d.locks().get('compute'):
        raise RuntimeError('active compute reservation; no native claim')
    if (F / 'compute-claim.json').exists():
        raise RuntimeError('retained claim; no re-claim')
    result = d.post('/lock', {'me': d.OWNER, 'name': 'compute', 'ttl': 600,
        'note': 'Winter4 bounded local Foam sort 0/1 comparison: two matching native viewport views, exact owned2 actors only, raw materials/global settings untouched; intended one map save + independent readback/backup. No PIE/import/tests/Blender/render/build/restart.'})
    d.write_new(F / 'compute-claim.json', {'utc': d._utc(), 'claim': result})
    if result.get('ok') is not True or not d.same_compute_lease(d.locks().get('compute', {}), result.get('lock', {})):
        raise RuntimeError('exact bounded compute claim unconfirmed')
    d.post('/heartbeat', {'me': d.OWNER, 'status': 'Winter4 local foam sort comparison: bounded sole-native phase, exact saved217/145/184 retained, no other writer/PIE'})
    print(json.dumps(result))


def custody():
    d._lease(); p.resources()
    value = d.load(F / 'prepared.json')
    for pin in value['sources'].values(): d._check(pin)
    d._check(value['baseline']); d._check(value['map_before']); d._check(value['previous_placement'])
    c = d.load(F / 'compute-claim.json')['claim']['lock']
    if not d.same_compute_lease(d.locks().get('compute', {}), c) or time.time() > c['at'] + c['ttl'] - 100:
        raise RuntimeError('exact compute/deadline reserve required; preserve current state')
    return c


def config():
    base = d.load(BASE); old = d.load(p.F / 'readback.json')
    return {'baseline_scene': base['scene'], 'expected_rows': old['new_actors'], 'foam_actor_path': FOAM_ACTOR,
            'baseline_world_digest': old['all_world_existing_actor_digest']}


def assets(claim):
    value = d.load(p.PACKET / 'prepared.json')
    for pin in [value['native_source'], *value['helpers'].values()]: d._check(pin)
    cfg = p.h.configuration(value, SimpleNamespace(folder=F), claim)
    return d.module_code(value) + '\nasset_cfg=' + repr(cfg) + '''
packet,nodes,scopes=scope['_config'](asset_cfg)
asset_report,objects=scope['_inspect'](asset_cfg,nodes,scopes,final=True,metadata=True)
if asset_report['issues'] or asset_report['triangles']!=2912 or len(objects)!=6:
    raise RuntimeError('unchanged saved six assets/raw-alpha factors required')
'''


def render_settings(value):
    value = copy.deepcopy(value); value.get('viewport', {}).pop('camera', None)
    return value


def dispatch(name, body, *, expected_stage, dirty=False, inspect_assets=False, timeout=100):
    c = custody()
    d.write_new(F / (name + '-dispatch.json'), {'utc': d._utc(),
        'stage': 'dispatch_pending_no_replay', 'compute_claim': d.load(F / 'compute-claim.json'),
        'host': d.pin(__file__), 'helper': d.pin(HELPER)})
    code = p._snap_definition() + '\n' + p.HELPER.read_text() + '\n' + HELPER.read_text() + '\n'
    code += 'cfg=' + repr(config()) + '\nphase_deadline_epoch=' + repr(c['at'] + c['ttl'] - 100) + '''
def phase_deadline():
    if time.time()>phase_deadline_epoch:raise RuntimeError('absolute visual deadline reserve reached; preserve current state')
def dirty_state():
    return {'maps':[x.get_path_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
            'content':[x.get_path_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
def same_camera(actual,wanted):
    return all(math.isfinite(actual[g][k]) and abs(actual[g][k]-v)<=1e-5 for g in ('location','rotation') for k,v in wanted[g].items())
phase_deadline()
'''
    if inspect_assets: code += assets(c)
    code += '\nphase_deadline()\n' + body
    d.write_new(F / (name + '-body-used.json'), code)
    wrapped = 'try:\n' + textwrap.indent(code, '    ') + "\nexcept Exception as exc:\n    import traceback\n    result={'stage':'halted_preserve_partial','error':str(exc),'error_type':type(exc).__name__,'traceback':traceback.format_exc()[-5000:]}\n"
    try:
        result = p.g.native(wrapped, dirty=dirty, timeout=timeout)
    except Exception as exc:
        d.write_new(F / (name + '-host-error.json'), {'utc': d._utc(), 'error': str(exc),
            'error_type': type(exc).__name__, 'bridge_reply': getattr(exc, 'reply', None),
            'outcome': 'uncertain_until_journal_and_readonly_reconciliation; never blindly replay'})
        raise
    d.write_new(F / (name + '-return.json'), result)
    if not isinstance(result, dict) or result.get('stage') != expected_stage:
        raise RuntimeError('native phase halted; reconcile saved reply/journal before further mutation')
    return result


def qualify():
    d.protect(d.load(BASE))
    r = dispatch('qualify', '''
proof=visual_pair(cfg,0)
if not same_camera(proof['scene']['camera'],cfg['baseline_scene']['camera']):raise RuntimeError('precomparison camera differs')
result={'stage':'winter4_local_visual_preflight_readonly','proof':proof,'asset_report':asset_report,
        'renderer':contributing_renderer_readbacks(),'dirty':dirty_state(),'native_mutations':0}
''', expected_stage='winter4_local_visual_preflight_readonly', inspect_assets=True, timeout=120)
    d._same_scene(r['proof']['scene'], d.load(BASE)['scene']); d.protect(d.load(BASE))
    print(json.dumps({'stage': r['stage'], 'dirty': r['dirty'], 'issues': r['asset_report']['issues']}))


def camera(view, state):
    d.protect(d.load(BASE))
    if state not in ('before', 'after'): raise ValueError('explicit before/after required')
    priority = 0 if state == 'before' else 1
    centre = [-292350., 348900., 25400.]
    offset = [3500., 7500., 4500.] if view == 'forward' else [-3500., -7500., 4500.]
    location = [centre[i] + offset[i] for i in range(3)]
    body = 'view=' + repr(view) + '\nlocation=' + repr(location) + '\ntarget=' + repr(centre) + '\nexpected=' + repr(priority) + '''
proof=visual_pair(cfg,expected)
phase_deadline()
e.set_level_viewport_camera_info(unreal.Vector(*location),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*location),unreal.Vector(*target)))
result={'stage':'winter4_visual_camera_only','view':view,'scene':snapshot_scene(),
        'renderer':contributing_renderer_readbacks(),'actor_asset_mutations':0,'dirty':dirty_state()}
'''
    r = dispatch(state + '-' + view, body, expected_stage='winter4_visual_camera_only', dirty=state == 'after')
    if state == 'after':
        before = d.load(F / ('before-' + view + '-return.json'))
        if not all(abs(r['scene']['camera'][g][k] - v) <= 1e-5 for g in ('location', 'rotation') for k, v in before['scene']['camera'][g].items()):
            raise RuntimeError('matching comparison camera differs')
        if render_settings(r['renderer']) != render_settings(before['renderer']):
            raise RuntimeError('contributing rendering settings differ between comparison views')
    custody()
    response = d.wire.call(d.wire.UNREAL, 'viewport_screenshot', width=1280, height=720, timeout=45, side='Unreal')
    payload = response.get('result', response)
    raw = base64.b64decode(payload['image_png_base64'], validate=True)
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise RuntimeError('actual editor PNG required')
    path = F / (state + '-' + view + '.png')
    with path.open('xb') as f: f.write(raw)
    witness = dispatch(state + '-' + view + '-capture-witness', 'expected=' + repr(priority) + '''
proof=visual_pair(cfg,expected)
result={'stage':'winter4_visual_capture_postreadback','scene':proof['scene'],
        'renderer':contributing_renderer_readbacks(),'sort_components':proof['components'],'dirty':dirty_state()}
''', expected_stage='winter4_visual_capture_postreadback', dirty=state == 'after')
    d._same_scene(witness['scene'], r['scene'])
    if render_settings(witness['renderer']) != render_settings(r['renderer']):
        raise RuntimeError('post-capture contributing settings changed; preserve capture as unqualified')
    d.write_new(F / (state + '-' + view + '-image.json'), {'utc': d._utc(), 'image': d.pin(path),
        'scene_camera': r['scene']['camera'], 'renderer': r['renderer'], 'stage': 'actual_editor_viewport_capture',
        'sort_state': {'Water': 0, 'FoamCore': priority}, 'post_capture': d.pin(F / (state + '-' + view + '-capture-witness-return.json')), 'not_gameplay': True})
    d.protect(d.load(BASE)); print(json.dumps(d.pin(path)))


def candidate():
    for view in ('forward', 'reverse'): d.load(F / ('before-' + view + '-image.json'))
    d.protect(d.load(BASE))
    journal = str(F / 'native-candidate.json')
    r = dispatch('candidate', 'journal=' + repr(journal) + '''
proof=visual_pair(cfg,0)
foam=next(a for a in sub.get_all_level_actors() if a.get_path_name()==cfg['foam_actor_path'])
component=foam.get_component_by_class(unreal.StaticMeshComponent)
j=Path(journal);report={'stage':'candidate_intent_recorded','operation':'owned_foam_component_modify_then_set_translucent_sort_priority','old':0,'new':1,'component':component.get_path_name(),'dirty_before':dirty_state()}
phase_deadline()
with j.open('x',encoding='utf-8') as f:json.dump(report,f);f.flush();os.fsync(f.fileno())
phase_deadline();report['modify_return']=component.modify(True);component.set_translucent_sort_priority(1)
report.update(stage='candidate_priority_set_readback',proof=visual_pair(cfg,1),dirty_after=dirty_state())
with j.open('w',encoding='utf-8') as f:json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
result=report
''', expected_stage='candidate_priority_set_readback', timeout=120)
    print(json.dumps({'stage': r['stage'], 'dirty_after': r['dirty_after']}))


def finish(decision):
    """Only after personal visual review: retain candidate or restore default."""
    review = d.load(F / 'operator-visual-review.json')
    if review['decision'] != decision or review.get('personally_inspected_four_images') is not True:
        raise RuntimeError('explicit matching two-view personal review required')
    reviewed_settings = None
    for state in ('before', 'after'):
        for view in ('forward', 'reverse'):
            image = d.load(F / (state + '-' + view + '-image.json'))
            d._check(image['image']); d._check(image['post_capture'])
            settings = render_settings(image['renderer'])
            if reviewed_settings is not None and settings != reviewed_settings:
                raise RuntimeError('all four reviewed contributing settings must match')
            reviewed_settings = settings
    d.protect(d.load(BASE))
    r = dispatch('finish-' + decision, 'decision=' + repr(decision) + '\nreviewed_settings=' + repr(reviewed_settings) + '\njournal=' + repr(str(F / 'native-finish.json')) + '''
proof=visual_pair(cfg,1)
current_settings=contributing_renderer_readbacks();current_settings.get('viewport',{}).pop('camera',None)
if current_settings!=reviewed_settings:raise RuntimeError('contributing renderer state drift after reviewed captures')
j=Path(journal);report={'stage':'visual_finish_admitted','decision':decision,'save_return':None,'intents':[]}
def keep():
    with j.open('w',encoding='utf-8') as f:json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
def intent(operation):phase_deadline();report['intents'].append(operation);keep()
with j.open('x',encoding='utf-8') as f:json.dump(report,f);f.flush();os.fsync(f.fileno())
if decision=='revert':
    component=next(a for a in sub.get_all_level_actors() if a.get_path_name()==cfg['foam_actor_path']).get_component_by_class(unreal.StaticMeshComponent)
    intent('restore_only_owned_foam_priority0');report['restore_modify_return']=component.modify(True);component.set_translucent_sort_priority(0)
intent('restore_original_viewport_camera')
c=cfg['baseline_scene']['camera'];e.set_level_viewport_camera_info(unreal.Vector(**c['location']),unreal.Rotator(pitch=c['rotation']['pitch'],yaw=c['rotation']['yaw'],roll=c['rotation']['roll']))
proof=visual_pair(cfg,1 if decision=='keep' else 0)
if not same_camera(proof['scene']['camera'],cfg['baseline_scene']['camera']):raise RuntimeError('restored camera differs beyond existing tolerance')
if dirty_state()['content']:raise RuntimeError('unexpected content edits; preserve state')
report['proof_before_save']=proof
intent('save_only_owned_intended_world_map')
phase_deadline();started=time.perf_counter();report['save_return']=bool(unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Daedalus/DaedalusWorld'));report['save_s']=round(time.perf_counter()-started,6)
report.update(stage='visual_finish_map_save_returned',dirty_after=dirty_state());keep();result=report
''', expected_stage='visual_finish_map_save_returned', dirty=True, timeout=120)
    if r.get('save_return') is not True or r['dirty_after'] != {'maps': [], 'content': []}:
        raise RuntimeError('true clean intended save not confirmed; never replay')
    print(json.dumps({k: r[k] for k in ('stage', 'decision', 'save_return', 'save_s', 'dirty_after')}))


def reconcile():
    """Read-only observation after an interrupted phase; never replays it."""
    r = dispatch('reconcile', '''
component=next(a for a in sub.get_all_level_actors() if a.get_path_name()==cfg['foam_actor_path']).get_component_by_class(unreal.StaticMeshComponent)
priority=component.get_editor_property('translucency_sort_priority')
proof=visual_pair(cfg,priority)
result={'stage':'winter4_visual_readonly_reconciled','priority':priority,'proof':proof,
        'asset_report':asset_report,'dirty':dirty_state(),'native_mutations':0}
''', expected_stage='winter4_visual_readonly_reconciled', dirty=True, inspect_assets=True, timeout=120)
    print(json.dumps({'stage': r['stage'], 'priority': r['priority'], 'dirty': r['dirty']}))


def abort():
    """One explicit restoration after read-only reconciliation, before any save.

    A pending/uncertain save or prior restoration is a hold, not a replay route.
    This needs no completed images and never clears dirty flags artificially.
    """
    observed = d.load(F / 'reconcile-return.json')
    if observed.get('stage') != 'winter4_visual_readonly_reconciled':
        raise RuntimeError('known read-only reconciliation required before restoration')
    if (F / 'native-finish.json').exists() or any(F.glob('finish-*-dispatch.json')):
        raise RuntimeError('save dispatch may already exist; reconcile it without another save')
    d.protect(d.load(BASE))
    r = dispatch('abort', 'expected=' + repr(observed['priority']) + '\njournal=' + repr(str(F / 'native-abort.json')) + '''
proof=visual_pair(cfg,expected)
j=Path(journal);report={'stage':'explicit_restoration_intent','decision':'revert','save_return':None,'intents':[],'reason':'Interrupted comparison; restore known baseline only, no visual improvement claim.'}
def keep():
    with j.open('w',encoding='utf-8') as f:json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
def intent(operation):phase_deadline();report['intents'].append(operation);keep()
with j.open('x',encoding='utf-8') as f:json.dump(report,f);f.flush();os.fsync(f.fileno())
if expected==1:
    component=next(a for a in sub.get_all_level_actors() if a.get_path_name()==cfg['foam_actor_path']).get_component_by_class(unreal.StaticMeshComponent)
    intent('restore_owned_foam_priority0');report['modify_return']=component.modify(True);component.set_translucent_sort_priority(0)
intent('restore_original_camera')
c=cfg['baseline_scene']['camera'];e.set_level_viewport_camera_info(unreal.Vector(**c['location']),unreal.Rotator(pitch=c['rotation']['pitch'],yaw=c['rotation']['yaw'],roll=c['rotation']['roll']))
proof=visual_pair(cfg,0)
if not same_camera(proof['scene']['camera'],cfg['baseline_scene']['camera']):raise RuntimeError('restoration camera differs')
if dirty_state()['content']:raise RuntimeError('unexpected content dirty; preserve state')
intent('one_explicit_restoration_map_save')
phase_deadline();started=time.perf_counter();report['save_return']=bool(unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Daedalus/DaedalusWorld'));report['save_s']=round(time.perf_counter()-started,6)
report.update(stage='explicit_restoration_save_returned',proof=proof,dirty_after=dirty_state());keep();result=report
''', expected_stage='explicit_restoration_save_returned', dirty=True, inspect_assets=True, timeout=120)
    if r.get('save_return') is not True or r['dirty_after'] != {'maps': [], 'content': []}:
        raise RuntimeError('restoration save not confirmed; no replay')
    print(json.dumps({'stage': r['stage'], 'save_return': r['save_return'], 'save_s': r['save_s']}))


def readback():
    saved_path = F / ('native-finish.json' if (F / 'native-finish.json').exists() else 'native-abort.json')
    saved = d.load(saved_path); decision = saved['decision']
    if saved.get('save_return') is not True: raise RuntimeError('known true first save required')
    r = dispatch('readback', 'expected=' + repr(1 if decision == 'keep' else 0) + '''
proof=visual_pair(cfg,expected)
if not same_camera(proof['scene']['camera'],cfg['baseline_scene']['camera']):raise RuntimeError('saved camera differs')
result={'stage':'winter4_local_visual_saved_readback','proof':proof,'asset_report':asset_report,
        'renderer':contributing_renderer_readbacks(),'dirty':dirty_state()}
''', expected_stage='winter4_local_visual_saved_readback', inspect_assets=True, timeout=120)
    if r['dirty'] != {'maps': [], 'content': []}: raise RuntimeError('saved readback must be clean')
    current = d.fingerprint(d.MAP_FILE); backup = F / 'saved-map.umap'; p.exclusive_copy(d.MAP_FILE, backup)
    if d.fingerprint(backup) != current: raise RuntimeError('saved map backup differs')
    after = copy.deepcopy(d.load(BASE))
    after.update(utc=d._utc(), stage='winter4_local_visual_' + decision + '_saved_readback',
        map={'path': str(d.MAP_FILE), **current}, map_backup=str(backup), scene=r['proof']['scene'],
        component_visual_state={'Winter4Water': 0, 'Winter4FoamCore': 1 if decision == 'keep' else 0,
            'distance_offset': 0, 'proof': d.pin(F / 'readback-return.json')},
        provenance={'previous_baseline': d.pin(BASE),
            'visual_review': d.pin(F / 'operator-visual-review.json') if (F / 'operator-visual-review.json').exists() else None,
            'map_save': d.pin(saved_path)})
    d.protect(after); d.write_new(F / 'saved-production-baseline.json', after)
    completion = {'utc': d._utc(), 'stage': 'winter4_local_visual_comparison_complete', 'decision': decision,
        'baseline': d.pin(F / 'saved-production-baseline.json'), 'readback': d.pin(F / 'readback-return.json'),
        'map': after['map'], 'save_return': True, 'save_s': saved['save_s'],
        'actor_records': 145, 'protected_packages': 217, 'source_files': 184,
        'visual_review': after['provenance']['visual_review'], 'asset_report_issues': r['asset_report']['issues'],
        'comparison_aborted': saved_path.name == 'native-abort.json',
        'cycle_metrics': {'imports': 0, 'created_assets': 0, 'new_actors': 0, 'map_save_calls': 1},
        'limits': 'Two decorative STAGING tubes, no receiving realm context/fluid/navigation/gameplay acceptance. Forced whole-component order is a presentation choice, not general intersecting-transparency correctness. Effective viewport EV/showflags lack verified public getters.'}
    d.write_new(F / 'completion.json', completion); print(json.dumps(completion))


def release():
    completed = d.load(F / 'completion.json'); custody()
    if d.load(F / 'readback-return.json')['dirty'] != {'maps': [], 'content': []}:
        raise RuntimeError('known clean completed native readback required for release')
    d.protect(d.load(completed['baseline']['path']))
    result = d.post('/unlock', {'me': d.OWNER, 'name': 'compute'})
    locks_after = d.locks()
    d.write_new(F / 'compute-release.json', {'utc': d._utc(), 'result': result,
        'locks_after': locks_after, 'last_native': d.pin(F / 'readback-return.json'),
        'native_operations_after_readback': 0})
    if result.get('ok') is not True or locks_after.get('compute'):
        raise RuntimeError('explicit compute release not confirmed')
    print(json.dumps({'utc': d._utc(), 'stage': 'compute_released', 'result': result}))


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('phase', choices=('prepare', 'claim', 'qualify', 'camera', 'candidate', 'finish', 'readback', 'reconcile', 'abort', 'release'))
    a.add_argument('--view', choices=('forward', 'reverse')); a.add_argument('--state', choices=('before', 'after'))
    a.add_argument('--decision', choices=('keep', 'revert')); args = a.parse_args()
    if args.phase == 'camera': camera(args.view, args.state)
    elif args.phase == 'finish': finish(args.decision)
    else: globals()[args.phase]()
