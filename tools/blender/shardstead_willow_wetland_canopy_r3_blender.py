"""File-only default. Future ONE granted background process: copy-author + 3 views.

blender --background --factory-startup --disable-autoexec --threads 2
 --python-exit-code 2 --python THIS.py -- --execute --self-sha256 REVIEWED_SHA
No export, asset overwrite, old-output mutation, or runtime admission on import.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import shardstead_willow_wetland_canopy_r3 as canopy
import shardstead_willow_wetland_polish_r2_views as r2views

ROOT=Path(__file__).resolve().parents[2]
R3_PINS={
 'tools/blender/shardstead_willow_wetland_canopy_r3.py':'3dd759c9a1da996f55bb97f3400ed2db2050c10819e916e08a9baf1e58c0753b',
 'tools/blender/shardstead_willow_wetland_canopy_r3_test.py':'3fdf088521952352ff29636e4f70ff830f66a132d0f38292aaf5826606be00af',
 'data/ecology/shardstead-willow-wetland-canopy-r3.json':'71e892066d13c6be7e41bbe00166aed717c333fded5b323bd3f0dff33299f06f'}
R2_ROOT=ROOT/'artifacts/biomes/shardstead/WillowWetland/pilot-r2'
R2_INPUTS={'WillowPilotR2.blend':r2views.SCENE_SHA,'authored-r2.json':r2views.RECEIPT_SHA,
 'R1-input-copy.blend':r2views.author.SCENE_SHA,
 'views-r1/views-r1.json':'0187500b27e69281ee0b7fa517e3cc1298905745c6b4fa32a71a35755fa203db'}


def destination():
    path=ROOT/'artifacts/biomes/shardstead/WillowWetland/pilot-r3'
    r2views.author.no_reparse(path)
    r2views.author.need(not path.exists(),'Existing/partial R3 root; preserve it, no replay')
    return path


def replacement_contract(plan,reference):
    need=r2views.author.need
    new,old=plan['exported'][0],reference['exported'][0]
    need(new['name']=='WillowPilot_Willow' and new['role']=='flora','Only Willow role may change')
    need(len(new['triangles'])==3072 and new['materials']==old['materials']
         and new['pivot']==old['pivot']==[0,0,0] and new['units']=='metres','R3 Willow contract differs')
    need(plan['exported'][1:]==reference['exported'][1:]
         and plan['path_context']==reference['path_context']
         and plan['context_recipe']==reference['recipe'],'Protected R2 context changed')


def preflight():
    pins={}
    for path,expected in R3_PINS.items():
        pins[path]=r2views.author.digest(ROOT/path)
        r2views.author.need(pins[path]==expected,'R3 source pin changed')
    # reference() verifies all seven original R2 files and executes only pinned
    # pure producer bytes. Never invoke any old module main()/output stage.
    reference=canopy.reference().build();plan=canopy.build()
    for path in canopy.FROZEN:
        pins[path]=r2views.author.digest(ROOT/path)
    replacement_contract(plan,reference)
    inputs={}
    for name,expected in R2_INPUTS.items():
        inputs[name]=r2views.author.digest(R2_ROOT/name)
        r2views.author.need(inputs[name]==expected,'Actual R2 input changed: '+name)
    author_receipt=json.loads((R2_ROOT/'authored-r2.json').read_text())
    r2views.matched_contract(author_receipt,reference['recipe'])
    views_receipt=json.loads((R2_ROOT/'views-r1/views-r1.json').read_text())
    r2views.author.need(views_receipt['settings']==reference['recipe']['render']
                       and views_receipt['source_r1_sha256']==r2views.SOURCE_SHA
                       and [v['camera'] for v in views_receipt['views']]==reference['recipe']['views'],
                       'Actual R2 matched contract differs')
    return plan,reference,destination(),pins,inputs


def protected_snapshot(bpy):
    """Capture actual non-Willow object data before/after the ONLY data swap."""
    records={}
    for obj in bpy.data.objects:
        if obj.name=='WillowPilot_Willow': continue
        data=dict(type=obj.type,location=list(obj.location),rotation=list(obj.rotation_euler),
                  scale=list(obj.scale),parent=obj.parent.name if obj.parent else None,
                  collections=sorted(c.name for c in obj.users_collection))
        if obj.type=='MESH':
            data.update(vertices=[list(v.co) for v in obj.data.vertices],
                        triangles=[list(p.vertices) for p in obj.data.polygons],
                        material_indices=[p.material_index for p in obj.data.polygons],
                        materials=[m.name for m in obj.data.materials])
        records[obj.name]=data
    return canopy.pin(records)


def matched_views(bpy,recipe,output):
    """Same actual R2 camera/render mechanics, only literal R3 stage paths."""
    from mathutils import Vector
    output.mkdir(exist_ok=False)
    scene=bpy.context.scene;settings=recipe['render']
    scene.render.engine=settings['engine'];scene.cycles.device=settings['device']
    scene.cycles.samples=settings['samples'];scene.render.threads_mode='FIXED'
    scene.render.threads=settings['threads']
    scene.render.resolution_x,scene.render.resolution_y=settings['resolution']
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('R3MatchedReviewWorld');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=settings['world_strength'];scene.world=world
    light=bpy.data.lights.new('R3MatchedReviewSun','SUN');light.energy=settings['sun_energy']
    sun=bpy.data.objects.new(light.name,light);scene.collection.objects.link(sun);sun.rotation_euler=(.4,-.6,-.3)
    images=[]
    for view in recipe['views']:
        camera=bpy.data.cameras.new('R3Matched_'+view['name']);obj=bpy.data.objects.new(camera.name,camera)
        scene.collection.objects.link(obj);obj.location=view['location']
        obj.rotation_euler=(Vector(view['target'])-obj.location).to_track_quat('-Z','Y').to_euler()
        camera.lens=view['lens'];scene.camera=obj
        path=output/(view['name']+'.png');r2views.author.need(not path.exists(),'View overwrite refused')
        scene.render.filepath=str(path)
        r2views.author.need(bpy.ops.render.render(write_still=True)=={'FINISHED'},'Render did not finish')
        dimensions=r2views.png_dimensions(path)
        r2views.author.need(dimensions==settings['resolution'],'Wrong rendered dimensions')
        images.append(dict(path=path.name,bytes=path.stat().st_size,sha256=r2views.author.digest(path),
                           dimensions=dimensions,camera=view,reviewed=False))
    return images


def execute(self_sha):
    need=r2views.author.need;digest=r2views.author.digest
    need(digest(__file__)==self_sha,'Self SHA does not match separate future grant')
    plan,reference,output,pins,inputs=preflight()
    import bpy
    need(bpy.app.background and not bpy.data.filepath,'Requires fresh factory background process')
    need(not bpy.context.preferences.filepaths.use_scripts_auto_execute,'Require --disable-autoexec')
    # New flags are checked against the installed operator schema before use;
    # unsupported flags HOLD rather than silently load UI or execute scripts.
    properties=bpy.ops.wm.open_mainfile.get_rna_type().properties.keys()
    need('load_ui' in properties and 'use_scripts' in properties,'Required safe-open flags unsupported')
    output.mkdir(parents=True,exist_ok=False)
    copied=output/'R2-input-copy.blend'
    with copied.open('xb') as stream: stream.write((R2_ROOT/'WillowPilotR2.blend').read_bytes())
    need(digest(copied)==r2views.SCENE_SHA,'R2 copy differs')
    need(bpy.ops.wm.open_mainfile(filepath=str(copied),load_ui=False,use_scripts=False)=={'FINISHED'},'Copy open failed')
    need(bpy.app.background and Path(bpy.data.filepath).absolute()==copied.absolute(),'Wrong scene open')
    r2views.validate_saved_scene(bpy,reference)
    before=protected_snapshot(bpy)
    descriptor=plan['exported'][0];willow=bpy.data.objects['WillowPilot_Willow']
    original_materials=list(willow.data.materials)
    need([m.name for m in original_materials]==[r2views.author.MATERIALS[label][0] for label in descriptor['materials']],
         'Known R2 Willow material aliases differ')
    data=bpy.data.meshes.new('WillowPilot_Willow_R3')
    data.from_pydata(descriptor['vertices'],[],descriptor['triangles']);data.update()
    for material in original_materials: data.materials.append(material)
    for polygon,index in zip(data.polygons,descriptor['material_indices']): polygon.material_index=index
    willow.data=data  # Only existing Willow object's mesh changes; no deletion.
    post_plan=dict(exported=plan['exported'],path_context=plan['path_context'])
    observed=r2views.validate_saved_scene(bpy,post_plan)
    need(protected_snapshot(bpy)==before,'Non-Willow object data changed')
    saved=output/'WillowPilotR3.blend'
    need(not saved.exists(),'R3 scene overwrite refused')
    bpy.context.scene['willow_r3_source_inputs']=json.dumps(pins,sort_keys=True)
    need(bpy.ops.wm.save_as_mainfile(filepath=str(saved),copy=True)=={'FINISHED'},'R3 scene save failed')
    authored=dict(stage='authored',source_pins=pins,self_sha256=self_sha,r2_inputs=inputs,
                  editable=dict(path=saved.name,sha256=digest(saved)),scene_observations=observed,
                  protected_objects_sha256=before,exports=None,views=None,reopened=None,native=None,quality_accepted=None)
    with (output/'authored-r3.json').open('x') as stream: json.dump(authored,stream,indent=2)
    images=matched_views(bpy,reference['recipe'],output/'views-r1')
    for name,expected in R2_INPUTS.items(): need(digest(R2_ROOT/name)==expected,'Old R2 input changed')
    need(digest(copied)==r2views.SCENE_SHA and digest(saved)==authored['editable']['sha256'],'Saved scene changed')
    receipt=dict(stage='rendered-unreviewed',source_pins=pins,self_sha256=self_sha,
                 scene_sha256=digest(saved),authored_receipt_sha256=digest(output/'authored-r3.json'),
                 r2_inputs=inputs,scene_observations=observed,protected_objects_sha256=before,
                 settings=reference['recipe']['render'],views=images,quality_accepted=None,exports=None,native=None)
    with (output/'views-r1/views-r1.json').open('x') as stream: json.dump(receipt,stream,indent=2)
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--self-sha256')
    args=parser.parse_args(argv)
    if args.execute: value=execute(args.self_sha256)
    else:
        plan,_,out,pins,_=preflight()
        value=dict(status='SOURCE_ONLY_DRY_RUN',future_output=str(out),pins=pins,
                   willow_triangles=len(plan['exported'][0]['triangles']),actual=plan['actual'])
    print(json.dumps(value))


if __name__=='__main__':
    main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
