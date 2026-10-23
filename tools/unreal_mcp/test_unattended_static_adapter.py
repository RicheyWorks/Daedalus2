# SPDX-License-Identifier: MIT
"""Focused synthetic tests. No Unreal, host modules, network or live imports.

Qualification files below are test data only, never production review evidence.
Native functions are AST-extracted into stdlib-only fake scopes so the embedded
payload's import-unreal statement and executable steps are never run.
"""
import ast
import copy
import ctypes
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unattended_static_adapter as adapter
import prepare_static_profile as preparation


NATIVE = Path(adapter.__file__).with_name('unattended_static_native.inc')


def native_function(name, **scope):
    tree = ast.parse(NATIVE.read_bytes())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(NATIVE), 'exec'), scope)
    return scope[name]


class StaticPolicyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.fbx = self.root / 'SyntheticPond.fbx'
        self.fbx.write_bytes(b'synthetic FBX test bytes, not an asset')
        self.sidecar = self.root / 'SyntheticPond.json'
        self.sidecar.write_text('{"synthetic": true}', encoding='utf-8')
        self.image = self.root / 'SyntheticReview.png'
        self.image.write_bytes(b'synthetic image witness, not a source review')
        self.source = adapter.pin(self.fbx)
        self.metadata = adapter.pin(self.sidecar)
        self.row = {'name': 'SyntheticPond', 'fbx': str(self.fbx),
                    'sidecar': str(self.sidecar),
                    'fingerprint': {k: self.source[k] for k in ('sha256', 'bytes')},
                    'sidecar_fingerprint': {k: self.metadata[k] for k in ('sha256', 'bytes')},
                    'destination': adapter.PREFIX + 'Synthetic_' + self.source['sha256'][:16],
                    'source_unit_scale_factor': 100, 'mesh_geometry_count': 1,
                    'mesh_model_count': 1, 'triangles': 12,
                    'animations': 0, 'animation_curves': 0, 'deformers': 0,
                    'textures': 0, 'videos': 0, 'authored_ucx': 0,
                    'provenance': {'synthetic': True}, 'rgba_bytes': [[1, 2, 3, 255]]}
        self.doc = {'schema': 'daedalus.source-qualified-small-static.v1',
                    'stage': 'qualified_static_candidates_source_only',
                    'source_views_personally_inspected_by_operator': True,
                    'operator_visual_review': {'operator': 'synthetic-test-owner',
                        'observations': ['Synthetic unit-test review statement'],
                        'actual_image': adapter.pin(self.image)},
                    'source_pins': [self.source, self.metadata], 'items': [self.row]}
        self.qualification = self.root / 'synthetic-qualification.json'
        self.cfg = {'owner': 'synthetic-test-owner', 'selected_name': self.row['name']}
        self.item = {'id': 'SyntheticPond', 'destination': self.row['destination'],
                     'sources': [self.source, self.metadata], 'policy': {'synthetic': True}}

    def selected(self):
        self.qualification.write_text(json.dumps(self.doc), encoding='utf-8')
        self.cfg['qualification'] = adapter.pin(self.qualification)
        return adapter.selected(self.item, self.cfg)

    def test_synthetic_review_binds_exact_source_and_sidecar(self):
        self.assertEqual(self.selected(), self.row)

    def test_not_personally_reviewed_is_not_qualified(self):
        for value in (False, None, 'true', 1):
            with self.subTest(value=value):
                self.doc['source_views_personally_inspected_by_operator'] = value
                with self.assertRaises(adapter.q.Refused):
                    self.selected()

    def test_prepared_stage_cannot_be_relabelled_by_adapter(self):
        self.doc['stage'] = 'prepared_not_validated'
        with self.assertRaises(adapter.q.Refused):
            self.selected()

    def test_existing_operator_review_needs_no_new_identity_or_format_gate(self):
        self.doc.pop('operator_visual_review')
        self.assertEqual(self.selected(), self.row)
        self.doc['operator_visual_review'] = {'operator': 'existing-source-auditor'}
        self.assertEqual(self.selected(), self.row)

    def test_missing_or_tampered_review_image_is_refused(self):
        self.image.write_bytes(b'changed test image')
        with self.assertRaises(adapter.q.Refused):
            self.selected()

    def test_source_hash_duplicate_refused_under_different_name_and_destination(self):
        duplicate = copy.deepcopy(self.row)
        duplicate['name'] = 'AnotherName'
        duplicate['destination'] = adapter.PREFIX + 'Elsewhere_' + self.source['sha256'][:16]
        self.doc['items'].append(duplicate)
        with self.assertRaisesRegex(adapter.q.Refused, 'Duplicate'):
            self.selected()

    def test_case_duplicate_and_nested_destinations_refused(self):
        for destination in (self.row['destination'].upper(), self.row['destination'] + '/Child'):
            with self.subTest(destination=destination):
                duplicate = copy.deepcopy(self.row)
                duplicate.update(name='Other', destination=destination)
                duplicate['fingerprint']['sha256'] = 'f' * 64
                self.doc['items'] = [self.row, duplicate]
                with self.assertRaisesRegex(adapter.q.Refused, 'overlapping'):
                    self.selected()

    def test_changed_destination_or_sidecar_binding_refused(self):
        self.item['destination'] += '/Changed'
        with self.assertRaises(adapter.q.Refused):
            self.selected()
        self.item['destination'] = self.row['destination']
        self.item['sources'] = [self.metadata, self.source]
        with self.assertRaises(adapter.q.Refused):
            self.selected()

    def test_static_gate_does_not_allow_animation_or_unit_changes(self):
        for key, value in (('animations', 1), ('deformers', 1), ('textures', 1),
                           ('source_unit_scale_factor', 1), ('triangles', 3001)):
            with self.subTest(key=key):
                old = self.row[key]
                self.row[key] = value
                with self.assertRaises(adapter.q.Refused):
                    self.selected()
                self.row[key] = old

    def test_source_changed_after_review_is_refused(self):
        self.fbx.write_bytes(b'changed after test qualification')
        with self.assertRaises(adapter.q.Refused):
            self.selected()

    def test_immutable_snapshots_require_exact_hash_order_extension_and_bytes(self):
        snapshots = []
        for index, original in enumerate(self.item['sources']):
            path = self.root / ('snapshot' + str(index) + Path(original['path']).suffix)
            path.write_bytes(Path(original['path']).read_bytes())
            snapshots.append(adapter.pin(path))
        self.assertEqual(adapter.snapshots_for(self.item, snapshots), snapshots)
        for mutation in ('hash', 'size', 'order', 'extension', 'missing'):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(snapshots)
                if mutation == 'hash': changed[0]['sha256'] = 'f' * 64
                if mutation == 'size': changed[0]['bytes'] += 1
                if mutation == 'order': changed.reverse()
                if mutation == 'extension': changed[0]['path'] += '.json'
                if mutation == 'missing': changed.pop()
                with self.assertRaises(adapter.q.Refused):
                    adapter.snapshots_for(self.item, changed)

    def test_snapshot_bytes_tampering_refused_even_with_original_witness(self):
        snapshots = copy.deepcopy(self.item['sources'])
        self.fbx.write_bytes(b'tampered immutable input')
        with self.assertRaises(adapter.q.Refused):
            adapter.snapshots_for(self.item, snapshots)

    def test_cross_policy_source_hash_duplicate_prevents_host_loading(self):
        other = copy.deepcopy(self.item)
        other.update(id='OtherPond', destination=adapter.PREFIX + 'Other_' + self.source['sha256'][:16])
        other['policy'] = {'different-policy-file': True}
        cfg = {'owner': self.cfg['owner'], 'selected_name': 'SyntheticPond'}
        cfg2 = {**cfg, 'selected_name': 'OtherPond'}
        frozen = {'owner': cfg['owner'], 'items': [self.item, other]}
        with patch.object(adapter, 'policy', side_effect=[(cfg, self.row), (cfg2, self.row)]), \
                patch.object(adapter, 'protected'), patch.object(adapter, 'load_module') as load:
            with self.assertRaisesRegex(adapter.q.Refused, 'Duplicate source hash'):
                adapter.Adapter(frozen, self.root)
            load.assert_not_called()

    def test_cross_policy_case_destination_duplicate_prevents_host_loading(self):
        other = copy.deepcopy(self.item)
        other.update(id='OtherPond', destination=self.item['destination'].upper())
        row2 = copy.deepcopy(self.row)
        row2['fingerprint']['sha256'] = 'f' * 64
        cfg = {'owner': self.cfg['owner'], 'selected_name': 'SyntheticPond'}
        cfg2 = {**cfg, 'selected_name': 'OtherPond'}
        frozen = {'owner': cfg['owner'], 'items': [self.item, other]}
        with patch.object(adapter, 'policy', side_effect=[(cfg, self.row), (cfg2, row2)]), \
                patch.object(adapter, 'protected'), patch.object(adapter, 'load_module') as load:
            with self.assertRaisesRegex(adapter.q.Refused, 'destination'):
                adapter.Adapter(frozen, self.root)
            load.assert_not_called()

    def test_host_resource_floors_prevent_any_native_or_host_read(self):
        obj = object.__new__(adapter.Adapter)
        obj.folder, obj.frozen, obj.host = self.root, {}, Mock()
        floors = {'physical': adapter.q.MIN_PHYSICAL, 'commit': adapter.q.MIN_COMMIT,
                  'disk': adapter.q.MIN_DISK}
        for key in floors:
            with self.subTest(key=key):
                sample = {**floors, key: floors[key] - 1}
                with patch.object(adapter, 'policy', return_value=({}, self.row)), \
                        patch.object(adapter, 'protected', return_value={}), \
                        patch.object(adapter.q, 'resources', return_value=sample):
                    with self.assertRaisesRegex(adapter.q.Refused, 'Resource floor'):
                        obj._call(self.item, 'admit_execute')
                self.assertEqual(obj.host.mock_calls, [])


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.obj = object.__new__(adapter.Adapter)
        self.obj.folder = self.root
        self.obj._call = Mock(side_effect=AssertionError('Native dispatch forbidden in reconciliation'))
        self.item = {'id': 'SyntheticPond', 'destination': '/Game/Synthetic/Pond', 'sources': []}
        self.native = self.root / 'native'
        self.native.mkdir()

    def test_missing_completion_and_partial_terminal_stay_pending(self):
        for evidence in (None, 'import-terminal.json', 'validation-original.json'):
            with self.subTest(evidence=evidence):
                if evidence:
                    folder = self.native / 'op'
                    folder.mkdir(exist_ok=True)
                    (folder / evidence).write_text('{"synthetic": true}', encoding='utf-8')
                self.assertEqual(self.obj.reconcile(self.item, 'op'), {'state': 'pending'})
        self.obj._call.assert_not_called()

    def test_pending_reconciliation_admission_blocks_before_native_dispatch(self):
        items = self.root / 'items'
        items.mkdir()
        (items / (self.item['id'] + '.json')).write_text(
            json.dumps({'operation_id': 'op', 'state': 'UNCERTAIN'}), encoding='utf-8')
        with self.assertRaisesRegex(adapter.q.Refused, 'uncertain'):
            self.obj.admit(self.item, 'reconcile')
        self.obj._call.assert_not_called()

    def test_completed_receipt_read_unchanged_without_native_dispatch(self):
        result = {'operation_id': 'op', 'item_key': adapter.q.digest(self.item),
                  'state': 'complete', 'validation': {'status': 'NotValidated'},
                  'original_capture_time': 'synthetic-do-not-retimestamp'}
        path = self.native / 'op.json'
        path.write_text(json.dumps(result), encoding='utf-8')
        before = path.read_bytes()
        self.assertEqual(self.obj.reconcile(self.item, 'op'), {'state': 'complete', 'result': result})
        self.assertEqual(path.read_bytes(), before)
        self.obj._call.assert_not_called()

    def test_wrong_operation_item_or_nonterminal_receipt_refused(self):
        original = {'operation_id': 'op', 'item_key': adapter.q.digest(self.item), 'state': 'complete'}
        for key, value in (('operation_id', 'other'), ('item_key', 'f' * 64), ('state', 'inflight')):
            with self.subTest(key=key):
                (self.native / 'op.json').write_text(json.dumps({**original, key: value}), encoding='utf-8')
                with self.assertRaises(adapter.q.Refused):
                    self.obj.reconcile(self.item, 'op')
        self.obj._call.assert_not_called()


