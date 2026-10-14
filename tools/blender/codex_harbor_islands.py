"""Original additive harbor contest entries; run only during a claimed Blender turn.

blender -b -P codex_harbor_islands.py -- FRESH_OUTPUT
Shared helpers reset the background scene. Never execute in a teammate's live scene.
Exports separated role meshes in GLB, editable .blend and placement/provenance manifest.
Collision and gameplay are deliberately separate Unreal integration steps.
"""
from pathlib import Path
import sys, math, random, json, hashlib, argparse

parser = argparse.ArgumentParser()
parser.add_argument('output')
parser.add_argument('--with-terrain', action='store_true',
                    help='Optional original shell; default exports additive dressing only')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
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


def terrain(seed):
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


def dock():
    for y in range(-39, -17, 2):
        box((12, y, .24), (6, 1.8, .32), wood, bevel=.06)
    for y in [-38, -30, -22]:
        for x in [9, 15]: cone((x, y, -1), .25, .25, 4, wood)
    for x in range(5, 22, 2): box((x, -38, .24), (1.8, 5, .32), wood, bevel=.06)


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
    for i in range(22):
        angle = rng.uniform(0, math.tau); radius = rng.uniform(23, 34)
        x, y = radius*math.cos(angle), radius*math.sin(angle)
        if y < -18 or (x < -8 and y < 18): continue
        h = rng.uniform(4.5, 7)
        cone((x, y, h/2), .35, .22, h, wood)
        for dx, dy, dz in [(0, 0, h), (-1.7, .2, h-.8), (1.5, -.7, h-.5)]:
            ball((x+dx, y+dy, dz), (2.5, 2.1, 1.8), blossom if pink and i%3 == 0 else leaf)
    for i in range(60):
        x, y = rng.uniform(-30, 30), rng.uniform(-25, 25)
        if x*x+y*y > 900 or (x < -8 and y > 0) or (x > 8 and y < 0): continue
        cone((x, y, .25), .06, .04, .5, leaf, n=5)
        ball((x, y, .55), (.22, .22, .13), blossom if i%2 else lamp)


records = []
for index, title in enumerate(['CopperBeacon', 'BlossomHarbor', 'StormwatchCove']):
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    parts = []
    if args.with_terrain:
        group('Terrain', lambda: terrain(8401+index))
    group('Dock', dock)
    group('Beacon', lambda: lighthouse(12+index*3))
    group('Boathouse', boathouse)
    group('CaveArch', cave)
    group('Foliage', lambda: foliage(950+index, index == 1))
    group('Lagoon', lambda: ball((4, -26, .05), (9, 12, .12), water))
    # Water props require fitting to the receiving terrain's shoreline on placement.
    group('Waterfall', lambda: box((3, -43, -9), (2.5, .25, 18), water))
    name = 'CodexHarbor_' + title
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    glb = OUT/(name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_animations=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')))
    records.append({'id': name, 'file': glb.name, 'sha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
                    'seed': 8401+index, 'foliage_seed': 950+index,
                    'includes_terrain': args.with_terrain, 'target_footprint_metres': [92, 92],
                    'origin': 'receiving terrain ground centre Z=0',
                    'objects': len(objects), 'roles': sorted({o['harbor_role'] for o in objects}),
                    'stage': 'Blender export; Unreal placement, collision and gameplay pending'})
    (OUT/'harbor-manifest.json').write_text(json.dumps({'schemaVersion': 1, 'assets': records,
        'native_verified': False, 'author': 'team-codex',
        'placement_contract': 'Metres +Z up; role objects retain local positions; fit to receiving terrain',
        'collision_contract': 'No collision authored; foliage/water nonblocking; dock/building collision required'}, indent=2)+'\n')
    print('HARBOR_EXPORTED '+name, flush=True)
