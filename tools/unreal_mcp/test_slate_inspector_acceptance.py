# SPDX-License-Identifier: MIT
"""Pure synthetic contract tests; no captured editor state or native execution."""
import copy
import datetime
import hashlib
import json
import unittest
from unittest.mock import patch

from tools.unreal_mcp import slate_inspector_acceptance as acceptance
from tools.unreal_mcp.slate_inspector_results import ContractViolation


PID = 12345
WORLD = "/Game/Maps/Example.Example"
NOW = datetime.datetime(2026, 10, 19, 17, 10, tzinfo=datetime.timezone.utc)
PROCESS_START = "2026-10-19T16:00:00.0000000+00:00"
CAPTURE_ID = "a77d24f2-842b-4fb3-a364-67cad3d8da42"
REQUEST_ID = "synthetic-retained-request-1"
TEXT = ('generic "Details" [pos=0,0 size=320,240] [src=SDetailsView.cpp:1] [ref=g7]\n'
        '  text "Selected actor" [pos=2,2 size=200,20] [ref=t1]\n')


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def binding(**changes):
    value = {
        "scope": "existing_primary_level_editor_details", "status": "Bound",
        "bound": True, "approved_ref": "g7", "process_id": PID, "world": WORLD,
        "tab_id": "LevelEditorSelectionDetails", "tab_label": "Details",
        "panel_type": "SDetailsView", "window_title": "Example Editor",
        "owning_manager_agrees": True, "window_identity_agrees": True,
        "panel_visible": True, "tab_foreground": True, "window_visible": True,
        "cache_roundtrip": True, "keyboard_focus_preserved": True,
        "active_window_preserved": True, "ref_preexisting": False, "diagnostic": "",
    }
    value.update(changes)
    return value


class DetailsBindingTests(unittest.TestCase):
    def read(self, value=None, **expectations):
        raw = json.dumps(binding() if value is None else value)
        return acceptance.read_details_binding(raw, expected_process_id=expectations.get("pid", PID),
                                               expected_world=expectations.get("world", WORLD))

    def test_exact_binding_and_both_ref_preexisting_values(self):
        for preexisting in (False, True):
            value = binding(ref_preexisting=preexisting, tab_label="詳細 😀", window_title="Éditeur")
            self.assertEqual(self.read(value), value)

    def test_every_agreement_flag_requires_exact_true(self):
        flags = ("bound", "owning_manager_agrees", "window_identity_agrees", "panel_visible",
                 "tab_foreground", "window_visible", "cache_roundtrip",
                 "keyboard_focus_preserved", "active_window_preserved")
        for flag in flags:
            for invalid in (False, 1, 1.0, "true", None):
                with self.subTest(flag=flag, invalid=invalid), self.assertRaises(ContractViolation):
                    self.read(binding(**{flag: invalid}))

    def test_missing_unknown_and_rejected_binding(self):
        for key in binding():
            changed = binding()
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(ContractViolation):
                self.read(changed)
        for changed in (binding(extra=True), binding(status="Rejected"),
                        binding(scope="all_windows"), binding(diagnostic="Could not bind")):
            with self.subTest(changed=changed), self.assertRaises(ContractViolation):
                self.read(changed)

    def test_expected_receiver_identity_is_external_and_exact(self):
        for changed in (binding(process_id=PID+1), binding(world=WORLD+"_old"),
                        binding(process_id=True), binding(process_id=0),
                        binding(process_id=4294967296), binding(process_id=float(PID))):
            with self.subTest(changed=changed), self.assertRaises(ContractViolation):
                self.read(changed)
        for expected in (True, 0, 1.5, "12345"):
            with self.subTest(expected=expected), self.assertRaises(ContractViolation):
                self.read(pid=expected)

    def test_unapproved_tab_or_malformed_ref(self):
        for changed in (binding(tab_id="LevelEditorViewport"), binding(approved_ref=""),
                        binding(approved_ref="g0"), binding(approved_ref="g2147483648"),
                        binding(approved_ref="../g7"), binding(ref_preexisting=1)):
            with self.subTest(changed=changed), self.assertRaises(ContractViolation):
                self.read(changed)

    def test_native_errors_envelopes_duplicates_nonfinite_and_bad_unicode(self):
        raw = json.dumps(binding())
        values = ("Error: Could not bind Details", "[]", "null", "{", {},
                  json.dumps({"returnValue": raw}),
                  raw.replace('"bound": true', '"bound": true, "bound": true'),
                  raw.replace('"bound": true', '"bound": true, "boun\\u0064": true'),
                  raw.replace('"process_id": 12345', '"process_id": NaN'),
                  json.dumps(binding(panel_type="\ud800")),
                  json.dumps(binding(window_title="Editor\x00window")))
        for value in values:
            with self.subTest(value=value), self.assertRaises(ContractViolation):
                acceptance.read_details_binding(value, expected_process_id=PID, expected_world=WORLD)


