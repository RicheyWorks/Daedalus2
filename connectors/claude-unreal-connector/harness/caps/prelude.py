# SPDX-License-Identifier: MIT
# Runs INSIDE the Unreal Editor (sent through execute_python), before an area module's probes.
#
# A probe is a function decorated with @probe("area.name"). It makes something real in the editor, reads it back,
# and returns a dict with "ok": True only when the read-back proves the thing worked. Anything it makes goes
# through spawn()/new_asset() so cleanup() removes it, and the user's level and content are left as they were.
# Probes never open modal dialogs: no file pickers, no prompts, and assets are created through factories, not
# menu commands.
import json
import time
import traceback

import unreal

PROBE_DIR = "/Game/_ClaudeProbe"
PROBE_FOLDER = "ClaudeProbe"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
WORLD = UES.get_editor_world()
_MADE_ACTORS = []
_PROBES = []
ORIGIN = unreal.Vector(0.0, 0.0, -50000.0)   # far below the islands, out of the user's view


def probe(pid):
    def wrap(fn):
        _PROBES.append((pid, fn))
        return fn
    return wrap


def spawn(cls, loc=None, rot=None):
    loc = loc if loc is not None else ORIGIN
    a = EAS.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0, 0, 0))
    if a is None:
        raise RuntimeError("spawn_actor_from_class(%s) returned None" % cls.__name__)
    a.set_folder_path(PROBE_FOLDER)
    _MADE_ACTORS.append(a)
    return a


def new_asset(name, cls, factory, sub=""):
    path = PROBE_DIR + sub
    full = path + "/" + name
    if EAL.does_asset_exist(full):
        EAL.delete_asset(full)
    a = AT.create_asset(name, path, cls, factory)
    if a is None:
        raise RuntimeError("create_asset(%s, %s) returned None" % (name, factory.get_class().get_name()))
    return a


def exists(path):
    return EAL.does_asset_exist(path)


def near(a, b, tol=0.01):
    return abs(a - b) <= tol


def cleanup():
    n = 0
    for a in _MADE_ACTORS:
        try:
            if a is not None and EAS.destroy_actor(a):
                n += 1
        except Exception:
            pass
    del _MADE_ACTORS[:]
    for a in EAS.get_all_level_actors():   # anything a probe spawned some other way
        if str(a.get_folder_path()) == PROBE_FOLDER:
            EAS.destroy_actor(a)
            n += 1
    if EAL.does_directory_exist(PROBE_DIR):
        EAL.delete_directory(PROBE_DIR)
    return n


def run_probes(only=None):
    out = {}
    for pid, fn in _PROBES:
        if only and pid not in only:
            continue
        t0 = time.time()
        try:
            with unreal.ScopedEditorTransaction("Claude probe " + pid):
                r = fn() or {}
            if not isinstance(r, dict):
                r = {"value": repr(r)}
            r.setdefault("ok", False)
        except Exception as e:
            r = {"ok": False, "error": "%s: %s" % (type(e).__name__, e), "trace": traceback.format_exc()[-800:]}
        r["ms"] = int((time.time() - t0) * 1000)
        out[pid] = json.loads(json.dumps(r, default=repr))
    removed = cleanup()
    return {"probes": out, "cleaned": removed, "leftover_dir": EAL.does_directory_exist(PROBE_DIR)}
