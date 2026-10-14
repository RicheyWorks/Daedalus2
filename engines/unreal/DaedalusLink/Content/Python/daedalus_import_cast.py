# SPDX-License-Identifier: MIT
"""Import a realm cast (Sol's rigged GLBs: 14-bone humanoids with Idle/Walk/Attack/Hurt clips) into the project.

    import daedalus_import_cast as C
    C.import_folder(r"C:\\Users\\730ri\\Documents\\Codex\\2026-10-13\\gallery-buildout\\cast")      # every Mob_*.glb
    C.report("Mob_Gallery_CuratorVell")                                                   # what the import made

Each GLB lands in /Game/Daedalus/Art/Cast/<Id>/ as a SkeletalMesh (+ Skeleton, PhysicsAsset, materials) and its
clips as AnimSequences. ADaedalusTalker finds them by the id (Mob_<Realm>_<WhoPascal>); DaedalusBattlePresentation
plays the clips. Idempotent: an id already imported with the same SHA-256 (manifest.json beside the GLBs) is skipped.
Runs inside the editor only (unreal module); the pure helpers (ids, sha) are importable headless for tests.
"""
import hashlib
import json
import os

try:
    import unreal   # noqa: F401
    HAVE_UNREAL = True
except ImportError:   # headless tests
    HAVE_UNREAL = False

CAST_ROOT = "/Game/Daedalus/Art/Cast"
STAMP = "daedalus_cast_sha256"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def talker_asset_id(cast, who):
    """The id a Talker looks for: Mob_<Realm>_<WhoPascal>, Sol's convention (Mob_Gallery_CuratorVell).
    cast is the .dcs name (gallery-city, parcels, bricks, labyrinth)."""
    realm = {"gallery-city": "Gallery", "parcels": "Parcels", "bricks": "Brick", "labyrinth": "Labyrinth",
             "world-zero": "Zero", "ocean": "Ocean"}.get(cast.lower(), cast.split("-")[0].capitalize())
    # Sol's exports also use Mob_Bricks_ and Mob_Lab_; ADaedalusTalker::ArtIds() tries those after the canonical id.
    words = [w for w in "".join(c if c.isalnum() else " " for c in who).split() if w]
    return "Mob_%s_%s" % (realm, "".join(w[:1].upper() + w[1:] for w in words))


def plan(folder):
    """[(id, glb path, sha from the manifest or the file)] for every Mob_*.glb in the folder."""
    out = []
    manifest = {}
    mp = os.path.join(folder, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp, encoding="utf-8") as f:
                for a in json.load(f).get("assets", []):
                    manifest[a.get("id")] = a.get("sha256", "")
        except (ValueError, OSError):
            manifest = {}
    for name in sorted(os.listdir(folder)):
        if not (name.startswith("Mob_") and name.lower().endswith(".glb")):
            continue
        asset_id = name[:-4]
        path = os.path.join(folder, name)
        out.append((asset_id, path, manifest.get(asset_id) or sha256(path)))
    return out


def _stamp_of(asset_id, root=CAST_ROOT):
    path = "%s/%s/%s" % (root, asset_id, asset_id)
    data = unreal.EditorAssetLibrary.get_metadata_tag(unreal.load_asset(path), STAMP) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    return data or ""


def import_one(asset_id, glb, sha, force=False, root=CAST_ROOT):
    """Import one GLB. Returns (status, assets): status in imported | skipped | failed."""
    dest = "%s/%s" % (root, asset_id)
    if not force and _stamp_of(asset_id, root) == sha:
        return "skipped", _assets_under(dest)
    task = unreal.AssetImportTask()
    task.filename = glb
    task.destination_path = dest
    task.destination_name = asset_id
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    made = _assets_under(dest)
    skel = [a for a in made if a["class"] == "SkeletalMesh"]
    if not skel:
        return "failed", made
    mesh = unreal.load_asset(skel[0]["path"])
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, STAMP, sha)
    unreal.EditorAssetLibrary.save_asset(skel[0]["path"], only_if_is_dirty=False)
    return "imported", made


def _assets_under(dest):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    out = []
    for d in reg.get_assets_by_path(dest, recursive=True):
        out.append({"path": str(d.package_name) + "." + str(d.asset_name), "name": str(d.asset_name), "class": str(d.asset_class_path.asset_name)})
    return out


def import_folder(folder, force=False, root=CAST_ROOT):
    """Import every Mob_*.glb (root: /Game/Daedalus/Art/Cast for talkers, .../Creatures for creatures); prints one
    line per asset and returns the summary dict."""
    summary = {"imported": [], "skipped": [], "failed": []}
    for asset_id, glb, sha in plan(folder):
        status, made = import_one(asset_id, glb, sha, force, root)
        summary[status].append(asset_id)
        clips = [a["name"] for a in made if a["class"] == "AnimSequence"]
        print("%-9s %s  skeletal=%d clips=%s" % (status, asset_id, sum(1 for a in made if a["class"] == "SkeletalMesh"), ",".join(clips) or "-"))
    print("cast import: %d imported, %d skipped, %d failed" % (len(summary["imported"]), len(summary["skipped"]), len(summary["failed"])))
    return summary


def report(asset_id):
    made = _assets_under("%s/%s" % (CAST_ROOT, asset_id))
    return {"id": asset_id, "sha": _stamp_of(asset_id), "assets": made}
