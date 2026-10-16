"""Pure deterministic pendulous Willow-role proposal; no bpy or file writes."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RECIPE=ROOT/'data/ecology/shardstead-willow-wetland-canopy-r3.json'
FROZEN={
 'tools/blender/shardstead_willow_wetland_polish_r2.py':{'d828f4bcde4b2033990e776d88c000810bcd05458256b31b11d2d32d9fc6cce4'},
 'data/ecology/shardstead-willow-wetland-polish-r2.json':{'b6e783c7c8053de3857e2ad70cf839fefbe754766147701ef31ad3f0932d2d74','f66365eddc7f94c6ad6ffa9e1af706526916c6046a266756edbfa32100d295e5'},
 'tools/blender/shardstead_willow_wetland_polish_r2_test.py':{'fa311d992ff5f5639d1df94356aebf21f22d89afcd72b0dca4f088be91601dd6'},
 'tools/blender/shardstead_willow_wetland_polish_r2_blender.py':{'c0d0e3be93b05cb0c9a9081ec927ec407cbc23ba4ecca41068a452f236b7552a'},
 'tools/blender/shardstead_willow_wetland_polish_r2_blender_test.py':{'ab86d0d247a8aeaa6578ff316e6391ba0c67a17a5060c32e1041c4aac4c3f3eb'},
 'tools/blender/shardstead_willow_wetland_polish_r2_views.py':{'65c9f7fd8114dfd606b33347f6e328201188069dcc04bd20bd28c41213e822c0'},
 'tools/blender/shardstead_willow_wetland_polish_r2_views_test.py':{'ac175a2e01772b394f4e220a8d9c9d491c2e927408b744fa8d9c7b2365d4fbe7'}}


def pin(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def reference():
    raw=None
    for path,accepted in FROZEN.items():
        data=(ROOT/path).read_bytes()
        if hashlib.sha256(data).hexdigest() not in accepted:
            raise ValueError('Frozen R2 source changed: '+path)
        if path.endswith('polish_r2.py'): raw=data
    path=ROOT/'tools/blender/shardstead_willow_wetland_polish_r2.py'
    spec=importlib.util.spec_from_file_location('_frozen_willow_r2',path)
    module=importlib.util.module_from_spec(spec)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def configuration():
    recipe=json.loads(RECIPE.read_text())
    if (recipe['schema']!='daedalus.shardstead.willow-canopy/v3' or recipe['units']!='metres'
        or recipe['pivot']!=[0,0,0] or recipe['willow_triangle_cap']>3392
        or recipe['output']!='artifacts/biomes/shardstead/WillowWetland/pilot-r3'):
        raise ValueError('Wrong source-only R3 contract')
    return recipe


def curtain(target,points,half_widths,depth,tangent,radial,append,material):
    """Tapered solid ribbon; each centre is a downward hanging control point."""
    vertices=[]
    for centre,width in zip(points,half_widths):
        for side,thickness in ((-1,-1),(1,-1),(1,1),(-1,1)):
            vertices.append(tuple(centre[i]+side*width*tangent[i]+thickness*depth*radial[i] for i in range(3)))
    faces=[]
    for ring in range(len(points)-1):
        for side in range(4):
            a=ring*4+side;b=ring*4+(side+1)%4
            faces.extend([(a,b,b+4),(a,b+4,a+4)])
    faces.extend([(0,2,1),(0,3,2)])
    last=(len(points)-1)*4
    faces.extend([(last,last+1,last+2),(last,last+2,last+3)])
    append(target,vertices,faces,material)
    return vertices


def branch_sweep(target,points,radius,material,azimuth,append,sides=4):
    """Oriented cross sections along a planar rising-then-descending branch.

    Azimuth is perpendicular to the radial/Z branch plane. At every station,
    U=azimuth and V=T cross U ensure U cross V points along the local tangent.
    The same outward side/cap order therefore works on both slope directions.
    """
    vertices=[]
    for station,point in enumerate(points):
        before=points[max(0,station-1)];after=points[min(len(points)-1,station+1)]
        direction=[after[i]-before[i] for i in range(3)]
        length=math.sqrt(sum(v*v for v in direction))
        if length<=1e-12: raise ValueError('Undefined branch tangent')
        t=[v/length for v in direction]
        v=(t[1]*azimuth[2]-t[2]*azimuth[1],
           t[2]*azimuth[0]-t[0]*azimuth[2],t[0]*azimuth[1]-t[1]*azimuth[0])
        v_length=math.sqrt(sum(value*value for value in v))
        if v_length<=1e-12: raise ValueError('Undefined branch frame')
        v=tuple(value/v_length for value in v)
        for side in range(sides):
            angle=math.tau*side/sides
            vertices.append(tuple(point[i]+radius*(math.cos(angle)*azimuth[i]+math.sin(angle)*v[i]) for i in range(3)))
    faces=[]
    for station in range(len(points)-1):
        for side in range(sides):
            a=station*sides+side;b=station*sides+(side+1)%sides
            faces.extend([(a,b,b+sides),(a,b+sides,a+sides)])
    for start,reverse in ((0,True),((len(points)-1)*sides,False)):
        for side in range(1,sides-1):
            face=(start,start+side,start+side+1)
            faces.append(tuple(reversed(face)) if reverse else face)
    append(target,vertices,faces,material)


def build():
    recipe=configuration();r2=reference();baseline=r2.build()
    if pin(baseline['recipe']['placements'])!=recipe['placement_sha256']:
        raise ValueError('Retained placements changed')
    willow=r2.mesh('WillowPilot_Willow','flora',baseline['exported'][0]['materials'][:])
    structures=[]
    for index,placement in enumerate(baseline['recipe']['placements']):
        if index%3: continue
        x,y,z=placement['position'];yaw=placement['yaw']
        # Exact original R2 trunk primitive, radius, anchors and material.
        r2.tube(willow,[(x,y,z-.02),(x+.1,y,z+1.8),(x,y,z+3.4)],.16,0)
        for branch in range(recipe['branches_per_tree']):
            angle=yaw+branch*math.tau/recipe['branches_per_tree']
            radial=(math.cos(angle),math.sin(angle),0.)
            tangent=(-radial[1],radial[0],0.)
            def world(profile):
                return [(x+r*radial[0],y+r*radial[1],z+h) for r,h in profile]
            points=world(recipe['branch_profile'])
            branch_sweep(willow,points,recipe['branch_radius'],0,tangent,r2.append,sides=4)
            leaves=[]
            for number,item in enumerate(recipe['curtains']):
                centres=world(item['profile'])
                if centres[0]!=points[item['attachment_index']]:
                    raise ValueError('Foliage detached from branch control point')
                start=len(willow['vertices'])
                curtain(willow,centres,recipe['curtain_half_widths'],recipe['curtain_half_depth'],
                        tangent,radial,r2.append,1+number%2)
                leaves.append(dict(centres=centres,attachment=points[item['attachment_index']],
                                   vertex_range=[start,len(willow['vertices'])]))
            structures.append(dict(tree_index=index,branch=branch,centreline=points,curtains=leaves))
    if len(willow['triangles'])>recipe['willow_triangle_cap']:
        raise ValueError('R2 Willow-role triangle cap exceeded')
    # Reuse actual unchanged R2 objects; no re-generation of another role.
    baseline['exported'][0]=willow
    return dict(exported=baseline['exported'],path_context=baseline['path_context'],
                context_recipe=baseline['recipe'],canopy_recipe=recipe,structures=structures,
                actual=recipe['actual'],status='SOURCE_ONLY_UNRENDERED_UNACCEPTED')


def main():
    plan=build()
    print(json.dumps(dict(status=plan['status'],proposed_output=plan['canopy_recipe']['output'],
          willow_triangles=len(plan['exported'][0]['triangles']),trees=4,
          pendulous_branches=len(plan['structures']),unchanged_roles=['Reeds','Pond','path','terrain/context'],
          actual=plan['actual'])))


if __name__=='__main__':
    main()
