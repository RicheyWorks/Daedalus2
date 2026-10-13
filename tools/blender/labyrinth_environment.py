"""Metre-scale modular maze/interaction kit, Blender --background --python this.py -- OUTPUT."""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
exec(compile(Path(__file__).with_name('labyrinth_cast.py').read_text().split('records=[]')[0],__file__,'exec'))
KIT=[('Floor4m','4m snapping floor'),('Wall4m','4m wall with route inset'),('Corner4m','L-shaped maze corner'),('GateArch','Riddle gate frame'),('ThreadAnchor','Attach persistent route thread'),('ChalkMarker','Player path marking surface'),('TrapPlate','Readable pressure trap'),('MirrorPanel','Reflection puzzle surface'),('HedgePlanter','Regrowing hedge obstacle'),('StriderPerch','Mount rest and care'),('HornbackTrough','Livestock care and calming'),('EchoBell','Echo timing puzzle')]
records=[]
for i,(name,role) in enumerate(KIT):
    parts=[]
    if name in ['Floor4m','Wall4m','Corner4m']:
        box((0,0,.1),(4,4,.2),slate)
        if name!='Floor4m':box((0,1.85,1.5),(4,.3,3),teal)
        if name=='Corner4m':box((1.85,0,1.5),(.3,4,3),teal)
        if name!='Floor4m':box((0,1.68,1.6),(3.5,.04,.08),gold)
    elif name=='GateArch':
        for x in [-1.25,1.25]:box((x,0,1.6),(.35,.5,3.2),slate)
        box((0,0,3.1),(2.8,.5,.25),gold)
    else:
        box((0,0,.1),(1.2,1,.2),slate)
        if name=='ThreadAnchor':
            cone((0,0,.6),.12,.12,1,gold);ring((0,0,1.15),.20,.035,ivory).rotation_euler.x=math.pi/2
        elif name=='ChalkMarker':box((0,0,.24),(.7,.7,.08),ivory);box((0,0,.30),(.45,.08,.03),teal)
        elif name=='TrapPlate':
            box((0,0,.23),(.9,.75,.1),rust)
            for x in [-.3,0,.3]:cone((x,0,.4),.06,0,.28,gold)
        elif name=='MirrorPanel':box((0,0,1.1),(.85,.14,1.9),gold);box((0,-.08,1.1),(.68,.03,1.7),ivory)
        elif name=='HedgePlanter':
            box((0,0,.4),(1.1,.8,.55),gold)
            for x in [-.3,0,.3]:ball((x,0,.85),(.27,.28,.5),teal,'spine')
        elif name=='StriderPerch':
            for x in [-.4,.4]:cone((x,0,.85),.07,.07,1.5,gold)
            box((0,0,1.55),(1.1,.22,.16),dark)
        elif name=='HornbackTrough':
            for y in [-.35,.35]:box((0,y,.5),(1.1,.12,.5),dark)
            for x in [-.5,.5]:box((x,0,.5),(.12,.7,.5),dark)
            box((0,0,.39),(.9,.55,.05),teal)
        elif name=='EchoBell':
            for x in [-.4,.4]:box((x,0,.9),(.12,.2,1.6),dark)
            box((0,0,1.6),(.9,.2,.12),dark);cone((0,0,1.15),.29,.14,.5,gold)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Prop_Lab_'+name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    path=OUT/(o.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True)
    tri=sum(len(p.vertices)-2 for p in o.data.polygons);radius=math.ceil(max(Vector(c).length for c in o.bound_box)*100)
    records.append(dict(id=o.name,role=role,file=path.name,triangles=tri,rig='static',bones=0,radius_cm=radius,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    o.location=((i%4)*5,(i//4)*5,0)
    bpy.ops.object.text_add(location=(o.location.x-1.5,o.location.y-2,.02));t=bpy.context.object;t.data.body=name;t.data.size=.28;t.data.materials.append(ivory)
bpy.ops.object.camera_add(location=(25,-25,35));c=bpy.context.object;c.rotation_euler=(Vector((7.5,5,1))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=25;bpy.context.scene.camera=c
bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.data.materials.append(slate)
for loc in [(0,-5,18),(15,15,20)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=6000;l.data.size=15;l.rotation_euler=(Vector((7,5,0))-l.location).to_track_quat('-Z','Y').to_euler()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_x=1700;s.render.resolution_y=1300;s.render.resolution_percentage=100;s.render.filepath=str(OUT/'contact-sheet.png');s.world.color=(.18,.18,.18)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'labyrinth-environment.blend'));bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps({'assets':records,'status':'static art; collision/interactions pending'},indent=2))
(OUT/'labyrinth-environment.bba').write_text('BBA 1\n'+''.join(f"asset {r['id']} lod0 {r['triangles']} lod1 - radius {r['radius_cm']} switch {max(500,20*r['radius_cm'])}\n" for r in records))
print('LAB_ENV_OK',len(records))
