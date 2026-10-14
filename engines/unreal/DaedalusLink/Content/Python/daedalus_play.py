# SPDX-License-Identifier: MIT
"""Play-test harness for the Daedalus hero, foes and Ghost (ADR-045).

One bridge call starts a scenario; it runs frame by frame inside Play (a slate post-tick callback), so a held
trigger or a stick is held for real frames, not one; a second call reads the result: the record it gathered and
PASS/FAIL checks. Every scenario says what it proves, so a failure names the mechanic that broke.

    daedalus.play_scenario {"name": "foes_hunt"}   -> starts it (Play must be running)
    daedalus.play_status                           -> {"running": .., "frames": .., "result": {...}}
    daedalus.play_snapshot                         -> hero, foes, Ghosts, routes, fps right now
    daedalus.full_speed                            -> stop the editor throttling Play when it isn't in front

Scenarios: shoot, views_layouts, ghost, foes_hunt, shield, encounters, armor. Add one by writing a generator below: it yields once
per frame and returns its checks.
"""

import math
import os

import unreal

_run = {"name": None, "gen": None, "handle": None, "frames": 0, "result": None, "error": None, "human": 0}


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


def play_capture(p=None):
    """A PNG of what the player sees in Play (the editor's screenshot and capture_view use the editor camera, and the
    viewport screenshot times out during Play). A SceneCapture2D is placed at the player camera, rendered to a target,
    exported, and removed. Returns the file's path (read it with any file tool)."""
    import os, tempfile, time as _t
    p = p or {}
    w = world()
    if w is None:
        raise RuntimeError("start Play first")
    width, height = int(p.get("width", 1280)), int(p.get("height", 720))
    cam = unreal.GameplayStatics.get_player_camera_manager(w, 0)
    loc, rot = cam.get_camera_location(), cam.get_camera_rotation()
    rt = unreal.RenderingLibrary.create_render_target2d(w, width, height)
    # Python can't spawn actors into the Play world, but it can add a component to one: borrow the player's pawn.
    host = unreal.GameplayStatics.get_player_pawn(w, 0)
    comp = host.add_component_by_class(unreal.SceneCaptureComponent2D, False, unreal.Transform(), False)
    try:
        comp.set_world_location_and_rotation(loc, rot, False, False)
        comp.set_editor_property("texture_target", rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property("fov_angle", cam.get_fov_angle())
        comp.capture_scene()
        yield
        out_dir = p.get("dir") or os.path.join(tempfile.gettempdir(), "daedalus-captures")
        os.makedirs(out_dir, exist_ok=True)
        name = p.get("name") or "play_%d" % int(_t.time() * 1000)
        unreal.RenderingLibrary.export_render_target(w, rt, out_dir, name)
        path = os.path.join(out_dir, name + ".png")
        deadline = _t.time() + 20
        while not (os.path.exists(path) and os.path.getsize(path) > 0):
            if _t.time() > deadline:
                raise TimeoutError("the capture was not written")
            yield
        return {"path": path, "bytes": os.path.getsize(path), "camera": [round(loc.x), round(loc.y), round(loc.z)]}
    finally:
        comp.destroy_component(comp)


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


HUMAN_KEYS = ("LeftMouseButton", "RightMouseButton", "W", "A", "S", "D", "SpaceBar", "E", "Escape", "Tab", "I", "LeftShift",
              "Gamepad_LeftX", "Gamepad_LeftY", "Gamepad_FaceButton_Bottom")


def _human_input():
    """True when a person is driving the Play window right now (23:37: Richey's mouse locked into the viewport
    mid-run and the hero walked off the script). Checked every frame while a scenario runs."""
    try:
        pc = unreal.GameplayStatics.get_player_controller(world(), 0)
        if not pc:
            return False
        for k in HUMAN_KEYS:
            if pc.is_input_key_down(unreal.Key(k)):
                return True
    except Exception:
        return False
    return False


def _tick(_dt):
    if _run["gen"] is None:
        return
    if world() is None:
        _finish(error="Play stopped")
        return
    _run["frames"] += 1
    if _run["frames"] % 5 == 0 and _human_input():
        _run["human"] += 1
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
        result["human_input_frames"] = _run["human"]
        if _run["human"]:   # a person touched the controls: the numbers are not the scenario's
            result["interrupted"] = "human input on %d sampled frames; rerun with the Play window unfocused" % _run["human"]
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
    _run.update(name=name, gen=fn(p or {}), frames=0, result=None, error=None, human=0)
    _run["handle"] = unreal.register_slate_post_tick_callback(_tick)
    return {"started": name}


def play_status(p=None):
    return {"scenario": _run["name"], "running": _run["gen"] is not None, "frames": _run["frames"],
            "error": _run["error"], "result": _run["result"]}


def _frames(n):
    for _ in range(n):
        yield


def _seconds(s, max_frames=20000):
    """Wait s seconds of GAME time (not frames). Under -d3d11 Play ran far faster than the 60 fps the frame counts
    assumed, so 90 frames was well under a second and foes 'did not move' (2026-10-13 compile turn)."""
    w = world()
    t0 = unreal.GameplayStatics.get_time_seconds(w) if w else 0.0
    for _ in range(max_frames):
        yield
        w = world()
        if not w or unreal.GameplayStatics.get_time_seconds(w) - t0 >= s:
            return


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
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    h.spawn_foes(3)                       # on foot, so they stand on the hero's level
    bike = h.spawn_vehicle()
    yield
    mounted = h.interact()
    on_bike = pc.get_controlled_pawn() == bike
    start = bike.get_actor_location()
    for i in range(20):
        bike.drive(0.5, 0.0, False)
        yield
    bike.drive(0.0, 0.0, False)
    moved = (bike.get_actor_location() - start).length()
    kills0 = h.get_editor_property("kills")
    for _ in range(900):
        if not foes():
            break
        here = bike.get_actor_location()
        target = min(foes(), key=lambda f: (f.get_actor_location() - here).length())
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


def scenario_encounters(p):
    """Encounters (ADR-046): packs land on flat ground 25-60 m out, on the ground, and the director keeps adding them."""
    h = hero()
    _clear_foes()
    h.set_editor_property("invulnerable", True)
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.Encounters 1")
    made = [h.spawn_pack() for _ in range(3)]
    yield
    placed = foes()
    dists = [round(dist(f, h)) for f in placed]
    grounded = 0
    for f in placed:
        loc = f.get_actor_location()
        hit = unreal.SystemLibrary.line_trace_single_for_objects(world(), loc, loc - unreal.Vector(0, 0, 600),
            [unreal.ObjectTypeQuery.ECC_WORLD_STATIC], False, [f], unreal.DrawDebugTrace.NONE, True)
        t = hit.to_tuple() if hit else None
        if t and t[0] and loc.z - t[5].z < 400:
            grounded += 1
    before = len(foes())
    t = 0.0
    while t < 12.0:
        t += unreal.GameplayStatics.get_world_delta_seconds(world())
        yield
    after = len(foes())
    stats = h.encounter_stats()
    _clear_foes()
    h.set_editor_property("invulnerable", False)
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    return {"checks": [
        _check("three packs placed", all(n >= 2 for n in made), f"sizes={made}"),
        _check("packs 10-80 m away", len(dists) > 0 and all(1000 <= d <= 8000 for d in dists), f"dists={dists}"),
        _check("every foe on the ground", len(placed) > 0 and grounded == len(placed), f"{grounded}/{len(placed)}"),
        _check("director adds packs on its own", after > before, f"before={before} after={after}"),
    ], "stats": stats}


def scenario_armor(p):
    """Armor (ADR-047): three cores raise a tier, a knight drops a core you can walk over, overshield goes past full and fades."""
    import json, os
    h = hero()
    _clear_foes()
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    h.set_armor_tier(0)
    base = h.get_editor_property("max_shield")
    for _ in range(3):
        h.add_shield_core()
    tier1 = h.get_editor_property("armor_tier")
    max1 = h.get_editor_property("max_shield")
    yield
    # A knight's core, picked up by walking onto it.
    h.spawn_foes(4)
    knight = [f for f in foes() if f.get_editor_property("kind") == "STONE_KNIGHT"]
    cores0 = h.get_editor_property("shield_cores")
    if knight:
        unreal.GameplayStatics.apply_damage(knight[0], 9999.0, None, h, None)
    for _ in range(10):
        yield
    picks = _all(unreal.DaedalusPickup)
    dropped = len(picks)
    if picks:
        loc = picks[0].get_actor_location()
        h.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + 40), False, True)
    for _ in range(10):
        yield
    cores1 = h.get_editor_property("shield_cores")
    # Overshield.
    h.give_overshield(100.0)
    over = h.get_editor_property("shield")
    t = 0.0
    while t < 3.0:
        t += unreal.GameplayStatics.get_world_delta_seconds(world())
        yield
    faded = h.get_editor_property("shield")
    saved = os.path.join(unreal.Paths.project_saved_dir(), "Config", "DaedalusHero.json")
    on_disk = json.load(open(saved)) if os.path.exists(saved) else {}
    _clear_foes()
    h.set_armor_tier(0)
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    return {"checks": [
        _check("three cores raise a tier", tier1 == 1 and max1 == base + 40, f"tier={tier1} max={max1} base={base}"),
        _check("a knight drops a core", dropped >= 1, f"pickups={dropped}"),
        _check("walking onto it collects it", cores1 == cores0 + 1, f"cores {cores0}->{cores1}"),
        _check("overshield goes past full", over > max1, f"shield={round(over)} max={max1}"),
        _check("overshield fades", max1 <= faded < over, f"{round(over)}->{round(faded)}"),
        _check("progress saved to disk", on_disk.get("armor_tier") == 1, str(on_disk)),
    ]}


