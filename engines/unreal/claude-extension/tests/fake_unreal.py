# SPDX-License-Identifier: MIT
"""A stand-in for Unreal's `unreal` module: just enough of the editor API for the bridge's commands, so the
connector's plumbing (MCP -> socket -> game-thread pump -> reply) is tested without Unreal. It records what
the bridge asked the "editor" to do. It is not Unreal: the real calls are proven only in the editor."""
import os
import struct
import zlib


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


class EditorActorSubsystem:
    def get_all_level_actors(self): return list(LEVEL)
    def get_selected_level_actors(self): return LEVEL[:1]


class UnrealEditorSubsystem:
    def get_editor_world(self): return _World()


class LevelEditorSubsystem:
    def is_in_play_in_editor(self): return STATE["pie"]
    def editor_request_begin_play(self):
        CALLS.append("begin_play"); STATE["pie_wait"] = 3   # Play starts a few frames later, as in the editor
    def editor_play_simulate(self): CALLS.append("simulate"); STATE["pie_wait"] = 3
    def editor_request_end_play(self): CALLS.append("end_play"); STATE["pie"] = False
    def save_current_level(self): CALLS.append("save_level"); return True


_SUBS = {}


def get_editor_subsystem(cls):
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


LOGDIR = None


class Paths:
    @staticmethod
    def get_project_file_path(): return "C:/Unreal/DaedalusRealm/DaedalusRealm.uproject"
    @staticmethod
    def project_log_dir(): return LOGDIR
    @staticmethod
    def project_saved_dir(): return LOGDIR
    @staticmethod
    def convert_relative_path_to_full(p): return os.path.abspath(p)


class EditorLoadingAndSavingUtils:
    @staticmethod
    def save_dirty_packages(a, b): CALLS.append("save_dirty"); return True


def log(msg): pass
def log_warning(msg): pass
def log_error(msg): pass
