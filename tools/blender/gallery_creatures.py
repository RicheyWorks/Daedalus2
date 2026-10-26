"""Original Gallery City creatures, vehicles and pets; behavior remains proposed."""
from pathlib import Path
import ast
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
# Reuse exactly the verified rig function without executing Portal gameplay-table
# initialization. Adding a Portal species must not break Gallery art generation.
tree=ast.parse(Path(__file__).with_name('portal_monsters.py').read_text())
rig_function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='monster_rig')
exec(compile(ast.Module(body=[rig_function],type_ignores=[]),__file__,'exec'))
# Humanoid primitives default to spine; creatures use body. Never leave weights
# pointing at a nonexistent spine, which makes glTF invent a neutral joint.
_box,_cone,_ring=box,cone,ring
def box(p,s,m,bone='body',bevel=.015):return _box(p,s,m,bone,bevel)
def cone(p,r1,r2,d,m,bone='body',n=10):return _cone(p,r1,r2,d,m,bone,n)
def ring(p,r,minor,m,bone='body'):return _ring(p,r,minor,m,bone)
ROSTER=[('Smudgeling','Ink creature','blob'),('ThumbtackBeetle','Metal beetle','beetle'),
 ('CanvasMoth','Canvas-wing creature','moth'),('EaselStrider','Tripod creature','easel'),
 ('TurpentineToad','Toad creature','toad'),('MosaicHound','Tile hound','hound'),
 ('GildedFrameMimic','Living frame creature','frame'),('SentinelBust','Marble sentinel','bust'),
 ('LightProjection','Colour construct; replaces spooky wraith proposal','prism'),
 ('GreyWash','Colour-draining boss proposal','wash'),('PaperCrane','Ambient origami bird','crane'),
 ('BrushtailSquirrel','Ambient brush-tailed animal','squirrel'),('GalleryDrone','Realm mount; flight pending','drone'),
 ('KiteRay','Gliding companion','ray'),('EaselMule','Pack companion','mule'),
 ('Inkpup','Friendly pet','pup'),('PrismFinch','Friendly pet','finch'),
 ('CrayonGecko','Friendly pet','gecko'),('LampMoth','Friendly pet','lamp')]

def smooth(p,s,m,bone='body'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=p)
    o=bpy.context.object;o.scale=s;finish(o,m,bone)
    for polygon in o.data.polygons:polygon.use_smooth=True
    return o

def eyes(x=.10,y=-.34,z=.83):
    for sign in [-1,1]:
        smooth((sign*x,y,z),(.048,.025,.060),cream,'head')
        smooth((sign*x,y-.023,z),(.022,.015,.035),ink,'head')

