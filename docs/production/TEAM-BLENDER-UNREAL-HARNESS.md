# Shared team and editor harness improvements

Source inspection on 2026-10-13, Codex. This is a source assessment, not a live editor benchmark.

## What Blender gets right
Installed addon: `%APPDATA%/Blender Foundation/Blender/4.3/scripts/addons/claude_blender_bridge/__init__.py`, version1.0.2.
It binds loopback, echoes request IDs, frames JSON by newline, queues work onto Blender's main-thread timer,
and exposes scene/object inspection, code execution and visual results. Main-thread execution matches bpy's requirements.
The separate `projects/blender-harness` layers discoverable plugins, risk levels, logs/accounting and
queue ownership over that connector. Its queue protects unsaved work, refuses another owner's active asset,
and distinguishes REJECTED asset defects from BLOCKED editor availability. These are reusable patterns.

Its limitations matter too: client timeout does not cancel Blender work; blindly retrying can duplicate it.
Discovery and fast screenshots do not establish durable async receipt/replay protection. The installed addon
has a 64MiB line limit and main-thread timeout1800s; those are source settings, not measured responsiveness.

## Shared Codex, Claude and Grok contract
Use the existing teamlink/live_handoff protocol for all teams, including Grok when available. A queued message
is not acceptance. Producer sends one artifact-first request to its named consumer; consumer acknowledges,
reviews, and returns source hash plus a planned integration window. Engine mutation requires the shared lease.
Never restart a job solely because a request or observation timed out. Carry exact source/artifact identity
through export, queue, import, saved package and runtime evidence. Build completion is distinct from success;
saved scene construction is distinct from playable acceptance. Keep wrappers model-independent.

## Implemented pipeline improvement
New export/prebuilt reports bind their GLB to streamed SHA256 plus byte count, checked before Unreal import.
A same-size replacement is refused before any editor request. Changes detected while collecting the GLB
witness are refused. Legacy reports retain compatibility through structural revalidation and are explicitly
labelled legacy-structure-only; they do not gain a false historical byte identity.
Tests cover unchanged, same-size mutation, missing file, collection mutation and both legacy paths.
This is a pre-dispatch check, not a filesystem lock: a writer racing after validation is still possible.
Next stronger step is an immutable content-addressed import snapshot with importer-side digest confirmation.

## Coordinated next work
Poot owns command discovery and turn-runner checkpoints; Codex owns the pipeline byte-identity seam and
Unreal launcher stack89/101/102/104/105. Claude owns runtime/editor integration. Confirm current claims
on the hub before implementation. Blender harness additions should reuse its Registry/Gateway rather than
introduce a parallel queue: add durable accepted/running/completed/succeeded receipts, replay-safe job IDs,
and bounded progress/status inspection. Add producer/consumer stage timestamps to measure queue delay,
export, import and verification separately. Do not label planned changes as installed.

No installed addon, live Blender scene, Unreal editor, stable team client or hosted service was changed by this PR.


## Follow-up implementation: private import snapshots
land() now copies into a unique temporary daedalus-pipeline/import-snapshots subdirectory,
verifies the copy and sends its path plus digest to Unreal. The import script validates the
snapshot before creating AssetImportTask. Source path and private import path are both in the
report. Snapshots remain after success/failure/timeout; do not delete them while a job might
still be active. A future explicit quiescent-job cleanup command is needed to bound disk use.
This is isolated handoff storage, not OS-enforced immutability or protection against an adversary
changing the private file after the importer's digest check. Legacy evidence remains labelled.
