# SPDX-License-Identifier: MIT
"""Offline seam tests; never contact an editor."""
import hashlib
import importlib
from pathlib import Path
import sys
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
