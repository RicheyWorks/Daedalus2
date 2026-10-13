# SPDX-License-Identifier: MIT
"""The art queue watcher (ADR-051): Blender team → Unreal, live, with no one relaying.

The Blender team and Claude share one folder (default C:\\Users\\730ri\\projects\\bot-team\\art):

    BRIEF.md        the rules and the asset list (written by Claude)
    QUEUE.md        the board: one Markdown table row per asset, with a Status cell
    <Kind>\\<Asset>.blend   the work (Kind = the asset name's prefix: Tool, Item, Mob, Veh, Bld, Prop, Sky, Wpn)
    NOTES\\<Asset>.md       questions and answers about one asset
    feed.jsonl      every event, one JSON line each, newest last (what the lead bot reads to plan its day)
    STATUS.md       the board's live summary: counts, what's waiting on whom, the last events
    reports\\<Asset>.json   the pipeline's full report for each attempt

Status flow: TODO → DOING (who) → READY → SHIPPING → SHIPPED (tris, size) | REJECTED: <check> → … → READY.
REJECTED means the asset is wrong and the Blender team must fix it. BLOCKED: <why> means Unreal failed on its own
side (the bridge dropped, or the import made nothing while Blender and the file were fine); the asset is fine, and
the watcher retries it by itself every BLOCKED_RETRY_S seconds, so nobody needs to touch the row.

Every few seconds the watcher reads QUEUE.md. For each READY row it:
  1. needs both bridges up (Blender 127.0.0.1:9876, Unreal 127.0.0.1:9877); if not, it says so in STATUS.md and
     leaves the row alone;
  2. opens <Kind>\\<Asset>.blend in Blender, unless Blender already has unsaved work in another file, which it
     never throws away: the row waits (WAITING: Blender has unsaved work) until that's saved;
  3. exports the meshes in the collection named after the asset (or every visible mesh if there's no such
     collection) and imports them into Unreal under /Game/Daedalus/Art/<Kind>/<Asset>, through the pipeline's
     judge (asset_pipeline.ship);
  4. adds the brief's own rules: the triangle budget for the kind and at most 3 material slots per mesh;
  5. writes SHIPPED or REJECTED: <the first failed check> into the row, the report, and a feed line.

Only the Status and Notes cells of an existing row are rewritten. Observed producer changes are preserved by
re-reading before replacement and checking claim revisions. External writers still need a shared locking
protocol to close the final compare/replace race.

    python -m asset_pipeline.artqueue --once            # one pass
    python -m asset_pipeline.artqueue --every 10        # watch (Ctrl+C to stop)
"""
import argparse
import datetime
import json
import os
import re
import queue as _queue
import sys
import threading
import time
import traceback
import tempfile
import uuid
import stat

from . import ship as pipeline
from . import teamlink
from . import wire

DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "projects", "bot-team", "art")
KINDS = ("Tool", "Item", "Mob", "Veh", "Bld", "Prop", "Sky", "Wpn")
# Triangle budgets by kind (BRIEF.md).
BUDGET = {"Tool": 3000, "Item": 3000, "Wpn": 3000, "Prop": 3000, "Mob": 6000, "Veh": 12000, "Bld": 15000,
          "Sky": 15000}
MAX_SLOTS = 3
PUBLICATION_ATTEMPTS = 5
PUBLICATION_RETRY_S = 0.05
PRODUCER_JOIN_S = 0.5
HANDOFF_WAIT_S = 0.05


class PublicationError(OSError):
    """Local ledger publication failed; this does not imply an import failed."""


class RowConflict(PublicationError):
    """The asset's own revision changed; never publish over its new owner."""


_BOARD_LOCKS = {}
_BOARD_LOCKS_GUARD = threading.Lock()


def board_lock(path):
    # Cooperating Watcher objects in this process share the same row critical section.
    key = os.path.normcase(os.path.abspath(path))
    with _BOARD_LOCKS_GUARD:
        return _BOARD_LOCKS.setdefault(key, threading.RLock())


