# SPDX-License-Identifier: MIT
"""Daedalus commands for the Claude Unreal Bridge (claude-unreal-connector), added through its register() API:

  daedalus.import_world   download a World Package from a Daedalus server, import it, verify it, frame it
  daedalus.frame_world    point the editor viewport at a Daedalus world in the open level

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


def _register(bridge):
    bridge.register("daedalus.import_world", import_world,
                    "Download a Daedalus World Package from its server, import it (chunks, materials, sky, ark, live "
                    "actor, view), verify it against the manifest, and frame the viewport; returns every PASS/FAIL check",
                    {"server": "str (default http://localhost:8088)", "world": "str (default world-zero)",
                     "live": "bool (only the live actor)"})
    bridge.register("daedalus.frame_world", frame_world,
                    "Point the editor viewport at a Daedalus world in the open level", {"world": "str"})


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
