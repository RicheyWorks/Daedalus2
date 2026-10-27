# SPDX-License-Identifier: MIT
"""Offline legacy snapshot adapter tests; every source/store is a tempfixture."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from . import packet
from .contracts import ContractError


ROLES = ("session", "launch", "config", "owner", "terminal", "ledger", "monitor",
         "native", "catalog", "journal", "source", "build")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(packet.canonical(value))
    return {"sha256": packet.digest(path.read_bytes()), "bytes": path.stat().st_size}


def fixture(source_root):
    """Return an explicitly pinned synthetic legacy R22 saved-boundary request."""
    root = Path(source_root)
    root.mkdir(parents=True, exist_ok=True)
    identity = {"owner": "fixture-outgoing", "session": "fixture-session-1", "host": "fixture-host"}
    session_ref = "C:/Synthetic/Original/fixture-session-1"
    editor = {"pid": 9000, "start_utc": "2026-10-26T09:00:00.1234567Z"}
    counts = {"skull": 20, "toter": 20}
    status = {"stage": "paused_saved_boundary", "saved_counts": counts,
              "source_counts": counts, "next_index": 21, "pending": None}
    logical_paths = {role: "C:/Synthetic/Original/" + role + ".json" for role in ROLES}
    originals = {
        "session": {"schema": "daedalus-r22-session/1", "session_id": identity["session"],
                    "owner": identity["owner"], "started_utc": "2026-10-26T10:00:01Z",
                    "deadline_utc": "2026-10-26T11:00:01Z", "editor_receipt": editor,
                    "editor_receipt_sha256": "4" * 64},
        "launch": {"pid": 4242, "start": "2026-10-26T10:00:00.1234567Z"},
        "config": {"schema": "daedalus-r22-resume/1", "lease_owner": identity["owner"],
                   "expected_editor_pid": editor["pid"],
                   "initial_checkpoint": {"counts": {"skull": 10, "toter": 10}, "next_index": 11}},
        "owner": {"pid": 4242, "lease_owner": identity["owner"], "r22_session": session_ref,
                  "sole_editor": editor["pid"], "editor_start_utc": editor["start_utc"],
                  "utc": "2026-10-26T10:00:01Z"},
        "terminal": {"pid": 4242, "utc": "2026-10-26T10:02:00Z", "r22_session": session_ref,
                     "status": status},
        "ledger": {"saved_counts": counts, "source_counts": counts, "next_index": 21,
                   "last_native_receipt": logical_paths["native"], "last_world": "/Game/Fixture/SavedBoundary"},
        "monitor": {"utc": "2026-10-26T10:02:30Z", "owner_pid": 4242,
                    "saved_counts": counts, "source_counts": counts, "next_index": 21,
                    "active": status},
        "native": {"native": {"saved": True, "dirty": {"maps": [], "content": []},
                              "play": False, "import_active": False, "pending": None,
                              "world": "/Game/Fixture/SavedBoundary.SavedBoundary",
                              "item_records": {"fixture-skull-20": {}, "fixture-toter-20": {}}}},
        "catalog": {"fixture_only": True, "ids": ["fixture-skull-20", "fixture-toter-20"]},
    }
    for role, value in originals.items():
        write_json(root / (role + ".json"), value)
    ledger_hash = packet.digest((root / "ledger.json").read_bytes())
    native_hash = packet.digest((root / "native.json").read_bytes())
    journal = {"schema": "daedalus.source-operation-journal.v1", "session_id": identity["session"],
               "complete": True, "through_utc": "2026-10-26T10:03:00Z",
               "operations": [{"id": "fixture-save-1", "intent_sha256": ledger_hash,
                               "target_ids": ["fixture-skull-20", "fixture-toter-20"],
                               "outcome": "saved", "result_sha256": native_hash,
                               "reconciled": True, "event_utc": "2026-10-26T10:01:59Z"}]}
    write_json(root / "journal.json", journal)
    inputs = {}
    for role in ROLES:
        path = root / (role + ".json")
        if role in ("source", "build"):
            inputs[role] = {"status": "unknown", "path": None, "logical_path": None,
                            "sha256": None, "bytes": None, "reason": "No historical build-time fixture evidence"}
        else:
            inputs[role] = {"status": "present", "path": role + ".json", "logical_path": logical_paths[role],
                            "sha256": packet.digest(path.read_bytes()), "bytes": path.stat().st_size, "reason": None}
    return {"schema": "daedalus.source-snapshot-request.v1", "profile": "legacy-r22-saved-boundary.v1",
            "campaign": "fixture-campaign", "captured_utc": "2026-10-26T10:03:00Z",
            "max_source_age_seconds": 120, "identity": identity, "session_ref": session_ref,
            "runtime": {"name": "fixture-runtime", "version": "3.10", "artifact_sha256": "3" * 64,
                        "generation": "editor:%d@%s" % (editor["pid"], editor["start_utc"])},
            "source_state": {"dirty": None, "exceptions": []}, "inputs": inputs}


class SourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="daedalus-source-snapshot-",
                                                     dir=os.environ.get("DAEDALUS_TEST_TMPDIR"))
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "originals"
        self.store = self.root / "store"
        self.request = fixture(self.source)

    def originals(self):
        return {path.name: path.read_bytes() for path in self.source.iterdir() if path.is_file()}

    def edit(self, role, mutate, request=None):
        value = packet.read_json(self.source / (role + ".json"))
        mutate(value)
        pin = write_json(self.source / (role + ".json"), value)
        (request or self.request)["inputs"][role].update(pin)

    def capture(self, request=None, store=None, fault=None):
        from . import source_snapshot
        return source_snapshot.capture(request or self.request, self.source, store or self.store, fault=fault)

    def read_snapshot(self, store=None):
        from . import source_snapshot
        return source_snapshot.read_snapshot(store or self.store)

    def assert_held(self, result, code, store=None):
        self.assertEqual(result["status"], "held")
        self.assertFalse(result["may_execute"])
        self.assertIn(code, {reason["code"] for reason in result["reasons"]})
        self.assertFalse(((store or self.store) / "packet" / "current.json").exists())

    def test_healthy_source_seals_without_outgoing_process_or_network(self):
        before = self.originals()
        request_before = copy.deepcopy(self.request)
        with mock.patch("socket.create_connection", side_effect=AssertionError("outgoing disabled")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("process launch disabled")):
            result = self.capture()
            readback = self.read_snapshot()
        self.assertEqual(result["status"], "sealed")
        self.assertEqual(readback["status"], "sealed")
        self.assertFalse(result["may_execute"])
        self.assertEqual(result["admission_status"], "held")
        self.assertEqual(result["liveness"], "not_observed")
        self.assertTrue(result["source_boundary_verified"])
        sealed = packet.read_packet(self.store / "packet")
        checkpoint = sealed["checkpoint"]
        self.assertEqual(checkpoint["source"]["status"], "unknown")
        self.assertEqual(checkpoint["build"]["status"], "unknown")
        self.assertEqual(checkpoint["progress"]["counts"], {"skull": 20, "toter": 20})
        self.assertEqual(checkpoint["progress"]["next_index"], 21)
        self.assertEqual(checkpoint["owner"]["start_utc"], "2026-10-26T10:00:00.1234567Z")
        self.assertEqual(checkpoint["saved_utc"], "2026-10-26T10:01:59Z")
        self.assertEqual(checkpoint["window"], {"start_utc": "2026-10-26T10:00:01Z", "deadline_utc": "2026-10-26T11:00:01Z"})
        self.assertEqual(self.request, request_before)
        self.assertEqual(self.originals(), before)
        copies = self.store / "source-snapshot" / "copies"
        for role, row in self.request["inputs"].items():
            with self.subTest(role=role):
                if row["status"] == "present":
                    self.assertEqual((copies / (role + ".json")).read_bytes(), before[role + ".json"])
        self.assertTrue((self.store / "source-snapshot" / "request.json").is_file())
        self.assertTrue((self.store / "source-snapshot" / "capture.json").is_file())
        self.assertTrue((self.store / "source-snapshot" / "result.json").is_file())

    def test_equivalent_source_capture_is_deterministic_and_preserves_prior_packet(self):
        first = self.capture()
        prior = (self.store / "packet" / "current.json").read_bytes()
        prior_packet = packet.read_packet(self.store / "packet")
        other_store = self.root / "second-store"
        second = self.capture(store=other_store)
        self.assertEqual(first["status"], "sealed")
        self.assertEqual(second["status"], "sealed")
        self.assertEqual(packet.read_packet(other_store / "packet")["sha256"], prior_packet["sha256"])
        self.assertEqual((self.store / "packet" / "current.json").read_bytes(), prior)

    def test_existing_store_is_never_overwritten_or_retried(self):
        self.capture()
        before = {path.relative_to(self.store).as_posix(): path.read_bytes()
                  for path in self.store.rglob("*") if path.is_file()}
        with self.assertRaises(ContractError) as caught:
            self.capture()
        self.assertEqual(caught.exception.code, "snapshot_store_exists")
        self.assertEqual(before, {path.relative_to(self.store).as_posix(): path.read_bytes()
                                  for path in self.store.rglob("*") if path.is_file()})
        empty_store = self.root / "existing-empty-store"
        empty_store.mkdir()
        with self.assertRaises(ContractError) as caught:
            self.capture(store=empty_store)
        self.assertEqual(caught.exception.code, "snapshot_store_exists")

    def test_request_pin_mismatch_and_missing_file_hold(self):
        original = (self.source / "catalog.json").read_bytes()
        (self.source / "catalog.json").write_bytes(original + b" ")
        self.assert_held(self.capture(), "INPUT_CHANGED")
        source = self.root / "missing-inputs"
        request = fixture(source)
        (source / "owner.json").rename(source / "retained-owner.json")
        from . import source_snapshot
        store = self.root / "missing-store"
        result = source_snapshot.capture(request, source, store)
        self.assertEqual(result["status"], "held")
        self.assertIn("INPUT_MISSING", {reason["code"] for reason in result["reasons"]})
        self.assertFalse((store / "packet" / "current.json").exists())

    def test_whole_set_race_after_copy_is_held_before_publication(self):
        before = self.originals()
        for phase in ("after_copy", "after_validation"):
            with self.subTest(phase=phase):
                store = self.root / ("race-store-" + phase)
                (self.source / "catalog.json").write_bytes(before["catalog.json"])
                def change_source(actual):
                    if actual == phase:
                        (self.source / "catalog.json").write_bytes(before["catalog.json"] + b" ")
                self.assert_held(self.capture(store=store, fault=change_source), "INPUT_CHANGED", store=store)
        for name, raw in before.items():
            if name != "catalog.json":
                self.assertEqual((self.source / name).read_bytes(), raw)

    def test_partial_copy_failure_preserves_evidence_and_has_no_completed_snapshot(self):
        phases = ("after_copy", "after_validation", "after_seal", "before_result")
        for phase in phases:
            with self.subTest(phase=phase):
                store = self.root / ("interrupted-" + phase)
                before = self.originals()
                def interrupt(actual):
                    if actual == phase:
                        raise RuntimeError("injected writer absence at " + phase)
                with self.assertRaisesRegex(RuntimeError, "writer absence"):
                    self.capture(store=store, fault=interrupt)
                self.assertEqual(self.originals(), before)
                self.assertFalse((store / "source-snapshot" / "result.json").exists())
                with self.assertRaises((ContractError, OSError)):
                    self.read_snapshot(store)
                if phase in ("after_seal", "before_result"):
                    self.assertEqual(packet.read_packet(store / "packet")["checkpoint"]["progress"]["next_index"], 21)

    def test_stale_source_times_never_refresh_from_capture_time(self):
        self.request["captured_utc"] = "2026-10-26T10:10:00Z"
        self.edit("journal", lambda value: value.update(through_utc=self.request["captured_utc"]))
        self.assert_held(self.capture(), "STALE_SOURCE")

    def test_mixed_producer_and_editor_generations_hold(self):
        cases = [("owner", lambda value: value.update(pid=4243)),
                 ("terminal", lambda value: value.update(pid=4243)),
                 ("monitor", lambda value: value.update(owner_pid=4243)),
                 ("owner", lambda value: value.update(editor_start_utc="2026-10-26T09:00:00.1234568Z")),
                 ("owner", lambda value: value.update(sole_editor=9001)),
                 ("config", lambda value: value.update(expected_editor_pid=9001)),
                 ("owner", lambda value: value.update(r22_session="different-session"))]
        for index, (role, mutate) in enumerate(cases):
            with self.subTest(role=role, index=index):
                source = self.root / ("mixed-inputs-" + str(index))
                request = fixture(source)
                value = packet.read_json(source / (role + ".json"))
                mutate(value)
                request["inputs"][role].update(write_json(source / (role + ".json"), value))
                from . import source_snapshot
                store = self.root / ("mixed-store-" + str(index))
                result = source_snapshot.capture(request, source, store)
                self.assertEqual(result["status"], "held")
                self.assertIn("SOURCE_MISMATCH", {reason["code"] for reason in result["reasons"]})
                self.assertFalse((store / "packet" / "current.json").exists())

    def test_owner_observation_timestamp_is_not_producer_generation(self):
        self.edit("owner", lambda value: value.update(utc="2026-10-26T10:00:01.0000000+00:00"))
        result = self.capture()
        self.assertEqual(result["status"], "sealed")
        self.assertEqual(packet.read_packet(self.store / "packet")["checkpoint"]["owner"]["start_utc"],
                         "2026-10-26T10:00:00.1234567Z")

    def test_pending_native_and_monitor_effects_hold(self):
        cases = [("terminal", lambda value: value["status"].update(pending={"id": "pending-op"})),
                 ("monitor", lambda value: value["active"].update(pending={"id": "pending-op"})),
                 ("native", lambda value: value["native"].update(pending={"id": "pending-op"})),
                 ("monitor", lambda value: value["active"].update(stage="native_dispatch"))]
        for index, (role, mutate) in enumerate(cases):
            with self.subTest(role=role, index=index):
                source = self.root / ("pending-inputs-" + str(index))
                request = fixture(source)
                value = packet.read_json(source / (role + ".json"))
                mutate(value)
                request["inputs"][role].update(write_json(source / (role + ".json"), value))
                from . import source_snapshot
                store = self.root / ("pending-store-" + str(index))
                result = source_snapshot.capture(request, source, store)
                self.assertEqual(result["status"], "held")
                self.assertFalse((store / "packet" / "current.json").exists())

    def test_later_or_uncertain_operations_never_replay_or_advance(self):
        for index, outcome in enumerate(("pending", "unknown", "partial", "saved", "failed_no_effect")):
            with self.subTest(outcome=outcome):
                source = self.root / ("later-inputs-" + str(index))
                request = fixture(source)
                journal = packet.read_json(source / "journal.json")
                later = copy.deepcopy(journal["operations"][0])
                later.update(id="later-operation", event_utc="2026-10-26T10:02:01Z",
                             outcome=outcome, reconciled=outcome in ("saved", "failed_no_effect"))
                if outcome in ("pending", "unknown"):
                    later["result_sha256"] = None
                journal["operations"].append(later)
                request["inputs"]["journal"].update(write_json(source / "journal.json", journal))
                from . import source_snapshot
                store = self.root / ("later-store-" + str(index))
                result = source_snapshot.capture(request, source, store)
                self.assertEqual(result["status"], "held")
                self.assertIn("LATER_OPERATION", {reason["code"] for reason in result["reasons"]})
                self.assertFalse((store / "packet" / "current.json").exists())

    def test_incomplete_journal_holds(self):
        self.edit("journal", lambda value: value.update(complete=False))
        self.assert_held(self.capture(), "JOURNAL_UNKNOWN")

    def test_cross_file_saved_counts_next_index_world_and_result_mismatch_hold(self):
        cases = [("monitor", lambda value: value.update(next_index=22)),
                 ("terminal", lambda value: value["status"]["saved_counts"].update(skull=21)),
                 ("ledger", lambda value: value["source_counts"].update(toter=21)),
                 ("ledger", lambda value: value.update(last_native_receipt="C:/Unexpected/native.json")),
                 ("native", lambda value: value["native"].update(world="/Game/Other.Other")),
                 ("journal", lambda value: value["operations"][0].update(intent_sha256="a" * 64)),
                 ("journal", lambda value: value["operations"][0].update(intent_sha256=self.request["inputs"]["native"]["sha256"])),
                 ("journal", lambda value: value["operations"][0].update(result_sha256="a" * 64)),
                 ("journal", lambda value: value["operations"][0].update(target_ids=["unretained-id"]))]
        for index, (role, mutate) in enumerate(cases):
            with self.subTest(role=role, index=index):
                source = self.root / ("mismatch-inputs-" + str(index))
                request = fixture(source)
                value = packet.read_json(source / (role + ".json"))
                mutate(value)
                request["inputs"][role].update(write_json(source / (role + ".json"), value))
                from . import source_snapshot
                store = self.root / ("mismatch-store-" + str(index))
                result = source_snapshot.capture(request, source, store)
                self.assertEqual(result["status"], "held")
                self.assertFalse((store / "packet" / "current.json").exists())

    def test_malformed_request_and_unsafe_or_duplicate_paths_refuse(self):
        cases = [lambda value: value.update(schema="unsupported"),
                 lambda value: value.update(profile="unsupported"),
                 lambda value: value.update(max_source_age_seconds=True),
                 lambda value: value.update(extra=True),
                 lambda value: value["inputs"]["owner"].update(path="../owner.json"),
                 lambda value: value["inputs"]["owner"].update(path="C:/Unsafe/owner.json"),
                 lambda value: value["inputs"]["owner"].update(path="SESSION.json")]
        for index, mutate in enumerate(cases):
            with self.subTest(index=index):
                request = copy.deepcopy(self.request)
                mutate(request)
                with self.assertRaises(ContractError):
                    self.capture(request, self.root / ("invalid-store-" + str(index)))

    def test_invalid_original_window_is_not_reset_at_capture(self):
        self.edit("session", lambda value: value.update(deadline_utc="2026-10-26T09:59:00Z"))
        self.assert_held(self.capture(), "INVALID_WINDOW")

    def test_supplemental_originals_and_result_tampering_fail_readback(self):
        for index, relative in enumerate(("request.json", "capture.json", "result.json", "copies/owner.json")):
            with self.subTest(relative=relative):
                store = self.root / ("tamper-store-" + str(index))
                result = self.capture(store=store)
                self.assertEqual(result["status"], "sealed")
                path = store / "source-snapshot" / relative
                if relative == "result.json":
                    value = packet.read_json(path)
                    value["schema"] = "unsupported"
                    write_json(path, value)
                else:
                    path.write_bytes(path.read_bytes() + b" ")
                with self.assertRaises((ContractError, OSError)):
                    self.read_snapshot(store)

    def test_optional_build_provenance_is_validated_and_bound_when_retained(self):
        source = {"schema": "daedalus.build-inputs.v1", "commit": "1" * 40,
                  "files": [{"path": "Source/Fixture.py", "category": "source", "bytes": 16,
                             "sha256": packet.digest(b"synthetic input\n")}]}
        source_pin = write_json(self.source / "source.json", source)
        build = {"schema": "daedalus.build-provenance.v1", "recorded_at_build_time": True,
                 "source_commit": source["commit"], "inputs_before_sha256": source_pin["sha256"],
                 "inputs_after_sha256": source_pin["sha256"], "artifact_sha256": self.request["runtime"]["artifact_sha256"],
                 "toolchain": {"engine": "synthetic-engine", "compiler": "synthetic-compiler"},
                 "command": ["synthetic-build", "fixture"], "exit_code": 0}
        build_pin = write_json(self.source / "build.json", build)
        for role, pin in (("source", source_pin), ("build", build_pin)):
            self.request["inputs"][role] = dict(pin, status="present", path=role + ".json",
                                                 logical_path="C:/Synthetic/Original/" + role + ".json", reason=None)
        self.request["source_state"]["dirty"] = False
        result = self.capture()
        self.assertEqual(result["status"], "sealed")
        self.assertEqual(result["admission_status"], "held")
        checkpoint = packet.read_packet(self.store / "packet")["checkpoint"]
        self.assertEqual(checkpoint["source"]["status"], "recorded")
        self.assertEqual(checkpoint["build"]["status"], "bound")
        self.assertEqual(checkpoint["source"]["manifest_sha256"], source_pin["sha256"])
        self.assertEqual(checkpoint["build"]["receipt_sha256"], build_pin["sha256"])
        build["inputs_after_sha256"] = "a" * 64
        self.request["inputs"]["build"].update(write_json(self.source / "build.json", build))
        other = self.root / "changed-build-store"
        self.assert_held(self.capture(store=other), "build_binding", store=other)

    def test_completed_snapshot_reader_requires_advertised_receipt_hash(self):
        from . import source_snapshot
        result = self.capture()
        self.assertEqual(source_snapshot.read_snapshot(self.store, expected_sha256=result["receipt_sha256"]), result)
        with self.assertRaises(ContractError) as caught:
            source_snapshot.read_snapshot(self.store, expected_sha256="f" * 64)
        self.assertEqual(caught.exception.code, "snapshot_receipt_hash")

    def test_unknown_essential_receipt_holds_and_old_liveness_is_only_source_data(self):
        missing = copy.deepcopy(self.request)
        missing["inputs"]["owner"] = {"status": "unknown", "path": None, "logical_path": None,
                                         "sha256": None, "bytes": None, "reason": "not exported"}
        self.assert_held(self.capture(missing), "INPUT_MISSING")
        self.edit("monitor", lambda value: value.update(owner_live=True, editor_live=True))
        other = self.root / "old-liveness-store"
        result = self.capture(store=other)
        self.assertEqual(result["status"], "sealed")
        self.assertEqual(result["liveness"], "not_observed")
        self.assertEqual(result["admission_status"], "held")

    def test_cli_capture_inspect_hold_and_invalid_profile_exit_codes(self):
        from . import cli
        request_file = self.root / "request-input.json"
        write_json(request_file, self.request)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["source-snapshot", "--request", str(request_file),
                                  "--source-root", str(self.source), "--store", str(self.store)])
        self.assertEqual(exit_code, 0, stderr.getvalue())
        sealed = json.loads(stdout.getvalue())
        self.assertEqual(sealed["status"], "sealed")
        self.assertEqual(sealed["admission_status"], "held")
        self.assertFalse(sealed["may_execute"])
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["inspect-source-snapshot", "--store", str(self.store),
                                  "--expected-receipt", sealed["receipt_sha256"]])
        self.assertEqual(exit_code, 0, stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue()), sealed)
        self.edit("journal", lambda value: value["operations"][0].update(outcome="pending", result_sha256=None, reconciled=False))
        write_json(request_file, self.request)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["source-snapshot", "--request", str(request_file),
                                  "--source-root", str(self.source), "--store", str(self.root / "pending-cli-store")])
        self.assertEqual(exit_code, 3, stderr.getvalue())
        held = json.loads(stdout.getvalue())
        self.assertEqual(held["status"], "held")
        self.assertIn("PENDING_WORK", {reason["code"] for reason in held["reasons"]})
        self.assertFalse(held["may_execute"])
        malformed = copy.deepcopy(self.request)
        malformed["profile"] = "unsupported-profile"
        write_json(request_file, malformed)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["source-snapshot", "--request", str(request_file),
                                  "--source-root", str(self.source), "--store", str(self.root / "invalid-cli-store")])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["error"]["code"], "UNSUPPORTED_SOURCE_PROFILE")
        self.assertFalse(error["may_execute"])

    def test_normalized_output_path_cannot_hide_overlap_with_source(self):
        before = self.originals()
        outside = self.root / "outside"
        outside.mkdir()
        disguised = outside / ".." / "originals" / "captured"
        with self.assertRaises(ContractError) as caught:
            self.capture(store=disguised)
        self.assertEqual(caught.exception.code, "overlapping_store")
        self.assertFalse((self.source / "captured").exists())
        self.assertEqual(self.originals(), before)

    def test_optional_legacy_identity_window_and_sequence_facts_cannot_contradict(self):
        cases = [("terminal", ("status", "r22_session"), "C:/Other/session", "SOURCE_MISMATCH"),
                 ("monitor", ("active", "r22_session"), "C:/Other/session", "SOURCE_MISMATCH"),
                 ("config", ("window_hours",), 2, "INVALID_WINDOW"),
                 ("session", ("editor_receipt", "configured_owner"), "foreign-owner", "SOURCE_MISMATCH"),
                 ("monitor", ("editor_pid",), 9001, "SOURCE_MISMATCH"),
                 ("monitor", ("last_native_receipt",), "C:/Other/native.json", "SOURCE_MISMATCH"),
                 ("owner", ("editor_launch_receipt",), "C:/Other/editor-launch.json", "SOURCE_MISMATCH"),
                 ("owner", ("utc",), "2026-10-26T10:00:02Z", "SOURCE_MISMATCH"),
                 ("session", ("initial_checkpoint", "next_index"), 12, "SOURCE_MISMATCH"),
                 ("session", ("speed_profile",), "different-profile", "SOURCE_MISMATCH"),
                 ("native", ("native", "open_sequence"), "/Game/Fixture/UnresolvedSequence", "PENDING_WORK")]
        from . import source_snapshot
        for index, case in enumerate([None] + cases):
            with self.subTest(case=case):
                source = self.root / ("optional-inputs-" + str(index))
                request = fixture(source)
                documents = {role: packet.read_json(source / (role + ".json"))
                             for role, row in request["inputs"].items() if row["status"] == "present"}
                documents["terminal"]["status"]["r22_session"] = request["session_ref"]
                documents["monitor"]["active"]["r22_session"] = request["session_ref"]
                documents["config"]["window_hours"] = 1
                documents["config"]["speed_profile"] = "existing-safe-serial"
                documents["session"]["initial_checkpoint"] = copy.deepcopy(documents["config"]["initial_checkpoint"])
                documents["session"]["speed_profile"] = documents["config"]["speed_profile"]
                documents["session"]["editor_receipt"]["configured_owner"] = request["identity"]["owner"]
                documents["monitor"]["editor_pid"] = documents["session"]["editor_receipt"]["pid"]
                documents["monitor"]["last_native_receipt"] = documents["ledger"]["last_native_receipt"]
                documents["owner"]["editor_launch_receipt"] = request["session_ref"] + "/editor-launch.json"
                documents["native"]["native"]["open_sequence"] = None
                if case is not None:
                    role, keys, value, code = case
                    target = documents[role]
                    for key in keys[:-1]:
                        target = target[key]
                    target[keys[-1]] = value
                for role, value in documents.items():
                    request["inputs"][role].update(write_json(source / (role + ".json"), value))
                documents["journal"]["operations"][0]["intent_sha256"] = request["inputs"]["ledger"]["sha256"]
                documents["journal"]["operations"][0]["result_sha256"] = request["inputs"]["native"]["sha256"]
                request["inputs"]["journal"].update(write_json(source / "journal.json", documents["journal"]))
                store = self.root / ("optional-store-" + str(index))
                result = source_snapshot.capture(request, source, store)
                if case is None:
                    self.assertEqual(result["status"], "sealed")
                else:
                    self.assert_held(result, code, store=store)

    def test_boolean_aliases_cannot_pass_integer_counts_indices_or_pids(self):
        cases = []
        states = (("ledger", ()), ("terminal", ("status",)),
                  ("monitor", ()), ("monitor", ("active",)))
        for role, prefix in states:
            for field in ("saved_counts", "source_counts"):
                cases.append((role, prefix + (field, "skull")))
            cases.append((role, prefix + ("next_index",)))
        cases += [("launch", ("pid",)), ("owner", ("pid",)),
                  ("terminal", ("pid",)), ("monitor", ("owner_pid",)),
                  ("session", ("editor_receipt", "pid")),
                  ("config", ("expected_editor_pid",)), ("owner", ("sole_editor",)),
                  ("monitor", ("editor_pid",)), ("ledger", ("owner_pid",)),
                  ("terminal", ("status", "owner_pid")), ("monitor", ("active", "owner_pid"))]
        from . import source_snapshot
        for index, case in enumerate([None] + cases):
            with self.subTest(case=case):
                source = self.root / ("integer-inputs-" + str(index))
                request = fixture(source)
                documents = {role: packet.read_json(source / (role + ".json"))
                             for role, row in request["inputs"].items() if row["status"] == "present"}
                for role, prefix in states:
                    state = documents[role]
                    for key in prefix:
                        state = state[key]
                    state.update(saved_counts={"skull": 1, "toter": 1}, source_counts={"skull": 1, "toter": 1},
                                 next_index=1, owner_pid=1)
                documents["launch"]["pid"] = documents["owner"]["pid"] = documents["terminal"]["pid"] = 1
                documents["session"]["editor_receipt"]["pid"] = 1
                documents["config"]["expected_editor_pid"] = documents["owner"]["sole_editor"] = 1
                documents["monitor"]["editor_pid"] = 1
                request["runtime"]["generation"] = "editor:1@" + documents["session"]["editor_receipt"]["start_utc"]
                if case is not None:
                    role, keys = case
                    target = documents[role]
                    for key in keys[:-1]:
                        target = target[key]
                    target[keys[-1]] = True
                for role, value in documents.items():
                    request["inputs"][role].update(write_json(source / (role + ".json"), value))
                documents["journal"]["operations"][0]["intent_sha256"] = request["inputs"]["ledger"]["sha256"]
                documents["journal"]["operations"][0]["result_sha256"] = request["inputs"]["native"]["sha256"]
                request["inputs"]["journal"].update(write_json(source / "journal.json", documents["journal"]))
                store = self.root / ("integer-store-" + str(index))
                result = source_snapshot.capture(request, source, store)
                if case is None:
                    self.assertEqual(result["status"], "sealed")
                else:
                    self.assert_held(result, "INVALID_FIELD", store=store)


if __name__ == "__main__":
    unittest.main()
