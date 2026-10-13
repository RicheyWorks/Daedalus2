"""Original Parcels creatures, machinery and helpful pets; rules remain proposals."""
from pathlib import Path
exec(compile(Path(__file__).with_name('realm_creature.py').read_text(),__file__,'exec'))
ROSTER=[('MailboxMimic','Mailbox encounter','mailbox'),('BurrowVole','Burrowing creature','vole'),
 ('HaySprite','Field creature','hay'),('ThistleBoar','Briar boar','boar'),('TwineSnake','Twine serpent','snake'),
 ('WheelbarrowGolem','Cart creature','cart'),('StampedeCalf','Field calf','calf'),('CombineCrab','Machine crab','crab'),
 ('RustwingHawk','Field hunter','hawk'),('BlightBailiff','Boss proposal; no deed authority','bailiff'),
 ('FenceLark','Ambient bird','lark'),('PuddleDuck','Ambient bird','duck'),('ParcelHelicopter','Realm mount; physics pending','heli'),
 ('DraftOx','Pack companion','ox'),('GyroGoat','Climbing companion','goat'),('ParcelPup','Helpful pet','pup'),
 ('CloverRabbit','Helpful pet','rabbit'),('BarnOwlet','Helpful pet','owl'),('SeedMouse','Helpful pet','mouse')]
records=[]
for i,(name,role,kind) in enumerate(ROSTER):
    parts=[];coat=mat('Parcels creature '+name,[(.30,.17,.10),(.42,.31,.12),(.14,.30,.18)][i%3])
    if kind in ['vole','boar','calf','ox','goat','pup','rabbit','mouse']:
        smooth((0,.05,.56),(.27,.38,.22),coat);smooth((0,-.30,.78),(.19,.19,.20),coat,'head');eyes(.08,-.46,.84)
        for side,sign in [('L',1),('R',-1)]:
            for y in [-.17,.27]:box((sign*.18,y,.25),(.10,.13,.45),ink,'leg.'+side,.025)
            cone((sign*.13,-.28,1.04),.055,0,.30 if kind=='rabbit' else .12,cream,'head',5)
        segment((0,.35,.66),(0,.65,.73),.035,cream,'tail')
        if kind in ['ox','goat']:
            for x in [-.18,.18]:segment((x,-.25,.98),(x*1.6,-.20,1.16),.035,brass,'head')
        if kind=='boar':
            for x in [-.11,.11]:cone((x,-.48,.68),.03,0,.17,cream,'head',5)
            for y in [-.03,.13,.29]:cone((0,y,.91),.05,0,.18,coat,'body',4)
        if kind=='goat':cone((0,-.35,.56),.04,0,.19,cream,'head')
        if kind=='mouse':
            for x in [-.14,.14]:smooth((x,-.23,.98),(.10,.04,.11),cream,'head')
        if kind=='pup':smooth((0,-.47,.76),(.065,.04,.045),ink,'head')
    elif kind in ['hawk','lark','duck','owl']:
        smooth((0,0,.62),(.18,.28,.22),coat);smooth((0,-.22,.89),(.17,.16,.19),coat,'head');eyes(.08,-.36,.94)
        box((0,-.42,.82),(.15,.16,.04),brass,'head',.01)
        for side,sign in [('L',1),('R',-1)]:
            box((sign*.28,0,.68),(.40,.22,.045),cream,'wing.'+side,.01)
            box((sign*.10,0,.19),(.09,.20,.35),brass,'leg.'+side,.01)
        if kind=='owl':
            for x in [-.08,.08]:ring((x,-.37,.94),.07,.02,cream,'head').rotation_euler.x=math.pi/2
        if kind=='hawk':cone((0,0,1.14),.055,0,.20,cream,'head',4)
    elif kind=='snake':
        for k in range(6):smooth((math.sin(k*.7)*.19,.11*k,.24+.035*k),(.15,.14,.12),cream,'tail' if k>2 else 'body')
        smooth((0,-.16,.52),(.19,.17,.16),coat,'head');eyes(.07,-.30,.58)
    elif kind=='hay':
        box((0,0,.60),(.42,.34,.60),cream);smooth((0,-.12,.94),(.17,.16,.15),coat,'head');eyes(.07,-.25,.99)
        for x in [-.14,0,.14]:segment((x,0,.8),(x+.04,0,1.3),.018,brass,'body')
        for side,sign in [('L',1),('R',-1)]:box((sign*.16,0,.19),(.08,.10,.37),coat,'leg.'+side)
    elif kind in ['mailbox','cart','crab','heli','bailiff']:
        if kind=='mailbox':
            box((0,0,.63),(.48,.56,.44),coat);box((0,-.30,.63),(.39,.03,.30),cream,'head');eyes(.10,-.33,.70)
            box((.3,0,.9),(.05,.08,.5),brass);box((.37,0,1.13),(.18,.08,.11),coat)
        elif kind=='cart':
            box((0,0,.65),(.60,.70,.20),cream);ring((0,-.3,.3),.20,.05,ink,'leg.L').rotation_euler.x=math.pi/2
            for x in [-.23,.23]:segment((x,.2,.65),(x,.55,.72),.035,coat,'body')
            smooth((0,-.28,.85),(.17,.16,.15),coat,'head');eyes(.07,-.41,.91)
        elif kind=='crab':
            box((0,0,.62),(.60,.5,.30),coat);box((0,-.30,.8),(.34,.13,.18),cream,'head');eyes(.10,-.38,.84)
            for side,sign in [('L',1),('R',-1)]:
                for y in [-.18,0,.18]:segment((sign*.22,y,.60),(sign*.50,y,.08),.025,brass,'leg.'+side)
                box((sign*.50,-.25,.68),(.24,.18,.13),cream,'wing.'+side)
        elif kind=='heli':
            smooth((0,0,.70),(.35,.48,.25),coat);smooth((0,-.3,.75),(.27,.16,.18),glass if 'glass' in globals() else white,'head')
            segment((0,.3,.7),(0,1.1,.8),.055,brass,'tail');box((0,.98,.96),(.32,.10,.07),cream,'tail')
            segment((0,0,.9),(0,0,1.25),.035,brass,'body')
            box((0,0,1.24),(1.6,.10,.035),cream,'wing.L');box((0,0,1.27),(.10,1.6,.035),cream,'wing.R')
            for side,sign in [('L',1),('R',-1)]:box((sign*.25,0,.33),(.06,.80,.07),ink,'leg.'+side)
        else:
            box((0,0,.72),(.47,.31,.55),coat);smooth((0,-.04,1.13),(.17,.15,.19),cream,'head');eyes(.07,-.18,1.17)
            box((0,0,1.33),(.40,.32,.045),ink,'head');box((0,0,1.4),(.27,.22,.12),ink,'head')
            for side,sign in [('L',1),('R',-1)]:box((sign*.16,0,.24),(.14,.18,.48),ink,'leg.'+side)
            box((.34,-.08,.75),(.28,.06,.34),cream,'wing.L')
    mesh,rig=monster_rig('Mob_Parcels_'+name)
    records.append(export_character(mesh,rig,role,'ParcelsCreatureV1',{'role_count':1,'behavior_status':'proposal; native binding pending'}))
    rig.location=((i%5)*2.8,(i//5)*2.8,0);label(name,i,5,2.8)
finish_scene(records,5,2.8,'parcels-creatures',['Idle','Walk','Attack','Hurt'])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='The Parcels'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'parcels.bba')
