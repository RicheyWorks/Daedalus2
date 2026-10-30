"""Explicit sole-operator context read. Importing performs no Unreal calls.

No explicit render, PIE, asset/map load, streaming setter, queue edit or asset save.
Absence of implicit dependency/property-resolution effects is not guaranteed. Frame evaluation
is a separate explicit option and requires a closed Sequencer plus an actual
operator protection reader. Editor facts do not prove the old MRQ PIE visibility.
"""
import hashlib
import json
import math
import struct

WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
LEVEL_PACKAGE = '/Game/YTM/Maps/YTM_Island'
SEQUENCE = '/Game/YTM/Seq/WB_Flythrough_YTMIsland.WB_Flythrough_YTMIsland'
PACKAGE_FILE = 'C:/Unreal/DaedalusRealm/Content/YTM/Seq/WB_Flythrough_YTMIsland.uasset'
PACKAGE_SHA = '10af7554917cf73c7d67882c65e01ffffc9a78b876395f9278adf3529957d076'
TAG = 'YTM_Island'
MAX_EDITOR_ACTORS = 32768
MAX_TAGGED = 512
MAX_COMPONENTS = 32
PROTECTED = ('project', 'world', 'pie', 'game_world', 'dirty_maps', 'dirty_content',
             'scene', 'selection', 'camera', 'queue_sha256')


class Held(RuntimeError):
    pass


class RestoreHeld(Held):
    def __init__(self, operation_error, cleanup_errors):
        self.operation_error = (None if operation_error is None else
                                type(operation_error).__name__ + ': ' + str(operation_error)[:1024])
        self.cleanup_errors = list(cleanup_errors)
        super().__init__('Operation: ' + str(self.operation_error) + '; Cleanup: ' + '; '.join(cleanup_errors))


def need(value, message):
    if not value:
        raise Held(message)


def identity(obj):
    if obj is None:
        return None
    return {'path': obj.get_path_name(), 'class': obj.get_class().get_path_name()}


def prop(obj, name):
    return obj.get_editor_property(name)


def finite(value):
    need(type(value) in (int, float) and math.isfinite(value), 'Nonfinite numeric fact')
    return float(value)


def xyz(value):
    return [finite(getattr(value, k)) for k in ('x', 'y', 'z')]


def rotation(value):
    return [finite(getattr(value, k)) for k in ('pitch', 'yaw', 'roll')]


def bounded(values, limit, label):
    need(len(values) <= limit, label + ' exceeds bound; no accepted truncation')
    return values


def optional_property(obj, name):
    try:
        value = prop(obj, name)
        need(type(value) is bool, 'Expected bool: ' + name)
        return {'value': value}
    except Exception as exc:
        return {'value': None, 'unavailable': str(exc)[:512]}


def geometry_relation(location, camera_rotation, horizontal_fov, vertical_fov, target):
    """Point-direction evidence only: no occlusion/frustum/render acceptance."""
    delta = [finite(t) - finite(c) for t, c in zip(target, location)]
    distance = math.sqrt(sum(v * v for v in delta))
    need(distance > 0, 'Camera and target coincide')
    p, y, r = [math.radians(finite(v)) for v in camera_rotation]
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    forward = (cp * cy, cp * sy, sp)
    right = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    up = (-(cr * sp * cy + sr * sy), sr * cy - cr * sp * sy, cr * cp)
    dot = lambda axis: sum(a * b for a, b in zip(delta, axis))
    depth = dot(forward)
    h = math.degrees(math.atan2(dot(right), depth))
    v = math.degrees(math.atan2(dot(up), depth))
    return {'distance_cm': distance, 'forward_depth_cm': depth,
            'horizontal_angle_deg': h, 'vertical_angle_deg': v,
            'center_in_fov_angular_test': depth > 0 and abs(h) <= horizontal_fov / 2 and abs(v) <= vertical_fov / 2,
            'occlusion_or_render_visibility_proven': False}


