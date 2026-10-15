# SPDX-License-Identifier: MIT
"""Read-only Winter4 placement routines for the existing guarded native body.

Read/exec this source AFTER the established g.native environment and injected
snap(actor) definition. Required existing globals: unreal, math, json, hashlib,
e (UnrealEditorSubsystem), world, sub (EditorActorSubsystem). This is not a host
CLI, does not dispatch anything and performs no work until a function is called.
Ownership, deadlines, resources, queue guards, journals and writes belong to the
caller. No imports, asset loads, actor mutations or saves occur in this helper.
"""

STAGING_PREFIX = 'CodexStage_Winter4Stream1CoreR1_'
STAGING_FOLDER = 'CodexContest/Staging/Winter4Stream1CoreR1'
CANAL_ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Winter4CanalWaterR1_ad06dd2b3b95da8b'
WORLD_PATH = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
MAX_WORLD_ACTORS = 100000
MAX_INSTANCE_QUERIES = 100000
MAX_COMPONENT_QUERIES = 200000
_CANAL_ROLES = {
    'Octet_Winter_4_Canal_Stream1': ('Octet_Winter_4_Canal_Stream1', 'HD_SkyWater_frost', 'Water'),
    'Octet_Winter_4_Canal_Stream1_Core': ('Octet_Winter_4__al_Stream1_Core', 'HD_SkyFoam', 'Foam')}


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _xyz(value):
    values = [float(getattr(value, key)) for key in ('x', 'y', 'z')]
    if any(not math.isfinite(number) for number in values):
        raise RuntimeError('nonfinite native vector; no clearance/preservation claim')
    return values


def _three(value, name):
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or any(not _finite_number(number) for number in value)):
        raise ValueError('exact finite three-vector required: ' + name)
    return [float(number) for number in value]


def _world_actors():
    if e.get_editor_world().get_path_name() != WORLD_PATH or world.get_path_name() != WORLD_PATH:
        raise RuntimeError('exact existing Daedalus editor world required')
    actors = list(sub.get_all_level_actors())
    if len(actors) > MAX_WORLD_ACTORS:
        raise RuntimeError('bounded all-world actor inspection exceeded; no partial clearance claim')
    return actors


def snapshot_scene():
    """Established Codex actor records plus camera; no camera/actor changes."""
    actors = _world_actors()
    position, rotation = e.get_level_viewport_camera_info()
    return {'world': world.get_path_name(),
            'actors': [snap(actor) for actor in actors if actor.get_actor_label().startswith('Codex')],
            'camera': {'location': dict(zip(('x', 'y', 'z'), _xyz(position))),
                       'rotation': {key: float(getattr(rotation, key)) for key in ('pitch', 'yaw', 'roll')}}}


def assert_old(oldScene, expectedNewLabels=(), expectedNewCount=0):
    """Require the exact prior 143 Codex records and only declared additions.

    Camera comparison is intentionally the caller's separately journalled phase.
    Other-team actors are covered by world_existing_actor_digest, not this prefix.
    """
    if not isinstance(oldScene, dict) or oldScene.get('world') != WORLD_PATH:
        raise ValueError('explicit prior saved Daedalus scene required')
    old_rows = oldScene.get('actors')
    labels = list(expectedNewLabels)
    if (not isinstance(old_rows, list) or len(old_rows) != 143
            or type(expectedNewCount) is not int or expectedNewCount not in (0, 2)
            or len(labels) != expectedNewCount or len(set(labels)) != len(labels)
            or any(not isinstance(label, str) or not label.startswith(STAGING_PREFIX) for label in labels)):
        raise ValueError('exact prior143 and declared zero/two staged labels required')
    before = {row['path']: row for row in old_rows}
    current = snapshot_scene()
    now = {row['path']: row for row in current['actors']}
    if len(before) != 143 or len(now) != len(current['actors']):
        raise RuntimeError('duplicate prior/current actor paths')
    if any(now.get(path) != row for path, row in before.items()):
        raise RuntimeError('prior143 saved actor records differ; preserve work')
    added = [row for path, row in now.items() if path not in before]
    if len(added) != expectedNewCount or {row['label'] for row in added} != set(labels):
        raise RuntimeError('unexpected Codex actors or incomplete staged pair')
    return {'scene': current, 'new_actors': added, 'old_actor_records_preserved': 143,
            'camera_compared': False, 'issues': []}


