# SPDX-License-Identifier: MIT
"""The Claude Unreal Bridge on its stand-in editor, plus the asset import Unreal does for the pipeline.

    python3 harness/standin_unreal.py <unreal-connector-dir> <port> <seconds>

Import reads the real .glb the way Interchange did live on UE 5.8.3: one StaticMesh per mesh node, named after
the node, with the node's scale baked into its bounds (centimetres), a bare mesh given the default slot,
and one material asset per material, under <dest>/<file>/StaticMeshes and /Materials. Import must run on
the game thread, as in the editor.
The add-on command pipeline.fault makes the next import lose something, so the harness can prove the
judge says no:
  "drop_mesh"     one mesh never arrives
  "drop_tris"     a mesh comes in with fewer triangles
  "nanite"        Nanite on: LOD0 (the fallback) has fewer triangles than the source, which is intact (must pass)
  "drop_slot"     a mesh comes in with one material slot fewer
  "scale_m"       sizes stay in metres (a units bug)
  "no_materials"  no material assets are made
"""
import os
import runpy
import sys

CONNECTOR = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(CONNECTOR, "tests"))
sys.path.insert(0, os.path.join(CONNECTOR, "plugin", "ClaudeUnrealBridge", "Content", "Python"))

import fake_unreal as U          # noqa: E402
sys.modules["unreal"] = U
from asset_pipeline import glb   # noqa: E402

ASSETS = {}
FAULT = {"next": None}
SAVED = []   # directories the import script saved (it must, or the editor asks "Save Content?" on close)


class _Obj:
    def get_editor_property(self, k): return getattr(self, k)
    def set_editor_property(self, k, v): setattr(self, k, v)
    def get_name(self): return self._name


class MaterialInterface(_Obj):
    def __init__(self, name, path=""): self._name, self._path = name, path
    def get_path_name(self): return self._path


class StaticMaterial(_Obj):
    def __init__(self, slot, material=None): self.material_slot_name, self.material_interface = slot, material


class Box:
    def __init__(self, size):
        self.min = U.V(0, 0, 0)
        self.max = U.V(*size)


class MeshDescription:
    def __init__(self, tris): self._tris = tris
    def get_triangle_count(self): return self._tris


class NaniteSettings(_Obj):
    def __init__(self, enabled): self.enabled = enabled


class StaticMesh(_Obj):
    def __init__(self, name, tris, slots, size_cm, render_tris=None, nanite=False):
        self._name, self._tris, self._size = name, tris, size_cm
        self._render = tris if render_tris is None else render_tris
        self.nanite_settings = NaniteSettings(nanite)
        self.static_materials = [StaticMaterial(s) for s in slots]

    def use(self, materials):
        for sm in self.static_materials:
            sm.material_interface = materials.get(sm.material_slot_name)
    def get_num_triangles(self, lod): return self._render if lod == 0 else 0
    def get_static_mesh_description(self, lod): return MeshDescription(self._tris) if lod == 0 else None
    def get_bounding_box(self): return Box(self._size)


class AssetImportTask(_Obj):
    def __init__(self):
        self.filename = self.destination_path = ""
        self.automated = self.replace_existing = self.save = False
        self.imported_object_paths = []


class _AssetTools:
    def import_asset_tasks(self, tasks):
        U._game_thread_only("import_asset_tasks")
        for t in tasks:
            if not t.automated:
                raise RuntimeError("a non-automated import would open the import dialog")
            s = glb.summarize(t.filename)
            fault, FAULT["next"] = FAULT["next"], None
            # As seen live (UE 5.8.3): one static mesh per node, named after the node, scale baked in.
            nodes = s["nodes"][:-1] if fault == "drop_mesh" else s["nodes"]
            base = "%s/%s" % (t.destination_path, os.path.splitext(os.path.basename(t.filename))[0])
            # As seen live (UE 5.8.3): materials are created beside the meshes but not reported as imported; the
            # meshes' slots point at them. no_materials: the slots keep the engine default.
            mats = {} if fault == "no_materials" else {
                name: MaterialInterface(name, "%s/Materials/%s.%s" % (base, name, name)) for name in s["materials"]}
            for mi in mats.values():
                ASSETS[mi.get_path_name()] = mi
            for i, n in enumerate(nodes):
                m = s["meshes"][n["mesh"]]
                tris = m["triangles"] - (1 if fault == "drop_tris" and i == 0 else 0)
                slots = m["materials"] or ["-1"]            # Unreal gives a bare mesh the default material slot
                slots = slots[:-1] if fault == "drop_slot" and i == 0 else slots
                k = 1.0 if fault == "scale_m" else 100.0
                size = [d * k for d in n["dims"]]
                path = "%s/%s/StaticMeshes/%s" % (t.destination_path, os.path.splitext(os.path.basename(t.filename))[0], n["name"])
                # As seen live (UE 5.8.3): Nanite on by default; LOD0 is the fallback, a few % fewer triangles.
                nanite = fault == "nanite"
                mesh = StaticMesh(n["name"], tris, slots, size, render_tris=tris - tris // 20 if nanite else None, nanite=nanite)
                mesh.use(mats)
                ASSETS[path] = mesh
                t.imported_object_paths.append(path)
            U.CALLS.append("import %s -> %s" % (os.path.basename(t.filename), t.destination_path))


class AssetToolsHelpers:
    @staticmethod
    def get_asset_tools(): return _AssetTools()


class EditorAssetLibrary:
    @staticmethod
    def load_asset(path):
        U._game_thread_only("load_asset")
        return ASSETS.get(path)

    @staticmethod
    def list_assets(dest, recursive=True):
        return [p for p in ASSETS if p.startswith(dest + "/")]

    @staticmethod
    def save_directory(dest, only_if_is_dirty=True, recursive=True):
        U._game_thread_only("save_directory")
        SAVED.append(dest)
        return True


for _n in ("MaterialInterface", "StaticMesh", "AssetImportTask", "AssetToolsHelpers", "EditorAssetLibrary"):
    setattr(U, _n, globals()[_n])

import claude_unreal_bridge as bridge  # noqa: E402
bridge.register("pipeline.saved", lambda p: {"saved": list(SAVED)}, "directories saved", {})
bridge.register("pipeline.fault", lambda p: FAULT.update(next=p.get("kind")) or {"next": FAULT["next"]},
                "Make the next import lose something (harness only)", {"kind": "str"})
bridge.register("pipeline.assets", lambda p: {"assets": sorted(ASSETS)}, "Every asset imported so far")

sys.argv = [os.path.join(CONNECTOR, "tests", "host.py")] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name="__main__")