def _live():
    w = _all(unreal.DaedalusWorldActor)
    return max(w, key=lambda a: a.chunk_count()) if w else None


def scenario_dig(p):
    """Dig and build (ADR-049): the pick mines the cube under the reticle into the bag, places it back, the world
    changes, and the server takes the edits."""
    h = hero()
    live = _live()
    if live is None or live.chunk_count() == 0:
        return {"checks": [_check("a live World actor with chunks", False, "none in this level")]}
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    while h.get_editor_property("current_weapon") != 2:
        h.switch_weapon()
    # Look at the ground a couple of metres ahead.
    loc = h.get_actor_location()
    fwd = h.get_actor_forward_vector()
    h.aim_at(unreal.Vector(loc.x + fwd.x * 200, loc.y + fwd.y * 200, loc.z - 110))
    for _ in range(5):
        yield
    target = h.get_editor_property("target_type")
    t = h.get_editor_property("target_cube")
    cube = unreal.IntVector(t.x, t.y, t.z)   # a copy: get_editor_property hands back a live view of the struct
    mined0 = h.get_editor_property("cubes_mined")
    sent0 = live.get_editor_property("edits_sent")
    hardness = unreal.DaedalusHero.hardness(target) if target else 0
    ok_mine = h.mine_target()
    yield
    after = live.cube_at(live.cube_center(cube))
    bag = dict(h.get_editor_property("bag"))
    for _ in range(5):
        yield
    # Put it back: aim at the hole's far wall. From eye height the ray to the hole's floor hits the near rim
    # first (it put the cube on the rim); the far wall's face points back at us, so its neighbour is the hole.
    c = live.cube_center(cube)
    me = h.get_actor_location()
    away = unreal.Vector(c.x - me.x, c.y - me.y, 0)
    n = max((away.x ** 2 + away.y ** 2) ** 0.5, 1.0)
    h.aim_at(unreal.Vector(c.x + away.x / n * 49, c.y + away.y / n * 49, c.z))
    for _ in range(5):
        yield
    placed = h.place_cube() if h.get_editor_property("selected_cube") else False
    yield
    back = live.cube_at(live.cube_center(cube))
    t = 0.0
    while t < 2.0:
        t += unreal.GameplayStatics.get_world_delta_seconds(world())
        yield
    sent = live.get_editor_property("edits_sent") - sent0
    accepted = live.get_editor_property("edits_accepted")
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    return {"checks": [
        _check("a cube under the reticle", bool(target) and target != "AIR", f"target={target} hardness={hardness}"),
        _check("mined it", ok_mine and h.get_editor_property("cubes_mined") == mined0 + 1, f"now={after}"),
        _check("the world lost it", after == "AIR", f"cube={cube} is {after}"),
        _check("it went in the bag", bag.get(target, 0) >= 1, str(bag)),
        _check("placed one back", placed and back == target, f"placed={h.get_editor_property('cubes_placed')} hole now {back}"),
        _check("edits sent to the server", sent >= 2, f"sent={sent} accepted_total={accepted}"),
    ], "server_accepted_total": accepted}


def scenario_fall(p):
    """Falls hurt past about five cubes; a short drop doesn't."""
    h = hero()
    _clear_foes()
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    for _ in range(30):
        yield
    start = h.get_actor_location()
    results = []
    for height in (250, 1500):
        taken0 = h.get_editor_property("fall_damage_taken")
        h.set_actor_location(unreal.Vector(start.x, start.y, start.z + height), False, True)
        t = 0.0
        while t < 3.0:
            t += unreal.GameplayStatics.get_world_delta_seconds(world())
            yield
        results.append((height, round(h.get_editor_property("fall_damage_taken") - taken0, 1),
                        round(h.get_editor_property("last_landing_speed"))))
        h.set_armor_tier(h.get_editor_property("armor_tier"))   # refills the shield (Shield is read-only to Python)
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    return {"checks": [
        _check("a 2.5 m drop is free", results[0][1] == 0, str(results[0])),
        _check("a 15 m fall hurts", results[1][1] > 0, str(results[1])),
    ]}


def scenario_dress(p):
    """The world dresser (ADR-054): once the live cubes are in, the shipped art library grows on them and a town
    stands near the start. Checks counts, then puts the camera over the town for a look."""
    dresser = None
    for _ in range(900):   # the live world streams in, then the dresser waits for it to settle
        ds = _all(unreal.DaedalusDresser)
        dresser = ds[0] if ds else None
        if dresser and dresser.stats().startswith("placed="):
            break
        yield
    stats = dresser.stats() if dresser else "no dresser"
    kv = dict(t.split("=", 1) for t in stats.split() if "=" in t)
    n = lambda k: int(kv.get(k, "0").split(",")[0])
    return {"checks": [
        _check("a dresser is in the world", dresser is not None),
        _check("it dressed the live world", n("placed") >= 300, stats),
        _check("trees grow, spaced", n("trees") >= 20, stats),
        _check("plants of many kinds", n("meshes") >= 20, stats),
        _check("a town stands near the start", n("town") >= 10, stats),
    ], "stats": stats, "town": str(dresser.town_center()) if dresser else None}


