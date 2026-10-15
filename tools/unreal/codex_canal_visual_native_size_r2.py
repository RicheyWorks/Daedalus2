# SPDX-License-Identifier: MIT
"""Read-only pair proof and contributing renderer observations for Winter4.

Inject after the frozen placement helper in the established guarded native
scope (unreal, math, json, e, world, sub, snap and placement read helpers).
Nothing runs on import. No asset load, settings write, mutation or dispatch.
Camera preservation, custody, deadlines, journalling and saves belong to caller.
"""

_VISUAL_WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
_VISUAL_ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/Winter4CanalWaterR1_ad06dd2b3b95da8b'
_VISUAL_FOLDER = 'CodexContest/Staging/Winter4Stream1CoreR1'
_VISUAL_PATHS = [_VISUAL_WORLD + ':PersistentLevel.StaticMeshActor_4018',
                 _VISUAL_WORLD + ':PersistentLevel.StaticMeshActor_4019']
_VISUAL_NAMES = [('Water', 'Octet_Winter_4_Canal_Stream1', 'HD_SkyWater_frost'),
                 ('FoamCore', 'Octet_Winter_4__al_Stream1_Core', 'HD_SkyFoam')]


def visual_pair(cfg, expected_foam_priority):
    """Prove the fixed saved pair; only Foam priority may be explicitly 0 or 1.

    cfg: baseline_scene (all145 saved actor records), expected_rows (the exact
    two saved new_actors rows), baseline_world_digest (prior22869 actor digest).
    Actor snapshots omit sort priority, so that value is checked separately.
    The old validate_pair remains untouched and is never called here.
    """
    if type(expected_foam_priority) is not int or expected_foam_priority not in (0, 1):
        raise ValueError('only exact baseline0 or declared Foam1 visual candidate allowed')
    baseline, expected = cfg['baseline_scene'], cfg['expected_rows']
    if (baseline.get('world') != _VISUAL_WORLD or len(baseline.get('actors', [])) != 145
            or not isinstance(expected, list) or len(expected) != 2
            or {row['path'] for row in expected} != set(_VISUAL_PATHS)):
        raise ValueError('exact saved145 scene and two immutable staged rows required')
    before = {row['path']: row for row in baseline['actors']}
    if len(before) != 145 or any(before.get(row['path']) != row for row in expected):
        raise ValueError('expected pair rows must be exact members of saved145 baseline')
    scene = snapshot_scene()
    if scene['world'] != _VISUAL_WORLD or len(scene['actors']) != 145:
        raise RuntimeError('exact saved145 actor count/world required')
    current = {row['path']: row for row in scene['actors']}
    if len(current) != 145 or current != before:
        raise RuntimeError('all145 actor records must remain exact; only unsnapped sort priority may differ')
    actors = {actor.get_path_name(): actor for actor in _world_actors()}
    records, flags = [], []
    for index, (suffix, mesh_name, material_name) in enumerate(_VISUAL_NAMES):
        path = _VISUAL_PATHS[index]; actor = actors[path]; saved = before[path]
        mesh_path = _VISUAL_ROOT + '/Winter4_Canal_Stream1_Core_R1/StaticMeshes/' + mesh_name + '.' + mesh_name
        material_path = _VISUAL_ROOT + '/Winter4_Canal_Stream1_Core_R1/Materials/' + material_name + '.' + material_name
        parent_name = 'M_Codex_Winter4_' + ('Water' if index == 0 else 'Foam') + '_RawAlpha_R1'
        parent_path = _VISUAL_ROOT + '/OwnedParents/' + parent_name + '.' + parent_name
        if (saved['label'] != 'CodexStage_Winter4Stream1CoreR1_' + suffix
                or saved['folder'] != _VISUAL_FOLDER or saved['rotation'] != [0., 0., 0.]
                or saved['scale'] != [1., 1., 1.]
                or actor.get_class().get_path_name() != '/Script/Engine.StaticMeshActor'
                or actor.get_attach_parent_actor() is not None or str(actor.get_folder_path()) != _VISUAL_FOLDER):
            raise RuntimeError('fixed staged class/identity/folder/unit transform required')
        components = list(actor.get_components_by_class(unreal.StaticMeshComponent))
        if len(components) != 1 or components[0].get_class().get_path_name() != '/Script/Engine.StaticMeshComponent':
            raise RuntimeError('exact one ordinary saved static component required')
        component = components[0]; mesh = component.static_mesh; material = component.get_material(0)
        if (len(saved['components']) != 1 or saved['components'][0]['mesh'] != mesh_path
                or saved['components'][0]['materials'] != [material_path]
                or not isinstance(mesh, unreal.StaticMesh) or mesh.get_path_name() != mesh_path
                or not isinstance(material, unreal.MaterialInstanceConstant) or material.get_path_name() != material_path
                or list(component.get_editor_property('override_materials'))
                or len(list(mesh.get_editor_property('static_materials'))) != 1
                or component.get_num_materials() != 1 or mesh.get_material(0) != material
                or material.get_editor_property('parent') is None
                or material.get_editor_property('parent').get_path_name() != parent_path
                or material.get_base_material().get_path_name() != parent_path):
            raise RuntimeError('exact inherited saved mesh/MIC/owned-parent chain required')
        basis = _basis(component.get_world_transform())
        wanted_basis = [[saved['location'][axis] + point[axis] for axis in range(3)]
                        for point in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))]
        if any(abs(a-b) > .002 for actual, wanted in zip(basis, wanted_basis) for a,b in zip(actual,wanted)):
            raise RuntimeError('effective component source-root transform changed')
        priority = component.get_editor_property('translucency_sort_priority')
        distance = component.get_editor_property('translucency_sort_distance_offset')
        collision = component.get_collision_enabled(); simulated = component.is_simulating_physics()
        wanted_priority = 0 if index == 0 else expected_foam_priority
        if (type(priority) is not int or priority != wanted_priority
                or type(distance) not in (int,float) or not math.isfinite(distance) or distance != 0.
                or collision != unreal.CollisionEnabled.NO_COLLISION or simulated is not False):
            raise RuntimeError('exact Water0/Foam-declared priority, distance0 and decorative flags required')
        records.append(saved)
        flags.append({'actor':path,'component':component.get_path_name(),'material':material_path,
                      'owned_parent':parent_path,'translucency_sort_priority':priority,
                      'translucency_sort_distance_offset':float(distance),'material_override_count':0,
                      'collision_enabled':str(collision),'simulate_physics':simulated,'world_basis_cm':basis})
    if records[0]['location'] != records[1]['location']:
        raise RuntimeError('source pair must retain the same rigid translation')
    digest = world_existing_actor_digest(_VISUAL_PATHS); prior = cfg['baseline_world_digest']
    if (digest.get('excluded_paths') != sorted(_VISUAL_PATHS)
            or prior.get('excluded_paths') not in ([], sorted(_VISUAL_PATHS))
            or {key:value for key,value in digest.items() if key != 'excluded_paths'} !=
               {key:value for key,value in prior.items() if key != 'excluded_paths'}):
        raise RuntimeError('prior all-world actor/component digest changed beyond exact pair exclusions')
    return {'stage':'winter4_visual_pair_verified','scene':scene,'new_actors':records,'components':flags,
            'expected_foam_priority':expected_foam_priority,'global_actor_digest':digest,
            'actor_records_preserved':145,'camera_compared':False,'native_mutations':0,'issues':[],
            'limits':'Sort priority checked explicitly; snapshots/digest do not cover every serialized property or ISM transform. Caller guards raw material/graph and saved bytes separately.'}


