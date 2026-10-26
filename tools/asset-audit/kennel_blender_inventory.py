# SPDX-License-Identifier: MIT
"""Blender background inventory; reads existing GLBs, writes only to an explicit output directory.
blender --background --factory-startup --python this.py -- --output /absolute/output
Display objects are normalized; report bounds are original imported Blender meters.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    kennel = root / 'tools/islands/kennel-isle'
    book = json.loads((kennel / 'tonics.json').read_text(encoding='utf-8'))
    assets = [(name, kennel / 'glb' / f'Item_Herb_AMF_{name}_Bundle1.glb') for name in sorted(book['herbs'])]
    assets += [('Mend tonic T1', kennel / 'glb/Item_Tonic_AMF_Mend_T1.glb'),
               ('Trough V1', kennel / 'glb/Prop_Water_AMF_Trough_V1.glb')]
    missing = [str(path) for _, path in assets if not path.is_file()]
    if missing:
        raise RuntimeError('Missing source assets: ' + ', '.join(missing))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    records = []
    for index, (label, source) in enumerate(assets):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(source))
        imported = set(bpy.data.objects) - before
        meshes = [obj for obj in imported if obj.type == 'MESH']
        if not meshes:
            raise RuntimeError(f'No mesh: {source}')
        points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
        low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
        high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
        extent = high - low
        if not all(math.isfinite(v) for v in extent) or max(extent) <= 0:
            raise RuntimeError(f'Invalid bounds: {source}')
        triangles = 0
        for obj in meshes:
            obj.data.calc_loop_triangles()
            triangles += len(obj.data.loop_triangles)
        records.append(dict(label=label, source=source.relative_to(root).as_posix(),
                            sha256=hashlib.sha256(source.read_bytes()).hexdigest(), bytes=source.stat().st_size,
                            mesh_objects=len(meshes), triangles=triangles,
                            dimensions_m=[round(v, 6) for v in extent]))
        # Detach first, preserving imported world transforms; never modify or export source files.
        transforms = {obj: obj.matrix_world.copy() for obj in meshes}
        for obj in meshes:
            obj.parent = None
            obj.matrix_world = transforms[obj]
        x, y = (index % 4 - 1.5) * 3.4, (1.5 - index // 4) * 3.5
        scale = 2.1 / max(extent)
        center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
        transform = Matrix.Translation(Vector((x, y, .12))) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-center)
        for obj in meshes:
            obj.matrix_world = transform @ transforms[obj]
        for obj in imported - set(meshes):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.ops.object.text_add(location=(x, y - 1.45, .04))
        text = bpy.context.object
        text.data.body = label
        text.data.align_x = 'CENTER'
        text.data.size = .27
        text.data.extrude = .002
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.03))
    floor = bpy.context.object
    mat = bpy.data.materials.new('Inventory background')
    mat.diffuse_color = (.075, .09, .12, 1)
    floor.data.materials.append(mat)
    bpy.ops.object.camera_add(location=(0, -10, 23))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 16.8
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type='AREA', location=(0, -3, 13))
    bpy.context.object.data.energy = 2400
    bpy.context.object.data.shape = 'DISK'
    bpy.context.object.data.size = 12
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.world.color = (.25, .25, .25)
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output / 'kennel-inventory.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'kennel-inventory.blend'))
    bpy.ops.render.render(write_still=True)
    report = dict(blender=bpy.app.version_string, assets=records, count=len(records),
                  display_normalized=True, unit='imported Blender meters',
                  scope='Geometry/import inventory only; not Unreal material, collision or gameplay proof')
    (output / 'kennel-inventory.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('INVENTORY_OK', len(records), output)


if __name__ == '__main__':
    main()
