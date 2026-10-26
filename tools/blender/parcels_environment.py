"""Original Parcels modules plus unchanged owned AMF trough reuse; static art."""
from pathlib import Path
import shutil,struct
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
grass=mat('Parcels grass',(.18,.32,.12));soil=mat('Parcels soil',(.21,.12,.06));wood=mat('Parcels wood',(.34,.20,.09))
red=mat('Parcels red paint',(.40,.095,.045));water=mat('Parcels water',(.07,.28,.40))
KIT=[('FieldTile','Field module'),('SoilBed','Crop bed'),('RoadTile','Travel road module'),('Fence','Boundary module'),
 ('FarmGate','Farm entry'),('BarnWall','Farm wall'),('BarnDoor','Clear farm doorway'),('HayBale','Farm supplies'),
 ('SeedCrate','Seed supplies'),('Mailbox','Delivery station'),('PostCounter','Mail station'),('Noticeboard','Quest board'),
 ('SurveyMarker','Survey presentation; no deed authority'),('WeatherVane','Weather station'),('Beehive','Bee station'),
 ('MilkCart','Transport/cart station'),('RainCollector','Water collection presentation'),('Well','Water source'),
 ('Helipad','Mount departure presentation'),('FuelPump','Vehicle service station'),('MarketStall','Market station'),
 ('BoatDock','Ocean departure dock'),('UnderwaterAirlock','Ocean arrival presentation')]
