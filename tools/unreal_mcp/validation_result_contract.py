# SPDX-License-Identifier: MIT
"""Pure acceptance of explicit C++ DataValidation member snapshots.

This is NOT a discovered MCP/Python wire schema or an exposed native callable.
UE 5.8.3 has an instance BlueprintCallable ValidateAssetsWithSettings API, but
no existing official toolset binding was found. DataValidation is outside the
reviewed R6 plugin closure. A future separately admitted native producer must
capture fresh settings/results, including non-reflected ValidatorMessages and
AssetsDetails members. This consumer neither loads that plugin nor runs it.

The supported contract is a nonempty exact set of ordinary standalone object
paths. External-object/owner substitution, accumulated results, missing per-asset
identity, skipped/unchecked assets, warnings, and limit hits cannot pass.
"""
import re

from .automation_result_contract import _count, _require


NATIVE_RUNTIME_QUALIFIED = False
OFFICIAL_MCP_CALLABLE_VERIFIED = False
SOURCE_PROVENANCE = {
    "engine": "UE 5.8.3 / changelist 58210709",
    "plugin": "Engine/Plugins/Editor/DataValidation/DataValidation.uplugin",
    "plugin_sha256": "d0d847d443bd29d92aa16f3f8a6cd7f2776a042bd2140a8e6242650681600ce2",
    "header_sha256": "463558fd5bc145575def4caa75eb22d49a1c06dab7e1e0b927dd9781fc058174",
    "implementation_sha256": "c7a758c926f413240cfa598ab90af296db9dc39584c43ae3d56f7dbe2546b0a8",
    "module_build_sha256": "1ba5fb815558c9f75e3d0fdb6c598d1c6e03387a6a1788aff3f62380eb986820",
    "source_lines": "EditorValidatorSubsystem.h:46-222,287-293; EditorValidatorSubsystem.cpp:699-735,767-826,998-1099",
    "native_seam": "DataValidationModule.cpp:360-375; GEditor->GetEditorSubsystem<UEditorValidatorSubsystem>()",
    "binding_limit": "instance BlueprintCallable; not static/AICallable; AssetsDetails members lack UPROPERTY",
}


def evaluate_native_validation(requested_assets, native_return, results, settings):
    """Check native counts and explicit identity; never reinterpret int as bool.

    Arguments use exact native member names, not assumed snake_case aliases.
    Detail Result is projected explicitly as the native enum name ("Valid");
    this is a snapshot convention, not a claim about reflection serialization.
    Snapshot provenance, fresh OutResults and the actual native invocation are
    caller obligations; a syntactically passing snapshot cannot prove them.
    ``MaxAssetsToValidate`` must exceed the request size because native code
    marks the limit reached even at exact equality without omitted assets.
    """
    _require(isinstance(requested_assets, (list, tuple)) and bool(requested_assets),
             "requested assets must be nonempty")
    _require(all(isinstance(path, str) and re.fullmatch(
        r"/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.[A-Za-z0-9_]+", path)
        for path in requested_assets), "expected exact ordinary ASCII top-level object paths")
    _require(len(set(requested_assets)) == len(requested_assets), "duplicate requested asset")
    _require(isinstance(results, dict) and isinstance(settings, dict), "expected native member snapshots")
    fields = ("NumRequested", "NumExternalObjects", "NumChecked", "NumValid", "NumInvalid",
              "NumSkipped", "NumWarnings", "NumUnableToValidate")
    counts = {field: _count(results.get(field), field) for field in fields}
    _count(native_return, "native return")
    _require(type(results.get("bAssetLimitReached")) is bool, "invalid asset limit flag")
    _require(native_return == counts["NumWarnings"] + counts["NumInvalid"],
             "native return must equal warning count plus invalid count")
    _require(counts["NumValid"] + counts["NumInvalid"] + counts["NumUnableToValidate"]
             == counts["NumChecked"], "validation result buckets differ from checked")
    _require(counts["NumWarnings"] <= counts["NumChecked"], "warnings exceed checked assets")
    _require(counts["NumChecked"] + counts["NumSkipped"] <= counts["NumRequested"],
             "processed assets exceed requested count; results may not be fresh")
    bool_fields = ("bLoadAssetsForValidation", "bLoadExternalObjectsForValidation",
                   "bCollectPerAssetDetails", "bCaptureAssetLoadLogs", "bCaptureLogsDuringValidation")
    for field in bool_fields:
        _require(type(settings.get(field)) is bool, "missing explicit setting: " + field)
    maximum = _count(settings.get("MaxAssetsToValidate"), "MaxAssetsToValidate")
    details = results.get("AssetsDetails")
    messages = results.get("ValidatorMessages")
    _require(isinstance(details, dict), "native AssetsDetails snapshot is required")
    _require(isinstance(messages, list), "non-reflected native ValidatorMessages snapshot is required")
    expected = len(requested_assets)
    problems = []
    if counts["NumRequested"] != expected:
        problems.append("requested_count_changed_or_owner_substituted")
    if counts["NumExternalObjects"]:
        problems.append("external_objects_outside_contract")
    if counts["NumChecked"] != expected or counts["NumValid"] != expected:
        problems.append("not_all_requested_assets_checked_and_valid")
    for field in ("NumInvalid", "NumSkipped", "NumUnableToValidate", "NumWarnings"):
        if counts[field]:
            problems.append(field)
    if results["bAssetLimitReached"] or maximum <= expected:
        problems.append("asset_limit_reached_or_insufficient_headroom")
    if set(details) != set(requested_assets):
        problems.append("per_asset_identity_not_exact")
    else:
        for path in requested_assets:
            detail = details[path]
            package_name, asset_name = path.split(".")
            if (not isinstance(detail, dict)
                    or detail.get("PackageName") != package_name
                    or detail.get("AssetName") != asset_name
                    or detail.get("Result") != "Valid"
                    or any(detail.get(field) != [] for field in (
                        "ValidationErrors", "ValidationWarnings", "ValidationMessages", "ExternalObjects"))):
                problems.append("per_asset_details_not_explicitly_valid: " + path)
    if messages:
        problems.append("validator_wide_messages_require_review")
    if not all(settings[field] for field in bool_fields if field != "bLoadExternalObjectsForValidation"):
        problems.append("loading_details_or_log_capture_disabled")
    return {"accepted": not problems, "outcome": "passed" if not problems else "not_accepted",
            "requested": list(requested_assets), "counts": counts, "native_return": native_return,
            "problems": problems, "native_runtime_qualified": NATIVE_RUNTIME_QUALIFIED,
            "official_mcp_callable_verified": OFFICIAL_MCP_CALLABLE_VERIFIED,
            "snapshot_kind": "explicit_native_members_not_mcp_schema"}
