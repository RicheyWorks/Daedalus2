# SPDX-License-Identifier: MIT
"""Per-import FBX unit options around Epic's installed, unsaved import helper.

The caller owns native admission, source/namespace pins, output verification and
explicit save/reopen. No editor or toolset is loaded merely by importing this
module. A separately registered ToolsetDefinition can call ``import_file``.

Unlike the installed StaticMeshTools wrapper, every call explicitly converts
FBX scene units to UE centimeters with uniform scale 1.0. This honors a source
UnitScaleFactor of 100 without adding a second manual factor of 100. Options are
set on the new FbxImportUI instance; no persistent configuration is saved.
"""
from pathlib import Path


def _native_api():
    import unreal
    from editor_toolset.toolsets.asset import import_asset
    return unreal, import_asset


def _fbx_source(source_file):
    path = Path(source_file)
    if not path.is_file():
        raise FileNotFoundError("Source file not found: " + str(path))
    if path.suffix.lower() != ".fbx":
        raise ValueError("Unit-qualified static import requires an FBX source")
    with path.open("rb") as source:
        header = source.read(256)
    text = header[3:] if header.startswith(b"\xef\xbb\xbf") else header
    binary = header.startswith(b"Kaydara FBX Binary  \x00\x1a\x00") and len(header) >= 27
    if not binary and not text.lstrip().startswith(b"; FBX"):
        raise ValueError("Source has no recognized binary or ASCII FBX header")
    # Identification only. Epic's factory/helper validates the complete FBX and
    # propagates invalid-body, collision and no-produced-asset errors unchanged.
    return str(path.resolve())


def import_file(folder_path, asset_name, source_file, import_materials=False,
                import_textures=False, combine_meshes=True):
    """Import with explicit centimeter conversion; return Epic's result unchanged.

    The shared helper enforces no replacement, automated import and save=False.
    Its factory-extension check and import failures remain authoritative.
    """
    source_file = _fbx_source(source_file)
    unreal, import_asset = _native_api()
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.original_import_type = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials = import_materials
    options.import_textures = import_textures
    options.import_animations = False
    options.static_mesh_import_data.combine_meshes = combine_meshes
    options.static_mesh_import_data.convert_scene = True
    options.static_mesh_import_data.convert_scene_unit = True
    options.static_mesh_import_data.import_uniform_scale = 1.0
    return import_asset(folder_path, asset_name, source_file,
                        options=options, factory=unreal.FbxFactory())
