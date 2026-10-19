# SPDX-License-Identifier: MIT
"""Runtime-unqualified diagnostics around the stock owned Blueprint setter.

The caller owns native admission, source qualification, game-thread dispatch,
and reconciliation. This module imports no Unreal module, registers nothing,
and never compiles, loads, saves, changes flags, or retries a setter. Dependencies
are injected so the diagnostic-loss regression can be tested without Unreal.

The official tool_raising_exceptions context keeps Python failures from being
reduced to str(exc) by the stock tool decorator. A UFunction can still wrap an
original exception as RuntimeError; observed_type means exactly the type seen
here. Native RaiseScriptError events are not catchable Python exceptions. The
surrounding official ToolsetRegistry execution must retain those native events.
"""
from __future__ import annotations

import json
import ntpath
import re


PACKAGE = "/Game/CodexToolEvaluation/BlueprintAcceptanceR2/BP_CompileReceipt"
OBJECT_PATH = PACKAGE + ".BP_CompileReceipt"
GENERATED_CLASS = PACKAGE + ".BP_CompileReceipt_C"
CDO_PATH = PACKAGE + ".Default__BP_CompileReceipt_C"
VARIABLE = "AuditValue"


class DiagnosticError(RuntimeError):
    """Nonempty stage/type diagnostics; UNKNOWN never authorizes replay."""

    def __init__(self, stage, observed_type, detail, effects="NONE"):
        self.stage = stage
        self.observed_type = observed_type
        self.effects = effects
        detail = detail if detail else "<empty exception message>"
        instruction = "; reconcile before any separately authorized retry" if effects == "UNKNOWN" else ""
        super().__init__(f"BlueprintCDODiagnostics stage={stage}; observed_type={observed_type}; "
                         f"detail={detail}; effects={effects}{instruction}")


def _require(condition, stage, detail):
    if not condition:
        raise DiagnosticError(stage, "GuardRejected", detail)


def _invoke(stage, callback, raising_exceptions, *, effects="NONE"):
    try:
        with raising_exceptions():
            return callback()
    except Exception as exc:
        raise DiagnosticError(stage, type(exc).__name__, str(exc), effects) from exc


def _path(value):
    return value.get_path_name() if value is not None else None


def _project_key(value):
    _require(isinstance(value, str) and ntpath.isabs(value), "guard.project",
             "an absolute externally admitted disposable project filename is required")
    _require(re.fullmatch(r"DisposableMCPR[1-9][0-9]*\.uproject", ntpath.basename(value)) is not None,
             "guard.project", "only a DisposableMCPR numbered diagnostic project is supported")
    return ntpath.normcase(ntpath.normpath(value.replace("/", "\\")))


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite JSON value: " + value)


