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
    return [float(x) if nd is None else round(x, nd) for x in (v.x, v.y, v.z)]


def _rot(r, nd=2):
    return [float(x) if nd is None else round(x, nd) for x in (r.pitch, r.yaw, r.roll)]


def _actors():
    """Every actor of the open level. During Play the editor refuses EditorActorSubsystem (it logs
    'The Editor is currently in a play mode' as an error on every status poll, 2026-10-13), so the Play world's
    actors are listed through GameplayStatics instead; they are the live ones a bot wants anyway."""
    if _in_pie():
        ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        game = getattr(ues, "get_game_world", None)
        world = game() if game else None
        if world is not None:
            return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def _selected():
    """Selected actors: none during Play (selection is an editor thing, and asking logs an error)."""
    if _in_pie():
        return []
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()


def _find_actor(name):
    actors = list(_actors())
    exact = [a for a in actors if a.get_path_name() == name]
    hits = exact or [a for a in actors if a.get_actor_label() == name or a.get_name() == name]
    if not hits:
        raise ValueError("no actor labelled or named %r in the open level" % name)
    if len(hits) != 1:
        raise ValueError("ambiguous actor %r; use an exact path: %s" %
                         (name, ", ".join(sorted(a.get_path_name() for a in hits))))
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
            "selected": [a.get_actor_label() for a in _selected()]}


def cmd_get_actor_info(p):
    return _actor_info(_find_actor(p["name"]))


def _actor_info(a, precise=False, selected=None):
    """Shared actor value serializer; legacy readback keeps its rounding and keys."""
    nd = None if precise else 2
    origin, extent = a.get_actor_bounds(False)
    comps = []
    components = a.get_components_by_class(unreal.ActorComponent)
    if precise and len(components) > MAX_ACTORS:
        raise ValueError("actor observation exceeds the component limit %d" % MAX_ACTORS)
    for c in components:
        entry = {"name": c.get_name(), "class": c.get_class().get_name()}
        if precise:
            entry["path"] = c.get_path_name()
        if isinstance(c, unreal.StaticMeshComponent):
            mesh = c.get_editor_property("static_mesh")
            entry["mesh"] = mesh.get_path_name() if mesh else None
            materials = c.get_materials()
            if precise and len(materials) > MAX_ACTORS:
                raise ValueError("actor observation exceeds the material slot limit %d" % MAX_ACTORS)
            entry["materials"] = [m.get_path_name() if m else None for m in materials]
        comps.append(entry)
    out = {"label": a.get_actor_label(), "name": a.get_name(), "class": a.get_class().get_name(),
           "folder": str(a.get_folder_path()), "location": _vec(a.get_actor_location(), nd),
           "rotation": _rot(a.get_actor_rotation(), nd), "scale": _vec(a.get_actor_scale3d(), nd),
           "bounds": {"origin": _vec(origin, nd), "extent": _vec(extent, nd)}, "components": comps}
    if precise:
        parent = a.get_attach_parent_actor()
        out.update(path=a.get_path_name(), class_path=a.get_class().get_path_name(),
                   parent_path=parent.get_path_name() if parent is not None else None,
                   selected=a.get_path_name() in (selected or set()))
    return out


def _scene_source():
    """Resolve the observation world once; never fall back to editor actors during Play."""
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    playing = _in_pie()
    world = subsystem.get_game_world() if playing else subsystem.get_editor_world()
    if world is None:
        raise SceneWorldUnavailable("the %s world is unavailable" % ("Play" if playing else "editor"))
    if playing:
        actors = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
        selected = set()
    else:
        actors_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = list(actors_subsystem.get_all_level_actors())
        selected = {a.get_path_name() for a in actors_subsystem.get_selected_level_actors()}
    return world, "pie" if playing else "editor", actors, selected


from claude_unreal_scene import MAX_ACTORS, SceneCommands, SceneWorldUnavailable
_scene = SceneCommands(_scene_source, _actor_info)


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


def _remote_node(want):
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
    # `want` (this project's folder) is read on the game thread by the caller: this runs on a background thread,
    # where touching the unreal API raises "Attempted to access Unreal API from outside the main game thread".
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


_remote_lock = threading.Lock()


