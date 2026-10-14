# SPDX-License-Identifier: MIT
"""More control over Unreal from the bridge (Richey, 2026-10-13). Registered by daedalus_bridge_commands:

    daedalus.console   {cmd}                       any console command, in the Play world when Play runs, else the editor
                                                   (stat fps, r.ScreenPercentage 50, slomo 0.5, t.MaxFPS 60, showflag.Fog 0,
                                                   Automation RunTests Daedalus, ...). Returns the log lines it produced.
    daedalus.log_report {all?}                     errors/warnings since Play began (or the whole log), classified and counted
    daedalus.input     {action, x?, y?, z?, seconds?}  inject hero input for a while: Move x=right y=forward, Jump, Attack...
    daedalus.goto      {x, y, z, yaw?, snap?} | {actor}   teleport the hero to a point (snapped to the ground) or to an actor's label
    daedalus.look      {yaw, pitch}                 point the camera
    daedalus.state     {}                           one line of the hero's state (position, health, weapon, realm, what is open)
    daedalus.automation {filter, timeout?}          run the editor's automation tests matching filter, collect PASS/FAIL from the log
    daedalus.cvar      {name, value?}               read or set a console variable

Everything is PIE-safe: nothing here touches the editor's actor subsystem while Play runs.
"""
import re
import time

import unreal

STRIP = re.compile(r"^\[[^\]]+\]\[\s*\d+\]")


def _playing():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    check = getattr(les, "is_in_play_in_editor", None)
    return bool(check()) if check else False


def _game_world():
    """The Play world while Play runs, else the editor world (UWorld exposes no 'am I a game world' in Python)."""
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    g = getattr(ues, "get_game_world", None)
    w = g() if (g and _playing()) else None
    return w if w is not None else ues.get_editor_world()


def _hero():
    w = _game_world()
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusHero):
        return a
    return None