class PreparationTests(unittest.TestCase):
    def retained_route(self):
        fixture = Path(__file__).with_name('fixtures') / 'commons-pond-20261023.json'
        measured = json.loads(fixture.read_bytes())
        helper = measured['native_route_files']['native_helper']
        if not Path(helper['path']).is_file():
            self.skipTest('Retained local pure-data helper is not present on this machine')
        return fixture, measured, helper

    def test_actual_measured_held_packet_refused_before_creating_output(self):
        fixture, measured, helper = self.retained_route()
        self.assertIs(measured['source_views_personally_inspected_by_operator'], False)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, dedup, environment = (root / name for name in
                                             ('baseline.json', 'dedup.json', 'environment.json'))
            baseline.write_text('{}', encoding='utf-8')
            dedup.write_text('{}', encoding='utf-8')
            environment.write_text(json.dumps({
                'owner': 'synthetic-test-owner',
                'editor': {'pid': 1, 'start_utc': '2026-10-23T00:00:00Z',
                           'project': str(root / 'Synthetic.uproject'),
                           'world': '/Game/Synthetic/Synthetic.Synthetic'},
                'engine_version': 'synthetic-test-version',
                'start_by_utc': '2030-01-01T00:00:00Z',
                'importer': helper,
                'shared': measured['native_route_files']['shared_helper'],
                'host': measured['native_route_files']['host_delivery'],
                'wire': {'unused': 'qualification must fail before host use'},
                'dependencies': []}), encoding='utf-8')
            destination = root / 'must-not-exist'
            with self.assertRaisesRegex(adapter.q.Refused, 'operator-reviewed source qualification'):
                preparation.prepare(fixture, baseline, dedup, environment, destination)
            self.assertFalse(destination.exists())

    def test_synthetic_packet_freezes_file_only_without_importing_host(self):
        _, measured, helper = self.retained_route()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, sidecar, image = (root / name for name in ('synthetic.fbx', 'synthetic.json', 'review.png'))
            source.write_bytes(b'synthetic FBX; not a production source')
            sidecar.write_text('{"synthetic":true}', encoding='utf-8')
            image.write_bytes(b'synthetic review witness only')
            source_pin, sidecar_pin = adapter.pin(source), adapter.pin(sidecar)
            row = {'name': 'SyntheticPond', 'fbx': str(source), 'sidecar': str(sidecar),
                   'fingerprint': {k: source_pin[k] for k in ('sha256', 'bytes')},
                   'sidecar_fingerprint': {k: sidecar_pin[k] for k in ('sha256', 'bytes')},
                   'destination': adapter.PREFIX + 'CommonsPond20261023/Synthetic_' + source_pin['sha256'][:16],
                   'source_unit_scale_factor': 100, 'mesh_geometry_count': 1, 'mesh_model_count': 1,
                   'triangles': 1, 'animations': 0, 'animation_curves': 0, 'deformers': 0,
                   'textures': 0, 'videos': 0, 'authored_ucx': 0,
                   'source_bounds': {'min': [0, 0, 0], 'max': [1, 1, 1]},
                   'provenance': {'synthetic': True}, 'rgba_bytes': [[1, 2, 3, 255]]}
            qualification = root / 'synthetic-review.json'
            qualification.write_text(json.dumps({
                'schema': 'daedalus.source-qualified-small-static.v1',
                'stage': 'qualified_static_candidates_source_only',
                'source_views_personally_inspected_by_operator': True,
                'operator_visual_review': {'operator': 'synthetic-test-owner',
                    'observations': ['Synthetic unit-test data only'], 'actual_image': adapter.pin(image)},
                'source_pins': [source_pin, sidecar_pin], 'items': [row]}), encoding='utf-8')
            editor = {'pid': 1, 'start_utc': '2026-10-23T00:00:00Z',
                      'project': str(root / 'project/Synthetic.uproject'), 'world': '/Game/Synthetic/Map.Map'}
            protected = []
            for relative in ('Content/Synthetic/Map.umap',
                             'Plugins/DaedalusLink/Binaries/Win64/UnrealEditor-DaedalusLink.dll',
                             'Content/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.uasset'):
                path = Path(editor['project']).parent / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'synthetic protected file')
                protected.append(adapter.pin(path))
            baseline, dedup = root / 'baseline.json', root / 'dedup.json'
            baseline.write_text(json.dumps({'schema': 'daedalus.static-owner-baseline.v1',
                'editor': editor, 'context': {'world': editor['world']}, 'files': protected}), encoding='utf-8')
            dedup.write_text('{"synthetic":"not a native inventory"}', encoding='utf-8')
            host, wire = root / 'must_not_import_host.py', root / 'must_not_import_wire.py'
            for module in (host, wire):
                module.write_text('raise AssertionError("Preparation imported a host module")', encoding='utf-8')
            environment = root / 'environment.json'
            environment.write_text(json.dumps({'owner': 'synthetic-test-owner', 'editor': editor,
                'engine_version': 'synthetic-test-version', 'start_by_utc': '2030-01-01T00:00:00Z',
                'importer': helper, 'shared': measured['native_route_files']['shared_helper'],
                'host': adapter.pin(host), 'wire': adapter.pin(wire),
                'dependencies': [adapter.pin(host), adapter.pin(wire)]}), encoding='utf-8')
            destination = root / 'synthetic-prepared'
            with patch.object(adapter, 'load_module', side_effect=AssertionError('Host import forbidden')):
                result = preparation.prepare(qualification, baseline, dedup, environment, destination)
            self.assertEqual((result['items'], result['imported'], result['admitted']), (1, 0, 0))
            self.assertEqual(result['native_validation'], 'NotValidated')
            self.assertIs(result['native_profile_tested'], False)
            frozen = adapter.q.load(destination / 'state/manifest.json')
            self.assertEqual(frozen['items'][0]['sources'], [source_pin, sidecar_pin])
            self.assertFalse((destination / 'state/items/SyntheticPond.json').exists())