records=[]
for i,(name,role,kind) in enumerate(ROSTER):
    parts=[];pigment=mat('Gallery pigment '+name,[(.12,.32,.43),(.45,.18,.32),(.15,.41,.29)][i%3])
    if kind in ['blob','wash']:
        for k in range(3 if kind=='blob' else 7):
            smooth(((k%3-1)*.24,(k//3)*.18,.33+.05*(k%2)),(.27,.26,.30),ink if kind=='blob' else cream)
        smooth((0,-.20,.69),(.18,.17,.17),pigment,'head');eyes(.07,-.34,.73)
    elif kind in ['beetle','toad']:
        smooth((0,0,.50),(.33,.40,.22),brass if kind=='beetle' else pigment)
        smooth((0,-.30,.65),(.22,.19,.15),pigment,'head');eyes(.11,-.46,.71)
        for side,sign in [('L',1),('R',-1)]:
            for y in [-.22,0,.22]:segment((sign*.25,y,.50),(sign*.45,y,.08),.035,ink,'leg.'+side)
        if kind=='beetle':cone((0,0,.83),.09,.025,.42,brass,'body');ring((0,0,.76),.22,.04,brass,'body')
        else:
            for x in [-.22,0,.22]:smooth((x,.14,.70),(.07,.06,.04),brass)
    elif kind in ['moth','lamp','ray','crane','finch']:
        smooth((0,0,.74),(.10,.25,.11),pigment)
        smooth((0,-.26,.88),(.12,.13,.14),pigment,'head');eyes(.06,-.36,.92)
        for side,sign in [('L',1),('R',-1)]:
            wing=box((sign*.36,.03,.77),(.58,.38,.035),cream if kind in ['moth','crane'] else pigment,'wing.'+side,.008)
            wing.rotation_euler.y=sign*.18
            if kind in ['moth','lamp']:
                smooth((sign*.34,-.07,.81),(.09,.12,.02),brass,'wing.'+side)
            elif kind=='ray':cone((sign*.66,.05,.77),.09,0,.18,pigment,'wing.'+side,3)
        segment((0,.2,.75),(0,.6,.65),.025,brass,'tail')
        if kind=='crane':segment((0,-.35,.89),(0,-.60,.83),.025,brass,'head')
        if kind=='lamp':smooth((0,0,.77),(.13,.20,.17),brass);ring((0,0,1.0),.10,.02,ink)
        if kind=='finch':cone((0,-.29,1.09),.035,0,.18,brass,'head',4)
    elif kind in ['hound','mule','pup','squirrel','gecko']:
        box((0,.02,.62),(.38,.58,.29),pigment,'body',.04)
        smooth((0,-.30,.87),(.20,.19,.21),pigment,'head');eyes(.09,-.46,.93)
        for side,sign in [('L',1),('R',-1)]:
            for y in [-.18,.24]:box((sign*.16,y,.29),(.10,.12,.50),ink,'leg.'+side,.02)
            cone((sign*.13,-.27,1.12),.055,0,.22 if kind=='mule' else .13,cream,'head',5)
        segment((0,.30,.69),(0,.61,.85),.055,brass,'tail')
        if kind=='hound':
            for x in [-.13,0,.13]:
                for y in [-.10,.07,.24]:box((x,y,.79),(.105,.13,.035),cream)
        if kind=='mule':box((0,.03,.86),(.30,.35,.19),cream);box((.29,.08,.64),(.18,.3,.35),brass)
        if kind=='squirrel':smooth((0,.5,.85),(.18,.14,.43),cream,'tail')
        if kind=='gecko':
            for k in range(4):cone((0,.10+k*.15,.87),.045,0,.14,brass,'tail',4)
        if kind=='pup':smooth((0,-.49,.81),(.07,.04,.05),ink,'head')
    elif kind in ['easel','frame','bust','prism','drone']:
        if kind=='easel':
            for side,x in [('L',.23),('R',-.23)]:segment((0,0,1.15),(x,-.13,.02),.045,brass,'leg.'+side)
            segment((0,0,1.15),(0,.25,.02),.045,brass,'tail');box((0,-.03,.81),(.45,.12,.56),cream);eyes(.10,-.13,.95)
        elif kind=='frame':
            for x in [-.28,.28]:box((x,0,.69),(.08,.12,.72),brass)
            for z in [.33,1.05]:box((0,0,z),(.64,.12,.08),brass)
            smooth((0,-.10,.78),(.16,.06,.15),ink,'head');eyes(.07,-.17,.82)
        elif kind=='bust':
            box((0,0,.20),(.45,.36,.40),brass);smooth((0,0,.78),(.30,.27,.40),cream,'head');eyes(.12,-.24,.88)
            for x in [-.22,-.11,0,.11,.22]:smooth((x,.03,1.12),(.085,.22,.09),brass,'head')
        elif kind=='prism':
            cone((0,0,.68),.32,0,.80,pigment,'body',4);ring((0,0,.60),.44,.025,brass);eyes(.08,-.19,.78)
        else:
            box((0,0,.76),(.50,.40,.14),ink);smooth((0,-.24,.72),(.11,.06,.08),brass,'head')
            for side,sign in [('L',1),('R',-1)]:
                for y in [-.26,.26]:
                    segment((0,y*.5,.76),(sign*.47,y,.76),.035,brass,'wing.'+side)
                    ring((sign*.47,y,.76),.19,.03,pigment,'wing.'+side)
                    box((sign*.47,y,.76),(.31,.035,.025),cream,'wing.'+side,0)
            box((0,0,.40),(.30,.27,.14),cream)
    mesh,rig=monster_rig('Mob_Gallery_'+name)
    unknown={group.name for group in mesh.vertex_groups}-set(rig.data.bones.keys())
    if unknown:raise ValueError('Weights reference missing bones: '+str(unknown))
    records.append(export_character(mesh,rig,role,'GalleryCreatureV1',{'role_count':1,'behavior_status':'proposal; native binding pending'}))
    rig.location=((i%5)*2.8,(i//5)*2.8,0);label(name,i,5,2.8)
finish_scene(records,5,2.8,'gallery-creatures',['Idle','Walk','Attack','Hurt'])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='Gallery City'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'gallery.bba')
