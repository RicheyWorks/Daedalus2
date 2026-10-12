"""Headless, isolated Blender builder: 20 archetypes x 25 explicit variants.

blender --background --factory-startup --python build_sol_art.py -- OUTPUT
Does not contact either connector, alter the open Blender scene or import into Unreal.
"""
import bpy
import json
import math
import pathlib
import sys
import time

OUT = pathlib.Path(sys.argv[sys.argv.index('--') + 1])
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'manifest.json').exists():
    raise RuntimeError('Existing completed build: use a fresh output directory')
START = time.perf_counter()
ARCHETYPES = ['SpringBowl', 'FilterTower', 'Cistern', 'Trough', 'RainCatcher', 'Wellhead',
              'Dawnleaf', 'Rillprism', 'Cinderbud', 'Stillmoss', 'Stridefern', 'Clearbell',
              'RingMortar', 'Hen', 'Goat', 'GrainBundle', 'EggBasket', 'MilkJug',
              'CustardBowl', 'PortalArch']
PALETTE = [(0.11,.32,.48,1), (.40,.75,.90,1), (.19,.42,.24,1), (.82,.62,.29,1),
           (.61,.27,.18,1), (.83,.78,.57,1), (.61,.40,.75,1)]
MATS = []
for i, color in enumerate(PALETTE):
    m = bpy.data.materials.new('SOL_Palette_' + str(i)); m.use_nodes = True
    m.diffuse_color = color
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = color
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .85
    MATS.append(m)
for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
VERTICES, FACES, COLORS = [], [], []

