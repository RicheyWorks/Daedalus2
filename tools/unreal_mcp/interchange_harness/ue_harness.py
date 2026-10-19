"""Editor side of the Interchange harness. Runs ONE stage per bridge call on the game thread.

NATIVE STATUS: the start/poll/facts/save stages reuse the pattern that passed live in item e
(PR197). The pipeline-override and add_sockets stages are AUTHORED, NOT YET RUN natively:
every property set is attempted, read back and reported, never assumed applied.

    import ue_harness as h
    h.start(plan)          # {"started": bool, "overrides": {...applied/failed...}}
    h.poll()               # {"done": bool, "done_objects": [...]}
    h.add_sockets(plan)    # from plan["sockets"]["sockets"] (sidecar), returns per-socket result
    h.facts(plan)          # raw facts for harness_core.evaluate
    h.save(plan)           # only dirty packages under plan["destination"], up to 3 passes
"""
import re
import sys
import time

import unreal

_KEY = "_ueb_interchange_harness_state"


def _st():
    mod = sys.modules[__name__]
    if not hasattr(mod, _KEY):
        setattr(mod, _KEY, {})
    return getattr(mod, _KEY)


def _dirty():
    u = unreal.EditorLoadingAndSavingUtils
    return [p.get_name() for p in u.get_dirty_content_packages()] + [p.get_name() for p in u.get_dirty_map_packages()]


def _try_set(obj, prop, value, report, label):
    try:
        obj.set_editor_property(prop, value)
        report[label] = {"prop": prop, "set": value, "readback": obj.get_editor_property(prop)}
        return True
    except Exception as exc:
        report.setdefault("failed", []).append("%s.%s: %r" % (label, prop, exc)[:200])
        return False


def _pipeline(plan, report):
    """Stock generic pipeline with only the plan's options changed. Unknown names are reported."""
    p = unreal.InterchangeGenericAssetsPipeline()
    o = plan["options"]
    mesh = p.get_editor_property("mesh_pipeline")
    mat = p.get_editor_property("material_pipeline")
    common = p.get_editor_property("common_meshes_properties")
    _try_set(mesh, "build_nanite", o["build_nanite"], report, "nanite")
    _try_set(mesh, "import_collision_according_to_mesh_name", o["collision_from_ucx"], report, "ucx")
    _try_set(common, "bake_meshes", o["bake_meshes"], report, "bake")
    _try_set(common, "generate_lightmap_u_vs", o["generate_lightmap_uvs"], report, "lightmap")
    _try_set(mat, "import_materials", o["import_materials"], report, "import_materials")
    # 48194: reuse-existing and create-new are separate; set each on its own, report both.
    for name in ("reuse_existing_materials", "search_existing_materials"):
        if _try_set(mat, name, o["reuse_existing_materials"], report, "reuse_existing"):
            break
    _try_set(mat, "create_new_materials", o["create_new_materials"], report, "create_new")
    return p


def _on_done(objects):
    st = _st()
    st["done"] = True
    st["done_objects"] = [o.get_path_name() for o in (objects or []) if o]


def start(plan, reimport_obj=None):
    st = _st()
    for k in ("done", "done_objects"):
        st.pop(k, None)
    st["t0"] = time.time()
    report = {}
    params = unreal.ImportAssetParameters()
    params.is_automated = True
    params.override_pipelines = [_pipeline(plan, report)]
    if reimport_obj is not None:
        params.reimport_asset = reimport_obj
    params.on_assets_import_done.bind_callable(_on_done)
    st["params"] = params
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    src = unreal.InterchangeManager.create_source_data(plan["source"])
    started = bool(mgr.import_asset(plan["destination"], src, params))
    return {"started": started, "overrides": report}


def poll():
    st = _st()
    return {"done": bool(st.get("done")), "done_objects": st.get("done_objects"), "elapsed_s": round(time.time() - st.get("t0", time.time()), 3)}


