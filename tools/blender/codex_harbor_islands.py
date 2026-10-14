"""Original additive harbor entries; isolated headless export alongside owner ingestion.

blender -b -P codex_harbor_islands.py -- FRESH_OUTPUT
Shared helpers reset the background scene. Never execute in a teammate's live scene.
Exports separated role meshes in GLB, editable .blend and placement/provenance manifest.
Collision and gameplay are deliberately separate Unreal integration steps.
"""
from pathlib import Path
import sys, math, random, json, hashlib, argparse, time
import bmesh

parser = argparse.ArgumentParser()
parser.add_argument('output')
parser.add_argument('--with-terrain', action='store_true',
                    help='Optional original shell; default exports additive dressing only')
parser.add_argument('--preset', choices=['all', 'CopperBeacon', 'BlossomHarbor', 'StormwatchCove'],
                    default='all', help='Export one complete kit in a bounded shared-tool turn')
parser.add_argument('--preview-only', action='store_true',
                    help='Save editable scene without delivery FBX/GLB or collision generation')
parser.add_argument('--render', action='store_true',
                    help='Render a consistent review camera using four CPU threads')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
SHORE_Y = -42.
OUT = Path(args.output)
if OUT.exists() and any(OUT.iterdir()):
    raise ValueError('Use a fresh output directory; existing entries must be retained')
exec(compile(Path(__file__).with_name('portal_common.py').read_text(), __file__, 'exec'))

grass = mat('Harbor meadow', (.28, .48, .25))
sand = mat('Harbor pale limestone', (.72, .65, .46))
rock = mat('Harbor slate', (.22, .28, .34))
wood = mat('Harbor cedar', (.31, .17, .095))
plaster = mat('Harbor lime plaster', (.82, .78, .62))
roof = mat('Harbor copper roof', (.15, .39, .38), .25)
water = mat('Harbor lagoon water', (.055, .37, .52))
water.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.28
foam = mat('Harbor soft foam', (.78,.89,.90))
leaf = mat('Harbor wind trees', (.20, .37, .22))
blossom = mat('Harbor blossoms', (.69, .38, .49))
lamp = mat('Harbor beacon amber', (1., .61, .16))
lamp.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1., .5, .08, 1.)
lamp.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 2.


def name_new(before, role):
    for obj in set(bpy.context.scene.objects) - before:
        if obj.type == 'MESH':
            obj.name = role + '_' + obj.name
            obj['harbor_role'] = role


def group(role, fn):
    before = set(bpy.context.scene.objects)
    fn()
    name_new(before, role)


def ground_height(x, y):
    if not args.with_terrain: return 0
    # A sheltered rise behind the beacon, with a flat building foundation.
    hill = 2.8*max(0, 1-math.hypot(x+19, y-13)/26)**2
    if math.hypot(x+15, y-6)<6: hill = 1.3
    # Actual lagoon basin and a narrow outlet to the southern rim.
    basin = ((x-12)/9)**2 + ((y+28)/14)**2
    t=max(0,min(1,(math.sqrt(basin)-.8)/.5))
    if y < -36: t=min(t,max(0,min(1,(abs(x-12)-1.8)/2.2)))
    t=t*t*(3-2*t)
    return -.7*(1-t)+(.45+hill)*t


def raise_group(role, height):
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.get('harbor_role')==role: obj.location.z += height


