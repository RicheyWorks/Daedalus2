# SPDX-License-Identifier: MIT
"""Opt-in binding; future admitted disposable DataValidation profile only.

This module registers nothing and does not enable plugins or start a server.
The producer's output describes reflected per-object validation, not native
ValidateAssetsWithSettings counts or an assumed struct serialization.
"""
import unreal
import toolset_registry

from .per_asset_validation_producer import validate_object as _validate_object


@unreal.uclass()
class PerAssetValidationTools(unreal.ToolsetDefinition):
    """Validate one already-loaded exact-owned asset with explicit issue output."""

    @toolset_registry.tool_call
    @staticmethod
    def validate_object(asset: unreal.Object, expected_project_file: str, validation_usecase: str) -> str:
        """Call real IsObjectValid once, retaining enum/errors/warnings."""
        return _validate_object(asset, expected_project_file, validation_usecase,
                                unreal_api=unreal,
                                raising_exceptions=toolset_registry.tool_raising_exceptions)
