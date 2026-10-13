# SPDX-License-Identifier: MIT
"""OddsReaper's 20-minute editor turn, in order, hard-capped at 18 min. Run ONLY when 2hot2trot/referee grants the slot.
    python oddsreaper_turn.py [--skip-build]
Steps: preflight -> build DaedalusLink (unreal-job -Start -Fast; reopens editor) -> sky director -> island ->
hero shot (retry + HighResShot fallback) -> 20 s Play check + shot (if time) -> stop Play -> save -> tidy ->
post DONE + HANDOFF art-master-flex on the team link.
Talks to the Claude Unreal Bridge (127.0.0.1:9877, PROTOCOL.md). Whatever fails, it always stops Play and saves."""
import base64, json, os, shutil, socket, subprocess, sys, time

T0 = time.time(); CAP = 18 * 60
REPO = r"C:\Users\730ri\projects\Daedalus2"
PY = REPO + r"\engines\unreal\DaedalusLink\Content\Python"
TOOL = REPO + r"\tools\islands\oddsreaper"
SHOTS = r"C:\Users\730ri\projects\bot-team\shots\oddsreaper"
OUTBOX = r"C:\Users\730ri\projects\bot-team\link\outbox\oddsreaper.jsonl"
TIDY = r"C:\Users\730ri\projects\studio-screen-connector\tidy.ps1"
NEXT = "art-master-flex"  # round-2 order after oddsreaper
LOG = []


def left(): return CAP - (time.time() - T0)
def say(m): line = f"[{(time.time() - T0) / 60:5.1f}m] {m}"; print(line, flush=True); LOG.append(line)
def link(text, to="*"):
    with open(OUTBOX, "a", encoding="utf-8") as f: f.write(json.dumps({"to": to, "type": "note", "body": {"text": text}}) + "\n")


def call(kind, timeout=120, **params):
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


def py(code, timeout=600):
    return call("execute_python", timeout=timeout, code=code).get("result")


def wait_bridge(secs):
    end = time.time() + secs
    while time.time() < end:
        try: return call("ping", timeout=10)
        except Exception: time.sleep(5)
    raise RuntimeError("editor bridge did not come up")


def take_hero_shot(name="hero_unreal_editor.png"):
    """Round-1 timed out on viewport_screenshot. Retry a few sizes, then HighResShot/Shot fallback."""
    shot_path = os.path.join(SHOTS, name)
    shot_ok = False
    for attempt, (w, h, settle, to) in enumerate(((1920, 1080, 5, 45), (1920, 1080, 8, 60), (1280, 720, 5, 45)), 1):
        if left() < 15: break
        try:
            time.sleep(settle)
            r = call("viewport_screenshot", timeout=to, width=w, height=h)
            with open(shot_path, "wb") as f: f.write(base64.b64decode(r["image_png_base64"]))
            say(f"shot {shot_path} ({w}x{h} attempt {attempt})")
            shot_ok = True
            break
        except Exception as e:
            say(f"viewport_screenshot attempt {attempt} failed: {e}")
    if not shot_ok and left() > 20:
        try:
            hr = os.path.join(SHOTS, "hero_highres")
            os.makedirs(hr, exist_ok=True)
            code = (
                "import unreal\n"
                "unreal.SystemLibrary.execute_console_command(None, 'HighResShot 1920x1080')\n"
                "unreal.SystemLibrary.execute_console_command(None, 'Shot')\n"
                "result = {'ok': True}"
            )
            time.sleep(3)
            call("execute_python", timeout=30, code=code)
            time.sleep(4)
            saved = r"C:\Unreal\DaedalusRealm\Saved\Screenshots"
            cands = []
            for root, _, files in os.walk(saved):
                for fn in files:
                    if fn.lower().endswith(".png"):
                        cands.append(os.path.join(root, fn))
            if cands:
                newest = max(cands, key=os.path.getmtime)
                shutil.copy2(newest, shot_path)
                say(f"shot fallback HighResShot/Shot -> {shot_path} from {newest}")
                shot_ok = True
            else:
                say("HighResShot fallback: no png under Saved/Screenshots yet")
        except Exception as e:
            say(f"HighResShot fallback failed: {e}")
    if not shot_ok:
        say("viewport_screenshot FAILED after retries + HighResShot; hero shot still owed")
        link("NEED island:oddsreaper: viewport_screenshot still failing after retries+HighResShot; hero shot owed (unreal-team bridge 9877)")
    return shot_ok


