"""Original Labyrinth creature silhouettes, rigid-part rigs and Idle/Move clips.
Blender --background --python this.py -- OUTPUT. No AI/collision/gameplay bindings.
"""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
# Reuse the owned cast primitives/materials, stopping before its scene build.
shared=Path(__file__).with_name('labyrinth_cast.py').read_text().split('records=[]')[0]
exec(compile(shared,str(Path(__file__).with_name('labyrinth_cast.py')),'exec'))
ROSTER=[
 ('CornerRat','rat','Common: scavenger in corners',.65),('ChalkEater','beetle','Common: consumes path chalk',.7),
 ('GlowGrub','grub','Common: living light trail',.65),('HedgeStalker','hound','Uncommon: hedge ambush',1.1),
 ('MirrorBat','bat','Uncommon: misleading reflections',.85),('WallMimic','wall','Rare: false doorway',1.5),
 ('ThreadSpider','spider','Rare: cuts marked thread',.9),('HornbackBull','bull','Elite: corridor stampede',1.5),
 ('SentinelSphinxling','sphinx','Elite: guards riddle rooms',1.3),('FoldingMaze','maze','Boss: folding wall creature',2.0),
 ('MossSnail','snail','Ambient: moss recycling',.75),('EchoCricket','cricket','Ambient: echo timing clue',.65),
 ('SkyStrider','bird','Mount: realm sky-strider',1.8),('CorridorHound','hound','Companion: scent route guide',1.0),
 ('LanternWisp','wisp','Companion: bounded route lighting',.75),('ChalkKitten','cat','Pet: finds chalk caches',.65),
 ('CompassBeetle','beetle','Pet: reacts near exits',.6),('Mazemouse','mouse','Pet: narrow-gap scout',.5),
 ('ThreadMoth','moth','Pet: follows marked thread',.65)]
records=[]
def creature(form):
    body=teal if form in ['hound','snail','grub','cricket'] else slate
    if form in ['wall','maze']:
        box((0,0,.8),(.9,.55,1.4),slate,'body')
        for x in [-.4,.4]:box((x,-.31,.85),(.10,.08,1.3),gold,'body')
        if form=='maze':
            for x in [-.7,.7]:box((x,0,.8),(.25,.5,1.5),slate,'wing.L' if x>0 else 'wing.R')
            for z in [.35,.75,1.15]:box((0,-.32,z),(.70,.08,.1),ivory,'body')
        for x in [-.17,.17]:ball((x,-.33,1.2),(.065,.025,.055),light,'head')
        return
    if form=='wisp':
        ball((0,0,.8),(.2,.2,.32),light,'body')
        for x in [-.24,.24]:cone((x,0,.9),.09,0,.6,teal,'wing.L' if x>0 else 'wing.R')
        ring((0,0,.8),.33,.035,gold,'body')
        return
    if form=='bird':
        ball((0,0,.85),(.28,.42,.35),teal,'body')
        segment((0,-.15,.9),(0,-.35,1.5),.1,ivory,'head')
        ball((0,-.38,1.6),(.16,.19,.17),slate,'head')
        o=cone((0,-.62,1.6),.08,0,.24,gold,'head');o.rotation_euler.x=math.pi/2
        for x in [-.19,.19]:segment((x,0,.6),(x,0,.13),.055,gold,'leg.L' if x>0 else 'leg.R')
    else:
        ball((0,0,.65),(.28,.42,.25),body,'body')
        ball((0,-.4,.77),(.22,.23,.21),body,'head')
        for x in [-.19,.19]:
            for y in [-.20,.23]:segment((x,y,.6),(x,y,.1),.065,dark,'leg.L' if x>0 else 'leg.R')
    for x in [-.09,.09]:ball((x,-.59,.84 if form!='bird' else 1.65),(.025,.018,.028),light,'head')
    if form in ['rat','mouse','cat','hound','bull','sphinx']:
        if form in ['rat','mouse','cat']: 
            for x in [-.17,.17]:cone((x,-.4,1.04),.1,.015,.21,ivory,'head')
        if form=='hound':
            for x in [-.17,.17]:box((x,-.35,.98),(.12,.12,.29),rust,'head')
            box((0,-.59,.71),(.20,.25,.14),ivory,'head')
        segment((0,.3,.7),(0,.7,.8),.045,gold,'tail')
        if form=='bull':
            box((0,-.28,.73),(.65,.35,.43),rust,'body')
            for x in [-.23,.23]:segment((x,-.39,.99),(x*1.7,-.41,1.28),.065,ivory,'head')
        if form=='sphinx':
            cone((0,-.42,1.05),.24,.10,.32,gold,'head')
    if form in ['bat','moth','bird','sphinx']:
        for x in [-1,1]:
            o=box((x*.48,.04,.8),(.66,.15,.035),ivory if form=='moth' else teal,'wing.L' if x>0 else 'wing.R');o.rotation_euler.y=x*.25
            for k in range(3):box((x*(.3+k*.17),.13,.8),(.14,.30-.05*k,.04),gold,'wing.L' if x>0 else 'wing.R')
        if form=='moth':
            for x in [-.13,.13]:segment((x,-.42,.95),(x*1.5,-.50,1.2),.018,gold,'head')
    if form in ['beetle','spider','cricket']:
        for sign in [-1,1]:
            for y in [-.24,0,.24]:
                segment((sign*.2,y,.64),(sign*.55,y,.18),.022,gold,'leg.L' if sign>0 else 'leg.R')
        if form=='beetle':
            ball((0,.04,.86),(.29,.34,.16),gold,'body');box((0,0,1.0),(.04,.44,.02),ivory,'body')
        if form=='spider':
            ball((0,.3,.74),(.31,.31,.26),rust,'body')
            for x in [-.04,.04]:segment((x,-.56,.7),(x,-.63,.57),.025,ivory,'head')
        if form=='cricket':
            for x in [-.3,.3]:segment((x,.2,.8),(x*1.7,.4,.1),.04,teal,'leg.L' if x>0 else 'leg.R')
    if form=='grub':
        for y in [-.35,-.15,.05,.25,.45]:ball((0,y,.55),(.28,.16,.22),light,'body')
    if form=='snail':
        ball((0,.06,.91),(.3,.28,.30),ivory,'body')
        for radius,z in [(.22,.97),(.13,1.05)]:ring((0,0,z),radius,.025,gold,'body')
        for x in [-.10,.10]:segment((x,-.4,.8),(x,-.49,1.1),.018,teal,'head')

