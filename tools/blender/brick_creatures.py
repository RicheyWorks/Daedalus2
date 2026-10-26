"""Original studded constructs, companions and pets; native behavior pending."""
from pathlib import Path
exec(compile(Path(__file__).with_name('realm_creature.py').read_text(),__file__,'exec'))
ROSTER=[('Brickbug','Construct encounter','bug'),('LooseStud','Construct encounter','stud'),
 ('PlateCrab','Construct encounter','crab'),('HingeHound','Construct encounter','hound'),
 ('SlopeSlug','Construct encounter','slug'),('RebuildRex','Boss proposal','rex'),
 ('WindUpKnight','Construct encounter','knight'),('TowerTitan','Boss proposal','tower'),
 ('MagnetMoth','Construct encounter','moth'),('Unmaker','Boss proposal; visual only, no structure authority','hand'),
 ('ClockworkPigeon','Ambient bird','bird'),('SpringFrog','Ambient creature','frog'),
 ('BrickPlane','Realm vehicle; flight pending','plane'),('BrickPony','Realm mount','pony'),
 ('HoverCart','Realm vehicle; hover physics pending','cart'),('Studpup','Helpful pet','pup'),
 ('TileTurtle','Helpful pet','turtle'),('SpinnerTop','Helpful pet','top'),('PocketBot','Helpful pet','bot')]

def plate(p,s,m,bone='body'):
    box(p,s,m,bone,.025)
    for x in [-s[0]*.25,s[0]*.25]:
        cone((p[0]+x,p[1],p[2]+s[2]/2+.025),.04,.04,.05,brass,bone,8)

def legs(count=2):
    for side,sign in [('L',1),('R',-1)]:
        for k in range(count):
            y=(k-(count-1)/2)*.25
            box((sign*.22,y,.24),(.12,.16,.46),ink,'leg.'+side,.02)

records=[]
for i,(name,role,kind) in enumerate(ROSTER):
    parts=[];coat=mat('Brick construct '+name,[(.60,.10,.065),(.055,.28,.50),(.66,.43,.055),(.09,.38,.22)][i%4])
    if kind in ['hound','pony','pup','rex']:
        plate((0,.05,.65),(.45,.60,.30),coat);plate((0,-.35,.87),(.30,.30,.28),coat,'head');eyes(.075,-.52,.93)
        legs(1 if kind=='rex' else 2)
        box((0,-.53,.79),(.24,.17,.10),cream,'head')
        box((0,.54,.70),(.10,.48,.10),coat,'tail')
        for x in [-.10,.10]:box((x,-.29,1.08),(.07,.10,.18),brass,'head')
        if kind=='rex':
            for y in [.03,.22,.41]:cone((0,y,.95),.08,0,.22,brass,'body',4)
            for side,sign in [('L',1),('R',-1)]:box((sign*.29,-.16,.70),(.10,.30,.10),cream,'wing.'+side)
        if kind=='pony':box((0,.08,.86),(.33,.30,.12),ink)
        if kind=='pup':ring((0,-.19,.73),.19,.025,brass,'head').rotation_euler.x=math.pi/2
    elif kind in ['bug','crab','slug','turtle','frog']:
        plate((0,0,.50),(.56,.64,.20 if kind=='slug' else .30),coat)
        plate((0,-.34,.63),(.27,.20,.20),cream,'head');eyes(.075,-.46,.68)
        if kind!='slug':legs(3 if kind in ['bug','crab'] else 2)
        if kind=='crab':
            for side,sign in [('L',1),('R',-1)]:plate((sign*.46,-.27,.62),(.25,.30,.10),coat,'wing.'+side)
        if kind=='bug':
            for x in [-.09,.09]:box((x,-.30,.87),(.025,.035,.25),brass,'head')
        if kind=='slug':
            for y in [.05,.27,.49]:box((0,y,.60),(.40,.16,.16),coat)
        if kind=='turtle':plate((0,.06,.73),(.47,.48,.18),brass)
        if kind=='frog':
            for side,sign in [('L',1),('R',-1)]:box((sign*.30,.20,.20),(.20,.35,.15),coat,'leg.'+side)
    elif kind in ['bird','moth','plane']:
        plate((0,0,.70),(.26,.70,.20),coat);plate((0,-.34,.87),(.24,.25,.18),cream,'head');eyes(.06,-.48,.90)
        for side,sign in [('L',1),('R',-1)]:
            plate((sign*.43,0,.76),(.65,.38,.06),coat,'wing.'+side)
            box((sign*.12,0,.26),(.06,.19,.37),ink,'leg.'+side)
        plate((0,.48,.77),(.40,.22,.07),brass,'tail')
        if kind=='plane':
            box((0,-.53,.74),(.65,.04,.07),ink,'head');box((0,.06,.93),(.20,.25,.14),ink)
        if kind=='moth':
            for x in [-.08,.08]:box((x,-.22,1.05),(.02,.025,.26),brass,'head')
    elif kind in ['knight','tower','bot']:
        plate((0,0,.76),(.44,.31,.46),coat);plate((0,-.04,1.15),(.30,.25,.27),cream,'head');eyes(.07,-.18,1.19);legs(1)
        for side,sign in [('L',1),('R',-1)]:box((sign*.34,0,.75),(.15,.18,.35),coat,'wing.'+side)
        if kind=='knight':
            ring((0,.24,.83),.18,.035,brass).rotation_euler.x=math.pi/2
            box((.38,-.08,.97),(.05,.06,.62),cream,'wing.L')
        if kind=='tower':
            for x in [-.16,0,.16]:box((x,0,1.40),(.10,.27,.16),coat,'head')
            plate((0,0,.89),(.53,.38,.15),brass)
        if kind=='bot':cone((0,0,1.43),.045,.045,.18,brass,'head',8)
    elif kind=='hand':
        plate((0,0,.63),(.65,.22,.48),coat);eyes(.12,-.14,.74)
        for k,x in enumerate([-.24,-.08,.08,.24]):box((x,0,1.04),(.11,.20,.45-.06*abs(k-1)),cream,'head')
        box((-.42,0,.68),(.24,.19,.12),brass,'wing.R');box((0,0,.24),(.28,.22,.30),ink)
    elif kind=='cart':
        plate((0,0,.55),(.65,.75,.17),coat);plate((0,-.35,.74),(.32,.15,.18),cream,'head');eyes(.08,-.44,.78)
        for side,sign in [('L',1),('R',-1)]:
            for y in [-.22,.22]:cone((sign*.25,y,.29),.13,.08,.19,brass,'leg.'+side,8)
        box((0,.25,.77),(.50,.06,.28),coat)
    elif kind=='top':
        cone((0,0,.48),.06,.36,.65,coat);cone((0,0,.84),.36,.12,.09,brass)
        plate((0,-.10,.94),(.24,.18,.16),cream,'head');eyes(.06,-.21,.98)
    else:
        cone((0,0,.50),.30,.30,.38,coat, n=12);plate((0,-.06,.79),(.25,.22,.20),cream,'head');eyes(.07,-.19,.83);legs(1)
    mesh,rig=monster_rig('Mob_Bricks_'+name)
    records.append(export_character(mesh,rig,role,'BrickCreatureV1',{'role_count':1,'behavior_status':'proposal; native binding pending'}))
    rig.location=((i%5)*2.8,(i//5)*2.8,0);label(name,i,5,2.8)
finish_scene(records,5,2.8,'brick-creatures',['Idle','Walk','Attack','Hurt'])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='Brick Realm'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'bricks.bba')
