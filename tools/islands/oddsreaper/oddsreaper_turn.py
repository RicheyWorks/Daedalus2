# SPDX-License-Identifier: MIT
"""OddsReaper's 20-minute editor turn, in order, hard-capped at 18 min. Run ONLY when 2hot2trot/referee grants the slot.
    python oddsreaper_turn.py [--skip-build]
Steps: preflight -> build DaedalusLink (unreal-job -Start -Fast; reopens editor) -> sky director -> island ->
SAVE sublevel+DaedalusWorld (before shot; bridge timeout can't zero the turn) -> write island_result.json ->
hero shot (SceneCapture2D warm, then viewport retry + HighResShot) -> 20 s Play check + shot (if time) ->
stop Play -> restore_world_sky (Clear) -> save OddsReaperIsland ONLY -> verify Clear -> tidy -> post DONE + HANDOFF
$OR_NEXT (default art-master-flex) on the team link. Never a blind bridge save after Play (round 3/4 storm leak).
Talks to the Claude Unreal Bridge (127.0.0.1:9877, PROTOCOL.md). Whatever fails, it always stops Play and saves.
Bridge liveness PREFLIGHT before TURN START: short ping; if the bridge is dead (GPU-crashed editor, refused or hung)
it posts one HOLD note, does NOT start the 18-min clock or place anything, re-pings every OR_PREFLIGHT_S (default 30 s)
and needs two good pings in a row, until alive or give-up (default turn start + 60 min, OR_GIVE_UP_MIN; OR_GIVE_UP=HH:MM rolls past midnight). Each check writes
bot-team/shots/oddsreaper/bridge_status.json {ok, ts, detail}. Build (-Fast) only runs after the bridge is alive
(or after a successful preflight recovery); never burn the turn on a dead editor."""
from pathlib import Path
import base64, datetime as dt, json, os, shutil, socket, subprocess, sys, time

T0 = time.time(); CAP = 18 * 60
REPO = r"C:\Users\730ri\projects\Daedalus2"
PY = REPO + r"\engines\unreal\DaedalusLink\Content\Python"
TOOL = REPO + r"\tools\islands\oddsreaper"
LAYOUT = REPO + r"\data\islands\oddsreaper\layout.json"
SHOTS = r"C:\Users\730ri\projects\bot-team\shots\oddsreaper"
RESULT = os.path.join(SHOTS, "island_result.json")
OUTBOX = r"C:\Users\730ri\projects\bot-team\link\outbox\oddsreaper.jsonl"
TIDY = r"C:\Users\730ri\projects\studio-screen-connector\tidy.ps1"
NEXT = os.environ.get("OR_NEXT", "art-master-flex")  # round 3+: set OR_NEXT to whoever the referee names
PORT = int(os.environ.get("OR_BRIDGE_PORT", "9877"))
PREFLIGHT_S = int(os.environ.get("OR_PREFLIGHT_S", "30"))
PING_S = int(os.environ.get("OR_PING_S", "5"))
GIVE_UP_HHMM = os.environ.get("OR_GIVE_UP", "")  # "" = start + OR_GIVE_UP_MIN; a passed HH:MM rolls to tomorrow
GIVE_UP_MIN = int(os.environ.get("OR_GIVE_UP_MIN", "60"))
LOG = []


MIN_BUILD_GB = float(os.environ.get("OR_MIN_BUILD_GB", "2.0"))  # -Fast build reopens the editor (big RAM spike)
MIN_PLAY_GB = float(os.environ.get("OR_MIN_PLAY_GB", "1.5"))    # PIE duplicates the world; referee: ~1 GB free, batch small
# Island-only temp capture lights (disk-saver/hephaestus lit-capture pattern, storm-cool tint).
# SceneCapture blacks out when the world is dark; warm daylight fills would wash oddsreaper_storm to Clear.
# Spawn tagged OR_TEMP_* for the shot only, destroy before any save. OR_TEMP_LIGHTS=0 disables.
TEMP_LIGHT_TAG = "OR_TempCapture"
TEMP_LIGHT_PREFIX = "OR_TEMP_"
TEMP_FILL_INTENSITY = 2.5e5   # half of heph/disk-saver 5e5 — keep stormish luma
TEMP_SUN_INTENSITY = 4.0
TEMP_EV100 = 10.0
TEMP_LIGHT_RGB = (180, 200, 255)  # cool storm fill (not warm daylight 255,244,225)


def temp_lights_plan(env=None):
    """Pure decision: should scene_capture_hero spawn island-only temp lights? Returns (use, reason)."""
    env = os.environ if env is None else env
    if env.get("OR_TEMP_LIGHTS", "1") == "0":
        return False, "disabled (OR_TEMP_LIGHTS=0)"
    return True, "spawn island-only OR_TEMP storm-cool sun/fill/PPV (no atmosphere sun; destroy before save)"


