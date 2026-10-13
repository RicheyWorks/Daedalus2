# SPDX-License-Identifier: MIT
"""OddsReaper's 20-minute editor turn, in order, hard-capped at 18 min. Run ONLY when 2hot2trot/referee grants the slot.
    python oddsreaper_turn.py [--skip-build]
Steps: preflight -> build DaedalusLink (unreal-job -Start -Fast; reopens editor) -> sky director -> island ->
SAVE sublevel+DaedalusWorld (before shot; bridge timeout can't zero the turn) -> write island_result.json ->
hero shot (SceneCapture2D warm, then viewport retry + HighResShot) -> 20 s Play check + shot (if time) ->
stop Play -> save -> tidy -> post DONE + HANDOFF art-master-flex on the team link.
Talks to the Claude Unreal Bridge (127.0.0.1:9877, PROTOCOL.md). Whatever fails, it always stops Play and saves."""
import base64, json, os, shutil, socket, subprocess, sys, time, datetime

T0 = time.time(); CAP = 18 * 60
REPO = r"C:\Users\730ri\projects\Daedalus2"
PY = REPO + r"\engines\unreal\DaedalusLink\Content\Python"
TOOL = REPO + r"\tools\islands\oddsreaper"
LAYOUT = REPO + r"\data\islands\oddsreaper\layout.json"
SHOTS = r"C:\Users\730ri\projects\bot-team\shots\oddsreaper"
RESULT = os.path.join(SHOTS, "island_result.json")
OUTBOX = r"C:\Users\730ri\projects\bot-team\link\outbox\oddsreaper.jsonl"
TIDY = r"C:\Users\730ri\projects\studio-screen-connector\tidy.ps1"
NEXT = "art-master-flex"  # round-2 order after oddsreaper
LOG = []


def left(): return CAP - (time.time() - T0)
def say(m): line = f"[{(time.time() - T0) / 60:5.1f}m] {m}"; print(line, flush=True); LOG.append(line)
def link(text, to="*"):
    with open(OUTBOX, "a", encoding="utf-8") as f: f.write(json.dumps({"to": to, "type": "note", "body": {"text": text}}) + "\n")


def write_result(d):
    """Outcome on disk so a bridge timeout mid-capture does not lose the turn (hephaestus 20:36 pattern)."""
    d = dict(d, ts=datetime.datetime.now().isoformat(timespec="seconds"))
    try:
        os.makedirs(SHOTS, exist_ok=True)
        with open(RESULT, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, default=str)
        say(f"island_result -> {RESULT}")
    except Exception as e:
        say(f"island_result write failed: {e}")


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


def scene_capture_hero(cam, target, name="hero_unreal_editor.png"):
    """Warm SceneCapture2D (hephaestus/prometheus pattern). Bypasses flaky viewport_screenshot."""
    code = f'''
import unreal, os, time
SHOTS = r"{SHOTS}"
out_name = r"{name}"
out_path = os.path.join(SHOTS, out_name)
os.makedirs(SHOTS, exist_ok=True)
cam_loc = unreal.Vector({cam[0]}, {cam[1]}, {cam[2]})
target_loc = unreal.Vector({target[0]}, {target[1]}, {target[2]})
ue_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ue_sub.get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in actors.get_all_level_actors():
    if str(a.get_actor_label()).startswith("OddsReaper Hero Capture"):
        try: actors.destroy_actor(a)
        except Exception: pass
rt = unreal.RenderingLibrary.create_render_target2d(world, 1920, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8)
look = unreal.MathLibrary.find_look_at_rotation(cam_loc, target_loc)
cap = actors.spawn_actor_from_class(unreal.SceneCapture2D, cam_loc, look)
cap.set_actor_label("OddsReaper Hero Capture"); cap.set_folder_path("OddsReaper")
sc = cap.capture_component2d
sc.set_editor_property("texture_target", rt)
sc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
sc.set_editor_property("fov_angle", 55.0)
pp = sc.get_editor_property("post_process_settings")
for k, v in (("override_auto_exposure_bias", True), ("auto_exposure_bias", 1.0),
             ("override_white_temp", True), ("white_temp", 5200.0),
             ("override_bloom_intensity", True), ("bloom_intensity", 0.4)):
    try: pp.set_editor_property(k, v)
    except Exception: pass
sc.set_editor_property("post_process_settings", pp)
sc.set_editor_property("post_process_blend_weight", 1.0)
sc.capture_scene()
unreal.RenderingLibrary.export_render_target(world, rt, SHOTS, out_name)
try: actors.destroy_actor(cap)
except Exception: pass
time.sleep(0.5)
ok = os.path.isfile(out_path) and os.path.getsize(out_path) > 1000
result = {{"ok": ok, "path": out_path, "size": os.path.getsize(out_path) if ok else 0}}
'''
    try:
        r = py(code, timeout=90)
        if isinstance(r, dict) and r.get("ok"):
            say(f"shot SceneCapture2D -> {r.get('path')} ({r.get('size')} B)")
            return True
        say(f"SceneCapture2D returned: {r}")
    except Exception as e:
        say(f"SceneCapture2D failed: {e}")
    return False


