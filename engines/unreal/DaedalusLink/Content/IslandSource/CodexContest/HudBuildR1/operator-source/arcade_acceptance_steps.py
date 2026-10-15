"""Prepared native phase strings; import/calling code() never contacts Unreal.

The sole operator sends one returned string through existing execute_python.
Only run in the owned unsaved blank-map PIE, with its cabinet auto_advance=False.
The operator owns backups, fixture creation/removal, receipts, PIE exit and exact
Hero/save restoration. This module never creates/removes a filesystem fixture.
"""
from textwrap import dedent

COMMON = r'''
import unreal,sys,time
from pathlib import Path
bridge=sys.modules.get('claude_unreal_bridge')
if bridge is None:raise RuntimeError('existing bridge unavailable')
other=[req.get('type') for gen,req,box in bridge._running if req.get('type')!='execute_python' or not str((req.get('params') or {}).get('code','')).startswith('# Codex bounded arcade acceptance phase')]
unfinished=sum(not box['done'].is_set() for box,stamp in bridge._job_boxes.values())
if other or bridge._jobs.qsize() or unfinished or bridge._remote_lock.locked():raise RuntimeError('conflicting native work')
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('owned PIE required')
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not w or 'DaedalusWorld' in w.get_path_name():raise RuntimeError('require owned blank-map PIE, never production-world PIE')
actors=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.DaedalusDesktopArcade)
label=CFG.get('actor_label')
if label:actors=[x for x in actors if x.get_actor_label()==label]
if len(actors)!=1:raise RuntimeError('require exactly one owned PIE arcade')
a=actors[0]
if a.get_editor_property('auto_advance'):raise RuntimeError('disable only owned PIE cabinet auto_advance before manual steps; never use two clocks')
def state():
    s=a.get_state()
    return {n:s.get_editor_property(n) for n in ('initialized','open','paused','over','won','save_pending','has_saved_run','id','title','note','persistence_message','score','lives','seed','steps','option')}
def controls(**values):
    c=unreal.DaedalusDesktopArcadeInput()
    for key,value in values.items():c.set_editor_property(key,value)
    a.set_arcade_input(c)
def step(**values):
    controls(**values)
    n=a.advance_game(1.0/60.0)
    a.clear_arcade_input()
    return n
checks=[]
def check(name,passed,detail=None):checks.append({'check':name,'passed':bool(passed),'detail':detail})
result={'phase':CFG['phase'],'world':w.get_path_name(),'arcade':a.get_path_name(),'actor_label':a.get_actor_label(),
    'checks':checks,'input_scope':'programmatic reflected native dispatch, not physical controller evidence','native_ui_or_world_save':False}
'''

