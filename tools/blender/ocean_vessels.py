"""Original Ocean skiff/submarine. Metres, +X forward, Z=0 waterline pivot."""
import sys
from pathlib import Path
if Path(sys.argv[sys.argv.index('--')+1]).exists():raise ValueError('Fresh delivery directory required')
exec(compile(Path(__file__).with_name('portal_common.py').read_text(encoding='utf-8'),__file__,'exec'))
import bmesh

wood=mat('Ocean honey wood',(.36,.19,.075));plank=mat('Ocean light deck',(.58,.36,.16))
ocean_teal=mat('Ocean enamel teal',(.025,.28,.30),.2);ochre=mat('Ocean submarine ochre',(.72,.39,.07),.25)
metal=mat('Ocean aged brass',(.62,.39,.12),.7);sail=mat('Ocean sail linen',(.85,.77,.56))
glass=mat('Ocean blue glass',(.13,.55,.67),.1);trim=mat('Ocean midnight trim',(.015,.045,.07),.2)
lamp=mat('Ocean lantern glow',(.98,.48,.07))
lamp.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=(.98,.35,.025,1)
lamp.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=1.5
for material in [metal,glass,ocean_teal,ochre]:material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.3

def custom(name,vertices,faces,material):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    return finish(obj,material,'spine')

def export_vessel(name,role):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    path=OUT/(name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=False)
    bounds=[list(v) for v in obj.bound_box]
    record=dict(id=name,role=role,file=path.name,triangles=sum(len(p.vertices)-2 for p in obj.data.polygons),
                rig='static',bones=0,role_count=0,radius_cm=math.ceil(max(Vector(c).length for c in obj.bound_box)*100),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pivot='waterline',forward_axis='+X',bounds_blender_m=bounds)
    return obj,record

records=[];parts=[]
vertices=[]
for x,width in [(-2.25,.12),(-1.8,.64),(-.8,.9),(.7,.88),(1.7,.55),(2.3,.035)]:
    vertices += [(x,y,z) for y,z in [(width,.42),(width,.05),(.6*width,-.43),(.15*width,-.58),
                                   (-.15*width,-.58),(-.6*width,-.43),(-width,.05),(-width,.42)]]
faces=[tuple(reversed(range(8))),tuple(range(40,48))]
for ring_index in range(5):
    for j in range(8):faces.append((ring_index*8+j,ring_index*8+(j+1)%8,(ring_index+1)*8+(j+1)%8,(ring_index+1)*8+j))
custom('Carvel skiff hull',vertices,faces,ocean_teal)
for y in [-.52,-.26,0,.26,.52]:box((0,y,.43),(3.65,.24,.10),plank if y else wood,bevel=.02)
for y in [-.78,.78]:segment((-1.65,y,.49),(1.1,y,.49),.045,metal,'spine')
box((-.95,0,.92),(1.12,1.02,.88),wood,bevel=.06)
ball((-.95,0,1.39),(.68,.64,.16),ocean_teal,'spine')
for y in [-.522,.522]:
    box((-.9,y,1.04),(.66,.025,.35),metal,bevel=.025)
    box((-.9,y*1.01,1.04),(.56,.02,.25),glass,bevel=.02)
cone((.5,0,1.85),.045,.03,2.85,wood,n=12)
segment((.5,0,1.15),(-1.5,0,1.35),.025,metal,'spine')
custom('Curved linen sail',[(.5,.02,3.2),(.5,.02,1.18),(-1.45,.10,1.4),(-.8,.16,2.45)],[(0,1,2),(0,2,3)],sail)
for x in [-1.8,1.7]:
    cone((x,0,.65),.04,.04,.38,metal,n=8)
    ring((x,0,.85),.105,.018,metal).rotation_euler.y=math.pi/2
box((1.45,-.42,.75),(.18,.18,.32),metal)
box((1.45,-.42,.77),(.13,.13,.22),lamp)
wheel=ring((-.18,0,.95),.19,.022,metal);wheel.rotation_euler.y=math.pi/2
for y in [-.62,.62]:ball((-.15,y,.68),(.2,.12,.2),sail,'spine')
boat,record=export_vessel('Prop_Ocean_TideSkiff','Dock boat; helm/boarding presentation');records.append(record)
boat.location=(0,0,1.0)

