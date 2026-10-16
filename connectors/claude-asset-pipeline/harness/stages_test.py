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


GUI_NOW = "2026-10-16T06:20:00Z"
GUI_PROVENANCE = {
    "r2_terminal": ("task-3/copperfall-ark-rest-polish-842401/after-r2/existing-session-attempt-32797/0010.json",
                    6221, "85f0adb84eb409d396ac0326c58a4a585a5299ae26bd28fcca1429fe2f4f1233"),
    "r1_terminal": ("task-3/copperfall-ark-rest-polish-842401/after-r1/existing-session-attempt-32783/0005.json",
                    2751, "c2f675e6b180b9f551d2cbeab9f1f8fdc26ce86ae518c0ebdb1d0984c1bc5e33"),
    "baseline": ("task-3/copperfall-ark-rest-polish-842401/after-r2/reconciled-session-baseline.json",
                 628, "dd2a246823ccd29db3c7f4fd8b6fb7643183f4e2665f8c36d8a89991f5d62526"),
    "r2_release": ("task-3/open-session-20261016/grant32797-release.json",
                   1387, "16a0bc1b75f36d40484792adc075e56ecd6f6e806bd15162fa0199fbb3d3f580"),
    "r1_release": ("task-3/open-session-20261016/grant32783-release.json",
                   1406, "ed6a23783c8e1ada7401104d4507921a7fcf306095abf36ce3190a74960b4e37"),
}


