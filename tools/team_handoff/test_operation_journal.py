# SPDX-License-Identifier: MIT
"""Durable journal tests with synthetic receipts and no outgoing participant."""
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


def write_json(root, name, value, logical_path=None):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(packet.canonical(value))
    return {"path": name, "logical_path": logical_path or "C:/Synthetic/Original/" + name,
            "sha256": packet.digest(path.read_bytes()), "bytes": path.stat().st_size}


def fixture(parent):
    """Return config, first intent and explicitly supplied synthetic evidence root."""
    root = Path(parent) / "inputs"
    root.mkdir(parents=True, exist_ok=True)
    config = {"schema": "daedalus.operation-journal-store.v1",
              "identity": {"owner": "fixture-owner", "session": "fixture-session", "host": "fixture-host"},
              "window": {"start_utc": "2026-10-26T10:00:00Z", "deadline_utc": "2026-10-26T11:00:00Z"},
              "scope": {"kind": "declared-store-only", "id": "fixture-operation-boundary"},
              "created_utc": "2026-10-26T10:00:00Z", "authority_ref": "fixture-original-assignment"}
    original = write_json(root, "input.json", {"fixture_only": True, "job": "fixture-save-1"})
    intent = {"schema": "daedalus.operation-journal-intent.v1", "operation_key": "op-1",
              "operation_id": "fixture-save-1", "session_id": config["identity"]["session"],
              "event_utc": "2026-10-26T10:01:00Z", "kind": "fixture-native-save",
              "expected_predecessor_sha256": None, "target_ids": ["fixture-skull-1", "fixture-toter-1"],
              "output_refs": ["/Game/Fixture/SavedBoundary"], "inputs": [original]}
    return config, intent, root


def record_spec(intent, root, stage, *, outcome=None, references=None, tag=""):
    """Create a matching record/proof pair; all apparent native facts are fixtures."""
    outcome = outcome or ("success" if stage == "result" else "saved")
    refs = {"result_sha256": None, "save_sha256": None, "native_sha256": None, "ledger_sha256": None}
    if references:
        refs.update(references)
    evidence = {"receipt": None, "native": None, "ledger": None}
    if stage == "save" and outcome == "saved":
        native = {"native": {"saved": True, "dirty": {"maps": [], "content": []}, "play": False,
                              "import_active": False, "pending": None,
                              "world": "/Game/Fixture/SavedBoundary.SavedBoundary",
                              "item_records": {target: {} for target in intent["target_ids"]}}}
        native_pin = write_json(root, "native" + tag + ".json", native)
        ledger = {"saved_counts": {"skull": 1, "toter": 1}, "source_counts": {"skull": 1, "toter": 1},
                  "next_index": 2, "last_native_receipt": native_pin["logical_path"],
                  "last_world": "/Game/Fixture/SavedBoundary"}
        ledger_pin = write_json(root, "ledger" + tag + ".json", ledger)
        evidence.update(native=native_pin, ledger=ledger_pin)
        refs.update(native_sha256=native_pin["sha256"], ledger_sha256=ledger_pin["sha256"])
    event_utc = {"result": "2026-10-26T10:02:00Z", "save": "2026-10-26T10:03:00Z", "readback": "2026-10-26T10:04:00Z"}[stage]
    reason = "Explicit synthetic unresolved result" if outcome in ("partial", "unknown") else None
    spec = {"schema": "daedalus.operation-journal-record.v1", "stage": stage,
            "operation_key": intent["operation_key"], "operation_id": intent["operation_id"],
            "session_id": intent["session_id"], "event_utc": event_utc,
            "intent_sha256": packet.digest(packet.canonical(intent)), "target_ids": copy.deepcopy(intent["target_ids"]),
            "outcome": outcome, "references": refs, "evidence": evidence, "reason": reason}
    proof = {key: copy.deepcopy(value) for key, value in spec.items() if key not in ("schema", "operation_key", "evidence")}
    proof.update(schema="daedalus.operation-journal-proof.v1",
                 saved=(outcome == "saved") if stage == "save" else None,
                 matches=(outcome in ("saved", "failed_no_effect")) if stage == "readback" else None)
    evidence["receipt"] = write_json(root, stage + "-proof" + tag + ".json", proof)
    return spec


def saved_records(intent, root):
    result = record_spec(intent, root, "result")
    saved = record_spec(intent, root, "save", references={"result_sha256": result["evidence"]["receipt"]["sha256"]})
    refs = dict(saved["references"], save_sha256=saved["evidence"]["receipt"]["sha256"])
    readback = record_spec(intent, root, "readback", references=refs)
    return result, saved, readback


