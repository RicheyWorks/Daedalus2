# SPDX-License-Identifier: MIT
"""Focused synthetic protocol/filesystem tests; no Codex, HTTP, UI or workers."""
import copy
from datetime import timedelta
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import codex_completion as c
from asset_pipeline import worker_status as w

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

    def test_powershell_seven_digit_utc_fraction(self):
        self.assertEqual(869441, c.utc("2026-10-16T07:00:46.8694415+00:00").microsecond)

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


class WorkerStatusTest(unittest.TestCase):
    envelope = CompletionTest.envelope
    save = CompletionTest.save

    @classmethod
    def setUpClass(cls):
        cls.checkins = w.checkins_module(os.environ.get("DAEDALUS_CHECKINS_SOURCE"))

    def setUp(self):
        CompletionTest.setUp(self)
        self.assignment = {"id": 10, "from": c.COORDINATOR, "to": "unreal-team", "type": "ping",
                           "body": {"assignment_id": "current-job", "request_id": "request-1"}}
        self.status = w.Status(self.root/"unified", self.checkins, self.link)
        self.status.register(self.assignment, NOW, 90)

    def message(self, mid, kind, **body):
        return {"id": mid, "from": "unreal-team", "to": c.COORDINATOR, "type": kind,
                "body": {"assignment_id": "current-job", "request_id": "request-1",
                         "session_id": "session-1", "reported_at_utc": NOW, **body}}

    def ingest(self, *messages):
        self.status.ingest(list(messages), NOW)
        return self.status.rows(NOW)[0]

    def test_legacy_prose_does_not_become_claude_start(self):
        row = self.ingest(self.message(11, "checkin", text="Done everything"))
        self.assertEqual("unknown", row["status"])
        self.assertFalse(row["semantic_start"])

    def test_reported_completion_without_start_does_not_invent_acceptance(self):
        row = self.ingest(self.message(11, "task.completed"))
        self.assertEqual("finished", row["status"])
        self.assertTrue(row["acceptance_missing"])
        self.assertFalse(row["semantic_start"])
        self.assertEqual("owner-self-report", row["outcome_authority"])
        self.assertFalse(row["may_assign"])

    def test_blocked_without_start_is_actionable(self):
        row = self.ingest(self.message(11, "checkin", status="BLOCKED"))
        self.assertEqual("blocked", row["status"])
        self.assertTrue(row["acceptance_missing"])
        self.assertFalse(row["semantic_start"])
        self.assertEqual(1, len(self.status.queue(NOW)))

    def test_progress_without_start_still_unknown(self):
        self.assertEqual("unknown", self.ingest(self.message(11, "task.progress"))["status"])

    def test_transport_ack_not_semantic_start(self):
        row = self.ingest({"id": 11, "from": "unreal-team", "to": c.COORDINATOR,
                           "type": "ack", "body": {"id": 10}})
        self.assertTrue(row["transport_ack"])
        self.assertEqual("unknown", row["status"])

    def test_qualified_start_is_attributed_working(self):
        row = self.ingest(self.message(11, "task.start"))
        self.assertEqual("working", row["status"])
        self.assertEqual("session-1", row["session_id"])
        self.assertIn("self-report", row["source"])
        self.assertIsNone(row["turn_id"])

    def test_missing_report_time_is_unknown(self):
        row = self.ingest(self.message(11, "task.start", reported_at_utc=None))
        self.assertEqual("unknown", row["status"])
        self.assertEqual("unknown", row["freshness"])

    def test_session_metadata_rejects_prose_and_urls(self):
        with self.assertRaisesRegex(ValueError, "session"):
            self.ingest(self.message(11, "task.start", session_id="https://example.test/private"))

    def test_stale_report_not_refreshed_by_new_observation(self):
        self.ingest(self.message(11, "task.start"))
        later = (c.utc(NOW)+timedelta(seconds=91)).isoformat()
        self.status.ingest([], later)
        self.assertEqual("unknown", self.status.rows(later)[0]["status"])
        self.assertEqual("stale", self.status.rows(later)[0]["freshness"])

    def test_newer_assignment_invalidates_old_completion(self):
        self.ingest(self.message(11, "task.start"), self.message(12, "task.completed"))
        assignment = copy.deepcopy(self.assignment)
        assignment["id"], assignment["body"]["assignment_id"] = 13, "new-job"
        row = self.ingest(assignment)
        self.assertEqual("unknown", row["status"])
        self.assertEqual("newer-assignment", row["reason"])
        self.assertFalse(row["may_assign"])

    def test_foreign_route_does_not_supply_status(self):
        message = self.message(11, "task.start")
        message["from"] = "ultra"
        self.assertFalse(self.ingest(message)["semantic_start"])

    def test_blocked_and_failed_are_actionable(self):
        row = self.ingest(self.message(11, "task.start"), self.message(12, "task.failed"))
        self.assertEqual("blocked", row["status"])
        self.assertEqual(1, len(self.status.queue(NOW)))

    def test_duplicate_completion_restart_has_one_notice(self):
        messages = [self.message(11, "task.start"), self.message(12, "task.completed")]
        self.ingest(*messages)
        self.status.queue(NOW)
        self.status.notify()
        recovered = w.Status(self.root/"unified", self.checkins, self.link)
        recovered.ingest(messages, NOW)
        recovered.queue(NOW)
        self.assertTrue(recovered.notify()[0]["duplicate"])
        self.assertEqual(1, self.link.sends)

    def test_status_semantic_ack_is_distinct_and_correlated(self):
        self.ingest(self.message(11, "task.start"), self.message(12, "task.completed"))
        key = self.status.queue(NOW)[0]
        mid = self.status.notify()[0]["message_id"]
        self.link.append(c.COORDINATOR, c.SENDER, "ack", {"id": mid})
        self.assertIsNone(self.status.acks(key)["semantic_ack"])
        self.link.append(c.COORDINATOR, c.SENDER, "worker.status.ack", {
            "event_key": key, "owner": "unreal-team", "task_id": "current-job", "session_id": "session-1",
            "notification_id": mid, "decision": "received"})
        self.assertIsNotNone(self.status.acks(key)["semantic_ack"])

    def test_status_uncertain_delivery_recovers_without_resend(self):
        self.ingest(self.message(11, "task.start"), self.message(12, "task.completed"))
        self.status.queue(NOW)
        self.link.lose_response = True
        self.assertEqual("uncertain", self.status.notify()[0]["delivery"])
        self.assertTrue(self.status.notify()[0]["recovered"])
        self.assertEqual(1, self.link.sends)

    def test_unchanged_working_has_no_queue_or_notice(self):
        self.ingest(self.message(11, "task.start"))
        self.assertEqual([], self.status.queue(NOW))
        self.assertEqual([], self.status.notify())

    def test_missing_checkpoint_emits_one_decision(self):
        self.ingest(self.message(11, "task.start"))
        later = (c.utc(NOW)+timedelta(seconds=91)).isoformat()
        self.assertEqual(self.status.queue(later), self.status.queue(later))
        # A stale transition and a one-time checkpoint advice may coexist;
        # repeated evaluation must not issue another reminder or send work.
        self.assertTrue(self.status.state["claude"]["reminder_issued"])

    def test_codex_newer_active_not_replaced_by_old_completion(self):
        old = self.save(self.envelope())
        self.status.codex(TASK, old, NOW)
        active = self.envelope("inProgress", "active", "turn-2")
        active["observed_at_utc"] = (c.utc(NOW)+timedelta(seconds=1)).isoformat()
        self.status.codex(TASK, self.save(active, "active.json"), active["observed_at_utc"])
        self.assertFalse(self.status.codex(TASK, old, active["observed_at_utc"]))
        self.assertEqual("working", self.status.rows(active["observed_at_utc"])[1]["status"])

    def test_stale_codex_never_means_idle(self):
        self.status.codex(TASK, self.source, NOW)
        later = (c.utc(NOW)+timedelta(seconds=61)).isoformat()
        self.assertEqual("unknown", self.status.rows(later)[1]["status"])

    def test_future_report_does_not_publish_state(self):
        before = c.read(self.status.path)[0]
        future = (c.utc(NOW)+timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "future"):
            self.ingest(self.message(11, "task.start", reported_at_utc=future))
        self.assertEqual(before, c.read(self.status.path)[0])

    def test_disconnected_never_claims_finished(self):
        self.ingest(self.message(11, "task.start"), self.message(12, "task.completed"))
        self.status.state["connected"] = False
        self.assertEqual("unknown", self.status.rows(NOW)[0]["status"])

    def test_wrong_dependency_pin_fails_closed(self):
        path = self.root/"wrong.py"
        path.write_text("raise RuntimeError('must not execute')")
        with self.assertRaisesRegex(ValueError, "dependency"):
            w.checkins_module(path)

    def test_reobserved_same_codex_completion_does_not_notify_twice(self):
        self.status.codex(TASK, self.source, NOW)
        before = self.status.queue(NOW)
        newer = self.envelope()
        later = (c.utc(NOW)+timedelta(seconds=1)).isoformat()
        newer["observed_at_utc"] = later
        self.status.codex(TASK, self.save(newer), later)
        self.assertEqual(before, self.status.queue(later))

    def test_bounded_listener_catches_final_wake_without_auto_ack(self):
        link = FakeLink()
        link.up = True
        link.messages = [self.message(11, "task.start")]
        def wait(after, timeout):
            link.messages.append(self.message(12, "task.completed"))
            return [link.messages[-1]], 12
        link.wait = wait
        result = self.status.listen(link, seconds=.01, max_waits=1)
        self.assertEqual(1, result["waits"])
        self.assertEqual("completed", self.status.state["claude"]["stage"])
        self.assertEqual(0, link.sends)
        self.assertFalse(result["automatic_collector"])

    def test_bounded_listener_disconnect_queues_unknown_once(self):
        link = FakeLink()
        link.up = False
        link.unavailable = True
        with patch.object(w.time, "sleep"):
            self.status.listen(link, seconds=.01, max_waits=2)
        self.assertFalse(self.status.state["connected"])
        rows = self.status.rows(NOW)
        self.assertEqual("unknown", rows[0]["status"])
        self.assertEqual("disconnected", rows[0]["reason"])
        self.assertEqual(1, len(self.status.state["queued"]))

    def test_listener_does_not_skip_cross_route_new_assignment(self):
        link = FakeLink()
        link.up = True
        link.messages = [self.message(11, "task.start")]
        replacement = copy.deepcopy(self.assignment)
        replacement["id"], replacement["body"]["assignment_id"] = 12, "next-job"
        link.messages.append(replacement)
        link.wait = lambda after, timeout: ([], 12)
        self.status.listen(link, seconds=.01, max_waits=1)
        self.assertEqual(12, self.status.state["claude"]["superseded_by"])
        self.assertEqual(12, self.status.state["cursor"])

    def test_invalid_listener_limits_fail_before_wait(self):
        with self.assertRaisesRegex(ValueError, "bounded"):
            self.status.listen(self.link, seconds=w.MAX_SECONDS+1)

    def test_follow_tracks_only_actual_coordinator_assignment_without_dispatch(self):
        self.status.follow_assignments = True
        replacement = copy.deepcopy(self.assignment)
        replacement["id"], replacement["body"]["assignment_id"] = 12, "next-job"
        report = self.message(13, "task.blocked", assignment_id="next-job")
        self.status.ingest([self.message(11, "task.completed"), replacement, report], NOW)
        row = self.status.rows(NOW)[0]
        self.assertEqual("next-job", row["task_id"])
        self.assertEqual("blocked", row["status"])
        self.assertTrue(row["acceptance_missing"])
        self.assertEqual(1, len(list((self.root/"unified/notices/assignment_history").glob("*.json"))))
        self.assertEqual(0, self.link.sends)
        # Original retained bootstrap assignment remains valid across restart.
        recovered = w.Status(self.root/"unified", self.checkins, self.link, True)
        recovered.register(self.assignment, NOW)
        recovered.ingest([replacement, report], NOW)
        self.assertEqual("next-job", recovered.rows(NOW)[0]["task_id"])

    def test_follow_does_not_adopt_worker_self_assignment_or_alias(self):
        self.status.follow_assignments = True
        replacement = copy.deepcopy(self.assignment)
        replacement["id"], replacement["body"]["assignment_id"] = 12, "next-job"
        replacement["from"] = "unreal-team"
        self.ingest(replacement)
        replacement["id"], replacement["from"], replacement["to"] = 13, c.COORDINATOR, "claude"
        self.ingest(replacement)
        self.assertEqual("current-job", self.status.rows(NOW)[0]["task_id"])

    def test_bounded_eight_hour_option_exercises_same_finite_loop(self):
        link = FakeLink()
        link.up = True
        link.wait = lambda after, timeout: ([], after)
        self.assertEqual(1, self.status.listen(link, seconds=w.MAX_SECONDS, max_waits=1)["waits"])




