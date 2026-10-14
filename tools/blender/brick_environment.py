"""Original two-metre modular Brick Realm kit; static geometry, no behavior."""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
blue=mat('Brick blue',(.055,.24,.42));red=mat('Brick red',(.48,.08,.04));green=mat('Brick meadow',(.16,.32,.13))
KIT=[('MeadowTile','Continuous meadow module'),('Baseplate','Construction floor'),('RoadTile','Continuous vehicle road'),
 ('Wall','Construction wall'),('WindowWall','Window module'),('DoorFrame','Clear doorway'),('Column','Corner support'),
 ('Rail','Raised platform boundary'),('Ramp','Continuous access slope'),('Stairs','Raised platform access'),
 ('Workbench','Repair station'),('Kiln','Crafting station'),('RecipeArchive','Blueprint archive'),('CraneBase','Crane station'),
 ('SalvageBin','Parts recovery station'),('Noticeboard','Quest presentation'),('TradeCounter','Realm trade station'),
 ('RunwayTile','Continuous airfield strip'),('HangarFrame','Clear aircraft shelter entry'),('RepairBay','Vehicle service platform'),
 ('ConcertPlatform','Touring jukebox station'),('RainbowFrame','Rainbow departure presentation'),
 ('BoatDock','Ocean departure dock'),('UnderwaterAirlock','Ocean arrival presentation')]

def studs(width=1.6,y=0,z=.045):
    for x in [-width/2,0,width/2]:cone((x,y,z),.065,.065,.05,brass,n=8)

records=[]
for i,(name,role) in enumerate(KIT):
    parts=[]
    if name in ['MeadowTile','Baseplate','RoadTile','RunwayTile']:
        box((0,0,-.10),(2,2,.20),green if name=='MeadowTile' else blue if name=='Baseplate' else ink,bevel=0)
        if name=='Baseplate':
            for y in [-.8,0,.8]:studs(y=y)
        if name in ['RoadTile','RunwayTile']:
            for y in [-.65,.65]:box((0,y,.006),(.10,.40,.012),cream,bevel=0)
            if name=='RunwayTile':
                for x in [-.85,.85]:box((x,0,.006),(.06,2,.012),cream,bevel=0)
    elif name in ['Wall','WindowWall']:
        if name=='Wall':box((0,0,1.2),(2,.20,2.4),red,bevel=0)
        else:
            for x in [-.75,.75]:box((x,0,1.2),(.5,.20,2.4),red,bevel=0)
            for z in [.3,2.1]:box((0,0,z),(1,.20,.6),red,bevel=0)
        studs(z=2.435)
    elif name in ['DoorFrame','HangarFrame','RainbowFrame','UnderwaterAirlock']:
        width=4 if name=='HangarFrame' else 2;height=3 if name=='HangarFrame' else 2.4
        for x in [-width/2+.12,width/2-.12]:box((x,0,height/2),(.24,.30,height),blue)
        box((0,0,height),(width,.30,.20),brass)
        if name=='RainbowFrame':
            for x in [-.65,0,.65]:cone((x,0,height+.18),.07,.07,.14,cream,n=8)
        if name=='UnderwaterAirlock':ring((0,-.04,1.2),.55,.06,blue).rotation_euler.x=math.pi/2
    elif name in ['Column','Rail']:
        if name=='Column':box((0,0,1.2),(.35,.35,2.4),blue);studs(.20,z=2.435)
        else:
            for x in [-.9,.9]:box((x,0,.5),(.12,.12,1),blue)
            for z in [.35,.90]:box((0,0,z),(2,.08,.08),brass)
    elif name=='Ramp':
        verts=[(-1,-1,0),(1,-1,0),(-1,1,0),(1,1,0),(-1,-1,.03),(1,-1,.03),(-1,1,.53),(1,1,.53)]
        faces=[(4,5,7,6),(0,2,3,1),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
        data=bpy.data.meshes.new('Brick access slope');data.from_pydata(verts,[],faces);data.update()
        obj=bpy.data.objects.new('Ramp',data);bpy.context.collection.objects.link(obj);finish(obj,blue,'spine')
    elif name=='Stairs':
        for k in range(5):box((0,-.8+k*.4,.05*(k+1)),(2,.4,.10*(k+1)),blue,bevel=0)
    elif name in ['RepairBay','ConcertPlatform','BoatDock']:
        box((0,0,-.15),(4,4,.30),blue,bevel=0)
        if name=='RepairBay':
            for x in [-1.5,1.5]:box((x,0,.04),(.12,3,.08),brass)
        if name=='ConcertPlatform':
            for x in [-1.65,1.65]:box((x,1.6,1),(.30,.30,2),red)
            box((0,1.6,2),(3.6,.25,.16),brass)
        if name=='BoatDock':
            for x in [-1.75,1.75]:cone((x,1.5,.40),.12,.12,.8,brass,n=8)
    elif name in ['Workbench','TradeCounter','SalvageBin']:
        box((0,0,.45),(1.2,.65,.9),red);box((0,0,.94),(1.35,.75,.08),brass)
        if name=='SalvageBin':
            for x in [-.35,0,.35]:box((x,0,1.07),(.22,.22,.18),blue);studs(.12,y=0,z=1.19)
        if name=='Workbench':box((0,0,1.07),(.30,.30,.18),cream);ring((.40,0,1.04),.11,.025,ink)
        if name=='TradeCounter':box((0,-.35,.7),(.35,.025,.20),cream)
    elif name=='Kiln':
        box((0,0,.6),(.90,.8,1.2),red);box((0,-.42,.5),(.55,.04,.50),ink)
        cone((0,0,1.48),.17,.17,.56,blue,n=8)
    elif name=='CraneBase':
        box((0,0,.15),(1.3,1.3,.3),blue);box((0,0,1.25),(.20,.20,2.2),brass)
        box((.6,0,2.3),(1.4,.16,.16),brass);segment((1.2,0,2.25),(1.2,0,1.1),.025,ink,'spine')
        ring((1.2,0,1),.12,.025,ink).rotation_euler.x=math.pi/2
    else:
        box((0,0,1),(1.3,.16,1.6),blue)
        for x in [-.45,.45]:box((x,0,.2),(.12,.16,.4),brass)
        for x in [-.3,.3]:box((x,-.10,1.05),(.40,.025,.65),cream)
        if name=='RecipeArchive':
            for z in [.55,.9,1.25,1.6]:box((0,-.20,z),(1.25,.30,.06),brass)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    if len(parts)>1:bpy.ops.object.join()
    obj=bpy.context.object;obj.name='Prop_Bricks_'+name;bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    path=OUT/(obj.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=False)
    triangles=sum(len(p.vertices)-2 for p in obj.data.polygons);radius=math.ceil(max(Vector(c).length for c in obj.bound_box)*100)
    records.append(dict(id=obj.name,file=path.name,role=role,triangles=triangles,bones=0,rig='static',radius_cm=radius,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),role_count=0,snap_grid_metres=2,interaction='native binding pending'))
    obj.location=((i%5)*5,(i//5)*5,0);label(name,i,5,5)
finish_scene(records,5,5,'brick-environment',[])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='Brick Realm'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'bricks.bba')
