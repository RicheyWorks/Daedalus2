# SPDX-License-Identifier: MIT
"""Opt-in official ToolsetRegistry binding for per-import FBX unit conversion.

Load/register only inside an admitted Unreal project. This module neither
registers itself nor starts a server, saves assets, or changes project settings.
"""
import unreal
import toolset_registry

from .unit_qualified_static_import import import_file as _import_file


@unreal.uclass()
class UnitQualifiedStaticMeshTools(unreal.ToolsetDefinition):
    """Static FBX import honoring authored scene units in centimeters."""

    @toolset_registry.tool_call
    @staticmethod
    def import_file(folder_path: str, asset_name: str, source_file: str,
                    import_materials: bool = False, import_textures: bool = False,
                    combine_meshes: bool = True) -> list[unreal.Object]:
        """Return unsaved imported assets with explicit FBX unit conversion.

        The caller must verify owned output paths, geometry and material slots,
        then explicitly save a nonempty exact allowlist. Existing assets are
        never replaced by the shared installed import helper.
        """
        return _import_file(folder_path, asset_name, source_file,
                            import_materials, import_textures, combine_meshes)
