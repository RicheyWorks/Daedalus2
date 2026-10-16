# SPDX-License-Identifier: MIT
"""Bounded TeamLink status listener plus caller-supplied supported Codex evidence.

No Codex/Claude private endpoint, autonomous MCP collector, assignment or model wake.
Claude states are qualified self-reports, never authoritative session terminal proof.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

from . import codex_completion as c
from .teamlink import Link

CHECKINS_SHA = "810fe24c3ce54d1e6a3e9df081f7dfbca8b038cbe0e3dc9dd3a63e2a0490fbae"


def checkins_module(path=None):
    """Compose the actual separately owned PR172 source; never copy its parser."""
    path = Path(path) if path else Path(__file__).with_name("team_checkins.py")
    with path.open("rb") as stream:
        raw = stream.read(c.MAX_BYTES + 1)
    c.need(hashlib.sha256(raw).hexdigest() == CHECKINS_SHA, "PR172 dependency missing/different; reconcile source pin")
    spec = importlib.util.spec_from_file_location("_pinned_team_checkins", path)
    module = importlib.util.module_from_spec(spec)
    # Execute the verified bytes, avoiding a check-then-reopen dependency race.
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def instant():
    return datetime.now(timezone.utc).isoformat()


def event_key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class Status:
    """Single-writer durable status and actionable outbox, sharing PR171 delivery."""
    def __init__(self, folder, checkins, notifier=None):
        self.folder, self.checkins = Path(folder), checkins
        self.path = self.folder / "current.json"
        self.state = c.read(self.path)[0] if self.path.exists() else {
            "schema": "daedalus.worker-status.v1", "claude": None, "witness": None,
            "codex": {}, "queued": [], "cursor": 0, "connected": False}
        c.need(self.state.get("schema") == "daedalus.worker-status.v1", "unsupported status state")
        self.observer = c.Observer(self.folder / "notices", notifier)

    def save(self):
        c.need(len(json.dumps(self.state, allow_nan=False).encode()) <= c.MAX_BYTES, "status bound reached; retain and reconcile")
        self.checkins.save(self.path, self.state)

    def register(self, assignment, deadline, checkpoint_seconds=900):
        previous = self.state["claude"]
        if previous:
            c.need(previous["assignment_sha256"] == self.checkins.digest(assignment),
                   "different assignment requires separate state directory; no automatic reassignment")
        else:
            self.state["claude"] = self.checkins.create(assignment, deadline, checkpoint_seconds)
            self.state["cursor"] = assignment["id"] - 1
        self.save()

    def ingest(self, messages, observed_at):
        c.need(isinstance(messages, list) and len(messages) <= 2000, "bounded hub messages required")
        c.need(c.utc(observed_at) <= datetime.now(timezone.utc), "future hub observation")
        previous = self.state["claude"]
        c.need(previous is not None, "register actual coordinator assignment first")
        reduced = self.checkins.reduce(previous, messages, observed_at)
        last = reduced["last_semantic_id"]
        if last != previous["last_semantic_id"]:
            matches = [m for m in messages if m.get("id") == last]
            c.need(len(matches) == 1 and self.checkins.digest(matches[0]) == reduced["seen"][str(last)],
                   "accepted semantic witness unavailable")
            message = matches[0]
            body = message["body"]
            reported = body.get("reported_at_utc")
            if reported is not None:
                c.need(c.utc(reported) <= c.utc(observed_at), "future reported check-in")
            session = body.get("session_id")
            c.need(session is None or isinstance(session, str)
                   and re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", session),
                   "invalid reported session identity")
            self.state["witness"] = {"message_id": last, "source_sha256": self.checkins.digest(message),
                                     "session_id": session, "reported_at_utc": reported,
                                     "received_at_utc": observed_at}
        self.state["claude"] = reduced
        self.state["cursor"] = max(self.state["cursor"], reduced["cursor"])
        self.state["connected"] = True
        self.state["last_hub_read_utc"] = observed_at
        self.save()

    def codex(self, task, path, now=None):
        now = now or instant()
        value = c.snapshot(path, task, now, fresh=False)
        previous = self.state["codex"].get(task)
        if previous:
            old, new = c.utc(previous["observed_at_utc"]), c.utc(value["observed_at_utc"])
            if new < old:
                return False
            c.need(new != old or previous == value, "conflicting same-time Codex observations")
        c.need(len(self.state["codex"]) < 32 or task in self.state["codex"], "at most 32 Codex tasks")
        self.state["codex"][task] = value
        self.save()
        return True

    def rows(self, now=None):
        now = now or instant()
        current = c.utc(now)
        rows = []
        state, witness = self.state["claude"], self.state["witness"] or {}
        if state:
            reported = witness.get("reported_at_utc")
            age = (current - c.utc(reported)).total_seconds() if reported else None
            fresh = age is not None and 0 <= age <= state["checkpoint_seconds"]
            known = fresh and self.state["connected"] and not state["superseded_by"]
            stage = state["stage"]
            status = ("working" if stage in ("start", "progress") else
                      "finished" if stage == "completed" else
                      "blocked" if stage in ("blocked", "failed", "cancelled") else "unknown") if known else "unknown"
            reason = ("newer-assignment" if state["superseded_by"] else "disconnected" if not self.state["connected"] else
                      "missing-report-time" if age is None else "stale" if not fresh else stage)
            rows.append({"owner": state["worker"], "provider": "claude", "task_id": state["assignment_id"],
                         "assignment_id": state["assignment_id"], "session_id": witness.get("session_id"),
                         "turn_id": None, "status": status, "outcome": stage if state["terminal"] else "unknown",
                         "freshness": "unknown" if age is None else "fresh" if fresh else "stale",
                         "reason": reason, "last_update_utc": reported, "observed_at_utc": witness.get("received_at_utc"),
                         "source": "structured-owner-self-report-not-session-terminal-api",
                         "source_sha256": witness.get("source_sha256"), "message_id": witness.get("message_id"),
                         "transport_ack": state["transport_ack"], "semantic_start": state["started"],
                         "superseded_by": state["superseded_by"], "may_assign": False})
        for task, value in sorted(self.state["codex"].items()):
            age = (current - c.utc(value["observed_at_utc"])).total_seconds()
            fresh = 0 <= age <= c.MAX_AGE
            status = ("working" if value["worker_state"] == "busy" else
                      "finished" if value["terminal"] and value["worker_state"] == "idle" and value["outcome"] == "succeeded" else
                      "blocked" if value["terminal"] and value["outcome"] in ("failed", "cancelled") else "unknown") if fresh else "unknown"
            rows.append({"owner": task, "provider": "codex", "task_id": task, "assignment_id": None,
                         "session_id": None, "turn_id": value["latest_turn_id"], "status": status,
                         "outcome": value["outcome"], "freshness": "fresh" if fresh else "stale",
                         "reason": value["status"] if fresh else "stale", "last_update_utc": value["observed_at_utc"],
                         "source": value["collection"], "source_sha256": value["source_sha256"], "may_assign": False})
        return rows

    def queue(self, now=None):
        now = now or instant()
        state = self.state["claude"]
        advice = None
        if state:
            self.state["claude"], advice = self.checkins.checkpoint(state, now)
        for row in self.rows(now):
            if row["status"] not in ("finished", "blocked") and row["reason"] not in (
                    "stale", "disconnected", "newer-assignment") and not (advice and row["provider"] == "claude"):
                continue
            key = event_key([row["provider"], row["owner"], row["task_id"], row.get("session_id"),
                             row.get("turn_id"), row.get("message_id"), row["status"], row["reason"]])
            if key not in self.state["queued"]:
                body = {"schema": "daedalus.worker-status-actionable.v1", "event_key": key,
                        **row, "decision_required": row["status"] != "finished", "parent_push": False,
                        "automatic_assignment": False}
                if advice and row["provider"] == "claude":
                    body["advice"] = advice
                self.observer.record("queue", key, body)
                self.state["queued"].append(key)
        self.save()
        return list(self.state["queued"])

    def notify(self):
        results = []
        for key in self.state["queued"]:
            body = self.observer.get("queue", key)
            result = self.observer.notify(key, body, "worker.status.actionable")
            results.append(result)
        return results

    def acks(self, key):
        body = self.observer.get("queue", key)
        c.need(body is not None, "unknown queued event")
        return self.observer.acknowledgments(key, "worker.status.ack", {
            "owner": body["owner"], "task_id": body["task_id"], "session_id": body["session_id"]})

    def listen(self, reader, seconds=10, wait_seconds=5, max_waits=4, codex=(), notify=False):
        c.need(0 < seconds <= 600 and 0 < wait_seconds <= 25 and type(max_waits) is int and 1 <= max_waits <= 120,
               "bounded listener limits required")
        start, cpu = time.monotonic(), time.process_time()
        waits, failures = 0, 0
        while waits < max_waits and time.monotonic() - start < seconds:
            waits += 1
            timeout = min(wait_seconds, seconds - (time.monotonic() - start))
            for task, path in codex:
                self.codex(task, path)
            try:
                # Catch up ALL routes to see superseding coordinator assignments.
                messages = c.Observer(self.folder, reader).log(self.state["cursor"])
                self.ingest(messages, instant())
                self.queue()
                if notify:
                    self.notify()
                # Read-only; no broker ACK/registration/presence or work dispatch.
                received, last = reader.wait(self.state["cursor"], timeout)
                c.need(getattr(reader, "up", True) and isinstance(received, list)
                       and type(last) is int and last >= self.state["cursor"],
                       "TeamLink wait unavailable")
                # Do not advance from wait.last: /log must inspect intervening routes.
                failures = 0
            except (ValueError, OSError, TypeError, KeyError):
                failures += 1
                self.state["connected"] = False
                self.save()
                self.queue()
                time.sleep(min(2 ** min(failures - 1, 3), max(0, seconds - (time.monotonic() - start))))
        # One catch-up includes the last wake, without another long wait.
        try:
            self.ingest(c.Observer(self.folder, reader).log(self.state["cursor"]), instant())
        except (ValueError, OSError, TypeError, KeyError):
            self.state["connected"] = False
        self.queue()
        deliveries = self.notify() if notify else []
        return {"schema": "daedalus.worker-status-run.v1", "rows": self.rows(), "queued": self.state["queued"],
                "deliveries": deliveries, "waits": waits, "wall_seconds": time.monotonic()-start,
                "process_cpu_seconds": time.process_time()-cpu, "automatic_collector": False,
                "parent_push": False, "automatic_assignment": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--checkins-module", help="exact PR172 source when not merged; SHA pinned")
    parser.add_argument("--assignment", required=True)
    parser.add_argument("--start-deadline", required=True)
    parser.add_argument("--snapshot", help="retained {observed_at_utc,messages} hub snapshot")
    parser.add_argument("--codex", action="append", default=[], help="TASK=retained-observation.json (max32)")
    parser.add_argument("--listen-seconds", type=float, default=0)
    parser.add_argument("--wait-seconds", type=float, default=5)
    parser.add_argument("--max-waits", type=int, default=4)
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--ack-key")
    args = parser.parse_args(argv)
    lock = Path(args.state) / "writer.lock"
    owned = False
    try:
        module = checkins_module(args.checkins_module)
        assignment = c.read(args.assignment)[0]
        sources = []
        c.need(len(args.codex) <= 32, "at most32 tool observations")
        for item in args.codex:
            task, path = item.split("=", 1)
            sources.append((c.identity(task), path))
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("x"):
            owned = True
        status = Status(args.state, module, Link(c.SENDER) if args.notify or args.ack_key else None)
        status.register(assignment, args.start_deadline)
        if args.snapshot:
            data = c.read(args.snapshot)[0]
            status.ingest(data["messages"], data["observed_at_utc"])
        for task, path in sources:
            status.codex(task, path)
        if args.listen_seconds:
            result = status.listen(Link(c.COORDINATOR), args.listen_seconds, args.wait_seconds,
                                   args.max_waits, sources, args.notify)
        else:
            status.queue()
            result = {"rows": status.rows(), "queued": status.state["queued"],
                      "deliveries": status.notify() if args.notify else []}
        if args.ack_key:
            result["acknowledgments"] = status.acks(args.ack_key)
        print(json.dumps(result, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, OverflowError, RecursionError) as error:
        print(json.dumps({"error": str(error), "parent_push": False, "automatic_assignment": False}), file=sys.stderr)
        return 3
    finally:
        if owned:
            lock.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
