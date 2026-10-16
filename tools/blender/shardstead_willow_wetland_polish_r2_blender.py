"""Thin future background-only author adapter; default is read-only dry-run.

Future command (requires a separate serialized runtime grant):
blender --background --factory-startup --disable-autoexec --python THIS.py --
  --stage author --execute --adapter-sha256 REVIEWED_SHA --r1-scene RETAINED_R1
No export/render/reopen/native stage is implemented or automatically chained.
"""
import argparse
import hashlib
import json
import math
import stat
from pathlib import Path
import sys

import shardstead_willow_wetland_polish_r2 as geometry

ROOT=Path(__file__).resolve().parents[2]
PREFIX='Shardstead_WillowWetland_8407'
SCENE_SHA='711c773df106761775d4c6c3bd051c79db9f9d91f4a1f5532773066f63863993'
PINS={'tools/blender/shardstead_willow_wetland_polish_r2.py':
      {'d828f4bcde4b2033990e776d88c000810bcd05458256b31b11d2d32d9fc6cce4'},
      'data/ecology/shardstead-willow-wetland-polish-r2.json':
      {'b6e783c7c8053de3857e2ad70cf839fefbe754766147701ef31ad3f0932d2d74',
       'f66365eddc7f94c6ad6ffa9e1af706526916c6046a266756edbfa32100d295e5'},
      'tools/blender/shardstead_willow_wetland_polish_r2_test.py':
      {'fa311d992ff5f5639d1df94356aebf21f22d89afcd72b0dca4f088be91601dd6'}}
MATERIALS={
    'bark':(PREFIX+'_willow_bark',(.19,.11,.065,1),.7),
    'leaf_sage':(PREFIX+'_willow_leaf',(.20,.40,.19,1),.7),
    'leaf_light':(PREFIX+'_willow_leaf',(.20,.40,.19,1),.7),
    'reed':(PREFIX+'_reed',(.35,.45,.16,1),.7),
    'reed_seed':(PREFIX+'_reed',(.35,.45,.16,1),.7),
    'water':(PREFIX+'_pond_water',(.055,.24,.26,1),.7),
    'shore_soil':('Pilot_SageGround',(.16,.24,.12,1),.85),
    'earth':('Pilot_EarthPath',(.36,.22,.13,1),.85)}


def need(condition,message):
    if not condition: raise ValueError(message)


def no_reparse(path):
    path=Path(path).absolute()
    for part in (path,*path.parents):
        try:
            metadata=part.lstat()  # Inspect the link itself, never its target.
        except FileNotFoundError:
            continue  # A missing output tail still requires checking every ancestor.
        need(not stat.S_ISLNK(metadata.st_mode)
             and not (getattr(metadata,'st_file_attributes',0)&0x400),
             'Refuse symlink/reparse source or output')


def digest(path):
    no_reparse(path)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output_path(root=ROOT):
    destination=Path(root)/'artifacts/biomes/shardstead/WillowWetland/pilot-r2'
    no_reparse(destination)
    need(not destination.exists(),'R2 output already exists; retain partial result, no replay')
    return destination


def bindings():
    """Exact R1 source-derived inventory; never a wildcard deletion list."""
    expected={'Synthetic_WillowPilot_Ground':('MESH',None),
              'Synthetic_North_Path':('MESH',None),
              PREFIX+'_WaterSurface':('MESH','habitats'),
              'ExistingTerrainReference':('EMPTY','terrain'),
              'ProtectedPondRefuge':('EMPTY','habitats'),
              'ExistingRescuerReference':('EMPTY','characters')}
    replace={'Synthetic_North_Path',PREFIX+'_WaterSurface'}
    for index in range(12):
        if index%3==0:
            expected['WillowBarkCandidate_'+str(index)]=('EMPTY','resources')
            names=['Willow_%d_Trunk'%index]+['Willow_%d_Drape_%d'%(index,b) for b in range(8)]
        else:
            names=['DecorativeReed_%d_%d'%(index,s) for s in range(5)]
        for name in names:
            expected[name]=('CURVE','flora');replace.add(name)
    return expected,replace


