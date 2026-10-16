"""Pure R2 geometry proposal. Default invocation prints a dry-run summary only.

No bpy import, scene mutation, file writes, render/export or production receipts.
Future serialized Blender authoring must consume these meshes under a new grant.
"""
import json
import math
from pathlib import Path

RECIPE = Path(__file__).resolve().parents[2]/'data/ecology/shardstead-willow-wetland-polish-r2.json'


def configuration():
    recipe = json.loads(RECIPE.read_text(encoding='utf-8'))
    if (recipe['schema'] != 'daedalus.shardstead.willow-polish/v2'
            or recipe['version'] != 'pilot-r2' or recipe['units'] != 'metres'
            or recipe['frame'] != 'WORLD_XY_METRES' or recipe['seed'] != 8407
            or recipe['output'] != 'artifacts/biomes/shardstead/WillowWetland/pilot-r2'
            or recipe['polish']['max_exported_triangles'] > 8000):
        raise ValueError('Wrong versioned synthetic geometry contract')
    return recipe


def height(recipe, x, y):
    terrain = recipe['terrain']
    t = max(0., min(1., (math.hypot(x, y)-terrain['basin_radius'])
                   /(terrain['shore_radius']-terrain['basin_radius'])))
    return terrain['basin_floor']+(terrain['shore_height']-terrain['basin_floor'])*t*t*(3-2*t)


def mesh(name, role, materials):
    return dict(name=name, role=role, pivot=[0., 0., 0.], units='metres',
                vertices=[], triangles=[], material_indices=[], materials=materials)


def surface_height(recipe, x, y):
    r=math.hypot(x,y)
    inner,outer=recipe['pond']['radius'],recipe['terrain']['shore_radius']
    if inner<=r<=outer:
        t=(r-inner)/(outer-inner)
        collar=recipe['pond']['water_z']+(recipe['terrain']['shore_height']-recipe['pond']['water_z'])*t*t*(3-2*t)
        return max(height(recipe,x,y),collar)
    return height(recipe,x,y)


def append(target, vertices, triangles, material=0):
    offset = len(target['vertices'])
    target['vertices'].extend(vertices)
    target['triangles'].extend(tuple(offset+i for i in face) for face in triangles)
    target['material_indices'].extend([material]*len(triangles))


def ellipsoid(target, centre, radii, material, sides=8):
    """Three latitude rings and distinct poles: no collapsed pole triangles."""
    x, y, z = centre
    rx, ry, rz = radii
    vertices = [(x, y, z+rz)]
    for ring in range(1, 4):
        phi = math.pi*ring/4
        for i in range(sides):
            angle = math.tau*i/sides
            vertices.append((x+rx*math.sin(phi)*math.cos(angle),
                             y+ry*math.sin(phi)*math.sin(angle),z+rz*math.cos(phi)))
    bottom = len(vertices)
    vertices.append((x, y, z-rz))
    faces = []
    for i in range(sides):
        j = (i+1)%sides
        faces.append((0,1+i,1+j))
        for ring in range(2):
            a,b = 1+ring*sides+i,1+ring*sides+j
            faces.extend([(a,a+sides,b+sides),(a,b+sides,b)])
        faces.append((bottom,1+2*sides+j,1+2*sides+i))
    append(target, vertices, faces, material)


def tube(target, points, radius, material, sides=6):
    # Upright/slightly leaning original forms; horizontal cross sections.
    vertices = [(x+radius*math.cos(math.tau*i/sides),
                 y+radius*math.sin(math.tau*i/sides),z)
                for x,y,z in points for i in range(sides)]
    faces = []
    for ring in range(len(points)-1):
        for i in range(sides):
            j=(i+1)%sides
            a,b=ring*sides+i,ring*sides+j
            faces.extend([(a,b,b+sides),(a,b+sides,a+sides)])
    for start, reverse in ((0,True),((len(points)-1)*sides,False)):
        for i in range(1,sides-1):
            face=(start,start+i,start+i+1)
            faces.append(tuple(reversed(face)) if reverse else face)
    append(target, vertices, faces, material)


