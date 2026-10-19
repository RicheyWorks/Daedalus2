# SPDX-License-Identifier: MIT
"""Durable parent outbox; an authorized external supported-tool caller owns I/O.

Composes codex_completion's parser and create-new records. No MCP client,
background collector, broker, credentials, assignment or automatic resend.
"""
import hashlib
import json
from datetime import datetime, timezone

from asset_pipeline import codex_completion as c


SEND_TOOL = "mcp__codex_app__send_message_to_thread"
CALL_SCHEMA = "daedalus.parent-tool-result.v1"
ACK_SCHEMA = "daedalus.parent-worker-ack.v1"
EVENT_TYPES = ("working", "completed", "idle", "blocked")


def _key(parts):
    return hashlib.sha256(json.dumps(parts, separators=(",", ":")).encode()).hexdigest()


def _instant():
    return datetime.now(timezone.utc).isoformat()


def _matches(view, kind):
    same = view["turn_id"] == view["latest_turn_id"] and view["turn_id"] is not None
    if kind == "working":
        return same and view["worker_state"] == "busy" and not view["terminal"]
    if kind in ("completed", "idle"):
        return same and view["terminal"] and view["outcome"] == "succeeded" and view["worker_state"] == "idle"
    return same and view["terminal"] and view["outcome"] in ("failed", "cancelled") and view["worker_state"] != "busy"


