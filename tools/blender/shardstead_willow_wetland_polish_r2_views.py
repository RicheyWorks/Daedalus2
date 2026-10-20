"""Thin matched-view consumer. Default is file-only; future execution needs a grant.

Future argv: blender --background --factory-startup --disable-autoexec --threads 2
--python-exit-code 2 --python THIS.py -- --execute --views-sha256 REVIEWED_SHA
--scene AUTHORED_R2 --r1-source FROZEN_PILOT_PY --r1-views FROZEN_R1_VIEWS_DIR
No blend save, geometry/material edits, export, native call, or chained stage.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import shardstead_willow_wetland_polish_r2_blender as author

ROOT=Path(__file__).resolve().parents[2]
SCENE_SHA='fdb03921b5010df83a8ea53787ebc762e69604b72a1d9a86f939297ea2bf91f7'
RECEIPT_SHA='a705b60bf5b28221eedee591ad64cda4b1f6f200bf3823c8a8045dc59cac250f'
AUTHOR_SHA='c0d0e3be93b05cb0c9a9081ec927ec407cbc23ba4ecca41068a452f236b7552a'
SOURCE_SHA='0f77409dc9f58edecf9bdced92afc458fdb41469b2026f1fd5cfe24c1734a094'
PINS={**author.PINS,
      'tools/blender/shardstead_willow_wetland_polish_r2_blender.py':{AUTHOR_SHA},
      'tools/blender/shardstead_willow_wetland_polish_r2_blender_test.py':
      {'ab86d0d247a8aeaa6578ff316e6391ba0c67a17a5060c32e1041c4aac4c3f3eb'}}
R1_PNGS={'overview':'a9811e5678794ffa740a4133828b16381a45a9d44f1f7749cfb3aa03bf87747b',
         'player_contact':'507ffa34ebe9872397db897fdff44f489f1a021be5e02df5f9c0f5be7dce9a28',
         'refuge_detail':'83b5829809901b55dc5ca28ccbb02f20e9dbdc8232c786f1828f9fb991f69fe9'}


def fresh_output(scene):
    destination=Path(scene).parent/'views-r1'
    author.no_reparse(destination)
    author.need(not destination.exists(),'Views output occupied; preserve partial stage, no replay')
    return destination


def png_dimensions(path):
    with Path(path).open('rb') as stream: header=stream.read(24)
    author.need(len(header)==24 and header[:8]==b'\x89PNG\r\n\x1a\n' and header[12:16]==b'IHDR',
                'Rendered PNG header invalid')
    return list(struct.unpack('>II',header[16:24]))


def matched_contract(receipt,recipe):
    author.need(receipt['matched_view_contract']==recipe['views']
                and receipt['render_contract']==recipe['render'],'Matched R1 view/settings mismatch')
    author.need([v['name'] for v in recipe['views']]==list(R1_PNGS),'Wrong three view identities')
    author.need(all(receipt[key] is None for key in ('exports','views','reopened','native','quality_accepted')),
                'Authored receipt unexpectedly advanced')


def preflight(scene,r1_source,r1_views):
    scene=Path(scene).absolute()
    author.no_reparse(scene)
    author.need(scene.absolute()==ROOT/'artifacts/biomes/shardstead/WillowWetland/pilot-r2/WillowPilotR2.blend',
                'Only exact owned authored R2 scene is allowed')
    author.need(author.digest(scene)==SCENE_SHA,'Wrong R2 scene bytes')
    receipt_path=scene.parent/'authored-r2.json'
    author.need(author.digest(receipt_path)==RECEIPT_SHA,'Wrong immutable authored receipt')
    receipt=json.loads(receipt_path.read_text())
    author.need(author.digest(scene.parent/'R1-input-copy.blend')==author.SCENE_SHA,'Wrong retained R1 copy')
    pins={}
    for path,accepted in PINS.items():
        pins[path]=author.digest(ROOT/path)
        author.need(pins[path] in accepted,'Changed reviewed source '+path)
    author.need(author.digest(r1_source)==SOURCE_SHA,'R1 view mechanics source changed')
    comparisons={}
    for name,expected in R1_PNGS.items():
        path=Path(r1_views)/(name+'.png')
        comparisons[name]=author.digest(path)
        author.need(comparisons[name]==expected,'R1 comparison PNG changed')
        author.need(png_dimensions(path)==[1000,1000],'Wrong R1 comparison dimensions')
    plan=author.geometry.build()
    author.validate_descriptors(plan)
    matched_contract(receipt,plan['recipe'])
    return plan,receipt,fresh_output(scene),pins,comparisons


def expected_inventory(plan):
    inventory,replaced=author.bindings()
    inventory={name:value for name,value in inventory.items() if name not in replaced}
    for descriptor in plan['exported']+[plan['path_context']]:
        role=descriptor['role'] if descriptor['role']!='context' else None
        inventory[descriptor['name']]=('MESH',role)
    return inventory


def validate_saved_scene(bpy,plan):
    scene=bpy.context.scene
    author.need(scene.unit_settings.system=='METRIC' and abs(scene.unit_settings.scale_length-1)<1e-6,
                'Saved scene metre units differ')
    actual={}
    for obj in bpy.data.objects:
        roles=[r for r in ('terrain','flora','habitats','resources','creatures','characters')
               if author.PREFIX+'_'+r in [c.name for c in obj.users_collection]]
        author.need(len(roles)<=1,'Ambiguous saved role')
        actual[obj.name]=(obj.type,roles[0] if roles else None)
    author.need(actual==expected_inventory(plan),'Saved inventory differs; no camera/render mutation')
    observations=[]
    for descriptor in plan['exported']+[plan['path_context']]:
        obj=bpy.data.objects[descriptor['name']]
        author.need(obj.parent is None and not obj.modifiers,'Unexpected parent/modifier')
        author.need(all(abs(v)<1e-6 for v in (*obj.location,*obj.rotation_euler))
                    and all(abs(v-1)<1e-6 for v in obj.scale),'Saved shared pivot differs')
        author.need(len(obj.data.vertices)==len(descriptor['vertices'])
                    and len(obj.data.polygons)==len(descriptor['triangles']),'Saved geometry counts differ')
        for vertex,expected in zip(obj.data.vertices,descriptor['vertices']):
            author.need(all(abs(a-b)<1e-5 for a,b in zip(vertex.co,expected)),'Saved vertex differs')
        for polygon,face,slot in zip(obj.data.polygons,descriptor['triangles'],descriptor['material_indices']):
            author.need(tuple(polygon.vertices)==tuple(face) and polygon.material_index==slot,
                        'Saved triangles/material indices differ')
        labels=[author.MATERIALS[label][0] for label in descriptor['materials']]
        author.need([m.name for m in obj.data.materials]==labels,'Saved material bindings differ')
        bounds=[[min(v.co[i] for v in obj.data.vertices) for i in range(3)],
                [max(v.co[i] for v in obj.data.vertices) for i in range(3)]]
        observations.append(dict(name=obj.name,role=descriptor['role'],triangles=len(obj.data.polygons),
                                 vertices=len(obj.data.vertices),bounds_metres=bounds,materials=labels,
                                 pivot=[float(v) for v in obj.location]))
    for _,(name,colour,roughness) in author.MATERIALS.items():
        material=bpy.data.materials.get(name)
        author.need(material is not None and material.use_nodes,'Saved material missing')
        shader=material.node_tree.nodes.get('Principled BSDF')
        author.need(shader is not None and not shader.inputs['Base Color'].is_linked
                    and not shader.inputs['Roughness'].is_linked,'Saved material graph differs')
        author.need(all(abs(a-b)<1e-5 for a,b in zip(material.diffuse_color,colour))
                    and all(abs(a-b)<1e-5 for a,b in zip(shader.inputs['Base Color'].default_value,colour))
                    and abs(shader.inputs['Roughness'].default_value-roughness)<1e-5,'Saved material values differ')
    author.need(abs(scene.view_settings.exposure)<1e-6 and abs(scene.view_settings.gamma-1)<1e-6,
                'Nonbaseline exposure/gamma; no silent correction')
    return observations


def render(scene_path,r1_source,r1_views,self_sha):
    author.need(author.digest(__file__)==self_sha,'Views script SHA differs from future grant')
    plan,authored,output,pins,comparisons=preflight(scene_path,r1_source,r1_views)
    scene_path=Path(scene_path).absolute()
    import bpy
    from mathutils import Vector
    author.need(bpy.app.background and not bpy.data.filepath,'Requires fresh background process')
    author.need(not bpy.context.preferences.filepaths.use_scripts_auto_execute,'Require --disable-autoexec')
    author.need(bpy.ops.wm.open_mainfile(filepath=str(scene_path))=={'FINISHED'},'Opening R2 scene failed')
    author.need(Path(bpy.data.filepath).absolute()==Path(scene_path).absolute(),'Wrong opened scene')
    observed=validate_saved_scene(bpy,plan)
    # All guards pass before reserving fresh four-file stage output.
    output.mkdir(exist_ok=False)
    scene=bpy.context.scene;settings=plan['recipe']['render']
    scene.render.engine=settings['engine'];scene.cycles.device=settings['device']
    scene.cycles.samples=settings['samples'];scene.render.threads_mode='FIXED'
    scene.render.threads=settings['threads']
    scene.render.resolution_x,scene.render.resolution_y=settings['resolution']
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('R2MatchedReviewWorld');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=settings['world_strength'];scene.world=world
    light=bpy.data.lights.new('R2MatchedReviewSun','SUN');light.energy=settings['sun_energy']
    sun=bpy.data.objects.new(light.name,light);scene.collection.objects.link(sun)
    sun.rotation_euler=(.4,-.6,-.3)
    images=[]
    for view in plan['recipe']['views']:
        camera=bpy.data.cameras.new('R2Matched_'+view['name'])
        obj=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(obj)
        obj.location=view['location'];obj.rotation_euler=(Vector(view['target'])-obj.location).to_track_quat('-Z','Y').to_euler()
        camera.lens=view['lens'];scene.camera=obj
        path=output/(view['name']+'.png')
        author.need(not path.exists(),'Existing view refuses overwrite')
        scene.render.filepath=str(path)
        author.need(bpy.ops.render.render(write_still=True)=={'FINISHED'},'Render did not finish')
        dimensions=png_dimensions(path)
        author.need(dimensions==settings['resolution'],'Rendered dimensions differ')
        images.append(dict(path=path.name,sha256=author.digest(path),bytes=path.stat().st_size,
                           dimensions=dimensions,camera=view,reviewed=False))
    author.need(author.digest(scene_path)==SCENE_SHA
                and author.digest(Path(scene_path).parent/'authored-r2.json')==RECEIPT_SHA,
                'Scene/author receipt changed; do not save blend')
    value=dict(stage='rendered-unreviewed',synthetic=True,inputs=pins,self_sha256=self_sha,
               scene_sha256=SCENE_SHA,authored_receipt_sha256=RECEIPT_SHA,source_r1_sha256=SOURCE_SHA,
               r1_comparison_pngs=comparisons,scene_observations=observed,settings=settings,
               color_management=dict(view_transform=scene.view_settings.view_transform,
                                     exposure=scene.view_settings.exposure,gamma=scene.view_settings.gamma),
               sun_rotation=[.4,-.6,-.3],views=images,quality_accepted=None,native=None,exports=None)
    with (output/'views-r1.json').open('x',encoding='utf-8') as stream: json.dump(value,stream,indent=2)
    return value


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',required=True);parser.add_argument('--r1-source',required=True)
    parser.add_argument('--r1-views',required=True);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--views-sha256')
    args=parser.parse_args(argv)
    if args.execute:
        value=render(args.scene,args.r1_source,args.r1_views,args.views_sha256)
    else:
        plan,_,out,pins,_=preflight(args.scene,args.r1_source,args.r1_views)
        value=dict(status='SOURCE_ONLY_DRY_RUN',output=str(out),inputs=pins,
                   views=plan['recipe']['views'],render=plan['recipe']['render'],
                   actual_views=None,quality_accepted=None,runtime='UNEXECUTED')
    print(json.dumps(value))


if __name__=='__main__':
    main(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