records=[]
for i,(name,role) in enumerate(KIT):
    parts=[]
    if name in ['FieldTile','SoilBed','RoadTile']:
        box((0,0,-.1),(2,2,.2),grass if name=='FieldTile' else soil if name=='SoilBed' else cream,bevel=0)
        if name=='SoilBed':
            for x in [-.65,0,.65]:box((x,0,.04),(.18,1.8,.08),soil)
        if name=='RoadTile':
            for y in [-.6,0,.6]:box((0,y,.015),(.10,.30,.025),wood)
    elif name in ['Fence','FarmGate','BarnDoor','UnderwaterAirlock']:
        height=2.3 if name in ['BarnDoor','UnderwaterAirlock'] else 1.1
        for x in [-.9,.9]:box((x,0,height/2),(.18,.18,height),wood)
        box((0,0,height),(2,.18,.12),red)
        if name=='Fence':
            for z in [.4,.85]:box((0,0,z),(2,.08,.07),cream)
        if name=='UnderwaterAirlock':ring((0,-.05,1.25),.55,.055,water).rotation_euler.x=math.pi/2
    elif name=='BarnWall':
        box((0,0,1.2),(2,.18,2.4),red,bevel=0)
        for x in [-.8,-.4,0,.4,.8]:box((x,-.12,1.2),(.06,.04,2.3),wood)
    elif name in ['HayBale','SeedCrate']:
        box((0,0,.3),(.8,.6,.6),cream if name=='HayBale' else wood)
        if name=='HayBale':
            for x in [-.25,.25]:box((x,-.32,.3),(.04,.02,.60),wood)
        else:
            for x in [-.25,0,.25]:cone((x,0,.72),.085,.05,.26,cream)
    elif name=='Mailbox':
        box((0,0,.5),(.10,.10,1),wood);box((0,0,1.15),(.5,.6,.30),red)
        box((0,-.32,1.15),(.40,.02,.21),cream)
    elif name in ['PostCounter','MarketStall','FuelPump']:
        box((0,0,.45),(1.3,.6,.9),wood if name!='FuelPump' else red)
        box((0,0,.93),(1.4,.7,.06),cream)
        if name=='MarketStall':
            for x in [-.6,.6]:box((x,.18,1.35),(.06,.06,1),wood)
            box((0,.18,1.9),(1.6,1,.08),red)
        elif name=='FuelPump':ring((.36,-.35,.80),.2,.025,ink).rotation_euler.x=math.pi/2
        else:box((0,-.36,.7),(.3,.025,.15),red)
    elif name=='Noticeboard':
        box((0,0,1),(1.3,.12,1),wood)
        for x in [-.3,.3]:box((x,-.08,1),(.36,.02,.45),cream)
        for x in [-.5,.5]:box((x,0,.3),(.08,.08,.6),wood)
    elif name in ['SurveyMarker','WeatherVane']:
        segment((0,0,0),(0,0,1.6),.035,wood,'spine')
        if name=='SurveyMarker':box((0,0,1.62),(.55,.07,.10),red)
        else:box((0,0,1.62),(.7,.04,.05),brass);cone((.32,0,1.7),.065,0,.15,red,n=3)
    elif name=='Beehive':
        box((0,0,.35),(.6,.5,.7),wood)
        for z in [.2,.4,.6]:box((0,-.27,z),(.48,.02,.025),cream)
    elif name=='MilkCart':
        box((0,0,.5),(.8,1,.12),wood)
        for x in [-.4,.4]:
            wheel=ring((x,0,.30),.23,.045,ink);wheel.rotation_euler.y=math.pi/2
        for x in [-.2,.2]:cone((x,0,.75),.12,.07,.40,cream)
        segment((0,.4,.5),(0,.95,.60),.03,wood,'spine')
    elif name in ['RainCollector','Well']:
        ring((0,0,.45),.42,.08,wood);box((0,0,.08),(.65,.65,.16),water)
        if name=='RainCollector':cone((0,0,.8),.30,.60,.55,cream)
        else:
            for x in [-.45,.45]:box((x,0,1),(.1,.1,2),wood)
            box((0,0,1.95),(1.2,.6,.08),red)
    elif name in ['Helipad','BoatDock']:
        box((0,0,-.15),(4,4,.30),cream if name=='Helipad' else wood,bevel=0)
        if name=='Helipad':ring((0,0,.02),1.3,.035,red);box((0,0,.025),(.07,1.2,.03),red)
        else:
            for x in [-1.8,1.8]:box((x,0,.30),(.12,4,.60),cream)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    if len(parts)>1:bpy.ops.object.join()
    obj=bpy.context.object;obj.name='Prop_Parcels_'+name;bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    path=OUT/(obj.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=False)
    triangles=sum(len(p.vertices)-2 for p in obj.data.polygons);radius=math.ceil(max(Vector(c).length for c in obj.bound_box)*100)
    records.append(dict(id=obj.name,file=path.name,role=role,triangles=triangles,bones=0,rig='static',radius_cm=radius,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),role_count=0,snap_grid_metres=2,interaction='native binding pending'))
    obj.location=((i%5)*5,(i//5)*5,0);label(name,i,5,5)
# Preserve the existing mesh bytes and identity; geometry reuse does not import behavior.
source=Path(__file__).resolve().parents[2]/'tools/islands/kennel-isle/glb/Prop_Water_AMF_Trough_V12.glb'
raw=source.read_bytes();doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
triangles=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
shutil.copyfile(source,OUT/source.name);bpy.ops.import_scene.gltf(filepath=str(source))
imported=list(bpy.context.selected_objects)
radius=math.ceil(max((obj.matrix_world@Vector(c)).length for obj in imported if obj.type=='MESH' for c in obj.bound_box)*100)
for obj in imported:
    if obj.parent not in imported:obj.location+=Vector((15,20,0))
records.append(dict(id=source.stem,file=source.name,role='Existing AMF trough geometry reuse; behavior not copied',
    triangles=triangles,bones=0,rig='static',radius_cm=radius,sha256=hashlib.sha256(raw).hexdigest(),role_count=0,
    reused_source=str(source.relative_to(Path(__file__).resolve().parents[2])),new_asset=False))
label('Existing AMF trough',23,5,5)
finish_scene(records,5,5,'parcels-environment',[],render='--skip-render' not in sys.argv)
manifest=json.loads((OUT/'manifest.json').read_text());manifest['realm']='The Parcels'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'portal.bba').replace(OUT/'parcels.bba')
