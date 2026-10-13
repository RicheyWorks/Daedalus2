"""Blender 4.3: first three original Labyrinth cast members, shared rigid-part rig.
Run: blender --background --python labyrinth_cast.py -- OUTPUT
Faces -Y in Blender, metre scale, base at Z=0. No gameplay implementation.
"""
import bpy, math, sys, json, hashlib
from pathlib import Path
from mathutils import Vector

OUT=Path(sys.argv[sys.argv.index('--')+1]); OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def mat(name,c,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.72
    return m
slate=mat('Midnight wool',(.035,.10,.14)); teal=mat('Weathered teal',(.06,.29,.30))
ivory=mat('Thread ivory',(.76,.65,.43)); gold=mat('Antique brass',(.48,.29,.08),.65)
skin=mat('Warm clay',(.42,.22,.13)); dark=mat('Leather',(.065,.036,.024))
light=mat('Lantern amber',(.95,.46,.075)); rust=mat('Ari terracotta',(.43,.10,.055))
parts=[]
def finish(o,m,bone):
    o.data.materials.append(m)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.vertex_groups.new(name=bone).add(list(range(len(o.data.vertices))),1,'REPLACE')
    parts.append(o);return o
def box(p,s,m,bone='spine',bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=s
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('Soft crafted edges','BEVEL');mod.width=bevel;mod.segments=1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,m,bone)
def cone(p,r1,r2,d,m,bone='spine',n=10):
    bpy.ops.mesh.primitive_cone_add(vertices=n,radius1=r1,radius2=r2,depth=d,location=p)
    return finish(bpy.context.object,m,bone)
def ball(p,s,m,bone='head'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=p)
    o=bpy.context.object;o.scale=s;return finish(o,m,bone)
def segment(a,b,r,m,bone):
    a,b=Vector(a),Vector(b);o=cone((a+b)/2,r,r*.85,(b-a).length,m,bone)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def ring(p,r,minor,m,bone='spine'):
    bpy.ops.mesh.primitive_torus_add(major_segments=16,minor_segments=6,location=p,major_radius=r,minor_radius=minor)
    return finish(bpy.context.object,m,bone)

BONES=[('root',(0,0,0),(0,0,.2),None),('pelvis',(0,0,.9),(0,0,1.08),'root'),
 ('spine',(0,0,1.08),(0,0,1.5),'pelvis'),('head',(0,0,1.5),(0,0,1.9),'spine')]
for side,x in [('L',.21),('R',-.21)]:
    BONES += [('thigh.'+side,(x*.6,0,.94),(x*.6,0,.55),'pelvis'),
      ('calf.'+side,(x*.6,0,.55),(x*.6,0,.15),'thigh.'+side),
      ('foot.'+side,(x*.6,0,.15),(x*.6,-.18,.10),'calf.'+side),
      ('arm.'+side,(x,0,1.44),(x*1.48,0,1.15),'spine'),
      ('forearm.'+side,(x*1.48,0,1.15),(x*1.6,-.03,.92),'arm.'+side)]

def rig_mesh(name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.armature_add(location=(0,0,0));rig=bpy.context.object;rig.name=name+'_Rig'
    bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
    for name_,head,tail,parent in BONES:
        b=rig.data.edit_bones.new(name_);b.head=head;b.tail=tail
        if parent:b.parent=rig.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    mod=mesh.modifiers.new('Labyrinth humanoid v1','ARMATURE');mod.object=rig;mesh.parent=rig
    for name_,_,_,_ in BONES:rig.pose.bones[name_].rotation_mode='XYZ'
    for clip,length in [('Idle',48),('Walk',24)]:
        rig.animation_data_create();action=bpy.data.actions.new(clip);rig.animation_data.action=action
        for f in range(1,length+2,3):
            t=(f-1)/length*2*math.pi
            for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)
            rig.pose.bones['pelvis'].location.y=(.018*abs(math.sin(t)) if clip=='Walk' else .007*math.sin(t))
            rig.pose.bones['spine'].rotation_euler.x=.018*math.sin(t)
            if clip=='Walk':
                for s,phase in [('L',1),('R',-1)]:
                    rig.pose.bones['thigh.'+s].rotation_euler.x=.30*math.sin(t)*phase
                    rig.pose.bones['calf.'+s].rotation_euler.x=max(0,-math.sin(t)*phase)*.30
                    rig.pose.bones['arm.'+s].rotation_euler.x=-.20*math.sin(t)*phase
            for p in rig.pose.bones:
                p.keyframe_insert(data_path='rotation_euler',frame=f)
                p.keyframe_insert(data_path='location',frame=f)
        track=rig.animation_data.nla_tracks.new();track.name=clip;track.strips.new(clip,1,action)
        rig.animation_data.action=None
    for tr in rig.animation_data.nla_tracks:tr.mute=True
    for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)
    return mesh,rig

