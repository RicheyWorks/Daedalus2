# Deterministic ingestion runner: first milestone

**Source/offline milestone; native adoption is NOT established. Do not start a
production backlog or overnight run with this cut.** No live owner adapter is
supplied or implicitly approved. The test adapter is entirely synthetic and must
never be used as native evidence. Native/runtime/production qualification flags
stay false.

The queue itself makes no LLM/paid API calls, starts no editor/service, and does
not replace an importer. It reuses the exact published PR146
`daedalus_ingestion_receipts.py` blob `965d501dba68f0b407ec700e5ac39fda623ba3c6`
from commit `be695b7ed022752a9e69b7894fc1d22a0f1031fd`
(SHA256 `1fe687e4658cfa28a5b47035bbecb32d1e1de75ead1ec0ea6d3450dce59b7117`)
for fingerprints, atomic fsync/replace writes and immutable input snapshots.
The existing `native_validation_snapshot_consumer.py` remains unchanged.

The existing ADR051 art watcher remains intact. It opens/exports Blender work
and retries BLOCKED rows automatically; it does not provide this newer strict
known/uncertain-outcome plus genuine native-validation contract. Do not run both
watchers against the same work. Breakwater is a gameplay simulation, not an
ingestion backend. No new shared queue board or transport protocol is added.

## Launch, resume, stop (interface for a future qualified owner adapter)

From the repository, using the existing Python 3.10+ runtime:

```powershell
python tools/unreal_mcp/unattended_ingestion.py prepare --manifest C:/owned/selected-source-manifest.json --state C:/owned/ingestion-run-001
python tools/unreal_mcp/unattended_ingestion.py run --state C:/owned/ingestion-run-001 --max-items 1
python tools/unreal_mcp/unattended_ingestion.py status --state C:/owned/ingestion-run-001
python tools/unreal_mcp/unattended_ingestion.py stop --state C:/owned/ingestion-run-001
python tools/unreal_mcp/unattended_ingestion.py resume --state C:/owned/ingestion-run-001 --max-items 1
```

`prepare` verifies explicit local source/policy/adapter/dependency hashes and
creates a NEW state directory; it does not import/execute adapter code. `run`
and `resume` use the same frozen manifest, runner bytes and item checkpoints.
`STOP` is persistent: resume refuses while it exists. After the active request is
known terminal, remove only that owned `STOP` file to explicitly resume. Stop
never kills an editor/request or discards unsaved work; it applies at the next
safe boundary. The adapter must bound calls/timeouts. There is no background
watch/service, automatic editor restart, rapid poll, or default bulk launch.
Run exits on a resource/ownership/uncertain-outcome hold; resume later, with no
model required. Predispatch resource/busy holds are paced at least60seconds and
limited to3 attempts, including across process resumes. The manifest supports
at most256 explicitly selected items; the CLI defaults to1, not the backlog.

The Windows physical/commit floors remain1,700,000/2,200,000KiB. No CLI override
lowers them. A conservative10GiB free disk reserve applies to the state volume.
The state folder and Unreal project must be on the SAME volume in this first
cut; the runner does not certify other output-volume headroom. These are read
gates, not changes to system settings. Other platforms can run the synthetic
tests; live resource admission is Windows-only.

## Frozen manifest

JSON schema `daedalus.unattended-ingestion.v1` has exactly these top-level keys:

- `owner`: actual hub actor, e.g. `codex-play-guard` (never another actor).
- `owned_destination`: explicit narrow `/Game/...` namespace; each item owns a
  disjoint child namespace. No replace/overwrite/placement is implicit.
- `engine_version`: exact expected native version string.
- `editor`: `pid`, `start_utc` (explicitUTC), absolute `project` and exact `world`.
- `adapter`: `file` witness and exact ABI `version`.
- `dependencies`:1..32 explicit file witnesses for installed DLL, native helper,
  policy/provenance readers, adapter dependencies and any required baseline.
- `items`:1..256 objects with exact keys `id`, `destination`, `sources` and
  `policy`. `sources` is1..8 file witnesses; `policy` is the existing reviewed
  importer/profile contract, not an instruction to relax it.

Every file witness has exactly `path` (absolute), `sha256` and `bytes`.
Symlinks, changed/missing files, duplicate IDs, overlapping destinations and
duplicate content/policy are refused. The item identity includes full source,
destination and policy fingerprints; queue identity also binds engine/editor,
adapter and dependencies. A new source/profile/editor identity requires a new
reviewed manifest/state after reconciliation, not editing an old queue.
Only host-runner interruption with the SAME editor is covered by this cut;
editor-process replacement is a hold, not unattended recovery.