def terrain(seed):
    global SHORE_Y
    rng = random.Random(seed)
    n = 32
    radii = [42 + rng.uniform(-3, 3) for _ in range(n)]
    vertices = [(0, 0, 0)]
    for radius_scale, z in [(1., 0), (.99, -2.5), (.91, -5), (.70, -14), (.25, -22)]:
        vertices.extend((radii[i] * radius_scale * math.cos(i*math.tau/n),
                         radii[i] * radius_scale * math.sin(i*math.tau/n), z) for i in range(n))
    bottom = len(vertices); vertices.append((0, 0, -25))
    faces = []; slots = []
    for i in range(n):
        j = (i+1) % n
        faces.append((0, 1+i, 1+j)); slots.append(0)
        for layer in range(4):
            a = 1 + layer*n; b = a+n
            faces.append((a+i, b+i, b+j, a+j)); slots.append(1 if layer < 2 else 2)
        faces.append((bottom, 1+4*n+j, 1+4*n+i)); slots.append(2)
    mesh = bpy.data.meshes.new('Harbor strata'); mesh.from_pydata(vertices, [], faces); mesh.update()
    obj = bpy.data.objects.new('Terrain', mesh); bpy.context.collection.objects.link(obj)
    for material in [grass, sand, rock]: mesh.materials.append(material)
    for polygon, slot in zip(mesh.polygons, slots): polygon.material_index = slot
    # Exactly 92m XY, matching the existing pool's native footprint contract.
    bpy.context.view_layer.update()
    obj.scale.x = 92 / obj.dimensions.x; obj.scale.y = 92 / obj.dimensions.y
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    rim=[v.co.copy() for v in mesh.vertices[1:n+1]]
    intersections=[]
    for first,second in zip(rim,rim[1:]+rim[:1]):
        if min(first.x,second.x)<=12<=max(first.x,second.x) and abs(second.x-first.x)>1e-8:
            t=(12-first.x)/(second.x-first.x)
            intersections.append(first.y+t*(second.y-first.y))
    SHORE_Y=min(intersections)
    bm=bmesh.new(); bm.from_mesh(mesh)
    top_edges={edge for face in bm.faces if face.material_index==0 for edge in face.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(top_edges), cuts=10, use_grid_fill=True)
    for vertex in bm.verts:
        if abs(vertex.co.z)<1e-5: vertex.co.z=ground_height(vertex.co.x,vertex.co.y)
    for face in bm.faces:
        if face.material_index==0:
            centre=face.calc_center_median()
            basin=((centre.x-12)/10)**2+((centre.y+28)/15)**2
            if basin<1.35 or (abs(centre.x-12)<3.5 and centre.y<-34): face.material_index=1
    bm.normal_update(); bm.to_mesh(mesh); bm.free(); mesh.update()


def dock():
    for y in range(-39, -17, 2):
        box((12, y, .8), (6, 1.8, .32), wood, bevel=.06)
    for y in [-38, -30, -22]:
        for x in [9, 15]: cone((x, y, -1), .25, .25, 4, wood)
    # The cross-deck is a shallow raised landing. Its boards used to intersect
    # walkway boards at the same surface height, causing visible z-fighting.
    for x in range(5, 22, 2): box((x, -38, .92), (1.8, 5, .32), wood, bevel=.06)


def lighthouse(height):
    cone((-15, 6, 1), 5, 5, 2, sand, n=12)
    cone((-15, 6, height/2+1), 3.2, 2.3, height, plaster, n=12)
    for z in [height*.35, height*.7]: cone((-15, 6, z+1), 3.1-z*.04, 3.1-z*.04, .65, roof, n=12)
    cone((-15, 6, height+1.4), 3, 3, .5, wood, n=12)
    cone((-15, 6, height+3), .85, .85, 2.5, lamp, n=12)
    for i in range(8):
        t = i*math.tau/8
        cone((-15+2.3*math.cos(t), 6+2.3*math.sin(t), height+3), .14, .14, 3, wood)
    cone((-15, 6, height+5), 3.6, .15, 2.5, roof, n=8)
    box((-15, 3, 2), (1.5, .35, 3), wood)


def boathouse():
    box((15, -11, 2.7), (9, 7, 5.4), plaster, bevel=.10)
    for side in [-1, 1]:
        obj = box((15+side*2.6, -11, 6), (6, 8, .35), roof, bevel=.04)
        obj.rotation_euler.y = side*.48
    box((15, -14.6, 2), (3, .3, 4), wood)
    for x in [12, 18]: box((x, -14.65, 3.4), (1.4, .25, 1.5), lamp)
    # Dry-docked hull: visible prop, not a claimed drivable vehicle.
    boat = ball((23, -13, 1), (2, 4, 1), wood)
    box((23, -13, 1.7), (2.4, 4, .22), sand)