class EmbeddedNativeTests(unittest.TestCase):
    def test_embedded_native_compiles_without_execution(self):
        compile(NATIVE.read_bytes(), str(NATIVE), 'exec')

    def test_private_helper_world_parameter_preserves_original_guard(self):
        code = """
checks = []
def _shared(cfg):
    def original_guard():
        checks.append(cfg['marker'])
        return 'original-guard-ran'
    return {'WORLD': '/Game/Original', '_preflight': original_guard,
            'policy': {'untouched': True}}
def preflight(cfg):
    return _shared(cfg)['_preflight']()
"""
        helper = native_function('helper', source=lambda _: code,
                                 CFG={'frozen': {'editor': {'world': '/Game/SyntheticWorld'}}})
        scope = helper({'importer': {'path': 'synthetic_importer.py'}})
        shared = scope['_shared']({'marker': 'synthetic-check'})
        self.assertEqual(shared['WORLD'], '/Game/SyntheticWorld')
        self.assertEqual(shared['policy'], {'untouched': True})
        self.assertEqual(shared['_preflight'](), 'original-guard-ran')
        self.assertEqual(scope['preflight']({'marker': 'second-check'}), 'original-guard-ran')
        self.assertEqual(scope['checks'], ['synthetic-check', 'second-check'])

    def memory_function(self, physical=1740800000, commit=2252800000, available=True):
        def observe(pointer):
            pointer._obj.physical, pointer._obj.commit = physical, commit
            return available
        proxy = SimpleNamespace(Structure=ctypes.Structure, c_uint32=ctypes.c_uint32,
                                c_uint64=ctypes.c_uint64, sizeof=ctypes.sizeof, byref=ctypes.byref,
                                windll=SimpleNamespace(kernel32=SimpleNamespace(GlobalMemoryStatusEx=observe)))
        return native_function('memory', ctypes=proxy)

    def test_native_memory_exact_floors_allowed(self):
        self.memory_function()()

    def test_native_memory_below_either_floor_or_unavailable_holds(self):
        for sample in ({'physical': 1740799999}, {'commit': 2252799999}, {'available': False}):
            with self.subTest(sample=sample):
                with self.assertRaisesRegex(RuntimeError, 'Native memory floor'):
                    self.memory_function(**sample)()

    def inventory_function(self, *, additional=False, actual_sha=None, item_name='SyntheticNewPond',
                           inventory_witness=None):
        path = '/Game/Daedalus/Art/Islands/Existing.Existing'
        sha = 'a' * 64
        row = SimpleNamespace(package_name=path.split('.')[0], asset_name='Existing',
                              asset_class_path=SimpleNamespace(asset_name='StaticMesh'))
        rows = [row]
        if additional:
            rows.append(SimpleNamespace(package_name='/Game/Daedalus/Art/Islands/Unknown',
                                        asset_name='Unknown', asset_class_path=SimpleNamespace(asset_name='StaticMesh')))
        registry = SimpleNamespace(get_assets_by_path=lambda *args, **kwargs: rows)
        mesh_type = type('SyntheticStaticMesh', (), {})
        mesh = mesh_type()
        unreal = SimpleNamespace(StaticMesh=mesh_type,
            AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: registry),
            EditorAssetLibrary=SimpleNamespace(load_asset=lambda _: mesh,
                get_metadata_tag=lambda *args: sha if actual_sha is None else actual_sha))
        inventory = {'schema': 'daedalus.static-source-inventory.v1',
                     'roots': ['/Game/Daedalus/Art/Islands'],
                     'assets': {path: {'sha256': sha} if inventory_witness is None else inventory_witness}}
        item = {'name': item_name, 'fingerprint': {'sha256': 'b' * 64}}
        fn = native_function('deduplicate', json=json, unreal=unreal, memory=lambda: None,
                             source=lambda _: json.dumps(inventory),
                             CFG={'policy': {'dedup': {'synthetic': True}}, 'known_outputs': {}})
        return fn, item

    def test_complete_source_inventory_allows_new_distinct_source(self):
        fn, item = self.inventory_function()
        result = fn(item)
        self.assertEqual(result['source_hashes_checked'], 1)
        self.assertEqual(result['global_names_checked'], 1)

    def test_source_inventory_missing_current_mesh_holds(self):
        fn, item = self.inventory_function(additional=True)
        with self.assertRaisesRegex(RuntimeError, 'coverage changed/unknown'):
            fn(item)

    def test_source_hash_already_imported_holds_instead_of_duplicate_import(self):
        fn, item = self.inventory_function()
        item['fingerprint']['sha256'] = 'a' * 64
        with self.assertRaisesRegex(RuntimeError, 'Source hash already imported'):
            fn(item)

    def test_missing_native_hash_provenance_holds(self):
        fn, item = self.inventory_function(actual_sha='')
        with self.assertRaisesRegex(RuntimeError, 'provenance differs/unknown'):
            fn(item)

    def test_missing_inventory_hash_holds(self):
        fn, item = self.inventory_function(inventory_witness={})
        with self.assertRaisesRegex(RuntimeError, 'Unknown source hash'):
            fn(item)

    def test_global_name_case_duplicate_holds(self):
        fn, item = self.inventory_function(item_name='eXIsTiNg')
        with self.assertRaisesRegex(RuntimeError, 'name already present globally'):
            fn(item)


if __name__ == '__main__':
    unittest.main()
