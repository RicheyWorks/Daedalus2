# Journaled operator asset batches

Runs explicit static-asset specs through the existing prebuilt/land pipeline. This is an operator
batch executor, not a replacement art board, broker queue, scene producer or automatic editor watcher.

## Implemented code
* Bounded schema1 specs:1..500 unique named static assets, source SHA256 and Blender export evidence,
  safe destinations, operator source-root containment. Duplicate JSON fields are rejected.
* File-only planning: source hashes and static route compatibility, no journal or bridge queries.
* Exclusive OS journal lock, atomically published progress/receipts, immutable spec/root binding.
* Completed verified/rejected assets skip on resume. Only preparing/prepared/not-dispatched states
  can be attempted again. Unknown/reply-received/error-received dispatches require reconciliation;
  neither a timeout nor a caller-edited READY board row is used as cancellation evidence.
* Actual current Unreal lease observed before each asset. It must belong to --me and cover the
  configured import observation window. The executor never claims/renews/steals a lease.
* One import call at a time. On dispatch failure the batch stops, preserves the retained snapshot
  and request receipt, and makes no subsequent editor mutation. No transport retry is introduced.
* Skinned/animated/morph GLBs refuse this static route; use the existing dedicated cast importer.

Example spec:
```
{"schema_version":1,"assets":[{"name":"Prop_Lamp","kind":"static","glb":"Prop_Lamp.glb",
 "sha256":"<actual64hex>","dest":"/Game/Daedalus/Art/Prop",
 "blender":{"objects":[{"name":"Lamp","triangles":60,"materials":["Brass"],"dims":[1,0.4,0.4]}]}}]}
```

Run from connectors/claude-asset-pipeline:
```
python -m asset_pipeline.pipeline_batch --spec batch.json --source-root ART_ROOT
python -m asset_pipeline.pipeline_batch --spec batch.json --source-root ART_ROOT --journal run.json --run --me EXISTING_LEASE_HOLDER --limit 25
```
Default mode plans only. --run explicitly imports and requires the existing lease. Rerunning the same
spec/journal resumes completed work without repeating it. Changed specs need a new reviewed run;
never reset unknown journal state just to get past a hold. Reconciliation tooling is a separate
operator slice and is not implemented here. There is no automatic snapshot deletion.

Offline native smoke used the actual repaired Gallery Ramp for file planning, persisted/reloaded
unknown dispatch refusal, and overlapping-writer lock refusal. No bridge/editor commands executed.
This does not prove live batch speed, import correctness or frame-budget behavior on large assets.
Shared-editor operation remains owner-controlled. A separate journal does not grant a second engine
lease; the lease guard is required before mutation.
