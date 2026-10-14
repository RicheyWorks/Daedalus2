"""Original 92 m island mesh pool for Claude request 29882.
Blender 4.3: blender -b -P island_mesh_pool.py -- OUTPUT [--fragments 12 --pads 6 --render]
GLB contains only render geometry; FBX companion carries named UCX convex hulls.
The original pool has flat tops; optional specials have rim Z=0 and depressed surfaces.
"""
from pathlib import Path
import argparse, math, random, hashlib, json, sys, bmesh
# Reuse owned material/helper setup; no imported models or third-party textures.
exec(compile(Path(__file__).with_name('portal_common.py').read_text(), __file__, 'exec'))
parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('--fragments',type=int,default=12)
parser.add_argument('--pads',type=int,default=6);parser.add_argument('--render',action='store_true')
parser.add_argument('--special-fragments',type=int,default=0,
                    help='Add up to six new crater/split-top assets without replacing the original pool')
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if not 0<=a.fragments<=12 or not 0<=a.pads<=6 or not 0<=a.special_fragments<=6 or a.fragments+a.pads+a.special_fragments==0:raise ValueError('Bounded nonempty pool required')
OUT=Path(a.output)
if a.special_fragments and OUT.exists() and any(OUT.iterdir()):
    raise ValueError('Special batch requires a fresh/empty directory; retain the original pool')
OUT.mkdir(parents=True,exist_ok=True)
stone_top=mat('Island weathered slate',(.23,.31,.30));rock=mat('Island dark basalt',(.09,.12,.17))
rock_light=mat('Island exposed facets',(.18,.22,.28));grass=mat('Island terrace moss',(.22,.34,.17))
clay=mat('Island terrace earth',(.26,.20,.13));MATERIALS=[stone_top,rock,rock_light,grass,clay]
N=24

def outline(exponent):
    out=[]
    for i in range(N):
        t=i*math.tau/N;c=math.cos(t);s=math.sin(t)
        out.append((46*math.copysign(abs(c)**exponent,c),46*math.copysign(abs(s)**exponent,s)))
    return out

