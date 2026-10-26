# Offline takeover packets

This is a source capability for packaging the existing Daedalus checkpoint and
evidence chain while an operator is healthy. A successor can inspect the sealed
packet and produce a deterministic admission plan without an outgoing model
response. **Generic automatic takeover is not deployed.** Nothing here starts a
producer, probes processes, acquires scheduler leases, touches the editor, or
installs a listener or daemon.

Python 3.10+ and the standard library are sufficient. Run from the repository root:

```sh
python -m unittest tools.team_handoff.test_takeover -v
python -m tools.team_handoff.cli seal --store /tmp/takeover-demo --checkpoint tools/team_handoff/examples/checkpoint.json --evidence-root tools/team_handoff/examples --expected-current none
python -m tools.team_handoff.cli inspect --store /tmp/takeover-demo
python -m tools.team_handoff.cli plan --store /tmp/takeover-demo --request tools/team_handoff/examples/admission.json
```

Use a fresh private store outside the evidence tree; the paths must be disjoint.
The examples are synthetic, with fixed timestamps and declared build facts. Set
the admission request's `packet_sha256` to the digest returned by `seal`; changing
any checkpoint or evidence byte changes that digest. The example request is an
offline fixture, not current authority or a reusable production window. On Windows,
substitute a fresh temporary path for `/tmp/takeover-demo`.
In constrained local sandboxes, set `DAEDALUS_TEST_TMPDIR` to an explicitly writable
fixture directory before running tests; ordinary CI runner temporary storage works
with the default.

`examples/checkpoint.json` is the normalized versioned summary; its checkpoint
evidence role points to the separate raw `current-operator-checkpoint.json`.

CLI exit codes are `0` for publication, inspection or a plan ready for live
admission, `3` for a held plan, and `2` for malformed input, integrity failure or
I/O failure. Errors contain a stable `error.code` and a specific message. Every
plan sets `may_execute: false` and `live_integration_required: true`. Readiness
describes the supplied evidence; it grants no work authorization.

## Package and publication contract

`seal(store, checkpoint, evidence_root, expected_current=None)` copies the seven
named evidence roles without changing their original bytes or files. The embedded
versioned checkpoint is a summary of those existing receipts, not a replacement
progress ledger. It retains owner/session/host/PID/start identity, runtime and
configuration/artifact pins, the original run window, sequence/prior digest,
counts, next index, phase,
provenance and operation outcomes. Unknown provenance is explicit and remains a
hold; post hoc current hashes do not establish historical build parity.

The implementation reuses the R18/R20 receipt fields and the R22 / existing
`asset_pipeline.live_handoff` durable-write pattern: exclusive file creation,
flush/fsync, cooperative OS serialization, and atomic pointer replacement last.
It introduces no second message transport or production lock protocol.

```text
store/
  .publish.lock                 private publication serialization only
  current.json                  schema + selected packet SHA-256
  previous.json                 prior valid selection after an update
  packets/<manifest-sha256>/
    manifest.json               schema + checkpoint + file hashes and sizes
    evidence/<relative-path>    exact retained receipt copies
```

Receipt copies and manifest are written and checked before publication. A new
store requires sequence `1` and a null prior digest. Each update requires the exact
`expected_current` digest, same campaign, next sequence, matching prior digest,
nondecreasing saved time/counts/next index, and a valid predecessor packet. Missing
or corrupt current state never silently initializes a new chain. Same-campaign
updates preserve the original window; `window_chain` rejects a reset.

An interrupted publication leaves the old current packet selected until atomic
replacement. Staging directories, unadvertised sealed packets and temporary files
are retained for diagnosis. Failure after pointer replacement has an uncertain
caller outcome: inspect current state before any retry. The current pointer's
failure does not cause automatic fallback. `inspect --selection previous` can
read retained evidence; planning from `previous` always holds until current and
later dispatch evidence have been reconciled.

The store is for cooperating writers on a local filesystem with atomic rename.
Its OS lock releases when its process exits; the remaining lock filename does not
prove a live publisher. It is unrelated to producer identity, scheduler leases or
resource custody. Expected-current checks are not compare-and-swap against an
external writer that ignores the protocol. There is no hostile-writer fencing,
network-filesystem guarantee or whole-machine power-loss guarantee. Hashes detect
content changes relative to a pinned digest; they are not signatures, authentication
or tamper-proof storage. Pin the advertised digest through the existing trusted
handoff route.

## Evidence adapters and provenance

