# SPDX-License-Identifier: MIT
"""Claude Unreal Bridge: lets Claude operate the open Unreal Editor (ADR-032), the way the Claude Blender
connector operates Blender.

A small server inside the editor listens on 127.0.0.1 (default port 9877, env DAEDALUS_BRIDGE_PORT). Each
connection sends one JSON line {"id", "type", "params"} and gets one JSON line back
{"id", "status": "ok"|"error", "result" | "message", "traceback"}.

Every command runs on the editor's game thread: socket threads only queue jobs, and a Slate post-tick callback
runs them. A command may be a generator. It then runs one step per editor tick, so it can wait for something
the editor does over several frames (a screenshot being written, Play starting) without freezing the editor.

Commands: ping, get_level_info, get_actor_info, execute_python, viewport_screenshot, play, stop, save,
import_world, frame_world, output_log. Anything else goes through execute_python with the full `unreal` API.

Only 127.0.0.1 is served, so other machines can't reach it. Any program on this computer can while it runs.
Set DAEDALUS_BRIDGE=off to keep it from starting.
"""

import base64
import contextlib
import io
import json
import os
import queue
import socket
import sys
import tempfile
import threading
import time
import traceback
import types

try:
    import unreal
except ImportError:  # pragma: no cover - tests install a stand-in module first
    unreal = None

DEFAULT_PORT = 9877
_jobs = queue.Queue()
_running = []          # generators in progress: (generator, reply box)
_server = {"sock": None, "thread": None, "port": None, "tick": None}


# ---------------------------------------------------------------- helpers

def _vec(v, nd=2):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def _rot(r, nd=2):
    return [round(r.pitch, nd), round(r.yaw, nd), round(r.roll, nd)]


def _actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def _find_actor(name):
    hits = [a for a in _actors() if a.get_actor_label() == name or a.get_name() == name]
    if not hits:
        raise ValueError("no actor labelled or named %r in the open level" % name)
    return hits[0]


def _world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _png_b64(path):
    """The PNG at path as base64, and its size in bytes."""
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii"), len(data)


def _in_pie():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    check = getattr(les, "is_in_play_in_editor", None)
    return bool(check()) if check else False


# ---------------------------------------------------------------- commands

def cmd_ping(_p):
    world = _world()
    return {
        "engine": unreal.SystemLibrary.get_engine_version(),
        "project": unreal.Paths.get_project_file_path(),
        "level": world.get_path_name() if world else None,
        "actors": len(_actors()),
        "playing": _in_pie(),
        "bridge_port": _server["port"],
    }


def cmd_get_level_info(p):
    limit = int(p.get("limit", 300))
    folder = p.get("folder")
    out, total = [], 0
    for a in _actors():
        path = str(a.get_folder_path())
        if folder and not path.startswith(folder):
            continue
        total += 1
        if len(out) < limit:
            out.append({"label": a.get_actor_label(), "class": a.get_class().get_name(), "folder": path,
                        "location": _vec(a.get_actor_location())})
    world = _world()
    return {"level": world.get_path_name() if world else None, "actors_total": total, "actors": out,
            "selected": [a.get_actor_label() for a in
                         unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()]}


def cmd_get_actor_info(p):
    a = _find_actor(p["name"])
    origin, extent = a.get_actor_bounds(False)
    comps = []
    for c in a.get_components_by_class(unreal.ActorComponent):
        entry = {"name": c.get_name(), "class": c.get_class().get_name()}
        if isinstance(c, unreal.StaticMeshComponent):
            mesh = c.get_editor_property("static_mesh")
            entry["mesh"] = mesh.get_path_name() if mesh else None
            entry["materials"] = [m.get_path_name() if m else None for m in c.get_materials()]
        comps.append(entry)
    return {"label": a.get_actor_label(), "name": a.get_name(), "class": a.get_class().get_name(),
            "folder": str(a.get_folder_path()), "location": _vec(a.get_actor_location()),
            "rotation": _rot(a.get_actor_rotation()), "scale": _vec(a.get_actor_scale3d()),
            "bounds": {"origin": _vec(origin), "extent": _vec(extent)}, "components": comps}


