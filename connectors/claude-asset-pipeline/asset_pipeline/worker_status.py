# SPDX-License-Identifier: MIT
"""Bounded TeamLink status listener plus caller-supplied supported Codex evidence.

No Codex/Claude private endpoint, autonomous MCP collector, assignment or model wake.
Owner states are qualified self-reports, never authoritative session terminal proof.
"""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

from . import codex_completion as c
from .teamlink import Link

CHECKINS_SHA = "87421d4813b3b51cae02b8f8e55e0daf15e097249efbc4c1094142ccdff0846a"
MAX_SECONDS = 8 * 60 * 60


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
    def __init__(self, folder, checkins, notifier=None, follow_assignments=False):
        self.folder, self.checkins = Path(folder), checkins
        self.path = self.folder / "current.json"
        self.state = c.read(self.path)[0] if self.path.exists() else {
            "schema": "daedalus.worker-status.v1", "claude": None, "witness": None,
            "codex": {}, "queued": [], "cursor": 0, "connected": False}
        c.need(self.state.get("schema") == "daedalus.worker-status.v1", "unsupported status state")
        self.observer = c.Observer(self.folder / "notices", notifier)
        self.follow_assignments = follow_assignments

    def save(self):
        c.need(len(json.dumps(self.state, allow_nan=False).encode()) <= c.MAX_BYTES, "status bound reached; retain and reconcile")
        self.checkins.save(self.path, self.state)

    def register(self, assignment, deadline, checkpoint_seconds=900):
        previous = self.state["claude"]
        if previous:
            root = self.state.get("root_assignment_sha256", previous["assignment_sha256"])
            c.need(root == self.checkins.digest(assignment),
                   "different assignment requires separate state directory; no automatic reassignment")
        else:
            self.state["claude"] = self.checkins.create(assignment, deadline, checkpoint_seconds)
            self.state["cursor"] = assignment["id"] - 1
        self.state.setdefault("root_assignment_sha256", self.checkins.digest(assignment))
        self.save()

    def ingest(self, messages, observed_at):
        c.need(isinstance(messages, list) and len(messages) <= 2000, "bounded hub messages required")
        c.need(c.utc(observed_at) <= datetime.now(timezone.utc), "future hub observation")
        previous = self.state["claude"]
        c.need(previous is not None, "register actual coordinator assignment first")
        reduced = self.checkins.reduce(previous, messages, observed_at)
        if self.follow_assignments and reduced["superseded_by"]:
            replacements = [m for m in messages if m["id"] == reduced["superseded_by"]]
            c.need(len(replacements) == 1, "new assignment source missing; reconcile before following")
            replacement = replacements[0]
            c.need(replacement.get("from") == previous["coordinator"]
                   and replacement.get("to") == previous["worker"], "known-worker assignment route required")
            deadline = (c.utc(observed_at) + timedelta(seconds=previous["checkpoint_seconds"])).isoformat()
            adopted = self.checkins.create(replacement, deadline, previous["checkpoint_seconds"])
            self.observer.record("assignment_history", event_key([previous["worker"], previous["assignment_sha256"]]),
                                 {"state": reduced, "witness": self.state["witness"], "tracked_at_utc": observed_at})
            self.state["witness"] = None
            previous = adopted
            reduced = self.checkins.reduce(adopted, [m for m in messages if m["id"] >= replacement["id"]], observed_at)
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
                         "acceptance_missing": state.get("acceptance_missing", not state["started"]),
                         "outcome_authority": "owner-self-report",
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
        c.need(0 < seconds <= MAX_SECONDS and 0 < wait_seconds <= 25 and type(max_waits) is int and 1 <= max_waits <= 12000,
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


class ProfileAcknowledgments(c.Observer):
    """Keep frozen ACK matching; require explicit presence even for null fields."""
    FIELDS = ("profile_id", "provider", "owner", "assignment_id", "task_id", "session_id", "turn_id", "source")

    def log(self, after):
        return [message for message in super().log(after)
                if message.get("type") != "worker.status.ack"
                or isinstance(message.get("body"), dict) and all(field in message["body"] for field in self.FIELDS)]

class ProfileStatus(Status):
    """One configured owner's reports and independently supplied tool evidence."""
    def __init__(self, folder, checkins, profile, notifier=None):
        self.profile = profile
        assignment = profile["assignment"]
        self.profile_id = event_key([profile["owner"], profile["provider"],
                                     assignment["body"]["assignment_id"], assignment["body"]["request_id"]])
        super().__init__(folder, checkins, notifier, profile["follow_assignments"])
        self.register(assignment, profile["start_deadline"], profile["checkpoint_seconds"])

    def ingest(self, messages, observed_at):
        before = self.state["claude"]["assignment_sha256"]
        super().ingest(messages, observed_at)
        if self.state["claude"]["assignment_sha256"] != before or self.state["claude"]["superseded_by"]:
            self.state["codex"] = {}
            self.save()

    def rows(self, now=None):
        bound = (not self.state["claude"]["superseded_by"]
                 and self.state["claude"]["assignment_sha256"] == self.checkins.digest(self.profile["assignment"]))
        rows = []
        for row in super().rows(now):
            reported = row.get("outcome_authority") == "owner-self-report"
            if not reported and not bound:
                continue  # Never relabel a retained old turn as a new assignment.
            if reported and "codex" in self.profile:
                row["supported_tool_binding"] = "configured" if bound else "superseded"
            rows.append(row)
            row.update(profile_id=self.profile_id, owner=self.profile["owner"],
                       provider=self.profile["provider"] if reported else "codex",
                       assignment_id=self.state["claude"]["assignment_id"])
            row.setdefault("session_id", None)
            row.setdefault("turn_id", None)
            if not reported:
                row["outcome_authority"] = "supported-tool-observation"
        return rows

    @staticmethod
    def notice_key(row, advice=None):
        return event_key([row["profile_id"], row["provider"], row["owner"], row["assignment_id"],
                          row["task_id"], row["source"], row.get("session_id"), row.get("turn_id"),
                          row.get("message_id"), row["status"], row["reason"],
                          advice["action"] if advice else None])

    def queue(self, now=None):
        now = now or instant()
        self.state["claude"], advice = self.checkins.checkpoint(self.state["claude"], now)
        for row in self.rows(now):
            reported = row["outcome_authority"] == "owner-self-report"
            notices = []
            if row["status"] in ("finished", "blocked") or row["reason"] in (
                    "stale", "disconnected", "newer-assignment"):
                notices.append(None)
            if advice and reported:
                notices.append(advice)
            for reminder in notices:
                key = self.notice_key(row, reminder)
                if key in self.state["queued"]:
                    continue
                body = {"schema": "daedalus.worker-status-actionable.v1", "event_key": key,
                        **row, "decision_required": reminder is not None or row["status"] != "finished",
                        "parent_push": False, "automatic_assignment": False}
                if reminder:
                    body["advice"] = reminder
                self.observer.record("queue", key, body)
                self.state["queued"].append(key)
        self.save()
        return list(self.state["queued"])

    def notify(self, now=None):
        now = now or instant()
        current = self.rows(now)
        results = []
        for key in self.state["queued"]:
            body = self.observer.get("queue", key)
            # Existing intents are reconciled by the frozen Observer, never resent.
            retained = self.observer.get("deliveries", key) or self.observer.get("intents", key)
            if not retained and not any(self.notice_key(row, body.get("advice")) == key for row in current):
                results.append({"event_key": key, "owner": self.profile["owner"],
                                "delivery": "withheld", "reason": "status-or-assignment-changed",
                                "automatic_retry": False})
                continue
            results.append(self.observer.notify(key, body, "worker.status.actionable"))
        return results

    def acks(self, key):
        body = self.observer.get("queue", key)
        c.need(body is not None, "unknown queued owner event")
        expected = {field: body[field] for field in (
            "profile_id", "provider", "owner", "assignment_id", "task_id", "session_id", "turn_id", "source")}
        observer = ProfileAcknowledgments(self.observer.folder, self.observer.link)
        return observer.acknowledgments(key, "worker.status.ack", expected)


class Fanout:
    """Explicit bounded registry; hub messages cannot create owners, files or routes."""
    SCHEMA = "daedalus.worker-status-profiles.v1"

    def __init__(self, folder, checkins, config, notifier=None):
        c.need(isinstance(config, dict) and set(config) == {"schema", "coordinator", "profiles"}
               and config["schema"] == self.SCHEMA and config["coordinator"] == c.COORDINATOR,
               "explicit coordinator-owned profiles configuration required")
        profiles = config["profiles"]
        c.need(isinstance(profiles, list) and 1 <= len(profiles) <= 32, "configure 1..32 owner profiles")
        config = json.loads(json.dumps(config, allow_nan=False))
        owners = set()
        required = {"owner", "provider", "assignment", "start_deadline", "checkpoint_seconds",
                    "follow_assignments", "notify"}
        for profile in config["profiles"]:
            c.need(isinstance(profile, dict) and required <= set(profile)
                   and set(profile) <= required | {"codex"}, "explicit bounded owner profile required")
            owner = c.identity(profile["owner"])
            c.need(owner not in owners and owner != c.COORDINATOR, "unique configured owner required")
            owners.add(owner)
            c.need(profile["provider"] in ("claude", "codex")
                   and type(profile["follow_assignments"]) is bool and type(profile["notify"]) is bool,
                   "explicit provider and notification/follow consent required")
            assignment = profile["assignment"]
            c.need(isinstance(assignment, dict) and assignment.get("from") == c.COORDINATOR
                   and assignment.get("to") == owner and assignment.get("type") in ("ping", "task.assign"),
                   "configured owner assignment route required")
            checkins.create(assignment, profile["start_deadline"], profile["checkpoint_seconds"])
            if "codex" in profile:
                source = profile["codex"]
                c.need(profile["provider"] == "codex" and isinstance(source, dict)
                       and set(source) == {"task_id", "snapshot"}
                       and isinstance(source["snapshot"], str) and bool(source["snapshot"]),
                       "explicit supported Codex task/snapshot binding required")
                c.identity(source["task_id"])
        self.folder, self.checkins = Path(folder), checkins
        self.path = self.folder / "current.json"
        self.config = config
        pin = event_key(config)
        self.state = c.read(self.path)[0] if self.path.exists() else {
            "schema": "daedalus.worker-status-fanout.v1", "config_sha256": pin,
            "cursor": 0, "queued": [], "connected": False}
        c.need(self.state.get("schema") == "daedalus.worker-status-fanout.v1"
               and self.state.get("config_sha256") == pin,
               "different profiles require a separate state directory")
        self.profiles = {}
        for profile in config["profiles"]:
            owner = profile["owner"]
            child = self.folder / "profiles" / event_key([owner, profile["provider"]])
            self.profiles[owner] = ProfileStatus(child, checkins, profile, notifier)
        self.save()

    def save(self):
        if not self.state["connected"]:
            for child in self.profiles.values():
                child.state["connected"] = False
                child.save()
        self.state["cursor"] = min(child.state["cursor"] for child in self.profiles.values())
        self.state["queued"] = sorted(key for child in self.profiles.values() for key in child.state["queued"])
        c.need(len(json.dumps(self.state, allow_nan=False).encode()) <= c.MAX_BYTES, "fanout state bound reached")
        self.checkins.save(self.path, self.state)

    def ingest(self, messages, observed_at):
        c.need(isinstance(messages, list) and len(messages) <= 2000, "bounded hub messages required")
        c.need(c.utc(observed_at) <= datetime.now(timezone.utc), "future hub observation")
        # Reject conflicting broker IDs before any owner's durable state advances.
        batch = {}
        for message in messages:
            c.need(isinstance(message, dict), "structured hub message required")
            mid, pin = self.checkins.positive(message["id"]), self.checkins.digest(message)
            c.need(mid not in batch or batch[mid] == pin, "conflicting replay for broker message ID")
            batch[mid] = pin
            for child in self.profiles.values():
                prior = child.state["claude"]["seen"].get(str(mid))
                c.need(prior is None or prior == pin, "conflicting replay for broker message ID")
                assignment = child.state["claude"]
                body = message.get("body")
                if (message.get("from") == c.COORDINATOR and message.get("to") == child.profile["owner"]
                        and message.get("type") in ("ping", "task.assign") and isinstance(body, dict)
                        and body.get("assignment_id") == assignment["assignment_id"]):
                    c.need(pin == assignment["assignment_sha256"], "conflicting configured assignment")
        for child in self.profiles.values():
            child.ingest(messages, observed_at)
        self.state["connected"] = True
        self.save()

    def codex(self, owner, path=None, now=None):
        c.need(owner in self.profiles, "unconfigured owner")
        child = self.profiles[owner]
        source = child.profile.get("codex")
        c.need(source is not None, "owner has no configured supported Codex source")
        if (child.state["claude"]["superseded_by"]
                or child.state["claude"]["assignment_sha256"] != self.checkins.digest(child.profile["assignment"])):
            return False  # A new task binding needs an explicit coordinator profile, not hub text.
        path = source["snapshot"] if path is None else path
        c.need(Path(path).resolve() == Path(source["snapshot"]).resolve(), "unconfigured snapshot path")
        return child.codex(source["task_id"], path, now)

    def sources(self):
        return [(owner, child.profile["codex"]["snapshot"]) for owner, child in self.profiles.items()
                if "codex" in child.profile]

    def rows(self, now=None):
        return [row for owner in sorted(self.profiles) for row in self.profiles[owner].rows(now)]

    def queue(self, now=None):
        if not self.state["connected"]:
            for child in self.profiles.values():
                child.state["connected"] = False
        for child in self.profiles.values():
            child.queue(now)
        self.save()
        return list(self.state["queued"])

    def notify(self, now=None):
        results = []
        for child in self.profiles.values():
            if child.profile["notify"] and child.observer.link is not None:
                results.extend(child.notify(now))
            else:
                results.extend({"event_key": key, "owner": child.profile["owner"], "delivery": "disabled"}
                               for key in child.state["queued"])
        return results

    def acks(self, key):
        matches = [child for child in self.profiles.values() if key in child.state["queued"]]
        c.need(len(matches) == 1, "unknown or ambiguous owner event")
        return matches[0].acks(key)

    # Reuse the existing finite listener and its limits/backoff; no new poller.
    listen = Status.listen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--checkins-module", help="exact PR172 source when not merged; SHA pinned")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--assignment")
    mode.add_argument("--profiles", help="explicit coordinator-owned bounded profiles JSON")
    parser.add_argument("--start-deadline")
    parser.add_argument("--snapshot", help="retained {observed_at_utc,messages} hub snapshot")
    parser.add_argument("--codex", action="append", default=[], help="legacy TASK=retained-observation.json (max32)")
    parser.add_argument("--listen-seconds", type=float, default=0)
    parser.add_argument("--wait-seconds", type=float, default=5)
    parser.add_argument("--max-waits", type=int, default=4)
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--ack-key")
    parser.add_argument("--follow-assignments", action="store_true", help="legacy tracking-only assignment following")
    args = parser.parse_args(argv)
    lock = Path(args.state) / "writer.lock"
    owned = False
    try:
        module = checkins_module(args.checkins_module)
        sources = []
        if args.profiles:
            c.need(not args.codex and not args.start_deadline and not args.follow_assignments,
                   "profiles own their explicit tool bindings, deadlines and follow policy")
            config = c.read(args.profiles)[0]
        else:
            c.need(args.start_deadline is not None, "legacy assignment requires --start-deadline")
            assignment = c.read(args.assignment)[0]
            c.need(len(args.codex) <= 32, "at most32 tool observations")
            for item in args.codex:
                task, path = item.split("=", 1)
                sources.append((c.identity(task), path))
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("x"):
            owned = True
        notifier = Link(c.SENDER) if args.notify or args.ack_key else None
        if args.profiles:
            status = Fanout(args.state, module, config, notifier)
            sources = status.sources()
        else:
            status = Status(args.state, module, notifier, args.follow_assignments)
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
