# Research notes and roadmap (2026-10-11)

Two surveys informed this connector:
1. **Outside:** open-source Unreal MCP servers and agent bridges, Epic's documentation and forums, issue
   trackers, and community threads.
2. **Inside:** the automation harnesses already built in [CSRBT](https://github.com/RicheyWorks/CSRBT) and
   [FlowersForever](https://github.com/RicheyWorks/FlowersForever).

## Adopted

- **Unattended execution through Unreal's own Python Remote Execution.** `remote_execution.py`
  (PythonScriptPlugin) sends `unattended: true` with each command. That sets `GIsRunningUnattendedScript`,
  which makes the editor cancel modal dialogs ("suppressing some UI") instead of blocking the game thread.
  - Verified on UE 5.8.3: `run_command(self, command, unattended=True, exec_mode=...)`.
  - The bridge sends `execute_python` this way from a background thread and yields editor ticks while it
    waits. `install.ps1` sets `bRemoteExecution=True`.
  - Sources: [EPythonCommandFlags](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/PythonScriptPlugin/EPythonCommandFlags),
    [IAMSamuelRodda/mcp-unreal](https://github.com/IAMSamuelRodda/mcp-unreal),
    [groscy/unreal-mcp](https://github.com/groscy/unreal-mcp).
- **The outside-the-editor window harness** (`win.ps1`) stays as the fallback for dialogs that unattended
  mode doesn't cover. No other project we found answers dialogs from outside the editor.

## Next (ranked)

1. **Job ids and a result journal** for long commands. The client never resends, and polls for the result
   by id, so a slow import can't time out and run twice. ([chisomobanzi/Unreal-MCP](https://github.com/chisomobanzi/Unreal-MCP),
   [BatSasha52/GameplayMCPToolset](https://github.com/BatSasha52/GameplayMCPToolset))
2. **`batch`:** many commands in one call, under one `unreal.ScopedEditorTransaction` (one undo).
3. **A gateway contract with a risk ladder,** from CSRBT's `tools/harness_contract.py` (the Java form is
   FlowersForever's `HarnessGateway`).
   - Every command declares its risk: READ (status, level, log), SENSITIVE_READ (screenshot), MUTATE
     (execute_python, import), DESTRUCTIVE (save, delete).
   - The MCP layer derives `readOnlyHint` and `destructiveHint` from the risk.
   - `request_id` replay.
4. **A walk ledger.** Drive every command in `list_commands` from its schema, and account
   `discovered == driven + refused + failed + excluded`. A new command with no test then shows up as
   UNACCOUNTED. (CSRBT `tools/harness_walk.py`)
5. **A mutant runner for the bridge**, catalogued as (name, file, old, new, why), recorded with
   `mutant_ledger.record()`. Example mutants:
   - drain one job per tick
   - remove the re-entry guard
   - report an error as ok
   - a huge timeout

   (CSRBT `tools/mutate_run_all.py`, `tools/mutant_ledger.py`)
6. **Floors:** a minimum check count per suite, so a suite that silently runs 0 checks is red.
   (FlowersForever `scripts/verify_harness.py`, CSRBT `tools/verify/floors.json`)
7. **Faster, UI-free screenshots:** a `SceneCapture2D` into a `TextureRenderTarget2D`, then
   `RenderingLibrary.export_render_target`. Before capturing, wait on `FinishAllAssetCompilation` and
   shader compilation, which avoids black frames.
8. **Pre-seeded suppressible dialogs.** Write `SuppressableDialogs` keys into
   `Saved/Config/Windows/EditorPerProjectUserSettings.ini` before launch. Unverified section name.
9. **Watch Epic's official "Unreal MCP"** (experimental in UE 5.8: HTTP at 127.0.0.1:8000/mcp, Python
   toolsets via `unreal.ToolsetDefinition`). A bridge command set could also be published as a toolset.
   It says nothing about dialogs, which is where this connector is different.

## Pitfalls to guard against

- **A UE 5.8.3 PythonScriptPlugin GC crash** with closures held in Python reference cycles
  ([forum](https://forums.unrealengine.com/t/ue5-8-pythonscriptplugin-crash-during-gc-fpycfunctionwithclosureobject-layout-omits-weakref-vectorcall-fields/2776052)).
  Register module-level functions for tick callbacks; the bridge's `pump` is one.
- **Silent no-ops in the Python API:**
  - Python names are snake_case.
  - Blueprint class paths need `_C`.
  - Interchange imports are async.
  - Edits need `PostEditChangeProperty` / `set_editor_property`.

  ([ibrews/ue5-mcp](https://github.com/ibrews/ue5-mcp))
- **Saving:** the editor doesn't auto-save, so call `save` after changes.

## Projects surveyed

- [Epic Unreal MCP](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)
- [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)
- [flopperam/unreal-engine-mcp](https://github.com/flopperam/unreal-engine-mcp)
- [remiphilippe/mcp-unreal](https://github.com/remiphilippe/mcp-unreal)
- [unreal-engine-mcp (PyPI)](https://pypi.org/project/unreal-engine-mcp/)
- [groscy/unreal-mcp](https://github.com/groscy/unreal-mcp)
- [IAMSamuelRodda/mcp-unreal](https://github.com/IAMSamuelRodda/mcp-unreal)
- [chisomobanzi/Unreal-MCP](https://github.com/chisomobanzi/Unreal-MCP)
- [BatSasha52/GameplayMCPToolset](https://github.com/BatSasha52/GameplayMCPToolset)
- [ibrews/ue5-mcp](https://github.com/ibrews/ue5-mcp)
- More under the GitHub topic [unreal-mcp](https://github.com/topics/unreal-mcp).

Reddit and X added little beyond these; GitHub, Epic's docs and Epic's forums held the substance.


## Engineering research consolidation (2026-10-14)

This append records the source audits and engineering findings already shared with the team. The older ranked Next list above is historical; this dated status is the current handoff. Original text is preserved. Research findings are design evidence, not proof that another framework or a proposed capability runs in Daedalus.

Ownership: Buff owns documentation and canonical lessons; Root/PootScoot coordinates this factual append. Coding proceeds independently. An owner below identifies an accepted work assignment; unclaimed means coordination is still required. All cited implementation PRs were OPEN when checked on 2026-10-14. Source implemented, draft, or CI green does not mean merged, installed, deployed, or accepted in the shared editor.

### Source implementations and active work

| Priority | Work and actual owner | Current status and evidence | Acceptance boundary |
| --- | --- | --- | --- |
| P0 | Bridge shutdown cleanup — Root/PootScoot | Source implementation completed on the isolated bridge-stop-cleanup branch; PR publication and CI pending at this append. Baseline stop removed listener/tick but left queued requests, suspended generators, and reply boxes. Offline 21 lifecycle units + 27 transport + 21 walk + 10 steps checks reported passing; independent source review found no blocking issue. This is not live acceptance. | Release pending waiters with truthful interruption errors, run owned generator cleanup on the game thread, preserve completed results, survive cleanup failures/repeated stop, and perform no editor relaunch. Already dispatched remote Python may still have effects; no rollback claim. |
| P0 | Async command discovery — Root/PootScoot, [PR103](https://github.com/RicheyWorks/Daedalus2/pull/103), a0ec9229 | Source implemented in an open draft: metadata advertises existing async acceptance, exact job_result polling, nested terminal status, and process-local retention. 31 transport checks and all four CI checks reported green. This did not add durable execution or cancellation. | Submit once, poll the accepted ID, inspect the nested reply to distinguish completion from success; policy refusal must not execute the mutation. Live integration remains separate. |
| P0 | Exact JSON adapter results — Root/PootScoot, [PR106](https://github.com/RicheyWorks/Daedalus2/pull/106), c8193b7f | Source implemented in an open draft: preserve false, zero, empty string, and null; use empty-object fallback only for an absent result field. 18 offline Node cases; restoring the old truthy fallback rejects four cases; all four CI checks reported green. | Preserve exact JSON values and null-safe PNG handling through the actual adapter; no runtime deployment is implied. |
| P0 | Truthful turn exit and atomic progress — Codex Scope B, coordinated by Root/PootScoot, [PR107](https://github.com/RicheyWorks/Daedalus2/pull/107), 4fe3ed67 | Source implemented in an open draft: failed/stopped turns return nonzero; UUID-specific checkpoints publish before work and after completed phases; legacy final-report path/keys remain. Accept both legacy and full GUID build IDs. 16 units + 24 workflow checks pass on Windows/Linux; all four exact-head CI checks green. | Checkpoint refusal must stop the next operation and preserve prior complete JSON. Match the complete started build ID. Checkpoints do not add automatic resumption, cancellation, or lease enforcement. |
| P0 | Windows launch/wait receipts — Sol, [PR101](https://github.com/RicheyWorks/Daedalus2/pull/101), [PR102](https://github.com/RicheyWorks/Daedalus2/pull/102), [PR104](https://github.com/RicheyWorks/Daedalus2/pull/104), [PR105](https://github.com/RicheyWorks/Daedalus2/pull/105) | Source implemented in open stacked PRs. PR101 preserves an accepted ID/PID when .started writing fails and uses a nonfatal warning even under strict warning preference (ee12ef75; 11 native fixture groups). PR102 adds GUID IDs and checks CIM acceptance/PID. PR104 makes Wait status truthful and publishes atomic completion markers. Public PR105 scope is preparation/pull failure handling, default failure, and completion publication before unsafe continuation. | Review stack dependencies and exact head tests before integration. Launcher acceptance is not build success; live diagnostics without completion remain running; malformed markers fail. Captured fixture commands are not an Unreal build or editor restart. These public scopes do not imply a whole-stack Root review. |
| P0 | GLB handoff identity — Sol, [PR108](https://github.com/RicheyWorks/Daedalus2/pull/108), 20effc37 | Source implemented in an open PR: streamed SHA256 and byte count bind new reports to exported bytes; pre-dispatch and witness checks reject changed bytes. Legacy reports explicitly retain structure-only assurance. Earlier docs-only head 3ce1bbe7 had no checks; current head 20effc37 has green pipeline checks, while broader Build & test remained running at the latest handoff. Prior code head dcdd88d2 had four green checks. | Counts/sizes alone cannot prove artifact identity. A pre-dispatch digest is not a lock against later writes. Review current source, exact-head pipeline results, and inherited evidence separately; a green pipeline check is not a whole-repository or live-editor acceptance claim. |
| P0 | Private verified import snapshots — Sol, [PR109](https://github.com/RicheyWorks/Daedalus2/pull/109), 56b33f22 | Source implemented in an open stack on PR108: unique private import path, verified copied bytes, digest recheck inside Unreal before the first import API call, and snapshot retention after timeout. Current head has two green OS pipeline checks; Root independently ran 9 identity + 10 GLB + 19 judge checks for the reviewed snapshot implementation. This is not a whole-stack review or live acceptance. | No live Interchange acceptance yet. Storage is isolated, not OS-enforced immutable. Remove snapshots only after confirmed job quiescence; timeout does not establish quiescence or permission to retry. |
| P0 | CLI failure/timeout receipts — Sol, [PR114](https://github.com/RicheyWorks/Daedalus2/pull/114), 2d709ab8 | Source implemented in an open stack on PR109; bounded independent review found no blocker (11 receipt + 10 GLB + 19 judge checks, atomic-replacement and successful-CLI probes). Current head has two green OS pipeline checks; reviewed implementation code is unchanged after rebase. Preserve partial report and snapshot identity, publish failure JSON atomically, distinguish export failure from unknown post-dispatch import outcome. | Reconciliation must retain source/import paths and hash; no automatic retry or cleanup. Remote job/replay reconciliation remains proposed. |
| P1 | Existing PC-job exit and PNG fixes — Root/PootScoot, [PR89](https://github.com/RicheyWorks/Daedalus2/pull/89), a303d9e2; [PR99](https://github.com/RicheyWorks/Daedalus2/pull/99), 3a608a8c | Both are open drafts. PR89 preserves PC-job completion codes/Wait status (10 native fixtures, five CI checks reported green). PR99 exports capture_view as actual PNG bytes (four CI checks reported green). Source-only. | Receipt status must reflect the child outcome; PNG signature/format must match its declared output. These tests do not establish live editor acceptance. |
| P1 | Existing Blender probe/expected-state seams — Sol owns asset-pipeline handoff; companion-harness adaptation unclaimed | Source audit found Blender 4.3/addon 1.0.2; connector source b90c6f45 normalized to installed digest prefix 20f2b65c. Companion C:\Users\730ri\projects\blender-harness at ea430882 has the measured-probe implementation at bharness/plugins/probe.py:30, the pure-judge implementation at judge.py:13, and queue.py:128/179 expected-state re-read seams. These are source line references, not test counts. Existing guard is nontransactional. Six static MCP schemas use synchronous sockets, a 1800-second timeout, and a timer draining at most eight requests; no per-job progress/deduplication was established. | Keep the actual probe as the preflight seam; reproduce stale expected-state refusal before mutation. A re-read alone does not atomically fence a subsequent mutation or prove exactly-once execution. Broader async/reconciliation work remains proposed. |
| P1 | Existing game-thread yielding/import fixes — Fable/Claude | import_cast/daedalus.steps work exists on main (4a089220/e27daec6); one item per editor tick is existing behavior. PIE-safe _selected is also already on main and must not be duplicated. Claude/Fable's post-crash 20/24 owner-scenario result is owner-reported, not independently verified by Root. | Keep frame-critical Unreal work native; use bounded yielding for heavy editor tasks. Root's last live evidence was at 04:48 UTC and lease ended 04:50; this source work claims no newer Root live acceptance. |

### Proposed work, ranked for coordination

1. **P0 — Durable acceptance and exact-ID result recovery. Owner: unclaimed; proposed.** Existing async discovery/polling is source implemented in PR103, but the current job/result stores are process-local. Add a reviewed acceptance journal and reconcile lost replies before any retry. [ChiR24 result-cache audit][chir-results] reports a 32-entry cache that can evict running entries and a process-local ledger, so neither is a durability model. Acceptance: a lost client reply does not submit a second mutation; restart reports unknown/interrupted work honestly; explicit ID polling recovers retained terminal evidence; no exactly-once promise.

2. **P1 — Generation-fenced completion and saved-state reconciliation. Owner: unclaimed; proposed.** [litequeue claim-ID tests][lite-claims] and [idempotency tests][lite-idempotency] are useful generation-fencing evidence: an old worker must not complete a newer claim. They do not cancel a previously dispatched Unreal operation. Its [SQLite configuration][lite-source] uses WAL/NORMAL; [SQLite synchronous guidance][sqlite-sync] limits power-loss durability. Acceptance: reject stale completion, retain the accepted generation/hash, distinguish dispatched from saved/confirmed state, and reconcile after restart. A database transaction and an Unreal .umap save are not one atomic transaction; use immutable generations, a hashed ready manifest, and a journal of individual saves.

3. **P1 — Fair, bounded game-thread admission. Owner: unclaimed; proposed.** [ChiR24's request queue][chir-queue] is source evidence for a bounded/fair game-thread lane and re-entry handling. Use the lesson, not copied framework code. Acceptance: bound backlog and work per tick; exercise multiple producers, nested ticks, shutdown/admission races, and refusal without executing a mutation; preserve per-agent ownership. Thread scheduling is not an editor lease.

4. **P1 — Import completion before success or snapshot cleanup. Owner: Sol for current snapshot lane; completion integration unclaimed/proposed.** [Interchange manager][interchange-manager] async-start acceptance must be separated from terminal [FImportResult][interchange-result] evidence; obtaining imported objects may block. Global cancel-all is unsuitable as one agent's cancellation mechanism. Acceptance: a successful start followed by failure/cancel/timeout never reports an import success; wait/poll without blocking a frame-critical path; verify returned objects plus the intended saved package; retain snapshots while completion remains unknown.

5. **P1 — Full actor-path identity and duplicate-label refusal. Owner: unclaimed; pending coordination (hub29437), proposed after shutdown work.** Current _find_actor selects the first matching label or name. Acceptance: prefer a verified full object path and scoped identity; refuse ambiguous duplicate labels before mutation; test two actors with the same label, a missing actor, and editor/PIE worlds. No broad scene rewrite.

6. **P2 — Fingerprinted delta manifests and success-only checkpoints. Owner: unclaimed; proposed.** [pydoit dependency source][doit-dependency] supplies config/dependency fingerprint and success-after-execution lessons. Acceptance: hash effective input/config/tool versions, use stable scoped managed IDs, skip only when output/save evidence also matches, and update successful checkpoints only after confirmed completion. A matching file timestamp or submitted save is insufficient.

7. **P2 — Three-way artist-preserving reimport. Owner: unclaimed; proposed.** [AYON's USD contribution tests][ayon-threeway] compare supported properties across baseline/current/proposed states to preserve local artist changes and report conflicts. Use managed IDs and explicit ownership. The [AYON Unreal loader][ayon-loader] contains delete-before-copy/unique-name behavior unsuitable for direct reuse here; [Epic reimport strategies][reimport-strategy] require an explicit preservation policy. Acceptance: artist edits survive, conflicting changes are reported, unrelated actors/assets remain untouched, and repeat imports retain identity. No raw replacement of loaded .uasset files, deletion based on a missing source, or copied delete-before-import workflow.

8. **P2 — Measured preservation and real rollback witnesses. Owner: unclaimed; proposed.** [Code4Scene's source-preservation verifier][source-preservation] requires a frozen source snapshot for edit/repair preservation. [PinWright's rollback test][pinwright-rollback] deliberately fails compilation, resolves original node GUIDs, and verifies exactly one reciprocal pin link. Acceptance: capture a frozen owned baseline and inspect the actual post-failure state before claiming restoration. Bridge generator cleanup, an undo transaction, a prompt, and a screenshot alone do not prove rollback.

9. **P2 — Reflection discovery with truthful graph-edit outcomes. Owner: unclaimed; proposed.** [UCP BlueprintGraphDiffer][ucp-differ] matches GUIDs before weaker fingerprints and scopes link removals, but adds link-change report entries without checking TryCreateConnection's return. Its transaction is not proof of successful edits or rollback. Acceptance: validate supported reflected types/parameters; reject ambiguous identity; test rejected connections, invalid property values, preserved unrelated links, and actual resulting graph state. Do not treat an attempted operation count as a success witness.

10. **P2 — Parser diagnostics before accepting empty dependencies. Owner: unclaimed; proposed.** [OpenUSD dependency tests][usd-dependencies] motivate checking parse diagnostics: zero unresolved dependencies can accompany corrupt/empty input and produce a false pass. Acceptance: invalid/truncated USD fails before import; valid empty content is distinguished from parse failure; diagnostics, stage validity, resolved references, and the ready-manifest identity are recorded.

11. **P3 — Native UE 5.8 MCP/toolset comparison. Owner: unclaimed; research/watchlist only.** [Epic Unreal MCP][epic-mcp] is experimental; [SlateInspectorToolset][slate-inspector] is a possible discovery/UI-toolset reference. Acceptance for any future evaluation: compare supported operations, completion semantics, permissions, and compatibility using source/isolated tests first. This backlog does not authorize enabling listeners, installing plugins, changing runtime permissions, or taking an editor lease.

12. **P3 — Framework and license gates. Owner: unclaimed; evaluation only.** [UnrealJs v2.6.0][unrealjs-release] is reported UE 5.8-compatible; its NCSOFT/BSD-style terms must not be called MIT. No framework code is copied or adopted by these findings. Monolith/BFU were mentioned in prior discussion, but precise primary links were not available for this consolidation: source identification, test-quality, and license details remain unverified; no adoption recommendation is recorded.

### Evidence and integration limits

- The supplied external sources were audited for specific design lessons; they are not dependencies installed into this project.
- Source/fixture checks and another owner's live result are separate evidence. No new GPU, bridge, editor, production, or deployment action was performed for this consolidation.
- Interrupted bridge work can have partial effects. Closing a generator may run owned finally cleanup, but it does not undo prior mutations or stop an already dispatched remote Python worker. A listener stop/timeout is not proof of editor death: [Claireon lifecycle tests][claireon-lifecycle] distinguish these states and discourage automatic relaunch.
- Shared canonical lessons remain Buff's lane; this is an append to the existing tracked connector research roadmap. Proposed work still needs named coordination before implementation.

[chir-queue]: https://github.com/ChiR24/Unreal_mcp/blob/dev/plugins/EngineWire/Source/EngineWire/Private/Core/Subsystem/EngineWireSubsystemRequestQueue.cpp
[chir-results]: https://github.com/ChiR24/Unreal_mcp/blob/dev/src/server/gateway/gateway-task-results.ts
[lite-claims]: https://github.com/litements/litequeue/blob/main/tests/test_message_claim_ids.py
[lite-idempotency]: https://github.com/litements/litequeue/blob/main/tests/test_idempotency.py
[lite-source]: https://github.com/litements/litequeue/blob/main/src/litequeue/__init__.py
[sqlite-sync]: https://sqlite.org/pragma.html#pragma_synchronous
[interchange-manager]: https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/InterchangeEngine/UInterchangeManager
[interchange-result]: https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/InterchangeEngine/FImportResult?lang=en-US
[doit-dependency]: https://github.com/pydoit/doit/blob/master/doit/dependency.py
[ayon-threeway]: https://github.com/ynput/ayon-core/blob/be4f257e5867cb034cb8808922087266e9e19125/tests/client/ayon_core/plugins/publish/test_usd_contribution_stacking.py
[ayon-loader]: https://github.com/ynput/ayon-unreal/blob/43b4a800a52289dd0bae19b1345889a835766bb7/client/ayon_unreal/plugins/load/load_staticmesh_fbx.py
[reimport-strategy]: https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/InterchangeCore/EReimportStrategyFlags
[source-preservation]: https://github.com/SimWorld-AI/Code4Scene/blob/2716e4397f768bf16b1f33dd34680d48aed0601f/code4scene/evaluation/verifiers/source_preservation.py
[pinwright-rollback]: https://github.com/PinWright/pinwright-ue/blob/47eb9718857f185cdd2e445f54d3b1329ada8701/Source/PinWright/Private/Tests/Bpir/TestBpirCompileRollbackGraphPins.cpp
[ucp-differ]: https://github.com/Italink/UnrealClientProtocol/blob/7f0a56e27875b40259b46a7f2de33e7de7d2045f/Source/UnrealClientProtocolEditor/Private/Blueprint/BlueprintGraphDiffer.cpp
[usd-dependencies]: https://github.com/PixarAnimationStudios/OpenUSD/blob/ce1ed124c1f59368f1248e1bc6d334cd0907b722/pxr/usd/usdUtils/testenv/testUsdUtilsDependencies.py
[epic-mcp]: https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor
[slate-inspector]: https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/SlateInspectorToolset/USlateInspectorToolset
[unrealjs-release]: https://github.com/getnamo/UnrealJs/releases/tag/v2.6.0
[claireon-lifecycle]: https://github.com/believer-oss/Claireon/blob/89bee2f4c62d1df625cca71ae66e7c81a415a009/Content/Python/claireon_proxy_test.py#L604