def scenario_wild(p):
    """Creatures (ADR-055): the dresser's herds are the Blender team's animals, assembled from their parts; they
    wander without walking off ledges and the shy ones bolt from the hero. Foes wear their Mob_ art too, keeping their
    (hidden) collision so the blaster still hits them."""
    critters = []
    for _ in range(900):
        critters = _all(unreal.DaedalusCritter)
        if len(critters) >= 5:
            break
        yield
    species = sorted({c.get_editor_property("species") for c in critters})
    built = [c for c in critters if c.get_editor_property("parts") > 0]
    for _ in _seconds(8.0):   # grazing, the 1.5 s and 4 s re-grounding, then wandering (critters graze up to 4 s first)
        yield
    walked = [c for c in critters if c.get_editor_property("walked") > 1.0]
    h = hero()
    shy = [c for c in critters if c.is_shy()]
    fled = False
    if h and shy:
        target = shy[0]
        at = target.get_actor_location()
        h.set_actor_location(unreal.Vector(at.x - 250.0, at.y, at.z + 120.0), False, True)
        for _ in _seconds(1.5):
            yield
        fled = target.get_editor_property("flees") > 0
    _clear_foes()
    if h:
        h.spawn_foes(4)
    for _ in _frames(10):
        yield
    fs = foes()
    dressed = [f for f in fs if f.get_editor_property("art_parts") > 0]
    kinds = sorted({f.get_editor_property("kind") for f in dressed})
    return {"checks": [
        _check("herds are out", len(critters) >= 10, "%d critters" % len(critters)),
        _check("of several species", len(species) >= 3, ", ".join(species)),
        _check("every animal is built from shipped parts", len(critters) > 0 and len(built) == len(critters),
               "%d/%d" % (len(built), len(critters))),
        _check("they wander", len(walked) >= max(1, len(critters) // 4), "%d walked" % len(walked)),
        _check("a shy one bolts from the hero", fled, shy[0].get_editor_property("species") if shy else "none shy"),
        _check("foes wear their Mob_ art", len(fs) > 0 and len(dressed) == len(fs), "%d/%d %s" % (len(dressed), len(fs), kinds)),
    ], "species": species}


def scenario_orrery(p):
    """The Orrery Reach (ADR-057): the hero plays the Keeper's Logbook. Talk to the Keeper, fix the filter, pick up the
    Lantern chart, wait for a starbloom's hour and harvest it, steep a tea, then harvest the Lantern pair and steep
    the Lantern Brew. Each step is checked on the logbook."""
    h = hero()
    o = unreal.DaedalusOrrery.get_orrery(world()) if hasattr(unreal, "DaedalusOrrery") else None
    if h is None or o is None:
        return {"error": "start Play with the Orrery build"}
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 0")
    sky = _all(unreal.DaedalusSkyDirector) if hasattr(unreal, "DaedalusSkyDirector") else []
    log = []

    def go(label):
        acts = [a for a in _all(unreal.DaedalusUsable) if a.get_actor_label() == label]
        if not acts:
            return False
        at = acts[0].get_actor_location()
        h.set_actor_location(unreal.Vector(at.x - 150.0, at.y, at.z + 100.0), False, True)
        return True

    def use(label):
        ok = go(label)
        yield
        yield
        r = h.interact() if ok else False
        log.append((label, ok, o.state()))
        yield

    def hour_of(name):
        return {x.split(":")[0]: int(x.split(":")[1]) for x in p.get("hours", "").split(",") if ":" in x}.get(name)

    def set_hour(hh):
        if sky:
            sky[0].set_time_of_day(hh + 0.1)
        else:
            t = unreal.GameplayStatics.get_time_seconds(world())
            o.set_editor_property("start_hour", (hh + 0.1 - t / o.get_editor_property("seconds_per_hour")) % 24.0)

    yield from use("Orr_Keeper_Ostra")
    s1 = o.get_editor_property("step")
    yield from use("Orr_Play_Filter")
    clean = o.get_editor_property("clean_water")
    yield from use("Orr_Chart_Lantern")
    s3 = o.get_editor_property("step")
    set_hour(18)                       # Duskmallow's hour
    for _ in range(4):
        yield
    yield from use("Orr_Bloom_Duskmallow")
    s4 = o.get_editor_property("step")
    yield from use("Orr_Play_Kettle")
    s5 = o.get_editor_property("step")
    # the Lantern pair: Duskmallow regrows tomorrow, so pick Sunsprig at 8:00 and a fresh Duskmallow the next dusk
    set_hour(8)
    for _ in range(4):
        yield
    yield from use("Orr_Bloom_Sunsprig")
    set_hour(18)                       # a new dusk: Duskmallow has regrown since its hour passed
    for _ in range(4):
        yield
    yield from use("Orr_Bloom_Duskmallow")
    satchel = list(o.get_editor_property("satchel"))
    yield from use("Orr_Play_Kettle")
    brews = list(o.get_editor_property("brews"))
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    return {"checks": [
        _check("the Keeper starts the logbook", s1 == 1, log[0] if log else ""),
        _check("the filter makes the water drinkable", clean and o.get_editor_property("step") >= 2, o.state()),
        _check("the Lantern chart is found", s3 == 3, o.state()),
        _check("a starbloom is harvested in its hour", s4 == 4, o.state()),
        _check("the first tea is steeped", s5 == 5 and any(b.endswith("Tea") for b in brews), brews),
        _check("the Lantern pair makes the Lantern Brew", "Lantern Brew" in brews, "%s / satchel %s" % (brews, satchel)),
    ], "log": [str(x) for x in log], "state": o.state()}


def _kv(line):
    """A realm state line ('mode=FIELD map=TOWN1 x=3 ...') as a dict; msg= is the rest of the line."""
    out = {}
    head, _, msg = line.partition(" msg=")
    for tok in head.split():
        k, _, v = tok.partition("=")
        out[k] = v
    out["msg"] = msg
    return out


def realm(p=None):
    """Drive the 8-bit realm from the bridge: {cmd} is any RealmInput command; returns its state."""
    h = hero()
    if h is None:
        return {"error": "start Play first"}
    cmd = (p or {}).get("cmd", "")
    if cmd == "enter":
        h.enter_realm(int((p or {}).get("seed", 7)))
        return {"state": h.realm_state()}
    if cmd == "exit":
        h.exit_realm()
        return {"state": h.realm_state()}
    state = h.realm_input(cmd) if cmd else h.realm_state()
    return {"state": state, "fields": _kv(state) if "map=" in state else {}}


def realm_capture(p=None):
    h = hero()
    out_dir = os.path.join(unreal.Paths.project_saved_dir(), "Realm")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, (p or {}).get("name", "realm.png"))
    return {"ok": bool(h and h.realm_capture(path)), "path": path}


def scenario_realm(p):
    """The 8-bit realm (ADR-052): through a portal the world turns 8-bit; the Java engines' realm loads (from the
    server, or the shipped one), the party walks while a direction is held, a fight is won, the status menu opens,
    the screen is captured from the framebuffer, and the portal sends the party home with its progress saved."""
    h = hero()
    seed = int(p.get("seed", 7))
    if h.is_realm_open():
        h.exit_realm()
        yield from _frames(5)
    h.enter_realm(seed)
    st = ""
    for _ in range(400):
        st = h.realm_state()
        if "map=" in st or "refused" in st:
            break
        yield
    out_dir = os.path.join(unreal.Paths.project_saved_dir(), "Realm")
    os.makedirs(out_dir, exist_ok=True)
    shots = []

    def cap(name):
        path = os.path.join(out_dir, name)
        if h.realm_capture(path):
            shots.append(path)

    first = _kv(st) if "map=" in st else {}
    cap("realm_arrival.png")
    for _ in range(8):   # close the welcome (a restored save has none: a blind A would open the menu instead)
        if _kv(h.realm_state()).get("ui") == "NONE":
            break
        h.realm_input("b")
    h.realm_input("toughen")
    steps0 = int(_kv(h.realm_state()).get("steps", 0))
    walked = 0
    for way in ("right", "left", "down", "up"):   # the first way that isn't water or a wall
        h.realm_input("hold:" + way)
        yield from _frames(30)
        h.realm_input("release:" + way)
        yield from _frames(5)
        walked = int(_kv(h.realm_state()).get("steps", 0)) - steps0
        if walked >= 3:
            break
    while _kv(h.realm_state()).get("mode") == "BATTLE":   # walking can meet monsters
        h.realm_input("autofight")
        h.realm_input("a")
        yield
    h.realm_input("a")
    wins0 = int(_kv(h.realm_state()).get("wins", 0))
    h.realm_input("battle:BLIGHT_SLIME+PUFFCAP")
    yield from _frames(5)
    in_battle = _kv(h.realm_state()).get("mode") == "BATTLE"
    cap("realm_battle.png")
    h.realm_input("autofight")
    won = int(_kv(h.realm_state()).get("wins", 0)) == wins0 + 1
    for _ in range(8):   # close whatever is up (a drop's message, say) before opening the menu
        if _kv(h.realm_state()).get("ui") == "NONE":
            break
        h.realm_input("b")
    for c in ("b", "down", "a"):   # COMMAND is a 2x3 grid: TALK SPELL / STATUS ITEM / SEARCH EQUIP
        h.realm_input(c)
    status = _kv(h.realm_state()).get("ui") == "STATUS"
    cap("realm_status.png")
    h.realm_input("a")
    h.realm_input("b")
    h.realm_input("portal")
    h.realm_input("up")
    said = _kv(h.realm_state()).get("msg", "")
    for _ in range(60):   # A finishes the typewriter, A again turns the page or closes
        if not h.is_realm_open():
            break
        if _kv(h.realm_state()).get("ui") == "MESSAGE":
            h.realm_input("a")
        yield
    save_path = os.path.join(unreal.Paths.project_saved_dir(), "Config", "DaedalusRealm.sav")
    saved = os.path.exists(save_path) and open(save_path).read().startswith("DRS 1")
    return {"checks": [
        _check("the realm loaded", first.get("map") == "FIELD", st[:160]),
        _check("from the server or the shipped spec", "source=server" in st or "source=shipped" in st, st[:40]),
        _check("holding a direction walks", walked >= 3, f"steps={walked}"),
        _check("a forced fight starts", in_battle),
        _check("and is won", won),
        _check("the status menu opens", status),
        _check("the framebuffer captures", len(shots) == 3, str(shots)),
        _check("the portal says goodbye", "PORTAL" in said, said),
        _check("and closes the realm", not h.is_realm_open()),
        _check("the party is saved", saved, save_path),
    ], "shots": shots}


def scenario_tactics(p):
    """Squad tactics (ADR-060): three foes as one squad. The local director makes one attack and two flank; a Java
    (outside) RETREAT spec takes over and holds; a bad spec changes nothing; hits come back as DTE 1 events."""
    h = hero()
    _clear_foes()
    h.set_editor_property("invulnerable", True)
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.FoesHunt 1")
    unreal.SystemLibrary.execute_console_command(world(), "daedalus.Tactics 0")   # the scenario drives the ticks
    placed = h.spawn_foes(3)
    squad = foes()
    for i, f in enumerate(sorted(squad, key=lambda f: f.get_name())):
        f.set_editor_property("squad", "test-squad")
        f.set_editor_property("unit_id", "t%d" % (i + 1))
    tac = unreal.DaedalusTactics.get_tactics(world())
    spec = tac.decide_now("test-squad")
    verbs = sorted(l.split()[2] for l in spec.splitlines() if l.startswith("order "))
    orders0 = {f.get_editor_property("unit_id"): f.get_editor_property("order_verb") for f in foes()}
    flankers = [f for f in foes() if f.get_editor_property("order_verb") == "FLANK"]
    before = {f.get_name(): (f.get_actor_location() - f.get_editor_property("order_point")).length() for f in flankers}
    states = set()
    for _ in _seconds(1.5):
        states.update(f.get_editor_property("state") for f in foes())
        yield
    after = {f.get_name(): (f.get_actor_location() - f.get_editor_property("order_point")).length() for f in flankers}
    closed = [round(before[k] - after.get(k, before[k])) for k in before]

    # Java takes over: t1 retreats 1500 cm straight away from the hero
    t1 = [f for f in foes() if f.get_editor_property("unit_id") == "t1"]
    out, held, moved = "", False, 0
    if t1:
        a, hl = t1[0].get_actor_location(), h.get_actor_location()
        d = unreal.Vector(a.x - hl.x, a.y - hl.y, 0.0)
        n = max(d.length(), 1.0)
        goal = unreal.Vector(a.x + d.x / n * 1500, a.y + d.y / n * 1500, a.z)
        d0 = dist(t1[0], h)
        out = tac.apply_orders("DTO 1\nsquad test-squad tick 99\norder t1 RETREAT - %.1f %.1f %.1f | scenario: Java says fall back\n"
                               % (goal.x, goal.y, goal.z))
        unreal.SystemLibrary.execute_console_command(world(), "daedalus.Tactics 1")   # the local director may run, but Java holds it
        for _ in _seconds(1.0):
            yield
        held = t1[0].get_editor_property("order_verb") == "RETREAT" if foes() else False
        moved = round(dist(t1[0], h) - d0) if foes() else 0
    bad = tac.apply_orders("DTO 1\nsquad test-squad tick 1\norder t2 JUMP - 0 0 0\n")
    # a hit comes back as an event
    tac.take_events()
    target = sorted(foes(), key=lambda f: dist(f, h))
    if target:
        if h.get_editor_property("current_weapon") != 1:
            h.switch_weapon()
        for _ in _seconds(0.5):
            h.aim_at(target[0].get_actor_location())
            h.fire()
            yield
    events = tac.take_events()
    roster = tac.take_roster("test-squad")
    h.set_editor_property("invulnerable", False)
    return {"checks": [
        _check("three foes placed as one squad", placed == 3 and len(squad) == 3, f"placed={placed}"),
        _check("the director: one attacks, two flank", verbs == ["ATTACK", "FLANK", "FLANK"], str(verbs)),
        _check("the foes took those orders", sorted(v for v in orders0.values() if v) == ["ATTACK", "FLANK", "FLANK"], str(orders0)),
        _check("the flankers move to their flank points", len(closed) == 2 and all(c > 50 for c in closed), str(closed)),
        _check("a Java spec applies", out.startswith("applied=1"), out),
        _check("Java's order holds against the local director", held, f"held={held}"),
        _check("the retreating foe got further away", moved > 150, f"moved={moved}"),
        _check("a bad spec is refused whole", bad.startswith("refused: line 3"), bad),
        _check("the roster is DTR 1 with this world's session", roster.startswith("DTR 1\nsession " + tac.session_id() + " squad test-squad"),
               roster[:160]),
        _check("a fallen foe stays on the roster at health 0", ("event DOWN" not in events) or (" 0.0 " in roster), roster[:300]),
        _check("a repeated Java tick is ignored, an older one refused",
               tac.apply_orders("DTO 1\nsquad test-squad tick 99\n").startswith("repeat")
               and tac.apply_orders("DTO 1\nsquad test-squad tick 98\n").startswith("refused: stale")),
        _check("hits come back as DTE 1 events", events.startswith("DTE 1") and ("event HIT" in events or "event DOWN" in events), events[:200]),
    ], "states": sorted(states), "stats": tac.stats(), "spec": spec}


def scenario_tactics_remote(p):
    """The Java director over HTTP (ADR-060 transport): with the local director off and daedalus.TacticsRemote 1, a
    squad's orders come from POST /api/v1/tactics/decide on daedalus.Server, applied without blocking a frame.
    Needs the Daedalus server running; when it is not, the first check says so."""
    import urllib.request
    h = hero()
    _clear_foes()
    h.set_editor_property("invulnerable", True)
    w = world()
    server = unreal.SystemLibrary.get_console_variable_string_value("daedalus.Server") or "http://localhost:8088"
    try:
        up = urllib.request.urlopen(server + "/api/v1/worlds", timeout=2).status == 200
    except Exception as e:  # reported as the first check
        up, server = False, "%s (%s)" % (server, e)
    unreal.SystemLibrary.execute_console_command(w, "daedalus.FoesHunt 1")
    unreal.SystemLibrary.execute_console_command(w, "daedalus.Tactics 0")
    unreal.SystemLibrary.execute_console_command(w, "daedalus.TacticsRemote 1")
    placed = h.spawn_foes(3)
    for i, f in enumerate(sorted(foes(), key=lambda f: f.get_name())):
        f.set_editor_property("squad", "remote-squad")
        f.set_editor_property("unit_id", "r%d" % (i + 1))
    tac = unreal.DaedalusTactics.get_tactics(w)
    frames = 0
    for _ in _seconds(5.0):   # four or five round trips at one a second
        frames += 1
        yield
    stats = tac.stats()
    kv = dict(x.split("=", 1) for x in stats.split() if "=" in x)
    answered, asked = (int(v) for v in kv.get("remote", "0/0").split("/"))
    verbs = sorted(f.get_editor_property("order_verb") for f in foes() if f.get_editor_property("order_verb"))
    unreal.SystemLibrary.execute_console_command(w, "daedalus.TacticsRemote 0")
    unreal.SystemLibrary.execute_console_command(w, "daedalus.Tactics 1")
    h.set_editor_property("invulnerable", False)
    return {"checks": [
        _check("the Daedalus server answers", up, server),
        _check("three foes placed as one squad", placed == 3, f"placed={placed}"),
        _check("the squad was asked about once a second", asked >= 3, stats),
        _check("Java answered", answered >= 2, stats),
        _check("Java's orders were applied (local director off)", int(kv.get("applied", "0")) >= 1 and len(verbs) == 3, str(verbs)),
        _check("nothing failed", kv.get("failed", "0") == "0", stats),
    ], "stats": stats, "frames": frames}


def scenario_shiny(p):
    """Shiny (ADR-065 rule 9): a shiny critter and a shiny foe stand next to the hero. Both must carry the glow (a
    point light) and the orbiting sparks, be taller than their plain twins, the foe must have more health, and the
    sparks must actually move. Spawned in the Play world only; nothing is saved."""
    h = hero()
    w = world()
    at = h.get_actor_location()
    fwd = h.get_actor_forward_vector()
    # Python can only spawn into the editor world; UDaedalusFilm.spawn_in_play puts actors into the Play world.
    # BeginPlay runs at spawn, so shiny is set right after and Rebuild applies it.
    spawn = unreal.DaedalusFilm.spawn_in_play
    plain = spawn(h, unreal.DaedalusCritter, at + fwd * 300 + unreal.Vector(0, -150, 100), unreal.Rotator(0, 0, 0))
    shiny = spawn(h, unreal.DaedalusCritter, at + fwd * 300 + unreal.Vector(0, 150, 100), unreal.Rotator(0, 0, 0))
    for c in (plain, shiny):
        c.set_editor_property("species", "Mob_Sheep")
    shiny.set_editor_property("shiny", True)
    plain.rebuild()
    shiny.rebuild()
    foe_plain = spawn(h, unreal.DaedalusTarget, at + fwd * 600 + unreal.Vector(0, -200, 100), unreal.Rotator(0, 0, 0))
    foe_shiny = spawn(h, unreal.DaedalusTarget, at + fwd * 600 + unreal.Vector(0, 200, 100), unreal.Rotator(0, 0, 0))
    foe_shiny.make_shiny()
    for f in (foe_plain, foe_shiny):
        f.set_editor_property("hunts", False)
    yield from _frames(3)

    def sparks(a):
        return [c for c in a.get_components_by_class(unreal.StaticMeshComponent) if "ShinySpark" in c.get_name()]

    def lights(a):
        return a.get_components_by_class(unreal.PointLightComponent)

    def where(a):   # plain tuples: a Vector from get_editor_property can be a live view of the component's value
        return [(v.x, v.y, v.z) for v in (c.get_editor_property("relative_location") for c in sparks(a))]

    s0 = where(shiny)
    t0 = unreal.GameplayStatics.get_time_seconds(w)
    for _ in range(600):   # until a second of game time has passed (Play may run fast or slow)
        if unreal.GameplayStatics.get_time_seconds(w) - t0 >= 1.0:
            break
        yield
    t1 = unreal.GameplayStatics.get_time_seconds(w)
    s1 = where(shiny)
    dists = [math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b))) for a, b in zip(s0, s1)]
    moved = bool(dists) and min(dists) > 5
    cap = os.path.join(unreal.Paths.project_saved_dir(), "Daedalus", "shiny.png")
    return {"checks": [
        _check("the shiny critter glows", len(lights(shiny)) == 1 and len(lights(plain)) == 0),
        _check("and wears orbiting sparks", len(sparks(shiny)) == 7 and len(sparks(plain)) == 0),
        _check("the sparks move", moved, "dt=%.2fs min=%.1fcm" % (t1 - t0, min(dists) if dists else -1)),
        _check("it stands taller", shiny.get_actor_scale3d().z > plain.get_actor_scale3d().z * 1.1),
        _check("the shiny foe glows too", len(lights(foe_shiny)) == 1 and len(lights(foe_plain)) == 0),
        _check("with more health", foe_shiny.get_editor_property("max_health") > foe_plain.get_editor_property("max_health") * 1.4,
               "%s vs %s" % (foe_shiny.get_editor_property("max_health"), foe_plain.get_editor_property("max_health"))),
    ]}


