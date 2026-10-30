"""Original two-metre modular Gallery City kit; static export, no interaction proof."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from static_uv import ensure_static_uv
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
stone=mat('Gallery pale stone',(.43,.48,.51));wood=mat('Gallery walnut',(.21,.11,.07))
paint=mat('Gallery cobalt pigment',(.055,.22,.43));glass=mat('Gallery painted glass',(.17,.45,.49))
KIT=[('FloorTile','Walkable floor module'),('MosaicFloor','Colour tile floor'),('Walkway','Hanging walkway'),
 ('FrameWall','Modular framed wall'),('WindowWall','Window wall'),('DoorFrame','Clear doorway module'),
 ('CornerColumn','Modular corner support'),('Railing','Walkway boundary'),('Ramp','Access ramp'),
 ('Stairs','Raised walkway access'),('PaintingFrame','Art display frame'),('MuralPanel','Painted hint surface'),
 ('RestorationBench','Restoration station'),('PigmentCrate','Craft supplies presentation'),
 ('BrushRack','Tool display'),('VarnishStation','Painting protection station'),('TailorStand','Cosmetic station'),
 ('CriticLectern','Build review station'),('DroneDock','Mount pickup presentation'),
 ('DroneRepairBench','Mount repair station'),('ConcertPlatform','Touring jukebox performance station'),
 ('RainbowFrame','Rainbow departure frame'),('AirlockEntry','Underwater dock arrival presentation'),
 ('QuestNoticeboard','Readable quest presentation')]

def frame(width,height,material=brass,y=0):
    for x in [-width/2,width/2]:box((x,y,height/2),(.10,.18,height),material,bevel=.015)
    for z in [.05,height-.05]:box((0,y,z),(width+.10,.18,.10),material,bevel=.015)

records=[]
for i,(name,role) in enumerate(KIT):
    parts=[]
    if name in ['FloorTile','MosaicFloor','Walkway']:
        box((0,0,-.10),(2,2,.20),stone,bevel=0)
        if name=='MosaicFloor':
            for x in [-.65,0,.65]:
                for y in [-.65,0,.65]:box((x,y,.015),(.58,.58,.025),paint if x==y else cream,bevel=.004)
        if name=='Walkway':
            for x in [-.9,.9]:box((x,0,.30),(.07,2,.60),brass)
    elif name in ['FrameWall','WindowWall']:
        box((0,.08,1.2),(2,.16,2.4),stone,bevel=0);frame(1.8,2.3,y=-.06)
        box((0,-.07,1.25),(1.4,.035,1.6),glass if name=='WindowWall' else paint)
        if name=='WindowWall':box((0,-.11,1.25),(.045,.04,1.6),brass)
    elif name in ['DoorFrame','RainbowFrame','AirlockEntry']:
        for x in [-.85,.85]:box((x,0,1.15),(.30,.30,2.30),brass if name=='RainbowFrame' else stone)
        box((0,0,2.3),(2,.30,.20),brass)
        if name=='RainbowFrame':
            for x in [-.7,0,.7]:ball((x,0,2.53),(.10,.10,.10),glass)
        if name=='AirlockEntry':
            ring((0,-.05,1.2),.55,.07,glass).rotation_euler.x=math.pi/2
            for x in [-.82,.82]:box((x,-.19,1.25),(.08,.08,.7),paint)
    elif name in ['CornerColumn','Railing']:
        if name=='CornerColumn':box((0,0,1.2),(.3,.3,2.4),stone);box((0,0,2.35),(.5,.5,.1),brass)
        else:
            for x in [-.95,.95]:box((x,0,.5),(.10,.10,1),brass)
            for z in [.3,.9]:box((0,0,z),(2,.07,.07),brass)
    elif name in ['Ramp','Stairs']:
        if name=='Ramp':
            # Single continuous slope, 2m run, 0.5m rise; underside at ground.
            verts=[(-1,-1,0),(1,-1,0),(-1,1,0),(1,1,0),(-1,-1,.03),(1,-1,.03),(-1,1,.53),(1,1,.53)]
            faces=[(4,5,7,6),(0,2,3,1),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
            data=bpy.data.meshes.new('Gallery access slope');data.from_pydata(verts,[],faces);data.update()
            obj=bpy.data.objects.new('Ramp',data);bpy.context.collection.objects.link(obj);finish(obj,stone,'spine')
        else:
            for step in range(5):box((0,-.8+step*.4,.05*(step+1)),(2,.4,.10*(step+1)),stone,bevel=0)
    elif name in ['PaintingFrame','MuralPanel','QuestNoticeboard']:
        frame(1.4,1.5);box((0,.02,.75),(1.3,.04,1.4),wood if name=='QuestNoticeboard' else cream)
        for x,z in [(-.3,.4),(.15,.8),(-.2,1.1)]:box((x,-.025,z),(.30,.02,.19),paint)
        if name=='QuestNoticeboard':
            for x in [-.45,.4]:box((x,-.02,.7),(.25,.02,.40),cream)
    elif name in ['DroneDock','ConcertPlatform']:
        box((0,0,-.15),(4,4,.3),wood if name=='ConcertPlatform' else stone,bevel=0)
        ring((0,0,.015),1.25,.04,brass)
        if name=='ConcertPlatform':
            for x in [-1.6,1.6]:box((x,1.5,1.1),(.25,.30,2.2),brass)
            box((0,1.5,2.2),(3.5,.22,.15),paint)
        else:
            for x in [-1.8,1.8]:box((x,0,.12),(.1,2.5,.25),paint)
    elif name=='PigmentCrate':
        box((0,0,.3),(.7,.6,.6),wood)
        for x in [-.2,0,.2]:cone((x,0,.69),.09,.09,.22,paint)
    elif name=='BrushRack':
        box((0,0,.35),(.8,.4,.7),wood)
        for x in [-.3,-.1,.1,.3]:segment((x,0,.7),(x,0,1.4),.025,brass,'spine');cone((x,0,1.45),.04,.015,.15,cream)
    elif name=='TailorStand':
        cone((0,0,.6),.2,.14,1.2,stone);box((0,0,1.20),(.7,.3,.18),paint)
        for x in [-.3,.3]:box((x,0,.95),(.13,.27,.5),paint)
    else:
        box((0,0,.42),(1.2,.6,.84),wood);box((0,0,.88),(1.4,.7,.10),cream)
        if name=='CriticLectern':box((0,.14,1.12),(.55,.38,.08),paint)
        elif name=='DroneRepairBench':ring((0,0,1.0),.22,.04,brass);box((.40,0,1),(.20,.15,.14),ink)
        elif name=='VarnishStation':
            for x in [-.4,0,.4]:cone((x,0,1.06),.1,.065,.28,glass)
        else:box((0,0,.96),(.7,.45,.03),paint);box((.45,0,1.04),(.13,.15,.2),brass)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=bpy.context.object;obj.name='Prop_Gallery_'+name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    if name=='Ramp':ensure_static_uv(obj)
    path=OUT/(obj.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=False,export_tangents=(name=='Ramp'))
    triangles=sum(len(p.vertices)-2 for p in obj.data.polygons);radius=math.ceil(max(Vector(c).length for c in obj.bound_box)*100)
    records.append(dict(id=obj.name,file=path.name,role=role,triangles=triangles,bones=0,rig='static',radius_cm=radius,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),role_count=0,snap_grid_metres=2,interaction='native binding pending'))
    obj.location=((i%5)*5,(i//5)*5,0);label(name,i,5,5)
finish_scene(records,5,5,'gallery-environment',[])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='Gallery City'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'gallery.bba')