def state(utc):
    idle = {"queue": 0, "other_running": [], "remote_locked": False, "unfinished_async": []}
    return {
        "utc": utc, "writes": 0, "bridge_before": dict(idle), "bridge_after": dict(idle),
        "errors": {}, "project": "../../Unreal/Example.uproject", "world": WORLD,
        "pie": False, "game_world": None, "dirty_maps": [], "dirty_content": [],
        "scene": {"actors": 3, "sha256": "a" * 64,
                  "scope": "actor path/class/label/location/rotation/scale"},
        "selection": [], "camera": {"location": [1.0, 2.0, 3.0], "rotation": [0.0, 45.0, 0.0]},
        "interchange": {"module_loaded": False, "module_file": None, "state_present": False,
                        "done": None, "done_objects": None},
    }


def capture():
    raw_binding = json.dumps(binding(), ensure_ascii=False)
    return {
        "schema": "daedalus.official-slate-panel-capture.v1", "capture_id": CAPTURE_ID,
        "editor": {"pid": PID, "process_start_utc": PROCESS_START, "world": WORLD},
        "route": {"kind": "existing_bridge_reflected_uobject_call", "bridge_command": "execute_python",
                  "bridge_address": "127.0.0.1:9877", "request_id": REQUEST_ID,
                  "toolset_object_path": "/Script/SlateInspectorToolset.Default__SlateInspectorToolset",
                  "toolset_class_path": "/Script/SlateInspectorToolset.SlateInspectorToolset",
                  "reflected_method": "Snapshot"},
        "binding": {"raw_return_json": raw_binding, "payload": binding(), "utf8_sha256": digest(raw_binding)},
        "snapshot_request": {"Ref": "g7", "MaxDepth": 2, "bIncludeSourceLocations": True},
        "call": {"started_utc": "2026-10-19T17:09:50+00:00", "ended_utc": "2026-10-19T17:09:51+00:00"},
        "raw_return_text": TEXT, "raw_return_utf8_sha256": digest(TEXT),
        "preservation": {"before": state("2026-10-19T10:09:49-07:00"),
                         "after": state("2026-10-19T17:09:52+00:00"),
                         "equal_fields": {field: True for field in
                                          ("project", "world", "pie", "game_world", "dirty_maps",
                                           "dirty_content", "scene", "selection", "camera")}, "accepted": True},
        "state_effects": {"assets": 0, "world": 0, "input": 0, "observers": 0,
                          "ref_cache": "append_or_reuse_one_shared_ref"},
    }


