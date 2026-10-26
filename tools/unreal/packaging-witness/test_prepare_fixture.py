import json
from pathlib import Path
import tempfile
import unittest

from prepare_fixture import MAP, prepare


class PreparationScopeTests(unittest.TestCase):
    def test_existing_output_never_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / "existing"; out.mkdir()
            sentinel = out / "keep"; sentinel.write_bytes(b"keep")
            with self.assertRaisesRegex(ValueError, "new owned output"):
                prepare(root / "plugin", root / "content", root / "unused.json", out)
            self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_full_realm_map_refused_before_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); closure = root / "closure.json"; out = root / "new"
            closure.write_text(json.dumps({"result": {"preserved": True, "action": {
                "normal_close_ready": True, "closure": [{"package": "/Game/Daedalus/DaedalusWorld"}]}}}))
            with self.assertRaisesRegex(ValueError, "Exact private map"):
                prepare(root / "plugin", root / "content", closure, out)
            self.assertFalse(out.exists())

    def test_traversal_in_package_refused_before_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); content = root / "content"; closure = root / "closure.json"; out = root / "new"
            asset = content / (MAP.removeprefix("/Game/") + ".umap")
            asset.parent.mkdir(parents=True); asset.write_bytes(b"owned dummy map")
            closure.write_text(json.dumps({"result": {"preserved": True, "action": {
                "normal_close_ready": True, "closure": [{"package": MAP},
                    {"package": "/Game/CodexToolEvaluation/HLODMinimal/R1/../Outside"}]}}}))
            with self.assertRaisesRegex(ValueError, "outside the bounded"):
                prepare(root / "plugin", content, closure, out)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
