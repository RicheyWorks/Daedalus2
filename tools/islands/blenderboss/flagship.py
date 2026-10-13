"""Blender Boss Island flagship (contest). blender -b --factory-startup --python assets/flagship.py -- <art> <out_png>"""
import bpy, bmesh, sys, os, math, random, re, json
from mathutils import Vector, noise
a = sys.argv[sys.argv.index("--")+1:]; ART, PNG = a[0], a[1]
os.makedirs(os.path.join(ART, "flagship"), exist_ok=True); GLB = os.path.join(ART, "glb"); NAME = "Prop_Island_Flagship_BlenderBoss"
BASE = []; R = 120.0  # radius m: double the 60 m planned island radius (240 m across)
random.seed(1337)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
root = bpy.data.collections.new(NAME); sc.collection.children.link(root)
def h(x, y):
    d = math.hypot(x, y) / R
    base = max(0.0, 1 - d**2.2) * 14
    n = noise.fractal(Vector((x/45, y/45, 0.3)), 0.6, 2.0, 5) * 5
    ridge = max(0, 1 - math.hypot(x+35, y-30)/40) * 18   # quarry hill NW
    t = base + n*max(0, 1-d) + ridge
    t = round(t/3.0)*3.0*0.15 + t*0.85                # terraced tiers
    return t if d < 0.96 else t*(1-(d-0.96)/0.04)-3*(d-0.96)/0.04 if d < 1 else -3
# terrain: polar mesh, smooth circular rim (no grid stair-steps)
bm = bmesh.new(); RINGS, SEG = 90, 256
ctr = bm.verts.new((0, 0, h(0, 0))); rings = []
for i in range(1, RINGS+1):
    rr = R*1.0*i/RINGS; rings.append([bm.verts.new((rr*math.cos(j*6.283185/SEG), rr*math.sin(j*6.283185/SEG), h(rr*math.cos(j*6.283185/SEG), rr*math.sin(j*6.283185/SEG)))) for j in range(SEG)])
for j in range(SEG): bm.faces.new((ctr, rings[0][j], rings[0][(j+1) % SEG]))
for i in range(RINGS-1):
    for j in range(SEG): bm.faces.new((rings[i][j], rings[i+1][j], rings[i+1][(j+1) % SEG], rings[i][(j+1) % SEG]))
lip = [bm.verts.new((v.co.x*1.01, v.co.y*1.01, -3.0)) for v in rings[-1]]
for j in range(SEG): bm.faces.new((rings[-1][j], lip[j], lip[(j+1) % SEG], rings[-1][(j+1) % SEG]))
me = bpy.data.meshes.new(NAME+"_Terrain"); bm.normal_update(); bm.to_mesh(me); bm.free()
ter = bpy.data.objects.new(NAME+"_Terrain", me); root.objects.link(ter); BASE.append(ter)
# flat material slots (Unreal's glTF import ignores vertex colours -> terrain showed white): 0 grass 1 rock 2 sand 3 dirt 4 water
def tmat(n, c, a=1.0):
    m = bpy.data.materials.new(n); m.use_nodes = True; p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = c; p.inputs["Roughness"].default_value = 0.9 if a == 1.0 else 0.1
    if a < 1.0: p.inputs["Alpha"].default_value = a; m.blend_method = "BLEND"
    me.materials.append(m)
tmat("M_BB_Grass", (0.20, 0.50, 0.12, 1)); tmat("M_BB_TerrainRock", (0.45, 0.42, 0.38, 1)); tmat("M_BB_Sand", (0.80, 0.72, 0.50, 1))
tmat("M_BB_Dirt", (0.36, 0.26, 0.17, 1)); tmat("M_BB_ShoreWater", (0.10, 0.62, 0.85, 1))
for poly in me.polygons:
    vs = [me.vertices[k].co for k in poly.vertices]; z = sum(v.z for v in vs)/len(vs); cx = sum(v.x for v in vs)/len(vs); cy = sum(v.y for v in vs)/len(vs)
    d = math.hypot(cx, cy) / R; steep = poly.normal.z < 0.80 if poly.area > 0 else False
    if z < -0.5: k = 3                                          # rim lip / underside edge
    elif d > 0.93 and z < 0.5: k = 4                            # wet shoreline ring
    elif z < 1.5: k = 2                                         # beach
    elif z >= 13 or steep: k = 1                                # hilltop / cliffs
    elif math.hypot(cx + 35, cy - 30) < 26 or math.hypot(cx, cy) < 14: k = 3   # quarry floor + plaza dirt
    else: k = 0
    poly.material_index = k