class PanelCaptureTests(unittest.TestCase):
    def setUp(self):
        self.consumed = set()
        self.clock = patch.object(acceptance, "_utc_now", return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def read(self, value=None, **changes):
        options = {"expected_process_id": PID, "expected_process_start_utc": PROCESS_START,
                   "expected_world": WORLD, "expected_capture_id": CAPTURE_ID,
                   "expected_request_id": REQUEST_ID, "consumed_capture_ids": self.consumed}
        options.update(changes)
        return acceptance.read_panel_capture(capture() if value is None else value, **options)

    def test_fresh_evidence_is_separate_from_unchanged_plan_contract(self):
        original = capture()
        before = copy.deepcopy(original)
        result = self.read(original)
        self.assertEqual(original, before)
        self.assertTrue(result["fresh_at_check"])
        self.assertEqual(result["capture_evidence"], "caller_attested_capture")
        self.assertFalse(result["native_runtime_qualified"])
        self.assertFalse(result["current_receiver_rechecked"])
        self.assertTrue(result["packet"]["plan_only"])
        self.assertFalse(result["packet"]["execution_authorized"])
        self.assertFalse(result["packet"]["native_runtime_qualified"])
        self.assertEqual(result["packet"]["freshness"], "unproven")
        self.assertEqual(result["snapshot_sha256"], digest(TEXT))
        self.assertEqual(self.consumed, {"capture:"+CAPTURE_ID, "request:"+REQUEST_ID})

    def test_replay_capture_or_retained_request_rejected(self):
        self.read()
        with self.assertRaisesRegex(ContractViolation, "already consumed"):
            self.read()
        changed = capture()
        changed["capture_id"] = "c7a02c90-dc91-46dc-b71b-88c7a8da73bc"
        with self.assertRaisesRegex(ContractViolation, "already consumed"):
            self.read(changed, expected_capture_id=changed["capture_id"])

    def test_receiver_pid_start_world_and_external_dispatch_ids_are_required(self):
        mutations = (("editor", "pid", PID+1), ("editor", "pid", True),
                     ("editor", "world", WORLD+"_old"),
                     ("editor", "process_start_utc", "2026-10-19T16:00:01+00:00"),
                     ("route", "request_id", "another-request"))
        for section, field, value in mutations:
            changed = capture()
            changed[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaises(ContractViolation):
                self.read(changed)
        with self.assertRaises(ContractViolation):
            self.read(expected_capture_id="capture-not-uuid")
        self.assertEqual(self.consumed, set())

    def test_wrong_route_or_unexpected_mcp_envelope_rejected(self):
        for field, value in (("kind", "mcp"), ("bridge_address", "127.0.0.1:8000"),
                             ("reflected_method", "Click"), ("bridge_command", "other"),
                             ("toolset_object_path", "")):
            changed = capture()
            changed["route"][field] = value
            with self.subTest(field=field), self.assertRaises(ContractViolation):
                self.read(changed)
        for changed in ({"result": capture()}, {**capture(), "mcp_session_id": "invented"}):
            with self.assertRaises(ContractViolation):
                self.read(changed)

    def test_raw_binding_hash_and_payload_cannot_be_replaced_by_reserialization(self):
        for mutation in ("hash", "raw", "payload"):
            changed = capture()
            if mutation == "hash":
                changed["binding"]["utf8_sha256"] = "0" * 64
            elif mutation == "raw":
                changed["binding"]["raw_return_json"] += "\n"
            else:
                changed["binding"]["payload"]["ref_preexisting"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ContractViolation):
                self.read(changed)

    def test_snapshot_ref_depth_source_flag_and_hash_are_exact(self):
        for field, value in (("Ref", "g8"), ("Ref", ""), ("MaxDepth", True),
                             ("MaxDepth", 3), ("bIncludeSourceLocations", False)):
            changed = capture()
            changed["snapshot_request"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ContractViolation):
                self.read(changed)
        changed = capture()
        changed["raw_return_utf8_sha256"] = "0" * 64
        with self.assertRaises(ContractViolation):
            self.read(changed)

    def test_native_error_blank_json_control_and_malformed_accessibility_text_rejected(self):
        for text in ("Error: Could not resolve ref", " ", "{}", "not a snapshot", TEXT+"\x01",
                     TEXT.replace("[ref=g7]", "[ref=g0]"), TEXT+"\ud800"):
            changed = capture()
            changed["raw_return_text"] = text
            changed["raw_return_utf8_sha256"] = digest(text) if "\ud800" not in text else "0" * 64
            with self.subTest(text=text), self.assertRaises(ContractViolation):
                self.read(changed)

    def test_stale_future_unordered_or_naive_times_cannot_refresh_evidence(self):
        for start, end in (("2026-10-19T17:00:00+00:00", "2026-10-19T17:00:01+00:00"),
                           ("2026-10-19T18:00:00+00:00", "2026-10-19T18:00:01+00:00"),
                           ("2026-10-19T17:09:55+00:00", "2026-10-19T17:09:50+00:00"),
                           ("2026-10-19T17:09:50", "2026-10-19T17:09:51+00:00")):
            changed = capture()
            changed["call"] = {"started_utc": start, "ended_utc": end}
            retained = copy.deepcopy(changed)
            with self.subTest(start=start), self.assertRaises(ContractViolation):
                self.read(changed)
            self.assertEqual(changed, retained)
        with self.assertRaises(TypeError):
            self.read(now=NOW)
        self.assertEqual(self.consumed, set())

    def test_preservation_recomputes_comparisons_instead_of_trusting_true_flags(self):
        for field, value in (("world", WORLD+"_changed"), ("selection", ["/Game/Other.Other"]),
                             ("camera", {"location": [9, 9, 9], "rotation": [0, 0, 0]}),
                             ("dirty_maps", ["/Game/Dirty"]), ("pie", True), ("game_world", False),
                             ("writes", False), ("errors", {"camera": "unavailable"})):
            changed = capture()
            changed["preservation"]["after"][field] = value
            with self.subTest(field=field), self.assertRaises(ContractViolation):
                self.read(changed)

    def test_preservation_flags_and_bridge_idle_types_are_exact(self):
        for field, value in (("queue", False), ("queue", 1), ("remote_locked", 0),
                             ("other_running", ["foreign"]), ("unfinished_async", ["job"])):
            changed = capture()
            changed["preservation"]["before"]["bridge_before"][field] = value
            with self.subTest(field=field), self.assertRaises(ContractViolation):
                self.read(changed)
        for section, field in (("equal_fields", "camera"),):
            changed = capture()
            changed["preservation"][section][field] = 1
            with self.assertRaises(ContractViolation):
                self.read(changed)
        changed = capture()
        changed["preservation"]["accepted"] = False
        with self.assertRaises(ContractViolation):
            self.read(changed)

    def test_preservation_must_bracket_call_and_state_effects_are_zero_ints(self):
        changed = capture()
        changed["preservation"]["after"]["utc"] = "2026-10-19T17:09:49+00:00"
        with self.assertRaises(ContractViolation):
            self.read(changed)
        for field in ("assets", "world", "input", "observers"):
            for value in (False, 1):
                changed = capture()
                changed["state_effects"][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ContractViolation):
                    self.read(changed)
        self.assertEqual(self.consumed, set())


if __name__ == "__main__":
    unittest.main()
