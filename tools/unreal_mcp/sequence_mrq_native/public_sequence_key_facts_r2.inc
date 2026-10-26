# Source-only callback body for main's existing n.run nine-field guard.
# Substitute repr(host UUID) / repr(fresh absolute raw filename) for placeholders.
# Public loaded-object readers only. No old reader execution, loads, templates,
# private MovieScene properties, UI, evaluation, setters, saves, or MRQ calls.
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_pk_target = '/Game/YTM/Seq/WB_Flythrough_YTMIsland.WB_Flythrough_YTMIsland'
_pk_package = Path('C:/Unreal/DaedalusRealm/Content/YTM/Seq/WB_Flythrough_YTMIsland.uasset')
_pk_sha = '10af7554917cf73c7d67882c65e01ffffc9a78b876395f9278adf3529957d076'
_pk_limits = {'bindings': 64, 'tracks': 128, 'sections': 256, 'channels': 512, 'keys': 4096, 'keys_per_channel': 512}
def _pk_need(value, message):
    if not value:
        raise RuntimeError(message)


def _pk_id(obj):
    return None if obj is None else {'path': str(obj.get_path_name()), 'class': str(obj.get_class().get_path_name())}


def _pk_prop(obj, name):
    return obj.get_editor_property(name)


def _pk_int(value):
    _pk_need(type(value) is int, 'Actual integer field required')
    return value


def _pk_num(value):
    _pk_need(type(value) in (int, float) and math.isfinite(value), 'Actual finite numeric field required')
    return value


def _pk_guid(value):
    return ''.join('%08x' % (_pk_int(_pk_prop(value, k)) & 0xffffffff) for k in ('a', 'b', 'c', 'd'))


def _pk_rate(value):
    row = [_pk_int(_pk_prop(value, 'numerator')), _pk_int(_pk_prop(value, 'denominator'))]
    _pk_need(all(0 < x <= 1000000 for x in row), 'Invalid rational rate')
    return row


