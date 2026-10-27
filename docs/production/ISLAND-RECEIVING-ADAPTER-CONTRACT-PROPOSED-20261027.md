# Island production receiving-adapter contract: PROPOSED (for Boss review, not adopted)

Author: hephaestus (R22 job 2, Buffffff msgs 56522 / 56527). Date: 2026-10-27.
Code: `tools/unreal_preflight/island_receiving_adapter/contract.py`. Contract tests: `test_contract.py` (14, synthetic only).

**Status: PROPOSED.** There is no production wiring, provider loader, run command, editor/broker/lease call, or I/O.
`ProposedNativeAdapter` raises `NotImplementedError` on purpose. Boss keeps preflight, scheduling, concurrency, recovery and adoption.

## Sources (read-only; nothing copied, no Codex code imported)

1. **Offline boundary:** `Documents/Codex/2026-10-26/task-8/island-continuation-source/`
   - `HANDOFF.md`
   - `island_continuation.prepare_session / plan_next / simulate_step`
   - `island_policy.build_request / check_guard`
   - `island_checkpoint.validate_mock_receipt`
   - the injected `guard(request)` and `receipt(request)` mocks in `test_island_continuation.py`
2. **Proven legacy recipe:** `Documents/Codex/2026-10-14/task-2/focused_native_islands_20261023.py`
   - `run(seed)` stages: `ReadWholeIslandTarget`, `NativeImportWholeIsland`, `AdmitSavedWholeIsland`, `UnloadCleanOwnedIslandPackages`
   - the `value` of `AdmitSavedWholeIsland` and its `items[0]` report
   - `batch-complete.json`

## The contract

`simulate_step(root, generation, guard_provider, invocation_provider)` already takes two injected callables, so the adapter has two methods:

| Method | Input | Output | Shape authority |
|---|---|---|---|
| `preflight(request)` | `island-receiving-invocation/v1` (exact key set of `build_request`) | `island-mock-preflight/v1` (exact key set of the `guard` mock) | `check_guard` (timing, window, floors, `BossActionRequired`); `validate_preflight_shape` checks keys and bindings only |
| `invoke(request)` | same request | `island-mock-result/v1` (exact key set of the `receipt` mock) | `validate_mock_receipt`; `validate_result` mirrors it for one island |

Fixed by the boundary:
- The request carries `receiving_adapter_required=True`, `legacy_run_seed_is_directly_safe=False`, `automatic_restart=False`, `automatic_lease_mutation=False`, `execution_mode="mock"` and `native_admission=False`.
- `invocation_id` is `session_id:generation`, and `item.seed == seed`.
- The result must be terminal and complete:
  - `imported`, `saved` and `admitted` are 1; `held`, `failed` and `reused` are 0;
  - `known_terminal` is true and `pending_native_operations` is false;
  - all five `recipe_checks` are true and the five `preservation` keys are exact and true;
  - identity is bound to `request_sha256`, using the same canonical encoding as `island_checkpoint.encoded`.

## Mapping from the legacy recipe (`map_legacy_action`)

| Boundary field | Legacy source | Status |
|---|---|---|
| imported/saved/admitted/held/failed/reused | `AdmitSavedWholeIsland` value | direct |
| recipe_checks.geometry_matches, material_mapping_matches | value | direct |
| recipe_checks.source_factor_bindings_match, vertex_colour_sample_matches | `items[0]` report | direct |
| recipe_checks.validation_reported_valid | report.validation: status `Valid`, `native_invoked`, `accepted` (same expression as legacy `admitted`) | derived |
| preservation.world/actors/camera/selection | value.preservation | direct |
| preservation.source | **none** (legacy has `clean` instead) | **OPEN** |
| known_terminal | `KNOWN_TERMINAL` row in `native-substeps.jsonl`, supplied by the caller | caller-observed, else **OPEN** |
| pending_native_operations | **none** (only `native_import_active`) | **OPEN** |
| session_id / invocation_id / seed / request_sha256 | **none** in `run(seed)` | **OPEN** (adapter-asserted only) |
| schema / simulated / native_admission | mock only | **OPEN** |

Nothing is defaulted to true. The mapped candidate is **refused** by `validate_result` until Boss resolves the OPEN items.
The tests prove this. A dirty or import-active legacy island, a wrong source pin, or a report that is not exactly one island refuses outright.

## OPEN questions (Boss)

- **OPEN-native-schema:** What are the native preflight and result schema names, and who may set `native_admission=true`? Today only the mock ones exist.
- **OPEN-preservation-source:** Should the adapter report `preservation.source` from the `NativeImportWholeIsland` pin re-hash, which raises on change? Or should the boundary accept legacy `clean`?
- **OPEN-pending:** How is `pending_native_operations=false` proven? Legacy `state.pending` is internal to the editor session.
- **OPEN-known-terminal:** Is the `KNOWN_TERMINAL` journal row the agreed terminal proof (as `finish_saved` uses it)?
- **OPEN-identity:** Should the recipe, not just the adapter, echo `session_id`, `invocation_id` and `request_sha256`?
- **OPEN-destination:** Legacy hard-codes `/Game/Daedalus/Art/Islands/HDNative20261023/<stem>` and discovers the source with `source_for(seed)`. Must the adapter prove equality with `item.destination` and `item.source` before invoking?
- **OPEN-world:** Legacy uses `f.WORLD + '.L_Daedalus_MorningReview'` and the boundary uses `expected_world`. Same value?
- **OPEN-leases:** Legacy `f.claim()` and `close_saved_batch` mutate leases and packages, and the boundary forbids automatic lease mutation. Which custodian does them? HANDOFF also says: do not run or import `continue_native_islands_24h_20261023.py`, and audit transitive dependencies (including `focused_island_source_materials_20261023`).