# SPDX-License-Identifier: MIT
"""PNG capture regression outside Unreal, sockets, and the Windows window harness."""
import base64
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fake_unreal
sys.modules["unreal"] = fake_unreal
sys.path.insert(0, str(HERE.parent / "plugin" / "ClaudeUnrealBridge" / "Content" / "Python"))
import claude_unreal_bridge as bridge


class CaptureViewTest(unittest.TestCase):
    def setUp(self):
        self.actors = list(fake_unreal.LEVEL)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

    def tearDown(self):
        fake_unreal.LEVEL[:] = self.actors

    def capture(self):
        # Use a deterministic filename. The fixed six-plus-one step budget
        # fails promptly if the PNG is missing, without waiting 20 seconds.
        with mock.patch.object(bridge.tempfile, "gettempdir", return_value=self.temporary.name), \
                mock.patch.object(bridge.time, "time", return_value=100):
            job = bridge.cmd_capture_view({"width": 960, "height": 540})
            # Two exclusive warm-up ticks, two pre-capture idle ticks, then
            # two post-capture confirmation ticks precede any PNG export.
            for _ in range(6):
                self.assertIsNone(next(job))
            try:
                next(job)
            except StopIteration as done:
                return done.value
            self.fail("capture did not finish after the readiness and confirmation ticks")

    def test_capture_exports_png_with_requested_dimensions_and_cleans_up(self):
        result = self.capture()
        data = base64.b64decode(result["image_png_base64"])
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", data[16:24]), (960, 540))
        self.assertEqual((result["width"], result["height"]), (960, 540))
        self.assertEqual(result["bytes"], len(data))
        self.assertEqual(Path(result["path"]).suffix, ".png")
        self.assertEqual(Path(result["path"]).read_bytes(), data)
        self.assertEqual(fake_unreal.LEVEL, self.actors)

    def test_export_failure_still_removes_temporary_actor(self):
        with mock.patch.object(fake_unreal.RenderingLibrary, "export_render_target", side_effect=OSError("synthetic export failure")):
            with self.assertRaisesRegex(OSError, "synthetic export failure"):
                self.capture()
        self.assertEqual(fake_unreal.LEVEL, self.actors)

    def test_stand_in_float_export_preserves_filename_and_is_not_png(self):
        rt = fake_unreal.RenderingLibrary.create_render_target2d(None, 960, 540)
        fake_unreal.RenderingLibrary.export_render_target(None, rt, self.temporary.name, "extensionless")
        output = Path(self.temporary.name) / "extensionless"
        self.assertEqual(output.read_bytes()[:4], b"\x76\x2f\x31\x01")
        self.assertFalse(output.with_suffix(".png").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
