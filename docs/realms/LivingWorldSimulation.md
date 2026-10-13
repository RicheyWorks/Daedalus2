# Living World Simulation: first slice

## Architecture assessment and plan

Repository assessment on 2026-10-12, base `586a4694`:

| Existing component | Reuse and gap |
|---|---|
| `daedalus-core` generators, graph/solver abstractions, `WorldId` | Portable deterministic foundation. Keep their APIs and world generation unchanged. |
| `world.ecology.Ecosystem`, `Community`, `EcologyLedger` | Already model seeded ecology and durable island populations. Do not replace them or introduce another weather/ecology engine. |
| `WorldService.tickEcology`, `MAX_CATCH_UP`, atomic sidecars | Existing server-clock and bounded catch-up pattern. Settlement resource/NPC/quest state and replay validation are missing. |
| `Npc`, `NpcState`, `WorldOps` | Existing NPC identity and interaction surface. Add a persistent decision overlay keyed to that identity, not another navigation or animation engine. |
| `WorldStore` v13, `WorldHub`, world packages | Preserve bytes/contracts. Add an independently versioned simulation sidecar; do not change geometry persistence. |
| REST `/api/v1/world/...`, STOMP `/topic/world/...`, Spring events | Reuse JSON/HTTP and STOMP transport. Add a versioned simulation resource; leave existing event frames unchanged. |
| Plugin event API/runtime and `LivingSlab` | Existing extensibility and live maze mutation. No parallel event bus or maze mutation implementation. |
| Wallet authentication / production JWT security | Player identity comes from the authenticated principal. No wallet, chain, token, or settlement dependency in core. |
| Poot's native Tideglass host / crafting PRs | Separate ownership. This slice transfers finite settlement water directly to its NPC; it does not introduce player inventories or a competing trade/reward ledger. |

Implement incrementally: (1) pure immutable deterministic transition model, (2) versioned
snapshot plus ordered replay tail and durable file adapter, (3) opt-in backend service and
versioned HTTP/STOMP surface, (4) replay/restart/idempotency/compatibility tests and measured
benchmark. No Unreal or Blender process, asset, or DaedalusLink changes.

The complete first scenario is one settlement in an existing world: its cistern regenerates
on simulation ticks, its keeper follows a daily schedule and requests water when supplies
run out, and a predictable dry spell temporarily stops regeneration. An authenticated
steward can deliver finite cistern water to the keeper. Delivering three units completes
the shortage quest and records who helped. Completion is persistent and grants no currency
or duplicable item. Unreal will render the resulting decisions through its existing API
client; local navigation, animation, physics, and combat remain engine responsibilities.

Initial risks and boundaries: one simulation writer per sidecar; atomically persist before
publishing/acknowledging transitions; bound catch-up and replay memory; reject malformed
snapshots and divergence; retain idempotency receipts without silently expiring them.
The service is opt-in and single-region. Active/inactive scheduling changes wake frequency,
not deterministic world rules. This is not a distributed MMO or a player-count claim.

## Implemented rules and persistence

`LivingWorld.apply(state, input)` is the portable entry point. It accepts an immutable
state and an ordered input, and returns the next state, optional receipt, and structured
events. The only dependencies are JDK 21 and existing core world identities. There are no
external calls in this transition function. `SimulationTimeline` retains a checkpoint
plus at most 64 state-changing inputs, each with the expected SHA-256 state hash.
Recovery replays and verifies every retained input. Compaction preserves current state
and all receipts; it does not retain an indefinite audit of older inputs.

The initial settlement has three cistern units and an empty keeper reserve. The cistern
gains one unit every six ticks, capped at twelve; the keeper consumes one every twelve
ticks, with a six-unit reserve cap. Hours 0–5 and 18–23 of each 24-tick day are rest time.
During working hours, an empty reserve selects `REQUEST_WATER`; otherwise the keeper
selects `WORK`. Each decision has a human-readable reason. This decision overlay uses
existing `npc-zero`; it does not change the existing NPC position/talk state.