records=[]
for index,(name,role) in enumerate([('Wayfinder','Hero: thread, chalk and compass'),('ThreadSpinnerAri','NPC: thread supply and path-marking quests'),('LanternKeeper','NPC: light supply and route guidance')]):
    parts=[];coat=rust if index==1 else teal if index==0 else slate
    cone((0,0,1.22),.27,.23,.48,coat)
    cone((0,0,.96),.30,.23,.20,coat,'pelvis')
    cone((0,0,1.03),.245,.245,.065,dark,'pelvis')
    box((0,-.295,1.04),(.1,.03,.075),gold,'pelvis')
    cone((0,0,1.53),.08,.08,.12,skin,'head')
    ball((0,-.015,1.70),(.145,.13,.19),skin)
    box((0,-.145,1.68),(.06,.065,.07),skin,'head')
    for x in [-.052,.052]:box((x,-.138,1.74),(.025,.018,.015),dark,'head',0)
    for s,x in [('L',.21),('R',-.21)]:
        segment((x*.6,0,.92),(x*.6,0,.56),.085,dark,'thigh.'+s)
        segment((x*.6,0,.56),(x*.6,0,.19),.07,coat,'calf.'+s)
        box((x*.6,-.065,.12),(.16,.28,.24),dark,'foot.'+s)
        segment((x,0,1.43),(x*1.48,0,1.15),.095,coat,'arm.'+s)
        segment((x*1.48,0,1.15),(x*1.6,-.03,.97),.067,coat,'forearm.'+s)
        ball((x*1.6,-.03,.93),(.06,.065,.08),skin,'forearm.'+s)
    if index==0:
        # Broad hood, asymmetric shoulder cape, compass and survey pack.
        ball((0,.018,1.78),(.18,.155,.19),teal)
        ball((0,-.105,1.74),(.125,.105,.145),skin)
        for x in [-.05,.05]:box((x,-.205,1.77),(.02,.012,.015),dark,'head',0)
        box((.18,.02,1.43),(.30,.39,.15),ivory)
        box((0,.23,1.28),(.36,.22,.37),dark)
        o=cone((-.13,-.255,1.30),.085,.085,.03,gold);o.rotation_euler.x=math.pi/2
        box((.19,-.22,1.17),(.04,.05,.16),ivory)
    elif index==1:
        # Wide brim, long apron and horizontal spool backpack.
        cone((0,0,1.89),.29,.29,.035,rust,'head',16)
        cone((0,0,1.97),.14,.10,.14,rust,'head')
        box((0,-.325,1.03),(.31,.045,.55),ivory,'pelvis')
        for z in [1.15,1.39]:
            o=cone((0,.27,z),.105,.105,.44,ivory);o.rotation_euler.y=math.pi/2
            for x in [-.23,.23]:
                o=cone((x,.27,z),.14,.14,.035,gold);o.rotation_euler.y=math.pi/2
    else:
        # Tall lantern hat and held cage lantern distinguish the keeper.
        cone((0,0,1.94),.19,.11,.27,slate,'head')
        cone((0,0,2.09),.13,0,.12,gold,'head')
        box((0,-.24,1.27),(.15,.035,.34),gold)
        x=.38;y=-.06;bone='forearm.L'
        ring((x,y,.87),.06,.012,gold,bone).rotation_euler.x=math.pi/2
        box((x,y,.68),(.18,.18,.27),light,bone)
        for z in [.53,.83]:box((x,y,z),(.25,.25,.055),gold,bone)
        for dx in [-.105,.105]:
            for dy in [-.105,.105]:box((x+dx,y+dy,.68),(.024,.024,.3),dark,bone,0)
    mesh,rig=rig_mesh('Mob_Lab_'+name)
    bpy.context.view_layer.update();tri=sum(len(p.vertices)-2 for p in mesh.data.polygons)
    radius=math.ceil(max(Vector(c).length for c in mesh.bound_box)*100)
    bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True)
    for tr in rig.animation_data.nla_tracks:tr.mute=False
    path=OUT/(mesh.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS')
    for tr in rig.animation_data.nla_tracks:tr.mute=True
    for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)
    records.append(dict(id=mesh.name,role=role,triangles=tri,bones=len(BONES),file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),radius_cm=radius,rig='LabyrinthHumanoidV1'))
    rig.location.x=index*1.5
    bpy.ops.object.text_add(location=(index*1.5-.6,-.65,.01));t=bpy.context.object;t.data.body=name;t.data.size=.14;t.data.materials.append(ivory)

bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.data.materials.append(slate)
bpy.ops.object.camera_add(location=(5,-9,5));cam=bpy.context.object;cam.rotation_euler=(Vector((1.5,0,1))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=5.6;bpy.context.scene.camera=cam
for loc,power in [((0,-4,7),1300),((4,3,6),1800)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=5
    o.rotation_euler=(Vector((1.5,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=4
s.render.resolution_x=1500;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.render.fps=24
s.render.filepath=str(OUT/'contact-sheet.png');s.world.color=(.18,.18,.18)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'labyrinth-cast-batch1.blend'));bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps({'assets':records,'status':'rigged-art; Unreal acceptance pending','weighting':'rigid parts, one bone per vertex','clips':['Idle','Walk']},indent=2))
(OUT/'labyrinth-cast.bba').write_text('BBA 1\n'+''.join(f"asset {r['id']} lod0 {r['triangles']} lod1 - radius {r['radius_cm']} switch {max(500,20*r['radius_cm'])}\n" for r in records))
print('LABYRINTH_CAST_OK',len(records))
