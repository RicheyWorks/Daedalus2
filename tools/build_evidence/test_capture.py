# SPDX-License-Identifier: MIT
"""Serial synthetic-build regressions; never run native commands or inspect Git."""

from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools.build_evidence import capture as builder
from tools.team_handoff import packet
from tools.team_handoff.contracts import ContractError, EVIDENCE_ROLES, validate_checkpoint

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None


ARTIFACT = b"synthetic artifact\x00\xff\n"
BUILD = ("from pathlib import Path; p=Path('out'); p.mkdir(exist_ok=True); "
         "(p/'artifact.bin').write_bytes(" + repr(ARTIFACT) + "); print('synthetic build')")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def instant(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def document(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class CaptureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="build-evidence-test-",
                                                 dir=os.environ.get("DAEDALUS_TEST_TMPDIR"))
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.case_number = 0

    def case(self, code=BUILD):
        self.case_number += 1
        workspace = self.root / ("workspace-" + str(self.case_number))
        (workspace / "Source").mkdir(parents=True)
        original = {"Source/input.txt": b"declared source\x00\r\n",
                    "Source/config.cfg": b"synthetic=true\n"}
        for name, raw in original.items():
            (workspace / name).write_bytes(raw)
        request = {"schema": "daedalus.build-capture-request.v1", "source_commit": "1" * 40,
                   "toolchain": {"engine": "declared synthetic engine", "compiler": "declared synthetic compiler"},
                   "command": [sys.executable, "-B", "-c", code],
                   "inputs": [{"path": "Source", "kind": "directory", "category": "source"}],
                   "artifact": "out/artifact.bin", "timeout_seconds": 5, "notes": {}}
        path = self.root / ("request-" + str(self.case_number) + ".json")
        output = self.root / ("capture-" + str(self.case_number))
        self.write_request(path, request)
        return path, workspace, output, request, original

    def write_request(self, path, value):
        # Intentionally not canonical: the producer must retain/hash the actual request bytes.
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def failed(self, output, result, code=None):
        self.assertEqual(result["status"], "failed", result)
        self.assertIsNotNone(result["error"])
        if code is not None:
            self.assertEqual(result["error"]["code"], code, result)
        self.assertFalse((output / "receipts").exists(), "No admissible success directory may be advertised")
        self.assertEqual(document(output / "capture.json"), result)
        with self.assertRaises((ContractError, OSError)):
            builder.inspect_capture(output)

    def test_success_retains_exact_bytes_hashes_and_compatible_receipts(self):
        path, workspace, output, request, original = self.case()
        raw_request = path.read_bytes()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        self.assertEqual(builder.inspect_capture(output), result)
        self.assertEqual((output / "request.json").read_bytes(), raw_request)
        self.assertEqual(result["request_sha256"], sha256(raw_request))
        self.assertEqual(result["command_sha256"], sha256(packet.canonical(request["command"])))
        self.assertEqual(result["process"]["exit_code"], 0)
        self.assertTrue(result["process"]["child_reaped"])
        self.assertEqual(result["artifact"]["observation"], "absent_before_present_after")
        self.assertIsNone(result["artifact"]["before"])
        self.assertEqual((output / "artifact.bin").read_bytes(), ARTIFACT)
        self.assertEqual(result["artifact"]["after"], {"bytes": len(ARTIFACT), "sha256": sha256(ARTIFACT)})
        for name, raw in original.items():
            self.assertEqual((workspace / name).read_bytes(), raw)
            self.assertEqual((output / "inputs" / name).read_bytes(), raw)
        source_raw = (output / "receipts/source.json").read_bytes()
        self.assertEqual(source_raw, (output / "inputs-before.json").read_bytes())
        self.assertEqual(source_raw, (output / "inputs-after.json").read_bytes())
        source = document(output / "receipts/source.json")
        self.assertEqual(set(source), {"schema", "commit", "files"})
        self.assertEqual([row["path"] for row in source["files"]], sorted(original))
        for row in source["files"]:
            self.assertEqual(set(row), {"path", "category", "sha256", "bytes"})
            self.assertEqual(row["sha256"], sha256(original[row["path"]]))
            self.assertEqual(row["bytes"], len(original[row["path"]]))
        build = document(output / "receipts/build.json")
        self.assertEqual(set(build), {"schema", "recorded_at_build_time", "source_commit",
                                     "inputs_before_sha256", "inputs_after_sha256", "artifact_sha256",
                                     "toolchain", "command", "exit_code"})
        self.assertIs(build["recorded_at_build_time"], True)
        self.assertEqual(build["inputs_before_sha256"], sha256(source_raw))
        self.assertEqual(build["inputs_after_sha256"], sha256(source_raw))
        self.assertEqual(build["artifact_sha256"], sha256(ARTIFACT))
        self.assertEqual(build["command"], request["command"])
        self.assertEqual(build["toolchain"], request["toolchain"])
        marker = document(output / "receipts/success.json")
        self.assertEqual(len(marker["files"]), 10)
        for name, pin in marker["files"].items():
            raw = (output / name).read_bytes()
            self.assertEqual(pin, {"sha256": sha256(raw), "bytes": len(raw)}, name)

    def test_existing_consumer_seals_and_reads_receipts_without_native_claims(self):
        path, workspace, output, request, _ = self.case()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        source_hash = sha256((output / "receipts/source.json").read_bytes())
        build_hash = sha256((output / "receipts/build.json").read_bytes())
        start = instant(result["created_utc"])
        checkpoint = {
            "schema": "daedalus.takeover-checkpoint.v1", "campaign": "synthetic-capture-only",
            "sequence": 1, "prior_sha256": None, "saved_utc": result["finished_utc"], "phase": "uncertain",
            "owner": {"owner": "synthetic-not-a-live-owner", "session": "synthetic-session",
                      "host": "synthetic-host", "pid": 12345, "start_utc": result["created_utc"]},
            "runtime": {"name": "synthetic-not-installed", "version": "fixture-only",
                        "config_sha256": "2" * 64, "artifact_sha256": sha256(ARTIFACT),
                        "generation": "synthetic-no-native-adoption"},
            "window": {"start_utc": result["created_utc"],
                       "deadline_utc": (start + dt.timedelta(minutes=5)).isoformat().replace("+00:00", "Z")},
            "progress": {"counts": {"fixture_only": 0}, "next_index": 1, "last_operation_id": None},
            "source": {"status": "recorded", "commit": request["source_commit"],
                       "manifest_sha256": source_hash, "dirty": False, "exceptions": [], "reason": None},
            "build": {"status": "bound", "source_manifest_sha256": source_hash,
                      "artifact_sha256": sha256(ARTIFACT), "receipt_sha256": build_hash, "reason": None},
            "evidence": {role: {"status": "unknown", "path": None,
                                "reason": "Synthetic contract test; no live owner, progress or native observations"}
                         for role in EVIDENCE_ROLES},
            "operations": [],
        }
        for role in ("source", "build"):
            checkpoint["evidence"][role] = {"status": "present", "path": role + ".json", "reason": None}
        validate_checkpoint(checkpoint)
        store = self.root / "synthetic-seal-store"
        sealed = packet.seal(store, checkpoint, output / "receipts")
        inspected = packet.read_packet(store)
        self.assertEqual(inspected["sha256"], sealed["sha256"])
        self.assertEqual(inspected["checkpoint"]["source"]["manifest_sha256"], source_hash)
        self.assertEqual(inspected["checkpoint"]["build"]["receipt_sha256"], build_hash)
        self.assertEqual(inspected["checkpoint"]["evidence"]["native"]["status"], "unknown")
        for role in ("source", "build"):
            retained = store / "packets" / sealed["sha256"] / "evidence" / (role + ".json")
            self.assertEqual(retained.read_bytes(), (output / "receipts" / (role + ".json")).read_bytes())
        # Deliberately no admission/plan-ready assertion: sealing does not establish native custody.

    def test_notes_cannot_supply_outcome_truth_or_refresh_observed_times(self):
        path, workspace, output, request, _ = self.case()
        request["notes"] = {"started_utc": "1900-01-01T00:00:00Z", "exit_code": 97,
                            "source_commit_verified": True, "toolchain_verified": True,
                            "recorded_at_build_time": False, "unknown": None}
        self.write_request(path, request)
        before = dt.datetime.now(dt.timezone.utc)
        result = builder.capture(path, workspace, output)
        after = dt.datetime.now(dt.timezone.utc)
        self.assertEqual(result["status"], "captured", result)
        self.assertEqual(result["notes"], request["notes"])
        self.assertIs(result["unknowns"]["source_commit_verified"], False)
        self.assertIs(result["unknowns"]["toolchain_verified"], False)
        for name in ("dependency_completeness", "external_dependencies", "runtime_or_editor_parity",
                     "artifact_causal_producer", "continuous_input_immutability", "descendant_completion"):
            self.assertEqual(result["unknowns"][name], "unknown")
        times = [instant(result["created_utc"]), instant(result["artifact"]["before_observed_utc"]),
                 instant(result["process"]["started_utc"]), instant(result["process"]["ended_utc"]),
                 instant(result["artifact"]["after_observed_utc"]), instant(result["finished_utc"])]
        self.assertEqual(times, sorted(times))
        self.assertLessEqual(before, times[0])
        self.assertLessEqual(times[-1], after)
        retained = (output / "capture.json").read_bytes()
        self.assertEqual(builder.inspect_capture(output)["finished_utc"], result["finished_utc"])
        self.assertEqual((output / "capture.json").read_bytes(), retained)
        self.assertEqual(document(output / "receipts/build.json")["exit_code"], 0)

    @unittest.skipIf(Draft202012Validator is None, "jsonschema test dependency is unavailable")
    def test_published_request_and_existing_receipt_schemas_accept_actual_capture(self):
        path, workspace, output, request, _ = self.case()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        request_schema = document(Path(__file__).with_name("schemas") / "capture-request-v1.schema.json")
        schema_root = Path(packet.__file__).parent / "schemas"
        source_schema = document(schema_root / "build-inputs.schema.json")
        build_schema = document(schema_root / "build-provenance.schema.json")
        source = document(output / "receipts/source.json")
        build = document(output / "receipts/build.json")
        for schema, value in ((request_schema, request), (source_schema, source), (build_schema, build)):
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(value)
        invalid_request = copy.deepcopy(request)
        invalid_request["timeout_seconds"] = True
        self.assertFalse(Draft202012Validator(request_schema).is_valid(invalid_request))
        invalid_source = copy.deepcopy(source)
        invalid_source["files"][0]["bytes"] = True
        self.assertFalse(Draft202012Validator(source_schema).is_valid(invalid_source))
        invalid_build = copy.deepcopy(build)
        invalid_build["recorded_at_build_time"] = False
        self.assertFalse(Draft202012Validator(build_schema).is_valid(invalid_build))
        invalid_build = copy.deepcopy(build)
        invalid_build["created_utc"] = result["created_utc"]
        self.assertFalse(Draft202012Validator(build_schema).is_valid(invalid_build))

    def test_request_schema_refuses_extra_missing_and_boolean_fields_before_reservation(self):
        for change in ("extra", "missing", "version", "boolean_timeout", "zero_commit", "toolchain_extra"):
            with self.subTest(change=change):
                path, workspace, output, request, _ = self.case()
                if change == "extra":
                    request["exit_code"] = 0
                elif change == "missing":
                    del request["notes"]
                elif change == "version":
                    request["schema"] = "daedalus.build-capture-request.v2"
                elif change == "boolean_timeout":
                    request["timeout_seconds"] = True
                elif change == "zero_commit":
                    request["source_commit"] = "0" * 40
                else:
                    request["toolchain"]["observed"] = True
                self.write_request(path, request)
                with mock.patch.object(builder, "_run") as run:
                    with self.assertRaises(ContractError):
                        builder.capture(path, workspace, output)
                    run.assert_not_called()
                self.assertFalse(output.exists())

    def test_malformed_json_notes_refuse_before_output_or_child(self):
        for variant in ("overflow", "surrogate", "deep", "nan", "duplicate", "oversized"):
            with self.subTest(variant=variant):
                path, workspace, output, request, _ = self.case()
                raw = json.dumps(request).encode("utf-8")
                notes = {"overflow": b'{"value":1e999}', "surrogate": b'{"value":"\\ud800"}',
                         "deep": b'{"value":' * 1500 + b"0" + b"}" * 1500,
                         "nan": b'{"value":NaN}', "oversized": b'{"value":"' + b"x" * 65536 + b'"}'}
                if variant == "duplicate":
                    raw = raw.replace(b'"timeout_seconds": 5', b'"timeout_seconds": 5, "timeout_seconds": 5')
                else:
                    raw = raw.replace(b'"notes": {}', b'"notes": ' + notes[variant])
                path.write_bytes(raw)
                with mock.patch.object(builder, "_run") as run:
                    with self.assertRaises(ContractError):
                        builder.capture(path, workspace, output)
                    run.assert_not_called()
                self.assertFalse(output.exists())

    def test_unsafe_paths_case_collisions_and_overlapping_roots_are_rejected(self):
        for name in ("../Source", "Source/../input.txt", "Source//input.txt", "/Source", "NUL.txt"):
            _, _, _, request, _ = self.case()
            request["inputs"][0]["path"] = name
            with self.subTest(name=name), self.assertRaises(ContractError):
                builder.validate_request(request)
        for second in ("source", "Source/child", "Source"):
            _, _, _, request, _ = self.case()
            request["inputs"].append({"path": second, "kind": "directory", "category": "source"})
            with self.subTest(second=second), self.assertRaises(ContractError):
                builder.validate_request(request)

    def test_case_collision_in_enumerated_directory_refuses_portably(self):
        path, workspace, output, _, _ = self.case()
        with mock.patch.object(builder.os, "scandir") as scan:
            scan.return_value.__enter__.return_value = iter([SimpleNamespace(name="input.txt"),
                                                            SimpleNamespace(name="INPUT.txt")])
            result = builder.capture(path, workspace, output)
        self.failed(output, result, "case_collision")
        self.assertIsNone(result["process"])

    def test_artifact_and_input_prefix_case_alias_is_refused(self):
        _, _, _, request, _ = self.case()
        request["inputs"] = [{"path": "Source/input.txt", "kind": "file", "category": "source"}]
        request["artifact"] = "source/result.bin"
        with self.assertRaises(ContractError):
            builder.validate_request(request)

    def test_input_mutation_addition_and_removal_preserve_before_evidence(self):
        changes = ("Path('Source/input.txt').write_bytes(b'changed source')",
                   "Path('Source/added.txt').write_bytes(b'new declared-root member')",
                   "Path('Source/input.txt').unlink()")
        for change in changes:
            with self.subTest(change=change):
                path, workspace, output, _, original = self.case("from pathlib import Path; " + change + "; " + BUILD)
                result = builder.capture(path, workspace, output)
                self.failed(output, result)
                self.assertIn(result["error"]["code"], ("inputs_changed", "observation_incomplete"))
                for name, raw in original.items():
                    self.assertEqual((output / "inputs" / name).read_bytes(), raw)
                self.assertEqual(result["process"]["exit_code"], 0)

    def test_missing_root_after_command_is_incomplete_not_success(self):
        code = "import shutil; shutil.rmtree('Source'); " + BUILD
        path, workspace, output, _, _ = self.case(code)
        result = builder.capture(path, workspace, output)
        self.failed(output, result, "observation_incomplete")
        self.assertEqual(result["process"]["exit_code"], 0)

    def test_stale_artifact_is_preserved_and_never_launches_child(self):
        path, workspace, output, _, _ = self.case()
        artifact = workspace / "out/artifact.bin"
        artifact.parent.mkdir()
        artifact.write_bytes(b"preexisting artifact")
        with mock.patch.object(builder, "_run") as run:
            result = builder.capture(path, workspace, output)
            run.assert_not_called()
        self.failed(output, result, "stale_artifact")
        self.assertEqual(artifact.read_bytes(), b"preexisting artifact")
        self.assertIsNone(result["process"])

    def test_zero_exit_without_artifact_is_not_success_provenance(self):
        path, workspace, output, _, _ = self.case("print('no artifact')")
        result = builder.capture(path, workspace, output)
        self.failed(output, result, "artifact_missing")
        self.assertEqual(result["process"]["exit_code"], 0)

    def test_artifact_input_and_output_workspace_overlap_refuse_before_child(self):
        path, workspace, output, request, _ = self.case()
        request["artifact"] = "Source/artifact.bin"
        self.write_request(path, request)
        with self.assertRaises(ContractError):
            builder.capture(path, workspace, output)
        self.assertFalse(output.exists())
        path, workspace, _, _, _ = self.case()
        overlap = workspace / "capture"
        with self.assertRaises(ContractError):
            builder.capture(path, workspace, overlap)
        self.assertFalse(overlap.exists())

    def test_failed_command_retains_real_nonzero_outcome(self):
        path, workspace, output, _, _ = self.case("print('real failure'); raise SystemExit(7)")
        result = builder.capture(path, workspace, output)
        self.failed(output, result, "command_failed")
        self.assertEqual(result["process"]["status"], "exited")
        self.assertEqual(result["process"]["exit_code"], 7)
        self.assertIn(b"real failure", (output / "command.log").read_bytes())

    def test_launch_error_is_recorded_without_caller_success(self):
        path, workspace, output, _, _ = self.case()
        with mock.patch.object(builder.subprocess, "Popen", side_effect=OSError("synthetic launch error")):
            result = builder.capture(path, workspace, output)
        self.failed(output, result, "command_failed")
        self.assertEqual(result["process"]["status"], "launch_error")
        self.assertIsNone(result["process"]["exit_code"])

    def test_timeout_supervises_only_synthetic_foreground_child(self):
        path, workspace, output, request, _ = self.case("import time; time.sleep(3)")
        request["timeout_seconds"] = 1
        self.write_request(path, request)
        result = builder.capture(path, workspace, output)
        self.failed(output, result, "command_failed")
        self.assertEqual(result["process"]["status"], "timeout")
        self.assertTrue(result["process"]["child_reaped"])

    def test_output_limit_retains_bounded_log_and_refuses_provenance(self):
        path, workspace, output, _, _ = self.case(BUILD + "; import sys; sys.stdout.write('x'*2048)")
        with mock.patch.object(builder, "MAX_LOG", 64):
            result = builder.capture(path, workspace, output)
        self.failed(output, result, "command_failed")
        self.assertTrue(result["process"]["log_truncated"])
        self.assertEqual(result["process"]["status"], "output_limit")
        self.assertLessEqual((output / "command.log").stat().st_size, 64)

    def test_finite_input_and_artifact_limits_fail_without_large_fixtures(self):
        for constant, limit in (("MAX_FILES", 1), ("MAX_FILE", 3), ("MAX_TOTAL", 3),
                                ("MAX_ENTRIES", 1), ("MAX_DEPTH", 0), ("MAX_ARTIFACT", 3)):
            with self.subTest(constant=constant):
                path, workspace, output, _, _ = self.case()
                with mock.patch.object(builder, constant, limit):
                    result = builder.capture(path, workspace, output)
                self.failed(output, result)

    def test_faults_preserve_incomplete_evidence_without_published_receipts(self):
        for phase in ("before_command", "after_command", "before_publish"):
            for exception in (OSError, KeyboardInterrupt):
                with self.subTest(phase=phase, exception=exception):
                    path, workspace, output, _, original = self.case()

                    def fault(actual):
                        if actual == phase:
                            raise exception("synthetic fault at " + phase)

                    result = builder.capture(path, workspace, output, fault=fault)
                    self.failed(output, result, "io_error" if exception is OSError else "interrupted")
                    for name, raw in original.items():
                        self.assertEqual((output / "inputs" / name).read_bytes(), raw)
                    if phase == "before_command":
                        self.assertIsNone(result["process"])
                    else:
                        self.assertEqual(result["process"]["exit_code"], 0)

    def test_inspect_rejects_corrupt_retained_artifact_log_and_source_copy(self):
        path, workspace, output, _, _ = self.case()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        for name in ("artifact.bin", "command.log", "receipts/build.json", "inputs/Source/input.txt"):
            with self.subTest(name=name):
                target = output / name
                original = target.read_bytes()
                target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                with self.assertRaises((ContractError, OSError)):
                    builder.inspect_capture(output)
                target.write_bytes(original)
        self.assertEqual(builder.inspect_capture(output), result)

    def test_inspect_rejects_rehashed_false_build_time_claim(self):
        path, workspace, output, _, _ = self.case()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        build_path = output / "receipts/build.json"
        build = document(build_path)
        build["recorded_at_build_time"] = False
        build_path.write_bytes(packet.canonical(build))
        marker_path = output / "receipts/success.json"
        marker = document(marker_path)
        raw = build_path.read_bytes()
        marker["files"]["receipts/build.json"] = {"sha256": sha256(raw), "bytes": len(raw)}
        marker_path.write_bytes(packet.canonical(marker))
        with self.assertRaises((ContractError, OSError)):
            builder.inspect_capture(output)

    def test_inspect_refuses_rehashed_unknown_capture_version(self):
        path, workspace, output, _, _ = self.case()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        result["schema"] = "daedalus.build-capture.v99"
        raw = packet.canonical(result)
        (output / "capture.json").write_bytes(raw)
        marker_path = output / "receipts/success.json"
        marker = document(marker_path)
        marker["files"]["capture.json"] = {"sha256": sha256(raw), "bytes": len(raw)}
        marker_path.write_bytes(packet.canonical(marker))
        with self.assertRaises(ContractError):
            builder.inspect_capture(output)

    def test_inspect_refuses_boolean_pin_size(self):
        path, workspace, output, _, _ = self.case("from pathlib import Path; Path('out').mkdir(); Path('out/artifact.bin').write_bytes(b'fresh')")
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        marker_path = output / "receipts/success.json"
        marker = document(marker_path)
        self.assertEqual(marker["files"]["command.log"]["bytes"], 0)
        marker["files"]["command.log"]["bytes"] = False
        marker_path.write_bytes(packet.canonical(marker))
        with self.assertRaises(ContractError):
            builder.inspect_capture(output)

    def test_inspect_refuses_rehashed_log_exceeding_capture_limit(self):
        path, workspace, output, _, _ = self.case()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        raw = b"x" * 65
        (output / "command.log").write_bytes(raw)
        marker_path = output / "receipts/success.json"
        marker = document(marker_path)
        marker["files"]["command.log"] = {"sha256": sha256(raw), "bytes": len(raw)}
        marker_path.write_bytes(packet.canonical(marker))
        with mock.patch.object(builder, "MAX_LOG", 64), self.assertRaises(ContractError):
            builder.inspect_capture(output)

    def test_cli_success_inspect_and_error_codes_have_structured_output(self):
        path, workspace, output, _, _ = self.case()
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = builder.main(["capture", "--request", str(path), "--workspace", str(workspace), "--output", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "captured")
        self.assertEqual(stderr.getvalue(), "")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(builder.main(["inspect", "--output", str(output)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "captured")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(builder.main(["inspect", "--output", str(self.root / "absent")]), 2)
        self.assertIn("code", json.loads(stderr.getvalue())["error"])
        path, workspace, output, _, _ = self.case("raise SystemExit(9)")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(builder.main(["capture", "--request", str(path), "--workspace", str(workspace), "--output", str(output)]), 3)
        self.assertEqual(json.loads(stdout.getvalue())["process"]["exit_code"], 9)

    def test_real_child_interruption_is_retained_and_direct_child_reaped(self):
        path, workspace, output, _, _ = self.case("import time; time.sleep(3)")
        with mock.patch.object(builder.time, "sleep", side_effect=KeyboardInterrupt):
            result = builder.capture(path, workspace, output)
        self.failed(output, result, "command_failed")
        self.assertEqual(result["process"]["status"], "interrupted")
        self.assertTrue(result["process"]["child_reaped"])

    def test_combined_log_preserves_binary_bytes(self):
        path, workspace, output, _, _ = self.case(BUILD + "; import os; os.write(1,b'\\x00\\xff'); os.write(2,b'\\xfe\\x00')")
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        self.assertIn(b"\x00\xff\xfe\x00", (output / "command.log").read_bytes())

    def test_hard_linked_inputs_are_refused_before_launch(self):
        path, workspace, output, _, _ = self.case()
        os.link(workspace / "Source/input.txt", workspace / "Source/alias.txt")
        with mock.patch.object(builder, "_run") as run:
            result = builder.capture(path, workspace, output)
            run.assert_not_called()
        self.failed(output, result, "linked_path")

    def test_publication_destination_race_preserves_foreign_entry(self):
        path, workspace, output, _, _ = self.case()
        def fault(phase):
            if phase == "before_publish":
                (output / "receipts").mkdir()
                (output / "receipts/foreign.txt").write_bytes(b"preserve collision")
        result = builder.capture(path, workspace, output, fault=fault)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(result["error"]["code"], "publication_collision")
        self.assertEqual((output / "receipts/foreign.txt").read_bytes(), b"preserve collision")
        self.assertFalse((output / "receipts/success.json").exists())
        with self.assertRaises((ContractError, OSError)):
            builder.inspect_capture(output)

    def test_partial_capture_is_not_admissible_and_existing_output_is_never_reused(self):
        partial = self.root / "partial"
        partial.mkdir()
        (partial / "capture.json").write_text('{"status":"captured"}', encoding="utf-8")
        with self.assertRaises((ContractError, OSError)):
            builder.inspect_capture(partial)
        path, workspace, output, _, _ = self.case()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        before = {item.relative_to(output).as_posix(): item.read_bytes()
                  for item in output.rglob("*") if item.is_file()}
        with mock.patch.object(builder, "_run") as run:
            with self.assertRaises(OSError):
                builder.capture(path, workspace, output)
            run.assert_not_called()
        after = {item.relative_to(output).as_posix(): item.read_bytes()
                 for item in output.rglob("*") if item.is_file()}
        self.assertEqual(after, before)

    def test_empty_declared_directories_are_retained_for_inspection(self):
        path, workspace, output, _, _ = self.case()
        (workspace / "Source/empty").mkdir()
        result = builder.capture(path, workspace, output)
        self.assertEqual(result["status"], "captured", result)
        self.assertTrue((output / "inputs/Source/empty").is_dir())
        self.assertEqual(builder.inspect_capture(output), result)


if __name__ == "__main__":
    unittest.main()
