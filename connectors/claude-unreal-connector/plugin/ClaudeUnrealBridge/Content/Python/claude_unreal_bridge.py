# SPDX-License-Identifier: MIT
"""Claude Unreal Bridge: lets Claude, or any agent, operate the open Unreal Editor.
Part of claude-unreal-connector (MIT). It works the same way as the Claude Blender connector.

A small server inside the editor listens on 127.0.0.1 (default port 9877, env CLAUDE_UNREAL_PORT). Each
connection sends one JSON line {"id", "type", "params"} and gets one JSON line back
{"id", "status": "ok"|"error", "result" | "message", "traceback"}.

Every command runs on the editor's game thread: socket threads only queue jobs, and a Slate post-tick callback
runs them. A command may be a generator. It then runs one step per editor tick, so it can wait for something
the editor does over several frames (a screenshot being written, Play starting) without freezing the editor.

Built-in commands: ping, list_commands, get_level_info, get_actor_info, execute_python, viewport_screenshot,
play, stop, save, output_log. Anything else goes through execute_python, with the full `unreal` API.

Projects add their own commands with register(name, fn, description, params). DaedalusLink, for example,
registers daedalus.import_world. Agents find them with list_commands and call them by name. A command
function takes the params dict and returns a JSON-serializable value, or it is a generator that yields once
per editor tick until it returns.

Only 127.0.0.1 is served, so other machines can't reach it. Any program on this computer can while it runs.
Set CLAUDE_UNREAL_BRIDGE=off to keep it from starting.
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


# ---------------------------------------------------------------- execute_python, unattended

RESULT_MARK = "__CLAUDE_UNREAL_RESULT__"
_remote = {"rx": None, "node": None, "error": None}


def _wrap(code):
    """Claude's code, wrapped so its `result` variable comes back as one marked line of output."""
    return ("import json as _cj, unreal\n"
            "result = None\n"
            "exec(compile(%r, '<claude>', 'exec'))\n"
            "try:\n    _cr = _cj.dumps(result)\nexcept TypeError:\n    _cr = _cj.dumps(repr(result))\n"
            "print(%r + _cr)\n") % (code, RESULT_MARK)


def _remote_node():
    """Unreal's own Python Remote Execution, connected to this editor. Commands it runs carry the "unattended"
    flag, so the editor cancels a modal dialog instead of waiting on it (a modal on the game thread would freeze
    the bridge). Needs Project Settings > Python > Enable Remote Execution (bRemoteExecution, which install.ps1
    sets). Returns (RemoteExecution, node id), or None when it is off. Runs off the game thread."""
    if _remote["rx"] is not None:
        return _remote["rx"], _remote["node"]
    try:
        import remote_execution as rex   # Epic's client, shipped in PythonScriptPlugin/Content/Python
    except ImportError as e:
        _remote["error"] = "remote_execution.py not found (%s)" % e
        return None
    rx = rex.RemoteExecution()
    rx.start()
    want = os.path.normcase(os.path.abspath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())))
    deadline = time.time() + 3.0
    node = None
    while time.time() < deadline and node is None:
        nodes = list(rx.remote_nodes)
        for n in nodes:
            root = os.path.normcase(os.path.abspath(n.get("project_root", "") or ""))
            if root.rstrip("\\/") == want.rstrip("\\/"):
                node = n.get("node_id")
                break
        if node is None and len(nodes) == 1 and time.time() > deadline - 1.5:
            node = nodes[0].get("node_id")   # one editor answered: this one, even if it names its project differently
        time.sleep(0.1)
    if node is None:
        rx.stop()
        _remote["error"] = "Remote Execution is off (Project Settings > Python > Enable Remote Execution)"
        return None
    rx.open_command_connection(node)
    _remote.update(rx=rx, node=node, error=None)
    return rx, node


def _run_remote(code, box):
    """Background thread: send the wrapped code through Remote Execution, unattended, and keep the reply."""
    try:
        got = _remote_node()
        if got is None:
            box["fallback"] = _remote["error"]
            return
        rx, _node = got
        box["reply"] = rx.run_command(_wrap(code), unattended=True)
    except Exception as e:
        box["fallback"] = "Remote Execution failed: %s" % e
        _remote.update(rx=None, node=None)
    finally:
        box["done"] = True


def _exec_here(code):
    scope = {"unreal": unreal, "__name__": "__claude__", "result": None}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<claude>", "exec"), scope)
    result = scope.get("result")
    try:
        json.dumps(result)
    except TypeError:
        result = repr(result)
    return {"stdout": buf.getvalue()[-20000:], "result": result, "unattended": False}


