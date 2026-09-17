# Daedalus World — Phase 0 Architecture

**Status:** Audit complete. No production code restructured.
**Date:** 2026-09-16
**Branch:** `cursor/living-maze-hardening-and-capacitated-flow`
**Decision:** Additive evolution. The maze, graph, theory, well, desktop, explore, and plugin surfaces stay. A persistent programmable voxel layer is added beside them.

This document is the Phase 0 audit required before World Zero implementation. It is an engineering decision record, not a product manifesto.

---

## 0. Non-negotiable: keep the cool features

Daedalus World is original because it is **not** a Voxels clone and **not** a stripped maze engine with blocks glued on.

The existing product already has a distinctive stack:

- 23 generators and 10 solvers on a graph seam
- living mazes, traffic, breed, campaign, daily, tournament
- theory (min-cut, tours, fingerprint, complexity, heuristic lens, sanctuaries, hardest route)
- fog-of-war agents, ghosts, spectate, multiplayer STOMP ownership
- JAR-isolated plugins that can add algorithms, never silently replace them
- a vanilla web well at `/`, a JavaFX desktop, and a first-person explore host
- prod JWT posture pinned by tests, RFC 7807 errors, bounded stores, determinism goldens

**World Zero adds a persistent voxel world. It does not retire any of that.**

If a later slice would delete, hide, or break a listed KEEP item to make voxels easier, that slice is wrong. Adapt at a new boundary. Do not cannibalize the laboratory.

The originality hook is composition:

```
maze DNA          → generate / live / solve / analyze spaces
voxel persistence → place / remove / save / reload matter
plugin objects    → doors, later traps, portals, NPCs
automation        → discover → drive → observe → trace → account
```

A parcel that is *also* a generated, living, solvable maze — inspectable by the same theory endpoints and operable by an agent — is Daedalus. A parcel that is only a pile of cubes is not.

---

## 1. What Daedalus 2 is today

### 1.1 Stack

| Layer | Fact |
|---|---|
| Language | Java 21 |
| Build | Maven reactor, Spring Boot 4.1.0 parent |
| Version | `1.2.0-SNAPSHOT` |
| Core deps | `daedalus-core` is SLF4J-only. No Spring, Jackson, or JPA. |
| Server | Spring Boot REST + STOMP `/ws` + optional Redis leaderboard |
| Clients | Vanilla JS well at `/`; JavaFX desktop; LWJGL explore (ADR-017) |
| CI | Ubuntu `mvn -B install` + examples; Windows plugin-host job; JaCoCo ratchet both directions; Checkstyle; SpotBugs |

Reactor modules (parent `pom.xml`):

```
daedalus-plugin-api
daedalus-core
daedalus-plugin-runtime
daedalus-server
daedalus-desktop
daedalus-explore
```

Standalone examples (not reactor children): `biome-plugin`, `dungeon-layout`, `openxr-plugin`, `loadbalancer-topology`, `benchmark-harness`.

### 1.2 Spatial model (this is the important gap)

There is **no** voxel, chunk, parcel, or `BlockType` type in the tree.

| Type | Shape | Role |
|---|---|---|
| `MazeGrid` | `rows × cols` cells | 2D cell graph. Four walls per cell. Start/goal. |
| `Cell` | 4-bit open mask | Carved passages, not solid cubes. |
| `Point` | `(row, col)` | Node identity in the maze plane. |
| `TileType` | WALL / PASSAGE / START / GOAL / … | 2D paint projection via `toTileGrid()`. |
| `Graph` | dense `int` node ids | Allocation-free adjacency. Solvers and theory run here. |
| `MazeGraph` | live view | Grid as `Graph`. |
| `CsrGraph` | snapshot | Materialised topology. |
| `ExploreWorld` | extruded `MazeGrid` | Corridors from `toTileGrid()`. Y is height of walls, not a third maze axis (ADR-017). |

World Zero must introduce a **new** volumetric model. It must not rewrite `MazeGrid` into 3D. ADR-017 already rejected that: a true 3-axis maze would rewrite every generator and solver.

### 1.3 Persistence

Almost everything is process-local and bounded (ADR-005).

| Store | Mechanism | Survives restart? |
|---|---|---|
| Generated mazes | Caffeine (`MazeGenerationService`) | No |
| Sessions | Caffeine (`GameSessionService`) | No |
| Agent walks, ghosts, tours, tournaments, complexity fits | Caffeine | No |
| Living runs / traffic | ConcurrentHashMap + bounds | No |
| Daily maze | date → UUID map, maze still in Caffeine | No |
| Campaign | derived from seed | Yes (pure function) |
| Leaderboard | in-memory, or Redis when enabled | Only with Redis |
| STOMP | simple in-memory broker | No |

