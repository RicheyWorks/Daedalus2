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


def capture(folder, names, revision='native', assembly=None, three_views=False):
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
    out=folder/'QA'
    if not revision.replace('_','').replace('-','').isalnum():raise ValueError('capture revision must be filename-safe')
    report=out/('staging.'+revision+'-review.json')
    if report.exists():raise ValueError('retain existing native review receipt')
    views=[('overview',[6500,-8000,5000],[0,0,-300])]
    if three_views:views += [('route',[2800,4900,800],[900,1000,1100]),('crown',[-2200,2600,3300],[0,0,1800])]
    for row in patches:
        if row['island'] in names:
            for view,_,_ in views:
                if (out/(row['island']+'.'+revision+'-'+view+'.png')).exists():raise ValueError('retain existing capture; choose a new revision')
    result={'stage':'native_still_views','map_sha256_at_capture':fingerprint(world['plan']['map_file'])['sha256'],'views':[],
            'acceptance':'appearance only; no movement/collision/final quality acceptance'}
    for row,view,eye_offset,target_offset in ((row,view,eye,target) for row in patches for view,eye,target in views):
        if row['island'] not in names:continue
        origin=list(row['island_origin_cm'])
        centre=[origin[i]+target_offset[i] for i in range(3)]
        eye=[origin[i]+eye_offset[i] for i in range(3)]
        delta=[centre[i]-eye[i] for i in range(3)]
        pose={'location':dict(zip(('x','y','z'),eye)),
              'rotation':{'pitch':math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),'yaw':math.degrees(math.atan2(delta[1],delta[0])),'roll':0},'scale':{'x':1,'y':1,'z':1}}
        m.call(APP,'SetCameraTransform',transform=pose)
        camera=m.call(APP,'GetCameraTransform')
        reply=wire.call(wire.UNREAL,'viewport_screenshot',width=1280,height=720,timeout=60,side='Unreal')
        image=reply.get('result',reply)
        if 'image_png_base64' not in image:raise RuntimeError('native capture did not return image bytes: '+str(reply))
        data=base64.b64decode(image['image_png_base64'])
        path=out/(row['island']+'.'+revision+'-'+view+'.png')
        if path.exists():raise ValueError('retain existing capture; choose a new output revision')
        path.write_bytes(data)
        result['views'].append({'island':row['island'],'view':view,'path':str(path),'camera':camera,'sha256':hashlib.sha256(data).hexdigest(),
                                'bytes':len(data),'when_utc':datetime.now(timezone.utc).isoformat()})
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--island',action='append',required=True)
    parser.add_argument('--revision',default='native')
    parser.add_argument('--assembly',type=Path,help='optional additional saved assembly journal')
    parser.add_argument('--three-views',action='store_true')
    args=parser.parse_args()
    print(json.dumps(capture(args.folder,set(args.island),args.revision,args.assembly,args.three_views),indent=2))
