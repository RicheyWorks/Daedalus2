"""Original Brick Realm cast; modular body/rest, distinct tools and silhouettes."""
from pathlib import Path
exec(compile(Path(__file__).with_name('realm_humanoid.py').read_text(),__file__,'exec'))
ROSTER=[('Builder','Hero builder','hero'),('ForemanKip','Blueprint quest guide','foreman'),
 ('BrickBaker','Kiln crafting guide','baker'),('BlueprintArchivist','Recipe archive','archive'),
 ('CraneOperatorSal','Structure crew','crane'),('DemolitionDuo','Demolition challenge representative','demo'),
 ('MayorMinifold','Town quest guide','mayor'),('AirfieldAceNova','Plane mount guide','pilot'),
 ('ToySoldierSergeant','Tactics guide','soldier'),('MissingPieceCollector','Collection quests','collector'),
 ('AdhesiveAlchemist','NonHalloween Glue Witch art reinterpretation','glue'),
 ('Studmonger','Realm game-currency exchange presentation','merchant'),('BuilderKidsClub','Club representative','kid')]
records=[]
for i,(name,role,kind) in enumerate(ROSTER):
    parts=[];coat=mat('Brick '+name,[(.48,.10,.065),(.07,.25,.43),(.58,.40,.075)][i%3]);humanoid_body(coat)
    box((0,-.18,1.25),(.38,.05,.32),coat,'spine',.008)
    for x in [-.11,.11]:
        for z in [1.15,1.32]:cone((x,-.21,z),.035,.035,.06,brass,'spine',8).rotation_euler.x=math.pi/2
    if kind in ['hero','foreman','crane','demo','kid']:
        cone((0,0,1.94),.24,.24,.045,brass,'head');box((0,0,2.0),(.31,.25,.12),brass,'head',.025)
        if kind in ['hero','demo']:
            box((-.37,0,1.16),(.31,.14,.17),brass,'forearm.R');box((-.37,0,.95),(.05,.07,.35),ink,'forearm.R')
        if kind=='hero':box((0,.22,1.20),(.39,.19,.44),coat,'spine')
        if kind=='foreman':box((0,-.27,1.13),(.34,.04,.30),cream,'spine')
        if kind=='crane':box((.36,0,1.1),(.17,.14,.25),ink,'forearm.L');segment((.36,0,1.22),(.36,0,1.6),.02,brass,'forearm.L')
        if kind=='kid':box((0,-.25,1.1),(.22,.16,.16),cream,'spine')
    elif kind in ['baker','archive','collector']:
        box((0,-.18,1.11),(.32,.04,.46),cream,'spine')
        if kind=='baker':cone((0,0,2),.19,.19,.19,cream,'head');box((.37,0,1.08),(.22,.14,.16),coat,'forearm.L')
        elif kind=='archive':box((0,.25,1.27),(.33,.22,.40),cream,'spine');box((0,-.26,1.18),(.36,.05,.30),coat,'spine')
        else:
            for x in [-.16,.16]:box((x,-.24,1.05),(.17,.10,.23),ink,'spine')
            ring((.36,0,1.22),.11,.025,brass,'forearm.L').rotation_euler.x=math.pi/2
    elif kind=='mayor':
        cone((0,0,1.96),.36,.36,.04,ink,'head');box((0,0,2.16),(.30,.26,.39),ink,'head')
        box((0,-.18,1.20),(.11,.04,.25),cream,'spine');cone((.36,0,1.1),.06,.06,.28,brass,'forearm.L')
    elif kind=='pilot':
        box((0,-.14,1.81),(.28,.06,.08),brass,'head');box((0,.22,1.23),(.36,.18,.40),ink,'spine')
        box((0,-.19,1.3),(.17,.04,.08),cream,'spine')
    elif kind=='soldier':
        box((0,0,1.99),(.31,.28,.20),coat,'head');cone((0,0,2.18),.04,0,.16,brass,'head')
        box((-.37,0,1.2),(.055,.08,.52),cream,'forearm.R');box((.37,-.07,1.13),(.27,.08,.39),coat,'forearm.L')
    elif kind=='glue':
        box((0,-.16,1.11),(.35,.04,.50),cream,'spine');box((0,-.14,1.80),(.29,.065,.085),brass,'head')
        for x in [-.16,.16]:cone((x,-.23,1.15),.05,.025,.18,white,'spine')
        cone((.36,0,1.12),.10,.065,.26,coat,'forearm.L')
    else:
        box((0,.24,1.21),(.39,.20,.40),ink,'spine');cone((0,0,1.94),.24,.24,.04,coat,'head')
        ring((.36,0,1.16),.09,.03,brass,'forearm.L').rotation_euler.x=math.pi/2
    mesh,rig=rig_mesh('Mob_Bricks_'+name);animate_humanoid(rig)
    scale=.75 if kind in ['mayor','kid'] else 1
    records.append(export_character(mesh,rig,role,'BrickHumanoidV1',{'role_count':1,'recommended_scale':scale,
        'behavior_status':'native binding pending'}))
    rig.scale=(scale,scale,scale);rig.location=((i%4)*2.5,(i//4)*2.5,0);label(name,i,4,2.5)
finish_scene(records,4,2.5,'brick-cast',['Idle','Walk','Attack','Hurt'])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='Brick Realm'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'bricks.bba')
