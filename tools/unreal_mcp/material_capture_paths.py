"""Normalize an observed Unreal project path without weakening its allowlist.

The native producer supplies unreal.Paths.convert_relative_path_to_full. Tests
inject a resolver, while actual captures retain the reported path separately.
This module has no engine, network, filesystem or clock side effects.
"""

PROJECT = "C:/Unreal/DaedalusRealm/DaedalusRealm.uproject"


class ProjectPathHeld(ValueError):
    pass


def canonical_project_path(reported, resolve_absolute):
    if type(reported) is not str or not reported or len(reported) > 1024 or "\x00" in reported:
        raise ProjectPathHeld("A bounded actual project path is required")
    if not callable(resolve_absolute):
        raise ProjectPathHeld("The actual Unreal absolute-path resolver is required")
    try:
        resolved = resolve_absolute(reported)
    except Exception as exc:
        raise ProjectPathHeld("The actual project path could not be resolved") from exc
    if type(resolved) is not str or not resolved or len(resolved) > 1024 or "\x00" in resolved:
        raise ProjectPathHeld("The resolver did not return a bounded project path")
    canonical = resolved.replace("\\", "/")
    if canonical != PROJECT:
        raise ProjectPathHeld("The observed project is outside the exact admitted project")
    return canonical