def shape(name,index,pad,special=False):
    rng=random.Random(0xDAD20000+index+(100 if pad else 0));p=.65+(.75*index/(5 if pad else 11))
    top=outline(p);height=1+index*.4 if pad else 8+index*12/11
    depth=(.8+.5*index) if index<3 else (1.5+.5*(index-3))
    def surface(x,y):
        if not special:return 0
        # Three crater bowls and three north/south rifts. The top fan is faceted,
        # shallow and continuous; these are slopes, not an invisible void.
        if index<3:return -depth if x==0 and y==0 else 0
        return -depth*max(0,1-abs(x)/12)
    points=[(0,0,surface(0,0))]+[(x,y,surface(x,y)) for x,y in top]
    for x,y in top:
        shrink=.99 if pad else rng.uniform(.75,.97)
        points.append((x*shrink,y*shrink,-height*(.2 if pad else rng.uniform(.35,.60))))
    offset=(0,0) if pad or special else (rng.uniform(-3,3),rng.uniform(-3,3))
    for x,y in top:
        shrink=.94 if pad else rng.uniform(.24,.58)
        points.append((offset[0]+x*shrink,offset[1]+y*shrink,-height*(1 if pad else rng.uniform(.73,.96))))
    bottom=len(points);points.append((offset[0],offset[1],-height));faces=[];slots=[]
    for i in range(N):
        j=(i+1)%N;faces.append((0,1+i,1+j));slots.append(3 if pad else 0)
        faces.append((1+i,1+N+i,1+N+j,1+j));slots.append(4 if pad else 2)
        faces.append((1+N+i,1+2*N+i,1+2*N+j,1+N+j));slots.append(4 if pad else rng.choice([1,1,2]))
        faces.append((bottom,1+2*N+j,1+2*N+i));slots.append(4 if pad else 1)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    for m in MATERIALS:mesh.materials.append(m)
    for polygon,slot in zip(mesh.polygons,slots):polygon.material_index=slot
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        v=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x/92+.5,v.y/92+.5)
    bm=bmesh.new();bm.from_mesh(mesh)
    if any(len(e.link_faces)!=2 for e in bm.edges):raise ValueError('Non-manifold render shell '+name)
    bm.free();mesh.calc_loop_triangles()
    if abs(obj.dimensions.x-92)>1e-4 or abs(obj.dimensions.y-92)>1e-4:raise ValueError('Footprint mismatch '+name)
    if max(v.co.z for v in mesh.vertices)>1e-6 or abs(min(v.co.z for v in mesh.vertices)+height)>1e-4:raise ValueError('Top/thickness mismatch '+name)
    # Concave tops need separate radial convex pieces. All support vertices stay
    # within their top triangle's XY footprint and below its plane: no convex
    # bridge over the crater/rift. Existing flat pool retains its single hull.
    sectors=range(N) if special else [None];hulls=[];collision_parts=[]
    for sector in sectors:
        indices=list(range(len(points))) if sector is None else [0,1+sector,1+(sector+1)%N,
            1+N+sector,1+N+(sector+1)%N,1+2*N+sector,1+2*N+(sector+1)%N,bottom]
        if sector is not None:
            first,second,third=(Vector(points[i]) for i in indices[:3]);normal=(second-first).cross(third-first)
            if normal.z<=0 or any(normal.dot(Vector(points[i])-first)>1e-5 for i in indices[3:]):
                raise ValueError('Collision support crosses the top plane '+name)
        bm=bmesh.new()
        for i in indices:bm.verts.new(points[i])
        bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
        unused=[v for v in bm.verts if not v.link_faces]
        if unused:bmesh.ops.delete(bm,geom=unused,context='VERTS')
        bm.normal_update()
        if any(len(e.link_faces)!=2 for e in bm.edges):raise ValueError('Non-manifold collision hull '+name)
        hull_name='UCX_'+name+f'_{len(hulls):02d}'
        hullmesh=bpy.data.meshes.new(hull_name);bm.to_mesh(hullmesh);bm.free()
        hull=bpy.data.objects.new(hull_name,hullmesh);bpy.context.collection.objects.link(hull);hull.hide_render=True
        hulls.append(hull)
        collision_parts.append({'name':hull.name,'vertices':[list(v.co) for v in hullmesh.vertices],
                                'faces':[list(f.vertices) for f in hullmesh.polygons]})
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    glb=OUT/(name+'.glb');bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False)
    for hull in hulls:hull.select_set(True)
    fbx=OUT/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,apply_unit_scale=True,axis_forward='-Y',axis_up='Z')
    collision=({'schemaVersion':2,'hulls':collision_parts} if special else collision_parts[0].copy())
    collision['coordinates']='Blender metres +Z up; convert with the same asset importer'
    (OUT/(name+'.collision.json')).write_text(json.dumps(collision,indent=2)+'\n')
    record={'id':name,'kind':'terrace-pad' if pad else 'asteroid-fragment','file':glb.name,'sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),
            'fbx':fbx.name,'fbx_sha256':hashlib.sha256(fbx.read_bytes()).hexdigest(),'footprint_metres':[92,92],
            'thickness_metres':height,'expected_native_bounds_cm':[9200,9200,height*100],'origin':'top centre Z=0','triangles':len(mesh.loop_triangles),'collision':hulls[0].name if not special else [h.name for h in hulls],
            'collision_file':name+'.collision.json','collision_triangles':sum(len(f)-2 for part in collision_parts for f in part['faces']),
            'status':'exported; native import/collision/walk proof pending'}
    if special:record.update({'kind':'crater-fragment' if index<3 else 'split-top-fragment',
        'surface_depth_metres':depth,'collision_hulls':len(hulls),'origin':'XY centre; rim height Z=0',
        'top_contract':'rim Z=0; depressed continuous walking surface'})
    return obj,hulls,record

records=[]
for pad,count,special in [(False,a.fragments,False),(True,a.pads,False),(False,a.special_fragments,True)]:
    for i in range(count):
        name=('Island_Frag_Special_' if special else 'Island_Pad_' if pad else 'Island_Frag_')+f'{i+1:02d}'
        obj,hulls,record=shape(name,i,pad,special);records.append(record)
        pos=((len(records)-1)%6*120,(len(records)-1)//6*120,0);obj.location=pos
        for hull in hulls:hull.location=pos
        (OUT/'island-mesh-pool.json').write_text(json.dumps({'schemaVersion':1,'assets':records,'native_verified':False},indent=2)+'\n')
        print('ISLAND_ASSET_READY '+name,flush=True)
# Scene is a review arrangement; individual exports above remain origin-centred.
cx=300;cy=(math.ceil(len(records)/6)-1)*60
bpy.ops.object.camera_add(location=(cx+500,cy-650,600));cam=bpy.context.object
cam.rotation_euler=(Vector((cx,cy,-5))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=850;cam.data.clip_end=5000;bpy.context.scene.camera=cam
bpy.ops.object.light_add(type='SUN',location=(0,0,300));bpy.context.object.rotation_euler=(.4,-.6,-.3);bpy.context.object.data.energy=3
bpy.ops.object.light_add(type='SUN');bpy.context.object.rotation_euler=(1.2,.4,2.5);bpy.context.object.data.energy=.6
scene=bpy.context.scene;scene.world.color=(.17,.21,.29);scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1900;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'island-mesh-pool.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island-mesh-pool.blend'))
if a.render:bpy.ops.render.render(write_still=True)
print('ISLAND_POOL_READY '+str(len(records)),flush=True)
