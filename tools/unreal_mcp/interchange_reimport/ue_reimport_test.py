"""Interchange import -> save -> reimport identity test, run inside a live UE 5.8 editor.

Call the stages one at a time over the editor bridge (one GLB per call). The import is
asynchronous, so a stage never blocks the game thread waiting for it:

    import ue_reimport_test as t
    t.start_import(test_root, source_glb)        # returns {"started": bool}; started != done
    t.poll()                                      # until {"done": True}; then inspect results
    t.facts(test_root, asset)                     # mesh / tris / bounds / materials / collision / socket
    t.save_test_root(test_root)                   # saves ONLY dirty packages under test_root
    t.start_reimport(test_root, asset, source_glb) # same source path, new bytes
    t.poll(); t.facts(...); t.compare_identity()  # same UObject, not a new one

Rules from Epic primary sources (link 48194): reimport/import True only means started;
completion is OnAssetsImportDone; Done is not success, so inspect the results and compare
object identities; imports are not undoable, so use a test-only content folder.
Stock Interchange pipelines are used (no override), so the facts describe the default.
"""
import sys
import time

import unreal

_STATE_KEY = "_ueb_interchange_reimport_state"


def _state():
    st = getattr(sys.modules[__name__], _STATE_KEY, None)
    if st is None:
        st = {}
        setattr(sys.modules[__name__], _STATE_KEY, st)
    return st


def _dirty():
    u = unreal.EditorLoadingAndSavingUtils
    return [p.get_name() for p in u.get_dirty_content_packages()] + [p.get_name() for p in u.get_dirty_map_packages()]


def _on_done(objects):
    st = _state()
    st["done"] = True
    st["done_at"] = time.time()
    st["done_objects"] = [o.get_path_name() for o in (objects or []) if o]


def _start(test_root, source_glb, reimport_obj=None):
    st = _state()
    for k in ("done", "done_objects", "started", "error"):
        st.pop(k, None)
    st["source"] = source_glb
    st["t0"] = time.time()
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    src = unreal.InterchangeManager.create_source_data(source_glb)
    params = unreal.ImportAssetParameters()
    params.is_automated = True
    if reimport_obj is not None:
        params.reimport_asset = reimport_obj
    cb = params.on_assets_import_done
    for binder in ("bind_callable", "add_callable"):
        if hasattr(cb, binder):
            getattr(cb, binder)(_on_done)
            st["callback"] = binder
            break
    st["params"] = params  # keep the delegate alive
    st["started"] = bool(mgr.import_asset(test_root, src, params))
    return {"started": st["started"], "callback": st.get("callback"), "dirty_before": None}


def start_import(test_root, source_glb):
    if unreal.EditorAssetLibrary.does_directory_exist(test_root):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        if ar.get_assets_by_path(test_root, recursive=True):
            return {"started": False, "error": "test_root not empty; refusing"}
    return _start(test_root, source_glb)


def _mesh(test_root, asset):
    # Interchange nests output as <root>/<asset>/StaticMeshes/<asset>; find the StaticMesh by name.
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    for a in ar.get_assets_by_path(test_root, recursive=True):
        if str(a.asset_name) == asset and str(a.asset_class_path.asset_name) == "StaticMesh":
            return unreal.EditorAssetLibrary.load_asset(str(a.package_name))
    return None


def start_reimport(test_root, asset, source_glb):
    mesh = _mesh(test_root, asset)
    if mesh is None:
        return {"started": False, "error": "asset missing"}
    _state()["before_obj"] = mesh
    return _start(test_root, source_glb, reimport_obj=mesh)


def poll():
    st = _state()
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    out = {"started": st.get("started"), "done": bool(st.get("done")), "elapsed_s": round(time.time() - st.get("t0", time.time()), 3)}
    if st.get("done"):
        out["done_objects"] = st.get("done_objects")
    obj = st.get("before_obj")
    if obj is not None:
        out["being_imported"] = bool(mgr.is_object_being_imported(obj))
    return out


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # report, never hide
        return {"error": repr(exc)} if default is None else default


