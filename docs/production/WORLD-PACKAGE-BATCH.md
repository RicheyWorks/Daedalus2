# Offline World Package batch planning

`python -m tools.world_package.batch_cli request.json` validates up to 16 explicit
packages serially and prints a deterministic inventory. It uses the existing
single-package reader, archive integrity checks, destination derivation and replay
rules. It never extracts packages, imports assets or connects to a running world.

```json
{
  "format": "daedalus-world-batch-request",
  "version": 1,
  "packages": [
    {"key": "north", "package": "fixtures/north.daedalus.zip"},
    {"key": "south", "package": "fixtures/south.daedalus.zip"}
  ],
  "prior_receipts": []
}
```

Paths in CLI requests are relative to the request file; API paths are passed to
the existing planner as supplied. Keys are unique, case sensitive caller labels.
URLs, UNC/device paths and drive-relative paths are refused before opening any
request, package or export path. Windows root-only paths also refuse rather than
depending on a hidden current drive. No directory discovery, globbing, network
fetch or previous-plan loading occurs. Local filesystem links are not a sandbox;
callers must choose trusted local input and output parent directories.
The request and result share `tools/world_package/batch-plan-v1.schema.json`, which
references the existing single-plan/receipt schema. Offline schema consumers must
register that local schema; the `.invalid` schema ID is not a network endpoint.

Inputs are processed in key order. Unique inventory records are sorted by raw
world ID, revision and exact ZIP SHA-256. Exact-byte aliases reference the smallest
key and receive `duplicate`; this does not imply acceptance. Different bytes for
the same raw world/revision mark every matching alias `conflict`, with no selected
winner or executable plan in those records. Distinct revisions retain separate
versioned destinations. Unicode, case and original asset identities are preserved.

`prior_receipts` contains at most one explicit accepted v1 receipt per raw world
ID. All receipts are validated, including unused ones. Every candidate for a
world is compared against that same receipt. An exact accepted replay becomes
`no_op`; stale revisions and conflicting accepted bytes are errors. A proposal
never becomes evidence for a later proposal. To resume work, rerun the explicit
request with actual owner-supplied accepted receipts. Receipt authenticity and
native acceptance remain the native owner's responsibility.

Malformed request envelopes refuse immediately. Individual package and replay
errors are retained in `items`, while independent inputs still get inventory
records. `ready` is false if any item has an error or conflict, and the CLI exits
1. Such output is a diagnostic inventory and must not be admitted as a batch.
`counts` counts input items, so duplicate and conflicting aliases are included.

`--output new-plan.json` exclusively creates a file only for a ready batch.
Serialization completes before creation. Existing files, links, directories,
inputs and request files are refused without truncation. The same JSON is also
printed to stdout. A write/close failure returns 1 and may leave a partial newly
created file; it is reported and preserved, never silently replaced or cleaned up.
There is no native importer execution command.

Resource limits are 1 MiB request JSON, 16 inputs/receipts and 8 MiB serialized
inventory. Each package retains the reader's 64 MiB compressed snapshot, 256 MiB
expanded and 4096-member limits. Before opening an input, the batch reserves its
full 64 MiB plus oversize-probe allowance from a 256 MiB source-read budget.
Successful snapshots refund unused bytes; failures conservatively retain their
reservation. An input is refused before opening when a full reservation cannot
fit, even if its apparent file size is small. `budget` distinguishes charged and
successfully validated bytes. Exact duplicates are each validated and charged;
no untrusted path/stat cache substitutes for a snapshot. Expanded data remains
serial and per-package bounded (at most 16 times the per-package work limit).