for p in me.polygons: p.use_smooth = True
# underside: inverted cone
bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=R*1.0, depth=80, location=(0, 0, -42.5)); cone = bpy.context.object
cone.rotation_euler.x = math.pi; cone.name = NAME+"_Underside"; rm = bpy.data.materials.new("M_BB_Rock"); rm.diffuse_color = (0.30,0.24,0.20,1)
rm.use_nodes = True; rm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.30,0.24,0.20,1); cone.data.materials.append(rm); BASE.append(cone)
for c in cone.users_collection: c.objects.unlink(cone)
root.objects.link(cone)
# catalog
names = sorted(f[:-4] for f in os.listdir(GLB) if f.endswith(".glb") and not f.endswith("_LOD1.glb"))   # LOD1s are not separate models
def pick(rx, n): return [x for x in names if re.match(rx, x) and "_Harvested" not in x and "_Depleted" not in x][:n]
proto = {}
def load(an):
    if an in proto: return proto[an]
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, an+".glb"))
    objs = [o for o in bpy.data.objects if o not in before]
    for o in objs:
        for c in list(o.users_collection): c.objects.unlink(o)
    proto[an] = [o for o in objs if o.parent is None and o.type in ("MESH","EMPTY")] or objs; proto[an+"__all"] = objs
    return proto[an]
placed = []; LAYOUT = []   # BASE = terrain/water/pier objects -> Prop_Island_BlenderBoss_Base.glb
def put(an, x, y, s=1.0, rot=None, zoff=0.0, tag=""):
    z = h(x, y) + zoff
    for src in load(an):
        o = src.copy(); o.location = (x, y, z); o.rotation_euler.z = random.uniform(0, 6.283) if rot is None else rot
        o.scale = (s, s, s); root.objects.link(o); o["catalog"] = an; o["zone"] = tag
        for ch in src.children_recursive:
            c2 = ch.copy(); c2.parent = o; root.objects.link(c2)
    placed.append((an, tag)); LAYOUT.append({"asset": an, "x": round(x, 2), "y": round(y, 2), "z": round(z, 2), "yaw": round(math.degrees(o.rotation_euler.z), 1), "scale": round(s, 3), "zone": tag})
def scatter(pool, n, cx, cy, rad, tag, s=(0.9, 1.3)):
    for k in range(n):
        ang, rr = random.uniform(0, 6.283), rad*math.sqrt(random.random())
        x, y = cx+rr*math.cos(ang), cy+rr*math.sin(ang)
        if math.hypot(x, y) < R*0.93 and h(x,y) > 1.5: put(pool[k % len(pool)], x, y, random.uniform(*s), tag=tag)
trees = pick(r"Prop_Tree_.*_Mature", 20) or pick(r"Prop_Tree_", 20)
herbs = pick(r"Prop_Herb_", 40); blooms = pick(r"Prop_Bloom_", 30)
ores = pick(r"Prop_OreNode_.*_Large", 10) + pick(r"Prop_OreNode_.*_Small", 10)
stations = [x for x in names if re.search(r"Smelter|Forge|Cook|Anvil|Bench|Kiln|Loom|Furnace|Mill|Still", x) and not x.startswith(("Item_", "Mob_", "Prop_BBIsle_", "Prop_Decor_"))][:12]
mobs = pick(r"Mob_(Meadow|Forest)_(Grazer|Hopper|Crawler)", 18); crew = [c for c in pick(r"Mob_Crew_", 12) if c != "Mob_Crew_Cook"]
rocks = pick(r"Prop_Island_(Boulder|Driftwood|Tidepool)", 30); chests = pick(r"Prop_Chest_", 6)
scatter(trees, 140, 35, -25, 70, "orchard-forest", (1.0, 1.6))
scatter(trees, 60, -20, 60, 40, "north-grove", (1.0, 1.5))
for k, hb in enumerate(herbs*3):                                   # spiral herb garden, the Boss's signature
    t = k*0.55; rr = 6 + t*1.1
    if rr < 34: put(hb, -55+rr*math.cos(t)*0.6, -40+rr*math.sin(t)*0.6, 1.2, tag="herb-spiral")
scatter(blooms, 70, -55, -40, 30, "bloom-meadow")
scatter(ores, 40, -35, 30, 26, "quarry-hill", (1.0, 1.8))
for k, st in enumerate(stations):                                  # crafting plaza ring
    t = k/max(1, len(stations))*6.283; put(st, 10+14*math.cos(t), 5+14*math.sin(t), 1.0, rot=t+math.pi, tag="crafting-plaza")