def _json_object(raw):
    if not isinstance(raw, str):
        raise ValueError("stock JSON property result/input must be a string")
    value = json.loads(raw, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError("JSON properties must be an object")
    return value


def _context(blueprint, expected_project_file, *, unreal_api, object_tools, raising_exceptions):
    expected_project = _project_key(expected_project_file)
    actual_project = _invoke("context.project", lambda: unreal_api.Paths.convert_relative_path_to_full(
        unreal_api.Paths.get_project_file_path()), raising_exceptions)
    _require(_project_key(actual_project) == expected_project, "guard.project", "current project differs from admission")
    _require(isinstance(blueprint, unreal_api.Blueprint), "guard.blueprint", "an already resolved Blueprint is required")
    actual_path = _invoke("context.blueprint_path", lambda: _path(blueprint), raising_exceptions)
    _require(actual_path == OBJECT_PATH, "guard.blueprint", "Blueprint is outside the exact owned diagnostic fixture")

    generated = _invoke("context.generated_class", blueprint.generated_class, raising_exceptions)
    generated_path = _invoke("context.generated_class_path", lambda: _path(generated), raising_exceptions)
    _require(generated is not None and generated_path == GENERATED_CLASS,
             "guard.generated_class", "exact compiled diagnostic class is required")
    cdo = _invoke("context.cdo", lambda: unreal_api.get_default_object(generated), raising_exceptions)
    cdo_path = _invoke("context.cdo_path", lambda: _path(cdo), raising_exceptions)
    _require(isinstance(cdo, unreal_api.Actor) and cdo_path == CDO_PATH,
             "guard.cdo", "exact Actor class default object is required")
    cdo_class_path = _invoke("context.cdo_class", lambda: _path(cdo.get_class()), raising_exceptions)
    _require(cdo_class_path == GENERATED_CLASS, "guard.cdo", "CDO generated class differs")
    cdo_world = _invoke("context.cdo_world", cdo.get_world, raising_exceptions)

    les = _invoke("context.LevelEditorSubsystem", lambda: unreal_api.get_editor_subsystem(
        unreal_api.LevelEditorSubsystem), raising_exceptions)
    les_truthy = _invoke("context.LevelEditorSubsystem_truthiness", lambda: bool(les), raising_exceptions)
    level_pie = _invoke("context.level_editor_pie", lambda: les.is_in_play_in_editor(),
                        raising_exceptions) if les_truthy else None
    _require(not les_truthy or type(level_pie) is bool, "guard.pie", "level editor PIE observation is not boolean")
    current_level = _invoke("context.current_level", lambda: les.get_current_level(),
                            raising_exceptions) if les_truthy else None
    editor = _invoke("context.UnrealEditorSubsystem", lambda: unreal_api.get_editor_subsystem(
        unreal_api.UnrealEditorSubsystem), raising_exceptions)
    editor_truthy = _invoke("context.UnrealEditorSubsystem_truthiness", lambda: bool(editor), raising_exceptions)
    game_world = _invoke("context.game_world", lambda: editor.get_game_world(),
                         raising_exceptions) if editor_truthy else None
    cdo_world_path = _invoke("context.cdo_world_path", lambda: _path(cdo_world), raising_exceptions)
    current_level_path = _invoke("context.current_level_path", lambda: _path(current_level), raising_exceptions)
    game_world_path = _invoke("context.game_world_path", lambda: _path(game_world), raising_exceptions)
    raw = _invoke("stock.ObjectTools.get_properties", lambda: object_tools.get_properties(
        blueprint, [VARIABLE]), raising_exceptions)
    properties = _invoke("context.property_json", lambda: _json_object(raw), raising_exceptions)
    _require(set(properties) == {VARIABLE} and type(properties[VARIABLE]) is int,
             "guard.property", "the exact integer AuditValue default is required")
    return {
        "schema": "codex.blueprint-cdo-diagnostic-context.v1",
        "runtime_qualified": False,
        "caller_native_admission_required": True,
        "project_basename": ntpath.basename(actual_project),
        "project_matches_external_expected": True,
        "blueprint": actual_path,
        "generated_class": generated_path,
        "cdo": cdo_path,
        "cdo_world": cdo_world_path,
        "level_editor_subsystem_truthy": les_truthy,
        "level_editor_in_pie": level_pie,
        "current_level": current_level_path,
        "unreal_editor_subsystem_truthy": editor_truthy,
        "pie_world_checked": editor_truthy,
        "game_world": game_world_path,
        "properties": properties,
        "runtime_property_flags_observed": False,
        "property_flags_changed": False,
        "property_flags_limitation": "Stock inspection does not expose property flags; stock setter permissions remain authoritative.",
        "native_mutation_calls": 0,
    }


def inspect_context(blueprint, expected_project_file, *, unreal_api, object_tools, raising_exceptions):
    """Read only: exact already resolved CDO, world, LES truthiness, and default.

    A missing LevelEditorSubsystem is reported, not retrospectively attributed
    to the consumed failure. An unavailable UnrealEditorSubsystem makes the PIE
    observation unknown; set_properties then refuses to dispatch its mutation.
    """
    return json.dumps(_context(blueprint, expected_project_file, unreal_api=unreal_api,
                              object_tools=object_tools, raising_exceptions=raising_exceptions),
                      allow_nan=False, sort_keys=True)


def set_properties(blueprint, values, expected_project_file, *, unreal_api, object_tools, raising_exceptions):
    """Dispatch the unchanged stock setter once, only for owned integer 0 -> 37.

    This is a diagnostic correction, not a qualified fix for the value-37
    failure. Missing LES does not bypass require_editable: the stock method is
    still called and its own guards remain authoritative. Any failure after
    dispatch has unknown effects and requires reconciliation without replay.
    A True return is only the stock return; native error events and subsequent
    value/compile/save/persistence checks belong to the admitted caller.
    """
    proposed = _invoke("guard.values_json", lambda: _json_object(values), raising_exceptions)
    _require(set(proposed) == {VARIABLE} and type(proposed[VARIABLE]) is int and proposed[VARIABLE] == 37,
             "guard.values", "only the exact integer AuditValue target 37 is supported")
    facts = _context(blueprint, expected_project_file, unreal_api=unreal_api,
                     object_tools=object_tools, raising_exceptions=raising_exceptions)
    _require(facts["cdo_world"] is None, "guard.cdo_world", "a world-bound object cannot enter the CDO setter")
    _require(facts["pie_world_checked"] and facts["game_world"] is None
             and (facts["level_editor_in_pie"] is None or facts["level_editor_in_pie"] is False),
             "guard.pie", "PIE must be observed inactive before setter dispatch")
    _require(facts["properties"] == {VARIABLE: 0}, "guard.current_default",
             "expected current default zero; reconcile changed/unknown state without replay")
    result = _invoke("stock.ObjectTools.set_properties", lambda: object_tools.set_properties(
        blueprint, values), raising_exceptions, effects="UNKNOWN")
    if result is not True:
        raise DiagnosticError("stock.ObjectTools.set_properties.return", type(result).__name__,
                              "stock setter did not return literal True", "UNKNOWN")
    return result
