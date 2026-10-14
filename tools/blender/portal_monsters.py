"""Source-keyed Portal bestiary: three VISUAL tiers, no stat or encounter-table changes."""
from pathlib import Path
import re
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
source_path=Path(__file__).resolve().parents[2]/'daedalus-core/src/main/java/com/daedalus/world/retro/RetroMonster.java'
source=source_path.read_text();source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
entries=re.findall(r'^\s*([A-Z_]+)\("([^"]+)",\s*(\d+),\s*(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+),',source,re.M)
assert len(entries)==15,'bestiary changed; review before exporting'
records=[]
def color(hexvalue,tier):
    v=int(hexvalue,16);base=[((v>>shift)&255)/255 for shift in [16,8,0]]
    return tuple(min(1,c*(1 if tier==1 else .85)+(.12 if tier==2 else .22 if tier==3 else 0)) for c in base)
def shape(kind,body,accent):
    if kind==0:
        ball((0,0,.4),(.5,.42,.36),body,'body');ball((0,-.2,.59),(.29,.25,.20),body,'head')
        box((0,-.43,.38),(.24,.04,.04),accent,'body')
    elif kind==1:
        cone((0,0,.6),.32,0,.85,body,'body');ring((0,0,.65),.36,.03,accent,'body')
        for x in [-.3,.3]:cone((x,0,.6),.09,0,.4,accent,'wing.L' if x>0 else 'wing.R')
    elif kind==2:
        ball((0,0,.54),(.38,.46,.31),body,'body');box((0,-.4,.65),(.29,.29,.25),accent,'head')
        for x in [-.27,0,.27]:cone((x,.08,.88),.085,0,.32,accent,'body',4)
        for x in [-.27,.27]:
            for y in [-.25,.25]:box((x,y,.21),(.13,.15,.42),body,'leg.L' if x>0 else 'leg.R')
    elif kind==3:
        cone((0,0,.38),.18,.12,.6,accent,'body');ball((0,0,.83),(.5,.42,.19),body,'head')
        for x,y in [(-.22,0),(.20,.10),(0,-.23)]:ball((x,y,.98),(.07,.07,.025),accent,'head')
    elif kind==4:
        box((0,0,.75),(.50,.32,.52),body,'body');box((0,0,1.13),(.34,.3,.28),body,'head')
        box((0,-.16,1.16),(.27,.025,.045),accent,'head')
        for x in [-.14,.14]:box((x,0,.25),(.16,.2,.5),body,'leg.L' if x>0 else 'leg.R')
        box((-.39,0,.81),(.12,.17,.4),accent,'wing.R');box((.37,-.05,.85),(.30,.10,.4),accent,'wing.L')
        box((-.4,0,1.08),(.05,.08,.5),accent,'wing.R')
    elif kind==5:
        ball((0,0,.65),(.20,.31,.23),body,'body');ball((0,-.3,.8),(.15,.17,.16),body,'head')
        for x in [-1,1]:
            o=box((x*.42,0,.7),(.65,.23,.045),body,'wing.L' if x>0 else 'wing.R');o.rotation_euler.y=x*.25
            for k in range(3):box((x*(.30+.16*k),.14,.69),(.12,.32-.06*k,.045),accent,'wing.L' if x>0 else 'wing.R')
    elif kind==6:
        box((0,0,.35),(.65,.47,.5),body,'body');box((0,.09,.78),(.66,.13,.3),body,'head')
        for x in [-.24,-.08,.08,.24]:cone((x,-.22,.65),.035,0,.18,accent,'head')
        for x in [-.24,.24]:box((x,-.25,.37),(.05,.035,.5),accent,'body')
    elif kind==7:
        ball((0,0,.7),(.36,.33,.36),body,'body');ball((0,-.31,.73),(.19,.04,.18),accent,'head');ball((0,-.355,.73),(.09,.02,.10),ink,'head')
    elif kind==8:
        ball((0,0,.65),(.32,.45,.3),body,'body');box((0,-.42,.9),(.28,.33,.24),body,'head')
        for x in [-.21,.21]:
            for y in [-.2,.24]:segment((x,y,.56),(x,y,.08),.07,accent,'leg.L' if x>0 else 'leg.R')
        segment((0,.32,.65),(0,.85,.88),.07,body,'tail')
        for sign in [-1,1]:
            o=box((sign*.43,.05,.91),(.62,.30,.05),accent,'wing.L' if sign>0 else 'wing.R');o.rotation_euler.y=sign*.3
            cone((sign*.1,-.37,1.08),.035,0,.2,accent,'head')
        for x in [-.08,.08]:box((x,-.59,.96),(.04,.03,.045),ink,'head',0)
    if kind!=7 and kind!=8:
        for x in [-.095,.095]:box((x,-.56 if kind==2 else -.445 if kind==0 else -.23 if kind==6 else -.17,.59 if kind in [0,2] else 1.16 if kind==4 else .43 if kind==3 else .75),(.045,.03,.04),ink,'head',0)

