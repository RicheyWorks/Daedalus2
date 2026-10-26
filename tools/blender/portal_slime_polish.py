"""Ten original slime individuals tied to the approved fifty-by-ten roster."""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_monsters.py').read_text().split('variants=')[0],__file__,'exec'))

def smooth(p,s,m,bone='body'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,location=p)
    o=bpy.context.object;o.scale=s;finish(o,m,bone)
    for polygon in o.data.polygons:polygon.use_smooth=True
    return o

records=[]
for i in range(10):
    parts=[]
    green=mat('Slime gel '+str(i),(.07+.008*i,.38+.008*i,.12+.004*i))
    shader=green.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.23;shader.inputs['Coat Weight'].default_value=.5
    moss=mat('Slime crest '+str(i),(.08,.20,.065));mouth=mat('Slime mouth '+str(i),(.02,.055,.025))
    width=.43+.012*(i%4);height=.34+.018*(i//4)
    smooth((0,0,.38),(width,.37,height),green)
    smooth((0,-.16,.57),(.32,.26,.23),green,'head')
    for x in [-1,1]:
        smooth((x*.19,-.34,.59),(.115,.055,.115 if i%2==0 else .095),cream,'head')
        smooth((x*.19+.012*((i%3)-1),-.39,.59),(.046,.018,.063),ink,'head')
        smooth((x*.19-.012,-.409,.62),(.015,.008,.018),white,'head')
        brow=box((x*.19,-.40,.73),(.16,.03,.025),moss,'head',.012);brow.rotation_euler.y=x*(.10+.045*i)
    for k in range(5):
        x=(k-2)*.043;z=.43+.10*(x*x/.01)
        smooth((x,-.39,z),(.032,.025,.018),mouth,'head')
    smooth((-.28,-.28,.45),(.05,.015,.025),moss,'head')
    for k in range(3+i%5):
        x=(k-(2+i%5)/2)*.11
        cone((x,.04,.75),.06,.012,.16+.025*(k%2),moss,'body',6)
    for x in [-.3,.3]:smooth((x,.10,.13),(.18,.23,.10),green)
    mesh,rig=monster_rig('Mob_Portal_BLIGHT_SLIME_Polish_'+str(i+1).zfill(2))
    for track in rig.animation_data.nla_tracks:
        for strip in track.strips:
            act=strip.action;rig.animation_data.action=act
            for curve in act.fcurves:
                for key in curve.keyframe_points:key.interpolation='BEZIER'
            length=48 if track.name=='Idle' else 24
            for frame in range(1,length+2,3):
                wave=math.sin((frame-1)/length*2*math.pi)
                body=rig.pose.bones['body'];body.scale=(1+.06*wave,1+.06*wave,1-.10*wave)
                body.keyframe_insert(data_path='scale',frame=frame)
                if track.name=='Walk':
                    body.location.z=.09*(1-math.cos((frame-1)/length*2*math.pi))
                    body.keyframe_insert(data_path='location',index=2,frame=frame)
            rig.animation_data.action=None
    for p in rig.pose.bones:p.scale=(1,1,1);p.location=(0,0,0);p.rotation_euler=(0,0,0)
    records.append(export_character(mesh,rig,'Existing Blight Slime encounter visual','PortalCreatureV1',
        {'role_count':0,'population_id':'Portal_enemy_BLIGHT_SLIME_'+str(i+1).zfill(2),
         'source_monster':'BLIGHT_SLIME','source_file_sha256':source_hash,'individual':i+1,
         'status':'art candidate; existing rules and native binding pending'}))
    rig.location=((i%5)*2.5,(i//5)*2.5,0);label('Slime '+str(i+1),i,5,2.5)
finish_scene(records,5,2.5,'portal-slime-polish',['Idle','Walk','Attack','Hurt'])