def _run_remote(code, box, want):
    """Background thread: send the wrapped code through Remote Execution, unattended, and keep the reply.
    Never touches the unreal module (game thread only).

    One Remote Execution command connection is shared by every client thread and Epic's client is not
    thread-safe: concurrent run_command calls swapped replies (the art queue got another bot's `true` and failed
    with "'bool' object is not subscriptable"). So calls are serialized, but the wait is bounded: a run_command
    that never returned once held a plain lock and wedged every later call. On a 30 s wait the call runs
    in-process instead, and any failure drops the connection so the next call reconnects. (2026-10-12)"""
    got_lock = _remote_lock.acquire(timeout=30)
    try:
        if not got_lock:
            box["fallback"] = "Remote Execution busy for more than 30 s"
            return
        got = _remote_node(want)
        if got is None:
            box["fallback"] = _remote["error"]
            return
        rx, _node = got
        box["reply"] = rx.run_command(_wrap(code), unattended=True)
    except Exception as e:
        box["fallback"] = "Remote Execution failed: %s" % e
        try:
            if _remote["rx"] is not None:
                _remote["rx"].stop()
        except Exception:
            pass
        _remote.update(rx=None, node=None)
    finally:
        if got_lock:
            _remote_lock.release()
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
    want = os.path.normcase(os.path.abspath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())))
    threading.Thread(target=_run_remote, args=(code, box, want), name="claude-unreal-remote", daemon=True).start()
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


def cmd_capture_view(p):
    """A picture of what the editor camera sees, rendered by a SceneCapture2D into a render target and exported
    as PNG: no editor UI, and no dependence on the viewport's size or focus. The capture actor is removed after."""
    width, height = int(p.get("width", 1280)), int(p.get("height", 720))
    world = _world()
    loc, rot = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info()
    rt = unreal.RenderingLibrary.create_render_target2d(world, width, height)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cap = actors.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot)
    try:
        comp = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
        comp.set_editor_property("texture_target", rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.capture_scene()
        yield   # let the render thread finish the capture before reading it back
        out_dir = tempfile.gettempdir()
        name = "claude_unreal_capture_%d" % int(time.time() * 1000)
        unreal.RenderingLibrary.export_render_target(world, rt, out_dir, name)
        path = os.path.join(out_dir, name + ".png")
        deadline = time.time() + 20
        while not (os.path.exists(path) and os.path.getsize(path) > 0):
            if time.time() > deadline:
                raise TimeoutError("the render target was not written")
            yield
        b64, n = _png_b64(path)
        return {"image_png_base64": b64, "path": path, "bytes": n, "width": width, "height": height}
    finally:
        actors.destroy_actor(cap)


def cmd_batch(p):
    """Run several commands in order as one editor transaction (one undo). Each item is {"type", "params"} and
    passes the same policy as a single call; the batch stops at the first error unless keep_going is true."""
    items = p.get("commands") or []
    if not isinstance(items, list) or not items:
        raise ValueError("batch needs commands: [{type, params}, ...]")
    for it in items:
        name = it.get("type")
        if name not in COMMANDS or name in ("batch",):
            raise ValueError("batch can't run %r" % name)
        risk = RISK_OF.get(name, "MUTATE")
        if not POLICY.get(risk, False):
            raise PermissionError("%s in the batch is %s, which the policy does not allow" % (name, risk))
    results = []
    with unreal.ScopedEditorTransaction(p.get("transaction", "Claude batch")):
        for it in items:
            try:
                out = COMMANDS[it["type"]](it.get("params") or {})
                if isinstance(out, types.GeneratorType):
                    while True:
                        try:
                            next(out)
                        except StopIteration as stop:
                            out = stop.value
                            break
                        yield
                results.append({"type": it["type"], "status": "ok", "result": out})
            except Exception as e:
                results.append({"type": it["type"], "status": "error", "message": "%s: %s" % (type(e).__name__, e)})
                if not p.get("keep_going"):
                    break
    return {"results": results, "ok": all(r["status"] == "ok" for r in results) and len(results) == len(items)}


def cmd_list_commands(_p):
    return {"commands": [{"name": n, "description": DESCRIPTIONS.get(n, ""), "params": PARAMS.get(n, {}),
                          "risk": RISK_OF.get(n, "MUTATE")} for n in sorted(COMMANDS)],
            "policy": dict(POLICY), "risks": list(RISKS)}


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
    "capture_view": cmd_capture_view,
    "batch": cmd_batch,
    "job_result": lambda p: _job_result({}, p).get("result"),   # answered on the socket thread; listed here
    "scene_snapshot": _scene.snapshot,
    "scene_verify": _scene.verify,
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
    "capture_view": "A PNG of what the editor camera sees, rendered by a scene capture (no editor UI); params width, height",
    "batch": "Several commands in order as one undo step; params commands [{type, params}], transaction, keep_going",
    "job_result": "The answer to a command sent with async: true; params job_id. status running or done",
    "scene_snapshot": "Read one bounded page of loaded actors with exact paths and world/session context",
    "scene_verify": "Read exact actor paths and compare explicit expected values; returns observed values and mismatches",
}
PARAMS = {
    "get_level_info": {"limit": "int", "folder": "str"}, "get_actor_info": {"name": "str (required)"},
    "execute_python": {"code": "str (required)"}, "viewport_screenshot": {"width": "int", "height": "int"},
    "play": {"simulate": "bool"}, "output_log": {"lines": "int", "filter": "str"},
    "capture_view": {"width": "int", "height": "int"},
    "batch": {"commands": "list (required)", "transaction": "str", "keep_going": "bool"},
    "job_result": {"job_id": "str (required)"},
    "scene_snapshot": {"folder": "str", "offset": "int", "limit": "int"},
    "scene_verify": {"schema_version": "int (required)", "context": "dict (required)",
                     "actors": "list (required)", "tolerance": "dict"},
}