World Zero's "save, stop, restart, identical" requirement is **new**. Maze caches are not a persistence layer. Do not pretend they are. Do not put World Zero voxels into the maze Caffeine cache.

### 1.4 Plugin system

`MazePlugin` can:

1. Register generators / solvers (`PluginContext.generators()` / `solvers()`).
2. Publish / listen to POJO events (`MazeGeneratedEvent`, `MazeSolvedEvent`, `PlayerMovedEvent`, `MazeMutatedEvent`, `AgentSteppedEvent`, `TrafficPulseEvent`, `SessionCompletedEvent`, `PluginFailedEvent`).
3. Reach host beans via `PluginContext.bean(Class)`.

Lifecycle: `discover` → `init` → `registerAlgorithms` → `start` → `stop`. External JARs get their own `URLClassLoader`. Algorithm ids are claimed once; collision fails the plugin. `shutdownAll()` unregisters contributed algorithms and closes loaders. The server actually calls this (`PluginConfig` `destroyMethod`).

There is **no** capability / affordance / door / portal / inventory SPI. Plugins extend the *algorithm catalog* and *event bus*, not world objects.

### 1.5 Server surface

REST under `/api/v1`. Auth in prod is executable: `ProdAuthPostureTest` boots prod, drives every controller mapping, and compares the answer to the README table **and** its own `EXPECTED` map. A new world endpoint that is not listed in both places fails the build.

STOMP at `/ws`, client `SEND` refused, broadcast-only. Topics:

| Topic | Frames |
|---|---|
| `/topic/maze/{id}/state` | `GeneratedFrame` / `MutationFrame` / `TrafficFrame` |
| `/topic/maze/{id}/solver` | `SolvedFrame` |
| `/topic/session/{id}/player` | `MoveFrame` (owned sessions: owner + authenticated joiners, ADR-012) |
| `/topic/plugins/failures` | `PluginFailedFrame` |

The well is already a browser client: `index.html` plus enumerated scripts (`draw.js`, `api.js`, `live.js`, `campaign.js`, `solve.js`, …). It is a 2D maze laboratory, not a WebGL voxel renderer. That is KEEP, not a gap to "fix."

### 1.6 Hosts

| Host | Job |
|---|---|
| Well (`daedalus-server` static) | Public 2D laboratory. Generate, live, solve, race, campaign, spectate, hunt, theory. |
| Desktop (`daedalus-desktop`) | JavaFX host. Boots Spring, paints the same thin-wall projection, off-FX work (`DesktopWork`). |
| Explore (`daedalus-explore`) | First-person extrusion. Headless mesh/walk/fog/input in `mvn verify`. GLFW/OpenXR launch-only. |

### 1.7 Security and verification that World Zero must not weaken

- Dev/test/desktop: open `SecurityConfig`. Prod: `ProdSecurityConfig` + JWT.
- `ErrorContractTest`: every 4xx/5xx is `application/problem+json` with a `type`.
- `DeterminismGoldenTest`: seeded answers match digests from another JVM.
- `BoundedStoresTest`: every Caffeine cache declares size and (where idle) TTL.
- `GeneratorInvariantFuzzTest`: every registered generator, from the live registry.
- Plugin host shutdown on Windows CI.
- JaCoCo floor **and** ceiling per module.

---

## 2. Classification

Rule: **KEEP means the feature remains reachable and tested.** ADAPT means a new seam, not a rewrite of the old one.

### KEEP — unchanged through World Zero

