# SPDX-License-Identifier: MIT
"""Runs when the editor starts (Unreal runs every plugin's Content/Python/init_unreal.py).

Once a level holding a Daedalus world has opened, point the viewport at the world once, so the islands
are the first thing on screen instead of empty sky. Headless runs (commandlets) have no viewport and skip it.
"""

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
