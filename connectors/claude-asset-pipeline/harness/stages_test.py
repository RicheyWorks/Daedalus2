# SPDX-License-Identifier: MIT
"""Offline receipt failures and real retained-process excerpts; no app calls.

The three process/progress excerpts below were read on 2026-10-16. Artifact
payloads in this portable suite are explicitly synthetic. Full actual packet
verification is a separate command documented in stage-recovery.md.
"""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import stages as s

NOW = "2026-10-16T05:00:00Z"
ACCEPTED = "2026-10-15T16:27:44Z"
FIXTURE_PROVENANCE = {
    "copperfall_failure": {
        "origin": "task-3/copperfall-ark-rest-polish-842401/before-hero-build.process.json",
        "bytes": 430, "sha256": "47287c751a4aaa2c4272db0aacb46e43b0837ba773023c6e8639502a59c28f95",
        "excerpt": {"pid": 40644, "exit_code": 1, "wall_seconds": 4.145,
                    "start_utc": "2026-10-15T16:27:44.9288309Z"}},
    "copperfall_recovery": {
        "origin": "task-3/copperfall-ark-rest-polish-842401/before-hero-resume-export-r2.process.json",
        "bytes": 460, "sha256": "b00b3ceea0e86c0ec56837f2c26ce214a657412628b49e7dd95b547c8657e3d0",
        "excerpt": {"pid": 66636, "exit_code": 0, "resume_export": True,
                    "wall_seconds": 19.008, "start_utc": "2026-10-15T16:52:53.8114298Z"}},
    "nursery_execution": {
        "origin": "task/character-upgrades/aetherflow-habitat-r1/polish-r1/after-preview-r1-job/execution.json",
        "bytes": 11822, "sha256": "29fe3f8384961bdfde3f4a9c3722020abe37b827cf8822d92ac3e67c6920bab4",
        "excerpt": {"schema": "daedalus.nursery-one-preview-execution.v1", "stage": "TERMINAL",
                    "process_id": 49760, "terminal_known": True, "exit_code": 0,
                    "release": {"status": "OURS_RELEASED_VERIFIED",
                                "observed_utc": "2026-10-15T16:49:08.5907195Z",
                                "unlock_attempted": True, "response": {"ok": True, "lock": None},
                                "after": {}}}},
    "nursery_progress": {
        "origin": "task/character-upgrades/aetherflow-habitat-r1/polish-r1/after-preview-r1/job-progress.json",
        "bytes": 5427, "sha256": "e03d72d690e9221903584ac389dee17366a33e8f7e8687ce665e8aed23cc25ab",
        "excerpt": {"schema": "daedalus.aetherflow-habitat-progress.v1",
                    "stage": "STATIC_EXPORT_SAVED_RENDERING",
                    "recorded_utc": "2026-10-15T16:49:07.967249+00:00"}},
}


class StagesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.process = self.write("process.json", {"exit_code": 0})
        self.artifact = self.write("artifact.bin", b"synthetic portable artifact")

    def write(self, name, value):
        path = self.root / name
        path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
        return s.fingerprint(path)

    def document(self, outcome="succeeded", effects="complete"):
        terminal = {"state": "terminal", "observed_at_utc": NOW,
                    "outcome": outcome, "effects": effects,
                    "process": {"exit_code": 0, "evidence": self.process},
                    "outputs": {"blend": self.artifact}}
        return {"schema": s.SCHEMA, "job_id": "portable", "observed_at_utc": NOW,
                "identities": {}, "stages": [{"stage_id": "source", "effect": "local-files",
                "requires": [], "required_outputs": ["blend"], "attempts": [{
                    "attempt_id": "attempt-1", "inputs": {}, "events": [
                        {"state": "accepted", "observed_at_utc": ACCEPTED}, terminal]}]}]}

    def terminal(self, doc):
        return doc["stages"][0]["attempts"][0]["events"][-1]

    def inspect(self, doc):
        return s.inspect(doc, self.root, NOW)

    def test_complete_requires_exit_and_output(self):
        result = self.inspect(self.document())
        self.assertTrue(result["complete"])
        self.assertFalse(result["native_qualified"])
        self.assertFalse(result["execution"])

    def test_file_existence_without_terminal_is_only_accepted(self):
        doc = self.document()
        doc["stages"][0]["attempts"][0]["events"].pop()
        self.assertEqual("accepted", self.inspect(doc)["stages"][0]["status"])

    def test_source_only_plan_missing(self):
        doc = self.document()
        doc["stages"][0]["attempts"] = []
        self.assertEqual("missing", self.inspect(doc)["stages"][0]["status"])

    def test_success_without_process_rejected(self):
        doc = self.document()
        del self.terminal(doc)["process"]
        with self.assertRaisesRegex(ValueError, "exit0"):
            self.inspect(doc)

    def test_success_missing_artifact_rejected(self):
        doc = self.document()
        self.terminal(doc)["outputs"] = {}
        with self.assertRaisesRegex(ValueError, "required"):
            self.inspect(doc)

    def test_actual_saved_before_failed_export_is_partial(self):
        process = self.write("actual-failure-excerpt.json", FIXTURE_PROVENANCE["copperfall_failure"]["excerpt"])
        doc = self.document("failed", "partial")
        self.terminal(doc)["process"] = {"exit_code": 1, "evidence": process}
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("reconciliation-required", row["status"])
        self.assertEqual(self.artifact, row["verified_outputs"]["blend"])

    def test_actual_recovery_adapter_requires_explicit_selected_outputs(self):
        process = self.write("recovery.json", FIXTURE_PROVENANCE["copperfall_recovery"]["excerpt"])
        manifest = self.write("manifest.json", {"source": self.artifact})
        doc = s.adapt_process(process["path"], manifest["path"], "recovery", "export",
                              {"blend": "source"}, NOW, attempt_id="observed-recovery")
        self.assertTrue(self.inspect(doc)["complete"])

    def test_actual_nursery_progress_does_not_override_terminal(self):
        process = self.write("nursery.json", FIXTURE_PROVENANCE["nursery_execution"]["excerpt"])
        progress = self.write("progress.json", FIXTURE_PROVENANCE["nursery_progress"]["excerpt"])
        manifest = self.write("manifest.json", {"hero": self.artifact})
        doc = s.adapt_process(process["path"], manifest["path"], "nursery", "hero",
                              {"hero": "hero"}, NOW, progress["path"], attempt_id="observed-nursery")
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("succeeded", row["status"])
        self.assertIs(True, row["compute_release"])
        self.assertIn("nonterminal progress", row["issues"][0])

    def test_release_and_progress_do_not_supply_exit(self):
        doc = self.document()
        del self.terminal(doc)["process"]
        self.terminal(doc)["compute_release"] = {"released": True, "evidence": self.write("release.json", {"released": True})}
        with self.assertRaisesRegex(ValueError, "exit0"):
            self.inspect(doc)

    def test_stale_running_never_advises_replay(self):
        doc = self.document()
        doc["stages"][0]["attempts"][0]["events"][-1] = {"state": "running", "observed_at_utc": ACCEPTED}
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("reconciliation-required", row["status"])
        self.assertEqual("running", row["observed_state"])

    def test_external_success_still_requires_operator(self):
        doc = self.document()
        doc["stages"][0]["effect"] = "external"
        self.assertEqual("reconciliation-required", self.inspect(doc)["stages"][0]["status"])

    def test_unknown_effects_cannot_claim_success(self):
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.inspect(self.document(effects="unknown"))

    def test_later_success_does_not_erase_partial_attempt(self):
        doc = self.document("unknown", "partial")
        second = copy.deepcopy(doc["stages"][0]["attempts"][0])
        second["attempt_id"] = "attempt-2"
        second["events"][0]["observed_at_utc"] = NOW
        second["events"][-1].update(outcome="succeeded", effects="complete")
        doc["stages"][0]["attempts"].append(second)
        self.assertEqual("reconciliation-required", self.inspect(doc)["stages"][0]["status"])

    def test_changed_input_pin_rejected(self):
        doc = self.document()
        pin = self.write("recipe.json", {"seed": 842401})
        doc["stages"][0]["attempts"][0]["inputs"]["recipe"] = pin
        Path(pin["path"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "changed pin"):
            self.inspect(doc)

    def test_missing_output_file_rejected(self):
        Path(self.artifact["path"]).unlink()
        with self.assertRaises(OSError):
            self.inspect(self.document())

    def test_process_field_must_match_retained_bytes(self):
        doc = self.document()
        self.terminal(doc)["process"]["exit_code"] = 1
        with self.assertRaisesRegex(ValueError, "contradictory"):
            self.inspect(doc)

    def test_failure_without_nonzero_exit_is_not_proven(self):
        with self.assertRaisesRegex(ValueError, "nonzero"):
            self.inspect(self.document("failed"))

    def test_missing_stage_advice_pins_completed_upstream(self):
        doc = self.document()
        doc["stages"].append({"stage_id": "render", "effect": "local-files", "requires": ["source"],
                              "required_outputs": ["hero"], "attempts": []})
        result = self.inspect(doc)
        self.assertFalse(result["complete"])
        self.assertEqual([], result["stages"][1]["blocked_by"])
        self.assertEqual(self.artifact, result["stages"][0]["verified_outputs"]["blend"])

    def test_missing_used_material_is_error(self):
        doc = self.document()
        usage = {"used": ["terrain"], "retained": [], "validated_unused": []}
        self.terminal(doc)["materials"] = dict(usage, evidence=self.write("usage.json", usage))
        with self.assertRaisesRegex(ValueError, "USED"):
            self.inspect(doc)

    def test_unused_orphan_requires_explicit_pinned_usage_proof(self):
        doc = self.document()
        usage = {"used": ["terrain"], "retained": ["terrain"], "validated_unused": ["CAR_lamp"]}
        self.terminal(doc)["materials"] = dict(usage, evidence=self.write("usage.json", usage))
        self.assertTrue(self.inspect(doc)["complete"])

    def test_material_cannot_be_both_used_and_orphan(self):
        doc = self.document()
        usage = {"used": ["terrain"], "retained": ["terrain"], "validated_unused": ["terrain"]}
        self.terminal(doc)["materials"] = dict(usage, evidence=self.write("usage.json", usage))
        with self.assertRaisesRegex(ValueError, "marked unused"):
            self.inspect(doc)

    def test_identity_fields_never_alias(self):
        doc = self.document()
        doc["identities"] = {"realmAuthoringKey": {"type": "string", "value": "WORLD-ZERO"},
                             "runtimeWorldId": {"type": "integer", "value": 7},
                             "catalogueId": {"type": "string", "value": "land-catalogue"}}
        self.assertEqual(doc["identities"], self.inspect(doc)["identities"])

    def test_boolean_is_not_integer_identity(self):
        doc = self.document()
        doc["identities"]["runtimeWorldId"] = {"type": "integer", "value": True}
        with self.assertRaisesRegex(ValueError, "signed64"):
            self.inspect(doc)

    def test_malformed_and_duplicate_json_rejected(self):
        for content in (b'{"job_id":', b'{"x":1,"x":2}', b'{"x":NaN}'):
            pin = self.write("bad.json", content)
            with self.assertRaises(ValueError):
                s.read_json(pin["path"])

    def test_lifecycle_and_utc_order_rejected(self):
        doc = self.document()
        doc["stages"][0]["attempts"][0]["events"].reverse()
        with self.assertRaisesRegex(ValueError, "lifecycle"):
            self.inspect(doc)
        doc = self.document()
        doc["observed_at_utc"] = "2026-10-16T05:00:00"
        with self.assertRaisesRegex(ValueError, "UTC"):
            self.inspect(doc)

    def test_publish_is_exclusive_and_read_back(self):
        path = self.root / "receipt.json"
        doc = self.document()
        pin = s.publish(doc, path, self.root, NOW)
        self.assertEqual(doc, s.read_json(path))
        with self.assertRaises(FileExistsError):
            s.publish(doc, path, self.root, NOW)
        self.assertEqual(pin, s.fingerprint(path))

    def test_prepublication_failure_leaves_no_public_receipt(self):
        path = self.root / "receipt.json"
        with patch.object(s.os, "fsync", side_effect=OSError("injected flush failure")):
            with self.assertRaises(OSError):
                s.publish(self.document(), path, self.root, NOW)
        self.assertFalse(path.exists())
        self.assertFalse(list(self.root.glob(".stage-*")))

    def test_postpublication_failure_retains_uncertain_receipt(self):
        path = self.root / "receipt.json"
        original_read = s.read_json
        def fail_destination_readback(source):
            if Path(source) == path:
                raise OSError("injected destination readback failure")
            return original_read(source)
        with patch.object(s, "read_json", side_effect=fail_destination_readback):
            with self.assertRaises(OSError):
                s.publish(self.document(), path, self.root, NOW)
        self.assertTrue(path.is_file())

    def test_prior_event_rewrite_rejected(self):
        doc = self.document()
        old = copy.deepcopy(doc)
        doc["previous"] = self.write("previous.json", old)
        doc["stages"][0]["attempts"][0]["events"][0]["observed_at_utc"] = "2026-10-15T16:27:43Z"
        with self.assertRaisesRegex(ValueError, "prior events"):
            self.inspect(doc)

    def test_append_missing_stage_preserves_history(self):
        doc = self.document()
        old = copy.deepcopy(doc)
        doc["previous"] = self.write("previous.json", old)
        doc["stages"].append({"stage_id": "hero", "requires": ["source"], "effect": "local-files",
                              "required_outputs": ["hero"], "attempts": []})
        self.assertFalse(self.inspect(doc)["complete"])

    def test_pin_and_document_work_caps(self):
        with patch.object(s, "MAX_PINS", 1):
            with self.assertRaisesRegex(ValueError, "budget"):
                self.inspect(self.document())
        doc = self.document()
        doc["provenance"] = "x" * (s.MAX_JSON + 1)
        with self.assertRaisesRegex(ValueError, "1 MiB"):
            self.inspect(doc)

    def test_cli_invalid_and_incomplete_have_nonzero_outcome(self):
        invalid = self.root / "invalid.json"
        invalid.write_text("{")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(3, s.main(["verify", str(invalid)]))
            doc = self.document()
            doc["stages"][0]["attempts"] = []
            pin = self.write("missing.json", doc)
            self.assertEqual(2, s.main(["verify", pin["path"], "--now", NOW]))

    def append_attempt(self, doc, terminal=None):
        events = [{"state": "accepted", "observed_at_utc": NOW}]
        if terminal:
            events.append(terminal)
        doc["stages"][0]["attempts"].append({"attempt_id": "attempt-2", "inputs": {}, "events": events})

    def old_release_and_progress(self, doc):
        self.terminal(doc)["compute_release"] = {"released": True, "evidence": self.write("release.json", {"released": True})}
        self.terminal(doc)["progress"] = {"state": "rendering", "evidence": self.write("progress.json", {"state": "rendering"})}

    def test_completed_then_accepted_does_not_inherit_old_fields(self):
        doc = self.document()
        self.old_release_and_progress(doc)
        self.append_attempt(doc)
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("accepted", row["status"])
        self.assertEqual({}, row["verified_outputs"])
        self.assertEqual([], row["issues"])
        for key in ("process", "compute_release", "progress"):
            self.assertNotIn(key, row)
        self.assertIs(True, row["previous_attempts"][0]["compute_release"])

    def test_completed_then_running_has_only_current_attempt_observation(self):
        doc = self.document()
        self.old_release_and_progress(doc)
        self.append_attempt(doc)
        doc["stages"][0]["attempts"][-1]["events"].append({"state": "running", "observed_at_utc": NOW})
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("attempt-2", row["attempt_id"])
        self.assertEqual("running", row["observed_state"])
        self.assertEqual({}, row["verified_outputs"])
        self.assertNotIn("compute_release", row)
        self.assertNotIn("process", row)

    def test_later_terminal_without_release_does_not_inherit_release(self):
        doc = self.document()
        later = copy.deepcopy(self.terminal(doc))
        self.old_release_and_progress(doc)
        self.append_attempt(doc, later)
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("succeeded", row["status"])
        self.assertNotIn("compute_release", row)
        self.assertNotIn("progress", row)
        self.assertEqual([], row["issues"])

    def test_noeffects_failed_then_new_accepted_does_not_inherit_process(self):
        doc = self.document("failed", "none")
        self.terminal(doc)["process"] = {"exit_code": 1, "evidence": self.write("failure.json", {"exit_code": 1})}
        self.append_attempt(doc)
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("accepted", row["status"])
        self.assertNotIn("process", row)
        self.assertEqual(1, row["previous_attempts"][0]["process"])

    def test_noeffects_failed_then_new_success_has_current_evidence_only(self):
        doc = self.document("failed", "none")
        self.terminal(doc)["process"] = {"exit_code": 1, "evidence": self.write("failure.json", {"exit_code": 1})}
        later = copy.deepcopy(self.terminal(self.document()))
        self.append_attempt(doc, later)
        result = self.inspect(doc)
        self.assertTrue(result["complete"])
        self.assertEqual(0, result["stages"][0]["process"])
        self.assertEqual("failed", result["stages"][0]["previous_attempts"][0]["status"])

    def invalid_adapter_cli(self, manifest, selection, progress=None):
        args = ["adapt-process", "--process", self.process["path"], "--manifest", manifest,
                "--job-id", "invalid-input", "--stage-id", "export", "--attempt-id", "read-1",
                "--observed-at-utc", NOW, "--output-field", "hero="+selection]
        if progress:
            args += ["--progress", progress]
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = s.main(args)
        self.assertEqual(3, result)
        self.assertEqual("", stdout.getvalue())
        self.assertFalse(json.loads(stderr.getvalue())["execution"])
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_array_progress_is_bounded_json_error(self):
        manifest = self.write("manifest.json", {"source": self.artifact})
        progress = self.write("progress-array.json", [])
        self.invalid_adapter_cli(manifest["path"], "source", progress["path"])

    def test_cli_out_of_range_selector_is_bounded_json_error(self):
        manifest = self.write("manifest.json", {"views": []})
        self.invalid_adapter_cli(manifest["path"], "views.2")

    def test_cli_scalar_selector_is_bounded_json_error(self):
        manifest = self.write("manifest.json", {"views": 7})
        self.invalid_adapter_cli(manifest["path"], "views.hero")

    def test_adapter_requires_caller_explicit_attempt_identity(self):
        manifest = self.write("manifest.json", {"source": self.artifact})
        with self.assertRaisesRegex(ValueError, "identity"):
            s.adapt_process(self.process["path"], manifest["path"], "job", "stage", {"blend": "source"}, NOW)


if __name__ == "__main__":
    unittest.main()
