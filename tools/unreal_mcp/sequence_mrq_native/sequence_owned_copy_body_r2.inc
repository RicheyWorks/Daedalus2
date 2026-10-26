# Source-only R2 public binding/SpawnTrack repair; executed R1 is immutable.
# Source-only authored body. The sole operator supplies plan, unreal,
# snapshot/qualify/before/record, and independently verified process_generation.
import copy as _sc_copy_module
import datetime as _sc_datetime
import hashlib as _sc_hashlib
import json as _sc_json
import math as _sc_math
import os as _sc_os
import re as _sc_re
from fractions import Fraction as _sc_Fraction
from pathlib import Path as _sc_Path

_SC_SOURCE = '/Game/YTM/Seq/WB_Flythrough_YTMIsland.WB_Flythrough_YTMIsland'
_SC_SOURCE_SHA = '10af7554917cf73c7d67882c65e01ffffc9a78b876395f9278adf3529957d076'
_SC_JOB_SHA = 'f5760dff4b85014e6e0c19e731b032571974ed2d594246fc654093a634fd88cb'
_SC_COPY_ROOT = '/Game/CodexToolEvaluation/EpicIntegrationR1/Sequence/'
_SC_PROJECT = 'C:/Unreal/DaedalusRealm/DaedalusRealm.uproject'
_SC_FIELDS = ('project', 'world', 'pie', 'game_world', 'dirty_maps', 'dirty_content', 'scene', 'selection', 'camera')
_SC_CONTENT = _sc_Path('C:/Unreal/DaedalusRealm/Content')
_SC_FRAMES = (0, 90, 179)
_SC_TRACKS = {'/Script/MovieSceneTracks.MovieScene3DTransformTrack', '/Script/MovieSceneTracks.MovieSceneCameraCutTrack', '/Script/MovieScene.MovieSceneSpawnTrack'}
_SC_SECTIONS = {'/Script/MovieSceneTracks.MovieScene3DTransformSection', '/Script/MovieSceneTracks.MovieSceneCameraCutSection', '/Script/MovieScene.MovieSceneSpawnSection'}


def _sc_need(ok, message):
    if not ok:
        raise RuntimeError(message)


