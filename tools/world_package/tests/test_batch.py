# SPDX-License-Identifier: MIT
"""Synthetic batch workflow and refusal checks; no native/runtime operations."""

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

from tools.world_package import PlanError, build_plan
from tools.world_package import batch_plan
from tools.world_package.batch_cli import main
from tools.world_package.batch_plan import build_batch, encode_batch
from tools.world_package.tests.fixtures import MANIFEST, package, receipt


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.first = package(self.root / "first.zip")

    def request(self, *paths, receipts=()):
        return {"format": batch_plan.REQUEST_FORMAT, "version": 1,
                "packages": [{"key": "item-" + str(index), "package": str(path)}
                             for index, path in enumerate(paths or (self.first,))],
                "prior_receipts": list(receipts)}

    def variant(self, name, world_id="world-zero", revision=12, **changes):
        manifest = copy.deepcopy(MANIFEST)
        manifest["world"].update(id=world_id, revision=revision)
        manifest.update(changes)
        return package(self.root / name, manifest)

    def run_cli(self, request, *args):
        source = self.root / "request.json"
        source.write_text(json.dumps(request), encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main([str(source), *map(str, args)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_deterministic_inventory_dedups_bytes_preserves_raw_worlds_and_inputs(self):
        alias = self.root / "alias.zip"
        alias.write_bytes(self.first.read_bytes())
        other = self.variant("other.zip", world_id="WORLD-zero")
        request = self.request(self.first, alias, other)
        before = copy.deepcopy(request)
        source_bytes = {path: path.read_bytes() for path in (self.first, alias, other)}
        result = build_batch(request)
        self.assertTrue(result["ready"])
        self.assertEqual({"plan_new": 2, "no_op": 0, "duplicate": 1, "error": 0, "conflict": 0}, result["counts"])
        self.assertEqual("item-0", result["items"][1]["duplicate_of"])
        self.assertEqual(build_plan(self.first), result["inventory"][1]["plan"])
        request["packages"].reverse()
        self.assertEqual(encode_batch(result), encode_batch(build_batch(request)))
        request["packages"].reverse()
        self.assertEqual(before, request)
        self.assertFalse(result["native_acceptance"])
        for path, data in source_bytes.items():
            self.assertEqual(data, path.read_bytes())

    def test_same_revision_different_bytes_blocks_all_aliases_without_choosing_winner(self):
        changed = self.variant("changed.zip", generator="different bytes")
        request = self.request(self.first, changed)
        result = build_batch(request)
        self.assertFalse(result["ready"])
        self.assertEqual(2, result["counts"]["conflict"])
        self.assertTrue(all("plan" not in entry for entry in result["inventory"]))
        request["packages"].reverse()
        self.assertEqual(result, build_batch(request))

    def test_receipts_resume_only_exact_accepted_bytes_and_preserve_versioned_destinations(self):
        initial = build_plan(self.first)
        prior = receipt(initial)
        newer = self.variant("newer.zip", revision=13)
        older = self.variant("older.zip", revision=11)
        result = build_batch(self.request(self.first, newer, older, receipts=[prior]))
        self.assertEqual(["no_op", "plan_new", "error"], [item["status"] for item in result["items"]])
        self.assertFalse(result["ready"])
        new_plan = next(item["plan"] for item in result["inventory"] if item["world"]["revision"] == 13)
        self.assertEqual(build_plan(newer, prior), new_plan)
        self.assertNotEqual(initial["destination"]["root"], new_plan["destination"]["root"])
        self.assertEqual(prior, receipt(initial))
        # Candidate revisions are proposals; a batch does not chain them into receipts.
        clean = build_batch(self.request(self.first, newer))
        self.assertEqual(2, clean["counts"]["plan_new"])
        self.assertTrue(all(item["plan"]["previous_destination_root"] is None for item in clean["inventory"]))

    def test_request_refuses_ambiguous_receipts_plans_unknown_fields_and_unbounded_inputs(self):
        accepted = receipt(build_plan(self.first))
        for evidence in ([accepted, accepted], [build_plan(self.first)], [build_batch(self.request())]):
            with self.subTest(evidence=evidence[0]["format"]), self.assertRaises(PlanError):
                build_batch(self.request(receipts=evidence))
        for field, value in (("version", True), ("packages", []), ("packages", iter([])),
                             ("packages", self.request()["packages"] * 17), ("extra", 1)):
            request = self.request()
            request[field] = value
            with self.subTest(field=field, value=type(value)), self.assertRaises(PlanError):
                build_batch(request)
        request = self.request(self.first, self.first)
        request["packages"][1]["key"] = "item-0"
        with self.assertRaisesRegex(PlanError, "duplicate input key"):
            build_batch(request)
        request = self.request("https://example.invalid/world.zip")
        with self.assertRaisesRegex(PlanError, "local absolute"):
            build_batch(request)
        for path in ("D:asset.zip", "\\asset.zip", "\\\\server\\share\\asset.zip", "\\\\?\\C:\\asset.zip"):
            with self.subTest(path=path), self.assertRaisesRegex(PlanError, "paths are refused"):
                build_batch(self.request(path))
        with patch.object(Path, "open", side_effect=AssertionError("must not open network path")), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(1, main(["\\\\server\\share\\request.json"]))
            for url in ("https://example.invalid/request.json", "file://server/share/request.json"):
                self.assertEqual(1, main([url]))
                self.assertEqual(1, main([str(self.root / "request.json"), "--output", url]))

    def test_bad_later_archive_remains_per_item_failure_and_prevents_export(self):
        bad = self.root / "bad.zip"
        bad.write_bytes(b"invalid ZIP bytes")
        output = self.root / "plan.json"
        code, stdout, stderr = self.run_cli(self.request(self.first.name, bad.name), "--output", output)
        self.assertEqual(1, code)
        result = json.loads(stdout)
        self.assertFalse(result["ready"])
        self.assertEqual(["plan_new", "error"], [item["status"] for item in result["items"]])
        self.assertIn("cannot read package", result["items"][1]["error"])
        self.assertFalse(output.exists())
        self.assertEqual("", stderr)

    def test_source_budget_reserves_before_open_and_refunds_only_success(self):
        # Tiny patched reservation lets these checks cover exact boundaries
        # without allocating near the production reader's 64 MiB cap.
        reserve = 4097
        size = self.first.stat().st_size
        request = self.request(self.first, self.first)
        with patch.object(batch_plan, "MAX_PACKAGE_BYTES", reserve - 1), \
                patch.object(batch_plan, "MAX_SOURCE_BYTES", reserve + size):
            result = build_batch(request)
        self.assertTrue(result["ready"])
        self.assertEqual(2 * size, result["budget"]["source_bytes_charged"])
        bad = self.root / "bad.zip"
        bad.write_bytes(b"bad")
        with patch.object(batch_plan, "MAX_PACKAGE_BYTES", reserve - 1), \
                patch.object(batch_plan, "MAX_SOURCE_BYTES", reserve):
            result = build_batch(self.request(bad, self.first))
        self.assertEqual(1, result["budget"]["package_attempts"])
        self.assertEqual(reserve, result["budget"]["source_bytes_charged"])
        self.assertIn("before opening", result["items"][1]["error"])
        with patch.object(batch_plan, "MAX_OUTPUT_BYTES", 10), self.assertRaisesRegex(PlanError, "output budget"):
            build_batch(self.request())

    def test_cli_exclusive_export_and_request_errors_preserve_existing_bytes(self):
        output = self.root / "plan.json"
        code, stdout, stderr = self.run_cli(self.request(self.first.name), "--output", output)
        self.assertEqual((0, ""), (code, stderr))
        self.assertEqual(stdout.encode(), output.read_bytes())
        for target in (output, self.first, self.root / "request.json", self.root):
            before = target.read_bytes() if target.is_file() else None
            code, stdout, stderr = self.run_cli(self.request(self.first.name), "--output", target)
            self.assertEqual(1, code)
            self.assertEqual("", stdout)
            self.assertIn("export failed", stderr)
            if before is not None:
                self.assertEqual(before, target.read_bytes())
        source = self.root / "duplicate.json"
        source.write_text('{"format":"x","format":"y"}')
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(1, main([str(source)]))
        self.assertIn("duplicate JSON key", stderr.getvalue())

    def test_schema_uses_existing_plan_contract_and_rejects_weakened_batch(self):
        root = Path(batch_plan.__file__).parent
        single = json.loads((root / "import-plan-v1.schema.json").read_text())
        schema = json.loads((root / "batch-plan-v1.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        registry = Registry().with_resource(single["$id"], Resource.from_contents(single))
        validator = Draft202012Validator(schema, registry=registry)
        request = self.request()
        result = build_batch(request)
        validator.validate(request)
        validator.validate(result)
        result["native_acceptance"] = True
        with self.assertRaises(ValidationError):
            validator.validate(result)

    def test_short_export_write_returns_failure_and_preserves_named_partial_file(self):
        output = self.root / "partial.json"
        original_open = Path.open

        @contextlib.contextmanager
        def short_open(path, *args, **kwargs):
            with original_open(path, *args, **kwargs) as stream:
                if path == output:
                    writer = type("ShortWriter", (), {"write": lambda _, data: stream.write(data[:7])})()
                    yield writer
                else:
                    yield stream

        with patch.object(Path, "open", short_open):
            code, stdout, stderr = self.run_cli(self.request(self.first.name), "--output", output)
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertIn("short batch export write", stderr)
        self.assertIn(str(output), stderr)
        self.assertEqual(7, output.stat().st_size)


if __name__ == "__main__":
    unittest.main()