PHASES = {
    "logic": r'''
catalog=[{'id':e.id,'title':e.title,'controls':e.controls} for e in a.get_available_games()]
expected={'minesweeper','pong','dungeon','asteroids','football','pacman','sega_shooter','shadow_ninja','star_shooter','dodge_ball','contra','zelda'}
check('exact twelve stable IDs',len(catalog)==12 and {x['id'] for x in catalog}==expected,catalog)
result['games']=[]
for entry in catalog:
    ok=a.start_game(entry['id'],730);initial=state()
    count=step();advanced=state()
    a.restart_game();restarted=state()
    check(entry['id']+' start/one step/restart',ok and initial['id']==entry['id'] and initial['initialized'] and initial['steps']==0 and count==1 and advanced['steps']==1 and restarted['steps']==0 and restarted['id']==entry['id'],{'initial':initial,'advanced':advanced,'restarted':restarted})
    result['games'].append({'id':entry['id'],'start_return':ok,'advance_return':count,'initial':initial,'advanced':advanced,'restarted':restarted})
a.start_game('pong',730)
result['final']=state()
''',
    "source_keys": r'''
a.start_game('contra',730);title=state()
for _ in range(4):step()
frozen=state()
check('Contra title remains title during neutral fixed steps','TITLE' in title['note'] and 'TITLE' in frozen['note'] and frozen['lives']==3,frozen)
for key in (0,0,1,1,2,3,2,3,4,5):a.submit_arcade_source_key(key)
armed=state()
check('ordered raw keyboard bonus arms thirty lives without final-A start',armed['lives']==30 and 'TITLE' in armed['note'],armed)
accepted=a.submit_arcade_source_controller_button(0);started=state()
check('separate controller-A method starts with armed lives',accepted and started['lives']==30 and 'TITLE' not in started['note'],started)
a.restart_game();reset=state()
check('host Restart resets standard three-life active run',reset['lives']==3 and reset['steps']==0 and 'TITLE' not in reset['note'],reset)
a.start_game('contra',730)
for key in (0,0,1,1,2,3,2,3,4,5):a.submit_arcade_source_key(key)
a.submit_arcade_source_key(6);keyboard=state()
check('raw Enter starts armed title',keyboard['lives']==30 and 'TITLE' not in keyboard['note'],keyboard)
a.start_game('shadow_ninja',730);before=state();count=step(jump=True,jump_pressed=True);after=state()
check('Shadow Ninja reflected jump dispatch advances one native step',count==1 and after['id']=='shadow_ninja' and after['steps']==before['steps']+1,after)
result.update(title=title,armed=armed,controller_started=started,keyboard_started=keyboard,shadow_ninja=after)
result['limits']=['Controller source-method dispatch does not prove a physical controller, Slate key handling or hardware lifecycle.','The ordered bonus code belongs to Contra/Ironwake Advance; no Ninja cheat is invented.']
''',
    "mines": r'''
a.start_game('minesweeper',730);initial=state()
step(action_pressed=True);flagged=state()
step(fire_pressed=True);blocked=state()
check('flag first cell and refuse its reveal','Mines remaining 9' in flagged['note'] and blocked['score']==0,{'flagged':flagged,'blocked':blocked})
step(action_pressed=True);unflagged=state()
step(fire_pressed=True);revealed=state()
check('first reveal safe neighbourhood','Mines remaining 10' in unflagged['note'] and revealed['score']>=4 and (not revealed['over'] or revealed['won']),revealed)
option_rows=[]
for option in (0,1,2):
    ok=a.set_game_option(option);s=state();option_rows.append({'option':option,'return':ok,'state':s})
    check('Mines option '+str(option)+' resets board',ok and a.get_game_option()==option and s['score']==0 and not s['over'],s)
a.set_game_option(0);a.restart_game();result.update(initial=initial,first_reveal=revealed,options=option_rows,final=state())
result['limits']=['Grid dimensions, flag glyphs and chord rendering require actual HUD observation; status alone does not expose hidden mine layout.']
''',
    "pong_point": r'''
a.start_game('pong',730)
observed=None
for index in range(600):
    step(up=index<60)
    s=state()
    if 'ready -' in s['note']:
        observed={'manual_steps':index+1,'state':s};break
check('Pong reaches real scored-point preparation within six hundred native steps',observed is not None,observed)
if observed:
    step(jump_pressed=True);early=state()
    check('fresh Jump serves early without score replacement','ready -' not in early['note'] and early['score']==observed['state']['score'],early)
    result['early_serve']=early
result['point']=observed;result['final']=state()
result['limits']=['A bounded point observation is native core evidence; visible ball/paddle/point cues require HUD pixels. No private game state is patched.']
''',
    "star_request": r'''
target=Path('C:/Unreal/DaedalusRealm/Saved/DaedalusDesktopGames/star_shooter.dgs')
if not CFG.get('owned_empty_target_fixture') or not target.is_dir() or any(target.iterdir()):
    raise RuntimeError('operator must first journal/create exact absent-target empty directory fixture; no arbitrary filename or permission changes')
if state()['save_pending']:raise RuntimeError('prior pending save must be reconciled, never replace it')
a.start_game('star_shooter',730);a.pause_game(True)
step(down=True)  # pause menu selection 0 Resume -> 1 Save & Quit
step(fire_pressed=True)
failed=state();observed=time.monotonic()
check('Star failed native write retains pending snapshot',failed['save_pending'] and failed['paused'] and 'Star save failed' in failed['persistence_message'],failed)
replace=a.start_game('pong',730);option=a.set_game_option(0);a.restart_game();a.pause_game(False)
guarded=state()
check('pending Star run rejects replacement/restart/option/unpause',not replace and not option and guarded['id']=='star_shooter' and guarded['save_pending'] and guarded['paused'],guarded)
result.update(failed=failed,guarded=guarded,request_observed_monotonic=observed,fixture=str(target),next_phase='operator removes only its verified empty target directory; wait at least 5.05 real seconds, then star_retry with request_observed_monotonic')
''',
    "star_retry": r'''
target=Path('C:/Unreal/DaedalusRealm/Saved/DaedalusDesktopGames/star_shooter.dgs')
if target.exists():raise RuntimeError('target fixture remains or another writer created output; inspect before retry')
elapsed=time.monotonic()-float(CFG['request_observed_monotonic'])
if elapsed<5.05:raise RuntimeError('five real seconds have not elapsed; no clock patch or blocking sleep')
before=state()
if before['id']!='star_shooter' or not before['save_pending']:raise RuntimeError('exact pending Star run required')
count=a.advance_game(0.0)  # intentionally processes persistence without a simulation step
after=state()
check('real-time retry acknowledges only successful run save',count==0 and not after['save_pending'] and after['has_saved_run'] and target.is_file() and target.stat().st_size<=4096,after)
result.update(elapsed_real_seconds=elapsed,before=before,after=after,advance_return=count)
result['limits']=['Operator fingerprints/archives generated DGS1 bytes and restores original absence/files only after all own callbacks and PIE EndPlay have stopped.','No malformed live saves, ACL changes, read-only flags or security settings are used.']
''',
    "ui_open": r'''
hero=unreal.GameplayStatics.get_player_character(w,0)
pc=unreal.GameplayStatics.get_player_controller(w,0)
if not hero or not isinstance(hero,unreal.DaedalusHero) or not pc or hero.get_controller()!=pc:raise RuntimeError('local possessed DaedalusHero required; no substitute is spawned by this phase')
if state()['save_pending']:raise RuntimeError('reconcile pending save before switching to UI pass')
game=CFG.get('game','pong')
if a.get_selected_game_id()!=game:a.start_game(game,730)
hero.set_actor_location(a.get_actor_location()+unreal.Vector(150,0,0),False,False)
before=state()
if before['open']:raise RuntimeError('close previous owned overlay and let its deferred close finish before fresh Hero Interact')
interaction=hero.interact();after=state()
check('normal Hero Interact opens actual Slate cabinet',after['open'] and after['id']==game,{'interact_return':interaction,'before':before,'after':after})
result.update(hero=hero.get_path_name(),controller=pc.get_path_name(),state=after,interaction_return=interaction)
result['screenshot_plan']='Capture actual active PIE viewport/window including Slate overlay, then inspect title, status/control text, game canvas and clipping. Scene-only capture_view does not establish Slate/HUD rendering. bOpen alone proves widget attachment, not pixels.'
result['limits']=['This method call exercises Hero nearest-Usable dispatch; it does not prove physical E/button input.','Manual native step clock remains sole clock; auto_advance stays false.','Do not interact with Realm or Settings; restore exact Hero progress files after EndPlay.']
''',
    "ui_close": r'''
before=state();a.clear_arcade_input();a.close_arcade()
result.update(before=before,close_dispatched=True,next_phase='allow the normal next core ticker frame, then ui_closed_read; never block the game thread')
''',
    "ui_closed_read": r'''
s=state();check('deferred Slate close completed',not s['open'],s)
result['state']=s
result['limits']=['Record local controller cursor/pause/focus restoration separately; bOpen alone does not prove focus or a physical device.']
''',
}


def code(phase, **config):
    """Return native source only. The caller dispatches and retains its receipt."""
    if phase not in PHASES:
        raise ValueError("unknown phase: " + phase)
    cfg = dict(config, phase=phase)
    return "# Codex bounded arcade acceptance phase " + phase + "\nCFG=" + repr(cfg) + "\n" + dedent(COMMON) + dedent(PHASES[phase])


def phases():
    return tuple(PHASES)
