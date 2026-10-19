# SPDX-License-Identifier: MIT
"""One real reflected IsObjectValid call for an already-loaded owned asset.

Source-supported, runtime-unqualified UE 5.8.3 route. This module imports no
Unreal module and never registers tools, loads/saves assets, writes properties,
changes validators/settings, or retries. Enabled native validators execute
callbacks; their effects are not proven harmless by this producer.

This is deliberately distinct from ValidateAssetsWithSettings and its native
FValidateAssetsResults. Counters below are derived from one returned per-object
enum and its explicit FText issue arrays. There is no native aggregate snapshot,
raw-log capture, external-object traversal, or validator-wide message capture.

Future qualification: enable DataValidation only in a fresh admitted disposable
profile; register the opt-in binding; verify its actual complete schema; create
and load only FIXTURE_OBJECT_PATH through existing official tools; call once
with Script usecase; retain actual enum/errors/warnings and post-call clean/
idle/source guards. NotValidated is a useful non-pass observation. A controlled
native Valid/Invalid validator fixture requires separate reviewed registration,
then guaranteed removal; injected tests do not qualify that native behavior.
"""
import json
import ntpath
import re


FIXTURE_OBJECT_PATH = "/Game/CodexToolEvaluation/DataValidationR1/DA_ValidationReceipt.DA_ValidationReceipt"
SCHEMA = "codex.official-per-object-validation.v1"
SOURCE_PROVENANCE = {
    "engine": "UE 5.8.3 changelist 58210709",
    "api": "UEditorValidatorSubsystem::IsObjectValid",
    "header": "Engine/Plugins/Editor/DataValidation/Source/DataValidation/Public/EditorValidatorSubsystem.h:339-344",
    "header_sha256": "463558fd5bc145575def4caa75eb22d49a1c06dab7e1e0b927dd9781fc058174",
    "implementation_lines": "EditorValidatorSubsystem.cpp:571-580,605-625,645-696",
    "implementation_sha256": "c7a758c926f413240cfa598ab90af296db9dc39584c43ae3d56f7dbe2546b0a8",
    "python_tuple": "PyGenUtil.cpp:1036-1059 return first then out parameters;1154-1200 packs tuple",
    "python_tuple_sha256": "252a0b06b77abd07c8dbb5972b47dc430a6d7f889eee2d5ae50a6d114b528e58",
    "python_inputs": "PyUtil.cpp:584-598 nonconst output arrays are not input arguments",
    "python_inputs_sha256": "87f923173ada88b25a39c2e500af4104500bbfb32e4cb6a3d9aa20d890ce298d",
    "usecase": "CoreUObject/Public/Misc/DataValidation.h:19-39 Script enum",
    "usecase_sha256": "611d83c8b9294b9c45244d13a727e1e91fe11a9369cefbf225d2137ada3ad602",
    "plugin_sha256": "d0d847d443bd29d92aa16f3f8a6cd7f2776a042bd2140a8e6242650681600ce2",
    "plugin_dependencies": "DataValidation.uplugin declares Editor/PreDefault module; no Plugins dependency field",
    "profile_limit": "DataValidation is disabled in current R7; future disposable profile admission required",
}


class ValidationProducerError(RuntimeError):
    """A guard or call failed; UNKNOWN effects never authorize replay."""

    def __init__(self, stage, observed_type, detail, effects="NONE"):
        self.stage, self.observed_type, self.effects = stage, observed_type, effects
        super().__init__("PerAssetValidation stage=%s; observed_type=%s; detail=%s; effects=%s; no automatic retry"
                         % (stage, observed_type, detail or "<empty exception message>", effects))


def _require(condition, stage, detail, effects="NONE"):
    if not condition:
        raise ValidationProducerError(stage, "GuardRejected", detail, effects)


def _invoke(stage, callback, raising_exceptions, effects="NONE"):
    try:
        with raising_exceptions():
            return callback()
    except Exception as exc:
        raise ValidationProducerError(stage, type(exc).__name__, str(exc), effects) from exc


def _project_key(value):
    _require(isinstance(value, str) and ntpath.isabs(value)
             and re.fullmatch(r"DisposableMCPR[1-9][0-9]*\.uproject", ntpath.basename(value)) is not None,
             "guard.project", "absolute externally admitted numbered disposable project is required")
    return ntpath.normcase(ntpath.normpath(value.replace("/", "\\")))


def _messages(values, unreal_api, stage):
    _require(isinstance(values, (list, tuple, unreal_api.Array)), stage,
             "expected reflected FText array", "UNKNOWN")
    _require(all(isinstance(value, (str, unreal_api.Text)) for value in values), stage,
             "expected FText/string issue members", "UNKNOWN")
    return [str(value) for value in values]


