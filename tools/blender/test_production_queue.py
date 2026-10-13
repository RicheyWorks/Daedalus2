import unittest
from production_queue import report


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.assets = [{'id': 'A', 'sha256': 'a' * 64, 'export': 'Validated'},
                       {'id': 'B', 'sha256': 'b' * 64, 'export': 'Validated'}]

    def receipt(self, **changes):
        return dict(dict(id='A', sha256='a' * 64, stage='Imported',
                         owner='unreal-team', evidence='capture/A.png'), **changes)

    def test_export_is_not_import_or_play(self):
        result = report([self.assets], [], 2)
        self.assertTrue(result['request_claude_turn'])
        self.assertEqual(result['play_proof_receipts'], 0)
        self.assertIsNone(result['actual_time_share'])

    def test_import_clears_only_matching_asset(self):
        result = report([self.assets], [self.receipt()], 2)
        self.assertEqual(result['waiting_for_import'], ['B'])
        self.assertFalse(result['request_claude_turn'])

    def test_stale_unknown_and_empty_proof_rejected(self):
        for changes in [{'sha256': 'c' * 64}, {'id': 'C'}, {'evidence': ''},
                        {'owner': ''}, {'stage': 'Ready'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                report([self.assets], [self.receipt(**changes)])

    def test_duplicate_batches_rejected(self):
        with self.assertRaises(ValueError):
            report([self.assets, self.assets], [])

    def test_play_receipt_is_not_downgraded_by_later_import(self):
        result = report([self.assets], [self.receipt(stage='Play proven'), self.receipt()])
        self.assertEqual(result['play_proof_receipts'], 1)
        self.assertEqual(result['import_receipts'], 1)


if __name__ == '__main__':
    unittest.main()