def cmd_execute_python(p):
    """Run Claude's code. By default it goes through Remote Execution in unattended mode (dialogs are canceled,
    not waited on), while this command yields editor ticks so the editor is free to run it. Without Remote
    Execution, or with unattended=false, it runs here directly."""
    code = p["code"]
    if not p.get("unattended", True):
        return _exec_here(code)
    box = {"done": False, "reply": None, "fallback": None}
    threading.Thread(target=_run_remote, args=(code, box), name="claude-unreal-remote", daemon=True).start()
    deadline = time.time() + float(p.get("timeout", 600))
    while not box["done"]:
        if time.time() > deadline:
            raise TimeoutError("the editor did not run the code within the timeout")
        yield
    if box["fallback"]:
        out = _exec_here(code)
        out["note"] = box["fallback"] + "; ran directly, so a modal dialog would block the editor"
        return out
    reply = box["reply"] or {}
    lines, result = [], None
    for entry in reply.get("output", []) or []:
        text = entry.get("output", "") if isinstance(entry, dict) else str(entry)
        if text.startswith(RESULT_MARK):
            result = json.loads(text[len(RESULT_MARK):])
        else:
            lines.append(text)
    if not reply.get("success", False):
        raise RuntimeError((reply.get("result") or "the code raised an error") + "\n" + "\n".join(lines)[-6000:])
    return {"stdout": "\n".join(lines)[-20000:], "result": result, "unattended": True}


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


def cmd_list_commands(_p):
    return {"commands": [{"name": n, "description": DESCRIPTIONS.get(n, ""), "params": PARAMS.get(n, {})}
                         for n in sorted(COMMANDS)]}


COMMANDS = {
    "ping": cmd_ping,
    "list_commands": cmd_list_commands,
    "get_level_info": cmd_get_level_info,
    "get_actor_info": cmd_get_actor_info,
    "execute_python": cmd_execute_python,
    "viewport_screenshot": cmd_viewport_screenshot,
    "play": cmd_play,
    "stop": cmd_stop,
    "save": cmd_save,
    "output_log": cmd_output_log,
}


DESCRIPTIONS = {
    "ping": "Engine version, project, open level, actor count, whether Play is running",
    "list_commands": "Every command this bridge answers, with its description and parameters",
    "get_level_info": "Actors in the open level (label, class, Outliner folder, location); params limit, folder",
    "get_actor_info": "One actor by label or name: transform, bounds, components, meshes, materials",
    "execute_python": "Run Python on the game thread with `unreal` imported; returns stdout and `result`",
    "viewport_screenshot": "A PNG of the active level viewport (base64); params width, height",
    "play": "Start Play In Editor (or Simulate) and wait until it runs; param simulate",
    "stop": "Stop Play In Editor and wait until it ends",
    "save": "Save the current level and every changed asset",
    "output_log": "The last lines of the editor log; params lines, filter",
}
PARAMS = {
    "get_level_info": {"limit": "int", "folder": "str"}, "get_actor_info": {"name": "str (required)"},
    "execute_python": {"code": "str (required)"}, "viewport_screenshot": {"width": "int", "height": "int"},
    "play": {"simulate": "bool"}, "output_log": {"lines": "int", "filter": "str"},
}


def register(name, fn, description="", params=None):
    """Add a command, e.g. register("daedalus.import_world", fn, "...", {"server": "str"}). Namespaced names
    ("project.verb") keep add-ons from colliding with each other and with built-ins. Registering a name
    again replaces it, so a project can reload its commands."""
    if not name or not callable(fn):
        raise ValueError("register needs a name and a callable")
    COMMANDS[name] = fn
    DESCRIPTIONS[name] = description
    PARAMS[name] = dict(params or {})


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


_pumping = []   # non-empty while pump() runs


def pump(_delta=0.0, max_jobs=8):
    """One editor tick: advance running commands one step, then start up to max_jobs queued ones.

    Some editor calls tick Slate themselves (take_high_res_screenshot does), which calls pump() again while a
    command is mid-step. That nested tick does nothing: the outer pump is still running, so the generator
    cannot be stepped again ("generator already executing") and no new command may start inside another.
    """
    if _pumping:
        return
    _pumping.append(True)
    try:
        for gen, req, box in list(_running):
            _step(gen, req, box)
        for _ in range(max_jobs):
            try:
                req, box = _jobs.get_nowait()
            except queue.Empty:
                break
            _start(req, box)
    finally:
        _pumping.clear()


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
    port = int(port or os.environ.get("CLAUDE_UNREAL_PORT") or os.environ.get("DAEDALUS_BRIDGE_PORT") or DEFAULT_PORT)
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