def validate_inventory(actual):
    expected,_=bindings()
    need(actual==expected,'R1 object names/types/role membership differ; no mutation')


def validate_descriptors(plan):
    expected=[('WillowPilot_Willow','flora'),('WillowPilot_Reeds','flora'),('WillowPilot_Pond','habitats')]
    need([(m['name'],m['role']) for m in plan['exported']]==expected,'Unknown export role')
    need(sum(len(m['triangles']) for m in plan['exported'])==6496,'Reviewed geometry count changed')
    for mesh in plan['exported']+[plan['path_context']]:
        need(mesh['pivot']==[0,0,0] and mesh['units']=='metres','Wrong shared metre pivot')
        need(all(label in MATERIALS for label in mesh['materials']),'Unknown material intent')
        need(len(mesh['triangles'])==len(mesh['material_indices']),'Missing face material mapping')
        for vertex in mesh['vertices']:
            need(len(vertex)==3 and all(math.isfinite(v) for v in vertex),'Nonfinite vertex')
        for face,material in zip(mesh['triangles'],mesh['material_indices']):
            need(len(face)==3 and len(set(face))==3 and all(type(i) is int and 0<=i<len(mesh['vertices']) for i in face),
                 'Invalid triangle indices')
            need(type(material) is int and 0<=material<len(mesh['materials']),'Invalid material index')


def preflight(scene,root=ROOT):
    pins={}
    for name,accepted in PINS.items():
        value=digest(Path(root)/name)
        need(value in accepted,'Reviewed source pin changed: '+name)
        pins[name]=value
    need(digest(scene)==SCENE_SHA,'Retained R1 scene hash mismatch')
    output=output_path(root)
    plan=geometry.build()
    validate_descriptors(plan)
    return plan,output,pins


