# SPDX-License-Identifier: MIT
"""Offline fixtures for the Slate Inspector execution-packet adapter."""
import hashlib
import json
import unittest
from unittest.mock import patch

from tools.unreal_mcp import slate_inspector_packet as pkt
from tools.unreal_mcp import slate_inspector_results as s
from tools.unreal_mcp.slate_inspector_results import ContractViolation


def observer(identifier="observer_2", ref="w1", root=False, depth=30, size=80):
    return {"identifier": identifier, "root": root, "rootRef": ref,
            "maxDepth": depth, "cachedSnapshotSize": size}


def encoded(*rows):
    return json.dumps(list(rows))


ROOT = observer("observer_1", "", True, 0, 50)
PANEL = observer()
SNAPSHOT = 'window "Example" [pos=0,0 size=800,600] [ref=w1]\n  button "Save" [ref=b1]\n'
WINDOWS = json.dumps([{"index": 0, "title": 'Window "A"'}, {"index": 1, "title": ""}])


class SlateInspectorPacketTests(unittest.TestCase):
    def test_full_windows_snapshot_cleanup_packet_plan_only(self):
        before, after = encoded(ROOT), encoded(ROOT, PANEL)
        packet = pkt.build_execution_packet(
            approved_ref="w1",
            max_depth=30,
            purpose="metaverse_panel_inspection",
            windows_return=WINDOWS,
            snapshot_return=SNAPSHOT,
            observers_before=before,
            observers_after=after,
            observe_return_value="observer_2",
            caller_owns_observer=True,
        )
        self.assertEqual(packet["kind"], pkt.PACKET_KIND)
        self.assertEqual(packet["version"], pkt.PACKET_VERSION)
        self.assertEqual(packet["toolset"], s.TOOLSET)
        self.assertEqual(packet["approved_ref"], "w1")
        self.assertEqual(packet["purpose"], "metaverse_panel_inspection")
        self.assertEqual(packet["source_commit"], pkt.SOURCE_COMMIT)
        self.assertTrue(packet["contract_valid"])
        self.assertFalse(packet["execution_authorized"])
        self.assertTrue(packet["plan_only"])
        self.assertFalse(packet["native_runtime_qualified"])
        self.assertEqual(packet["freshness"], "unproven")
        self.assertEqual(packet["panel_binding"], "qualified_caller_request_only")
        self.assertTrue(packet["never_executes_natively"])
        self.assertEqual(packet["sole_unreal_writer"], "codex-play-guard")
        self.assertEqual(packet["source_provenance"], s.SOURCE_PROVENANCE)
        step_names = [step["step"] for step in packet["steps"]]
        self.assertEqual(step_names, ["windows_list", "snapshot", "cleanup_plan"])
        self.assertIn("windows_return", packet["content_hashes"])
        self.assertIn("snapshot_return", packet["content_hashes"])
        self.assertEqual(
            packet["content_hashes"]["snapshot_return"],
            hashlib.sha256(SNAPSHOT.encode()).hexdigest(),
        )
        self.assertEqual(len(packet["packet_sha256"]), 64)
        cleanup = packet["steps"][2]
        self.assertEqual(cleanup["planned_tool"], "Unobserve")
        self.assertFalse(cleanup["execution_authorized"])
        self.assertTrue(cleanup["plan_only"])

    def test_builder_class_matches_function(self):
        builder = pkt.ExecutionPacketBuilder(approved_ref="w1", purpose="metaverse_panel_inspection")
        packet = builder.build(snapshot_return=SNAPSHOT)
        self.assertEqual(packet["approved_ref"], "w1")
        self.assertEqual(packet["purpose"], "metaverse_panel_inspection")
        self.assertEqual(packet["steps"][0]["step"], "snapshot")

    def test_observers_only_packet(self):
        raw = encoded(ROOT, PANEL)
        packet = pkt.build_execution_packet(approved_ref="w1", observers_return=raw)
        self.assertEqual([step["step"] for step in packet["steps"]], ["observers"])
        self.assertEqual(packet["steps"][0]["row_count"], 2)

    def test_metaverse_purpose_field_present_and_customizable(self):
        packet = pkt.build_execution_packet(
            approved_ref="w1",
            purpose="metaverse_verify_ingestion_selection",
            snapshot_return=SNAPSHOT,
        )
        self.assertEqual(packet["purpose"], "metaverse_verify_ingestion_selection")

    def test_requires_at_least_one_slice(self):
        with self.assertRaises(ContractViolation):
            pkt.build_execution_packet(approved_ref="w1")

    def test_partial_cleanup_trio_rejected(self):
        with self.assertRaises(ContractViolation):
            pkt.build_execution_packet(
                approved_ref="w1",
                observers_before=encoded(ROOT),
                observers_after=encoded(ROOT, PANEL),
            )

    def test_empty_purpose_rejected(self):
        with self.assertRaises(ContractViolation):
            pkt.build_execution_packet(approved_ref="w1", purpose="  ", snapshot_return=SNAPSHOT)

    def test_bad_ref_rejected(self):
        for ref in ("", "w0", "../w1", None):
            with self.subTest(ref=ref), self.assertRaises(ContractViolation):
                pkt.build_execution_packet(approved_ref=ref, snapshot_return=SNAPSHOT)

    def test_depth_over_budget_rejected(self):
        with self.assertRaises(ContractViolation):
            pkt.build_execution_packet(approved_ref="w1", max_depth=65, snapshot_return=SNAPSHOT)

    def test_snapshot_ref_must_match_approved(self):
        with self.assertRaises(ContractViolation):
            pkt.build_execution_packet(
                approved_ref="w1",
                snapshot_return=SNAPSHOT,
                snapshot_ref="w2",
            )

    def test_empty_snapshot_rejected(self):
        for text in ("", " \n\t"):
            with self.subTest(text=repr(text)), self.assertRaises(ContractViolation):
                pkt.build_execution_packet(approved_ref="w1", snapshot_return=text)

    def test_window_mutation_actions_rejected_via_contract(self):
        # Adapter always passes action='list'; contract rejects if we misuse results.
        with self.assertRaises(ContractViolation):
            s.read_windows(WINDOWS, action="close")
        with self.assertRaises(ContractViolation):
            s.read_windows(WINDOWS, action="select")

    def test_cleanup_without_ownership_attestation_rejected(self):
        with self.assertRaises(ContractViolation):
            pkt.build_execution_packet(
                approved_ref="w1",
                observers_before=encoded(ROOT),
                observers_after=encoded(ROOT, PANEL),
                observe_return_value="observer_2",
                caller_owns_observer=False,
            )

    def test_no_file_io_or_socket(self):
        with patch("builtins.open", side_effect=AssertionError("no file I/O")), \
             patch("socket.socket", side_effect=AssertionError("no transport")):
            pkt.build_execution_packet(
                approved_ref="w1",
                windows_return=WINDOWS,
                snapshot_return=SNAPSHOT,
                observers_before=encoded(ROOT),
                observers_after=encoded(ROOT, PANEL),
                observe_return_value="observer_2",
                caller_owns_observer=True,
            )

    def test_imports_contract_module_not_redefined(self):
        import inspect
        self.assertIs(pkt.results.read_observers, s.read_observers)
        self.assertIs(pkt.ContractViolation, s.ContractViolation)
        self.assertFalse(hasattr(pkt, "read_observers"))
        source = inspect.getsource(pkt)
        self.assertNotIn("def read_observers", source)
        self.assertNotIn("def read_windows", source)
        self.assertNotIn("class PanelResults", source)
        self.assertIn("slate_inspector_results", source)

    def test_windows_note_not_panel_identity(self):
        packet = pkt.build_execution_packet(approved_ref="w1", windows_return=WINDOWS)
        note = packet["steps"][0]["note"]
        self.assertIn("NOT panel identity", note)

    def test_source_commit_pin(self):
        packet = pkt.build_execution_packet(approved_ref="w1", snapshot_return=SNAPSHOT)
        self.assertEqual(packet["source_commit"], "acf9ab7ae5186d2dd20b69f369460129053ddae5")


if __name__ == "__main__":
    unittest.main()
