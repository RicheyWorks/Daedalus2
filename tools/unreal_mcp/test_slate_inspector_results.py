# SPDX-License-Identifier: MIT
"""Source-derived offline fixtures, not captured Slate/editor observations."""
import hashlib
import json
import unittest
from unittest.mock import patch

from tools.unreal_mcp import slate_inspector_results as s


def observer(identifier="observer_2", ref="w1", root=False, depth=30, size=80):
    return {"identifier": identifier, "root": root, "rootRef": ref,
            "maxDepth": depth, "cachedSnapshotSize": size}


def encoded(*rows):
    return json.dumps(list(rows))


ROOT = observer("observer_1", "", True, 0, 50)
PANEL = observer()
SNAPSHOT = 'window "Example" [pos=0,0 size=800,600] [ref=w1]\n  button "Save" [ref=b1]\n'


class SlateInspectorResultsTests(unittest.TestCase):
    def setUp(self):
        self.panel = s.PanelResults("w1", 30)

    def snapshot(self, value=SNAPSHOT, **changes):
        request = {"ref": "w1", "max_depth": 30, "include_source_locations": False}
        request.update(changes)
        return self.panel.snapshot(value, **request)

    def test_list_observers_exact_native_fields_and_no_mutation(self):
        raw = encoded(ROOT, PANEL)
        self.assertEqual(s.read_observers(raw), [ROOT, PANEL])
        self.assertEqual(raw, encoded(ROOT, PANEL))

    def test_empty_inventory_is_accepted_as_empty_not_health_or_completion(self):
        self.assertEqual(s.read_observers("[]"), [])
        self.assertEqual(s.read_windows("[]", action="list"), [])

    def test_expired_nonroot_ref_and_zero_cached_size_are_representable(self):
        row = observer(ref="", size=0)
        self.assertEqual(s.read_observers(encoded(row)), [row])

    def test_observer_unknown_missing_and_duplicate_members_fail(self):
        for changed in ({**PANEL, "age": 0}, {k: v for k, v in PANEL.items() if k != "root"}):
            with self.subTest(changed=changed), self.assertRaises(s.ContractViolation):
                s.read_observers(encoded(changed))
        raw = encoded(PANEL).replace('"maxDepth": 30', '"maxDepth":30,"maxDepth":30')
        with self.assertRaises(s.ContractViolation):
            s.read_observers(raw)

    def test_observer_counts_are_int32_not_bool_or_nonfinite(self):
        for field in ("maxDepth", "cachedSnapshotSize"):
            for invalid in (True, -1, 1.5, 2147483648, float("nan")):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(s.ContractViolation):
                    s.read_observers(encoded({**PANEL, field: invalid}))

    def test_observer_identity_and_root_invariants(self):
        bad_rows = [encoded(PANEL, PANEL), encoded(ROOT, {**ROOT, "identifier": "observer_3"}),
                    encoded({**ROOT, "rootRef": "w1"}), encoded({**PANEL, "root": 1}),
                    encoded({**PANEL, "identifier": "observer_0"}), encoded({**PANEL, "rootRef": "../w1"})]
        for raw in bad_rows:
            with self.subTest(raw=raw), self.assertRaises(s.ContractViolation):
                s.read_observers(raw)

    def test_native_ref_and_observer_counter_int32_boundaries(self):
        s.PanelResults("w2147483647")
        row = observer("observer_2147483647", "w2147483647")
        self.assertEqual(s.read_observers(encoded(row)), [row])
        for ref in ("w2147483648", "w9999999999"):
            with self.subTest(ref=ref), self.assertRaises(s.ContractViolation):
                s.PanelResults(ref)
        for identifier in ("observer_2147483648", "observer_9999999999"):
            with self.subTest(identifier=identifier), self.assertRaises(s.ContractViolation):
                s.read_observers(encoded({**PANEL, "identifier": identifier}))

    def test_wrong_serializer_error_and_unknown_shapes_rejected(self):
        values = ({"returnValue": "[]"}, [], "null", "{}", "Error: Slate not initialized", "[", '[{"x":NaN}]')
        for value in values:
            with self.subTest(value=value), self.assertRaises(s.ContractViolation):
                s.read_observers(value)

    def test_windows_list_preserves_titles_without_panel_binding(self):
        rows = [{"index": 0, "title": 'Window "A"\n😀'}, {"index": 1, "title": ""}]
        self.assertEqual(s.read_windows(json.dumps(rows), action="list"), rows)
        self.assertNotIn("ref", rows[0])

    def test_window_mutation_actions_never_accepted(self):
        for action in ("close", "select", "", "LIST", None):
            with self.subTest(action=action), self.assertRaises(s.ContractViolation):
                s.read_windows("[]", action=action)

    def test_window_indices_unknown_fields_and_types_rejected(self):
        bad = [[{"index": 1, "title": "A"}], [{"index": True, "title": "A"}],
               [{"index": 0, "title": None}], [{"index": 0, "title": "A", "ref": "w1"}],
               [{"index": 0, "title": "A"}, {"index": 0, "title": "B"}]]
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(s.ContractViolation):
                s.read_windows(json.dumps(rows), action="list")

    def test_single_panel_ref_and_depth_approval_required(self):
        for ref in ("", "*", None, "w0", "w1,w2", "../w1"):
            with self.subTest(ref=ref), self.assertRaises(s.ContractViolation):
                s.PanelResults(ref)
        for depth in (-1, True, 65, 1.5):
            with self.subTest(depth=depth), self.assertRaises(s.ContractViolation):
                s.PanelResults("w1", depth)

    def test_snapshot_plain_text_hash_exact_bytes_and_cache_uncertainty(self):
        result = self.snapshot()
        self.assertEqual(result["text"], SNAPSHOT)
        self.assertEqual(result["content_sha256"], hashlib.sha256(SNAPSHOT.encode()).hexdigest())
        self.assertEqual(result["utf8_bytes"], len(SNAPSHOT.encode()))
        self.assertEqual(result["representation"], "plain_accessibility_text")
        self.assertEqual(result["cache"], "possibly_observer_cached")
        self.assertEqual(result["freshness"], "unproven")
        self.assertFalse(result["native_runtime_qualified"])
        self.assertFalse(result["automatic_actions"])

    def test_source_locations_bypass_cache_lookup_without_freshness_claim(self):
        result = self.snapshot(include_source_locations=True)
        self.assertEqual(result["cache"], "lookup_bypassed_by_request")
        self.assertEqual(result["freshness"], "unproven")

    def test_empty_snapshot_never_means_panel_absent_or_job_complete(self):
        for text in ("", " \n\t"):
            with self.subTest(text=text), self.assertRaises(s.ContractViolation):
                self.snapshot(text)

    def test_wrong_ref_depth_or_missing_source_flag_rejected(self):
        for changes in ({"ref": "w2"}, {"ref": ""}, {"max_depth": 31}, {"max_depth": -1},
                        {"max_depth": True}, {"include_source_locations": 0}):
            with self.subTest(changes=changes), self.assertRaises(s.ContractViolation):
                self.snapshot(**changes)
        self.assertEqual(self.snapshot(max_depth=0)["requested_depth"], 0)

    def test_snapshot_error_nul_invalid_unicode_and_wrapper_rejected(self):
        for value in ("Error: Could not resolve ref", " \nError: Could not resolve ref", "abc\x00", "\ud800", {}):
            with self.subTest(value=repr(value)), self.assertRaises(s.ContractViolation):
                self.snapshot(value)

    def test_snapshot_json_looking_text_remains_plain_text_not_widget_schema(self):
        result = self.snapshot('{"widgets":[]}')
        self.assertEqual(result["representation"], "plain_accessibility_text")
        self.assertNotIn("widgets", result)

    def test_text_byte_budget_including_multibyte_boundary(self):
        self.assertEqual(self.snapshot("a" * s.MAX_RETURN_BYTES)["utf8_bytes"], s.MAX_RETURN_BYTES)
        for text in ("a" * (s.MAX_RETURN_BYTES + 1), "😀" * (s.MAX_RETURN_BYTES // 4 + 1)):
            with self.subTest(length=len(text)), self.assertRaises(s.ContractViolation):
                self.snapshot(text)

    def test_inventory_row_budget(self):
        rows = [{"index": i, "title": ""} for i in range(s.MAX_ROWS + 1)]
        with self.assertRaises(s.ContractViolation):
            s.read_windows(json.dumps(rows), action="list")

    def test_cleanup_plan_exact_new_owned_observer_and_no_execution(self):
        before, after = encoded(ROOT), encoded(ROOT, PANEL)
        plan = self.panel.cleanup_plan(before, after, observe_return_value="observer_2", caller_owns_observer=True)
        self.assertEqual(plan["identifier"], "observer_2")
        self.assertEqual(plan["planned_tool"], "Unobserve")
        self.assertTrue(plan["plan_only"])
        self.assertFalse(plan["execution_authorized"])
        self.assertTrue(plan["live_revalidation_required"])
        self.assertEqual(plan["before_sha256"], hashlib.sha256(before.encode()).hexdigest())
        self.assertFalse(plan["native_runtime_qualified"])

    def test_cleanup_ownership_not_inferred_from_new_identifier(self):
        for attestation in (False, None, 1, "yes"):
            with self.subTest(attestation=attestation), self.assertRaises(s.ContractViolation):
                self.panel.cleanup_plan(encoded(ROOT), encoded(ROOT, PANEL),
                                        observe_return_value="observer_2", caller_owns_observer=attestation)

    def test_preexisting_observer_returned_by_observe_is_shared_not_cleanup_owned(self):
        before = encoded(ROOT, {**PANEL, "maxDepth": 1})
        after = encoded(ROOT, PANEL)
        with self.assertRaises(s.ContractViolation):
            self.panel.cleanup_plan(before, after, observe_return_value="observer_2", caller_owns_observer=True)

    def test_cleanup_foreign_root_unresolved_missing_or_wrong_return_rejected(self):
        cases = [(encoded(ROOT), encoded(ROOT, {**PANEL, "rootRef": "w2"}), "observer_2"),
                 ("[]", encoded(ROOT), "observer_1"),
                 (encoded(ROOT), encoded(ROOT, {**PANEL, "rootRef": ""}), "observer_2"),
                 (encoded(ROOT), encoded(ROOT), "observer_2"),
                 (encoded(ROOT), encoded(ROOT, PANEL), "Error: Could not resolve ref")]
        for before, after, returned in cases:
            with self.subTest(returned=returned, after=after), self.assertRaises(s.ContractViolation):
                self.panel.cleanup_plan(before, after, observe_return_value=returned, caller_owns_observer=True)

    def test_consumers_do_not_open_files_or_transport(self):
        with patch("builtins.open", side_effect=AssertionError("no file I/O")), \
             patch("socket.socket", side_effect=AssertionError("no transport")):
            self.snapshot()
            s.read_windows('[{"index":0,"title":"Example"}]', action="list")
            s.read_observers(encoded(ROOT, PANEL))
            self.panel.cleanup_plan(encoded(ROOT), encoded(ROOT, PANEL),
                                    observe_return_value="observer_2", caller_owns_observer=True)


if __name__ == "__main__":
    unittest.main()
