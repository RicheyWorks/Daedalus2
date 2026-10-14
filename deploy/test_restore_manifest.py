import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from restore_manifest import manifest, verify


class RestoreManifestTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.archive = Path(self.folder.name) / 'backup.tar.gz'
        self.entries = {'worlds/world/world-zero.daew': b'DAEWfixture',
                        'worlds/world/gallery.daew': b'DAEWfixture',
                        'worlds/world/worlds.registry': b'gallery GALLERY 42 Gallery City\n'}

    def expected(self):
        with tarfile.open(self.archive, 'w:gz') as archive:
            for name, data in self.entries.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        return manifest(self.archive)

    @staticmethod
    def response(rows):
        return b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n' + json.dumps({'worlds': rows}).encode()

    def test_complete_restore_matches_every_identity_and_metadata(self):
        expected = self.expected()
        self.assertEqual(verify(expected, self.response(expected['worlds'])), 2)

    def test_fresh_world_zero_is_not_a_successful_restore(self):
        expected = self.expected()
        with self.assertRaisesRegex(ValueError, 'IDs differ'):
            verify(expected, self.response(expected['worlds'][:1]))

    def test_same_count_with_wrong_world_is_refused(self):
        expected = self.expected()
        rows = [dict(row) for row in expected['worlds']]
        rows[1]['id'] = 'other-world'
        with self.assertRaisesRegex(ValueError, 'IDs differ'):
            verify(expected, self.response(rows))

    def test_seed_mismatch_is_refused(self):
        expected = self.expected()
        rows = [dict(row) for row in expected['worlds']]
        rows[1]['seed'] = 43
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            verify(expected, self.response(rows))

    def test_registered_world_missing_its_snapshot_is_refused(self):
        del self.entries['worlds/world/gallery.daew']
        with self.assertRaisesRegex(ValueError, 'do not agree'):
            self.expected()

    def test_orphan_snapshot_is_not_silently_ignored(self):
        del self.entries['worlds/world/worlds.registry']
        with self.assertRaisesRegex(ValueError, 'do not agree'):
            self.expected()

    def test_duplicate_served_world_is_refused(self):
        expected = self.expected()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            verify(expected, self.response(expected['worlds'] + expected['worlds'][:1]))

    def test_bad_snapshot_header_is_refused(self):
        self.entries['worlds/world/gallery.daew'] = b'bad'
        with self.assertRaisesRegex(ValueError, 'header'):
            self.expected()


if __name__ == '__main__':
    unittest.main()
