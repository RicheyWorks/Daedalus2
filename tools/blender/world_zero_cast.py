"""World Zero cross-realm NPCs. Headless isolated export; no render/live scene mutation.
Blender --background --python world_zero_cast.py -- NEW_OUTPUT_DIRECTORY
"""
from pathlib import Path
import sys
output=Path(sys.argv[sys.argv.index('--')+1])
if output.exists():raise ValueError('Use a new output directory; preserve prior deliveries')
exec(compile(Path(__file__).with_name('realm_humanoid.py').read_text(),__file__,'exec'))
ROSTER=[
 ('GateFerrymanBram','Gate Ferryman Bram','oar',(.07,.24,.29)),
 ('RainbowPainter','Rainbow Painter','palette',(.36,.13,.39)),
 ('WanderingMerchantZee','Wandering Merchant Zee','satchel',(.38,.21,.08)),
 ('HeartstoneSeekerCaptain','Heartstone Seeker Captain','compass',(.10,.20,.37)),
 ('CourierOfWorlds','Courier of Worlds','letter',(.38,.10,.09)),
 ('TugboatBalloonist','Tugboat Balloonist','balloon',(.09,.33,.22))]
records=[]
for i,(name,role,kind,color) in enumerate(ROSTER):
    parts=[];coat=mat('Zero '+name,color);humanoid_body(coat)
    box((0,-.18,1.16),(.30,.055,.08),brass,'spine',.008)
    if kind=='oar':
        segment((-.36,0,.12),(-.36,0,1.95),.028,brass,'forearm.R')
        box((-.36,0,.18),(.17,.055,.36),cream,'forearm.R',.02)
        cone((0,0,1.94),.21,.17,.12,coat,'head')
    elif kind=='palette':
        ball((.38,-.08,1.05),(.20,.045,.15),cream,'forearm.L')
        for j,c in enumerate([(.7,.09,.1),(.9,.55,.05),(.1,.55,.2),(.12,.28,.8),(.6,.18,.7)]):
            ball((.25+j*.055,-.13,1.07),(.025,.018,.026),mat('Rainbow pigment'+str(j),c),'forearm.L')
        segment((-.36,0,.83),(-.36,0,1.40),.014,brass,'forearm.R')
        box((-.36,0,1.42),(.06,.03,.10),cream,'forearm.R',.004)
    elif kind=='satchel':
        box((0,.27,1.15),(.42,.22,.49),ink,'spine',.035)
        box((.37,0,1.04),(.18,.13,.20),brass,'forearm.L',.02)
        cone((0,0,1.95),.26,.18,.07,coat,'head')
    elif kind=='compass':
        box((0,.24,1.22),(.35,.17,.38),ink,'spine',.025)
        ball((.36,-.05,1.1),(.09,.04,.09),brass,'forearm.L')
        ball((0,-.19,1.36),(.045,.028,.06),mat('Heartstone cyan',(.12,.65,.70)),'spine')
        box((0,0,1.99),(.28,.23,.09),cream,'head')
    elif kind=='letter':
        box((.33,0,.9),(.25,.13,.32),ink,'pelvis',.025)
        box((.36,-.1,1.06),(.19,.03,.12),cream,'forearm.L',.003)
        cone((0,0,1.94),.20,.16,.09,coat,'head')
    elif kind=='balloon':
        segment((-.37,0,.85),(-.37,0,2.25),.014,brass,'forearm.R')
        ball((-.37,0,2.48),(.18,.17,.25),mat('Balloon amber',(.82,.40,.08)),'forearm.R')
        box((0,.23,1.13),(.35,.16,.40),ink,'spine',.025)
        for x in [-.075,.075]:ball((x,-.14,1.92),(.065,.03,.04),brass,'head')
    mesh,rig=rig_mesh('Mob_Zero_'+name);animate_humanoid(rig)
    records.append(export_character(mesh,rig,role,'WorldZeroHumanoidV1',{'role_count':1,'behavior_status':'native binding pending'}))
    rig.location=((i%3)*2.8,(i//3)*2.8,0);label(role,i,3,2.8)
finish_scene(records,3,2.8,'world-zero-cast',['Idle','Walk','Attack','Hurt'],render=False)
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='World Zero'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'world-zero.bba')