class WatcherLease:
    """Exclusive admission, also for --once. Unknown/stale owners require reconciliation."""

    def __init__(self, folder):
        self.path = os.path.join(folder, ".watcher-admission.json")
        self.token = uuid.uuid4().hex
        self.owned = False

    def acquire(self):
        try:
            with open(self.path, "x", encoding="utf-8") as stream:
                self.owned = True
                json.dump({"token": self.token, "pid": os.getpid(),
                           "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            return False
        # A failed initial write intentionally leaves an uncertain lease in place.
        return True

    def release(self):
        if not self.owned:
            return False
        try:
            info = os.lstat(self.path)
            if not stat.S_ISREG(info.st_mode) or os.path.islink(self.path) or info.st_size > 4096:
                return False
            with open(self.path, encoding="utf-8") as stream:
                owner = json.load(stream)
            if not isinstance(owner, dict) or owner.get("token") != self.token:
                return False
            os.unlink(self.path)
            self.owned = False
            return True
        except (OSError, ValueError):
            return False


# ------------------------------------------------------------------------------------------------ the board

def parse(text):
    """Rows of the first Markdown table that has an Asset and a Status column:
    [{"line": i, "cells": [...], "asset": .., "status": .., "notes": ..}] plus the column indexes."""
    lines = text.split("\n")
    header = None
    rows = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("<!--") and header is not None:
            continue   # the Blender team's fenced row block (<!-- blender-team rows: begin/end -->) stays in the table
        if not s.startswith("|"):
            if header is not None and rows:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            low = [c.lower() for c in cells]
            if "asset" in low and "status" in low:
                header = {"asset": low.index("asset"), "status": low.index("status"),
                          "notes": low.index("notes") if "notes" in low else None, "width": len(cells)}
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue   # the |---| line
        if len(cells) < header["width"]:
            cells += [""] * (header["width"] - len(cells))
        rows.append({"line": i, "cells": cells, "asset": cells[header["asset"]],
                     "status": cells[header["status"]],
                     "notes": cells[header["notes"]] if header["notes"] is not None else ""})
    return rows, header


def state(status):
    """The status word: TODO, DOING, READY, SHIPPING, SHIPPED, REJECTED, WAITING, BLOCKED (upper case), or ''."""
    m = re.match(r"\s*([A-Za-z]+)", status or "")
    return m.group(1).upper() if m else ""


def set_row(text, asset, status, notes=None):
    """The board with one row's Status (and Notes) replaced; everything else byte for byte."""
    rows, header = parse(text)
    lines = text.split("\n")
    for r in rows:
        if r["asset"] == asset:
            cells = list(r["cells"])
            cells[header["status"]] = status.replace("|", "/")
            if notes is not None and header["notes"] is not None:
                cells[header["notes"]] = notes.replace("|", "/").replace("\n", " ")
            lines[r["line"]] = "| " + " | ".join(cells) + " |"
            return "\n".join(lines)
    raise KeyError(asset)


def conditional_row(text, asset, expected_cells, status, notes=None):
    """Compare the asset revision on EVERY retry; other rows may safely advance."""
    rows, _ = parse(text)
    row = next((r for r in rows if r["asset"] == asset), None)
    if row is None or tuple(row["cells"]) != expected_cells:
        raise RowConflict("asset revision changed before publication: " + asset)
    return set_row(text, asset, status, notes)


def add_row(text, asset, status, notes=""):
    """The board with a new row for `asset` after the table's last row (numbered one past the highest #)."""
    rows, header = parse(text)
    if header is None:
        raise ValueError("QUEUE.md has no table with Asset and Status columns")
    nums = [int(r["cells"][0]) for r in rows if r["cells"] and r["cells"][0].isdigit()]
    cells = [""] * header["width"]
    if header["asset"] != 0:
        cells[0] = str(max(nums or [0]) + 1)
    cells[header["asset"]] = asset
    low = [c.lower() for c in parse_header_cells(text)]
    if "kind" in low:
        cells[low.index("kind")] = (kind_of(asset) or "").lower()
    cells[header["status"]] = status
    if header["notes"] is not None:
        cells[header["notes"]] = notes
    lines = text.split("\n")
    fence = next((i for i, l in enumerate(lines) if l.strip().startswith(BLOCK_BEGIN)), None)
    above = [r for r in rows if fence is None or r["line"] < fence]
    if fence is not None and not above:
        at = fence
    else:
        rows = above or rows
        at = None
    at = at if at is not None else rows[-1]["line"] + 1 if rows else next(i for i, l in enumerate(lines) if l.strip().startswith("|")) + 2
    lines.insert(at, "| " + " | ".join(cells) + " |")
    return "\n".join(lines)


BLOCK_BEGIN = "<!-- blender-team rows: begin"


def parse_header_cells(text):
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if "asset" in [c.lower() for c in cells]:
                return cells
    return []


def kind_of(asset):
    k = asset.split("_", 1)[0]
    return k if k in KINDS else None


# ----------------------------------------------------------------------------------------------- the watcher

BLOCKED_RETRY_S = 60

# The judge's checks of the Blender side and the .glb file. When these all pass and Unreal still made no mesh,
# the fault is Unreal's (busy, in Play, a broken import), not the asset's.
BLENDER_SIDE = ("every Blender object reached the file", "triangles: Blender = file", "materials: Blender = file",
                "sizes: Blender = file")


def unreal_side_failure(report):
    """Why Unreal failed on its own side, or '' when the failure (if any) is the asset's."""
    checks = {c["check"]: c["ok"] for c in report.get("checks", [])}
    if not all(checks.get(n, False) for n in BLENDER_SIDE):
        return ""
    made = report.get("unreal") or {}
    if made.get("error"):
        return "Unreal import error: %s" % str(made["error"])[:100]
    if not made.get("meshes"):
        return "Unreal imported nothing (Blender and the file were fine)"
    return ""


class Watcher:
    def __init__(self, folder=DEFAULT_DIR, blender=wire.BLENDER, unreal=wire.UNREAL, ship=None, clock=time.time,
                 link=None):
        self.folder = folder
        self.blender = blender
        self.unreal = unreal
        self.ship = ship or pipeline.ship
        self.clock = clock
        self.queue = os.path.join(folder, "QUEUE.md")
        self.feed = os.path.join(folder, "feed.jsonl")
        self.status_md = os.path.join(folder, "STATUS.md")
        self.reports = os.path.join(folder, "reports")
        self.waiting_on = ""
        self.waiting_since = None   # when the current wait began (clock seconds), for stall detection
        self.blocked_at = {}        # asset -> when it was last BLOCKED, to pace the retries
        self.link = link            # teamlink.Link("unreal-team"), or None: every event also goes out live
        self.first = []             # name fragments shipped ahead of the rest (--first), e.g. a team's own slot
        self.lock = board_lock(self.queue)
        self._claims = {}
        self._pending_publications = {}
        self._report_versions = {}
        self._witnesses_discovered = False
        self._producer = None

    # -- files

    def read(self):
        for _ in range(5):
            try:
                with open(self.queue, encoding="utf-8") as f:
                    return f.read()
            except PermissionError:   # someone is saving it
                time.sleep(0.4)
        raise PermissionError(self.queue)

    def update(self, asset, status, notes=None):
        """Rewrite one row, only if the file didn't change between our read and our write."""
        with self.lock:
            return self._update(asset, status, notes)

    def _update(self, asset, status, notes):
        return self._change_board(set_row, asset, status, notes)

    def _change_board(self, change, *args):
        """Unique staging file, bounded sharing retries and a fresh conflict check.
        This optimistic check preserves observed producer edits; independent writers
        still need a shared locking protocol to close the final compare/replace gap.
        """
        last_error = None
        with self.lock:
            for attempt in range(PUBLICATION_ATTEMPTS):
                tmp = None
                try:
                    before = self.read()
                    after = change(before, *args)
                    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(self.queue) + ".", suffix=".tmp",
                                              dir=os.path.dirname(self.queue))
                    with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
                        stream.write(after)
                        stream.flush()
                        os.fsync(stream.fileno())
                    if self.read() != before:
                        continue
                    os.replace(tmp, self.queue)
                    return True
                except OSError as error:
                    if not isinstance(error, PermissionError) and getattr(error, "winerror", None) not in (5, 32, 33):
                        raise
                    last_error = error
                    if attempt + 1 < PUBLICATION_ATTEMPTS:
                        time.sleep(PUBLICATION_RETRY_S)
                finally:
                    if tmp is not None:
                        try:
                            os.unlink(tmp)
                        except FileNotFoundError:
                            pass
                        except OSError:
                            pass  # A locked staging file is not proof that the import failed.
        if last_error is not None:
            raise PublicationError("queue publication exhausted sharing retries") from last_error
        return False

    def _require_update(self, asset, status, notes=None):
        if not self.update(asset, status, notes):
            raise PublicationError("queue changed throughout bounded publication attempts: " + asset)

    def _owned_update(self, asset, status, notes=None):
        """An old attempt cannot reject/block a producer's newer revision."""
        token = self._claims.get(asset)
        if token is None:
            return self._require_update(asset, status, notes)
        with self.lock:
            rows, _ = parse(self.read())
            row = next((r for r in rows if r["asset"] == asset), None)
            if row is None or state(row["status"]) != "SHIPPING" or "[queue-claim:%s]" % token not in row["notes"]:
                raise RowConflict("claim changed before outcome publication: " + asset)
            if notes is None:
                notes = re.sub(r"\s*\[queue-(?:stage|claim):[^\]]*\]", "", row["notes"])
            if not self._change_board(conditional_row, asset, tuple(row["cells"]), status, notes):
                raise PublicationError("queue changed throughout outcome publication: " + asset)

    def _claim(self, asset):
        with self.lock:
            rows, _ = parse(self.read())
            row = next(r for r in rows if r["asset"] == asset)
            if state(row["status"]) not in ("READY", "WAITING", "BLOCKED"):
                raise RowConflict("asset is no longer eligible for claim: " + asset)
            if "[queue-stage:import-started]" in row["notes"]:
                raise RowConflict("unresolved import dispatch requires reconciliation: " + asset)
            token = uuid.uuid4().hex
            notes = row["notes"] + " [queue-claim:%s] [queue-stage:claimed-not-exported]" % token
            if not self._change_board(conditional_row, asset, tuple(row["cells"]), "SHIPPING", notes.strip()):
                raise PublicationError("queue changed throughout claim publication: " + asset)
            self._claims[asset] = token
            return token

    def _stage(self, asset, stage):
        """Durable distinction between not dispatched and uncertain editor operations."""
        with self.lock:
            if stage == "import-started" and not self._witnesses_discovered:
                self.reconcile_pending()
            rows, _ = parse(self.read())
            if stage == "import-started" and self.unresolved_imports(rows):
                raise RowConflict("an earlier import outcome requires owner reconciliation before new dispatch")
            row = next((r for r in rows if r["asset"] == asset), None)
            token = self._claims.get(asset)
            if row is None or not token or state(row["status"]) != "SHIPPING" or "[queue-claim:%s]" % token not in row["notes"]:
                raise RowConflict("claim changed before dispatch: " + asset)
            notes = re.sub(r"\s*\[queue-stage:[^\]]*\]", "", row["notes"])
            notes += " [queue-stage:%s]" % stage
            if not self._change_board(conditional_row, asset, tuple(row["cells"]), "SHIPPING", notes):
                raise PublicationError("queue changed throughout dispatch publication: " + asset)
            if stage == "import-started":
                witness = {"_queue_uncertainty": {"state": "unresolved", "asset": asset,
                           "claim_token": token, "reason": "import dispatch outcome not yet committed"}}
                self._pending_publications[asset] = witness  # Latch BEFORE I/O; failure never authorizes dispatch.
                try:
                    self._save_report(asset, witness)
                except OSError as error:
                    raise PublicationError("cannot persist import dispatch witness: " + asset) from error

    def _save_report(self, asset, report):
        os.makedirs(self.reports, exist_ok=True)
        target = os.path.join(self.reports, asset + ".json")
        fd, tmp = tempfile.mkstemp(prefix=asset + ".", suffix=".tmp", dir=self.reports)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, default=str)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, target)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _pending_report(self, asset):
        if asset in self._pending_publications:
            return self._pending_publications[asset]
        try:
            with open(os.path.join(self.reports, asset + ".json"), encoding="utf-8") as stream:
                report = json.load(stream)
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            # A present but unreadable witness is not permission to repeat an import.
            report = {"_queue_publication": {"state": "pending", "asset": asset, "invalid_report": True}}
        if not isinstance(report, dict):
            report = {"_queue_publication": {"state": "pending", "asset": asset, "invalid_report": True}}
        if "_queue_uncertainty" in report:
            self._pending_publications[asset] = report
            return report
        if "_queue_publication" in report:
            publication = report["_queue_publication"]
            if isinstance(publication, dict) and publication.get("state") == "published" and self._valid_publication(asset, report):
                return None
            # Explicit but malformed witness metadata is not absence of a witness.
            self._pending_publications[asset] = report
            return report
        return None

    def _valid_publication(self, asset, report):
        publication = report.get("_queue_publication")
        if not isinstance(publication, dict) or report.get("ok") is not True or publication.get("state") not in ("pending", "published"):
            return False
        dest = report.get("dest")
        token, status, notes = (publication.get(k) for k in ("claim_token", "status", "notes"))
        return (publication.get("asset") == asset and kind_of(asset) is not None
                and re.fullmatch(r"[A-Za-z0-9_]{1,200}", asset) is not None
                and isinstance(token, str) and re.fullmatch(r"[0-9a-f]{32}", token) is not None
                and isinstance(status, str) and re.fullmatch(r"SHIPPED \([0-9]+ tris, [0-9]+\.[0-9]{2} m\)", status) is not None
                and len(status) <= 200 and isinstance(dest, str) and 0 < len(dest) <= 1024
                and dest.startswith("/Game/") and not any(c in dest for c in "\r\n|")
                and isinstance(notes, str) and notes == "in Unreal: " + dest)

    def reconcile_pending(self):
        """No editor calls: discover durable witnesses and retry only ledger publication."""
        assets = set(self._pending_publications)
        if os.path.isdir(self.reports):
            with os.scandir(self.reports) as entries:
                for entry in entries:
                    if entry.name.endswith(".json") and entry.is_file(follow_symlinks=False):
                        asset = entry.name[:-5]
                        info = entry.stat(follow_symlinks=False)
                        version = (info.st_mtime_ns, info.st_size)
                        if asset not in assets and self._report_versions.get(asset) == version:
                            continue
                        self._report_versions[asset] = version
                        if self._pending_report(asset) is not None:
                            assets.add(asset)
        results = [self.reconcile_publication(asset) for asset in sorted(assets)]
        self._witnesses_discovered = True
        return results

    def unresolved_imports(self, rows):
        uncertain = {asset for asset, report in self._pending_publications.items() if "_queue_uncertainty" in report}
        for row in rows:
            if "[queue-stage:import-started]" not in row["notes"] or state(row["status"]) not in ("READY", "SHIPPING", "WAITING"):
                continue
            asset = row["asset"]
            report = self._pending_publications.get(asset, {})
            publication = report.get("_queue_publication")
            completed = (self._valid_publication(asset, report)
                         and "[queue-claim:%s]" % publication["claim_token"] in row["notes"])
            if not completed:
                uncertain.add(asset)
        return uncertain

    def reconcile_publication(self, asset):
        """Publish a correlated completed report, never repeat its editor operation."""
        report = self._pending_report(asset)
        if report is None:
            return None
        if not self._valid_publication(asset, report):
            return (asset, "RECONCILIATION_REQUIRED")
        publication = report["_queue_publication"]
        token = publication.get("claim_token", "")
        rows, _ = parse(self.read())
        row = next((r for r in rows if r["asset"] == asset), None)
        if not re.fullmatch(r"[0-9a-f]{32}", token) or row is None:
            return (asset, "RECONCILIATION_REQUIRED")
        already = row["status"] == publication.get("status") and row["notes"] == publication.get("notes")
        if not already and (state(row["status"]) != "SHIPPING" or "[queue-claim:%s]" % token not in row["notes"]):
            return (asset, "RECONCILIATION_REQUIRED")  # A new producer revision must not be overwritten.
        try:
            self._save_report(asset, report)  # Durable witness BEFORE publishing the row.
            if not already:
                if not self._change_board(conditional_row, asset, tuple(row["cells"]),
                                          publication["status"], publication["notes"]):
                    raise PublicationError("queue changed throughout report publication: " + asset)
            # Events are at least once across a crash between feed and report writes;
            # importantly, reconciliation NEVER repeats the editor import.
            self.event(asset, "shipped", result=publication["status"], dest=report["dest"],
                       exported_s=report.get("exported_s"), imported_s=report.get("imported_s"))
            publication["state"] = "published"
            self._save_report(asset, report)
        except RowConflict:
            publication["state"] = "pending"
            return (asset, "RECONCILIATION_REQUIRED")
        except (OSError, KeyError):
            publication["state"] = "pending"
            return (asset, "PUBLICATION_PENDING")
        self._pending_publications.pop(asset, None)
        return (asset, state(publication["status"]))

    def event(self, asset, what, **detail):
        with self.lock:
            self._event(asset, what, detail)

    def _event(self, asset, what, detail):
        line = {"at": datetime.datetime.fromtimestamp(self.clock()).isoformat(timespec="seconds"),
                "asset": asset, "event": what}
        line.update(detail)
        with open(self.feed, "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        if what in ("shipped", "rejected", "blocked", "error") and asset != "-":
            self.job_result(asset, what, detail)
        if self.link is not None:   # the same event, live, to everyone on the link
            body = {"asset": asset}
            body.update({k: v for k, v in detail.items() if isinstance(v, (str, int, float, bool, list)) or v is None})
            self.link.send("*", ("asset." if asset != "-" else "queue.") + what, body)

    def job_result(self, asset, what, detail):
        """The Unreal half of jobs\\<Asset>.json (the Blender team writes the file; we add our numbers to it)."""
        path = os.path.join(self.folder, "jobs", asset + ".json")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                job = json.load(f)
            rep_path = os.path.join(self.reports, asset + ".json")
            meshes = []
            if os.path.exists(rep_path):
                with open(rep_path, encoding="utf-8") as f:
                    meshes = (json.load(f).get("unreal") or {}).get("meshes", [])
            job["unreal"] = {"result": what, "at": datetime.datetime.fromtimestamp(self.clock()).isoformat(timespec="seconds"),
                             "status": detail.get("result") or detail.get("why", ""), "unreal_path": detail.get("dest", ""),
                             "unreal_tris": sum(m.get("triangles", 0) for m in meshes),
                             "render_tris": sum(m.get("render_triangles", m.get("triangles", 0)) for m in meshes)}
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(job, f, indent=2)
            os.replace(tmp, path)
        except (OSError, ValueError):
            pass   # their file, their format: never let it stop the queue

    # -- the live link (ADR-053)

    def on_message(self, m):
        """Act on one link message; returns True when the board should be looked at right now."""
        kind, body = m.get("type", ""), m.get("body") or {}
        if kind == "ack":
            return False
        self.link.ack(m["id"])
        if kind == "ping":
            self.link.send(m["from"], "pong", {"waiting_on": self.waiting_on}, reply_to=m["id"])
            return False
        if kind == "asset.ready":
            asset = str(body.get("asset", ""))
            rows, header = parse(self.read())
            row = next((r for r in rows if r["asset"] == asset), None)
            if not asset or header is None:
                self.link.send(m["from"], "note", {"text": "asset.ready needs {asset}; QUEUE.md must have its table"},
                               reply_to=m["id"])
                return False
            if row is None:   # built assets enter the board by themselves
                self.write_board(add_row, asset, "READY", "added by the link (%s)" % m["from"])
                self.event(asset, "added", by=m["from"])
            elif state(row["status"]) not in ("SHIPPING",):
                self.blocked_at.pop(asset, None)
                self.update(asset, "READY", "ready via the link (%s)" % m["from"])
            return True
        if kind == "queue.status":
            self.link.send(m["from"], "queue.state", {"waiting_on": self.waiting_on, "counts": self.counts()},
                           reply_to=m["id"])
        return False

    def write_board(self, change, *args):
        return self._change_board(change, *args)

    def counts(self):
        rows, _ = parse(self.read())
        out = {}
        for r in rows:
            out[state(r["status"]) or "?"] = out.get(state(r["status"]) or "?", 0) + 1
        return out

    def summary(self):
        rows, _ = parse(self.read())
        counts = {}
        for r in rows:
            counts[state(r["status"]) or "?"] = counts.get(state(r["status"]) or "?", 0) + 1
        recent = []
        if os.path.exists(self.feed):
            with open(self.feed, encoding="utf-8") as f:
                recent = f.readlines()[-15:]
        now = datetime.datetime.fromtimestamp(self.clock()).isoformat(timespec="seconds")
        out = ["# Art board status", "", "Updated %s by the queue watcher." % now, ""]
        out.append("| " + " | ".join("%s %d" % (k, v) for k, v in sorted(counts.items())) + " |")
        out.append("|" + "---|" * len(counts))
        out.append("")
        out.append("**Waiting on:** %s" % (self.waiting_on or "none"))
        blender = os.path.join(self.folder, "STATUS-blender.json")
        if os.path.exists(blender):
            try:
                with open(blender, encoding="utf-8") as f:
                    b = json.load(f)
                out += ["", "**Blender team:** %s%s%s" % (b.get("state", "?"), (", " + str(b["group"])) if b.get("group") else "",
                                                          (" " + str(b["progress"])) if b.get("progress") else "")]
            except (OSError, ValueError):
                out += ["", "**Blender team:** (STATUS-blender.json unreadable)"]
        if self.waiting_on:
            mins = (self.clock() - self.waiting_since) / 60.0 if self.waiting_since else 0.0
            since = datetime.datetime.fromtimestamp(self.waiting_since).isoformat(timespec="seconds") if self.waiting_since else now
            out += ["", "**Waiting on:** %s (since %s, %.0f min)" % (self.waiting_on, since, mins)]
        todo = [r["asset"] for r in rows if state(r["status"]) == "TODO"]
        rejected = ["%s (%s)" % (r["asset"], r["status"]) for r in rows if state(r["status"]) == "REJECTED"]
        if rejected:
            out += ["", "**Needs a fix (Blender team):** " + "; ".join(rejected)]
        blocked = ["%s (%s)" % (r["asset"], r["status"][len("BLOCKED:"):].strip()) for r in rows
                   if state(r["status"]) == "BLOCKED"]
        if blocked:
            out += ["", "**Blocked on Unreal, not the asset (retrying on its own):** " + "; ".join(blocked)]
        shipping = [r["asset"] for r in rows if state(r["status"]) == "SHIPPING"]
        if shipping:
            out += ["", "**SHIPPING claims (kept until completion or owner reconciliation):** "
                    + ", ".join(shipping[:8]) + (" …" if len(shipping) > 8 else "")]
        if todo:
            out += ["", "**Up next (TODO):** " + ", ".join(todo[:8]) + (" …" if len(todo) > 8 else "")]
        out += ["", "## Last events", ""]
        for line in reversed(recent):
            try:
                e = json.loads(line)
                out.append("- %s  %s  %s  %s" % (e.get("at", ""), e.get("asset", ""), e.get("event", ""),
                                                 e.get("why", e.get("result", ""))))
            except ValueError:
                pass
        with open(self.status_md, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")

    # -- one pass

    def tick(self):
        done = self.reconcile_pending()
        held = {asset for asset, result in done if result in ("PUBLICATION_PENDING", "RECONCILIATION_REQUIRED")}
        rows, header = parse(self.read())
        uncertain = self.unresolved_imports(rows)
        if uncertain:
            # A lost reply can leave the previous editor operation running. Pause
            # this watcher's NEW calls, including unrelated assets, until its owner
            # verifies resolution. Completed reports above still publish normally.
            self.waiting_on = "Unreal import outcome unresolved; owner reconciliation required: " + ", ".join(sorted(uncertain)[:8])
            self.track_wait()
            self.summary()
            return done
        if self._producer is not None and self._producer.is_alive():
            self.waiting_on = "previous export producer still finishing; no new dispatch"
            self.track_wait()
            self.summary()
            return done
        if header is None:
            self.waiting_on = "QUEUE.md has no table with Asset and Status columns"
            self.track_wait()
            self.summary()
            return done
        now = self.clock()
        ready = [r for r in rows if r["asset"] not in held and (state(r["status"]) in ("READY", "WAITING")
                 or (state(r["status"]) == "BLOCKED" and now - self.blocked_at.get(r["asset"], 0) >= BLOCKED_RETRY_S))]
        if ready:
            up_b, up_u = wire.reachable(self.blender), wire.reachable(self.unreal)
            missing = [n for n, up in (("Blender (connector on 9876)", up_b), ("Unreal (bridge on 9877)", up_u)) if not up]
            self.waiting_on = (", ".join(missing) + " to be open") if missing else ""
            # Unreal won't load or save assets during Play ("The Editor is currently in a play mode"); never stop
            # someone's Play session, wait for it to end.
            if not missing:
                try:
                    playing = wire.call(self.unreal, "execute_python", timeout=30, side="Unreal", unattended=False,
                                        bridge_timeout=30, code=PLAYING)["result"]
                except (OSError, wire.BridgeError) as e:   # a reset socket is Unreal busy, not a watcher failure
                    self.waiting_on = "Unreal busy (%s); retrying" % type(e).__name__
                    missing = ["busy"]
                    playing = False
                if playing:
                    self.waiting_on = "Unreal to leave Play mode (assets can't be saved while playing)"
                    missing = ["play"]
            if not missing:
                assets = [r["asset"] for r in ready]
                if self.first:   # stable: the board's order within each group
                    assets.sort(key=lambda a: not any(f in a for f in self.first))
                if len(assets) > 1 and hasattr(self.ship, "export") and hasattr(self.ship, "land"):
                    done.extend(self.ship_overlapped(assets))
                else:
                    for a in assets:
                        result = self.ship_one(a)
                        done.append(result)
                        if result[1] == "UNCERTAIN_IMPORT":
                            break
        else:
            self.waiting_on = "queue publication/reconciliation required for %d asset(s)" % len(held) if held else ""
        self.track_wait()
        self.summary()
        return done

    def track_wait(self):
        """A wait's start and end go to the feed, with how long it lasted, so a digest can flag stalls."""
        if self.waiting_on and self.waiting_since is None:
            self.waiting_since = self.clock()
            self.event("-", "waiting", why=self.waiting_on)
        elif not self.waiting_on and self.waiting_since is not None:
            self.event("-", "resumed", waited_s=round(self.clock() - self.waiting_since))
            self.waiting_since = None

    def recover(self):
        """Reconcile matching publication witnesses; unknown SHIPPING stays uncertain."""
        return [asset for asset, result in self.reconcile_pending() if result == "SHIPPED"]

    def prepare(self, asset):
        """Blender's first steps for one asset: (asset, kind, objects), or a finished (asset, status) result."""
        pending = self.reconcile_publication(asset)
        if pending is not None:
            return pending
        kind = kind_of(asset)
        if not kind:
            self._require_update(asset, "REJECTED: name must start with one of " + "/".join(KINDS) + "_")
            self.event(asset, "rejected", why="bad name")
            return (asset, "REJECTED")
        blend = os.path.join(self.folder, kind, asset + ".blend")
        # Built elsewhere (a cloud Blender): <Kind>\<Asset>.glb with <Asset>.sent.json, Blender's report of what it
        # sent. No Blender on this PC is needed; the judge still checks report = file = Unreal.
        glb_path = os.path.join(self.folder, kind, asset + ".glb")
        sent_path = os.path.join(self.folder, kind, asset + ".sent.json")
        if not os.path.exists(blend) and os.path.exists(glb_path) and os.path.exists(sent_path):
            with open(sent_path, encoding="utf-8") as f:
                sent = json.load(f)
            names = [o["name"] for o in sent.get("objects", [])]
            if not names:
                self._require_update(asset, "REJECTED: %s.sent.json lists no objects" % asset)
                self.event(asset, "rejected", why="empty sent.json")
                return (asset, "REJECTED")
            self._claim(asset)
            self.event(asset, "shipping", objects=names, source="prebuilt glb")
            return (asset, kind, {"objects": names, "source": "prebuilt", "glb": glb_path, "sent": sent})
        # Open the file, never at the cost of someone's unsaved work.
        if os.path.exists(blend):
            opened = wire.call(self.blender, "execute_code", side="Blender", code=OPEN_BLEND % json.dumps(blend))["result"]
            if opened.get("blocked"):
                self._require_update(asset, "WAITING: Blender has unsaved work in %s; save it and I'll continue" % opened.get("current", "another file"))
                self.event(asset, "waiting", why="unsaved work in Blender")
                return (asset, "WAITING")
        objects = wire.call(self.blender, "execute_code", side="Blender", code=PICK_OBJECTS % json.dumps(asset))["result"]
        if not objects["objects"]:
            self._require_update(asset, "REJECTED: no meshes (make a collection named %s, or save %s\\%s.blend)" % (asset, kind, asset))
            self.event(asset, "rejected", why="no meshes")
            return (asset, "REJECTED")
        self._claim(asset)
        self.event(asset, "shipping", objects=objects["objects"], source=objects["source"])
        return (asset, kind, objects)

    def ship_one(self, asset):
        got = self.prepare(asset)
        if len(got) == 2:
            return got
        _, kind, objects = got
        try:
            self._stage(asset, "import-started")
            if objects.get("source") == "prebuilt":
                report = pipeline.land(pipeline.prebuilt(asset, objects["glb"], objects["sent"]), "/Game/Daedalus/Art/" + kind,
                                       True, self.unreal) if not hasattr(self.ship, "land") else \
                    self.ship.land(pipeline.prebuilt(asset, objects["glb"], objects["sent"]), "/Game/Daedalus/Art/" + kind, True, self.unreal)
            else:
                report = self.ship(asset, objects["objects"], "/Game/Daedalus/Art/" + kind,
                                   os.path.join(self.folder, "glb"), True, self.blender, self.unreal)
        except PublicationError:
            raise
        except Exception as e:
            self.event(asset, "error", why="import outcome uncertain: %s" % str(e)[:120])
            return (asset, "UNCERTAIN_IMPORT")  # Keep SHIPPING; an import may have succeeded before transport failed.
        return self.finish(asset, kind, report)

    def ship_overlapped(self, assets):
        """Ship many at once with the two editors working side by side: a Blender thread opens and exports each
        asset while this thread imports the previous one into Unreal. The board, feed and link are written under
        one lock, so the two never interleave a row."""
        if self._producer is not None and self._producer.is_alive():
            raise PublicationError("previous export producer still finishing; no new dispatch")
        results = []
        handoff = _queue.Queue(maxsize=2)   # Blender stays at most two exports ahead
        stop = threading.Event()

        def enqueue(item):
            while not stop.is_set():
                try:
                    handoff.put(item, timeout=HANDOFF_WAIT_S)
                    return True
                except _queue.Full:
                    pass
            return False

        def blender_side():
            for a in assets:
                if stop.is_set():
                    break
                try:
                    got = self.prepare(a)
                    if len(got) == 2:
                        results.append(got)
                        continue
                    _, kind, objects = got
                    if stop.is_set():
                        break  # Claimed, but export/import never started; retain the claim for reconciliation.
                    if objects.get("source") == "prebuilt":
                        rep = pipeline.prebuilt(a, objects["glb"], objects["sent"])
                    else:
                        rep = self.ship.export(a, objects["objects"], os.path.join(self.folder, "glb"), self.blender)
                    self._stage(a, "exported-not-imported")
                    if stop.is_set():
                        break
                    if not enqueue((a, kind, rep, None)):
                        break
                except Exception as e:
                    if not enqueue((a, None, None, e)):
                        break
            enqueue(None)

        t = threading.Thread(target=blender_side, name="artqueue-blender", daemon=True)
        self._producer = t
        t.start()
        try:
            while True:
                try:
                    item = handoff.get(timeout=HANDOFF_WAIT_S)
                except _queue.Empty:
                    if stop.is_set() or not t.is_alive():
                        break
                    continue
                if item is None:
                    break
                if stop.is_set():
                    break  # Queued exports are not evidence that any Unreal import started.
                a, kind, rep, err = item
                if err is not None:
                    if isinstance(err, PublicationError):
                        raise err
                    results.append(self.block(a, "pipeline error: %s" % str(err)[:120], "error"))
                    continue
                try:
                    self._stage(a, "import-started")
                    rep = self.ship.land(rep, "/Game/Daedalus/Art/" + kind, True, self.unreal)
                except PublicationError:
                    raise
                except Exception as e:
                    stop.set()  # Includes bridge EOF, decode and judge errors after dispatch.
                    self.event(a, "error", why="import outcome uncertain: %s" % str(e)[:120])
                    results.append((a, "UNCERTAIN_IMPORT"))
                    break
                results.append(self.finish(a, kind, rep))
                if len(results) % 10 == 0:
                    self.track_wait()
                    with self.lock:
                        self.summary()
        finally:
            stop.set()
            t.join(timeout=PRODUCER_JOIN_S)
            if not t.is_alive():
                self._producer = None
        return results

    def finish(self, asset, kind, report):
        checks = list(report["checks"])
        tris = sum(o["triangles"] for o in report["blender"]["objects"])
        checks.append({"check": "triangle budget (%s %d)" % (kind, BUDGET[kind]), "ok": tris <= BUDGET[kind],
                       "detail": "%d triangles" % tris})
        slots = max([len(o["materials"]) for o in report["blender"]["objects"]] or [0])
        checks.append({"check": "material slots ≤ %d" % MAX_SLOTS, "ok": slots <= MAX_SLOTS, "detail": "%d" % slots})
        report["checks"] = checks
        report["ok"] = all(c["ok"] for c in checks)
        dims = [max(o["dims"]) for o in report["blender"]["objects"]]
        if report["ok"]:
            result = "SHIPPED (%d tris, %.2f m)" % (tris, max(dims or [0]))
            report["_queue_publication"] = {"state": "pending", "asset": asset,
                "claim_token": self._claims.get(asset, ""), "status": result, "notes": "in Unreal: %s" % report["dest"]}
            self._pending_publications[asset] = report
            published = self.reconcile_publication(asset)
            if published[1] != "SHIPPED":
                return published
            return (asset, "SHIPPED")
        why = unreal_side_failure(report)
        self._save_report(asset, report)
        if why:
            return self.block(asset, why, "blocked")
        failed = next(c for c in checks if not c["ok"])
        self._owned_update(asset, "REJECTED: %s (%s)" % (failed["check"], failed["detail"]))
        self._pending_publications.pop(asset, None)
        self.event(asset, "rejected", why=failed["check"], detail=failed["detail"])
        return (asset, "REJECTED")

    def block(self, asset, why, event):
        self.blocked_at[asset] = self.clock()
        self._owned_update(asset, "BLOCKED: %s" % why, "not the asset's fault; retrying every %d s" % BLOCKED_RETRY_S)
        self._pending_publications.pop(asset, None)
        self.event(asset, event, why=why)
        return (asset, "BLOCKED")


PLAYING = "import unreal\nresult = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is not None\n"

# What runs inside Blender (through the connector's execute_code).

OPEN_BLEND = """
import bpy, os
path = %s
current = bpy.data.filepath
if os.path.normcase(os.path.abspath(current or '')) == os.path.normcase(os.path.abspath(path)):
    result = {"opened": False, "blocked": False, "current": current}
elif bpy.data.is_dirty and (current or bpy.data.objects):
    result = {"opened": False, "blocked": True, "current": current or "an unsaved scene"}
else:
    bpy.ops.wm.open_mainfile(filepath=path)
    result = {"opened": True, "blocked": False, "current": path}
"""

PICK_OBJECTS = """
import bpy
name = %s
coll = bpy.data.collections.get(name)
def meshes(c):
    out = [o.name for o in c.objects if o.type == 'MESH']
    for child in c.children:
        out += meshes(child)
    return out
if coll:
    result = {"source": "collection", "objects": sorted(set(meshes(coll)))}
else:
    result = {"source": "visible", "objects": sorted(o.name for o in bpy.context.scene.objects if o.type == 'MESH' and o.visible_get())}
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Watch the art queue and ship READY assets into Unreal.")
    ap.add_argument("--folder", default=DEFAULT_DIR)
    ap.add_argument("--every", type=float, default=10.0, help="seconds between passes")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-link", action="store_true", help="don't join the team link (ADR-053)")
    ap.add_argument("--first", default="", help="comma-separated name fragments to ship first (e.g. _Orr_)")
    a = ap.parse_args(argv)
    w = Watcher(a.folder)
    w.first = [f for f in a.first.split(",") if f]
    lock = os.path.join(a.folder, ".watcher.lock")
    if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 60:
        print("another legacy watcher may be running (%s is fresh)" % lock)
        return 3
    lease = WatcherLease(a.folder)
    if not lease.acquire():
        print("watcher admission held (%s); owner release/reconciliation required" % lease.path)
        return 3
    try:
        return watch(a, w, lock)
    finally:
        if w._producer is not None and w._producer.is_alive():
            print("watcher admission retained: previous export producer still finishing", flush=True)
        else:
            lease.release()
            # Only release the legacy compatibility heartbeat that this process wrote.
            try:
                with open(lock, encoding="utf-8") as stream:
                    owned = stream.read(64) == str(os.getpid())
                if owned:
                    os.unlink(lock)
            except OSError:
                pass


def watch(a, w, lock):
    link = None if a.no_link else teamlink.Link("unreal-team")
    w.link = link
    print("watching %s every %.0fs%s" % (w.queue, a.every, "" if link is None else ", live on the team link"))
    for asset in w.recover():
        print("reconciled %s from a completed publication witness; no re-import" % asset, flush=True)
    after = 0
    if link is not None and link.health():
        link.register("Unreal team (Claude): ships Blender art into Unreal", ["asset.ready", "ping", "queue.status"],
                      "send asset.ready {asset}; results come back as asset.* broadcasts")
        # Catch up first: anything sent to us while we were down and never acknowledged.
        for m in link.pending():
            w.on_message(m)
        after = (link.health() or {}).get("last", 0)
    while True:
        failed = False
        try:
            with open(lock, "w") as f:
                f.write(str(os.getpid()))
            for asset, result in w.tick():
                print(datetime.datetime.now().strftime("%H:%M:%S"), asset, result, flush=True)
        except Exception:   # keep watching; the trace goes to the feed
            failed = True
            w.event("-", "watcher-error", why=traceback.format_exc()[-400:])
        if a.once:
            return 1 if failed else 0
        if link is None:
            time.sleep(a.every)
            continue
        # Wait on the link instead of sleeping: a message wakes the watcher at once (asset.ready ships now).
        link.heartbeat("waiting on: " + w.waiting_on if w.waiting_on else "ok")
        if not link.health():
            time.sleep(a.every)   # no broker: fall back to the 10 s board pass
            continue
        deadline = time.time() + a.every
        while time.time() < deadline:
            msgs, after = link.wait(after, max(0.5, deadline - time.time()))
            if not link.up:
                break
            wake = False
            for m in msgs:
                try:
                    wake = w.on_message(m) or wake
                except Exception:
                    w.event("-", "link-error", why=traceback.format_exc()[-300:])
            if wake:
                break


if __name__ == "__main__":
    sys.exit(main())