| Area | Why it stays |
|---|---|
| `daedalus-core` generators (all 23) | Maze DNA. Later they can *stamp* parcels. They are not voxel fillers. |
| `daedalus-core` solvers (all 10) | Same. Pathfinding in carved space. |
| `Graph` / `MazeGraph` / `CsrGraph` | Future voxel occupancy can grow a `Graph` view. The seam stays. |
| `Braider` / `Sealer` / living ticks | Living mazes are a world verb we already have. |
| `WeightedMazeGrid`, traffic, hotspots | Cost fields. Later: crowded corridors in a parcel. |
| `theory/*` | Analysis of spaces. Fingerprint, flow, tours, complexity, lens, sanctuaries, hardest route. |
| Campaign, daily, breed, tournament | The well's game loop. |
| Fog agent, ghosts, spectate, hunt | Presence and replay. |
| Sessions + ADR-012 STOMP ownership | Multiplayer we already paid for. |
| Plugin API + runtime + examples | Isolation, collision refusal, shutdown, biome/OpenXR/LBP examples. |
| Well at `/` and all of its scripts | Browser entry that already exists. |
| JavaFX desktop | Dev/admin/power 2D client. |
| Explore + OpenXR plugin | First-person maze walk. ADR-017 stays in force. |
| JWT / prod posture / RFC 7807 / rate limits | Security is not a migration tax. |
| Determinism goldens, fuzz, bounded stores | Verification culture. |
| Circuit breaker on generate | Honesty when generation fails. |
| Checkstyle, SpotBugs, JaCoCo ratchet, CI | Build stays green. |
| Single-instance posture (ADR-005) | World Zero is one server. No Redis-for-voxels, no broker relay. |
| Load-balancer / dungeon-layout examples | Graph-engine identity, not maze-only identity. |

### ADAPT — later, at new boundaries

| Area | Adaptation | When |
|---|---|---|
| Plugin SPI | Add optional world-object / capability registration. Do **not** rename `MazePlugin` or break `META-INF/services`. | Phase 5 (door), not Phase 1 |
| `PluginContext` | Optional `world()` / capability handle. Existing `generators()` / `solvers()` stay. | Phase 5–6 |
| Plugin events | Add `BlockPlacedEvent`, `DoorOpenedEvent`, … beside maze events. | Phase 3–5 |
| STOMP | Add `/topic/world/{worldId}/…` beside maze topics. Do not overload `/state` frame shapes. | Phase 4 |
| REST | New `/api/v1/world/**` controllers. Update README table **and** `ProdAuthPostureTest.EXPECTED` in the same commit. | Phase 3 |
| Well | New entry / panel that talks to world APIs. The maze well stays the default `/`. | After Phase 4 |
| Explore | Later: render voxel chunks **or** host both extruded maze and voxel volume. Do not replace corridor extrusion in World Zero. | After World Zero demo |
| Desktop | Later: inspect world revision / door state. Keep maze generate/solve. | After Phase 3 |
| `Graph` | Optional `VoxelOccupancyGraph` so solvers can walk walkable voxels. Generators still emit `MazeGrid`. | After Phase 2, only if a test needs it |
| Persistence house rules | World store is durable (file first). Still bounded. Still has a clock/size seam if cached. | Phase 2 |

### DEPRECATE — documentation / identity only

| Item | Note |
|---|---|
| "Daedalus is not a maze game" as a *deletion* brief | False brief. Daedalus is a graph engine **and** a maze laboratory **and** (now) a world. |
| Treating explore as "the 3D world" | Explore is an extruded maze host. The world is a new volumetric model. |

Nothing in production modules is deprecated for deletion.

### REMOVE LATER

**Nothing.** No production feature is on a removal list. "Scrap little" meant scrap the *scope ceiling* (Daedalus as only a small maze well), not scrap the well.

Uncommitted explore paint work on this branch is unrelated viewing polish. Leave it alone during World Zero slices.

### UNKNOWN

| Question | Why it can wait |
|---|---|
| File format for world snapshots (custom binary vs JSON) | Phase 2 chooses the smallest that round-trips five block types. |
| Whether a maze stamp is a parcel plugin or a core operation | After World Zero door works. |
| Shared meshing between `ExploreMesh` and voxel greedy mesh | Client concern; server stays authoritative on blocks. |
| Player body in voxels vs explore capsule | Phase 3+; World Zero can use discrete block-cell position first. |
| How theory endpoints address a maze that lives *inside* a world | Keep addressing `mazeId` as today. World gets its own ids. |

---

## 3. Proposed Daedalus World architecture

Additive. One process. No microservices. No blockchain. No new Maven module until a boundary is forced.

```
                         EXISTING (KEEP)
                 well / desktop / explore / plugins
                              |
                     REST + STOMP /ws
                              |
                      daedalus-server
                     (maze services stay)
                              |
                      plugin-runtime
                              |
                        daedalus-core
              MazeGrid / Graph / theory / generators
                              |
                    NEW (beside, not instead)
                        com.daedalus.world
                    World / Chunk / Block / Parcel*
                    revision / place / remove
                              |
                    NEW server operations
                   /api/v1/world/**
                   /topic/world/{id}/events
                              |
                    NEW automation (v0)
                   registry / trace / account
```

