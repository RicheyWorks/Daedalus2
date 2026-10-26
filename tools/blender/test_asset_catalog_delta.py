# SPDX-License-Identifier: MIT
import json
import importlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from asset_catalog_delta import compare_catalogs
from production_queue import report


class CatalogDeltaTests(unittest.TestCase):
    def test_complete_delta_is_sorted_and_does_not_mutate_catalogs(self):
        previous = {'same': 'a' * 64, 'gone': 'b' * 64, 'changed': 'c' * 64}
        current = {'new-z': 'd' * 64, 'changed': 'e' * 64,
                   'same': 'a' * 64, 'new-a': 'f' * 64}
        before, after = dict(previous), dict(current)
        self.assertEqual(compare_catalogs(previous, current), {
            'added': ['new-a', 'new-z'], 'changed': ['changed'],
            'removed': ['gone'], 'unchanged': ['same']})
        self.assertEqual(previous, before)
        self.assertEqual(current, after)

    def test_hash_tail_change_is_not_truncated_away(self):
        self.assertEqual(compare_catalogs({'A': 'a' * 64}, {'A': 'a' * 63 + 'b'})['changed'], ['A'])

    def test_empty_catalogs_are_explicit(self):
        empty = {'added': [], 'changed': [], 'removed': [], 'unchanged': []}
        self.assertEqual(compare_catalogs({}, {}), empty)
        self.assertEqual(compare_catalogs({}, {'A': 'a' * 64})['added'], ['A'])
        self.assertEqual(compare_catalogs({'A': 'a' * 64}, {})['removed'], ['A'])

    def test_invalid_previous_or_current_declarations_are_rejected(self):
        for malformed in ({'A': 'a' * 12}, {'A': 'A' * 64}, {'A': None},
                          {' A': 'a' * 64}, {'': 'a' * 64}, [], None):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    compare_catalogs(malformed, {})
                with self.assertRaises(ValueError):
                    compare_catalogs({}, malformed)

    def test_optional_previous_catalog_does_not_change_queue_or_receipt_counts(self):
        current = [{'id': 'A', 'sha256': 'a' * 64, 'export': 'Validated'}]
        previous = [{'id': 'A', 'sha256': 'b' * 64, 'export': 'Validated'},
                    {'id': 'old', 'sha256': 'c' * 64, 'export': 'Validated'}]
        receipt = {'id': 'A', 'sha256': 'a' * 64, 'stage': 'Imported',
                   'owner': 'unreal-team', 'evidence': 'owned/A.png'}
        legacy = report([current], [receipt])
        compared = report([current], [receipt], previous_batches=[previous])
        self.assertNotIn('export_delta', legacy)
        self.assertEqual(compared.pop('export_delta'), {
            'added': [], 'changed': ['A'], 'removed': ['old'], 'unchanged': []})
        self.assertEqual(compared, legacy)

    def test_invalid_previous_catalog_cannot_be_reported_as_a_valid_delta(self):
        valid = {'id': 'A', 'sha256': 'a' * 64, 'export': 'Validated'}
        for previous in ([[valid, valid]], [[dict(valid, export='Pending')]],
                         [[dict(valid, sha256='truncated')]]):
            with self.subTest(previous=previous), self.assertRaises(ValueError):
                report([[valid]], [], previous_batches=previous)

    def test_stale_import_receipt_is_still_rejected_with_previous_catalog(self):
        current = {'id': 'A', 'sha256': 'a' * 64, 'export': 'Validated'}
        stale = {'id': 'A', 'sha256': 'b' * 64, 'stage': 'Imported',
                 'owner': 'unreal-team', 'evidence': 'old/A.png'}
        with self.assertRaisesRegex(ValueError, 'Stale receipt'):
            report([[current]], [stale], previous_batches=[[current]])

    def test_cli_accepts_multiple_previous_batches_and_preserves_default_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            current = root / 'current.json'
            previous_a, previous_b = root / 'previous-a.json', root / 'previous-b.json'
            current.write_text(json.dumps([{'id': 'A', 'sha256': 'a' * 64,
                                           'export': 'Validated'}]), encoding='utf8')
            previous_a.write_text(json.dumps([{'id': 'A', 'sha256': 'b' * 64,
                                              'export': 'Validated'}]), encoding='utf8')
            previous_b.write_text(json.dumps([{'id': 'B', 'sha256': 'c' * 64,
                                              'export': 'Validated'}]), encoding='utf8')
            command = [sys.executable, str(Path(__file__).with_name('production_queue.py')),
                       str(current)]
            legacy = json.loads(subprocess.check_output(command, text=True))
            compared = json.loads(subprocess.check_output(
                command + ['--previous', str(previous_a), '--previous', str(previous_b)],
                text=True))
            self.assertEqual(compared.pop('export_delta'), {
                'added': [], 'changed': ['A'], 'removed': ['B'], 'unchanged': []})
            self.assertEqual(compared, legacy)

    def test_report_remains_importable_from_repository_namespace(self):
        root = str(Path(__file__).resolve().parents[2])
        with patch.object(sys, 'path', [root, *sys.path]):
            module = importlib.import_module('tools.blender.production_queue')
            result = module.report([], [], previous_batches=[])
        self.assertEqual(result['export_delta'], {
            'added': [], 'changed': [], 'removed': [], 'unchanged': []})


if __name__ == '__main__':
    unittest.main()
