# SPDX-License-Identifier: MIT
"""A stand-in for Unreal's `unreal` module: just enough of the editor API for the bridge's commands, so the
connector's plumbing (MCP -> socket -> game-thread pump -> reply) is tested without Unreal. It records what
the bridge asked the "editor" to do. It is not Unreal: the real calls are proven only in the editor."""
import os
import struct
import threading
import zlib

# Unreal's rule: its API may only be touched on the game thread. The stand-in enforces it, so a bridge that
# reads the API from a background thread fails here the way it fails in the editor (found live on UE 5.8.3:
# "Paths: Attempted to access Unreal API from outside the main game thread").
GAME_THREAD = [None]   # host.py sets this to the thread that pumps the bridge


def _game_thread_only(what):
    if GAME_THREAD[0] is not None and threading.get_ident() != GAME_THREAD[0]:
        raise RuntimeError("%s: Attempted to access Unreal API from outside the main game thread." % what)


class V:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z


class R:
    def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
        self.pitch, self.yaw, self.roll = pitch, yaw, roll


class _Class:
    def __init__(self, n): self.n = n
    def get_name(self): return self.n


class ActorComponent:
    def __init__(self, name): self.name = name
    def get_name(self): return self.name
    def get_class(self): return _Class(type(self).__name__)


class StaticMeshComponent(ActorComponent):
    def get_editor_property(self, k): return None
    def get_materials(self): return []


class Actor:
    def __init__(self, label, cls, folder, loc):
        self.label, self.cls, self.folder, self.loc = label, cls, folder, loc
        self.comps = [StaticMeshComponent(label + "_Mesh")]
    def get_actor_label(self): return self.label
    def get_name(self): return self.label.replace(" ", "_")
    def get_class(self): return _Class(self.cls)
    def get_folder_path(self): return self.folder
    def get_actor_location(self): return V(*self.loc)
    def get_actor_rotation(self): return R()
    def get_actor_scale3d(self): return V(1, 1, 1)
    def get_actor_bounds(self, _only_colliding): return V(*self.loc), V(100, 100, 100)
    def get_components_by_class(self, _cls): return self.comps


LEVEL = [Actor("chunk_0_2_-6", "StaticMeshActor", "Daedalus/world-zero", (1000, 2000, 3000)),
         Actor("Daedalus World (live) - World Zero", "DaedalusWorldActor", "Daedalus/world-zero", (0, 0, 0)),
         Actor("Sky", "SkyAtmosphere", "", (0, 0, 0))]
CALLS = []
STATE = {"pie": False, "pie_wait": 0}


class _World:
    def get_path_name(self): return "/Game/Daedalus/DaedalusWorld.DaedalusWorld"


class SceneCaptureComponent2D(ActorComponent):
    def __init__(self, name):
        super().__init__(name)
        self.props = {}
    def set_editor_property(self, k, v): self.props[k] = v
    def capture_scene(self): CALLS.append("capture_scene")


class SceneCaptureSource:
    SCS_FINAL_COLOR_LDR = "SCS_FINAL_COLOR_LDR"


class SceneCapture2D(Actor):
    pass


class _CaptureActor(Actor):
    def __init__(self):
        super().__init__("SceneCapture2D", "SceneCapture2D", "", (0, 0, 0))
        self.comp = SceneCaptureComponent2D("CaptureComponent2D")
    def get_component_by_class(self, cls): return self.comp


class EditorActorSubsystem:
    def get_all_level_actors(self):
        CALLS.append("editor_actors" + ("_in_pie" if STATE["pie"] else ""))   # in Play the real editor logs an error here
        return list(LEVEL)
    def get_selected_level_actors(self):
        CALLS.append("editor_selected" + ("_in_pie" if STATE["pie"] else ""))
        return LEVEL[:1]
    def spawn_actor_from_class(self, cls, loc, rot=None):
        a = _CaptureActor() if cls is SceneCapture2D else Actor(cls.__name__, cls.__name__, "", (loc.x, loc.y, loc.z))
        LEVEL.append(a); CALLS.append("spawn " + cls.__name__)
        return a
    def destroy_actor(self, a):
        if a in LEVEL:
            LEVEL.remove(a)
        CALLS.append("destroy " + a.get_actor_label())
        return True


