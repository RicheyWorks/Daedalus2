# SPDX-License-Identifier: MIT
"""Capture native views of already-saved Codex staging, through existing clients.

Run only during an accepted editor turn. This changes the viewport camera only;
it does not import, place actors, save the map, or change lighting/exposure.
"""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
import math
import struct
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'connectors/claude-asset-pipeline'))
from unreal_mcp.client import Mcp
from asset_pipeline import wire
from codex_contest_island_delivery import fingerprint
APP='EditorToolset.EditorAppToolset'
SCENE='editor_toolset.toolsets.scene.SceneTools'


def capture(folder, names, revision='native', assembly=None, three_views=False, local_views=None, width=1280, height=720):
    if type(width) is not int or type(height) is not int or not 320<=width<=3840 or not 180<=height<=2160:
        raise ValueError('require bounded native capture dimensions up to3840x2160')
    folder=Path(folder).resolve()
    patches=json.loads((folder/'codex-workshop-source-plan.json').read_text())
    world=json.loads((folder/'codex-workshop.world.json').read_text())
    if world.get('stage')!='placed_and_saved' or world.get('save_return') is not True:
        raise ValueError('saved staging receipt is required')
    if assembly:
        admitted=json.loads(Path(assembly).read_text())
        if admitted.get('stage')!='placed_and_saved' or admitted.get('save_return') is not True:raise ValueError('additional assembly must be saved')
        patches += [{'island':name,'island_origin_cm':origin} for name,origin in admitted['plan']['placements_cm'].items()]
    if not names.issubset({row['island'] for row in patches}):raise ValueError('unknown saved island selection')
    m=Mcp(timeout=30)
    if m.call(APP,'IsPIERunning') or m.call(SCENE,'get_current_level')!='/Game/Daedalus/DaedalusWorld':
        raise RuntimeError('require the agreed map with PIE stopped')
    initial_camera=m.call(APP,'GetCameraTransform')
    before_view=wire.obj(wire.call(wire.UNREAL,'execute_python',code='''import unreal
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
key=les.get_active_viewport_config_key()
result={'key':str(key),'game_view':les.editor_get_game_view(key),'horizontal_fov':les.get_level_viewport_fov(key),
 'dirty_maps':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
 'dirty_content':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
''',unattended=False,timeout=30,side='Unreal'),side='Unreal',what='capture display preflight')
    if before_view['dirty_maps'] or before_view['dirty_content']:raise RuntimeError('preserve unsaved work before presentation capture')
    out=folder/'QA'
    if not revision.replace('_','').replace('-','').isalnum():raise ValueError('capture revision must be filename-safe')
    report=out/('staging.'+revision+'-review.json')
    if report.exists():raise ValueError('retain existing native review receipt')
    views=[('overview',[6500,-8000,5000],[0,0,-300])]
    if three_views:views += [('route',[2800,4900,800],[900,1000,1100]),('crown',[-2200,2600,3300],[0,0,1800])]
    if local_views is not None:
        if three_views:raise ValueError('choose a retained local camera recipe or the default three views')
        views=json.loads(Path(local_views).read_text())
        if not isinstance(views,list) or not 1<=len(views)<=6:raise ValueError('require one to six local centimetre camera rows')
        seen=set()
        for row in views:
            if not isinstance(row,list) or len(row)!=3:raise ValueError('camera row requires name, eye and target offsets')
            name,eye,target=row
            if not isinstance(name,str) or not name.replace('_','').isalnum() or name in seen:raise ValueError('camera names must be unique filename-safe identifiers')
            if any(not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v) for v in (eye,target)) or eye==target:raise ValueError('camera offsets require distinct finite vectors')
            seen.add(name)
    for row in patches:
        if row['island'] in names:
            for view,_,_ in views:
                if (out/(row['island']+'.'+revision+'-'+view+'.png')).exists():raise ValueError('retain existing capture; choose a new revision')
    result={'stage':'native_still_views','map_sha256_at_capture':fingerprint(world['plan']['map_file'])['sha256'],'views':[],
            'acceptance':'appearance only; no movement/collision/final quality acceptance',
            'local_camera_recipe':str(Path(local_views).resolve()) if local_views else 'default',
            'projection':'existing native viewport projection/FOV unchanged','requested_pixels':[width,height],
            'initial_camera':initial_camera,'initial_view':before_view,'capture_calls':[],
            'capture_route':'existing viewport_screenshot -> AutomationLibrary.take_high_res_screenshot; native force_game_view default=true'}
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2);handle.write('\n')
    for row,view,eye_offset,target_offset in ((row,view,eye,target) for row in patches for view,eye,target in views):
        if row['island'] not in names:continue
        origin=list(row['island_origin_cm'])
        centre=[origin[i]+target_offset[i] for i in range(3)]
        eye=[origin[i]+eye_offset[i] for i in range(3)]
        delta=[centre[i]-eye[i] for i in range(3)]
        pose={'location':dict(zip(('x','y','z'),eye)),
              'rotation':{'pitch':math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),'yaw':math.degrees(math.atan2(delta[1],delta[0])),'roll':0},'scale':{'x':1,'y':1,'z':1}}
        action={'island':row['island'],'view':view,'state':'pending_camera','pose':pose}
        result['capture_calls'].append(action);result['stage']='native_capture_pending'
        report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        try:
            m.call(APP,'SetCameraTransform',transform=pose)
            camera=m.call(APP,'GetCameraTransform')
            action['state']='pending_screenshot'
            report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            reply=wire.call(wire.UNREAL,'viewport_screenshot',width=width,height=height,timeout=90,side='Unreal')
        except Exception as error:
            action.update(state='uncertain',error=str(error));result['stage']='capture_inspection_required'
            report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            raise  # no blind capture retry or camera move while its result is unknown
        image=reply.get('result',reply)
        if 'image_png_base64' not in image:raise RuntimeError('native capture did not return image bytes: '+str(reply))
        data=base64.b64decode(image['image_png_base64'])
        path=out/(row['island']+'.'+revision+'-'+view+'.png')
        if path.exists():raise ValueError('retain existing capture; choose a new output revision')
        path.write_bytes(data)
        pixels=list(struct.unpack('>II',data[16:24])) if data[:8]==b'\x89PNG\r\n\x1a\n' and data[12:16]==b'IHDR' else None
        action.update(state='responded',path=str(path),pixels=pixels)
        if pixels!=[width,height]:
            result['stage']='capture_inspection_required'
            report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            raise RuntimeError('retained native PNG dimensions differ from request; no upscale or replay')
        result['views'].append({'island':row['island'],'view':view,'path':str(path),'camera':camera,'sha256':hashlib.sha256(data).hexdigest(),
                                'bytes':len(data),'pixels':pixels,'native_render':True,'upscaled':False,
                                'when_utc':datetime.now(timezone.utc).isoformat()})
        result['stage']='native_capture_responded'
        report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    # Restore temporary camera/game-view display state only after every capture
    # has a known result. Lighting, exposure, FOV and world packages stay intact.
    result['stage']='display_restore_pending'
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    m.call(APP,'SetCameraTransform',transform=initial_camera)
    code='''import unreal
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
key=les.get_active_viewport_config_key()
if str(key)!=KEY:raise RuntimeError('active viewport changed; inspect before display restoration')
if les.editor_get_game_view(key)!=GAME:les.editor_set_game_view(GAME,key)
result={'key':str(key),'game_view':les.editor_get_game_view(key),'horizontal_fov':les.get_level_viewport_fov(key),
 'dirty_maps':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
 'dirty_content':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
'''.replace('KEY',repr(before_view['key'])).replace('GAME',repr(before_view['game_view']))
    after_view=wire.obj(wire.call(wire.UNREAL,'execute_python',code=code,unattended=False,timeout=30,side='Unreal'),side='Unreal',what='capture display restoration')
    result.update(restored_camera=m.call(APP,'GetCameraTransform'),restored_view=after_view,
                  map_unchanged=fingerprint(world['plan']['map_file'])['sha256']==result['map_sha256_at_capture'],stage='native_still_views')
    if after_view!=before_view or result['map_unchanged'] is not True:raise RuntimeError('capture changed display/package state; inspect retained evidence')
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--island',action='append',required=True)
    parser.add_argument('--revision',default='native')
    parser.add_argument('--assembly',type=Path,help='optional additional saved assembly journal')
    parser.add_argument('--three-views',action='store_true')
    parser.add_argument('--local-views',type=Path,help='retained name/eye/target offsets in native centimetres; viewport projection unchanged')
    parser.add_argument('--width',type=int,default=1280)
    parser.add_argument('--height',type=int,default=720)
    args=parser.parse_args()
    print(json.dumps(capture(args.folder,set(args.island),args.revision,args.assembly,args.three_views,args.local_views,args.width,args.height),indent=2))
