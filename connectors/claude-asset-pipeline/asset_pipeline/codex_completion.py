# SPDX-License-Identifier: MIT
"""Observe supported Codex tool results; notify TeamLink without dispatching work.

The caller supplies retained read_thread/wait_threads results. This module cannot
call Codex MCP tools, collect desktop events, or wake a parent/worker itself.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from .teamlink import Link

SCHEMA = "daedalus.codex-tool-observation.v1"
COORDINATOR = "pootscoot-coordination"
SENDER = "codex-completion-observer"
MAX_BYTES = 1 << 20
MAX_AGE = 60
TOOLS = ("mcp__codex_app__wait_threads", "mcp__codex_app__read_thread")
TERMINAL = {"completed": "succeeded", "failed": "failed", "interrupted": "cancelled"}
IDENT = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def identity(value):
    need(isinstance(value, str) and IDENT.fullmatch(value), "invalid task/turn identity")
    return value


def utc(value):
    need(isinstance(value, str) and len(value) <= 40
         and value.endswith(("Z", "+00:00")), "explicit UTC required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(result.utcoffset().total_seconds() == 0, "UTC required")
    return result


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    need(len(raw) <= MAX_BYTES, "JSON exceeds 1 MiB")
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read(path):
    with open(path, "rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    return decode(raw), hashlib.sha256(raw).hexdigest()


def write_once(path, value):
    """Atomic create-new publication. A post-link failure can leave evidence."""
    path = Path(path)
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    need(len(raw) <= MAX_BYTES, "record exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".completion-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # No replace/overwrite fallback.
    finally:
        os.unlink(temporary)
    need(read(path)[0] == value, "publication readback differs; reconcile retained record")


def payload(result):
    need(isinstance(result, dict) and not result.get("isError"), "Codex tool returned an error")
    blocks = result.get("content")
    need(isinstance(blocks, list) and len(blocks) == 1
         and isinstance(blocks[0], dict) and blocks[0].get("type") == "text"
         and isinstance(blocks[0].get("text"), str), "unsupported MCP result envelope")
    value = decode(blocks[0]["text"].encode("utf-8"))
    need(isinstance(value, dict), "tool payload must be an object")
    return value


def snapshot(path, task_id, now=None, selected_turn=None, fresh=True):
    """Parse the observed, versioned tool shapes; unknown never means idle."""
    task_id = identity(task_id)
    document, digest = read(path)
    need(isinstance(document, dict) and document.get("schema") == SCHEMA,
         "unsupported observation schema")
    tool = document.get("tool")
    need(tool in TOOLS, "unsupported collector tool")
    observed = utc(document.get("observed_at_utc"))
    now = utc(now) if now else datetime.now(timezone.utc)
    age = (now - observed).total_seconds()
    need(age >= 0 and (not fresh or age <= MAX_AGE), "stale/future observation; collect again")
    request = document.get("request")
    need(isinstance(request, dict), "retained tool request required")
    data = payload(document.get("result"))
    if tool == TOOLS[0]:
        targets = request.get("targets")
        need(isinstance(targets, list) and any(isinstance(t, dict) and t.get("threadId") == task_id
                                              for t in targets), "task not in tool request")
        polls = data.get("polls")
        need(isinstance(polls, list) and len(polls) <= 8, "unsupported wait snapshot")
        matches = [p for p in polls if isinstance(p, dict)
                   and isinstance(p.get("thread"), dict) and p["thread"].get("id") == task_id]
        need(len(matches) == 1, "missing/duplicate target poll; do not infer completion")
        poll = matches[0]
        need(poll.get("schemaVersion") == 1, "unsupported poll schema")
        thread, turn = poll["thread"], poll.get("latestTurn")
        latest = turn
        if selected_turn is not None:
            need(isinstance(turn, dict) and turn.get("id") == selected_turn,
                 "expected turn not in poll; collect read_thread history")
    else:
        need(request.get("threadId") == task_id and data.get("schemaVersion") == 1,
             "thread request/schema mismatch")
        thread = data.get("thread")
        need(isinstance(thread, dict) and thread.get("id") == task_id, "thread identity mismatch")
        page, turns = data.get("page"), data.get("turns")
        need(isinstance(page, dict) and page.get("order") == "newest_first"
             and isinstance(turns, list), "newest-first turns required")
        latest = turns[0] if turns else None
        if selected_turn is None:
            turn = latest
        else:
            matches = [t for t in turns if isinstance(t, dict) and t.get("id") == selected_turn]
            need(len(matches) == 1, "expected turn missing/duplicate; collect more history")
            turn = matches[0]
    state = thread.get("status")
    state = state.get("type") if isinstance(state, dict) else None
    need(turn is None or isinstance(turn, dict), "invalid turn")
    turn_id = identity(turn["id"]) if turn else None
    status = turn.get("status") if turn else None
    outcome = TERMINAL.get(status)
    terminal = outcome is not None
    if terminal:
        ended = turn.get("completedAt")
        need(type(ended) in (int, float) and 0 < ended <= observed.timestamp(),
             "terminal turn lacks valid completedAt")
        if status == "completed" and turn.get("error") is not None:
            outcome = "unknown"  # Contradictory success cannot authorize another job.
    latest_status = latest.get("status") if isinstance(latest, dict) else None
    active = latest_status in ("inProgress", "running") or state in ("active", "running", "inProgress", "busy")
    idle = state == "idle" and latest_status in TERMINAL and not active
    return {"task_id": task_id, "turn_id": turn_id, "status": status,
            "terminal": terminal, "outcome": outcome or "unknown",
            "worker_state": "busy" if active else "idle" if idle else "unknown",
            "latest_turn_id": latest.get("id") if isinstance(latest, dict) else None,
            "observed_at_utc": document["observed_at_utc"], "source_sha256": digest,
            "source_tool": tool, "collection": "supported-tool-caller-supplied"}


def key_for(task_id, turn_id):
    raw = json.dumps([identity(task_id), identity(turn_id)], separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


class Observer:
    """Durable records, bounded catch-up, and acknowledgment; never assignment."""
    def __init__(self, folder, link=None):
        self.folder = Path(folder)
        self.link = link

    def path(self, kind, key):
        need(isinstance(key, str) and re.fullmatch(r"[0-9a-f]{64}", key), "invalid event key")
        return self.folder / kind / (key + ".json")

    def record(self, kind, key, value):
        path = self.path(kind, key)
        try:
            write_once(path, value)
        except FileExistsError:
            need(read(path)[0] == value, "conflicting immutable " + kind + " record")
        return value

    def get(self, kind, key):
        path = self.path(kind, key)
        return read(path)[0] if path.exists() else None

    def observe(self, source, task_id, now=None, turn_id=None):
        view = snapshot(source, task_id, now, selected_turn=turn_id, fresh=False)
        if not view["terminal"]:
            return dict(view, event_key=None, notification="not-terminal")
        key = key_for(task_id, view["turn_id"])
        previous = self.get("events", key)
        if previous is not None:
            need(previous["outcome"] == view["outcome"], "contradictory terminal evidence")
        else:
            self.record("events", key, dict(view, event_key=key))
        return dict(view, event_key=key)

    def event(self, key):
        event = self.get("events", key)
        need(isinstance(event, dict) and event.get("event_key") == key
             and key_for(event.get("task_id"), event.get("turn_id")) == key,
             "missing/corrupt event")
        return event

    def log(self, after):
        need(self.link is not None, "TeamLink not configured")
        messages = []
        for _ in range(10):
            result = self.link._call("GET", "/log?after=%d&limit=200" % after)
            need(isinstance(result, dict) and isinstance(result.get("messages"), list),
                 "coordinator log unavailable; outcome unknown")
            page = result["messages"]
            need(len(page) <= 200, "unexpected log page size")
            for message in page:
                need(isinstance(message, dict) and type(message.get("id")) is int
                     and message["id"] > after, "invalid log ordering")
                messages.append(message)
                after = message["id"]
            if len(page) < 200:
                return messages
        raise ValueError("catch-up bound reached; no automatic resend")

    def deliver(self, key, current, now=None):
        event = self.event(key)
        view = snapshot(current, event["task_id"], now)  # Always reconcile before notifying.
        delivered = self.get("deliveries", key)
        if delivered:
            return dict(delivered, duplicate=True, current=view)
        intent = self.get("intents", key)
        if intent:
            matches = [m for m in self.log(intent["after"])
                       if m.get("from") == SENDER and m.get("to") == COORDINATOR
                       and m.get("type") == "codex.turn.terminal" and m.get("body") == intent["body"]]
            if matches:
                result = {"event_key": key, "message_id": matches[0]["id"],
                          "recovered": True, "matching_message_ids": [m["id"] for m in matches]}
                return dict(self.record("deliveries", key, result), current=view)
            return {"event_key": key, "delivery": "uncertain", "automatic_retry": False, "current": view}
        need(self.link is not None, "TeamLink not configured")
        health = self.link.health()
        need(isinstance(health, dict) and type(health.get("last")) is int, "TeamLink unavailable before intent")
        body = {"schema": "daedalus.codex-completion.v1", "event_key": key,
                "task_id": event["task_id"], "turn_id": event["turn_id"], "outcome": event["outcome"],
                "terminal_source_sha256": event["source_sha256"],
                "current_turn_id": view["turn_id"], "current_worker_state": view["worker_state"],
                "current_source_sha256": view["source_sha256"], "observed_at_utc": view["observed_at_utc"],
                "collector": view["collection"], "parent_push": False, "assignment_executed": False}
        intent = {"event_key": key, "after": health["last"], "body": body}
        try:
            write_once(self.path("intents", key), intent)
        except FileExistsError:
            return self.deliver(key, current, now)  # Loser reconciles; never sends.
        # /send acceptance is delivery only. Body correlation + local records
        # provide dedup; no assumption that the running broker persists UID.
        mid = self.link.send(COORDINATOR, "codex.turn.terminal", body,
                             topic="codex-completion")
        if type(mid) is not int or mid <= 0:
            return {"event_key": key, "delivery": "uncertain", "automatic_retry": False, "current": view}
        return dict(self.record("deliveries", key, {"event_key": key, "message_id": mid,
                                                  "recovered": False}), current=view)

    def status(self, key, current, now=None):
        event = self.event(key)
        view = snapshot(current, event["task_id"], now)
        delivery = self.get("deliveries", key)
        transport, semantic = None, None
        if delivery:
            for message in self.log(delivery["message_id"]):
                if message.get("from") != COORDINATOR or message.get("to") != SENDER:
                    continue
                body = message.get("body")
                if not isinstance(body, dict):
                    continue
                if message.get("type") == "ack" and body.get("id") == delivery["message_id"]:
                    transport = message["id"]
                if (message.get("type") == "codex.completion.ack"
                        and body.get("event_key") == key and body.get("task_id") == event["task_id"]
                        and body.get("turn_id") == event["turn_id"]
                        and body.get("notification_id") == delivery["message_id"]
                        and body.get("decision") == "received"):
                    semantic = message["id"]
            if transport is not None and not self.get("transport_ack", key):
                self.record("transport_ack", key, {"message_id": transport, "notification_id": delivery["message_id"]})
            if semantic is not None and not self.get("semantic_ack", key):
                self.record("semantic_ack", key, {"message_id": semantic, "notification_id": delivery["message_id"]})
        transport = self.get("transport_ack", key)
        semantic = self.get("semantic_ack", key)
        same = view["turn_id"] == event["turn_id"]
        eligible = bool(semantic and same and view["worker_state"] == "idle"
                        and view["outcome"] == event["outcome"] == "succeeded")
        return {"event_key": key, "task_id": event["task_id"], "turn_id": event["turn_id"],
                "delivery": delivery, "transport_ack": transport, "semantic_ack": semantic,
                "current": view, "newer_or_different_turn": not same,
                "may_offer_next_task": eligible, "assignment_executed": False, "parent_push": False,
                "boundary": "Recheck supported task state immediately before any separately authorized assignment."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("observe", "deliver", "status"):
        command = sub.add_parser(name)
        command.add_argument("--state", required=True)
        command.add_argument("--snapshot", required=True)
        command.add_argument("--task" if name == "observe" else "--key", required=True)
        if name == "observe":
            command.add_argument("--turn")
    args = parser.parse_args(argv)
    try:
        observer = Observer(args.state, None if args.command == "observe" else Link(SENDER))
        if args.command == "observe":
            result = observer.observe(args.snapshot, args.task, turn_id=args.turn)
        else:
            result = getattr(observer, args.command)(args.key, args.snapshot)
        print(json.dumps(result, allow_nan=False))
        return 2 if result.get("delivery") == "uncertain" else 0
    except (ValueError, OSError, KeyError, TypeError, OverflowError, RecursionError) as error:
        print(json.dumps({"error": str(error), "assignment_executed": False,
                          "parent_push": False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