def actor_facts(u, actor):
    center, extent = actor.get_actor_bounds(False, False)
    center, extent = xyz(center), xyz(extent)
    need(all(v >= 0 for v in extent), 'Negative bounds extent')
    comps = bounded(actor.get_components_by_class(u.StaticMeshComponent), MAX_COMPONENTS, 'Static mesh components')
    meshes = []
    for component in comps:
        meshes.append({'identity': identity(component),
                       'mesh': identity(prop(component, 'static_mesh')),
                       'visible_flag': optional_property(component, 'visible'),
                       'hidden_in_game': optional_property(component, 'hidden_in_game'),
                       'is_editor_only': optional_property(component, 'is_editor_only')})
    label = str(actor.get_actor_label(False))
    need(len(label) <= 512, 'Actor label too long')
    return {'identity': identity(actor), 'label': label, 'level': identity(actor.get_level()),
            'location_cm': xyz(actor.get_actor_location()),
            'rotation_pitch_yaw_roll_deg': rotation(actor.get_actor_rotation()),
            'is_editor_only_actor': optional_property(actor, 'is_editor_only_actor'),
            'hidden_in_game': optional_property(actor, 'hidden'),
            'hidden_in_editor_effective': bool(actor.is_hidden_ed()),
            'hidden_ed_level': optional_property(actor, 'hidden_ed_level'),
            'hidden_ed_layer': optional_property(actor, 'hidden_ed_layer'),
            'bounds_center_cm': center, 'bounds_extent_cm': extent,
            'bounds_nonzero': any(v > 0 for v in extent), 'static_mesh_components': meshes}


def scene_facts(u, world, actors):
    stream = u.GameplayStatics.get_streaming_level(world, LEVEL_PACKAGE)
    if stream is None:
        return {'streaming': None, 'actors': [], 'hold': 'Exact YTM streaming object absent; no load attempted'}
    # GetStreamingLevel performs a suffix match: independently bind the target.
    package = str(stream.get_world_asset_package_f_name())
    need(package == LEVEL_PACKAGE, 'Streaming package is not exact YTM target')
    level = stream.get_loaded_level()
    # BlueprintGetter is exposed as a property, not a callable method.
    # Attribute access dispatches ShouldBeLoaded; get_editor_property below
    # reads the separately recorded raw bShouldBeLoaded field.
    effective_loaded = stream.should_be_loaded
    need(type(effective_loaded) is bool, 'should_be_loaded getter property did not return bool')
    streaming = {'identity': identity(stream), 'world_asset_package': package,
                 'loaded_level': identity(level), 'is_level_loaded': bool(stream.is_level_loaded()),
                 'is_level_visible': bool(stream.is_level_visible()),
                 'should_be_loaded_effective': effective_loaded,
                 'should_be_loaded_raw': optional_property(stream, 'should_be_loaded'),
                 'should_be_visible_raw': optional_property(stream, 'should_be_visible'),
                 'should_be_visible_in_editor': optional_property(stream, 'should_be_visible_in_editor')}
    rows = []
    if level is not None:
        # One editor-only inventory also sees inactive loaded levels. It excludes
        # uneditable/outliner-hidden/transient actors; absence is not a full census.
        inventory = bounded(actors.get_all_level_actors(), MAX_EDITOR_ACTORS, 'Editor actor query')
        candidates = []
        for actor in inventory:
            if actor.get_level() == level and actor.actor_has_tag(TAG):
                candidates.append(actor)
                bounded(candidates, MAX_TAGGED, 'YTM tagged actors')
        for actor in sorted(candidates, key=lambda a: a.get_path_name()):
            rows.append(actor_facts(u, actor))
    return {'streaming': streaming, 'actors': rows,
            'inventory_scope': 'One bounded EditorActorSubsystem editable/nontransient/outliner actor snapshot; exact loaded YTM level + YTM_Island tag before detailed reads. No explicit load or visibility setter.',
            'ground_matches': [r['identity'] for r in rows if r['label'] == 'YTM_Island_Ground'],
            'spawn_matches': [r['identity'] for r in rows if r['label'] == 'YTM_Island_Spawn'],
            'editor_state_is_not_previous_mrq_pie_state': True}