def _mesh(plan):
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    for a in ar.get_assets_by_path(plan["destination"], recursive=True):
        if str(a.asset_name) == plan["asset"] and str(a.asset_class_path.asset_name) == "StaticMesh":
            return unreal.EditorAssetLibrary.load_asset(str(a.package_name))
    return None


def _convex(elem):
    txt = elem.export_text()
    vd = re.search(r"VertexData=\((.*?)\)\s*,\s*IndexData", txt)
    pts = [tuple(float(v) for v in p) for p in re.findall(r"X=([-\d.eE+]+),Y=([-\d.eE+]+),Z=([-\d.eE+]+)", vd.group(1))] if vd else []
    return {"verts": len(pts), "extent_cm": [round(max(a) - min(a), 3) for a in zip(*pts)] if pts else None}


def add_sockets(plan):
    mesh = _mesh(plan)
    if mesh is None:
        return {"error": "mesh missing"}
    mesh.modify()  # mark for transaction/dirty BEFORE the sockets change (review 48565)
    existing = {str(s.get_editor_property("socket_name")) for s in mesh.get_editor_property("sockets")}
    out = []
    for s in plan["sockets"]["sockets"]:
        if s["name"] in existing:
            out.append({"name": s["name"], "result": "kept existing"})
            continue
        sock = unreal.StaticMeshSocket(mesh)
        sock.set_editor_property("socket_name", s["name"])
        sock.set_editor_property("relative_location", unreal.Vector(*s["location_cm"]))
        p, y, r = s["rotation_pyr"]
        sock.set_editor_property("relative_rotation", unreal.Rotator(roll=r, pitch=p, yaw=y))
        sock.set_editor_property("relative_scale", unreal.Vector(*s["scale"]))
        socks = list(mesh.get_editor_property("sockets")) + [sock]
        mesh.set_editor_property("sockets", socks)
        out.append({"name": s["name"], "result": "added"})
    return {"sockets": out}


def facts(plan):
    mesh = _mesh(plan)
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    inv = sorted("%s [%s]" % (a.package_name, a.asset_class_path.asset_name) for a in ar.get_assets_by_path(plan["destination"], recursive=True))
    if mesh is None:
        return {"mesh": None, "mesh_found": False, "inventory": inv, "dirty": _dirty()}
    box = mesh.get_bounding_box()
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom") if body else None
    return {
        "mesh_found": True,
        "path": mesh.get_path_name(),
        "tris_lod0": mesh.get_num_triangles(0),
        "bounds_min_cm": [box.min.x, box.min.y, box.min.z],
        "bounds_max_cm": [box.max.x, box.max.y, box.max.z],
        "materials": [{"slot": str(m.get_editor_property("material_slot_name")),
                       "material": (m.get_editor_property("material_interface").get_path_name() if m.get_editor_property("material_interface") else None)}
                      for m in mesh.get_editor_property("static_materials")],
        "sockets": [{"name": str(s.get_editor_property("socket_name"))} for s in mesh.get_editor_property("sockets")],
        "collision": {"convex": len(agg.get_editor_property("convex_elems")) if agg else 0,
                      "hulls": [_convex(c) for c in agg.get_editor_property("convex_elems")] if agg else []},
        "nanite": mesh.get_editor_property("nanite_settings").get_editor_property("enabled"),
        "inventory": inv,
        "dirty": _dirty(),
    }


def save(plan):
    prefix = plan["destination"].rstrip("/") + "/"
    passes, saved = 0, []
    while passes < 3:
        dirty = _dirty()
        other = [p for p in dirty if not p.startswith(prefix)]
        if other:
            return {"saved": False, "error": "dirty outside destination; refusing", "other": other, "passes": passes}
        mine = [p for p in dirty if p.startswith(prefix)]
        if not mine:
            break
        passes += 1
        ok = bool(unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(p) for p in mine], True))
        saved.append({"pass": passes, "packages": mine, "ok": ok})
        if not ok:
            break
    return {"saved": all(s["ok"] for s in saved) if saved else False, "passes": passes, "detail": saved, "dirty_after": _dirty()}