"""Four hero forms and twelve original Portal townsfolk. Blender --python this.py -- OUTPUT."""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
ROSTER=[('Knight','Hero form: armoured sword and shield','knight'),('Tinker','Hero form: tools and mechanical pack','tinker'),('Herbalist','Hero form: staff and ingredient satchel','herbalist'),('Bard','Hero form: instrument and travel coat','bard'),('InnkeeperRusk','Inn and rest','inn'),('SmithGarra','Equipment upgrades','smith'),('ItemShopPim','Realm supplies','shop'),('QueenOfCinders','Castle quest giver','queen'),('RoyalScribe','Save point presentation','scribe'),('FortuneTeller','Clues and risk guidance','fortune'),('Keymaker','Lock and key guidance','key'),('WellChild','Water and town hints','child'),('NightWatch','Town safety and travel clues','watch'),('RetiredHero','Optional veteran quest','veteran'),('FerryWoman','Water crossing role','ferry'),('TavernBard','Touring jukebox cue role','bard')]
records=[]
for i,(name,role,kind) in enumerate(ROSTER):
    parts=[];coat=mat('Portal_'+name,(.08,.22,.52) if kind in ['knight','watch','veteran'] else (.12,.40,.22) if kind=='herbalist' else (.45,.09,.14) if kind in ['queen','bard'] else (.42,.24,.10))
    box((0,0,1.22),(.48,.30,.48),coat,'spine',.025);box((0,0,.94),(.48,.32,.13),ink,'pelvis')
    ball((0,-.015,1.73),(.14,.13,.18),face,'head');box((0,-.145,1.71),(.055,.05,.05),face,'head')
    for x in [-.05,.05]:box((x,-.14,1.77),(.025,.016,.018),ink,'head',0)
    for side,x in [('L',.21),('R',-.21)]:
        segment((x*.6,0,.94),(x*.6,0,.55),.085,coat,'thigh.'+side);segment((x*.6,0,.55),(x*.6,0,.15),.065,ink,'calf.'+side)
        box((x*.6,-.055,.12),(.16,.26,.24),ink,'foot.'+side)
        segment((x,0,1.44),(x*1.48,0,1.15),.09,coat,'arm.'+side);segment((x*1.48,0,1.15),(x*1.6,-.03,.93),.065,coat,'forearm.'+side)
        ball((x*1.6,-.03,.92),(.06,.065,.075),face,'forearm.'+side)
    if kind in ['knight','watch','veteran']:
        box((0,0,1.91),(.34,.28,.14),brass,'head');box((0,-.16,1.78),(.32,.05,.08),brass,'head')
        for x in [-.25,.25]:box((x,0,1.43),(.22,.32,.16),brass,'spine')
        box((-.38,0,1.2),(.055,.09,.6),white,'forearm.R');box((-.38,0,.97),(.28,.10,.045),brass,'forearm.R')
        box((.37,-.08,1.12),(.32,.09,.43),coat,'forearm.L');box((.37,-.14,1.12),(.20,.03,.10),brass,'forearm.L')
        if kind=='watch':cone((0,0,2.1),.06,0,.34,cream,'head')
        if kind=='veteran':box((0,.2,1.15),(.5,.09,.64),cream,'spine');box((-.05,-.16,1.78),(.085,.04,.06),ink,'head')
    elif kind=='tinker':
        box((0,.23,1.25),(.4,.22,.40),brass,'spine');ring((0,.36,1.30),.13,.035,ink,'spine').rotation_euler.x=math.pi/2
        box((0,-.16,1.8),(.30,.07,.09),brass,'head');box((-.37,0,1.12),(.16,.12,.30),brass,'forearm.R')
    elif kind=='herbalist':
        cone((0,0,1.95),.23,.07,.23,coat,'head');box((.15,-.23,1.17),(.18,.1,.28),cream,'spine')
        segment((-.37,0,.3),(-.37,0,1.62),.035,ink,'forearm.R');ball((-.37,0,1.7),(.10,.10,.14),coat,'forearm.R')
    elif kind=='bard':
        cone((0,0,1.92),.25,.25,.04,coat,'head');cone((0,0,2.0),.13,.13,.12,coat,'head')
        ball((0,-.25,1.10),(.18,.065,.23),brass,'spine');box((.1,-.25,1.39),(.05,.06,.4),ink,'spine')
        if name=='TavernBard':
            box((0,.18,1.2),(.55,.08,.75),coat,'spine')
            ring((0,-.28,1.10),.22,.03,cream,'spine').rotation_euler.x=math.pi/2
            cone((0,0,1.92),.35,.35,.04,cream,'head')
    elif kind=='queen':
        cone((0,0,.98),.33,.21,.45,coat,'pelvis')
        for x in [-.12,0,.12]:cone((x,0,1.98),.05,0,.22,brass,'head')
        box((0,.17,1.21),(.50,.06,.65),cream,'spine')
    elif kind in ['inn','shop','smith']:
        box((0,-.18,1.12),(.32,.04,.51),cream,'spine')
        if kind=='smith':box((-.38,0,1.16),(.33,.13,.15),ink,'forearm.R')
        elif kind=='shop':box((.37,0,1.05),(.22,.18,.25),coat,'forearm.L')
        else:cone((.36,0,1.1),.09,.09,.18,brass,'forearm.L')
    elif kind in ['scribe','fortune','key']:
        box((0,.22,1.23),(.35,.18,.38),cream,'spine')
        if kind=='scribe':box((0,-.24,1.18),(.35,.06,.3),cream,'spine')
        elif kind=='fortune':ball((0,-.25,1.2),(.14,.14,.14),white,'spine');cone((0,0,1.96),.23,.09,.23,coat,'head')
        else:ring((.36,0,1.17),.11,.035,brass,'forearm.L').rotation_euler.x=math.pi/2;box((.36,0,.97),(.05,.06,.3),brass,'forearm.L')
    elif kind=='child':box((0,0,1.93),(.29,.27,.1),coat,'head');cone((.34,0,1.07),.09,.07,.18,cream,'forearm.L')
    elif kind=='ferry':segment((-.37,0,.2),(-.37,0,1.6),.025,ink,'forearm.R');box((-.37,0,.32),(.18,.07,.3),cream,'forearm.R')
    mesh,rig=rig_mesh('Mob_Portal_'+name);animate_humanoid(rig)
    records.append(export_character(mesh,rig,role,'PortalHumanoidV1',{'role_status':'art form; existing gameplay role must be bound'}))
    rig.location=((i%4)*2.5,(i//4)*2.5,0);label(name,i,4,2.5)
finish_scene(records,4,2.5,'portal-town-cast',['Idle','Walk','Attack','Hurt'])