def scenario_inventory(p):
    """The tabbed inventory (hub 28570/28573/28574): the same controls in two realms with different catalogs and
    themes. Opened over Play, driven by the harness commands the keys map to; the state lines prove the tabs,
    the per-tab cursor, the actions, and that browsing changed no count. Slate panels don't show in a scene
    capture, so this is proven by state, like the menus."""
    h = hero()
    checks = []
    runs = {}
    for realm, stock, worn in (
        ("gallery-city", {"PAINT_SPRAY": 1, "WIDE_BRUSH": 1, "PIGMENT_RED": 12, "PAINTER_COAT": 1, "HEARTSTONE": 1}, ("HAND", "PAINT_SPRAY")),
        ("bricks", {"STUD_HAMMER": 1, "BRICK_RED": 240, "BRICK_BLUE": 31, "PLAN_BRIDGE": 1}, ("HAND", "STUD_HAMMER")),
    ):
        h.inventory_input("realm:" + realm)
        for item, n in stock.items():
            h.inventory_input("give:%s:%d" % (item, n))
        h.inventory_input("wear:%s:%s" % worn)
        before = dict(h.get_editor_property("satchel"))
        h.toggle_inventory()
        yield from _frames(2)
        lines = {"open": h.inventory_input("state")}
        lines["rb"] = h.inventory_input("tab+")
        lines["right"] = h.inventory_input("right")
        lines["rb2"] = h.inventory_input("tab+")
        lines["lb"] = h.inventory_input("tab-")
        lines["lb0"] = h.inventory_input("tab-")
        lines["act"] = h.inventory_input("accept")
        lines["pick"] = h.inventory_input("accept")
        yield from _frames(2)
        lines["after"] = h.inventory_input("state")
        closed = h.inventory_input("back").startswith("closed") and not h.is_inventory_open()
        after = dict(h.get_editor_property("satchel"))
        runs[realm] = {"lines": lines, "closed": closed, "same_counts": before == after}
    g, b = runs["gallery-city"], runs["bricks"]
    gl, bl = g["lines"], b["lines"]

    def kv(line):
        return _kv(line)

    checks += [
        _check("gallery opens on ALL in its theme", "tab=ALL(1/6)" in gl["open"] and "theme=gallery" in gl["open"], gl["open"]),
        _check("bricks opens on ALL in its theme", "tab=ALL(1/6)" in bl["open"] and "theme=bricks" in bl["open"], bl["open"]),
        _check("RB reaches each realm's own second tab", "tab=SPRAYS" in gl["rb"] and "tab=BRICKS" in bl["rb"], gl["rb"] + " | " + bl["rb"]),
        _check("the tab remembers its cursor after LB", kv(gl["lb"]).get("cursor") == "1" and kv(bl["lb"]).get("cursor") == "1", gl["lb"] + " | " + bl["lb"]),
        _check("ALL kept its own cursor", kv(gl["lb0"]).get("cursor") == "0" and kv(bl["lb0"]).get("cursor") == "0"),
        _check("A opens the actions, A picks one, and the host ran it", "actions=" in gl["act"] and "last=UNEQUIP PAINT_SPRAY" in gl["pick"]
               and "actions=" in bl["act"] and "last=UNEQUIP STUD_HAMMER" in bl["pick"], gl["pick"] + " | " + bl["pick"]),
        _check("after the host acts the item shows unworn and the place is kept", " worn" not in gl["after"].split(" last=")[0] and "cursor=0" in gl["after"], gl["after"]),
        _check("browsing changed no count", g["same_counts"] and b["same_counts"]),
        _check("B closes the panel in both realms", g["closed"] and b["closed"]),
    ]
    # World Zero: the hero's own tools, armour and cubes, nothing to stock.
    h.inventory_input("realm:world-zero")
    h.toggle_inventory()
    yield from _frames(2)
    zero = h.inventory_input("state")
    h.inventory_input("tab+")
    tools = h.inventory_input("state")
    h.inventory_input("back")
    h.inventory_input("realm:")
    checks += [
        _check("world zero lists the tools the hero carries", "realm=WORLD-ZERO" in zero and "tab=TOOLS" in tools and "item=SWORD x1 worn" in tools, tools),
    ]
    return {"checks": checks}


