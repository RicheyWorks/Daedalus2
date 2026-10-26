import hashlib
from pathlib import Path
import tempfile
import unittest
from construction_inventory import asset_row


class InventoryTest(unittest.TestCase):
    def test_ready_missing_and_stale_exports_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'asset.glb'; source.write_bytes(b'known bytes')
            row={'id':'Prop_Test','file':'asset.glb','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
            self.assertEqual(asset_row(row,root)['status'],'Hash matched')
            source.write_bytes(b'changed')
            self.assertEqual(asset_row(row,root)['status'],'Hash mismatch')
            source.unlink()
            self.assertEqual(asset_row(row,root)['status'],'Missing')

    def test_manifest_cannot_escape_root_or_forge_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):asset_row({'id':'x','file':'../outside','sha256':'0'*64},root)
            with self.assertRaises(ValueError):asset_row({'id':'x','file':'inside','sha256':'not a hash'},root)


if __name__=='__main__':unittest.main()
