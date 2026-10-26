import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from verify_runtime_data import verify


class RuntimeDataTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.host = Path(self.folder.name)
        self.plugin = self.host / 'Plugins/DaedalusLink'
        files = {}
        for relative in ('Content/Inventory/one.dic', 'Content/Inventory/new.dic',
                         'Content/Casts/one.dcs', 'Content/Realm/one.drr'):
            path = self.plugin / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(relative)
            files['engines/unreal/DaedalusLink/' + relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.host / 'source-manifest.json').write_text(json.dumps({
            'source_head': 'fixture', 'tracked_file_count': len(files), 'files': files}))
        self.export = self.host / 'target.json'
        self.dependencies = [{'Path': str(self.plugin / 'Content' / name / pattern), 'Type': 'UFS'}
                             for name, pattern in [('Inventory', '*.dic'), ('Casts', '*.dcs'), ('Realm', '*.drr')]]

    def run_export(self):
        self.export.write_text(json.dumps({'Configuration': 'Shipping', 'Platform': 'Win64',
            'Modules': {'DaedalusLink': {'RuntimeDependencies': self.dependencies}}}))
        return verify(self.host, self.export)

    def test_patterns_cover_new_files_without_counting_the_pattern_as_an_asset(self):
        result = self.run_export()
        self.assertEqual(len(result['files']), 4)
        self.assertFalse(result['packagedGameLaunchVerified'])

    def test_baseline_without_runtime_declarations_is_refused(self):
        self.dependencies.clear()
        with self.assertRaisesRegex(ValueError, 'omitted'):
            self.run_export()

    def test_missing_runtime_family_is_refused(self):
        self.dependencies.pop()
        with self.assertRaisesRegex(ValueError, 'omitted'):
            self.run_export()

    def test_changed_snapshot_cannot_be_reported_as_exact_head(self):
        (self.plugin / 'Content/Inventory/one.dic').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.run_export()

    def test_editor_python_is_not_silently_staged(self):
        directory = self.plugin / 'Content/Python'
        directory.mkdir()
        (directory / 'editor.py').write_text('pass')
        self.dependencies.append({'Path': str(directory / '*.py'), 'Type': 'UFS'})
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.run_export()

    def test_wrong_storage_type_is_refused(self):
        self.dependencies[0]['Type'] = 'DebugNonUFS'
        with self.assertRaisesRegex(ValueError, 'UFS'):
            self.run_export()


if __name__ == '__main__':
    unittest.main()