def scenario_dialogue(p):
    """Dialogue boxes in the 3D realms (Richey 2026-10-13, Animal Crossing style): an NPC line opens the box in the
    realm's theme, types itself with blips, pages, offers choices; A/B/up/down drive it; the outcome reaches the
    hero. Proven by state lines (Slate isn't in a scene capture). Play's frame rate sets the typewriter's pace, so
    every step reads the state and acts on it rather than counting frames."""
    h = hero()
    h.inventory_input("realm:gallery-city")
    h.speak("Curator Vell", "Welcome to the Gallery, painter. The Heartstone went missing last night and the Echo Choir has gone quiet. Would you look into it for me?", ["Of course", "Not now"])
    yield from _frames(2)
    opened = h.dialogue_input("state")
    yield from _frames(6)
    typed = h.dialogue_input("state")
    turned = ""
    for _ in range(4):   # A finishes the page, A turns it; however far the typewriter got
        turned = h.dialogue_input("a")
        if "page=2/2" in turned:
            break
    skipped = h.dialogue_input("state")
    if "choosing" not in skipped:
        skipped = h.dialogue_input("b")   # B skips to the end of the text: the choices
    was = _kv(skipped).get("choosing", "0/2").split("/")[0]
    down = h.dialogue_input("down")
    want = str((int(was) + 1) % 2)
    pick = h.dialogue_input("a")
    yield from _frames(2)
    after = h.dialogue_input("state")
    h.speak("Street Muralist", "Psst. The wall by the vat has a secret.", [])
    yield from _frames(2)
    h.dialogue_input("b")
    closed = h.dialogue_input("a")
    yield from _frames(2)
    h.inventory_input("realm:")
    return {"checks": [
        _check("the line opens the box in the realm's era", "open=1 era=MODERN who=Curator Vell page=1/2" in opened, opened),
        _check("it types itself with blips", int(_kv(typed).get("blips", "0")) > 5, typed),
        _check("A finishes the page and turns it", "page=2/2" in turned, turned),
        _check("the end of the text is the choices", "choosing=" in skipped, skipped),
        _check("down moves the choice and A picks it for the hero", ("choosing=%s/2" % want) in down and ("last=choice:%s:Curator Vell" % want) in pick, down + " | " + pick),
        _check("the box is down afterwards", after.startswith("closed") and not h.is_dialogue_open(), after),
        _check("a line without choices closes on A", "last=closed:Street Muralist" in closed and not h.is_dialogue_open(), closed),
    ]}


def scenario_cast(p):
    """A realm NPC with a script (DCS 1): Curator Vell spawned in Play, talked to through the dialogue box; the
    quest branch sets a flag, a second talk starts from it, and the Echo Choir (another talker) hears the
    realm-wide flag. State lines prove it."""
    h = hero()
    h.inventory_input("realm:gallery-city")
    at = h.get_actor_location()
    fwd = h.get_actor_forward_vector()
    spawn = unreal.DaedalusFilm.spawn_in_play
    vell = spawn(h, unreal.DaedalusTalker, at + fwd * 220 + unreal.Vector(0, 0, 100), unreal.Rotator(0, 0, 0))
    vell.set_editor_property("who", "Curator Vell")
    choir = spawn(h, unreal.DaedalusTalker, at + fwd * 220 + unreal.Vector(0, 300, 100), unreal.Rotator(0, 0, 0))
    choir.set_editor_property("who", "Echo Choir")
    yield from _frames(2)
    bound = vell.rebind() and choir.rebind()
    yield from _frames(2)

    def through(talker, picks):
        """Talk, closing plain lines with B+A and answering asks with the given picks, until the box is down."""
        lines = []
        used = talker.talk_to(h)
        for _ in range(12):
            st = h.dialogue_input("state")
            if st.startswith("closed"):
                break
            lines.append(st)
            if "choosing" not in st:
                h.dialogue_input("b")      # skip the typewriter
                st = h.dialogue_input("state")
            if "choosing" in st:
                want = picks.pop(0) if picks else 0
                cur = int(_kv(st).get("choosing", "0/1").split("/")[0])
                for _ in range((want - cur) % 4):
                    h.dialogue_input("down")
            h.dialogue_input("a")
        return used, lines

    used1, first = through(vell, [1])        # "Not now"
    s1 = vell.state()
    used2, second = through(vell, [0])       # "Of course"
    s2 = vell.state()
    used3, third = through(vell, [1])        # waiting -> "I have it"
    s3 = vell.state()
    used4, choir_lines = through(choir, [])
    s4 = choir.state()
    h.inventory_input("realm:")
    return {"checks": [
        _check("both talkers bound their scripts", bound and "bound=1" in s1 and "bound=1" in s4, s1 + " | " + s4),
        _check("the first talk runs welcome, Heartstone, the ask", used1 and len(first) >= 3 and "who=Curator Vell" in first[0], " / ".join(first)[:300]),
        _check("'Not now' sets nothing", "flags= " in s1 + " " and "talks=1" in s1, s1),
        _check("'Of course' sets the quest flag", "heartstone" in s2 and "talks=2" in s2, s2),
        _check("the third talk starts at 'waiting' and 'I have it' finishes the quest", "heartstone_done" in s3 and any("Any word" in l or "page=" in l for l in third), s3),
        _check("the Choir hears the realm-wide flag and sings", "heartstone_done" in s4 and used4, s4),
        _check("the Curator's Frame Plate landed in the satchel", "given=FRAME_PLATE" in s3 and dict(h.get_editor_property("satchel")).get("FRAME_PLATE", 0) >= 1, s3),
        _check("the talkers wear Sol's imported cast (Mob_Gallery_<Who>)", "art=Mob_Gallery_CuratorVell:1" in s3 and "art=Mob_Gallery_EchoChoir:1" in s4, s3 + " | " + s4),
    ]}


