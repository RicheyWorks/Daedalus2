# OperatorR2 context refusal: evidence and diagnostic delta

**The actual mismatching field is not retained, so its root cause remains
unresolved. This delta fixes the missing failure evidence, not the acceptance
predicate.** The sole writer's authoritative closeout at
`2026-10-23T03:15:57.360884+00:00` remains: **3 prepared, 0 imported, 0 admitted,
3 held; 0 complete pages; no queue; native pending false; compute released**.
Metadata load count is **unknown**, superseding the earlier inferred zero.
No editor call or live import was made by this offline worker.

## Exact comparison performed offline

Evidence folder:
`C:/Users/730ri/Documents/Codex/2026-10-14/task-2/native-ingestion/CommonsPond20261023/OperatorR2`.

- `baseline.json`: 654,533 bytes, SHA256
  `f2a29b4a450ae47978cb06f8c9094527d3d423ee08426d50bafd13e35f01c7f6`,
  saved `03:11:39.849824 UTC`.
- `SourceMetadataPage0000R1/native-executed.py`: 10,725 bytes, SHA256
  `65e6d2a29956f2d529f082145a83c4e767b2f88d4e5bb5b72cc90c7b0580b040`,
  saved `03:12:02.431523 UTC`.
- `ReconcileContextRefusalR1-terminal.json`: 609,403 bytes, SHA256
  `4a64d89aa18d8501872b3792d891cd1558fd43a945f436703ec32532c03ab099`,
  saved `03:12:50.939356 UTC` (capture reports `03:12:50.931848 UTC`).
- `SourceMetadataPage0000R2/native-executed.py`: 10,731 bytes, SHA256
  `97798f4b4e62ae7cd8739a537022e02e1a066726ba17d6ff466dca07363038b5`,
  saved `03:14:15.677268 UTC`.

AST inspection of both request literals confirms the same baseline witness and
editor object, with identical parsed types and values. PID is 33628; generation
is `2026-10-23T00:11:34.8319282Z`; project is
`C:/Unreal/DaedalusRealm/DaedalusRealm.uproject`; world is
`/Game/CodexToolEvaluation/PlayableCourtyard/20261022/R1/L_LanternCourtyard.L_LanternCourtyard`.
Both requests pin native reader SHA256
`d7066956e731a3d4b70b4f22e1a6a27abcff54af968189c625719963f4e25138`,
19,491 bytes. Their journals retain only `ENTERED` with PID 33628.

The reconciliation executes that same pinned reader and captures its `context()`.
Its context exactly equals the parsed baseline: **zero field/type/value
differences** across world, camera, all 722 actors, components, mesh identities
and transform strings. Editor, PID and engine equality flags are true. No
serialization coercion is needed to obtain that equality. Transform strings
include a native struct address, but even those addresses match in this
readback. Address instability is a possibility, **not an established cause**.

The reconciliation is a later capture. It neither calls the failed admission
guard nor retains either failed guard's actual context/engine operands. The
same generic exception was used before and after metadata loads, so a later
match cannot determine the failed phase or historical load count. The missing
comparison is the **failing invocation's context or engine value against its
baseline/config, with first differing field/type/value, UTC interval and phase**.
The request's baseline/editor mismatch is ruled out offline; its outer PID
assertion and `ENTERED` also establish the dispatched process identity.

## What this delta changes

The existing exact Python inequality predicates, their short-circuit order,
memory/idle checks, original transform format and protected baselines remain.
No address stripping, float rounding/tolerance, context omission, validation
promotion or new approval gate is introduced.

On a refusal, the first error line now carries structured JSON identifying the
failed comparison (`editor`, `pid`, `context` or `engine_version`), baseline and
reader pins, capture interval, page offset, phase, attempted metadata-load call
count, and first unequal field with bounded expected/current types and JSON
values. Actor differences include actor identities. Missing keys and added or
removed actors retain the unmatched item. Supplemental full-operand digests
explicitly use sorted compact ASCII JSON encoded as UTF-8; these hashes are
**diagnostics only**, never the equality rule.

The exception also exposes `inventory_evidence` for the existing owner journal.
The bridge message is one parseable line under 4 KiB for native call-site values;
oversized detail uses a summary/digest and leaves full evidence in that
attribute. No diagnostic files are written by the helper itself. A capture
is taken once; diagnostics never take a second snapshot of a changed world.

Metadata pages label guards `before_metadata` and `after_metadata`. The load
counter increments before each `load_asset` call: it counts attempts, including
cached returns, not newly loaded packages or admitted meshes. Registry-only
guards use `before_registry`/`after_registry` with zero metadata load calls.

## Exact next operation for the sole writer

1. Apply this delta from PR415 at a safe boundary, without changing the active
   project or historical evidence. Repin the **actual installed** updated `.inc`
   SHA256/bytes in a new request config. Preserve the existing source review;
   matching source/view pins do not require new user authorization. Keep the
   prior exact baseline only while it still matches current protected state;
   do not edit historical JSON to make a guard pass.
2. Through the existing guarded read route, use a **new owned operation folder**
   for offset 0. Retain the same custody, protected-file, idle/resource and STOP
   checks. Add this small catch around the existing page action so failure
   evidence survives even if the transport raises before writing its reply:

```python
try:
    page = scope['capture_inventory_page'](CONFIG)
except RuntimeError as failure:
    evidence = getattr(failure, 'inventory_evidence', None)
    if evidence is not None:
        record('INVENTORY_CONTEXT_REFUSED', evidence)  # existing owned journal
    raise
```

   At the host boundary, also retain the caught existing `BridgeError.reply`
   and `str(error)` in a new immutable refusal artifact using the existing
   receipt writer. `retained_call` raises before it writes `native-reply.json`
   on error; absence of that file is not evidence that native work did not run.
   Reconcile any uncertain request before another dispatch, as before.
3. Return that actual refusal record to the coding worker. It supplies the
   missing comparison; a fresh successful readback alone does not. If the read
   succeeds, keep its genuine page and report success without inferring the
   historical cause. Do not normalize a future mismatch automatically.
4. Reader identity changes invalidate old page/index reader pins. There are
   currently no complete R2 pages to salvage. After the failure is resolved,
   collect fresh pages with one reader identity and build a new index/queue;
   never edit old page claims. Existing complete-coverage, source hash,
   destination deduplication and native Valid admission remain mandatory.

The offline worker has completed the exact evidence comparison and diagnostic
patch. **Production diagnosis/import remain pending the sole writer's guarded
read**, not denied. No actual failed snapshot exists in the available artifacts;
there is no justified predicate change or actual-cause reproduction yet.

## Focused checks and lesson

Nine AST-isolated context tests pass with fake Unreal state. They verify exact
context acceptance; identity short-circuit order; real transform/camera/world/
component/actor/engine changes staying refused; no pointer normalization; type
reporting; bounded parseable errors; journal evidence and reader identity.
Eighteen isolated registry/page checks also passed after the phase/count change,
including before-load refusal (0 attempts) and after-load refusal (32 attempts),
and a final short page. These are synthetic diagnostics checks, **not a
reproduction of the unknown production cause**. The broader suite was not rerun.

**Lesson for later shared-file append:** Retain the actual unequal operands at
the guard that refuses, with capture time, identity and before/after effect
phase. Reusing one generic error for pre- and post-load checks loses the load
boundary. A later matching readback proves current preservation, not what
differed earlier; never weaken a protection based on that inference. Persist
transport errors explicitly when the normal receipt is written only on success.
