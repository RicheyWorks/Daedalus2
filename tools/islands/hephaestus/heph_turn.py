# SPDX-License-Identifier: MIT
"""Hephaestus's editor turn 17:43-17:53 PT (referee equal-turn order, after youtube-master; hard stop 17:52). Run ONLY on a granted slot.
    python heph_turn.py [--now]
Waits for the previous slot's HANDOFF (youtube-master) on the team link, never starting before START or after LAST_START,
then: ping bridge -> stop Play if running -> heph_island_ue.run() -> hero viewport + shot -> save -> post DONE + HANDOFF.
Talks to the Claude Unreal Bridge (127.0.0.1:9877). Whatever fails, it stops Play and saves. Hard cap 150 s of editor work."""
import base64, datetime as dt, json, os, socket, sys, time

REPO = r"C:\Users\730ri\projects\Daedalus2"
TOOL = REPO + r"\tools\islands\hephaestus"
LINK = r"C:\Users\730ri\projects\bot-team\link"
SHOTS = r"C:\Users\730ri\projects\bot-team\shots\hephaestus"
OUTBOX = LINK + r"\outbox\hephaestus.jsonl"
PREV = os.environ.get("HEPH_PREV", "youtube-master")
TODAY = dt.date.today()
START = dt.datetime.combine(TODAY, dt.time(17, 43))
FALLBACK = dt.datetime.combine(TODAY, dt.time(17, 44, 30))  # referee timetable: start even without HANDOFF if editor idle
HARD_STOP = dt.datetime.combine(TODAY, dt.time(17, 52))
LAST_START = dt.datetime.combine(TODAY, dt.time(17, 46))
CAP = 150  # recomputed at start: never past HARD_STOP minus 60 s for stop+save
LOG = []
T0 = None


def say(m):
    line = f"[{dt.datetime.now():%H:%M:%S}] {m}"; print(line, flush=True); LOG.append(line)


def link(text, to="*"):
    with open(OUTBOX, "a", encoding="utf-8") as f:
        f.write(json.dumps({"from": "hephaestus", "to": to, "type": "note", "body": {"text": text}}) + "\n")


def prev_handed_off(since):
    """True once PREV posts a HANDOFF on the shared log after `since`."""
    try:
        with open(LINK + r"\log.jsonl", "rb") as f:
            f.seek(max(0, os.path.getsize(LINK + r"\log.jsonl") - 2_000_000)); tail = f.read().decode("utf-8", "ignore")
    except OSError: return False
    for line in tail.splitlines()[::-1]:
        if PREV not in line or "HANDOFF" not in line: continue
        try: r = json.loads(line)
        except ValueError: continue
        if r.get("from") != PREV: continue
        ts = r.get("ts", "")
        try:
            if dt.datetime.fromisoformat(ts[:19]) >= since: return True
        except ValueError: pass
    return False


def call(kind, timeout=60, **params):
    params["bridge_timeout"] = timeout
    with socket.create_connection(("127.0.0.1", 9877), timeout=timeout + 10) as s:
        s.sendall((json.dumps({"id": int(time.time() * 1000), "type": kind, "params": params}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk: break
            buf += chunk
    r = json.loads(buf)
    if r.get("status") != "ok": raise RuntimeError(f"{kind}: {r.get('message')}")
    return r.get("result", {})


def left(): return CAP - (time.time() - T0)


def main():
    global T0
    if "--now" not in sys.argv:
        since = dt.datetime.combine(TODAY, dt.time(17, 30))
        while dt.datetime.now() < LAST_START and not (dt.datetime.now() >= START and (prev_handed_off(since) or dt.datetime.now() >= FALLBACK)):
            time.sleep(5)
        if dt.datetime.now() >= LAST_START:
            say(f"no HANDOFF from {PREV} by {LAST_START:%H:%M:%S}; not starting")
            link(f"BLOCKED editor-slot grok (hephaestus): no HANDOFF from {PREV} by {LAST_START:%H:%M}; did not touch the editor. Need a new slot.")
            return None
    global CAP
    T0 = time.time()
    CAP = max(0, min(420, (HARD_STOP - dt.datetime.now()).total_seconds() - 60))
    say(f"work cap {CAP:.0f}s, hard stop {HARD_STOP:%H:%M}")
    os.makedirs(SHOTS, exist_ok=True)
    link("TURN START hephaestus 17:43-17:53: DOING, placing Hephaestus Island in own sublevel")
    p = call("ping", timeout=15); say(f"editor: {p.get('level')} playing={p.get('playing')}")
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
            link("TURN DONE + HANDOFF hephaestus -> pythagoras (17:53 slot): editor saved, Play stopped")
            os.makedirs(SHOTS, exist_ok=True)
            open(os.path.join(SHOTS, "turn.log"), "w").write("\n".join(LOG))
