# SPDX-License-Identifier: MIT
"""Blender background factory-startup generator; reuses the shipped horse GLB.

Creates 500 static art variants, not implemented NPC behavior. See manifest.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = .48
    return mat


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def build(args):
    started = time.perf_counter()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'glb').mkdir(exist_ok=True)
    source = Path(args.source).resolve()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    parts = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(parts) == 7, 'Expected shipped seven-part Mob_Horse'
    for obj in parts:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
    original_materials = {m.name: m for o in parts for m in o.data.materials}
    horn_mat = next(m for name, m in original_materials.items() if name.endswith('_M1'))
    body_mat = next(m for name, m in original_materials.items() if name.endswith('_M0'))
    # Source horse faces -Y. Horn rooted in the forehead; ears and mane remain subtle.
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=.085, radius2=.004,
                                   depth=.63, location=(0, -.96, 2.565))
    horn = bpy.context.object
    horn.name = 'Unicorn_Horn'
    horn.data.materials.append(horn_mat)
    parts.append(horn)
    for x in (-.135, .135):
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=.07, radius2=.012,
                                       depth=.23, location=(x, -.79, 2.345))
        ear = bpy.context.object
        ear.data.materials.append(body_mat)
        parts.append(ear)
    for i in range(7):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=.14,
                                             location=(0, -.66 + i * .15, 2.20 - i * .035))
        mane = bpy.context.object
        mane.scale = (.62, 1, 1.25)
        mane.data.materials.append(horn_mat)
        parts.append(mane)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    base = bpy.context.object
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    base.rotation_euler.z += math.pi
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    base.name = 'Unicorn_Template'
    palettes = [
        ('Lavender', (.86,.82,.96), (.43,.24,.64)),
        ('Rose', (.98,.84,.88), (.70,.32,.48)),
        ('Mint', (.81,.95,.86), (.23,.52,.44)),
        ('Sky', (.82,.91,.99), (.29,.44,.70)),
        ('Peach', (.99,.89,.78), (.72,.42,.29)),
        ('Pearl', (.96,.95,.89), (.54,.49,.68)),
        ('Lilac', (.92,.83,.98), (.62,.35,.65)),
        ('Seafoam', (.80,.96,.95), (.23,.54,.62)),
        ('Moon', (.81,.85,.96), (.35,.36,.56)),
        ('Dawn', (.99,.93,.78), (.69,.54,.29)),
    ]
    templates = []
    for family, coat, accent in palettes:
        mesh = base.data.copy()
        replacements = [material(f'{family}_Coat', coat),
                        material(f'{family}_ManeHornHooves', accent),
                        material(f'{family}_Eyes', (.045,.035,.065))]
        for i, mat in enumerate(mesh.materials):
            mesh.materials[i] = replacements[int(mat.name.rsplit('_M', 1)[1])]
        templates.append(mesh)
    bpy.data.objects.remove(base, do_unlink=True)
    records = []
    objects = []
    for n in range(500):
        family_index, shape = divmod(n, 50)
        obj = bpy.data.objects.new(f'Mob_Unicorn_{n+1:03}', templates[family_index])
        bpy.context.collection.objects.link(obj)
        # 50 distinct body proportions per palette; origin stays at hoof level.
        obj.scale = (.91 + (shape % 5)*.045,
                     .91 + ((shape // 5) % 5)*.035,
                     .89 + (shape // 25)*.13 + (shape % 5)*.014)
        obj['asset_id'] = obj.name
        obj['role_intent'] = 'friendly_rainbow_guide_and_defender'
        obj['runtime_implemented'] = False
        obj['mountain_alpha'] = n == 487
        obj['burning_bull_response'] = 'stand_ground' if n == 487 else 'flee'
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = out / 'glb' / (obj.name + '.glb')
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB',
                                  use_selection=True, export_extras=True)
        obj.data.calc_loop_triangles()
        records.append(dict(id=obj.name, family=palettes[family_index][0],
                            scale=list(obj.scale), sex='male' if n < 250 and n % 2 == 0 else 'female',
                            mountain_alpha=n == 487,
                            burning_bull_response='stand_ground' if n == 487 else 'flee',
                            glb='glb/'+path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            triangles=len(obj.data.loop_triangles)))
        obj.location = ((n % 25)*3.5, (n // 25)*4.2, 0)
        objects.append(obj)
        if (n+1) % 50 == 0:
            print('UNICORNS_EXPORTED', n+1, flush=True)
    # Half the individuals belong to mixed pairs. Female-only ordinary herds
    # total 238, with a separate 12-member quest herd completing 500.
    groups = [dict(id=f'Pair_{i+1:03}', kind='mixed_pair',
                   members=[records[2*i]['id'], records[2*i+1]['id']]) for i in range(125)]
    cursor = 250
    sizes = [2]*16 + [3]*33 + [4]*18 + [5]*3 + [6]*2 + [8]
    assert sum(sizes) == 238
    for i, size in enumerate(sizes):
        groups.append(dict(id=f'Herd_{i+1:03}', kind='female_herd',
                           members=[r['id'] for r in records[cursor:cursor+size]]))
        cursor += size
    groups.append(dict(id='Quest_Twelve', kind='exceptional_female_quest_herd',
                       members=[r['id'] for r in records[488:500]]))
    members = [member for group in groups for member in group['members']]
    assert len(members) == len(set(members)) == 500
    assert sum(r['sex']=='male' for r in records) == 125
    manifest = dict(schema='daedalus.unicorn-art/v1', count=500,
                    source=str(source), source_sha256=source_hash,
                    units='meters', forward='+Y', origin='ground',
                    status='static_art_exported; NPC integration and animation pending',
                    distribution_basis='50 percent of individuals in male-female pairs; not encounter probability',
                    behavior_intent=['help_player', 'defend_player', 'guide_to_selected_realm_rainbow'],
                    behavior_priority=['ordinary_unicorn_flees_burning_bull',
                                       'mountain_alpha_exempt_from_burning_bull_fear',
                                       'otherwise_defend_player_then_guide'],
                    quest=dict(herd='Quest_Twelve', burning_bulls_driven_to_sea=10,
                               reward='chest of realm-specific strongest legendary items',
                               runtime_implemented=False),
                    assets=records, groups=groups)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.world.color = (.22,.22,.22)
    floor = material('DisplayFloor', (.055,.075,.105))
    bpy.ops.mesh.primitive_plane_add(size=250, location=(42,38,-.035))
    bpy.context.object.data.materials.append(floor)
    bpy.ops.object.light_add(type='SUN', location=(0,0,30))
    bpy.context.object.rotation_euler = (.35,-.45,-.3)
    bpy.context.object.data.energy = 2.4
    bpy.ops.object.camera_add(location=(105,133,120))
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 125
    aim(camera, (42,39,0))
    scene.camera = camera
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 1600
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(out / 'all-500.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'unicorn-guides-500.blend'))
    bpy.ops.render.render(write_still=True)
    # A closer sheet shows one representative of each family, without moving assets.
    for obj in objects:
        obj.hide_render = True
    previews = []
    for i in range(10):
        preview = objects[i*50+24].copy()
        scene.collection.objects.link(preview)
        preview.hide_render = False
        preview.location = ((i % 5)*3.5, (i // 5)*5, 0)
        previews.append(preview)
    camera.location = (19,24,18)
    aim(camera, (7,2.5,1.1))
    camera.data.ortho_scale = 21
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.filepath = str(out / 'palette-preview.png')
    bpy.ops.render.render(write_still=True)
    manifest['generation_seconds'] = round(time.perf_counter()-started, 2)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('UNICORNS_COMPLETE', manifest['count'], manifest['generation_seconds'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    build(parser.parse_args(sys.argv[sys.argv.index('--')+1:]))
