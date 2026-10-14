# SPDX-License-Identifier: MIT
"""Fit existing saved salvage modules to hash-matched original island terrain.

Consumes source patch planning and native mesh bounds; no editor calls/imports.
The FBX basis must agree on all nonempty island layers before a recipe is emitted.
"""
import argparse
import json
from pathlib import Path


def recipe(folder):
    folder=Path(folder)
    patches=json.loads((folder/'codex-workshop-source-plan.json').read_text())
    native=json.loads((folder/'codex-native-local-bounds.json').read_text())['result']
    saved=json.loads((folder/'codex-prepared.unreal.json').read_text())
    modules={row['name']:row['meshes'][0]['path'] for row in saved['results'] if row['kind']=='module'}
    entries=[]
    for island in patches:
        name=island['island']
        for row in (r for r in native if r['group']==name):
            layer=row['source_name'][len(name)+1:]
            box=island['source_bounds'][layer]
            expected={'min':[box['min'][0]*100,-box['max'][1]*100,box['min'][2]*100],
                      'max':[box['max'][0]*100,-box['min'][1]*100,box['max'][2]*100]}
            if any(abs(row[edge][i]-expected[edge][i])>.02 for edge in ('min','max') for i in range(3)):
                raise ValueError('native FBX bounds differ from the source basis: '+row['source_name'])
        patch=island['source_patch_metres']
        base=[island['island_origin_cm'][0]+patch['x']*100,
              island['island_origin_cm'][1]-patch['y']*100,
              island['island_origin_cm'][2]+patch['floor_z']*100]
        variant=island['variant']
        # Positive pitch turns the saved beam's +X long axis upright in Unreal.
        props=[('GearboxHousing',[0,0,1.5],'housing',0,1),
               ('DriveShaft',[0,-2.25,2],'shaft',0,1),
               ('TurbineRotor',[0,-3.75,2],'rotor',0,1),
               ('BridgeCoupler',[-2,0,1.25],'crossbeam',0,1),
               ('BridgeCoupler',[-1.5,0,0],'west_leg',90,.3125),
               ('BridgeCoupler',[1.5,0,0],'east_leg',90,.3125),
               ('CrystalBattery',[2,1,0],'battery',0,1),
               ('WagonWheel',[3.5,1.5,1.25],'spare_wheel',0,1),
               ('SailPanel',[1.5,3,0],'signal_sail',0,1)]
        for part,offset,role,pitch,sx in props:
            key=next(k for k in modules if k.startswith('CodexModule_'+variant+'_'+part+'_'))
            entries.append({'label':'CodexDress_'+variant+'_'+role,'mesh_path':modules[key],
                            'transform':{'location':dict(zip(('x','y','z'),[base[0]+offset[0]*100,base[1]-offset[1]*100,base[2]+offset[2]*100])),
                                         'rotation':{'pitch':pitch,'yaw':0,'roll':0},'scale':{'x':sx,'y':1,'z':1}},
                            'role':role,'island':name})
    return {'schema':'daedalus.codex-workshop-recipe.v1','staging_only':True,
            'source_to_native_basis':'centimetres: (x, -y, z), verified against every island layer bounds',
            'implemented_gameplay':False,'entries':entries}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    result=recipe(args.folder)
    target=args.folder/'codex-workshop.dressing.json'
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'plan':str(target),'actors':len(result['entries']),'unique_modules':len({r['mesh_path'] for r in result['entries']})}))
