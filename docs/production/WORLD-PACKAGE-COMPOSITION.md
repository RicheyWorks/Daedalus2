# Compose frozen World Package jobs

`python -m tools.world_package.job_compose_cli create --child north JOB_A --child south JOB_B --output FRESH`
creates one self-contained aggregate. The library entry point is
`compose_jobs([{"key": "north", "job": "JOB_A"}, ...], fresh_output)`.
Selection is explicit; no directory discovery or original-package lookup occurs.
Caller keys are unique, bounded text and sorted deterministically. Aggregate keys
use fixed child/item indices, preserving original keys separately without using
them as filesystem names. Existing outputs and outputs inside selected children
refuse without overwrite or cleanup.

Each child passes existing `inspect_job` validation. Its exact manifest,
provenance, request and plan bytes are copied under `children/0000/`-style paths.
These control-only records are lineage, not standalone executable or accepted
jobs. `aggregate/` is one unchanged existing frozen-job layout containing all
selected ZIPs. Copied ZIP hashes/sizes are checked again against inspected child
pins. `lineage.json` retains child manifest digests, caller/original keys, source
paths as provenance and exact child-to-aggregate mappings. The outer
`composite.json` publishes last through the same no-replace hardlink method.

Identical complete accepted-receipt values deduplicate by raw world ID.
Conflicting values, including differing witness references, refuse rather than
choosing a newer/preferred receipt. Global receipt union may change aggregate
actions or make a candidate stale; child plans retain their original receipt
scope. Plans and job manifests never confer acceptance. Existing batch rules
handle byte aliases and cross-child world/revision conflicts.

`python -m tools.world_package.job_compose_cli inspect FRESH` verifies outer
inventory/pins and the aggregate job, derives mapping/receipt union from copied
controls and replays each child plan against aggregate ZIPs with its own receipts.
No source-child or original path is reopened, and moving the whole container
preserves inspection results. Both APIs return manifest, aggregate and lineage;
the CLI prints a bounded manifest summary.

Limits are 16 selectors and 16 total package inputs, the existing 256 MiB package
budget, 16 MiB total copied child controls, 1 MiB lineage and 64 KiB per manifest.
All metadata budgets preflight before deep child inspection. Existing ZIP and
plan limits remain. The first refusal stops composition without claiming later
children were evaluated. Partial outer evidence is retained; a nested aggregate
may already be published while the outer job remains unpublished. Uncertain
publication must be inspected before any retry. Hardlink support and trusted
parent directories/no competing writers remain required. Pins prove retained-byte
consistency, not authenticity or custody. No extraction, native import, execution,
scheduler, lease or live-world action is provided.
