"""Original Shardstead workers. Run Blender background with -- OUTPUT. Reuses owned cast rig."""
from pathlib import Path
exec(compile(Path(__file__).with_name('realm_humanoid.py').read_text(),__file__,'exec'))

def animate_worker_activity(rig):
    """Append job motions to the existing rig; no root motion or gameplay events."""
    for clip,length in [('Mine',36),('Trade',48),('Repair',36)]:
        rig.animation_data_create()
        action=bpy.data.actions.new(clip)
        rig.animation_data.action=action
        for frame in range(1,length+2,3):
            phase=(frame-1)/length*2*math.pi
            stroke=(1-math.cos(phase))/2
            for pose in rig.pose.bones:
                pose.rotation_euler=(0,0,0)
                pose.location=(0,0,0)
            if clip=='Mine':
                rig.pose.bones['spine'].rotation_euler.x=.12*stroke
                rig.pose.bones['arm.R'].rotation_euler.x=-1.15*stroke
                rig.pose.bones['forearm.R'].rotation_euler.x=-.45*stroke
                rig.pose.bones['arm.L'].rotation_euler.x=-.35*stroke
            elif clip=='Trade':
                rig.pose.bones['arm.L'].rotation_euler.x=-.65*stroke
                rig.pose.bones['forearm.L'].rotation_euler.x=-.30*stroke
                rig.pose.bones['head'].rotation_euler.x=.06*stroke
            else:
                rig.pose.bones['spine'].rotation_euler.x=.08
                for side,sign in [('R',1),('L',-1)]:
                    rig.pose.bones['arm.'+side].rotation_euler.x=-.55
                    rig.pose.bones['forearm.'+side].rotation_euler.x=-.30+.12*math.sin(phase)*sign
            for pose in rig.pose.bones:
                pose.keyframe_insert(data_path='rotation_euler',frame=frame)
                pose.keyframe_insert(data_path='location',frame=frame)
        track=rig.animation_data.nla_tracks.new()
        track.name=clip
        track.strips.new(clip,1,action)
        track.mute=True
        rig.animation_data.action=None
    for pose in rig.pose.bones:
        pose.rotation_euler=(0,0,0)
        pose.location=(0,0,0)

records=[]
roles=[('Twaker_Prospector','prospector',(.12,.36,.38)),('Twaker_Cachekeeper','crystal cache keeper',(.34,.16,.48)),('Twaker_Trader','barter merchant',(.55,.29,.12)),('Shardstead_Farmer','food producer',(.22,.40,.13)),('Shardstead_Energywright','energy producer',(.12,.30,.52)),('Shardstead_Rescuer','unicorn rescue guide',(.57,.22,.24))]
for i,(name,role,color) in enumerate(roles):
    parts.clear();coat=mat(name+' coat',color);humanoid_body(coat)
    # Wide brim, brass faceplate, layered backpack and job-specific tools.
    cone((0,0,1.91),.23,.23,.045,coat,'head');cone((0,0,2.00),.15,.11,.16,coat,'head')
    box((0,.23,1.30),(.34,.20,.35),ink,'spine',.035)
    box((0,.34,1.36),(.20,.025,.10),brass,'spine')
    if i in (0,1):
        crystal=mat(name+' crystal',(.31,.74,.85) if i==0 else (.68,.32,.84),.15)
        cone((.34,-.03,1.08),.07,0,.24,crystal,'forearm.L',6)
        segment((-.34,-.04,.86),(-.34,-.04,1.37),.025,brass,'forearm.R')
        box((-.34,-.04,1.36),(.30,.045,.045),brass,'forearm.R')
    elif i==2:
        box((.33,-.12,1.02),(.20,.10,.17),brass,'forearm.L')
        ring((0,-.17,1.25),.08,.013,brass,'spine')
    elif i==3:
        segment((-.34,-.04,.85),(-.34,-.04,1.42),.023,cream,'forearm.R')
        box((-.34,-.04,1.43),(.24,.055,.06),brass,'forearm.R')
    elif i==4:
        for x in (-.1,.1):cone((x,.27,1.57),.07,.07,.28,brass,'spine')
        ball((0,-.18,1.34),(.06,.025,.06),white,'spine')
    else:
        box((0,-.17,1.28),(.17,.03,.045),white,'spine')
        box((0,-.17,1.28),(.045,.03,.17),white,'spine')
        ring((.32,-.05,1.05),.10,.018,cream,'forearm.L')
    mesh,rig=rig_mesh(name);animate_humanoid(rig);animate_worker_activity(rig)
    records.append(export_character(mesh,rig,role,'shared-humanoid-14',{'realm':'Island','activity':'Shardstead'}))
    rig.location=(i%3*3,i//3*3,0);label(role,i,3,3)
finish_scene(records,3,3,'shardstead-workers',['Idle','Walk','Attack','Hurt','Mine','Trade','Repair'],render='--render' in sys.argv)

manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='Island';manifest['activity']='Shardstead';(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