def is_temp_light_actor(label, tags=None):
    """True for actors this module spawned for a one-shot hero capture (label or tag)."""
    label = str(label or "")
    tags = [str(t) for t in (tags or [])]
    return label.startswith(TEMP_LIGHT_PREFIX) or TEMP_LIGHT_TAG in tags



def free_ram_gb():
    """Host free physical RAM in GB (Windows GlobalMemoryStatusEx); None if unreadable (gate then fails open)."""
    try:
        import ctypes
        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS(); m.dwLength = ctypes.sizeof(MS)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)): return None
        return m.ullAvailPhys / 2**30
    except Exception:
        return None


def ram_ok(step, need_gb, free=None):
    """True if the heavy step may run. Low RAM (round 5: 0.86-1.07 GB free) skips build/PIE instead of OOM-ing the shared editor."""
    free = free_ram_gb() if free is None else free
    if free is None:
        say(f"RAM gate {step}: free RAM unreadable; allowing"); return True
    if free < need_gb:
        say(f"RAM gate {step}: SKIP, free {free:.2f} GB < {need_gb:.2f} GB"); return False
    say(f"RAM gate {step}: ok, free {free:.2f} GB"); return True


def left(): return CAP - (time.time() - T0)
def say(m): line = f"[{(time.time() - T0) / 60:5.1f}m] {m}"; print(line, flush=True); LOG.append(line)
def link(text, to="*"):
    with open(OUTBOX, "a", encoding="utf-8") as f: f.write(json.dumps({"to": to, "type": "note", "body": {"text": text}}) + "\n")


def write_result(d):
    """Outcome on disk so a bridge timeout mid-capture does not lose the turn (hephaestus 20:36 pattern)."""
    d = dict(d, ts=dt.datetime.now().isoformat(timespec="seconds"))
    try:
        os.makedirs(SHOTS, exist_ok=True)
        with open(RESULT, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, default=str)
        say(f"island_result -> {RESULT}")
    except Exception as e:
        say(f"island_result write failed: {e}")


def call(kind, timeout=120, **params):
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


def py(code, timeout=600):
    return call("execute_python", timeout=timeout, code=code).get("result")


def wait_bridge(secs):
    end = time.time() + secs
    while time.time() < end:
        try: return call("ping", timeout=10)
        except Exception: time.sleep(5)
    raise RuntimeError("editor bridge did not come up")


def _give_up_dt(now=None):
    """Round-3 turns run past 23:00: a fixed 23:00 cut-off made preflight() return False at once (no ping).
    Default is start + GIVE_UP_MIN; an explicit HH:MM that has already passed means tomorrow (after midnight)."""
    now = now or dt.datetime.now()
    if not GIVE_UP_HHMM:
        return now + dt.timedelta(minutes=GIVE_UP_MIN)
    h, m = GIVE_UP_HHMM.split(":")
    t = dt.datetime.combine(now.date(), dt.time(int(h), int(m)))
    return t if t > now else t + dt.timedelta(days=1)


def bridge_alive():
    """Short liveness ping. GPU-dead editor may refuse the socket or never answer; both count as dead.
    Writes shots/oddsreaper/bridge_status.json {ok, ts, detail} on every check."""
    try:
        p = call("ping", timeout=PING_S)
        ok, detail = True, f"level={p.get('level')} playing={p.get('playing')}"
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"[:300]
    try:
        os.makedirs(SHOTS, exist_ok=True)
        with open(os.path.join(SHOTS, "bridge_status.json"), "w", encoding="utf-8") as f:
            json.dump({"ok": ok, "ts": dt.datetime.now().isoformat(timespec="seconds"), "port": PORT, "detail": detail}, f)
    except OSError:
        pass
    return ok, detail


def preflight():
    """Do not TURN START while the bridge is dead: a crashed editor must not burn our 18-minute turn.
    True once the bridge answers (twice in a row if it had been dead), False if still dead at GIVE_UP."""
    give_up = _give_up_dt()
    held = False
    while dt.datetime.now() < give_up:
        ok, detail = bridge_alive()
        if ok and held:
            time.sleep(10)
            ok, detail = bridge_alive()
        if ok:
            say(f"preflight: bridge 127.0.0.1:{PORT} alive ({detail})")
            if held:
                link(f"DOING oddsreaper: bridge {PORT} answering again ({detail}); starting turn")
            return True
        say(f"preflight: bridge 127.0.0.1:{PORT} DEAD ({detail}); NOT starting or placing; re-ping in {PREFLIGHT_S}s "
            f"(give-up {give_up:%H:%M})")
        if not held:
            link(f"HOLD oddsreaper: bridge {PORT} is dead ({detail[:120]}); NOT starting the turn or placing; "
                 f"re-pinging every {PREFLIGHT_S}s until it answers or {give_up:%H:%M}. Turn clock not started.")
            held = True
        time.sleep(PREFLIGHT_S)
    return False


