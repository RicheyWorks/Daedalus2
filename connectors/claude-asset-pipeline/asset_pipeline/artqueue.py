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

Only the Status and Notes cells of a row are ever rewritten, and only when the file hasn't changed underneath
(read, compute, re-read, compare, write), so a bot editing another row at the same moment is not overwritten.

    python -m asset_pipeline.artqueue --once            # one pass
    python -m asset_pipeline.artqueue --every 10        # watch (Ctrl+C to stop)
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import traceback

from . import ship as pipeline
from . import teamlink
from . import wire

DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "projects", "bot-team", "art")
KINDS = ("Tool", "Item", "Mob", "Veh", "Bld", "Prop", "Sky", "Wpn")
# Triangle budgets by kind (BRIEF.md).
BUDGET = {"Tool": 3000, "Item": 3000, "Wpn": 3000, "Prop": 3000, "Mob": 6000, "Veh": 12000, "Bld": 15000,
          "Sky": 15000}
MAX_SLOTS = 3


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
        for _ in range(5):
            before = self.read()
            after = set_row(before, asset, status, notes)
            if self.read() != before:
                continue
            tmp = self.queue + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(after)
            os.replace(tmp, self.queue)
            return True
        return False

    def event(self, asset, what, **detail):
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
        for _ in range(5):
            before = self.read()
            after = change(before, *args)
            if self.read() != before:
                continue
            tmp = self.queue + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(after)
            os.replace(tmp, self.queue)
            return True
        return False

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
        rows, header = parse(self.read())
        if header is None:
            self.waiting_on = "QUEUE.md has no table with Asset and Status columns"
            self.track_wait()
            self.summary()
            return []
        now = self.clock()
        ready = [r for r in rows if state(r["status"]) in ("READY", "WAITING")
                 or (state(r["status"]) == "BLOCKED" and now - self.blocked_at.get(r["asset"], 0) >= BLOCKED_RETRY_S)]
        done = []
        if ready:
            up_b, up_u = wire.reachable(self.blender), wire.reachable(self.unreal)
            missing = [n for n, up in (("Blender (connector on 9876)", up_b), ("Unreal (bridge on 9877)", up_u)) if not up]
            self.waiting_on = (", ".join(missing) + " to be open") if missing else ""
            # Unreal won't load or save assets during Play ("The Editor is currently in a play mode"); never stop
            # someone's Play session, wait for it to end.
            if not missing:
                try:
                    playing = wire.call(self.unreal, "execute_python", side="Unreal", code=PLAYING)["result"]
                except (OSError, wire.BridgeError) as e:   # a reset socket is Unreal busy, not a watcher failure
                    self.waiting_on = "Unreal busy (%s); retrying" % type(e).__name__
                    missing = ["busy"]
                    playing = False
                if playing:
                    self.waiting_on = "Unreal to leave Play mode (assets can't be saved while playing)"
                    missing = ["play"]
            if not missing:
                for r in ready:
                    done.append(self.ship_one(r["asset"]))
        else:
            self.waiting_on = ""
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

    def ship_one(self, asset):
        kind = kind_of(asset)
        if not kind:
            self.update(asset, "REJECTED: name must start with one of " + "/".join(KINDS) + "_")
            self.event(asset, "rejected", why="bad name")
            return (asset, "REJECTED")
        blend = os.path.join(self.folder, kind, asset + ".blend")
        # Open the file, never at the cost of someone's unsaved work.
        if os.path.exists(blend):
            opened = wire.call(self.blender, "execute_code", side="Blender", code=OPEN_BLEND % json.dumps(blend))["result"]
            if opened.get("blocked"):
                self.update(asset, "WAITING: Blender has unsaved work in %s; save it and I'll continue" % opened.get("current", "another file"))
                self.event(asset, "waiting", why="unsaved work in Blender")
                return (asset, "WAITING")
        objects = wire.call(self.blender, "execute_code", side="Blender", code=PICK_OBJECTS % json.dumps(asset))["result"]
        if not objects["objects"]:
            self.update(asset, "REJECTED: no meshes (make a collection named %s, or save %s\\%s.blend)" % (asset, kind, asset))
            self.event(asset, "rejected", why="no meshes")
            return (asset, "REJECTED")
        self.update(asset, "SHIPPING")
        self.event(asset, "shipping", objects=objects["objects"], source=objects["source"])
        try:
            report = self.ship(asset, objects["objects"], "/Game/Daedalus/Art/" + kind,
                               os.path.join(self.folder, "glb"), True, self.blender, self.unreal)
        except Exception as e:   # a bridge error is Unreal's (or Blender's) problem, not the asset's
            return self.block(asset, "pipeline error: %s" % str(e)[:120], "error")
        checks = list(report["checks"])
        tris = sum(o["triangles"] for o in report["blender"]["objects"])
        checks.append({"check": "triangle budget (%s %d)" % (kind, BUDGET[kind]), "ok": tris <= BUDGET[kind],
                       "detail": "%d triangles" % tris})
        slots = max([len(o["materials"]) for o in report["blender"]["objects"]] or [0])
        checks.append({"check": "material slots ≤ %d" % MAX_SLOTS, "ok": slots <= MAX_SLOTS, "detail": "%d" % slots})
        report["checks"] = checks
        report["ok"] = all(c["ok"] for c in checks)
        os.makedirs(self.reports, exist_ok=True)
        with open(os.path.join(self.reports, asset + ".json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        dims = [max(o["dims"]) for o in report["blender"]["objects"]]
        if report["ok"]:
            result = "SHIPPED (%d tris, %.2f m)" % (tris, max(dims or [0]))
            self.update(asset, result, "in Unreal: %s" % report["dest"])
            self.event(asset, "shipped", result=result, dest=report["dest"])
            return (asset, "SHIPPED")
        why = unreal_side_failure(report)
        if why:
            return self.block(asset, why, "blocked")
        failed = next(c for c in checks if not c["ok"])
        self.update(asset, "REJECTED: %s (%s)" % (failed["check"], failed["detail"]))
        self.event(asset, "rejected", why=failed["check"], detail=failed["detail"])
        return (asset, "REJECTED")


    def block(self, asset, why, event):
        self.blocked_at[asset] = self.clock()
        self.update(asset, "BLOCKED: %s" % why, "not the asset's fault; retrying every %d s" % BLOCKED_RETRY_S)
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
    a = ap.parse_args(argv)
    link = None if a.no_link else teamlink.Link("unreal-team")
    w = Watcher(a.folder, link=link)
    lock = os.path.join(a.folder, ".watcher.lock")
    if not a.once:
        if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 60:
            print("another watcher is running (%s is fresh)" % lock)
            return 3
    print("watching %s every %.0fs%s" % (w.queue, a.every, "" if link is None else ", live on the team link"))
    after = 0
    if link is not None and link.health():
        # Catch up first: anything sent to us while we were down and never acknowledged.
        for m in link.pending():
            w.on_message(m)
        after = (link.health() or {}).get("last", 0)
    while True:
        try:
            with open(lock, "w") as f:
                f.write(str(os.getpid()))
            for asset, result in w.tick():
                print(datetime.datetime.now().strftime("%H:%M:%S"), asset, result, flush=True)
        except Exception:   # keep watching; the trace goes to the feed
            w.event("-", "watcher-error", why=traceback.format_exc()[-400:])
        if a.once:
            return 0
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
