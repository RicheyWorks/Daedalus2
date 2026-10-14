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
SLAB_M = 2.0
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
            x, y, z = p["at"]
            slab = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z - SLAB_M * 50.0))
            slab.static_mesh_component.set_static_mesh(cube)
            slab.set_actor_scale3d(unreal.Vector(LAND_M, LAND_M, SLAB_M))
            slab.set_actor_label(label)
            slab.set_folder_path("%s/District_%d" % (folder, p["district"]))
            slab.tags = [unreal.Name("Land"), unreal.Name("Realm:%s" % realm), unreal.Name("Deed:%d" % p["n"]), unreal.Name("District:%d" % p["district"])]
            txt = sub.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(x, y, z + 300.0), unreal.Rotator(90.0, 0.0, 0.0))
            txt.text_render.set_text(unreal.Text("LAND %d" % p["n"]))
            txt.text_render.set_world_size(600.0)
            txt.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
            txt.set_actor_label("%s%d_Sign" % (pre, p["n"]))
            txt.set_folder_path("%s/District_%d" % (folder, p["district"]))
            txt.attach_to_actor(slab, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
            made += 1
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False)
    return {"realm": realm, "rings": rings, "free_cells": len(todo), "made": made, "skipped": skipped, "estates": len(estates),
            "hub_cells": len(hub_cells), "ground_cm": ground, "districts": sorted({p["district"] for p in todo})}


def remove(realm="WORLD-ZERO"):
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    gone = 0
    for label, a in _existing(realm).items():
        sub.destroy_actor(a)
        gone += 1
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False)
    return {"removed": gone}


def report(realm="WORLD-ZERO"):
    have = _existing(realm)
    slabs = [l for l in have if not l.endswith("_Sign")]
    nums = [int(l.split("_")[-1]) for l in slabs]
    return {"realm": realm, "plots": len(slabs), "signs": len(have) - len(slabs), "lowest": min(nums, default=-1), "highest": max(nums, default=-1)}