for i,(name,form,role,scale) in enumerate(ROSTER):
    parts=[];creature(form)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='Mob_Lab_'+name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.armature_add();rig=bpy.context.object;rig.name=mesh.name+'_Rig'
    bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
    bones=[('root',(0,0,0),(0,0,.2),None),('body',(0,0,.2),(0,0,.65),'root'),('head',(0,-.3,.65),(0,-.3,1.05),'body'),('tail',(0,.3,.65),(0,.7,.65),'body'),('leg.L',(.19,0,.65),(.19,0,.1),'body'),('leg.R',(-.19,0,.65),(-.19,0,.1),'body'),('wing.L',(.2,0,.8),(.65,0,.8),'body'),('wing.R',(-.2,0,.8),(-.65,0,.8),'body')]
    for bn,h,t,parent in bones:
        b=rig.data.edit_bones.new(bn);b.head=h;b.tail=t
        if parent:b.parent=rig.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');mod=mesh.modifiers.new('Rigid creature rig','ARMATURE');mod.object=rig;mesh.parent=rig
    for clip,n in [('Idle',48),('Move',24)]:
        rig.animation_data_create();act=bpy.data.actions.new(clip);rig.animation_data.action=act
        for f in range(1,n+2,3):
            phase=(f-1)/n*2*math.pi
            for p in rig.pose.bones:
                p.rotation_mode='XYZ';p.rotation_euler=(0,0,0);p.location=(0,0,0)
            rig.pose.bones['body'].location.y=.015*math.sin(phase)
            rig.pose.bones['head'].rotation_euler.z=.035*math.sin(phase)
            if clip=='Move':
                for side,sign in [('L',1),('R',-1)]:
                    rig.pose.bones['leg.'+side].rotation_euler.x=.23*math.sin(phase)*sign
                    rig.pose.bones['wing.'+side].rotation_euler.x=.32*math.sin(phase)*sign
                rig.pose.bones['tail'].rotation_euler.z=.18*math.sin(phase)
            for p in rig.pose.bones:p.keyframe_insert(data_path='rotation_euler',frame=f);p.keyframe_insert(data_path='location',frame=f)
        tr=rig.animation_data.nla_tracks.new();tr.name=clip;tr.strips.new(clip,1,act);rig.animation_data.action=None
    bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True)
    path=OUT/(mesh.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS')
    for tr in rig.animation_data.nla_tracks:tr.mute=True
    for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)
    tri=sum(len(p.vertices)-2 for p in mesh.data.polygons);radius=math.ceil(max(Vector(c).length for c in mesh.bound_box)*100)
    records.append(dict(id=mesh.name,role=role,file=path.name,triangles=tri,bones=8,rig='LabyrinthCreatureV1',recommended_scale=scale,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),radius_cm=radius))
    rig.scale=(scale,)*3
    rig.location=((i%5)*3.5,(i//5)*4,0)
    bpy.ops.object.text_add(location=(rig.location.x-1.2,rig.location.y-1.2,.02));t=bpy.context.object;t.data.body=name;t.data.size=.24;t.data.materials.append(ivory)
bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.data.materials.append(slate)
bpy.ops.object.camera_add(location=(22,-26,30));cam=bpy.context.object;cam.rotation_euler=(Vector((7,6,1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=24;bpy.context.scene.camera=cam
for loc in [(2,-5,15),(14,15,15)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=5000;l.data.size=12;l.rotation_euler=(Vector((7,6,0))-l.location).to_track_quat('-Z','Y').to_euler()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=4;s.render.fps=24;s.render.resolution_x=1800;s.render.resolution_y=1500;s.render.resolution_percentage=100;s.world.color=(.18,.18,.18);s.render.filepath=str(OUT/'contact-sheet.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'labyrinth-creature-cast.blend'));bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps({'assets':records,'clips':['Idle','Move'],'weighting':'rigid parts','status':'art prototype; Unreal acceptance pending'},indent=2))
(OUT/'labyrinth-cast.bba').write_text('BBA 1\n'+''.join(f"asset {r['id']} lod0 {r['triangles']} lod1 - radius {r['radius_cm']} switch {max(500,20*r['radius_cm'])}\n" for r in records))
print('LAB_CREATURES_OK',len(records))