## Owner adapter seam (unfinished native prerequisite)

The runner loads only the pinned local adapter bytes. That adapter is executable
trusted code and needs source review plus actual native acceptance; a hash alone
is NOT proof the adapter is safe. It must reuse an already qualified existing
importer/harness and current native guarded route. It must not call an LLM,
acquire credentials, install anything, touch Cursor/satellite work, launch a
second editor, or relax material/animation/provenance policy.

`VERSION` must match the manifest. `create(frozen_manifest, state_directory)`
returns an object with:

| Method | Contract |
|---|---|
| `admit(item, phase)` | Read-only current ownership/readiness/policy check for `execute`, `verify` or `reconcile`. Return actual editor/version/holder and booleans `exclusive_writer`, `idle`, `preserved`, `policy_verified`; a new import also requires `destination_vacant`. Acquire/renew ordinary exclusive Unreal AND compute custody through the existing broker; verify no competing native/async/import/render/test work and clean protected state. Never force-unlock another owner or rely on this runner's local lock to serialize legacy callers. |
| `execute(item, operation_id, snapshots, native_receipt_path)` | Exactly one admitted bounded request using the supplied verified immutable snapshots. Write an operation-bound durable native receipt BEFORE replying. Import/save only new assets in the item namespace, applying every existing source/material/etc gate. Capture actual native validation and protected state; no world placement. Saving new private packages is intermediate, never final admission on its own. On completion normally release compute/read back, preserve editor custody. Never import twice after timeout. |
| `reconcile(item, operation_id)` | Read-only reconciliation of the SAME native journal/job. Return `{"state":"complete","result":...}` only for the actual known terminal; otherwise pending/unknown and stop. No import/save/retry. Host never re-executes an INFLIGHT/UNCERTAIN item automatically, even after process restart. |
| `verify_saved(item, result)` | Guarded current readback, no mutation: exact saved output inventory/settings/metadata/hash/provenance still match. Return booleanTrue only after actual checks, otherwise hold/quarantine. |

Only `low_memory`, `low_disk`, `editor_busy` and `lease_busy` with explicit
`native_dispatched:false` can produce a predispatch WAITING retry. Failure after
dispatch is uncertain until reconciled. An exception/transport timeout never
authorizes a new import. Quarantined work is terminal to this runner; it is not
silently reset or automatically repaired. Keep originals and all failed evidence.

The completion fields checked by `validation()` in the runner bind the operation,
item key, engine, destination, exact asset paths and their actual Content `.uasset`
files; exact capture editor/operation/route/start/endUTC; actual validation
envelope; and adapter-preserved state. Native evidence is at most300seconds old
and cannot be retimestamped. `Valid` alone is insufficient: actual native invocation,
accepted=true, cancellation=false, return integer0, exact canonical requested set,
details/counters, Script policy, attested fresh results/invocation and no errors,
warnings, extra objects or limits are required. NotValidated is held; Skipped is
distinct; Invalid/warnings/incomplete/cancelled/malformed cannot become DONE.
The adapter's preservation attestation must be backed by its existing before/after
native+file receipts; the runner cannot independently prove an arbitrary adapter's
claims. Synthetic receipt acceptance is NOT native execution evidence.

## Evidence and next finite step

```powershell
python -m unittest tools/unreal_mcp/test_unattended_ingestion.py -v
```

The offline suite covers actual two-child-process interruption/reconciliation,
no second effect, uncertainty, stop boundaries, kernel exclusion, frozen pins,
overlapping/duplicate work, bounded resource retries, saved-output tampering,
wrong owner/policy and validation refusal. Temporary fake `.uasset` files are plain
text; no Unreal imports/network occur. A Windows restricted temp sandbox may deny
atomic `os.replace`; run the same reviewed offline test normally, not a weaker
non-atomic writer or changed security settings.

**Native proof is still missing:** no current existing importer adapter produces
the combined strict Valid/provenance/preservation completion shape. The minimal
next batch is that thin owner adapter for ONE already qualified source/profile,
then a tiny isolated import, interrupted-host reconciliation/no duplicate effect,
saved/readback validation and unchanged originals/world/camera proof. Do not
reinterpret the old watcher's SHIPPED or saved-receipt flag as native validation.
Only after that proof can a separate explicit selected production batch be admitted.
