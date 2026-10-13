# Adaptive Combat Director: first encounter

This is an additive Java strategic layer over Claude's `SquadDirector` and `TacticalOrders`
from `e0f48495` (ADR-060). It does not replace the native fallback or change DTO 1/DTE 1.
The branch includes the reviewed Living World work from PR29; neither branch is deployed.

## Reuse and gaps

| Existing component | Use / boundary |
|---|---|
| `TacticalOrders`, `SquadDirector`, C++ tactics core, parity fixture | Reuse wire format, deterministic distance/name ordering, flank/retreat geometry and local fallback. |
| `Graph`, `MazeGraph`, `CsrGraph`, BFS/A* and solver budgets | Existing strategic topology seam; do not introduce another pathfinder. They are not 3D navigation. |
| `LivingWorld`, checkpoint/replay, WorldHub, REST/STOMP | Persistent-world authority and transport patterns remain separate from combat execution. |
| `WorldStore`, world-package export | Preserve bytes and public contracts. Faction checkpoint is separate, versioned DTM 1. |
| `WorldMesher`, `DaedalusMeshCore.h`, `MeshFixtureTest`, `mesh_core_test` | Existing cross-language geometry parity; measure before proposing acceleration. |
| Benchmark harness, `LivingWorldBenchmark` | Extend existing example module, with raw samples summarized separately from capacity claims. |
| Pythagoras battlefield ecology | Owner supplies cover/concealment. This slice does not duplicate fire, cover or ecology calculations. |

DTE 1 alone does not carry a complete trusted roster or faction. Claude's integrated main
changes add DTR 1 with session, squad, tick, health/maxHealth and downed members retained;
`AdaptiveDirector.fromRoster` reuses `TacticalOrders.Roster.toUnits` and validates the Frame.
The host still supplies trusted player/objective observations, faction and weapon style.
PLAYER now carries health, with -1 meaning unknown. Native ApplyOrders rejects stale ticks
and treats repeats separately; a new world session receives a new identity. Transport must
still fence sessions and use authenticated authoritative inputs; this is not deployed transport.

## Deterministic policy and bounds

`AdaptiveDirector.Frame` is an immutable validated authoritative snapshot. Coordinates are
Unreal centimetres with the DTO 1 limit of 1e8; ids use the existing grammar; at most 256
unique units are accepted. Reject bad health, non-finite coordinates, duplicate ids, invalid
ticks and wrong sessions before planning. The caller controls clocks; the kernel has none.

Units are canonicalized by id. The existing baseline ranks distance/name. The adaptive layer:

- With no current squad sighting, holds position and does not learn hidden player elevation.
- Dead units receive no orders. Wounded units retreat; casualty pressure raises the threshold
  from 30% to at most 45%, without altering health, damage, speed or accuracy.
- A healthy unit nearest the objective defends when it is threatened, the player is elevated,
  or repeated elevated encounters have taught the faction a defensive posture.
- At most two flankers, reduced to one after two casualties. Long-range observations widen
  the flank radius from 900 to 1200 cm. No arbitrary difficulty multiplier is applied.
- For squads larger than three, at most one available reserve reinforces a threatened objective.
- Every order explains its cause. Out-of-bounds geometric targets safely become HOLD.

O(n log n) sorting and linear observation/planning passes are bounded by n <= 256; no search,
network request or unbounded iteration occurs inside a decision. Population benchmarks above
256 explicitly partition independent squads. They do not bypass the per-spec order bound.

Faction `Memory` carries bounded elevation samples and casualty pressure, an explicit session,
and the last canonical-frame digest. Repeating the same tick/frame is idempotent; changing its
contents or sending an older tick is refused. A new encounter requires an explicit host call,
which retains learned elevation and halves casualty pressure. There is one memory per
faction/encounter owner, not a shared concurrent mutable singleton.

DTM 1 encodes a <=512-byte checkpoint with version and SHA-256 corruption detection. It is
not an authenticity signature. File-reload tests and the demo prove continuation; the host
must commit bytes through its durable single-writer persistence mechanism before externally
publishing a decision. No production persistence service, HTTP ingestion endpoint, or
automatic merge into the Living World sidecar is installed in this slice.