def author(scene,adapter_sha256):
    # Only explicit future invocation imports bpy, after immutable file guards.
    need(digest(__file__)==adapter_sha256,'Adapter hash must match separately reviewed allocation')
    plan,output,pins=preflight(scene)
    import bpy
    need(bpy.app.background,'Refuse live GUI authoring')
    need(not bpy.data.filepath,'Start from unsaved factory background process')
    need(not bpy.context.preferences.filepaths.use_scripts_auto_execute,'Require --disable-autoexec')
    # Atomic fresh-root reservation; an interrupted stage is retained, never replayed.
    output.mkdir(parents=True,exist_ok=False)
    copied=output/'R1-input-copy.blend'
    with copied.open('xb') as target:
        target.write(Path(scene).read_bytes())
    need(digest(copied)==SCENE_SHA,'Copied input changed')
    need(bpy.ops.wm.open_mainfile(filepath=str(copied))=={'FINISHED'},'Opening owned copy failed')
    need(bpy.app.background and Path(bpy.data.filepath).resolve()==copied.resolve(),'Wrong copied scene')
    need(bpy.context.scene.unit_settings.system=='METRIC'
         and abs(bpy.context.scene.unit_settings.scale_length-1)<1e-6,'Wrong scene units')
    actual={}
    for obj in bpy.data.objects:
        roles=[role for role in ('terrain','flora','habitats','resources','creatures','characters')
               if PREFIX+'_'+role in [c.name for c in obj.users_collection]]
        need(len(roles)<=1,'Ambiguous R1 role')
        actual[obj.name]=(obj.type,roles[0] if roles else None)
    validate_inventory(actual)
    expected_collections={PREFIX}|{PREFIX+'_'+r for r in ('terrain','flora','habitats','resources','creatures','characters')}
    need(expected_collections.issubset(set(bpy.data.collections.keys())),'Missing R1 collections')
    need(not any(c.name not in expected_collections and (c.objects or c.children) for c in bpy.data.collections),
         'Unknown populated collection')
    need(all(abs(v)<1e-6 for obj in bpy.data.objects if obj.type in ('MESH','CURVE') for v in (*obj.location,*obj.rotation_euler))
         and all(abs(v-1)<1e-6 for obj in bpy.data.objects for v in obj.scale if obj.type in ('MESH','CURVE')),
         'Unexpected source transforms; world geometry requires shared origin')
    resolved={}
    for label,(name,colour,roughness) in MATERIALS.items():
        material=bpy.data.materials.get(name)
        need(material is not None and material.use_nodes,'Missing R1 material '+name)
        bsdf=material.node_tree.nodes.get('Principled BSDF')
        need(bsdf is not None,'Missing R1 Principled shader')
        need(all(abs(a-b)<1e-5 for a,b in zip(material.diffuse_color,colour))
             and all(abs(a-b)<1e-5 for a,b in zip(bsdf.inputs['Base Color'].default_value,colour))
             and abs(bsdf.inputs['Roughness'].default_value-roughness)<1e-5,'R1 material values differ')
        need(not bsdf.inputs['Base Color'].is_linked and not bsdf.inputs['Roughness'].is_linked,
             'Unexpected linked R1 material inputs')
        resolved[label]=material
    # Retain terrain, references, resources, scene lighting and all render settings.
    # No camera/material creation or lighting/exposure/gamma modification.
    _,replace=bindings()
    staged=[]
    for descriptor in plan['exported']+[plan['path_context']]:
        data=bpy.data.meshes.new('R2_'+descriptor['name'])
        data.from_pydata(descriptor['vertices'],[],descriptor['triangles'])
        data.update()
        for label in descriptor['materials']: data.materials.append(resolved[label])
        for polygon,index in zip(data.polygons,descriptor['material_indices']): polygon.material_index=index
        obj=bpy.data.objects.new('R2_'+descriptor['name'],data)
        collection=(bpy.data.collections[PREFIX+'_'+descriptor['role']]
                    if descriptor['role']!='context' else bpy.context.scene.collection)
        collection.objects.link(obj)
        staged.append((obj,descriptor['name']))
    for name in sorted(replace): bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    for obj,name in staged: obj.name=name
    destination=output/'WillowPilotR2.blend'
    need(not destination.exists(),'Existing R2 scene')
    bpy.context.scene['willow_r2_source_inputs']=json.dumps(pins,sort_keys=True)
    need(bpy.ops.wm.save_as_mainfile(filepath=str(destination),copy=True)=={'FINISHED'},'R2 save failed')
    need(digest(scene)==SCENE_SHA and digest(copied)==SCENE_SHA,'Original/copied R1 bytes changed')
    receipt=dict(stage='authored',synthetic=True,inputs=pins,adapter_sha256=adapter_sha256,
                 r1_scene_sha256=SCENE_SHA,editable=dict(path=destination.name,sha256=digest(destination)),
                 exports=None,views=None,reopened=None,native=None,quality_accepted=None,
                 matched_view_contract=plan['recipe']['views'],render_contract=plan['recipe']['render'])
    with (output/'authored-r2.json').open('x',encoding='utf-8') as stream: json.dump(receipt,stream,indent=2)
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['dry-run','author'],default='dry-run')
    parser.add_argument('--r1-scene',required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--adapter-sha256')
    args=parser.parse_args(argv)
    need((args.stage=='author')==args.execute,'Author requires explicit --execute; no implicit production')
    if args.execute:
        value=author(args.r1_scene,args.adapter_sha256)
    else:
        plan,output,pins=preflight(args.r1_scene)
        value=dict(status='SOURCE_ONLY_DRY_RUN',output=str(output),inputs=pins,
                   objects_expected=len(bindings()[0]),replace_exact=len(bindings()[1]),
                   actual=plan['actual'],runtime_bindings='PENDING_UNEXECUTED')
    print(json.dumps(value))


if __name__=='__main__':
    main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
