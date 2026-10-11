# SPDX-License-Identifier: MIT
"""
Import a Daedalus World Package into an Unreal Engine 5 project (ADR-032).

Inside the editor (Tools > Execute Python Script, or the Output Log's "py" command):

    py "<Project>/Plugins/DaedalusLink/Content/Python/import_world_package.py" "C:/path/world-zero-r12.daedalus.zip"
    py "<...>/import_world_package.py" http://localhost:8088 world-zero --live

Headless, as setup-unreal.ps1 -Import runs it:

    UnrealEditor-Cmd.exe Project.uproject -run=pythonscript -script="<...>/import_world_package.py <zip>"

What it does:
  1. reads the package (a .zip on disk, or downloads /api/v1/world/<id>/package from a server);
  2. checks it: format, version, a glTF 2.0 binary whose size and node count match the manifest;
  3. makes two materials that show vertex colour (opaque, and translucent for water, glass, rainbows,
     gate doorways) under /Game/Daedalus/Materials;
  4. imports world.glb and assets/ark.glb under /Game/Daedalus/<world id>/ with Interchange;
  5. places the baked world in the level /Game/Daedalus/DaedalusWorld (made if missing, then saved), plus a "Daedalus World" actor with ServerUrl, WorldId,
     materials and ark mesh set, ready to follow the live server (tick Load On Begin Play and hide the
     baked folder); with --live it skips the bake and the actor follows the server from the first frame.

Run with --dry-run (or outside Unreal) to only read, check and print the plan; exit status 1 if the package
is not a valid Daedalus World Package. Standard library only.
"""

import json
import os
import struct
import sys
import tempfile
import urllib.request
import zipfile

FORMAT = "daedalus-world-package"
VERSION = 1
CONTENT_ROOT = "/Game/Daedalus"
LEVEL = CONTENT_ROOT + "/DaedalusWorld"

try:
    import unreal  # present only inside the Unreal editor
except ImportError:  # pragma: no cover - the CLI path
    unreal = None


class PackageError(Exception):
    """The file is not a Daedalus World Package this importer understands."""


def fetch(server, world, into):
    """Download a world's package from a running Daedalus server; returns the zip's path."""
    url = server.rstrip("/") + "/api/v1/world/" + world + "/package"
    path = os.path.join(into, world + ".daedalus.zip")
    with urllib.request.urlopen(url, timeout=60) as r, open(path, "wb") as out:
        out.write(r.read())
    return path


def glb_summary(data):
    """Header and JSON chunk of a binary glTF; raises PackageError when it is not glTF 2.0."""
    if len(data) < 20:
        raise PackageError("world.glb is too short to be glTF")
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise PackageError("world.glb is not glTF 2.0 binary")
    if length != len(data):
        raise PackageError("world.glb says %d bytes but has %d" % (length, len(data)))
    json_len, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise PackageError("world.glb has no JSON chunk")
    gltf = json.loads(data[20:20 + json_len].decode("utf-8"))
    if gltf.get("asset", {}).get("version") != "2.0":
        raise PackageError("world.glb asset.version is not 2.0")
    return gltf


def read_package(zip_path):
    """Open and check a package; returns (manifest, gltf json, names in the zip)."""
    try:
        z = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as e:
        raise PackageError("not a zip: %s" % e)
    with z:
        names = z.namelist()
        for need in ("manifest.json", "world.glb"):
            if need not in names:
                raise PackageError("missing " + need)
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
        if manifest.get("format") != FORMAT:
            raise PackageError("format is %r, not %r" % (manifest.get("format"), FORMAT))
        if manifest.get("version") != VERSION:
            raise PackageError("package version %r; this importer reads %d" % (manifest.get("version"), VERSION))
        gltf = glb_summary(z.read("world.glb"))
    geometry = manifest.get("geometry", {})
    nodes = len(gltf.get("nodes", []))
    if nodes != geometry.get("chunks"):
        raise PackageError("manifest says %s chunks, world.glb has %d nodes" % (geometry.get("chunks"), nodes))
    for asset in manifest.get("assets", []):
        if asset["file"] not in names:
            raise PackageError("manifest lists %s but the zip lacks it" % asset["file"])
    return manifest, gltf, names


def plan(manifest, names):
    """What the import will do, as lines a person can read; also the dry run's output."""
    w = manifest["world"]
    g = manifest["geometry"]
    dest = "%s/%s" % (CONTENT_ROOT, safe_name(w["id"]))
    lines = [
        "Daedalus World Package v%d: %s (%s, %s) at revision %d" % (manifest["version"], w["title"], w["id"],
                                                                    w["style"], w["revision"]),
        "  geometry: %d chunks, %d triangles -> %s/world" % (g["chunks"], g["triangles"], dest),
        "  materials: %s/Materials/M_DaedalusOpaque, M_DaedalusTranslucent (vertex colour)" % CONTENT_ROOT,
    ]
    for a in manifest.get("assets", []):
        lines.append("  asset %s: %s -> %s/%s (%s)" % (a["name"], a["file"], dest, a["name"], a["use"]))
    plots = manifest.get("plots", [])
    lines.append("  islands: %d, plots: %d (%d claimed), sky gates: %d, vessels: %d, mount: %s" % (
        len(manifest.get("islands", [])), len(plots), sum(1 for p in plots if p.get("owner")),
        len(manifest.get("gates", [])), len(manifest.get("arks", [])), manifest["mount"]["kind"]))
    obby = manifest.get("obby")
    if obby:
        steps = obby.get("steps", [])
        lines.append("  obby: %d platforms over lava, %d checkpoints, spawn at %s" % (
            len(steps) - 1, sum(1 for s in steps if s.get("checkpoint")), obby.get("spawn")))
    art = manifest.get("art", [])
    if art:
        lines.append("  art: %d frames of maze art (images served by the live world)" % len(art))
    for gate in manifest.get("gates", []):
        lines.append("    gate %d -> %s (%s) gate %d" % (gate["gate"], gate["toTitle"], gate["toWorld"], gate["toGate"]))
    live = manifest.get("live", {})
    if live.get("api"):
        lines.append("  live: Daedalus World actor following %s" % live["api"])
    if manifest.get("chain"):
        c = manifest["chain"]
        lines.append("  chain: deeds on chain %d at %s" % (c["chainId"], c["deedContract"]))
    return lines


