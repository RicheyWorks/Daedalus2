# SPDX-License-Identifier: MIT
"""Focused file-only inventory tests; packages below are synthetic plain text.

No Unreal, host modules, network, native calls or real asset imports are used.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import static_source_inventory as inventory


class InventoryTests(unittest.TestCase):
    def test_retained_operator_2119_paths_and_hyphenated_name_are_supported(self):
        path = Path('C:/Users/730ri/Documents/Codex/2026-10-14/task-2/native-ingestion/CommonsPond20261023/OperatorR1/registry-corpus-paths.json')
        if not path.is_file(): self.skipTest('Retained operator packet is local evidence')
        paths = inventory.capture(inventory.pin(path))
        self.assertEqual(len(paths), 2119)
        self.assertEqual(inventory.path_digest(paths), 'be785a5a724cb442dd3ce3ff23eabd41bfc2e1d3037c246607e6a2202523b7c1')
        self.assertTrue(any('BronzeSunRim-0_4' in row for row in paths))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.editor = {'pid': 123, 'start_utc': '2026-10-23T00:00:00.0000000Z',
                       'project': str(self.root / 'Synthetic.uproject'),
                       'world': '/Game/Synthetic.Synthetic'}
        self.reader_file = self.root / 'synthetic-reader.inc'
        self.reader_file.write_text('# synthetic reader witness; never executed\n', encoding='utf-8')
        self.reader = inventory.pin(self.reader_file)

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def fixture(self, count=65):
        # Repeated source hashes are intentional: existing multipart meshes may
        # share one source. Duplicate object paths are a different error.
        paths = [inventory.ROOT + '/Synthetic/Mesh' + format(i, '05d') +
                 '.Mesh' + format(i, '05d') for i in range(count)]
        capture_file = self.write('registry.json', {'root': inventory.ROOT,
            'count': count, 'paths': paths, 'source_hashes_verified': False})
        capture = inventory.pin(capture_file)
        package_dir = self.root / 'synthetic-packages'
        package_dir.mkdir(exist_ok=True)
        rows = []
        for i, asset in enumerate(paths):
            package = package_dir / ('Mesh' + format(i, '05d') + '.uasset')
            package.write_text('SYNTHETIC PLAIN TEXT NOT AN UNREAL ASSET\n', encoding='utf-8')
            rows.append({'asset': asset, 'source_sha256': 'a' * 64,
                         'package': inventory.pin(package)})
        files = []
        for offset in range(0, count, inventory.PAGE_ROWS):
            selected = rows[offset:offset + inventory.PAGE_ROWS]
            files.append(self.write('page-' + format(offset, '05d') + '.json', {
                'schema': inventory.PAGE, 'state': 'complete', 'editor': self.editor,
                'registry_sha256': capture['sha256'], 'reader_sha256': self.reader['sha256'],
                'offset': offset, 'requested': len(selected), 'rows': selected, 'issues': []}))
        return inventory.build_index(capture, self.editor, self.reader, files), files

    def changed_page(self, index, position, change):
        modified = copy.deepcopy(index)
        descriptor = modified['pages'][position]
        page = json.loads(Path(descriptor['file']['path']).read_text(encoding='utf-8'))
        change(page)
        path = self.write('changed-page-' + str(position) + '.json', page)
        descriptor['file'] = inventory.pin(path)
        return modified

    def test_2501_rows_have_complete_32_row_pages_and_short_final_page(self):
        index, _ = self.fixture(2501)
        self.assertGreater(index['path_count'], 2119)
        self.assertEqual(len(index['pages']), 79)
        pages = list(inventory.pages(index))
        self.assertEqual([len(page) for page in pages], [32] * 78 + [5])
        self.assertEqual(sum(map(len, pages)), 2501)
        self.assertEqual(len({row['asset'] for page in pages for row in page}), 2501)
        self.assertEqual({row['source_sha256'] for page in pages for row in page}, {'a' * 64})
        index_file = self.write('complete-index.json', index)
        self.assertEqual(inventory.read_index(inventory.pin(index_file)), index)

    def test_all_page_boundaries_include_no_missing_or_repeated_rows(self):
        index, _ = self.fixture()
        rows = [row['asset'] for page in inventory.pages(index) for row in page]
        self.assertEqual(rows, inventory.capture(index['registry']))
        self.assertEqual([page['offset'] for page in index['pages']], [0, 32, 64])

    def test_partial_page_state_and_short_middle_page_are_refused(self):
        index, _ = self.fixture()
        for mutation in ('state', 'short', 'requested'):
            with self.subTest(mutation=mutation):
                def change(page):
                    if mutation == 'state': page['state'] = 'partial'
                    if mutation == 'short': page['rows'].pop()
                    if mutation == 'requested': page['requested'] -= 1
                with self.assertRaises(ValueError):
                    inventory.validate(self.changed_page(index, 1, change))

    def test_partial_index_missing_middle_or_final_page_is_refused(self):
        index, _ = self.fixture()
        for position in (1, 2):
            with self.subTest(position=position):
                modified = copy.deepcopy(index)
                modified['pages'].pop(position)
                with self.assertRaises(ValueError): inventory.validate(modified)

    def test_page_offset_gap_or_overlap_is_refused(self):
        index, _ = self.fixture()
        for offset in (31, 33):
            with self.subTest(offset=offset):
                modified = copy.deepcopy(index)
                modified['pages'][1]['offset'] = offset
                with self.assertRaises(ValueError): inventory.validate(modified)

    def test_reordered_page_descriptors_are_refused(self):
        index, _ = self.fixture()
        index['pages'][0], index['pages'][1] = index['pages'][1], index['pages'][0]
        with self.assertRaises(ValueError): inventory.validate(index)

    def test_empty_trailing_page_and_boolean_descriptor_offset_are_refused(self):
        index, _ = self.fixture()
        empty = self.write('empty-trailing-page.json', {
            'schema': inventory.PAGE, 'state': 'complete', 'editor': self.editor,
            'registry_sha256': index['registry']['sha256'], 'reader_sha256': self.reader['sha256'],
            'offset': 65, 'requested': 0, 'rows': [], 'issues': []})
        modified = copy.deepcopy(index)
        modified['pages'].append({'file': inventory.pin(empty), 'offset': 65, 'count': 0})
        with self.assertRaises(ValueError): inventory.validate(modified)
        index['pages'][0]['offset'] = False
        with self.assertRaises(ValueError): inventory.validate(index)

    def test_duplicate_page_file_is_refused(self):
        index, _ = self.fixture()
        index['pages'][1]['file'] = index['pages'][0]['file']
        with self.assertRaisesRegex(ValueError, 'Duplicate page file'):
            inventory.validate(index)

    def test_duplicate_object_row_within_page_is_refused(self):
        index, _ = self.fixture()
        def change(page): page['rows'][1] = copy.deepcopy(page['rows'][0])
        with self.assertRaises(ValueError):
            inventory.validate(self.changed_page(index, 0, change))

    def test_duplicate_object_row_across_page_boundary_is_refused(self):
        index, files = self.fixture()
        first = json.loads(files[0].read_text(encoding='utf-8'))['rows'][-1]
        def change(page): page['rows'][0] = first
        with self.assertRaises(ValueError):
            inventory.validate(self.changed_page(index, 1, change))

    def test_out_of_order_rows_are_refused(self):
        index, _ = self.fixture()
        def change(page): page['rows'][0], page['rows'][1] = page['rows'][1], page['rows'][0]
        with self.assertRaises(ValueError):
            inventory.validate(self.changed_page(index, 0, change))

    def test_case_duplicate_or_exact_duplicate_capture_is_refused(self):
        paths = [inventory.ROOT + '/One.One', inventory.ROOT + '/Two.Two']
        for duplicate in (paths[0], paths[0].replace('/One.One', '/one.one')):
            with self.subTest(duplicate=duplicate):
                path = self.write('duplicate-capture.json', {'root': inventory.ROOT,
                    'count': 3, 'paths': paths + [duplicate]})
                with self.assertRaisesRegex(ValueError, 'Duplicate registry object path'):
                    inventory.capture(inventory.pin(path))

    def test_duplicate_json_keys_in_index_or_page_are_refused(self):
        index, files = self.fixture()
        index_file = self.root / 'duplicate-key-index.json'
        raw = json.dumps(index)
        index_file.write_text('{"schema":"duplicate",' + raw[1:], encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            inventory.read_index(inventory.pin(index_file))
        raw = files[0].read_text(encoding='utf-8')
        page_file = self.root / 'duplicate-key-page.json'
        page_file.write_text('{"state":"duplicate",' + raw[1:], encoding='utf-8')
        index['pages'][0]['file'] = inventory.pin(page_file)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            inventory.validate(index)

    def test_tampered_page_bytes_are_refused(self):
        index, files = self.fixture()
        raw = files[0].read_text(encoding='utf-8')
        files[0].write_text(raw.replace('complete', 'tampered'), encoding='utf-8')
        with self.assertRaises(ValueError): inventory.validate(index)

    def test_unknown_malformed_or_missing_source_hash_is_refused(self):
        index, _ = self.fixture()
        for value in ('', None, 'z' * 64, 'a' * 63):
            with self.subTest(value=value):
                def change(page): page['rows'][0]['source_sha256'] = value
                with self.assertRaisesRegex(ValueError, 'Unknown native source hash'):
                    inventory.validate(self.changed_page(index, 0, change))
        def remove(page): page['rows'][0].pop('source_sha256')
        with self.assertRaisesRegex(ValueError, 'Unknown native source hash'):
            inventory.validate(self.changed_page(index, 0, remove))

    def test_unsupported_state_schema_or_issues_are_refused(self):
        index, _ = self.fixture()
        for key, value in (('state', 'unsupported'), ('schema', 'unknown'), ('issues', ['missing metadata'])):
            with self.subTest(key=key):
                def change(page): page[key] = value
                with self.assertRaises(ValueError):
                    inventory.validate(self.changed_page(index, 0, change))
        index['schema'] = 'daedalus.static-source-inventory.v1'
        with self.assertRaises(ValueError): inventory.validate(index)

    def test_editor_generation_or_world_mismatch_is_refused(self):
        index, _ = self.fixture()
        for key, value in (('pid', 999), ('start_utc', '2026-10-22T00:00:00Z'),
                           ('world', '/Game/Other.Other')):
            with self.subTest(key=key):
                def change(page): page['editor'][key] = value
                with self.assertRaises(ValueError):
                    inventory.validate(self.changed_page(index, 0, change))

    def test_corpus_or_reader_fingerprint_mismatch_is_refused(self):
        index, _ = self.fixture()
        for key in ('registry_sha256', 'reader_sha256'):
            with self.subTest(key=key):
                def change(page): page[key] = 'b' * 64
                with self.assertRaises(ValueError):
                    inventory.validate(self.changed_page(index, 0, change))

    def test_capture_count_root_or_path_digest_mismatch_is_refused(self):
        index, _ = self.fixture()
        for key, value in (('path_count', 64), ('path_digest', 'f' * 64), ('root', '/Game/Other')):
            with self.subTest(key=key):
                modified = copy.deepcopy(index)
                modified[key] = value
                with self.assertRaises(ValueError): inventory.validate(modified)
        capture = json.loads(Path(index['registry']['path']).read_text(encoding='utf-8'))
        capture['count'] -= 1
        with self.assertRaises(ValueError):
            inventory.capture(inventory.pin(self.write('wrong-count.json', capture)))

    def test_missing_or_extra_page_file_list_is_refused_by_builder(self):
        index, files = self.fixture()
        for supplied in (files[:-1], files + [files[-1]]):
            with self.subTest(length=len(supplied)):
                with self.assertRaises(ValueError):
                    inventory.build_index(index['registry'], self.editor, self.reader, supplied)

    def test_outside_root_or_malformed_capture_path_is_refused(self):
        for path in ('/Game/Other/One.One', inventory.ROOT + '/MissingObjectSeparator'):
            with self.subTest(path=path):
                capture = self.write('bad-path.json', {'root': inventory.ROOT, 'count': 1, 'paths': [path]})
                with self.assertRaises(ValueError): inventory.capture(inventory.pin(capture))


if __name__ == '__main__':
    unittest.main()
