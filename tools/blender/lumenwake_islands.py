"""Author original Lumenwake islands and a four-plot Super Island in Blender.

Blender --background --factory-startup --threads 4 --python lumenwake_islands.py --
    --output artifacts/islands/lumenwake/v01 --build hero --render

Metres, Z up. New standalone authoring scenes; never run in a shared live scene.
No server/chain/Unreal changes. Super Island = four or more distinct connected plots.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import random
import shutil
import sys
import time
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PALETTE = {
    'cream': ('Warm ivory', (.90, .80, .59), .7, 0),
    'wall': ('Lime plaster', (.78, .69, .48), .78, 0),
    'roof': ('Patinated copper', (.085, .34, .30), .35, .28),
    'roof_dark': ('Copper shadow', (.045, .16, .17), .5, .18),
    'wood': ('Warm cedar', (.28, .12, .065), .68, 0),
    'wood_light': ('Honey cedar', (.53, .29, .115), .7, 0),
    'brass': ('Old brass', (.57, .34, .105), .33, .65),
    'glass': ('Blue glass', (.19, .43, .50), .19, .28),
    'glow': ('Lantern amber', (1.0, .47, .095), .35, 0),
    'stone': ('Blue slate', (.19, .25, .27), .9, 0),
    'stone_light': ('Weathered limestone', (.58, .62, .51), .9, 0),
    'leaf_sage': ('Fern sage', (.28, .48, .25), .93, 0),
    'leaf_dark': ('Deep laurel', (.065, .23, .14), .93, 0),
    'leaf_gold': ('Sunlit meadow', (.47, .59, .23), .94, 0),
    'flower_coral': ('Peach blossom', (.93, .41, .25), .8, 0),
    'flower_ivory': ('Moonflower', (.95, .83, .51), .75, 0),
    'flower_lavender': ('Heather lavender', (.55, .39, .69), .84, 0),
    'soil': ('River clay', (.44, .30, .17), .94, 0),
    'water': ('Jewel lagoon', (.035, .38, .43), .18, .08),
    'foam': ('Soft water foam', (.65, .84, .76), .5, 0),
    'sand': ('Golden limestone shore', (.68, .56, .32), .95, 0),
    'path': ('Warm flagstone', (.70, .58, .39), .9, 0),
    'heart': ('Heartstone turquoise', (.16, .81, .67), .35, .16),
    'rock_dark': ('Basalt shadow', (.11, .155, .17), .94, 0),
}
MATS = {}
ACTIVE = None
OBJECTS = []


def material(key):
    label, rgb, roughness, metal = PALETTE[key]
    mat = bpy.data.materials.new('LW_' + label.replace(' ', '_'))
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metal
    if key in ('glow', 'heart'):
        shader.inputs['Emission Color'].default_value = (*rgb, 1)
        shader.inputs['Emission Strength'].default_value = 1.7 if key == 'glow' else 1.0
    if key == 'water':
        shader.inputs['IOR'].default_value = 1.333
        shader.inputs['Transmission Weight'].default_value = .12
    if key == 'glass':
        shader.inputs['Coat Weight'].default_value = .45
    return mat


def new_collection(name, parent=None):
    collection = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(collection)
    return collection


def install(obj, mat):
    if not obj.name.startswith(('Bld_', 'Prop_', 'Veh_', 'Mob_', 'Item_', 'Tool_', 'Wpn_', 'Sky_')):
        obj.name = ('Bld_' if 'Architecture' in ACTIVE.name else 'Prop_') + obj.name
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    ACTIVE.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    obj['creator'] = 'Buckwild Sol / original Lumenwake art'
    OBJECTS.append(obj)
    return obj


def mesh(name, verts, faces, mat):
    data = bpy.data.meshes.new(name + '_Mesh')
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    return install(obj, mat)


def box(name, loc, scale, mat, bevel=.15):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new('Crafted_edges', 'BEVEL')
        mod.width = min(bevel, min(scale) * .23)
        mod.segments = 2
        mod.affect = 'EDGES'
        normal = obj.modifiers.new('Corner_normals', 'WEIGHTED_NORMAL')
        normal.keep_sharp = True
    return install(obj, mat)


def sphere(name, loc, scale, mat, segments=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return install(obj, mat)


def cylinder(name, loc, radius, depth, mat, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    if radius > .1:
        mod = obj.modifiers.new('Edge_catchlight', 'BEVEL')
        mod.width = min(.08, radius * .08, depth * .15)
        mod.segments = 2
        obj.modifiers.new('Corner_normals', 'WEIGHTED_NORMAL')
    return install(obj, mat)


def beam(name, a, b, radius, mat, vertices=10):
    start, end = Vector(a), Vector(b)
    delta = end - start
    obj = cylinder(name, (start + end) / 2, radius, delta.length, mat, vertices)
    obj.rotation_euler = delta.to_track_quat('Z', 'Y').to_euler()
    return obj


def curve(name, points, radius, mat):
    data = bpy.data.curves.new(name + '_Curve', 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 2
    data.bevel_depth = radius
    data.bevel_resolution = 2
    spline = data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for p, xyz in zip(spline.points, points):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    return install(obj, mat)


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def api():
    return dict(box=box, sphere=sphere, cylinder=cylinder, beam=beam, curve=curve, mesh=mesh, materials=MATS)


def smooth(t):
    t = min(1., max(0., t))
    return t * t * (3 - 2 * t)


def segment_distance(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0., min(1., ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def terrain_function(variant):
    if variant == 'hero':
        river = [(-15, -12), (-43, -20), (-54, -43), (-63, -70), (-65, -111)]
        spring = [(-20, 24), (-24, 13), (-15, -12)]
    else:
        river = [(-118, -12), (-73, -12), (-45, -1), (-15, -12), (25, -15), (65, -12), (118, -12)]
        spring = [(-36, 43), (-25, 21), (-15, -12)]
    channels = river + []
    def height(x, y):
        pond = math.sqrt(((x + 15) / 27) ** 2 + ((y + 12) / 19) ** 2)
        hill = (23 if variant == 'hero' else 13) * math.exp(-((x + 35) / 37) ** 2 - ((y - 50) / 39) ** 2)
        hill += 4 * math.exp(-((x - 72) / 35) ** 2 - ((y - 56) / 38) ** 2)
        # Leave a gentle littoral shelf instead of a steep hill right at the water.
        hill *= smooth((pond - 1.22) / .75)
        subtle = .45 * math.sin(x / 17) * math.sin(y / 23)
        h = 10 + hill + subtle
        # The landmark and three residences stand on authored, level terraces.
        for px, py, r, z in [(-24, 46, 14, 25 if variant == 'hero' else 20), (35, -42, 10, 10.5), (58, -30, 10, 10.5), (45, -62, 10, 10.5)]:
            d = math.hypot(x - px, y - py)
            blend = 1 - smooth((d - r) / 5)
            h = h * (1 - blend) + z * blend
        for axis in ('x', 'y'):
            cross, along = (abs(y), abs(x)) if axis == 'x' else (abs(x), abs(y))
            blend = (1 - smooth((cross - 5) / 4)) * smooth((along - 57) / 8)
            h = h * (1 - blend) + 10 * blend
        basin = 1 - smooth((pond - .86) / .34)
        distance = min(segment_distance(x, y, a, b) for poly in (river, spring) for a, b in zip(poly, poly[1:]))
        channel = 1 - smooth((distance - 2.2) / 8.0)
        low = max(basin, channel)
        result = h * (1 - low) + 4.3 * low
        # A level waterfront terrace, with all channels left open beneath bridges.
        ring = math.sqrt(((x + 15) / 38) ** 2 + ((y + 12) / 30) ** 2)
        terrace = 1 - smooth((abs(ring - 1) * 30 - 2.4) / 4.5)
        terrace *= smooth((distance - 3.2) / 2.8)
        result = result * (1 - terrace) + 10.05 * terrace
        return result
    return height, river, spring


def inside(x, y):
    return (x / 116) ** 4 + (y / 116) ** 4 <= 1


def clipped_water(triangle, level=7.25):
    polygon = list(triangle)
    result = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        ain, bin = a[2] <= level, b[2] <= level
        if ain:
            result.append((a[0], a[1], level))
        if ain != bin:
            t = (level - a[2]) / (b[2] - a[2])
            result.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, level))
    return result


def build_ground(height, variant):
    verts, faces, lookup = [], [], {}
    step = 1
    for iy, y in enumerate(range(-116, 117, step)):
        for ix, x in enumerate(range(-116, 117, step)):
            if inside(x, y):
                lookup[ix, iy] = len(verts)
                verts.append((x, y, height(x, y)))
    for ix in range(232 // step):
        for iy in range(232 // step):
            ids = [(ix, iy), (ix + 1, iy), (ix + 1, iy + 1), (ix, iy + 1)]
            if all(p in lookup for p in ids):
                a, b, c, d = (lookup[p] for p in ids)
                faces.extend(((a, b, c), (a, c, d)))
    top = mesh('Bld_LW_' + variant.title() + '_LivingTerrain', verts, faces, MATS['leaf_sage'])
    top.data.materials.append(MATS['leaf_gold'])
    top.data.materials.append(MATS['sand'])
    terrain_mat = MATS['leaf_sage'].copy(); terrain_mat.name = 'LW_Continuous_Vertex_Colored_Shore'
    colors = top.data.color_attributes.new(name='LW_terrain_color', type='FLOAT_COLOR', domain='POINT')
    color_node = terrain_mat.node_tree.nodes.new('ShaderNodeVertexColor'); color_node.layer_name = 'LW_terrain_color'
    terrain_mat.node_tree.links.new(color_node.outputs['Color'], terrain_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    top.data.materials[0] = terrain_mat
    for i, (x, y, z) in enumerate(verts):
        shore = 1 - smooth((z - 7.3) / 2.8)
        sunlight = .22 * smooth((x - 25) / 80) + .12 * smooth((-y - 35) / 70)
        grass = tuple(PALETTE['leaf_sage'][1][k] * (1 - sunlight) + PALETTE['leaf_gold'][1][k] * sunlight for k in range(3))
        rgb = tuple(grass[k] * (1 - shore) + PALETTE['sand'][1][k] * shore for k in range(3))
        colors.data[i].color = (*rgb, 1)
    for face in top.data.polygons: face.use_smooth = True
    # Close the authored perimeter over the two-metre grid's stair-stepped edge.
    rim_verts, rim_faces = [], []
    for factor in (.955, 1.0):
        for i in range(96):
            a = i * math.tau / 96
            c, s = math.cos(a), math.sin(a)
            r = 116 / (abs(c) ** 4 + abs(s) ** 4) ** .25
            x, y = factor * r * c, factor * r * s
            rim_verts.append((x, y, height(x, y) + .035))
    for i in range(96):
        j = (i + 1) % 96
        rim_faces.append((i, 96 + i, 96 + j, j))
    mesh('Bld_LW_' + variant.title() + '_MossyCliffCrest', rim_verts, rim_faces, MATS['leaf_sage'])
    shell_verts, shell_faces, shell_slots = [], [], []
    n = 96
    for layer, (factor, depth) in enumerate([(1., 0), (.985, -6), (.90, -19), (.77, -34), (.45, -46)]):
        for i in range(n):
            angle = i * math.tau / n
            c, s = math.cos(angle), math.sin(angle)
            r = 116 / (abs(c) ** 4 + abs(s) ** 4) ** .25
            x, y = r * c, r * s
            z = height(x, y) if layer == 0 else depth + 2 * math.sin(i * 1.7 + layer)
            shell_verts.append((x * factor, y * factor, z))
    shell_verts.append((-5, 0, -57))
    for layer in range(4):
        for i in range(n):
            j = (i + 1) % n
            shell_faces.append((layer * n + i, (layer + 1) * n + i, (layer + 1) * n + j, layer * n + j))
            shell_slots.append((layer + i // 7) % 3)
    for i in range(n):
        shell_faces.append((4 * n + i, 5 * n, 4 * n + (i + 1) % n)); shell_slots.append(2)
    shell = mesh('Bld_LW_' + variant.title() + '_ShatteredStrata', shell_verts, shell_faces, MATS['stone'])
    shell.data.materials.append(MATS['stone_light']); shell.data.materials.append(MATS['rock_dark'])
    for face, slot in zip(shell.data.polygons, shell_slots): face.material_index = slot
    water_verts, water_faces = [], []
    for face in faces:
        clipped = clipped_water([verts[k] for k in face])
        if len(clipped) >= 3:
            start = len(water_verts); water_verts.extend(clipped); water_faces.append(tuple(range(start, len(water_verts))))
    mesh('Prop_LW_' + variant.title() + '_ConnectedWater', water_verts, water_faces, MATS['water'])
    # Planted heartstone and strata fissures show the fragment's depth and history.
    for i, (x, y, z, h) in enumerate([(-6, -89, -29, 17), (-18, -91, -26, 9), (7, -85, -31, 11)]):
        c = cylinder(f'Prop_LW_Heartstone_{i}', (x, y, z), h * .16, h, MATS['heart'], 6)
        c.rotation_euler[1] = .2 - i * .18
    return top


def ribbon(name, points, width, height, mat):
    fitted = []
    for a, b in zip(points, points[1:]):
        count = max(1, math.ceil(math.hypot(b[0]-a[0], b[1]-a[1]) / .8))
        fitted.extend((a[0]+(b[0]-a[0])*i/count, a[1]+(b[1]-a[1])*i/count) for i in range(count))
    fitted.append(points[-1]); points = fitted
    verts, faces = [], []
    for i, (x, y) in enumerate(points):
        before, after = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = max(.001, math.hypot(dx, dy))
        for side in (-1, 1):
            xx, yy = x - dy / length * width / 2 * side, y + dx / length * width / 2 * side
            verts.append((xx, yy, height(xx, yy) + .075))
        if i: faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    return mesh(name, verts, faces, mat)


def terrain_paths(height, variant):
    points = [(-15 + 38 * math.cos(i * math.tau / 96), -12 + 30 * math.sin(i * math.tau / 96)) for i in range(97)]
    terrace = ribbon('Prop_LW_Lagoon_Promenade', points, 3.2, lambda x, y: 10.24, MATS['path'])
    solid = terrace.modifiers.new('Continuous_waterfront_terrace', 'SOLIDIFY'); solid.thickness = .22
    # Stream channels remain open under the deck, with fitted piers at real wet crossings.
    for i, (x, y) in enumerate(points[:-1]):
        if i % 3 or height(x, y) >= 9.5: continue
        ground = height(x, y) - .2
        cylinder('Prop_LW_Promenade_Stream_Pier', (x, y, (ground + 10.1) / 2), .23, 10.1 - ground, MATS['stone_light'], 12)
    for i, points in enumerate([
        [(15, -35), (22, -40), (35, -42), (44, -38), (58, -30)],
        [(35, -42), (36, -51), (45, -62)],
        [(-17, 19), (-18, 28), (-24, 39), (-24, 46)],
        [(-52, -8), (-65, -9), (-80, -3), (-91, 4)],
    ]):
        # The observatory ascent is the architecture team's supported stair, not a second folded overlay.
        if variant == 'hero' and i == 2: continue
        ribbon(f'Prop_LW_Story_Path_{i}', points, 2.8, height, MATS['path'])
    # Hand-set stepping stones and grounded route lanterns.
    for i in range(12):
        a = .35 + i * .30
        x, y = -15 + 41 * math.cos(a), -12 + 33 * math.sin(a)
        if height(x, y) > 8.5:
            z = height(x, y)
            cylinder(f'Prop_LW_PathLight_Post_{i}', (x, y, z + .9), .12, 1.8, MATS['brass'], 8)
            box(f'Prop_LW_PathLight_Glass_{i}', (x, y, z + 1.85), (.6, .6, .65), MATS['glow'], .10)
            box(f'Prop_LW_PathLight_Hat_{i}', (x, y, z + 2.23), (.8, .8, .12), MATS['roof'], .03)


def waterfall(height, variant):
    if variant != 'hero': return
    verts, faces = [], []
    for j in range(33):
        t = j / 32
        x, y, z = -65 + .8 * math.sin(t * 4), -111 - 4 * t - 3 * t * t, 7.25 - 58 * t
        for k in range(9):
            side = k / 8 - .5
            verts.append((x + side * (5.2 - 2.5 * t), y + .32 * math.sin(t * 28 + k * .7), z + .15 * math.sin(k * 1.3 + t * 31)))
        if j:
            for k in range(8): faces.append(((j - 1) * 9 + k, j * 9 + k, j * 9 + k + 1, (j - 1) * 9 + k + 1))
    fall = mesh('Prop_LW_Willowfall_ShapedFlow', verts, faces, MATS['water'])
    for polygon in fall.data.polygons: polygon.use_smooth = True
    for i in range(5):
        points = []
        for j in range(24):
            t = j / 23
            points.append((-66.7 + .8 * i + .7 * math.sin(t * 4), -111.5 - 4 * t - 3 * t * t, 7.34 - 54 * t))
        curve(f'Prop_LW_Waterfall_SilkenFoam_{i}', points, .055 + i * .01, MATS['foam'])
    for i in range(14):
        a = i * 2.399
        sphere(f'Prop_LW_Willowfall_Mist_{i}', (-65 + 3 * math.sin(a), -118 + 2 * math.cos(a), -48 - (i % 3)), (1.6, 1.3, .7), MATS['foam'], 12, 6)


def hero_landscape_details(height):
    # A visible geology backdrop, with planted ledges and a restrained ancient ruin.
    rng = random.Random(510147)
    for index, (x, y, width, depth, rise) in enumerate([
        (-66, 70, 25, 19, 9), (-50, 78, 19, 14, 12), (-73, 54, 17, 18, 6),
        (-30, 85, 19, 12, 7), (77, 49, 16, 11, 4), (88, 33, 10, 9, 3),
    ]):
        z = height(x, y)
        for level in range(3):
            w, d = width * (1 - level * .15), depth * (1 - level * .13)
            h = rise / 3
            shape = []
            for zz in (z + level*h, z + (level+1)*h):
                for k in range(9):
                    a = k * math.tau / 9
                    rr = 1 + .10 * math.sin(k * 2.7 + index)
                    shape.append((x + level*.8 + w*.5*rr*math.cos(a), y-level*.6+d*.5*rr*math.sin(a), zz))
            faces = [tuple(range(8,-1,-1)), tuple(range(9,18))] + [(k,(k+1)%9,(k+1)%9+9,k+9) for k in range(9)]
            mesh(f'Prop_LW_Ridge_{index}_Strata_{level}', shape, faces, MATS['stone'] if level%2==0 else MATS['stone_light'])
        cap = [(x+1.6+width*.36*math.cos(k*math.tau/9), y-1.2+depth*.36*math.sin(k*math.tau/9),z+rise+.06) for k in range(9)]
        mesh(f'Prop_LW_Ridge_{index}_MossCap', cap, [tuple(range(9))], MATS['leaf_dark'])
    # Close-up river stones vary in size and remain fitted into the actual bank.
    for i in range(28):
        t = i / 27
        x, y = -50 - 15 * t + (5 if i % 2 else -5), -24 - 72 * t
        z = height(x, y)
        if z < 7.5: continue
        size = rng.uniform(.65, 2.0)
        rock = box(f'Prop_LW_Riverbank_Stone_{i}', (x, y, z + size * .22), (size * 1.4, size, size * .7),
                   MATS['stone_light'] if i % 4 == 0 else MATS['stone'], size * .18)
        rock.rotation_euler[2] = rng.uniform(-.6, .6)
    # Deliberately bounded meadow ribbons: folded blades, not random flower dots.
    verts, faces = [], []
    for cx, cy, r, count in [(-88, -48, 12, 160), (77, -58, 13, 140), (-76, 21, 9, 100),
                             (54, 76, 10, 100), (70, 18, 12, 110), (4, -79, 8, 80)]:
        for _ in range(count):
            a, radius = rng.random() * math.tau, math.sqrt(rng.random()) * r
            x, y = cx + radius * math.cos(a), cy + radius * math.sin(a)
            z = height(x, y)
            if z < 8.3: continue
            h, w = rng.uniform(.22, .8), rng.uniform(.05, .13)
            for angle in (a, a + 2.1, a + 4.2):
                dx, dy = math.cos(angle), math.sin(angle)
                start = len(verts)
                verts += [(x - dy*w, y + dx*w, z+.015), (x+dy*w, y-dx*w, z+.015),
                          (x+dx*h*.20+dy*w*.6, y+dy*h*.20-dx*w*.6, z+h*.6),
                          (x+dx*h*.20-dy*w*.6, y+dy*h*.20+dx*w*.6, z+h*.6),
                          (x+dx*h*.43, y+dy*h*.43, z+h)]
                faces += [(start, start+1, start+2, start+3), (start+3, start+2, start+4)]
    mesh('Prop_LW_Authored_Meadow_Grass', verts, faces, MATS['leaf_dark'])
    # A pair of tiny original static scale figures. They are staged props, not rigged NPCs.
    for i, (x, y) in enumerate([(28, -42), (-42, -48)]):
        z = height(x, y)
        box(f'Prop_LW_Visitor_{i}_BootL', (x-.15, y, z+.15), (.22, .38, .3), MATS['wood'], .04)
        box(f'Prop_LW_Visitor_{i}_BootR', (x+.15, y, z+.15), (.22, .38, .3), MATS['wood'], .04)
        box(f'Prop_LW_Visitor_{i}_Coat', (x, y, z+.82), (.58, .36, 1.03), MATS['roof'], .14)
        sphere(f'Prop_LW_Visitor_{i}_Head', (x, y, z+1.57), (.30, .27, .31), MATS['cream'], 12, 6)
        cylinder(f'Prop_LW_Visitor_{i}_Hat', (x, y, z+1.86), .49, .10, MATS['wood_light'], 16)
        box(f'Prop_LW_Visitor_{i}_Satchel', (x+.34, y, z+.70), (.26, .22, .43), MATS['brass'], .05)


def water_details(height):
    for i in range(18):
        a = i * 2.399
        x, y = -15 + (8 + i % 4 * 4) * math.cos(a), -12 + (7 + i % 3 * 3) * math.sin(a)
        if height(x, y) > 6.8: continue
        points = [(x + 1.3 * math.cos(j * math.pi / 14), y + .38 * math.sin(j * math.pi / 14), 7.32) for j in range(15)]
        curve(f'Prop_LW_Lagoon_WindRipple_{i}', points, .035, MATS['foam'])
    # Boardwalk by the water, with non-intersecting discrete planks and visible joinery.
    for i in range(22):
        x, y = 7 + i * .65, -18
        box(f'Prop_LW_Lagoon_Pier_Plank_{i}', (x, y, 8.15), (.61, 4, .22), MATS['wood_light'], .04)
    for x in (8, 14, 20):
        for y in (-19.5, -16.5):
            cylinder('Prop_LW_Lagoon_Pier_Post', (x, y, 6.0), .25, 5, MATS['wood'], 10)
    for x in (9, 19):
        box('Prop_LW_Lagoon_Seat', (x, -18.5, 8.8), (2.6, .65, .23), MATS['wood'], .06)
    # A small lotus cluster, modeled petals rather than coloured terrain dots.
    for i in range(5):
        x, y = -27 + i * 2.7, -23 + (i % 2) * 1.2
        if height(x, y) > 6.9: continue
        cylinder('Prop_LW_Lotus_Pad', (x, y, 7.3), .82, .075, MATS['leaf_dark'], 12)
        for j in range(7):
            a = j * math.tau / 7
            petal = sphere('Prop_LW_Lotus_Petal', (x + .24 * math.cos(a), y + .24 * math.sin(a), 7.53), (.33, .13, .13), MATS['flower_ivory'], 10, 5)
            petal.rotation_euler[2] = a


def sockets(height):
    positions = {'E': (120, 0), 'W': (-120, 0), 'N': (0, 120), 'S': (0, -120)}
    for side, (x, y) in positions.items():
        alongx = side in ('E', 'W')
        sign = 1 if side in ('E', 'N') else -1
        centre = (110 * sign, 0, 9.65) if alongx else (0, 110 * sign, 9.65)
        box(f'Prop_LW_Socket_{side}_StoneCollar', centre, (20, 11, .65) if alongx else (11, 20, .65), MATS['stone_light'], .12)
        for j in range(20):
            a = (100.5 + j) * sign
            loc = (a, 0, 10.025) if alongx else (0, a, 10.025)
            box(f'Prop_LW_Socket_{side}_Deck_{j}', loc, (.95, 8, .08) if alongx else (8, .95, .08), MATS['wood_light'], .018)
        for offset in (-4.7, 4.7):
            a = (100 * sign, offset, 11.15) if alongx else (offset, 100 * sign, 11.15)
            b = (119.6 * sign, offset, 11.15) if alongx else (offset, 119.6 * sign, 11.15)
            beam(f'Prop_LW_Socket_{side}_Handrail', a, b, .10, MATS['brass'])
            for u in (101, 110, 119):
                loc = (u * sign, offset, 10.6) if alongx else (offset, u * sign, 10.6)
                cylinder(f'Prop_LW_Socket_{side}_RailPost', loc, .09, 1.2, MATS['brass'], 8)
        marker = bpy.data.objects.new('Socket_' + side, None)
        marker.empty_display_type = 'ARROWS'; marker.empty_display_size = 4
        marker.location = (x, y, 10)
        ACTIVE.objects.link(marker)
        marker['socket_side'] = side; marker['clear_width_m'] = 8; marker['walkway_datum_m'] = 10
        marker['template_identity_only'] = True
    return [{'side': s, 'position': [*xy, 10], 'clearWidth': 8} for s, xy in positions.items()]


def tugship(x=-75, y=-56, z=24):
    # An original small tow ark, complete claw, keel, cabin, lift envelope and rigging.
    before = set(bpy.context.scene.objects)
    box('Veh_LW_TugArk_Deck', (x, y, z), (15, 5.2, .5), MATS['wood_light'], .22)
    sphere('Veh_LW_TugArk_Hull', (x, y, z - 1.3), (8.4, 2.8, 2.1), MATS['wood'], 24, 8)
    for i in range(9):
        xx = x - 6 + i * 1.5
        points = [(xx, y - 2.8 * math.cos(j * math.pi / 12), z - 2.7 * math.sin(j * math.pi / 12)) for j in range(13)]
        curve('Veh_LW_TugArk_Hull_Rib', points, .09, MATS['brass'])
    box('Veh_LW_TugArk_Cabin', (x + 2.5, y, z + 1.8), (4.4, 3.9, 3.2), MATS['cream'], .22)
    box('Veh_LW_TugArk_Cabin_Roof', (x + 2.5, y, z + 3.6), (5.1, 4.6, .45), MATS['roof'], .18)
    box('Veh_LW_TugArk_Windscreen', (x + .21, y, z + 2.0), (.09, 2.6, 1.35), MATS['glass'], .02)
    envelope = sphere('Veh_LW_TugArk_Lift_Envelope', (x, y, z + 10), (12.5, 4.8, 4.3), MATS['cream'], 32, 12)
    for offset in (-4, 0, 4):
        points = [(x + offset, y + 4.82 * math.cos(j * math.tau / 48), z + 10 + 4.32 * math.sin(j * math.tau / 48)) for j in range(49)]
        curve('Veh_LW_TugArk_Envelope_Band', points, .055, MATS['brass'])
    for xx in (x - 4, x + 5):
        for yy in (y - 2, y + 2):
            beam('Veh_LW_TugArk_Lift_Rig', (xx, yy, z + .3), (xx, yy * 0 + y + (yy-y) * 1.6, z + 9), .08, MATS['wood'])
    cylinder('Veh_LW_TugArk_Tow_Winch', (x - 4, y, z + 1.2), .9, 1.7, MATS['brass'], 16)
    beam('Veh_LW_TugArk_Tow_Boom', (x - 5, y, z + 1), (x - 11, y, z - 1), .25, MATS['roof_dark'])
    for sign in (-1, 1):
        points = [(x - 10, y + sign * .6, z - 1), (x - 12, y + sign * 1.6, z - 1.8), (x - 13.2, y + sign * .5, z - 2.2)]
        curve('Veh_LW_TugArk_Grapple_Claw', points, .22, MATS['brass'])
    curve('Veh_LW_TugArk_MooringLine', [(x - 10, y, z - 1), (x - 17, y, z - 2), (x - 22, y + 2, 12)], .10, MATS['wood'])
    for obj in set(bpy.context.scene.objects) - before: obj['asset_role'] = 'tug_ark_visual'


def connections(parent, layout):
    global ACTIVE
    ACTIVE = new_collection('LW_SuperIsland_ConnectionKit', parent)
    edges = [(item['start'], item['end'], f"Link_{i}_{item['plots'][0]}_{item['plots'][1]}")
             for i, item in enumerate(layout['connectors'])]
    records = []
    for a, b, label in edges:
        dx, dy = b[0] - a[0], b[1] - a[1]
        horizontal = bool(dx)
        for i in range(32):
            t = (i + .5) / 32
            loc = (a[0] + dx * t, a[1] + dy * t, 10.025)
            box('Prop_LW_Join_' + label + '_Board', loc, (.48, 8, .08) if horizontal else (8, .48, .08), MATS['wood_light'], .015)
        for off in (-4.5, 4.5):
            aa = (a[0], a[1] + off, 11.2) if horizontal else (a[0] + off, a[1], 11.2)
            bb = (b[0], b[1] + off, 11.2) if horizontal else (b[0] + off, b[1], 11.2)
            beam('Prop_LW_Join_' + label + '_Rail', aa, bb, .11, MATS['brass'])
            beam('Prop_LW_Join_' + label + '_Outer_Rail_Sill', (aa[0], aa[1], 9.87), (bb[0], bb[1], 9.87), .18, MATS['roof_dark'])
            for i in range(5):
                t = i / 4
                loc = (a[0] + dx * t, a[1] + dy * t + off, 10.6) if horizontal else (a[0] + dx * t + off, a[1] + dy * t, 10.6)
                cylinder('Prop_LW_Join_' + label + '_Post', loc, .1, 1.2, MATS['brass'], 8)
                inner = (loc[0], a[1] + off * 3.8 / 4.5, 9.87) if horizontal else (a[0] + off * 3.8 / 4.5, loc[1], 9.87)
                beam('Prop_LW_Join_' + label + '_Post_Outrigger', inner, (loc[0], loc[1], 9.87), .14, MATS['roof_dark'])
        # A visible tension truss below the deck and fixed sockets at both ends.
        for off in (-3.8, 3.8):
            aa = (a[0], a[1] + off, 9.2) if horizontal else (a[0] + off, a[1], 9.2)
            bb = (b[0], b[1] + off, 9.2) if horizontal else (b[0] + off, b[1], 9.2)
            beam('Prop_LW_Join_' + label + '_UnderBeam', aa, bb, .18, MATS['roof_dark'])
            mid = ((a[0]+b[0])/2, (a[1]+b[1])/2, 7.8)
            beam('Prop_LW_Join_' + label + '_TensionA', aa, mid, .10, MATS['brass'])
            beam('Prop_LW_Join_' + label + '_TensionB', mid, bb, .10, MATS['brass'])
        records.append({'name': label, 'start': list(a), 'end': list(b), 'lengthM': 16, 'clearWidthM': 8})
    return records


def camera(name, location, target, ortho=None, lens=40):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.lens = lens; data.clip_end = 4000
    if ortho: data.type = 'ORTHO'; data.ortho_scale = ortho
    bpy.context.scene.camera = obj
    return obj


def lighting(dusk=False):
    scene = bpy.context.scene
    world = bpy.data.worlds.new('LW_Storybook_Sky')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = ((.24, .36, .49, 1) if dusk else (.52, .69, .78, 1))
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35 if dusk else .55
    scene.world = world
    for obj in list(scene.objects):
        if obj.type == 'LIGHT': bpy.data.objects.remove(obj, do_unlink=True)
    for name, loc, energy, color, size in [
        ('LW_Sunbox', (-150, -180, 240), 130000 if dusk else 280000, (1, .64, .34) if dusk else (1, .88, .68), 140),
        ('LW_Skylight', (70, 100, 230), 180000 if dusk else 220000, (.36, .58, 1) if dusk else (.61, .80, 1), 160),
        ('LW_Rim', (-40, 200, 90), 90000, (.50, .88, .81), 120),
    ]:
        data = bpy.data.lights.new(name, 'AREA'); data.energy = energy; data.color = color; data.shape = 'DISK'; data.size = size
        obj = bpy.data.objects.new(name, data); scene.collection.objects.link(obj); obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 10)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data = bpy.data.lights.new('LW_Sun', 'SUN'); data.energy = .9 if dusk else 1.5; data.angle = .22
    data.color = (1, .60, .30) if dusk else (1, .89, .72)
    obj = bpy.data.objects.new('LW_Sun', data); scene.collection.objects.link(obj); obj.rotation_euler = (math.radians(27), math.radians(-20), math.radians(-34))


def scene_setup():
    global ACTIVE, OBJECTS, MATS
    bpy.ops.wm.read_factory_settings(use_empty=True)
    OBJECTS = []; MATS = {key: material(key) for key in PALETTE}
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'; scene.cycles.samples = 48; scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5; scene.cycles.transparent_max_bounces = 4
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 4
    scene.render.resolution_x = 1400; scene.render.resolution_y = 1050; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.film_transparent = False
    scene.use_nodes = True
    nodes = scene.node_tree.nodes; nodes.clear()
    layers = nodes.new('CompositorNodeRLayers'); glare = nodes.new('CompositorNodeGlare'); glare.glare_type = 'FOG_GLOW'; glare.threshold = 3.8; glare.quality = 'MEDIUM'; glare.mix = -.92
    composite = nodes.new('CompositorNodeComposite'); scene.node_tree.links.new(layers.outputs['Image'], glare.inputs['Image']); scene.node_tree.links.new(glare.outputs['Image'], composite.inputs['Image'])
    lighting()


def build_island(variant='hero', plot='DEMO-A'):
    global ACTIVE
    parent = new_collection('LW_LumenwakeSanctuary' if variant == 'hero' else 'LW_RiverjoinCommons')
    parent['authoring_plot_id'] = plot; parent['identity_is_demo_only'] = True; parent['module_envelope_m'] = 240
    height, river, spring = terrain_function(variant)
    ACTIVE = new_collection('LW_' + variant + '_Terrain', parent); build_ground(height, variant)
    ACTIVE = new_collection('LW_' + variant + '_Water', parent); waterfall(height, variant); water_details(height)
    if variant == 'hero':
        ACTIVE = new_collection('LW_Hero_RidgesAndMeadows', parent); hero_landscape_details(height)
    ACTIVE = new_collection('LW_' + variant + '_Routes', parent); terrain_paths(height, variant)
    ACTIVE = new_collection('LW_' + variant + '_Architecture', parent)
    architecture = load_module('lumenwake_architecture').build_architecture(api(), height, variant=variant)
    ACTIVE = new_collection('LW_' + variant + '_Foliage', parent)
    exclusions = [(-15, -12, 31), (-24, 46, 17), (35, -42, 9), (58, -30, 9), (45, -62, 9)]
    foliage = load_module('lumenwake_foliage').build_foliage(api(), height, variant=variant, exclusions=exclusions)
    ACTIVE = new_collection('LW_' + variant + '_Sockets', parent); socket_records = sockets(height)
    ACTIVE = new_collection('LW_' + variant + '_TugArk', parent); tugship()
    anchor_position = (-97, -54, 12)
    anchor_ground = height(anchor_position[0], anchor_position[1]) - .2
    cylinder('Prop_LW_TowAnchor_Grounded_Pedestal', (-97, -54, (anchor_ground + 11.75) / 2), .5, 11.75 - anchor_ground, MATS['stone_light'], 12)
    curve('Prop_LW_TowAnchor_Brass_Eye', [(-97, -54 + .65 * math.cos(i * math.tau / 32), 12 + .65 * math.sin(i * math.tau / 32)) for i in range(33)], .12, MATS['brass'])
    anchor = bpy.data.objects.new('TowAnchor_' + plot.replace('-', '_'), None)
    anchor.location = anchor_position; anchor.empty_display_type = 'ARROWS'; anchor.empty_display_size = 2
    ACTIVE.objects.link(anchor)
    anchor['tow_anchor'] = True; anchor['authoring_plot_id'] = plot; anchor['approach_direction_local'] = [-1, 0, 0]
    anchor['visual_pose_only'] = True
    plot_root = bpy.data.objects.new('PlotRoot_' + plot.replace('-', '_'), None)
    plot_root.empty_display_type = 'CUBE'; plot_root.empty_display_size = 2
    parent.objects.link(plot_root)
    plot_root['is_plot_root'] = True; plot_root['authoring_plot_id'] = plot
    plot_root['deed_identity_is_demo_only'] = True
    for obj in list(parent.all_objects):
        if obj != plot_root and obj.parent is None:
            obj.parent = plot_root
    bpy.context.scene['name'] = 'Lumenwake Sanctuary' if variant == 'hero' else 'Riverjoin Commons'
    bpy.context.scene['visual_bar_source'] = 'VISUAL-QUALITY-BAR.md / 2026-10-14'
    bpy.context.scene['delivery_stage'] = 'Blender authored; native gameplay and chain unchanged'
    return parent, height, {'plot': plot, 'variant': variant, 'sockets': socket_records,
                            'towAnchor': {'positionM': list(anchor_position), 'approachDirection': [-1, 0, 0], 'visualPoseOnly': True},
                            'architecture': {k: v for k, v in architecture.items() if k != 'objects'},
                            'foliage': {k: v for k, v in foliage.items() if k != 'objects'}}


def save_scene(path):
    # Preserve sources with modifiers. Export bakes the same authored modifiers.
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)


def export_scene(path, collections):
    bpy.ops.object.select_all(action='DESELECT')
    # Bake the export copy after saving editable curve/modifier sources.
    curves = [obj for collection in collections for obj in collection.all_objects if obj.type == 'CURVE']
    for obj in curves: obj.select_set(True)
    if curves:
        bpy.context.view_layer.objects.active = curves[0]
        bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT')
    for collection in collections:
        for obj in collection.all_objects:
            if obj.type in ('MESH', 'CURVE') or obj.get('is_plot_root') or obj.get('socket_side') or obj.get('tow_anchor'):
                obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_extras=True, export_cameras=False, export_lights=False)


def render_view(path, location, target, ortho=None, dusk=False, resolution=None, lens=40):
    scene = bpy.context.scene
    if resolution: scene.render.resolution_x, scene.render.resolution_y = resolution
    lighting(dusk); cam = camera('LW_RenderCamera', location, target, ortho, lens=lens)
    scene.render.filepath = str(path)
    start = time.monotonic(); bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    return {'file': path.name, 'renderSeconds': round(time.monotonic() - start, 3), 'lighting': 'dusk' if dusk else 'day'}


def file_record(path):
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def scene_metrics(collections):
    graph = bpy.context.evaluated_depsgraph_get()
    rows, total = [], 0
    for collection in collections:
        for obj in collection.all_objects:
            if obj.type not in ('MESH', 'CURVE'): continue
            evaluated = obj.evaluated_get(graph)
            data = evaluated.to_mesh()
            if not data: continue
            data.calc_loop_triangles(); triangles = len(data.loop_triangles); total += triangles
            rows.append({'name': obj.name, 'triangles': triangles, 'materialSlots': len(data.materials)})
            evaluated.to_mesh_clear()
    return {'objects': len(rows), 'triangles': total, 'maximumMaterialSlotsPerObject': max((r['materialSlots'] for r in rows), default=0),
            'largestMeshes': sorted(rows, key=lambda r: r['triangles'], reverse=True)[:10], 'basis': 'Evaluated Blender authoring geometry; not a native frame profile.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--build', choices=['hero', 'template', 'super'], default='hero')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--plots', type=int, default=4, help='Distinct authoring members in a Super Island, minimum four.')
    parser.add_argument('--columns', type=int, default=2)
    parser.add_argument('--preview', action='store_true', help='Use 24-sample 1120x840 preview views.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    snapshots = output / 'recipe-source'; snapshots.mkdir(exist_ok=True)
    source_records = []
    for name in ('lumenwake_islands.py', 'lumenwake_architecture.py', 'lumenwake_foliage.py', 'super_island_layout.py'):
        src, dst = ROOT / name, snapshots / name
        if dst.exists() and hashlib.sha256(dst.read_bytes()).digest() != hashlib.sha256(src.read_bytes()).digest():
            raise RuntimeError('Recipe changed between stages; use a fresh version directory.')
        if not dst.exists(): shutil.copyfile(src, dst)
        source_records.append(file_record(dst))
    start = time.monotonic(); scene_setup(); views = []
    if args.preview: bpy.context.scene.cycles.samples = 24
    if args.build in ('hero', 'template'):
        variant = args.build; title = 'Lumenwake_Sanctuary' if variant == 'hero' else 'Riverjoin_Commons'
        source = output / (title + '.blend')
        if source.exists(): raise RuntimeError('Retain existing source; use a fresh version directory.')
        parent, height, metadata = build_island(variant, 'DEMO-A' if variant == 'hero' else 'DEMO-B')
        camera('LW_HeroCamera', (260, -335, 265), (-2, 0, 0), 370)
        save_scene(source); export = output / (title + '.glb'); export_scene(export, [parent])
        metadata['geometry'] = scene_metrics([parent])
        if args.render:
            size = (1120, 840) if args.preview else (1800, 1350)
            views.append(render_view(output / (title + '_day.png'), (260, -335, 265), (-2, 0, 0), 370, resolution=size))
            if not args.preview:
                views.append(render_view(output / (title + '_dusk.png'), (245, -315, 210), (-2, 0, 3), 370, dusk=True, resolution=size))
                px, py = (10, -42) if variant == 'hero' else (18, -42)
                views.append(render_view(output / (title + '_player.png'), (px, py, height(px, py) + 1.7), (-22, 42, 28), resolution=(1600, 1000), lens=30))
                views.append(render_view(output / (title + '_detail.png'), (17, -78, 47), (43, -39, 15), resolution=(1600, 1000), lens=45))
                if variant == 'template':
                    views.append(render_view(output / (title + '_plan.png'), (0, 0, 400), (0, 0, 10), 270, resolution=(1400, 1400)))
        metadata.update(name=title, source=file_record(source), export=file_record(export))
    else:
        title = 'Lumenwake_Super_Island'
        source = output / (title + '.blend')
        if source.exists(): raise RuntimeError('Retain existing source; use a fresh version directory.')
        member_ids = ['DEMO-' + (chr(65 + i) if i < 26 else str(i + 1)) for i in range(args.plots)]
        layout = load_module('super_island_layout').layout_plots(member_ids, columns=args.columns)
        paths = [(item['plot'], output / ('Lumenwake_Sanctuary.blend' if i == 0 else 'Riverjoin_Commons.blend'), item['position'])
                 for i, item in enumerate(layout['plots'])]
        root = new_collection('LW_SuperIsland_FourDistinctPlots'); plots = []
        for plot, path, offset in paths:
            with bpy.data.libraries.load(str(path), link=False) as (src, dst):
                expected = 'LW_LumenwakeSanctuary' if plot == 'DEMO-A' else 'LW_RiverjoinCommons'
                dst.collections = [expected]
            collection = dst.collections[0]; root.children.link(collection)
            collection.name = 'LW_Plot_' + plot.replace('-', '_'); collection['authoring_plot_id'] = plot
            rotation = 0 if plot in ('DEMO-A', 'DEMO-B') else (member_ids.index(plot) - 1) % 4 * 90
            for obj in collection.all_objects:
                if obj.parent is None:
                    obj.location += Vector(offset)
                    obj.rotation_euler[2] += math.radians(rotation)
                obj['plot_id'] = plot
                if obj.get('is_plot_root'):
                    obj['source_archetype_plot'] = obj.get('authoring_plot_id', '')
                    obj['authoring_plot_id'] = plot
                    obj.name = 'PlotRoot_' + plot.replace('-', '_')
                if obj.get('tow_anchor'):
                    obj['authoring_plot_id'] = plot
                    obj.name = 'TowAnchor_' + plot.replace('-', '_')
                if obj.get('socket_side'):
                    cardinal = ['E', 'N', 'W', 'S']
                    obj['socket_world_side'] = cardinal[(cardinal.index(obj['socket_side']) + rotation // 90) % 4]
                # Variants use an authored roof/leaf material tint, preserving shape and IDs.
                if plot in ('DEMO-C', 'DEMO-D') and obj.type == 'MESH':
                    for slot in obj.material_slots:
                        if slot.material and 'Patinated_copper' in slot.material.name:
                            replacement = MATS['roof_dark'] if plot == 'DEMO-C' else MATS['brass']
                            slot.link = 'OBJECT'; slot.material = replacement
            plots.append({'authoringPlotId': plot, 'source': path.name, 'inputSource': file_record(path),
                          'positionM': list(offset), 'rotationDegrees': rotation, 'ownership': 'demo only'})
        bridge_records = connections(root, layout)
        metadata = {'name': title, 'superIslandMinimumPlots': 4, 'distinctPlots': plots, 'connectors': bridge_records,
                    'plotIdentitiesRemainSeparate': True, 'nativeAuthority': 'not changed', 'authoringLayout': layout}
        frame_size = max(layout['bounds']['landEnvelopeSize']) * 1.48
        camera('LW_SuperCamera', (650, -790, 620), (0, 0, -3), frame_size)
        save_scene(source); export = output / (title + '.glb'); export_scene(export, [root])
        metadata['geometry'] = scene_metrics([root])
        if args.render:
            views.append(render_view(output / (title + '_day.png'), (650, -790, 620), (0, 0, -3), frame_size, resolution=(1800, 1350)))
            views.append(render_view(output / (title + '_connections.png'), (0, -455, 600), (0, 0, 0), frame_size * .92, resolution=(1600, 1200)))
            views.append(render_view(output / (title + '_joint_detail.png'), (18, -173, 32), (0, -128, 10), resolution=(1600, 1000)))
        metadata.update(source=file_record(source), export=file_record(export))
    metadata.update(schemaVersion=1, units='metres', plotEnvelopeM=240, plotCentrePitchM=256,
                    nativeImported=False, deployed=False, testsRun=False, views=views,
                    blenderVersion=bpy.app.version_string, sourceSnapshots=source_records,
                    elapsedBuildAndRenderSeconds=round(time.monotonic() - start, 3))
    for view in views: view.update(file_record(output / view['file']))
    manifest = output / (title + '_manifest.json')
    manifest.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print('LUMENWAKE_DELIVERY ' + json.dumps({'manifest': str(manifest), 'source': str(source), 'views': len(views), 'elapsed': metadata['elapsedBuildAndRenderSeconds']}), flush=True)


if __name__ == '__main__': main()