class FanoutTest(unittest.TestCase):
    """Synthetic multi-owner boundaries; no broker, worker or supported-tool calls."""

    OWNERS = ("buckwild-sol", "buckwild-claude", "buckwild-luna")
    SELF_REPORT = "structured-owner-self-report-not-session-terminal-api"
    TOOL_REPORT = "supported-tool-caller-supplied"

    @classmethod
    def setUpClass(cls):
        cls.checkins = w.checkins_module(os.environ.get("DAEDALUS_CHECKINS_SOURCE"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.link = FakeLink()
        self.now = (c.utc(w.instant()) - timedelta(seconds=10)).isoformat()
        self.config = {
            "schema": "daedalus.worker-status-profiles.v1",
            "coordinator": c.COORDINATOR,
            "profiles": [self.profile(owner, i) for i, owner in enumerate(self.OWNERS)],
        }

    def at(self, seconds):
        return (c.utc(self.now) + timedelta(seconds=seconds)).isoformat()

    def profile(self, owner, index=0, provider=None):
        return {
            "owner": owner,
            "provider": provider or ("claude" if index == 1 else "codex"),
            "assignment": {
                "id": 10 + index, "from": c.COORDINATOR, "to": owner, "type": "ping",
                "body": {"assignment_id": "shared-job", "request_id": "request." + owner},
            },
            "start_deadline": self.at(60),
            "checkpoint_seconds": 90,
            "follow_assignments": False,
            "notify": True,
        }

    def fanout(self, config=None, name="fanout", notifier=True):
        return w.Fanout(self.root / name, self.checkins,
                        copy.deepcopy(self.config if config is None else config),
                        self.link if notifier else None)

    def report(self, owner, mid, kind, **body):
        return {
            "id": mid, "from": owner, "to": c.COORDINATOR, "type": kind,
            "body": {"assignment_id": "shared-job", "request_id": "request." + owner,
                     "session_id": "session." + owner, "reported_at_utc": self.now, **body},
        }

    def row(self, fanout, owner, now=None, source=None):
        matches = [row for row in fanout.rows(now or self.now)
                   if row["owner"] == owner and row["source"] == (source or self.SELF_REPORT)]
        self.assertEqual(1, len(matches))
        return matches[0]

    def notices(self):
        return [message for message in self.link.messages
                if message["type"] == "worker.status.actionable"]

    def body(self, fanout, key):
        found = [child.observer.get("queue", key) for child in fanout.profiles.values()]
        found = [value for value in found if value is not None]
        self.assertEqual(1, len(found))
        return found[0]

    def tool(self, name="tool.json", status="completed", state="idle", turn=TURN,
             task=TASK, observed=None):
        observed = observed or self.now
        data = {"schemaVersion": 1, "thread": {"id": task, "status": {"type": state}},
                "latestTurn": {"id": turn, "status": status, "error": None,
                               "completedAt": c.utc(observed).timestamp() - 1
                               if status in c.TERMINAL else None}}
        value = {
            "schema": c.SCHEMA, "tool": c.TOOLS[0],
            "request": {"targets": [{"threadId": task}], "timeoutMs": 0},
            "observed_at_utc": observed,
            "result": {"isError": False, "content": [{"type": "text",
                                                       "text": json.dumps({"polls": [data]})}]},
        }
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_simultaneous_owners_keep_shared_assignment_ids_separate(self):
        fanout = self.fanout()
        a, b, d = self.OWNERS
        fanout.ingest([self.report(a, 100, "task.start"),
                       self.report(b, 101, "task.blocked"),
                       self.report(d, 102, "task.completed")], self.now)
        rows = [self.row(fanout, owner) for owner in self.OWNERS]
        self.assertEqual(["working", "blocked", "finished"], [row["status"] for row in rows])
        self.assertEqual(3, len({row["profile_id"] for row in rows}))
        self.assertTrue(all(row["assignment_id"] == "shared-job" for row in rows))
        self.assertTrue(rows[1]["acceptance_missing"])
        self.assertTrue(rows[2]["acceptance_missing"])
        self.assertFalse(rows[2]["semantic_start"])
        self.assertTrue(all(row["outcome_authority"] == "owner-self-report" for row in rows))
        self.assertTrue(all(row["may_assign"] is False for row in rows))
        keys = fanout.queue(self.now)
        self.assertEqual(2, len(keys))
        self.assertEqual({b, d}, {self.body(fanout, key)["owner"] for key in keys})
        fanout.notify(self.now)
        self.assertEqual(2, self.link.sends)

    def test_deadline_advice_is_per_owner_and_only_issued_once(self):
        config = copy.deepcopy(self.config)
        config["profiles"] = config["profiles"][:2]
        config["profiles"][0]["start_deadline"] = self.at(-1)
        config["profiles"][1]["start_deadline"] = self.at(300)
        fanout = self.fanout(config)
        fanout.ingest([], self.now)
        first = fanout.queue(self.now)
        self.assertTrue(fanout.profiles[self.OWNERS[0]].state["claude"]["reminder_issued"])
        self.assertFalse(fanout.profiles[self.OWNERS[1]].state["claude"]["reminder_issued"])
        self.assertTrue(first)
        self.assertEqual({self.OWNERS[0]}, {self.body(fanout, key)["owner"] for key in first})
        self.assertEqual(first, fanout.queue(self.now))
        self.assertEqual(0, self.link.sends)

    def test_wrong_routes_exact_replay_and_conflicting_replay(self):
        fanout = self.fanout()
        owner = self.OWNERS[0]
        wrong_sender = self.report(owner, 100, "task.completed")
        wrong_sender["from"] = "unconfigured-owner"
        wrong_receiver = self.report(owner, 101, "task.completed")
        wrong_receiver["to"] = "unconfigured-coordinator"
        wrong_assignment = self.report(owner, 102, "task.completed", assignment_id="other-job")
        wrong_assignment["reply_to"] = self.config["profiles"][0]["assignment"]["id"]
        wrong_request = self.report(owner, 103, "task.completed", request_id="other-request")
        wrong_request["reply_to"] = self.config["profiles"][0]["assignment"]["id"]
        fanout.ingest([wrong_sender, wrong_receiver, wrong_assignment, wrong_request], self.now)
        self.assertTrue(all(row["status"] == "unknown" for row in fanout.rows(self.now)))
        start = self.report(owner, 104, "task.start")
        fanout.ingest([start], self.now)
        fanout.ingest([copy.deepcopy(start)], self.now)
        self.assertEqual("working", self.row(fanout, owner)["status"])
        changed = copy.deepcopy(start)
        changed["type"] = "task.completed"
        with self.assertRaises(ValueError):
            fanout.ingest([changed], self.now)
        conflicting_assignment = copy.deepcopy(self.config["profiles"][0]["assignment"])
        conflicting_assignment["id"] = 200
        conflicting_assignment["body"]["request_id"] = "conflicting-request"
        with self.assertRaises(ValueError):
            fanout.ingest([self.report(self.OWNERS[1], 201, "task.start"),
                           conflicting_assignment], self.now)
        self.assertEqual("unknown", self.row(fanout, self.OWNERS[1])["status"])
        self.assertEqual(0, self.link.sends)

    def test_owner_two_cannot_ack_owner_one_and_all_fields_are_correlated(self):
        fanout = self.fanout()
        fanout.ingest([self.report(owner, 100 + i, "task.completed")
                       for i, owner in enumerate(self.OWNERS[:2])], self.now)
        fanout.queue(self.now)
        fanout.notify(self.now)
        notices = {message["body"]["owner"]: message for message in self.notices()}
        first, second = (notices[owner] for owner in self.OWNERS[:2])
        key, mid = first["body"]["event_key"], first["id"]
        fields = ("profile_id", "provider", "owner", "assignment_id",
                  "task_id", "session_id", "turn_id", "source")
        correct = {field: first["body"][field] for field in fields}
        correct.update(event_key=key, notification_id=mid, decision="received")
        foreign = {field: second["body"][field] for field in fields}
        foreign.update(event_key=key, notification_id=mid, decision="received")
        self.link.append(c.COORDINATOR, c.SENDER, "worker.status.ack", foreign)
        self.assertIsNone(fanout.acks(key)["semantic_ack"])
        for field in fields:
            with self.subTest(field=field):
                wrong = dict(correct, **{field: "wrong-" + field})
                self.link.append(c.COORDINATOR, c.SENDER, "worker.status.ack", wrong)
                self.assertIsNone(fanout.acks(key)["semantic_ack"])
        for field in fields:
            if correct[field] is None:
                with self.subTest(missing_null_field=field):
                    omitted = dict(correct)
                    del omitted[field]
                    self.link.append(c.COORDINATOR, c.SENDER, "worker.status.ack", omitted)
                    self.assertIsNone(fanout.acks(key)["semantic_ack"])
        self.link.append(c.COORDINATOR, c.SENDER, "ack", {"id": mid})
        self.assertIsNone(fanout.acks(key)["semantic_ack"])
        self.link.append(c.COORDINATOR, c.SENDER, "worker.status.ack", correct)
        self.assertIsNotNone(fanout.acks(key)["semantic_ack"])
        self.assertTrue(all(row["may_assign"] is False for row in fanout.rows(self.now)))

    def test_restart_deduplicates_each_owner_notice(self):
        fanout = self.fanout()
        reports = [self.report(owner, 100 + i, "task.completed")
                   for i, owner in enumerate(self.OWNERS[:2])]
        fanout.ingest(reports, self.now)
        keys = fanout.queue(self.now)
        fanout.notify(self.now)
        restarted = self.fanout()
        restarted.ingest(reports, self.now)
        self.assertEqual(keys, restarted.queue(self.now))
        results = restarted.notify(self.now)
        self.assertTrue(results)
        self.assertTrue(all(result.get("duplicate") for result in results))
        self.assertEqual(2, self.link.sends)

    def test_profile_and_global_notification_opt_ins_are_both_required(self):
        config = copy.deepcopy(self.config)
        for profile in config["profiles"]:
            profile["notify"] = False
        disabled = self.fanout(config, name="profile-disabled")
        disabled.ingest([self.report(self.OWNERS[0], 100, "task.blocked")], self.now)
        disabled.queue(self.now)
        disabled.notify(self.now)
        offline = self.fanout(name="no-notifier", notifier=False)
        offline.ingest([self.report(self.OWNERS[0], 100, "task.blocked")], self.now)
        offline.queue(self.now)
        offline.notify(self.now)
        self.assertEqual(0, self.link.sends)
        for fanout in (disabled, offline):
            for key in fanout.state["queued"]:
                self.assertTrue(all(child.observer.get("intents", key) is None
                                    for child in fanout.profiles.values()))

    def test_prose_and_stale_reports_remain_unknown(self):
        fanout = self.fanout()
        a, b = self.OWNERS[:2]
        fanout.ingest([self.report(a, 100, "checkin", text="Done, ready for more work"),
                       self.report(b, 101, "task.start")], self.now)
        self.assertEqual("unknown", self.row(fanout, a)["status"])
        self.assertEqual("working", self.row(fanout, b)["status"])
        late = self.at(91)
        row = self.row(fanout, b, late)
        self.assertEqual("unknown", row["status"])
        self.assertEqual("stale", row["freshness"])
        self.assertFalse(row["may_assign"])

    def test_newer_supported_tool_turn_holds_previous_completion_notice(self):
        config = copy.deepcopy(self.config)
        path = self.tool()
        owner = self.OWNERS[0]
        config["profiles"][0]["codex"] = {"task_id": TASK, "snapshot": str(path)}
        fanout = self.fanout(config)
        fanout.ingest([], self.now)
        fanout.codex(owner, now=self.now)
        keys = fanout.queue(self.now)
        completed = [key for key in keys if self.body(fanout, key)["source"] == self.TOOL_REPORT]
        self.assertEqual(1, len(completed))
        later = self.at(1)
        self.tool(status="inProgress", state="active", turn="turn-2", observed=later)
        fanout.codex(owner, now=later)
        self.assertEqual("working", self.row(fanout, owner, later, self.TOOL_REPORT)["status"])
        fanout.notify(later)
        self.assertFalse(any(message["body"]["event_key"] in completed for message in self.notices()))

    def test_stale_owner_completion_is_not_sent_from_old_queue(self):
        fanout = self.fanout()
        owner = self.OWNERS[0]
        fanout.ingest([self.report(owner, 100, "task.completed")], self.now)
        keys = fanout.queue(self.now)
        self.assertEqual(1, len(keys))
        fanout.notify(self.at(91))
        self.assertFalse(any(message["body"]["event_key"] == keys[0] for message in self.notices()))
        self.assertEqual("unknown", self.row(fanout, owner, self.at(91))["status"])

    def test_new_assignment_holds_queued_previous_owner_completion(self):
        config = copy.deepcopy(self.config)
        owner = self.OWNERS[0]
        config["profiles"][0]["codex"] = {"task_id": TASK, "snapshot": str(self.tool())}
        fanout = self.fanout(config)
        fanout.ingest([self.report(owner, 100, "task.completed")], self.now)
        fanout.codex(owner, now=self.now)
        keys = fanout.queue(self.now)
        self.assertTrue(any(self.body(fanout, key)["source"] == self.TOOL_REPORT for key in keys))
        assignment = copy.deepcopy(config["profiles"][0]["assignment"])
        assignment["id"], assignment["body"]["assignment_id"] = 200, "new-job"
        fanout.ingest([assignment], self.now)
        self.assertEqual("newer-assignment", self.row(fanout, owner)["reason"])
        with patch.object(c, "snapshot", side_effect=AssertionError("superseded source must not be read")):
            self.assertFalse(fanout.codex(owner, now=self.now))
        self.assertFalse(any(row["source"] == self.TOOL_REPORT and row["status"] == "finished"
                             for row in fanout.rows(self.now)))
        fanout.notify(self.now)
        self.assertFalse(any(message["body"]["event_key"] in keys for message in self.notices()))

    def test_uncertain_delivery_is_recovered_after_restart_without_resend(self):
        fanout = self.fanout()
        fanout.ingest([self.report(self.OWNERS[0], 100, "task.completed")], self.now)
        fanout.queue(self.now)
        self.link.lose_response = True
        first = fanout.notify(self.now)
        self.assertEqual("uncertain", first[0]["delivery"])
        restarted = self.fanout()
        recovered = restarted.notify(self.now)
        self.assertTrue(recovered[0]["recovered"])
        self.assertEqual(1, self.link.sends)

    def test_unmatched_uncertain_intent_is_only_reconciled_even_when_stale(self):
        fanout = self.fanout()
        owner = self.OWNERS[0]
        fanout.ingest([self.report(owner, 100, "task.completed")], self.now)
        key = fanout.queue(self.now)[0]
        body = self.body(fanout, key)
        fanout.profiles[owner].observer.record(
            "intents", key, {"event_key": key, "after": 0, "body": body,
                            "kind": "worker.status.actionable"})
        results = fanout.notify(self.at(91))
        self.assertEqual("uncertain", results[0]["delivery"])
        self.assertFalse(results[0]["automatic_retry"])
        self.assertEqual(0, self.link.sends)

    def test_invalid_profile_sets_and_changed_config_fail_closed(self):
        cases = []
        empty = copy.deepcopy(self.config)
        empty["profiles"] = []
        cases.append(empty)
        too_many = copy.deepcopy(self.config)
        too_many["profiles"] = [self.profile("worker-%d" % i, i) for i in range(33)]
        cases.append(too_many)
        duplicate = copy.deepcopy(self.config)
        duplicate["profiles"][1]["owner"] = duplicate["profiles"][0]["owner"]
        duplicate["profiles"][1]["assignment"]["to"] = duplicate["profiles"][0]["owner"]
        cases.append(duplicate)
        wrong_route = copy.deepcopy(self.config)
        wrong_route["profiles"][0]["assignment"]["to"] = "another-owner"
        cases.append(wrong_route)
        for flag in ("notify", "follow_assignments"):
            malformed = copy.deepcopy(self.config)
            malformed["profiles"][0][flag] = "false"
            cases.append(malformed)
            missing = copy.deepcopy(self.config)
            del missing["profiles"][0][flag]
            cases.append(missing)
        for index, config in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(ValueError):
                self.fanout(config, name="invalid-%d" % index)
        maximum = copy.deepcopy(too_many)
        maximum["profiles"] = maximum["profiles"][:32]
        self.assertEqual(32, len(self.fanout(maximum, name="max32").profiles))
        self.fanout(name="pinned")
        changed = copy.deepcopy(self.config)
        changed["profiles"][0]["start_deadline"] = self.at(120)
        with self.assertRaises(ValueError):
            self.fanout(changed, name="pinned")
        self.assertEqual(3, len(self.fanout(name="pinned").profiles))
        self.assertEqual(0, self.link.sends)

    def test_supported_tool_requires_explicit_task_and_exact_snapshot_binding(self):
        owner = self.OWNERS[0]
        path = self.tool()
        unbound = self.fanout(name="unbound")
        with self.assertRaises(ValueError):
            unbound.codex(owner, path, self.now)
        config = copy.deepcopy(self.config)
        config["profiles"][0]["codex"] = {"task_id": TASK, "snapshot": str(path)}
        fanout = self.fanout(config, name="bound")
        fanout.ingest([], self.now)
        self.assertTrue(fanout.codex(owner, now=self.now))
        report = self.row(fanout, owner)
        tool = self.row(fanout, owner, source=self.TOOL_REPORT)
        self.assertEqual("unknown", report["status"])
        self.assertEqual("owner-self-report", report["outcome_authority"])
        self.assertEqual("shared-job", report["task_id"])
        self.assertEqual(TASK, tool["task_id"])
        self.assertEqual("supported-tool-observation", tool["outcome_authority"])
        self.assertFalse(tool["may_assign"])
        alternate = self.tool(name="unconfigured-snapshot.json")
        with self.assertRaises(ValueError):
            fanout.codex(owner, alternate, self.now)
        self.tool(task="unconfigured-task")
        with self.assertRaises(ValueError):
            fanout.codex(owner, now=self.now)

    def test_follow_assignment_is_limited_to_its_configured_owner(self):
        config = copy.deepcopy(self.config)
        config["profiles"][0]["follow_assignments"] = True
        config["profiles"][0]["codex"] = {"task_id": TASK, "snapshot": str(self.tool())}
        fanout = self.fanout(config)
        a, b = self.OWNERS[:2]
        fanout.ingest([self.report(a, 100, "task.completed"),
                       self.report(b, 101, "task.completed")], self.now)
        fanout.codex(a, now=self.now)
        self.assertEqual("finished", self.row(fanout, a, source=self.TOOL_REPORT)["status"])
        previous = fanout.queue(self.now)
        assignment = copy.deepcopy(config["profiles"][0]["assignment"])
        assignment["id"], assignment["body"]["assignment_id"] = 200, "next-job"
        fanout.ingest([assignment, self.report(a, 201, "task.blocked",
                                              assignment_id="next-job")], self.now)
        self.assertEqual("next-job", self.row(fanout, a)["assignment_id"])
        self.assertEqual("blocked", self.row(fanout, a)["status"])
        self.assertEqual("shared-job", self.row(fanout, b)["assignment_id"])
        self.assertEqual("finished", self.row(fanout, b)["status"])
        with patch.object(c, "snapshot", side_effect=AssertionError("superseded source must not be read")):
            self.assertFalse(fanout.codex(a, now=self.now))
        self.assertFalse(any(row["owner"] == a and row["source"] == self.TOOL_REPORT
                             and row["status"] == "finished" for row in fanout.rows(self.now)))
        fanout.queue(self.now)
        fanout.notify(self.now)
        self.assertFalse(any(message["body"]["owner"] == a
                             and message["body"]["event_key"] in previous for message in self.notices()))
        self.assertTrue(all(message["to"] == c.COORDINATOR for message in self.notices()))
        self.assertTrue(all(row["may_assign"] is False for row in fanout.rows(self.now)))

    def test_legacy_assignment_cli_remains_supported_without_profiles(self):
        assignment = self.root / "assignment.json"
        assignment.write_text(json.dumps(self.config["profiles"][0]["assignment"]), encoding="utf-8")
        snapshot = self.root / "hub.json"
        snapshot.write_text(json.dumps({
            "observed_at_utc": self.now,
            "messages": [self.report(self.OWNERS[0], 100, "task.start")],
        }), encoding="utf-8")
        args = ["--state", str(self.root / "legacy"), "--assignment", str(assignment),
                "--start-deadline", self.at(60), "--snapshot", str(snapshot)]
        external = os.environ.get("DAEDALUS_CHECKINS_SOURCE")
        if external:
            args.extend(["--checkins-module", external])
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = w.main(args)
        self.assertEqual(0, result, stderr.getvalue())
        self.assertEqual("working", json.loads(stdout.getvalue())["rows"][0]["status"])
        self.assertEqual(0, self.link.sends)


if __name__ == "__main__":
    unittest.main()