for k, c in enumerate(chests): put(c, 10+4*math.cos(k), 5+4*math.sin(k), 1.0, tag="crafting-plaza")
scatter(mobs, 40, 55, 45, 22, "livestock-pen")
for k, c in enumerate(crew): put(c, 10+7*math.cos(k*0.52), 5+7*math.sin(k*0.52), 1.0, rot=k*0.52+math.pi, tag="crew-npc")
if "Mob_Crew_Cook" in names and "Prop_CookingPot_Lit" in names:   # the cook works the plaza pot
    put("Prop_CookingPot_Lit", 2, -4, 1.2, tag="crafting-plaza"); put("Mob_Crew_Cook", 3.2, -4, 1.0, rot=math.pi/2, tag="crew-npc")
bbi = [x for x in names if x.startswith("Prop_BBIsle_")]   # island-only unique models, zoned with spacing (no clutter)
ZONE = {"farm": (("Beehive", "Trough", "Coop", "Scarecrow", "Planter", "Windmill", "Fence"), (55, 45), 8, 42),
        "village": (("Bench", "Table", "Shelf", "Barrel", "Crate", "Cart", "Well", "Tent", "Sign", "Lamp", "Banner", "Bell"), (10, 5), 18, 55),
        "monument": (("Statue", "Arch", "Obelisk", "Totem", "Sundial", "Bridge"), (0, 0), 60, 100)}
taken = [(o.location.x, o.location.y) for o in root.objects if "catalog" in o]
rng = random.Random(500)
for an in bbi:
    fam = an.split("_")[2]; z = next((v for v in ZONE.values() if fam in v[0]), ZONE["village"]); (cx, cy), r0, r1 = z[1], z[2], z[3]
    gap = 6.0 if fam in ("Windmill", "Arch", "Bridge", "Tent", "Obelisk") else 3.5
    for tries in range(200):
        ang = rng.uniform(0, 6.283); rr = rng.uniform(r0, r1); x, y = cx+rr*math.cos(ang), cy+rr*math.sin(ang)
        if math.hypot(x, y) < R*0.88 and h(x, y) > 1.5 and all((x-p)**2+(y-q)**2 > gap*gap for p, q in taken): break
        if tries == 199: gap *= 0.8
    taken.append((x, y)); put(an, x, y, 1.0, rot=math.atan2(cy-y, cx-x) if fam in ("Bench", "Statue", "Arch", "Sign") else None, tag="bbisle-unique")
for k in range(70):                                                # shoreline rocks
    t = random.uniform(0, 6.283); rr = R*random.uniform(0.86, 0.95); put(rocks[k % len(rocks)], rr*math.cos(t), rr*math.sin(t), random.uniform(0.8, 2.0), tag="shore")
# ark dock: pier east + moored ark
wood = bpy.data.materials.new("M_BB_Pier"); wood.diffuse_color = (0.45, 0.30, 0.18, 1)
wood.use_nodes = True; wood.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.45, 0.30, 0.18, 1)
z0 = h(R*0.85, 0) + 0.6
for k in range(14):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(R*0.82+k*2.6, 0, z0)); p = bpy.context.object; p.scale = (2.5, 6, 0.3)
    p.name = "%s_Pier_%02d" % (NAME, k); p.data.materials.append(wood); BASE.append(p)
    for c in p.users_collection: c.objects.unlink(p)
    root.objects.link(p)
for k, dc in enumerate(pick(r"Veh_ArkPart_DockClamp_", 4)): put(dc, R*0.86+k*8, 4.5, 1.2, rot=0, zoff=z0-h(R*0.86+k*8, 4.5), tag="ark-dock")
if "Veh_Ark" in names: put("Veh_Ark", R*0.82+40, -12, 1.0, rot=math.pi/2, zoff=z0+4-h(R*0.82+40, -12), tag="ark-dock")
# ---- water chain: spring + rain catchment -> cistern -> aqueduct/channels -> irrigation (herb spiral, orchard, meadow) + troughs, well, waterwheel
def mat(n, c, emit=0.0, alpha=1.0):
    m = bpy.data.materials.get(n) or bpy.data.materials.new(n); m.use_nodes = True; p = m.node_tree.nodes["Principled BSDF"]
    p.inputs[0].default_value = c; m.diffuse_color = c
    if alpha < 1: p.inputs["Alpha"].default_value = alpha; p.inputs["Roughness"].default_value = 0.05
    if emit: p.inputs["Emission Color"].default_value = c; p.inputs["Emission Strength"].default_value = emit
    return m