def box(x, y, z, sx, sy, sz, color):
    start = len(VERTICES)
    VERTICES.extend((x+dx*sx/2, y+dy*sy/2, z+dz*sz/2) for dx,dy,dz in
                    [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                     (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
    FACES.extend(tuple(start+i for i in f) for f in
                 [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    COLORS.extend([color]*6)

def basin(width, depth, height, water=True):
    box(0,0,.05,width,depth,.1,0)
    for x in (-width/2+.05,width/2-.05): box(x,0,height/2,.1,depth,height,0)
    for y in (-depth/2+.05,depth/2-.05): box(0,y,height/2,width,.1,height,0)
    if water: box(0,0,height*.6,width-.2,depth-.2,.04,1)

def shape(archetype, variant):
    s = .85 + (variant % 5)*.075
    h = .8 + (variant // 5)*.1
    if archetype in ('SpringBowl','Trough','RainCatcher','CustardBowl','RingMortar'):
        w,d,z = {'SpringBowl':(2,2,.5),'Trough':(2,.8,.55),
                 'RainCatcher':(1.8,1.8,1),'CustardBowl':(.35,.35,.18),
                 'RingMortar':(.6,.6,.4)}[archetype]
        basin(w*s,d*s,z*h, archetype not in ('RingMortar','CustardBowl'))
        if archetype == 'CustardBowl': box(0,0,.12*h,.22*s,.22*s,.04,3)
        if archetype == 'RingMortar':
            for x,y in ((-.12,0),(0,.12),(.12,0)): box(x,y,.2,.06,.06,.1,2)
    elif archetype in ('Cistern','FilterTower','Wellhead','MilkJug'):
        w,z = {'Cistern':(2,2),'FilterTower':(.8,2),'Wellhead':(1.3,.8),'MilkJug':(.25,.4)}[archetype]
        basin(w*s,w*s,z*h,True)
        if archetype == 'FilterTower':
            for i in range(3): box(0,0,(.35+i*.5)*h,.65*s,.65*s,.15,3 if i%2 else 0)
        if archetype == 'Wellhead':
            for x in (-.7,.7): box(x*s,0,1.1,.1,.1,2.2,3)
            box(0,0,2.2,1.6*s,.7,.1,3)
        if archetype == 'MilkJug': box(0,0,.4*h,.15*s,.15*s,.08,5)
    elif archetype in ARCHETYPES[6:12]:
        c = 2 if archetype in ('Stillmoss','Stridefern') else 3 if archetype=='Dawnleaf' else 1 if archetype=='Rillprism' else 4 if archetype=='Cinderbud' else 6
        box(0,0,.2*h,.045,.045,.4*h,2)
        for i in range(3+variant%3):
            a = i*math.tau/(3+variant%3)
            # Each fictional species has its own silhouette, beyond its colour.
            dimensions = {'Dawnleaf':(.14,.08,.045),'Rillprism':(.045,.045,.18),
                          'Cinderbud':(.09,.09,.09),'Stillmoss':(.18,.16,.025),
                          'Stridefern':(.24,.035,.025),'Clearbell':(.07,.07,.14)}[archetype]
            box(.12*s*math.cos(a),.12*s*math.sin(a),.12+i*.055,
                dimensions[0]*s,dimensions[1]*s,dimensions[2],c)
        box(0,0,.42*h,.13*s,.13*s,.1,c)
    elif archetype in ('Hen','Goat'):
        q = .5 if archetype=='Hen' else 1
        for x in (-.2,.2):
            for y in (-.3,.3): box(x*q*s,y*q*s,.18*q,.08*q,.08*q,.36*q,4)
        box(0,0,.5*q,.6*q*s,.8*q*s,.4*q*h,5)
        box(0,-.5*q*s,.78*q,.3*q,.3*q,.3*q,5)
        box(0,-.69*q*s,.78*q,.11*q,.15*q,.09*q,3)  # unmistakable -Y front
        if archetype=='Goat':
            for x in (-.1,.1): box(x,-.5*s,.99,.055,.07,.18,4)
        else: box(0,-.5*q*s,.96*q,.06,.16*q,.07,4)
    elif archetype=='PortalArch':
        for x in (-1.5,1.5): box(x*s,0,1.7*h,.5*s,.6,3.4*h,6)
        box(0,0,3.4*h,3.5*s,.6,.4,6)
        for x in (-1,0,1): box(x*s,-.32,3.4*h,.18,.06,.18,1)
    elif archetype=='GrainBundle':
        for i in range(5): box((i-2)*.065*s,0,.3*h,.055,.055,.6*h,3)
        box(0,0,.2,.4*s,.09,.06,4)
    elif archetype=='EggBasket':
        basin(.5*s,.4*s,.2,False)
        for x in (-.12,.12): box(x,0,.23,.1,.15,.16,5)
    else: raise ValueError(archetype)

rows = []
for archetype in ARCHETYPES:
    for variant in range(25):
        VERTICES.clear(); FACES.clear(); COLORS.clear()
        shape(archetype, variant)
        kind = 'Mob' if archetype in ('Hen','Goat') else 'Item' if archetype in ('EggBasket','MilkJug','CustardBowl','GrainBundle') else 'Prop'
        name = f'{kind}_SOL_{archetype}_{variant+1:02}'
        mesh = bpy.data.meshes.new(name); mesh.from_pydata(VERTICES,[],FACES); mesh.update()
        colors = sorted(set(COLORS))
        for color in colors: mesh.materials.append(MATS[color])
        for poly,color in zip(mesh.polygons,COLORS): poly.material_index = colors.index(color)
        # Stand on z=0, centred in x/y; geometry is applied, object transforms remain identity.
        low = min(v.co.z for v in mesh.vertices)
        for v in mesh.vertices: v.co.z -= low
        obj = bpy.data.objects.new(name,mesh)
        collection = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(collection)
        collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
        dest = OUT / kind; dest.mkdir(exist_ok=True)
        glb = dest / (name+'.glb'); blend = dest / (name+'.blend')
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True)
        # Include the scene: the watcher opens the .blend, then selects scene-visible objects.
        bpy.data.libraries.write(str(blend),{bpy.context.scene})
        mesh.calc_loop_triangles()
        rows.append({'asset':name,'archetype':archetype,'variant':variant+1,'kind':kind,
                     'triangles':len(mesh.loop_triangles),'materials':len(colors),
                     'dimensions_m':list(obj.dimensions),'glb':str(glb),'blend':str(blend),
                     'objects':[name], 'status':'BLENDER_EXPORTED_NOT_IMPORTED'})
        bpy.data.objects.remove(obj,do_unlink=True); bpy.data.collections.remove(collection)
        bpy.data.meshes.remove(mesh)
    print('SOL_FINISHED', archetype, len(rows), flush=True)
report = {'schema':'daedalus.sol.art/v1','count':len(rows),'archetypes':20,'variants_each':25,
          'build_seconds':time.perf_counter()-START,'origin_cm':[2000000,0,0],
          'diameter_m':240,'unreal_count':0,'assets':rows}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('SOL_BUILD_COMPLETE',len(rows),report['build_seconds'],flush=True)
