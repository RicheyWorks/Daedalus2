# SPDX-License-Identifier: MIT
"""Offline seam tests; never contact an editor."""
import hashlib
import importlib
from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ship = importlib.import_module("asset_pipeline.ship")

class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "asset.glb"
        self.path.write_bytes(b"fixture bytes A")
        self.snapshot_root = patch.object(ship.tempfile, "gettempdir", return_value=self.temp.name)
        self.snapshot_root.start()
        self.addCleanup(self.snapshot_root.stop)

    def report(self):
        with patch.object(ship.glb, "summarize", return_value={"fixture": True}):
            return ship.prebuilt("Asset", str(self.path), {"objects": []})

    def test_unchanged_import(self):
        report = self.report()
        self.assertEqual(report["artifact"], {"sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(), "bytes": 15})
        with patch.object(ship.wire, "call", return_value={"result": {}}) as call, patch.object(ship, "judge", return_value=[{"ok": True}]):
            self.assertTrue(ship.land(report)["ok"])
            call.assert_called_once()
        self.assertEqual(report["artifact_binding"], "export-sha256")

    def test_original_replaced_after_dispatch_snapshot_survives(self):
        report = self.report()
        def consume(*args, **kwargs):
            self.path.write_bytes(b"fixture bytes B")
            self.assertNotEqual(report["import_path"], str(self.path))
            self.assertEqual(Path(report["import_path"]).read_bytes(), b"fixture bytes A")
            self.assertEqual(ship.fingerprint(report["import_path"]), report["artifact"])
            return {"result": {}}
        with patch.object(ship.wire, "call", side_effect=consume), patch.object(ship, "judge", return_value=[{"ok": True}]):
            ship.land(report)

    def test_timeout_preserves_dispatched_snapshot(self):
        report = self.report()
        with patch.object(ship.wire, "call", side_effect=TimeoutError("still running")):
            with self.assertRaises(TimeoutError): ship.land(report)
        self.assertTrue(Path(report["import_path"]).exists())

    def test_importer_rejects_corrupted_snapshot_before_unreal_api(self):
        from asset_pipeline import sides
        import types
        path = self.path
        artifact = ship.fingerprint(path)
        path.write_bytes(b"fixture bytes B")
        code = sides.script(sides.UNREAL_IMPORT, path=str(path), artifact=artifact, dest="/Game/Test")
        # Empty Unreal stub: reaching an import API would fail this test differently.
        with patch.dict(sys.modules, {"unreal": types.ModuleType("unreal")}):
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                exec(code, {})

    def test_same_size_changed_bytes_refused(self):
        report = self.report()
        self.path.write_bytes(b"fixture bytes B")
        with patch.object(ship.wire, "call") as call:
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                ship.land(report)
            call.assert_not_called()

    def test_missing_file_refused(self):
        report = self.report()
        self.path.unlink()
        with patch.object(ship.wire, "call") as call:
            with self.assertRaises(OSError): ship.land(report)
            call.assert_not_called()

    def test_changed_during_witness_refused(self):
        def changed(path):
            self.path.write_bytes(b"fixture bytes B")
            return {}
        with patch.object(ship.glb, "summarize", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "collecting"):
                ship.prebuilt("Asset", str(self.path), {})

    def test_legacy_changed_structure_refused(self):
        report = self.report()
        del report["artifact"]
        with patch.object(ship.glb, "summarize", return_value={"different": True}), patch.object(ship.wire, "call") as call:
            with self.assertRaisesRegex(ValueError, "legacy"): ship.land(report)
            call.assert_not_called()

    def test_legacy_unchanged_labelled(self):
        report = self.report()
        del report["artifact"]
        with patch.object(ship.glb, "summarize", return_value=report["file"]), patch.object(ship.wire, "call", return_value={"result": {}}), patch.object(ship, "judge", return_value=[{"ok": True}]):
            ship.land(report)
        self.assertEqual(report["artifact_binding"], "legacy-structure-only")

if __name__ == "__main__": unittest.main(verbosity=2)
