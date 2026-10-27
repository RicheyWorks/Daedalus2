# SPDX-License-Identifier: MIT
"""Explicit request-builder regressions using synthetic exports only."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from . import checkpoint_store, packet, source_request, source_snapshot
from .contracts import ContractError
from .test_source_snapshot import fixture, write_json


def selection_for(request):
    """Drop pins from an existing fixture, retaining every caller declaration."""
    value = {key: copy.deepcopy(item) for key, item in request.items()
             if key not in ("schema", "inputs", "captured_utc")}
    value.update(schema="daedalus.source-request-selection.v1", inputs={})
    for role, row in request["inputs"].items():
        keys = ("status", "path", "logical_path") if row["status"] == "present" else ("status", "reason")
        value["inputs"][role] = {key: row[key] for key in keys}
    return value


class SourceRequestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="daedalus-source-request-",
                                                 dir=os.environ.get("DAEDALUS_TEST_TMPDIR"))
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.exports = self.root / "exports"
        self.original_request = fixture(self.exports)
        self.selection = selection_for(self.original_request)
        self.captured_utc = self.original_request["captured_utc"]

    @staticmethod
    def files(root):
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    def build(self, selection=None, captured_utc=None):
        return source_request.build_request(self.selection if selection is None else selection, self.exports,
                                            self.captured_utc if captured_utc is None else captured_utc)

    def test_request_preserves_declarations_bytes_unknowns_and_existing_consumers(self):
        originals = self.files(self.exports)
        selection = copy.deepcopy(self.selection)
        with mock.patch("socket.create_connection", side_effect=AssertionError("no outgoing participant")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("no process dispatch")):
            built = self.build()
            self.assertEqual(self.files(self.exports), originals)
            self.assertEqual(self.selection, selection)
            self.assertEqual(built, self.original_request)
            self.assertIsNone(source_snapshot.validate_request(built))
            snapshot = source_snapshot.capture(built, self.exports, self.root / "snapshot")
            published = checkpoint_store.publish(self.root / "rolling", built, self.exports)
        self.assertEqual(snapshot["status"], "sealed")
        self.assertEqual(published["status"], "complete")
        self.assertEqual(published["snapshot"]["packet_sha256"], snapshot["packet_sha256"])
        self.assertFalse(published["may_execute"])
        self.assertEqual(published["snapshot"]["admission_status"], "held")
        self.assertEqual(published["snapshot"]["liveness"], "not_observed")
        self.assertEqual(published["checkpoint"]["saved_utc"], "2026-10-26T10:01:59Z")
        self.assertEqual(published["checkpoint"]["owner"]["start_utc"], "2026-10-26T10:00:00.1234567Z")
        self.assertEqual(built["captured_utc"], self.captured_utc)
        for role in ("source", "build"):
            self.assertEqual(built["inputs"][role], self.original_request["inputs"][role])
            self.assertEqual(published["checkpoint"][role]["status"], "unknown")
        self.assertEqual(self.files(self.exports), originals)

    def test_only_selected_files_are_read_and_raw_catalog_and_json_bytes_are_pinned(self):
        launch = packet.read_json(self.exports / "launch.json")
        raw_launch = b"\xef\xbb\xbf" + (json.dumps(launch, indent=3) + "\r\n").encode("utf-8")
        (self.exports / "launch.json").write_bytes(raw_launch)
        raw_catalog = b"\x00\xffopaque original catalog\r\n"
        (self.exports / "catalog.json").write_bytes(raw_catalog)
        (self.exports / "unselected.json").write_bytes(b"not JSON and never selected")
        before = self.files(self.exports)
        original_read = packet._read
        allowed = {self.exports / row["path"] for row in self.selection["inputs"].values() if row["status"] == "present"}
        def read_selected(path, limit=packet.MAX_JSON_BYTES):
            self.assertIn(Path(path), allowed, "Builder followed an unselected or logical reference")
            return original_read(path, limit)
        with mock.patch.object(packet, "_read", side_effect=read_selected) as reads:
            built = self.build(captured_utc="2026-10-26T10:03:00.0000000+00:00")
        self.assertEqual(reads.call_count, len(allowed))
        self.assertEqual(built["inputs"]["launch"]["sha256"], packet.digest(raw_launch))
        self.assertEqual(built["inputs"]["launch"]["bytes"], len(raw_launch))
        self.assertEqual(built["inputs"]["catalog"]["sha256"], packet.digest(raw_catalog))
        self.assertEqual(built["inputs"]["catalog"]["bytes"], len(raw_catalog))
        self.assertEqual(built["runtime"], self.selection["runtime"])
        self.assertEqual(built["captured_utc"], "2026-10-26T10:03:00.0000000+00:00")
        self.assertEqual(source_snapshot.capture(built, self.exports, self.root / "opaque-catalog")["status"], "sealed")
        missing = copy.deepcopy(self.selection)
        missing["inputs"]["owner"] = {"status": "unknown", "reason": "Explicitly not selected"}
        allowed.remove(self.exports / "owner.json")
        with mock.patch.object(packet, "_read", side_effect=read_selected) as reads:
            unknown = self.build(missing)
        self.assertEqual(reads.call_count, len(allowed))
        self.assertEqual(unknown["inputs"]["owner"], {"status": "unknown", "path": None, "logical_path": None,
                                                       "sha256": None, "bytes": None, "reason": "Explicitly not selected"})
        self.assertEqual(self.files(self.exports), before)

    def test_invalid_metadata_roles_and_paths_refuse_before_any_export_access(self):
        def missing_role(value):
            del value["inputs"]["owner"]
        mutations = (missing_role,
                     lambda value: value.update(schema="unsupported"),
                     lambda value: value.update(captured_utc=self.captured_utc),
                     lambda value: value.update(profile="unsupported"),
                     lambda value: value.update(max_source_age_seconds=True),
                     lambda value: value["runtime"].pop("generation"),
                     lambda value: value["inputs"]["owner"].update(path="SESSION.json"),
                     lambda value: value["inputs"]["owner"].update(path="../owner.json"),
                     lambda value: value["inputs"]["owner"].update(sha256="a" * 64),
                     lambda value: value["inputs"]["source"].update(reason=""))
        for index, mutate in enumerate(mutations):
            with self.subTest(invalid=index):
                selection = copy.deepcopy(self.selection)
                mutate(selection)
                with mock.patch.object(packet, "_root", side_effect=AssertionError("Metadata must precede filesystem access")), \
                        mock.patch.object(packet, "_read", side_effect=AssertionError("No export read for malformed metadata")), \
                        self.assertRaises(ContractError):
                    self.build(selection)
        with mock.patch.object(packet, "_root", side_effect=AssertionError("Invalid UTC must precede filesystem access")), \
                self.assertRaises(ContractError):
            self.build(captured_utc="not-a-timestamp")

    def test_missing_or_malformed_object_receipts_refuse_without_substitutions(self):
        for index, raw in enumerate((b'{"unfinished":', b'[]', b'null', b'"scalar"', b'{"pid":1,"pid":2}')):
            with self.subTest(receipt=raw):
                exports = self.root / ("malformed-" + str(index))
                original = fixture(exports)
                (exports / "owner.json").write_bytes(raw)
                before = self.files(exports)
                with self.assertRaises(ContractError):
                    source_request.build_request(selection_for(original), exports, original["captured_utc"])
                self.assertEqual(self.files(exports), before)
        (self.exports / "owner.json").rename(self.exports / "retained-owner.json")
        before = self.files(self.exports)
        with self.assertRaises((ContractError, OSError)):
            self.build()
        self.assertEqual(self.files(self.exports), before)

    def test_existing_per_file_and_aggregate_limits_are_enforced_without_writes(self):
        before = self.files(self.exports)
        with mock.patch.object(packet, "MAX_EVIDENCE_BYTES", 1), self.assertRaises(ContractError) as caught:
            self.build()
        self.assertEqual(caught.exception.code, "file_size")
        total = sum(row["bytes"] for row in self.original_request["inputs"].values() if row["status"] == "present")
        with mock.patch.object(packet, "MAX_TOTAL_BYTES", total - 1), self.assertRaises(ContractError) as caught:
            self.build()
        self.assertEqual(caught.exception.code, "evidence_size")
        self.assertEqual(self.files(self.exports), before)

    def test_changed_bytes_after_build_are_held_by_the_unchanged_capture_consumer(self):
        built = self.build()
        (self.exports / "catalog.json").write_bytes((self.exports / "catalog.json").read_bytes() + b" ")
        after_change = self.files(self.exports)
        snapshot = source_snapshot.capture(built, self.exports, self.root / "changed-snapshot")
        self.assertEqual(snapshot["status"], "held")
        self.assertIn("INPUT_CHANGED", {reason["code"] for reason in snapshot["reasons"]})
        rolling = checkpoint_store.publish(self.root / "changed-rolling", built, self.exports)
        self.assertEqual(rolling["status"], "held")
        self.assertFalse(rolling["published"])
        self.assertIsNone(rolling["sha256"])
        self.assertFalse((self.root / "changed-rolling" / "current.json").exists())
        self.assertEqual(self.files(self.exports), after_change)

    def test_cli_stdout_request_can_be_published_and_keeps_holds_and_errors_explicit(self):
        from . import cli
        selection_path = self.root / "selection.json"
        selection_path.write_bytes(packet.canonical(self.selection))
        builder_args = ["source-request", "--selection", str(selection_path), "--source-root", str(self.exports),
                        "--captured-utc", self.captured_utc]
        def call(arguments, expected_exit):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli.main(arguments)
            self.assertEqual(code, expected_exit, stderr.getvalue())
            self.assertEqual(stderr.getvalue(), "")
            return stdout.getvalue(), json.loads(stdout.getvalue())
        raw, request = call(builder_args, 0)
        self.assertEqual(request, self.original_request)
        request_path = self.root / "built-request.json"
        request_path.write_text(raw, encoding="utf-8")
        store = self.root / "cli-rolling"
        published = call(["checkpoint-publish", "--store", str(store), "--request", str(request_path),
                          "--source-root", str(self.exports), "--expected-current", "none"], 0)[1]
        self.assertTrue(published["published"])
        self.assertFalse(published["may_execute"])
        journal = packet.read_json(self.exports / "journal.json")
        journal["complete"] = False
        write_json(self.exports / "journal.json", journal)
        raw, request = call(builder_args, 0)
        request_path.write_text(raw, encoding="utf-8")
        held = call(["checkpoint-publish", "--store", str(store), "--request", str(request_path),
                     "--source-root", str(self.exports), "--expected-current", published["sha256"]], 3)[1]
        self.assertFalse(held["published"])
        self.assertIn("JOURNAL_UNKNOWN", {reason["code"] for reason in held["reasons"]})
        self.assertEqual(checkpoint_store.read(store)["sha256"], published["sha256"])
        invalid = copy.deepcopy(self.selection)
        del invalid["inputs"]["owner"]
        selection_path.write_bytes(packet.canonical(invalid))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(builder_args), 2)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["error"]["code"], "INVALID_FIELD")
        self.assertFalse(error["may_execute"])


if __name__ == "__main__":
    unittest.main()
