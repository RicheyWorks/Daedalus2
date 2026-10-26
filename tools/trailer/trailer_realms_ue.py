# SPDX-License-Identifier: MIT
"""Trailer part 2, filmed in Play: the rainbows, a flight through a sky gate, each realm past a rainbow, the 8-bit
portal realm, and a pull-back. One frame per editor tick, like trailer_ue.py.

    TRAILER_DIR = r"C:/Users/730ri/projects/D2-build/tools/trailer"
    exec(open(TRAILER_DIR + "/trailer_realms_ue.py").read())

Needs world-zero to have gates (POST /api/v1/world/world-zero/gates {toWorld}). The world actor travels through
gate g, the realm is filmed once its chunks stop arriving, and it travels back through the far world's gate.
Writes <take>/frames/f_%05d.png, captions.txt (start|frames|caption) and status.json. Leaves Play in world-zero.
"""
import json
import os
import sys
import time

import unreal

HERE = globals().get("TRAILER_DIR", r"C:\Users\730ri\projects\Daedalus2\tools\trailer")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import importlib  # noqa: E402
import trailer_plan as tp  # noqa: E402

importlib.reload(tp)

W_, H_ = 1280, 720
ROOT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "Daedalus", "trailer")
OUT = os.path.join(ROOT, time.strftime("realms-%m%d-%H%M%S"))
FRAMES = os.path.join(OUT, "frames")
os.makedirs(FRAMES, exist_ok=True)
with open(os.path.join(ROOT, "latest_realms.txt"), "w") as _f:
    _f.write(OUT)

ST = {"i": 0, "seg": "", "errors": [], "done": False, "captions": [], "log": []}


def _world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def _status():
    with open(os.path.join(OUT, "status.json"), "w") as f:
        json.dump({k: v for k, v in ST.items() if k not in ("gen", "handle")}, f)
    with open(os.path.join(OUT, "captions.txt"), "w") as f:
        for a, n, c in ST["captions"]:
            f.write("%d|%d|%s\n" % (a, n, c))


w = _world()
if not w:
    raise RuntimeError("start Play first")
WA = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusWorldActor)[0]
HERO = unreal.GameplayStatics.get_player_pawn(w, 0)
try:
    HERO.set_editor_property("invulnerable", True)
except Exception:
    pass
RT = unreal.RenderingLibrary.create_render_target2d(w, W_, H_, unreal.TextureRenderTargetFormat.RTF_RGBA8)
CAM = unreal.DaedalusFilm.spawn_film_camera(HERO)
CC = CAM.get_component_by_class(unreal.SceneCaptureComponent2D)
CC.set_editor_property("texture_target", RT)
CC.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
CC.set_editor_property("capture_every_frame", False)
CC.set_editor_property("fov_angle", 70.0)


def _shoot(eye, tgt):
    p, y = tp.rotation(eye, tgt)
    CAM.set_actor_location_and_rotation(unreal.Vector(*eye), unreal.Rotator(0.0, p, y), False, True)
    CC.capture_scene()
    unreal.RenderingLibrary.export_render_target(_world(), RT, FRAMES, "f_%05d.png" % ST["i"])
    ST["i"] += 1


def _film(name, caption, cam_of_t):
    """Film one segment: cam_of_t(t in 0..1) -> (eye, target)."""
    n = tp.seg_frames(name)
    ST["seg"] = name
    ST["captions"].append((ST["i"], n, caption))
    for k in range(n):
        _shoot(*cam_of_t(k / max(1, n - 1)))
        yield
    _status()


def _gates():
    gs = sorted(WA.get_editor_property("gates"), key=lambda g: g.gate)
    return [g for g in gs if str(g.to_world)]


def _chunks():
    return len(WA.get_components_by_class(unreal.ProceduralMeshComponent))


def _arrive(world_id, max_ticks=1800):
    """Wait until the actor is world_id and its chunk count has held still for 45 ticks."""
    last, still = -1, 0
    for _ in range(max_ticks):
        n = _chunks()
        if str(WA.get_editor_property("world_id")) == world_id and n > 0:
            still = still + 1 if n == last else 0
            if still >= 45:
                return True
        last = n
        yield
    ST["errors"].append("load timeout: " + world_id)
    return False


