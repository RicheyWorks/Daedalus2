# Offline campaign throughput toolkit

Python 3.10+, standard library only. These explicit commands never import a
producer, invoke Unreal/Blender, start a timer, acquire a campaign lease or change
production pins. Inputs are retained evidence supplied by the owner. Pins retain
the existing `{path, bytes, sha256}` contract; the toolkit never captures new
production pins. Only synthetic fixtures belong in this source directory.

```text
python -B -m tools.campaign_throughput_toolkit verify --request verify.json --output fresh-check
python -B -m tools.campaign_throughput_toolkit verify --request next.json --state fresh-check/state.json --full --output next-check
python -B -m tools.campaign_throughput_toolkit validate --request validation.json --report fresh-report.json
python -B -m tools.campaign_throughput_toolkit catalog --receipt-pin retained-pin.json --chunk 1 --output-dir fresh-offline-catalog
python -B -m tools.campaign_throughput_toolkit snapshot --output-dir fresh-offline-catalog
```

`verify.json` has schema `daedalus-offline-verify-request/1`, `pins` (all old
protected pins plus explicitly approved additions), absolute coverage `roots`,
`chunk`, optional `phase` (`start`, `chunk`, `stop`) and `full_every` (default 25).
After chunk 1 it requires `previous_chunk`, `previous_receipt` and nonempty
`previous_files` pins. The previous file pins must match the protected inventory.
The caller supplies their approved receipt-to-file binding; a receipt filename
or cache does not prove it. Every file in the coverage roots must be pinned.
Keep reports and cache outside those roots.

Initial/start/stop, every 25th chunk, explicit `--full`, and skipped checkpoints
hash the full inventory. Intermediate checks hash previous evidence, new pins
and files whose size/mtime/ctime/device/inode changed. Missing, unknown or changed
bytes, removed pins and altered old pins refuse. Metadata reuse is intermittent
verification: a concealed change may persist until the next full check. Trusted
local cache, trusted pins/parent directories and serial caller invocation are
required. Reads detect ordinary races, not an atomic filesystem snapshot. No
production cadence is activated.

`validation.json` has exactly schema `daedalus-offline-validation-request/1`,
`source_manifest` and `native_receipt` pins, absolute evidence `roots`, `chunk`,
ten-index `range`, and the 20 exact retained `item_ids` in source/receipt order.
Validation rehashes every blend/FBX, binds all imports to item/group destinations,
checks retained geometry/material/save evidence and canonical DataValidation
snapshots through `tools.unreal_mcp.native_validation_snapshot_consumer`.
It proposes one bounded pass over all referenced new assets (batches <=16),
lists material/other references without retained validation and shared references,
and sets `native_invoked=false`, `native_admission=false`. Existing receipts do
not prove a complete native dependency graph, validator implementation/set
parity, or native package hashes. Those remain explicit pending evidence.

Catalog export reuses the exact R18 `active_item`/`immutable` projections and CSV
columns, row order, UTF-8 and CRLF. A local SQLite index provides per-item lookups;
immutable item deltas and per-chunk CSVs append without rewriting a cumulative
JSON catalog. Unchanged entries are reused. `current.json` publishes last;
interrupted publication retains lock/pending evidence and refuses replay.
`--full` audits immutable segments against the index. `snapshot` explicitly
creates the cumulative stop snapshot. This is a **new offline index protocol**,
not a drop-in replacement for R18 `catalog-state.json`/`current.json`; old output
directories are refused. The per-item payload and per-chunk CSV contract remain
stable. Default receipt reads rehash pins; `--trust-metadata` is opt-in and
discloses its local cache trust. No-op exports preserve CSV/current bytes/mtime.

No source result establishes native admission or a speedup. Plan §4 still needs
Boss-owned review, a never-used sandbox range, same-seed/build source and package
byte parity, validator/dependency-closure parity, ten-chunk timing/resource
evidence, and saved-boundary adoption. Current R22c/scripts/config/guards/pins,
assets, receipts, catalogs and editor/lease state remain unchanged.

```text
python -B -m unittest discover -s tools/campaign_throughput_toolkit -t . -p 'test_*.py' -v
```
