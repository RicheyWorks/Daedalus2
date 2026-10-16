# SPDX-License-Identifier: MIT
"""Offline receiving-contract tests; no Unreal, network or process execution.

The tiny temporary source packet exercises the real retained GLB decoder. Its
fixture fingerprints replace profile pins only within a mock context, so these
tests do not depend on a producer checkout or alter any production source.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import codex_tidepen_penwater_profile as profile


class PlacementTests(unittest.TestCase):
    def test_root_is_baked_once_as_flat_xzy_centimetres(self):
        box = profile.expected_native_bounds()
        self.assertEqual(box['min'][:2], [-750.0, -550.0])
        self.assertEqual(box['max'][:2], [750.0, 550.0])
        self.assertAlmostEqual(box['min'][2], -8.0, places=6)
        self.assertEqual(box['min'][2], box['max'][2])
        self.assertEqual([box['max'][i] - box['min'][i] for i in range(3)],
                         [1500.0, 1100.0, 0.0])

    def test_neutral_actor_moves_only_tide_delta_at_asymmetric_anchor(self):
        # Source normal/low/high surfaces are -.08/-.58/+.52m. The mesh
        # already contains the -.08m root; the actor must not add it again.
        anchor = [12345.0, -6789.0, 4321.0]
        for state, actor_z, surface_z in [('normal', 4321.0, 4313.0),
                                            ('low', 4271.0, 4263.0),
                                            ('high', 4381.0, 4373.0)]:
            with self.subTest(state=state):
                result = profile.tide_placement(state, anchor)
                self.assertEqual(result['actor_translation_cm'], [12345.0, -6789.0, actor_z])
                self.assertEqual(result['mesh_relative_translation_cm'], [0.0, 0.0, 0.0])
                self.assertAlmostEqual(result['surface_z_cm'], surface_z, places=6)
                self.assertEqual(result['actor_scale'], [1.0, 1.0, 1.0])
                self.assertEqual(result['rotation_degrees'], [0.0, 0.0, 0.0])
                self.assertIs(result['native_observed'], False)
                self.assertIs(result['world_anchor_assigned'], False)
        self.assertEqual(anchor, [12345.0, -6789.0, 4321.0])

    def test_logical_pivot_compensation_preserves_physical_surface(self):
        for state, logical_z, physical_z in [('normal', 4313.0, 4313.0),
                                             ('low', 4263.0, 4263.0),
                                             ('high', 4373.0, 4373.0)]:
            with self.subTest(state=state):
                result = profile.tide_placement(state, (12345, -6789, 4321),
                                                retain_logical_pivot=True)
                neutral = profile.tide_placement(state, (12345, -6789, 4321))
                self.assertEqual(result['actor_translation_cm'][:2], [12345, -6789])
                self.assertAlmostEqual(result['actor_translation_cm'][2], logical_z, places=6)
                self.assertAlmostEqual(result['mesh_relative_translation_cm'][2], 8.0, places=6)
                self.assertAlmostEqual(result['surface_z_cm'], physical_z, places=6)
                self.assertAlmostEqual(result['surface_z_cm'], neutral['surface_z_cm'], places=10)

    def test_unknown_tides_and_nonfinite_or_invalid_anchors_are_refused(self):
        for state in ('storm', 'LOW', '', 0, None):
            with self.subTest(state=state), self.assertRaises(ValueError):
                profile.tide_placement(state)
        for anchor in ([0, 0], [0, 0, 0, 0], [True, 0, 0], ['0', 0, 0],
                       [math.nan, 0, 0], [0, math.inf, 0], [0, 0, -math.inf]):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                profile.tide_placement('normal', anchor)


class MaterialTests(unittest.TestCase):
    def test_only_omitted_gltf_emission_default_is_expanded(self):
        raw = deepcopy(profile.RAW_MATERIAL)
        before = deepcopy(raw)
        semantic = profile.semantic_material(raw)
        self.assertEqual(raw, before)
        self.assertNotIn('emissiveFactor', raw)
        self.assertEqual(set(semantic) - set(raw), {'emissiveFactor'})
        self.assertEqual(semantic['emissiveFactor'], [0.0, 0.0, 0.0])
        for key, value in raw.items():
            self.assertEqual(semantic[key], value)
        self.assertNotEqual(profile.canonical_sha(raw), profile.canonical_sha(semantic))
        semantic['pbrMetallicRoughness']['baseColorFactor'][0] = 1.0
        self.assertEqual(raw, before, 'Semantic result must not alias raw nested factors')

    def test_raw_linear_factors_are_not_gamma_transferred_or_quantized(self):
        semantic = profile.semantic_material(deepcopy(profile.RAW_MATERIAL))
        pbr = semantic['pbrMetallicRoughness']
        self.assertEqual(pbr['baseColorFactor'],
                         [0.3199999928474426, 0.7200000286102295,
                          0.7400000095367432, 0.3199999928474426])
        self.assertEqual(pbr['roughnessFactor'], 0.05000000074505806)
        self.assertEqual(pbr['metallicFactor'], 0)
        self.assertEqual(semantic['alphaMode'], 'BLEND')
        self.assertIs(semantic['doubleSided'], True)

    def test_modified_materials_or_additional_fields_are_not_silently_normalized(self):
        mutations = [
            lambda raw: raw.update(alphaMode='OPAQUE'),
            lambda raw: raw.update(doubleSided=False),
            lambda raw: raw.update(name='OtherWater'),
            lambda raw: raw.update(emissiveFactor=[0.0, 0.0, 0.0]),
            lambda raw: raw.update(extensions={'KHR_materials_unlit': {}}),
            lambda raw: raw['pbrMetallicRoughness'].update(baseColorTexture={'index': 0}),
            lambda raw: raw['pbrMetallicRoughness'].update(roughnessFactor=math.nan),
            lambda raw: raw['pbrMetallicRoughness']['baseColorFactor'].__setitem__(3, 1.0),
        ]
        for index, mutate in enumerate(mutations):
            raw = deepcopy(profile.RAW_MATERIAL)
            mutate(raw)
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                profile.semantic_material(raw)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.objects = [
            {'path': profile.ROOT + '/StaticMeshes/ObservedWater.ObservedWater', 'class': 'StaticMesh'},
            {'path': profile.ROOT + '/Materials/HD_PenWaterClear.HD_PenWaterClear',
             'class': 'MaterialInstanceConstant'},
        ]

    def test_exact_observed_pair_is_order_independent_and_still_unsaved(self):
        expected = {'mesh': self.objects[0]['path'], 'instance': self.objects[1]['path'],
                    'parent_package': profile.PARENT, 'imported_objects': 2,
                    'private_parents': 1, 'expected_saved_packages': 3, 'native_saved': False}
        self.assertEqual(profile.validate_imported_inventory(self.objects), expected)
        self.assertEqual(profile.validate_imported_inventory(list(reversed(self.objects))), expected)

    def test_direct_material_missing_extra_duplicate_or_foreign_outputs_are_refused(self):
        direct = deepcopy(self.objects); direct[1]['class'] = 'Material'
        duplicate_class = deepcopy(self.objects); duplicate_class[1]['class'] = 'StaticMesh'
        duplicate_path = deepcopy(self.objects); duplicate_path[1]['path'] = duplicate_path[0]['path']
        foreign = deepcopy(self.objects); foreign[0]['path'] = '/Game/SomebodyElse/Mesh.Mesh'
        lookalike = deepcopy(self.objects); lookalike[0]['path'] = profile.ROOT + '_Other/Mesh.Mesh'
        parent = deepcopy(self.objects); parent[1]['path'] = profile.PARENT + '.' + profile.PARENT.rsplit('/', 1)[1]
        extra = deepcopy(self.objects) + [{'path': profile.ROOT + '/Extra.Extra', 'class': 'Texture2D'}]
        extra_field = deepcopy(self.objects); extra_field[0]['guessed_name'] = True
        for objects in ([], self.objects[:1], extra, direct, duplicate_class, duplicate_path,
                        foreign, lookalike, parent, extra_field, tuple(self.objects)):
            with self.subTest(objects=objects), self.assertRaises(ValueError):
                profile.validate_imported_inventory(objects)

    def test_malformed_object_paths_are_not_treated_as_asset_receipts(self):
        for suffix in ('/Mesh', '/Mesh.Other', '//Mesh.Mesh', '/Dir/../Mesh.Mesh',
                       '/Mesh.Mesh.Extra', '/Dir\\Mesh.Mesh', '/Mesh.'):
            objects = deepcopy(self.objects); objects[0]['path'] = profile.ROOT + suffix
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                profile.validate_imported_inventory(objects)


class PrivateMaterialReuseTests(unittest.TestCase):
    def test_constructor_and_factor_mapping_need_no_unreal_api_or_helper_edits(self):
        class ForbiddenUnreal(types.ModuleType):
            def __getattr__(self, name):
                raise AssertionError('Offline policy accessed unreal.' + name)

        native = (Path(__file__).resolve().parents[2]
                  / 'engines/unreal/DaedalusLink/Content/Python')
        helper = native / 'daedalus_codex_canal_material.py'
        original = helper.read_bytes()
        spec = importlib.util.spec_from_file_location(
            '_offline_tidepen_material_policy', native / 'daedalus_codex_tidepen_penwater_policy.py')
        wrapper = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'unreal': ForbiddenUnreal('unreal')}), \
                tempfile.TemporaryDirectory(prefix='tidepen-policy-witness-') as witness:
            spec.loader.exec_module(wrapper)
            policy = wrapper.PenWaterPolicy(
                profile.ROOT + '/Materials/MI_HD_PenWaterClear.MI_HD_PenWaterClear', witness)
            self.assertEqual(policy.source_parameters(), {
                'BaseColorFactor': [0.3199999928474426, 0.7200000286102295,
                                    0.7400000095367432, 0.3199999928474426],
                'EmissiveFactor': [0.0, 0.0, 0.0, 1.0],
                'RoughnessFactor': 0.05000000074505806,
                'MetallicFactor': 0, 'EmissiveStrength': 1.0,
            })
            identity = policy.source_identity()
            raw_sha = profile.canonical_sha(profile.RAW_MATERIAL)
            semantic_sha = profile.canonical_sha(profile.semantic_material(profile.RAW_MATERIAL))
            self.assertEqual(identity['raw_material_sha256'], raw_sha)
            self.assertEqual(identity['helper_raw_metadata_sha256'], raw_sha)
            self.assertEqual(identity['semantic_material_sha256'], semantic_sha)
            self.assertNotEqual(raw_sha, semantic_sha)
            self.assertIs(identity['native_verified'], False)
            self.assertEqual(policy._scope['ROOT'], profile.ROOT)
            self.assertEqual(policy._scope['WITNESS_DIRECTORY'], witness)
            self.assertEqual(set(policy._scope['SOURCE_VALUES']), {'HD_PenWaterClear'})
            for name in ('inspect_partial_parent', 'resume_parent', 'PARTIAL_WATER', 'PARTIAL_NODES'):
                self.assertNotIn(name, policy._scope)
            self.assertEqual(identity['helper_source_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(helper.read_bytes(), original)


def fixture_glb():
    """Real embedded 41-position, 40-triangle fan with explicit normal data."""
    points = [(0.0, 0.0, 0.0)] + [
        (7.5 * math.cos(i * math.tau / 40), 0.0, 5.5 * math.sin(i * math.tau / 40))
        for i in range(40)]
    positions = b''.join(struct.pack('<3f', *point) for point in points)
    normals = struct.pack('<3f', 0.0, 1.0, 0.0) * len(points)
    indices = b''.join(struct.pack('<3H', 0, i + 1, (i + 1) % 40 + 1) for i in range(40))
    binary = positions + normals + indices
    document = {
        'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'TidePen_r3_PenWater', 'mesh': 0,
                   'translation': [0, -0.07999999821186066, 0]}],
        'materials': [deepcopy(profile.RAW_MATERIAL)],
        'meshes': [{'name': 'TidePen_r3_PenWater', 'primitives': [
            {'attributes': {'POSITION': 0, 'NORMAL': 1}, 'indices': 2, 'material': 0}]}],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': 41, 'type': 'VEC3'},
            {'bufferView': 1, 'componentType': 5126, 'count': 41, 'type': 'VEC3'},
            {'bufferView': 2, 'componentType': 5123, 'count': 120, 'type': 'SCALAR'}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': len(positions)},
            {'buffer': 0, 'byteOffset': len(positions), 'byteLength': len(normals)},
            {'buffer': 0, 'byteOffset': len(positions) + len(normals), 'byteLength': len(indices)}],
        'buffers': [{'byteLength': len(binary)}],
    }
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary += b'\0' * (-len(binary) % 4)
    return (struct.pack('<III', 0x46546C67, 2, 28 + len(encoded) + len(binary))
            + struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
            + struct.pack('<II', len(binary), 0x004E4942) + binary)


@contextmanager
def source_packet():
    with tempfile.TemporaryDirectory(prefix='tidepen-contract-test-') as temporary:
        root = Path(temporary)
        states = [{'id': state, 'offset_m': offset}
                  for state, offset in [('low', -0.5), ('normal', 0.0), ('high', 0.6)]]
        layout = {'roles': {'PenWater': {'file': 'TidePen_r3_PenWater.glb', 'triangles': 40,
                   'materials': ['HD_PenWaterClear'], 'collision': [], 'anchor': [0.0, 0.0, -0.08]}},
                  'habitat': {'water_states': states}, 'provenance': {'fixture': 'offline only'}}
        (root / 'TidePen_r3_PenWater.glb').write_bytes(fixture_glb())
        (root / 'TidePen_r3.layout.json').write_text(json.dumps(layout), encoding='utf-8')
        (root / 'TidePen_r3.tides.json').write_text(
            json.dumps({'shots': [{'water_state': state} for state in states]}), encoding='utf-8')
        pins = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in profile.PINS}
        release = {'hub_message': {'id': 32741, 'from': 'unreal-team'}, 'fixture': 'not an execution grant'}
        with patch.object(profile, 'PINS', pins), patch.object(profile, 'RELEASE_SHA', profile.canonical_sha(release)):
            yield root, release


class SourceContractTests(unittest.TestCase):
    def test_contract_cannot_claim_import_save_placement_or_native_grant(self):
        with source_packet() as (root, release):
            result = profile.build_contract(root, release)
        self.assertEqual(result['stage'], 'SOURCE_QUALIFIED_NATIVE_NOT_ADMITTED')
        self.assertIs(result['source_qualified'], True)
        self.assertIs(result['native_ready'], False)
        self.assertEqual(result['scope']['roles'], ['PenWater'])
        for key in ('native_execution_authorized', 'imported', 'saved', 'placed'):
            self.assertIs(result['scope'][key], False)
        self.assertIsNone(result['native_plan']['actual_imported_object_paths'])
        self.assertEqual(result['native_plan']['task'],
                         {'replace_existing': False, 'save': False, 'options': None})
        self.assertEqual(result['native_plan']['expected_saved_packages'], 3)
        self.assertEqual(result['geometry']['render_triangles'], 40)
        self.assertIs(result['geometry']['zero_z_extent_intentional'], True)
        self.assertNotIn('emissiveFactor', result['raw_material'])
        self.assertEqual(result['semantic_material']['emissiveFactor'], [0.0, 0.0, 0.0])

    def test_modified_source_bytes_fail_before_admission(self):
        for name in profile.PINS:
            with self.subTest(name=name), source_packet() as (root, release):
                with (root / name).open('ab') as handle:
                    handle.write(b'changed')
                with self.assertRaises(ValueError):
                    profile.build_contract(root, release)

    def test_release_change_is_not_a_source_execution_authorization(self):
        with source_packet() as (root, release):
            changed = deepcopy(release); changed['hub_message']['id'] = 32691
            with self.assertRaises(ValueError):
                profile.build_contract(root, changed)


if __name__ == '__main__':
    unittest.main()