def binding_key(u, proxy, sequence):
    """Mirror FMovieSceneBindingProxy identity using values, not Python struct wrappers.

    Engine MovieSceneBindingProxy.h operator== compares BindingID and Sequence.
    A/B/C/D are the full 128-bit GUID, including signed Python representations.
    """
    bind = u.MovieSceneBindingExtensions
    need(bind.is_valid(proxy), 'Invalid camera binding proxy')
    need(identity(prop(proxy, 'sequence')) == identity(sequence), 'Foreign binding sequence')
    guid = bind.get_id(proxy)
    words = [prop(guid, name) for name in ('a', 'b', 'c', 'd')]
    need(all(type(x) is int and -(2 ** 31) <= x < 2 ** 32 for x in words), 'Malformed GUID components')
    key = ''.join('%08x' % (x & 0xffffffff) for x in words)
    need(key != '0' * 32, 'Zero camera binding GUID')
    return key


def island_camera_translation(rows, spawn):
    """Qualify this existing YTM recipe before translating a private copy.

    The saved original recipe is seven orbit keys at 30 Hz, frames 0..360,
    radius 14000 cm, 4000 cm height, 160 degree sweep and 25% push-in.
    Translation preserves orientation, timing, tangents and all other channels.
    Require exact double recipe values or exact IEEE binary32-rounded recipe
    values (the retained saved shot has the latter). No fitted epsilon.
    """
    need(type(rows) is list and len(rows) == 7, 'Exactly seven recipe positions required')
    need(type(spawn) is list and len(spawn) == 3, 'Actual Spawn position required')
    destination = [finite(x) for x in spawn]
    positions = []
    for k, row in enumerate(rows):
        need(type(row) is dict and row.get('frame') == 60 * k and type(row['frame']) is int,
             'Recipe frames differ')
        value = row.get('position')
        need(type(value) is list and len(value) == 3, 'Recipe position missing')
        p = [finite(x) for x in value]
        positions.append(p)
    # Center sample is on +X with exactly representable radius and height.
    origin = [positions[3][0] - 12250, positions[3][1], positions[3][2] - 4000]
    recipe = []
    for k in range(7):
        angle = math.radians(-80 + 160 * k / 6)
        radius = 14000 * (1 - .25 * k / 6)
        recipe.append([origin[0] + radius * math.cos(angle), origin[1] + radius * math.sin(angle), origin[2] + 4000])
    rounded = [[struct.unpack('<f', struct.pack('<f', v))[0] for v in row] for row in recipe]
    need(positions == recipe or positions == rounded, 'Saved camera differs from qualified YTM orbit recipe')
    delta = [destination[j] - origin[j] for j in range(3)]
    need(all(abs(x) <= 3e6 for x in delta), 'Translation exceeds this explicit island recovery bound')
    return {'source_recipe_center_cm': origin, 'actual_spawn_cm': destination, 'translation_cm': delta,
            'recipe_comparison': 'exact_binary64' if positions == recipe else 'exact_binary32_rounded'}


def camera_binding(u, sequence):
    seq, tracks, sections, bind = u.MovieSceneSequenceExtensions, u.MovieSceneTrackExtensions, u.MovieSceneSectionExtensions, u.MovieSceneBindingExtensions
    cuts = []
    for track in bounded(seq.get_tracks(sequence), 64, 'Root tracks'):
        if identity(track)['class'] == '/Script/MovieSceneTracks.MovieSceneCameraCutTrack':
            for section in bounded(tracks.get_sections(track), 64, 'Camera cut sections'):
                if (sections.has_start_frame(section) and sections.has_end_frame(section)
                        and sections.get_start_frame(section) <= 90 < sections.get_end_frame(section)):
                    cuts.append(section)
    need(len(cuts) == 1, 'Exactly one frame-90 camera cut required')
    opaque = cuts[0].get_camera_binding_id()
    proxy = seq.resolve_binding_id(sequence, opaque)
    need(bind.is_valid(proxy) and prop(proxy, 'sequence') == sequence, 'Camera cut is not resolved to exact root sequence')
    guid = binding_key(u, proxy, sequence)
    matches = [p for p in bounded(seq.get_bindings(sequence), 64, 'Bindings') if binding_key(u, p, sequence) == guid]
    need(len(matches) == 1, 'Camera proxy missing or ambiguous')
    return opaque, seq.get_binding_id(sequence, matches[0]), guid


