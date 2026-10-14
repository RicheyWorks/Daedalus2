import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from container_smoke import ROOT, check_jar


class ContainerResourcesTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.jar = Path(self.folder.name) / 'app.jar'

    def package(self, missing_catalog=False, bad_tonic=False):
        core_bytes = io.BytesIO()
        fixtures = sorted((ROOT / 'engines/unreal/DaedalusLink/Content/Inventory').glob('*.dic'))
        with zipfile.ZipFile(core_bytes, 'w') as core:
            for index, file in enumerate(fixtures):
                if not (index == 0 and missing_catalog):
                    core.writestr('inventory/' + file.name, file.read_bytes())
        with zipfile.ZipFile(self.jar, 'w') as boot:
            boot.writestr('BOOT-INF/lib/daedalus-core-fixture.jar', core_bytes.getvalue())
            tonic = (ROOT / 'tools/islands/kennel-isle/tonics.json').read_bytes()
            boot.writestr('BOOT-INF/classes/kennel/tonics.json', b'{}' if bad_tonic else tonic)

    def test_every_source_catalog_and_tonic_are_checked(self):
        self.package()
        fixtures, hashes = check_jar(self.jar)
        self.assertEqual(set(hashes), {file.name for file in fixtures} | {'kennel/tonics.json'})

    def test_omitted_shared_catalog_cannot_pass(self):
        self.package(missing_catalog=True)
        with self.assertRaises(KeyError):
            check_jar(self.jar)

    def test_wrong_tonic_cannot_pass(self):
        self.package(bad_tonic=True)
        with self.assertRaisesRegex(ValueError, 'tonic'):
            check_jar(self.jar)

    def test_archive_without_nested_core_cannot_pass(self):
        with zipfile.ZipFile(self.jar, 'w') as boot:
            boot.writestr('other', 'not a server')
        with self.assertRaisesRegex(ValueError, 'core'):
            check_jar(self.jar)


if __name__ == '__main__':
    unittest.main()
