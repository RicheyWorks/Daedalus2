# SPDX-License-Identifier: MIT
"""Play-test harness for the Daedalus hero, foes and Ghost (ADR-045).

One bridge call starts a scenario; it runs frame by frame inside Play (a slate post-tick callback), so a held
trigger or a stick is held for real frames, not one; a second call reads the result: the record it gathered and
PASS/FAIL checks. Every scenario says what it proves, so a failure names the mechanic that broke.

    daedalus.play_scenario {"name": "foes_hunt"}   -> starts it (Play must be running)
    daedalus.play_status                           -> {"running": .., "frames": .., "result": {...}}
    daedalus.play_snapshot                         -> hero, foes, Ghosts, routes, fps right now
    daedalus.full_speed                            -> stop the editor throttling Play when it isn't in front

Scenarios: shoot, views_layouts, ghost, foes_hunt, shield. Add one by writing a generator below: it yields once
per frame and returns its checks.
"""

import math

import unreal

_run = {"name": None, "gen": None, "handle": None, "frames": 0, "result": None, "error": None}


# ---------------------------------------------------------------------------------------------------- the world

def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def _all(cls):
    w = world()
    return list(unreal.GameplayStatics.get_all_actors_of_class(w, cls)) if w else []


def hero():
    h = _all(unreal.DaedalusHero)
    return h[0] if h else None


def foes(alive=True):
    return [f for f in _all(unreal.DaedalusTarget) if not alive or f.get_editor_property("health") > 0]


def ghosts():
    return _all(unreal.DaedalusGhost)


def controller():
    return unreal.GameplayStatics.get_player_controller(world(), 0)


def dist(a, b):
    return (a.get_actor_location() - b.get_actor_location()).length()


def fps():
    w = world()
    return round(1.0 / max(unreal.GameplayStatics.get_world_delta_seconds(w), 1e-3)) if w else 0


def full_speed(p=None):
    """The editor drops Play to ~3 fps when another window is in front. The setting isn't exposed to Python, so:
    set it now with the console's `set` on the class default, and write it to the per-project editor ini so it
    holds from the next start too."""
    import os
    out = {}
    try:
        unreal.SystemLibrary.execute_console_command(None, "set EditorPerformanceSettings bThrottleCPUWhenNotForeground False")
        out["console"] = "sent"
    except Exception as e:
        out["console"] = repr(e)
    ini = os.path.join(unreal.Paths.project_saved_dir(), "Config", "WindowsEditor", "EditorPerProjectUserSettings.ini")
    section, key = "[/Script/UnrealEd.EditorPerformanceSettings]", "bThrottleCPUWhenNotForeground=False"
    try:
        text = open(ini, encoding="utf-8").read() if os.path.exists(ini) else ""
        if key not in text:
            if section in text:
                text = text.replace(section, section + "\n" + key, 1)
            else:
                text += "\n" + section + "\n" + key + "\n"
            os.makedirs(os.path.dirname(ini), exist_ok=True)
            open(ini, "w", encoding="utf-8").write(text)
        out["ini"] = ini
    except Exception as e:
        out["ini"] = repr(e)
    out["fps"] = fps()
    return out


def snapshot(p=None):
    h = hero()
    out = {"playing": world() is not None, "fps": fps()}
    if h:
        g = lambda k: h.get_editor_property(k)
        out["hero"] = {k: (round(g(k), 1) if isinstance(g(k), float) else g(k)) for k in
                       ("shield", "health", "deaths", "damage_taken", "kills", "exp", "shots_fired", "hits",
                        "current_weapon", "camera_view", "respawns")}
        out["hero"]["riding"] = bool(h.get_attach_parent_actor())
        out["nav"] = h.nav_stats()
    out["foes"] = [{"kind": f.get_editor_property("kind"), "state": f.get_editor_property("state"),
                    "health": round(f.get_editor_property("health")), "attacks": f.get_editor_property("attacks"),
                    "landed": f.get_editor_property("landed"), "routes": f.get_editor_property("routes"),
                    "to_hero": round(dist(f, h)) if h else None} for f in foes()]
    out["ghosts"] = [{"rider": bool(b.get_editor_property("rider")), "shots": b.get_editor_property("shots_fired"),
                      "hits": b.get_editor_property("hits")} for b in ghosts()]
    return out


# -------------------------------------------------------------------------------------------------- the runner

def _check(name, ok, detail=""):
    return {"check": name, "pass": bool(ok), "detail": detail}