def _visual_read(call):
    try:
        value = call()
        json.dumps(value, allow_nan=False)
        return {'available':True,'value':value}
    except Exception as error:
        return {'available':False,'value':None,'error_type':type(error).__name__,'error':str(error)[:300]}


def _visual_enum(obj, name):
    value = obj.get_editor_property(name)
    if value is None:raise RuntimeError('enum property returned None')
    return str(value)


def _visual_bool(obj, name):
    value = obj.get_editor_property(name)
    if type(value) is not bool:raise RuntimeError('expected public boolean property')
    return value


def _visual_number(obj, name):
    value = obj.get_editor_property(name)
    if type(value) not in (int,float) or not math.isfinite(value):raise RuntimeError('expected finite numeric property')
    return value


def _visual_settings(obj, property_name='settings'):
    result = {}
    try:settings = obj.get_editor_property(property_name)
    except Exception as error:
        return {'available':False,'error_type':type(error).__name__,'error':str(error)[:300]}
    for name in ('auto_exposure_method','reflection_method','translucency_type'):
        result[name] = _visual_read(lambda name=name:_visual_enum(settings,name))
    for name in ('auto_exposure_bias','auto_exposure_min_brightness','auto_exposure_max_brightness','film_white_clip'):
        result[name] = _visual_read(lambda name=name:_visual_number(settings,name))
    for name in ('auto_exposure_method','auto_exposure_bias','auto_exposure_min_brightness',
                 'auto_exposure_max_brightness','auto_exposure_apply_physical_camera_exposure',
                 'color_gamma','film_white_clip','reflection_method','translucency_type'):
        key = 'override_' + name
        result[key] = _visual_read(lambda key=key:_visual_bool(settings,key))
    result['auto_exposure_apply_physical_camera_exposure'] = _visual_read(
        lambda:_visual_bool(settings,'auto_exposure_apply_physical_camera_exposure'))
    result['color_gamma'] = _visual_read(lambda:[float(getattr(settings.get_editor_property('color_gamma'),axis))
                                                for axis in ('x','y','z','w')])
    return {'available':True,'fields':result,'scope':'Contributing settings only; effective blended viewport exposure is not measured.'}


