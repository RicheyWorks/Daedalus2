"""Read-only native proof for the retained Copperfall three-role placement.

The sole operator inserts BODY after the established g.native preflight.  Importing
this module does not contact Unreal or execute BODY.  The body creates transient
DynamicMesh copies only; it never modifies actors, assets, packages or files.
"""

BODY = r'''
ground_expected = [-314900.0, 299550.0, 17615.324]
origin_expected = [-317950.0, 297700.0, 17515.324]
translation_expected = [-316100.0, 299550.0, 17348.324]
terrain_label = 'CodexIsland_summit_rim_84011_HeroR4_island'
terrain_mesh_path = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/4baeb945202507ea41b225c2/CodexIsland_summit_rim_84011_HeroR4_island.CodexIsland_summit_rim_84011_HeroR4_island'
tolerance_cm = 0.02

for key, expected in (('ground_world_cm', ground_expected),
                      ('terrain_origin_cm', origin_expected)):
    value = cfg.get(key)
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in value)
            or any(abs(value[i] - expected[i]) > 0.002 for i in range(3))):
        raise RuntimeError('Exact retained Copperfall ground configuration differs: ' + key)
if cfg.get('terrain_label', terrain_label) != terrain_label:
    raise RuntimeError('Exact retained HeroR4 terrain label required')

actors = sub.get_all_level_actors()
terrain = [actor for actor in actors if actor.get_actor_label() == terrain_label]
if len(terrain) != 1:
    raise RuntimeError('Exactly one saved HeroR4 terrain actor required')
terrain = terrain[0]
position = terrain.get_actor_location()
if (any(abs(getattr(position, key) - origin_expected[i]) > tolerance_cm
        for i, key in enumerate(('x', 'y', 'z')))
        or terrain.get_actor_rotation() != unreal.Rotator()
        or terrain.get_actor_scale3d() != unreal.Vector(1, 1, 1)):
    raise RuntimeError('Saved HeroR4 terrain unit transform differs')
terrain_component = terrain.get_component_by_class(unreal.StaticMeshComponent)
if terrain_component is None or terrain_component.static_mesh is None:
    raise RuntimeError('Saved HeroR4 terrain StaticMeshComponent absent')
terrain_mesh = terrain_component.static_mesh
if terrain_mesh.get_path_name() != terrain_mesh_path:
    raise RuntimeError('Saved HeroR4 terrain mesh binding differs')
terrain_transform = terrain_component.get_world_transform()
for local in ((0, 0, 0), (100, 0, 0), (0, 100, 0), (0, 0, 100)):
    transformed = unreal.MathLibrary.transform_location(
        terrain_transform, unreal.Vector(*local))
    if any(abs(getattr(transformed, key) - origin_expected[i] - local[i])
           > tolerance_cm for i, key in enumerate(('x', 'y', 'z'))):
        raise RuntimeError('Terrain component transform differs from saved unit basis')

geometry_cache = {}
measured_meshes = []

def copied_geometry(mesh):
    key = mesh.get_path_name()
    if key in geometry_cache:
        return geometry_cache[key]
    options = unreal.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('use_build_scale', True)
    copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, unreal.DynamicMesh(), options, unreal.GeometryScriptMeshReadLOD())
    dynamic = copied[0] if isinstance(copied, tuple) else copied
    outcome = str(copied[-1]) if isinstance(copied, tuple) else 'DynamicMesh direct return'
    if isinstance(copied, tuple) and (len(copied) < 2 or 'SUCCESS' not in outcome.upper()):
        raise RuntimeError('Native read-only geometry copy failed: ' + key + ': ' + outcome)
    if not isinstance(dynamic, unreal.DynamicMesh):
        raise RuntimeError('Unsupported native geometry-copy return shape: ' + key)
    count = dynamic.get_triangle_count()
    if count <= 0 or count > 100000:
        raise RuntimeError('Geometry exceeds bounded 1..100000-triangle inspection: '
                           + key + ': ' + str(count))
    geometry_cache[key] = (dynamic, count)
    measured_meshes.append({'mesh': key, 'triangles': count,
                            'copy_outcome': outcome, 'use_build_scale': True})
    return dynamic, count

def triangle_points(dynamic, triangle_index):
    valid, *points = dynamic.get_triangle_positions(triangle_index)
    if (not valid or len(points) != 3
            or any(not math.isfinite(getattr(point, key))
                   for point in points for key in ('x', 'y', 'z'))):
        raise RuntimeError('Native triangle positions incomplete or nonfinite')
    return points

terrain_dynamic, terrain_triangle_count = copied_geometry(terrain_mesh)
if terrain_triangle_count != 82320:
    raise RuntimeError('Exact retained HeroR4 terrain must have 82320 triangles')

# Each unit cell must consist of precisely two complete half-square triangles.
# Their shared edge must be a diagonal; their other vertices lie on opposite
# sides.  This proves the entire 500x500cm patch within the stated tolerance,
# instead of inferring support between a sparse set of sampled points.
cells = {(x, y): [] for x in range(28, 33) for y in range(16, 21)}
for triangle_index in range(terrain_triangle_count):
    points = triangle_points(terrain_dynamic, triangle_index)
    if any(abs(point.z - 100.0) > tolerance_cm for point in points):
        continue
    corners = []
    for point in points:
        gx, gy = round(point.x / 100.0), round(point.y / 100.0)
        if (abs(point.x - gx * 100.0) > tolerance_cm
                or abs(point.y - gy * 100.0) > tolerance_cm):
            break
        corners.append((gx, gy))
    if len(corners) != 3 or len(set(corners)) != 3:
        continue
    x0 = min(corner[0] for corner in corners)
    y0 = min(corner[1] for corner in corners)
    if ((x0, y0) not in cells
            or max(corner[0] for corner in corners) - x0 != 1
            or max(corner[1] for corner in corners) - y0 != 1):
        continue
    twice_area_grid = abs(
        (corners[1][0] - corners[0][0]) * (corners[2][1] - corners[0][1])
        - (corners[1][1] - corners[0][1]) * (corners[2][0] - corners[0][0]))
    if twice_area_grid != 1:
        continue
    cells[x0, y0].append({
        'triangle_index': triangle_index,
        'native_local_vertices_cm': [[point.x, point.y, point.z] for point in points],
        'corners_grid': corners, 'area_cm2': 5000.0})

ground_support = []
for (x0, y0), halves in sorted(cells.items()):
    if len(halves) != 2:
        raise RuntimeError('Ground cell needs exactly two complete flat halves: '
                           + str((x0, y0)) + ': ' + str(len(halves)))
    first = set(tuple(corner) for corner in halves[0]['corners_grid'])
    second = set(tuple(corner) for corner in halves[1]['corners_grid'])
    union = first | second
    shared = first & second
    expected = {(x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)}
    if union != expected or len(shared) != 2:
        raise RuntimeError('Ground half-square corner union/edge differs: ' + str((x0, y0)))
    a, b = sorted(shared)
    if a[0] == b[0] or a[1] == b[1]:
        raise RuntimeError('Ground shared edge is not the full opposite-corner diagonal')
    first_other = next(iter(first - shared))
    second_other = next(iter(second - shared))
    def side(point):
        return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])
    if side(first_other) * side(second_other) >= 0:
        raise RuntimeError('Ground halves are not on opposite sides of their diagonal')
    ground_support.append({
        'cell_native_local_min_xy_cm': [x0 * 100.0, y0 * 100.0],
        'flat_local_z_cm': 100.0, 'ground_world_z_cm': ground_expected[2],
        'corner_union_grid': sorted(union), 'shared_diagonal_grid': [a, b],
        'opposite_diagonal_sides': True, 'covered_area_cm2': 10000.0,
        'halves': halves})

lo = [ground_expected[0] - 250.0, ground_expected[1] - 250.0,
      ground_expected[2] + 0.5]
hi = [ground_expected[0] + 250.0, ground_expected[1] + 250.0,
      ground_expected[2] + 250.0]
refinements = []
blockers = []
actor_bounds_candidates = 0
mesh_instance_bounds_candidates = 0
for actor in actors:
    center, radius = actor.get_actor_bounds(False)
    if any(not math.isfinite(getattr(value, key))
           for value in (center, radius) for key in ('x', 'y', 'z')):
        raise RuntimeError('Nonfinite level actor bounds; cannot establish clearance')
    if not all(getattr(center, key) + getattr(radius, key) > lo[i]
               and getattr(center, key) - getattr(radius, key) < hi[i]
               for i, key in enumerate(('x', 'y', 'z'))):
        continue
    actor_bounds_candidates += 1
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = component.static_mesh
        if mesh is None:
            continue
        transforms = (
            [component.get_instance_transform(index, world_space=True)
             for index in range(component.get_instance_count())]
            if isinstance(component, unreal.InstancedStaticMeshComponent)
            else [component.get_world_transform()])
        bounds = mesh.get_bounding_box()
        if any(not math.isfinite(getattr(point, key))
               for point in (bounds.min, bounds.max) for key in ('x', 'y', 'z')):
            raise RuntimeError('Nonfinite static mesh bounds; cannot establish clearance')
        for instance_index, transform in enumerate(transforms):
            local = [unreal.MathLibrary.inverse_transform_location(
                transform, unreal.Vector(x, y, z))
                for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
            if any(not math.isfinite(getattr(point, key))
                   for point in local for key in ('x', 'y', 'z')):
                raise RuntimeError('Nonfinite inverse component/instance transform')
            local_min = [min(getattr(point, key) for point in local) for key in ('x', 'y', 'z')]
            local_max = [max(getattr(point, key) for point in local) for key in ('x', 'y', 'z')]
            if not all(getattr(bounds.max, key) > local_min[i]
                       and getattr(bounds.min, key) < local_max[i]
                       for i, key in enumerate(('x', 'y', 'z'))):
                continue
            mesh_instance_bounds_candidates += 1
            dynamic, count = copied_geometry(mesh)
            hits = []
            for triangle_index in range(count):
                points = triangle_points(dynamic, triangle_index)
                if all(max(getattr(point, key) for point in points) > local_min[i]
                       and min(getattr(point, key) for point in points) < local_max[i]
                       for i, key in enumerate(('x', 'y', 'z'))):
                    hits.append(triangle_index)
                    if len(hits) >= 8:
                        break
            record = {'actor': actor.get_actor_label(), 'actor_path': actor.get_path_name(),
                      'component': component.get_path_name(), 'mesh': mesh.get_path_name(),
                      'instance_index': instance_index, 'triangle_bbox_hits': hits,
                      'hits_truncated_at_eight': len(hits) == 8,
                      'local_query_bounds_cm': {'min': local_min, 'max': local_max}}
            refinements.append(record)
            if hits:
                blockers.append(record)

if blockers:
    raise RuntimeError('Copperfall full-height static geometry clearance conflicts: '
                       + json.dumps(blockers))
result = {
    'stage': 'native_25_complete_flat_cells_and_full_height_static_clearance_proven',
    'terrain_actor': terrain.get_path_name(), 'terrain_mesh': terrain_mesh.get_path_name(),
    'terrain_triangle_count': terrain_triangle_count,
    'terrain_origin_cm': origin_expected, 'ground_world_cm': ground_expected,
    'common_actor_translation_cm': translation_expected, 'actor_scale': [1.0, 1.0, 1.0],
    'ground_support': ground_support, 'verified_ground_cells': len(ground_support),
    'verified_ground_triangles': sum(len(cell['halves']) for cell in ground_support),
    'support_area_cm2': sum(cell['covered_area_cm2'] for cell in ground_support),
    'support_coordinate_tolerance_cm': tolerance_cm,
    'expanded_world_box_cm': {'min': lo, 'max': hi},
    'clearance': {'blockers': blockers, 'refinements': refinements,
                  'level_actors_checked': len(actors),
                  'actor_bounds_candidates': actor_bounds_candidates,
                  'mesh_instance_bounds_candidates': mesh_instance_bounds_candidates,
                  'terrain_included': True,
                  'method': 'Conservative local triangle-AABB rejection for every overlapping static mesh component and actual ISM instance; ground contact excluded only below ground+0.5cm.'},
    'measured_meshes': measured_meshes, 'native_mutations': 0,
    'persistent_actor_asset_package_file_mutations': False,
    'transient_dynamic_mesh_copies_created': len(geometry_cache),
    'limits': ['StaticMeshComponent/ISM geometry only; non-static geometry and physics/navigation/runtime acceptance are separate.',
               'CopyMeshFromStaticMesh triangle indices must be dense 0..count-1 as in the existing imported static mesh production path; invalid indices halt the proof.',
               'Terrain support is established within0.02cm coordinate tolerance; imported role geometry/material checks and final placement/save belong to the host recipe.']}
'''
