"""Original Parcels humanoid cast; interaction and quest effects are not implemented here."""
from pathlib import Path
exec(compile(Path(__file__).with_name('realm_humanoid.py').read_text(),__file__,'exec'))
ROSTER=[('Courier','Hero parcel courier','hero'),('PostmasterGrue','Delivery quest board','mail'),
 ('PlotSurveyorIlka','Survey presentation; no deed authority','survey'),('FenceSmith','Fence crafting','smith'),
 ('SeedBrokerOtt','Seed supplies','seed'),('ScarecrowElder','Helpful field guide','straw'),
 ('HelipadChiefRosa','Helicopter guidance','pilot'),('MilkCartTwins','Cart escort role representative','milk'),
 ('LostLetterCourier','Lost letter quest; nonHalloween ghost reinterpretation','letter'),
 ('BeekeeperHollis','Bee and honey supplies','bee'),('AuctionCrow','Market role','crow'),
 ('WeatherVaneKeeper','Storm and crop guidance','weather'),('NeighbourFeudPair','Boundary quest representative','boundary')]
records=[]
for i,(name,role,kind) in enumerate(ROSTER):
    parts=[];coat=mat('Parcels '+name,[(.32,.18,.10),(.18,.33,.20),(.39,.26,.09)][i%3]);humanoid_body(coat)
    if kind in ['hero','mail','letter']:
        box((0,.23,1.24),(.39,.18,.43),cream,'spine',.025)
        box((0,0,1.94),(.34,.30,.07),coat,'head')
        box((0,-.17,1.12),(.30,.04,.22),cream,'spine')
        for sign in [-1,1]:segment((sign*.14,-.20,1.22),(0,-.20,1.12),.008,brass,'spine')
        if kind=='hero':box((.36,-.1,1.1),(.34,.10,.43),coat,'forearm.L');box((-.36,0,1.15),(.24,.14,.15),brass,'forearm.R')
        if kind=='mail':cone((-.36,0,1.13),.07,.07,.20,brass,'forearm.R')
    elif kind in ['survey','boundary']:
        box((0,-.19,1.18),(.36,.06,.30),cream,'spine')
        segment((-.37,0,.25),(-.37,0,1.55),.025,brass,'forearm.R')
        for z in [.5,.75,1.0,1.25]:box((-.37,-.025,z),(.09,.02,.012),ink,'forearm.R',0)
        if kind=='survey':box((0,.23,1.3),(.28,.18,.25),brass,'spine')
        else:box((.36,0,1.05),(.18,.13,.26),coat,'forearm.L')
    elif kind=='smith':
        box((0,-.17,1.15),(.31,.05,.47),cream,'spine');box((-.36,0,1.17),(.32,.14,.16),ink,'forearm.R')
    elif kind in ['seed','milk']:
        for x in [-.15,.15]:box((x,-.21,1.12),(.12,.09,.22),cream,'spine')
        if kind=='seed':ball((.36,0,1.04),(.13,.10,.14),coat,'forearm.L');cone((0,0,1.96),.27,.27,.04,cream,'head')
        else:cone((.36,0,1.14),.10,.06,.32,white,'forearm.L');ring((.36,0,1.32),.055,.015,brass,'forearm.L')
    elif kind=='straw':
        cone((0,0,1.95),.34,.34,.045,cream,'head');cone((0,0,2.04),.17,.12,.14,coat,'head')
        for x in [-.15,.15]:box((x,-.18,1.15),(.08,.03,.08),cream,'spine')
        for x in [-.36,.36]:segment((x,0,1.05),(x+.06,0,.90),.012,cream,'forearm.L' if x>0 else 'forearm.R')
    elif kind=='pilot':
        box((0,-.14,1.80),(.29,.065,.085),brass,'head');box((0,.22,1.22),(.36,.18,.42),ink,'spine')
        box((0,-.18,1.22),(.16,.05,.1),cream,'spine')
    elif kind=='bee':
        cone((0,0,1.95),.30,.30,.045,cream,'head');box((0,-.16,1.69),(.33,.05,.36),white,'head')
        for z in [1.56,1.67,1.78]:box((0,-.20,z),(.28,.02,.012),ink,'head',0)
        cone((.36,0,1.10),.10,.10,.24,brass,'forearm.L')
    elif kind=='crow':
        box((0,-.21,1.75),(.10,.22,.10),brass,'head');box((0,0,1.97),(.34,.28,.04),ink,'head')
        box((0,.19,1.18),(.48,.05,.55),ink,'spine')
    elif kind=='weather':
        segment((-.36,0,.5),(-.36,0,1.65),.025,brass,'forearm.R');box((-.36,0,1.62),(.36,.05,.05),cream,'forearm.R')
        cone((0,0,1.97),.22,.06,.22,coat,'head')
    mesh,rig=rig_mesh('Mob_Parcels_'+name);animate_humanoid(rig)
    records.append(export_character(mesh,rig,role,'ParcelsHumanoidV1',{'role_count':1,'behavior_status':'native binding pending'}))
    rig.location=((i%4)*2.5,(i//4)*2.5,0);label(name,i,4,2.5)
finish_scene(records,4,2.5,'parcels-cast',['Idle','Walk','Attack','Hurt'])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='The Parcels'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'parcels.bba')
