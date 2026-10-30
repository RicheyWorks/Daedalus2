"""Run with Blender --background --factory-startup --python-exit-code 1 --python this_file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from static_uv import ensure_static_uv

mesh = bpy.data.meshes.new('missing UV regression')
mesh.from_pydata([(0,0,0),(2,0,0),(2,2,.5),(0,2,.5)], [], [(0,1,2,3)])
mesh.update()
obj = bpy.data.objects.new('UV regression', mesh)
bpy.context.collection.objects.link(obj)
try:
    mesh.calc_tangents()
except RuntimeError:
    pass
else:
    raise AssertionError('Missing UV baseline unexpectedly computed tangents')
positions = [tuple(vertex.co) for vertex in mesh.vertices]
assert ensure_static_uv(obj)
uv = [tuple(loop.uv) for loop in mesh.uv_layers.active.data]
assert not ensure_static_uv(obj)
assert uv == [tuple(loop.uv) for loop in mesh.uv_layers.active.data]
assert positions == [tuple(vertex.co) for vertex in mesh.vertices]
assert all(loop.tangent.length > .99 for loop in mesh.loops)
empty = bpy.data.objects.new('not a mesh', None)
try:
    ensure_static_uv(empty)
except ValueError:
    pass
else:
    raise AssertionError('Nonmesh accepted')
print('STATIC_UV_REGRESSION_PASS baseline refusal, repair, geometry, tangents, idempotence, nonmesh refusal')