def cave():
    # Separate arch parts leave a genuine opening; never cover it with one hull.
    for x in [-4, 4]: box((x, -38, -7), (3, 5, 10), rock, bevel=.5)
    box((0, -38, -2.5), (11, 5, 2), rock, bevel=.4)
    box((0, -36, -11.8), (6, 8, .4), sand)


def foliage(seed, pink):
    rng = random.Random(seed)
    for i in range(48):
        angle = rng.uniform(0, math.tau); radius = rng.uniform(23, 34)
        x, y = radius*math.cos(angle), radius*math.sin(angle)
        if y < -18 or (x < -8 and y < 18): continue
        # Crown envelopes need clearance, not merely trunk-point separation.
        # Boathouse roof spans x~9..21/y~-15..-7; boat occupies x~21..25.
        if 5 < x < 29 and -21 < y < 0: continue
        h = rng.uniform(4.5, 7)
        ground=ground_height(x,y)
        cone((x, y, ground+h/2), .35, .22, h, wood)
        for dx, dy, dz in [(0, 0, h), (-1.7, .2, h-.8), (1.5, -.7, h-.5)]:
            ball((x+dx, y+dy, ground+dz), (2.5, 2.1, 1.8), blossom if pink and i%3 == 0 else leaf)
    for i in range(160):
        x, y = rng.uniform(-30, 30), rng.uniform(-25, 25)
        if x*x+y*y > 900 or (x < -8 and y > 0) or (x > 8 and y < 0): continue
        ground=ground_height(x,y)
        if ground < 0: continue
        cone((x, y, ground+.25), .06, .04, .5, leaf, n=5)
        ball((x, y, ground+.55), (.22, .22, .13), blossom if i%2 else lamp)


def garden_paths():
    # Meandering stepping stones connect the dock, cottage and beacon.
    for i in range(24):
        t = i/23
        x = 15-30*t+2*math.sin(t*math.tau)
        y = -16+22*t
        stone = box((x, y, ground_height(x,y)+.12), (1.3, 1., .24), sand, bevel=.14)
        stone.rotation_euler.z = .25*math.sin(i)
    for x, y in [(-5, -12), (-6, 16), (19, 9), (3, 18)]:
        ground=ground_height(x,y)
        ball((x, y, ground+.23), (4, 2.5, .35), leaf)
        for i in range(7):
            t = i*math.tau/7
            ball((x+2.4*math.cos(t), y+1.4*math.sin(t), ground+.75), (.5, .5, .35), blossom)
    for i in range(13):
        t = i*math.pi/12
        ball((12+10*math.cos(t), -28+13*math.sin(t), .28), (.7, .6, .55), sand)


def falling_water(outlet_y):
    # Static review geometry: a curved falling sheet, not a simulated fluid.
    vertices=[]
    for i in range(13):
        t=i/12
        width=1.7-.35*t
        centre=12+.25*math.sin(t*math.pi)
        y=outlet_y-1.7*t*t
        z=-.03-18*t
        vertices.extend([(centre-width,y,z),(centre+width,y,z)])
    faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(12)]
    data=bpy.data.meshes.new('Curved waterfall');data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new('Curved waterfall',data);bpy.context.collection.objects.link(obj)
    data.materials.append(water)
    solid=obj.modifiers.new('Water sheet thickness','SOLIDIFY');solid.thickness=.035
    for i in range(9):
        x=10.6+i*.35
        ball((x,outlet_y-.1,.01),(.28,.18,.045),foam)
    # A few restrained highlights help the flow read without a glowing wall.
    for i in range(3):
        t=.2+i*.24
        ball((11.4+i*.5,outlet_y-1.7*t*t,-18*t),(.10,.05,.65),foam)