Each evidence role is either `{status: present, path: <relative-path>, reason: null}`
or `{status: unknown, path: null, reason: <explicit reason>}`. Paths are portable,
normalized and distinct without case collisions; symlinks, junctions/reparse
points, traversal, reserved device names, missing/extra files, duplicate JSON keys,
unsupported schemas and hash/size mismatches are rejected. Evidence is limited to
16 MiB per file and 64 MiB per packet; JSON documents are limited to 2 MiB.

| Role | Supported retained content and checks |
| --- | --- |
| `checkpoint` | Existing R20 monitor JSON: `saved_counts`, `next_index` and `owner_pid` match the summary. Saved/stopped phases require `active.stage` to be `chunk_saved` or `paused_saved_boundary`. |
| `owner` | Existing owner JSON: `pid` matches; any supplied owner/session/host/start identity must also match. Legacy `utc` is not treated as process start time. |
| `ledger` | Existing ledger JSON: `saved_counts` and `next_index` match. Other original fields stay intact. |
| `native` | Original native JSON, directly or under `native`. Saved/stopped boundaries require `saved: true`, empty dirty maps/content, no Play and no active import. |
| `catalog` | Existing catalog receipt/export bytes, hash-bound without inventing new item identities or approval. |
| `source` | When recorded: exact `daedalus.build-inputs.v1` manifest with commit and complete declared source/header/descriptor/config/generated input inventory. |
| `build` | When bound: exact `daedalus.build-provenance.v1` receipt, matching source commit, before/after input digest and artifact hash, build-time capture flag, engine/compiler, command and successful exit. |

These adapters cross-check retained boundary facts. They do not inspect saved
assets, catalog rows, all native admission conditions or the actual compiler
input graph. Generation identity must come from an independently verified launch
receipt/probe, not legacy owner timestamps. A build input inventory's completeness
and `recorded_at_build_time` are producer attestations; this package does not
retroactively prove them or run a build. The later build integration must freeze
and capture the actual complete inputs around the build.

Operations retain stable IDs, target IDs, intent/result digests, outcome and
reconciliation status. Their non-null digests must refer to retained evidence
bytes; aggregate journal/ledger/native receipts may carry those facts. Unknown,
pending and partial outcomes remain unresolved. A saved reconciled operation is
already recorded, never a replay instruction. The planner never increments
counts or next index, retries an operation, or manufactures exactly-once effects.

## Admission and library use

```python
from tools.team_handoff.contracts import plan
from tools.team_handoff.packet import read_json, read_packet

packet = read_packet(store)  # integrity, supported adapters and provenance first
result = plan(packet["checkpoint"], read_json(request_path), packet["sha256"],
              selection=packet["selection"])
```

The pure `plan` function validates document structure and supplied facts. It does
no filesystem verification itself: use `read_packet` before planning, as the CLI
does. It requires a fresh successor session, explicit existing authority reference,
same host, matching runtime/generation/config/artifact, sufficiently fresh exact
predecessor identity and verified absent/exited state, both custody observations
for the actual successor, a valid existing window, bound source/build provenance,
all required evidence and complete journal inventory through the observation.
The request window must match the retained checkpoint's exact UTC instants;
`WINDOW_CHANGED` holds an attempted extension or restart. Its original authority
and authenticity remain live-provider attestations, not proof created by this library.
Alive, inaccessible/unknown, stale or reused identities hold. Source exceptions
and changed bindings require a separately reviewed transition; v1 has no bypass.

Later operation evidence, incomplete inventory, unresolved outcomes and a
noncurrent packet hold continuation. Outgoing silence, stale heartbeat, lease
expiry and timeout are never process-death or no-effect evidence. The current
checkpoint can predate dispatch journals outside this store: an integration must
inventory those durable journals before supplying `journal.complete: true`.
That declaration is an attestation, not a scan performed by this library.

The schemas in `schemas/` describe the versioned wire shapes. Python validators
are authoritative for semantic equality, timestamp precision/calendar validity,
relative paths, hash links and conditional admission. Preserve up to nine UTC
fractional digits, including .NET's seven-digit process generation timestamps.

## Explicit legacy-source snapshot adapter

`source_snapshot.capture(request, source_root, store)` closes the offline seam
between exported legacy receipts and `seal`. The supported profile is
`legacy-r22-saved-boundary.v1`; actual owner names are data. It reads only the
twelve allowlisted input roles and never searches a campaign directory or follows
a path embedded in a receipt. Each supplied file has an explicit relative path,
original logical reference, SHA-256 and byte size. Missing facts require an
explicit absence reason. The output store must be fresh, with an existing parent,
and disjoint from the exported inputs.

```sh
python -m tools.team_handoff.cli source-snapshot --request tools/team_handoff/examples/source-snapshot-request.json --source-root tools/team_handoff/examples --store /tmp/source-snapshot-demo
python -m tools.team_handoff.cli inspect-source-snapshot --store /tmp/source-snapshot-demo --expected-receipt <receipt_sha256>
```