def evaluate_frame90(u, sequence, actor_api, viewport_api, scene):
    lib = u.LevelSequenceEditorBlueprintLibrary
    for method in ('get_current_level_sequence', 'get_focused_level_sequence', 'is_playing',
                   'open_level_sequence', 'close_level_sequence', 'pause',
                   'is_camera_cut_locked_to_viewport', 'set_lock_camera_cut_to_viewport',
                   'set_global_position', 'get_bound_objects'):
        need(callable(getattr(lib, method, None)), 'Missing Sequencer API before open: ' + method)
    for api, methods in ((actor_api, ('get_selected_level_actors', 'set_selected_level_actors')),
                         (viewport_api, ('get_level_viewport_camera_info', 'set_level_viewport_camera_info'))):
        for method in methods:
            need(callable(getattr(api, method, None)), 'Missing restore API before open: ' + method)
    need(lib.get_current_level_sequence() is None and lib.get_focused_level_sequence() is None,
         'Existing Sequencer context must remain untouched; requires closed editor')
    need(not lib.is_playing(), 'Sequencer playing')
    opaque, local, guid = camera_binding(u, sequence)
    selected = bounded(actor_api.get_selected_level_actors(), 4096, 'Selection')
    camera_before = viewport_api.get_level_viewport_camera_info()
    opened, old_lock, result, errors, operation_error = False, None, None, [], None
    try:
        opened = True  # opening may partially succeed then raise; inspect in finally
        need(lib.open_level_sequence(sequence), 'Could not open exact sequence')
        need(lib.get_current_level_sequence() == sequence and lib.get_focused_level_sequence() == sequence, 'Unexpected Sequencer context')
        old_lock = bool(lib.is_camera_cut_locked_to_viewport())
        lib.pause()
        lib.set_lock_camera_cut_to_viewport(False)
        params = u.MovieSceneSequencePlaybackParams()
        params.set_editor_property('frame', u.FrameTime(u.FrameNumber(90)))
        params.set_editor_property('position_type', u.MovieScenePositionType.FRAME)
        params.set_editor_property('update_method', u.UpdatePositionMethod.JUMP)
        lib.set_global_position(params, u.MovieSceneTimeUnit.DISPLAY_RATE)
        need(lib.get_current_level_sequence() == sequence and lib.get_focused_level_sequence() == sequence,
             'Sequencer context changed during evaluation')
        a, b = lib.get_bound_objects(opaque), lib.get_bound_objects(local)
        need(len(a) == len(b) == 1 and identity(a[0]) == identity(b[0]), 'Opaque/local camera resolution differs')
        need(identity(a[0])['class'] == '/Script/CinematicCamera.CineCameraActor', 'Expected exact native CineCameraActor')
        component = a[0].get_cine_camera_component()
        loc = xyz(component.get_world_location())
        rot = rotation(component.get_world_rotation())
        hfov, vfov = finite(component.get_horizontal_field_of_view()), finite(component.get_vertical_field_of_view())
        need(0 < hfov < 180 and 0 < vfov < 180, 'Invalid evaluated FOV')
        targets = []
        for row in scene['actors']:
            if row['label'] in ('YTM_Island_Ground', 'YTM_Island_Spawn'):
                point = row['location_cm'] if row['label'] == 'YTM_Island_Spawn' else row['bounds_center_cm']
                targets.append({'identity': row['identity'], 'label': row['label'], 'target_center_cm': point,
                                'target_source': 'actor_location' if row['label'] == 'YTM_Island_Spawn' else 'actor_bounds_center',
                                'relation': geometry_relation(loc, rot, hfov, vfov, point)})
        result = {'frame_display': 90, 'binding_guid': guid, 'actor': identity(a[0]), 'component': identity(component),
                  'location_cm': loc, 'rotation_pitch_yaw_roll_deg': rot,
                  'horizontal_fov_deg': hfov, 'vertical_fov_deg': vfov, 'targets': targets,
                  'binding_proof': 'Public ResolveBindingID exact root proxy and identical single bound object from opaque/local IDs',
                  'evaluated': True, 'render_invoked': False}
    except Exception as exc:
        operation_error = exc
        raise
    finally:
        if opened:
            try:
                if lib.get_current_level_sequence() == sequence:
                    try:
                        if old_lock is not None:
                            lib.set_lock_camera_cut_to_viewport(old_lock)
                    finally:
                        lib.close_level_sequence()
                        need(lib.get_current_level_sequence() is None and lib.get_focused_level_sequence() is None,
                             'Owned Sequencer context did not close')
                else:
                    need(lib.get_current_level_sequence() is None, 'Foreign Sequencer context: not closed')
            except Exception as exc:
                errors.append('Sequencer restore: ' + str(exc)[:512])
        try:
            current = actor_api.get_selected_level_actors()
            if sorted(x.get_path_name() for x in current) != sorted(x.get_path_name() for x in selected):
                actor_api.set_selected_level_actors(selected)
        except Exception as exc:
            errors.append('Selection restore: ' + str(exc)[:512])
        try:
            current = viewport_api.get_level_viewport_camera_info()
            if (xyz(current[0]), rotation(current[1])) != (xyz(camera_before[0]), rotation(camera_before[1])):
                viewport_api.set_level_viewport_camera_info(*camera_before)
        except Exception as exc:
            errors.append('Viewport restore: ' + str(exc)[:512])
        if errors:
            raise RestoreHeld(operation_error, errors) from operation_error
    return result


