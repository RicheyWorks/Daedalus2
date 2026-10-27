# SPDX-License-Identifier: MIT

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.world_package import PlanError, build_plan
from tools.world_package.batch_plan import build_batch
from tools.world_package.batch_request import create_request, main
from tools.world_package.tests.fixtures import package, receipt


class BatchRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_paths_are_bound_and_sorted_without_opening_or_discovering_packages(self):
        with patch.object(Path, "open", side_effect=AssertionError("package must not be opened")):
            first = create_request(["other.zip", "sub/../first.zip"], base_directory=str(self.root))
            second = create_request(["first.zip", "other.zip"], base_directory=str(self.root))
        self.assertEqual(first, second)
        self.assertEqual(2, len(first["packages"]))
        self.assertTrue(all(Path(item["package"]).is_absolute() for item in first["packages"]))
        self.assertTrue(all(item["key"].startswith("package-") and len(item["key"]) == 72 for item in first["packages"]))
        self.assertEqual([], list(self.root.iterdir()))
        with self.assertRaisesRegex(PlanError, "more than once"):
            create_request(["first.zip", "sub/../first.zip"], base_directory=str(self.root))

    def test_explicit_receipt_file_roundtrips_to_exact_no_op_and_does_not_change_sources(self):
        source = package(self.root / "fixture.zip")
        accepted = self.root / "accepted.json"
        accepted.write_text(json.dumps(receipt(build_plan(source))), encoding="utf-8")
        before = (source.read_bytes(), accepted.read_bytes())
        request = create_request([source.name], [accepted.name], base_directory=str(self.root))
        result = build_batch(request)
        self.assertTrue(result["ready"])
        self.assertEqual(1, result["counts"]["no_op"])
        self.assertEqual(before, (source.read_bytes(), accepted.read_bytes()))
        with self.assertRaisesRegex(PlanError, "multiple accepted receipts"):
            create_request([str(source)], [str(accepted), str(accepted)])

    def test_invalid_receipts_paths_and_counts_refuse_without_package_fallback(self):
        evidence = self.root / "evidence.json"
        for value in (b"x" * 65537, b'{"format":"one","format":"two"}', b'{"format":"daedalus-world-import-plan"}'):
            evidence.write_bytes(value)
            with self.subTest(value=value[:40]), self.assertRaises(PlanError):
                create_request(["missing.zip"], [str(evidence)], base_directory=str(self.root))
        for paths in ([], ["x"] * 17, iter(["x"])):
            with self.subTest(paths=type(paths)), self.assertRaises(PlanError):
                create_request(paths)
        for value in ("https://example.invalid/x.zip", "file://server/share/x.zip", "D:x.zip", "\\\\server\\share\\x.zip"):
            with patch.object(Path, "open", side_effect=AssertionError("must refuse before opening")), \
                    self.subTest(path=value), self.assertRaises(PlanError):
                create_request([value])
            with patch.object(Path, "open", side_effect=AssertionError("must refuse before opening")), \
                    contextlib.redirect_stderr(io.StringIO()) as stderr, contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(1, main([value]))
            self.assertIn("refused", stderr.getvalue())
            self.assertEqual("", stdout.getvalue())

    def test_cli_emits_only_request_json_and_never_writes_output_files(self):
        with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(0, main(["fixture.zip", "--base-directory", str(self.root)]))
        self.assertEqual("", stderr.getvalue())
        request = json.loads(stdout.getvalue())
        self.assertEqual(str(self.root / "fixture.zip"), request["packages"][0]["package"])
        self.assertEqual([], list(self.root.iterdir()))


if __name__ == "__main__":
    unittest.main()