class ScopedEditorTransaction:
    """One undo step; the stand-in records that it opened and closed."""
    def __init__(self, description): self.description = description
    def __enter__(self): CALLS.append("transaction begin " + self.description); return self
    def __exit__(self, *exc): CALLS.append("transaction end"); return False


class RenderingLibrary:
    @staticmethod
    def create_render_target2d(world, w, h): return {"w": w, "h": h}
    @staticmethod
    def export_render_target(world, rt, out_dir, name):
        with open(os.path.join(out_dir, name + ".png"), "wb") as f:
            f.write(_png(rt["w"] // 64 or 1, rt["h"] // 64 or 1))


class UnrealEditorSubsystem:
    def get_editor_world(self): return _World()
    def get_game_world(self): return _World() if STATE["pie"] else None
    def get_level_viewport_camera_info(self): return V(-500, -500, 800), R(-30, 45, 0)


class GameplayStatics:
    @staticmethod
    def get_all_actors_of_class(world, cls):
        CALLS.append("game_actors")
        return list(LEVEL)


class LevelEditorSubsystem:
    def is_in_play_in_editor(self): return STATE["pie"]
    def editor_request_begin_play(self):
        CALLS.append("begin_play"); STATE["pie_wait"] = 3   # Play starts a few frames later, as in the editor
    def editor_play_simulate(self): CALLS.append("simulate"); STATE["pie_wait"] = 3
    def editor_request_end_play(self): CALLS.append("end_play"); STATE["pie"] = False
    def save_current_level(self): CALLS.append("save_level"); return True


_SUBS = {}


def get_editor_subsystem(cls):
    _game_thread_only(cls.__name__)
    return _SUBS.setdefault(cls, cls())


def tick():
    """The fake editor's frame: Play comes up after its wait, pending screenshots get written."""
    if STATE["pie_wait"] > 0:
        STATE["pie_wait"] -= 1
        if STATE["pie_wait"] == 0:
            STATE["pie"] = True
    for path, frames in list(_SHOTS.items()):
        if frames <= 0:
            with open(path, "wb") as f:
                f.write(_png(4, 3))
            del _SHOTS[path]
        else:
            _SHOTS[path] = frames - 1


def _png(w, h):
    raw = b"".join(b"\x00" + b"\x80\x40\x20" * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


_SHOTS = {}
NESTED_TICK = None   # host.py points this at the bridge's pump


class AutomationLibrary:
    @staticmethod
    def take_high_res_screenshot(w, h, path):
        CALLS.append("screenshot %dx%d" % (w, h)); _SHOTS[path] = 2   # written two frames later
        # The real editor ticks Slate inside this call, which re-enters the bridge's pump while the
        # screenshot command's generator is running (found on Richmond's PC: "generator already executing").
        if NESTED_TICK is not None:
            NESTED_TICK()


class SystemLibrary:
    @staticmethod
    def get_engine_version(): return "5.8.3-fake"
    @staticmethod
    def execute_console_command(world, cmd): CALLS.append("console " + cmd)


LOGDIR = None


class Paths:
    @staticmethod
    def get_project_file_path(): _game_thread_only("Paths"); return "C:/Unreal/DaedalusRealm/DaedalusRealm.uproject"
    @staticmethod
    def project_log_dir(): return LOGDIR
    @staticmethod
    def project_saved_dir(): return LOGDIR
    @staticmethod
    def convert_relative_path_to_full(p): return os.path.abspath(p)
    @staticmethod
    def project_dir(): _game_thread_only("Paths"); return LOGDIR


class EditorLoadingAndSavingUtils:
    @staticmethod
    def save_dirty_packages(a, b): CALLS.append("save_dirty"); return True


def log(msg): pass
def log_warning(msg): pass
def log_error(msg): pass
