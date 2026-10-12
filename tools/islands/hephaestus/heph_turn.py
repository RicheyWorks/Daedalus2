# SPDX-License-Identifier: MIT
"""Hephaestus's 10-minute editor turn (referee equal-turn order: youtube-master -> hephaestus -> pythagoras). Run ONLY for a granted turn.
    python heph_turn.py [--now]
The referee HOLDS the turn clock while the editor is down, so every slot after the hold shifts. This runner is therefore
handoff-driven, not clock-driven: it never starts before EARLIEST, and it starts only when the previous holder (youtube-master)
posts a HANDOFF, or the referee (buffffff) / 2hot2trot posts a GRANT or GO addressed to hephaestus. No fixed-time fallback.
The 10 minutes are counted from the moment it starts: work hard-stops at start+8 min, Play stop + save by start+9 min.
Then: ping bridge (retries while the editor comes back) -> stop Play if running -> heph_island_ue.run() -> hero shot -> save ->
post DONE + HANDOFF -> pythagoras. Bridge port: HEPH_BRIDGE_PORT (default 9877; editor B in the multi-editor plan is 9878).
Whatever fails, it stops Play and saves."""
import base64, datetime as dt, json, os, re, socket, sys, time

REPO = r"C:\Users\730ri\projects\Daedalus2"
TOOL = REPO + r"\tools\islands\hephaestus"
LINK = r"C:\Users\730ri\projects\bot-team\link"
SHOTS = r"C:\Users\730ri\projects\bot-team\shots\hephaestus"
OUTBOX = LINK + r"\outbox\hephaestus.jsonl"
PREV = os.environ.get("HEPH_PREV", "youtube-master")
NEXT = os.environ.get("HEPH_NEXT", "pythagoras")
GRANTERS = ("buffffff", "2hot2trot")
PORT = int(os.environ.get("HEPH_BRIDGE_PORT", "9877"))
TODAY = dt.date.today()
EARLIEST = dt.datetime.combine(TODAY, dt.time(17, 43))  # referee slot before any hold shift; never earlier
SINCE = dt.datetime.combine(TODAY, dt.time(17, 30))     # only HANDOFF/GRANT posts newer than this count
GIVE_UP = dt.datetime.combine(TODAY, dt.time(21, 0))    # stop waiting; post BLOCKED and go to the back of the line
TURN_S, WORK_S, SAVE_S = 600, 480, 60
# a real handoff names us as the receiver ("HANDOFF youtube-master -> hephaestus"); "going after disk-saver HANDOFF" must not count
HANDOFF_US = re.compile(r"HANDOFF[^.]{0,60}?(->|\\u2192|\u2192|\bto\b)\s*hephaestus", re.I)
GRANT_US = re.compile(r"GRANT[^.]{0,40}?hephaestus|GO hephaestus", re.I)
LOG = []
T0 = None
HARD_STOP = None


def say(m):
    line = f"[{dt.datetime.now():%H:%M:%S}] {m}"; print(line, flush=True); LOG.append(line)


def link(text, to="*"):
    with open(OUTBOX, "a", encoding="utf-8") as f:
        f.write(json.dumps({"from": "hephaestus", "to": to, "type": "note", "body": {"text": text}}) + "\n")


def _tail():
    p = LINK + r"\log.jsonl"
    try:
        with open(p, "rb") as f:
            f.seek(max(0, os.path.getsize(p) - 2_000_000)); return f.read().decode("utf-8", "ignore")
    except OSError: return ""


def go_signal(since):
    """Who cleared us to start: PREV's HANDOFF, or a GRANT/GO to hephaestus from the referee or 2hot2trot (newer than `since`)."""
    for line in _tail().splitlines()[::-1]:
        if "HANDOFF" not in line and "GRANT" not in line and "GO" not in line: continue
        try: r = json.loads(line)
        except ValueError: continue
        try:
            if dt.datetime.fromisoformat(str(r.get("ts", ""))[:19]) < since: continue
        except ValueError: continue
        text = json.dumps(r.get("body", {}))
        src = r.get("from")
        if src == PREV and (HANDOFF_US.search(text) or "TURN DONE" in text): return f"{PREV} HANDOFF #{r.get('id')}"
        if src in GRANTERS and ((r.get("to") == "hephaestus" and re.search(r"\bGRANT|\bGO\b", text)) or GRANT_US.search(text)):
            return f"{src} GRANT #{r.get('id')}"
    return None


