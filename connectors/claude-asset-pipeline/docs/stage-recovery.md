# Offline stage evidence

`python -m asset_pipeline.stages` reads producer receipts and pinned files. It
reports completed, accepted, running, missing, failed and uncertain stages and
offers conservative advice. It never runs a process, contacts Blender/Unreal or
HTTP, changes a lease, cancels work, imports, saves an asset, or resumes a job.
The existing native `pipeline_batch.py` journal remains its owner's separate
dispatch/reconciliation surface; this helper neither replaces nor adopts it.

Run from `connectors/claude-asset-pipeline`, with standard-library Python 3.10+:

```text
python harness/stages_test.py
python -m asset_pipeline.stages verify receipt.json --root ARTIFACT_ROOT
python -m asset_pipeline.stages publish candidate.json --root ARTIFACT_ROOT --output receipt-002.json
```

`verify` returns 0 only when all local stages have retained successful terminal
evidence and every required nonempty output pin verifies. It returns 2 for valid
but incomplete/uncertain evidence, and 3 for malformed, contradictory, changed or
unavailable evidence. Parsed command results are JSON; argparse usage errors retain its standard text/exit2. `adapt-process` emits a candidate,
not a verified or published result. `publish` reports successful publication of
evidence, including honest failed/unknown evidence; that exit code is **not job
success**. Verify the published receipt separately.

## Producer emission contract

A job declares its exact `job_id`, ordered stages, dependencies and required
output roles. An attempt has a caller-selected `attempt_id`, pinned `inputs`
(name source/tool/recipe/input roles explicitly), and append-only events:

```json
{
  "schema": "daedalus.stage-evidence.v1",
  "job_id": "copperfall-example",
  "observed_at_utc": "2026-10-16T05:00:00Z",
  "identities": {},
  "stages": [{
    "stage_id": "export",
    "requires": [],
    "effect": "local-files",
    "required_outputs": ["glb"],
    "attempts": [{
      "attempt_id": "export-1",
      "inputs": {},
      "events": [{"state": "accepted", "observed_at_utc": "2026-10-16T05:00:00Z"}]
    }]
  }]
}
```

This example is only accepted, not running or complete. Real source/tool/recipe
pins must come from the emitting wrapper; the helper does not guess missing
versions from filenames. Pins have exactly `path`, `bytes`, `sha256`. Relative
paths resolve against explicit `--root`; absolute retained paths are also
supported. A terminal event has `outcome` (`succeeded`, `failed`, `unknown`),
`effects` (`none`, `complete`, `partial`, `unknown`), `outputs` keyed by role,
and optional separate `process`, `compute_release`, `progress`, `materials`.

For success the wrapper must provide `process: {"exit_code": 0, "evidence": PIN}`
whose retained JSON actually contains integer `exit_code: 0`, plus all required
output pins. File presence, a transport ACK, progress text or compute release
alone cannot complete a stage. A nonzero process exit proves failure, while a
saved source file can still be retained as a verified partial output. A
persistent GUI operation must use its own actual operation-result adapter;
this finite-process adapter must not invent exit0 for a living Blender process.

`compute_release: {"released": true, "evidence": PIN}` requires a separate
retained JSON `released: true`. The Nursery adapter also understands its exact
historical `OURS_RELEASED_VERIFIED` record only when unlock was attempted,
the response confirms an empty lock, and the retained after-read has no compute
holder. This is dated evidence, not a current lease observation or allocation.
Progress can name its explicit `field` (for example `stage`); it remains separate
from terminal process evidence. Stale running attempts require reconciliation,
and a rendering progress string after known terminal is reported as an issue.

Optional identities remain independent typed fields: `realmAuthoringKey`,
`runtimeWorldId`, `catalogueId`. Each supplied value is
`{"type":"string","value":"..."}` or `{"type":"integer","value":7}`.
Absent identity remains absent; none is inferred or used as an alias. These
types do not define or change any realm's runtime identity contract.

An optional material witness contains explicit `used`, `retained`,
`validated_unused` lists and a pin to JSON containing those exact lists. A
missing used material is an error. An absent palette name is never silently
classified as an unused orphan. Usage proof is supplied by the producer, not
deduced from a missing material name.

## Immutable publication and uncertainty

