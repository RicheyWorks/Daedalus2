# Epic integration acceptance recipe

This is the bounded acceptance recipe for the source integration. It depends on [PR #408](https://github.com/RicheyWorks/Daedalus2/pull/408) and [PR #409](https://github.com/RicheyWorks/Daedalus2/pull/409); those links do not assert their merge or adoption status. Run through the existing admitted editor connection and sole operator. These helpers add no transport, server, or authority to mutate another owner's work.

## Evidence and adoption boundary

| Gate | Current evidence | Limit |
| --- | --- | --- |
| First integration build | Exit 0; measured elapsed time 274.6032471 seconds | Compilation does not establish installation or runtime behavior. |
| Offline checks | 50 tests passed | Fakes and source contracts do not establish native acceptance. |
| Blueprint | Created, edited to integer 37, strictly compiled, saved, and reopened with 37 | Acceptance covers that owned asset and recorded process transition. |
| Slate R1 | **CRASHED** during the geometry-only `FWidgetPath` route with empty pointer positions | Pointer-aware routing and owned-content detachment repaired and rebuilt (exit 0, 9.6477064 seconds). Recovery acceptance is pending; the original crash remains failed evidence. |
| Native validation | **NOT RUN** | Policy and snapshot checks are not a native invocation receipt. |
| Automation | **NOT RUN** | Discovery, catalogue, and completed native run still need receipts. |
| Import/reimport checks | **NOT RUN** | Existing harness capability is not evidence for this integration. |

Keep **installed**, **live-tested**, and **adopted** separate. Installed means the intended binary and contracts were identified in the running editor. Live-tested means a particular admitted operation produced its required native observations. Adopted means its scoped acceptance and preservation evidence were reviewed. The Blueprint result and failed Slate attempt do not establish blanket adoption of the complete batch. Record installation identity with each later runtime result.

## Admission and Blueprint acceptance

Use [blueprint_editor_context.py](../../tools/unreal_mcp/blueprint_editor_context.py) and [blueprint_acceptance.py](../../tools/unreal_mcp/blueprint_acceptance.py). The context contract pins engine `5.8.3-58210709+++UE5+Release-5.8`, the caller's expected project identity, editor subsystems, and observed no-PIE/no-game-world state. Its qualification is `EDITOR_CONTEXT_ONLY`: it does not relax property flags or stock editability checks, manufacture subsystems, or prove a setter succeeded. Nullable editor-world/current-level reads are allowed for this asset-only Actor CDO operation.

Before dispatch, establish sole custody, no conflicting operation, preservation of existing work, and a durable journal. An exception or lost response after dispatch is an unknown outcome: reconcile exact asset state before considering another mutation. Do not replay a create, setter, or save merely because its response is missing.

The caller supplies the installed stock `BlueprintTools`, `ObjectTools`, raising-exceptions context, expected project file, and receipt recorder:

```python
from tools.unreal_mcp.blueprint_acceptance import (
    create_edit_compile, save_exact, fresh_readback,
)

common = dict(unreal_api=ue, object_tools=ObjectTools,
              raising_exceptions=raising_exceptions,
              expected_project_file=expected_project_file, record=record)
create_edit_compile(blueprint_tools=BlueprintTools, **common)
# Review the unsaved result and exact dirty-package state first.
save_exact(**common)
# Only after the operator proves a normal reopen in a fresh editor process:
fresh_readback(**common)
```

The fixed target is `/Game/CodexToolEvaluation/EpicIntegrationR1/BP_CompileReceipt`, variable `AuditValue`, target integer `37`.

1. Refuse an existing destination and any pre-existing dirty map/content. Create with the reflected class object `ue.Actor.static_class()`, not the Python `ue.Actor` type.
2. Add the integer variable using stock APIs; compile with `warnings_as_errors=True`. Observe an exact Actor CDO, typed integer default `0`, and `UP_TO_DATE` status.
3. Requalify context, record the setter dispatch, and call the stock property setter exactly once. Require literal `True`, strict compilation, typed integer `37`, and `UP_TO_DATE`. This phase remains unsaved.
4. `save_exact` permits only the owned package to be dirty and no dirty maps. Require literal `True` from the exact loaded-asset save, fresh value/status readback, and empty dirty map/content lists afterward.
5. Record fresh process identity outside the helper. `fresh_readback` must load the exact asset, observe typed `37` and `UP_TO_DATE`, and observe clean dirty lists. Its return value cannot itself prove a new process.

Do not delete or replace an existing target to make this recipe pass. A later attempt needs a separately reviewed owned target or an explicit reconciliation of the original attempt.

## Reflected native validation and Slate

The root [DaedalusEditorAcceptanceLibrary](../../engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusEditorAcceptanceLibrary.h) exposes JSON-returning wrappers:

```python
validation_reply = ue.DaedalusEditorAcceptanceLibrary.validate_named_assets(
    asset_object_paths, allowed_package_root, False)
# Fixture-only; currently blocked by the recorded Slate R1 crash:
# slate_reply = ue.DaedalusEditorAcceptanceLibrary.run_slate_button_fixture()
```

Validation delegates to the existing native `FDaedalusNativeValidationBridge`; it does not create another validation implementation. Its admission requires game-thread/editor/no-PIE state, no active compilation or registry discovery, and 1–16 distinct canonical, already-loaded, registered, clean, non-map assets within the explicit approved subtree. `/Game` alone is too broad. The bridge does not load, scan, save, or register validators. Existing validators and delegates can perform work; this is not a sandbox. Cancellation is checked before and after the synchronous native call and cannot interrupt a validator already executing.

Retain the complete envelope, including `native_invoked`, outcome, cancellation, diagnostics, and unchanged `snapshot_json`. Feed that exact snapshot string to [native_validation_snapshot_consumer.consume](../../tools/unreal_mcp/native_validation_snapshot_consumer.py). Parsing and consistency acceptance alone do not prove invocation. The supplied-struct projection path explicitly leaves `native_invoked=false` and `accepted=false`; `native_runtime_qualified` remains false by design.

The acceptance fixture honors `Valid`, `Invalid`, and `NotValidated` only beneath `/Game/CodexToolEvaluation/EpicIntegrationR1/Validation/`. The Slate wrapper delegates to [FDaedalusSlateAcceptanceBridge](../../engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusSlateAcceptanceBridge.h), which owns a disposable virtual button/window/user, with no caller-selected production widget. A passing receipt must prove refusal cases, exactly one handled click, focus preservation, release, and cleanup; `production_ui_accepted` remains false. **Do not rerun the crashed R1 route until the owner fix is installed and the new attempt is freshly admitted.**

## Canonical serializer staging

The canonical [native_validation_result_snapshot.h](../../tools/unreal_mcp/native_validation_result_snapshot.h) is **30,250 bytes**, SHA256:

```text
8bde83421c0c7c0c1913cf6c9a9c6614e089ca78b84479a3b5e8ab9d869edfe7
```

The staging step in [setup-unreal.ps1](../../engines/unreal/setup-unreal.ps1) copies those exact bytes into the target plugin's `Build/AcceptedContracts/native_validation_result_snapshot.h` and compares source/destination SHA256, failing on mismatch. The setup script has broader project effects; it is not a read-only staging command. [DaedalusLink.Build.cs](../../engines/unreal/DaedalusLink/Source/DaedalusLink/DaedalusLink.Build.cs) prefers the repository canonical header, otherwise the staged header, and fails when neither exists. Build.cs checks existence, not the hash. Record the actual selected/staged fingerprint; do not maintain an independently edited serializer copy or silently accept a changed hash.

## Automation discovery, catalogue, and run

Use [AutomationResultContract](../../tools/unreal_mcp/automation_result_contract.py) with completed results from an already-admitted `Mcp` client. It supplies no dispatch, retry, editor qualification, or custody mechanism. `RunTests` stops existing tests before starting the requested set, so runner custody is required too.

```python
from tools.unreal_mcp.automation_result_contract import (
    AutomationResultContract, TOOLSET,
)

requested = [
    "Daedalus.Editor.Validation.Policy",
    "Daedalus.Editor.Validation.NativeProjection",
    "Daedalus.Editor.Validation.NamedFixtures",
]
contract = AutomationResultContract(requested)
contract.accept_discovery(
    m.call(TOOLSET, "DiscoverTests", bForceRediscover=False))
contract.accept_catalog(m.call(
    TOOLSET, "ListTests", NameFilter="Daedalus.Editor.Validation.",
    TagFilter="", Limit=0))
verdict = contract.evaluate_run(
    m.call(TOOLSET, "RunTests", TestNames=requested))
```

`TOOLSET` is `AutomationTestToolset.AutomationTestToolset`. The filter is a substring; `Limit=0` removes the cap. Require the exact requested catalogue and matching total/returned counts; do not locally trim broader results. Failures, skips, warnings, unfinished results, or unknown transport outcomes cannot establish a pass or authorize replay.

[NamedFixtures](../../engines/unreal/DaedalusLink/Source/DaedalusLink/Private/Tests/DaedalusNativeValidationBridgeTest.cpp) needs **three asset arguments plus a root: four editor-launch flags**, read from `FCommandLine`, not Automation `Parameters`:

```text
-DaedalusValidationFixtureRoot=<approved-owned-validation-subtree>
-DaedalusValidationValid=<exact-valid-fixture-object-path>
-DaedalusValidationInvalid=<exact-invalid-fixture-object-path>
-DaedalusValidationNotValidated=<exact-not-validated-fixture-object-path>
```

Prepare three distinct, already-loaded, registered, clean fixtures under the supported validation root before admitting the run. NamedFixtures makes three native validation calls and expects Valid/Invalid/NotValidated, accepting only Valid. `Policy` checks policy; `NativeProjection` checks supplied-struct projection. Passing either does not attest a native validation invocation. The current integration has not run these checks.

## Safe import and reimport acceptance

Reuse [harness_core.build_plan/evaluate](../../tools/unreal_mcp/interchange_harness/harness_core.py) and [ue_harness](../../tools/unreal_mcp/interchange_harness/ue_harness.py); do not introduce a parallel importer. `build_plan` requires a checkpoint path and verifies supplied source SHA256/byte count. Use a new, admitted owned `/Game` subtree, an exact expected output inventory, source/config pins, and a preservation baseline before import. A frozen profile's requested options override the explicit overrides dictionary; record the resulting plan rather than assuming the caller's flags won.

Dispatch `start(plan)` once. Retain its pipeline/options report, then reconcile completion with `poll()` and native `facts(plan)`. The current route retains the transient Interchange pipeline and passes its `SoftObjectPath`. A requested setting or `started=True` is not native readback. Check exact identities, geometry/bounds/units, material assignments, collision, Nanite, and any claimed sockets/LODs against the admitted profile.

For reimport, use `start(plan, reimport_obj=owned_existing_object)` only for the explicitly admitted owned object. Compare its identity and the preservation baseline afterward; never redirect reimport to an unrelated existing asset. Unknown async outcomes require readback, not another start.

Review facts before saving. `save(plan)` refuses dirty packages outside the destination and limits save passes, but that subtree guard does not prove every package inside it is authorized. Require the expected exact inventory, inspect save results and final dirty state, and retain evidence that unrelated packages, maps, actors, and source payloads were preserved. Import, save, reopen, and adoption remain separate gates. This integration's import/reimport acceptance is **NOT RUN**.