def call(kind, timeout=60, **params):
    params["bridge_timeout"] = timeout
    with socket.create_connection(("127.0.0.1", PORT), timeout=timeout + 10) as s:
        s.sendall((json.dumps({"id": int(time.time() * 1000), "type": kind, "params": params}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk: break
            buf += chunk
    r = json.loads(buf)
    if r.get("status") != "ok": raise RuntimeError(f"{kind}: {r.get('message')}")
    return r.get("result", {})


def left(): return (HARD_STOP - dt.timedelta(seconds=SAVE_S) - dt.datetime.now()).total_seconds()


def main():
    global T0, HARD_STOP
    why = "--now"
    if "--now" not in sys.argv:
        why = None
        while dt.datetime.now() < GIVE_UP:
            if dt.datetime.now() >= EARLIEST:
                why = go_signal(SINCE)
                if why: break
            time.sleep(5)
        if not why:
            say(f"no HANDOFF from {PREV} and no GRANT by {GIVE_UP:%H:%M}; not starting")
            link(f"BLOCKED editor turn (hephaestus): no HANDOFF from {PREV} or referee GRANT by {GIVE_UP:%H:%M}; "
                 "did not touch the editor. Back of the line; need a new turn.")
            return None
    T0 = time.time()
    start = dt.datetime.now()
    HARD_STOP = start + dt.timedelta(seconds=WORK_S + SAVE_S)
    say(f"go: {why}; work until {start + dt.timedelta(seconds=WORK_S):%H:%M:%S}, saved by {HARD_STOP:%H:%M:%S}, port {PORT}")
    os.makedirs(SHOTS, exist_ok=True)
    link(f"TURN START hephaestus {start:%H:%M}-{start + dt.timedelta(seconds=TURN_S):%H:%M} (after {why}): "
         "DOING, placing Hephaestus Island in its own sublevel")
    p = None
    while p is None and left() > 60:
        try: p = call("ping", timeout=15)
        except Exception as e: say(f"bridge not up yet ({e}); retrying"); time.sleep(10)
    if p is None: raise RuntimeError(f"bridge 127.0.0.1:{PORT} never answered")
    say(f"editor: {p.get('level')} playing={p.get('playing')}")
    if p.get("playing"): call("stop")
    code = (f"import runpy,sys; sys.path.insert(0, r'{TOOL}'); "
            f"result = runpy.run_path(r'{TOOL}\\heph_island_ue.py', run_name='heph_turn')['run']()")
    isle = call("execute_python", timeout=int(max(30, left() - 25)), code=code).get("result"); say(f"island: {isle}")
    if isle and left() > 15:
        cam, rot = isle["cam"], isle["cam_rot"]
        call("execute_python", timeout=15, code="import unreal; unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)."
             f"set_level_viewport_camera_info(unreal.Vector({cam[0]},{cam[1]},{cam[2]}), unreal.Rotator(roll=0,pitch={rot[0]},yaw={rot[1]}))")
        time.sleep(3)
        r = call("viewport_screenshot", timeout=30, width=1920, height=1080)
        path = os.path.join(SHOTS, "hero_unreal_editor.png")
        with open(path, "wb") as f: f.write(base64.b64decode(r["image_png_base64"]))
        say(f"shot {path}")
    return isle


if __name__ == "__main__":
    ok, err, isle = True, "", None
    try:
        isle = main()
        if isle is None and T0 is None: sys.exit(0)
        ok = bool(isle and isle.get("ok"))
    except Exception as e: ok, err = False, str(e); say(f"FAIL {e}")
    finally:
        if T0 is not None:
            for step, fn in (("stop", lambda: call("stop", timeout=20)), ("save", lambda: call("save", timeout=60))):
                try: fn(); say(step)
                except Exception as e: say(f"{step} failed: {e}")
            secs = time.time() - T0
            summary = (f"placed {isle['placed']}/{isle['want']}, imported {isle['imported']} hero glbs, missing {isle['missing']}"
                       if isle else "no placement result")
            link(f"{'DONE' if ok else 'BLOCKED'} island:hephaestus editor turn {secs:.0f}s: {summary}; sublevel "
                 f"/Game/Hephaestus/Maps/HephaestusIsland at 6000000,2000000; shot in {SHOTS}" + ("" if ok else f" | {err[:200]}") +
                 " | Play stopped, saved")
            link(f"TURN DONE + HANDOFF hephaestus -> {NEXT}: editor saved, Play stopped")
            os.makedirs(SHOTS, exist_ok=True)
            open(os.path.join(SHOTS, "turn.log"), "w").write("\n".join(LOG))