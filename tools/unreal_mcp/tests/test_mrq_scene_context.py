"""Value-identity regressions; no Unreal, network, or production assets."""
import unittest
import math
import struct
from types import SimpleNamespace
from tools.unreal_mcp import mrq_scene_context as m


class Obj:
    def __init__(self, path='/Sequence', cls='/LevelSequence', **props):
        self.path, self.cls, self.props = path, cls, props

    def get_path_name(self):
        return self.path

    def get_class(self):
        return Obj(self.cls)

    def get_editor_property(self, key):
        return self.props[key]


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.seq = Obj()
        self.proxy = self.proxy_for()
        self.candidates = [self.proxy_for()]
        section = SimpleNamespace(get_camera_binding_id=lambda: 'opaque')
        track = Obj('/Cut', '/Script/MovieSceneTracks.MovieSceneCameraCutTrack')
        self.u = SimpleNamespace(
            MovieSceneBindingExtensions=SimpleNamespace(is_valid=lambda p: p.props.get('valid', True), get_id=lambda p: p.props['guid']),
            MovieSceneSequenceExtensions=SimpleNamespace(get_tracks=lambda s: [track], resolve_binding_id=lambda s, o: self.proxy,
                get_bindings=lambda s: self.candidates, get_binding_id=lambda s, p: 'local'),
            MovieSceneTrackExtensions=SimpleNamespace(get_sections=lambda t: [section]),
            MovieSceneSectionExtensions=SimpleNamespace(has_start_frame=lambda s: True, has_end_frame=lambda s: True,
                get_start_frame=lambda s: 0, get_end_frame=lambda s: 360))

    def proxy_for(self, words=(1, 2, 3, -1), sequence=None):
        return Obj(sequence=sequence or self.seq, guid=Obj(**dict(zip('abcd', words))))

    def test_distinct_wrappers_same_native_value(self):
        self.assertNotEqual(self.proxy, self.candidates[0])
        self.assertNotEqual(self.proxy.props['guid'], self.candidates[0].props['guid'])
        self.assertEqual(m.camera_binding(self.u, self.seq), ('opaque', 'local', '000000010000000200000003ffffffff'))

    def test_duplicate_identity_refused(self):
        self.candidates.append(self.proxy_for())
        with self.assertRaisesRegex(m.Held, 'ambiguous'):
            m.camera_binding(self.u, self.seq)

    def test_foreign_sequence_refused(self):
        self.candidates = [self.proxy_for(sequence=Obj('/Other'))]
        with self.assertRaisesRegex(m.Held, 'Foreign'):
            m.camera_binding(self.u, self.seq)

    def test_missing_identity_refused(self):
        self.candidates = [self.proxy_for(words=(5, 6, 7, 8))]
        with self.assertRaisesRegex(m.Held, 'missing'):
            m.camera_binding(self.u, self.seq)

    def test_malformed_and_zero_guid_refused(self):
        for words in [(0, 0, 0, 0), (True, 2, 3, 4), (2 ** 32, 2, 3, 4), (1.0, 2, 3, 4)]:
            with self.subTest(words=words), self.assertRaises(m.Held):
                m.binding_key(self.u, self.proxy_for(words), self.seq)

    def test_invalid_proxy_refused(self):
        self.proxy.props['valid'] = False
        with self.assertRaises(m.Held):
            m.camera_binding(self.u, self.seq)


class TranslationTests(unittest.TestCase):
    def rows(self):
        return [{'frame': 60 * k, 'position': [14000 * (1 - .25 * k / 6) * math.cos(math.radians(-80 + 160 * k / 6)),
                -2600000 + 14000 * (1 - .25 * k / 6) * math.sin(math.radians(-80 + 160 * k / 6)), 4100.0]} for k in range(7)]

    def test_saved_recipe_to_actual_marker(self):
        p = m.island_camera_translation(self.rows(), [130050., 105700., 100.])
        self.assertEqual(p['translation_cm'], [130050., 2705700., 0.])

    def test_exact_float32_recipe_and_small_wrong_value(self):
        rows = self.rows()
        for row in rows:
            row['position'] = [struct.unpack('<f', struct.pack('<f', v))[0] for v in row['position']]
        self.assertEqual(m.island_camera_translation(rows, [130050., 105700., 100.])['recipe_comparison'], 'exact_binary32_rounded')
        rows[0]['position'][0] += 1e-8
        with self.assertRaises(m.Held):
            m.island_camera_translation(rows, [130050., 105700., 100.])

    def test_changed_recipe_refused(self):
        rows = self.rows(); rows[3]['position'][0] += 1
        with self.assertRaises(m.Held):
            m.island_camera_translation(rows, [0, 0, 0])

    def test_wrong_time_or_missing_key_refused(self):
        for rows in [self.rows()[:-1], list(reversed(self.rows()))]:
            with self.assertRaises(m.Held):
                m.island_camera_translation(rows, [0, 0, 0])

    def test_nonfinite_or_excessive_target_refused(self):
        for target in [[0, float('nan'), 0], [4e6, 0, 0]]:
            with self.assertRaises(m.Held):
                m.island_camera_translation(self.rows(), target)


if __name__ == '__main__':
    unittest.main()