def safe_name(s):
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in s)


def to_unreal(xyz, units=100.0):
    """Daedalus metres, +Y up, right-handed -> Unreal centimetres, +Z up, left-handed."""
    return (xyz[0] * units, xyz[2] * units, xyz[1] * units)


# ---------------------------------------------------------------- inside the editor

def _material(name, translucent):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    path = CONTENT_ROOT + "/Materials"
    existing = unreal.EditorAssetLibrary.load_asset(path + "/" + name)
    if existing:
        return existing
    mat = tools.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -400, 0)
    mel.connect_material_property(vc, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.2 if translucent else 0.9)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    if translucent:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property("two_sided", True)
        alpha = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 300)
        alpha.set_editor_property("r", 0.62)
        mel.connect_material_property(alpha, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def _import(file_path, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", file_path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return [unreal.EditorAssetLibrary.load_asset(p) for p in task.get_editor_property("imported_object_paths")]


def import_into_unreal(zip_path, manifest, live_only=False):
    w = manifest["world"]
    dest = "%s/%s" % (CONTENT_ROOT, safe_name(w["id"]))
    work = tempfile.mkdtemp(prefix="daedalus_")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(work)
    opaque = _material("M_DaedalusOpaque", False)
    translucent = _material("M_DaedalusTranslucent", True)

    world_assets = [] if live_only else _import(os.path.join(work, "world.glb"), dest + "/world")
    ark_mesh = None
    for a in manifest.get("assets", []):
        imported = _import(os.path.join(work, a["file"]), dest + "/" + safe_name(a["name"]))
        if a["name"] == "ark":
            ark_mesh = next((o for o in imported if isinstance(o, unreal.StaticMesh)), None)

    # Work in the Daedalus level (setup-unreal.ps1 makes it the project's startup map), so a headless run
    # leaves something saved behind.
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        levels.load_level(LEVEL)
    else:
        levels.new_level(LEVEL)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for old in actors.get_all_level_actors():
        if str(old.get_folder_path()) == "Daedalus/" + w["id"]:
            actors.destroy_actor(old)  # re-importing a world replaces it rather than stacking a copy
    placed = 0
    for asset in world_assets:
        if not isinstance(asset, unreal.StaticMesh):
            continue
        # Chunk geometry is in world coordinates already: every chunk mesh sits at the origin.
        actor = actors.spawn_actor_from_object(asset, unreal.Vector(0, 0, 0))
        actor.set_folder_path("Daedalus/" + w["id"])
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        for i in range(comp.get_num_materials()):
            slot = str(comp.get_material_slot_names()[i]) if i < len(comp.get_material_slot_names()) else ""
            comp.set_material(i, translucent if "translucent" in slot else opaque)
        placed += 1

    live_class = unreal.load_class(None, "/Script/DaedalusLink.DaedalusWorldActor")
    if live_class and manifest.get("live", {}).get("api"):
        live = actors.spawn_actor_from_class(live_class, unreal.Vector(0, 0, 0))
        live.set_actor_label("Daedalus World (live) - " + w["title"])
        live.set_folder_path("Daedalus/" + w["id"])
        api = manifest["live"]["api"]
        live.set_editor_property("server_url", api[:api.index("/api/v1/")])
        live.set_editor_property("world_id", w["id"])
        live.set_editor_property("opaque_material", opaque)
        live.set_editor_property("translucent_material", translucent)
        if ark_mesh:
            live.set_editor_property("ark_mesh", ark_mesh)
        # Baked chunks and a live actor would draw the world twice: only one of them runs by default.
        live.set_editor_property("load_on_begin_play", live_only)
    levels.save_current_level()
    unreal.log("Daedalus: placed %d chunk meshes of %s; live actor %s" % (placed, w["title"],
               "added" if live_class else "skipped (enable the DaedalusLink plugin)"))


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    dry = "--dry-run" in argv or unreal is None
    if not args:
        print(__doc__)
        return 2
    try:
        if args[0].startswith("http://") or args[0].startswith("https://"):
            if len(args) < 2:
                raise PackageError("give a world id after the server URL")
            zip_path = fetch(args[0], args[1], tempfile.mkdtemp(prefix="daedalus_"))
        else:
            zip_path = args[0]
        manifest, _, names = read_package(zip_path)
    except (PackageError, OSError, ValueError, KeyError) as e:
        print("NOT a Daedalus World Package: %s" % e)
        return 1
    for line in plan(manifest, names):
        print(line)
    if dry:
        print("dry run: nothing imported" + ("" if unreal else " (not inside Unreal)"))
        return 0
    import_into_unreal(zip_path, manifest, live_only="--live" in argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