def _tick(_dt):
    if _run["gen"] is None:
        return
    if world() is None:
        _finish(error="Play stopped")
        return
    _run["frames"] += 1
    try:
        next(_run["gen"])
    except StopIteration as done:
        _finish(result=done.value)
    except Exception as e:  # a broken scenario must not leave a callback running
        _finish(error=repr(e))


def _finish(result=None, error=None):
    if _run["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(_run["handle"])
    _run.update(handle=None, gen=None, error=error)
    if result is not None:
        checks = result.get("checks", [])
        result["passed"] = sum(1 for c in checks if c["pass"])
        result["total"] = len(checks)
    _run["result"] = result


def play_scenario(p):
    name = (p or {}).get("name", "")
    fn = SCENARIOS.get(name)
    if not fn:
        return {"error": "unknown scenario", "scenarios": sorted(SCENARIOS)}
    if world() is None or hero() is None:
        return {"error": "start Play first (the hero must be in the world)"}
    if _run["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(_run["handle"])
    full_speed()
    _run.update(name=name, gen=fn(p or {}), frames=0, result=None, error=None)
    _run["handle"] = unreal.register_slate_post_tick_callback(_tick)
    return {"started": name}


def play_status(p=None):
    return {"scenario": _run["name"], "running": _run["gen"] is not None, "frames": _run["frames"],
            "error": _run["error"], "result": _run["result"]}


def _frames(n):
    for _ in range(n):
        yield


def _clear_foes():
    for f in _all(unreal.DaedalusTarget):
        f.destroy_actor()


# --------------------------------------------------------------------------------------------------- scenarios

def scenario_shoot(p):
    """The blaster: spawn four foes, aim and fire each frame until they are down; kills and EXP add up."""
    h = hero()
    _clear_foes()
    if h.get_editor_property("current_weapon") != 1:
        h.switch_weapon()
    placed = h.spawn_foes(4)
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    kills0, exp0 = h.get_editor_property("kills"), h.get_editor_property("exp")
    want = sum(f.get_editor_property("exp_value") for f in foes())
    for _ in range(900):
        left = sorted(foes(), key=lambda f: dist(f, h))
        if not left:
            break
        h.aim_at(left[0].get_actor_location())
        h.fire()
        yield
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    kills = h.get_editor_property("kills") - kills0
    exp = h.get_editor_property("exp") - exp0
    return {"checks": [
        _check("four foes placed on the ground", placed == 4, f"placed={placed}"),
        _check("all foes down", not foes(), f"left={len(foes())}"),
        _check("kills counted", kills == placed, f"kills={kills}"),
        _check("EXP matches ADR-037", exp == want, f"exp={exp} want={want}"),
        _check("hits registered", h.get_editor_property("hits") > 0),
    ]}


def scenario_views_layouts(p):
    """Views cycle through all three; Bumper Jumper moves jump to LB; invert look survives."""
    h = hero()
    views = []
    for _ in range(3):
        h.cycle_view()
        views.append(h.get_editor_property("camera_view"))
        yield
    jump = lambda: [s for s in h.describe_bindings() if s.startswith("IA_Jump <- Gamepad")]
    before = jump()
    old = h.get_setting("ButtonLayout")
    h.set_setting("ButtonLayout", 1)
    yield
    after = jump()
    h.set_setting("ButtonLayout", old)
    return {"checks": [
        _check("three views visited", sorted(views) == [0, 1, 2], f"views={views}"),
        _check("default jump on A", any("FaceButton_Bottom" in s for s in before), str(before)),
        _check("Bumper Jumper jump on LB", any("LeftShoulder" in s for s in after), str(after)),
    ], "invert_look_y": h.get_setting("InvertLookY")}


def scenario_ghost(p):
    """The Ghost: call it, get on, drive, shoot foes from it (kills credit the rider), get off and walk."""
    h = hero()
    pc = controller()
    _clear_foes()
    for b in ghosts():
        b.destroy_actor()
    bike = h.spawn_vehicle()
    yield
    mounted = h.interact()
    on_bike = pc.get_controlled_pawn() == bike
    start = bike.get_actor_location()
    for i in range(45):
        bike.drive(0.7, 0.0, i > 20)
        yield
    bike.drive(0.0, 0.0, False)
    moved = (bike.get_actor_location() - start).length()
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    h.spawn_foes(3)
    kills0 = h.get_editor_property("kills")
    for _ in range(600):
        here = bike.get_actor_location()
        level = [f for f in foes() if abs(f.get_actor_location().z - here.z) < 300]
        if not level:
            break
        target = min(level, key=lambda f: (f.get_actor_location() - here).length())
        cam = bike.get_editor_property("camera").get_world_location()
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam, target.get_actor_location()))
        bike.fire_guns()
        yield
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    kills = h.get_editor_property("kills") - kills0
    bike.dismount()
    for _ in range(30):
        yield
    mode = str(h.get_editor_property("character_movement").movement_mode)
    return {"checks": [
        _check("mounted with Interact", mounted and on_bike),
        _check("drove", moved > 200, f"moved={round(moved)}cm"),
        _check("guns killed and credited the rider", kills > 0, f"kills={kills} shots={bike.get_editor_property('shots_fired')}"),
        _check("off the bike and walking", pc.get_controlled_pawn() == h and "WALKING" in mode, mode),
    ]}