MW, MS, MWOOD = mat("M_BB_Water", (0.10, 0.75, 1.0, 1), emit=0.6, alpha=0.9), mat("M_BB_Stone", (0.62, 0.60, 0.56, 1)), mat("M_BB_WaterWood", (0.42, 0.28, 0.16, 1))
def blk(n, size, loc, m, rz=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.scale = size; o.rotation_euler.z = rz; o.name = NAME + "_Water_" + n
    o.data.materials.append(m)
    for c in o.users_collection: c.objects.unlink(o)
    root.objects.link(o); BASE.append(o); return o
def cyl(n, r, d, loc, m, rx=0.0, ry=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=d, location=loc, rotation=(rx, ry, 0)); o = bpy.context.object; o.name = NAME + "_Water_" + n
    o.data.materials.append(m)
    for c in o.users_collection: c.objects.unlink(o)
    root.objects.link(o); BASE.append(o); return o
def run(n, a, b2, w, m, lift=0.4, arches=False):
    """straight channel/aqueduct segment a->b following terrain, water strip inside a stone trough"""
    (ax, ay), (bx, by) = a, b2; L = math.hypot(bx-ax, by-ay); rz = math.atan2(by-ay, bx-ax); seg = max(1, int(L/4))
    for i in range(seg):
        t0 = (i+0.5)/seg; x, y = ax+(bx-ax)*t0, ay+(by-ay)*t0; zt = h(x, y) + lift + (2.5 if arches else 0)
        W = w * 1.6; blk("%s_%02d_bed" % (n, i), (L/seg+0.05, W+0.8, 0.3), (x, y, zt-0.35), MS, rz)                     # deeper: floor sits lower
        for sd in (-1, 1): blk("%s_%02d_wall%d" % (n, i, sd), (L/seg+0.05, 0.4, 0.9), (x - sd*math.sin(rz)*(W/2+0.2), y + sd*math.cos(rz)*(W/2+0.2), zt), MS, rz)
        blk("%s_%02d_w" % (n, i), (L/seg+0.05, W, 0.12), (x, y, zt+0.05), MW, rz)
        if arches and i % 2 == 0: blk("%s_%02d_pier" % (n, i), (0.8, w+0.5, 2.5), (x, y, h(x, y)+lift+1.1), MS, rz)
SPRING, CIST, WELL, WHEEL = (-35, 30), (-12, 8), (16, -10), (30, 20)
z = h(*SPRING); cyl("Spring_Pool", 4.5, 0.6, (SPRING[0], SPRING[1], z+0.2), MS); cyl("Spring_Water", 4.0, 0.15, (SPRING[0], SPRING[1], z+0.5), MW)
for k in range(5): blk("Spring_Rock%d" % k, (1.2, 1.0, 1.5+k*0.3), (SPRING[0]+5*math.cos(k*1.2), SPRING[1]+5*math.sin(k*1.2), z+0.8), MS, k)
cz = h(*CIST); blk("Catchment_Roof", (9, 7, 0.25), (CIST[0], CIST[1]-8, cz+4.2), MWOOD, 0.1)               # rain catchment roof over the plaza edge
for dx in (-4, 4):
    for dy in (-3, 3): blk("Catchment_Post%d%d" % (dx, dy), (0.3, 0.3, 4.2), (CIST[0]+dx, CIST[1]-8+dy, cz+2.1), MWOOD)
blk("Catchment_Gutter", (0.4, 0.4, 3), (CIST[0], CIST[1]-4.5, cz+2.6), MWOOD)
cyl("Cistern", 3.2, 3.0, (CIST[0], CIST[1], cz+1.5), MS); cyl("Cistern_Water", 2.9, 0.1, (CIST[0], CIST[1], cz+2.95), MW)
run("Aqueduct", SPRING, CIST, 0.9, MW, arches=True)                                                     # spring -> cistern on arches
run("Ch_Herb", CIST, (-48, -34), 0.6, MW); run("Ch_HerbRing", (-48, -34), (-62, -46), 0.5, MW)          # herb spiral irrigation
run("Ch_Orchard", CIST, (30, -20), 0.6, MW); run("Ch_Orchard2", (30, -20), (50, -40), 0.5, MW)          # orchard
run("Ch_Meadow", (-48, -34), (-66, -22), 0.5, MW)                                                       # bloom meadow
run("Ch_Pen", CIST, WHEEL, 0.6, MW); run("Ch_Pen2", WHEEL, (52, 40), 0.6, MW)                           # waterwheel -> livestock troughs
for k in range(4):                                                                                       # livestock troughs at the pen
    x, y = 52+6*math.cos(k*1.57), 40+6*math.sin(k*1.57); blk("Trough%d_Box" % k, (2.4, 0.9, 0.6), (x, y, h(x, y)+0.3), MWOOD, k*1.57); blk("Trough%d_W" % k, (2.2, 0.7, 0.1), (x, y, h(x, y)+0.55), MW, k*1.57)
wz = h(*WELL); cyl("Well_Ring", 1.3, 1.0, (WELL[0], WELL[1], wz+0.5), MS); cyl("Well_Water", 1.05, 0.1, (WELL[0], WELL[1], wz+0.8), MW)
for dx in (-1.2, 1.2): blk("Well_Post%d" % dx, (0.2, 0.2, 2.4), (WELL[0]+dx, WELL[1], wz+1.2), MWOOD)
blk("Well_Roof", (3.0, 2.0, 0.2), (WELL[0], WELL[1], wz+2.5), MWOOD); blk("Well_Axle", (2.4, 0.15, 0.15), (WELL[0], WELL[1], wz+2.0), MWOOD)
qz = h(*WHEEL); cyl("Wheel_Hub", 0.4, 1.2, (WHEEL[0], WHEEL[1], qz+3.2), MWOOD, rx=math.pi/2); cyl("Wheel_Rim", 3.0, 0.5, (WHEEL[0], WHEEL[1], qz+3.2), MWOOD, rx=math.pi/2)
for k in range(8): blk("Wheel_Paddle%d" % k, (0.25, 0.9, 2.8), (WHEEL[0]+2.9*math.cos(k*0.785), WHEEL[1], qz+3.2+2.9*math.sin(k*0.785)), MWOOD)
for dx in (-0.8, 0.8): blk("Wheel_Frame%d" % dx, (0.3, 0.3, 3.4), (WHEEL[0], WHEEL[1]+dx, qz+1.7), MS)
blk("Wheel_Race", (8, 1.2, 0.4), (WHEEL[0], WHEEL[1], qz+0.3), MS); blk("Wheel_RaceW", (8, 0.9, 0.1), (WHEEL[0], WHEEL[1], qz+0.55), MW)
# lights/camera/render
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sun.data.energy = 5; sun.rotation_euler = (0.9, 0.2, 2.3); sc.collection.objects.link(sun)
w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.48, 0.90, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (235, -255, 130); cam.data.lens = 35
d = Vector((50, -10, -5)) - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.render.resolution_x, sc.render.resolution_y = 1920, 1080; sc.render.filepath = PNG
sc.view_settings.view_transform = "AgX"
bpy.ops.render.render(write_still=True)
# export: island collection only
for o in bpy.data.objects: o.select_set(False)
for o in root.all_objects: o.select_set(True)
out = os.path.join(GLB, NAME+".glb")
bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_apply=True)
for o in bpy.data.objects: o.select_set(False)
# Base = ONE mesh (multi-material). A multi-node glb imports into Unreal as hundreds of StaticMeshes and the island script
# then found only one stray part (a pier block): "base ok" but no terrain visible. Join copies so the scene/.blend keep parts.
bpy.ops.object.select_all(action="DESELECT"); _dup = []
for o in BASE:
    c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c); c.select_set(True); _dup.append(c)
bpy.context.view_layer.objects.active = _dup[0]; bpy.ops.object.join(); _jb = bpy.context.view_layer.objects.active
_jb.name = _jb.data.name = "Prop_Island_BlenderBoss_Base"; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action="DESELECT"); _jb.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(GLB, "Prop_Island_BlenderBoss_Base.glb"), use_selection=True, export_apply=True)
print("BASE_JOINED", len(BASE), len(_jb.data.polygons), len(_jb.data.materials)); bpy.data.objects.remove(_jb)
json.dump({"island": "BlenderBoss", "origin_cm": [-6000000, 6000000, 0], "radius_m": R, "base_asset": "Prop_Island_BlenderBoss_Base",
           "hero_cam_m": [235, -255, 130], "hero_target_m": [50, -10, -5], "placements": LAYOUT}, open(os.path.join(ART, "flagship", "layout.json"), "w"), indent=0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, "flagship", NAME+".blend"))
from collections import Counter
print(json.dumps({"asset": NAME, "placed": len(placed), "unique": len(set(a for a, _ in placed)), "zones": Counter(t for _, t in placed), "glb": out, "mb": round(os.path.getsize(out)/1e6, 1), "stations": stations}))