parts=[]
ball((0,0,0),(2.45,.83,.83),ochre,'spine')
for x in [-1.0,1.0]:ring((x,0,0),.74,.055,ocean_teal).rotation_euler.y=math.pi/2
ball((2.0,0,.08),(.53,.52,.52),glass,'spine')
ring((2.05,0,.08),.48,.05,metal).rotation_euler.y=math.pi/2
for x in [-.95,0,.95]:
    for side in [-1,1]:
        ring((x,side*.79,.04),.23,.045,metal).rotation_euler.x=math.pi/2
        ball((x,side*.8,.04),(.19,.045,.19),glass,'spine')
        for angle in [0,math.pi/2,math.pi,3*math.pi/2]:
            ball((x+.25*math.cos(angle),side*.82,.04+.25*math.sin(angle)),(.035,.035,.035),trim,'spine')
cone((-.4,0,.86),.47,.47,.13,ocean_teal,n=16);ring((-.4,0,.95),.35,.035,metal)
cone((-.4,0,1.35),.06,.06,.8,metal,n=10)
segment((-.4,0,1.75),(.0,0,1.75),.07,metal,'spine');ball((.04,0,1.75),(.07,.07,.07),glass,'spine')
box((-1.75,0,.86),(.7,.10,.65),ocean_teal,bevel=.025)
for y in [-.8,.8]:box((-1.65,y,-.12),(.85,.55,.10),ocean_teal,bevel=.025)
ring((-2.48,0,0),.58,.045,metal).rotation_euler.y=math.pi/2
for angle in [0,math.pi/2,math.pi,3*math.pi/2]:
    blade=box((-2.48,.25*math.sin(angle),.25*math.cos(angle)),(.10,.17,.65),ocean_teal,bevel=.025)
    blade.rotation_euler.x=-angle
ball((-2.56,0,0),(.16,.16,.16),metal,'spine')
box((.75,0,.85),(.16,.16,.12),lamp)
sub,record=export_vessel('Prop_Ocean_CoralSubmarine','Submerged dock vessel; dive/helm presentation');records.append(record)
sub.location=(7,0,1.0)

parts=[]
for row in range(16):
    for column in range(6):
        box((-5+column*2,-2.85+row*.38,1.0),(1.97,.355,.14),plank if (row+column)%3 else wood,bevel=.012)
for x in [-5.6,0,5.6]:
    beam=cone((x,0,.05),.32,.32,6.4,wood,n=12);beam.rotation_euler.x=math.pi/2
for y in [-3.06,3.06]:
    for x in [-5,-3,-1,1,3,5]:box((x,y,.51),(1.96,.12,1.08),wood,bevel=.015)
for x in [-6.06,6.06]:
    for y in [-2,-.5,1,2.5]:box((x,y,.51),(.12,1.47,1.08),wood,bevel=.015)
for y in [-3.15,3.15]:
    for x in [-6,-3,0,3,6]:
        if y<0 and x==0:continue
        cone((x,y,1.65),.11,.10,1.35,wood,n=10)
        ring((x,y,2.15),.12,.025,cream)
    for a,b in [(-6,-3),(-3,-1.7),(1.7,3),(3,6)]:
        segment((a,y,1.95),(b,y,1.88),.025,cream,'spine')
for x in [-6,6]:segment((x,-3.15,1.95),(x,3.15,1.95),.025,cream,'spine')
for x in [-5.5,5.5]:
    cone((x,2.6,2.0),.055,.055,1.85,metal,n=10)
    box((x,2.6,2.88),(.30,.30,.45),metal,bevel=.025)
    box((x,2.6,2.88),(.245,.245,.32),lamp,bevel=.015)
for x in [-4,4]:
    buoy=ring((x,-3.24,1.35),.30,.07,sail);buoy.rotation_euler.x=math.pi/2
    segment((x,-3.15,1.9),(x,-3.24,1.5),.018,cream,'spine')
dock,record=export_vessel('Prop_Ocean_HarbourDock','Modular harbour dressing; existing pier collision presentation');records.append(record)
dock.location=(3.5,11,1)
if '--reuse-vessels' in sys.argv:
    import shutil
    previous=Path(sys.argv[sys.argv.index('--reuse-vessels')+1])
    frozen={r['id']:r for r in json.loads((previous/'manifest.json').read_text(encoding='utf-8'))['assets']}
    for record in records[:2]:
        original=frozen[record['id']];source=previous/original['file']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=original['sha256'] or original['triangles']!=record['triangles']:
            raise ValueError('Frozen vessel delivery differs')
        shutil.copy2(source,OUT/record['file']);record['sha256']=original['sha256'];record['reused_unchanged_from']=str(source)
finish_scene(records,2,7,'ocean-vessels',[],render=False)
(OUT/'portal.bba').rename(OUT/'ocean.bba')
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'));manifest['realm']='Ocean';manifest['status']='original static art; native assignment/collision/animation pending'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('OCEAN_VESSELS_EXPORTED',len(records),sum(r['triangles'] for r in records))