def scene_capture_hero(cam, target, name="hero_unreal_editor.png"):
    """Storm-cool SceneCapture2D with optional island-only OR_TEMP lights (never saved)."""
    use_tmp, tmp_why = temp_lights_plan()
    code = f"""
import unreal, os, time
SHOTS = r"{SHOTS}"
out_name = r"{name}"
out_path = os.path.join(SHOTS, out_name)
os.makedirs(SHOTS, exist_ok=True)
cam_loc = unreal.Vector({cam[0]}, {cam[1]}, {cam[2]})
target_loc = unreal.Vector({target[0]}, {target[1]}, {target[2]})
USE_TMP = {use_tmp!r}
TMP_WHY = {tmp_why!r}
TMP_TAG = {TEMP_LIGHT_TAG!r}
TMP_PREFIX = {TEMP_LIGHT_PREFIX!r}
FILL_I = {TEMP_FILL_INTENSITY}
SUN_I = {TEMP_SUN_INTENSITY}
EV100 = {TEMP_EV100}
RGB = {TEMP_LIGHT_RGB!r}
ue_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
gw = unreal.EditorLevelLibrary.get_game_world()
world = gw or ue_sub.get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
temp_info = {{"used": False, "reason": TMP_WHY, "spawned": [], "removed": []}}

def _is_tmp(lab, tags):
    return lab.startswith(TMP_PREFIX) or TMP_TAG in tags

def _cleanup_temps():
    removed = []
    for a in list(actors.get_all_level_actors()):
        lab = str(a.get_actor_label())
        tags = [str(t) for t in (getattr(a, "tags", None) or [])]
        if _is_tmp(lab, tags) or lab.startswith("OddsReaper Hero Capture"):
            try:
                actors.destroy_actor(a); removed.append(lab)
            except Exception:
                pass
    temp_info["removed"] = removed
    return removed

_cleanup_temps()  # clear leftover OR_TEMP / prior capture from a partial run
origin_v = unreal.Vector((cam_loc.x + target_loc.x) * 0.5, (cam_loc.y + target_loc.y) * 0.5, 0.0)

def _spawn_temp(cls, loc, rot, nm):
    if gw:
        xf = unreal.Transform(loc, rot, unreal.Vector(1, 1, 1))
        a = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(gw, cls, xf)
        a = unreal.GameplayStatics.finish_spawning_actor(a, xf)
    else:
        a = actors.spawn_actor_from_class(cls, loc, rot)
        a.set_folder_path("OddsReaper/TempCapture")
    a.tags = [TMP_TAG]
    a.set_actor_label(TMP_PREFIX + nm)
    temp_info["spawned"].append(a.get_actor_label())
    return a

if USE_TMP:
    try:
        sun = _spawn_temp(unreal.DirectionalLight, origin_v + unreal.Vector(0, 0, 3000),
                          unreal.Rotator(0, -40, 35), "Sun")
        sc_sun = sun.light_component
        sc_sun.set_editor_property("intensity", SUN_I)
        sc_sun.set_editor_property("light_color", unreal.Color(RGB[0], RGB[1], RGB[2], 255))
        try: sc_sun.set_editor_property("atmosphere_sun_light", False)
        except Exception: pass
        fill = _spawn_temp(unreal.PointLight, origin_v + unreal.Vector(0, 0, 6000),
                           unreal.Rotator(0, 0, 0), "Fill")
        fc = fill.point_light_component
        fc.set_editor_property("intensity", FILL_I)
        fc.set_editor_property("light_color", unreal.Color(RGB[0], RGB[1], RGB[2], 255))
        fc.set_editor_property("attenuation_radius", 20000.0)
        fc.set_editor_property("cast_shadows", False)
        ppv = _spawn_temp(unreal.PostProcessVolume, origin_v, unreal.Rotator(0, 0, 0), "PPV")
        ppv.set_editor_property("unbound", False)
        ppv.set_actor_scale3d(unreal.Vector(200, 200, 100))
        s = ppv.settings
        for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
                     ("auto_exposure_min_brightness", EV100),
                     ("auto_exposure_max_brightness", EV100),
                     ("auto_exposure_bias", 0.25)):
            try:
                s.set_editor_property("override_" + k, True)
                s.set_editor_property(k, v)
            except Exception as e:
                temp_info.setdefault("notes", []).append(f"{{k}}: {{str(e)[:60]}}")
        ppv.set_editor_property("settings", s)
        temp_info["used"] = True
    except Exception as e:
        temp_info["error"] = str(e)[:160]
        _cleanup_temps()

rt = unreal.RenderingLibrary.create_render_target2d(world, 1920, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8)
look = unreal.MathLibrary.find_look_at_rotation(cam_loc, target_loc)
if gw:  # spawn INTO the PIE world (EditorActorSubsystem only spawns in the editor world)
    xf = unreal.Transform(cam_loc, look, unreal.Vector(1, 1, 1))
    cap = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(gw, unreal.SceneCapture2D, xf)
    cap = unreal.GameplayStatics.finish_spawning_actor(cap, xf)
else:
    cap = actors.spawn_actor_from_class(unreal.SceneCapture2D, cam_loc, look)
    cap.set_actor_label("OddsReaper Hero Capture"); cap.set_folder_path("OddsReaper")
sc = cap.capture_component2d
sc.set_editor_property("texture_target", rt)
sc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
sc.set_editor_property("fov_angle", 55.0)
pp = sc.get_editor_property("post_process_settings")
for k, v in (("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.5),
             ("override_white_temp", True), ("white_temp", 6500.0),
             ("override_bloom_intensity", True), ("bloom_intensity", 0.35)):
    try: pp.set_editor_property(k, v)
    except Exception: pass
sc.set_editor_property("post_process_settings", pp)
sc.set_editor_property("post_process_blend_weight", 1.0)
sc.capture_scene()
unreal.RenderingLibrary.export_render_target(world, rt, SHOTS, out_name)
try: (cap.destroy_actor() if gw else actors.destroy_actor(cap))
except Exception: pass
_cleanup_temps()  # ALWAYS strip OR_TEMP_* before any later save
time.sleep(0.5)
ok = os.path.isfile(out_path) and os.path.getsize(out_path) > 1000
result = {{"ok": ok, "path": out_path, "size": os.path.getsize(out_path) if ok else 0, "temp_lights": temp_info}}
"""
    try:
        r = py(code, timeout=90)
        if isinstance(r, dict) and r.get("ok"):
            tl = r.get("temp_lights") or {}
            say(f"shot SceneCapture2D -> {r.get('path')} ({r.get('size')} B; temp_lights used={tl.get('used')})")
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