\* Parcel ownership is designed, not implemented in World Zero. `ownerId` is a string. No wallet.

### 3.1 World primitives (Phase 1)

New package `com.daedalus.world` in `daedalus-core` (still framework-free):

| Type | Contract |
|---|---|
| `WorldId` | Opaque string id. World Zero uses a single well-known id, e.g. `world-zero`. |
| `BlockType` | `AIR`, `STONE`, `DIRT`, `WOOD`, `GLASS` (five). Extensible enum or registry later. |
| `BlockCoordinate` | `(x, y, z)` ints. Y-up, to match explore. |
| `ChunkCoordinate` | `floorDiv` of block coords by 16. |
| `Chunk` | `16×16×16` block payload + local revision. Sparse worlds omit empty chunks. |
| `World` | id, sparse chunk map, monotonic `WorldRevision`. |
| `WorldRevision` | Long. Increments on every mutating op. |

Chunk size is **16³**. Correctness first. No meshing in core.

Coordinate law (tests must pin):

```
chunkOf(block)  = (floorDiv(x,16), floorDiv(y,16), floorDiv(z,16))
localOf(block)  = (mod(x,16), mod(y,16), mod(z,16))   // positive mod
world.contains  = chunk present && local block != AIR  (or explicit get)
```

Negative coordinates must work. `Math.floorDiv` / `floorMod`, not `%`.

### 3.2 Maze DNA inside the world (designed now, implemented after World Zero)

Do not implement a giant stamper in Phase 1. Do lock the relationship:

1. A `MazeGrid` remains a 2D cell graph.
2. A later `MazeStamp` (name TBD) writes WALL tiles as `STONE` (or a `MAZE_WALL` type) into a world slab, PASSAGE as `AIR`, at a chosen origin and height.
3. Living ticks that mutate that maze can later rewrite the stamped slab. The maze cache and the world store stay two sources; a stamp is an explicit projection.
4. Solvers keep running on `MazeGrid` / `Graph`. They do not need voxels to remain correct.
5. Explore keeps walking extruded `MazeGrid`. A voxel camera is a later host, not a replacement.

That is how the well, the campaign, and first-person explore remain first-class after the world exists.

### 3.3 Programmable door (Phase 5)

The first world object. Not a block type with a comment.

```
Door
  id
  worldId
  block position (or two blocks: hinge + swing — start with one occupancy cell)
  state: CLOSED | OPEN
  capabilities: door.inspect, door.open, door.close
```

Human REST/STOMP and automation invoke the **same** domain method. Silence is not success: `LOCKED` / `ALREADY_OPEN` are observable results.

Do not build Switch/Portal/NPC plugins now.

### 3.4 Automation interface (Phase 6–7)

Principles only — no CSRBT/FlowersForever code.

```
DISCOVER → ADDRESS → DRIVE → OBSERVE → TRACE → ACCOUNT
UNACCOUNTED = 0
```

`AutomationSession` is the World Zero runner: address a cube, drive a capability through `WorldOps`, observe the cube/door (inspect does not bump revision), append a `DriveTrace` step. Discovery must not be the same list as the drive table. A newly registered capability that nobody drives must fail the harness.

World Zero registry minimum:

- `world.inspect`
- `chunk.inspect`
- `block.inspect`
- `block.place`
- `block.remove`
- `door.inspect`
- `door.open`
- `door.close`

### 3.5 Ownership (designed, not built)

```
Parcel
  parcelId
  ownerId          // string; account later, never a wallet type in core
  bounds
  permissions
  chunk refs
  features
  plugin refs
  createdAt / updatedAt / version
```

World Zero can be one implicit parcel: the whole tiny world, owner `system`. No NFT. No permissions engine.

---

## 4. Module boundaries

| Module | World Zero change |
|---|---|
| `daedalus-core` | **Add** `com.daedalus.world` + tests. Touch no generator/solver. |
| `daedalus-plugin-api` | Untouched until the door needs an event or capability type. |
| `daedalus-plugin-runtime` | Untouched until a plugin must register a door. |
| `daedalus-server` | New world controller/service **after** core primitives prove themselves. Maze controllers stay. |
| `daedalus-desktop` | Untouched in Phases 1–2. |
| `daedalus-explore` | Untouched in Phases 1–4. Corridor host stays the 3D maze view. |
| `examples/*` | Untouched. |
| Well static JS | Untouched until there is a world API to call. |

No seventh reactor module. A `daedalus-world` jar would split the embeddable core for no reason.

---

## 5. Technical debt that matters to the pivot

