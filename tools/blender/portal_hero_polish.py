"""Original hero polish pilot. Keeps the shared rest rig; not final character art.

Blender --background --python SCRIPT -- OUTPUT
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))

def round_part(p,s,m,bone='head'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=p)
    o=bpy.context.object;o.scale=s;finish(o,m,bone)
    for polygon in o.data.polygons:polygon.use_smooth=True
    return o

coat=mat('Indigo woven coat',(.045,.14,.26)); leather=mat('Oxblood leather',(.19,.065,.035))
metal=mat('Hammered bronze',(.56,.32,.10),.72); hair=mat('Chestnut hair',(.10,.045,.025))
for material in [metal,white]:material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.34
parts=[]
round_part((0,0,1.24),(.24,.16,.30),coat,'spine')
box((0,0,.97),(.45,.32,.12),leather,'pelvis',.035)
for x in [-.16,0,.16]:box((x,-.17,1.05),(.11,.07,.20),metal,'pelvis',.025)
box((0,-.195,1.29),(.32,.08,.30),metal,'spine',.06)
for z in [1.19,1.29,1.39]:box((0,-.244,z),(.21,.018,.012),cream,'spine',0)
round_part((0,0,1.72),(.15,.135,.185),face)
round_part((0,-.137,1.70),(.033,.036,.043),face)
for x in [-.057,.057]:
    round_part((x,-.119,1.758),(.036,.017,.025),cream)
    round_part((x,-.136,1.758),(.015,.012,.018),ink)
    round_part((x-.004,-.146,1.765),(.005,.003,.005),white)
    segment((x-.028,-.13,1.803),(x+.024,-.13,1.812),.011,hair,'head')
segment((-.034,-.127,1.65),(.025,-.127,1.655),.009,leather,'head')
round_part((0,.018,1.855),(.16,.135,.085),hair)
for x,z in [(-.12,1.86),(-.075,1.88),(-.02,1.90),(.04,1.89),(.10,1.87)]:
    round_part((x,-.075,z),(.055,.07,.07),hair)
round_part((-.145,0,1.73),(.04,.05,.07),face)
round_part((.145,0,1.73),(.04,.05,.07),face)
for side,x in [('L',.21),('R',-.21)]:
    segment((x*.6,0,.94),(x*.6,0,.55),.085,coat,'thigh.'+side)
    segment((x*.6,0,.55),(x*.6,0,.15),.07,leather,'calf.'+side)
    round_part((x*.6,-.07,.11),(.095,.16,.105),leather,'foot.'+side)
    box((x*.6,-.09,.04),(.18,.29,.055),ink,'foot.'+side,.02)
    round_part((x,0,1.44),(.13,.18,.12),metal,'arm.'+side)
    segment((x,0,1.44),(x*1.48,0,1.15),.08,coat,'arm.'+side)
    segment((x*1.48,0,1.15),(x*1.6,-.03,.93),.07,leather,'forearm.'+side)
    round_part((x*1.6,-.03,.92),(.075,.075,.08),leather,'forearm.'+side)
    ring((x*.6,0,.46),.08,.015,metal,'calf.'+side)
# Split travel cape and satchel add readable asymmetry without new rig bones.
for x in [-.15,.15]:box((x,.20,1.18),(.26,.05,.65),coat,'spine',.035)
box((.18,-.20,1.01),(.16,.11,.20),leather,'pelvis',.03)
round_part((.39,-.10,1.15),(.22,.055,.29),leather,'forearm.L')
o=ring((.39,-.15,1.15),.22,.025,metal,'forearm.L');o.rotation_euler.x=math.pi/2;o.scale.y=1.25
box((.39,-.17,1.15),(.025,.02,.31),metal,'forearm.L',.005)
box((-.39,0,1.30),(.055,.07,.66),white,'forearm.R',.015)
box((-.39,0,.99),(.25,.08,.04),metal,'forearm.R',.015)
mesh,rig=rig_mesh('Mob_Portal_Knight_Polish');animate_humanoid(rig)
for track in rig.animation_data.nla_tracks:
    for strip in track.strips:
        for curve in strip.action.fcurves:
            for key in curve.keyframe_points:key.interpolation='BEZIER'
record=export_character(mesh,rig,'Hero polish review; existing knight rules','PortalHumanoidV1',
                        {'role_count':0,'replaces_visual_candidate':'Mob_Portal_Knight','status':'review pilot'})
finish_scene([record],1,2.5,'portal-hero-polish',['Idle','Walk','Attack','Hurt'])