def path_mesh(recipe):
    """Use the same half-metre vertices/diagonals as R1 terrain, not 4 corners."""
    result=mesh('Synthetic_North_Path','context',['earth'])
    x0,y0,x1,y1=recipe['paths'][0]['aabb']
    step=recipe['polish']['path_grid_metres']
    nx,ny=round((x1-x0)/step),round((y1-y0)/step)
    vertices=[(x0+col*step,y0+row*step,surface_height(recipe,x0+col*step,y0+row*step)+.025)
              for row in range(ny+1) for col in range(nx+1)]
    faces=[]
    for row in range(ny):
        for col in range(nx):
            a=row*(nx+1)+col
            faces.extend([(a,a+1,a+nx+2),(a,a+nx+2,a+nx+1)])
    append(result,vertices,faces)
    return result


def build(recipe=None):
    recipe=configuration() if recipe is None else recipe
    willow=mesh('WillowPilot_Willow','flora',['bark','leaf_sage','leaf_light'])
    reeds=mesh('WillowPilot_Reeds','flora',['reed','reed_seed'])
    pond=mesh('WillowPilot_Pond','habitats',['water','shore_soil'])
    for index,placement in enumerate(recipe['placements']):
        x,y,z=placement['position']; yaw=placement['yaw']
        if index%3==0:
            tube(willow,[(x,y,z-.02),(x+.1,y,z+1.8),(x,y,z+3.4)],.16,0)
            ellipsoid(willow,(x,y,z+3.25),(1.25,1.25,.58),1)
            for branch in range(8):
                angle=yaw+math.tau*branch/8
                dx,dy=math.cos(angle),math.sin(angle)
                # Broad hanging leaf masses replace R1 eight bare green strands;
                # all foliage remains inside original1.655m footprint proof.
                ellipsoid(willow,(x+dx,y+dy,z+2.55),(.48,.48,.98),1+branch%2)
                ellipsoid(willow,(x+.6*dx,y+.6*dy,z+3.25),(.65,.65,.45),1)
        else:
            for stem in range(5):
                sx,sy=x+.08*(stem-2),y+.06*(stem%2)
                base=height(recipe,sx,sy)-.02
                tube(reeds,[(sx,sy,base),(sx+.10,sy,base+1.12)],.036,0)
                ellipsoid(reeds,(sx+.10,sy,base+1.05),(.065,.065,.15),1,sides=6)
                for sign in (-1,1):
                    # Raised double-sided triangular blades catch silhouette.
                    v=[(sx,sy,base+.35),(sx+sign*.28,sy+.035,base+.78),
                       (sx+sign*.13,sy-.035,base+.62)]
                    append(reeds,v,[(0,1,2),(2,1,0)],0)
    segments=64
    radius=recipe['pond']['radius']; water=recipe['pond']['water_z']
    vertices=[(0.,0.,water)]+[(radius*math.cos(math.tau*i/segments),
               radius*math.sin(math.tau*i/segments),water) for i in range(segments)]
    append(pond,vertices,[(0,1+i,1+(i+1)%segments) for i in range(segments)])
    # R1 water stops at r6,z0 but ground there is ~-.896m. This explicit
    # decorative collar closes that exposed gap without changing terrain/masks,
    # water radius, placements or path footprint. It is NOT traversability proof.
    vertices=[]
    for ring in range(6):
        t=ring/5; r=radius+(recipe['terrain']['shore_radius']-radius)*t
        z=water+(recipe['terrain']['shore_height']-water)*t*t*(3-2*t)
        for i in range(segments):
            angle=math.tau*i/segments
            vertices.append((r*math.cos(angle),r*math.sin(angle),z))
    faces=[]
    for ring in range(5):
        for i in range(segments):
            j=(i+1)%segments;a=ring*segments+i;b=ring*segments+j
            faces.extend([(a,a+segments,b),(b,a+segments,b+segments)])
    append(pond,vertices,faces,1)
    exported=[willow,reeds,pond]
    if sum(len(m['triangles']) for m in exported)>recipe['polish']['max_exported_triangles']:
        raise ValueError('Exported triangle budget exceeded')
    return dict(exported=exported,path_context=path_mesh(recipe),recipe=recipe,
                actual={stage:None for stage in ('authored','exports','views','reopened','native','quality_accepted')},
                status='SOURCE_ONLY_UNRENDERED_UNACCEPTED')


def main():
    plan=build()
    print(json.dumps(dict(status=plan['status'],output=plan['recipe']['output'],
          roles=[dict(name=m['name'],role=m['role'],triangles=len(m['triangles'])) for m in plan['exported']],
          exported_triangles=sum(len(m['triangles']) for m in plan['exported']),actual=plan['actual'])))


if __name__=='__main__':
    main()
