# SPDX-License-Identifier: MIT
"""Rolling composite selection tests using existing synthetic source receipts."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from . import packet, source_snapshot
from .contracts import ContractError
from .test_source_snapshot import fixture, write_json


def source_boundary(root, advance=0, earlier_operations=None, *, known_provenance=True):
    """Advance a coherent exported fixture without rewriting any earlier export."""
    root = Path(root)
    request = fixture(root)
    if known_provenance:
        source = {"schema": "daedalus.build-inputs.v1", "commit": "1" * 40,
                  "files": [{"path": "Source/Fixture.py", "category": "source", "bytes": 16,
                             "sha256": packet.digest(b"synthetic input\n")}]}
        source_pin = write_json(root / "source.json", source)
        build = {"schema": "daedalus.build-provenance.v1", "recorded_at_build_time": True,
                 "source_commit": source["commit"], "inputs_before_sha256": source_pin["sha256"],
                 "inputs_after_sha256": source_pin["sha256"], "artifact_sha256": request["runtime"]["artifact_sha256"],
                 "toolchain": {"engine": "synthetic-engine", "compiler": "synthetic-compiler"},
                 "command": ["synthetic-build", "fixture"], "exit_code": 0}
        build_pin = write_json(root / "build.json", build)
        for role, pin in (("source", source_pin), ("build", build_pin)):
            request["inputs"][role] = dict(pin, status="present", path=role + ".json",
                                               logical_path="C:/Synthetic/Original/" + role + ".json", reason=None)
        request["source_state"]["dirty"] = False
    if advance == 0:
        return request
    documents = {role: packet.read_json(root / row["path"])
                 for role, row in request["inputs"].items() if row["status"] == "present"}
    count = 20 + advance
    counts = {"skull": count, "toter": count}
    for state in (documents["ledger"], documents["terminal"]["status"],
                  documents["monitor"], documents["monitor"]["active"]):
        state.update(saved_counts=copy.deepcopy(counts), source_counts=copy.deepcopy(counts), next_index=count + 1)
    targets = ["fixture-skull-%d" % count, "fixture-toter-%d" % count]
    documents["native"]["native"]["item_records"] = {target: {} for target in targets}
    documents["catalog"]["ids"] = targets
    documents["terminal"]["utc"] = "2026-10-26T10:%02d:00Z" % (2 + advance * 2)
    documents["monitor"]["utc"] = "2026-10-26T10:%02d:30Z" % (2 + advance * 2)
    request["captured_utc"] = "2026-10-26T10:%02d:00Z" % (3 + advance * 2)
    for role, value in documents.items():
        request["inputs"][role].update(write_json(root / request["inputs"][role]["path"], value))
    prior = copy.deepcopy(earlier_operations if earlier_operations is not None else documents["journal"]["operations"])
    prior.append({"id": "fixture-save-%d" % (advance + 1),
                  "intent_sha256": request["inputs"]["ledger"]["sha256"], "target_ids": targets,
                  "outcome": "saved", "result_sha256": request["inputs"]["native"]["sha256"],
                  "reconciled": True, "event_utc": "2026-10-26T10:%02d:59Z" % (1 + advance * 2)})
    documents["journal"].update(operations=prior, through_utc=request["captured_utc"])
    request["inputs"]["journal"].update(write_json(root / "journal.json", documents["journal"]))
    return request


class CheckpointStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="daedalus-rolling-checkpoint-",
                                                 dir=os.environ.get("DAEDALUS_TEST_TMPDIR"))
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.sources, self.requests = [], []
        earlier = None
        for advance in range(3):
            source = self.root / ("source-%d" % advance)
            request = source_boundary(source, advance, earlier)
            earlier = packet.read_json(source / "journal.json")["operations"]
            self.sources.append(source)
            self.requests.append(request)
        self.store = self.root / "store"

    @staticmethod
    def library():
        from . import checkpoint_store
        return checkpoint_store

    def publish(self, advance=0, *, expected=None, store=None, request=None, source=None, fault=None):
        return self.library().publish(store or self.store, request or self.requests[advance],
                                      source or self.sources[advance], expected_current=expected, fault=fault)

    def read(self, selection="current", *, store=None, expected=None):
        return self.library().read(store or self.store, selection=selection, expected_sha256=expected)

    @staticmethod
    def files(root):
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    @staticmethod
    def edit(source, request, role, mutate):
        path = source / request["inputs"][role]["path"]
        value = packet.read_json(path)
        mutate(value)
        request["inputs"][role].update(write_json(path, value))

    def test_two_boundaries_select_complete_composites_without_rewriting_inner_history(self):
        originals = [self.files(source) for source in self.sources]
        with mock.patch("socket.create_connection", side_effect=AssertionError("outgoing unavailable")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("no process dispatch")):
            first = self.publish()
            retained = self.files(self.store / first["capture"])
            second = self.publish(1, expected=first["sha256"])
            current = self.read(expected=second["sha256"])
            previous = self.read("previous", expected=first["sha256"])
        self.assertEqual((first["status"], second["status"]), ("complete", "complete"))
        self.assertTrue(first["published"])
        self.assertTrue(second["published"])
        self.assertFalse(current["may_execute"])
        self.assertEqual((first["sequence"], second["sequence"]), (1, 2))
        self.assertIsNone(first["prior_sha256"])
        self.assertEqual(second["prior_sha256"], first["sha256"])
        self.assertEqual((current["sha256"], previous["sha256"]), (second["sha256"], first["sha256"]))
        self.assertEqual((current["current_sha256"], current["previous_sha256"]), (second["sha256"], first["sha256"]))
        self.assertEqual(current["checkpoint"]["progress"]["next_index"], 22)
        self.assertEqual(previous["checkpoint"]["progress"]["next_index"], 21)
        for result, stamp in ((previous, "2026-10-26T10:01:59Z"), (current, "2026-10-26T10:03:59Z")):
            self.assertEqual(result["checkpoint"]["sequence"], 1)
            self.assertIsNone(result["checkpoint"]["prior_sha256"])
            self.assertEqual(result["checkpoint"]["saved_utc"], stamp)
            self.assertEqual(result["snapshot"]["source_event_utc"], stamp)
            self.assertEqual(result["snapshot"]["admission_status"], "held")
            self.assertEqual(result["snapshot"]["liveness"], "not_observed")
            self.assertEqual(result["checkpoint"]["source"]["status"], "recorded")
            self.assertEqual(result["checkpoint"]["build"]["status"], "bound")
            capture = self.store / result["capture"]
            original_snapshot = source_snapshot.read_snapshot(capture, expected_sha256=result["snapshot"]["receipt_sha256"])
            self.assertEqual(original_snapshot, result["snapshot"])
            self.assertEqual(packet.read_packet(capture / "packet")["checkpoint"], result["checkpoint"])
            self.assertEqual(packet.digest((self.store / "entries" / (result["sha256"] + ".json")).read_bytes()), result["sha256"])
        self.assertEqual(self.files(self.store / first["capture"]), retained)
        self.assertEqual([self.files(source) for source in self.sources], originals)

    def test_stale_expected_current_refuses_before_any_capture(self):
        first = self.publish()
        before = self.files(self.store)
        for expected in (None, "f" * 64):
            with self.subTest(expected=expected), self.assertRaises(ContractError) as caught:
                self.publish(1, expected=expected)
            self.assertEqual(caught.exception.code, "current_changed")
            self.assertEqual(self.files(self.store), before)
        self.assertEqual(self.read()["sha256"], first["sha256"])

    def test_changed_continuity_and_regressing_progress_hold_without_advancing_index(self):
        first = self.publish()
        pointer = (self.store / "current.json").read_bytes()
        cases = ("campaign", "host", "runtime", "window", "source", "build", "counts", "next-index", "kinds", "saved-time", "captured-time")
        for label in cases:
            with self.subTest(change=label):
                source = self.root / ("changed-" + label)
                request = source_boundary(source, 0 if label in ("saved-time", "captured-time") else 1,
                                          packet.read_json(self.sources[0] / "journal.json")["operations"])
                if label == "campaign":
                    request["campaign"] = "different-campaign"
                elif label == "host":
                    request["identity"]["host"] = "different-host"
                elif label == "runtime":
                    request["runtime"]["version"] = "different-runtime"
                elif label == "window":
                    self.edit(source, request, "session", lambda value: value.update(deadline_utc="2026-10-26T11:30:01Z"))
                elif label == "source":
                    self.edit(source, request, "source", lambda value: value["files"][0].update(sha256="a" * 64))
                    self.edit(source, request, "build", lambda value: value.update(
                        inputs_before_sha256=request["inputs"]["source"]["sha256"],
                        inputs_after_sha256=request["inputs"]["source"]["sha256"]))
                elif label == "build":
                    self.edit(source, request, "build", lambda value: value["toolchain"].update(compiler="different-synthetic-compiler"))
                elif label in ("counts", "next-index", "kinds"):
                    count = {"skull": 19, "toter": 19} if label == "counts" else {"skull": 21, "toter": 21}
                    if label == "kinds":
                        count["bonus"] = 0
                    next_index = 20 if label in ("counts", "next-index") else 22
                    for role in ("ledger", "terminal", "monitor"):
                        def update(value, role=role):
                            states = ([value, value["active"]] if role == "monitor" else
                                      [value["status"]] if role == "terminal" else [value])
                            for state in states:
                                state.update(saved_counts=copy.deepcopy(count), source_counts=copy.deepcopy(count), next_index=next_index)
                        self.edit(source, request, role, update)
                    self.edit(source, request, "journal", lambda value: value["operations"][-1].update(intent_sha256=request["inputs"]["ledger"]["sha256"]))
                elif label == "saved-time":
                    self.edit(source, request, "journal", lambda value: value["operations"][0].update(event_utc="2026-10-26T10:01:58Z"))
                elif label == "captured-time":
                    request["captured_utc"] = "2026-10-26T10:02:45Z"
                    self.edit(source, request, "journal", lambda value: value.update(through_utc=request["captured_utc"]))
                result = self.publish(expected=first["sha256"], request=request, source=source)
                self.assertEqual(result["status"], "held")
                self.assertFalse(result["published"])
                self.assertIsNone(result["sha256"])
                self.assertEqual(result["snapshot"]["status"], "sealed")
                code = ("window_chain" if label == "window" else
                        "progress_regression" if label in ("counts", "next-index") else
                        "checkpoint_time_regression" if label in ("saved-time", "captured-time") else
                        "checkpoint_continuity")
                self.assertIn(code, {reason["code"] for reason in result["reasons"]})
                self.assertEqual((self.store / "current.json").read_bytes(), pointer)
                self.assertEqual(self.read()["sha256"], first["sha256"])
                self.assertTrue((self.store / result["capture"]).is_dir())

    def test_unsealed_or_inflight_source_is_retained_but_never_advertised(self):
        first = self.publish()
        before = (self.store / "current.json").read_bytes()
        for label in ("journal-incomplete", "pending-effect"):
            with self.subTest(source=label):
                source = self.root / label
                request = source_boundary(source)
                if label == "journal-incomplete":
                    self.edit(source, request, "journal", lambda value: value.update(complete=False))
                else:
                    self.edit(source, request, "monitor", lambda value: value["active"].update(pending={"id": "unresolved-effect"}))
                result = self.publish(expected=first["sha256"], request=request, source=source)
                self.assertEqual(result["status"], "held")
                self.assertFalse(result["published"])
                self.assertIsNone(result["sha256"])
                self.assertEqual(result["snapshot"]["status"], "held")
                self.assertTrue((self.store / result["capture"] / "source-snapshot" / "result.json").is_file())
                self.assertEqual((self.store / "current.json").read_bytes(), before)
                self.assertEqual(self.read()["sha256"], first["sha256"])

    def test_corrupt_current_composite_does_not_prevent_explicit_previous_selection(self):
        first = self.publish()
        second = self.publish(1, expected=first["sha256"])
        previous_bytes = self.files(self.store / first["capture"])
        owner_copy = self.store / second["capture"] / "source-snapshot" / "copies" / "owner.json"
        owner_copy.write_bytes(owner_copy.read_bytes() + b" ")
        with self.assertRaises((ContractError, OSError)):
            self.read()
        previous = self.read("previous", expected=first["sha256"])
        self.assertEqual(previous["sha256"], first["sha256"])
        self.assertEqual(previous["checkpoint"], first["checkpoint"])
        self.assertEqual(self.files(self.store / first["capture"]), previous_bytes)

    def test_interruption_before_pointer_retains_current_previous_and_unadvertised_capture(self):
        for phase in ("capture:after_copy", "capture:after_seal", "after_capture", "after_entry", "before_pointer_replace"):
            with self.subTest(phase=phase):
                store = self.root / ("interrupted-" + phase.replace(":", "-"))
                first = self.publish(store=store)
                second = self.publish(1, expected=first["sha256"], store=store)
                pointer = (store / "current.json").read_bytes()
                retained = {path.name: path.read_bytes() for path in (store / "entries").glob("*.json")}
                captures = set((store / "captures").iterdir())
                def stop(actual):
                    if actual == phase:
                        raise RuntimeError("publisher absent at " + phase)
                with self.assertRaises(RuntimeError):
                    self.publish(2, expected=second["sha256"], store=store, fault=stop)
                self.assertEqual((store / "current.json").read_bytes(), pointer)
                self.assertEqual(self.read(store=store)["sha256"], second["sha256"])
                self.assertEqual(self.read("previous", store=store)["sha256"], first["sha256"])
                self.assertGreater(len(set((store / "captures").iterdir()) - captures), 0)
                for name, raw in retained.items():
                    self.assertEqual((store / "entries" / name).read_bytes(), raw)
                if phase in ("after_entry", "before_pointer_replace"):
                    self.assertGreater(len(list((store / "entries").glob("*.json"))), len(retained))

    def test_lost_reply_after_pointer_is_uncertain_and_new_current_can_be_read(self):
        first = self.publish()
        def lost_reply(phase):
            if phase == "after_pointer_replace":
                raise RuntimeError("reply absent after publication")
        with self.assertRaises(ContractError) as caught:
            self.publish(1, expected=first["sha256"], fault=lost_reply)
        self.assertEqual(caught.exception.code, "checkpoint_publication_uncertain")
        current = self.read()
        self.assertEqual(current["sequence"], 2)
        self.assertEqual(current["checkpoint"]["progress"]["next_index"], 22)
        self.assertEqual(self.read("previous")["sha256"], first["sha256"])
        before = self.files(self.store)
        with self.assertRaises(ContractError) as caught:
            self.publish(1, expected=first["sha256"])
        self.assertEqual(caught.exception.code, "current_changed")
        self.assertEqual(self.files(self.store), before)

    def test_initial_unknown_provenance_is_preserved_but_cannot_admit_continuation(self):
        first_source = self.root / "unknown-source"
        first_request = source_boundary(first_source, known_provenance=False)
        store = self.root / "unknown-store"
        first = self.publish(request=first_request, source=first_source, store=store)
        self.assertEqual(first["status"], "complete")
        self.assertFalse(first["may_execute"])
        self.assertEqual(first["snapshot"]["admission_status"], "held")
        self.assertEqual(first["checkpoint"]["source"]["status"], "unknown")
        self.assertEqual(first["checkpoint"]["build"]["status"], "unknown")
        self.assertIn("SOURCE_PROVENANCE_UNKNOWN", {reason["code"] for reason in first["snapshot"]["reasons"]})
        pointer = (store / "current.json").read_bytes()
        earlier = packet.read_json(first_source / "journal.json")["operations"]
        for known in (False, True):
            with self.subTest(later_provenance_known=known):
                source = self.root / ("unknown-later-" + str(known))
                request = source_boundary(source, 1, earlier, known_provenance=known)
                result = self.publish(expected=first["sha256"], request=request, source=source, store=store)
                self.assertEqual(result["status"], "held")
                self.assertFalse(result["published"])
                self.assertIn("checkpoint_provenance_unknown", {reason["code"] for reason in result["reasons"]})
                self.assertEqual((store / "current.json").read_bytes(), pointer)
                self.assertEqual(self.read(store=store)["sha256"], first["sha256"])

    def test_prior_journal_operations_and_cutoff_cannot_be_removed_or_rewritten(self):
        first = self.publish()
        before = (self.store / "current.json").read_bytes()
        earlier = packet.read_json(self.sources[0] / "journal.json")["operations"]
        for label in ("omitted-operation", "changed-time", "changed-id", "cutoff-regression"):
            with self.subTest(journal=label):
                source = self.root / label
                request = source_boundary(source, 0 if label == "cutoff-regression" else 1, earlier)
                if label == "omitted-operation":
                    self.edit(source, request, "journal", lambda value: value.update(operations=value["operations"][1:]))
                elif label == "changed-time":
                    self.edit(source, request, "journal", lambda value: value["operations"][0].update(event_utc="2026-10-26T10:01:58Z"))
                elif label == "changed-id":
                    self.edit(source, request, "journal", lambda value: value["operations"][0].update(id="changed-prior-operation"))
                else:
                    request["captured_utc"] = "2026-10-26T10:03:30Z"
                    self.edit(source, request, "journal", lambda value: value.update(through_utc="2026-10-26T10:02:59Z"))
                result = self.publish(expected=first["sha256"], request=request, source=source)
                self.assertEqual(result["status"], "held")
                self.assertFalse(result["published"])
                self.assertIn("checkpoint_journal_continuity", {reason["code"] for reason in result["reasons"]})
                self.assertEqual((self.store / "current.json").read_bytes(), before)
                self.assertEqual(self.read()["sha256"], first["sha256"])

    def test_cli_publish_and_explicit_selection_have_structured_safe_outcomes(self):
        from . import cli
        request_file = self.root / "request-input.json"
        request_file.write_bytes(packet.canonical(self.requests[0]))
        def call(arguments, expected_exit):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli.main(arguments)
            self.assertEqual(code, expected_exit, stderr.getvalue())
            self.assertEqual(stderr.getvalue(), "")
            return json.loads(stdout.getvalue())
        publish_args = ["checkpoint-publish", "--store", str(self.store), "--request", str(request_file),
                        "--source-root", str(self.sources[0]), "--expected-current", "none"]
        published = call(publish_args, 0)
        self.assertTrue(published["published"])
        self.assertFalse(published["may_execute"])
        inspected = call(["checkpoint-inspect", "--store", str(self.store), "--expected-digest", published["sha256"]], 0)
        self.assertEqual(inspected["sha256"], published["sha256"])
        source = self.root / "cli-pending"
        request = source_boundary(source)
        self.edit(source, request, "journal", lambda value: value.update(complete=False))
        request_file.write_bytes(packet.canonical(request))
        held = call(["checkpoint-publish", "--store", str(self.store), "--request", str(request_file),
                     "--source-root", str(source), "--expected-current", published["sha256"]], 3)
        self.assertFalse(held["published"])
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(publish_args), 2)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["error"]["code"], "current_changed")
        self.assertFalse(error["may_execute"])


if __name__ == "__main__":
    unittest.main()
