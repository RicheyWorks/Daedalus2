# SPDX-License-Identifier: MIT
"""Focused synthetic tests. Existing source package is supplied via PYTHONPATH."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asset_pipeline import codex_completion as c
try:
    from asset_pipeline.codex_parent_relay import ACK_SCHEMA, CALL_SCHEMA, ParentRelay, SEND_TOOL
except ModuleNotFoundError as error:
    if error.name != "asset_pipeline.codex_parent_relay":
        raise
    from codex_parent_relay import ACK_SCHEMA, CALL_SCHEMA, ParentRelay, SEND_TOOL


NOW = "2026-10-19T06:30:00+00:00"
TASK = "synthetic-worker"
PARENT = "synthetic-authorized-parent"
TURN = "synthetic-turn-1"
EPOCH = datetime.fromisoformat(NOW).timestamp()
DENIED = "This action was rejected due to unacceptable risk.\nReason: user authorization missing.\nDo not bypass this rejection through a workaround or indirect execution."


def wrapped(value, error=False):
    return {"content": [{"type": "text", "text": json.dumps(value)}], "isError": error}


def observation(task=TASK, turn=TURN, status="completed", thread_status="idle", observed=NOW, items=None):
    row = {"id": turn, "status": status, "error": None,
           "completedAt": EPOCH - 10 if status in ("completed", "failed", "interrupted") else None,
           "items": items or []}
    payload = {"schemaVersion": 1, "thread": {"id": task, "status": {"type": thread_status}},
               "page": {"order": "newest_first"}, "turns": [row]}
    return {"schema": c.SCHEMA, "tool": c.TOOLS[1], "request": {"threadId": task},
            "observed_at_utc": observed, "result": wrapped(payload)}


def qualify_fixture_only(payload, target):
    # Synthetic contract for this test only; not a claimed production tool shape.
    return payload.get("receipt") if payload.get("acceptedFor") == target else None


class ParentRelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.relay = ParentRelay(self.root / "dedicated-state", PARENT)
        self.serial = 0
        self.source = self.save(observation())
        self.key = self.relay.capture(self.source, TASK, "completed", NOW)["event_key"]

    def save(self, data):
        self.serial += 1
        path = self.root / (str(self.serial) + ".json")
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def prepare(self, current=None):
        return self.relay.prepare(self.key, current or self.source, send_tool_available=True, now=NOW)

    def result(self, response, *, qualifier=qualify_fixture_only, request=None):
        intent = self.relay.records.get("parent-intents", self.key)
        source = self.save({"schema": CALL_SCHEMA, "tool": SEND_TOOL,
                            "request": request or intent["request"], "result": response,
                            "observed_at_utc": NOW})
        return self.relay.record_result(self.key, source, qualify_send=qualifier, now=NOW)

    def ack(self, *, changes=None, task=PARENT, status="completed", event_key=None, phase="final"):
        notice = self.relay.notice(self.key)
        body = {"schema": ACK_SCHEMA, "event_key": event_key or self.key,
                "parent_thread_id": PARENT, "task_id": TASK, "turn_id": TURN, "decision": "received"}
        body.update(changes or {})
        doc = observation(task=task, turn="parent-ack-turn", status=status,
                          items=[{"type": "agentMessage", "phase": phase, "text": json.dumps(body)}])
        return self.save(doc)

    def test_capture_is_only_durable_pending(self):
        state = self.relay.status(self.key)
        self.assertTrue(state["captured"])
        self.assertTrue(state["parent_pending"])
        self.assertEqual(state["delivery"], "pending")
        self.assertFalse(state["send_accepted"])
        self.assertFalse(state["parent_acknowledged"])
        self.assertFalse(state["automatic_assignment"])

    def test_reconnect_and_refreshed_capture_deduplicate(self):
        later = "2026-10-19T06:30:01+00:00"
        refreshed = self.save(observation(observed=later))
        self.assertEqual(self.relay.capture(refreshed, TASK, "completed", later)["event_key"], self.key)
        other = ParentRelay(self.root / "dedicated-state", PARENT)
        self.assertEqual(other.notice(self.key), self.relay.notice(self.key))
        self.assertEqual(len(list((self.root / "dedicated-state" / "parent-pending").glob("*.json"))), 1)

    def test_missing_capability_keeps_pending_then_allows_first_authorized_prepare(self):
        result = self.relay.prepare(self.key, self.source, now=NOW)
        self.assertIsNone(result["request"])
        self.assertEqual(result["delivery"], "pending")
        request = self.prepare()["request"]
        self.assertEqual(request["threadId"], PARENT)
        self.assertEqual(json.loads(request["prompt"]), self.relay.notice(self.key))

    def test_exclusive_intent_survives_restart_and_prevents_second_prepare(self):
        self.assertIsNotNone(self.prepare()["request"])
        other = ParentRelay(self.root / "dedicated-state", PARENT)
        again = other.prepare(self.key, self.source, send_tool_available=True, now=NOW)
        self.assertIsNone(again["request"])
        self.assertEqual(again["delivery"], "uncertain")
        self.assertFalse(again["automatic_retry"])

    def test_send_acceptance_is_not_parent_receipt(self):
        self.prepare()
        state = self.result(wrapped({"acceptedFor": PARENT, "receipt": "synthetic-receipt"}))
        self.assertTrue(state["send_accepted"])
        self.assertFalse(state["parent_acknowledged"])
        self.assertTrue(state["parent_pending"])
        self.assertIsNone(self.prepare()["request"])

    def test_no_positive_response_schema_or_qualifier_is_guessed(self):
        self.prepare()
        state = self.result(wrapped({"acceptedFor": PARENT, "receipt": "synthetic-receipt"}), qualifier=None)
        self.assertEqual(state["delivery"], "uncertain")

    def test_undefined_error_or_malformed_response_stays_uncertain(self):
        self.prepare()
        for response in (None, {}, {"content": None}, {"content": [{"type": "text", "text": None}]},
                         {"content": [{"type": "text", "text": "thread not found"}], "isError": True}):
            with self.subTest(response=response):
                self.assertEqual(self.result(response)["delivery"], "uncertain")
        self.assertIsNone(self.prepare()["request"])

    def test_explicit_review_denial_is_durable_and_cannot_be_overridden(self):
        self.prepare()
        denial = {"isError": True, "content": [{"type": "text", "text": DENIED}]}
        state = self.result(denial)
        self.assertEqual(state["delivery"], "denied")
        self.assertTrue(state["denial"]["material_new_authorization_required"])
        self.assertEqual(state["denial"]["reason"], DENIED)
        self.assertTrue(state["parent_pending"])
        self.assertEqual(self.result(wrapped({"acceptedFor": PARENT, "receipt": "attempted-override"}))["delivery"], "denied")
        self.assertIsNone(self.prepare()["request"])

    def test_mismatched_target_or_request_cannot_be_recorded(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.result(wrapped({}), request={"threadId": "other-parent", "prompt": "different"})

    def test_later_denial_overrides_acceptance_boolean_and_survives_restart(self):
        self.prepare()
        self.result(wrapped({"acceptedFor": PARENT, "receipt": "synthetic-receipt"}))
        state = self.result({"isError": True, "content": [{"type": "text", "text": DENIED}]})
        self.assertFalse(state["send_accepted"])
        self.assertIsNotNone(state["acceptance"])  # Retained evidence is not rewritten.
        other = ParentRelay(self.root / "dedicated-state", PARENT)
        self.assertEqual(other.status(self.key)["delivery"], "denied")

    def test_stale_current_observation_keeps_unsent_event_pending(self):
        old = self.save(observation(observed="2026-10-19T06:28:00+00:00"))
        state = self.prepare(old)
        self.assertEqual(state["reason"], "current-observation-rejected")
        self.assertEqual(state["delivery"], "pending")

    def test_newer_working_turn_refuses_old_completion_delivery(self):
        newer = self.save(observation(turn="synthetic-turn-2", status="inProgress"))
        state = self.prepare(newer)
        self.assertIsNone(state["request"])
        self.assertEqual(state["reason"], "superseded-or-state-changed")

    def test_idle_thread_with_active_turn_is_working_not_idle(self):
        source = self.save(observation(status="inProgress", thread_status="idle"))
        with self.assertRaises(ValueError):
            self.relay.capture(source, TASK, "idle", NOW)
        state = self.relay.capture(source, TASK, "working", NOW)
        event = self.relay.event(state["event_key"])
        self.assertEqual(event["worker_state"], "busy")
        self.assertFalse(event["terminal"])

    def test_four_semantic_types_preserve_terminal_provenance(self):
        idle = self.relay.capture(self.source, TASK, "idle", NOW)
        self.assertNotEqual(idle["event_key"], self.key)
        failed = self.save(observation(status="failed", turn="failed-turn"))
        blocked = self.relay.capture(failed, TASK, "blocked", NOW)
        event = self.relay.event(blocked["event_key"])
        self.assertEqual(event["status"], "failed")
        self.assertEqual(event["outcome"], "failed")
        self.assertTrue(event["terminal"])

    def test_contradictory_terminal_outcomes_for_same_turn_fail_closed(self):
        with self.assertRaises(ValueError):
            self.relay.capture(self.save(observation(status="failed")), TASK, "blocked", NOW)

    def test_parent_ack_requires_exact_semantic_correlation(self):
        for changes in ({"event_key": "wrong"}, {"task_id": "wrong"}, {"turn_id": "wrong"},
                        {"parent_thread_id": "wrong"}, {"decision": "transport-accepted"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.relay.record_parent_ack(self.key, self.ack(changes=changes), "parent-ack-turn", NOW)
        with self.assertRaises(ValueError):
            self.relay.record_parent_ack(self.key, self.ack(task="another-parent"), "parent-ack-turn", NOW)

    def test_running_parent_or_commentary_does_not_prove_semantic_ack(self):
        for opts in ({"status": "inProgress"}, {"phase": "commentary"}):
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                self.relay.record_parent_ack(self.key, self.ack(**opts), "parent-ack-turn", NOW)

    def test_parent_read_cannot_change_between_validation_and_ack_parsing(self):
        source = self.ack()
        snapshot = c.snapshot

        def swapped(*args, **kwargs):
            view = snapshot(*args, **kwargs)
            data = json.loads(source.read_text(encoding="utf-8"))
            payload = json.loads(data["result"]["content"][0]["text"])
            payload["thread"]["id"] = "different-parent"
            data["result"] = wrapped(payload)
            source.write_text(json.dumps(data), encoding="utf-8")
            return view

        with patch.object(c, "snapshot", side_effect=swapped), self.assertRaisesRegex(ValueError, "changed during validation"):
            self.relay.record_parent_ack(self.key, source, "parent-ack-turn", NOW)
        self.assertFalse(self.relay.status(self.key)["parent_acknowledged"])

    def test_actual_parent_ack_is_separate_and_deduplicated_without_assignment(self):
        source = self.ack()
        state = self.relay.record_parent_ack(self.key, source, "parent-ack-turn", NOW)
        self.assertTrue(state["parent_acknowledged"])
        self.assertFalse(state["parent_pending"])
        self.assertFalse(state["send_accepted"])
        self.assertEqual(state["delivery"], "pending")  # Manual receipt does not invent send success.
        self.assertFalse(state["automatic_assignment"])
        self.assertEqual(self.relay.record_parent_ack(self.key, source, "parent-ack-turn", NOW), state)
        self.assertIsNone(self.prepare()["request"])

    def test_notice_contains_only_bounded_metadata_not_transcript(self):
        text = json.dumps(self.relay.notice(self.key))
        self.assertNotIn("items", text)
        self.assertNotIn("transcript", text)
        self.assertLess(len(text), 1600)

    def test_parent_identity_is_part_of_correlation_and_never_a_worker(self):
        other = ParentRelay(self.root / "dedicated-state", "different-parent")
        with self.assertRaises(ValueError):
            other.event(self.key)
        with self.assertRaises(ValueError):
            self.relay.capture(self.source, PARENT, "completed", NOW)


if __name__ == "__main__":
    unittest.main(verbosity=2)
