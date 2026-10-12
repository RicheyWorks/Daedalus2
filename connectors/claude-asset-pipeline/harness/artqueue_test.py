# SPDX-License-Identifier: MIT
"""The art queue watcher (ADR-051) against fake bridges: every path a row can take, and the board stays intact.

    python harness/artqueue_test.py        # prints n/m; exits 1 on a failure
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from asset_pipeline import artqueue, wire   # noqa: E402

BOARD = """# Art queue (Daedalus)

Some words.

| # | Asset | Kind | Size | Status | Notes |
|---|---|---|---|---|---|
| 1 | Tool_Pickaxe | tool | 0.9 m | READY | stone head |
| 2 | Item_Coal | item | 0.35 m | TODO | |
| 3 | Mob_BlightSlime | foe | 0.8 m | DOING (grok) | |
"""

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s %s" % ("ok  " if ok else "FAIL", name, detail))


PLAYING = {"on": False}


class FakeBlender:
    def __init__(self, dirty=False, current="", objects=("Pick_Handle", "Pick_Head")):
        self.dirty, self.current, self.objects, self.opened = dirty, current, list(objects), []

    def call(self, addr, command, timeout=600, side="bridge", **p):
        code = p["code"]
        if "get_game_world" in code:
            PLAYING["params"] = dict(p)
            return {"result": PLAYING["on"]}
        if "open_mainfile" in code:
            path = json.loads(code.split("path = ", 1)[1].split("\n", 1)[0])
            if os.path.normcase(self.current) == os.path.normcase(path):
                return {"result": {"opened": False, "blocked": False}}
            if self.dirty:
                return {"result": {"opened": False, "blocked": True, "current": self.current or "an unsaved scene"}}
            self.opened.append(path)
            self.current = path
            return {"result": {"opened": True, "blocked": False}}
        return {"result": {"source": "collection", "objects": self.objects}}


def report(ok=True, tris=1200, slots=2, failed=None):
    checks = [{"check": "triangles: Blender = file", "ok": failed != "tri", "detail": "x"}]
    return {"ok": ok, "checks": checks, "dest": "/Game/Daedalus/Art/Tool/Tool_Pickaxe",
            "blender": {"objects": [{"triangles": tris, "materials": ["m%d" % i for i in range(slots)], "dims": [0.9, 0.1, 0.3]}]}}


def setup(board=BOARD, blend=True, blender=None, up=(True, True), ship=None):
    d = tempfile.mkdtemp(prefix="artq-")
    with open(os.path.join(d, "QUEUE.md"), "w", encoding="utf-8") as f:
        f.write(board)
    if blend:
        os.makedirs(os.path.join(d, "Tool"))
        open(os.path.join(d, "Tool", "Tool_Pickaxe.blend"), "wb").close()
    fb = blender or FakeBlender()
    wire.call = fb.call
    wire.reachable = lambda addr, timeout=2.0: up[0] if addr == wire.BLENDER else up[1]
    w = artqueue.Watcher(d, ship=ship or (lambda *a, **k: report()), clock=lambda: 1760000000)
    return d, w, fb


def row(d, asset):
    rows, _ = artqueue.parse(open(os.path.join(d, "QUEUE.md"), encoding="utf-8").read())
    return next(r for r in rows if r["asset"] == asset)


def feed(d):
    p = os.path.join(d, "feed.jsonl")
    return [json.loads(x) for x in open(p, encoding="utf-8")] if os.path.exists(p) else []


# 1. the board parses; set_row touches one row only
rows, header = artqueue.parse(BOARD)
check("parses three rows", [r["asset"] for r in rows] == ["Tool_Pickaxe", "Item_Coal", "Mob_BlightSlime"])
changed = artqueue.set_row(BOARD, "Item_Coal", "DOING (claude)", "on it")
diff = [(a, b) for a, b in zip(BOARD.split("\n"), changed.split("\n")) if a != b]
check("set_row changes exactly one line", len(diff) == 1 and "DOING (claude)" in diff[0][1] and "on it" in diff[0][1])
check("state() reads the word", artqueue.state("REJECTED: x") == "REJECTED" and artqueue.state("doing (x)") == "DOING")

# 2. bridges down: hands off, and the status says why
d, w, fb = setup(up=(False, True))
w.tick()
check("bridges down: row left READY", row(d, "Tool_Pickaxe")["status"] == "READY")
check("bridges down: STATUS.md names Blender", "Blender" in open(os.path.join(d, "STATUS.md"), encoding="utf-8").read())
shutil.rmtree(d)

# 2b. Unreal in Play: wait, don't touch; the wait is timed for stall detection
d, w, fb = setup()
clock = {"t": 1760000000}
w.clock = lambda: clock["t"]
PLAYING["on"] = True
w.tick()
clock["t"] += 12 * 60
w.tick()
check("wait: STATUS.md says how long", "12 min" in open(os.path.join(d, "STATUS.md"), encoding="utf-8").read())
check("unreal playing: row left READY", row(d, "Tool_Pickaxe")["status"] == "READY")
check("unreal playing: STATUS.md says Play", "Play mode" in open(os.path.join(d, "STATUS.md"), encoding="utf-8").read())
PLAYING["on"] = False
w.tick()
check("unreal playing: ships after Play ends", row(d, "Tool_Pickaxe")["status"].startswith("SHIPPED"))
ev = [e for e in feed(d) if e["asset"] == "-"]
check("wait: feed has waiting then resumed with seconds", [e["event"] for e in ev] == ["waiting", "resumed"] and ev[1]["waited_s"] == 720, str(ev))
shutil.rmtree(d)

# 3. the happy path
d, w, fb = setup()
w.tick()
r = row(d, "Tool_Pickaxe")
check("shipped: row says SHIPPED with tris", r["status"].startswith("SHIPPED (1200 tris"), r["status"])
check("shipped: the .blend was opened", len(fb.opened) == 1)
check("shipped: report saved", os.path.exists(os.path.join(d, "reports", "Tool_Pickaxe.json")))
check("shipped: feed has shipping then shipped", [e["event"] for e in feed(d)] == ["shipping", "shipped"])
check("shipped: other rows untouched", row(d, "Mob_BlightSlime")["status"] == "DOING (grok)")
w.tick()
check("shipped rows are not shipped again", [e["event"] for e in feed(d)].count("shipped") == 1)
shutil.rmtree(d)

# 4. someone's unsaved work is never thrown away
d, w, fb = setup(blender=FakeBlender(dirty=True, current="C:/art/Mob/Mob_Other.blend"))
w.tick()
check("unsaved work: row WAITING, nothing opened", row(d, "Tool_Pickaxe")["status"].startswith("WAITING") and not fb.opened)
fb.dirty = False
w.tick()
check("unsaved work: ships once it's saved", row(d, "Tool_Pickaxe")["status"].startswith("SHIPPED"))
shutil.rmtree(d)

# 5. over the triangle budget
d, w, fb = setup(ship=lambda *a, **k: report(tris=9000))
w.tick()
check("over budget: REJECTED names the budget", "triangle budget" in row(d, "Tool_Pickaxe")["status"], row(d, "Tool_Pickaxe")["status"])
shutil.rmtree(d)

# 6. too many material slots
d, w, fb = setup(ship=lambda *a, **k: report(slots=5))
w.tick()
check("five slots: REJECTED names slots", "material slots" in row(d, "Tool_Pickaxe")["status"])
shutil.rmtree(d)

# 7. the judge's own failure is passed on
d, w, fb = setup(ship=lambda *a, **k: report(ok=False, failed="tri"))
w.tick()
check("judge failure: REJECTED names its check", "triangles: Blender = file" in row(d, "Tool_Pickaxe")["status"])
shutil.rmtree(d)

# 8. a bad name
d, w, fb = setup(board=BOARD.replace("Tool_Pickaxe", "Pickaxe"), blend=False)
w.tick()
check("bad name: REJECTED with the prefixes", row(d, "Pickaxe")["status"].startswith("REJECTED: name must start"))
shutil.rmtree(d)

# 9. no meshes
d, w, fb = setup(blender=FakeBlender(objects=()))
w.tick()
check("no meshes: REJECTED says how to fix", "no meshes" in row(d, "Tool_Pickaxe")["status"])
shutil.rmtree(d)


# 10. a bridge error mid-ship: back to READY with a note; the watcher lives
def boom(*a, **k):
    raise wire.BridgeError("Unreal", {"message": "import failed"})


d, w, fb = setup(ship=boom)
w.tick()
r = row(d, "Tool_Pickaxe")
check("bridge error: BLOCKED, not REJECTED, with a retry note", r["status"].startswith("BLOCKED: pipeline error")
      and "retrying" in r["notes"], str(r))
check("bridge error: feed says error", feed(d)[-1]["event"] == "error")
check("bridge error: STATUS.md says blocked on Unreal", "Blocked on Unreal" in open(os.path.join(d, "STATUS.md"), encoding="utf-8").read())
shutil.rmtree(d)


# 10b. Unreal imports nothing while Blender and the file were fine (today's import during a game test): BLOCKED,
#      retried by itself after BLOCKED_RETRY_S, and it ships once Unreal behaves.
def unreal_made_nothing(*a, **k):
    rep = report(ok=False)
    rep["checks"] = [{"check": n, "ok": True, "detail": ""} for n in artqueue.BLENDER_SIDE] + [
        {"check": "every file mesh became an Unreal static mesh", "ok": False, "detail": "file 2, Unreal 0"}]
    rep["unreal"] = {"meshes": [], "materials": []}
    return rep


outcome = {"fn": unreal_made_nothing}
d, w, fb = setup(ship=lambda *a, **k: outcome["fn"](*a, **k))
clock = {"t": 1760000000}
w.clock = lambda: clock["t"]
w.tick()
check("unreal made nothing: BLOCKED, not REJECTED", row(d, "Tool_Pickaxe")["status"].startswith("BLOCKED: Unreal imported nothing"),
      row(d, "Tool_Pickaxe")["status"])
outcome["fn"] = lambda *a, **k: report()
clock["t"] += 10
w.tick()
check("blocked: not retried before the pause", row(d, "Tool_Pickaxe")["status"].startswith("BLOCKED"))
clock["t"] += artqueue.BLOCKED_RETRY_S
w.tick()
check("blocked: retried by itself and shipped", row(d, "Tool_Pickaxe")["status"].startswith("SHIPPED"), row(d, "Tool_Pickaxe")["status"])
shutil.rmtree(d)

# 10c. Blender's side wrong and Unreal empty: the asset's fault, still REJECTED.
def blender_wrong(*a, **k):
    rep = unreal_made_nothing()
    rep["checks"][1]["ok"] = False
    rep["checks"][1]["detail"] = "Blender 10, file 8"
    return rep


d, w, fb = setup(ship=blender_wrong)
w.tick()
check("blender side wrong: REJECTED names the check", row(d, "Tool_Pickaxe")["status"].startswith("REJECTED: triangles: Blender = file"),
      row(d, "Tool_Pickaxe")["status"])
check("unreal_side_failure says '' for a healthy report", artqueue.unreal_side_failure(report()) == "")
check("an import error message is blocked with its words",
      "boom" in artqueue.unreal_side_failure({"checks": [{"check": n, "ok": True} for n in artqueue.BLENDER_SIDE],
                                              "unreal": {"error": "boom", "meshes": [1]}}))
shutil.rmtree(d)

# 11. someone edits the board mid-write: their edit survives
d, w, fb = setup()
real = w.read
calls = {"n": 0}


def racing_read():
    text = real()
    calls["n"] += 1
    if calls["n"] == 1:   # just after our first read, a bot claims Item_Coal on disk
        with open(w.queue, "w", encoding="utf-8") as f:
            f.write(artqueue.set_row(text, "Item_Coal", "DOING (chatgpt)"))
    return text if calls["n"] == 1 else real()


w.read = racing_read
w.update("Tool_Pickaxe", "SHIPPING")
w.read = real
check("race: their claim survives", row(d, "Item_Coal")["status"] == "DOING (chatgpt)")
check("race: our change landed too", row(d, "Tool_Pickaxe")["status"] == "SHIPPING")
shutil.rmtree(d)

# 12. the Blender-side open script itself (run against a stub bpy): unsaved work blocks, a clean file opens
import types   # noqa: E402


def run_open(current, dirty, objects, path="C:/art/Tool/Tool_Pickaxe.blend"):
    opened = []
    bpy = types.SimpleNamespace(
        data=types.SimpleNamespace(filepath=current, is_dirty=dirty, objects=objects),
        ops=types.SimpleNamespace(wm=types.SimpleNamespace(open_mainfile=lambda filepath: opened.append(filepath))))
    sys.modules["bpy"] = bpy
    scope = {}
    exec(artqueue.OPEN_BLEND % json.dumps(path), scope)
    del sys.modules["bpy"]
    return scope["result"], opened


res, opened = run_open("C:/art/Mob/Other.blend", True, ["Cube"])
check("blender script: unsaved other file blocks", res["blocked"] and not opened)
res, opened = run_open("", True, ["Cube"])
check("blender script: unsaved new scene blocks", res["blocked"] and not opened)
res, opened = run_open("C:/art/Mob/Other.blend", False, ["Cube"])
check("blender script: saved file is swapped for the asset", res["opened"] and opened)
res, opened = run_open("C:/art/Tool/Tool_Pickaxe.blend", True, ["Cube"])
check("blender script: already open (even unsaved) is used as is", not res["blocked"] and not opened)

# 13. The Blender team's fenced row block: its rows are on the board, and our own new rows go above it.
FENCED = BOARD + "<!-- blender-team rows: begin -->\n| 200 | Prop_Fern | prop | 0.6 m | READY | judged |\n<!-- blender-team rows: end -->\n"
rows, _ = artqueue.parse(FENCED)
check("fenced block: its rows are read as board rows", [r["asset"] for r in rows][-1] == "Prop_Fern" and len(rows) == 4)
added = artqueue.add_row(FENCED, "Tool_Axe", "READY", "via link")
lines = added.split("\n")
check("fenced block: our new row goes above their block", lines.index("<!-- blender-team rows: begin -->")
      > next(i for i, l in enumerate(lines) if "Tool_Axe" in l))
check("fenced block: and is numbered past every row", "| 201 | Tool_Axe |" in added, added)

# 14. A reset socket during the Play check is Unreal busy: wait, don't crash.
def resetting(addr, command, timeout=600, side="bridge", **p):
    if "get_game_world" in p["code"]:
        raise ConnectionResetError(10054, "forcibly closed")
    return FakeBlender().call(addr, command, timeout, side, **p)


d, w, fb = setup()
wire.call = resetting
w.tick()
check("socket reset: row left READY, no watcher error", row(d, "Tool_Pickaxe")["status"] == "READY"
      and not any(e["event"] == "watcher-error" for e in feed(d)))
check("socket reset: STATUS.md says Unreal busy", "Unreal busy" in open(os.path.join(d, "STATUS.md"), encoding="utf-8").read())
shutil.rmtree(d)

# 15. jobs\<Asset>.json gets the Unreal half; STATUS.md shows the Blender team's line.
d, w, fb = setup()
os.makedirs(os.path.join(d, "jobs"))
with open(os.path.join(d, "jobs", "Tool_Pickaxe.json"), "w", encoding="utf-8") as f:
    json.dump({"asset": "Tool_Pickaxe", "tris": 1200}, f)
with open(os.path.join(d, "STATUS-blender.json"), "w", encoding="utf-8") as f:
    json.dump({"state": "building", "group": "tools", "progress": "4/12"}, f)
w.tick()
job = json.load(open(os.path.join(d, "jobs", "Tool_Pickaxe.json"), encoding="utf-8"))
check("jobs json: their half kept, ours added", job["tris"] == 1200 and job["unreal"]["result"] == "shipped"
      and job["unreal"]["unreal_path"].endswith("Tool_Pickaxe"), job)
st = open(os.path.join(d, "STATUS.md"), encoding="utf-8").read()
check("STATUS.md: one line from STATUS-blender.json", "**Blender team:** building, tools 4/12" in st, st[:400])
check("STATUS.md: always says what it waits on", "**Waiting on:** none" in st)
shutil.rmtree(d)

# 12. Overlapped shipping (ADR-055): Blender exports the next asset while Unreal imports this one; one bad import
#     blocks only itself; the Play check goes straight to the game thread with a bounded wait.
import threading as _th   # noqa: E402
import time as _time      # noqa: E402
BOARD4 = """| # | Asset | Kind | Size | Status | Notes |
|---|---|---|---|---|---|
| 1 | Prop_A | prop | 1 m | READY | |
| 2 | Prop_B | prop | 1 m | READY | |
| 3 | Prop_C | prop | 1 m | READY | |
| 4 | Prop_D | prop | 1 m | READY | |
"""
seen = {"export": [], "land": []}


def _export(name, objects, folder, blender):
    seen["export"].append((name, _th.current_thread().name, _time.time()))
    _time.sleep(0.25)
    r = report()
    r.update(name=name)
    return r


def _land(rep, dest, save, unreal):
    seen["land"].append((rep["name"], _th.current_thread().name, _time.time()))
    _time.sleep(0.25)
    if rep["name"] == "Prop_C":
        raise OSError("bridge reset")
    rep["dest"] = dest + "/" + rep["name"]
    return rep


def _seq(*a, **k):
    raise AssertionError("the overlapped path should be used")


_seq.export, _seq.land = _export, _land
d, w, fb = setup(board=BOARD4, blend=False, ship=_seq)
fb.objects = ["Mesh"]
t0 = _time.time()
out = w.tick()
took = _time.time() - t0
got = dict(out)
check("overlapped: all four handled", sorted(got) == ["Prop_A", "Prop_B", "Prop_C", "Prop_D"], out)
check("overlapped: the three good ones ship, the bad import is BLOCKED (Unreal's fault, retried)",
      [got[a] for a in ("Prop_A", "Prop_B", "Prop_D")] == ["SHIPPED"] * 3 and got["Prop_C"] == "BLOCKED", got)
check("overlapped: exports run on the Blender thread, imports on this one",
      {t for _, t, _ in seen["export"]} == {"artqueue-blender"} and "artqueue-blender" not in {t for _, t, _ in seen["land"]},
      seen)
check("overlapped: imports keep the board's order", [n for n, _, _ in seen["land"]] == ["Prop_A", "Prop_B", "Prop_C", "Prop_D"])
check("overlapped: faster than one at a time (8 x 0.25 s in sequence)", took < 1.6, "%.2f s" % took)
check("overlapped: an export overlaps an import", any(e[2] < l[2] + 0.25 and e[2] > l[2]
      for e in seen["export"] for l in seen["land"]), seen)
check("the Play check runs on the game thread with a bounded wait (no Remote Execution channel)",
      PLAYING.get("params", {}).get("unattended") is False and PLAYING["params"].get("bridge_timeout") == 30,
      PLAYING.get("params"))
board_after = open(os.path.join(d, "QUEUE.md"), encoding="utf-8").read()
check("overlapped: the board is still one table of four rows", len(artqueue.parse(board_after)[0]) == 4, board_after)
shutil.rmtree(d)

n = sum(results)
print("%d/%d" % (n, len(results)))
sys.exit(0 if n == len(results) else 1)