def _visual_post_process(obj):
    row = {'path':obj.get_path_name(),'class':obj.get_class().get_path_name()}
    for name in ('enabled','unbound'):
        row[name] = _visual_read(lambda name=name:_visual_bool(obj,name))
    for name in ('priority','blend_weight','blend_radius'):
        row[name] = _visual_read(lambda name=name:_visual_number(obj,name))
    row['settings'] = _visual_settings(obj)
    return row


def contributing_renderer_readbacks():
    """Optional named public getters only; unsupported fields never block pair proof.

    No final-view EV or live EngineShowFlags getter is assumed. CVar strings
    avoid treating the numeric getter's missing-variable zero as a valid value.
    """
    result = {'schema':'daedalus.winter4.contributing-renderer-readbacks.v1','native_mutations':0}
    viewport = {}; result['viewport'] = viewport
    try:
        level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        key = level.get_active_viewport_config_key(); viewport['config_key'] = str(key)
        viewport['game_view'] = _visual_read(lambda:level.editor_get_game_view(key))
        viewport['exact_camera_view'] = _visual_read(lambda:level.get_exact_camera_view(key))
        viewport['fov'] = _visual_read(lambda:level.get_level_viewport_fov(key))
        try:
            pilot = level.get_pilot_level_actor(key)
            viewport['pilot'] = {'available':True,'value':pilot.get_path_name() if pilot else None}
        except Exception as error:
            pilot = None
            viewport['pilot'] = {'available':False,'value':None,'error_type':type(error).__name__,'error':str(error)[:300]}
        cameras = list(pilot.get_components_by_class(unreal.CameraComponent)) if pilot else []
        viewport['pilot_camera_count'] = len(cameras); viewport['pilot_cameras'] = []
        for camera in cameras[:4]:
            viewport['pilot_cameras'].append({'path':camera.get_path_name(),
                'field_of_view':_visual_read(lambda camera=camera:_visual_number(camera,'field_of_view')),
                'post_process_blend_weight':_visual_read(lambda camera=camera:_visual_number(camera,'post_process_blend_weight')),
                'settings':_visual_settings(camera,'post_process_settings')})
        viewport['pilot_cameras_truncated'] = len(cameras)>4
    except Exception as error:
        for name in ('config_key','game_view','exact_camera_view','fov','pilot','pilot_cameras'):
            if name not in viewport:
                viewport[name] = {'available':False,'value':None,'error_type':type(error).__name__,'error':str(error)[:300]}
    viewport['camera'] = _visual_read(lambda:snapshot_scene()['camera'])
    viewport['size'] = _visual_read(lambda:{axis:int(getattr(e.get_level_viewport_size(),axis)) for axis in ('x','y')})
    result['cvars'] = {}
    for name in ('r.DefaultFeature.AutoExposure','r.DefaultFeature.AutoExposure.Method',
                 'r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange','r.TonemapperGamma',
                 'r.HDR.Display.OutputDevice','r.HDR.Display.ColorGamut','r.TranslucentSortPolicy'):
        item = _visual_read(lambda name=name:unreal.SystemLibrary.get_console_variable_string_value(name))
        if item['available'] and item['value']=='':
            item = {'available':False,'value':None,'error':'Console getter returned empty string; missing/unavailable, not zero.'}
        result['cvars'][name] = item
    config = {}; result['renderer_config'] = config
    try:
        renderer = unreal.get_default_object(unreal.RendererSettings)
        for name in ('working_color_space_choice','translucent_sort_policy'):
            config[name] = _visual_read(lambda name=name:_visual_enum(renderer,name))
        config['translucent_sort_axis'] = _visual_read(lambda:_xyz(renderer.get_editor_property('translucent_sort_axis')))
    except Exception as error:
        config['unavailable'] = {'error_type':type(error).__name__,'error':str(error)[:300]}
    config['scope'] = 'Project config/CDO; restart-required working-space setting is not proof of active final output.'
    volumes = []; components = []; pp_errors = []; actors = []
    try:
        actors = _world_actors()
        for actor in actors:
            if isinstance(actor,unreal.PostProcessVolume):volumes.append(actor)
            try:components.extend(actor.get_components_by_class(unreal.PostProcessComponent))
            except Exception as error:
                if len(pp_errors)<8:pp_errors.append({'actor':actor.get_path_name(),'error_type':type(error).__name__,'error':str(error)[:200]})
        result['post_process'] = {'volume_count':len(volumes),'component_count':len(components),
            'volumes':[_visual_post_process(obj) for obj in volumes[:64]],
            'components':[_visual_post_process(obj) for obj in components[:64]],
            'truncated':len(volumes)>64 or len(components)>64,'errors':pp_errors}
    except Exception as error:
        result['post_process'] = {'available':False,'error_type':type(error).__name__,'error':str(error)[:300]}
    result['owned_parent_settings'] = []
    for path in _VISUAL_PATHS:
        row = {'actor':path}
        try:
            actor = next(actor for actor in actors if actor.get_path_name()==path)
            parent = actor.get_component_by_class(unreal.StaticMeshComponent).get_material(0).get_base_material()
            row['parent'] = parent.get_path_name()
            for name in ('use_translucency_vertex_fog','apply_cloud_fogging','compute_fog_per_pixel',
                         'screen_space_reflections','enable_responsive_aa','disable_depth_test'):
                row[name] = _visual_read(lambda name=name:_visual_bool(parent,name))
            for name in ('translucency_pass','translucency_lighting_mode','refraction_method'):
                row[name] = _visual_read(lambda name=name:_visual_enum(parent,name))
        except Exception as error:
            row['unavailable'] = {'error_type':type(error).__name__,'error':str(error)[:300]}
        result['owned_parent_settings'].append(row)
    result['unsupported'] = {'effective_final_view_exposure_ev':'No verified public Python getter.',
                             'live_viewport_tonemapper_show_flags':'EditorViewportClient C++ state; no verified public Python getter.'}
    result['limits'] = 'Read-only contributing settings; no global setting changes, inferred gamma correction, final blended-exposure proof or automatic visual quality verdict.'
    return result
