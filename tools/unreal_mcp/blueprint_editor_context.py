# SPDX-License-Identifier: MIT
"""Read-only editor prerequisites to check before any Blueprint create/edit.

No Unreal import, module loading, subsystem registration, or mutation occurs
here. The caller supplies the live Unreal API and owns admission, game-thread
dispatch, observation freshness, and the startup profile. Qualification does
not replace the stock ObjectTools editability guard or establish setter success.

The supported build is deliberately exact. Installed source: PyCore.cpp
1904/2094 exposes unreal.is_editor(); KismetSystemLibrary.cpp 268 returns
FEngineVersion::Current().ToString(); LevelEditorSubsystem.h 37-45 declares the
editor subsystem used by toolset_registry/helpers.py 59-60. Asset-only Actor
CDOs need no editor map: null editor_world/current_level are valid observations.
"""
from __future__ import annotations

import ntpath


SCHEMA = "codex.blueprint-editor-context.v1"
SUPPORTED_ENGINE_VERSION = "5.8.3-58210709+++UE5+Release-5.8"


class ContextHold(RuntimeError):
    """Stop before Blueprint work; a context failure never authorizes a bypass."""

    def __init__(self, stage, detail, *, observed_type="GuardRejected"):
        self.stage = stage
        self.observed_type = observed_type
        self.effects = "NONE"
        super().__init__(f"BlueprintEditorContext HOLD stage={stage}; "
                         f"observed_type={observed_type}; "
                         f"detail={detail or '<empty exception message>'}; "
                         "no Blueprint create/edit is permitted")


def _require(condition, stage, detail):
    if not condition:
        raise ContextHold(stage, detail)


def _read(stage, callback):
    try:
        return callback()
    except Exception as exc:
        raise ContextHold(stage, str(exc), observed_type=type(exc).__name__) from exc


def _object_path(value):
    if value is None:
        return None
    path = value.get_path_name()
    if not isinstance(path, str) or not path.strip():
        raise ValueError("a non-null observed object must have a nonempty path")
    return path


def _project_key(value, stage):
    _require(isinstance(value, str) and bool(value.strip()) and ntpath.isabs(value)
             and bool(ntpath.splitdrive(value)[0])
             and ntpath.splitext(value)[1].lower() == ".uproject",
             stage, "a fully qualified absolute .uproject filename is required")
    return ntpath.normcase(ntpath.normpath(value))


def collect_context(*, unreal_api):
    """Collect only live getters; missing subsystems remain explicit unknowns.

    A missing LevelEditorSubsystem is the observed R8 prerequisite failure.
    Do not repair it here. The startup profile must establish it before this
    probe, and qualify() must pass before creating even the first Blueprint.
    """
    is_editor = _read("collect.is_editor", lambda: unreal_api.is_editor())
    facts = {
        "schema": SCHEMA,
        "caller_native_admission_required": True,
        "native_mutation_calls": 0,
        "engine_version": _read("collect.engine_version", lambda: unreal_api.SystemLibrary.get_engine_version()),
        "is_editor": is_editor,
        "project_file": _read("collect.project_file", lambda: unreal_api.Paths.convert_relative_path_to_full(
            unreal_api.Paths.get_project_file_path())),
        "level_editor_subsystem_truthy": False,
        "unreal_editor_subsystem_truthy": False,
        "level_editor_pie_checked": False,
        "level_editor_in_pie": None,
        "current_level_checked": False,
        "current_level": None,
        "editor_world_checked": False,
        "editor_world": None,
        "pie_world_checked": False,
        "game_world": None,
    }
    # The native subsystem getter dereferences GEditor. Do not call it outside
    # editor mode, nor turn an untyped observation into a truthy admission.
    if is_editor is not True:
        return facts

    les = _read("collect.LevelEditorSubsystem", lambda: unreal_api.get_editor_subsystem(
        unreal_api.LevelEditorSubsystem))
    les_truthy = _read("collect.LevelEditorSubsystem.truthiness", lambda: bool(les))
    facts["level_editor_subsystem_truthy"] = les_truthy
    if les_truthy:
        facts["level_editor_in_pie"] = _read("collect.level_editor_in_pie", lambda: les.is_in_play_in_editor())
        facts["level_editor_pie_checked"] = True
        facts["current_level"] = _read("collect.current_level", lambda: _object_path(les.get_current_level()))
        facts["current_level_checked"] = True

    editor = _read("collect.UnrealEditorSubsystem", lambda: unreal_api.get_editor_subsystem(
        unreal_api.UnrealEditorSubsystem))
    editor_truthy = _read("collect.UnrealEditorSubsystem.truthiness", lambda: bool(editor))
    facts["unreal_editor_subsystem_truthy"] = editor_truthy
    if editor_truthy:
        facts["editor_world"] = _read("collect.editor_world", lambda: _object_path(editor.get_editor_world()))
        facts["editor_world_checked"] = True
        facts["game_world"] = _read("collect.game_world", lambda: _object_path(editor.get_game_world()))
        facts["pie_world_checked"] = True
    return facts


def qualify(context, expected_project_file):
    """Pure, fail-closed qualification of freshly collected editor context.

    Windows project identities are compared without filesystem access. A pass
    checks context only: native admission and stock per-object permissions
    remain the caller's responsibility. No profile is changed or recommended
    for an unreviewed engine build.
    """
    _require(type(context) is dict and context.get("schema") == SCHEMA,
             "qualify.schema", "a collected Blueprint editor context is required")
    _require(context.get("engine_version") == SUPPORTED_ENGINE_VERSION,
             "qualify.engine_version", "unsupported engine context; source-qualify the build before Blueprint work; "
             f"expected {SUPPORTED_ENGINE_VERSION}")
    expected = _project_key(expected_project_file, "qualify.expected_project")
    actual = _project_key(context.get("project_file"), "qualify.project")
    _require(actual == expected, "qualify.project", "the live project differs from the externally admitted project")
    _require(context.get("is_editor") is True, "qualify.is_editor", "the live process must be in editor mode")
    _require(context.get("level_editor_subsystem_truthy") is True,
             "qualify.LevelEditorSubsystem", "LevelEditorSubsystem is unavailable; start the supported editor "
             "profile with its Level Editor prerequisite and requalify before creating a Blueprint; "
             "do not bypass the stock require_editable guard")
    _require(context.get("unreal_editor_subsystem_truthy") is True,
             "qualify.UnrealEditorSubsystem", "UnrealEditorSubsystem is unavailable; PIE state is unknown")
    _require(context.get("level_editor_pie_checked") is True and context.get("level_editor_in_pie") is False,
             "qualify.pie", "LevelEditorSubsystem must report literal False for PIE")
    _require(context.get("pie_world_checked") is True and "game_world" in context and context["game_world"] is None,
             "qualify.game_world", "the live game-world query must complete and return null")
    for name in ("editor_world", "current_level"):
        value = context.get(name)
        _require(context.get(name + "_checked") is True and name in context
                 and (value is None or isinstance(value, str) and bool(value.strip())),
                 "qualify." + name, "a completed nullable object-path observation is required")
    _require(context.get("caller_native_admission_required") is True
             and type(context.get("native_mutation_calls")) is int and context["native_mutation_calls"] == 0,
             "qualify.scope", "only the read-only context probe is supported; native admission remains required")
    return {**context, "project_matches_external_expected": True,
            "qualified": True, "qualification_scope": "EDITOR_CONTEXT_ONLY"}
