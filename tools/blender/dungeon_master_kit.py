"""Original Labyrinth interaction props. Blender --background --python this.py -- OUTPUT.

Static meshes only: host-side C++ controls interaction. Dimensions in metres.
"""
import bpy, sys, json, math, hashlib
from pathlib import Path
from mathutils import Vector

OUT = Path(sys.argv[sys.argv.index('--') + 1]); OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def material(name, color, metal=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=.65
    return m
STONE=material('Labyrinth slate',(.12,.19,.24)); GOLD=material('Aged brass',(.54,.32,.10),.6)
PAPER=material('Archive ivory',(.8,.68,.43)); BLUE=material('Guide turquoise',(.08,.57,.62),.25)
parts=[]
def cube(loc,scale,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat); parts.append(o); return o
def cyl(loc,radius,depth,mat,verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc)
    o=bpy.context.object; o.data.materials.append(mat); parts.append(o); return o
def base():
    cube((0,0,.08),(.9,.7,.16),STONE)
def build(kind):
    base()
    if kind=='NarratorLectern':
        cube((0,0,.65),(.24,.26,1.15),GOLD)
        o=cube((0,0,1.26),(.85,.65,.10),STONE); o.rotation_euler.x=math.radians(15)
        for x in [-.19,.19]:
            o=cube((x,0,1.33),(.36,.5,.035),PAPER); o.rotation_euler.x=math.radians(15)
    elif kind=='ChoiceTrident':
        cube((0,0,.63),(.14,.18,1),GOLD); cube((0,0,1.05),(.8,.12,.12),GOLD)
        for x,z in [(-.32,1.30),(0,1.5),(.32,1.3)]:
            cyl((x,0,z),.13,.36,BLUE,4)
    elif kind=='ChronicleArchive':
        for x in [-.35,.35]: cube((x,0,.86),(.12,.55,1.4),STONE)
        for z in [.3,.85,1.45]: cube((0,0,z),(.8,.6,.10),GOLD)
        for z in [.59,1.13]:
            for x in [-.23,0,.23]: cube((x,0,z),(.13,.40,.4),PAPER)
    elif kind=='QuestSeal':
        cyl((0,0,.45),.27,.65,STONE)
        o=cyl((0,0,1.08),.4,.12,GOLD,8); o.rotation_euler.x=math.pi/2
        o=cyl((0,-.075,1.08),.28,.08,BLUE,6); o.rotation_euler.x=math.pi/2
    elif kind=='ReturnWaymarker':
        cube((0,0,.86),(.15,.15,1.4),STONE)
        for z,s in [(1.4,1),(.95,-1)]:
            cube((0,0,z),(.66,.13,.19),GOLD)
            o=cyl((s*.37,0,z),.18,.14,BLUE,3); o.rotation_euler.x=math.pi/2
    elif kind=='RiftThreshold':
        for x in [-.7,.7]: cube((x,0,1.25),(.22,.45,2.5),STONE)
        cube((0,0,2.45),(1.62,.45,.22),GOLD)
        for x in [-.7,.7]: cube((x,-.24,1.3),(.06,.04,1.7),BLUE)
        cube((0,0,.07),(1.6,.65,.14),STONE)
    elif kind=='PartyRally':
        cyl((0,0,.28),.43,.24,GOLD)
        for a in [0,2*math.pi/3,4*math.pi/3]:
            x,y=.25*math.cos(a),.25*math.sin(a)
            cyl((x,y,.70),.10,.7,STONE); cyl((x,y,1.12),.14,.16,BLUE,6)
    elif kind=='RewardReliquary':
        cube((0,0,.4),(.65,.48,.5),STONE)
        for x in [-.25,.25]: cube((x,0,.46),(.07,.51,.58),GOLD)
        o=cyl((0,0,.92),.24,.38,BLUE,4); o.rotation_euler.z=math.pi/4

names=['NarratorLectern','ChoiceTrident','ChronicleArchive','QuestSeal','ReturnWaymarker','RiftThreshold','PartyRally','RewardReliquary']
roles=['Display authoritative narrative and available choices','Select a currently offered choice','Read recent history without replaying actions','Show current quest state','Local navigation marker, not a realm portal','Visual dungeon threshold; no automatic realm transfer','Display party health and combat state','Visual reward display; no client-side item grants']
records=[]
for i,(name,role) in enumerate(zip(names,roles)):
    parts=[]; build(name)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join(); o=bpy.context.object
    o.name='Prop_Lab_DM_'+name
    bpy.context.scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.context.view_layer.update()
    dims=list(o.dimensions); tris=sum(len(p.vertices)-2 for p in o.data.polygons)
    path=OUT/(o.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True)
    records.append(dict(id=o.name,role=role,file=path.name,triangles=tris,dimensions_m=dims,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status='static-art-only'))
    o.location=((i%4)*2.4,(i//4)*3,0)
    bpy.ops.object.text_add(location=(o.location.x-.8,o.location.y-.7,.01))
    t=bpy.context.object; t.name='Label_'+name; t.data.body=name; t.data.size=.16; t.data.materials.append(PAPER)
cube((3.6,1.4,-.12),(11,8,.2),STONE)
bpy.ops.object.camera_add(location=(11,-13,15)); cam=bpy.context.object
cam.rotation_euler=(Vector((3.6,1.4,.6))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'; cam.data.ortho_scale=13; bpy.context.scene.camera=cam
for loc,power,size in [((2,-3,10),2000,8),((7,7,8),1700,7)]:
    bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.data.energy=power; l.data.shape='DISK'; l.data.size=size
    l.rotation_euler=(Vector((3.6,1.4,0))-l.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=24
scene.render.threads_mode='FIXED'; scene.render.threads=4
scene.render.resolution_x=1600; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.world.color=(.16,.16,.16); scene.render.filepath=str(OUT/'contact-sheet.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'labyrinth-dungeon-master-kit.blend'))
bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps({'schema':'labyrinth-props-v1','assets':records,'not_included':['rigs','animations','collision','Unreal placement','runtime interactions']},indent=2))
print('DUNGEON_KIT_OK',len(records),sum(r['triangles'] for r in records))