class GuiStagesTest(unittest.TestCase):
    """Real retained R2/R1 scalar structure; all portable payload bytes synthetic."""
    setUp = StagesTest.setUp
    write = StagesTest.write
    terminal = StagesTest.terminal

    def fixture(self):
        hashes = {"Copperfall_Ark_Rest_842401_polish_r1": "6e3e18e5ca5314b0fcb0b2e4435ec74542c34d23bfb14cf9b682012bb16e2bf0",
                  "Scene": "45605c9a7e2d2eb4d36ef2fa6a9fbf4a008ecc75232972751425a72cb51e3302"}
        proof = {"schema": s.GUI_SCHEMA, "operation_id": "copperfall-after-r2-32797",
                 "accepted_allocation_hub": 32797, "state": s.GUI_SUCCEEDED,
                 "started_at_utc": "2026-10-16T05:50:29.038158+00:00",
                 "finished_at_utc": "2026-10-16T05:50:49.127201+00:00",
                 "process_exit_code": None, "process_launched": False, "existing_blender_pid": 12580,
                 "startup_copy_result": ["FINISHED"], "source_copy_result": ["FINISHED"],
                 "render_operator_result": ["FINISHED"], "startup_backup": self.artifact,
                 "original_context": {"scene": "Scene", "view_layer": "ViewLayer", "active_object": "Cube",
                                      "selected": ["Cube"], "mode": "OBJECT", "filepath": ""},
                 "retained_scene_hashes": hashes, "startup_objects_preserved": True,
                 "original_context_restored": True, "retained_scenes_preserved": True,
                 "scene": "Copperfall_Ark_Rest_842401_polish_r2"}
        for key in ("source", "glb", "fbx", "hero"):
            proof[key] = self.write(key + ".bin", ("synthetic " + key).encode())
        baseline = {"read_only": True, "run_called": False, "pid": 12580,
                    "scene_hashes": copy.deepcopy(hashes), "original_scene": "Scene", "mode": "OBJECT",
                    "active": "Cube", "selected": ["Cube"], "filepath": "",
                    "observed_at_utc": "2026-10-16T05:46:15.059455+00:00"}
        release = {"grant": 32797, "observed_at_utc": "2026-10-16T05:51:37.3570228Z",
                   "before": {"compute": {"holder": "pootscoot"}}, "unlock": {"ok": True, "lock": None},
                   "after": {"unreal": {"holder": "codex-play-guard"}}}
        return proof, baseline, release

    def adapt(self, proof, baseline, release):
        terminal = self.write("gui.json", proof)
        before = self.write("baseline.json", baseline) if baseline is not None else None
        after = self.write("released.json", release) if release is not None else None
        return s.adapt_gui(terminal["path"], "gui-retained", "source-export-hero", proof["operation_id"],
                           {"blend": "source", "glb": "glb", "fbx": "fbx", "hero": "hero"}, GUI_NOW,
                           before["path"] if before else None, after["path"] if after else None,
                           "pootscoot" if after else None)

    def inspect(self, doc):
        return s.inspect(doc, self.root, GUI_NOW)

    def assert_reconcile(self, proof, baseline, release):
        result = self.inspect(self.adapt(proof, baseline, release))
        self.assertFalse(result["complete"])
        self.assertEqual("reconciliation-required", result["stages"][0]["status"])
        self.assertEqual("operator-reconciliation-only-no-replay", result["stages"][0]["advice"])
        return result["stages"][0]

    def test_real_r2_structure_completes_with_null_process_exit(self):
        doc = self.adapt(*self.fixture())
        result = self.inspect(doc)
        self.assertTrue(result["complete"])
        self.assertFalse(result["native_qualified"])
        self.assertFalse(result["execution"])
        row = result["stages"][0]
        self.assertNotIn("process", row)
        self.assertIsNone(row["gui_operation"]["process_exit_code"])
        self.assertTrue(row["gui_operation"]["operation_completed"])
        self.assertTrue(row["gui_operation"]["restoration_verified"])
        self.assertIs(True, row["compute_release"])
        self.assertEqual(4, len(row["verified_outputs"]))

    def test_real_r1_failed_structure_preserves_partial_scene_and_no_replay(self):
        proof, _, release = self.fixture()
        proof.update(operation_id="copperfall-after-r1-32783", accepted_allocation_hub=32783,
                     state="TERMINAL_FAILED_PARTIAL_OUTPUTS_RECONCILE",
                     started_at_utc="2026-10-16T05:37:03.816250+00:00",
                     finished_at_utc="2026-10-16T05:37:04.063618+00:00",
                     scene="Copperfall_Ark_Rest_842401_polish_r1")
        for key in ("source", "glb", "fbx", "hero", "source_copy_result", "render_operator_result",
                    "retained_scenes_preserved", "retained_scene_hashes"):
            del proof[key]
        release.update(grant=32783, observed_at_utc="2026-10-16T05:38:27.3547761Z")
        row = self.assert_reconcile(proof, None, release)
        self.assertTrue(row["gui_operation"]["operation_terminal"])
        self.assertFalse(row["gui_operation"]["operation_completed"])
        self.assertEqual(proof["scene"], row["gui_operation"]["retained_partial_scene"])
        self.assertEqual({}, row["verified_outputs"])
        self.assertIs(True, row["compute_release"])

    def test_each_missing_or_false_finished_and_restoration_witness_is_incomplete(self):
        for key in ("startup_copy_result", "source_copy_result", "render_operator_result",
                    "startup_objects_preserved", "original_context_restored", "retained_scenes_preserved",
                    "startup_backup", "process_exit_code", "process_launched", "existing_blender_pid"):
            for value in ("missing", False):
                # A false exit is contradictory, rather than a missing witness.
                if key == "process_exit_code" and value is False:
                    continue
                with self.subTest(key=key, value=value):
                    proof, baseline, release = self.fixture()
                    if value == "missing":
                        del proof[key]
                    else:
                        proof[key] = True if key == "process_launched" else value
                    self.assert_reconcile(proof, baseline, release)

    def test_missing_baseline_or_required_output_cannot_complete(self):
        proof, baseline, release = self.fixture()
        self.assert_reconcile(proof, None, release)
        for key in ("source", "glb", "fbx", "hero"):
            with self.subTest(key=key):
                proof, baseline, release = self.fixture()
                del proof[key]
                self.assert_reconcile(proof, baseline, release)

    def test_baseline_hash_context_identity_and_clock_must_match(self):
        changes = (("scene_hashes", {}), ("scene_hashes", {"Scene": "0" * 64}),
                   ("pid", 1), ("active", "Other"), ("selected", []), ("read_only", False),
                   ("run_called", True), ("observed_at_utc", GUI_NOW))
        for key, value in changes:
            with self.subTest(key=key, value=value):
                proof, baseline, release = self.fixture()
                baseline[key] = value
                self.assert_reconcile(proof, baseline, release)

    def test_separate_release_is_required_even_after_finished_outputs(self):
        proof, baseline, _ = self.fixture()
        row = self.assert_reconcile(proof, baseline, None)
        self.assertTrue(row["gui_operation"]["operation_completed"])
        self.assertNotIn("compute_release", row)

    def test_wrong_or_ambiguous_release_does_not_prove_completion(self):
        changes = (("grant", 32783), ("grant", True), ("before", {}),
                   ("before", {"compute": {"holder": "another-owner"}}),
                   ("after", {"compute": None}), ("unlock", {"ok": False, "lock": None}),
                   ("unlock", {"ok": 1, "lock": None}),
                   ("observed_at_utc", "2026-10-16T05:50:49.1272009Z"),
                   ("observed_at_utc", "2026-10-16T06:20:00.0000001Z"),
                   ("observed_at_utc", "malformed"))
        for key, value in changes:
            with self.subTest(key=key, value=value):
                proof, baseline, release = self.fixture()
                release[key] = value
                row = self.assert_reconcile(proof, baseline, release)
                self.assertIsNone(row["compute_release"])

    def test_exact_submicrosecond_utc_ordering_without_truncation(self):
        self.assertLess(s.gui_clock("2026-10-16T05:00:00.1234567Z"),
                        s.gui_clock("2026-10-16T05:00:00.1234568+00:00"))
        self.assertEqual(s.gui_clock("2026-10-16T05:00:00.1Z"),
                         s.gui_clock("2026-10-16T05:00:00.100000000+00:00"))
        for clock in ("2026-10-16T05:00:00.1234567890Z", "2026-10-16T05:00:00+01:00",
                      "2026-10-16T05:00:00", "2026-13-16T05:00:00Z"):
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                s.gui_clock(clock)

    def test_unknown_state_or_bad_terminal_clock_requires_reconciliation(self):
        for key, value in (("state", "RENDERING"), ("state", []), ("finished_at_utc", None),
                           ("finished_at_utc", "2026-10-16T05:00:00Z")):
            proof, baseline, release = self.fixture()
            proof[key] = value
            self.assert_reconcile(proof, baseline, release)

    def test_zero_exit_or_forged_operation_release_effects_are_rejected(self):
        proof, baseline, release = self.fixture()
        proof["process_exit_code"] = 0
        with self.assertRaisesRegex(ValueError, "process exit"):
            self.inspect(self.adapt(proof, baseline, release))
        doc = self.adapt(*self.fixture())
        self.terminal(doc)["compute_release"] = {"released": True, "evidence": self.write("fake.json", {"released": True})}
        with self.assertRaisesRegex(ValueError, "operation-bound"):
            self.inspect(doc)
        doc = self.adapt(*self.fixture())
        self.terminal(doc)["effects"] = "none"
        with self.assertRaisesRegex(ValueError, "effects differ"):
            self.inspect(doc)

    def test_operation_attempt_and_allocation_are_bound_to_raw_terminal(self):
        for key, value in (("operation_id", "different-attempt"), ("allocation_id", 32783)):
            doc = self.adapt(*self.fixture())
            self.terminal(doc)["gui_operation"][key] = value
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                self.inspect(doc)

    def test_changed_terminal_baseline_release_and_output_pins_fail_closed(self):
        for selected in ("terminal", "baseline", "release", "hero"):
            doc = self.adapt(*self.fixture())
            event = self.terminal(doc)
            pin = {"terminal": event["gui_operation"]["evidence"],
                   "baseline": event["gui_operation"]["baseline"],
                   "release": event["compute_release"]["evidence"], "hero": event["outputs"]["hero"]}[selected]
            Path(pin["path"]).write_bytes(b"changed after adaptation")
            with self.subTest(pin=selected), self.assertRaisesRegex(ValueError, "changed pin"):
                self.inspect(doc)

    def test_output_pin_cannot_be_substituted_or_empty(self):
        doc = self.adapt(*self.fixture())
        self.terminal(doc)["outputs"]["hero"] = self.artifact
        with self.assertRaisesRegex(ValueError, "differs from retained"):
            self.inspect(doc)
        proof, baseline, release = self.fixture()
        proof["hero"] = self.write("empty.png", b"")
        self.assert_reconcile(proof, baseline, release)

    def test_empty_backup_or_matching_malformed_context_is_incomplete(self):
        proof, baseline, release = self.fixture()
        proof["startup_backup"] = self.write("empty.blend", b"")
        self.assert_reconcile(proof, baseline, release)
        for source_key, before_key, value in (("scene", "original_scene", None),
                                               ("selected", "selected", 0), ("mode", "mode", "")):
            with self.subTest(key=source_key):
                proof, baseline, release = self.fixture()
                proof["original_context"][source_key] = baseline[before_key] = value
                self.assert_reconcile(proof, baseline, release)

    def test_gui_attempt_witness_not_inherited_by_new_attempt(self):
        doc = self.adapt(*self.fixture())
        doc["stages"][0]["attempts"].append({"attempt_id": "next", "inputs": {},
            "events": [{"state": "accepted", "observed_at_utc": GUI_NOW}]})
        row = self.inspect(doc)["stages"][0]
        self.assertEqual("accepted", row["status"])
        self.assertNotIn("gui_operation", row)
        self.assertNotIn("compute_release", row)
        self.assertTrue(row["previous_attempts"][0]["gui_operation"]["operation_completed"])

    def test_cli_gui_bad_receipt_or_selected_pin_returns_json3(self):
        for value in ([], {"schema": "unknown"}, b'{"schema":',
                      dict(self.fixture()[0], hero={"bytes": 1})):
            pin = self.write("bad-gui.json", value)
            args = ["adapt-gui", "--terminal", pin["path"], "--job-id", "job", "--stage-id", "stage",
                    "--attempt-id", "copperfall-after-r2-32797", "--observed-at-utc", GUI_NOW,
                    "--output-field", "hero=hero"]
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(3, s.main(args))
            self.assertEqual("", stdout.getvalue())
            self.assertFalse(json.loads(stderr.getvalue())["complete"])
            self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