def monster_rig(name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.armature_add();rig=bpy.context.object;rig.name=name+'_Rig';bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
    bones=[('root',(0,0,0),(0,0,.2),None),('body',(0,0,.2),(0,0,.65),'root'),('head',(0,-.3,.65),(0,-.3,1.05),'body'),('tail',(0,.3,.65),(0,.7,.65),'body'),('leg.L',(.19,0,.65),(.19,0,.1),'body'),('leg.R',(-.19,0,.65),(-.19,0,.1),'body'),('wing.L',(.2,0,.8),(.65,0,.8),'body'),('wing.R',(-.2,0,.8),(-.65,0,.8),'body')]
    for bn,h,t,parent in bones:
        b=rig.data.edit_bones.new(bn);b.head=h;b.tail=t
        if parent:b.parent=rig.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');mesh.parent=rig;mod=mesh.modifiers.new('Portal creature rig','ARMATURE');mod.object=rig
    for p in rig.pose.bones:p.rotation_mode='XYZ'
    for clip,n in [('Idle',48),('Walk',24),('Attack',24),('Hurt',24)]:
        rig.animation_data_create();act=bpy.data.actions.new(clip);rig.animation_data.action=act
        for f in range(1,n+2,6 if clip=='Walk' else 3):
            phase=(f-1)/n*2*math.pi
            for p in rig.pose.bones:p.location=(0,0,0);p.rotation_euler=(0,0,0)
            rig.pose.bones['body'].location.y=.035*math.sin(phase)
            if clip=='Walk':
                for side,sign in [('L',1),('R',-1)]:rig.pose.bones['leg.'+side].rotation_euler.x=.24*math.sin(phase)*sign;rig.pose.bones['wing.'+side].rotation_euler.x=.26*math.sin(phase)*sign
            elif clip=='Attack':rig.pose.bones['head'].rotation_euler.x=-.3*(1-math.cos(phase))/2
            elif clip=='Hurt':rig.pose.bones['body'].rotation_euler.z=.18*math.sin(phase)
            for p in rig.pose.bones:p.keyframe_insert(data_path='rotation_euler',frame=f);p.keyframe_insert(data_path='location',frame=f)
        if clip=='Walk':
            for fc in act.fcurves:
                for key in fc.keyframe_points:key.interpolation='CONSTANT'
        tr=rig.animation_data.nla_tracks.new();tr.name=clip;tr.strips.new(clip,1,act);rig.animation_data.action=None
    return mesh,rig

variants=[(*entry,tier,False) for entry in entries for tier in [1,2,3]]+[('GOLDEN_PUFFCAP','GOLDEN PUFFCAP','3','0xF8B800','0xF0D090',1,True),('EGG_HATCHLING','EGG HATCHLING','8','0x3CA8B8','0xF0D090',1,True),('YOUNG_DRAGON','YOUNG DRAGON','8','0x2058A8','0xF0D090',1,True)]
for i,(key,title,kind,body_hex,accent_hex,tier,proposed) in enumerate(variants):
    parts=[];body=mat('Portal_'+key+'_T'+str(tier),color(body_hex,tier));accent=mat('Portal_accent_'+key+'_T'+str(tier),color(accent_hex,tier))
    shape(int(kind),body,accent)
    if key=='SHARD_TYRANT':
        for x in [-.12,0,.12]:cone((x,0,1.38),.04,0,.18,accent,'head')
    name='Mob_Portal_'+key+'_T'+str(tier);mesh,rig=monster_rig(name)
    records.append(export_character(mesh,rig,'Encounter visual: '+title,'PortalCreatureV1',{'source_monster':None if proposed else key,'source_file_sha256':source_hash,'visual_tier':tier,'new_species':proposed,'lifecycle_group':'PortalLandDragon' if kind=='8' else None,'role_count':1 if tier==1 and key!='YOUNG_DRAGON' else 0,'recommended_scale':.65 if key=='EGG_HATCHLING' else 1,'gameplay':'proposed' if proposed else 'reuse existing RetroMonster rules; no tier rebalance'}))
    rig.location=((i%7)*2.5,(i//7)*2.5,0);label(key+'_T'+str(tier),i,7,2.5)
finish_scene(records,7,2.5,'portal-bestiary',['Idle','Walk','Attack','Hurt'])
