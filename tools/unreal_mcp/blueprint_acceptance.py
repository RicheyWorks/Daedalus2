# SPDX-License-Identifier: MIT
"""One owned Blueprint acceptance using the installed, unchanged Epic tools.

The caller owns admission, a durable no-replay journal and game-thread dispatch.
No tool or transport is registered here. Creation and exact save are separate
stages so a failed edit cannot be presented as a saved success. The previous
disposable-project diagnostic and its failed receipts remain unchanged.
"""
from __future__ import annotations

import json

from .blueprint_editor_context import collect_context, qualify


FOLDER = "/Game/CodexToolEvaluation/EpicIntegrationR1"
NAME = "BP_CompileReceipt"
PACKAGE = FOLDER + "/" + NAME
OBJECT = PACKAGE + "." + NAME
VARIABLE = "AuditValue"
TARGET = 37


class AcceptanceHold(RuntimeError):
    def __init__(self, stage, detail, effects="NONE"):
        self.stage, self.effects = stage, effects
        super().__init__(f"Blueprint acceptance {stage}: {detail}; effects={effects}; reconcile, never replay")


def _require(condition, stage, detail, effects="NONE"):
    if not condition:
        raise AcceptanceHold(stage, detail, effects)


def _invoke(stage, operation, raising_exceptions, *, effects="UNKNOWN"):
    try:
        with raising_exceptions():
            return operation()
    except AcceptanceHold:
        raise
    except Exception as exc:
        raise AcceptanceHold(stage, f"{type(exc).__name__}: {str(exc) or '<empty message>'}", effects) from exc


def _facts_unchecked(bp, ue, objects, raising_exceptions):
    _require(isinstance(bp, ue.Blueprint) and bp.get_path_name() == OBJECT,
             "identity", "only the exact owned Blueprint is admitted", "UNKNOWN")
    generated = bp.generated_class()
    _require(generated is not None and generated.get_path_name() == OBJECT + "_C",
             "generated_class", "the exact generated class is required", "UNKNOWN")
    cdo = ue.get_default_object(generated)
    _require(isinstance(cdo, ue.Actor) and cdo.get_world() is None,
             "cdo", "an Actor CDO without a world is required", "UNKNOWN")
    raw = _invoke("read_default", lambda: objects.get_properties(bp, [VARIABLE]), raising_exceptions)
    try:
        values = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise AcceptanceHold("read_default", "stock property response is not JSON", "UNKNOWN") from exc
    _require(isinstance(values, dict) and set(values) == {VARIABLE} and type(values[VARIABLE]) is int,
             "read_default", "one exact integer AuditValue is required", "UNKNOWN")
    status = bp.get_editor_property("status")
    return {"object": bp.get_path_name(), "generated_class": generated.get_path_name(),
            "cdo": cdo.get_path_name(), "cdo_world": None, "value": values[VARIABLE],
            "status": str(status), "up_to_date": status == ue.BlueprintStatus.BS_UP_TO_DATE}


def _facts(bp, ue, objects, raising_exceptions):
    try:
        return _facts_unchecked(bp, ue, objects, raising_exceptions)
    except AcceptanceHold:
        raise
    except Exception as exc:
        raise AcceptanceHold("observe_facts", f"{type(exc).__name__}: {str(exc) or '<empty message>'}",
                             "UNKNOWN") from exc


def _dirty(ue, raising_exceptions):
    return _invoke("observe_dirty", lambda: {
        "maps": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
        "content": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())},
        raising_exceptions)