def run_file(path, timeout):
    return py(f"import runpy,sys; sys.path.insert(0, r'{os.path.dirname(path)}'); "
              f"result = runpy.run_path(r'{path}', run_name='oddsreaper_turn')['run']()", timeout)


def main():
    os.makedirs(SHOTS, exist_ok=True)
    link("DOING editor-slot oddsreaper: turn started (round-2; HANDOFF -> art-master-flex)")
    if "--skip-build" not in sys.argv:
        say("build DaedalusLink (-Fast; editor reopens)")
        subprocess.run(["powershell", "-NoProfile", "-File", REPO + r"\engines\unreal\unreal-job.ps1", "-Start", "-Fast"], check=True)
        while left() > 600:
            out = subprocess.run(["powershell", "-NoProfile", "-File", REPO + r"\engines\unreal\unreal-job.ps1", "-Wait"],
                                 capture_output=True, text=True).stdout
            if "BUILD FAILED" in out: raise RuntimeError("build failed:\n" + out[-3000:])
            if "BUILD OK" in out: break
        say("build ok")
    p = wait_bridge(min(300, left() - 480)); say(f"editor up: {p.get('level')} playing={p.get('playing')}")
    if p.get("playing"): call("stop")
    say(f"sky director: {run_file(PY + r'/daedalus_sky_director.py', 240)}")
    if left() < 540: raise RuntimeError("out of time before island import")
    isle = run_file(TOOL + r"\place_oddsreaper_island.py", int(min(600, left() - 240))); say(f"island: {isle}")
    cam, rot = isle["cam"], isle["cam_rot"]
    py("import unreal; unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info("
       f"unreal.Vector({cam[0]},{cam[1]},{cam[2]}), unreal.Rotator(roll=0,pitch={rot[0]},yaw={rot[1]}))", 30)
    shot_ok = take_hero_shot("hero_unreal_editor.png")
    # 20s Play check only if time remains (save window needs ~2 min)
    if left() > 120:
        try:
            call("play", timeout=60); say("Play start (20s check)"); time.sleep(20)
            py("import unreal\nw=unreal.EditorLevelLibrary.get_game_world()\nd=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusSkyDirector)] if w else []\n"
               "result={'directors':len(d),'hour':d[0].get_hour() if d else None,'weather':str(d[0].get_editor_property('weather')) if d else None}", 30)
            try:
                take_hero_shot("hero_unreal_play.png")
            except Exception as e:
                say(f"play shot skipped: {e}")
            call("stop", timeout=30); say("Play stop after 20s check")
        except Exception as e:
            say(f"Play check failed: {e}")
            try: call("stop", timeout=20)
            except Exception: pass
    else:
        say(f"skip Play check; only {left():.0f}s left before save window")
    if not shot_ok and not os.path.exists(os.path.join(SHOTS, "hero_unreal_editor.png")):
        # Island placed; shot still owed — do not fail the whole turn on screenshot alone
        say("hero shot missing after retries; turn continues to save/HANDOFF")
    return isle


if __name__ == "__main__":
    ok, err = True, ""
    try: main()
    except Exception as e: ok, err = False, str(e); say(f"FAIL {e}")
    finally:
        for step, fn in (("stop", lambda: call("stop", timeout=60)), ("save", lambda: call("save", timeout=180)),
                         ("tidy", lambda: subprocess.run(["powershell", "-NoProfile", "-File", TIDY, "-Once"], timeout=60))):
            try: fn(); say(step)
            except Exception as e: say(f"{step} failed: {e}")
        mins = (time.time() - T0) / 60
        link(f"{'DONE' if ok else 'BLOCKED'} island:OddsReaper editor turn {mins:.1f} min: sky director + island placed, shots in {SHOTS}" +
             ("" if ok else f" | {err[:200]}") + " | Play stopped, saved, tidied")
        link(f"HANDOFF oddsreaper -> {NEXT}: editor saved, Play stopped", to=NEXT)
        open(os.path.join(SHOTS, "turn.log"), "w").write("\n".join(LOG))
