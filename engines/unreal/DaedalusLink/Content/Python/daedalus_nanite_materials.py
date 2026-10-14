# SPDX-License-Identifier: MIT
"""Move the shipped art library's materials onto the project's Nanite-ready base (ADR-055).

Every glTF import parents its material instances to the Interchange plugin's MI_Default_Opaque_DS, whose base
M_Default has no Nanite usage flag. The flag can't be saved into engine content, so a packaged game would draw every
Nanite mesh in the library with the default material. New imports are fixed by the pipeline (sides.UNREAL_IMPORT);
this moves the ones already shipped. It is undoable: each change is written to Saved/Daedalus/nanite-materials.json
first, and undo() puts every instance back on its old parent.

    import daedalus_nanite_materials as n
    n.status()          # how many are still on the engine plugin's base
    n.run(100)          # move (and save) up to 100 per call: keep each bridge call short; call again until left == 0
    n.undo()            # put them all back
"""
import json
import os

import unreal

EAL = unreal.EditorAssetLibrary
OURS = "/Game/Daedalus/Materials/Gltf"
LEDGER = os.path.join(unreal.Paths.project_saved_dir(), "Daedalus", "nanite-materials.json")


def _engine_bound():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    f = unreal.ARFilter(package_paths=["/Game/Daedalus/Art"], recursive_paths=True,
                        class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "MaterialInstanceConstant")])
    return [a for a in reg.get_assets(f) if "/InterchangeAssets/" in str(a.get_tag_value("Parent"))]


def _ours(engine_mi):
    path = OURS + "/" + engine_mi.get_name()
    if not EAL.does_asset_exist(OURS + "/M_Default"):
        EAL.duplicate_asset("/InterchangeAssets/gltf/M_Default", OURS + "/M_Default")
        base = EAL.load_asset(OURS + "/M_Default")
        base.set_editor_property("used_with_nanite", True)
        base.set_editor_property("used_with_instanced_static_meshes", True)
        unreal.MaterialEditingLibrary.recompile_material(base)
        EAL.save_asset(OURS + "/M_Default", only_if_is_dirty=False)
    if not EAL.does_asset_exist(path):
        EAL.duplicate_asset(engine_mi.get_path_name().split(".")[0], path)
        unreal.MaterialEditingLibrary.set_material_instance_parent(EAL.load_asset(path), EAL.load_asset(OURS + "/M_Default"))
        EAL.save_asset(path, only_if_is_dirty=False)
    return EAL.load_asset(path)


def _ledger():
    try:
        with open(LEDGER) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _write(book):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(book, fh, indent=0, sort_keys=True)
    os.replace(tmp, LEDGER)


def status():
    return {"left": len(_engine_bound()), "moved": len(_ledger()), "ledger": LEDGER}


def run(batch=200):
    """Move up to `batch` instances. The ledger (the way back) is written once before the batch's changes and once
    after: writing it after every asset made a 10,000-entry JSON rewrite per move (about a second each, 2026-10-13)."""
    book = _ledger()
    todo = _engine_bound()[:int(batch)]
    pending = []
    for a in todo:
        mi = a.get_asset()
        old = mi.get_editor_property("parent")
        if old is None:
            continue
        book[mi.get_path_name()] = old.get_path_name()
        pending.append((mi, old))
    _write(book)                         # every old parent is on disk before anything changes
    moved = 0
    with unreal.ScopedSlowTask(len(pending), "Daedalus: materials onto the project base") as task:
        task.make_dialog(True)
        for mi, old in pending:
            if task.should_cancel():
                break
            task.enter_progress_frame(1)
            unreal.MaterialEditingLibrary.set_material_instance_parent(mi, _ours(old))
            moved += 1
    # Save without the per-asset checkout prompt: EditorAssetLibrary.save_loaded_asset goes through
    # InternalPromptForCheckoutAndSave, which opens a window per save; 3.5 minutes of that inside one bridge call
    # ended in a D3D11 CreateSwapChain fatal error (editor crash, 2026-10-13). save_packages has no prompt.
    pkgs = [mi.get_outermost() for mi, _ in pending[:moved]]
    if pkgs:
        unreal.EditorLoadingAndSavingUtils.save_packages(pkgs, only_dirty=True)
    out = status()
    out["moved_now"] = moved
    return out


def steps(chunk=25, save_every=150, limit=None):
    """Generator for daedalus.steps: reparent `chunk` instances per editor tick, save every `save_every`, until none
    is left on the engine base (or `limit` moved). One bridge call, the editor ticks between chunks, so neither
    the GPU watchdog (22:19) nor the swap-chain fatal (19:14) can fire. Yields a status line per chunk."""
    book = _ledger()
    moved = 0
    pending_pkgs = []
    queue = _engine_bound()            # scanned ONCE: rescanning 13k assets per chunk cost 10 s a chunk (22:50)
    if limit is not None:
        queue = queue[:int(limit)]
    total = len(queue)
    while queue:
        todo, queue = queue[:int(chunk)], queue[int(chunk):]
        pairs = []
        for a in todo:
            mi = a.get_asset()
            old = mi.get_editor_property("parent")
            if old is None:
                continue
            book[mi.get_path_name()] = old.get_path_name()
            pairs.append((mi, old))
        _write(book)
        for mi, old in pairs:
            unreal.MaterialEditingLibrary.set_material_instance_parent(mi, _ours(old))
            pending_pkgs.append(mi.get_outermost())
            moved += 1
        if len(pending_pkgs) >= save_every:
            unreal.EditorLoadingAndSavingUtils.save_packages(pending_pkgs, only_dirty=True)
            pending_pkgs = []
        yield "moved=%d of %d" % (moved, total)
    if pending_pkgs:
        unreal.EditorLoadingAndSavingUtils.save_packages(pending_pkgs, only_dirty=True)
        yield "saved tail"
    out = status()
    out["moved_now"] = moved
    return out


def undo():
    book = _ledger()
    back = 0
    for path, parent in list(book.items()):
        mi = EAL.load_asset(path.split(".")[0])
        p = EAL.load_asset(parent.split(".")[0])
        if mi is not None and p is not None:
            unreal.MaterialEditingLibrary.set_material_instance_parent(mi, p)
            EAL.save_loaded_asset(mi, only_if_is_dirty=False)
            back += 1
        del book[path]
        _write(book)
    return {"restored": back, "left": len(book)}