The one-shot `DRY_SPELL` starts at tick `24 + floorMod(seed, 12)`, ends twelve ticks later,
and suppresses cistern regeneration while active. Its precondition is reaching that
scheduled tick; explicit start/end events record its duration. Delivery moves 1–3 actual
cistern units into the keeper reserve. Reaching three units completes the shortage quest
once and remembers the actor permanently, even when water is later consumed. The quest
has no item/currency reward, expiry, dependencies, or separate acceptance action in v1.

Host time is `(serverMillis - savedEpochMillis) / savedTickMillis`, with at most 64 ticks
per advance. Older targets cannot rewind state. Reads mark the region active for thirty
seconds; inactive regions wake at ten times the configured interval and use the same
rules. This avoids full-frequency idle updates but still performs bounded individual
steps, not an analytical simulation of arbitrarily long absences. Catch-up can require
multiple wakes. The initial v1 region is the single settlement selected by world ID.

The server commits before exposing state or publishing events. A local sidecar has an
exclusive lifetime file lock, a forced temporary file, and atomic replacement. Unsupported
atomic moves fail closed. Version, checksum, collection bounds, identity, and replay
hashes are checked on load; corrupt data never silently resets. A lost save acknowledgment
is reconciled from disk under the lock; an unknown outcome makes the service unavailable.
An abrupt JVM exit/restart is tested. Hardware power-loss durability and network filesystem
lock semantics are not claimed; directory metadata is not separately fsynced.

Bounds are 1 MiB per encoded snapshot, 64 replay inputs, 64 recent events, and 1,024
idempotency receipts. New unique deliveries are refused when receipts are full; old
duplicates remain valid. There is no automatic receipt eviction. Long-running production
use needs a reviewed durable receipt-store migration before lifting that limit. Back up
the sidecar while the writer is stopped; preserve its epoch, rate, seed, and steward.
Changing those configured identities/rate requires an explicit migration, not deleting
the file. SHA-256 detects corruption/divergence, not malicious edits by a disk owner.

## Backend configuration and wire contract

Disabled by default. Enable for an already mounted world and an existing authenticated
principal; the simulation does not create an account or grant inventory ownership.

```text
DAEDALUS_SIMULATION_ENABLED=true
DAEDALUS_SIMULATION_FILE=/absolute/persistent/path/world-zero.simulation
DAEDALUS_SIMULATION_STEWARD=alice
DAEDALUS_SIMULATION_WORLD_ID=world-zero
DAEDALUS_SIMULATION_TICK_MS=1000
DAEDALUS_SIMULATION_POLL_MS=1000
```

The sidecar directory must be writable and exclusive to this server. Spring properties
are the corresponding `daedalus.simulation.*` keys. `tick-ms` is 1–86,400,000; polling
must be a positive integer number of milliseconds. Seed comes from `WorldHub`, not a second
seed configuration. All new HTTP endpoints require authentication in production. Supply
also explicitly checks Principal in every profile and requires its name to equal the
configured steward. It reuses the `mazeGenerate` per-caller rate-limit template already
used for world mutations. No actor or time field is accepted as authoritative client input.

| Transport | Contract |
|---|---|
| `GET /api/v1/world/{id}/simulation/v1` | Current `View`, schema version 1. |
| `POST /api/v1/world/{id}/simulation/v1/actions/supply` | Body `{"requestId":"00000000-0000-0000-0000-000000000001","water":3}`; returns `{receipt, duplicate, state}`. |
| STOMP `/topic/world/{id}/simulation/v1` | `{state, events}` after a durable transition, through the existing broker. |

`View` fields: `schemaVersion`, `worldId`, `tick`, `revision`, `stateHash`, `cisternWater`,
`keeperWater`, `npcId`, `task`, `reason`, `questCompleted`, `rememberedActor`, `drySpell`,
`active`, `eventSequence`, and `events`. The internal receipt ledger is not exposed.
An event has `sequence`, `tick`, `kind`, and bounded diagnostic `detail`. A receipt has
`actor`, `water`, `tick`, `revision`, and `questCompleted` as of the original action.
Counters are signed Java 64-bit integers; clients should preserve their integer precision.
The state hash covers authoritative state, including private receipts; clients cannot
recompute it from the public view alone.

