# SPDX-License-Identifier: MIT
"""Make a mesh's face order deterministic, so its GLB bytes repeat build to build.

Blender 5.2's UV sphere (bmesh.ops.create_uvsphere and bpy.ops.mesh.primitive_uv_sphere_add) emits its faces in a
different order on every run; the exported GLB then hashes differently with identical geometry (see
AUTOMATION-LESSONS, 2026-10-15). Call sort_faces on any mesh built from such a primitive before export:

    import stable_mesh
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    stable_mesh.sort_faces(bpy.context.object)

Faces are ranked by their rounded centroid, then by their rounded vertex positions as a tie-break. Geometry and
vertex order are unchanged; only the face order becomes stable. Verify with repro_check.py.
"""
import bmesh
import bpy


def _key(f):
    c = f.calc_center_median()
    return (tuple(round(v, 5) for v in c), tuple(sorted(tuple(round(v, 5) for v in x.co) for x in f.verts)))


def sort_bmesh(bm):
    order = {f: k for k, f in enumerate(sorted(bm.faces, key=_key))}
    bm.faces.sort(key=lambda f: order[f])
    bm.faces.index_update()
    return bm


def sort_faces(obj_or_mesh):
    me = obj_or_mesh.data if isinstance(obj_or_mesh, bpy.types.Object) else obj_or_mesh
    bm = bmesh.new()
    bm.from_mesh(me)
    sort_bmesh(bm)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return obj_or_mesh
