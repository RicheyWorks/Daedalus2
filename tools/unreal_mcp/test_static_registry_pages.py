# SPDX-License-Identifier: MIT
"""AST-isolated registry/page tests. No Unreal, host, network or live assets.

AssetRegistry and native objects below are fakes. All package files are plain
text; only selected function definitions from the payload are executed.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import static_source_inventory as inventory

NATIVE = Path(__file__).with_name('unattended_static_native.inc')


def functions(names, **scope):
    tree = ast.parse(NATIVE.read_bytes())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes} != set(names): raise AssertionError('Native functions absent')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(NATIVE), 'exec'), scope)
    return scope


def finish(generator):
    yields = []
    while True:
        try: yields.append(next(generator))
        except StopIteration as ended: return ended.value, yields


def asset(path, kind='StaticMesh'):
    package, name = path.rsplit('.', 1)
    return SimpleNamespace(package_name=package, asset_name=name,
                           asset_class_path=SimpleNamespace(asset_name=kind))


class Registry:
    def __init__(self, root, mapping):
        self.root, self.mapping, self.calls = root, mapping, []
        self.folders = [p for p in mapping if p != root]
        self.global_rows = [row for rows in mapping.values() for row in rows]

    def get_sub_paths(self, in_base_path, in_recurse):
        # Match the native bInRecurse parameter, not an invented recursive kwarg.
        self.calls.append(('folders', in_base_path, in_recurse))
        if in_base_path == self.root: return self.folders
        return [p for p in [self.root] + self.folders if p.startswith(in_base_path + '/')]

    def get_assets_by_path(self, path, recursive):
        self.calls.append(('assets', path, recursive))
        if recursive: raise AssertionError('Corpus enumeration must use direct folders')
        return self.mapping.get(path, [])


class RegistryPageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reserves = []
        self.editor = {'pid': 123, 'start_utc': '2026-10-23T00:00:00Z',
                       'project': str(self.root / 'Synthetic.uproject'),
                       'world': '/Game/Synthetic.Synthetic'}
        reader = self.root / 'synthetic-native-reader.inc'
        reader.write_text('# SYNTHETIC reader pin, not executable native evidence\n', encoding='utf-8')
        self.reader = inventory.pin(reader)
        self.stop = self.root / 'STOP'

    def memory(self, reserve=0): self.reserves.append(reserve)

    def scope(self, **extra):
        return functions(['source', 'registry_paths', 'capture_inventory_page', 'deduplicate'],
            Path=Path, json=json, hashlib=hashlib, memory=self.memory,
            time=SimpleNamespace(monotonic=lambda: 0), inventory_admission=lambda _, **__: None,
            inventory_reader=lambda _: inventory.__dict__, **extra)

    def fixture(self, count=65, folders=10):
        mapping = {inventory.ROOT: []}
        paths, rows = [], []
        for i in range(count):
            folder = inventory.ROOT + '/Synthetic' + format(i % folders, '03d')
            path = folder + '/Mesh' + format(i, '05d') + '.Mesh' + format(i, '05d')
            mapping.setdefault(folder, []).append(asset(path))
            package = self.root / 'Content' / (path.split('.')[0][len('/Game/'):] + '.uasset')
            package.parent.mkdir(parents=True, exist_ok=True)
            package.write_text('SYNTHETIC PLAIN TEXT NOT AN UNREAL ASSET\n', encoding='utf-8')
            paths.append(path)
            rows.append({'asset': path, 'source_sha256': 'a' * 64, 'package': inventory.pin(package)})
        paths.sort(); rows.sort(key=lambda row: row['asset'])
        capture_file = self.root / 'registry.json'
        capture_file.write_text(json.dumps({'root': inventory.ROOT, 'count': len(paths), 'paths': paths,
                                           'source_hashes_verified': False}), encoding='utf-8')
        capture = inventory.pin(capture_file)
        page_files = []
        for offset in range(0, len(rows), inventory.PAGE_ROWS):
            selected = rows[offset:offset + inventory.PAGE_ROWS]
            file = self.root / ('page-' + format(offset, '05d') + '.json')
            file.write_text(json.dumps({'schema': inventory.PAGE, 'state': 'complete',
                'editor': self.editor, 'registry_sha256': capture['sha256'],
                'reader_sha256': self.reader['sha256'], 'offset': offset,
                'requested': len(selected), 'rows': selected, 'issues': []}), encoding='utf-8')
            page_files.append(file)
        index = inventory.build_index(capture, self.editor, self.reader, page_files)
        index_file = self.root / 'index.json'
        index_file.write_text(json.dumps(index), encoding='utf-8')
        return Registry(inventory.ROOT, mapping), paths, rows, capture, inventory.pin(index_file)

    def unreal(self, registry, eal=None):
        if eal is None:
            def forbidden(*_): raise AssertionError('Dedup must not load a mesh')
            eal = SimpleNamespace(load_asset=forbidden)
        return SimpleNamespace(AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: registry),
                               EditorAssetLibrary=eal, StaticMesh=FakeMesh)

    def dedup_scope(self, registry, index):
        cfg = {'policy': {'inventory_reader': {'fake': True}, 'dedup': index, 'native': self.reader},
               'frozen': {'editor': self.editor}, 'stop_path': str(self.stop), 'known_outputs': {}}
        return self.scope(unreal=self.unreal(registry), CFG=cfg)

    def test_2501_direct_folder_meshes_complete_with_no_fixed_512_prefix(self):
        paths = [inventory.ROOT + '/Mesh' + format(i, '05d') + '.Mesh' + format(i, '05d') for i in range(2501)]
        registry = Registry(inventory.ROOT, {inventory.ROOT: [asset(p) for p in paths]})
        scope = self.scope()
        (observed, evidence), yields = finish(scope['registry_paths'](registry, inventory.ROOT))
        self.assertEqual(observed, paths)
        self.assertTrue(evidence['complete'])
        self.assertEqual(evidence['largest_direct_response'], 2501)
        self.assertEqual(yields, [])
        self.assertTrue(all(reserve == 128 * 1024**2 for reserve in self.reserves))

    def test_multiple_direct_folders_yield_and_include_root_mesh(self):
        registry, paths, *_ = self.fixture()
        root_path = inventory.ROOT + '/RootMesh.RootMesh'
        registry.mapping[inventory.ROOT].append(asset(root_path))
        scope = self.scope()
        (observed, evidence), yields = finish(scope['registry_paths'](registry, inventory.ROOT))
        self.assertEqual(observed, sorted(paths + [root_path]))
        self.assertGreaterEqual(len(yields), 1)
        self.assertEqual(evidence['folder_count'], 11)
        self.assertTrue(all(not call[2] for call in registry.calls if call[0] == 'assets'))

    def test_duplicate_folder_or_object_paths_are_refused(self):
        for kind in ('folder', 'object', 'case_object'):
            with self.subTest(kind=kind):
                folder = inventory.ROOT + '/One'
                path = folder + '/Mesh.Mesh'
                registry = Registry(inventory.ROOT, {inventory.ROOT: [], folder: [asset(path)]})
                if kind == 'folder': registry.folders.append(folder.lower())
                else: registry.mapping[folder].append(asset(path if kind == 'object' else folder + '/mesh.mesh'))
                with self.assertRaisesRegex(RuntimeError, 'Duplicate|inconsistent'):
                    finish(self.scope()['registry_paths'](registry, inventory.ROOT))

    def test_oversized_native_array_is_refused_without_prefix_iteration(self):
        class TooMany:
            def __len__(self): return 4097
            def __iter__(self): raise AssertionError('Never consume a truncated prefix')
        registry = Registry(inventory.ROOT, {inventory.ROOT: []})
        registry.mapping[inventory.ROOT] = TooMany()
        with self.assertRaisesRegex(RuntimeError, '4096'):
            finish(self.scope()['registry_paths'](registry, inventory.ROOT))

    def test_unsupported_folder_count_outside_or_recursive_rows_are_refused(self):
        registry = Registry(inventory.ROOT, {inventory.ROOT: []})
        registry.folders = [inventory.ROOT + '/F' + str(i) for i in range(16384)]
        with self.assertRaisesRegex(RuntimeError, 'Unsupported'):
            finish(self.scope()['registry_paths'](registry, inventory.ROOT))
        registry.folders = ['/Game/Outside']
        with self.assertRaisesRegex(RuntimeError, 'outside folder'):
            finish(self.scope()['registry_paths'](registry, inventory.ROOT))
        registry.folders = []
        registry.mapping[inventory.ROOT] = [asset(inventory.ROOT + '/Child/Mesh.Mesh')]
        with self.assertRaisesRegex(RuntimeError, 'recursive/outside'):
            finish(self.scope()['registry_paths'](registry, inventory.ROOT))

    def test_registry_stop_or_deadline_never_returns_complete_coverage(self):
        registry = Registry(inventory.ROOT, {inventory.ROOT: []})
        self.stop.write_text('stop', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            finish(self.scope()['registry_paths'](registry, inventory.ROOT, str(self.stop)))
        self.stop.unlink()
        clock = iter([0, 31])
        scope = self.scope(); scope['time'] = SimpleNamespace(monotonic=lambda: next(clock))
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            finish(scope['registry_paths'](registry, inventory.ROOT))

    def test_registry_memory_floor_refuses_before_fetching_native_rows(self):
        registry = Registry(inventory.ROOT, {inventory.ROOT: []})
        scope = self.scope()
        def refuse(_): raise RuntimeError('Native memory floor')
        scope['memory'] = refuse
        with self.assertRaisesRegex(RuntimeError, 'memory floor'):
            finish(scope['registry_paths'](registry, inventory.ROOT))
        self.assertEqual(registry.calls, [])

    def test_page_capture_loads_at_most_32_and_final_short_page_is_complete(self):
        registry, paths, rows, capture, _ = self.fixture()
        loads = []
        eal = SimpleNamespace(load_asset=lambda p: loads.append(p) or FakeMesh(),
                              get_metadata_tag=lambda mesh, key: 'a' * 64)
        scope = self.scope(unreal=self.unreal(registry, eal))
        admissions = []
        scope['inventory_admission'] = lambda _, **stage: admissions.append(stage)
        config = {'inventory_reader': {'fake': True}, 'reader': self.reader, 'registry': capture,
                  'offset': 0, 'editor': self.editor}
        result = scope['capture_inventory_page'](config)
        self.assertEqual((result['state'], result['requested'], len(result['rows'])), ('complete', 32, 32))
        self.assertEqual(loads, paths[:32])
        self.assertEqual(result['registry_sha256'], capture['sha256'])
        self.assertEqual(result['reader_sha256'], self.reader['sha256'])
        self.assertEqual(admissions, [{'phase': 'before_metadata', 'metadata_load_calls': 0},
                                      {'phase': 'after_metadata', 'metadata_load_calls': 32}])
        loads.clear(); admissions.clear(); config['offset'] = 64
        result = scope['capture_inventory_page'](config)
        self.assertEqual((result['state'], result['requested'], len(result['rows'])), ('complete', 1, 1))
        self.assertEqual(loads, paths[64:])
        self.assertEqual(admissions[-1], {'phase': 'after_metadata', 'metadata_load_calls': 1})

    def test_page_refusal_phase_never_claims_an_unknown_zero_load_count(self):
        registry, _, _, capture, _ = self.fixture()
        loads = []
        eal = SimpleNamespace(load_asset=lambda p: loads.append(p) or FakeMesh(),
                              get_metadata_tag=lambda mesh, key: 'a' * 64)
        scope = self.scope(unreal=self.unreal(registry, eal))
        config = {'inventory_reader': {}, 'reader': self.reader, 'registry': capture,
                  'offset': 0, 'editor': self.editor}
        for phase, count in [('before_metadata', 0), ('after_metadata', 32)]:
            with self.subTest(phase=phase):
                loads.clear()
                def admission(_, **stage):
                    if stage['phase'] == phase:
                        self.assertEqual(stage['metadata_load_calls'], count)
                        raise RuntimeError('synthetic exact context refusal: ' + phase)
                scope['inventory_admission'] = admission
                with self.assertRaisesRegex(RuntimeError, phase):
                    scope['capture_inventory_page'](config)
                self.assertEqual(len(loads), count)

    def test_unknown_source_page_is_unsupported_with_explicit_missing_provenance(self):
        registry, _, _, capture, _ = self.fixture()
        loads = []
        eal = SimpleNamespace(load_asset=lambda p: loads.append(p) or FakeMesh(),
                              get_metadata_tag=lambda mesh, key: '')
        scope = self.scope(unreal=self.unreal(registry, eal))
        result = scope['capture_inventory_page']({'inventory_reader': {}, 'reader': self.reader,
            'registry': capture, 'offset': 0, 'editor': self.editor})
        self.assertEqual(result['state'], 'unsupported')
        self.assertEqual(result['rows'], [])
        self.assertEqual(len(result['issues']), 32)
        self.assertTrue(all(row['reason'] == 'unknown_native_source_sha256' for row in result['issues']))
        self.assertEqual(len(loads), 32)

    def test_page_stop_or_time_limit_preserves_partial_evidence_without_complete_state(self):
        registry, _, _, capture, _ = self.fixture()
        loads = []
        eal = SimpleNamespace(load_asset=lambda p: loads.append(p) or FakeMesh(),
                              get_metadata_tag=lambda mesh, key: 'a' * 64)
        scope = self.scope(unreal=self.unreal(registry, eal))
        config = {'inventory_reader': {}, 'reader': self.reader, 'registry': capture,
                  'offset': 0, 'editor': self.editor, 'stop_path': str(self.stop)}
        self.stop.write_text('stop', encoding='utf-8')
        result = scope['capture_inventory_page'](config)
        self.assertEqual((result['state'], result['rows'], len(loads)), ('partial', [], 0))
        self.stop.unlink()
        clock = iter([0, 0, 31])
        scope['time'] = SimpleNamespace(monotonic=lambda: next(clock))
        result = scope['capture_inventory_page'](config)
        self.assertEqual(result['state'], 'partial')
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['issues'][0]['reason'], 'partial_time_or_stop')

    def test_page_offsets_and_changed_reader_witness_are_refused(self):
        registry, _, _, capture, _ = self.fixture()
        scope = self.scope(unreal=self.unreal(registry))
        config = {'inventory_reader': {}, 'reader': self.reader, 'registry': capture,
                  'offset': 0, 'editor': self.editor}
        for offset in (True, -1, 1, 65, 96):
            with self.subTest(offset=offset):
                config['offset'] = offset
                with self.assertRaises(RuntimeError): scope['capture_inventory_page'](config)
        config['offset'] = 0
        Path(self.reader['path']).write_text('changed reader', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'Pinned'):
            scope['capture_inventory_page'](config)

    def test_dedup_2501_rows_streams_all_pages_and_never_loads_meshes(self):
        registry, paths, _, _, index = self.fixture(2501, 40)
        scope = self.dedup_scope(registry, index)
        result, yields = finish(scope['deduplicate']({'name': 'NewPond', 'fingerprint': {'sha256': 'b' * 64}}))
        self.assertTrue(result['complete'])
        self.assertTrue(result['source_hashes_verified'])
        self.assertEqual((result['source_hashes_checked'], result['registry_path_count']), (2501, 2501))
        self.assertEqual(result['pages_verified'], 79)
        self.assertEqual(result['registry_path_digest'], inventory.path_digest(paths))
        self.assertGreaterEqual(len(yields), 79)
        self.assertTrue(all(not call[2] for call in registry.calls if call[0] == 'assets'))
        self.assertTrue(result['global_name_enumeration']['complete'])

    def test_candidate_hash_name_and_current_namespace_mismatch_hold(self):
        registry, paths, _, _, index = self.fixture()
        item = {'name': 'NewPond', 'fingerprint': {'sha256': 'a' * 64}}
        with self.assertRaisesRegex(RuntimeError, 'Source hash already imported'):
            finish(self.dedup_scope(registry, index)['deduplicate'](item))
        item = {'name': paths[0].rsplit('.', 1)[1], 'fingerprint': {'sha256': 'b' * 64}}
        with self.assertRaisesRegex(RuntimeError, 'name already present globally'):
            finish(self.dedup_scope(registry, index)['deduplicate'](item))
        folder = inventory.ROOT + '/Other'
        registry.folders.append(folder)
        registry.mapping[folder] = [asset(folder + '/Extra.Extra')]
        with self.assertRaisesRegex(RuntimeError, 'coverage changed/unknown'):
            finish(self.dedup_scope(registry, index)['deduplicate']({'name': 'NewPond', 'fingerprint': {'sha256': 'b' * 64}}))

    def test_saved_package_tampering_or_editor_binding_holds(self):
        registry, _, rows, _, index = self.fixture()
        item = {'name': 'NewPond', 'fingerprint': {'sha256': 'b' * 64}}
        scope = self.dedup_scope(registry, index)
        scope['CFG']['frozen']['editor'] = {**self.editor, 'pid': 999}
        with self.assertRaisesRegex(RuntimeError, 'editor/native reader differs'):
            finish(scope['deduplicate'](item))
        Path(rows[0]['package']['path']).write_text('changed saved package', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'Saved package changed'):
            finish(self.dedup_scope(registry, index)['deduplicate'](item))

    def test_non_mesh_global_candidate_name_and_missing_corpus_folder_hold(self):
        registry, _, _, _, index = self.fixture()
        registry.mapping[inventory.ROOT].append(asset(inventory.ROOT + '/NewPond.NewPond', 'Material'))
        item = {'name': 'newpond', 'fingerprint': {'sha256': 'b' * 64}}
        with self.assertRaisesRegex(RuntimeError, 'name already present globally'):
            finish(self.dedup_scope(registry, index)['deduplicate'](item))
        registry.mapping[inventory.ROOT].clear()
        registry.folders.pop()
        with self.assertRaisesRegex(RuntimeError, 'coverage changed/unknown'):
            finish(self.dedup_scope(registry, index)['deduplicate'](item))

    def test_corpus_changed_during_package_verification_holds(self):
        registry, _, _, _, index = self.fixture()
        scope = self.dedup_scope(registry, index)
        changed = []
        def fingerprint(file):
            if not changed:
                folder = registry.folders[0]
                registry.mapping[folder].append(asset(folder + '/NewDuringScan.NewDuringScan'))
                changed.append(True)
            return inventory.fingerprint(file)
        scope['inventory_reader'] = lambda _: {**inventory.__dict__, 'fingerprint': fingerprint}
        with self.assertRaisesRegex(RuntimeError, 'Corpus changed during'):
            finish(scope['deduplicate']({'name': 'NewPond', 'fingerprint': {'sha256': 'b' * 64}}))

    def test_source_scan_stop_or_deadline_holds_without_complete_coverage(self):
        registry, paths, _, _, index = self.fixture()
        scope = self.dedup_scope(registry, index)
        def enumeration(*args, **kwargs):
            if False: yield
            return paths, {'asset_rows': len(paths), 'complete': True}
        scope['registry_paths'] = enumeration
        item = {'name': 'NewPond', 'fingerprint': {'sha256': 'b' * 64}}
        self.stop.write_text('stop', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'Incomplete source coverage'):
            finish(scope['deduplicate'](item))
        self.stop.unlink()
        clock = iter([0, 61])
        scope['time'] = SimpleNamespace(monotonic=lambda: next(clock))
        with self.assertRaisesRegex(RuntimeError, 'Incomplete source coverage'):
            finish(scope['deduplicate'](item))


class FakeMesh:
    pass


if __name__ == '__main__':
    unittest.main()