def _log_lines():
    import os
    logdir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
    logs = sorted((os.path.join(logdir, f) for f in os.listdir(logdir) if f.endswith(".log")), key=os.path.getmtime, reverse=True)
    if not logs:
        return []
    with open(logs[0], "r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def console(p):
    cmd = str(p.get("cmd", "")).strip()
    if not cmd:
        raise ValueError("cmd is required")
    before = len(_log_lines())
    unreal.SystemLibrary.execute_console_command(_game_world(), cmd)
    time.sleep(0.05)
    after = _log_lines()[before:]
    return {"cmd": cmd, "playing": _playing(), "log": [STRIP.sub("", l).strip() for l in after][-60:]}


def cvar(p):
    name = str(p.get("name", "")).strip()
    if not name:
        raise ValueError("name is required")
    if "value" in p and p["value"] is not None:
        unreal.SystemLibrary.execute_console_command(_game_world(), "%s %s" % (name, p["value"]))
    val = None
    for getter in (unreal.SystemLibrary.get_console_variable_float_value, unreal.SystemLibrary.get_console_variable_int_value):
        try:
            val = getter(name)
            break
        except Exception:
            continue
    return {"name": name, "value": val}


def log_report(p):
    lines = _log_lines()
    if not p.get("all"):
        starts = [i for i, l in enumerate(lines) if "Bringing World" in l and "up for play" in l]
        if starts:
            lines = lines[starts[-1]:]
    errs, warns = {}, {}
    noise = re.compile(r"LogPython|LogStaticMesh: Display|Display:")
    for l in lines:
        if noise.search(l):
            continue
        key = re.sub(r"UEDPIE_\d+_\S+", "UEDPIE...", re.sub(r"/Game/\S+", "/Game/...", STRIP.sub("", l).strip()))[:160]
        if ": Error:" in l:
            errs[key] = errs.get(key, 0) + 1
        elif ": Warning:" in l:
            warns[key] = warns.get(key, 0) + 1
    top = lambda d: sorted(d.items(), key=lambda kv: -kv[1])[:8]
    return {"errors": sum(errs.values()), "warnings": sum(warns.values()),
            "top_errors": [{"n": n, "line": k} for k, n in top(errs)], "top_warnings": [{"n": n, "line": k} for k, n in top(warns)]}


def hero_input(p):
    h = _hero()
    if not h:
        raise RuntimeError("no hero in the world: start Play first")
    v = unreal.Vector(float(p.get("x", 0.0)), float(p.get("y", 0.0)), float(p.get("z", 0.0)))
    if p.get("action", "").lower() in ("jump", "attack", "melee", "dash", "aim", "switch", "interact", "sprint", "viewcycle", "callvehicle", "nextcube", "shoulder", "menu", "view", "inventory") and v.x == 0 and v.y == 0 and v.z == 0:
        v = unreal.Vector(1.0, 0.0, 0.0)   # a button press is a value of 1
    return {"result": h.inject(str(p.get("action", "")), v, float(p.get("seconds", 0.0))), "state": h.control_state()}


def goto(p):
    h = _hero()
    if not h:
        raise RuntimeError("no hero in the world: start Play first")
    if p.get("actor"):
        w = _game_world()
        target = None
        for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
            if a.get_name() == p["actor"] or a.get_actor_label() == p["actor"]:
                target = a
                break
        if not target:
            raise ValueError("no actor named %r in the Play world" % p["actor"])
        loc = target.get_actor_location() + target.get_actor_forward_vector() * -250.0 + unreal.Vector(0, 0, 100)
        yaw = target.get_actor_rotation().yaw
    else:
        loc = unreal.Vector(float(p["x"]), float(p["y"]), float(p.get("z", 0.0)))
        yaw = float(p.get("yaw", 0.0))
    ok = h.teleport(loc, yaw, bool(p.get("snap", True)))
    return {"ok": ok, "state": h.control_state()}


def look(p):
    h = _hero()
    if not h:
        raise RuntimeError("no hero in the world: start Play first")
    h.look(float(p.get("yaw", 0.0)), float(p.get("pitch", 0.0)))
    return {"state": h.control_state()}


def state(p):
    h = _hero()
    return {"state": h.control_state() if h else "no hero (not in Play)", "playing": _playing()}


def automation(p):
    """Run 'Automation RunTests <filter>' and collect results from the log until 'Automation Test Queue Empty'."""
    flt = str(p.get("filter", "Daedalus"))
    timeout = float(p.get("timeout", 120))
    before = len(_log_lines())
    unreal.SystemLibrary.execute_console_command(_game_world(), "Automation RunTests " + flt)
    t0 = time.time()
    done = False
    results = []
    while time.time() - t0 < timeout:
        time.sleep(1.0)
        new = _log_lines()[before:]
        for l in new:
            if "Test Completed" in l or "Automation Test Succeeded" in l or "Automation Test Failed" in l or "TestResult" in l:
                results.append(STRIP.sub("", l).strip()[:200])
            if "Automation Test Queue Empty" in l:
                done = True
        if done:
            break
    passed = sum(1 for r in results if "Succeeded" in r or "Success" in r)
    failed = sum(1 for r in results if "Failed" in r or "Fail" in r)
    return {"filter": flt, "done": done, "passed": passed, "failed": failed, "lines": results[-40:], "seconds": round(time.time() - t0, 1)}


def register(bridge):
    bridge.register("daedalus.console", console, "Run a console command (Play world when Play runs, else the editor); returns the log lines it produced", {"cmd": "str (required)"})
    bridge.register("daedalus.cvar", cvar, "Read or set a console variable", {"name": "str (required)", "value": "str|number (optional: set)"})
    bridge.register("daedalus.log_report", log_report, "Errors and warnings since Play began (all: whole log), classified with counts", {"all": "bool"})
    bridge.register("daedalus.input", hero_input, "Inject hero input: action (Move x=right y=forward, Jump, Attack, Melee, Dash, Aim, Switch, Interact, Sprint, ...) for seconds", {"action": "str (required)", "x": "float", "y": "float", "z": "float", "seconds": "float"})
    bridge.register("daedalus.goto", goto, "Teleport the hero to x,y,z (snapped to the ground) and yaw, or behind an actor by label/name", {"x": "float", "y": "float", "z": "float", "yaw": "float", "snap": "bool", "actor": "str"})
    bridge.register("daedalus.look", look, "Point the camera: yaw and pitch", {"yaw": "float", "pitch": "float"})
    bridge.register("daedalus.state", state, "One line of the hero's state", {})
    bridge.register("daedalus.automation", automation, "Run the editor's automation tests matching filter and collect the results", {"filter": "str (default Daedalus)", "timeout": "float"})