## Unreal integration handoff

The trusted host assembles Frame from its roster plus validated authoritative events, calls
`AdaptiveDirector.decide(memory, frame)`, durably stores the returned memory, and emits
`TacticalOrders.write(decision.orders())`. Submit the text asynchronously to
`UDaedalusTactics.ApplyOrders`; proposed cadence is 2 Hz per squad. Keep session/tick fencing at the
adapter. Never await Java inside movement, firing, collision, animation or replication.
Missing/expired Java decisions use the existing native fallback (ADR-060's three-second hold).
Unit identity, faction assignment, objective location and line-of-sight come from the server,
not an untrusted player's request. Lost DTE events require a roster resnapshot.

The generated `three-npc.dto` is directly consumable DTO 1: guard defends, scout flanks and
wounded retreats. Target positions still require Unreal navigation validation; geometric
flank points do not establish traversable routes. Test this first in the existing tactics
scenario, then with real cover after the ecology adapter is agreed.

Ownership: Astra owns Java adaptive decisions; Claude owns native tactics/Unreal execution;
Pootscoot owns the separate keeper consumer; Pythagoras owns battlefield ecology. READY is
not IN-GAME-DEMO. Native owner ACK, an authorized post-break editor window and linked in-game
screenshot/video are required for the latter. No editor or Unreal asset changes by Astra.

## Performance placement

| Workload | Initial placement | Evidence / decision rule |
|---|---|---|
| Strategic NPC/faction decisions, world evolution | Java | Bounded deterministic steps, durable authority; benchmark decision and wire cost separately. |
| Procedural generation and graph routing | Java | Reuse existing algorithms/budgets; baseline fixed seed and topology before changing code. |
| World meshing / spatial preparation | Existing Java + portable C++ | Parity tests already exist; optional native extraction only after equal-input/end-to-end profiling. |
| Movement, hit detection, physics, animation, prediction/replication | Unreal C++ | Frame-sensitive work belongs in the authoritative game server/client execution loop. |
| Serialization and transport | Existing DTO 1 plus asynchronous adapter | Count wire encoding, allocations, queueing and network latency separately; zero frame-critical round trips. |

No native rewrite is justified merely by language choice. The new benchmark records p50/p95/p99,
per-thread allocated bytes (when supported), JVM/OS/CPU count, 2,000 warmups and 1,000 samples.
Allocations are cumulative per sample, not retained/peak heap. Fixed-heap shared-machine
measurements are descriptive, not CI pass/fail thresholds or multiplayer capacity estimates.
Network latency, persistence fsync, JNI/FFM integration overhead and Unreal frame cost remain
unmeasured; no native speedup claim is made. Java stays at 21, with no preview FFM dependency.

Run core verification, then the existing benchmark example:

```text
mvn -B -ntp -pl daedalus-core -am install
mvn -B -ntp -f examples/benchmark-harness/pom.xml package
java -Xms128m -Xmx128m -cp examples/benchmark-harness/target/classes;daedalus-core/target/classes com.daedalus.examples.benchmark.AdaptiveBenchmark docs/benchmarks/adaptive-initial
```

The classpath separator shown is Windows; use `:` on Unix. The example writes the baseline,
DTO demonstration, DTM checkpoint and restart proof. Its simple file writes are a developer
demo, not a crash-safe production store. Baseline inputs intentionally include one known
weapon style; automatic weapon/route-learning needs additional trusted telemetry and balance
playtests, rather than invented information from DTE 1.

## Initial evidence (2026-10-13)

Java 21.0.4, Windows 11, 24 logical CPUs, fixed 128 MiB heap; raw data and executable
handoff are in [`../benchmarks/adaptive-initial`](../benchmarks/adaptive-initial/).

| NPC population | Decision + DTO encoding p95 | Allocated bytes per sample |
|---:|---:|---:|
| 3 | 20.5 us | 13,448 |
| 32 | 71.7 us | 89,720 |
| 128 | 152.5 us | 349,128 |
| 256 | 206.7 us | 694,456 |
| 1,024 (four squads) | 1,091.1 us | 2,757,416 |

Other p95 baselines: 101x101 generation 1,756.5 us; BFS 325.4 us; meshing a 256-block
floor 109.0 us; 64-tick Living World catch-up 7.8 us; faction checkpoint round trip 10.0 us.
Frame construction/validation is outside the decision timing; input hashing is inside.
The benchmark reuses fixed observations and measures phases sequentially; JIT/GC effects
mean individual phase percentiles must not be added or interpreted as causal speedups.
The allocation rate warrants profiling string hashing and DTO formatting before native
integration. These results do not demonstrate a native-acceleration need at squad cadence.

Validation: 589 core tests pass with coverage/Checkstyle/SpotBugs; benchmark example tests
4/4 pass. Existing C++ tactics checks pass 27/27 and mesh fixture checks 55/55 under MSVC
C++17 /O2. This is not an ASan run. The generated three-NPC DTO is also accepted by the
actual C++ parser and round-trips unchanged apart from platform line endings through
`examples/benchmark-harness/native/tactics_wire_probe.cpp`. Compile it with the existing
Unreal Public header directory as an include path; it has no Unreal runtime dependencies.
The generated restart proof verifies identical DTO decisions after a faction file reload.
Actual movement/navigation/combat and cross-process network latency still require the
Unreal owner's authorized integration window.

## Unreal-focused allocation pass and native handoff (2026-10-13)

JFR `profile` recordings of the same fixed-heap benchmark sampled temporary Vec/Unit/list
strings beneath `AdaptiveDirector.frameHash`. One pre-sized builder now preserves the
original record text without those intermediate strings. A compatibility test compares
against the original record hash for 0/1/3/32/128/256 units, all weapon styles, fractional
and boundary coordinates, signed zero, and checkpoint retry. DTO 1 and DTM 1 are unchanged.

Raw same-harness measurements are in `../benchmarks/adaptive-profile-before/baseline.csv`
and `../benchmarks/adaptive-profile-after/baseline.csv`. Both used JFR profile recording;
the after run overlapped validation on this shared machine. They are allocation evidence,
not an isolated latency comparison or an Unreal FPS measurement.

| Population | Decision bytes before | Decision bytes after | Decision + wire bytes before | Decision + wire bytes after |
|---:|---:|---:|---:|---:|
| 3 | 9,793 | 8,570 | 13,448 | 12,224 |
| 32 | 54,944 | 36,672 | 89,720 | 71,480 |
| 128 | 204,324 | 130,032 | 355,304 | 281,320 |
| 256 | 403,880 | 255,888 | 706,800 | 558,808 |
| 1,024 | 1,590,528 | 1,027,144 | 2,806,792 | 2,243,408 |

At 256 units decision allocation drops 36.6%, combined allocation 20.9%. Combined p95
in these recordings increases from 259.6 to 310.1 us; no latency speedup is claimed.
The first target is reduced backend allocation pressure while keeping gameplay native.

Claude acknowledged the integration in hub messages 27629/27632/27656; Astra replied in
27673. Proposed budget: Java decisions and DTO writing off the game thread at 2 Hz per
squad, asynchronous delivery, C++ parse + apply below 0.2 ms per 256-order spec. The
native budget is a target, not a measured result. Claude owns native binding, compilation,
navigation validation and the first post-break tactics playtest; that window is unscheduled.
Initial live binding uses the squad spawn centre as objective and threatened=false.
The deterministic DTO fixture separately demonstrates defend/flank/retreat. No-contact
HOLD is intentional: retreat must not consume a hidden player's position.

Remaining acceptance: authenticated delivery and session fencing; measured native parse,
apply, queue age and Unreal game-thread/frame cost; screenshot/video of actual three-enemy
behavior. Native core tests and a wire roundtrip alone do not establish those results.