Supply uses a canonical lower-case UUID generated once per intent. Retry the identical
UUID and water amount after timeouts/500 responses: a committed retry returns the original
receipt with `duplicate=true` and the **current** view, without another transfer. Reusing
the UUID with another amount/actor is invalid. Validation/stock/full-reserve/unknown-world
errors are 400, missing principal 401, wrong steward 403, exhausted receipt capacity or
unavailable writer on supply 409, rate limits 429, and storage failure 500 via existing
error handling. Do not generate a new UUID merely because an acknowledgment was lost.

STOMP is best-effort, with no durable outbox in v1. The topic follows existing public world
topic authorization and contains public settlement memory, including the helping actor.
It must not carry private player inventory or secrets. Fetch GET on connection/reconnection,
on an event-sequence gap, and periodically to reconcile missed final updates. Use revision
to ignore older snapshots. Event sequence may stay unchanged for time/activity transitions.
Publication failure never rolls back committed state. Metrics are
`daedalus.simulation.tick`, `daedalus.simulation.events` (tick-generated events),
`daedalus.simulation.failures`, and `daedalus.simulation.publish.failures`.

## Unreal integration handoff

No Unreal project, assets, scenes, or DaedalusLink source changed in this PR. The HTTP and
STOMP contract is tested with the server's existing Spring MVC/JSON stack; this is not a
claim that the new endpoint has already run in Unreal.

The integration agent should add an optional consumer using the existing authenticated
HTTP/STOMP connection. Bind `npcId` to the existing keeper actor; show its task/reason,
cistern and reserve levels, shortage objective, remembered helper, and dry-spell state.
Unreal handles animation/navigation and immediate feedback. Send supply only on a player
intent, keep its UUID across retries, and display the authoritative response. Do not
subtract a native inventory item: v1 moves communal water and is not an inventory adapter.
Do not award a native currency/item on `QUEST_COMPLETED` without a separate idempotent
inventory-owner contract coordinated with PootScoot/Claude.

Acceptance sequence: enable against a test world; GET initial 3/0; reach working hours
and observe `REQUEST_WATER`; deliver three with the steward's token; observe durable quest
completion and memory; repeat the same UUID and observe no extra transfer; restart the
backend and verify the same receipt/memory; observe dry spell and subsequent regeneration.
The backend tests exercise these transitions without an editor. A visible Unreal playtest
is the integration agent's remaining step, under the team's editor lease.

## Extension contracts (design, not additional engines)

Keep future modules as pure ordered transitions over versioned state, with external work
in adapters. A future `NpcDecisionPolicy` takes a read-only NPC/region snapshot and tick,
and returns a bounded intent plus reason; only the authoritative transition validates and
applies it. Optional high-level AI uses this same proposal boundary, never mutating state.
Relationship/faction memory and additional schedules require a schema migration.

A quest template should declare ID/version, precondition, objective, validated effects,
dependencies and failure rules. V1's shortage is the first concrete rule. Any future reward
must be committed through the established inventory owner with the quest completion ID as
the idempotency key. Crafting, player inventories, trade and blockchain settlement remain
external adapters; do not fork the native Tideglass CAS/save/retry host.

The future Director proposal contract is `(proposalId, schemaVersion, worldId,
expectedRevision, allowedEventType, boundedParameters, reason, expiresAtTick)`. Its input
is a read-only region/quest/resource/event summary plus aggregated activity telemetry.
An authoritative validator checks revision, expiry, allowed type, preconditions, duration
and effect budget, then logs an ordered accepted input. Rejection makes no state change.
The Director receives no direct ownership/inventory mutation capability. Reversal is a
new validated compensating input where feasible, never history rewriting. No AI Director
or arbitrary executable event scripting is introduced in this slice.

## Reproducible measurements

Run from the repository root after compiling core, using JDK 21 (`;` classpath separator
on Windows, `:` on Unix):

```text
mvn -B -ntp -pl daedalus-core -am test
javac --release 21 -cp daedalus-core/target/classes -d examples/benchmark-harness/target/simulation-classes examples/benchmark-harness/src/main/java/com/daedalus/examples/benchmark/LivingWorldBenchmark.java
java -Xms128m -Xmx128m -cp "daedalus-core/target/classes;examples/benchmark-harness/target/simulation-classes" com.daedalus.examples.benchmark.LivingWorldBenchmark 100000
```