def create_edit_compile(*, unreal_api, blueprint_tools, object_tools,
                        raising_exceptions, expected_project_file, record):
    """Create once; compile; invoke the stock 0->37 setter once; compile again.

    Does not save. Any exception after creation requires reconciliation against
    the caller's retained stage journal. It never deletes, retries or changes
    object/property flags, maps, actors, editor settings or subsystem registration.
    """
    ue = unreal_api
    context = qualify(collect_context(unreal_api=ue), expected_project_file)
    _require(not ue.EditorAssetLibrary.does_asset_exist(PACKAGE),
             "pre_create", "owned destination already exists; refuse replacement")
    _require(not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
             and not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
             "pre_create", "unrelated dirty work must be preserved before admission")
    record("context_qualified_before_create", {"context": context, "object": OBJECT})
    bp = _invoke("create", lambda: blueprint_tools.create(FOLDER, NAME, ue.Actor.static_class()),
                 raising_exceptions)
    created_path = _invoke("created_identity", bp.get_path_name, raising_exceptions)
    record("created_unsaved", {"object": created_path})
    _require(created_path == OBJECT, "created_identity", "unexpected created object", "UNKNOWN")
    _invoke("add_variable", lambda: blueprint_tools.add_variable(bp, VARIABLE, "int"), raising_exceptions)
    _invoke("compile_zero", lambda: blueprint_tools.compile_blueprint(bp, warnings_as_errors=True),
            raising_exceptions)
    before = _facts(bp, ue, object_tools, raising_exceptions)
    record("compiled_zero", before)
    _require(before["up_to_date"] and before["value"] == 0,
             "compiled_zero", "expected compiled integer default zero", "UNKNOWN")
    _invoke("context_before_set", lambda: qualify(collect_context(unreal_api=ue), expected_project_file),
            raising_exceptions)
    record("stock_setter_dispatch", {"object": OBJECT, "from": 0, "to": TARGET})
    changed = _invoke("stock_setter", lambda: object_tools.set_properties(
        bp, json.dumps({VARIABLE: TARGET})), raising_exceptions)
    _require(changed is True, "stock_setter", "stock setter did not return literal True", "UNKNOWN")
    _invoke("compile_target", lambda: blueprint_tools.compile_blueprint(bp, warnings_as_errors=True),
            raising_exceptions)
    after = _facts(bp, ue, object_tools, raising_exceptions)
    record("compiled_target_unsaved", after)
    _require(after["up_to_date"] and after["value"] == TARGET,
             "compiled_target", "compiled default must be exactly 37", "UNKNOWN")
    return after


def save_exact(*, unreal_api, object_tools, raising_exceptions,
               expected_project_file, record):
    """Save only the already-admitted exact Blueprint after a fresh context read."""
    ue = unreal_api
    qualify(collect_context(unreal_api=ue), expected_project_file)
    bp = _invoke("find_owned", lambda: ue.find_object(None, OBJECT), raising_exceptions)
    facts = _facts(bp, ue, object_tools, raising_exceptions)
    _require(facts["up_to_date"] and facts["value"] == TARGET,
             "pre_save", "a compiled value-37 Blueprint is required", "UNKNOWN")
    dirty_before = _dirty(ue, raising_exceptions)
    dirty_maps, dirty_content = dirty_before["maps"], dirty_before["content"]
    _require(not dirty_maps and set(dirty_content).issubset({PACKAGE}),
             "pre_save", "unrelated dirty packages are held", "UNKNOWN")
    record("exact_save_dispatch", {"object": OBJECT, "dirty_before": dirty_content})
    saved = _invoke("exact_save", lambda: ue.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=True),
                    raising_exceptions)
    _require(saved is True, "exact_save", "save did not return literal True", "UNKNOWN")
    after = _facts(bp, ue, object_tools, raising_exceptions)
    dirty_after = _dirty(ue, raising_exceptions)
    remaining, remaining_maps = dirty_after["content"], dirty_after["maps"]
    record("post_save_observation", {**after, "saved": saved, "dirty_content": remaining,
                                     "dirty_maps": remaining_maps})
    _require(after["up_to_date"] and after["value"] == TARGET,
             "post_save", "saved compiled default changed during save", "UNKNOWN")
    _require(not remaining and not remaining_maps,
             "post_save", "save did not retain clean packages", "UNKNOWN")
    result = {**after, "saved": saved, "dirty_after": remaining,
              "fresh_process_reopen": False, "property_flags_changed": False}
    record("exact_saved_readback", result)
    return result


def fresh_readback(*, unreal_api, object_tools, raising_exceptions,
                   expected_project_file, record):
    """Read the exact saved asset; the caller must prove this is a fresh process."""
    ue = unreal_api
    qualify(collect_context(unreal_api=ue), expected_project_file)
    bp = _invoke("load_owned_saved", lambda: ue.EditorAssetLibrary.load_asset(OBJECT),
                 raising_exceptions, effects="READ_ONLY")
    facts = _facts(bp, ue, object_tools, raising_exceptions)
    _require(facts["up_to_date"] and facts["value"] == TARGET,
             "fresh_readback", "saved compiled default is not exactly 37", "READ_ONLY")
    dirty_after = _dirty(ue, raising_exceptions)
    _require(not dirty_after["maps"] and not dirty_after["content"],
             "fresh_readback", "readback did not retain clean packages", "READ_ONLY")
    record("saved_asset_readback", facts)
    return {**facts, "fresh_process_identity_requires_caller_proof": True}
