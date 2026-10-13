"""Halloween is exclusive to Labyrinth. Original static seasonal kit, no runtime effects."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
exec(compile(Path(__file__).with_name('labyrinth_cast.py').read_text().split('records=[]')[0],__file__,'exec'))
NAMES=['PumpkinLantern','SkullEffigy','Gravestone','Coffin','Cauldron','CandleCluster','FriendlyGhostLantern','WitchHatStand','CrowPerch','CobwebFrame','CryptGate','PumpkinCrate']
records=[]
for i,name in enumerate(NAMES):
    parts=[];box((0,0,.06),(1,1,.12),slate)
    if name in ['PumpkinLantern','PumpkinCrate']:
        if name=='PumpkinCrate':box((0,0,.27),(.9,.7,.38),dark)
        for x in ([-.22,.22] if name=='PumpkinCrate' else [0]):
            ball((x,0,.52),(.28,.28,.28),rust);cone((x,0,.83),.045,.025,.12,teal)
            for eye in [-.1,.1]:box((x+eye,-.27,.58),(.07,.035,.07),light)
            box((x,-.28,.43),(.15,.04,.04),light)
    elif name=='SkullEffigy':
        cone((0,0,.53),.10,.10,.85,dark);ball((0,0,1.08),(.25,.19,.25),ivory)
        for x in [-.09,.09]:box((x,-.19,1.11),(.1,.05,.09),slate)
        for x in [-.1,0,.1]:box((x,-.15,.88),(.05,.09,.12),ivory)
    elif name=='Gravestone':
        box((0,0,.65),(.65,.22,1.15),teal);ball((0,0,1.2),(.33,.12,.2),teal)
        box((0,-.13,.82),(.36,.03,.055),gold);box((0,-.13,.74),(.05,.03,.25),gold)
    elif name=='Coffin':
        box((0,0,.31),(.6,1.3,.48),dark);box((0,0,.57),(.62,1.32,.08),gold)
        box((0,-.2,.63),(.32,.06,.03),ivory);box((0,-.2,.63),(.06,.5,.03),ivory)
    elif name=='Cauldron':
        ball((0,0,.52),(.39,.39,.35),slate);ring((0,0,.73),.33,.035,gold)
        cone((0,0,.75),.29,.29,.035,teal)
        for x in [-.43,.43]:ring((x,0,.55),.12,.025,gold).rotation_euler.y=math.pi/2
    elif name=='CandleCluster':
        for x,z in [(-.22,.4),(0,.68),(.22,.5)]:cone((x,0,z/2+.1),.06,.06,z,ivory);ball((x,0,z+.16),(.04,.04,.09),light)
    elif name=='FriendlyGhostLantern':
        cone((0,0,.65),.32,.14,.8,ivory);ball((0,0,1.06),(.2,.2,.22),ivory)
        for x in [-.08,.08]:ball((x,-.19,1.1),(.03,.02,.04),gold)
        box((0,-.20,.98),(.10,.025,.025),gold)
    elif name=='WitchHatStand':cone((0,0,.55),.08,.08,.9,dark);cone((0,0,1.02),.40,.40,.035,slate);cone((0,0,1.28),.24,0,.5,slate);ring((0,0,1.08),.21,.025,gold)
    elif name=='CrowPerch':
        box((0,0,.65),(.12,.12,1.1),dark);box((0,0,1.16),(.6,.16,.1),dark)
        ball((0,0,1.35),(.18,.23,.16),slate);ball((0,-.19,1.48),(.10,.10,.12),slate)
        o=cone((0,-.32,1.49),.045,0,.14,gold);o.rotation_euler.x=math.pi/2
    elif name=='CobwebFrame':
        for x in [-.5,.5]:box((x,0,.8),(.08,.10,1.4),dark)
        for z in [.15,1.5]:box((0,0,z),(1.08,.10,.08),dark)
        for k in range(8):
            a=k*math.pi/4;segment((0,0,.82),(.48*math.cos(a),0,.82+.6*math.sin(a)),.008,ivory,'spine')
        for r in [.18,.32,.45]:ring((0,0,.82),r,.008,ivory).rotation_euler.x=math.pi/2
    elif name=='CryptGate':
        for x in [-.55,.55]:box((x,0,.9),(.16,.25,1.7),slate)
        box((0,0,1.72),(1.26,.25,.13),gold)
        for x in [-.35,-.12,.12,.35]:cone((x,0,.9),.025,.025,1.5,dark)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Prop_Lab_Halloween_'+name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');path=OUT/(o.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True)
    tri=sum(len(p.vertices)-2 for p in o.data.polygons);radius=math.ceil(max(Vector(c).length for c in o.bound_box)*100)
    records.append(dict(id=o.name,role='Labyrinth-exclusive Halloween scenery: '+name,file=path.name,triangles=tri,rig='static',radius_cm=radius,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    o.location=((i%4)*2.2,(i//4)*2.6,0);bpy.ops.object.text_add(location=(o.location.x-.8,o.location.y-.75,.01));t=bpy.context.object;t.data.body=name;t.data.size=.14;t.data.materials.append(ivory)
bpy.ops.mesh.primitive_plane_add(size=100);bpy.context.object.data.materials.append(slate)
bpy.ops.object.camera_add(location=(12,-15,17));c=bpy.context.object;c.rotation_euler=(Vector((3.3,2.6,.7))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=12;bpy.context.scene.camera=c
for loc in [(0,-5,10),(8,8,12)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=2000;l.data.size=7;l.rotation_euler=(Vector((3,2.5,0))-l.location).to_track_quat('-Z','Y').to_euler()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_x=1600;s.render.resolution_y=1200;s.render.resolution_percentage=100;s.render.filepath=str(OUT/'contact-sheet.png');s.world.color=(.16,.16,.16)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'labyrinth-halloween.blend'));bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps({'assets':records,'realm':'Labyrinth','status':'static Halloween art; Unreal pending'},indent=2))
(OUT/'labyrinth-halloween.bba').write_text('BBA 1\n'+''.join(f"asset {r['id']} lod0 {r['triangles']} lod1 - radius {r['radius_cm']} switch {max(500,20*r['radius_cm'])}\n" for r in records))
