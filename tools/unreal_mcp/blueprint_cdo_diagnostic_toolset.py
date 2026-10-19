# SPDX-License-Identifier: MIT
"""Opt-in, runtime-unqualified diagnostics for the owned Blueprint CDO setter.

Import/register only in a separately admitted disposable project on the game
thread. This file neither registers itself with ToolsetRegistry nor acquires
admission, launches an editor, changes the engine, or retries operations.
"""
import unreal
import toolset_registry
from editor_toolset.toolsets.object import ObjectTools

from .blueprint_cdo_diagnostics import inspect_context as _inspect_context
from .blueprint_cdo_diagnostics import set_properties as _set_properties


@unreal.uclass()
class BlueprintCDODiagnosticTools(unreal.ToolsetDefinition):
    """Preserve stock setter guards while making Python failures actionable."""

    @toolset_registry.tool_call
    @staticmethod
    def inspect_context(blueprint: unreal.Blueprint, expected_project_file: str) -> str:
        """Read the exact already resolved diagnostic CDO and subsystem context."""
        return _inspect_context(blueprint, expected_project_file, unreal_api=unreal,
                                object_tools=ObjectTools,
                                raising_exceptions=toolset_registry.tool_raising_exceptions)

    @toolset_registry.tool_call
    @staticmethod
    def set_properties(blueprint: unreal.Blueprint, values: str, expected_project_file: str) -> bool:
        """Call the unchanged stock setter once; failures require reconciliation."""
        return _set_properties(blueprint, values, expected_project_file, unreal_api=unreal,
                               object_tools=ObjectTools,
                               raising_exceptions=toolset_registry.tool_raising_exceptions)