def _convex_extent(elem):
    """KConvexElem hides VertexData/ElemBox from Python in UE 5.8; read them from export_text()."""
    import re
    txt = elem.export_text()
    vd = re.search(r"VertexData=\((.*?)\)\s*,\s*IndexData", txt)
    pts = [tuple(float(v) for v in p) for p in re.findall(r"X=([-\d.eE+]+),Y=([-\d.eE+]+),Z=([-\d.eE+]+)", vd.group(1))] if vd else []
    return {"verts": len(pts), "extent_cm": [round(max(a) - min(a), 3) for a in zip(*pts)] if pts else None}


def facts(test_root, asset):
    mesh = _mesh(test_root, asset)
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    inv = sorted("%s [%s]" % (a.package_name, a.asset_class_path.asset_name) for a in ar.get_assets_by_path(test_root, recursive=True))
    if mesh is None:
        return {"mesh": None, "inventory": inv, "dirty": _dirty()}
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    box = mesh.get_bounding_box()
    mn, mx = box.min, box.max
    sockets = []
    # StaticMesh.Sockets is protected from Python in 5.8; read via the public API (see PR #203).
    for s in _safe(lambda: list(mesh.get_sockets_by_tag("") or []), []):
        loc = s.get_editor_property("relative_location")
        sockets.append({"name": str(s.get_editor_property("socket_name")), "location_cm": [loc.x, loc.y, loc.z]})
    mats = []
    for m in mesh.get_editor_property("static_materials"):
        mi = m.get_editor_property("material_interface")
        mats.append({"slot": str(m.get_editor_property("material_slot_name")), "material": mi.get_path_name() if mi else None})
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom") if body else None
    convex = []
    if agg:
        for c in agg.get_editor_property("convex_elems"):
            convex.append(_convex_extent(c))
    data = {
        "path": mesh.get_path_name(),
        "class": mesh.get_class().get_name(),
        "tris_lod0": _safe(lambda: mesh.get_num_triangles(0)),
        "verts_lod0": _safe(lambda: sms.get_number_verts(mesh, 0)),
        "lods": _safe(lambda: mesh.get_num_lods()),
        "bounds_min_cm": [mn.x, mn.y, mn.z],
        "bounds_max_cm": [mx.x, mx.y, mx.z],
        "dims_cm": [mx.x - mn.x, mx.y - mn.y, mx.z - mn.z],
        "materials": mats,
        "sockets": sockets,
        "collision": {
            "body_setup": bool(body),
            "convex": len(convex),
            "convex_elems": convex,
            "box": len(agg.get_editor_property("box_elems")) if agg else 0,
            "sphere": len(agg.get_editor_property("sphere_elems")) if agg else 0,
            "capsule": len(agg.get_editor_property("sphyl_elems")) if agg else 0,
            "subsystem_convex_count": _safe(lambda: sms.get_convex_collision_count(mesh)),
            "subsystem_simple_count": _safe(lambda: sms.get_simple_collision_count(mesh)),
            "trace_flag": str(_safe(lambda: body.get_editor_property("collision_trace_flag"))) if body else None,
        },
        "nanite": _safe(lambda: mesh.get_editor_property("nanite_settings").get_editor_property("enabled")),
        "inventory": inv,
        "dirty": _dirty(),
    }
    return data


def compare_identity():
    st = _state()
    before = st.get("before_obj")
    if before is None:
        return {"error": "no reimport baseline"}
    after = unreal.EditorAssetLibrary.load_asset(before.get_path_name())
    return {"before": before.get_path_name(), "after": after.get_path_name() if after else None,
            "same_uobject": bool(after is not None and after == before)}


def save_test_root(test_root):
    dirty = _dirty()
    prefix = test_root.rstrip("/") + "/"
    mine = [p for p in dirty if p.startswith(prefix)]
    other = [p for p in dirty if not p.startswith(prefix)]
    if other:
        return {"saved": False, "error": "dirty packages outside test_root; refusing", "other": other}
    pkgs = [unreal.load_package(p) for p in mine]
    ok = bool(unreal.EditorLoadingAndSavingUtils.save_packages(pkgs, True)) if pkgs else False
    return {"saved": ok, "packages": mine, "dirty_after": _dirty()}