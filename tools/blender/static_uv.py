"""Missing-UV repair for generated static meshes. Leaves an existing UV map untouched."""
def ensure_static_uv(obj):
    import bpy
    if obj.type != 'MESH' or not obj.data.polygons:
        raise ValueError('Expected a nonempty static mesh')
    if obj.data.uv_layers:
        return False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(island_margin=0.02)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    for tri in mesh.loop_triangles:
        a, b, c = [uv[index].uv for index in tri.loops]
        area = abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
        if area <= 1e-10:
            raise ValueError('UV repair left a degenerate triangle')
    mesh.calc_tangents()
    return True
