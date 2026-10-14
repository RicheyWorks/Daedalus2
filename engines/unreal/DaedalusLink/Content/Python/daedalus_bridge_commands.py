# SPDX-License-Identifier: MIT
"""Daedalus commands for the Claude Unreal Bridge (claude-unreal-connector), added through its register() API:

  daedalus.import_world   download a World Package from a Daedalus server, import it, verify it, frame it
  daedalus.frame_world    point the editor viewport at a Daedalus world in the open level
  daedalus.hero_setup     make Play spawn the Daedalus hero (ADR-036) standing on an island

The connector stays generic and these stay Daedalus's: an agent finds them with list_commands and calls them
with run_command. The bridge plugin may load after this one, so install() keeps trying on editor ticks until
the bridge can be imported (for up to about 30 s).
"""
import os
import sys
import tempfile

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def import_world(p):
    import import_world_package as iwp
    import daedalus_view as view
    server = p.get("server", "http://localhost:8088")
    world = p.get("world", "world-zero")
    live = bool(p.get("live"))
    zip_path = iwp.fetch(server, world, tempfile.mkdtemp(prefix="daedalus_"))
    manifest, _, _names = iwp.read_package(zip_path)
    iwp.import_into_unreal(zip_path, manifest, live_only=live)
    checks = iwp.judge(manifest, iwp.observe(manifest), live_only=live)
    iwp.report(manifest, checks, unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
    view.frame_editor(world)
    return {"world": manifest["world"], "geometry": manifest.get("geometry"),
            "ok": all(c["ok"] for c in checks), "checks": checks}


def frame_world(p):
    import daedalus_view as view
    return {"framed": bool(view.frame_editor(p.get("world")))}


HERO_START = "Daedalus Hero Start"


def hero_setup(p):
    """Set the level's GameMode Override to DaedalusGameMode and put a PlayerStart on top of an island.

    The island spot is found by tracing down onto the world's cubes near the middle of the biggest chunk, so the
    hero lands on grass, not in the sky. Needs the DaedalusLink module compiled with DaedalusHero (setup -Build).
    """
    import daedalus_view as view
    gm = getattr(unreal, "DaedalusGameMode", None)
    if gm is None:
        raise RuntimeError("DaedalusGameMode is not compiled in; run the setup line with -Build")
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    settings = world.get_world_settings()
    settings.set_editor_property("default_game_mode", gm.static_class())
    wid = p.get("world") or (view.daedalus_worlds() or ["world-zero"])[0]
    chunks = [a for a in eas.get_all_level_actors()
              if str(a.get_folder_path()) == view.FOLDER + wid and isinstance(a, unreal.StaticMeshActor)]
    chunks.sort(key=lambda a: -a.get_actor_bounds(False)[1].x * a.get_actor_bounds(False)[1].y)
    spot = None
    for a in chunks[:20]:
        o, e = a.get_actor_bounds(False)
        for dx, dy in ((0, 0), (0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2)):
            start = unreal.Vector(o.x + dx * e.x, o.y + dy * e.y, o.z + e.z + 2000)
            end = unreal.Vector(start.x, start.y, o.z - e.z - 2000)
            hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                         False, [], unreal.DrawDebugTrace.NONE, True)
            t = hit.to_tuple() if hit is not None else None
            if t and t[0]:
                spot = t[4]
                break
        if spot is not None:
            break
    if spot is None:
        raise RuntimeError("no island surface found under the world's chunks")
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart) and a.get_actor_label() in (HERO_START, view.START_LABEL):
            eas.destroy_actor(a)
    start = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(spot.x, spot.y, spot.z + 120),
                                       unreal.Rotator(0, 0, 45))
    start.set_actor_label(HERO_START)
    start.set_folder_path(view.FOLDER + wid)
    return {"game_mode": gm.__name__, "start": [round(spot.x), round(spot.y), round(spot.z + 120)], "world": wid}


def _register(bridge):
    bridge.register("daedalus.hero_setup", hero_setup,
                    "Make Play spawn the Daedalus hero (walk, jump, dash, sword, Zelda II down-thrust) on an island: "
                    "sets the GameMode Override and a PlayerStart on the ground", {"world": "str"})
    bridge.register("daedalus.import_world", import_world,
                    "Download a Daedalus World Package from its server, import it (chunks, materials, sky, ark, live "
                    "actor, view), verify it against the manifest, and frame the viewport; returns every PASS/FAIL check",
                    {"server": "str (default http://localhost:8088)", "world": "str (default world-zero)",
                     "live": "bool (only the live actor)"})
    bridge.register("daedalus.frame_world", frame_world,
                    "Point the editor viewport at a Daedalus world in the open level", {"world": "str"})
    try:
        import daedalus_play
        daedalus_play.register(bridge)
    except Exception as e:  # the play harness is optional; never block the other commands
        unreal.log_warning("Daedalus: play harness not loaded: %r" % (e,))
    try:
        import daedalus_control
        daedalus_control.register(bridge)
    except Exception as e:  # console, input, goto, look, state, automation, log_report
        unreal.log_warning("Daedalus: control commands not loaded: %r" % (e,))


_state = {"handle": None, "ticks": 0}


def _try(_delta=0.0):
    _state["ticks"] += 1
    try:
        import claude_unreal_bridge
    except ImportError:
        if _state["ticks"] > 1800 and _state["handle"] is not None:   # ~30 s: the bridge plugin is not enabled
            unreal.unregister_slate_post_tick_callback(_state["handle"])
            _state["handle"] = None
        return False
    _register(claude_unreal_bridge)
    if _state["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(_state["handle"])
        _state["handle"] = None
    unreal.log("Daedalus: commands added to the Claude Unreal Bridge")
    return True


def install():
    if not _try():
        _state["handle"] = unreal.register_slate_post_tick_callback(_try)
