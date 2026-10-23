"""Focused fake-boundary checks only; no Unreal import/native acceptance."""
import hashlib
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

SOURCE = Path(__file__).with_name('public_sequence_key_facts_r2.inc')
PIN = 'db56feec01bf301fac587d2dd9def31c40a956878bbe4bfe4ee26596d5d27b65'


class Struct:
    def __init__(self, **values):
        self.values = values

    def get_editor_property(self, name):
        if name not in self.values:
            raise AssertionError('Unexpected/nonpublic property: ' + name)
        return self.values[name]


class Obj:
    def __init__(self, path, kind):
        self.path, self.kind = path, kind

    def get_path_name(self):
        return self.path

    def get_class(self):
        return NS(get_path_name=lambda: self.kind)


class Opaque(Struct):
    def __eq__(self, other):
        raise AssertionError('Opaque ID equality must never be invoked')


class Proxy(Struct):
    def __eq__(self, other):
        return isinstance(other, Proxy) and self.values == other.values


class Channel(Obj, Struct):
    def __init__(self, name, kind, keys, default):
        Obj.__init__(self, '/Transient/' + name, '/Script/SequencerScripting.MovieSceneScripting' + kind + 'Channel')
        Struct.__init__(self, channel_name=name)
        self.keys, self.default = keys, default

    def has_default(self):
        return self.default is not None

    def get_default(self):
        return self.default

    def get_num_keys(self):
        return len(self.keys)

    def get_keys(self):
        return self.keys


class Key:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def get_time(self, unit):
        return Struct(frame_number=Struct(value=0), sub_frame=0.0)

    def __getattr__(self, name):
        if name.startswith('get_'):
            return lambda: 0.0
        raise AttributeError(name)


def fixture(mode='normal'):
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN
    scope = {}
    exec(compile(raw.decode().split('# ENTRY:', 1)[0], str(SOURCE), 'exec'), scope)
    seq = Obj('/Game/Owned.Sequence', '/Script/LevelSequence.LevelSequence')
    guid = Struct(a=1, b=2, c=3, d=4)
    proxy = Proxy(sequence=seq, binding_id=guid)
    resolved = proxy
    if mode == 'foreign_sequence':
        resolved = Proxy(sequence=Obj('/Game/Foreign.Sequence', seq.kind), binding_id=guid)
    if mode == 'wrong_guid':
        resolved = Proxy(sequence=seq, binding_id=Struct(a=9, b=2, c=3, d=4))
    camera = Obj('/Game/Owned.CameraCut', '/Script/MovieSceneTracks.MovieSceneCameraCutSection')
    camera.get_camera_binding_id = lambda: Opaque(guid=guid)
    transform_section = Obj('/Game/Owned.Transform', '/Script/MovieSceneTracks.MovieScene3DTransformSection')
    spawn_section = Obj('/Game/Owned.Spawn', '/Script/MovieSceneTracks.MovieSceneBoolSection')
    transform = Obj('/Game/Owned.TransformTrack', '/Script/MovieSceneTracks.MovieScene3DTransformTrack')
    spawn = Obj('/Game/Owned.SpawnTrack', '/Script/MovieScene.MovieSceneSpawnTrack')
    cut_track = Obj('/Game/Owned.Cuts', '/Script/MovieSceneTracks.MovieSceneCameraCutTrack')
    x = Channel('Location.X', 'Double', [Key(2431.074462890625)], None)
    scale = Channel('Scale.X', 'Double', [], 1.0)
    spawned = Channel('Spawned', 'Bool', [Key(True)], False)
    sequence_api = NS(get_display_rate=lambda s: Struct(numerator=30, denominator=1),
        get_tick_resolution=lambda s: Struct(numerator=24000, denominator=1),
        get_playback_start=lambda s: 0, get_playback_end=lambda s: 360,
        get_bindings=lambda s: [proxy, proxy] if mode == 'duplicate' else [proxy],
        get_tracks=lambda s: [cut_track], resolve_binding_id=lambda s, opaque: resolved)
    binding_api = NS(get_id=lambda p: p.values['binding_id'],
        is_valid=lambda p: mode != 'invalid_proxy', get_name=lambda p: 'Camera',
        get_display_name=lambda p: 'Camera', get_tracks=lambda p: [transform, spawn])
    track_api = NS(get_sections=lambda t: [camera] if t is cut_track else [transform_section] if t is transform else [spawn_section])
    section_api = NS(has_start_frame=lambda s: True, get_start_frame=lambda s: 0,
        has_end_frame=lambda s: True, get_end_frame=lambda s: 360,
        get_all_channels=lambda s: [x, scale] if s is transform_section else [spawned])
    scope['unreal'] = NS(find_object=lambda *a, **k: object(),
        MovieSceneSequenceExtensions=sequence_api, MovieSceneBindingExtensions=binding_api,
        MovieSceneTrackExtensions=track_api, MovieSceneSectionExtensions=section_api,
        MovieSceneTimeUnit=NS(TICK_RESOLUTION='tick', DISPLAY_RATE='display'))
    return scope['public_sequence_facts'](seq)


class PublicFacts(unittest.TestCase):
    def test_public_resolution_never_reads_hidden_id_fields_or_compares_opaque(self):
        facts = fixture()
        self.assertEqual(facts['errors'], [])
        self.assertTrue(facts['unique_local_camera_cut_binding'])
        self.assertFalse(facts['camera_cuts'][0]['opaque_binding_equality_invoked'])
        self.assertTrue(facts['camera_cuts'][0]['resolver_evaluation_hierarchy_compile_requested'])

    def test_foreign_sequence_does_not_qualify(self):
        self.assertFalse(fixture('foreign_sequence')['unique_local_camera_cut_binding'])

    def test_wrong_resolved_guid_does_not_qualify(self):
        self.assertFalse(fixture('wrong_guid')['unique_local_camera_cut_binding'])

    def test_invalid_proxy_does_not_qualify(self):
        self.assertFalse(fixture('invalid_proxy')['unique_local_camera_cut_binding'])

    def test_duplicate_guid_is_held(self):
        self.assertEqual(fixture('duplicate')['state'], 'HELD_INCOMPLETE_FACTS')

    def test_double_empty_keys_default_and_spawn_bool_are_retained(self):
        facts = fixture()
        tracks = facts['bindings'][0]['tracks']
        scale = tracks[0]['sections'][0]['channels'][1]
        spawn = tracks[1]['sections'][0]['channels'][0]
        self.assertEqual((scale['keys'], scale['has_default'], scale['default']), ([], True, 1.0))
        self.assertEqual((spawn['has_default'], spawn['default'], spawn['keys'][0]['value']), (True, False, True))
        self.assertEqual(facts['playback_range_display'], [0, 360])


if __name__ == '__main__':
    unittest.main()