# ---------------------------------------------------------------- the gateway contract
# Ported from the CSRBT and FlowersForever harness gateways. Every command declares a risk, least to most
# consequential; a policy says which risks are allowed. DESTRUCTIVE cannot be allowed without MUTATE. A command
# that does not declare a risk is held at MUTATE. The policy comes from CLAUDE_UNREAL_ALLOW (a comma list, e.g.
# "READ,SENSITIVE_READ"); the default allows everything, because this bridge exists for full control.
RISKS = ("READ", "SENSITIVE_READ", "MUTATE", "DESTRUCTIVE")
RISK_OF = {
    "ping": "READ", "list_commands": "READ", "get_level_info": "READ", "get_actor_info": "READ", "output_log": "READ",
    "viewport_screenshot": "SENSITIVE_READ",
    "execute_python": "MUTATE", "play": "MUTATE", "stop": "MUTATE",
    "save": "DESTRUCTIVE",
    "capture_view": "SENSITIVE_READ", "batch": "MUTATE", "job_result": "READ",
    "scene_snapshot": "READ", "scene_verify": "READ",
}


def _policy_from_env():
    raw = os.environ.get("CLAUDE_UNREAL_ALLOW", "").strip()
    allowed = set(RISKS) if not raw else {r.strip().upper() for r in raw.split(",") if r.strip()}
    pol = {r: (r in allowed) for r in RISKS}
    if pol["DESTRUCTIVE"] and not pol["MUTATE"]:
        pol["DESTRUCTIVE"] = False
    return pol


POLICY = _policy_from_env()


def set_policy(allowed):
    """Allow exactly these risks (an iterable of names). DESTRUCTIVE needs MUTATE."""
    allowed = {a.upper() for a in allowed}
    bad = allowed - set(RISKS)
    if bad:
        raise ValueError("unknown risk(s) %s; known: %s" % (sorted(bad), ", ".join(RISKS)))
    if "DESTRUCTIVE" in allowed and "MUTATE" not in allowed:
        raise ValueError("DESTRUCTIVE cannot be allowed without MUTATE")
    POLICY.clear()
    POLICY.update({r: (r in allowed) for r in RISKS})


def register(name, fn, description="", params=None, risk="MUTATE"):
    """Add a command, e.g. register("daedalus.import_world", fn, "...", {"server": "str"}, risk="MUTATE").
    Namespaced names ("project.verb") keep add-ons from colliding with each other and with built-ins.
    Registering a name again replaces it, so a project can reload its commands."""
    if not name or not callable(fn):
        raise ValueError("register needs a name and a callable")
    if risk not in RISKS:
        raise ValueError("risk must be one of %s" % ", ".join(RISKS))
    COMMANDS[name] = fn
    DESCRIPTIONS[name] = description
    PARAMS[name] = dict(params or {})
    RISK_OF[name] = risk


