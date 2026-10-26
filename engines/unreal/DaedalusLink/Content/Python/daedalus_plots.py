# SPDX-License-Identifier: MIT
"""Lay down the lands (Richey 2026-10-13: "push hard to get the amount of material in each world complete so that we
can hurry up to deploy the NFTs... get everything laid down in each realm then polish").

    import daedalus_plots as P
    P.plan(rings=6)      # which cells get a plot: every cell within `rings` of the hub that no estate or the hub holds
    P.apply(rings=6)     # spawn one plot per free cell: a 92 m ground slab + the deed number; idempotent by label
    P.remove()           # take every plot out again (editor only, no deletes on disk)

A plot is a StaticMeshActor (engine cube scaled to LAND_M x LAND_M x 2 m) labelled Land_<n> in folder
Lands/District_<d>, with a TextRenderActor showing the number, at the ADR-065 cell centre at the hub's ground height.
Estates already placed by daedalus_layout.spiral_apply() are read back from the islands' positions so their cells are
skipped. Pure planning (free cells, world positions) is testable without the editor.
"""
import math

import daedalus_land_grid as G

LAND_M = 92.0        # launch size of a land (ADR-065 rule 8)
SLAB_M = 12.0        # a plot is a solid floating slab of ground (the asteroid's pieces), not a sheet
CUBE = "/Engine/BasicShapes/Cube.Cube"        # 100 cm a side
FOLDER = "Lands"


def cells_within(rings):
    """Every cell number whose Chebyshev distance from the hub is <= rings, in spiral order."""
    out = []
    for n in range(G.COUNT):
        x, y = G.cell(n)
        if max(abs(x - G.HUB), abs(y - G.HUB)) <= rings:
            out.append(n)
        elif max(abs(x - G.HUB), abs(y - G.HUB)) > rings + 1:
            break
    return out


def taken_by_estates(estates):
    """estates: iterable of (x, y, size). Every cell number they cover."""
    used = set()
    for x, y, s in estates:
        cells = []
        if G.estate(x, y, s, cells) >= 0:
            used.update(cells)
    return used


def plan(rings=6, estates=(), hub_cells=(), hub_cm=(0.0, 0.0), ground_cm=0.0, pitch_m=G.PITCH_M):
    """[{n, cell, district, at: (x, y, z) cm}] for every free cell within `rings`."""
    used = taken_by_estates(estates) | set(hub_cells)
    out = []
    for n in cells_within(rings):
        if n in used:
            continue
        x, y = G.cell(n)
        mx, my = (x - G.HUB) * pitch_m, (y - G.HUB) * pitch_m
        out.append({"n": n, "cell": (x, y), "district": G.district(n),
                    "at": (hub_cm[0] + mx * 100.0, hub_cm[1] + my * 100.0, ground_cm)})
    return out


# ---- editor side ----------------------------------------------------------------------------------------------

def _labels_cache(sub=None):
    """{label} of every actor; a fresh scan each call (cheap enough: ~12k actors in ~50 ms)."""
    import unreal
    sub = sub or unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return {a.get_actor_label() for a in sub.get_all_level_actors()}


def save_packages_proven(pkgs):
    """Save these packages and prove each by its file mtime; raises naming any that was not written."""
    import os
    import time
    import unreal
    t0 = time.time()
    ok = unreal.EditorLoadingAndSavingUtils.save_packages(list(pkgs), only_dirty=False)
    stale = []
    for pk in pkgs:
        fn = unreal.Paths.convert_relative_path_to_full(unreal.PackageTools.package_name_to_filename(pk.get_name(), ".umap"))
        if not os.path.exists(fn) or os.path.getmtime(fn) < t0 - 1.0:
            stale.append(pk.get_name())
    if not ok or stale:
        raise RuntimeError("not written: ok=%s %s" % (ok, stale))
    return round(time.time() - t0, 1)


def save_world():
    """Save the persistent level explicitly and prove it by the .umap mtime (save_dirty_packages can clear the
    dirty flag without writing, 2026-10-13). Returns the seconds the save took."""
    import os
    import time
    import unreal
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    pk = w.get_outermost()
    fn = unreal.Paths.convert_relative_path_to_full(unreal.PackageTools.package_name_to_filename(pk.get_name(), ".umap"))
    t0 = time.time()
    ok = unreal.EditorLoadingAndSavingUtils.save_packages([pk], only_dirty=False)
    if not ok or not os.path.exists(fn) or os.path.getmtime(fn) < t0 - 1.0:
        # 02:20: ok=False while the editor's own autosave ("Auto-saving out of date packages") was running; one retry
        time.sleep(8.0)
        t0 = time.time()
        ok = unreal.EditorLoadingAndSavingUtils.save_packages([pk], only_dirty=False)
        if not ok or not os.path.exists(fn) or os.path.getmtime(fn) < t0 - 1.0:
            raise RuntimeError("the persistent level was not written (twice; autosave running?): ok=%s %s" % (ok, fn))
    return round(time.time() - t0, 1)