The fixtures are synthetic and have fixed historical timestamps. Choose a fresh
temporary output path on Windows. A completed capture returns `status: sealed`,
but **always** `admission_status: held`, `liveness: not_observed` and
`may_execute: false`. Exit `0` means the offline capture/inspection completed;
exit `3` retains a source-evidence HOLD, and exit `2` reports malformed input or
I/O/integrity failure. File observation time and historical `owner_live` fields
never become current liveness evidence.

The profile requires a consistent session/config, producer launch, owner,
terminal saved boundary, ledger, monitor, native receipt, catalog and explicit
journal inventory. Session owner/reference, producer PID/start and editor
PID/start must agree. Producer start comes from the pinned launch receipt, not
`owner.utc`. Original session start/deadline define the sealed window; the
request has no replacement-window field. `config.initial_checkpoint` describes
the predecessor and never resets current saved progress. Counts/next index come
from the agreeing current ledger/terminal/monitor. The last saved journal event
supplies `saved_utc`; capture time and file mtimes cannot refresh it.

The explicit journal copy uses `daedalus.source-operation-journal.v1` with a
session ID, complete-inventory declaration, cutoff and operations. Each operation
retains the existing six operation fields plus its original `event_utc`. The
current save must bind the retained ledger intent, native result and exact native
stable item identities. Unresolved operations, later results, source counts ahead
of saved counts, pending work, mismatched worlds/references or stale source events
hold capture. Nothing derives a replay command. This is a supported offline
inventory contract; no real journal scanner or reconciliation provider is installed.

All inputs are copied without rewriting their bytes, with complete hash rounds
around copying and a final recheck after semantic validation. Changed, missing or
contradictory files leave copied witnesses and a held result without publishing a
current packet. Input sets must be quiescent immutable exports: endpoint hashes
detect observable changes, and cannot fence an unrelated writer, detect arbitrary
ABA replacement or establish that no later live dispatch occurred.

```text
fresh-store/
  source-snapshot/
    request.json, capture.json, result.json
    copies/<role>.json          original exported bytes, including supplements
  packet/                       the existing sealed-packet store
    current.json, packets/...
```

Session, launch, config, terminal and journal originals are supplements to the
existing seven packet roles. The capture manifest pins every copy, both hash
rounds, the request and the mapped checkpoint. Its completed result links that
manifest to the sealed packet digest. **Pin both `receipt_sha256` and
`packet_sha256` through the trusted handoff route.**
`read_snapshot(store, expected_sha256=...)` verifies this composite, including
all supplements and the existing packet reader; `read_packet` alone does not
verify supplementary lineage. The checkpoint retains the latest verified save;
earlier reconciled operation history stays byte-for-byte in the journal copy.

An interruption may leave copies or even `packet/current.json` before the final
capture result exists. `read_snapshot` reports `snapshot_incomplete`; inspect and
reconcile that outcome. Repeating capture against an existing store is refused,
including after an interrupted or held attempt. Each new capture uses its own
retained store and starts an independent packet chain at sequence `1`; this
adapter does not mutate or append to a prior packet store.

Missing source/build receipts remain explicitly unknown. Supplied build-time
claims are checked by the existing provenance validator; current byte pins,
capture time or a supplied DLL hash never manufacture historical parity. Runtime
metadata, source completeness and journal completeness remain declared facts
requiring trusted integration. The adapter performs no process, resource,
broker, editor, build or custody calls.

## Remaining production integration

1. Have the existing sole producer call `seal` at coherent healthy boundaries with
   retained immutable receipt versions. Capture dispatch intents before effects
   and result/save/readback afterward; heartbeat updates must not relabel in-flight
   work as saved. No outgoing final message is required by the API.
2. Capture the exact complete frozen build input inventory and toolchain when the
   build runs, recheck it afterward, and retain output hashes. Add a supported,
   reviewed versioned transition when sources, runtime or editor generation change;
   missing historical binding remains unknown.
3. Supply real owner-generation probes, trusted current authority and normal
   scheduler custody observations, then perform the existing resource, native,
   quiescence, saved-asset/catalog and deadline admission checks. This library does
   not implement those providers or release any lease.
4. Reconcile all later journals and uncertain effects under the supported existing
   lifecycle. Test integration in an approved disposable window with the outgoing
   agent absent. Keep live acceptance separate from source tests and PR merge.

This change does not modify the immutable R22c packet, its session-specific stale
lock procedure, live guards, active campaigns, shared BOARD files or any original
assets/receipts. Future integration remains with the verified sole custodian.