STORM_CODE = r"""import unreal
w = unreal.EditorLevelLibrary.get_game_world()
# Sublevel streaming: MoodVolume lives on OddsReaperIsland. If that streaming level is unloaded in PIE,
# volumes=[] and only the director fallback runs (sky ok, but volume-driven wetness/hold never fires).
streamed = []
if w:
    try:
        _sl = unreal.GameplayStatics.get_streaming_level(w, "OddsReaperIsland")
        if _sl:
            _sl.set_should_be_loaded(True); _sl.set_should_be_visible(True); streamed.append("OddsReaperIsland")
    except Exception: pass
    for sl in list(getattr(w, "get_streaming_levels", lambda: [])() or []):
        pkg = ""
        for prop in ("world_asset_package_f_name", "package_name"):
            try:
                pkg = str(sl.get_editor_property(prop)); break
            except Exception:
                pass
        if "OddsReaper" not in pkg:
            continue
        for prop, val in (("should_be_loaded", True), ("should_be_visible", True)):
            try: sl.set_editor_property(prop, val)
            except Exception: pass
        for meth in ("set_should_be_loaded", "set_should_be_visible"):
            try: getattr(sl, meth)(True)
            except Exception: pass
        streamed.append(pkg)
d = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusSkyDirector)] if w else []
# Round-3 turn logged volumes=0 even after the streaming flip: should_be_loaded only takes effect on a later
# streaming update (same-tick search sees nothing), and PIE copies may not carry the editor actor label.
# Flush streaming first, then match by label OR by the volume's mood row (set from layout.json at placement).
flushed = False
if w and streamed:
    try: unreal.GameplayStatics.flush_level_streaming(w); flushed = True
    except Exception: pass
allv = list(unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusMoodVolume)) if w else []
def _vmood(a):
    try: return str(a.get_editor_property("mood"))
    except Exception: return ""
v = [a for a in allv if "OddsReaper" in a.get_actor_label()]
vmatch = "label" if v else None
if not v:
    v = [a for a in allv if _vmood(a) == "oddsreaper_storm"]; vmatch = "mood" if v else None
def st(x): return {"hour": round(x.get_hour(), 2), "weather": str(x.get_editor_property("weather")), "mood": str(x.get_editor_property("mood"))}
def setp(o, name, val):
    for p in (name, "b_" + name):
        try: o.set_editor_property(p, val); return True
        except Exception: pass
    return False
before = st(d[0]) if d else None
via = None
pinned = {}
if v and hasattr(v[0], "apply_now"):
    # PIE copy only (Stop discards it). The volume's 0.5 s view Tick reads the PLAYER camera, which sits on the
    # main island 4 km away, so it would call Restore() right after apply_now and blend back to Clear daylight
    # before the SceneCapture hero shot. Pin it: no view trigger, no restore on exit.
    pinned = {"trigger_on_view_off": setp(v[0], "trigger_on_view", False), "restore_on_exit_off": setp(v[0], "restore_on_exit", False)}
    v[0].apply_now(True); via = "volume.apply_now"
elif d:
    setp(d[0], "clock_running", False); d[0].set_editor_property("auto_weather_hours", 0.0)
    d[0].set_time_of_day(18.75); d[0].set_mood("oddsreaper_storm", True); d[0].set_weather(unreal.DaedalusWeather.STORM, True); via = "director"
# materials_mpc.json storm contract so felt/cliff/cistern MIDs match the sky look during the Play hero shot.
mpc_set = {}
try:
    mpc = None
    for path in ("/Game/OddsReaper/MPC_OR_SkyWeather", "/Game/OddsReaper/Art/MPC_OR_SkyWeather", "/Game/Daedalus/MPC_OR_SkyWeather"):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            mpc = unreal.EditorAssetLibrary.load_asset(path); break
    if mpc and w:
        for name, val in (("WindStrength", 0.95), ("Wetness", 1.0), ("StormPulse", 1.0), ("NightMask", 0.25)):
            try:
                unreal.MaterialLibrary.set_scalar_parameter_value(w, mpc, name, float(val)); mpc_set[name] = val
            except Exception as e:
                mpc_set[name] = "err:" + str(e)[:48]
    else:
        mpc_set = {"skipped": "mpc asset missing (data contract only until editor turn)"}
except Exception as e:
    mpc_set = {"error": str(e)[:80]}
result = {"directors": len(d), "volumes": len(v), "volumes_all": len(allv), "vmatch": vmatch, "flushed": flushed, "via": via, "pinned": pinned, "streamed": streamed, "mpc": mpc_set, "before": before, "after": st(d[0]) if d else None}"""
# Read-back after a few game ticks: proves the storm held (not restored by a volume Tick) before the shot.
STORM_CHECK_CODE = r"""import unreal
w = unreal.EditorLevelLibrary.get_game_world()
d = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusSkyDirector)] if w else []
x = d[0] if d else None
result = {'hour': round(x.get_hour(), 2), 'weather': str(x.get_editor_property('weather')), 'mood': str(x.get_editor_property('mood'))} if x else None"""


