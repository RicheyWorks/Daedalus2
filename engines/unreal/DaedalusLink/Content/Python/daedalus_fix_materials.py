# SPDX-License-Identifier: MIT
"""Give every imported Daedalus material the usage flags the world needs, and save it.

    import daedalus_fix_materials as M
    M.fix("/Game/Daedalus/Art")            # -> {"checked": n, "flagged": n, "saved": n}

Why: the Dresser draws props through HierarchicalInstancedStaticMesh pools; a material without
bUsedWithInstancedStaticMeshes gets compiled on the fly in the editor ("will recompile every editor launch until
resaved": 340 warnings per Play on 2026-10-13) and falls back to the DEFAULT material in a packaged game. Setting
the flag once and saving the asset ends both. Run outside Play (saving is an editor operation).
"""
import unreal

FLAGS = ("used_with_instanced_static_meshes", "used_with_skeletal_mesh", "used_with_nanite")


def fix(root="/Game/Daedalus/Art", dry=False):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    checked = flagged = saved = 0
    changed_paths = []
    for d in reg.get_assets_by_path(root, recursive=True):
        if str(d.asset_class_path.asset_name) != "Material":
            continue
        checked += 1
        m = d.get_asset()
        if m is None:
            continue
        dirty = False
        for flag in FLAGS:
            try:
                if not m.get_editor_property(flag):
                    if not dry:
                        m.set_editor_property(flag, True)
                    dirty = True
            except Exception:   # a flag this engine version doesn't expose
                pass
        if dirty:
            flagged += 1
            path = str(d.package_name)
            changed_paths.append(path)
            if not dry and unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False):
                saved += 1
    out = {"checked": checked, "flagged": flagged, "saved": saved, "dry": dry}
    print("materials: %(checked)d checked, %(flagged)d needed flags, %(saved)d saved" % out)
    return out
