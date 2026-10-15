"""Build a real modular Garden landing in the existing editor, one actor at a time.

Existing saved assets/palette only. No imports, old-actor edits, deletion, gameplay
or app settings. A retained journal prevents replay after partial/uncertain work.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).parent / 'contest-island-production'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'connectors/claude-asset-pipeline'))
from unreal_mcp.client import Mcp
from asset_pipeline import wire
BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
OUT = BASE / 'codex-garden-landing-r1.world.json'
if OUT.exists():
    raise RuntimeError('existing assembly outcome retained; inspect before any continuation')
m = Mcp(timeout=40)
APP = 'EditorToolset.EditorAppToolset'
SCENE = 'editor_toolset.toolsets.scene.SceneTools'
if m.call(APP, 'IsPIERunning'):
    raise RuntimeError('PIE running; hold placement')
entries = json.loads((BASE / 'codex-workshop.dressing.json').read_text())['entries']
templates = {role: next(row for row in entries if row['label'] == 'CodexDress_CopperPatina_' + role)
             for role in ('crossbeam', 'housing', 'battery')}
PREFIX = 'CodexBuild_GardenLandingR1_'
code = '''# Codex GardenLandingR1 preflight
import unreal,sys
b=sys.modules['claude_unreal_bridge']
others=[req.get('type') for gen,req,box in b._running if req.get('type')!='execute_python' or not (req.get('params') or {}).get('code','').startswith('# Codex GardenLandingR1 preflight')]
if others or b._jobs.qsize() or b._remote_lock.locked():raise RuntimeError('conflicting bridge mutation')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('preserve dirty work')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=sub.get_all_level_actors()
if any(a.get_actor_label().startswith('CodexBuild_GardenLandingR1_') for a in actors):raise RuntimeError('landing actors already exist; do not replay')
def snap(a):
    p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    comps=a.get_components_by_class(unreal.StaticMeshComponent)
    return {'path':a.get_path_name(),'label':a.get_actor_label(),'folder':str(a.get_folder_path()),'location':[p.x,p.y,p.z],'rotation':[r.pitch,r.yaw,r.roll],'scale':[s.x,s.y,s.z],'components':[{'path':c.get_path_name(),'mesh':c.static_mesh.get_path_name() if c.static_mesh else None,'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]} for c in comps]}
result={'world':unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name(),'existing_codex_actors':[snap(a) for a in actors if a.get_actor_label().startswith('Codex')],'templates':{a.get_actor_label():snap(a) for a in actors if a.get_actor_label() in ('CodexDress_CopperPatina_crossbeam','CodexDress_CopperPatina_housing','CodexDress_CopperPatina_battery')}}
'''
before = wire.obj(wire.call(wire.UNREAL, 'execute_python', code=code, unattended=False, timeout=35, side='Unreal'), side='Unreal', what='landing source/preservation preflight')
if before['world'] != '/Game/Daedalus/DaedalusWorld.DaedalusWorld' or len(before['templates']) != 3:
    raise RuntimeError('require exact current owned map and three existing palette templates')
for role, template in templates.items():
    native = before['templates'][template['label']]
    if len(native['components']) != 1 or native['components'][0]['mesh'] != template['mesh_path']:
        raise RuntimeError('existing module/palette contract drift')
# Known source route surface is 1 metre above the saved island origin. Coupler
# bounds are z[-25,+25]cm; setting its centre at floor-25 keeps its top flush.
floor = 18215.324 + 100
plan = []
for index, offset in enumerate((-150, -50, 50, 150)):
    plan.append({'name': PREFIX + 'deck_' + str(index + 1), 'role': 'crossbeam', 'xyz': [-343550 + offset, 325000, floor - 25], 'yaw': 90})
for side, offset in (('west', -125), ('east', 125)):
    plan.append({'name': PREFIX + side + '_housing', 'role': 'housing', 'xyz': [-343550 + offset, 325200, floor], 'yaw': 0})
    plan.append({'name': PREFIX + side + '_crystal', 'role': 'battery', 'xyz': [-343550 + offset, 325200, floor + 100], 'yaw': 0})
record = {'stage': 'bounded_visible_assembly_pending', 'utc': datetime.now(timezone.utc).isoformat(), 'map': before['world'], 'source_route_surface_metres': 1,
          'source_template_receipt': 'codex-workshop.dressing.json', 'before': before, 'plan': plan, 'mutations': [], 'actors': [],
          'new_folder': 'CodexContest/Staging/GardenLandingR1', 'existing_actors_modified': False, 'imports_dispatched': False, 'save_dispatched': False}
def retain():
    OUT.write_text(json.dumps(record, indent=2) + '\n')
with OUT.open('x', encoding='utf-8') as handle:
    json.dump(record, handle, indent=2)
# Keep the actual construction in front of the user, at the same route surface.
camera = {'location': {'x': -343550, 'y': 326150, 'z': floor + 300}, 'rotation': {'pitch': -9, 'yaw': -90, 'roll': 0}, 'scale': {'x': 1, 'y': 1, 'z': 1}}
m.call(APP, 'SetCameraTransform', transform=camera)
m.call('SlateInspectorToolset.SlateInspectorToolset', 'Windows', action='select', index=0)
record['construction_camera'] = m.call(APP, 'GetCameraTransform')
retain()
for row in plan:
    transform = {'location': dict(zip(('x', 'y', 'z'), row['xyz'])), 'rotation': {'pitch': 0, 'yaw': row['yaw'], 'roll': 0}, 'scale': {'x': 1, 'y': 1, 'z': 1}}
    args = {'asset_path': templates[row['role']]['mesh_path'].split('.')[0], 'name': row['name'], 'xform': transform, 'snap_to_ground': False}
    entry = {'tool': 'add_to_scene_from_asset', 'arguments': args, 'state': 'dispatch_pending'}
    record['mutations'].append(entry)
    retain()
    actor = m.call(SCENE, 'add_to_scene_from_asset', **args)
    entry.update(state='responded', result=actor)
    record['actors'].append({'label': row['name'], 'actor': actor, 'role': row['role'], 'mesh_path': templates[row['role']]['mesh_path'], 'transform': transform})
    retain()
    m.call(SCENE, 'set_actor_folder', actor=actor, folder_path=record['new_folder'])
    materials = before['templates'][templates[row['role']]['label']]['components'][0]['materials']
    bind = '# Codex GardenLandingR1 bind new actor only\nimport unreal\na=unreal.find_object(None,' + repr(actor['refPath']) + ')\nif a is None or a.get_actor_label()!=' + repr(row['name']) + ':raise RuntimeError("new actor identity drift")\nc=a.get_component_by_class(unreal.StaticMeshComponent)\npaths=' + repr(materials) + '\nfor i,p in enumerate(paths):\n    mat=unreal.load_asset(p) if p else None\n    if p and mat is None:raise RuntimeError("existing material unavailable")\n    c.set_material(i,mat)\nresult={"actor":a.get_path_name(),"label":a.get_actor_label(),"materials":[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]}\n'
    entry['palette_readback'] = wire.obj(wire.call(wire.UNREAL, 'execute_python', code=bind, unattended=False, timeout=25, side='Unreal'), side='Unreal', what='new landing actor palette')
    record['stage'] = 'visible_assembly_in_progress'
    retain()
    print(json.dumps({'placed': row['name'], 'actor': actor, 'count': len(record['actors'])}), flush=True)
record['stage'] = 'eight_new_actors_placed_unsaved_readback_pending'
retain()
print(json.dumps({'stage': record['stage'], 'receipt': str(OUT), 'new_actors': len(record['actors'])}), flush=True)