Each snapshot uses a fresh explicit output name. Publication flushes and fsyncs
staged bytes, atomically hard-links them to the exclusive destination, then
reads back the receipt and rechecks evidence. It never replaces a published
receipt or falls back to a non-atomic overwrite. On systems without usable
hard links it fails closed. Windows AppContainer Temp denied this primitive
with WinError5 in the observed development sandbox; the same actual operation
worked in normal user Temp. Do not weaken publication to hide that restriction.
File flush/readback is not a promise of storage-device or Windows directory
power-loss durability. POSIX directory metadata is fsynced when supported.

A failure after linking can leave a complete public receipt. Inspect its bytes
and artifacts before retry; never infer "no effects" from an exception. To
extend history, supply `previous` with a pin to the prior snapshot. The reader
checks that prior stage contracts, attempt IDs, inputs, events, identities and
provenance were not rewritten. Append new events, attempts or stages instead.
Failed attempts remain evidence. Reports keep prior attempt details in `previous_attempts`; latest output/process/release/progress fields belong only to the latest attempt. An earlier partial/unknown/running attempt
keeps the job at an operator-reconciliation boundary even if a later attempt
claims success; the helper has no automatic reconciliation override.

An `external` stage always requires its native/operator qualification. A source
receipt, successful finite process, output file or material witness never proves
current editor state, native saves, collision, replication, visual quality or
gameplay. Every report keeps `native_qualified: false` and `execution: false`.

Bounds: 1 MiB JSON, 32 ordered stages, 16 attempts per stage, three lifecycle
events per attempt, 32 inputs/outputs, 256 verified pin reads and 256 MiB total
pin work per inspection; each pinned file is at most 64 MiB. Duplicate JSON
keys, unknown schema fields, nonfinite numbers, invalid UTC ordering and
contradictory process/outcome data fail verification. Hashes are point-in-time
observations of files, not locks against concurrent producer edits.

## Actual retained Copperfall and Nursery examples

Read-only development verification on 16 October 2026 used the original files
below. Set `COPPERFALL` to the existing
`task-3/copperfall-ark-rest-polish-842401` directory; select a **fresh** place to
retain stdout. These commands do not rebuild, render or import anything:

```text
python -m asset_pipeline.stages adapt-process --process COPPERFALL/before-hero-resume-export-r2.process.json --manifest COPPERFALL/before/manifest.json --job-id copperfall-completed --stage-id source-export-hero --attempt-id retained-read-1 --observed-at-utc CURRENT_UTC --output-field blend=source --output-field glb=exports.glb --output-field fbx=exports.fbx --output-field hero=renders.hero > completed.json
python -m asset_pipeline.stages verify completed.json
python -m asset_pipeline.stages adapt-process --process COPPERFALL/before-hero-build.process.json --manifest COPPERFALL/before/manifest-before-export-recovery.json --job-id copperfall-failed --stage-id source-export-hero --attempt-id retained-read-1 --observed-at-utc CURRENT_UTC --output-field blend=source > failed.json
python -m asset_pipeline.stages verify failed.json
```

Replace `CURRENT_UTC` with an actual UTC observation such as the current output
of `datetime.now(timezone.utc).isoformat()`, not an old example date. Full actual
files verified: completed recovery retained exit0 and four pinned outputs
(Blend/GLB/FBX/hero); prior exit1 retained only the saved Blend and reported
reconciliation required, not success or automatic replay. The failed source
was later recovered; this historical failure is not a current asset blocker.
Actual development receipts are separate from these portable test fixtures.

Nursery's retained `after-preview-r1-job/execution.json` contains actual
exit0/terminal-known/release readback while `after-preview-r1/job-progress.json`
still says `STATIC_EXPORT_SAVED_RENDERING`. With explicit output selections
from that progress manifest, the adapter's `--progress PATH --progress-field
stage` retains both facts and reports the stale progress issue. It does not
change the producer's progress file or rerun the job.

The portable suite embeds sanitized scalar excerpts with original logical
paths, byte sizes, SHA256 and dates: Copperfall failure430B/47287c75…,
recovery460B/b00b3cee…, Nursery execution11822B/29fe3f83… and progress5427B/
e03d72d6…. Its artifact bytes are explicitly synthetic; those tests do not
claim to reproduce Blender exports or prove native behavior. A wrapper owner
must accept emission/adoption into its existing runner; no live runner, bridge,
queue or native journal integration is performed by this package.
