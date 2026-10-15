"""LOCAL source-backed UE5.8 sketch; importing this file performs no native work.

The sole operator must first reflect the listed methods/docs in the current
editor, preserve the current baseline, and provide its existing durable intent
writer. No import, actor/map edit, save, test, plugin enablement or cleanup runs
automatically. Asset creation is intentionally separate from disk saving.
UV0 is explicitly supplied, box-projected and checked before StaticMesh creation;
this surface UV channel is independent of optional lightmap UV generation.
"""
import math
import re

ENGINE = 'C:/Program Files/Epic Games/UE_5.8/Engine/'
GS = ENGINE + 'Plugins/Runtime/GeometryScripting/Source/'
OWNED_ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Native/GalleryCity/'

# Source ScriptName + reflected UFUNCTION snake_case names. Main should capture
# actual __doc__ strings, struct properties and Python return tuple order once.
REFLECTION_CHECKLIST = {
    'GeometryScriptSimpleMeshBuffers': {
        'properties': ['vertices', 'triangles', 'normals', 'uv0', 'vertex_colors', 'tri_group_ids'],
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshBasicEditFunctions.h:21-58'},
    'GeometryScript_MeshEdits.append_buffers_to_mesh': {
        'cpp': 'UDynamicMesh* (TargetMesh, const Buffers&, NewTriangleIndicesList&, MaterialID=0, bDeferChangeNotifications=false, Debug=nullptr)',
        'python_inputs': ['target_mesh', 'buffers', 'material_id=0', 'defer_change_notifications=False'],
        'expected_python_outputs': ['DynamicMesh return', 'GeometryScriptIndexList out'],
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshBasicEditFunctions.h:425-436'},
    'GeometryScript_Normals.set_per_face_normals': {
        'cpp': 'UDynamicMesh* (TargetMesh, Debug=nullptr)',
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshNormalsFunctions.h:129-133'},
    'GeometryScript_MeshQueries': {
        'methods': ['get_vertex_count', 'get_is_closed_mesh', 'get_num_open_border_edges', 'get_num_connected_components',
                    'get_mesh_bounding_box', 'get_num_uv_sets', 'get_triangle_u_vs'],
        'triangle_uv_outputs': ['Vector2D UV1', 'Vector2D UV2', 'Vector2D UV3', 'bool have_valid_u_vs'],
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshQueryFunctions.h:43-80,175-179,253-286'},
    'GeometryScript_UVs.set_mesh_u_vs_from_box_projection': {
        'cpp': 'UDynamicMesh* (TargetMesh, UVSetIndex, BoxTransform, Selection, MinIslandTriCount=2, Debug=nullptr)',
        'python_inputs': ['target_mesh', 'uv_set_index', 'box_transform', 'selection', 'min_island_tri_count=2'],
        'selection': 'GeometryScriptMeshSelection() is empty; implementation processes all triangles for an empty selection',
        'warning': 'Requires an existing UV layer. AppendBuffersToMesh resets layer count from full-length buffer UV arrays.',
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshUVFunctions.h:456-464'},
    'Transform': {
        'constructor': 'Transform()',
        'editor_properties': {'rotation': 'Quat', 'translation': 'Vector', 'scale3d': 'Vector'},
        'source': 'Actual UE5.8 Python Transform.__doc__; set translation and scale3d explicitly'},
    'GeometryScriptCreateNewStaticMeshAssetOptions': {
        'properties': ['enable_recompute_normals', 'enable_recompute_tangents', 'enable_nanite',
                       'enable_collision', 'collision_mode', 'use_original_vertex_order'],
        'warning': 'enable_collision defaults TRUE; explicitly set FALSE. Nanite defaults FALSE.',
        'source': GS + 'GeometryScriptingEditor/Public/GeometryScript/CreateNewAssetUtilityFunctions.h:47-79'},
    'GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh': {
        'cpp': 'UStaticMesh* (FromDynamicMesh, AssetPathAndName, Options, Outcome&, Debug=nullptr)',
        'python_inputs': ['from_dynamic_mesh', 'asset_path_and_name', 'options'],
        'expected_python_outputs': ['StaticMesh return', 'GeometryScriptOutcomePins out'],
        'source': GS + 'GeometryScriptingEditor/Public/GeometryScript/CreateNewAssetUtilityFunctions.h:175-182'},
    'GeometryScript_Primitives.append_box': {
        'cpp': 'UDynamicMesh* (TargetMesh, PrimitiveOptions, Transform, DimensionX=100, DimensionY=100, DimensionZ=100, StepsX=0, StepsY=0, StepsZ=0, Origin=Base, Debug=nullptr)',
        'struct': 'GeometryScriptPrimitiveOptions(material_id=0, flip_orientation=False)',
        'enum': 'GeometryScriptPrimitiveOriginMode.CENTER or BASE; pass explicitly',
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshPrimitiveFunctions.h:53-70,157-179'},
    'GeometryScript_MeshTransforms.transform_mesh': {
        'cpp': 'UDynamicMesh* (TargetMesh, Transform, bFixOrientationForNegativeScale=true, Debug=nullptr)',
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshTransformFunctions.h:25-31'},
    'GeometryScript_Materials.set_triangle_material_id': {
        'cpp': 'UDynamicMesh* (TargetMesh, TriangleID, MaterialID, bIsValidTriangle&, bDeferChangeNotifications=false)',
        'source': GS + 'GeometryScriptingCore/Public/GeometryScript/MeshMaterialFunctions.h:142-149'},
    'EditorAssetLibrary.save_loaded_asset': {
        'inputs': ['asset_to_save', 'only_if_is_dirty=False'], 'result': 'bool; explicit separate operator step'},
}


def planter_buffers(width=300.0, depth=160.0, height=80.0, thickness=12.0):
    """Pure data recipe in native centimetres: 16 positions, 14 quads/28 triangles.

    The solid shell is closed while the cavity is visibly open from above.
    Four CCW rings are outer-bottom, outer-top, inner-floor, inner-top.
    No Boolean, separate cube objects, imported payload or .01 scale is used.
    """
    values = (width, depth, height, thickness)
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
            or thickness <= 0 or width <= 2 * thickness or depth <= 2 * thickness or height <= thickness):
        raise ValueError('finite positive dimensions and a nonempty cavity required')
    a, b = width / 2, depth / 2
    c, d = a - thickness, b - thickness
    vertices = []
    for x, y, z in ((a, b, 0.), (a, b, height), (c, d, thickness), (c, d, height)):
        vertices.extend([(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)])
    quads = []
    for i in range(4):
        j = (i + 1) % 4
        quads.extend([(i, j, 4+j, 4+i), (8+i, 12+i, 12+j, 8+j), (4+i, 4+j, 12+j, 12+i)])
    quads.extend([(0, 3, 2, 1), (8, 9, 10, 11)])
    triangles = [tri for a, b, c, d in quads for tri in ((a, b, c), (a, c, d))]
    recipe = {'producer': 'Unreal GeometryScript direct hollow shell v1', 'units': 'native_cm',
              'dimensions_cm': list(values[:3]), 'thickness_cm': thickness,
              'vertices': 16, 'triangles': 28, 'material_id': 0, 'actor_scale': [1., 1., 1.],
              'expected_bounds_cm': {'min': [-width/2, -depth/2, 0.], 'max': [width/2, depth/2, height]}}
    return vertices, triangles, recipe


def _require_complete_uv0(ue, mesh):
    """Fail before persistent creation if UV0 is absent, incomplete or degenerate."""
    queries = ue.GeometryScript_MeshQueries
    channels = int(queries.get_num_uv_sets(mesh))
    if channels < 1:
        raise RuntimeError('UV0 absent; no persistent asset creation admitted')
    minimum_double_area = float('inf')
    for triangle in range(mesh.get_triangle_count()):
        row = queries.get_triangle_u_vs(mesh, 0, triangle)
        if not isinstance(row, tuple) or len(row) != 4 or row[-1] is not True:
            raise RuntimeError('UV0 triangle readback unavailable; no persistent creation admitted')
        points = [(float(uv.x), float(uv.y)) for uv in row[:3]]
        if any(not math.isfinite(value) for point in points for value in point):
            raise RuntimeError('UV0 contains nonfinite coordinates; no persistent creation admitted')
        a, b, c = points
        double_area = abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
        if double_area <= 1e-12:
            raise RuntimeError('UV0 contains a degenerate triangle; no persistent creation admitted')
        minimum_double_area = min(minimum_double_area, double_area)
    return {'channels': channels, 'channel': 0, 'triangles': mesh.get_triangle_count(),
            'all_triangles_valid_finite_nondegenerate': True, 'minimum_double_area': minimum_double_area,
            'method': 'explicit per-vertex UV0 buffer followed by whole-mesh box projection',
            'lightmap_uv_generation': False}


def make_planter_dynamic_mesh(ue, **dimensions):
    """Native transient mesh operation ONLY when explicitly called by operator."""
    vertices, triangles, recipe = planter_buffers(**dimensions)
    buffers = ue.GeometryScriptSimpleMeshBuffers()
    buffers.set_editor_property('vertices', [ue.Vector(*v) for v in vertices])
    buffers.set_editor_property('triangles', [ue.IntVector(*t) for t in triangles])
    width, depth, height = recipe['dimensions_cm']
    # AppendBuffersToMesh.cpp973-999 requires UV0.Num()==Vertices.Num(); an
    # omitted UV0 resets the mesh to zero UV channels. Seed every vertex before
    # append, then replace the seed with per-face box-projected overlay UVs.
    buffers.set_editor_property('uv0', [ue.Vector2D(x/width+.5, y/depth+.5) for x, y, z in vertices])
    mesh = ue.DynamicMesh()
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh, buffers, material_id=0)
    ue.GeometryScript_Normals.set_per_face_normals(mesh)
    projection = ue.Transform()
    projection.set_editor_property('translation', ue.Vector(0., 0., height/2))
    projection.set_editor_property('scale3d', ue.Vector(width, depth, height))
    ue.GeometryScript_UVs.set_mesh_u_vs_from_box_projection(mesh, 0, projection, ue.GeometryScriptMeshSelection(), 2)
    queries = ue.GeometryScript_MeshQueries
    if (queries.get_vertex_count(mesh) != 16 or mesh.get_triangle_count() != 28
            or not queries.get_is_closed_mesh(mesh) or queries.get_num_open_border_edges(mesh) != 0
            or queries.get_num_connected_components(mesh) != 1):
        raise RuntimeError('generated mesh differs; no asset creation admitted')
    recipe['uv0'] = _require_complete_uv0(ue, mesh)
    return mesh, recipe


def create_planter_asset_unsaved(ue, asset_path, owned_material, write_intent, **dimensions):
    """Source sketch; caller owns lease, clean-scene guard and durable journal.

    write_intent must persist/fsync via the existing production journal. On any
    exception preserve the new dirty asset and reconcile; NEVER call again to
    resume. This function never saves, overwrites, places actors or edits a map.
    """
    if (not isinstance(asset_path, str) or not asset_path.startswith(OWNED_ROOT)
            or asset_path.endswith('/') or re.fullmatch(r'/[A-Za-z0-9_/]+', asset_path) is None
            or '//' in asset_path or not callable(write_intent)):
        raise ValueError('fresh legal owned GalleryCity asset path and durable intent writer required')
    name = asset_path.rsplit('/', 1)[1]
    registry = ue.AssetRegistryHelpers.get_asset_registry()
    collisions = [str(row.package_name) for row in registry.get_assets_by_path('/Game', recursive=True)
                  if str(row.asset_name).casefold() == name.casefold()]
    if ue.EditorAssetLibrary.does_asset_exist(asset_path) or collisions:
        raise RuntimeError('asset name/path already exists; no overwrite/replay')
    if (not isinstance(owned_material, ue.MaterialInterface)
            or not owned_material.get_path_name().startswith('/Game/Daedalus/Art/Islands/CodexContest/')):
        raise ValueError('existing owned material required; shared parents remain unchanged')
    mesh, recipe = make_planter_dynamic_mesh(ue, **dimensions)
    options = ue.GeometryScriptCreateNewStaticMeshAssetOptions()
    for key in ('enable_collision', 'enable_nanite', 'enable_recompute_normals', 'enable_recompute_tangents'):
        options.set_editor_property(key, False)
    write_intent({'operation': 'create_new_owned_static_mesh_unsaved', 'path': asset_path, 'recipe': recipe})
    result = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, asset_path, options)
    # Confirm tuple order in the actual reflection snapshot before calling.
    if not isinstance(result, tuple) or len(result) != 2:
        raise RuntimeError('unexpected creation return shape; preserve/reconcile, never replay')
    asset, outcome = result
    if (not isinstance(asset, ue.StaticMesh) or outcome != ue.GeometryScriptOutcomePins.SUCCESS
            or asset.get_path_name() != asset_path + '.' + name):
        raise RuntimeError('new mesh/outcome/path differs; preserve/reconcile, never replay')
    write_intent({'operation': 'bind_existing_owned_material_to_new_mesh_only', 'path': asset.get_path_name(),
                  'material': owned_material.get_path_name()})
    asset.set_material(0, owned_material)
    return asset, recipe


# Operator steps after creation: inspect source+render triangle counts/bounds,
# build-scale1, collision0/NaniteFalse and exact material; add owned provenance
# with a durable metadata intent. THEN write a separate save intent and call
# EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), requiring
# True and retained file/readback receipts. Actor/map operations are outside this
# sketch. create helper cpp uses CreatePackage/NewObject without an absence
# guard and explicitly disables creation undo; therefore caller preservation and
# no-replay discipline are required even though the generated asset is small.
