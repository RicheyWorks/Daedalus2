"""Prepare one unsaved minimal PIE level, with exact production/save backups."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

TASK=Path(__file__).parent
ROOT=TASK/'contest-island-production'
BASE=ROOT/'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
OUT=BASE/'codex-arcade-gameplay-acceptance.json'
BACKUP=TASK/'arcade-acceptance-original-saves'
MAP=Path('C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap')
sys.path.insert(0,str(ROOT/'connectors/claude-asset-pipeline'))
from asset_pipeline import wire

def fp(p):
    h=hashlib.sha256(); size=0
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c);size+=len(c)
    return {'bytes':size,'sha256':h.hexdigest()}
def retain(d):OUT.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
if OUT.exists():raise RuntimeError('Retained acceptance outcome exists; inspect, never replay preparation')
loaded=json.loads((BASE/'codex-arcade-loaded-readback.json').read_text())
assert fp(MAP)==loaded['map_after_read']
paths=[Path('C:/Unreal/DaedalusRealm/Saved/Config')/name for name in ('DaedalusHero.json','DaedalusRealm.sav')]
paths.extend(Path('C:/Unreal/DaedalusRealm/Saved/DaedalusDesktopGames')/name for name in ('star_shooter.dgs','star_shooter.scores'))
BACKUP.mkdir(exist_ok=False)
saved=[]
for i,p in enumerate(paths):
    row={'path':str(p),'exists':p.exists()}
    if p.exists():
        assert p.is_file()
        b=BACKUP/(str(i)+'-'+p.name)
        shutil.copy2(p,b); row.update(original=fp(p),backup=str(b),mtime_ns=p.stat().st_mtime_ns,atime_ns=p.stat().st_atime_ns)
        assert fp(b)==row['original']
    saved.append(row)
assert not paths[2].exists() and not paths[3].exists(),'Existing arcade saves: adjust fixture before native action'
save_dir=paths[2].parent
assert not save_dir.exists(),'Existing arcade directory: inspect its ownership/content first'
tree=ast.parse((TASK/'build_visible_garden_landing.py').read_text())
original=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
snap=original[original.index('def snap(a):'):original.index("result={'world'")]
read='''# Codex minimal native acceptance preparation
import unreal,sys
b=sys.modules['claude_unreal_bridge']
others=[req.get('type') for gen,req,box in b._running if req.get('type')!='execute_python' or not (req.get('params') or {}).get('code','').startswith('# Codex minimal native acceptance preparation')]
if others or b._jobs.qsize() or b._remote_lock.locked():raise RuntimeError('conflicting bridge work')
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('existing PIE')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('dirty user work')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
p,r=e.get_level_viewport_camera_info()
''' + snap + '''
result={'world':e.get_editor_world().get_path_name(),'actors':[snap(a) for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label().startswith('Codex')],
 'camera':{'location':{'x':p.x,'y':p.y,'z':p.z},'rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll}}}
'''
before=wire.obj(wire.call(wire.UNREAL,'execute_python',code=read,unattended=False,timeout=30,side='Unreal'),side='Unreal',what='minimal acceptance saved-world preflight')
assert before['world']=='/Game/Daedalus/DaedalusWorld.DaedalusWorld' and len(before['actors'])==101
baseline={a['path']:a for a in loaded['native']['actors']}
assert {a['path']:a for a in before['actors']}==baseline,'Existing actor fields changed; inspect'
record={'schema':'daedalus.codex-bounded-native-gameplay-acceptance.v1','utc':datetime.now(timezone.utc).isoformat(),
 'stage':'temporary_blank_map_dispatching','user_authorized_gameplay_checks':True,
 'production_before':before,'production_map_before':fp(MAP),'save_backups':saved,
 'arcade_save_directory_existed':False,'production_world_save_dispatched':False,
 'temporary_map_save_dispatched':False,'new_editor':False,'steps':[]}
retain(record)
code='''# Codex prepare minimal unsaved arcade acceptance world
import unreal
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if e.get_editor_world().get_path_name()!='/Game/Daedalus/DaedalusWorld.DaedalusWorld':raise RuntimeError('unexpected current world')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('preserve dirty work')
w=unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
if not w:raise RuntimeError('blank map failed')
w.get_world_settings().set_editor_property('default_game_mode',unreal.DaedalusGameMode)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x=0,y=0,z=-25))
floor.set_actor_label('CodexTransientAcceptance_Floor')
floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube.Cube'))
floor.set_actor_scale3d(unreal.Vector(x=30,y=30,z=.5))
start=actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(x=0,y=0,z=110))
start.set_actor_label('CodexTransientAcceptance_PlayerStart')
arcade=actors.spawn_actor_from_class(unreal.DaedalusDesktopArcade,unreal.Vector(x=180,y=0,z=0))
arcade.set_actor_label('CodexTransientAcceptance_Arcade')
arcade.set_editor_property('auto_advance',False)
arcade.set_editor_property('initial_game_id','pong')
arcade.set_editor_property('initial_seed',730)
e.set_level_viewport_camera_info(unreal.Vector(x=-280,y=-500,z=280),unreal.Rotator(pitch=-15,yaw=55,roll=0))
result={'world':w.get_path_name(),'arcade':arcade.get_path_name(),'cabinet_id':arcade.get_cabinet_id(),
 'game_mode':str(w.get_world_settings().get_editor_property('default_game_mode')),
 'owned_actor_labels':[a.get_actor_label() for a in (floor,start,arcade)],'auto_advance':arcade.get_editor_property('auto_advance')}
'''
native=wire.obj(wire.call(wire.UNREAL,'execute_python',code=code,unattended=False,timeout=60,side='Unreal'),side='Unreal',what='minimal unsaved acceptance level preparation')
record.update(stage='minimal_unsaved_level_prepared',temporary_world=native,prepared_utc=datetime.now(timezone.utc).isoformat())
assert fp(MAP)==record['production_map_before']
retain(record)
print(json.dumps({'stage':record['stage'],'temporary_world':native,'production_map':record['production_map_before'],'save_backups':saved},indent=2))