Measured 2026-10-12 on Windows 11, Java 21.0.4, 24 logical processors, shared development
machine, one JVM thread. Raw output: [living-world-benchmark.csv](living-world-benchmark.csv).
Each throughput row uses 10,000 warm-up updates, 100,000 measured updates, empty receipt
ledgers and one tick per update. Latency percentiles sample the first 1,000 measured updates.

| Synthetic regions | Updates/s | p50 / p95 update | Heap before / after (bytes) |
|---:|---:|---:|---:|
| 1 | 875,074 | 1.6 / 2.6 µs | 9,371,648 / 29,180,048 |
| 100 | 1,076,119 | 1.2 / 2.1 µs | 51,200,144 / 7,882,096 |
| 1,000 | 1,169,674 | 1.3 / 2.1 µs | 27,805,040 / 4,599,448 |

The 5,707-byte snapshot with 64 replay inputs averaged 14.060 µs encode and 207.810 µs
decode/replay over 1,000 samples after 100 warm-ups. At the full 1,024-receipt bound,
1,000 64-tick catch-up updates averaged 208.009 µs after 200 warm-ups; an 80,299-byte
snapshot with 64 such replay inputs averaged 21.780 ms recovery over 20 samples.
This exposes receipt validation/copy/hash cost instead of extrapolating from empty ledgers.

Heap readings include garbage and GC timing; they are not retained/peak measurements.
These are descriptive microbenchmarks, not CI speed thresholds, disk persistence latency,
network benchmarks, entity population limits, or multiplayer capacity claims. Regional
rows represent one NPC/resource pair each. The production adapter currently hosts one
region and synchronously persists outside the pure kernel before publication.

## Verification and review status

JDK 21.0.4 validation: full server reactor `mvn -B -ntp -pl daedalus-server -am test`
passed 570 core, 20 Plugin API, 8 wallet, 33 plugin-runtime and 697 server tests.
A subsequent full core run, including one added malformed-snapshot test, passed 571.
That is 1,329 passing tests across the latest module runs, including 23 new simulation
tests. Final focused validation after path/polling hardening passed all 32 simulation
and API/configuration/security-coverage tests. Existing `WorldStoreTest`, world-package API, deterministic generation and
configuration/auth/rate-limit coverage tests remain green.

New tests cover deterministic replay through checkpoint compaction, corruption and
checksummed malformed payloads, dry-spell recovery, finite transfer/quest/NPC memory,
invalid/unauthorized input, duplicate and concurrent retries, receipt exhaustion,
exclusive writers, persistence/publication failures, lost acknowledgments, unavailable
storage, bounded catch-up and clock reversal, Spring opt-in/restart wiring, HTTP/STOMP
JSON contracts, and abrupt child-JVM termination followed by restart.

Checkstyle is clean. Core coverage and SpotBugs pass; two narrowly scoped immutable
timeline-field exclusions explain SpotBugs' representation warnings without suppressing
other classes or lowering severity. Full `verify` is blocked in unchanged
`daedalus-plugin-api`: instruction coverage 0.76 versus its required 0.96. This branch
does not change that module or its gate. Running the server checks independently also
finds three SpotBugs warnings in unchanged `PresenceService` (lines 54, 63 and 99), and
server instruction coverage 0.83 versus its 0.93 floor. Existing server classes account
for 27,084 covered / 5,554 missed instructions (83%); the new simulation adapter/config/
controller account for 785 covered / 33 missed (96%). The new simulation classes have
no remaining SpotBugs findings. Registry sharing has one narrowly scoped field exclusion.
No coverage threshold or unrelated source was changed to bypass these failures.
The PR must not be described as all-CI-green.
Unreal runtime acceptance remains an explicit integration handoff, not a backend test claim.

Checks beyond unit tests:

```text
mvn -B -ntp -pl daedalus-server -am verify
mvn -B -ntp -pl daedalus-server -am -DskipTests package spotbugs:check
mvn -B -ntp -pl daedalus-server jacoco:report jacoco:check@check
```

The first stops at the Plugin API gate after core verification passes. The second reaches
the server and reports only the three existing PresenceService findings. The third
checks the server's configured coverage rule independently. Keep those blockers visible
during review; do not merge or deploy this optional service as part of this handoff.
