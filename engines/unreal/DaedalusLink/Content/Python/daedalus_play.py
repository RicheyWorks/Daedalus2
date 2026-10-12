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
    h.realm_input("a")
    h.realm_input("toughen")
    steps0 = int(_kv(h.realm_state()).get("steps", 0))
    h.realm_input("hold:right")
    yield from _frames(60)
    h.realm_input("release:right")
    yield from _frames(10)
    walked = int(_kv(h.realm_state()).get("steps", 0)) - steps0
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
    h.realm_input("a")
    for c in ("b", "down", "down", "a"):
        h.realm_input(c)
    status = _kv(h.realm_state()).get("ui") == "STATUS"
    cap("realm_status.png")
    h.realm_input("a")
    h.realm_input("b")
    h.realm_input("portal")
    h.realm_input("up")
    said = _kv(h.realm_state()).get("msg", "")
    h.realm_input("a")
    for _ in range(60):
        if not h.is_realm_open():
            break
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


SCENARIOS = {
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