def export_role_meshes(name, objects):
    """One origin-centred FBX per role; reuse native StaticMesh import path.

    Join temporary copies, preserving the editable scene's individual props.
    Blocking props receive one convex UCX hull per original solid part. The
    sculpted concave terrain requires separately reviewed triangle collision;
    a whole-terrain convex hull would bridge the lagoon basin.
    """
    role_records = []
    for role in sorted({obj['harbor_role'] for obj in objects}):
        copies = []; hulls = []
        try:
            bpy.ops.object.select_all(action='DESELECT')
            for source in objects:
                if source['harbor_role'] != role:
                    continue
                clone = source.copy(); clone.data = source.data.copy()
                bpy.context.collection.objects.link(clone)
                clone.select_set(True); copies.append(clone)
            bpy.context.view_layer.objects.active = copies[0]
            bpy.ops.object.join()
            mesh = bpy.context.object
            mesh.name = name + '_' + role
            bpy.context.scene.cursor.location = (0, 0, 0)
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            mesh.data.calc_loop_triangles()
            blocking = role in {'Terrain', 'Dock', 'Beacon', 'Boathouse', 'CaveArch'}
            if blocking and role != 'Terrain':
                bpy.context.view_layer.update()
                for source in (o for o in objects if o['harbor_role'] == role):
                    bm = bmesh.new()
                    try:
                        for vertex in source.data.vertices:
                            bm.verts.new(source.matrix_world @ vertex.co)
                        bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
                        loose = [v for v in bm.verts if not v.link_faces]
                        if loose: bmesh.ops.delete(bm, geom=loose, context='VERTS')
                        bm.normal_update()
                        hull_name = 'UCX_' + mesh.name + f'_{len(hulls):03d}'
                        hull_data = bpy.data.meshes.new(hull_name)
                        bm.to_mesh(hull_data)
                    finally:
                        bm.free()
                    hull = bpy.data.objects.new(hull_name, hull_data)
                    bpy.context.collection.objects.link(hull)
                    hull.hide_render = True; hull.select_set(True); hulls.append(hull)
            fbx = OUT/(mesh.name+'.fbx')
            started = time.perf_counter()
            bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True,
                object_types={'MESH'}, add_leaf_bones=False, bake_anim=False,
                apply_unit_scale=True, axis_forward='-Y', axis_up='Z')
            elapsed = time.perf_counter()-started
            role_records.append({'id': mesh.name, 'role': role, 'fbx': fbx.name,
                'sha256': hashlib.sha256(fbx.read_bytes()).hexdigest(),
                'bytes': fbx.stat().st_size, 'triangles': len(mesh.data.loop_triangles),
                'export_seconds': elapsed, 'source_objects': sum(o['harbor_role']==role for o in objects),
                'collision': 'Concave terrain: owner-reviewed triangle collision required' if role=='Terrain' else
                             'UCX convex per solid source part' if blocking else 'none; nonblocking',
                'collision_hulls': len(hulls), 'pivot': 'common island centre Z=0',
                'suggested_blocking': blocking, 'native_collision_verified': False})
        finally:
            # Only remove temporary export copies still registered after join.
            for clone in copies + hulls:
                try:
                    if clone.name in bpy.data.objects:
                        bpy.data.objects.remove(clone, do_unlink=True)
                except ReferenceError:
                    pass
    return role_records


def review_scene(name):
    bpy.ops.object.camera_add(location=(110, -150, 100))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, -3, -4))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = 120
    scene = bpy.context.scene; scene.camera = camera
    bpy.ops.object.light_add(type='SUN')
    bpy.context.object.rotation_euler = (.5, -.4, -.6)
    bpy.context.object.data.energy = 3
    bpy.context.object.data.color=(1.,.88,.73)
    bpy.context.object.data.angle=.08
    scene.world.use_nodes=True
    background=scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value=(.30,.48,.65,1.)
    background.inputs['Strength'].default_value=.35
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 24
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 4
    scene.render.resolution_x = 1000; scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT/(name+'.review.png'))