def _exclusions(exclude_paths, actors):
    paths = list(exclude_paths)
    if len(paths) not in (0, 2) or len(set(paths)) != len(paths) or any(not isinstance(path, str) for path in paths):
        raise ValueError('only zero or exactly two explicit new actor paths may be excluded')
    by_path = {actor.get_path_name(): actor for actor in actors}
    if any(path not in by_path or not by_path[path].get_actor_label().startswith(STAGING_PREFIX)
           or by_path[path].get_class().get_path_name() != '/Script/Engine.StaticMeshActor'
           or str(by_path[path].get_folder_path()) != STAGING_FOLDER for path in paths):
        raise RuntimeError('exclusions must identify the exact live staged pair')
    return set(paths)


def _basis(transform):
    if transform is None:
        raise RuntimeError('native component/instance transform unavailable')
    return [_xyz(unreal.MathLibrary.transform_location(transform, unreal.Vector(*point)))
            for point in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))]


def world_existing_actor_digest(exclude_paths=()):
    """Hash every actor in explicit bounded scope, without retaining full rows.

    Includes static-component affine transforms and ISM counts. Per-instance
    transforms and arbitrary serialized actor/component properties are excluded.
    """
    actors = _world_actors()
    excluded = _exclusions(exclude_paths, actors)
    digest = hashlib.sha256()
    counts = {'actors': 0, 'static_components': 0, 'instanced_components': 0, 'instances': 0}
    for actor in sorted(actors, key=lambda item: item.get_path_name()):
        if actor.get_path_name() in excluded:
            continue
        rotation = actor.get_actor_rotation()
        parent = actor.get_attach_parent_actor()
        row = {'path': actor.get_path_name(), 'class': actor.get_class().get_path_name(),
               'label': actor.get_actor_label(), 'location': _xyz(actor.get_actor_location()),
               'rotation': [float(getattr(rotation, key)) for key in ('pitch', 'yaw', 'roll')],
               'scale': _xyz(actor.get_actor_scale3d()), 'attach_parent': parent.get_path_name() if parent else None,
               'static_components': []}
        for component in sorted(actor.get_components_by_class(unreal.StaticMeshComponent), key=lambda item: item.get_path_name()):
            counts['static_components'] += 1
            if counts['static_components'] > MAX_COMPONENT_QUERIES:
                raise RuntimeError('bounded component digest exceeded; no partial preservation claim')
            mesh = component.static_mesh
            item = {'path': component.get_path_name(), 'class': component.get_class().get_path_name(),
                    'mesh': mesh.get_path_name() if mesh else None,
                    'materials': [component.get_material(index).get_path_name() if component.get_material(index) else None
                                  for index in range(component.get_num_materials())],
                    'world_basis_cm': _basis(component.get_world_transform())}
            if isinstance(component, unreal.InstancedStaticMeshComponent):
                count = component.get_instance_count()
                if type(count) is not int or count < 0:
                    raise RuntimeError('invalid native ISM count')
                item['instance_count'] = count
                counts['instanced_components'] += 1
                counts['instances'] += count
            row['static_components'].append(item)
        digest.update((json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8'))
        counts['actors'] += 1
    return {'actor_count': counts['actors'], 'sha256': digest.hexdigest(), 'counts': counts,
            'excluded_paths': sorted(excluded), 'native_mutations': 0,
            'scope': 'Sorted ALL-world actor path/class/label/pose/scale/attach-parent plus static component path/class/mesh/materials/affine world transform/ISMcount.',
            'limits': 'No per-instance transforms or complete serialized actor properties; those are not claimed preserved by this digest.'}


def _box(minimum, maximum):
    lo, hi = _three(minimum, 'bounds.min'), _three(maximum, 'bounds.max')
    if any(lo[index] > hi[index] for index in range(3)):
        raise RuntimeError('reversed native/local bounds')
    return lo, hi


def _intersects(first, second):
    # Closed boxes conservatively include touching boundaries.
    return all(first[1][index] >= second[0][index] and first[0][index] <= second[1][index] for index in range(3))


def _center_box(center, extent):
    c, r = _xyz(center), _xyz(extent)
    if any(number < 0 for number in r):
        raise RuntimeError('negative cached native bounds extent')
    return ([c[index] - r[index] for index in range(3)], [c[index] + r[index] for index in range(3)])


def _component_box(component):
    value = unreal.SystemLibrary.get_component_bounds(component)
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise RuntimeError('unsupported public component bounds return shape')
    return _center_box(value[0], value[1])


def _transformed_box(local, transform):
    if transform is None:
        raise RuntimeError('native instance transform failed; no clearance claim')
    corners = [_xyz(unreal.MathLibrary.transform_location(transform, unreal.Vector(x, y, z)))
               for x in (local[0][0], local[1][0]) for y in (local[0][1], local[1][1]) for z in (local[0][2], local[1][2])]
    return ([min(point[index] for point in corners) for index in range(3)],
            [max(point[index] for point in corners) for index in range(3)])


def clearance(cfg):
    """Direct read-only all-world conservative bounds pass; never yields.

    Every candidate is padded 500 cm on all sides. Only owner/component bounds
    overlapping candidates expand ISM instances. No actors are implicitly ignored.
    Exclusions, when present, must be exactly the two explicit newly staged paths.
    """
    candidates = cfg.get('candidates') if isinstance(cfg, dict) else None
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 16:
        raise ValueError('one to sixteen explicit candidate boxes required')
    boxes, results = [], []
    names = set()
    for row in candidates:
        if not isinstance(row, dict) or not isinstance(row.get('name'), str) or row['name'] in names:
            raise ValueError('distinct named candidates required')
        names.add(row['name'])
        translation = _three(row['translation_cm'], 'translation_cm')
        local = _box(row['local_bounds']['min'], row['local_bounds']['max'])
        bounds = ([translation[index] + local[0][index] - 500. for index in range(3)],
                  [translation[index] + local[1][index] + 500. for index in range(3)])
        boxes.append(bounds)
        results.append({'name': row['name'], 'translation_cm': translation,
                        'padded_bounds_cm': {'min': bounds[0], 'max': bounds[1]},
                        'margin_cm': 500., 'blocker_count': 0, 'blockers': [], 'blockers_retained_limit': 32})
    actors = _world_actors()
    excluded = _exclusions(cfg.get('exclude_paths', ()), actors)
    counts = {'world_actors': len(actors), 'actors_checked': 0, 'actor_bounds_overlaps': 0,
              'primitive_components_checked': 0, 'static_components_checked': 0,
              'ism_components_expanded': 0, 'instance_transforms_checked': 0, 'bounds_failures': 0}
    existing_winter = []

    def add(hits, actor, component, reason, bounds=None, instance=None):
        for index in hits:
            result = results[index]
            result['blocker_count'] += 1
            if len(result['blockers']) < 32:
                result['blockers'].append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(),
                    'actor_class': actor.get_class().get_path_name(),
                    'component': component.get_path_name() if component else None,
                    'component_class': component.get_class().get_path_name() if component else None,
                    'instance': instance, 'reason': reason,
                    'bounds_cm': {'min': bounds[0], 'max': bounds[1]} if bounds else None})

    for actor in actors:
        if 'octet_winter_4' in actor.get_actor_label().lower():
            existing_winter.append({'path': actor.get_path_name(), 'label': actor.get_actor_label(),
                                    'class': actor.get_class().get_path_name()})
        if actor.get_path_name() in excluded:
            continue
        counts['actors_checked'] += 1
        try:
            center, extent = actor.get_actor_bounds(False)
            owner_box = _center_box(center, extent)
            hits = [index for index, box in enumerate(boxes) if _intersects(owner_box, box)]
        except Exception as error:
            counts['bounds_failures'] += 1
            add(range(len(boxes)), actor, None, 'unresolved owner bounds: ' + str(error))
            continue
        if not hits:
            continue
        counts['actor_bounds_overlaps'] += 1
        primitives = list(actor.get_components_by_class(unreal.PrimitiveComponent))
        for component in primitives:
            counts['primitive_components_checked'] += 1
            if counts['primitive_components_checked'] > MAX_COMPONENT_QUERIES:
                raise RuntimeError('bounded primitive clearance exceeded; no partial clearance claim')
            try:
                component_box = _component_box(component)
                component_hits = [index for index in hits if _intersects(component_box, boxes[index])]
            except Exception as error:
                counts['bounds_failures'] += 1
                add(hits, actor, component, 'unresolved component bounds: ' + str(error))
                continue
            if not component_hits:
                continue
            if not isinstance(component, unreal.StaticMeshComponent):
                add(component_hits, actor, component, 'conservative non-static primitive bounds', component_box)
                continue
            counts['static_components_checked'] += 1
            if not isinstance(component, unreal.InstancedStaticMeshComponent):
                # Includes ordinary static, spline/deformed subclasses and any
                # renderer-expanded cached bounds. Do not replace them with a
                # rigid undeformed mesh box that could produce a false clear.
                add(component_hits, actor, component, 'conservative static component world bounds', component_box)
                continue
            mesh = component.static_mesh
            if mesh is None:
                add(component_hits, actor, component, 'unresolved static component mesh', component_box)
                continue
            try:
                bounds = mesh.get_bounding_box()
                local = _box(_xyz(bounds.min), _xyz(bounds.max))
            except Exception as error:
                counts['bounds_failures'] += 1
                add(component_hits, actor, component, 'unresolved local mesh bounds: ' + str(error))
                continue
            if isinstance(component, unreal.InstancedStaticMeshComponent):
                count = component.get_instance_count()
                if type(count) is not int or count < 0 or counts['instance_transforms_checked'] + count > MAX_INSTANCE_QUERIES:
                    raise RuntimeError('bounded ISM clearance exceeded/invalid count; no partial clearance claim')
                try:
                    scale = component.get_editor_property('bounds_scale')
                    if not _finite_number(scale) or scale < 0:
                        raise RuntimeError('finite nonnegative native bounds_scale required')
                    scale = max(1., float(scale))
                except Exception as error:
                    counts['bounds_failures'] += 1
                    add(component_hits, actor, component, 'unresolved instanced bounds scale: ' + str(error), component_box)
                    continue
                counts['ism_components_expanded'] += 1
                indices = range(count)
            else:
                indices = (None,)
            for instance in indices:
                try:
                    if instance is not None:
                        counts['instance_transforms_checked'] += 1
                    transform = (component.get_instance_transform(instance, world_space=True) if instance is not None
                                 else component.get_world_transform())
                    actual = _transformed_box(local, transform)
                    center = [(actual[0][index] + actual[1][index]) * .5 for index in range(3)]
                    extent = [(actual[1][index] - actual[0][index]) * .5 * scale for index in range(3)]
                    actual = ([center[index] - extent[index] for index in range(3)],
                              [center[index] + extent[index] for index in range(3)])
                    actual_hits = [index for index in component_hits if _intersects(actual, boxes[index])]
                    add(actual_hits, actor, component, 'actual transformed static mesh bounds', actual, instance)
                except Exception as error:
                    counts['bounds_failures'] += 1
                    add(component_hits, actor, component, 'unresolved actual transform: ' + str(error), instance=instance)
    for result in results:
        result['blockers_retained'] = len(result['blockers'])
        result['blockers_truncated'] = result['blocker_count'] > len(result['blockers'])
        result['clear'] = result['blocker_count'] == 0
    return {'candidates': results, 'checked_counts': counts, 'winter_actors': existing_winter,
            'existing_winter4_actor_count': len(existing_winter), 'excluded_paths': sorted(excluded),
            'native_mutations': 0, 'limits': 'Conservative padded AABB clearance, not triangle contact/ground support/navigation/physics or visual acceptance. Counts are exact for this pass; unresolved bounds are retained blockers, never clear.'}