def validate_object(asset, expected_project_file, validation_usecase, *, unreal_api, raising_exceptions):
    """Return explicit native enum/errors/warnings, with labeled derived counts.

    The reflected Python call has two inputs and returns exactly
    (EDataValidationResult, ValidationErrors, ValidationWarnings). A different
    runtime binding shape fails closed after the single call; it is never retried.
    """
    expected = _project_key(expected_project_file)
    _require(validation_usecase == "Script", "guard.usecase", "explicit Script usecase required")
    actual = _invoke("context.project", lambda: unreal_api.Paths.convert_relative_path_to_full(
        unreal_api.Paths.get_project_file_path()), raising_exceptions)
    _require(_project_key(actual) == expected, "guard.project", "actual project differs from external admission")
    _require(isinstance(asset, unreal_api.Object), "guard.asset", "already-resolved Unreal object required")
    asset_path = _invoke("context.asset_path", asset.get_path_name, raising_exceptions)
    _require(asset_path == FIXTURE_OBJECT_PATH, "guard.asset", "asset leaves exact owned validation fixture")
    editor = _invoke("context.editor", lambda: unreal_api.get_editor_subsystem(
        unreal_api.UnrealEditorSubsystem), raising_exceptions)
    _require(bool(editor), "guard.pie", "editor subsystem required to observe game world")
    game_world = _invoke("context.game_world", editor.get_game_world, raising_exceptions)
    _require(game_world is None, "guard.pie", "game world must be absent")
    subsystem = _invoke("context.validator", lambda: unreal_api.get_editor_subsystem(
        unreal_api.EditorValidatorSubsystem), raising_exceptions)
    _require(bool(subsystem), "guard.validator", "DataValidation subsystem unavailable")
    subsystem_class = _invoke("context.validator_class", lambda: subsystem.get_class().get_path_name(), raising_exceptions)
    _require(subsystem_class == "/Script/DataValidation.EditorValidatorSubsystem", "guard.validator",
             "unreviewed subsystem subclass is outside this fixture")

    returned = _invoke("native.IsObjectValid", lambda: subsystem.is_object_valid(
        asset, unreal_api.DataValidationUsecase.SCRIPT), raising_exceptions, "UNKNOWN")
    _require(isinstance(returned, tuple) and len(returned) == 3, "result.binding",
             "expected (result, errors, warnings) tuple", "UNKNOWN")
    native_result, native_errors, native_warnings = returned
    _require(isinstance(native_result, unreal_api.DataValidationResult), "result.enum",
             "expected native DataValidationResult enum", "UNKNOWN")
    states = ((unreal_api.DataValidationResult.VALID, "Valid"),
              (unreal_api.DataValidationResult.INVALID, "Invalid"),
              (unreal_api.DataValidationResult.NOT_VALIDATED, "NotValidated"))
    state = next((name for value, name in states if native_result == value), None)
    _require(state is not None, "result.enum", "unrecognized native validation enum", "UNKNOWN")
    errors = _invoke("result.errors", lambda: _messages(native_errors, unreal_api, "result.errors"),
                     raising_exceptions, "UNKNOWN")
    warnings = _invoke("result.warnings", lambda: _messages(native_warnings, unreal_api, "result.warnings"),
                       raising_exceptions, "UNKNOWN")
    same_path = _invoke("result.asset_identity", asset.get_path_name, raising_exceptions, "UNKNOWN")
    _require(same_path == asset_path, "result.asset_identity", "asset identity changed during validation", "UNKNOWN")
    accepted = state == "Valid" and not errors and not warnings
    return json.dumps({
        "schema": SCHEMA, "native_runtime_qualified": False,
        "caller_native_admission_required": True, "project_matches_external_expected": True,
        "native_api": "UEditorValidatorSubsystem.IsObjectValid", "validation_usecase": "Script",
        "requested": [asset_path], "validation_calls": 1, "result": state,
        "errors": errors, "warnings": warnings, "accepted": accepted,
        "counts_origin": "producer-derived from one returned per-object result; not FValidateAssetsResults",
        "counts": {"requested": 1, "returned": 1, "valid": int(state == "Valid"),
                   "invalid": int(state == "Invalid"), "not_validated": int(state == "NotValidated"),
                   "assets_with_warnings": int(bool(warnings)),
                   "error_messages": len(errors), "warning_messages": len(warnings)},
        "associated_objects_supplied": 0, "raw_logs_captured": False,
        "native_aggregate_results_captured": False, "validator_wide_messages_captured": False,
        "validator_callbacks_effects_proven": False, "automatic_retries": 0,
    }, sort_keys=True, allow_nan=False)
