"""Blender background single-asset repair; distinct output required, originals never overwritten.
Use --python-exit-code 1 so a Python exception fails the host job.
"""
import hashlib
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from static_uv import ensure_static_uv

source, output = map(Path, sys.argv[sys.argv.index('--')+1:])
if source.resolve() == output.resolve() or output.exists():
    raise ValueError('Use a distinct new output file')
original = source.read_bytes()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if len(meshes) != 1 or any(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects):
    raise ValueError('Repair expects exactly one static mesh, no armature')
obj = meshes[0]
def geometry(mesh):
    mesh.calc_loop_triangles()
    return sorted(tuple(sorted(tuple(round(v, 6) for v in mesh.vertices[index].co)
                              for index in tri.vertices)) for tri in mesh.loop_triangles)
before = geometry(obj.data)
changed = ensure_static_uv(obj)
if geometry(obj.data) != before:
    raise ValueError('UV repair changed geometry')
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True,
                          export_animations=False, export_tangents=True)
# Reimport exported bytes to prove the delivered mesh still has valid UVs/tangents and geometry.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(output))
mesh = next(obj.data for obj in bpy.context.scene.objects if obj.type == 'MESH')
if geometry(mesh) != before or not mesh.uv_layers:
    raise ValueError('Delivered mesh geometry/UV check failed')
mesh.calc_tangents()
import math
if not all(math.isfinite(v) for loop in mesh.loops for v in loop.tangent):
    raise ValueError('Non-finite tangent')
if any(loop.tangent.length < .99 for loop in mesh.loops):
    raise ValueError('Degenerate tangent')
if source.read_bytes() != original:
    raise ValueError('Original asset changed')
report = dict(source=str(source), source_sha256=hashlib.sha256(original).hexdigest(),
              output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), repaired_missing_uv=changed,
              triangles=len(mesh.loop_triangles), geometry_preserved=True, finite_unit_tangents=True,
              original_preserved=True, unreal_reimport_verified=False)
output.with_suffix('.repair.json').write_text(json.dumps(report, indent=2)+'\n')
print('STATIC_UV_REPAIR_PASS', json.dumps(report))