def _pk_disk():
    with _pk_package.open('rb') as stream:
        body = stream.read(16 * 1024 * 1024 + 1)
    _pk_need(0 < len(body) <= 16 * 1024 * 1024, 'Exact package file bound exceeded')
    pin = {'path': str(_pk_package), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    _pk_need(pin['sha256'] == _pk_sha, 'Original WB package pin differs')
    return pin


def _pk_time(key, unit):
    when = key.get_time(unit)
    return {'frame': _pk_int(_pk_prop(_pk_prop(when, 'frame_number'), 'value')),
            'sub_frame': _pk_num(_pk_prop(when, 'sub_frame'))}


def public_sequence_facts(sequence):
    """Public loaded-sequence metadata only. No loads/writes/UI/evaluation.

    Reusable for an actual owned copy. This projection does not contain native
    handles, all serialized object properties, or adoption/preservation proof.
    """
    _pk_counts = {k: 0 for k in _pk_limits if k != 'keys_per_channel'}

    def _pk_rows(kind, rows):
        _pk_need(len(rows) <= _pk_limits[kind], kind + ' per-call limit exceeded')
        _pk_counts[kind] += len(rows)
        _pk_need(_pk_counts[kind] <= _pk_limits[kind], kind + ' cumulative limit exceeded')
        return rows

    _pk_facts = {'schema': 'daedalus.public-sequence-key-facts.v2', 'started_utc': datetime.now(timezone.utc).isoformat(), 'target': str(sequence.get_path_name()),
                 'limits': _pk_limits, 'bindings': [], 'root_tracks': [], 'camera_cuts': [],
                 'errors': [], 'load_calls': 0, 'mutation_calls': 0, 'evaluation_calls': 0,
                 'object_template_lookup_calls': 0, 'native_runtime_qualified': False,
                 'binding_resolution_side_effect_scope': 'Public ResolveBindingID may update MovieScene compiled hierarchy cache; no asset setters/saves, no shader or UBT build'}
    try:
        _pk_seq = sequence
        _pk_need(_pk_id(_pk_seq) is not None and _pk_id(_pk_seq)['class'] == '/Script/LevelSequence.LevelSequence', 'Actual loaded LevelSequence argument required')
        _pk_api = {}
        for _pk_name in ('MovieSceneSequenceExtensions', 'MovieSceneBindingExtensions', 'MovieSceneTrackExtensions', 'MovieSceneSectionExtensions'):
            _pk_need(unreal.find_object(None, '/Script/SequencerScripting.' + _pk_name, follow_redirectors=False) is not None, 'Required scripting class is not loaded: ' + _pk_name)
            _pk_api[_pk_name] = getattr(unreal, _pk_name, None)
            _pk_need(_pk_api[_pk_name] is not None, 'Required Python class is not exposed: ' + _pk_name)
        _pk_s = _pk_api['MovieSceneSequenceExtensions']
        _pk_b = _pk_api['MovieSceneBindingExtensions']
        _pk_t = _pk_api['MovieSceneTrackExtensions']
        _pk_c = _pk_api['MovieSceneSectionExtensions']
        _pk_unit = unreal.MovieSceneTimeUnit
        _pk_facts.update(identity=_pk_id(_pk_seq), display_rate=_pk_rate(_pk_s.get_display_rate(_pk_seq)),
                         tick_resolution=_pk_rate(_pk_s.get_tick_resolution(_pk_seq)),
                         playback_range_display=[_pk_int(_pk_s.get_playback_start(_pk_seq)), _pk_int(_pk_s.get_playback_end(_pk_seq))],
                         playback_precision='Installed integer display getters; not a sub-display-frame assertion')

        def _pk_tracks(tracks, binding_guid):
            output = []
            for item in _pk_rows('tracks', tracks):
                row = {'identity': _pk_id(item), 'sections': []}
                output.append(row)
                kind = row['identity']['class']
                if kind not in ('/Script/MovieSceneTracks.MovieScene3DTransformTrack', '/Script/MovieSceneTracks.MovieSceneCameraCutTrack', '/Script/MovieScene.MovieSceneSpawnTrack'):
                    row['coverage'] = 'Identity only; not an edit target'
                    continue
                try:
                    for child in _pk_rows('sections', _pk_t.get_sections(item)):
                        data = {'identity': _pk_id(child), 'channels': [],
                                'range_display': [_pk_c.get_start_frame(child) if _pk_c.has_start_frame(child) else None,
                                                  _pk_c.get_end_frame(child) if _pk_c.has_end_frame(child) else None]}
                        row['sections'].append(data)
                        if data['identity']['class'] == '/Script/MovieSceneTracks.MovieSceneCameraCutSection':
                            camera_id = child.get_camera_binding_id()
                            # Public resolver compiles the MovieScene evaluation hierarchy;
                            # this is disclosed cached-data work, never shader/UBT compilation.
                            resolved = _pk_s.resolve_binding_id(_pk_seq, camera_id)
                            resolved_sequence = _pk_prop(resolved, 'sequence')
                            resolved_guid = _pk_guid(_pk_b.get_id(resolved))
                            resolved_valid = bool(_pk_b.is_valid(resolved))
                            root_matches = [proxy for proxy in _pk_all_bindings if _pk_guid(_pk_b.get_id(proxy)) == resolved_guid]
                            proxy_equal = bool(len(root_matches) == 1 and resolved == root_matches[0])
                            cut = {'section': data['identity'], 'range_display': data['range_display'],
                                   'guid': _pk_guid(_pk_prop(camera_id, 'guid')),
                                   'resolved_guid': resolved_guid,
                                   'resolved_sequence': _pk_id(resolved_sequence),
                                   'resolved_proxy_valid': resolved_valid,
                                   'resolved_root_proxy_equal': proxy_equal,
                                   'opaque_binding_equality_invoked': False,
                                   'local_binding_match': bool(resolved_valid and resolved_sequence == _pk_seq
                                       and resolved_guid == _pk_guid(_pk_prop(camera_id, 'guid')) and proxy_equal),
                                   'proof': 'Public ResolveBindingID; valid resolved proxy with exact root Sequence/GUID and reflected BindingProxy equality to the unique enumerated root binding. Opaque binding-space equality is not claimed',
                                   'resolver_evaluation_hierarchy_compile_requested': True}
                            data['camera_binding'] = cut
                            _pk_facts['camera_cuts'].append(cut)
                            continue
                        for channel in _pk_rows('channels', _pk_c.get_all_channels(child)):
                            ch = {'identity': _pk_id(channel), 'name': str(_pk_prop(channel, 'channel_name')), 'keys': []}
                            data['channels'].append(ch)
                            if ch['identity']['class'] not in ('/Script/SequencerScripting.MovieSceneScriptingDoubleChannel', '/Script/SequencerScripting.MovieSceneScriptingBoolChannel'):
                                ch['coverage'] = 'Other channel identity only; not an edit target'
                                continue
                            is_double = ch['identity']['class'] == '/Script/SequencerScripting.MovieSceneScriptingDoubleChannel'
                            has_default = channel.has_default()
                            _pk_need(type(has_default) is bool, 'Actual channel default-presence Bool required')
                            ch['has_default'] = has_default
                            default_value = channel.get_default() if has_default else None
                            if has_default:
                                if is_double:
                                    _pk_num(default_value)
                                else:
                                    _pk_need(type(default_value) is bool, 'Actual Spawn Bool default required')
                            ch['default'] = default_value
                            count = _pk_int(channel.get_num_keys())
                            _pk_need(0 <= count <= _pk_limits['keys_per_channel'], 'Typed channel key count exceeded before get_keys')
                            keys = _pk_rows('keys', channel.get_keys())
                            _pk_need(len(keys) == count, 'Typed channel key count changed')
                            for index, key in enumerate(keys):
                                key_value = key.get_value()
                                if is_double:
                                    _pk_num(key_value)
                                else:
                                    _pk_need(type(key_value) is bool, 'Actual Spawn Bool key value required')
                                kr = {'index': index, 'tick_time': _pk_time(key, _pk_unit.TICK_RESOLUTION),
                                      'display_time': _pk_time(key, _pk_unit.DISPLAY_RATE), 'value': key_value}
                                if is_double:
                                    for method in ('get_interpolation_mode', 'get_tangent_mode', 'get_arrive_tangent', 'get_leave_tangent', 'get_arrive_tangent_weight', 'get_leave_tangent_weight'):
                                        value = getattr(key, method)()
                                        kr[method[4:]] = _pk_num(value) if type(value) in (int, float) else str(value)
                                ch['keys'].append(kr)
                except Exception as error:
                    row['error'] = type(error).__name__ + ': ' + str(error)[:1024]
                    _pk_facts['errors'].append({'binding_guid': binding_guid, 'track': row['identity'], 'error': row['error']})
            return output

        _pk_seen = set()
        _pk_all_bindings = _pk_rows('bindings', _pk_s.get_bindings(_pk_seq))
        for _pk_binding in _pk_all_bindings:
            _pk_identifier = _pk_guid(_pk_b.get_id(_pk_binding))
            _pk_need(_pk_identifier != '0' * 32 and _pk_identifier not in _pk_seen, 'Zero/duplicate binding GUID')
            _pk_seen.add(_pk_identifier)
            _pk_row = {'guid': _pk_identifier, 'name': str(_pk_b.get_name(_pk_binding)),
                       'display_name': str(_pk_b.get_display_name(_pk_binding)), 'proxy_valid': bool(_pk_b.is_valid(_pk_binding))}
            _pk_facts['bindings'].append(_pk_row)
            _pk_row['tracks'] = _pk_tracks(_pk_b.get_tracks(_pk_binding), _pk_identifier)
        _pk_facts['root_tracks'] = _pk_tracks(_pk_s.get_tracks(_pk_seq), None)
        _pk_cut_guids = sorted({cut['guid'] for cut in _pk_facts['camera_cuts']})
        _pk_facts['camera_cut_guids'] = _pk_cut_guids
        _pk_facts['unique_local_camera_cut_binding'] = bool(len(_pk_cut_guids) == 1 and _pk_cut_guids[0] in _pk_seen
            and all(cut['local_binding_match'] for cut in _pk_facts['camera_cuts']))
    except Exception as _pk_error:
        _pk_facts['errors'].append(type(_pk_error).__name__ + ': ' + str(_pk_error)[:1024])
    _pk_facts.update(observed_counts=_pk_counts, returned_utc=datetime.now(timezone.utc).isoformat(),
                     coverage='Public bindings/cut resolution, transform Double and Spawn Bool stored keys/defaults. No templates or evaluated motion. Other track/channel identities only.')
    _pk_facts['state'] = 'PUBLIC_KEY_FACTS_RETAINED' if not _pk_facts['errors'] else 'HELD_INCOMPLETE_FACTS'
    return _pk_facts


# ENTRY: main may exec only the definitions prefix to reuse the pure reader.
_pk_capture = __CAPTURE_ID__
_pk_output = Path(__RAW_FACTS_PATH__)
if sys.modules.get('unreal') is not unreal:
    raise RuntimeError('Actual admitted Unreal module required')
if not _pk_output.is_absolute() or _pk_output.is_symlink() or _pk_output.exists() or not _pk_output.parent.is_dir():
    raise RuntimeError('Fresh admitted absolute output path required')
_pk_disk_before = _pk_disk()
_pk_original = unreal.find_object(None, _pk_target, follow_redirectors=False)
_pk_need(_pk_id(_pk_original) == {'path': _pk_target, 'class': '/Script/LevelSequence.LevelSequence'}, 'Exact original LevelSequence is not already loaded')
_pk_facts = public_sequence_facts(_pk_original)
_pk_facts['capture_id'] = _pk_capture
_pk_disk_after = None
try:
    _pk_disk_after = _pk_disk()
except Exception as _pk_error:
    _pk_facts['errors'].append('package-after: ' + type(_pk_error).__name__ + ': ' + str(_pk_error)[:512])
_pk_facts.update(package_before=_pk_disk_before, package_after=_pk_disk_after,
                 original_package_unchanged=_pk_disk_before is not None and _pk_disk_before == _pk_disk_after,
                 returned_utc=datetime.now(timezone.utc).isoformat(),
                 coverage='Public bindings/cut resolution, transform Double and Spawn Bool stored keys/defaults. No templates or evaluated motion. Other track/channel identities only.')
_pk_facts['state'] = 'PUBLIC_KEY_FACTS_RETAINED' if not _pk_facts['errors'] else 'HELD_INCOMPLETE_FACTS'
_pk_raw = json.dumps(_pk_facts, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
if len(_pk_raw) > 262144:
    raise RuntimeError('Fact payload exceeds 256KiB; no accepted truncation')
with _pk_output.open('xb') as _pk_stream:
    _pk_stream.write(_pk_raw)
result = {'schema': 'daedalus.public-sequence-key-capture.v2', 'capture_id': _pk_capture,
          'raw': {'path': str(_pk_output.resolve()), 'bytes': len(_pk_raw), 'sha256': hashlib.sha256(_pk_raw).hexdigest()},
          'state': _pk_facts['state'], 'errors': _pk_facts['errors'],
          'original_package_unchanged': _pk_facts['original_package_unchanged'],
          'native_runtime_qualified': False, 'load_calls': 0, 'mutation_calls': 0, 'evaluation_calls': 0}
record('public-sequence-key-facts-returned', result)
