# SPDX-License-Identifier: MIT
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from .__main__ import main
from .test_validation import fixture, pin


class OfflineCLITests(unittest.TestCase):
    def test_verifier_fresh_bundle_and_no_rewrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            sources = root / "sources"
            sources.mkdir()
            source = sources / "file"
            source.write_bytes(b"synthetic")
            request = root / "verify.json"
            request.write_text(json.dumps({"schema": "daedalus-offline-verify-request/1",
                                          "pins": [pin(source)], "roots": [str(sources)],
                                          "chunk": 1, "phase": "start"}))
            output = root / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["verify", "--request", str(request), "--output", str(output)]), 0)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["mode"], "full")
            before = (output / "state.json").read_bytes()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["verify", "--request", str(request), "--output", str(output)]), 1)
            self.assertEqual((output / "state.json").read_bytes(), before)
            outside = root / "outside"
            outside.mkdir()
            escaped = outside / ".." / "sources" / "out"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["verify", "--request", str(request), "--output", str(escaped)]), 1)
            self.assertFalse((sources / "out").exists())

    def test_retained_validation_cli_and_failure_create_no_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            manifest, receipt = fixture(root)
            source, native = root / "source.json", root / "native.json"
            source.write_text(json.dumps(manifest))
            native.write_text(json.dumps(receipt))
            request = {"schema": "daedalus-offline-validation-request/1", "source_manifest": pin(source),
                       "native_receipt": pin(native), "roots": [str(root)], "chunk": 1,
                       "range": [101, 110], "item_ids": [item["id"] for item in manifest["items"]]}
            control, report = root / "request.json", root / "report.json"
            control.write_text(json.dumps(request))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["validate", "--request", str(control), "--report", str(report)]), 0)
            self.assertFalse(json.loads(report.read_text())["native_admission"])
            request["item_ids"][0] = "unknown"
            control.write_text(json.dumps(request))
            refused = root / "refused.json"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["validate", "--request", str(control), "--report", str(refused)]), 1)
            self.assertFalse(refused.exists())


if __name__ == "__main__":
    unittest.main()
