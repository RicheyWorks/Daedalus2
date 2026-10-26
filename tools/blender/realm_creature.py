"""Shared original creature rig; independent of any realm's gameplay table."""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
_box,_cone,_ring=box,cone,ring
def box(p,s,m,bone='body',bevel=.015):return _box(p,s,m,bone,bevel)
def cone(p,r1,r2,d,m,bone='body',n=10):return _cone(p,r1,r2,d,m,bone,n)
def ring(p,r,minor,m,bone='body'):return _ring(p,r,minor,m,bone)
def smooth(p,s,m,bone='body'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=p)
    obj=bpy.context.object;obj.scale=s;finish(obj,m,bone)
    for polygon in obj.data.polygons:polygon.use_smooth=True
    return obj
def eyes(x=.1,y=-.34,z=.83):
    for sign in [-1,1]:
        smooth((sign*x,y,z),(.048,.025,.060),cream,'head')
        smooth((sign*x,y-.023,z),(.022,.015,.035),ink,'head')

def monster_rig(name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.armature_add();rig=bpy.context.object;rig.name=name+'_Rig';bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
    bones=[('root',(0,0,0),(0,0,.2),None),('body',(0,0,.2),(0,0,.65),'root'),('head',(0,-.3,.65),(0,-.3,1.05),'body'),('tail',(0,.3,.65),(0,.7,.65),'body'),('leg.L',(.19,0,.65),(.19,0,.1),'body'),('leg.R',(-.19,0,.65),(-.19,0,.1),'body'),('wing.L',(.2,0,.8),(.65,0,.8),'body'),('wing.R',(-.2,0,.8),(-.65,0,.8),'body')]
    for bone_name,head,tail,parent in bones:
        bone=rig.data.edit_bones.new(bone_name);bone.head=head;bone.tail=tail
        if parent:bone.parent=rig.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');mesh.parent=rig;modifier=mesh.modifiers.new('Portal creature rig','ARMATURE');modifier.object=rig
    for pose in rig.pose.bones:pose.rotation_mode='XYZ'
    for clip,length in [('Idle',48),('Walk',24),('Attack',24),('Hurt',24)]:
        rig.animation_data_create();action=bpy.data.actions.new(clip);rig.animation_data.action=action
        for frame in range(1,length+2,6 if clip=='Walk' else 3):
            phase=(frame-1)/length*2*math.pi
            for pose in rig.pose.bones:pose.location=(0,0,0);pose.rotation_euler=(0,0,0)
            rig.pose.bones['body'].location.y=.035*math.sin(phase)
            if clip=='Walk':
                for side,sign in [('L',1),('R',-1)]:
                    rig.pose.bones['leg.'+side].rotation_euler.x=.24*math.sin(phase)*sign
                    rig.pose.bones['wing.'+side].rotation_euler.x=.26*math.sin(phase)*sign
            elif clip=='Attack':rig.pose.bones['head'].rotation_euler.x=-.3*(1-math.cos(phase))/2
            elif clip=='Hurt':rig.pose.bones['body'].rotation_euler.z=.18*math.sin(phase)
            for pose in rig.pose.bones:pose.keyframe_insert(data_path='rotation_euler',frame=frame);pose.keyframe_insert(data_path='location',frame=frame)
        if clip=='Walk':
            for curve in action.fcurves:
                for key in curve.keyframe_points:key.interpolation='CONSTANT'
        track=rig.animation_data.nla_tracks.new();track.name=clip;track.strips.new(clip,1,action);rig.animation_data.action=None
    return mesh,rig