def scenario_foes_hunt(p):
    """Foes hunt: ground foes find routes (the A* port) and close in; every kind attacks; the shield takes it."""
    h = hero()
    _clear_foes()
    h.set_editor_property("invulnerable", False)
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    placed = h.spawn_foes(4)
    start = {f.get_name(): dist(f, h) for f in foes()}
    taken0 = h.get_editor_property("damage_taken")
    frames = int(p.get("frames", 900))
    for _ in range(frames):
        if h.get_editor_property("health") < 40:   # don't let the test end in a fall
            h.set_editor_property("invulnerable", True)
        yield
    h.set_editor_property("invulnerable", False)
    out = {f.get_editor_property("kind"): f for f in foes()}
    closed = {k: round(start.get(f.get_name(), 0) - dist(f, h)) for k, f in out.items()}
    attacks = {k: f.get_editor_property("attacks") for k, f in out.items()}
    landed = {k: f.get_editor_property("landed") for k, f in out.items()}
    routes = {k: f.get_editor_property("routes") for k, f in out.items()}
    return {"checks": [
        _check("four foes placed", placed == 4, f"placed={placed}"),
        _check("ground foes found A* routes", routes.get("BLIGHT_SLIME", 0) > 0 and routes.get("STONE_KNIGHT", 0) > 0, str(routes)),
        _check("slime closed in", closed.get("BLIGHT_SLIME", 0) > 300, str(closed)),
        _check("every kind attacked", all(v > 0 for v in attacks.values()) and len(attacks) == 4, str(attacks)),
        _check("hits landed on the hero", sum(landed.values()) > 0, str(landed)),
        _check("damage taken", h.get_editor_property("damage_taken") > taken0),
    ], "nav": h.nav_stats(), "fps": fps()}


def scenario_shield(p):
    """Halo shield: damage takes the shield first, recharges after the delay, and a fall restores everything."""
    h = hero()
    _clear_foes()
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    h.set_editor_property("invulnerable", False)
    unreal.GameplayStatics.apply_damage(h, 30.0, None, None, None)
    s1, h1 = h.get_editor_property("shield"), h.get_editor_property("health")
    unreal.GameplayStatics.apply_damage(h, 90.0, None, None, None)
    s2, h2 = h.get_editor_property("shield"), h.get_editor_property("health")
    t = 0.0
    while t < 6.5:
        t += unreal.GameplayStatics.get_world_delta_seconds(world())
        yield
    s3, h3 = h.get_editor_property("shield"), h.get_editor_property("health")
    deaths0 = h.get_editor_property("deaths")
    unreal.GameplayStatics.apply_damage(h, 500.0, None, None, None)
    yield
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    return {"checks": [
        _check("first hit only on the shield", s1 == 70 and h1 == 100, f"shield={s1} health={h1}"),
        _check("overflow reaches health", s2 == 0 and h2 == 80, f"shield={s2} health={h2}"),
        _check("shield recharged after the delay", s3 > 50, f"shield={round(s3)} health={round(h3)}"),
        _check("a fall restores him", h.get_editor_property("deaths") == deaths0 + 1 and h.get_editor_property("health") == 100),
    ]}


SCENARIOS = {
    "shoot": scenario_shoot,
    "views_layouts": scenario_views_layouts,
    "ghost": scenario_ghost,
    "foes_hunt": scenario_foes_hunt,
    "shield": scenario_shield,
}


def register(bridge):
    bridge.register("daedalus.play_scenario", play_scenario,
                    "Start a play-test scenario inside Play (it runs frame by frame); read it with daedalus.play_status. "
                    "Scenarios: " + ", ".join(sorted(SCENARIOS)), {"name": "str", "frames": "int (foes_hunt)"})
    bridge.register("daedalus.play_status", play_status, "The running or finished scenario: frames, checks, record", {})
    bridge.register("daedalus.play_snapshot", snapshot, "Hero, foes, Ghosts, foe routes and fps right now", {})
    bridge.register("daedalus.full_speed", full_speed, "Stop the editor slowing Play when it is not the window in front", {})