def _sc_digest(value):
    return _sc_hashlib.sha256(_sc_json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _sc_finite(value):
    return type(value) in (int, float) and _sc_math.isfinite(value)


def _sc_prop(obj, name):
    return obj.get_editor_property(name)


def _sc_id(obj):
    return None if obj is None else {'path': obj.get_path_name(), 'class': obj.get_class().get_path_name()}


def _sc_guid(value):
    parts = [_sc_prop(value, name) for name in ('a', 'b', 'c', 'd')]
    _sc_need(all(type(x) is int for x in parts), 'Native GUID components unavailable')
    return ''.join('%08x' % (x & 0xffffffff) for x in parts)


def _sc_rate(value):
    result = [_sc_prop(value, 'numerator'), _sc_prop(value, 'denominator')]
    _sc_need(all(type(x) is int and 0 < x <= 1000000 for x in result), 'Invalid rational sequence rate')
    return result


def _sc_package_path(object_path):
    _sc_need(isinstance(object_path, str) and _sc_re.fullmatch(r'/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+', object_path), 'Canonical /Game object path required')
    package, asset = object_path.split('.')
    _sc_need(package.rsplit('/', 1)[-1] == asset, 'Canonical asset/package identity required')
    return _SC_CONTENT / (package[len('/Game/'):] + '.uasset')


def _sc_disk(object_path):
    path = _sc_package_path(object_path)
    with path.open('rb') as stream:
        data = stream.read(16 * 1024 * 1024 + 1)
    _sc_need(0 < len(data) <= 16 * 1024 * 1024, 'Sequence package exceeds bounded file receipt')
    return {'path': str(path), 'bytes': len(data), 'sha256': _sc_hashlib.sha256(data).hexdigest()}


def _sc_exact_key(rows, edit, display_rate, tick_resolution, expected):
    """Pure exact lookup against factual flat key rows; never creates a key."""
    _sc_need(isinstance(edit, dict) and type(edit.get('frame_display')) is int and 0 <= edit['frame_display'] < 180,
             'Edit must name one existing display frame0..179')
    _sc_need(edit.get('channel') in ('Location.X', 'Translation.X'), 'Only an actual translation X channel is owned')
    _sc_need(isinstance(edit.get('binding_guid'), str) and _sc_re.fullmatch(r'[0-9a-f]{32}', edit['binding_guid'])
             and int(edit['binding_guid'], 16) != 0, 'Exact nonzero camera binding GUID required')
    for rate in (display_rate, tick_resolution):
        _sc_need(isinstance(rate, list) and len(rate) == 2 and all(type(x) is int and 0 < x <= 1000000 for x in rate), 'Exact rational key-time conversion required')
    tick = _sc_Fraction(edit['frame_display'] * tick_resolution[0] * display_rate[1], tick_resolution[1] * display_rate[0])
    _sc_need(tick.denominator == 1, 'Existing display key must map exactly to an integer tick')
    matches = [row for row in rows if row.get('binding_guid') == edit['binding_guid']
               and row.get('channel') == edit['channel'] and row.get('tick_frame') == tick.numerator
               and type(row.get('tick_frame')) is int and type(row.get('sub_frame')) in (int, float) and row['sub_frame'] == 0]
    _sc_need(len(matches) == 1, 'Existing key identity is missing or ambiguous; no add/rekey/replay')
    selected = matches[0]
    _sc_need(_sc_finite(expected) and _sc_finite(selected.get('value')) and selected['value'] == expected,
             'Existing key value differs from independently prepared plan')
    _sc_need(selected.get('channel_class') == '/Script/SequencerScripting.MovieSceneScriptingDoubleChannel', 'Translation edit requires actual DoubleChannel')
    return selected


def _sc_public_root_cut(cut, identity, guid):
    """Admit public resolved-proxy facts, without asserting opaque-ID equality."""
    return (isinstance(cut, dict) and cut.get('resolved_proxy_valid') is True
            and cut.get('resolved_root_proxy_equal') is True and cut.get('local_binding_match') is True
            and cut.get('guid') == guid and cut.get('resolved_guid') == guid
            and cut.get('resolved_sequence') == identity and cut.get('opaque_binding_equality_invoked') is False)


def _sc_projection(sequence):
    """Thin adapter over the independently saved public-only facts helper."""
    _sc_need(callable(globals().get('public_sequence_facts')), 'Reviewed public_sequence_facts prefix is required before operation')
    observed = public_sequence_facts(sequence)
    _sc_need(observed.get('state') == 'PUBLIC_KEY_FACTS_RETAINED' and observed.get('errors') == [],
             'Public stored sequence facts are incomplete: ' + str(observed.get('errors')))
    facts = {key: _sc_copy_module.deepcopy(observed[key]) for key in
             ('identity', 'display_rate', 'tick_resolution', 'playback_range_display', 'bindings', 'root_tracks')}
    rows, cuts = [], []

    def tracks(items, binding_guid, prefix):
        for ti, item in enumerate(items):
            _sc_need(item['identity']['class'] in _SC_TRACKS and 'coverage' not in item and 'error' not in item,
                     'Unsupported track cannot claim typed preservation coverage')
            for si, section in enumerate(item['sections']):
                _sc_need(section['identity']['class'] in _SC_SECTIONS, 'Unsupported section cannot claim typed preservation coverage')
                for ci, channel in enumerate(section['channels']):
                    kind = channel['identity']['class']
                    _sc_need(kind in ('/Script/SequencerScripting.MovieSceneScriptingDoubleChannel', '/Script/SequencerScripting.MovieSceneScriptingBoolChannel') and 'coverage' not in channel,
                             'Only fully captured Double transform and Bool spawn channels are supported')
                    _sc_need(type(channel.get('has_default')) is bool and 'default' in channel, 'Actual channel default observation required')
                    # Scripting channel wrapper UObject paths are transient, not
                    # sequence data. The canonical identity is class plus name.
                    channel['identity'] = {'class': kind}
                    for ki, key in enumerate(channel['keys']):
                        _sc_need(key['index'] == ki, 'Public key index order differs')
                        when = key['tick_time']
                        rows.append({'binding_guid': binding_guid, 'channel': channel['name'], 'channel_class': kind,
                                     'tick_frame': when['frame'], 'sub_frame': when['sub_frame'], 'value': key['value'],
                                     'locator': prefix + (ti, si, ci, ki)})

    for bi, binding in enumerate(facts['bindings']):
        _sc_need(binding.get('proxy_valid') is True, 'Actual binding proxy invalid')
        tracks(binding['tracks'], binding['guid'], ('bindings', bi))
    tracks(facts['root_tracks'], None, ('root_tracks',))
    for cut in observed['camera_cuts']:
        obj = unreal.find_object(None, cut['section']['path'], follow_redirectors=False)
        _sc_need(_sc_id(obj) == cut['section'] and cut['section']['class'] == '/Script/MovieSceneTracks.MovieSceneCameraCutSection',
                 'Exact public camera-cut section is not loaded')
        native = obj.get_camera_binding_id()
        # Keep the real opaque ID untouched. Resolve through the public API;
        # no private struct field reflection or guessed local-zero fields.
        seq, bind = unreal.MovieSceneSequenceExtensions, unreal.MovieSceneBindingExtensions
        resolved = seq.resolve_binding_id(sequence, native)
        _sc_need(bind.is_valid(resolved) and _sc_prop(resolved, 'sequence') == sequence,
                 'Public camera binding resolver does not identify exact current root sequence')
        resolved_guid = _sc_guid(bind.get_id(resolved))
        proxies = [proxy for proxy in seq.get_bindings(sequence) if _sc_guid(bind.get_id(proxy)) == resolved_guid]
        _sc_need(len(proxies) == 1 and bind.is_valid(proxies[0]) and _sc_prop(proxies[0], 'sequence') == sequence,
                 'Resolved camera binding is missing or ambiguous in exact current sequence')
        # BindingProxy has an explicit reflected ScriptOperator==. Opaque
        # MovieSceneObjectBindingID does not; never infer native equality from
        # Python object identity on those structs.
        _sc_need(resolved == proxies[0], 'Resolved public proxy differs from unique current root binding')
        identity = {'guid': resolved_guid, 'resolved_proxy_valid': True,
                    'resolved_guid': resolved_guid, 'resolved_sequence': _sc_id(sequence),
                    'resolved_root_proxy_equal': True, 'local_binding_match': True,
                    'opaque_binding_equality_invoked': False,
                    'binding_proof': 'Public ResolveBindingID current-root Sequence+GUID+unique reflected BindingProxy equality; no opaque-ID equality assertion'}
        _sc_need(_sc_public_root_cut(cut, _sc_id(sequence), resolved_guid),
                 'Public helper camera root/proxy proof changed while reading')
        local_id = seq.get_binding_id(sequence, proxies[0])
        cuts.append((native, identity, cut['range_display'], local_id))
    _sc_json.dumps(facts, allow_nan=False)
    return {'facts': facts, 'rows': rows, 'cuts': cuts, 'inventory': observed['observed_counts']}


def _sc_rebind_key(sequence, chosen):
    """Rebind one proven stored key through public native handles, then verify."""
    _, bi, ti, si, ci, ki = chosen['locator']
    seq, bind = unreal.MovieSceneSequenceExtensions, unreal.MovieSceneBindingExtensions
    track, section = unreal.MovieSceneTrackExtensions, unreal.MovieSceneSectionExtensions
    bindings = seq.get_bindings(sequence)
    _sc_need(len(bindings) <= 64 and 0 <= bi < len(bindings), 'Binding handle index unavailable')
    binding = bindings[bi]
    _sc_need(_sc_guid(bind.get_id(binding)) == chosen['binding_guid'] and bind.is_valid(binding), 'Selected binding handle differs')
    tracks = bind.get_tracks(binding)
    _sc_need(len(tracks) <= 128 and 0 <= ti < len(tracks) and _sc_id(tracks[ti])['class'] == '/Script/MovieSceneTracks.MovieScene3DTransformTrack',
             'Selected key is not in exact transform track')
    sections = track.get_sections(tracks[ti])
    _sc_need(len(sections) <= 256 and 0 <= si < len(sections), 'Selected section handle unavailable')
    channels = section.get_all_channels(sections[si])
    _sc_need(len(channels) <= 512 and 0 <= ci < len(channels), 'Selected channel handle unavailable')
    channel = channels[ci]
    _sc_need(_sc_id(channel)['class'] == chosen['channel_class'] and str(_sc_prop(channel, 'channel_name')) == chosen['channel'],
             'Selected channel handle differs')
    count = channel.get_num_keys()
    _sc_need(type(count) is int and 0 <= count <= 512, 'Selected key handle count exceeded')
    keys = channel.get_keys()
    _sc_need(len(keys) == count and 0 <= ki < count, 'Selected existing key handle unavailable')
    key = keys[ki]
    when = key.get_time(unreal.MovieSceneTimeUnit.TICK_RESOLUTION)
    _sc_need(_sc_prop(_sc_prop(when, 'frame_number'), 'value') == chosen['tick_frame']
             and _sc_prop(when, 'sub_frame') == chosen['sub_frame'] and key.get_value() == chosen['value'],
             'Selected exact key handle/time/value differs from actual stored projection')
    return key


def _sc_other_hash(projection, selected):
    canonical = _sc_copy_module.deepcopy(projection['facts'])
    location = selected['locator']
    _sc_need(location[0] == 'bindings' and len(location) == 6, 'Target key must be in exact bound transform track')
    _, bi, ti, si, ci, ki = location
    row = canonical['bindings'][bi]['tracks'][ti]['sections'][si]['channels'][ci]['keys'][ki]
    _sc_need(row['value'] == selected['value'], 'Canonical exact key location differs')
    row['value'] = '<ONLY_DECLARED_KEY_VALUE_EXCLUDED>'
    return _sc_digest(canonical)


def _sc_restore_selection_camera():
    selected = _sc_actor_api.get_selected_level_actors()
    if sorted(x.get_path_name() for x in selected) != sorted(x.get_path_name() for x in _sc_original_selection):
        _sc_actor_api.set_selected_level_actors(_sc_original_selection)
        record('OWNED_SEQUENCE_SELECTION_RESTORED', {'actors': [x.get_path_name() for x in _sc_original_selection]})
    location, rotation = _sc_editor_api.get_level_viewport_camera_info()
    current = {'location': [location.x, location.y, location.z], 'rotation': [rotation.pitch, rotation.yaw, rotation.roll]}
    if current != before['camera']:
        _sc_editor_api.set_level_viewport_camera_info(_sc_original_camera[0], _sc_original_camera[1])
        record('OWNED_SEQUENCE_VIEWPORT_RESTORED', {'camera': before['camera']})


def _sc_evaluate(sequence, camera_binding, local_binding):
    library = unreal.LevelSequenceEditorBlueprintLibrary
    for method in ('get_current_level_sequence', 'get_focused_level_sequence', 'open_level_sequence', 'close_level_sequence',
                   'pause', 'is_camera_cut_locked_to_viewport', 'set_lock_camera_cut_to_viewport', 'set_global_position', 'get_bound_objects'):
        _sc_need(callable(getattr(library, method, None)), 'Missing installed Sequencer editor API: ' + method)
    _sc_need(callable(globals().get('public_sequence_facts')), 'Reviewed public-only facts helper prefix is required')
    samples, opened, old_lock = [], False, None
    try:
        _sc_need(library.get_current_level_sequence() is None and library.get_focused_level_sequence() is None,
                 'Sequencer context appeared before owned evaluation')
        record('OWNED_SEQUENCE_EDITOR_OPEN_INTENT', {'copy': plan['copy_sequence']})
        opened = bool(library.open_level_sequence(sequence))
        _sc_need(opened and library.get_current_level_sequence() == sequence and library.get_focused_level_sequence() == sequence,
                 'Owned sequence editor did not become exact current/focused context')
        old_lock = bool(library.is_camera_cut_locked_to_viewport())
        library.pause()
        library.set_lock_camera_cut_to_viewport(False)
        for frame in _SC_FRAMES:
            params = unreal.MovieSceneSequencePlaybackParams()
            params.set_editor_property('frame', unreal.FrameTime(unreal.FrameNumber(frame)))
            params.set_editor_property('position_type', unreal.MovieScenePositionType.FRAME)
            params.set_editor_property('update_method', unreal.UpdatePositionMethod.JUMP)
            library.set_global_position(params, unreal.MovieSceneTimeUnit.DISPLAY_RATE)
            _sc_need(library.get_current_level_sequence() == sequence and library.get_focused_level_sequence() == sequence,
                     'Owned evaluation context changed')
            objects = library.get_bound_objects(camera_binding)
            local_objects = library.get_bound_objects(local_binding)
            _sc_need(len(objects) == len(local_objects) == 1 and _sc_id(objects[0]) == _sc_id(local_objects[0]),
                     'Opaque camera cut and canonical local binding do not resolve the same actual object')
            _sc_need(len(objects) == 1 and objects[0].get_class().get_path_name() == '/Script/CinematicCamera.CineCameraActor',
                     'Exact camera binding did not resolve one CineCameraActor')
            value = objects[0].get_actor_location()
            point = [value.x, value.y, value.z]
            _sc_need(all(_sc_finite(x) for x in point), 'Nonfinite evaluated camera location')
            samples.append({'frame_display': frame, 'binding_guid': plan['edit']['binding_guid'],
                            'evaluated': True, 'location_cm': point})
        _sc_need(len({tuple(x['location_cm']) for x in samples}) > 1, 'Owned sequence did not produce actual evaluated motion')
        return samples
    finally:
        if library.get_current_level_sequence() == sequence:
            try:
                if old_lock is not None:
                    library.set_lock_camera_cut_to_viewport(old_lock)
            finally:
                library.close_level_sequence()
        _sc_restore_selection_camera()


def _sc_copy_snapshot(sequence, edited):
    projection = _sc_projection(sequence)
    facts = projection['facts']
    chosen = _sc_exact_key(projection['rows'], plan['edit'], facts['display_rate'], facts['tick_resolution'],
                           plan['edit']['after' if edited else 'before'])
    matching_cuts = [x for x in projection['cuts'] if x[1]['guid'] == plan['edit']['binding_guid']]
    _sc_need(len(projection['cuts']) == len(matching_cuts) == 1, 'Exactly one unchanged camera-cut binding required')
    native, cut, bounds, local_binding = matching_cuts[0]
    _sc_need(cut['resolved_proxy_valid'] is True and cut['local_binding_match'] is True
             and cut['resolved_sequence'] == _sc_id(sequence), 'Camera binding must publicly resolve to exact current root sequence')
    _sc_need(all(type(v) is int for v in bounds) and bounds[0] <= 0 and bounds[1] >= 180, 'Camera cut must cover all requested frames')
    samples = _sc_evaluate(sequence, native, local_binding)
    protected = snapshot()
    qualify(protected)
    _sc_need(all(protected[k] == before[k] for k in _SC_FIELDS), 'Protected nine-field state changed during owned evaluation')
    _sc_need(unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence() is None
             and unreal.LevelSequenceEditorBlueprintLibrary.get_focused_level_sequence() is None, 'Owned Sequencer context remains open')
    package = _sc_disk(plan['copy_sequence'])
    output = {'class': facts['identity']['class'], 'path': facts['identity']['path'],
              'pid': process_generation['pid'], 'project_path': process_generation['project_path'],
              'process_started_utc': process_generation['process_started_utc'],
              'observed_utc': _sc_datetime.datetime.now(_sc_datetime.timezone.utc).isoformat(),
              'display_rate': facts['display_rate'], 'tick_resolution': facts['tick_resolution'],
              'playback_range_display': facts['playback_range_display'],
              'camera_cut_binding_guid': cut['guid'], 'binding_valid': True, 'binding_ambiguous': False,
              'key': {'binding_guid': chosen['binding_guid'], 'channel': chosen['channel'],
                      'frame_display': plan['edit']['frame_display'], 'existing_key_count': 1, 'value': chosen['value']},
              'evaluated_camera_samples': samples, 'package_sha256': package['sha256'],
              'opaque_and_canonical_local_camera_objects_equal': True,
              'other_sequence_data_sha256': _sc_other_hash(projection, chosen),
              'protected_state_sha256': _sc_digest({k: protected[k] for k in _SC_FIELDS})}
    return output, projection, chosen, package


result = {'schema': 'daedalus.named-sequence-acceptance.v1', 'plan_id': plan.get('plan_id'),
          'native_invoked': True, 'state': 'HELD', 'errors': [], 'copy_existed_before': None,
          'source_package_before': None, 'source_package_after': None, 'saved_packages': [],
          'save_attempts': [], 'duplicate_attempted': False, 'duplicate_returned_exact_copy': False,
          'key_edit_attempted': False, 'key_edit_count': 0, 'normal_close': False, 'normal_release': False,
          'fresh_process_reopen': False, 'sequence_accepted': False, 'native_runtime_qualified': False,
          'metadata_coverage': 'Bounded public typed rates/range, binding IDs/names/validity, supported track/section identities/ranges, Double transform and Bool spawn channel names/classes/defaults/keys/tangents. No templates, protected properties, full serialization or all object properties.',
          'other_data_exclusion': 'Exactly the declared key value in that bounded typed projection; no other projected field excluded.',
          'sample_frames_display': list(_SC_FRAMES), 'explicit_asset_load_requests': 0,
          'implicit_engine_loads_attested': False,
          'resolver_cache_boundary': 'ResolveBindingID may compile MovieScene cached evaluation data; no shader/UBT compile or no-cache claim.',
          'allowlisted_copy_only': True}
_sc_actor_api = _sc_editor_api = None
_sc_original_selection = _sc_original_camera = None
_sc_copy = None
try:
    _sc_need(plan.get('schema') == 'daedalus.named-sequence-acceptance.v1'
             and plan.get('source_sequence') == _SC_SOURCE and plan.get('source_package_sha256') == _SC_SOURCE_SHA
             and plan.get('capture_job_sha256') == _SC_JOB_SHA and plan.get('requested_frames') == [0, 180]
             and plan.get('expected_display_rate') == [30, 1]
             and plan.get('plan_id') == _sc_digest({k: v for k, v in plan.items() if k != 'plan_id'}), 'Exact validated sequence plan required')
    _sc_need(plan['copy_sequence'].startswith(_SC_COPY_ROOT) and plan['copy_sequence'] != _SC_SOURCE, 'Fresh owned namespace required')
    copy_file = _sc_package_path(plan['copy_sequence'])
    _sc_need(_sc_finite(plan['edit'].get('before')) and _sc_finite(plan['edit'].get('after'))
             and plan['edit']['after'] - plan['edit']['before'] == 100, 'Exactly one explicit translation X +100cm edit required')
    _sc_need(process_generation['pid'] == _sc_os.getpid() and process_generation['project_path'] == _SC_PROJECT
             and isinstance(process_generation['process_started_utc'], str), 'Current independently supplied process generation required')
    qualify(before)
    library = unreal.LevelSequenceEditorBlueprintLibrary
    for method in ('get_current_level_sequence', 'get_focused_level_sequence', 'open_level_sequence', 'close_level_sequence',
                   'pause', 'is_camera_cut_locked_to_viewport', 'set_lock_camera_cut_to_viewport', 'set_global_position', 'get_bound_objects'):
        _sc_need(callable(getattr(library, method, None)), 'Missing installed Sequencer editor API before duplicate: ' + method)
    _sc_need(callable(globals().get('public_sequence_facts')), 'Reviewed public-only facts helper prefix is required before duplicate')
    _sc_need(library.get_current_level_sequence() is None and library.get_focused_level_sequence() is None,
             'Existing Sequencer context unsupported by this bounded adapter; HOLD before duplicate')
    _sc_actor_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    _sc_editor_api = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    _sc_original_selection = list(_sc_actor_api.get_selected_level_actors())
    _sc_original_camera = _sc_editor_api.get_level_viewport_camera_info()
    _sc_need(len(_sc_original_selection) <= 4096 and len(_sc_original_camera) == 2, 'Existing selection/viewport restoration unavailable')
    source = unreal.find_object(None, _SC_SOURCE, follow_redirectors=False)
    _sc_need(_sc_id(source) == {'path': _SC_SOURCE, 'class': '/Script/LevelSequence.LevelSequence'}, 'Exact original sequence must already be admitted/loaded')
    source_pin = _sc_disk(_SC_SOURCE)
    _sc_need(source_pin['sha256'] == _SC_SOURCE_SHA, 'Original sequence bytes differ before operation')
    result['source_package_before'] = source_pin['sha256']
    source_projection = _sc_projection(source)
    source_facts = source_projection['facts']
    _sc_need(source_facts['display_rate'] == [30, 1] and all(type(v) is int for v in source_facts['playback_range_display'])
             and source_facts['playback_range_display'][0] <= 0 and source_facts['playback_range_display'][1] >= 180,
             'Actual source rate/range differs from prepared plan')
    _sc_exact_key(source_projection['rows'], plan['edit'], source_facts['display_rate'], source_facts['tick_resolution'], plan['edit']['before'])
    _sc_need(len(source_projection['cuts']) == 1, 'Actual source needs one camera cut before duplication')
    _, source_cut, source_cut_range, _ = source_projection['cuts'][0]
    _sc_need(source_cut['guid'] == plan['edit']['binding_guid'] and source_cut['resolved_proxy_valid'] is True
             and source_cut['local_binding_match'] is True and source_cut['resolved_sequence'] == _sc_id(source)
             and all(type(v) is int for v in source_cut_range) and source_cut_range[0] <= 0 and source_cut_range[1] >= 180,
             'Source camera-cut identity/range differs before duplication')
    result['original_typed_projection_sha256_before'] = _sc_digest(source_facts)
    exists = unreal.EditorAssetLibrary.does_asset_exist(plan['copy_sequence'].split('.')[0])
    result['copy_existed_before'] = bool(exists or any(copy_file.with_suffix(ext).exists() for ext in ('.uasset', '.uexp', '.ubulk')))
    _sc_need(result['copy_existed_before'] is False, 'Owned package already exists; no duplicate/replay/overwrite')
    result['native_invoked'] = True
    record('OWNED_SEQUENCE_DUPLICATE_INTENT', {'plan_id': plan['plan_id'], 'source': _SC_SOURCE, 'copy': plan['copy_sequence'], 'source_sha256': _SC_SOURCE_SHA})
    result['duplicate_attempted'] = True
    _sc_copy = unreal.EditorAssetLibrary.duplicate_asset(_SC_SOURCE.split('.')[0], plan['copy_sequence'].split('.')[0])
    _sc_need(_sc_id(_sc_copy) == {'path': plan['copy_sequence'], 'class': '/Script/LevelSequence.LevelSequence'}, 'Duplication did not return exact owned LevelSequence; reconcile without replay')
    result['duplicate_returned_exact_copy'] = True
    for phase in ('baseline', 'edited'):
        if phase == 'edited':
            fresh = _sc_projection(_sc_copy)
            chosen = _sc_exact_key(fresh['rows'], plan['edit'], fresh['facts']['display_rate'], fresh['facts']['tick_resolution'], plan['edit']['before'])
            _sc_need(_sc_other_hash(fresh, chosen) == result['before_edit']['other_sequence_data_sha256'], 'Other projected sequence data changed before key edit')
            record('OWNED_SEQUENCE_ONE_KEY_EDIT_INTENT', {'plan_id': plan['plan_id'], 'edit': plan['edit']})
            result['key_edit_attempted'] = True
            _sc_rebind_key(_sc_copy, chosen).set_value(plan['edit']['after'])
            result['key_edit_count'] = 1
        record('OWNED_SEQUENCE_SAVE_INTENT', {'phase': phase, 'package': plan['copy_sequence'].split('.')[0]})
        saved = unreal.EditorAssetLibrary.save_loaded_asset(_sc_copy, only_if_is_dirty=False)
        result['save_attempts'].append({'phase': phase, 'package': plan['copy_sequence'].split('.')[0], 'saved': saved})
        _sc_need(saved is True, 'Owned copy save returned false; preserve current work, no retry')
        result['saved_packages'] = [plan['copy_sequence'].split('.')[0]]
        if phase == 'edited':
            # Actual effectful duplicate/edit/save work is known terminal before
            # its later evaluated readback observation, as the consumer requires.
            result['operation_terminal_utc'] = _sc_datetime.datetime.now(_sc_datetime.timezone.utc).isoformat()
            record('OWNED_SEQUENCE_EDIT_SAVE_KNOWN_TERMINAL', {'utc': result['operation_terminal_utc'], 'saved': True})
        value, projection, chosen, disk = _sc_copy_snapshot(_sc_copy, phase == 'edited')
        result['before_edit' if phase == 'baseline' else 'after_edit'] = value
        result['baseline_saved_file' if phase == 'baseline' else 'edited_saved_file'] = disk
        if phase == 'edited':
            _sc_need(value['other_sequence_data_sha256'] == result['before_edit']['other_sequence_data_sha256'], 'Unrelated bounded typed sequence projection changed')
            _sc_need(any(a['location_cm'] != b['location_cm'] for a, b in zip(result['before_edit']['evaluated_camera_samples'], value['evaluated_camera_samples'])),
                     'Changed key did not change actual camera location at common sample frames')
    result['source_package_after'] = _sc_disk(_SC_SOURCE)['sha256']
    result['original_typed_projection_sha256_after'] = _sc_digest(_sc_projection(source)['facts'])
    _sc_need(result['source_package_after'] == _SC_SOURCE_SHA
             and result['original_typed_projection_sha256_after'] == result['original_typed_projection_sha256_before'], 'Original sequence bytes or bounded facts changed')
    result['state'] = 'AWAITING_FRESH_REOPEN'
except Exception as _sc_error:
    result['errors'].append(type(_sc_error).__name__ + ': ' + str(_sc_error))
    result['state'] = 'HELD'
finally:
    if _sc_actor_api is not None and _sc_editor_api is not None and _sc_original_selection is not None and _sc_original_camera is not None:
        try:
            _sc_restore_selection_camera()
        except Exception as _sc_cleanup_error:
            result['errors'].append('Restoration: ' + type(_sc_cleanup_error).__name__ + ': ' + str(_sc_cleanup_error))
            result['state'] = 'HELD'
    try:
        result['source_package_after'] = _sc_disk(_SC_SOURCE)['sha256']
        _sc_need(result['source_package_after'] == _SC_SOURCE_SHA, 'Original package differs at actual terminal')
        if result['duplicate_returned_exact_copy'] and _sc_package_path(plan['copy_sequence']).exists():
            result['copy_saved_file_at_terminal'] = _sc_disk(plan['copy_sequence'])
    except Exception as _sc_pin_error:
        result['errors'].append('Terminal disk pins: ' + type(_sc_pin_error).__name__ + ': ' + str(_sc_pin_error))
        result['state'] = 'HELD'
    try:
        _sc_after = snapshot()
        result['after'] = _sc_after
        result['preservation'] = {k: _sc_after.get(k) == before.get(k) for k in _SC_FIELDS}
        result['preserved'] = all(result['preservation'].values())
        qualify(_sc_after)
        _sc_need(result['preserved'], 'Final protected nine-field state differs')
    except Exception as _sc_final_error:
        result['errors'].append('Final state: ' + type(_sc_final_error).__name__ + ': ' + str(_sc_final_error))
        result['state'] = 'HELD'
    record('OWNED_SEQUENCE_OPERATION_KNOWN_TERMINAL', {'state': result['state'], 'errors': result['errors'],
                                                    'duplicate_attempted': result['duplicate_attempted'],
                                                    'key_edit_count': result['key_edit_count'], 'saved_packages': result['saved_packages']})