def cmd_execute_python(p):
    code = p["code"]
    scope = {"unreal": unreal, "__name__": "__claude__", "result": None}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<claude>", "exec"), scope)
    result = scope.get("result")
    try:
        json.dumps(result)
    except TypeError:
        result = repr(result)
    return {"stdout": buf.getvalue()[-20000:], "result": result}


def cmd_viewport_screenshot(p):
    """Ask the editor for a high-res screenshot of the active viewport, then wait for the file (several frames)."""
    width = int(p.get("width", 1280))
    height = int(p.get("height", 720))
    path = os.path.join(tempfile.gettempdir(), "claude_unreal_%d.png" % int(time.time() * 1000))
    unreal.AutomationLibrary.take_high_res_screenshot(width, height, path)
    deadline = time.time() + float(p.get("timeout", 30))
    last = -1
    while time.time() < deadline:
        yield  # let the editor draw and write the file
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 0 and size == last:   # the size held for a frame: the write is finished
                b64, n = _png_b64(path)
                return {"image_png_base64": b64, "path": path, "bytes": n, "width": width, "height": height}
            last = size
    raise TimeoutError("the editor did not write the screenshot within the timeout; is a level viewport open?")


def cmd_play(p):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not _in_pie():
        if p.get("simulate"):
            les.editor_play_simulate()
        else:
            start = getattr(les, "editor_request_begin_play", None) or les.editor_play_simulate
            start()
    deadline = time.time() + 30
    while not _in_pie() and time.time() < deadline:
        yield
    return {"playing": _in_pie()}


def cmd_stop(_p):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if _in_pie():
        les.editor_request_end_play()
    deadline = time.time() + 30
    while _in_pie() and time.time() < deadline:
        yield
    return {"playing": _in_pie()}


def cmd_save(_p):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    saved_level = les.save_current_level()
    saved_all = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return {"level_saved": bool(saved_level), "dirty_packages_saved": bool(saved_all)}


def _daedalus_modules():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import import_world_package
    import daedalus_view
    return import_world_package, daedalus_view