These are real, and they are **not** reasons to pause World Zero. They are tripwires.

1. **Maze state dies on restart.** World persistence cannot reuse that pattern. If we copy Caffeine-only storage, World Zero's acceptance test is unsatisfiable.
2. **Two spatial truths.** `MazeGrid` (cell walls) vs voxels (solid cubes). Forcing one representation destroys generators *or* makes a dishonest world. Keep both.
3. **Plugin SPI is algorithm-shaped.** Door capabilities need a new optional surface. Expanding `MazePlugin` with unused defaults is fine; breaking ServiceLoader is not.
4. **`ProdAuthPostureTest` + README table + `ErrorContractTest`.** New routes are a three-file contract. Miss one and CI fails. That is a feature.
5. **`BoundedStoresTest`.** A new `ConcurrentHashMap` of worlds without a cap will fail the house rule. Durable file store + bounded *live* cache.
6. **JaCoCo ratchet.** New core types need tests that move coverage *and* a floor bump if we exceed headroom. Do not add dead code to "balance" the ceiling.
7. **Explore is not a voxel engine.** Meshing, collision, and fog there assume `toTileGrid()`. Do not stretch `ExploreMesh` into World Zero.
8. **STOMP simple broker / single instance.** Fine for World Zero. Two browser tabs on one server is the multi-observer proof, not two JVMs.
9. **Operational leftover risk (the jobIndex lesson).** When maze-cache code is *not* used for worlds, prove the world path does not call `MazeGenerationService`. Discovery of the operational surface, not intent.

---

## 6. Serious architectural problems

None block starting Phase 1. These would block claiming "we already have a world":

| Problem | Severity | Response |
|---|---|---|
| No volumetric model | Expected | Add `com.daedalus.world`. |
| No durable world store | High for Phase 2 | File-backed snapshot. Not maze Caffeine. |
| Plugin capabilities missing | High for Phase 5 | New types; keep `MazePlugin`. |
| Explore ≠ voxels | Medium | Leave explore; add rendering later. |
| Well is 2D | Low | Keep it. Browser voxel client is post–World Zero. |
| Sessions forget players | Low for World Zero | One player position on the world object is enough at first. |
| No automation registry | Expected | Phases 6–7. |

There is no existing world code that must be deleted. There is no blockchain to remove. There is no second worker farm.

---

## 7. Migration sequence

| Phase | Name | Code changes? | Success |
|---|---|---|---|
| 0 | Audit | This document only | Classification + first slice named |
| 1 | World primitives | `daedalus-core` only | Coordinates, chunk membership, get/set, tests |
| 2 | Persistence | core + tiny store | Place, remove, save, process restart, identical bytes/state |
| 3 | Server operations | `daedalus-server` | inspect/place/remove REST; maze API unchanged; posture tests updated |
| 4 | Events | server STOMP | `BLOCK_PLACED` / `BLOCK_REMOVED` / `WORLD_REVISION_CHANGED` |
| 5 | Programmable door | core + server | Same domain op for human and automation |
| 6 | Registry v0 | small new types | Discover the listed capabilities independently of drive |
| 7 | Accounting v0 | harness | `UNACCOUNTED = 0` or fail the build |

After Phase 7, *then* maze-stamp, well panel, second observer, explore voxel view — in that order, still without deleting KEEP items.

---

## 8. World Zero acceptance criteria

A tiny boring world that is architecturally correct.

- [x] One authoritative server process (existing Spring Boot host)
- [x] One persistent world (`world-zero`)
- [x] Chunked storage, 16³
- [x] Five block types
- [x] Place block, remove block, inspect block/chunk/world
- [x] Save; stop; start; world identical
- [x] Revision increments on mutation
- [x] STOMP world events (Phase 4)
- [x] One door with open/close/inspect (Phase 5)
- [x] Automation discovers and drives those capabilities (Phase 6)
- [x] Accounting report; harness fails if `UNACCOUNTED > 0` (Phase 7)
- [x] **Every KEEP row still works:** well generate/live/solve, daily, campaign, theory routes, plugins, desktop, explore smoke, prod auth table, determinism goldens
  (evidenced 2026-09-16: generate/live/solve, daily, campaign, insight, plugin SPI, desktop paint, explore world, ProdAuth world rows, goldens, and unknown-`generatorId` 404 after the fallback rethrow)