def scenario_realm_switch(p):
    """The realm session (hub 28885): one player, seven realms, four ways between them. Gates from World Zero,
    the portal in and back, a boat at a dock into the Ocean and a shore landing home; refusals leave the session
    where it is; the inventory catalog follows the realm; the session is in the hero's progress file."""
    h = hero()
    start = h.realm_session_state()
    before = int(_kv(start).get("switches", "0")) if "switches=" in start else 0   # the session persists across runs
    if "switches=" not in start:   # not started yet this Play: the count lives in the saved progress file
        try:
            import os, json
            with open(os.path.join(unreal.Paths.project_saved_dir(), "Config", "DaedalusHero.json"), encoding="utf-8") as f:
                before = int((json.load(f).get("realm_session", "") + " 0 0 0 0").split()[3])
        except Exception:
            before = 0
    g = h.switch_realm("gallery-city", "gate", "")
    cat_after_gate = h.inventory_catalog_name()
    landed = str(h.get_editor_property("landed_at"))
    gate = next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.TargetPoint) if a.get_actor_label() == "Gate_GALLERY-CITY"), None)
    near_gate = gate is not None and (h.get_actor_location() - gate.get_actor_location()).length() < 600.0
    bad = h.switch_realm("parcels", "gate", "")
    po = h.switch_realm("portal", "portal", "")
    yield from _frames(3)
    for _ in range(80):   # the 8-bit realm loads from the server or the shipped spec
        if "map=" in h.realm_state() or "refused" in h.realm_state():
            break
        yield
    in_portal = h.is_realm_open()
    back = h.switch_realm("gallery-city", "portal", "")
    yield from _frames(3)
    out = not h.is_realm_open()
    dock = h.switch_realm("ocean", "dock", "boat:vat-pier")
    wrong = h.switch_realm("bricks", "dock", "boat:x")
    shore = h.switch_realm("gallery-city", "shore", "")
    home = h.switch_realm("world-zero", "gate", "")
    state = h.realm_session_state()
    import os, json
    path = os.path.join(unreal.Paths.project_saved_dir(), "Config", "DaedalusHero.json")
    saved = ""
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f).get("realm_session", "")
    except Exception as e:
        saved = "no file: %s" % e
    return {"checks": [
        _check("a gate reaches Gallery City and its catalog follows", g.startswith("ok WORLD-ZERO -> GALLERY-CITY") and cat_after_gate == "gallery-city", g + " " + cat_after_gate),
        _check("the hero lands at the realm's gate marker (daedalus_realm_ground)", landed == "Gate_GALLERY-CITY" and near_gate, "landed=%s near=%s" % (landed, near_gate)),
        _check("a gate between two realms is refused", bad.startswith("refused"), bad),
        _check("the portal opens the 8-bit realm", po.startswith("ok GALLERY-CITY -> PORTAL") and in_portal, po),
        _check("and leads back where you came from", back.startswith("ok PORTAL -> GALLERY-CITY") and out, back),
        _check("a boat at a dock enters the Ocean", dock.startswith("ok GALLERY-CITY -> OCEAN"), dock),
        _check("a boat cannot land at another realm's dock", wrong.startswith("refused"), wrong),
        _check("a shore landing returns to the departure", shore.startswith("ok OCEAN -> GALLERY-CITY"), shore),
        _check("home by gate, six more switches counted", home.startswith("ok GALLERY-CITY -> WORLD-ZERO") and int(_kv(state).get("switches", "0")) - before == 6, state + " before=%d" % before),
        _check("the session is saved with the hero's progress", saved.startswith("WORLD-ZERO"), saved),
    ]}


def scenario_control(p):
    """More control over Unreal (Richey 2026-10-13): injected Enhanced Input moves the hero like a held key, a jump
    leaves the ground, goto snaps to the ground, look turns the camera, a console command runs in the Play world
    and the log report reads clean of errors for this Play."""
    import daedalus_control as C
    h = hero()
    w = world()
    p0 = h.get_actor_location()
    p0 = (p0.x, p0.y, p0.z)
    r = C.hero_input({"action": "Move", "y": 1.0, "seconds": 1.5})
    t0 = unreal.GameplayStatics.get_time_seconds(w)
    while unreal.GameplayStatics.get_time_seconds(w) - t0 < 2.0:
        yield
    p1 = h.get_actor_location()
    walked = ((p1.x - p0[0]) ** 2 + (p1.y - p0[1]) ** 2) ** 0.5
    zs = []
    C.hero_input({"action": "Jump"})
    for _ in range(25):
        zs.append(h.get_actor_location().z)
        yield
    rose = max(zs) - min(zs)
    far = unreal.Vector(p0[0] + 600.0, p0[1] + 600.0, p0[2] + 3000.0)
    g = C.goto({"x": far.x, "y": far.y, "z": far.z, "yaw": 90.0, "snap": True})
    yield from _frames(5)
    p2 = h.get_actor_location()
    lk = C.look({"yaw": 180.0, "pitch": -20.0})
    st = C.state({})["state"]
    cs = C.console({"cmd": "stat none"})
    rep = C.log_report({})
    return {"checks": [
        _check("injected Move walks the hero (held 1.5 s)", walked > 150.0, "walked=%.0f %s" % (walked, r["result"])),
        _check("an injected Jump leaves the ground", rose > 40.0, "rose=%.0f" % rose),
        _check("goto lands on the ground near the asked point, not 3000 up", g["ok"] and abs(p2.z - far.z) > 500.0 and abs(p2.x - far.x) < 50.0, g["state"]),
        _check("look turns the camera", "yaw=180" in lk["state"] or "yaw=-180" in lk["state"], lk["state"]),
        _check("state is one line with health, weapon and realm", "health=" in st and "weapon=" in st and "realm=" in st, st),
        _check("a console command runs in the Play world", cs["playing"] is True, str(cs)[:200]),
        _check("no editor errors this Play", rep["errors"] == 0, str(rep["top_errors"])[:300]),
    ]}


def scenario_stage(p):
    """The 8-bit battle on the 3D stage (hub 28710/29054): with Sol's ADaedalusBattlePresentation in the Play world,
    a realm fight's cues are forwarded to it every frame; RealmState counts them."""
    h = hero()
    spawn = unreal.DaedalusFilm.spawn_in_play
    at = h.get_actor_location()
    stage = spawn(h, unreal.DaedalusBattlePresentation, at + unreal.Vector(0, 0, 400), unreal.Rotator(0, 0, 0))
    yield from _frames(2)
    h.enter_realm(7)
    for _ in range(80):
        if "map=" in h.realm_state() or "refused" in h.realm_state():
            break
        yield
    for _ in range(8):
        if _kv(h.realm_state()).get("ui") == "NONE":
            break
        h.realm_input("b")
    h.realm_input("toughen")
    h.realm_input("battle:BLIGHT_SLIME+PUFFCAP")
    yield from _frames(2)
    h.realm_input("autofight")
    yield from _frames(4)
    st = h.realm_state()
    line = h.realm_input("stage")
    h.exit_realm()
    yield from _frames(2)
    return {"checks": [
        _check("the stage actor was found by the hero", "stage=1" in st, st[:200]),
        _check("a fight's cues reached it", int(_kv(st).get("cues_staged", "0")) >= 10, st[:200]),
        _check("the stage command says where they went", line.startswith("staged to"), line),
    ]}