def coverage_spec(config, head, operation_keys, root, *, producer_complete=True, tag=""):
    value = {"schema": "daedalus.operation-journal-coverage.v1", "session_id": config["identity"]["session"],
             "event_utc": "2026-10-26T10:05:00Z", "through_utc": "2026-10-26T10:05:00Z",
             "authority_ref": config["authority_ref"], "window": copy.deepcopy(config["window"]),
             "scope_id": config["scope"]["id"], "covers_head_sha256": head,
             "operation_keys": sorted(operation_keys), "producer_complete": producer_complete}
    proof = dict(value, schema="daedalus.operation-journal-coverage-proof.v1")
    value["receipt"] = write_json(root, "coverage-proof" + tag + ".json", proof)
    return value


class OperationJournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="daedalus-operation-journal-",
                                                     dir=os.environ.get("DAEDALUS_TEST_TMPDIR"))
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config, self.intent_spec, self.evidence = fixture(self.root)
        self.store = self.root / "store"

    @staticmethod
    def library():
        from . import operation_journal
        return operation_journal

    def create(self, store=None):
        return self.library().create(store or self.store, self.config)

    def intent(self, spec=None, store=None, fault=None):
        return self.library().intent(store or self.store, spec or self.intent_spec, self.evidence, fault=fault)

    def record(self, spec, store=None, fault=None):
        return self.library().record(store or self.store, spec, self.evidence, fault=fault)

    def inspect(self, store=None):
        return self.library().inspect(store or self.store)

    def originals(self):
        return {path.relative_to(self.evidence).as_posix(): path.read_bytes()
                for path in self.evidence.rglob("*") if path.is_file()}

    def inventory(self, through="2026-10-26T10:05:00Z", store=None):
        return self.library().inventory(store or self.store, through)

    def populate_saved(self, store=None):
        store = store or self.store
        self.create(store)
        granted = self.intent(store=store)
        self.assertTrue(granted["dispatch_granted"])
        stages = saved_records(self.intent_spec, self.evidence)
        for spec in stages:
            result = self.record(spec, store=store)
            self.assertTrue(result["recorded"])
            self.assertFalse(result["dispatch_granted"])
        return granted, stages

    def duplicate_without_grant(self, store, spec=None):
        try:
            answer = self.intent(spec, store=store)
        except ContractError:
            return
        self.assertFalse(answer["dispatch_granted"])

    @staticmethod
    def update_record_proof(spec, root, tag):
        proof = {key: copy.deepcopy(value) for key, value in spec.items() if key not in ("schema", "operation_key", "evidence")}
        proof.update(schema="daedalus.operation-journal-proof.v1",
                     saved=(spec["outcome"] == "saved") if spec["stage"] == "save" else None,
                     matches=(spec["outcome"] in ("saved", "failed_no_effect")) if spec["stage"] == "readback" else None)
        spec["evidence"]["receipt"] = write_json(root, spec["stage"] + "-proof-" + tag + ".json", proof)

    def test_intent_survives_outgoing_absence_and_only_one_call_grants(self):
        before = self.originals()
        with mock.patch("socket.create_connection", side_effect=AssertionError("outgoing disabled")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("process launch disabled")):
            self.create()
            first = self.intent()
            second = self.intent()
            recovered = self.library().recover(self.store)
            third = self.intent()
        self.assertTrue(first["dispatch_granted"])
        self.assertFalse(second["dispatch_granted"])
        self.assertFalse(third["dispatch_granted"])
        self.assertFalse(recovered["dispatch_granted"])
        self.assertEqual(first["intent_sha256"], packet.digest(packet.canonical(self.intent_spec)))
        self.assertFalse(first["may_execute"])
        self.assertEqual(self.originals(), before)
        self.assertEqual(self.inspect()["sequence"], 1)

    def test_exact_duplicate_intent_and_stage_preserve_head_and_original_times(self):
        self.create()
        first = self.intent()
        duplicate = self.intent()
        self.assertFalse(duplicate["recorded"])
        self.assertFalse(duplicate["dispatch_granted"])
        self.assertEqual(self.inspect()["head_sha256"], first["head_sha256"])
        result = record_spec(self.intent_spec, self.evidence, "result")
        recorded = self.record(result)
        duplicated = self.record(result)
        self.assertTrue(recorded["recorded"])
        self.assertFalse(duplicated["recorded"])
        self.assertFalse(duplicated["dispatch_granted"])
        self.assertEqual(self.inspect()["head_sha256"], recorded["head_sha256"])
        self.assertEqual(self.inspect()["operations"][self.intent_spec["operation_key"]]["stages"]["result"]["event_utc"], result["event_utc"])

    def test_conflicting_key_and_aliases_never_grant_or_replace_original(self):
        self.create()
        first = self.intent()
        cases = [dict(self.intent_spec, kind="different-kind"),
                 dict(self.intent_spec, operation_key="different-key", operation_id="different-operation"),
                 dict(self.intent_spec, event_utc="2026-10-26T10:01:01Z")]
        for spec in cases:
            with self.subTest(spec=spec), self.assertRaises(ContractError):
                self.intent(spec)
            self.assertEqual(self.inspect()["head_sha256"], first["head_sha256"])
        self.assertEqual(len(self.inspect()["operations"]), 1)

    def test_fault_before_reservation_never_creates_false_replay_proof(self):
        self.create()
        def stop(phase):
            if phase == "before_reservation":
                raise RuntimeError("writer absent before reservation")
        with self.assertRaises(RuntimeError):
            self.intent(fault=stop)
        self.assertFalse(list((self.store / "reservations").glob("*.json")))
        self.assertEqual(self.inspect()["sequence"], 0)
        first_actual_grant = self.intent()
        self.assertTrue(first_actual_grant["dispatch_granted"])
        self.assertFalse(self.intent()["dispatch_granted"])

    def test_durable_reservation_without_intent_stays_held_and_never_regrants(self):
        for phase in ("after_reservation", "after_inputs"):
            with self.subTest(phase=phase):
                store = self.root / ("reservation-" + phase)
                self.create(store)
                def stop(actual):
                    if actual == phase:
                        raise RuntimeError("caller absent at " + phase)
                with self.assertRaises(RuntimeError):
                    self.intent(store=store, fault=stop)
                state = self.inspect(store)
                self.assertEqual(state["status"], "held")
                self.assertTrue(state["issues"])
                self.assertTrue(list((store / "reservations").glob("*.json")))
                recovery = self.library().recover(store)
                self.assertFalse(recovery["dispatch_granted"])
                self.assertEqual(recovery["adopted_events"], 0)
                self.duplicate_without_grant(store)

    def test_orphan_event_recovery_adopts_complete_chain_without_dispatch_grant(self):
        for phase in ("after_event", "before_pointer_replace"):
            with self.subTest(phase=phase):
                store = self.root / ("orphan-" + phase)
                self.create(store)
                def stop(actual):
                    if actual == phase:
                        raise RuntimeError("lost publisher at " + phase)
                with self.assertRaises(RuntimeError):
                    self.intent(store=store, fault=stop)
                state = self.inspect(store)
                self.assertEqual(state["status"], "held")
                self.assertTrue(state["orphans"])
                original_events = {path.name: path.read_bytes() for path in (store / "events").glob("*.json")}
                recovered = self.library().recover(store)
                self.assertFalse(recovered["dispatch_granted"])
                self.assertEqual(recovered["adopted_events"], 1)
                self.assertEqual(original_events, {path.name: path.read_bytes() for path in (store / "events").glob("*.json")})
                self.duplicate_without_grant(store)

    def test_lost_reply_after_pointer_is_read_before_retry_and_never_regranted(self):
        self.create()
        def lost_reply(phase):
            if phase == "after_pointer":
                raise RuntimeError("reply lost after durable selection")
        with self.assertRaises(RuntimeError):
            self.intent(fault=lost_reply)
        state = self.inspect()
        self.assertEqual(state["sequence"], 1)
        self.assertIn(self.intent_spec["operation_key"], state["operations"])
        self.assertFalse(self.intent()["dispatch_granted"])
        recovered = self.library().recover(self.store)
        self.assertFalse(recovered["dispatch_granted"])
        self.assertEqual(recovered["adopted_events"], 0)

    def test_result_save_and_readback_are_separate_and_preserve_true_intent(self):
        self.create()
        granted = self.intent()
        result, saved, readback = saved_records(self.intent_spec, self.evidence)
        for spec in (result, saved):
            self.record(spec)
            state = self.inspect()["operations"][self.intent_spec["operation_key"]]
            self.assertFalse(state["reconciled"])
            self.assertNotEqual(state["outcome"], "saved")
        self.record(readback)
        state = self.inspect()["operations"][self.intent_spec["operation_key"]]
        self.assertTrue(state["reconciled"])
        self.assertEqual(state["outcome"], "saved")
        self.assertEqual(state["intent_sha256"], granted["intent_sha256"])
        self.assertNotEqual(granted["intent_sha256"], saved["references"]["ledger_sha256"])
        self.assertNotEqual(result["evidence"]["receipt"]["sha256"], saved["references"]["native_sha256"])
        exported = self.inventory()
        self.assertFalse(exported["complete"])
        operation = exported["operations"][0]
        self.assertEqual(operation["intent_sha256"], saved["references"]["ledger_sha256"])
        self.assertEqual(operation["result_sha256"], saved["references"]["native_sha256"])
        self.assertEqual(operation["event_utc"], saved["event_utc"])
        self.assertTrue(operation["reconciled"])
        self.assertEqual(operation["target_ids"], self.intent_spec["target_ids"])

    def test_missing_stages_and_wrong_bindings_never_manufacture_saved_outcome(self):
        self.create()
        self.intent()
        result, saved, readback = saved_records(self.intent_spec, self.evidence)
        for spec in (saved, readback):
            with self.subTest(stage=spec["stage"]), self.assertRaises(ContractError):
                self.record(spec)
        for index, change in enumerate((dict(intent_sha256="a" * 64), dict(session_id="other-session"),
                                         dict(operation_id="other-operation"), dict(target_ids=["other-target"]))):
            spec = copy.deepcopy(result)
            spec.update(change)
            self.update_record_proof(spec, self.evidence, "wrong-binding-" + str(index))
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.record(spec)
        self.assertEqual(self.inspect()["sequence"], 1)

    def test_unknown_and_partial_results_are_immutable_holds_without_automatic_resolution(self):
        for outcome in ("unknown", "partial"):
            with self.subTest(outcome=outcome):
                store = self.root / ("unresolved-" + outcome)
                self.create(store)
                self.intent(store=store)
                unresolved = record_spec(self.intent_spec, self.evidence, "result", outcome=outcome, tag="-" + outcome)
                self.record(unresolved, store=store)
                changed = record_spec(self.intent_spec, self.evidence, "result", tag="-" + outcome + "-replacement")
                with self.assertRaises(ContractError):
                    self.record(changed, store=store)
                inventory = self.inventory(store=store)
                self.assertFalse(inventory["complete"])
                self.assertFalse(inventory["operations"][0]["reconciled"])
                self.assertEqual(inventory["operations"][0]["outcome"], outcome)
                self.assertFalse(self.intent(store=store)["dispatch_granted"])

    def test_failed_no_effect_still_requires_matching_readback_evidence(self):
        self.create()
        self.intent()
        result = record_spec(self.intent_spec, self.evidence, "result", outcome="failed_no_effect")
        self.record(result)
        self.assertFalse(self.inspect()["operations"][self.intent_spec["operation_key"]]["reconciled"])
        readback = record_spec(self.intent_spec, self.evidence, "readback", outcome="failed_no_effect",
                               references={"result_sha256": result["evidence"]["receipt"]["sha256"]})
        self.record(readback)
        state = self.inspect()["operations"][self.intent_spec["operation_key"]]
        self.assertTrue(state["reconciled"])
        self.assertEqual(state["outcome"], "failed_no_effect")
        self.assertFalse(self.intent()["dispatch_granted"])

    def test_record_proof_and_original_receipt_hash_mismatches_preserve_head(self):
        self.create()
        first = self.intent()
        result = record_spec(self.intent_spec, self.evidence, "result")
        path = self.evidence / result["evidence"]["receipt"]["path"]
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ContractError):
            self.record(result)
        self.assertEqual(self.inspect()["head_sha256"], first["head_sha256"])
        mismatched = record_spec(self.intent_spec, self.evidence, "result", tag="-mismatched")
        mismatched["event_utc"] = "2026-10-26T10:02:01Z"
        with self.assertRaises(ContractError):
            self.record(mismatched)
        self.assertEqual(self.inspect()["head_sha256"], first["head_sha256"])

    def test_original_window_limits_intents_but_allows_receipted_closeout(self):
        self.create()
        expired = dict(self.intent_spec, event_utc="2026-10-26T11:00:00Z")
        with self.assertRaises(ContractError):
            self.intent(expired)
        granted = self.intent()
        self.assertTrue(granted["dispatch_granted"])
        result, saved, readback = saved_records(self.intent_spec, self.evidence)
        for index, spec in enumerate((result, saved, readback)):
            spec["event_utc"] = "2026-10-26T11:0%d:00Z" % (index + 1)
            self.update_record_proof(spec, self.evidence, "closeout-" + str(index))
            if spec["stage"] == "result":
                saved["references"]["result_sha256"] = spec["evidence"]["receipt"]["sha256"]
            elif spec["stage"] == "save":
                readback["references"].update(result_sha256=spec["references"]["result_sha256"],
                                               save_sha256=spec["evidence"]["receipt"]["sha256"])
            self.record(spec)
        self.assertTrue(self.inspect()["operations"][self.intent_spec["operation_key"]]["reconciled"])
        self.assertEqual(self.inspect()["config"]["window"], self.config["window"])

    def test_coverage_is_explicit_head_bound_and_does_not_imply_live_authority(self):
        self.populate_saved()
        initial = self.inventory()
        self.assertEqual(initial["schema"], "daedalus.source-operation-journal.v1")
        self.assertFalse(initial["complete"])
        self.assertFalse(initial["may_execute"])
        head = self.inspect()["head_sha256"]
        coverage = coverage_spec(self.config, head, [self.intent_spec["operation_key"]], self.evidence)
        response = self.library().cover(self.store, coverage, self.evidence)
        self.assertFalse(response["dispatch_granted"])
        covered = self.inventory()
        self.assertTrue(covered["complete"])
        self.assertEqual(covered["status"], "declared_complete")
        self.assertFalse(covered["may_execute"])
        self.assertEqual(covered["window"], self.config["window"])
        independent = copy.deepcopy(self.intent_spec)
        independent.update(operation_key="op-2", operation_id="fixture-save-2",
                           event_utc="2026-10-26T10:06:00Z", target_ids=["fixture-independent-2"],
                           output_refs=["/Game/Fixture/IndependentBoundary"],
                           inputs=[write_json(self.evidence, "input-2.json", {"fixture_only": True, "job": "fixture-save-2"})])
        self.assertTrue(self.intent(independent)["dispatch_granted"])
        later = self.inventory("2026-10-26T10:06:00Z")
        self.assertFalse(later["complete"])

    def test_coverage_cannot_claim_wrong_scope_keys_head_or_window(self):
        self.populate_saved()
        head = self.inspect()["head_sha256"]
        mutations = [lambda value: value.update(covers_head_sha256="f" * 64),
                     lambda value: value.update(operation_keys=[]),
                     lambda value: value.update(session_id="other-session"),
                     lambda value: value.update(scope_id="other-scope"),
                     lambda value: value["window"].update(deadline_utc="2026-10-26T12:00:00Z"),
                     lambda value: value.update(through_utc="2026-10-26T10:03:59Z")]
        for index, mutate in enumerate(mutations):
            value = coverage_spec(self.config, head, [self.intent_spec["operation_key"]], self.evidence,
                                  tag="-invalid-" + str(index))
            mutate(value)
            proof = {key: copy.deepcopy(item) for key, item in value.items() if key != "receipt"}
            proof["schema"] = "daedalus.operation-journal-coverage-proof.v1"
            value["receipt"] = write_json(self.evidence, "coverage-invalid-proof-" + str(index) + ".json", proof)
            with self.subTest(index=index), self.assertRaises(ContractError):
                self.library().cover(self.store, value, self.evidence)
            self.assertEqual(self.inspect()["head_sha256"], head)

    def test_tampered_events_pointer_and_reservation_remain_inspectable_holds(self):
        for part in ("event", "pointer", "reservation"):
            with self.subTest(part=part):
                store = self.root / ("tamper-" + part)
                self.create(store)
                self.intent(store=store)
                if part == "event":
                    path = next((store / "events").glob("*.json"))
                elif part == "pointer":
                    path = store / "current.json"
                else:
                    path = next((store / "reservations").glob("*.json"))
                if part == "event":
                    path.write_bytes(path.read_bytes() + b" ")
                else:
                    value = packet.read_json(path)
                    value["schema"] = "unsupported"
                    path.write_bytes(packet.canonical(value))
                state = self.inspect(store)
                self.assertEqual(state["status"], "held")
                self.assertTrue(state["issues"])
                self.assertFalse(state["dispatch_granted"])
                self.duplicate_without_grant(store)

    def test_input_tamper_missing_unsafe_and_oversized_receipts_never_grant(self):
        self.create()
        unsafe = copy.deepcopy(self.intent_spec)
        unsafe["inputs"][0]["path"] = "../input.json"
        with self.assertRaises(ContractError):
            self.intent(unsafe)
        oversized = copy.deepcopy(self.intent_spec)
        oversized["inputs"][0]["bytes"] = 512 * 1024 + 1
        with self.assertRaises(ContractError):
            self.intent(oversized)
        path = self.evidence / "input.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ContractError):
            self.intent()
        self.duplicate_without_grant(self.store)
        self.assertEqual(self.inspect()["sequence"], 0)

    def test_fresh_store_and_versioned_configuration_are_never_overwritten(self):
        created = self.create()
        self.assertFalse(created["dispatch_granted"])
        original = (self.store / "store.json").read_bytes()
        with self.assertRaises(ContractError):
            self.create()
        self.assertEqual((self.store / "store.json").read_bytes(), original)
        malformed = dict(self.config, schema="unsupported")
        with self.assertRaises(ContractError):
            self.library().create(self.root / "unsupported-store", malformed)

    def test_result_publication_loss_and_recovery_never_replays_effect(self):
        for phase in ("after_event", "after_pointer"):
            with self.subTest(phase=phase):
                store = self.root / ("result-loss-" + phase)
                self.create(store)
                self.intent(store=store)
                spec = record_spec(self.intent_spec, self.evidence, "result", tag="-" + phase)
                def stop(actual):
                    if actual == phase:
                        raise RuntimeError("result response absent at " + phase)
                with self.assertRaises(RuntimeError):
                    self.record(spec, store=store, fault=stop)
                recovered = self.library().recover(store)
                self.assertFalse(recovered["dispatch_granted"])
                self.assertEqual(recovered["adopted_events"], 1 if phase == "after_event" else 0)
                duplicate = self.record(spec, store=store)
                self.assertFalse(duplicate["recorded"])
                self.assertFalse(duplicate["dispatch_granted"])
                operation = self.inspect(store)["operations"][self.intent_spec["operation_key"]]
                self.assertEqual(operation["stages"]["result"]["receipt_sha256"], spec["evidence"]["receipt"]["sha256"])
                self.assertFalse(operation["reconciled"])
                self.duplicate_without_grant(store)

    def test_receipt_and_transaction_byte_limits_fail_without_dispatch(self):
        self.create()
        boundary = self.evidence / "boundary.bin"
        boundary.write_bytes(b"x" * (512 * 1024))
        exact = copy.deepcopy(self.intent_spec)
        exact["inputs"] = [{"path": "boundary.bin", "logical_path": "C:/Synthetic/Original/boundary.bin",
                            "sha256": packet.digest(boundary.read_bytes()), "bytes": boundary.stat().st_size}]
        self.assertTrue(self.intent(exact)["dispatch_granted"])
        store = self.root / "oversized-transaction"
        self.create(store)
        oversized = copy.deepcopy(self.intent_spec)
        oversized["inputs"] = [write_json(self.evidence, "large-%d.json" % index,
                                           {"fixture_only": True, "index": index, "blob": "x" * (400 * 1024)})
                               for index in range(3)]
        self.assertTrue(all(row["bytes"] < 512 * 1024 for row in oversized["inputs"]))
        self.assertGreater(sum(row["bytes"] for row in oversized["inputs"]), 1024 * 1024)
        with self.assertRaises(ContractError):
            self.intent(oversized, store=store)
        self.assertEqual(self.inspect(store)["sequence"], 0)
        self.duplicate_without_grant(store, oversized)

    def test_operation_event_and_store_capacity_preserve_selected_head(self):
        journal = self.library()
        self.assertEqual((journal.MAX_OPERATIONS, journal.MAX_EVENTS, journal.MAX_STORE_BYTES),
                         (128, 512, 32 * 1024 * 1024))
        for limit in ("MAX_OPERATIONS", "MAX_EVENTS", "MAX_STORE_BYTES"):
            with self.subTest(limit=limit):
                store = self.root / ("capacity-" + limit.lower())
                self.create(store)
                first = self.intent(store=store)
                selected = (store / "current.json").read_bytes()
                result = record_spec(self.intent_spec, self.evidence, "result", tag="-" + limit.lower())
                new_spec = copy.deepcopy(self.intent_spec)
                new_spec.update(operation_key="independent-key", operation_id="independent-operation",
                                target_ids=["independent-target"], output_refs=["/Game/Fixture/Independent"],
                                inputs=[write_json(self.evidence, "capacity-input-" + limit.lower() + ".json", {"job": limit})])
                cap = 1 if limit != "MAX_STORE_BYTES" else sum(path.stat().st_size for path in store.rglob("*") if path.is_file()) + 1
                with mock.patch.object(journal, limit, cap):
                    with self.assertRaises(ContractError):
                        if limit == "MAX_OPERATIONS":
                            self.intent(new_spec, store=store)
                        else:
                            self.record(result, store=store)
                self.assertEqual((store / "current.json").read_bytes(), selected)
                self.assertEqual(self.inspect(store)["head_sha256"], first["head_sha256"])
        malformed_store = self.root / "malformed-reservation-capacity"
        self.create(malformed_store)
        selected = (malformed_store / "current.json").read_bytes()
        for index in range(2):
            (malformed_store / "reservations" / ("%064x.json" % index)).write_bytes(b"")
        with mock.patch.object(journal, "MAX_OPERATIONS", 1):
            state = self.inspect(malformed_store)
        self.assertEqual(state["status"], "held")
        self.assertIn("journal_bounds", {issue["code"] for issue in state["issues"]})
        self.assertEqual((malformed_store / "current.json").read_bytes(), selected)

    def test_save_and_readback_must_reference_the_exact_earlier_witnesses(self):
        self.create()
        self.intent()
        result, saved, readback = saved_records(self.intent_spec, self.evidence)
        self.record(result)
        before_save = self.inspect()["head_sha256"]
        bad_save = copy.deepcopy(saved)
        bad_save["references"]["result_sha256"] = "a" * 64
        self.update_record_proof(bad_save, self.evidence, "wrong-save-result")
        with self.assertRaises(ContractError):
            self.record(bad_save)
        self.assertEqual(self.inspect()["head_sha256"], before_save)
        self.record(saved)
        before_readback = self.inspect()["head_sha256"]
        for name in ("result_sha256", "save_sha256", "native_sha256", "ledger_sha256"):
            with self.subTest(reference=name):
                bad_readback = copy.deepcopy(readback)
                bad_readback["references"][name] = "a" * 64
                self.update_record_proof(bad_readback, self.evidence, "wrong-readback-" + name)
                with self.assertRaises(ContractError):
                    self.record(bad_readback)
                self.assertEqual(self.inspect()["head_sha256"], before_readback)
        self.record(readback)
        self.assertTrue(self.inspect()["operations"][self.intent_spec["operation_key"]]["reconciled"])

    def test_partial_or_unknown_save_cannot_be_promoted_by_later_claim(self):
        for outcome in ("partial", "unknown"):
            with self.subTest(outcome=outcome):
                store = self.root / ("uncertain-save-" + outcome)
                self.create(store)
                self.intent(store=store)
                result = record_spec(self.intent_spec, self.evidence, "result", tag="-save-" + outcome)
                self.record(result, store=store)
                result_sha = result["evidence"]["receipt"]["sha256"]
                uncertain = record_spec(self.intent_spec, self.evidence, "save", outcome=outcome,
                                        references={"result_sha256": result_sha}, tag="-" + outcome)
                self.record(uncertain, store=store)
                promoted = record_spec(self.intent_spec, self.evidence, "save", references={"result_sha256": result_sha},
                                      tag="-" + outcome + "-promotion")
                with self.assertRaises(ContractError):
                    self.record(promoted, store=store)
                refs = dict(uncertain["references"], save_sha256=uncertain["evidence"]["receipt"]["sha256"])
                false_readback = record_spec(self.intent_spec, self.evidence, "readback", references=refs,
                                            tag="-" + outcome + "-false")
                with self.assertRaises(ContractError):
                    self.record(false_readback, store=store)
                unresolved_readback = record_spec(self.intent_spec, self.evidence, "readback", outcome="unknown",
                                                 references=refs, tag="-" + outcome + "-unknown")
                self.record(unresolved_readback, store=store)
                operation = self.inspect(store)["operations"][self.intent_spec["operation_key"]]
                self.assertFalse(operation["reconciled"])
                self.assertEqual(operation["stages"]["save"]["outcome"], outcome)
                self.assertEqual(operation["stages"]["readback"]["outcome"], "unknown")
                self.assertFalse(self.inventory(store=store)["complete"])

    def test_public_cli_writes_inspects_inventory_and_errors_without_dispatch(self):
        from . import cli
        def call(arguments, expected_exit):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli.main(arguments)
            self.assertEqual(code, expected_exit, stderr.getvalue())
            self.assertEqual(stderr.getvalue(), "")
            return json.loads(stdout.getvalue())
        config_file = self.root / "config-input.json"
        request_file = self.root / "intent-input.json"
        config_file.write_bytes(packet.canonical(self.config))
        request_file.write_bytes(packet.canonical(self.intent_spec))
        created = call(["journal-create", "--store", str(self.store), "--config", str(config_file)], 0)
        self.assertFalse(created["dispatch_granted"])
        args = ["journal-intent", "--store", str(self.store), "--request", str(request_file),
                "--evidence-root", str(self.evidence)]
        self.assertTrue(call(args, 0)["dispatch_granted"])
        self.assertFalse(call(args, 0)["dispatch_granted"])
        self.assertEqual(call(["journal-inspect", "--store", str(self.store)], 3)["status"], "held")
        inventory_args = ["journal-inventory", "--store", str(self.store), "--through-utc", "2026-10-26T10:05:00Z"]
        self.assertFalse(call(inventory_args, 3)["complete"])
        self.assertFalse(call(["journal-recover", "--store", str(self.store)], 3)["dispatch_granted"])
        for index, spec in enumerate(saved_records(self.intent_spec, self.evidence)):
            record_file = self.root / ("record-input-%d.json" % index)
            record_file.write_bytes(packet.canonical(spec))
            recorded = call(["journal-record", "--store", str(self.store), "--request", str(record_file),
                             "--evidence-root", str(self.evidence)], 0)
            self.assertTrue(recorded["recorded"])
            self.assertFalse(recorded["dispatch_granted"])
        state = call(["journal-inspect", "--store", str(self.store)], 0)
        coverage = coverage_spec(self.config, state["head_sha256"], [self.intent_spec["operation_key"]], self.evidence)
        coverage_file = self.root / "coverage-input.json"
        coverage_file.write_bytes(packet.canonical(coverage))
        self.assertFalse(call(["journal-cover", "--store", str(self.store), "--request", str(coverage_file),
                               "--evidence-root", str(self.evidence)], 0)["dispatch_granted"])
        complete = call(inventory_args, 0)
        self.assertTrue(complete["complete"])
        self.assertEqual(complete["scope"]["verification"], "caller-attestation-only")
        request_file.write_bytes(packet.canonical(dict(self.intent_spec, schema="unsupported")))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(args), 2)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["error"]["code"], "journal_version")
        self.assertFalse(error["may_execute"])

    def test_normalized_identity_aliases_and_unreserved_saved_worlds_are_rejected(self):
        for index, changes in enumerate((
                {"target_ids": ["fixture-skull-1", "FIXTURE-SKULL-1"]},
                {"output_refs": ["/Game/Fixture/SavedBoundary", "\\Game\\Fixture\\SavedBoundary"]})):
            with self.subTest(alias=changes):
                store = self.root / ("identity-alias-" + str(index))
                self.create(store)
                aliased = copy.deepcopy(self.intent_spec)
                aliased.update(changes)
                with self.assertRaises(ContractError):
                    self.intent(aliased, store=store)
                self.assertEqual(self.inspect(store)["sequence"], 0)
        for label in ("native-world-differs", "world-not-reserved", "open-sequence"):
            with self.subTest(save=label):
                store = self.root / label
                self.create(store)
                self.intent(store=store)
                result = record_spec(self.intent_spec, self.evidence, "result", tag="-" + label)
                result_answer = self.record(result, store=store)
                saved = record_spec(self.intent_spec, self.evidence, "save", tag="-" + label,
                                    references={"result_sha256": result["evidence"]["receipt"]["sha256"]})
                native_pin, ledger_pin = saved["evidence"]["native"], saved["evidence"]["ledger"]
                native = packet.read_json(self.evidence / native_pin["path"])
                ledger = packet.read_json(self.evidence / ledger_pin["path"])
                if label == "open-sequence":
                    native["native"]["open_sequence"] = "/Game/Fixture/UnresolvedSequence"
                else:
                    native["native"]["world"] = "/Game/Other/Unreserved.Unreserved"
                    if label == "world-not-reserved":
                        ledger["last_world"] = "/Game/Other/Unreserved"
                saved["evidence"]["native"] = write_json(self.evidence, native_pin["path"], native, native_pin["logical_path"])
                saved["evidence"]["ledger"] = write_json(self.evidence, ledger_pin["path"], ledger, ledger_pin["logical_path"])
                saved["references"].update(native_sha256=saved["evidence"]["native"]["sha256"],
                                             ledger_sha256=saved["evidence"]["ledger"]["sha256"])
                self.update_record_proof(saved, self.evidence, "binding-" + label)
                with self.assertRaises(ContractError):
                    self.record(saved, store=store)
                self.assertEqual(self.inspect(store)["head_sha256"], result_answer["head_sha256"])


if __name__ == "__main__":
    unittest.main()
