# SPDX-License-Identifier: MIT
"""Render the trailer's frames in Play, one frame per editor tick, so herds, foes and the sky keep moving.

Run inside the editor while Play is on (the bridge's execute_python):
    exec(open(r"C:\\Users\\730ri\\projects\\Daedalus2\\tools\\trailer\\trailer_ue.py").read())
It returns at once; a tick callback renders frame after frame into Saved/Daedalus/trailer/frames/f_00000.png and writes
status.json (done/total, errors). make_trailer.ps1 then cuts the video with ffmpeg. Read-only for the level: one
temporary SceneCapture2D in the Play world, gone when Play stops.
"""
import json
import os
import sys

import unreal

HERE = globals().get("TRAILER_DIR", r"C:\Users\730ri\projects\Daedalus2\tools\trailer")   # set TRAILER_DIR to run from another checkout
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import importlib  # noqa: E402
import trailer_plan  # noqa: E402

importlib.reload(trailer_plan)

W_, H_ = 1280, 720
import time  # noqa: E402

ROOT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "Daedalus", "trailer")
OUT = os.path.join(ROOT, time.strftime("run-%m%d-%H%M%S"))   # a new folder per take: nothing is ever deleted
FRAMES = os.path.join(OUT, "frames")
os.makedirs(FRAMES, exist_ok=True)
with open(os.path.join(ROOT, "latest.txt"), "w") as _f:
    _f.write(OUT)

PLAN = trailer_plan.frames()
STATE = {"i": 0, "total": len(PLAN), "errors": [], "handle": None, "done": False, "squad": False}


def _status():
    with open(os.path.join(OUT, "status.json"), "w") as f:
        json.dump({k: v for k, v in STATE.items() if k != "handle"}, f)


def _world():
    return unreal.EditorLevelLibrary.get_game_world()


w = _world()
if not w:
    raise RuntimeError("start Play first: the trailer films the running game")
unreal.SystemLibrary.execute_console_command(w, "daedalus.FoesHunt 1")
unreal.SystemLibrary.execute_console_command(w, "daedalus.Tactics 1")
RT = unreal.RenderingLibrary.create_render_target2d(w, W_, H_, unreal.TextureRenderTargetFormat.RTF_RGBA8)
_t = unreal.Transform()
CAM = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(w, unreal.SceneCapture2D, _t)
CAM = unreal.GameplayStatics.finish_spawning_actor(CAM, _t)
CC = CAM.get_component_by_class(unreal.SceneCaptureComponent2D)
CC.set_editor_property("texture_target", RT)
CC.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
CC.set_editor_property("capture_every_frame", False)
CC.set_editor_property("fov_angle", 70.0)


def _squad():
    """Before the squad shot: three foes near the hero as one squad, so the director flanks on camera."""
    h = unreal.GameplayStatics.get_player_pawn(_world(), 0)
    if not h:
        return
    try:
        h.set_editor_property("invulnerable", True)
        h.spawn_foes(3)
        foes = unreal.GameplayStatics.get_all_actors_of_class(_world(), unreal.DaedalusTarget)
        for i, f in enumerate(sorted(foes, key=lambda a: a.get_name())[-3:]):
            f.set_editor_property("squad", "trailer-squad")
            f.set_editor_property("unit_id", "tr%d" % (i + 1))
    except Exception as e:  # the shot still films the scene
        STATE["errors"].append("squad: " + str(e)[:120])


def _tick(dt):
    try:
        if STATE["done"]:
            return
        if not _world():
            STATE["errors"].append("Play stopped at frame %d" % STATE["i"])
            _finish()
            return
        i = STATE["i"]
        if i >= len(PLAN):
            _finish()
            return
        _, name, eye, (pitch, yaw), _cap = PLAN[i]
        if name == "squad" and not STATE["squad"]:
            STATE["squad"] = True
            _squad()
        CAM.set_actor_location_and_rotation(unreal.Vector(*eye), unreal.Rotator(0.0, pitch, yaw), False, True)
        CC.capture_scene()
        unreal.RenderingLibrary.export_render_target(_world(), RT, FRAMES, "f_%05d.png" % i)
        STATE["i"] = i + 1
        if STATE["i"] % 30 == 0:
            _status()
    except Exception as e:
        STATE["errors"].append(str(e)[:200])
        if len(STATE["errors"]) > 20:
            _finish()


def _finish():
    STATE["done"] = True
    if STATE["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(STATE["handle"])
        STATE["handle"] = None
    try:
        CAM.destroy_actor()
    except Exception:
        pass
    _status()


STATE["handle"] = unreal.register_slate_post_tick_callback(_tick)
_status()
result = {"frames": len(PLAN), "out": FRAMES}