class ParentRelay:
    """Use a dedicated state folder, never another observer's running state."""

    def __init__(self, folder, authorized_parent_thread_id):
        self.parent = c.identity(authorized_parent_thread_id)
        self.records = c.Observer(folder)  # No Link: relay cannot send anything.

    def event(self, key):
        event = self.records.get("parent-pending", key)
        c.need(isinstance(event, dict) and event.get("event_key") == key
               and event.get("parent_thread_id") == self.parent, "missing/conflicting parent event")
        c.need(_key([self.parent, event["task_id"], event["turn_id"], event["event_type"]]) == key,
               "corrupt parent event identity")
        return event

    def capture(self, source, task_id, event_type, now=None):
        c.need(event_type in EVENT_TYPES, "unsupported semantic event type")
        c.need(task_id != self.parent, "parent cannot be observed as its own worker")
        view = c.snapshot(source, task_id, now, fresh=False)
        c.need(_matches(view, event_type), "source does not establish requested semantic state")
        if view["terminal"]:
            terminal_key = _key([self.parent, task_id, view["turn_id"]])
            self.records.record("parent-terminal-facts", terminal_key,
                                {"status": view["status"], "outcome": view["outcome"]})
        key = _key([self.parent, task_id, view["turn_id"], event_type])
        previous = self.records.get("parent-pending", key)
        if previous is None:
            self.records.record("parent-pending", key, {
                "schema": "daedalus.parent-pending.v1", "event_key": key,
                "parent_thread_id": self.parent, "event_type": event_type,
                **view, "automatic_assignment": False})
        else:
            c.need(previous["outcome"] == view["outcome"] and previous["status"] == view["status"],
                   "contradictory source event")
        return self.status(key)

    def notice(self, key):
        event = self.event(key)
        # IDs, states and hashes only; never relay transcripts or task prose.
        return {"schema": "daedalus.parent-worker-notice.v1", "event_key": key,
                **{field: event[field] for field in (
                    "parent_thread_id", "task_id", "turn_id", "event_type", "status",
                    "terminal", "outcome", "source_tool", "source_sha256", "observed_at_utc")},
                "automatic_assignment": False, "ack_schema": ACK_SCHEMA}

    def status(self, key):
        self.event(key)
        denied = self.records.get("parent-denied", key)
        accepted = self.records.get("parent-send-accepted", key)
        ack = self.records.get("parent-ack", key)
        intent = self.records.get("parent-intents", key)
        delivery = "denied" if denied else "send-accepted" if accepted else "uncertain" if intent else "pending"
        return {"event_key": key, "captured": True, "delivery": delivery,
                "send_accepted": accepted is not None and denied is None, "parent_acknowledged": ack is not None,
                "parent_pending": ack is None, "denial": denied, "acceptance": accepted,
                "parent_ack": ack, "automatic_retry": False, "automatic_assignment": False,
                "background_service": False}

    def prepare(self, key, current, *, send_tool_available=False, now=None):
        """Return one exact supported-tool request after durable exclusive intent.

        External harness: prepare -> call the actual MCP tool -> retain its exact
        request/result -> record_result. A crash at any point leaves uncertainty,
        never permission to automatically call again. Missing capability creates
        no intent, so reconnect with fresh evidence may prepare the first attempt.
        """
        c.need(type(send_tool_available) is bool, "explicit capability bool required")
        event = self.event(key)
        state = self.status(key)
        if state["delivery"] != "pending" or state["parent_acknowledged"]:
            return dict(state, request=None, reason="retained-decision-no-resend")
        if not send_tool_available:
            return dict(state, request=None, reason="supported-send-tool-unavailable")
        try:
            view = c.snapshot(current, event["task_id"], now)
        except (ValueError, OSError, TypeError, KeyError, OverflowError):
            return dict(state, request=None, reason="current-observation-rejected")
        if view["turn_id"] != event["turn_id"] or not _matches(view, event["event_type"]):
            return dict(state, request=None, reason="superseded-or-state-changed")
        request = {"threadId": self.parent,
                   "prompt": json.dumps(self.notice(key), sort_keys=True, separators=(",", ":"))}
        intent = {"event_key": key, "tool": SEND_TOOL, "request": request,
                  "prepared_at_utc": now or _instant(), "current_source_sha256": view["source_sha256"]}
        try:
            c.write_once(self.records.path("parent-intents", key), intent)
        except FileExistsError:
            return dict(self.status(key), request=None, reason="exclusive-intent-already-retained")
        return dict(self.status(key), request=request, tool=SEND_TOOL, reason="one-authorized-external-call-prepared")

    def record_result(self, key, result_source, *, qualify_send=None, now=None):
        """Retain exact tool envelope. Positive send acceptance needs an adapter.

        qualify_send(payload, exact_target) returns a bounded receipt identifier
        only after verifying the ACTUAL supported tool's response contract.
        No positive result schema is invented here. Unknown/error results remain
        uncertain. Known automatic-review rejection is DENIED regardless of any
        injected qualifier; no retry/reset operation is provided.
        """
        self.event(key)
        intent = self.records.get("parent-intents", key)
        c.need(intent is not None, "no prepared send intent")
        envelope, digest = c.read(result_source)
        c.need(isinstance(envelope, dict) and envelope.get("schema") == CALL_SCHEMA
               and envelope.get("tool") == SEND_TOOL and envelope.get("request") == intent["request"],
               "tool result/request does not match the exact prepared request")
        observed = c.utc(envelope.get("observed_at_utc"))
        c.need(c.utc(intent["prepared_at_utc"]) <= observed <= c.utc(now or _instant()),
               "tool result timestamp outside intent/current time")
        evidence_key = _key([key, digest])
        self.records.record("parent-tool-results", evidence_key, envelope)
        result = envelope.get("result")
        blocks = result.get("content", []) if isinstance(result, dict) else []
        blocks = blocks if isinstance(blocks, list) else []
        rejection = next((b["text"] for b in blocks if isinstance(b, dict)
                          and b.get("type") == "text"
                          and isinstance(b.get("text"), str)
                          and "This action was rejected due to unacceptable risk." in b["text"]
                          and "Do not bypass" in b["text"]), None)
        if isinstance(result, dict) and result.get("isError") is True and rejection:
            if self.records.get("parent-denied", key) is None:
                self.records.record("parent-denied", key, {"event_key": key, "evidence_sha256": digest,
                                    "reason": rejection, "material_new_authorization_required": True})
            return self.status(key)
        if self.records.get("parent-denied", key):
            return self.status(key)  # Later evidence cannot override an authorization denial.
        reference = None
        try:
            payload = c.payload(result)
            if qualify_send is not None:
                reference = qualify_send(payload, self.parent)
            c.need(isinstance(reference, str) and 0 < len(reference) <= 128
                   and all(32 <= ord(ch) < 127 for ch in reference), "no qualified send acceptance")
        except (ValueError, TypeError, KeyError, OSError, OverflowError):
            return self.status(key)
        previous = self.records.get("parent-send-accepted", key)
        if previous is None:
            self.records.record("parent-send-accepted", key, {"event_key": key,
                                "tool_receipt_id": reference, "evidence_sha256": digest})
        else:
            c.need(previous["tool_receipt_id"] == reference, "contradictory send receipts; reconcile")
        return self.status(key)

    def record_parent_ack(self, key, read_source, ack_turn_id, now=None):
        """Only a correlated semantic ACK in an actual parent read proves receipt.

        Accepted transport or platform automatic task return is not this ACK.
        An ACK may reconcile receipt after an uncertain response or separately
        authorized manual delivery; it never changes the original send outcome.
        """
        event = self.event(key)
        view = c.snapshot(read_source, self.parent, now, selected_turn=ack_turn_id, fresh=False)
        c.need(view["terminal"] and view["outcome"] == "succeeded", "parent ACK turn not successful terminal")
        document, digest = c.read(read_source)
        c.need(digest == view["source_sha256"], "parent ACK evidence changed during validation")
        c.need(document["tool"] == c.TOOLS[1], "parent read_thread evidence required")
        data = c.payload(document["result"])
        turn = next(t for t in data["turns"] if t["id"] == ack_turn_id)
        expected = {"schema": ACK_SCHEMA, "event_key": key, "parent_thread_id": self.parent,
                    "task_id": event["task_id"], "turn_id": event["turn_id"], "decision": "received"}
        matched = False
        for item in turn.get("items", []):
            if not isinstance(item, dict) or item.get("type") != "agentMessage" or item.get("phase") != "final":
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            try:
                matched = c.decode(text.encode("utf-8")) == expected
            except (ValueError, UnicodeError):
                continue
            if matched:
                break
        c.need(matched, "no exact correlated semantic parent ACK")
        c.need(c.utc(document["observed_at_utc"]) >= c.utc(event["observed_at_utc"]),
               "parent ACK observation predates captured source")
        previous = self.records.get("parent-ack", key)
        if previous is None:
            self.records.record("parent-ack", key, {"event_key": key, "parent_thread_id": self.parent,
                                "ack_turn_id": ack_turn_id, "source_sha256": digest})
        return self.status(key)