records = []
for index, title in enumerate(['CopperBeacon', 'BlossomHarbor', 'StormwatchCove']):
    if args.preset not in {'all', title}:
        continue
    generation_started = time.perf_counter()
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    parts = []
    if args.with_terrain:
        group('Terrain', lambda: terrain(8401+index))
    group('Dock', dock)
    group('Beacon', lambda: lighthouse(12+index*3))
    raise_group('Beacon', ground_height(-15,6))
    group('Boathouse', boathouse)
    raise_group('Boathouse', ground_height(15,-11))
    group('CaveArch', cave)
    group('Foliage', lambda: foliage(950+index, index == 1))
    group('Garden', garden_paths)
    group('Lagoon', lambda: ball((12, -28, -.03), (8.7, 13.7, .10), water))
    outlet_end=SHORE_Y-.25
    group('Outlet', lambda: box((12,(-37+outlet_end)/2,-.03),(3.4,-37-outlet_end,.12),water))
    # Water props require fitting to the receiving terrain's shoreline on placement.
    group('Waterfall', lambda: falling_water(outlet_end))
    name = 'CodexHarbor_' + title
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    generation_seconds = time.perf_counter()-generation_started
    role_exports = [] if args.preview_only else export_role_meshes(name, objects)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    glb = None if args.preview_only else OUT/(name+'.glb')
    export_started = time.perf_counter()
    if glb:
        bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_animations=False)
    glb_seconds = None if args.preview_only else time.perf_counter()-export_started
    review_scene(name)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')))
    render_seconds = None
    if args.render:
        render_started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        # A normal-distance view catches defects hidden by the aerial framing.
        camera=bpy.context.scene.camera
        camera.location=(34,-40,5.5); camera.data.type='PERSP'; camera.data.lens=32
        camera.rotation_euler=(Vector((3,-7,3))-camera.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.scene.render.filepath=str(OUT/(name+'.player-review.png'))
        bpy.ops.render.render(write_still=True)
        render_seconds = time.perf_counter()-render_started
    records.append({'id': name, 'file': glb.name if glb else None,
                    'sha256': hashlib.sha256(glb.read_bytes()).hexdigest() if glb else None,
                    'seed': 8401+index, 'foliage_seed': 950+index,
                    'includes_terrain': args.with_terrain, 'target_footprint_metres': [92, 92],
                    'generation_seconds': generation_seconds, 'glb_export_seconds': glb_seconds,
                    'preview_only': args.preview_only, 'render_seconds': render_seconds,
                    'review_image': name+'.review.png' if args.render else None,
                    'player_review_image': name+'.player-review.png' if args.render else None,
                    'shoreline_outlet_y_metres': outlet_end,
                    'quality_ready': False,
                    'role_exports': role_exports,
                    'origin': 'receiving terrain ground centre Z=0',
                    'objects': len(objects), 'roles': sorted({o['harbor_role'] for o in objects}),
                    'stage': 'Blender preview; no delivery exports' if args.preview_only else
                             'Blender export; visual review and Unreal acceptance pending'})
    (OUT/'harbor-manifest.json').write_text(json.dumps({'schemaVersion': 1, 'assets': records,
        'native_verified': False, 'author': 'team-codex',
        'source_files': {filename: hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
                         for filename in ['codex_harbor_islands.py', 'portal_common.py', 'labyrinth_cast.py']},
        'placement_contract': 'Metres +Z up; role objects retain local positions; fit to receiving terrain',
        'collision_contract': 'FBX blocking props have per-solid UCX; sculpted terrain needs triangle collision; GLB render only; foliage/water nonblocking; native verification pending'}, indent=2)+'\n')
    print(('HARBOR_PREVIEW_READY ' if args.preview_only else 'HARBOR_EXPORTED ')+name, flush=True)