def cmd_import_world(p):
    """Download the world's package from the Daedalus server, import it, place the view, verify, and frame it."""
    iwp, view = _daedalus_modules()
    server = p.get("server", "http://localhost:8088")
    world = p.get("world", "world-zero")
    zip_path = iwp.fetch(server, world, tempfile.mkdtemp(prefix="daedalus_"))
    manifest, _, _names = iwp.read_package(zip_path)
    iwp.import_into_unreal(zip_path, manifest, live_only=bool(p.get("live")))
    checks = iwp.judge(manifest, iwp.observe(manifest), live_only=bool(p.get("live")))
    iwp.report(manifest, checks, unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
    view.frame_editor(world)
    return {"world": manifest["world"], "geometry": manifest.get("geometry"), "ok": all(c["ok"] for c in checks),
            "checks": checks}


def cmd_frame_world(p):
    _, view = _daedalus_modules()
    return {"framed": bool(view.frame_editor(p.get("world")))}


def cmd_output_log(p):
    """The last lines of the editor's log file, optionally only those containing `filter`."""
    lines = int(p.get("lines", 200))
    flt = p.get("filter")
    logdir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
    logs = sorted((os.path.join(logdir, f) for f in os.listdir(logdir) if f.endswith(".log")),
                  key=os.path.getmtime, reverse=True)
    if not logs:
        return {"file": None, "lines": []}
    with open(logs[0], "r", encoding="utf-8", errors="replace") as f:
        text = f.read().splitlines()
    if flt:
        text = [t for t in text if flt.lower() in t.lower()]
    return {"file": logs[0], "lines": text[-lines:]}


COMMANDS = {
    "ping": cmd_ping,
    "get_level_info": cmd_get_level_info,
    "get_actor_info": cmd_get_actor_info,
    "execute_python": cmd_execute_python,
    "viewport_screenshot": cmd_viewport_screenshot,
    "play": cmd_play,
    "stop": cmd_stop,
    "save": cmd_save,
    "import_world": cmd_import_world,
    "frame_world": cmd_frame_world,
    "output_log": cmd_output_log,
}


# ---------------------------------------------------------------- the game-thread pump

def _finish(box, reply):
    box["reply"] = reply
    box["done"].set()


def _error(req, e):
    return {"id": req.get("id"), "status": "error", "message": "%s: %s" % (type(e).__name__, e),
            "traceback": traceback.format_exc()[-6000:]}


def _start(req, box):
    fn = COMMANDS.get(req.get("type"))
    if fn is None:
        _finish(box, {"id": req.get("id"), "status": "error",
                      "message": "unknown command %r; known: %s" % (req.get("type"), ", ".join(sorted(COMMANDS)))})
        return
    try:
        out = fn(req.get("params") or {})
        if isinstance(out, types.GeneratorType):
            _running.append((out, req, box))
            _step(out, req, box)
        else:
            _finish(box, {"id": req.get("id"), "status": "ok", "result": out})
    except Exception as e:
        _finish(box, _error(req, e))


def _step(gen, req, box):
    try:
        next(gen)
    except StopIteration as stop:
        _running.remove((gen, req, box))
        _finish(box, {"id": req.get("id"), "status": "ok", "result": stop.value})
    except Exception as e:
        _running.remove((gen, req, box))
        _finish(box, _error(req, e))


def pump(_delta=0.0, max_jobs=8):
    """One editor tick: advance running commands one step, then start up to max_jobs queued ones."""
    for gen, req, box in list(_running):
        _step(gen, req, box)
    for _ in range(max_jobs):
        try:
            req, box = _jobs.get_nowait()
        except queue.Empty:
            break
        _start(req, box)


# ---------------------------------------------------------------- the socket side (never touches unreal)

def _client(conn):
    with conn:
        conn.settimeout(3600)
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(1 << 16)
            if not chunk:
                return
            data += chunk
        line = data.split(b"\n", 1)[0]
        try:
            req = json.loads(line.decode("utf-8"))
        except ValueError as e:
            conn.sendall((json.dumps({"id": None, "status": "error", "message": "bad JSON: %s" % e}) + "\n").encode())
            return
        box = {"done": threading.Event(), "reply": None}
        _jobs.put((req, box))
        if not box["done"].wait(timeout=float((req.get("params") or {}).get("bridge_timeout", 1800))):
            box["reply"] = {"id": req.get("id"), "status": "error",
                            "message": "the editor did not run the command in time (is a modal dialog open?)"}
        conn.sendall((json.dumps(box["reply"]) + "\n").encode("utf-8"))


def _accept(sock):
    while True:
        try:
            conn, _ = sock.accept()
        except OSError:
            return  # closed by stop()
        threading.Thread(target=_client, args=(conn,), name="claude-unreal-client", daemon=True).start()


def start(port=None, register_tick=True):
    """Listen on 127.0.0.1:port and pump commands on the editor's ticks. Returns the port."""
    if _server["sock"] is not None:
        return _server["port"]
    port = int(port or os.environ.get("DAEDALUS_BRIDGE_PORT") or DEFAULT_PORT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(8)
    _server.update(sock=sock, port=sock.getsockname()[1])
    _server["thread"] = threading.Thread(target=_accept, args=(sock,), name="claude-unreal-accept", daemon=True)
    _server["thread"].start()
    if register_tick and unreal is not None:
        _server["tick"] = unreal.register_slate_post_tick_callback(pump)
    if unreal is not None:
        unreal.log("Claude Unreal Bridge: listening on 127.0.0.1:%d" % _server["port"])
    return _server["port"]


def stop():
    if _server["tick"] is not None and unreal is not None:
        unreal.unregister_slate_post_tick_callback(_server["tick"])
    if _server["sock"] is not None:
        _server["sock"].close()
    _server.update(sock=None, thread=None, port=None, tick=None)