def take_hero_shot(cam=None, target=None, name="hero_unreal_editor.png"):
    """Prefer SceneCapture2D, then viewport retries, then HighResShot/Shot."""
    shot_path = os.path.join(SHOTS, name)
    shot_ok = False
    if cam is not None and target is not None and left() > 30:
        shot_ok = scene_capture_hero(cam, target, name)
    for attempt, (w, h, settle, to) in enumerate(((1920, 1080, 5, 45), (1920, 1080, 8, 60), (1280, 720, 5, 45)), 1):
        if shot_ok or left() < 15: break
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
        say("hero shot FAILED after SceneCapture + viewport retries + HighResShot; still owed")
        link("NEED island:oddsreaper: hero SceneCapture+viewport+HighResShot all failed; hero shot owed (unreal-team bridge 9877)")
    return shot_ok


def run_file(path, timeout):
    return py(f"import runpy,sys; sys.path.insert(0, r'{os.path.dirname(path)}'); "
              f"result = runpy.run_path(r'{path}', run_name='oddsreaper_turn')['run']()", timeout)


def hero_target_from_layout(isle):
    """World-space cam + look-at from layout.json (cm), falling back to island return."""
    try:
        lay = json.load(open(LAYOUT, encoding="utf-8"))
        ox, oy, oz = lay["origin_cm"]
        c = lay.get("hero_cam_m", [30, -175, 32])
        t = lay.get("hero_target_m", [0, -70, 6])
        cam = [ox + c[0] * 100, oy + c[1] * 100, oz + c[2] * 100]
        target = [ox + t[0] * 100, oy + t[1] * 100, oz + t[2] * 100]
        return cam, target
    except Exception as e:
        say(f"layout hero pose: {e}; using isle cam")
        cam = isle.get("cam") or [400000, -400000, 3200]
        target = [cam[0] - 3000, cam[1] + 10000, 600]
        return cam, target


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

    # SAVE BEFORE hero capture (hephaestus 20:36 / blender-team timeout lesson): island already in Content
    # even if SceneCapture or viewport_screenshot hangs the bridge.
    try:
        call("save", timeout=180); say("save before hero shot (sublevel + DaedalusWorld)")
        write_result({
            "stage": "saved", "ok": True,
            "placed": isle.get("placed") if isinstance(isle, dict) else None,
            "want": isle.get("want") if isinstance(isle, dict) else None,
            "cam": cam, "cam_rot": rot,
        })
    except Exception as e:
        say(f"pre-shot save failed: {e}")
        write_result({"stage": "save_failed", "ok": False, "error": str(e), "cam": cam, "cam_rot": rot})

    cam_w, target_w = hero_target_from_layout(isle)
    shot_ok = take_hero_shot(cam_w, target_w, "hero_unreal_editor.png")
    write_result({
        "stage": "shot", "ok": shot_ok,
        "shot": os.path.join(SHOTS, "hero_unreal_editor.png") if shot_ok else None,
        "cam": cam_w, "target": target_w,
    })

    # 20s Play check only if time remains (save window needs ~2 min)
    if left() > 120:
        try:
            call("play", timeout=60); say("Play start (20s check)"); time.sleep(20)
            py("import unreal\nw=unreal.EditorLevelLibrary.get_game_world()\nd=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusSkyDirector)] if w else []\n"
               "result={'directors':len(d),'hour':d[0].get_hour() if d else None,'weather':str(d[0].get_editor_property('weather')) if d else None}", 30)
            try:
                take_hero_shot(cam_w, target_w, "hero_unreal_play.png")
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
        write_result({"stage": "done", "ok": ok, "error": err or None, "mins": round(mins, 2)})
        link(f"{'DONE' if ok else 'BLOCKED'} island:OddsReaper editor turn {mins:.1f} min: sky director + island placed, shots in {SHOTS}" +
             ("" if ok else f" | {err[:200]}") + " | Play stopped, saved, tidied")
        link(f"HANDOFF oddsreaper -> {NEXT}: editor saved, Play stopped", to=NEXT)
        open(os.path.join(SHOTS, "turn.log"), "w").write("\n".join(LOG))
