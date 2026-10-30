# Island production receiving-adapter contract: R27-aligned (for custodian adoption)

Author: hephaestus (R22 job 2, Buffffff msgs 56522 / 56527), 2026-10-27, PROPOSED with 8 OPEN items.
Revision: unreal-team (Claude), 2026-10-29, folding in unreal-epic-boss's answers to all 8 OPEN items
(PR #906 comment, Oct 29 10:47 AM PT) and Richey's custodian decision (hub 57016/57017, Oct 29 11:17 AM PT).
Code: `tools/unreal_preflight/island_receiving_adapter/contract.py`. Tests: `test_contract.py` (26, synthetic only).

**Status: R27-aligned, not yet adopted.** No production wiring, provider loader, run command, editor/broker/lease
call or I/O. `ProposedNativeAdapter` still raises. Adoption and any run belong to the sole runtime custodian.

## Custodian

`RUNTIME_CUSTODIAN = "codex-play-guard"` (R27). Unreal Epic Boss handed over and is hands-off (Richey, Oct 29).
Only this owner holds or renews the `unreal` and `compute` leases. The adapter never claims, unlocks or saves outside
its owned folder; `close_saved_batch` retains leases (receiver 164, 181, 324-327).

## Sources (read-only; nothing copied, no Codex code imported)

1. **Offline boundary (mock path, unchanged):** `Documents/Codex/2026-10-26/task-8/island-continuation-source/`
   (`island_policy.build_request / check_guard`, `island_checkpoint.validate_mock_receipt`, injected `guard`/`receipt` mocks).
2. **R27 production receiver (native path, new):** `Documents/Codex/2026-10-14/task-2/producer-full-queue-r27-speed/native_receiver.py`
   — `native_world` (62-63), `functions` AST port (66-100), `close_saved_batch` (163-189), `receive` queue/profile
   (301-372), `validate_result` (375-398). Its `batch-complete.json` is the native result. Key set verified against a real
   receipt (`producer-full-queue-r26/progress/NativeBatches/Island10403/batch-complete.json`).
3. **Proven legacy recipe** `focused_native_islands_20261023.run(seed)` — still mapped by `map_legacy_action` for the
   offline boundary; the native path does not use its `source_for`/HDNative constant.

## The contract

| Method | Input | Output | Shape authority |
|---|---|---|---|
| `preflight(request)` | `island-receiving-invocation/v1` (exact `build_request` key set; `execution_mode` mock or native) | `island-mock-preflight/v1` key set | `check_guard` for timing/window/BossActionRequired; `validate_preflight_shape` for keys and bindings; `check_editor_floors` for Boss's native floors |
| `invoke(request)` | same request | mock: `island-mock-result/v1`; native: R27 `batch-complete.json` mapped by `map_r27_receipt` | mock: `validate_result`; native: `validate_r27_receipt` (= receiver 375-398) then `validate_native_result` |

Fixed by the boundary (both modes): `receiving_adapter_required=True`, `legacy_run_seed_is_directly_safe=False`,
`automatic_restart=False`, `automatic_lease_mutation=False`, request `native_admission=False`; `invocation_id` is
`session_id:generation`; `item.seed == seed`.

Native mode adds: `receiving_owner == RUNTIME_CUSTODIAN`; `expected_world == native_world(world)` and never the
MorningReview showcase; no recipe pin named `continue_native_islands_24h_20261023`.

## How the 8 OPEN items were closed (Boss, PR #906 comment)

| OPEN | Answer | Where in contract.py |
|---|---|---|
| native-schema | R27 `batch-complete.json` as checked by `native_receiver.validate_result`. `native_admission` is per item and only true when the custodian receipt shows `validation.status=='Valid'`, `accepted` and `native_invoked`. The adapter never sets it. | `validate_r27_receipt`, `map_r27_receipt` (copies the evidence, never asserts) |
| preservation-source | Re-hash the pins, refuse on change; legacy `clean` alone is not enough; plus `all(action.preservation.values())`. | `verify_rehash` (custodian injects `{path: sha256}`), `validate_r27_receipt` |
| pending | Proved from the receipt (`bridge_after` all false, `native_import_active` false, dirty empty, `failed==0`, counts close) plus one custodian live read before and after (no PIE/sequence/dirty). | `validate_r27_receipt`, `validate_live_read` ×2, ordering check |
| known-terminal | Required. | `validate_r27_receipt` |
| identity | Bound in the adapter's own sealed receipt with the pinned result hash; recipe bodies untouched. | `map_r27_receipt` → `sealed` (`island-adapter-sealed-receipt/v1`: request_sha256, result_sha256, custodian, pid, live-read UTCs, rehashed pins) |
| destination | Prove before invoking: source = pinned queue `island_by_seed[seed].source_path`; after: every returned package under `planned_destination_folder` or held. | `prove_destination`, package/saved-file prefix checks in `map_r27_receipt` |
| world | Not the same. Use `native_world(world)`; MorningReview protected. | `native_world`, `validate_request` |
| leases | Custodian only; adapter never claims/unlocks/saves outside its folder. | `RUNTIME_CUSTODIAN`, `check_editor_floors` (both leases held by custodian) |

## Editor-time constraints (Boss)

One serial editor, both leases held by the custodian. Floors: 1.74 GB physical, 2.25 GB commit, 3 GiB source/gallery,
25 GiB disk (`EDITOR_FLOORS`; R27 stopped on them Oct 29 10:36 AM PT). Islands interleave only at a clean saved boundary.
Never early-stop or kill a producer, never `-unattended` or `-AutoDeclinePackageRecovery`, never save outside owned packages.

## What the custodian supplies at run time (all data, no adapter I/O)

1. The request (native mode) and the pinned queue entry → `validate_request`, `prove_destination`.
2. A preflight snapshot → `validate_preflight_shape`, `check_editor_floors`.
3. After the native call: the R27 `batch-complete.json`, a fresh `{path: sha256}` re-hash of every request pin, one live
   read taken before and one after, and the admitted editor pid → `map_r27_receipt` → `(candidate, sealed)` →
   `validate_native_result`. A held island (`admitted=0, held=1`) maps cleanly but is refused as not admitted.

Nothing is defaulted to true. The mock path and its tests are unchanged except that `execution_mode` may now also be `native`.
