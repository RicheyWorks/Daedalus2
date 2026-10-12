"""Open one actual watcher source file per archetype, then render an offline art sheet."""
import bpy
import json
import pathlib
import sys
from mathutils import Vector
folder = pathlib.Path(sys.argv[sys.argv.index('--')+1])
manifest = json.loads((folder/'manifest.json').read_text())
samples = [a for a in manifest['assets'] if a['variant']==1]
checks = []
for a in samples:
    bpy.ops.wm.open_mainfile(filepath=a['blend'])
    coll = bpy.data.collections.get(a['asset'])
    obj = bpy.data.objects.get(a['asset'])
    if not coll or not obj or obj.name not in bpy.context.view_layer.objects:
        raise RuntimeError('Watcher source not scene-linked: '+a['asset'])
    if len(coll.objects)!=1 or obj.type!='MESH': raise RuntimeError('Bad source collection')
    obj.data.calc_loop_triangles()
    if len(obj.data.loop_triangles)!=a['triangles']: raise RuntimeError('Source triangle mismatch')
    checks.append(a['asset'])
(folder/'blend-source-validation.json').write_text(json.dumps({'passed':len(checks),'total':len(samples),
    'scope':'One actual scene-linked watcher source per archetype','assets':checks},indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True)
for i,a in enumerate(samples):
    bpy.ops.import_scene.gltf(filepath=a['glb'])
    obj = next(o for o in bpy.context.selected_objects if o.type=='MESH')
    obj.location = ((i%5-2)*4,(i//5-1.5)*4,0)
    if a['archetype'] in ('Hen','Goat'): obj.scale=(2,2,2)
scene = bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
if scene.world is None: scene.world=bpy.data.worlds.new('SOL_PreviewWorld')
scene.world.color=(.06,.08,.12)
bpy.ops.object.camera_add(location=(15,-22,22))
cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'; cam.data.ortho_scale=27; scene.camera=cam
scene.render.resolution_x=1200; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(folder/'art-preview.png')
bpy.ops.render.render(write_still=True)
(folder/'blend-source-validation.json').write_text(json.dumps({'passed':len(checks),'total':len(samples),
    'scope':'One actual scene-linked watcher source per archetype','assets':checks},indent=2))
print('SOL_SOURCE_VALIDATED',len(checks),flush=True)
