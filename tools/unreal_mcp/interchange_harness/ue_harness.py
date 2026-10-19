"""Editor side of the Interchange harness. Runs ONE stage per bridge call on the game thread.

NATIVE STATUS (first run 2026-10-19, UE 5.8, test folder): start/poll/add_sockets/facts/save and
set_nanite all ran live. Every property set is attempted, read back and reported, never assumed
applied. Known 5.8 facts: override_pipelines takes SoftObjectPath; StaticMesh.Sockets is protected
(use find_socket/add_socket); generate_lightmap_u_vs is not on common_meshes_properties (reported
in overrides.failed); a reimport ignores the override's build_nanite on an existing asset.

    import ue_harness as h
    h.start(plan)          # {"started": bool, "overrides": {...applied/failed...}}
    h.poll()               # {"done": bool, "done_objects": [...]}
    h.add_sockets(plan)    # from plan["sockets"]["sockets"] (sidecar), returns per-socket result
    h.set_nanite(plan)     # only if a reimport kept the old Nanite setting (see below)
    h.strip_simple_collision(plan)  # only for collision=false assets that still carry a hull
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
    if not o.get("generate_collision", True):
        # UE 5.8 (probed read-only 2026-10-19): mesh_pipeline.collision defaults True and
        # fallback_collision_type defaults CONVEX18DOP, which made a 24-vert hull on terrain_33.
        _try_set(mesh, "collision", False, report, "collision")
        _try_set(mesh, "fallback_collision_type", unreal.InterchangeMeshCollision.NONE, report, "fallback_collision")
        _try_set(mesh, "force_collision_primitive_generation", False, report, "force_collision")
    _try_set(common, "bake_meshes", o["bake_meshes"], report, "bake")
    # UE 5.8: generate_lightmap_u_vs lives on mesh_pipeline, not common_meshes_properties.
    _try_set(mesh, "generate_lightmap_u_vs", o["generate_lightmap_uvs"], report, "lightmap")
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
    # UE 5.8: OverridePipelines is an array of SoftObjectPath, not objects (native run 2026-10-19
    # raised "Cannot nativize InterchangeGenericAssetsPipeline as SoftObjectPath"). Keep the
    # transient pipeline alive in state so the soft path resolves during the async import.
    pipe = _pipeline(plan, report)
    st["pipeline"] = pipe
    params.override_pipelines = [unreal.SoftObjectPath(pipe.get_path_name())]
    report["pipeline_path"] = pipe.get_path_name()
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


def _sockets(mesh, names=()):
    """UE 5.8 marks StaticMesh.Sockets protected from Python (native run 2026-10-19), so read
    through the public API: get_sockets_by_tag("") plus find_socket for each expected name."""
    out = {}
    try:
        for s in mesh.get_sockets_by_tag("") or []:
            out[str(s.get_editor_property("socket_name"))] = s
    except Exception:
        pass
    for n in names:
        s = mesh.find_socket(n)
        if s is not None:
            out[n] = s
    return out


def _vec(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]


def _rot(r):
    return [round(r.pitch, 3), round(r.yaw, 3), round(r.roll, 3)]


def add_sockets(plan):
    """Add sidecar sockets after import. A socket that already exists natively (stock Interchange
    imports SOCKET_ empties) is KEPT; by default (plan option sidecar_rotation, opt out with
    overrides {"sidecar_rotation": False}) its relative_rotation is set from the sidecar, but only
    when the native position matches the sidecar within 0.5 cm. Native and sidecar rotations are
    logged in the result as evidence."""
    import harness_core as hc
    mesh = _mesh(plan)
    if mesh is None:
        return {"error": "mesh missing"}
    mesh.modify()  # mark for transaction/dirty BEFORE the sockets change (review 48565)
    existing = _sockets(mesh, [s["name"] for s in plan["sockets"]["sockets"]])
    rot_wins = plan["options"].get("sidecar_rotation", True)
    out = []
    for s in plan["sockets"]["sockets"]:
        if s["name"] in existing:
            sock = existing[s["name"]]
            nl = _vec(sock.get_editor_property("relative_location"))
            nr = _rot(sock.get_editor_property("relative_rotation"))
            e = {"name": s["name"], "native_location_cm": nl, "native_rotation_pyr": nr,
                 "sidecar_location_cm": s["location_cm"], "sidecar_rotation_pyr": s["rotation_pyr"],
                 "position_ok": hc.socket_position_ok(nl, s["location_cm"])}
            if not rot_wins:
                e["result"] = "kept existing (sidecar_rotation opted out)"
            elif not e["position_ok"]:
                e["result"] = "kept existing; rotation NOT applied: native position differs from sidecar by more than 0.5 cm"
            else:
                p, y, r = s["rotation_pyr"]
                sock.set_editor_property("relative_rotation", unreal.Rotator(roll=r, pitch=p, yaw=y))
                e["rotation_after_pyr"] = _rot(sock.get_editor_property("relative_rotation"))
                e["result"] = "kept existing; rotation from sidecar"
            out.append(e)
            continue
        sock = unreal.StaticMeshSocket(mesh)
        sock.set_editor_property("socket_name", s["name"])
        sock.set_editor_property("relative_location", unreal.Vector(*s["location_cm"]))
        p, y, r = s["rotation_pyr"]
        sock.set_editor_property("relative_rotation", unreal.Rotator(roll=r, pitch=p, yaw=y))
        sock.set_editor_property("relative_scale", unreal.Vector(*s["scale"]))
        mesh.add_socket(sock)
        out.append({"name": s["name"], "result": "added" if mesh.find_socket(s["name"]) is not None else "add failed"})
    return {"sockets": out}


def set_nanite(plan):
    """Apply plan build_nanite to an EXISTING mesh. Native run 2026-10-19: a reimport kept the
    asset's Nanite setting and ignored the override pipeline's build_nanite, so evaluate()
    reported nanite_as_planned=False; this stage fixes it and rebuilds (modify() first)."""
    mesh = _mesh(plan)
    if mesh is None:
        return {"error": "mesh missing"}
    ns = mesh.get_editor_property("nanite_settings")
    before = {"enabled": ns.get_editor_property("enabled"), "tris_lod0": mesh.get_num_triangles(0)}
    want = bool(plan["options"]["build_nanite"])
    if before["enabled"] != want:
        ns.set_editor_property("enabled", want)
        mesh.modify()
        mesh.set_editor_property("nanite_settings", ns)
    return {"before": before, "after": {"enabled": mesh.get_editor_property("nanite_settings").get_editor_property("enabled"),
                                        "tris_lod0": mesh.get_num_triangles(0)}}


def _simple_count(mesh):
    """All simple collision primitives in agg_geom: box, sphere, capsule, convex, tapered capsule.
    Native run 2026-10-19: StaticMeshEditorSubsystem.get_simple_collision_count() returned 0 on
    terrain_33 while it had 1 convex hull (it excludes convex), so it is not used here."""
    body = mesh.get_editor_property("body_setup")
    if body is None:
        return 0
    agg = body.get_editor_property("agg_geom")
    n = 0
    for k in ("box_elems", "sphere_elems", "sphyl_elems", "convex_elems", "tapered_capsule_elems"):
        try:
            n += len(agg.get_editor_property(k))
        except Exception:
            pass
    return n


def strip_simple_collision(plan):
    """Remove all simple collision when the plan says collision=false (existing assets, e.g. the
    terrain_33 auto hull from before this fix). Refuses when the plan wants collision."""
    if plan["options"].get("generate_collision", True):
        return {"error": "plan wants collision; refusing to strip"}
    mesh = _mesh(plan)
    if mesh is None:
        return {"error": "mesh missing"}
    before = _simple_count(mesh)
    if before:
        mesh.modify()
        unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).remove_collisions(mesh)
    return {"before": before, "after": _simple_count(mesh)}


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
        "sockets": [{"name": n, "location_cm": _vec(s.get_editor_property("relative_location")), "rotation_pyr": _rot(s.get_editor_property("relative_rotation"))}
                    for n, s in sorted(_sockets(mesh, [x["name"] for x in plan["sockets"]["sockets"]]).items())],
        "collision": {"convex": len(agg.get_editor_property("convex_elems")) if agg else 0,
                      "hulls": [_convex(c) for c in agg.get_editor_property("convex_elems")] if agg else []},
        "simple_collision_count": _simple_count(mesh),
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