def scenario_realm_ground(p):
    """Every 3D realm is laid down (BASE-LAYER.md, Richey 2026-10-13): a gate lands the hero at the realm's gate
    marker on its hub, the realm's cast stands there bound to its art, its creatures idle in the outer ring, the
    kit is on the ground and the first rings of lands are down; home by gate at the end."""
    h = hero()
    w = world()
    checks = []
    for realm in ("GALLERY-CITY", "PARCELS", "BRICKS", "LABYRINTH"):
        if h.realm_now() != "WORLD-ZERO":
            h.switch_realm("world-zero", "gate", "")
            yield from _frames(2)
        r = h.switch_realm(realm.lower(), "gate", "")
        yield from _frames(3)
        tag = "Realm:" + realm
        mine = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if any(str(t) == tag for t in a.tags)]
        kinds = {}
        for a in mine:
            k = "Talker" if a.get_class().get_name().startswith("DaedalusTalker") else next((str(t) for t in a.tags if str(t) in ("Hub", "Gate", "Spawn", "Dock", "SubDock", "Mount", "Kit", "Land", "Creature")), "other")
            kinds[k] = kinds.get(k, 0) + 1
        talkers = [a for a in mine if a.get_class().get_name().startswith("DaedalusTalker")]
        with_art = sum(1 for t in talkers if t.state().endswith(":1"))
        gate = next((a for a in mine if a.get_actor_label() == "Gate_" + realm), None)
        dist = (h.get_actor_location() - gate.get_actor_location()).length() if gate else -1
        landed = str(h.get_editor_property("landed_at"))
        checks.append(_check("%s: the gate lands the hero at Gate_%s" % (realm, realm), r.startswith("ok") and landed == "Gate_" + realm and 0 <= dist < 600, "%s landed=%s dist=%.0f" % (r, landed, dist)))
        checks.append(_check("%s: hub, 5 markers, 24 kit props, 160 lands are down" % realm, kinds.get("Hub", 0) == 1 and sum(kinds.get(k, 0) for k in ("Gate", "Spawn", "Dock", "SubDock", "Mount")) == 5 and kinds.get("Kit", 0) >= 24 and kinds.get("Land", 0) >= 160, str(kinds)))
        checks.append(_check("%s: 12 talkers stand at the hub, every one wearing its art" % realm, len(talkers) == 12 and with_art == 12, "talkers=%d art=%d" % (len(talkers), with_art)))
        checks.append(_check("%s: the bestiary idles in the outer ring" % realm, kinds.get("Creature", 0) >= 12, "creatures=%d" % kinds.get("Creature", 0)))
    home = h.switch_realm("world-zero", "gate", "")
    checks.append(_check("home by gate", home.startswith("ok"), home))
    return {"checks": checks}


def scenario_realm_host(p):
    """The world actor follows the hero through the server's realm directory (DaedalusRealmDirectoryCore): after a
    gate to Gallery City, the actor hosts the world the directory names for GALLERY-CITY. When the server has no
    directory yet (old build), the checks say so instead of failing on a missing host."""
    h = hero()
    w = world()
    wa = next(iter(unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusWorldActor)), None)
    if not wa:
        return {"checks": [_check("a DaedalusWorldActor is in the world", False, "none")]}
    wa.load_directory()
    for _ in range(90):
        yield
        if not wa.directory_state().startswith("directory=none why=not loaded"):
            break
    state = wa.directory_state()
    served = state.startswith("directory=ok")
    hosted = "GALLERY-CITY=" in state
    if h.realm_now() != "WORLD-ZERO":
        h.switch_realm("world-zero", "gate", "")
        yield from _frames(2)
    before = str(wa.get_editor_property("world_id"))
    r = h.switch_realm("gallery-city", "gate", "")
    yield from _frames(5)
    after = str(wa.get_editor_property("world_id"))
    h.switch_realm("world-zero", "gate", "")
    yield from _frames(5)
    home = str(wa.get_editor_property("world_id"))
    return {"checks": [
        _check("the directory was fetched (or the server said why not)", served or state.startswith("directory=none why=http"), state),
        _check("the directory binds the five realms and the Ocean" if served else "no directory on this server build (skip)", (not served) or "unhosted=-" in state, state),
        _check("the gate made the world actor host Gallery City's world" if hosted else "no Gallery host listed (skip)", (not hosted) or (r.startswith("ok") and after != before and after == wa.world_id_for_realm("GALLERY-CITY")), "%s -> %s (%s)" % (before, after, r)),
        _check("home by gate returns the actor to World Zero's world" if hosted else "home by gate (skip host check)", (not hosted) or home == before, home),
    ]}


def scenario_mounts(p):
    """Mounts per realm (BASE-LAYER row 9, DaedalusMountCore): in each 3D realm the called vehicle wears that
    realm's mount art (drone, helicopter, plane, sky-strider), flies to a lifted height within its ceiling, and
    World Zero still gives the hover bike."""
    h = hero()
    checks = []
    want = {"GALLERY-CITY": "Mob_Gallery_GalleryDrone", "PARCELS": "Mob_Parcels_ParcelHelicopter", "BRICKS": "Mob_Bricks_BrickPlane", "LABYRINTH": "Mob_Lab_SkyStrider"}
    for realm, art in want.items():
        if h.realm_now() != "WORLD-ZERO":
            h.switch_realm("world-zero", "gate", "")
            yield from _frames(2)
        h.switch_realm(realm.lower(), "gate", "")
        yield from _frames(3)
        g = h.spawn_vehicle()
        yield from _frames(2)
        st = g.mount_state() if g else "no vehicle"
        checks.append(_check("%s: the vehicle wears %s" % (realm, art), g is not None and ("art=%s:1" % art) in st, st))
        if g:
            z0 = g.get_actor_location().z
            g.lift(3000.0)
            yield from _seconds(2.0)   # game time (45 frames at 46 fps was under a second: Gallery dz=0, 02:15)
            z1 = g.get_actor_location().z
            st2 = g.mount_state()
            checks.append(_check("%s: it climbs when lifted, within its ceiling" % realm, z1 - z0 > 800.0 and "wanted=3000" in st2, "dz=%.0f %s" % (z1 - z0, st2)))
            g.destroy_actor()
    h.switch_realm("world-zero", "gate", "")
    yield from _frames(3)
    g = h.spawn_vehicle()
    st = g.mount_state() if g else "no vehicle"
    checks.append(_check("World Zero: the hover bike, ground-hugging", g is not None and "mount=hover bike" in st and "ceiling=0" in st, st))
    if g:
        g.destroy_actor()
    return {"checks": checks}


def scenario_portals(p):
    """Walk-in crossings (BASE-LAYER row 10, ADaedalusRealmPortal): the hub's east gate takes the hero to Gallery
    City by overlap alone, the cooldown keeps the landing gate from bouncing him back, Gallery's gate home returns
    him, and a dock portal asks the Ocean (refused or accepted by the session rules, never a crash)."""
    h = hero()
    w = world()
    portals = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusRealmPortal)}
    checks = [_check("portals are laid in the world (hub gates + realm gates/docks)", len(portals) >= 4 + 3 * 4, str(len(portals)))]
    if h.realm_now() != "WORLD-ZERO":
        h.switch_realm("world-zero", "gate", "")
        yield from _frames(2)
    east = portals.get("Portal_WORLD-ZERO_to_GALLERY-CITY")
    if east:
        h.teleport(east.get_actor_location() + unreal.Vector(-700, 0, 0), 0.0, True)
        yield from _seconds(3.5)   # the switch above set LastRealmSwitchAt: wait out the cooldown (02:15: 2 frames at 46 fps was not)
        r = east.cross(h)   # the same path the overlap takes
        yield from _frames(4)
        checks.append(_check("the east gate carries the hero to Gallery City", r.startswith("ok WORLD-ZERO -> GALLERY-CITY") and h.realm_now() == "GALLERY-CITY", r))
        home = portals.get("Portal_GALLERY-CITY_Gate")
        early = home.cross(h) if home else "no portal"
        checks.append(_check("the landing gate is on cooldown, so no bounce", early == "cooldown", early))
        yield from _seconds(3.5)   # game time, not frames: 105 frames at 46 fps is under the 3 s cooldown
        back = home.cross(h) if home else "no portal"
        yield from _frames(3)
        checks.append(_check("after the cooldown the gate takes him home", back.startswith("ok GALLERY-CITY -> WORLD-ZERO") and h.realm_now() == "WORLD-ZERO", back))
    dock = portals.get("Portal_PARCELS_Dock")
    if dock:
        h.switch_realm("parcels", "gate", "")
        yield from _seconds(3.5)
        r = dock.cross(h)
        yield from _frames(2)
        checks.append(_check("a dock portal asks the session for the Ocean (boat)", r.startswith("ok PARCELS -> OCEAN") or r.startswith("refused"), r))
        h.switch_realm("world-zero", "gate", "")
        yield from _frames(2)
    return {"checks": checks}


def scenario_bestiary(p):
    """The realm's bestiary (BASE-LAYER row 6, DaedalusBestiaryCore): packs spawned in Gallery City are gallery
    creatures (kinds from the table) wearing Sol's skeletal art; back in World Zero the crystal kinds return."""
    h = hero()
    w = world()
    checks = []
    if h.realm_now() != "WORLD-ZERO":
        h.switch_realm("world-zero", "gate", "")
        yield from _frames(2)
    h.switch_realm("gallery-city", "gate", "")
    yield from _frames(4)
    before = {a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusTarget)}
    made = sum(h.spawn_pack() for _ in range(3))
    yield from _frames(4)
    new = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusTarget) if a.get_name() not in before]
    kinds = sorted({str(a.get_editor_property("kind")) for a in new})
    gallery = {"SMUDGELING", "THUMBTACK_BEETLE", "CANVAS_MOTH", "EASEL_STRIDER", "TURPENTINE_TOAD", "MOSAIC_HOUND", "GILDED_FRAME_MIMIC", "SENTINEL_BUST", "GREY_WASH"}
    dressed = sum(1 for a in new if a.get_editor_property("skin_mesh") is not None)
    checks.append(_check("packs spawn in Gallery City", made >= 2 and len(new) >= 2, "made=%d new=%d" % (made, len(new))))
    checks.append(_check("every foe is a gallery creature from the bestiary", bool(kinds) and set(kinds) <= gallery, str(kinds)))
    checks.append(_check("each wears its skeletal art (not the crystal)", new and dressed == len(new), "dressed=%d/%d" % (dressed, len(new))))
    for a in new:
        a.destroy_actor()
    h.switch_realm("world-zero", "gate", "")
    yield from _frames(4)
    before = {a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusTarget)}
    h.spawn_pack()
    yield from _frames(3)
    home = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusTarget) if a.get_name() not in before]
    hk = sorted({str(a.get_editor_property("kind")) for a in home})
    checks.append(_check("home, the server's crystal kinds are back", bool(hk) and not (set(hk) & gallery), str(hk)))
    for a in home:
        a.destroy_actor()
    return {"checks": checks}