def _editor_inputs():
    """(estates, hub cells, hub centre cm, ground z cm) from the live level, via daedalus_layout's planner."""
    import unreal
    import daedalus_layout as L
    hub_cm, hub_size = L._hub()
    hub_cells = {G.number(x, y) for x, y in L.hub_cells(hub_size[0], hub_size[1])}
    sp = L.spiral_plan()
    estates = {(tuple(r["cell"]), r["estate"]) for r in sp["plan"]}
    ground = None
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in sub.get_all_level_actors():
        if a.get_class().get_name() == "PlayerStart":
            ground = a.get_actor_location().z - 100.0
            break
    if ground is None:
        ground = 0.0
    return [(c[0], c[1], s) for c, s in estates], hub_cells, hub_cm, ground


def _prefix(realm):
    return "Land_" if realm == "WORLD-ZERO" else "Land_%s_" % realm.replace("-", "")


def _existing(realm="WORLD-ZERO"):
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    import re
    pat = re.compile(r"^%s\d+(_Sign)?$" % re.escape(_prefix(realm)))
    return {a.get_actor_label(): a for a in sub.get_all_level_actors() if pat.match(a.get_actor_label())}


def lay_one(realm, n, at, district, size=1, cube=None, sub=None):
    """One plot: a LAND_M*size slab labelled <prefix><n> with its sign, tagged Land/Realm/Deed/District. `at` is the
    centre of the south-west cell in cm; an estate of size>1 is centred on its block (ADR-065). No check for an
    existing label: callers do that."""
    import unreal
    sub = sub or unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube = cube or unreal.load_asset(CUBE)
    pre = _prefix(realm)
    folder = FOLDER if realm == "WORLD-ZERO" else "Realms/%s/Lands" % realm
    x, y, z = at
    if size > 1:   # the block's centre is (size-1)/2 cells north-east of the south-west cell
        x += (size - 1) / 2.0 * G.PITCH_M * 100.0
        y += (size - 1) / 2.0 * G.PITCH_M * 100.0
    slab = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z - SLAB_M * 50.0))
    slab.static_mesh_component.set_static_mesh(cube)
    slab.set_actor_scale3d(unreal.Vector(LAND_M * size, LAND_M * size, SLAB_M))
    slab.set_actor_label("%s%d" % (pre, n))
    slab.set_folder_path("%s/District_%d" % (folder, district))
    slab.tags = [unreal.Name("Land"), unreal.Name("Realm:%s" % realm), unreal.Name("Deed:%d" % n), unreal.Name("District:%d" % district)]
    txt = sub.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(x, y, z + 300.0), unreal.Rotator(90.0, 0.0, 0.0))
    txt.text_render.set_text(unreal.Text("LAND %d" % n))
    txt.text_render.set_world_size(600.0)
    txt.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    txt.set_actor_label("%s%d_Sign" % (pre, n))
    txt.set_folder_path("%s/District_%d" % (folder, district))
    txt.attach_to_actor(slab, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    return slab


def apply(rings=6, realm="WORLD-ZERO", hub_cm=None, ground=None, hub_cells=None):
    """World Zero: estates and hub come from the live level. Another realm: pass its hub centre (cm), ground z and
    the cells its hub island holds (daedalus_realm_ground does)."""
    import unreal
    if realm == "WORLD-ZERO":
        estates, hub_cells, hub_cm, ground = _editor_inputs()
    else:
        estates, hub_cells = [], set(hub_cells or ())
    todo = plan(rings, estates, hub_cells, hub_cm, ground)
    have = _existing(realm)
    pre = _prefix(realm)
    folder = FOLDER if realm == "WORLD-ZERO" else "Realms/%s/Lands" % realm
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube = unreal.load_asset(CUBE)
    made = skipped = 0
    with unreal.ScopedSlowTask(len(todo), "Laying down lands") as task:
        task.make_dialog(True)
        for p in todo:
            task.enter_progress_frame(1)
            label = "%s%d" % (pre, p["n"])
            if label in have:
                skipped += 1
                continue
            lay_one(realm, p["n"], p["at"], p["district"], cube=cube, sub=sub)
            made += 1
    save_world()
    return {"realm": realm, "rings": rings, "free_cells": len(todo), "made": made, "skipped": skipped, "estates": len(estates),
            "hub_cells": len(hub_cells), "ground_cm": ground, "districts": sorted({p["district"] for p in todo})}


def remove(realm="WORLD-ZERO"):
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    gone = 0
    for label, a in _existing(realm).items():
        sub.destroy_actor(a)
        gone += 1
    save_world()
    return {"removed": gone}


def report(realm="WORLD-ZERO"):
    have = _existing(realm)
    slabs = [l for l in have if not l.endswith("_Sign")]
    nums = [int(l.split("_")[-1]) for l in slabs]
    return {"realm": realm, "plots": len(slabs), "signs": len(have) - len(slabs), "lowest": min(nums, default=-1), "highest": max(nums, default=-1)}