# request_id replay: a client that retries after a timeout sends the same request_id and gets the first answer
# back (marked replayed), instead of running the command twice. Kept for the last REPLAY_KEEP requests.
REPLAY_KEEP = 256
_replies = {}
_replay_order = []


def _remember(rid, reply):
    if rid is None:
        return
    _replies[rid] = reply
    _replay_order.append(rid)
    while len(_replay_order) > REPLAY_KEEP:
        _replies.pop(_replay_order.pop(0), None)


# ---------------------------------------------------------------- the game-thread pump

def _finish(box, reply):
    rid = box.get("request_id")
    if rid is not None and reply.get("status") == "ok":
        _remember(rid, dict(reply))
    box["reply"] = reply
    box["done"].set()


def _error(req, e):
    return {"id": req.get("id"), "status": "error", "message": "%s: %s" % (type(e).__name__, e),
            "traceback": traceback.format_exc()[-6000:]}


def _start(req, box):
    params = req.get("params") or {}
    rid = params.get("request_id")
    if rid is not None and rid in _replies:
        reply = dict(_replies[rid])
        reply["id"], reply["replayed"] = req.get("id"), True
        _finish(box, reply)
        return
    box["request_id"] = rid
    fn = COMMANDS.get(req.get("type"))
    if fn is None:
        _finish(box, {"id": req.get("id"), "status": "error", "code": "UNKNOWN",
                      "message": "unknown command %r; known: %s" % (req.get("type"), ", ".join(sorted(COMMANDS)))})
        return
    risk = RISK_OF.get(req.get("type"), "MUTATE")
    if not POLICY.get(risk, False):
        _finish(box, {"id": req.get("id"), "status": "error", "code": "REFUSED", "risk": risk,
                      "message": "%s is %s, which this bridge's policy does not allow (CLAUDE_UNREAL_ALLOW)"
                                 % (req.get("type"), risk)})
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
        params = req.get("params") or {}
        if req.get("type") == "job_result":
            conn.sendall((json.dumps(_job_result(req, params)) + "\n").encode("utf-8"))
            return
        box = {"done": threading.Event(), "reply": None}
        if params.get("async"):
            # Answer now with a job id; the command runs on the game thread as usual and job_result fetches it.
            # A long import then never meets a client timeout, so a client never resends it.
            jid = "job-%d-%d" % (int(time.time() * 1000), len(_job_boxes))
            _job_boxes[jid] = (box, time.time())
            _jobs.put((req, box))
            conn.sendall((json.dumps({"id": req.get("id"), "status": "ok", "result": {"job_id": jid, "state": "running"}})
                          + "\n").encode("utf-8"))
            return
        _jobs.put((req, box))
        if not box["done"].wait(timeout=float((req.get("params") or {}).get("bridge_timeout", 1800))):
            box["reply"] = {"id": req.get("id"), "status": "error",
                            "message": "the editor did not run the command in time (is a modal dialog open?)"}
        conn.sendall((json.dumps(box["reply"]) + "\n").encode("utf-8"))


_job_boxes = {}
JOB_KEEP_S = 3600


def _job_result(req, params):
    """Socket-thread side of async jobs: no unreal calls, so it answers even while the game thread is busy."""
    now = time.time()
    for k in [k for k, (_b, t) in _job_boxes.items() if now - t > JOB_KEEP_S]:
        _job_boxes.pop(k, None)
    jid = params.get("job_id")
    if jid not in _job_boxes:
        return {"id": req.get("id"), "status": "error", "code": "UNKNOWN_JOB", "message": "no job %r (or it expired)" % jid}
    box, _t = _job_boxes[jid]
    if not box["done"].is_set():
        return {"id": req.get("id"), "status": "ok", "result": {"job_id": jid, "state": "running"}}
    return {"id": req.get("id"), "status": "ok", "result": {"job_id": jid, "state": "done", "reply": box["reply"]}}


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
