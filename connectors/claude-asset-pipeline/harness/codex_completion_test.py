# SPDX-License-Identifier: MIT
"""Focused synthetic protocol/filesystem tests; no Codex, HTTP, UI or workers."""
import copy
from datetime import timedelta
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import codex_completion as c

NOW = "2026-10-16T06:30:00Z"
TASK, TURN = "task-1", "turn-1"


class FakeLink:
    def __init__(self):
        self.messages = []
        self.sends = 0
        self.lose_response = False
        self.unavailable = False

    def health(self):
        return None if self.unavailable else {"ok": True, "last": len(self.messages)}

    def append(self, sender, receiver, kind, body):
        self.messages.append({"id": len(self.messages)+1, "from": sender, "to": receiver,
                              "type": kind, "body": copy.deepcopy(body)})
        return self.messages[-1]["id"]

    def send(self, to, kind, body, topic=None):
        self.sends += 1
        mid = self.append(c.SENDER, to, kind, body)
        if self.lose_response:
            return None
        return mid

    def _call(self, method, path):
        if self.unavailable:
            return None
        after = int(path.split("after=")[1].split("&")[0])
        return {"messages": [m for m in self.messages if m["id"] > after][:200]}


class CompletionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.link = FakeLink()
        self.observer = c.Observer(self.root/"state", self.link)
        self.source = self.save(self.envelope())

    def envelope(self, status="completed", state="idle", turn_id=TURN, error=None):
        turn = {"id": turn_id, "status": status, "error": error,
                "completedAt": c.utc(NOW).timestamp()-1 if status in c.TERMINAL else None}
        data = {"timedOut": False, "wake": None, "polls": [{
            "schemaVersion": 1, "thread": {"id": TASK, "status": {"type": state}},
            "latestTurn": turn, "latestToolMarker": {"status": "completed"}}]}
        return {"schema": c.SCHEMA, "tool": c.TOOLS[0],
                "request": {"targets": [{"threadId": TASK}], "timeoutMs": 0},
                "observed_at_utc": NOW,
                "result": {"isError": False, "content": [{"type": "text", "text": json.dumps(data)}]}}

    def save(self, value, name="snapshot.json"):
        path = self.root/name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def observe(self, source=None):
        return self.observer.observe(source or self.source, TASK, NOW)

    def delivery(self):
        event = self.observe()
        result = self.observer.deliver(event["event_key"], self.source, NOW)
        return event["event_key"], result["message_id"]

    def semantic(self, key, mid, **overrides):
        body = {"event_key": key, "task_id": TASK, "turn_id": TURN,
                "notification_id": mid, "decision": "received"}
        body.update(overrides)
        return self.link.append(c.COORDINATOR, c.SENDER, "codex.completion.ack", body)

    def test_real_shape_terminal_detection_without_wake(self):
        result = self.observe()
        self.assertTrue(result["terminal"])
        self.assertEqual("succeeded", result["outcome"])
        self.assertEqual(c.key_for(TASK, TURN), result["event_key"])

    def test_tool_completion_marker_is_not_turn_completion(self):
        self.assertFalse(self.observe(self.save(self.envelope("inProgress", "active")))["terminal"])

    def test_timedout_false_is_not_completion(self):
        self.assertIsNone(self.observe(self.save(self.envelope("inProgress", "active")))["event_key"])

    def test_failed_terminal(self):
        self.assertEqual("failed", self.observe(self.save(self.envelope("failed")))["outcome"])

    def test_interrupted_terminal(self):
        self.assertEqual("cancelled", self.observe(self.save(self.envelope("interrupted")))["outcome"])

    def test_unknown_status_is_not_completion(self):
        self.assertFalse(self.observe(self.save(self.envelope("mystery")))["terminal"])

    def test_success_with_error_is_unknown(self):
        self.assertEqual("unknown", self.observe(self.save(self.envelope(error={"message": "bad"})))["outcome"])

    def test_busy_thread_does_not_become_idle(self):
        self.assertEqual("busy", self.observe(self.save(self.envelope(state="active")))["worker_state"])

    def test_unknown_thread_state_does_not_become_idle(self):
        self.assertEqual("unknown", self.observe(self.save(self.envelope(state="mystery")))["worker_state"])

    def test_duplicate_replay_one_event(self):
        self.assertEqual(self.observe()["event_key"], self.observe()["event_key"])
        self.assertEqual(1, len(list((self.root/"state/events").glob("*.json"))))

    def test_conflicting_terminal_is_rejected(self):
        self.observe()
        with self.assertRaisesRegex(ValueError, "contradictory"):
            self.observe(self.save(self.envelope("failed")))

    def test_tool_error_is_not_completion(self):
        source = self.envelope()
        source["result"]["isError"] = True
        with self.assertRaisesRegex(ValueError, "tool returned"):
            self.observe(self.save(source))

    def test_wrong_task_rejected(self):
        with self.assertRaises(ValueError):
            self.observer.observe(self.source, "other-task", NOW)

    def test_duplicate_polls_rejected(self):
        source = self.envelope()
        value = json.loads(source["result"]["content"][0]["text"])
        value["polls"] *= 2
        source["result"]["content"][0]["text"] = json.dumps(value)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.observe(self.save(source))

    def test_missing_completed_at_rejected(self):
        source = self.envelope()
        value = json.loads(source["result"]["content"][0]["text"])
        value["polls"][0]["latestTurn"]["completedAt"] = None
        source["result"]["content"][0]["text"] = json.dumps(value)
        with self.assertRaisesRegex(ValueError, "completedAt"):
            self.observe(self.save(source))

    def test_historical_completion_retained_but_stale_current_rejected(self):
        future = (c.utc(NOW)+timedelta(seconds=61)).isoformat()
        event = self.observer.observe(self.source, TASK, future)
        self.assertTrue(event["terminal"])
        with self.assertRaisesRegex(ValueError, "stale"):
            self.observer.deliver(event["event_key"], self.source, future)

    def test_read_history_old_terminal_with_newer_running(self):
        source = self.envelope()
        old = json.loads(source["result"]["content"][0]["text"])["polls"][0]["latestTurn"]
        value = {"schemaVersion": 1, "thread": {"id": TASK, "status": {"type": "active"}},
                 "page": {"order": "newest_first"}, "turns": [
                     {"id": "turn-2", "status": "inProgress"}, old]}
        source.update(tool=c.TOOLS[1], request={"threadId": TASK})
        source["result"]["content"][0]["text"] = json.dumps(value)
        path = self.save(source)
        result = self.observer.observe(path, TASK, NOW, turn_id=TURN)
        self.assertTrue(result["terminal"])
        self.assertEqual("busy", result["worker_state"])
        self.assertEqual("turn-2", result["latest_turn_id"])
        self.assertFalse(c.snapshot(path, TASK, NOW)["terminal"])

    def test_delivery_is_not_acknowledgment(self):
        key, _ = self.delivery()
        result = self.observer.status(key, self.source, NOW)
        self.assertIsNone(result["semantic_ack"])
        self.assertFalse(result["may_offer_next_task"])

    def test_duplicate_delivery_never_resends(self):
        key, _ = self.delivery()
        self.observer.deliver(key, self.source, NOW)
        self.assertEqual(1, self.link.sends)

    def test_reconnect_recovers_send_with_lost_response(self):
        self.link.lose_response = True
        key = self.observe()["event_key"]
        self.assertEqual("uncertain", self.observer.deliver(key, self.source, NOW)["delivery"])
        observer = c.Observer(self.root/"state", self.link)
        self.assertTrue(observer.deliver(key, self.source, NOW)["recovered"])
        self.assertEqual(1, self.link.sends)

    def test_uncertain_intent_without_message_is_not_retried(self):
        key = self.observe()["event_key"]
        self.observer.record("intents", key, {"event_key": key, "after": 0, "body": {}})
        self.assertEqual("uncertain", self.observer.deliver(key, self.source, NOW)["delivery"])
        self.assertEqual(0, self.link.sends)

    def test_broker_unavailable_before_intent_does_not_send(self):
        key = self.observe()["event_key"]
        self.link.unavailable = True
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.observer.deliver(key, self.source, NOW)
        self.assertIsNone(self.observer.get("intents", key))
        self.assertEqual(0, self.link.sends)

    def test_transport_ack_is_not_semantic_acceptance(self):
        key, mid = self.delivery()
        self.link.append(c.COORDINATOR, c.SENDER, "ack", {"id": mid})
        result = self.observer.status(key, self.source, NOW)
        self.assertIsNotNone(result["transport_ack"])
        self.assertIsNone(result["semantic_ack"])
        self.assertFalse(result["may_offer_next_task"])

    def test_semantic_ack_allows_only_fresh_same_successful_turn(self):
        key, mid = self.delivery()
        self.semantic(key, mid)
        self.assertTrue(self.observer.status(key, self.source, NOW)["may_offer_next_task"])

    def test_wrong_turn_semantic_ack_ignored(self):
        key, mid = self.delivery()
        self.semantic(key, mid, turn_id="other-turn")
        self.assertIsNone(self.observer.status(key, self.source, NOW)["semantic_ack"])

    def test_wrong_owner_ack_ignored(self):
        key, mid = self.delivery()
        self.link.append("someone-else", c.SENDER, "codex.completion.ack", {
            "event_key": key, "task_id": TASK, "turn_id": TURN,
            "notification_id": mid, "decision": "received"})
        self.assertIsNone(self.observer.status(key, self.source, NOW)["semantic_ack"])

    def test_newer_active_turn_overrides_previously_acknowledged_idle(self):
        key, mid = self.delivery()
        self.semantic(key, mid)
        source = self.save(self.envelope("inProgress", "active", "turn-2"))
        result = self.observer.status(key, source, NOW)
        self.assertTrue(result["newer_or_different_turn"])
        self.assertFalse(result["may_offer_next_task"])

    def test_failed_turn_needs_operator_even_after_ack(self):
        source = self.save(self.envelope("failed"))
        key, mid = self.delivery()
        self.semantic(key, mid)
        self.assertFalse(self.observer.status(key, source, NOW)["may_offer_next_task"])

    def test_json_duplicate_and_oversize_rejected(self):
        for raw in (b'{"x":1,"x":2}', b" "*(c.MAX_BYTES+1)):
            with self.assertRaises(ValueError):
                c.decode(raw)

    def test_cli_malformed_is_json_nonzero(self):
        source = self.root/"bad.json"
        source.write_text("{")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = c.main(["observe", "--state", str(self.root/"cli"),
                             "--snapshot", str(source), "--task", TASK])
        self.assertEqual(3, result)
        self.assertFalse(json.loads(stderr.getvalue())["assignment_executed"])

    def test_notification_contains_no_tool_prose(self):
        self.delivery()
        body = self.link.messages[0]["body"]
        self.assertNotIn("result", body)
        self.assertNotIn("content", body)
        self.assertFalse(body["parent_push"])


if __name__ == "__main__":
    unittest.main()
