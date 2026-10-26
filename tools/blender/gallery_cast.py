"""Original Gallery City cast. Blender --background --python SCRIPT -- OUTPUT.

Shared humanoid rest rig; role props are distinct. Quest descriptions are
presentation proposals, not implemented rewards or interactions.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(), __file__, 'exec'))

ROSTER = [
    ('Sketcher', 'Hero brush and palette', 'brush'),
    ('CuratorVell', 'Gallery quest presentation', 'frame'),
    ('FrameHangerTwins', 'Frame pulley crew role', 'pulley'),
    ('VarnishMonk', 'Painting protection supplies proposal', 'flask'),
    ('RestorerAma', 'Mural restoration guidance', 'roller'),
    ('PigmentMiner', 'Pigment crafting guidance', 'pick'),
    ('GalleryGuard', 'Gallery access guidance', 'guard'),
    ('StreetMuralist', 'Painted travel hints proposal', 'brush'),
    ('LightTailor', 'Realm cosmetic presentation', 'spool'),
    ('DroneMechanicPell', 'Drone upgrade presentation', 'gear'),
    ('CriticBloom', 'Build review quest proposal', 'book'),
    ('LostSelfPortrait', 'Missing frame quest proposal', 'portrait'),
    ('EchoChoir', 'Touring jukebox district cue proposal', 'choir'),
]
records=[]
for i,(name,role,kind) in enumerate(ROSTER):
    parts=[]
    coat=mat('Gallery '+name, [(.16,.32,.43),(.43,.19,.35),(.25,.42,.30)][i%3])
    box((0,0,1.22),(.46,.30,.47),coat,'spine')
    box((0,0,.96),(.45,.32,.12),brass,'pelvis')
    ball((0,0,1.73),(.14,.13,.18),face,'head')
    for x in [-.05,.05]:box((x,-.13,1.77),(.026,.02,.022),ink,'head',0)
    for side,x in [('L',.21),('R',-.21)]:
        segment((x*.6,0,.94),(x*.6,0,.55),.085,coat,'thigh.'+side)
        segment((x*.6,0,.55),(x*.6,0,.15),.065,ink,'calf.'+side)
        box((x*.6,-.05,.12),(.16,.25,.22),ink,'foot.'+side)
        segment((x,0,1.44),(x*1.48,0,1.15),.09,coat,'arm.'+side)
        segment((x*1.48,0,1.15),(x*1.6,-.03,.93),.065,coat,'forearm.'+side)
        ball((x*1.6,-.03,.92),(.065,.065,.07),face,'forearm.'+side)
    # Frames, tools and equipment differentiate occupations beyond palettes.
    if kind in ['frame','portrait']:
        for x in [-.24,.24]:box((x,-.23,1.2),(.06,.06,.52),brass,'spine')
        for z in [.94,1.46]:box((0,-.23,z),(.54,.06,.06),brass,'spine')
        if kind=='portrait':box((0,-.20,1.2),(.40,.025,.44),cream,'spine')
        else:
            for x in [-.075,.075]:ring((x,-.14,1.77),.06,.015,brass,'head').rotation_euler.x=math.pi/2
    elif kind in ['brush','roller','pick','guard']:
        segment((-.38,0,.55),(-.38,0,1.65),.025,ink,'forearm.R')
        if kind=='brush':cone((-.38,0,1.72),.065,.02,.20,cream,'forearm.R');ball((.36,-.07,1.1),(.18,.05,.22),brass,'forearm.L')
        elif kind=='roller':box((-.38,0,1.67),(.36,.12,.12),cream,'forearm.R')
        elif kind=='pick':box((-.38,0,1.65),(.40,.07,.07),brass,'forearm.R')
        else:box((0,0,1.94),(.34,.29,.15),brass,'head');box((.37,-.06,1.15),(.3,.08,.4),brass,'forearm.L')
    elif kind in ['pulley','gear','spool']:
        ring((0,.27,1.2),.22,.055,brass,'spine').rotation_euler.x=math.pi/2
        box((0,.18,1.2),(.38,.12,.42),ink,'spine')
        if kind=='gear':
            for z in [1.05,1.2,1.35]:box((-.37,0,z),(.22,.11,.07),brass,'forearm.R')
        elif kind=='pulley':segment((.36,0,.9),(.36,0,1.55),.03,cream,'forearm.L')
        else:cone((.36,0,1.12),.13,.13,.25,cream,'forearm.L')
    elif kind=='flask':cone((.36,0,1.1),.13,.07,.25,white,'forearm.L');cone((0,0,1.95),.24,.08,.23,coat,'head')
    elif kind=='book':box((0,-.24,1.18),(.38,.08,.32),cream,'spine');box((0,0,1.96),(.40,.28,.04),ink,'head')
    elif kind=='choir':
        for x in [-.22,0,.22]:cone((x,.20,1.54),.055,.055,.35,brass,'spine')
        box((0,-.17,1.12),(.38,.04,.26),cream,'spine')
    mesh,rig=rig_mesh('Mob_Gallery_'+name);animate_humanoid(rig)
    records.append(export_character(mesh,rig,role,'GalleryHumanoidV1',{'role_count':1,'role_status':'proposal; native binding pending'}))
    rig.location=((i%4)*2.5,(i//4)*2.5,0);label(name,i,4,2.5)
finish_scene(records,4,2.5,'gallery-city-cast',['Idle','Walk','Attack','Hurt'])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='Gallery City'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'portal.bba').replace(OUT/'gallery.bba')
