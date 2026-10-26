# Epic integration acceptance recipe

This is the bounded acceptance recipe for the integration source, documentation and retained runtime witness. It depends on [PR #408](https://github.com/RicheyWorks/Daedalus2/pull/408) and [PR #409](https://github.com/RicheyWorks/Daedalus2/pull/409); those links do not assert their merge or adoption status. Run through the existing admitted editor connection and sole operator. These helpers add no transport, server, or authority to mutate another owner's work.

## Evidence and adoption boundary

| Gate | Current evidence | Limit |
| --- | --- | --- |
| First integration build | Exit 0; measured elapsed time 274.6032471 seconds | Compilation does not establish installation or runtime behavior. |
| Offline checks | 50 tests passed | Fakes and source contracts do not establish native acceptance. |
| Blueprint | Created, edited to integer 37, strictly compiled, exactly saved, and observed as 37 after two fresh-process reopens | Acceptance covers that owned asset and recorded process transitions; no property flags changed or world saved. |
| Slate | R1 **CRASHED**; repaired R2 **PASS**: all required fields true, click count 1, empty failure reason, protected state equal | Disposable fixture only; `production_ui_accepted=false`. The original crash remains failed evidence. |
| Native validation R1 | Three real native calls: Valid/accepted true, Invalid/accepted false, configured NotValidated returned aggregate Valid/accepted true | **Three-class coverage INCOMPLETE**. All snapshots retain `native_runtime_qualified=false`. |
| AutomationResultsR1 | Four exact tests returned `Success`; 4 passed, 0 failed/skipped, no errors/warnings; strict consumer accepted | Covers the two Slate tests, validation Policy, and NativeProjection. NamedFixtures was not run. |
| Import/reimport checks | New owned mesh + two materials imported and saved; one reimport preserved UObject, geometry, materials, socket, UCX, Nanite and lightmap override 128; restored 4 and saved | No production assets or world placement/save; no additional fresh-process reopen after this import. |

These results come from the retained `EpicIntegrationSprint20261019` receipts through final readback at 2026-10-19 16:53:16 UTC. The [runtime witness](../../tools/unreal_mcp/fixtures/epic_integration_20261019.json) retains actual results and receipt hashes. Final preservation verified all 1,352 protected saved files, 223 unchanged original source/config files and three approved source/config updates; six new owned fixture packages are saved. Maps/content were clean, the 22,878-actor scene and camera were unchanged, all owned operations were terminal, and compute was released normally at 16:54:09 UTC while the editor and sole Unreal custody were retained.

Keep **installed**, **live-tested**, and **adopted** separate. Installed means the intended binary and contracts were identified in the running editor. Live-tested means a particular admitted operation produced its required native observations. Adopted means its scoped acceptance and preservation evidence were reviewed. The recorded Blueprint, Slate, and four-test results do not establish blanket adoption of the complete batch or close the remaining three-class validation gap. Record installation identity with each later runtime result.

The retained recovery history includes the Slate R1 crash, a first recovery link attempt ending with exit 6 (`LNK1104`), and the later `RecoveryBuildR3` exit 0 in 9.6477064 seconds. The link failure does not establish which process held the DLL. The focused repair uses a pointer-aware path and detaches only the fixture's own content during cleanup. Later success does not replace the earlier failed receipts.

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
# Fixture-only; the installed repaired route passed as NativeSlateR2:
slate_reply = ue.DaedalusEditorAcceptanceLibrary.run_slate_button_fixture()
```

Validation delegates to the existing native `FDaedalusNativeValidationBridge`; it does not create another validation implementation. Its admission requires game-thread/editor/no-PIE state, no active compilation or registry discovery, and 1–16 distinct canonical, already-loaded, registered, clean, non-map assets within the explicit approved subtree. `/Game` alone is too broad. The bridge does not load, scan, save, or register validators. Existing validators and delegates can perform work; this is not a sandbox. Cancellation is checked before and after the synchronous native call and cannot interrupt a validator already executing.

Retain the complete envelope, including `native_invoked`, outcome, cancellation, diagnostics, and unchanged `snapshot_json`. Feed that exact snapshot string to [native_validation_snapshot_consumer.consume](../../tools/unreal_mcp/native_validation_snapshot_consumer.py). Parsing and consistency acceptance alone do not prove invocation. The supplied-struct projection path explicitly leaves `native_invoked=false` and `accepted=false`; `native_runtime_qualified` remains false by design.

The acceptance fixture honors `Valid`, `Invalid`, and `NotValidated` only beneath `/Game/CodexToolEvaluation/EpicIntegrationR1/Validation/`. In `NativeValidationR1`, the saved fixtures carried those three configurations and all three replies attest native invocation. Valid and Invalid produced the expected aggregate outcomes. The configured NotValidated fixture produced aggregate Valid, so it does not demonstrate a native NotValidated result. At aggregate level, a participant's NotValidated is neutral when another enabled validator contributes Valid; these receipts do not attribute the positive result to an individual validator. Do not change the consumer or relabel the fixture to turn this into complete three-class acceptance.

The Slate wrapper delegates to [FDaedalusSlateAcceptanceBridge](../../engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusSlateAcceptanceBridge.h), which owns a disposable virtual button/window/user, with no caller-selected production widget. The repair constructs a pointer-aware `FWidgetPath` with an optional pointer entry for each widget; an unset optional is the intended identity transform for this 2D fixture. Geometry-only path validity was insufficient for routing in the failed R1 attempt.

A passing receipt requires the refusal cases, exactly one handled click, focus preservation, release, and cleanup. `window_unregister_called=true` attests the explicit `UnregisterVirtualWindow` API call; it does not independently enumerate Slate's private registry. `owned_content_detached=true` separately observes that the owned button has no parent and its path can no longer be generated after replacing the fixture window's content with `SNullWidget`. NativeSlateR2 recorded both, all other required fields, click count 1, empty failure reason, and `protected_equal=true`. Its `production_ui_accepted` remains false. Future attempts still require fresh admission and the repaired installed source identity.

## Canonical serializer staging

The canonical [native_validation_result_snapshot.h](../../tools/unreal_mcp/native_validation_result_snapshot.h) is **30,250 bytes**, SHA256:

```text
8bde83421c0c7c0c1913cf6c9a9c6614e089ca78b84479a3b5e8ab9d869edfe7
```

The staging step in [setup-unreal.ps1](../../engines/unreal/setup-unreal.ps1) copies those exact bytes into the target plugin's `Build/AcceptedContracts/native_validation_result_snapshot.h` and compares source/destination SHA256, failing on mismatch. The setup script has broader project effects; it is not a read-only staging command. [DaedalusLink.Build.cs](../../engines/unreal/DaedalusLink/Source/DaedalusLink/DaedalusLink.Build.cs) prefers the repository canonical header, otherwise the staged header, and fails when neither exists. Build.cs checks existence, not the hash. Record the actual selected/staged fingerprint; do not maintain an independently edited serializer copy or silently accept a changed hash.

## Automation discovery, catalogue, and run

Use [AutomationResultContract](../../tools/unreal_mcp/automation_result_contract.py) with completed results from an already-admitted `Mcp` client. It supplies no dispatch, retry, editor qualification, or custody mechanism. `RunTests` stops existing tests before starting the requested set, so runner custody is required too.

```python
import json
from tools.unreal_mcp.automation_result_contract import (
    AutomationResultContract, TOOLSET,
)

requested = [
    "Daedalus.Slate.Acceptance.VirtualButton",
    "Daedalus.Slate.Acceptance.RepeatCleanup",
    "Daedalus.Editor.Validation.Policy",
    "Daedalus.Editor.Validation.NativeProjection",
]
contract = AutomationResultContract(requested)
contract.accept_discovery(
    m.call(TOOLSET, "DiscoverTests", bForceRediscover=False))
raw_catalogs = {}
for name in requested:
    value = m.call(TOOLSET, "ListTests", NameFilter=name,
                   TagFilter="", Limit=0)
    row = json.loads(value) if isinstance(value, str) else value
    if (row.get("tests") != [name] or row.get("total") != 1
            or row.get("returned") != 1):
        raise RuntimeError("exact catalogue differs")
    raw_catalogs[name] = row  # Retain every complete native catalogue.
contract.accept_catalog(dict(tests=requested, total=len(requested),
                             returned=len(requested)))
verdict = contract.evaluate_run(
    m.call(TOOLSET, "RunTests", TestNames=requested))
```

`TOOLSET` is `AutomationTestToolset.AutomationTestToolset`. The filter is a substring; `Limit=0` removes the cap. This recipe first requires each complete native catalogue to contain exactly its one requested name, then submits their exact union to the strict consumer; it does not trim broader results. Require matching counts and retain the raw catalogues. Failures, skips, warnings, unfinished results, or unknown transport outcomes cannot establish a pass or authorize replay. In AutomationResultsR1 all four named tests returned `Success`, and `strict-consumer-verdicts-r1.json` records `accepted=true`, `all_completed=true`, and no problems, while preserving `native_runtime_qualified=false`.

[NamedFixtures](../../engines/unreal/DaedalusLink/Source/DaedalusLink/Private/Tests/DaedalusNativeValidationBridgeTest.cpp) needs **three asset arguments plus a root: four editor-launch flags**, read from `FCommandLine`, not Automation `Parameters`:

```text
-DaedalusValidationFixtureRoot=<approved-owned-validation-subtree>
-DaedalusValidationValid=<exact-valid-fixture-object-path>
-DaedalusValidationInvalid=<exact-invalid-fixture-object-path>
-DaedalusValidationNotValidated=<exact-not-validated-fixture-object-path>
```

Prepare three distinct, already-loaded, registered, clean fixtures under the supported validation root before admitting that separate run. NamedFixtures makes three native validation calls and expects Valid/Invalid/NotValidated, accepting only Valid. **NamedFixtures was not part of the four-test run.** `Policy` checks policy; `NativeProjection` checks supplied-struct projection. Their recorded success does not close the NotValidated aggregate gap or attest the three native calls; those invocation receipts are separately retained in NativeValidationR1.

## Safe import and reimport acceptance

Reuse [harness_core.build_plan/evaluate](../../tools/unreal_mcp/interchange_harness/harness_core.py) and [ue_harness](../../tools/unreal_mcp/interchange_harness/ue_harness.py); do not introduce a parallel importer. `build_plan` requires a checkpoint path and verifies supplied source SHA256/byte count. Use a new, admitted owned `/Game` subtree, an exact expected output inventory, source/config pins, and a preservation baseline before import. A frozen profile's requested options override the explicit overrides dictionary; record the resulting plan rather than assuming the caller's flags won.

Dispatch `start(plan)` once. Retain its pipeline/options report, then reconcile completion with `poll()` and native `facts(plan)`. The current route retains the transient Interchange pipeline and passes its `SoftObjectPath`. A requested setting or `started=True` is not native readback. Check exact identities, geometry/bounds/units, material assignments, collision, Nanite, and any claimed sockets/LODs against the admitted profile.

For reimport, use `start(plan, reimport_obj=owned_existing_object)` only for the explicitly admitted owned object. Compare its identity and the preservation baseline afterward; never redirect reimport to an unrelated existing asset. Unknown async outcomes require readback, not another start.

Review facts before saving. `save(plan)` refuses dirty packages outside the destination and limits save passes, but that subtree guard does not prove every package inside it is authorized. Require the expected exact inventory, inspect save results and final dirty state, and retain evidence that unrelated packages, maps, actors, and source payloads were preserved. Import, save, reopen, and adoption remain separate gates.

The completed bounded attempt targets `/Game/CodexToolEvaluation/EpicIntegrationR1/Import/Prop_PracticeCrate`, with exactly three flat source-named packages: `Prop_PracticeCrate`, `Prop_PracticeCrate_M0` and `Prop_PracticeCrate_M1`. Source SHA256 is `4e83515ecb6c49139db195354651fd6e23cebdf6150b2011778755ec8c41581f` (18,576 bytes). Native facts show 264 triangles, bounds 52 by 53 by 50 cm, one 24-vertex UCX hull, Nanite off, two stable material references and a native Top socket. One import save pass saved all three packages; reimport preserved the same UObject and all recorded facts plus custom lightmap 128, then restored 4 and saved the mesh. No world placement or world save occurred.

The earlier resource-floor hold dispatched zero calls. Read-only reconciliation established the flat output layout before admitting those exact packages; nothing was renamed or imported again. Poll elapsed values include resource holds and observation delay and are not import performance measurements. The reused harness warning that glTF drops socket empties is stale: this run observed the native socket without a sidecar or socket edit. The raw held/error receipts remain retained.

## Official Inspector: one existing Details panel

This follow-up uses the installed official `SlateInspectorToolset`, separately from the disposable C++ button fixture. `BindExistingDetailsPanel()` in the acceptance library locates the existing primary Level Editor Details tab through its owning tab manager. It requires the exact manager, content and window identity, a docked foreground tab, visible ancestors and positive geometry. It refuses missing or hidden content rather than opening or activating a tab. Its ref comes from the official exported shared cache and must round-trip to the same widget.

Call the official toolset's reflected `Snapshot` with that nonempty ref, a fixed admitted depth and `bIncludeSourceLocations=true`. The result is accessibility text, not a screenshot. Empty text and `Error:` returns fail acceptance. Do not use an empty ref, default all-window snapshot, `WaitFor`, input tools or another owner's observer. Source-location mode uses the live subtree renderer with `bResetCache=false`; it can append or reuse refs for the root and emitted descendants. The capture effect is `scoped_shared_ref_append_or_reuse`, without an exactly-one-ref claim.

The first actual Details capture bound successfully but returned empty text at depth 2. The pure consumer rejected it and consumed no replay IDs. The installed renderer counts skipped structural containers toward depth: the no-selection panel has `SBorder → SActorDetails → SVerticalBox` before meaningful descendants. Source locates its no-selection text at depth 5. The source-grounded follow-up used a new fixed-depth-5 request and new capture/request identity; the failed depth-2 receipt remains intact. It returned the expected no-selection text and splitter, with source locations. The strict pure consumer accepted that same actual capture within its 300-second freshness limit. No trial-depth loop or extra capture for bookkeeping ran.

Retain the host-allocated capture UUID and request ID before dispatch, actual editor PID/start time and world, exact reflected request, real start/end UTC, raw returned text and UTF-8 hash, exact binding payload/hash and before/after preservation observations. The pure consumer checks these against independently retained caller expectations and a caller-owned consumed-ID set. Its internal freshness clock has a 300-second limit: never retimestamp old evidence or take another Snapshot for bookkeeping. Hashes prove integrity, not caller authentication. Consumer evidence remains caller-attested with `current_receiver_rechecked=false`; existing packet `plan_only` and `native_runtime_qualified=false` flags stay unchanged.

The [separate Inspector witness](../../tools/unreal_mcp/fixtures/official_details_panel_20261019.json) records the compiled source checkpoint, failed empty depth-2 attempt and accepted fixed-depth-5 follow-up. The actual 182-byte accessibility return is pinned by SHA256 `03e2871eaa8f0454de1a307bccb61880f81b8f1f242b92428704be7f32691e5e`. The consumer uses the reviewed R3 capture contract and an independent exact-integer `expected_max_depth=5`; matching the supplied payload alone is insufficient. Its source hashes match before and after consumption. Caller-owned replay state advances only for the accepted new capture/request.

Its coherent build exited 0 in 256.5301464 measured seconds. The fresh process also read Blueprint 37 and the saved owned import's geometry, materials, socket, one UCX hull, Nanite off and original lightmap 4. All 1,358 protected saved files and expected source/config bytes match; the staged canonical header hash is explicitly verified. Compute was normally released at 17:41:09 UTC while sole Unreal custody and the open editor were retained. The local host's initial missing import-path preflight failed before any compute claim or native dispatch; that failure and correction are retained. No native request was replayed to resolve it.

For pure receipt consumption, supply expectations from the independently retained host dispatch and launch records:

```python
verdict = read_panel_capture(
    terminal["result"],
    expected_process_id=host_dispatch["pid"],
    expected_process_start_utc=host_dispatch["process_start_utc"],
    expected_world=host_dispatch["world"],
    expected_capture_id=host_dispatch["capture_id"],
    expected_request_id=host_dispatch["request_id"],
    expected_max_depth=5,
    consumed_capture_ids=retained_consumed_ids,
)
```

The pure consumer is delivered separately in [PR #411](https://github.com/RicheyWorks/Daedalus2/pull/411). This observed acceptance covers one existing Details panel's binding, bounded accessibility snapshot and strict same-capture consumption. It does not add input, observer, screenshot or production UI coverage, close the validation aggregate gap, or change generic parser/packet qualification flags.
