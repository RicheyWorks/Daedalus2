# SPDX-License-Identifier: MIT
"""Runs when the editor starts (Unreal runs every plugin's Content/Python/init_unreal.py).

1. Starts the Claude Unreal Bridge (claude_unreal_bridge.py) on 127.0.0.1:9877, so Claude can operate this editor
   (set DAEDALUS_BRIDGE=off to keep it from starting).
2. Once a level holding a Daedalus world has opened, points the viewport at the world once, so the islands are
   the first thing on screen instead of empty sky.
Headless runs (commandlets) have no viewport and skip both.
"""

import os

import unreal

try:
    import daedalus_view
except ImportError:  # pragma: no cover
    daedalus_view = None

_state = {"handle": None, "ticks": 0}


def _tick(_delta):
    _state["ticks"] += 1
    done = False
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if world is not None and daedalus_view.daedalus_worlds():
            done = daedalus_view.frame_editor()
    except Exception as e:  # never let a camera nicety break the editor
        unreal.log_warning("Daedalus: could not frame the viewport (%s)" % e)
        done = True
    # Give the level up to ~10 s of frames to load; after that, leave the camera alone.
    if done or _state["ticks"] > 600:
        unreal.unregister_slate_post_tick_callback(_state["handle"])


def _headless():
    check = getattr(unreal, "is_running_commandlet", None)
    return bool(check()) if check else False


if daedalus_view is not None and not _headless():
    try:
        _state["handle"] = unreal.register_slate_post_tick_callback(_tick)
    except Exception as e:  # no Slate (a headless run): nothing to frame
        unreal.log("Daedalus: viewport framing off (%s)" % e)


if not _headless() and os.environ.get("DAEDALUS_BRIDGE", "on").lower() != "off":
    try:
        import claude_unreal_bridge
        claude_unreal_bridge.start()
    except Exception as e:  # a port in use (a second editor) must not stop the editor opening
        unreal.log_warning("Claude Unreal Bridge did not start: %s" % e)