def storm_held(state):
    """True when a director read-back shows the OddsReaper storm look (headless-testable)."""
    if not isinstance(state, dict):
        return False
    return "STORM" in str(state.get("weather", "")).upper() and str(state.get("mood", "")) == "oddsreaper_storm"


def daylightish_rgb(mean_r, mean_b, lum):
    """Gate: warm+bright OR washed-bright (lum>140) = not storm. Round-2 was warm daylight; round-3 false OK was cool washed sky lum~220."""
    lum = float(lum); mean_r = float(mean_r); mean_b = float(mean_b)
    if lum > 140:
        return True
    return lum > 95 and mean_r > mean_b + 5


def hero_storm_rgb(path):
    """Mean RGB / luminance of a Play hero PNG. Round-2 play shot was daylightish (lum~145, R>B).
    Storm look should be cooler/darker. Pure/headless; returns None if file missing or unreadable."""
    try:
        from PIL import Image
    except ImportError:
        return None
    p = Path(path) if not isinstance(path, Path) else path
    if not p.is_file():
        return None
    try:
        im = Image.open(p).convert("RGB")
        w, h = im.size
        px = list(im.getdata())[::16]
        if not px:
            return None
        r = sum(c[0] for c in px) / len(px)
        g = sum(c[1] for c in px) / len(px)
        b = sum(c[2] for c in px) / len(px)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        sky = im.crop((0, 0, w, max(1, h // 4)))
        spx = list(sky.getdata())[::8]
        sr = sum(c[0] for c in spx) / len(spx)
        sg = sum(c[1] for c in spx) / len(spx)
        sb = sum(c[2] for c in spx) / len(spx)
        daylightish = daylightish_rgb(r, b, lum)
        stormish = (not daylightish) and ((b >= r - 2 and lum < 110) or (sb >= sr and lum < 100) or lum < 70)
        return {
            "path": str(p), "w": w, "h": h,
            "mean": {"R": round(r, 1), "G": round(g, 1), "B": round(b, 1)},
            "lum": round(lum, 1),
            "sky": {"R": round(sr, 1), "G": round(sg, 1), "B": round(sb, 1)},
            "daylightish": daylightish, "stormish": stormish,
        }
    except Exception as e:
        return {"error": str(e)[:120]}


def force_storm_in_pie():
    """Round-2 Play shot showed daylight: the Mood Volume fired only on player-pawn overlap and the PIE pawn spawns
    on another island. The rebuilt volume triggers on the view, but take_hero_shot uses a SceneCapture (not the player
    view), so force the OddsReaper look in the PIE world only, right before the Play shot. Stop discards PIE, so the
    saved DaedalusWorld director stays Clear for every other island. Falls back to the director if the old class is live."""
    try:
        r = py(STORM_CODE, 30)
        time.sleep(1.5)  # let the PIE world tick (volume Tick is 0.5 s) before trusting the look
        chk = py(STORM_CHECK_CODE, 20)
        if not storm_held(chk) and isinstance(r, dict) and r.get("directors"):
            py(STORM_CODE.replace('if v and hasattr(v[0], "apply_now"):', "if False:"), 30)  # director path, clock held
            time.sleep(1.0)
            chk = py(STORM_CHECK_CODE, 20)
            if isinstance(r, dict): r["reforced"] = "director"
        if isinstance(r, dict):
            r["held"] = storm_held(chk); r["check"] = chk
        return r
    except Exception as e:
        return {"error": str(e)[:200]}


def run_file(path, timeout):
    return py(f"import runpy,sys; sys.path.insert(0, r'{os.path.dirname(path)}'); "
              f"result = runpy.run_path(r'{path}', run_name='oddsreaper_turn')['run']()", timeout)


# ---- Post-Play save contract (round 3/4 lesson) ------------------------------------------------------------------
# The bridge "save" command is save_current_level + save_dirty_packages(True, True): it writes EVERY dirty package,
# including the persistent DaedalusWorld. In rounds 3/4 that put the oddsreaper_storm look (Storm, 18.75, clock
# paused) on disk for every island. After Play we therefore never blind-save. Sequence (post_play_plan):
#   stop -> restore_world_sky.py (young_meadow / Clear / 9.4 / clock running, its own verified persistent-map save)
#        -> save the OddsReaperIsland sublevel ONLY (set current + save_current_level; same as fix_oddsreaper_storm / r4_pie)
#        -> verify the editor-world director is Clear; if DaedalusWorld.umap moved during our sublevel save or the
#           world is not Clear, run restore_world_sky + verify once more.
SUBLEVEL = "OddsReaperIsland"
WORLD_UMAP = r"C:\Unreal\DaedalusRealm\Content\Daedalus\DaedalusWorld.umap"
SUB_UMAP = r"C:\Unreal\DaedalusRealm\Content\OddsReaper\Maps\OddsReaperIsland.umap"
RESTORE_WORLD_SKY = os.path.join(TOOL, "restore_world_sky.py")
CLEAR_WORLD = {"mood": "young_meadow", "weather": "CLEAR", "hour": 9.4, "clock_running": True}
CLEAR_HOUR_TOL = float(os.environ.get("OR_CLEAR_HOUR_TOL", "0.5"))  # clock runs after restore; allow small drift
POST_PLAY_SEQUENCE = ("stop", "restore_world_sky", "save_sublevel", "verify_clear")


def post_play_plan():
    """Pure contract: the post-Play order. There is no blind bridge 'save' step in it."""
    return list(POST_PLAY_SEQUENCE)


def world_clear(state, tol=None):
    """Pure: (ok, problems) for an editor-world director read-back (mood/weather/hour/clock_running)."""
    tol = CLEAR_HOUR_TOL if tol is None else tol
    if not isinstance(state, dict) or not state.get("directors", 1):
        return False, ["no director state"]
    bad = []
    if CLEAR_WORLD["mood"] not in str(state.get("mood", "")):
        bad.append(f"mood={state.get('mood')}")
    if CLEAR_WORLD["weather"] not in str(state.get("weather", "")).upper():
        bad.append(f"weather={state.get('weather')}")
    try:
        if abs(float(state.get("hour")) - CLEAR_WORLD["hour"]) > tol:
            bad.append(f"hour={state.get('hour')}")
    except (TypeError, ValueError):
        bad.append(f"hour={state.get('hour')}")
    if state.get("clock_running") is not True:
        bad.append(f"clock_running={state.get('clock_running')}")
    return not bad, bad


def world_umap_jumped(before, after):
    """Pure: True if DaedalusWorld.umap was rewritten during a step that may only touch our sublevel."""
    try:
        return float(after) > float(before)
    except (TypeError, ValueError):
        return False


def needs_reclear(save_info, verify):
    """Pure: re-run restore_world_sky when our sublevel save touched DaedalusWorld or the world is not Clear."""
    jumped = isinstance(save_info, dict) and world_umap_jumped(save_info.get("world_umap_before"),
                                                                save_info.get("world_umap_after"))
    return bool(jumped or not world_clear(verify)[0])


SAVE_SUBLEVEL_CODE = r"""import unreal, os, time
W = r"@WORLD_UMAP@"; S = r"@SUB_UMAP@"; NAME = "@SUBLEVEL@"
def m(p): return os.path.getmtime(p) if os.path.exists(p) else 0.0
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def cur():
    try: return str(les.get_current_level().get_outer().get_name())
    except Exception: return ""
prev = cur(); wb, sb = m(W), m(S)
les.set_current_level_by_name(NAME)
now = cur()
saved = bool(les.save_current_level()) if now == NAME else False  # current sublevel package only (no dirty-package sweep)
time.sleep(0.15)
wa, sa = m(W), m(S)
if prev and prev != NAME:
    try: les.set_current_level_by_name(prev)
    except Exception: pass
result = {"saved": saved, "current": now, "prev": prev, "world_umap_before": wb, "world_umap_after": wa,
          "sub_umap_before": sb, "sub_umap_after": sa, "sub_written": sa > sb}""".replace(
    "@WORLD_UMAP@", WORLD_UMAP).replace("@SUB_UMAP@", SUB_UMAP).replace("@SUBLEVEL@", SUBLEVEL)

VERIFY_CLEAR_CODE = r"""import unreal, os
W = r"@WORLD_UMAP@"
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
d = [a for a in actors if isinstance(a, unreal.DaedalusSkyDirector)]
def gp(o, name):
    for p in (name, "b_" + name):
        try: return o.get_editor_property(p)
        except Exception: pass
    return None
if d:
    x = d[0]
    try: hour = float(x.get_hour())
    except Exception: hour = float(gp(x, "time_of_day") or -1)
    cr = gp(x, "clock_running")
    result = {"directors": len(d), "mood": str(gp(x, "mood")), "weather": str(gp(x, "weather")), "hour": round(hour, 2),
              "clock_running": (bool(cr) if cr is not None else None),
              "world_umap_mtime": os.path.getmtime(W) if os.path.exists(W) else 0.0}
else:
    result = {"directors": 0}""".replace("@WORLD_UMAP@", WORLD_UMAP)


def post_play_save(ops=None):
    """Run the post-Play contract (post_play_plan). ops (step name -> callable) is injectable for headless tests.
    Never falls back to the bridge 'save' (save_dirty_packages would write a storm-dirty DaedalusWorld)."""
    ops = ops or {
        "stop": lambda: call("stop", timeout=60),
        "restore_world_sky": lambda: run_file(RESTORE_WORLD_SKY, 120),
        "save_sublevel": lambda: py(SAVE_SUBLEVEL_CODE, 120),
        "verify_clear": lambda: py(VERIFY_CLEAR_CODE, 30),
    }
    out = {"order": [], "reclear": False}

    def step(name, key=None):
        out["order"].append(name)
        try:
            r = ops[name]()
        except Exception as e:
            r = {"error": f"{type(e).__name__}: {e}"[:200]}
        out[key or name] = r
        return r

    for name in POST_PLAY_SEQUENCE:
        step(name)
    if needs_reclear(out.get("save_sublevel"), out.get("verify_clear")):
        out["reclear"] = True
        step("restore_world_sky", "restore_world_sky_2")
        step("verify_clear", "verify_clear_2")
    out["clear"], out["problems"] = world_clear(out.get("verify_clear_2", out.get("verify_clear")))
    sub = out.get("save_sublevel")
    out["sublevel_saved"] = bool(isinstance(sub, dict) and sub.get("saved"))
    out["ok"] = bool(out["clear"] and out["sublevel_saved"])
    return out


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
    # Preflight BEFORE TURN START / build: GPU-dead editor (D3D Device Removed) must not burn the slot.
    if not preflight():
        say(f"bridge 127.0.0.1:{PORT} still dead at give-up {dt.datetime.now():%H:%M}; not starting")
        link(f"BLOCKED editor turn (oddsreaper): bridge {PORT} stayed dead until {dt.datetime.now():%H:%M}; never started, "
             "did not touch the editor. Need a make-up once the editor is back.")
        write_result({"stage": "preflight_blocked", "ok": False, "error": "bridge dead until give-up"})
        return {"blocked": "bridge_dead"}
    global T0
    T0 = time.time()  # clock starts only after bridge is alive
    link(f"DOING editor-slot oddsreaper: turn started (HANDOFF -> {NEXT})")
    if "--skip-build" not in sys.argv and ram_ok("build", MIN_BUILD_GB):
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
    if left() > 120 and ram_ok("play", MIN_PLAY_GB):
        try:
            # Force storm at Play start, then settle 20s under storm before the hero shot (round-2 shot sat in
            # Clear daylight for 20s and only flipped at the end — MPC wetness/StormPulse never had time to read).
            call("play", timeout=60); say("Play start (storm then 20s settle)")
            say(f"storm in PIE: {force_storm_in_pie()}")
            time.sleep(20)
            # Re-pin after settle: MoodVolume / director can slip back to Clear during the 20s wait
            # (round-2 daylight hero class). Re-check, re-force if needed, then shoot.
            try:
                chk = py(STORM_CHECK_CODE, 20)
                if not storm_held(chk):
                    say(f"storm slipped after settle ({chk}); re-forcing before play shot")
                    say(f"storm re-force: {force_storm_in_pie()}")
                    time.sleep(2)
                else:
                    say(f"storm still held after settle: {chk}")
            except Exception as e:
                say(f"post-settle storm check failed: {e}; re-forcing once")
                try:
                    say(f"storm re-force: {force_storm_in_pie()}")
                except Exception:
                    pass
                time.sleep(2)
            play_name = "hero_unreal_play.png"
            try:
                take_hero_shot(cam_w, target_w, play_name)
            except Exception as e:
                say(f"play shot skipped: {e}")
            # RGB daylight gate: if the PNG still looks like warm daylight, one storm+reshoot pass.
            play_path = os.path.join(SHOTS, play_name)
            rgb = hero_storm_rgb(play_path)
            if isinstance(rgb, dict) and rgb.get("daylightish"):
                say(f"play hero still daylightish {rgb}; re-force + 5s + reshoot once")
                try:
                    say(f"storm re-force (rgb gate): {force_storm_in_pie()}")
                    time.sleep(5)
                    take_hero_shot(cam_w, target_w, play_name)
                    rgb2 = hero_storm_rgb(play_path)
                    say(f"play hero after rgb-gate reshoot: {rgb2}")
                except Exception as e:
                    say(f"rgb-gate reshoot failed: {e}")
            elif isinstance(rgb, dict):
                say(f"play hero rgb gate ok: {rgb}")
            call("stop", timeout=30); say("Play stop after 20s check")
        except Exception as e:
            say(f"Play check failed: {e}")
            try: call("stop", timeout=20)
            except Exception: pass
    else:
        say(f"skip Play check ({left():.0f}s left before save window, or RAM gate)")
    if not shot_ok and not os.path.exists(os.path.join(SHOTS, "hero_unreal_editor.png")):
        say("hero shot missing after retries; turn continues to save/HANDOFF")
    return isle


if __name__ == "__main__":
    ok, err, blocked = True, "", False
    try:
        r = main()
        if isinstance(r, dict) and r.get("blocked") == "bridge_dead":
            blocked = True
            ok, err = False, "bridge_dead"
    except Exception as e:
        ok, err = False, str(e); say(f"FAIL {e}")
    finally:
        if not blocked:
            # Post-Play contract: stop -> restore_world_sky -> save OddsReaperIsland only -> verify Clear.
            # Never a blind bridge save here (it wrote oddsreaper_storm into shared DaedalusWorld in rounds 3/4).
            pp = {}
            try:
                pp = post_play_save(); say(f"post-Play save: {pp}")
            except Exception as e:
                say(f"post-Play save failed: {e}")
            try:
                subprocess.run(["powershell", "-NoProfile", "-File", TIDY, "-Once"], timeout=60); say("tidy")
            except Exception as e:
                say(f"tidy failed: {e}")
            mins = (time.time() - T0) / 60
            write_result({"stage": "done", "ok": ok, "error": err or None, "mins": round(mins, 2), "post_play": pp})
            link(f"{'DONE' if ok else 'BLOCKED'} island:OddsReaper editor turn {mins:.1f} min: sky director + island placed, shots in {SHOTS}" +
                 ("" if ok else f" | {err[:200]}") +
                 f" | Play stopped, world sky restored (clear={pp.get('clear')}), OddsReaperIsland saved only "
                 f"(saved={pp.get('sublevel_saved')}, reclear={pp.get('reclear')}), tidied")
            link(f"HANDOFF oddsreaper -> {NEXT}: editor saved, Play stopped", to=NEXT)
        open(os.path.join(SHOTS, "turn.log"), "w").write("\n".join(LOG))