def collect(u, protected_state_reader, evaluate=False):
    """Operator calls after admission. protection callback must read actual state.

    It must include PROTECTED keys, complete relevant MRQ queue fingerprint and
    errors={} from the existing operator. No explicit asset loads; missing prerequisites
    produce HELD. evaluate=True temporarily opens ONLY already-loaded WB sequence.
    """
    result = {'schema': 'daedalus.mrq-scene-context.v1', 'state': 'HELD',
              'native_runtime_qualified': False, 'render_invoked': False, 'errors': []}
    before = protected_state_reader()
    need(all(k in before for k in PROTECTED) and before.get('errors') == {}, 'Actual complete protected state required')
    need(before['world'] == WORLD and before['pie'] is False and before['game_world'] is None, 'Wrong world or PIE/game activity')
    need(isinstance(before['queue_sha256'], str) and len(before['queue_sha256']) == 64
         and all(c in '0123456789abcdef' for c in before['queue_sha256']), 'Actual queue projection SHA256 required')
    before = json.loads(json.dumps(before, allow_nan=False))
    digest = lambda value: hashlib.sha256(json.dumps({k: value[k] for k in PROTECTED}, sort_keys=True,
                                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    result['protected_before_sha256'] = digest(before)
    try:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        need(world.get_path_name() == WORLD, 'Exact editor world required')
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        result['scene'] = scene_facts(u, world, actors)
        if evaluate:
            with open(PACKAGE_FILE, 'rb') as stream:
                data = stream.read(16777217)
            need(len(data) <= 16777216 and hashlib.sha256(data).hexdigest() == PACKAGE_SHA, 'Original sequence package pin differs')
            sequence = u.find_object(None, SEQUENCE, follow_redirectors=False)
            need(sequence is not None and identity(sequence)['class'] == '/Script/LevelSequence.LevelSequence', 'Exact source sequence must already be loaded')
            result['camera'] = evaluate_frame90(u, sequence, actors, u.get_editor_subsystem(u.UnrealEditorSubsystem), result['scene'])
        else:
            result['camera'] = {'evaluated': False, 'reason': 'Explicit evaluate=True required; default collects loaded scene only'}
        result['state'] = 'FACTS_COLLECTED_NOT_RENDER_ACCEPTED'
    except Exception as exc:
        result['errors'].append(type(exc).__name__ + ': ' + str(exc)[:2048])
        if isinstance(exc, RestoreHeld):
            result['evaluation_operation_error'] = exc.operation_error
            result['evaluation_cleanup_errors'] = exc.cleanup_errors
    finally:
        try:
            after = protected_state_reader()
            need(all(k in after for k in PROTECTED) and after.get('errors') == {}, 'Post-state unavailable')
            result['protected_after_sha256'] = digest(after)
            result['preservation'] = {k: before[k] == after[k] for k in PROTECTED}
            need(all(result['preservation'].values()), 'Protected state differs after context read')
        except Exception as exc:
            result['errors'].append('Preservation: ' + str(exc)[:2048])
        if result['errors']:
            result['state'] = 'HELD'
    need(len(json.dumps(result, allow_nan=False).encode()) <= 1048576, 'Result exceeds 1MiB; no truncated acceptance')
    return result
