# Host consumer for scene schema1

Implements Poot's actual SCENE-V1 contract from scoped-scene-observation, supplied in29531.
No producer changes, competing schema, editor call on import, remote queue or mutation retry.

asset_pipeline.scene_observation provides:
* snapshot(result, request): strict booleans/counts/context, exact path uniqueness, finite numeric
  values, bounded components/material slots, scope/paging/error consistency, explicit unavailable.
* verify_request(request): checks supported predicates/context before dispatch.
* verification(result, request): every requested exact identity must have one result, stale/source
  failures stay explicit, status/diagnostics agree with observed values and requested tolerances.
  Correlated reported match contradicted by observed values is malformed, never silently accepted.
* SceneClient.snapshot/verify: existing read commands through the host wire client.
* SceneClient.pages: bounded traversal with context-change and duplicate-path refusal. It records
  fresh pages and keeps atomic:false/loaded_only:true. Multiple pages never become a complete snapshot.
* CLI offline snapshot/verify JSON validation. --request is required for verification. Duplicate JSON
  fields, oversized/opaque/nonfinite values and invalid envelopes do not become healthy defaults.

All valid observed values are copied without rounding or boolean coercion. Nullable fields must be
present. Labels are preserved but never used as a fallback for exact path checks. Parent paths may
refer outside the page. Ordered nullable material slots and zero-slot/zero-component predicates
retain their meaning. Rotations use the producer contract's wrapped Euler-coordinate tolerance.

Offline smoke consumed all7 actual producer fixture shapes: full/empty/paged snapshots and
match/mismatch/unavailable/stale verification. A forged match with contradictory observed location
was refused. These are producer fake_unreal fixtures, not live editor evidence.

Example:
```
python -m asset_pipeline.scene_observation snapshot --input SNAPSHOT_REPLY.json --out CHECKED.json
python -m asset_pipeline.scene_observation verify --input VERIFY_REPLY.json --request REQUEST.json --out CHECKED.json
```
The producer is still under its own reviewed rollout. Paths/epochs are observation identities,
not permanent IDs or write authority. Same-path/native-address reuse limitations remain unchanged.
Read-only code must not infer WorldPartition-unloaded coverage or fix a scene based on these results.
