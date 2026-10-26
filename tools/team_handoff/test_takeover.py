# SPDX-License-Identifier: MIT
"""Serial, outgoing-agent-disabled acceptance tests using temporary files only."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from .contracts import ContractError, EVIDENCE_ROLES, plan, validate_checkpoint, validate_request
from . import packet
from . import cli


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(packet.canonical(value))
    return packet.digest(path.read_bytes())


def fixture(evidence_root):
    """Create a synthetic retained R20/R22-shaped boundary, never a live receipt."""
    root = Path(evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    counts = {"skull": 20, "toter": 20}
    identity = {"owner": "fixture-outgoing", "session": "fixture-session-1",
                "host": "fixture-host", "pid": 4242,
                "start_utc": "2026-10-26T10:00:00.1234567Z"}
    runtime = {"name": "fixture-runtime", "version": "3.10",
               "config_sha256": "2" * 64, "artifact_sha256": "3" * 64,
               "generation": "fixture-editor-9"}
    write_json(root / "checkpoint.json", {"saved_counts": counts, "next_index": 21,
                                          "owner_pid": identity["pid"],
                                          "active": {"stage": "paused_saved_boundary"}})
    write_json(root / "owner.json", dict(identity))
    ledger_hash = write_json(root / "ledger.json", {"saved_counts": counts,
                                                   "source_counts": counts, "next_index": 21,
                                                   "completed_chunks": ["fixture-chunk-1"],
                                                   "last_native_receipt": "native.json"})
    source = {"schema": "daedalus.build-inputs.v1", "commit": "1" * 40,
              "files": [{"path": "Source/Fixture.py", "category": "source", "bytes": 16,
                         "sha256": packet.digest(b"synthetic input\n")}]}
    source_hash = write_json(root / "source.json", source)
    build = {"schema": "daedalus.build-provenance.v1", "recorded_at_build_time": True,
             "source_commit": source["commit"], "inputs_before_sha256": source_hash,
             "inputs_after_sha256": source_hash, "artifact_sha256": runtime["artifact_sha256"],
             "toolchain": {"engine": "synthetic-engine", "compiler": "synthetic-compiler"},
             "command": ["synthetic-build", "fixture"], "exit_code": 0}
    build_hash = write_json(root / "build.json", build)
    native_hash = write_json(root / "native.json", {"native": {"saved": True,
                                     "dirty": {"maps": [], "content": []}, "play": False,
                                     "import_active": False, "stable_ids": ["fixture-skull-20", "fixture-toter-20"]}})
    write_json(root / "catalog.json", {"ids": ["fixture-skull-20", "fixture-toter-20"],
                                        "fixture_only": True})
    checkpoint = {"schema": "daedalus.takeover-checkpoint.v1", "campaign": "fixture-campaign",
                  "sequence": 1, "prior_sha256": None, "saved_utc": "2026-10-26T10:01:00Z",
                  "window": {"start_utc": "2026-10-26T10:01:00Z", "deadline_utc": "2026-10-26T11:01:00Z"},
                  "phase": "saved", "owner": identity, "runtime": runtime,
                  "progress": {"counts": counts, "next_index": 21, "last_operation_id": "fixture-save-1"},
                  "source": {"status": "recorded", "commit": source["commit"],
                             "manifest_sha256": source_hash, "dirty": False, "exceptions": [], "reason": None},
                  "build": {"status": "bound", "source_manifest_sha256": source_hash,
                            "artifact_sha256": runtime["artifact_sha256"], "receipt_sha256": build_hash, "reason": None},
                  "evidence": {role: {"status": "present", "path": role + ".json", "reason": None}
                               for role in EVIDENCE_ROLES},
                  "operations": [{"id": "fixture-save-1", "intent_sha256": ledger_hash,
                                  "target_ids": ["fixture-skull-20", "fixture-toter-20"],
                                  "outcome": "saved", "result_sha256": native_hash, "reconciled": True}]}
    return checkpoint


def request_for(checkpoint, packet_hash):
    """Supply explicit synthetic observations/authority, not live authorization."""
    return {"schema": "daedalus.takeover-admission.v1", "packet_sha256": packet_hash,
            "evaluated_utc": "2026-10-26T10:02:00Z",
            "successor": {"owner": "fixture-successor", "session": "fixture-session-2",
                          "host": checkpoint["owner"]["host"], "authority_ref": "fixture-assignment-only"},
            "previous_owner": {"identity": copy.deepcopy(checkpoint["owner"]), "state": "absent",
                               "observed_utc": "2026-10-26T10:01:59Z", "max_age_seconds": 30},
            "custody": {"owner": "fixture-successor", "unreal": "held", "compute": "held",
                        "authority_ref": "fixture-observation-only"},
            "runtime": copy.deepcopy(checkpoint["runtime"]),
            "source_manifest_sha256": checkpoint["source"]["manifest_sha256"],
            "build_receipt_sha256": checkpoint["build"]["receipt_sha256"],
            "journal": {"complete": True, "through_utc": "2026-10-26T10:02:00Z", "later_operations": []},
            "window": copy.deepcopy(checkpoint["window"])}


class OfflineTakeoverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="daedalus-offline-takeover-",
                                                     dir=os.environ.get("DAEDALUS_TEST_TMPDIR"))
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence = self.root / "inputs"
        self.store = self.root / "store"
        self.checkpoint = fixture(self.evidence)

    def seal(self, checkpoint=None, **kwargs):
        return packet.seal(self.store, checkpoint or self.checkpoint, self.evidence, **kwargs)

    def held(self, checkpoint, request, code, *, selection="current"):
        result = plan(checkpoint, request, request["packet_sha256"], selection=selection)
        self.assertEqual(result["status"], "held")
        self.assertFalse(result["may_execute"])
        self.assertTrue(result["live_integration_required"])
        self.assertIn(code, {reason["code"] for reason in result["reasons"]})
        self.assertEqual(result["progress"], checkpoint["progress"])
        return result

    def update(self, first):
        checkpoint = copy.deepcopy(self.checkpoint)
        checkpoint.update(sequence=2, prior_sha256=first["sha256"], saved_utc="2026-10-26T10:01:30Z")
        return checkpoint

    def rewrite_packet(self, first, mutate):
        """Fault fixture: recompute an outer digest to exercise semantic validation."""
        value = copy.deepcopy({key: first[key] for key in ("schema", "checkpoint", "files")})
        mutate(value)
        raw = packet.canonical(value)
        new_hash = packet.digest(raw)
        target = self.store / "packets" / new_hash
        shutil.copytree(self.store / "packets" / first["sha256"], target)
        (target / "manifest.json").write_bytes(raw)
        write_json(self.store / "current.json", {"schema": packet.POINTER_SCHEMA, "sha256": new_hash})

    def test_outgoing_absent_package_and_plan_need_no_network_or_process(self):
        originals = {path.name: path.read_bytes() for path in self.evidence.iterdir()}
        with mock.patch("socket.create_connection", side_effect=AssertionError("outgoing disabled")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("process launch disabled")):
            first = self.seal()
            loaded = packet.read_packet(self.store)
            request = request_for(loaded["checkpoint"], first["sha256"])
            result = plan(loaded["checkpoint"], request, loaded["sha256"])
        self.assertEqual(result["status"], "ready_for_live_admission")
        self.assertFalse(result["may_execute"])
        self.assertTrue(result["live_integration_required"])
        self.assertEqual(result["progress"]["next_index"], 21)
        self.assertEqual(result["operations"][0]["action"], "already_recorded")
        self.assertEqual(result, plan(loaded["checkpoint"], request, loaded["sha256"]))
        self.assertEqual(originals, {path.name: path.read_bytes() for path in self.evidence.iterdir()})

    def test_equivalent_inputs_produce_same_content_address(self):
        first = self.seal()
        other = packet.seal(self.root / "other-store", copy.deepcopy(self.checkpoint), self.evidence)
        self.assertEqual(first["sha256"], other["sha256"])
        self.assertEqual(first["files"], other["files"])

    def test_update_keeps_previous_and_requires_exact_current(self):
        first = self.seal()
        checkpoint = self.update(first)
        with self.assertRaises(ContractError) as caught:
            self.seal(checkpoint)
        self.assertEqual(caught.exception.code, "current_changed")
        second = self.seal(checkpoint, expected_current=first["sha256"])
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(packet.read_packet(self.store, "previous")["sha256"], first["sha256"])
        self.held(first["checkpoint"], request_for(first["checkpoint"], first["sha256"]), "NONCURRENT_PACKET", selection="previous")

    def test_faults_before_pointer_preserve_old_complete_packet(self):
        for phase in ("after_evidence", "after_manifest", "after_packet", "before_pointer_replace"):
            with self.subTest(phase=phase):
                store = self.root / ("fault-" + phase)
                first = packet.seal(store, self.checkpoint, self.evidence)
                checkpoint = self.update(first)
                def fail_at(actual):
                    if actual == phase:
                        raise RuntimeError("simulated writer loss at " + phase)
                with self.assertRaisesRegex(RuntimeError, "simulated writer loss"):
                    packet.seal(store, checkpoint, self.evidence, expected_current=first["sha256"], fault=fail_at)
                self.assertEqual(packet.read_packet(store)["sha256"], first["sha256"])
                self.assertTrue(any((store / "packets").iterdir()))
                second = packet.seal(store, checkpoint, self.evidence, expected_current=first["sha256"])
                self.assertEqual(packet.read_packet(store, "previous")["sha256"], first["sha256"])
                self.assertEqual(second["checkpoint"]["sequence"], 2)

    def test_fault_after_pointer_is_observed_as_published_before_any_retry(self):
        first = self.seal()
        checkpoint = self.update(first)
        def lost_reply(phase):
            if phase == "after_pointer":
                raise RuntimeError("lost response after publication")
        with self.assertRaisesRegex(RuntimeError, "lost response"):
            self.seal(checkpoint, expected_current=first["sha256"], fault=lost_reply)
        current = packet.read_packet(self.store)
        self.assertEqual(current["checkpoint"], checkpoint)
        self.assertEqual(packet.read_packet(self.store, "previous")["sha256"], first["sha256"])
        with self.assertRaises(ContractError) as caught:
            self.seal(checkpoint, expected_current=first["sha256"])
        self.assertEqual(caught.exception.code, "current_changed")

    def test_first_publication_failure_never_advertises_partial_packet(self):
        def fail_before_manifest(phase):
            if phase == "after_evidence":
                raise RuntimeError("writer absent")
        with self.assertRaises(RuntimeError):
            self.seal(fault=fail_before_manifest)
        self.assertFalse((self.store / "current.json").exists())
        with self.assertRaises(FileNotFoundError):
            packet.read_packet(self.store)

    def test_evidence_tamper_same_size_and_size_change_fail(self):
        for payload in (b"!", b"tampered with a longer payload"):
            with self.subTest(payload=payload):
                store = self.root / ("tamper-" + str(len(payload)))
                first = packet.seal(store, self.checkpoint, self.evidence)
                evidence = store / "packets" / first["sha256"] / "evidence" / "catalog.json"
                original = evidence.read_bytes()
                evidence.write_bytes(payload * len(original) if len(payload) == 1 else payload)
                with self.assertRaises(ContractError) as caught:
                    packet.read_packet(store)
                self.assertEqual(caught.exception.code, "evidence_hash")

    def test_manifest_tamper_fails_hash_before_interpretation(self):
        first = self.seal()
        manifest = self.store / "packets" / first["sha256"] / "manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b" ")
        with self.assertRaises(ContractError) as caught:
            packet.read_packet(self.store)
        self.assertEqual(caught.exception.code, "manifest_hash")

    def test_version_mismatches_and_unknown_fields_fail(self):
        for mutate in (lambda cp: cp.update(schema="daedalus.takeover-checkpoint.v99"),
                       lambda cp: cp.update(override=True),
                       lambda cp: cp["owner"].update(unrecognized=True)):
            with self.subTest(mutate=mutate):
                cp = copy.deepcopy(self.checkpoint)
                mutate(cp)
                with self.assertRaises(ContractError):
                    validate_checkpoint(cp)
        first = self.seal()
        self.rewrite_packet(first, lambda value: value.update(schema="daedalus.takeover-packet.v99"))
        with self.assertRaises(ContractError) as caught:
            packet.read_packet(self.store)
        self.assertEqual(caught.exception.code, "packet_version")

    def test_torn_pointer_does_not_silently_fall_back(self):
        first = self.seal()
        self.seal(self.update(first), expected_current=first["sha256"])
        (self.store / "current.json").write_bytes(b'{"schema":')
        with self.assertRaises(ContractError):
            packet.read_packet(self.store)
        previous = packet.read_packet(self.store, "previous")
        self.assertEqual(previous["sha256"], first["sha256"])
        self.held(previous["checkpoint"], request_for(previous["checkpoint"], previous["sha256"]),
                  "NONCURRENT_PACKET", selection="previous")

    def test_unexpected_or_missing_packet_files_are_rejected(self):
        first = self.seal()
        extra = self.store / "packets" / first["sha256"] / "extra.json"
        extra.write_text("{}", encoding="utf-8")
        with self.assertRaises(ContractError) as caught:
            packet.read_packet(self.store)
        self.assertEqual(caught.exception.code, "packet_inventory")
        other = packet.seal(self.root / "missing-store", self.checkpoint, self.evidence)
        path = self.root / "missing-store" / "packets" / other["sha256"] / "evidence" / "catalog.json"
        path.rename(path.with_name("renamed.json"))
        with self.assertRaises(ContractError) as caught:
            packet.read_packet(self.root / "missing-store")
        self.assertEqual(caught.exception.code, "packet_inventory")

    def test_chain_sequence_campaign_time_and_progress_regression_fail(self):
        first = self.seal()
        mutations = [lambda cp: cp.update(sequence=3), lambda cp: cp.update(campaign="other"),
                     lambda cp: cp.update(prior_sha256="f" * 64),
                     lambda cp: cp.update(saved_utc="2026-10-26T10:00:00Z"),
                     lambda cp: cp["progress"]["counts"].update(skull=19),
                     lambda cp: cp["progress"].update(next_index=20)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                cp = self.update(first)
                mutate(cp)
                with self.assertRaises(ContractError):
                    self.seal(cp, expected_current=first["sha256"])
                self.assertEqual(packet.read_packet(self.store)["sha256"], first["sha256"])

    def test_publication_chain_cannot_reset_authorized_window(self):
        first = self.seal()
        for changes in ({"start_utc": "2026-10-26T10:01:10Z"},
                        {"deadline_utc": "2026-10-26T12:01:00Z"}):
            with self.subTest(changes=changes):
                cp = self.update(first)
                cp["window"].update(changes)
                with self.assertRaises(ContractError) as caught:
                    self.seal(cp, expected_current=first["sha256"])
                self.assertEqual(caught.exception.code, "window_chain")
                self.assertEqual(packet.read_packet(self.store)["sha256"], first["sha256"])

    def test_owner_alive_unknown_reused_and_stale_all_hold(self):
        for state in ("alive", "unknown", "reused"):
            with self.subTest(state=state):
                request = request_for(self.checkpoint, "a" * 64)
                request["previous_owner"]["state"] = state
                self.held(self.checkpoint, request, "OWNER_" + state.upper())
        for observed in ("2026-10-26T10:00:00Z", "2026-10-26T10:02:01Z"):
            request = request_for(self.checkpoint, "a" * 64)
            request["previous_owner"]["observed_utc"] = observed
            self.held(self.checkpoint, request, "STALE_OWNER_OBSERVATION")

    def test_generation_precision_distinguishes_seven_digit_start_times(self):
        request = request_for(self.checkpoint, "a" * 64)
        request["previous_owner"]["identity"]["start_utc"] = "2026-10-26T10:00:00.1234568Z"
        self.held(self.checkpoint, request, "OWNER_IDENTITY_CHANGED")
        request["previous_owner"]["identity"]["start_utc"] = "2026-10-26T10:00:00.123456700+00:00"
        result = plan(self.checkpoint, request, request["packet_sha256"])
        self.assertEqual(result["status"], "ready_for_live_admission")

    def test_custody_authority_runtime_and_window_contracts_hold(self):
        cases = [(lambda req: req["custody"].update(owner="foreign"), "CUSTODY_UNESTABLISHED"),
                 (lambda req: req["custody"].update(unreal="unknown"), "CUSTODY_UNESTABLISHED"),
                 (lambda req: req["custody"].update(compute="foreign"), "CUSTODY_UNESTABLISHED"),
                 (lambda req: req["successor"].update(session=self.checkpoint["owner"]["session"]), "SESSION_REUSED"),
                 (lambda req: req["successor"].update(host="different-host"), "HOST_CHANGED"),
                 (lambda req: req["runtime"].update(version="changed"), "RUNTIME_CHANGED"),
                 (lambda req: req["runtime"].update(config_sha256="b" * 64), "RUNTIME_CHANGED"),
                 (lambda req: req["runtime"].update(artifact_sha256="b" * 64), "RUNTIME_CHANGED"),
                 (lambda req: req["runtime"].update(generation="changed"), "RUNTIME_CHANGED"),
                 (lambda req: req.update(build_receipt_sha256="b" * 64), "BUILD_CHANGED"),
                 (lambda req: req.update(source_manifest_sha256="b" * 64), "SOURCE_CHANGED"),
                 (lambda req: req["window"].update(deadline_utc="2026-10-26T10:01:59Z"), "WINDOW_CLOSED")]
        for mutate, code in cases:
            with self.subTest(code=code, mutate=mutate):
                request = request_for(self.checkpoint, "a" * 64)
                mutate(request)
                self.held(self.checkpoint, request, code)
        for missing in ("successor", "custody"):
            request = request_for(self.checkpoint, "a" * 64)
            request[missing]["authority_ref"] = ""
            with self.assertRaises(ContractError):
                validate_request(request)

    def test_explicit_missing_provenance_can_be_sealed_but_never_admitted(self):
        cp = copy.deepcopy(self.checkpoint)
        cp["source"] = {"status": "unknown", "commit": None, "manifest_sha256": None,
                        "dirty": None, "exceptions": [], "reason": "historical inputs absent"}
        cp["build"] = {"status": "unknown", "source_manifest_sha256": None,
                       "artifact_sha256": None, "receipt_sha256": None, "reason": "historical build binding absent"}
        for role in ("source", "build"):
            cp["evidence"][role] = {"status": "unknown", "path": None, "reason": "not retained"}
        first = self.seal(cp)
        result = self.held(cp, request_for(cp, first["sha256"]), "BUILD_PROVENANCE_UNKNOWN")
        self.assertIn("SOURCE_PROVENANCE_UNKNOWN", {row["code"] for row in result["reasons"]})
        self.assertEqual(packet.read_packet(self.store)["checkpoint"]["build"]["status"], "unknown")

    def test_missing_absence_reason_is_not_an_implicit_override(self):
        cp = copy.deepcopy(self.checkpoint)
        cp["build"]["status"] = "unknown"
        with self.assertRaises(ContractError):
            validate_checkpoint(cp)
        cp = copy.deepcopy(self.checkpoint)
        cp["source"]["exceptions"] = ["untracked input not historically bound"]
        self.held(cp, request_for(cp, "a" * 64), "SOURCE_EXCEPTIONS")

    def test_build_input_change_and_missing_build_receipt_fail_sealing(self):
        for field, value in (("inputs_after_sha256", "b" * 64), ("recorded_at_build_time", False),
                             ("artifact_sha256", "b" * 64), ("exit_code", 1), ("toolchain", {})):
            with self.subTest(field=field):
                source = self.root / ("bad-build-" + field)
                cp = fixture(source)
                build = json.loads((source / "build.json").read_text(encoding="utf-8"))
                build[field] = value
                cp["build"]["receipt_sha256"] = write_json(source / "build.json", build)
                with self.assertRaises(ContractError) as caught:
                    packet.seal(self.root / ("bad-store-" + field), cp, source)
                self.assertEqual(caught.exception.code, "build_binding")
        cp = copy.deepcopy(self.checkpoint)
        cp["evidence"]["build"] = {"status": "unknown", "path": None, "reason": "missing"}
        with self.assertRaises(ContractError):
            self.seal(cp)

    def test_inflight_unknown_partial_and_pending_operations_preserve_index(self):
        for outcome in ("pending", "unknown", "partial"):
            with self.subTest(outcome=outcome):
                cp = copy.deepcopy(self.checkpoint)
                cp["phase"] = "in_flight"
                operation = copy.deepcopy(cp["operations"][0])
                operation.update(id="fixture-next-operation", outcome=outcome, reconciled=False)
                if outcome != "partial":
                    operation["result_sha256"] = None
                cp["operations"].append(operation)
                first = packet.seal(self.root / ("inflight-" + outcome), cp, self.evidence)
                result = self.held(cp, request_for(cp, first["sha256"]), "OPERATION_UNRECONCILED")
                self.assertIn("UNRESOLVED_PHASE", {reason["code"] for reason in result["reasons"]})
                self.assertEqual(result["operations"][-1]["action"], "reconcile")
                self.assertEqual(result["progress"]["next_index"], 21)

    def test_saved_unreconciled_operation_never_replays_or_advances(self):
        cp = copy.deepcopy(self.checkpoint)
        cp["operations"][0]["reconciled"] = False
        result = self.held(cp, request_for(cp, "a" * 64), "OPERATION_UNRECONCILED")
        self.assertEqual(result["operations"][0]["action"], "reconcile")
        cp["operations"][0]["reconciled"] = True
        request = request_for(cp, "a" * 64)
        result = plan(cp, request, request["packet_sha256"])
        self.assertEqual(result["status"], "ready_for_live_admission")
        self.assertEqual(result["operations"][0]["action"], "already_recorded")
        self.assertEqual(result["progress"]["next_index"], 21)

    def test_later_journal_result_requires_new_reconciled_checkpoint(self):
        for outcome in ("unknown", "saved", "failed_no_effect"):
            with self.subTest(outcome=outcome):
                request = request_for(self.checkpoint, "a" * 64)
                later = copy.deepcopy(self.checkpoint["operations"][0])
                later.update(id="later-dispatch", outcome=outcome, reconciled=outcome != "unknown")
                request["journal"]["later_operations"] = [later]
                result = self.held(self.checkpoint, request, "LATER_OPERATION")
                self.assertEqual(result["operations"][-1]["action"], "reconcile")
        request = request_for(self.checkpoint, "a" * 64)
        changed = copy.deepcopy(self.checkpoint["operations"][0])
        changed["target_ids"] = ["different-stable-id"]
        request["journal"]["later_operations"] = [changed]
        self.held(self.checkpoint, request, "OPERATION_CHANGED")

    def test_incomplete_or_old_journal_inventory_holds(self):
        for mutate in (lambda journal: journal.update(complete=False),
                       lambda journal: journal.update(through_utc="2026-10-26T10:01:58Z"),
                       lambda journal: journal.update(through_utc="2026-10-26T10:02:01Z")):
            request = request_for(self.checkpoint, "a" * 64)
            mutate(request["journal"])
            self.held(self.checkpoint, request, "JOURNAL_INCOMPLETE")

    def test_unsafe_and_duplicate_paths_are_rejected(self):
        for name in ("../owner.json", "/absolute.json", "C:/owner.json", "a\\owner.json",
                     "a//owner.json", "CON.json", "folder/../owner.json", "folder/owner."):
            with self.subTest(name=name):
                cp = copy.deepcopy(self.checkpoint)
                cp["evidence"]["owner"]["path"] = name
                with self.assertRaises(ContractError):
                    self.seal(cp)
        cp = copy.deepcopy(self.checkpoint)
        cp["evidence"]["owner"]["path"] = "CHECKPOINT.json"
        with self.assertRaises(ContractError):
            self.seal(cp)

    def test_duplicate_json_keys_nonfinite_json_and_boolean_counts_fail(self):
        for raw in (b'{"schema":1,"schema":2}', b'{"value":NaN}', b'{"value":Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ContractError):
                    packet.decode(raw)
        cp = copy.deepcopy(self.checkpoint)
        cp["progress"]["counts"]["skull"] = True
        with self.assertRaises(ContractError):
            validate_checkpoint(cp)

    def test_store_overlap_and_busy_publisher_fail_without_reclaim(self):
        for store in (self.evidence, self.evidence / "store"):
            with self.subTest(store=store):
                with self.assertRaises(ContractError) as caught:
                    packet.seal(store, self.checkpoint, self.evidence)
                self.assertEqual(caught.exception.code, "overlapping_store")
        self.store.mkdir()
        with packet._writer(self.store):
            with self.assertRaises(ContractError) as caught:
                self.seal()
            self.assertEqual(caught.exception.code, "publisher_busy")
        self.assertTrue((self.store / ".publish.lock").exists())
        self.assertFalse((self.store / "current.json").exists())

    def test_unbound_operation_receipts_fail_sealing(self):
        for key in ("intent_sha256", "result_sha256"):
            cp = copy.deepcopy(self.checkpoint)
            cp["operations"][0][key] = "e" * 64
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.seal(cp)

    def test_contradictory_legacy_boundary_evidence_fails(self):
        mutations = [("ledger", lambda value: value.update(next_index=999)),
                     ("ledger", lambda value: value["saved_counts"].update(skull=999)),
                     ("checkpoint", lambda value: value.update(owner_pid=999)),
                     ("checkpoint", lambda value: value.update(next_index=999)),
                     ("checkpoint", lambda value: value["active"].update(stage="native_dispatch")),
                     ("checkpoint", lambda value: value["active"].update(pending="unresolved-dispatch")),
                     ("owner", lambda value: value.update(pid=999)),
                     ("owner", lambda value: value.update(owner="different-owner")),
                     ("owner", lambda value: value.update(session="different-session")),
                     ("owner", lambda value: value.update(host="different-host")),
                     ("owner", lambda value: value.update(start_utc="2026-10-26T10:00:00.1234568Z")),
                     ("native", lambda value: value["native"].update(saved=False)),
                     ("native", lambda value: value["native"].update(play=True)),
                     ("native", lambda value: value["native"].update(import_active=True)),
                     ("native", lambda value: value["native"]["dirty"]["maps"].append("unresolved-world"))]
        for index, (role, mutate) in enumerate(mutations):
            with self.subTest(role=role, index=index):
                evidence = self.root / ("contradiction-" + str(index))
                cp = fixture(evidence)
                value = json.loads((evidence / (role + ".json")).read_text(encoding="utf-8"))
                mutate(value)
                changed_hash = write_json(evidence / (role + ".json"), value)
                if role == "ledger":
                    cp["operations"][0]["intent_sha256"] = changed_hash
                elif role == "native":
                    cp["operations"][0]["result_sha256"] = changed_hash
                with self.assertRaises(ContractError):
                    packet.seal(self.root / ("contradictory-store-" + str(index)), cp, evidence)

    def test_cli_seal_inspect_ready_and_held_exit_codes(self):
        checkpoint_file = self.root / "checkpoint-input.json"
        request_file = self.root / "admission-input.json"
        write_json(checkpoint_file, self.checkpoint)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["seal", "--store", str(self.store), "--checkpoint", str(checkpoint_file),
                                  "--evidence-root", str(self.evidence), "--expected-current", "none"])
        self.assertEqual(exit_code, 0, stderr.getvalue())
        published = json.loads(stdout.getvalue())
        self.assertTrue(published["published"])
        self.assertFalse(published["may_execute"])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(cli.main(["inspect", "--store", str(self.store)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["sha256"], published["sha256"])
        request = request_for(self.checkpoint, published["sha256"])
        for state, expected_exit in (("absent", 0), ("unknown", 3)):
            with self.subTest(state=state):
                request["previous_owner"]["state"] = state
                write_json(request_file, request)
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(cli.main(["plan", "--store", str(self.store), "--request", str(request_file)]), expected_exit)
                value = json.loads(stdout.getvalue())
                self.assertEqual(value["status"], "held" if state == "unknown" else "ready_for_live_admission")
                self.assertFalse(value["may_execute"])
                self.assertEqual(stderr.getvalue(), "")

    def test_cli_error_is_actionable_json_and_has_nonzero_exit(self):
        for name, raw, code in (("malformed.json", b'{"schema":', "invalid_json"),
                                ("version.json", packet.canonical(dict(self.checkpoint, schema="unsupported")), "UNSUPPORTED_VERSION")):
            with self.subTest(name=name):
                source = self.root / name
                source.write_bytes(raw)
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(cli.main(["seal", "--store", str(self.store), "--checkpoint", str(source),
                                               "--evidence-root", str(self.evidence), "--expected-current", "none"]), 2)
                value = json.loads(stderr.getvalue())
                self.assertEqual(value["error"]["code"], code)
                self.assertFalse(value["may_execute"])
                self.assertEqual(stdout.getvalue(), "")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(["inspect", "--store", str(self.root / "missing-store")]), 2)
        self.assertIn("absent", json.loads(stderr.getvalue())["error"]["message"])

    def test_packet_identity_mismatch_and_request_version_never_admit(self):
        request = request_for(self.checkpoint, "a" * 64)
        value = plan(self.checkpoint, request, "b" * 64)
        self.assertEqual(value["status"], "held")
        self.assertIn("PACKET_CHANGED", {reason["code"] for reason in value["reasons"]})
        request["schema"] = "daedalus.takeover-admission.v99"
        with self.assertRaises(ContractError) as caught:
            validate_request(request)
        self.assertEqual(caught.exception.code, "UNSUPPORTED_VERSION")

    def test_window_reset_dirty_source_and_missing_last_operation_hold(self):
        for changes in ({"start_utc": "2026-10-26T10:01:30Z"},
                        {"deadline_utc": "2026-10-26T12:01:00Z"}):
            with self.subTest(changes=changes):
                request = request_for(self.checkpoint, "a" * 64)
                request["window"].update(changes)
                self.held(self.checkpoint, request, "WINDOW_CHANGED")
        cp = copy.deepcopy(self.checkpoint)
        cp["source"]["dirty"] = True
        self.held(cp, request_for(cp, "a" * 64), "DIRTY_SOURCE")
        cp = copy.deepcopy(self.checkpoint)
        cp["progress"]["last_operation_id"] = None
        self.held(cp, request_for(cp, "a" * 64), "LAST_OPERATION_MISSING")


if __name__ == "__main__":
    unittest.main()