def validate_pair(cfg):
    """Read-only exact staged actor/material/scale/collision invariants."""
    rows = cfg.get('rows') if isinstance(cfg, dict) else None
    translation = _three(cfg['translation_cm'], 'translation_cm')
    if (not isinstance(rows, list) or len(rows) != 2 or {row.get('role') for row in rows} != set(_CANAL_ROLES)
            or len({row.get('label') for row in rows}) != 2
            or any(not isinstance(row.get('label'), str) or not row['label'].startswith(STAGING_PREFIX) for row in rows)):
        raise ValueError('exact two distinct staged Winter4 roles/labels required')
    actors = _world_actors()
    staged = [actor for actor in actors if actor.get_actor_label().startswith(STAGING_PREFIX)]
    if len(staged) != 2 or {actor.get_actor_label() for actor in staged} != {row['label'] for row in rows}:
        raise RuntimeError('exact two staged actors required; no duplicate/extra prefix actors')
    flags, new_rows = [], []
    for row in rows:
        mesh_name, material_name, suffix = _CANAL_ROLES[row['role']]
        folder = CANAL_ROOT + '/Winter4_Canal_Stream1_Core_R1/'
        expected = {'mesh': folder + 'StaticMeshes/' + mesh_name + '.' + mesh_name,
                    'material': folder + 'Materials/' + material_name + '.' + material_name,
                    'owned_parent': CANAL_ROOT + '/OwnedParents/M_Codex_Winter4_' + suffix + '_RawAlpha_R1.M_Codex_Winter4_' + suffix + '_RawAlpha_R1'}
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError('exact saved two-role mesh/MIC/parent paths required')
        actor = next(actor for actor in staged if actor.get_actor_label() == row['label'])
        if (actor.get_class().get_path_name() != '/Script/Engine.StaticMeshActor'
                or str(actor.get_folder_path()) != STAGING_FOLDER or actor.get_attach_parent_actor() is not None):
            raise RuntimeError('exact staged StaticMeshActor class/folder required')
        observed = snap(actor)
        if (any(abs(observed['location'][index] - translation[index]) > .002 or abs(observed['scale'][index] - 1.) > 1e-6 for index in range(3))
                or observed['rotation'] != [0., 0., 0.] or len(observed['components']) != 1
                or observed['components'][0]['mesh'] != row['mesh'] or observed['components'][0]['materials'] != [row['material']]):
            raise RuntimeError('exact common source-root transform/one inherited material required')
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component is None or component.get_class().get_path_name() != '/Script/Engine.StaticMeshComponent':
            raise RuntimeError('exact single static mesh component required')
        mesh = component.static_mesh
        material = component.get_material(0)
        if list(component.get_editor_property('override_materials')):
            raise RuntimeError('staged component must inherit the saved MIC without material overrides')
        if (not isinstance(mesh, unreal.StaticMesh) or not isinstance(material, unreal.MaterialInstanceConstant)
                or len(list(mesh.get_editor_property('static_materials'))) != 1 or mesh.get_material(0) != material
                or material.get_editor_property('parent') is None
                or material.get_editor_property('parent').get_path_name() != row['owned_parent']
                or material.get_base_material().get_path_name() != row['owned_parent']):
            raise RuntimeError('unchanged saved mesh slot/MIC and exact owned parent required')
        basis = _basis(component.get_world_transform())
        expected_basis = [[translation[index] + point[index] for index in range(3)]
                          for point in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))]
        if any(abs(a - b) > .002 for actual, expected_point in zip(basis, expected_basis) for a, b in zip(actual, expected_point)):
            raise RuntimeError('effective component transform differs from unit actor/source-root transform')
        collision = component.get_collision_enabled()
        simulated = component.is_simulating_physics()
        priority = component.get_editor_property('translucency_sort_priority')
        distance = component.get_editor_property('translucency_sort_distance_offset')
        if (collision != unreal.CollisionEnabled.NO_COLLISION or simulated is not False
                or type(priority) is not int or priority != 0 or not _finite_number(distance) or distance != 0.):
            raise RuntimeError('decorative no-collision/no-simulation and default translucent sorting required')
        try:
            overlap = component.get_editor_property('generate_overlap_events')
            if type(overlap) is not bool:
                raise RuntimeError('unsupported overlap editor-property return shape: ' + type(overlap).__name__)
            overlap_observation = {'available': True, 'value': overlap, 'route': 'normal CPF_Edit editor-property read'}
        except Exception as error:
            overlap_observation = {'available': False, 'value': None, 'reason': str(error)}
        flags.append({'actor': actor.get_path_name(), 'component': component.get_path_name(),
                      'collision_enabled': str(collision), 'simulate_physics': simulated,
                      'generate_overlap_events_observed': overlap_observation,
                      'material_override_count': 0,
                      'translucency_sort_priority': priority, 'translucency_sort_distance_offset': distance,
                      'world_basis_cm': basis, 'overlap_limit': 'NO_COLLISION excludes queries/overlaps/simulation; the independent generation flag is observation only.'})
        new_rows.append(observed)
    return {'stage': 'exact_two_saved_canal_roles_placed_readback', 'scene': snapshot_scene(),
            'new_actors': new_rows, 'components': flags, 'native_mutations': 0, 'issues': [],
            'limits': 'Decorative static source pair only; translucent ordering/appearance, fluid behavior, navigation, support and runtime remain unaccepted.'}