Multiplayer "second client sees the block" is Phase 4+. Not a Phase 1 claim.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Feature cannibalization ("we had to drop the well") | KEEP table is a gate. PR description names what stayed. |
| MazeGrid rewritten to 3D | Forbidden. Stamp is a projection. |
| World hidden inside maze cache | Forbidden. Separate store. Prove maze service is not on the world write path. |
| Fake accounting (drive list == discover list) | Registry enumeration ≠ harness script. Add a capability in a test plugin and expect FAIL until driven or excluded. |
| Security regression | Same-commit README + `ProdAuthPostureTest` + problem JSON. |
| Coverage ratchet surprise | Tests first; bump floors when we earn them. |
| Scope explosion (NPCs, markets, WebGL) | Long-term list below is explicitly not now. |
| Uncommitted explore polish mixed into world commits | Do not stage those files on world slices. |

---

## 10. Long-term vision — do not implement yet

Compatible items below are now classified in
`docs/DAEDALUS_WORLD_ONE_ARCHITECTURE.md` (World One audit, 2026-09-17).
This Phase 0 file stays the World Zero record. Do not implement World One
from this list; implement only after that audit’s §8 slice is requested.

- Maze-stamped parcels and living slab updates
- Parcel permissions (still no blockchain)
- Inventories, shops, NPCs, portals, puzzles as plugins
- Browser WebGL client beside the well
- Explore voxel renderer beside corridor extrusion
- Agent builders that use the same capabilities as humans
- Large procedural terrain

The well remains the 2D laboratory. Explore remains the extruded-maze walk. The world is the persistent programmable volume. All three are Daedalus.

---

## 11. First implementation slice (after this audit)

**Do not start a restructure. Start one core package.**

### Slice 1 — `com.daedalus.world` primitives

Add only:

- `daedalus-core/src/main/java/com/daedalus/world/BlockType.java`
- `daedalus-core/src/main/java/com/daedalus/world/BlockCoordinate.java`
- `daedalus-core/src/main/java/com/daedalus/world/ChunkCoordinate.java`
- `daedalus-core/src/main/java/com/daedalus/world/Chunk.java`
- `daedalus-core/src/main/java/com/daedalus/world/WorldId.java`
- `daedalus-core/src/main/java/com/daedalus/world/WorldRevision.java`
- `daedalus-core/src/main/java/com/daedalus/world/World.java`
- `daedalus-core/src/test/java/com/daedalus/world/WorldCoordinatesTest.java`
- `daedalus-core/src/test/java/com/daedalus/world/WorldBlockStorageTest.java`

Prove:

1. `chunkOf` / `localOf` on positive, negative, and axis-crossing coordinates
2. A block written in a world is readable at the same coordinate
3. A block in another chunk does not leak
4. Default / missing chunk reads as `AIR`
5. `remove` returns that cell to `AIR`
6. Mutation bumps `WorldRevision`; inspect does not
7. Two worlds do not share chunk storage

Forbidden in this slice:

- Server endpoints
- Persistence
- Plugins
- Door
- Explore/desktop/well edits
- Generator/solver edits
- Blockchain, parcels UI, meshing, lighting

Tests first is appropriate here: the types are pure and the bugs (signed modulo, shared maps) are cheap to pin.

When Slice 1 is green, Phase 2 is a file-backed `WorldStore` with an explicit restart test — still without touching the maze cache.

---

## 12. Audit answers (Phase 0 close-out)

1. **What it is.** A Java 21 multi-module maze/graph engine with a Spring host, three clients, and a real plugin runtime. Spatial truth is a 2D cell graph plus an extruded first-person view. Persistence is almost entirely in-process cache.
2. **What survives unchanged.** Everything in the KEEP table: algorithms, theory, living mazes, well, desktop, explore, plugins, security, CI.
3. **What is adapted.** New world package; later optional plugin capabilities, new REST/STOMP, optional well panel, later voxel view in explore. Old seams keep their contracts.
4. **What is retired.** No production feature. Only the idea that Daedalus must stay a *small* maze-only product.
5. **Proposed architecture.** Authoritative Java server; `com.daedalus.world` beside `MazeGrid`; human and automation share domain ops; maze DNA stamps into the world later.
6. **Smallest path to World Zero.** Slice 1 primitives → file persistence → `/api/v1/world` → STOMP → one door → registry → `UNACCOUNTED = 0`.
7. **Serious problems.** No voxels; no durable store; plugin SPI is not capabilities; explore is not a voxel engine. All are expected. Dual spatial models are the design, not a defect.
8. **Exact first slice.** The file list in §11. Stop after those types and tests are proven. Do not restructure the reactor.