def _bounds():
    o, e = WA.get_actor_bounds(False)
    return (o.x, o.y, o.z), (e.x, e.y, e.z)


def _run():
    home = str(WA.get_editor_property("world_id"))
    gates = _gates()
    if not gates:
        ST["errors"].append("world-zero has no gates: POST /api/v1/world/world-zero/gates first")
        return
    centres = [(g.center.x, g.center.y, g.center.z) for g in gates]
    ST["log"].append("gates " + json.dumps([[round(c) for c in x] for x in centres]))
    row = tp.gate_row_shots(centres)
    for name in ("rainbows", "through"):
        cap = dict((s[0], s[2]) for s in tp.REALM_SEGMENTS)[name]
        yield from _film(name, cap, lambda t, p=row[name]: tp.camera("dolly", p, t))
    for k, g in enumerate(gates[:3]):
        to, title = str(g.to_world), str(g.to_title)
        WA.travel_through_gate(g.gate)
        ok = yield from _arrive(to)
        ST["log"].append("%s arrived=%s chunks=%d" % (to, ok, _chunks()))
        if ok:
            o, e = _bounds()
            orbit = tp.realm_orbit(o, e)
            yield from _film("realm:%d" % k, title.upper(), lambda t, p=orbit: tp.camera("orbit", p, t))
        back = [b for b in sorted(WA.get_editor_property("gates"), key=lambda b: b.gate) if str(b.to_world) == home]
        if back:
            WA.travel_through_gate(back[0].gate)
        else:
            WA.set_editor_property("world_id", home)
            WA.load_world()
        yield from _arrive(home)
    yield from _pixel()
    yield from _film("heal", dict((s[0], s[2]) for s in tp.REALM_SEGMENTS)["heal"],
                     lambda t, p=row["heal"]: tp.camera("dolly", p, t))


def _kv(s):
    out = {}
    for part in str(s).split():
        if "=" in part:
            a, b = part.split("=", 1)
            out[a] = b
    return out


def _pixel():
    """The 8-bit realm: its own framebuffer is the frame (768x720; normalize letterboxes it)."""
    h = HERO
    if h.is_realm_open():
        h.exit_realm()
    h.enter_realm(7)
    for _ in range(600):
        if "map=" in str(h.realm_state()):
            break
        yield
    for _ in range(8):
        if _kv(h.realm_state()).get("ui") == "NONE":
            break
        h.realm_input("b")
    h.realm_input("toughen")
    n = tp.seg_frames("pixel")
    ST["seg"] = "pixel"
    ST["captions"].append((ST["i"], n, dict((s[0], s[2]) for s in tp.REALM_SEGMENTS)["pixel"]))
    h.realm_input("hold:right")
    for k in range(n):
        if k == int(n * 0.25):
            h.realm_input("release:right")
            h.realm_input("hold:down")
        if k == int(n * 0.45):
            h.realm_input("release:down")
            h.realm_input("battle:BLIGHT_SLIME+PUFFCAP")
        if k == int(n * 0.8):
            h.realm_input("autofight")
        if not h.realm_capture(os.path.join(FRAMES, "f_%05d.png" % ST["i"])):
            ST["errors"].append("realm capture failed at %d" % ST["i"])
            _shoot((0, 0, 20000), (1, 0, 0))   # keep the frame count whole
        else:
            ST["i"] += 1
        yield
    for _ in range(8):
        if _kv(h.realm_state()).get("ui") == "NONE":
            break
        h.realm_input("b")
    h.exit_realm()
    for _ in range(20):
        yield
    _status()


def _tick(dt):
    if ST["done"]:
        return
    try:
        if not _world():
            ST["errors"].append("Play stopped at frame %d" % ST["i"])
            _finish()
            return
        next(ST["gen"])
    except StopIteration:
        _finish()
    except Exception as e:
        ST["errors"].append(repr(e)[:200])
        _finish()


def _finish():
    ST["done"] = True
    if ST.get("handle") is not None:
        unreal.unregister_slate_post_tick_callback(ST["handle"])
        ST["handle"] = None
    try:
        CAM.destroy_actor()
    except Exception:
        pass
    _status()


ST["gen"] = _run()
ST["handle"] = unreal.register_slate_post_tick_callback(_tick)
_status()
result = {"out": OUT}