TOUR_REALMS = ("WORLD-ZERO", "GALLERY-CITY", "PARCELS", "BRICKS", "LABYRINTH")
TOUR_STOPS = ("Mount", "Dock", "SubDock", "Gate", "Spawn")


def _tour_stops(realm):
    """[(name, actor)] the airship must dock at in this realm: the realm's markers (Dock_<realm> etc.), or for World
    Zero its portals (Portal_WORLD-ZERO_<Dock|SubDock|East...>) since the hub has no TargetPoint markers."""
    out = []
    if realm == "WORLD-ZERO":
        for a in _all(unreal.DaedalusRealmPortal):
            l = a.get_actor_label()
            if l.startswith("Portal_WORLD-ZERO_"):
                out.append((l.split("_", 2)[2], a))
    else:
        want = {"%s_%s" % (s, realm): s for s in TOUR_STOPS}
        for a in _all(unreal.TargetPoint):
            l = a.get_actor_label()
            if l in want:
                out.append((want[l], a))
    out.sort(key=lambda t: t[0])
    return out


def _fly_to(g, pc, at, max_frames=9000, arrive_cm=1200.0):
    """Steer the mounted vehicle at a world point (flat), boosting, until within arrive_cm or max_frames. Yields.
    Returns (frames, final flat distance)."""
    n = 0
    while n < max_frames:
        here = g.get_actor_location()
        dx, dy = at.x - here.x, at.y - here.y
        d = math.hypot(dx, dy)
        if d < arrive_cm:
            break
        pc.set_control_rotation(unreal.Rotator(0.0, math.degrees(math.atan2(dy, dx)), 0.0))
        g.drive(1.0, 0.0, d > 3000.0)
        n += 1
        yield
    g.drive(0.0, 0.0, False)
    here = g.get_actor_location()
    return n, math.hypot(at.x - here.x, at.y - here.y)


def scenario_airship(p):
    """The airship tour (Richey 2026-10-13 23:57: "once all the islands are done we must prove our flying air ship
    can fly and dock everywhere and explore the whole map"): in every realm the hero calls the realm's mount, gets
    on, climbs, flies to each marker (Mount pad, Dock, SubDock, Gate, Spawn) and settles onto it; in World Zero it
    also flies one long leg out over the islands to district 33's centre and back. Portals are switched off for the
    tour so a landing at a dock does not teleport the ship mid-flight. The receipt lists every landing with its
    distance, height over ground and frames flown."""
    import daedalus_land_grid as G
    import daedalus_districts as D
    h = hero()
    pc = controller()
    checks, landings = [], []
    portals = _all(unreal.DaedalusRealmPortal)
    for a in portals:
        a.set_actor_enable_collision(False)
    try:
        for realm in TOUR_REALMS:
            if h.realm_now() != realm:
                r = h.switch_realm(realm.lower(), "gate", "")
                yield from _frames(4)
                checks.append(_check("%s: the hero arrives for the tour" % realm, h.realm_now() == realm, r))
                if h.realm_now() != realm:
                    continue
            stops = _tour_stops(realm)
            checks.append(_check("%s: tour stops are laid (%d)" % (realm, len(stops)), len(stops) >= 2, ", ".join(s for s, _ in stops)))
            for b in ghosts():
                b.destroy_actor()
            g = h.spawn_vehicle()
            yield from _frames(2)
            if not g:
                checks.append(_check("%s: the mount answers the call" % realm, False, "no vehicle"))
                continue
            on = g.mount(h)   # not h.interact(): at a gate the nearest interactable can be an arcade cabinet (01:36, Pong)
            yield from _frames(2)
            st = g.mount_state()
            checks.append(_check("%s: the hero is aboard %s" % (realm, st.split(" ")[0]), pc.get_controlled_pawn() == g, st))
            g.lift(2500.0)
            yield from _frames(30)
            legs = [(name, a.get_actor_location()) for name, a in stops]
            if realm == "WORLD-ZERO":
                hub_cm = __import__("daedalus_realm_ground").ORIGINS["WORLD-ZERO"]
                cx, cy = G.cell(D.district_cells(33)[55])
                far = unreal.Vector(hub_cm[0] + (cx - G.HUB) * G.PITCH_M * 100.0, hub_cm[1] + (cy - G.HUB) * G.PITCH_M * 100.0, 0.0)
                legs.append(("District_33", far))
                legs.append(("Spawn", stops[0][1].get_actor_location() if stops else g.get_actor_location()))
            for name, at in legs:
                z0 = g.get_actor_location().z
                frames, d = yield from _fly_to(g, pc, at)
                g.lift(0.0)   # settle onto the pad
                yield from _frames(40)
                st = g.mount_state()
                grounded = "grounded=1" in st
                here = g.get_actor_location()
                landings.append({"realm": realm, "stop": name, "dist_cm": round(d), "frames": frames, "z": round(here.z), "grounded": grounded})
                checks.append(_check("%s: docked at %s" % (realm, name), d < 1500.0 and grounded, "d=%.0f frames=%d %s" % (d, frames, st)))
                g.lift(2500.0)
                yield from _frames(20)
            g.dismount()
            yield from _frames(2)
            g.destroy_actor()
    finally:
        for a in portals:
            a.set_actor_enable_collision(True)
    docked = sum(1 for l in landings if l["dist_cm"] < 1500 and l["grounded"])
    checks.append(_check("the airship docked everywhere: %d/%d landings" % (docked, len(landings)), landings and docked == len(landings), str(landings)[:900]))
    return {"checks": checks, "landings": landings}


SCENARIOS = {
    "airship": scenario_airship,
    "shoot": scenario_shoot,
    "views_layouts": scenario_views_layouts,
    "ghost": scenario_ghost,
    "foes_hunt": scenario_foes_hunt,
    "shield": scenario_shield,
    "encounters": scenario_encounters,
    "armor": scenario_armor,
    "dig": scenario_dig,
    "fall": scenario_fall,
    "realm": scenario_realm,
    "dress": scenario_dress,
    "wild": scenario_wild,
    "orrery": scenario_orrery,
    "tactics": scenario_tactics,
    "tactics_remote": scenario_tactics_remote,
    "shiny": scenario_shiny,
    "inventory": scenario_inventory,
    "dialogue": scenario_dialogue,
    "cast": scenario_cast,
    "realm_switch": scenario_realm_switch,
    "realm_ground": scenario_realm_ground,
    "realm_host": scenario_realm_host,
    "mounts": scenario_mounts,
    "portals": scenario_portals,
    "bestiary": scenario_bestiary,
    "control": scenario_control,
    "stage": scenario_stage,
}


def register(bridge):
    bridge.register("daedalus.play_scenario", play_scenario,
                    "Start a play-test scenario inside Play (it runs frame by frame); read it with daedalus.play_status. "
                    "Scenarios: " + ", ".join(sorted(SCENARIOS)), {"name": "str", "frames": "int (foes_hunt)"})
    bridge.register("daedalus.play_status", play_status, "The running or finished scenario: frames, checks, record", {})
    bridge.register("daedalus.play_snapshot", snapshot, "Hero, foes, Ghosts, foe routes and fps right now", {})
    bridge.register("daedalus.play_capture", play_capture,
                    "A PNG of what the player sees in Play (the camera, not the editor viewport); returns its path",
                    {"width": "int", "height": "int", "dir": "str", "name": "str"})
    bridge.register("daedalus.realm", realm,
                    "Drive the 8-bit realm (ADR-052): cmd=enter (seed) | exit | up/down/left/right/a/b/start | hold:<b> | "
                    "release:<b> | tick:<s> | place:<MAP>:<x>:<y>:<f> | give:<ITEM>:<n> | gold:<n> | battle:<ID>+<ID> | "
                    "autofight | toughen | portal | save | spec; empty cmd returns the state",
                    {"cmd": "str", "seed": "int"})
    bridge.register("daedalus.realm_capture", realm_capture,
                    "The realm's screen as a PNG (3x, from its framebuffer) in Saved/Realm; returns the path", {"name": "str"})
    bridge.register("daedalus.full_speed", full_speed, "Stop the editor slowing Play when it is not the window in front", {})
