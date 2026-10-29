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

---

## Owner direction addendum: living islands, farms and invasion defence (2026-10-14)

The owner's island direction now connects the shattered-planet story, floating
rivers/lakes/ponds, four-or-more-island Super Islands, the M.U.L.E. economy,
FarmVille-inspired homesteads and ecology-wide zombie defence. Plants vs. Zombies
and Clash of Critters are named inspirations for original Daedalus systems.

The source map and stages are:

| Layer | Existing source / continuation | Current stage in this delivery |
| --- | --- | --- |
| Shattered planet and connected homes | `STORY.md` sections 6.1, 7.1 and 7.2 | Owner story direction recorded |
| Free-air water and aquatic ecology | `realms/AetherflowReach.md`, `data/waterways/aetherflow-reach.json` | Authored Blender modules and local activities; native/persistent authority pending |
| M.U.L.E. and farming | `mechanics/ISLAND-FARMING.md`, `tools/economy/island_farm.py` | Local farm source over the retained Colony Ledger; live save/native bindings pending |
| Existing zombie waves | `tools/economy/vendor/mule/colony_ledger.py` `event` / `defend` | Aggregate prototype loss/defence/salvage; retained donor unchanged |
| Living ecological defence | `mechanics/LIVING-ISLAND-DEFENSE.md`, `data/defense/living-island-defense-plan.json` | Buildable design and backlog; tactical runtime pending |
| All-life levels, evolution and minigames | `mechanics/LIFE-PROGRESSION-AND-MINIGAMES.md`, `data/progression/life-progression-plan.json` | Owner direction and reusable activity/progression seams; universal runtime pending |
| Caves in every realm | `mechanics/REALM-CAVES-AND-DUNGEONS.md`, `data/caves/realm-caves.json`, `world/cave/RealmCaveBlueprints.java` in core | Shared blueprint source and themed catalog; host placement/travel/native integration pending |
| Shop, companion eggs and planned DAED | `production/DAEDALUS-NFT-SHOP.md`, `production/DAEDALUS-UTILITY-COIN.md` | Source/preview; bindings and deployment pending |

**Universal placement and purposeful ecology.** Placeable definitions should
support attack, aid, scouting, barriers, resource production and terrain roles.
Animals, trees, bees, carnivorous plants, crops, fungi, water plants and aquatic
life can contribute within their habitat and the island's theme. Reuse existing
species keys, item identities, art and friendly-target policy; proposed behavior
profiles do not automatically register species or grant combat capability.
Rendered abundance is not an inventory of player-owned combat units.

**One encounter outcome.** The shared phases are `warning`, `prepare`, `engage`,
`contain`, `recover` and `rewild`, with one authoritative encounter identity and durable receipts.
The retained donor immediately applies FOOD loss and `zombie_drop` on its
`zombie_wave` event. A future tactical encounter must replace that managed
resolution path, or it will charge losses and issue salvage twice. The farm's
memory-only action IDs are an existing source pattern, not durable server proof.

**Connected ownership.** Four or more physically connected islands make a Super
Island, preserving each deed and owner/build permissions. Defense lanes, bridges,
water approaches, cooperation and contributions use explicit accepted connections.
No numeric-neighbour shortcut grants shared stores or another owner's control.
Companion and egg NFT identities remain stable through gameplay state changes.

**Crew handoff.** Existing economy, ecology, friendly-combat, creature, native,
story and inventory owners extend their current lanes using the ordered backlog.
The newer shared `docs/mechanics/MECHANICS-REGISTRY.md` and existing production
workbook remain the tracking authorities; reconcile this direction into their
existing defence/creature/zombie rows. Do not allocate duplicate WZ or ADR numbers
from this older checkout. The dedicated plan records dependencies and pending
source/art/runtime stages so unfinished ideas remain available to other bots.

**All-life progression and modular games.** Animals, plants, trees, insects,
colonies, fish, fungi and microbes can level and evolve through suitable activity,
care, training, exploration, restoration and defence. Separate maturity, earned
level/mastery, evolved form and inherited genome/coat/song lineage. Keep one stable
individual or accepted colony identity, plus any existing NFT binding. Species,
population counts and client-rendered bodies remain distinct from those records.
Existing Portal hero XP, egg stages, local waterway journals, farm upgrades and
arcade games retain their own implementations and stages. Connect eligible results
through a versioned participant/result adapter and one durable progression receipt;
do not duplicate game rules or turn browser scores into authoritative XP. The new
specification records actual sources and the work still needed for universal levels.

**Caves across the realms.** Reuse `RetroRealmGenerator.generate(long)` for the
three-floor topology, stairs, encounters and reference content. The new immutable
`RealmCaveBlueprints` authoring layer adds themed, instance-scoped floor/port/content
references and keeps the complete DRR source snapshot. It does not replace the
generator, register a realm or carve another owner's terrain. Bind actual surface
entry and return, native geometry/nav, realm-specific combat, instance persistence
and accepted loot through their current owners. Preserve Portal's progression and
all other realms' visual/gameplay identity. Optional Ocean, proposed Lantern and
Phase 2 Space remain conditional; Orrery and Sol are locations in existing hosts.

**Resonance Ranch and Lifecraft.** The owner's next Island Realm layer combines
jukebox/CD-discovered beasts, original gel husbandry, farm production, cozy village
life and optional salvage/extraction. Additive `world.ranch.ResonanceRanch` source
keeps recording-derived base identity separate from learned training, finite local
goods, accepted cycles and bounded activity results. Existing JukeboxClient,
Genome and audio owners retain music/voice responsibility; new accepted-input
records are integration assertions, not authenticated service receipts.

`world.lifecraft.LifecraftDesigns` supplies portable modular body/habitat blueprint
rules for the requested 64-bit realm. It does not register a host, mutate inherited
genomes or implement the existing crew's exploration engine. Provisional Lantern
Reach remains that crew's lane pending approved identity and native adoption.
Current farm, ecology, inventory, world-clock, persistence and progression owners
must connect accepted transfers/results once and preserve separate land deeds.
See `mechanics/RESONANCE-RANCH-AND-LIFECRAFT.md` and its structured build plan.

The owner clarified that jukebox seeds are already random and wants a random
interaction to discover their associated monsters. `SeedResonance` supplies a
bounded beat/sigil echo challenge; the ranch encounter wrapper gates first
discovery on its stored completion plus accepted playback. The random encounter
does not change the existing seed-to-base-genome mapping. The separate 64-bit
Lifecraft target is now identified as the N64-era **Lantern Reach** design lane,
from its hub, portal worlds, collectible unlocks and playful movement. That
target name is routing metadata, while canonical realm allocation remains with
the established host owner.

## Shardstead crafting authority comparison — Team Codex, 14 October 2026

See [the owned crafting adoption handoff](production/SHARDSTEAD-CRAFTING-ADOPTION.md).
Coordinator main-tree snapshot `34dfe8340da967392930504d42a8185705449384`
was observed at 15 October 00:59:02 UTC (14 October Pacific). Direct bounded
source reads distinguish read-only DIC inventory catalogs from domain inventory
transactions. The inspected Shardstead ledger supports revision/replay and
prepare/persist/confirm for its existing operations, but has no Craft operation.
The inspected recipe sample uses exact item/count rows; overlapping tag matching
is a candidate comparison, not a confirmed defect or accepted implementation.

Remaining dependency: the current authoritative player-bag mutation owner,
source path/pin and accepted stack/tag/container/capacity model. Keep Unreal as
intent/display; do not create a parallel craft service, endpoint or persistence
format. No copied upstream code, immutable upstream revision, algorithm adoption,
build, installation or native acceptance is claimed. The dedicated handoff records
reference/defer decisions; this addition preserves existing ownership and sections.


<!-- coordinator-creature-farm-architecture-20261015:start -->
## Creature handling, farm custody and sheep-herder source boundary — coordinator, 15 October 2026

Direct user scope: a modular grapple creature-handling mode for targeting, tether/reel, safe release, capture eligibility and herding into suitable player-farm habitats; dangerous Sea/Pirate creatures require reinforced terrestrial or aquatic containment. Configurable species mass, temperament and learned trust may influence handling. Food/water/chemistry and craftable upgrades connect capture, care and the full FlowersForever farm integration. Existing player traversal and Hero input remain preserved.

Bounded actual source reads established useful pieces, not a complete capture authority: native DaedalusCritter has graze/walk/flee and ledge-safe movement; DaedalusHomestead's ADaedalusLivestock has local feed/trough/growth/production behavior. Neither inspected interface establishes durable individual creature identity, player-farm custody or capture/enclosure transactions. EcologyLedger abundance and ark cargo are aggregate population operations, not individual ownership. Recording-derived ResonanceRanch residents cannot accept arbitrary captured wildlife. The inspected Species/SpeciesCanon identifies ComputerPets-derived provenance and is excluded from this new work. A Tool_GrappleHook art entry alone does not establish a gameplay grapple API; the targeted search found no dedicated implementation. Retain existing traversal source/backlog and keep missing bindings explicit.

**Accepted isolated source claims, not shared native edits:**

- Creature-policy owner /root/checkpoint_review, ACK/START22:19:36UTC, staging root task/creature-handling-source; proposed repository destinations: engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusCreatureHandlingPolicy.h, data/gameplay/creature-handling-policy.json, docs/production/CREATURE-HANDLING-AND-FARM-BINDING.md. First decision code saved22:22:53UTC. The policy emits intents and validates correlated host receipts/revisions; capture/settlement cannot succeed from local intent alone.
- Character-source owner /root/miniature_village_source, ACK/START22:16:39UTC, staging root task/sheep-herders-source; source destinations tools/blender/sheep_herder_exemplar.py, data/sheep-herders-plan.json, docs/SHEEP-HERDERS-SOURCE.md plus additive story text and source receipt. Source saved22:24:07UTC; independent static review found a recipe-destination mismatch, corrected in owned metadata22:26:14UTC. No Blender output, roster, export, render, rig/animation acceptance or native character exists from this package yet.
- Existing Flowers owner codex-flowers-integration retains its entire consumer/backend contract. Hub32448 requests explicit ownership of the missing individual capture/farm transfer/capacity reservation/persistence seam. Request delivery is not acceptance. No new competing database, service, endpoint or replacement app is authorized by this source contract.

The proposed host boundary must carry stable player/creature/farm/profile identities, operation ID, expected revision, eligibility/custody evidence, capacity reservation and correlated authoritative result. Retry and stale/unknown results must hold safely without duplicate effects. Habitat suitability checks must use accepted species/environment/containment/care capabilities; reinforced cages and aquatic transport are not interchangeable. Craft recipes and inventory debits remain with their actual authority, never a read-only catalog or local UI.

The original herder source exemplar is unranked. A future explicit positive N uses herder-rarity-sha256-v1: versioned seed plus stable IDs, descending SHA256 score, stable-ID ascending ties, ceil(N/100) named quest candidates, exact realized top/N fraction disclosed. N remains unspecified; no 500-character commitment. Current sheep/prop source keys and the ordered PortalQuest progress interface are compatibility references, with runtime IDs/bindings null until adopted.

No shared Hero/input/Critter/Livestock/Flowers file was modified by these isolated source claims. No compile, tests, service, persistent access, native/editor or gameplay proof follows from them. Existing codex-play-guard is sole native operator; Ultra retains graphics-first Prismheart and its pixel-JRPG identity. The unrelated BlackJackPro restart-recovery action remains blocked pending its separate human approval.

### Actual-code metaverse comparison and next implementation — 22:32 UTC

The eight-area audit is saved in task/metaverse-capability-gap-audit-20261015.json,72858B,SHA91f8234ce91f6664b3b9ba70541b47d1d4eee7843cb71d0a01f176ed9e5e194c:45original app identities retained,34current source pins rechecked. Each area is PARTIAL overall, with individual existing/reusable/missing/unknown evidence; no live or full-parity acceptance.

| Area | Existing/reusable source | Confirmed missing or bounded unknown |
| --- | --- | --- |
| Identity/inventory | SessionController/GameSession subjects and owner lists; HeroService file progression | HTTP move lacks verified-subject-to-seat binding; common owned bag/creature mutation API unknown |
| Portable items | RetroItem/RetroCodec; WorldPackageController/Service manifests and GLB | Instance rights/dependencies, destination compatibility and atomic source-debit/destination-credit unknown |
| Permissions | STOMP authentication/send guards; World.may/ParcelGate | HTTP seat binding missing; inspected door actor fallback not authenticated; dependency rights graph unknown |
| Quest/progression | HeroService progress save, CampaignController, ordered PortalQuest source | Shared durable quest/reward/inventory settlement and reconnect reconstruction unknown |
| Creator tools | Existing block/stamp/parcel APIs, plugin registries and CapabilityRegistry | Complete adopted in-world authoring/permission/publish flow unknown; do not duplicate the current SPI |
| Social/discovery | PresenceController/Service bounded presence and world lists | Durable bookmarks, safe arrival/admission and full social workflow unknown |
| In-world apps |45identity matrix, full donor scopes retained, LBP/CSRBT adapters | Served/cooked pairing, lifecycle/reconnect and full original UI/native parity unverified |
| Asset publishing | WorldPackageService and exact producer/catalog export/receipt provenance | Confirmed receipt-intent inspection gap; immutable bundle/dependency-rights release adoption unknown |

First accepted same-owner gap fix: codex-csrbt-reuse /root/final_docs_review modifies ONLY tools/blender/production_catalog.py, production_queue.py, test_production_catalog.py and tools/csrbt_catalog/README.md in existing csrbt-production-catalog branch. Current code passes no supplied receipt snapshot to catalog inspection and checks export SHA without current/preserved owner/evidence/stage reconciliation. Existing get/asOf/full-field-hash APIs are reused; no new database, Java command, connector, automatic promotion or authority. Source implementation started after explicit GO; first-source ETA22:43UTC. Tests are authored but unrun, and runtime/publish remain unverified.

Higher-consequence capture/farm custody and per-seat HTTP authority need their existing shared owners' accepted contracts before shared edits. No parallel capture store or replacement farm app is being introduced. Primary-source comparison links and license limits are recorded in existing AUTOMATION-LESSONS.md, coordinator-metaverse-research-20261015 section: Second Life patterns, Resonite MIT bridge with session/beta/nondurable-snapshot limits, and Sandbox0.12 with unestablished SDK-copy permission. These are original implementation references, not imported code/assets.

Source milestone readback: creature-handling policy delivered22:29:59UTC, headerb9a6f555874629042367fc1e87aef0d96cab7e71e38fac55f74ac2e2d2acb254, config1b1c60ee..., contractc6880bfc..., all in the isolated source bundle, static reviewed/uncompiled/unbound. Sheep-herder independent source gate closed22:28:27UTC after both recipe mapping and background/factory-scene guard fixes; reviewdfe45b61d01bcc15ca5f8316f2198a696da290d3a9a374025a6d0330f006d0be. Actual generated characters/roster remain0, Nunspecified. Farm owner request32448 still awaits semantic acceptance.

### Consolidated source, authority and production checkpoint — 2026-10-15 22:58 UTC

Shared original realm-preserving adventures and purposeful collecting are the current design direction; the realm's genre/chemistry/survival and full implemented apps remain authoritative. Player-friendly engagement means explicit goals/progress, optional equivalent local onboarding, stable recovery and useful collections rather than filler or forced attendance. One concrete bridge is the same-package herder→Tide-Pen proposal, final dataSHA90df1c49d4298b764140aeb2bb48c96d5c4eae0c1d08adb6556a659902a834dc. It reuses actual ordered PortalQuest semantics and the frozen creature-intent/receipt contract, without another progress store. Account/character/realm/season scope, canonical facts/operations/receipts/revisions, freshness/correction, unknown/rejoin and host-atomic completion/award are requirements, not implemented durable behavior. Headerb9a6f555… and config1b1c60ee… are unchanged; host/Flowers/individual custody/registry/quest/item bindings remain null, all new policies/data disabled, uncompiled and untested. Exactly23 original Knights have separate private artifact visibility, context attraction, action reputation and owned-land IN-WORLD vault permissions; read-only wallet design is not an observer or authentication implementation. Parent reports independent static CLEAR22:56:56UTC for all four Knights pins; source remains proposed/uncompiled, not generated/runtime accepted. Paid chance/holdings weighting, MOST/pool-overflow/operator/winner/dev-AI-cost ideas remain qualitative LEGAL HOLD with every numeric/economic parameter unset and no implementation or action.

The full Dungeon AI donor app remains required, including its existing modules/API/UI/persistence and advanced behavior. Usage credits are separate from DAED, MULE/local Gold and gems. Parent-reported inspection found adapter branch c579 absent from both inspected checkouts; historical TeamCodex/Astra source and Claude native work are not proof of installed full wiring. Existing sole codex-play-guard owns any eventual native adoption. No source handoff, embed or small replacement establishes full app integration.

Current bounded audit artifact task/metaverse-capability-gap-audit-20261015.json has final SHA256cb1f006a8ebc573b8da502461522f8c3ccdfc49f33c751a28c2515302ba6231e. The existing catalog owner delivered local source commit750933675098aeaeac885f6a780f90be34109c3b in exactly four owned files: tools/blender/production_catalog.py, production_queue.py, test_production_catalog.py and tools/csrbt_catalog/README.md. Named lookup now passes supplied receipt intent and compares current/preserved export SHA, stage, owner and evidence; eight new focused tests were authored but UNRUN. Historical mocked checks do not validate this checkpoint. No Java/store/connector/promotion/authority was added.

Final read-only coin/MULE/minigame audit task/daed-coin-mule-minigame-reward-audit-20261015.json SHA256f6293946e149acd0365a558c1621d58c32657ca7b858ae9ed96daa524bd7a2b9 covers37 file pins (27source plus10native/cabinet). Genuine deployed DAED address/payment/award binding remains unbound; MULE, local game Gold and gems are distinct source semantics and cannot silently become DAED. The new own section in docs/production/DAEDALUS-UTILITY-COIN.md records the design/hold boundary.

Latest production facts below are **parent-reported readbacks**, not this documentation worker's native/browser/source acceptance: Winter4 namespace received six FIRST saves22:45, current protected217packages/143actors/184C++sources; world placement/BAR/gameplay remain held. Ultra's actual title work plus two builds exited0 and eight supplementary JPEGs exist, but no combat/controller runtime proof follows. Its primary-main47filecommit was denied; primary HEADc1ce262d74ad01e3e0ecd36fb8f3d52e57a1ef4c, exact denied command/reason still pending, no alternate commit route. Reedwheel's eight renders were delivered and parent confirms eight Library creates; no native quality pass is claimed. No new execution, financial action or publication is authorized by this update; existing BlackJack restart-recovery and publication denials remain in force.

### Living-land vision and acceptance milestones

**Owner vision:** Every Daedalus land is a distinctive living home worth exploring, improving and showing off. Its creatures, chemistry, resources, crafted structures and history create useful possibilities. Neighboring lands and cross-realm adventures give each parcel a meaningful place in the larger world.

High desirability/demand is a design goal only, not promised scarcity, resale value or investment return. Preserve modular implementations, realm identity and immutable versions. Acceptance milestones are: visual identity+biome; functional habitat+persistent residents; resource/craft/adventure loop; meaningful customization; neighboring-land collaboration; discoverable story/collectibles; saved progress+reliable realm transitions. Source or asset presence alone cannot complete them.
### Original land-mechanics comparison checklist — parent research, audit pending

Parent-researched references: [Terrariums v1](https://blog.axieinfinity.com/p/terrariums-v1-is-live) (parent reports Homeland sunset17June2026), [Terrariums v1.1](https://blog.axieinfinity.com/p/terrariums-v1-1-is-live) (current passive collection/plot accessories/evolved parts), [Terrariums Estates](https://support.axieinfinity.com/hc/en-us/articles/54666286201115-Terrariums-Estates) (adjacency), and [historical Homeland beta](https://blog.axieinfinity.com/p/homeland-beta-is-live) (active crafting). This batch did not independently open these links. Compare actual present/partial/missing evidence first; an independent audit is assigned, not complete. Reuse full farm, chemistry, creature, crafting and minigame contracts for original realm-appropriate adaptations, keeping cosmetic quality and active adventures primary. No copied assets/code, Axie feature-parity, NFT staking or financial-return claim.

| Existing milestone/backlog reference | Initial evidence-qualified status and next proof |
|---|---|
| Visual identity+biome; functional biome decorations | PARTIAL art/source evidence; native visual BAR/world acceptance remains held |
| Creature homes; persistent residents; evolved traits/accessories | PARTIAL local livestock/source proposals; individual ownership/care/save and destination chemistry bindings unresolved |
| Production→craft→equipment→adventure; upgrades | PARTIAL original farm/craft app/source interfaces; actual cross-module receipts and gameplay loop unverified |
| Meaningful customization; visible land history | PARTIAL authoring/capability/package source; adopted player workflow and persistent land-history contract UNKNOWN |
| Neighbor adjacency/settlement synergies and collaboration | UNKNOWN in this bounded check; audit actual ownership/permissions/settlement interfaces before any proposed wiring |
| Discoverable story and purposeful collectibles | PARTIAL six-step herder→Tide-Pen proposal/eight null-bound references, no installed quest or configured award |
| Saved progress and reliable realm transitions | PARTIAL existing progression/session source; coupled journal/custody/rejoin/atomic receipt acceptance missing |

Track concrete accepted gaps through the existing BACKLOG.md and existing realm production queues/owner sections after the audit, preserving completed content and versions; this checklist is not another subsystem or blanket missing-feature claim.
### Final qualified production cutoff — parent updates through22:57 UTC

Parent reports Opus semantic ACK32480 and R3 source/manifest delivery32489:19files, immutableR1/R2, layoutSHA95f7e173… and owner-reported commit591bfc761…. Exact-mesh UCX/anchor policy,8m clearance, rope spans and ledger rows are DESIGN/OWNER-REPORTED, not independently validated by this documentation worker or root; R3 has NO renders. Sky→Tide-Pen collaboration was acknowledged after R3, pending canonical/source-plan reading before writes. Native32486 reports PR147 remote head4c2cdfc6510e59366094abd2e2d077ad432384f8, saved intake unchanged217/143/184. New user-authorized placement/view32491 is SOURCE PREPARATION only, not native execution or a compute claim. Willow export32467 and Poot source32466 have no actual ACK/START in this cutoff.

Reedwheel's eight Library creates succeeded per parent receipt reedwheel-r2-parent-attachments-20261015.json; parent reports17R1/R2pins matched, three paired settings equal and all eight original image hashes recovered excluding metadata in memory. Windows metadata-attribute failure is recorded; no source image was altered. This is delivery/file comparison, not native BAR/gameplay acceptance. Parent's final Dungeon artifact is34227bytes SHA256392f5c5ce1aa932d438ad0bad9cbf0b56e3dff1ea6accdcc8425113c05144f21, superseding33318bytes/2bf432…; its scope remains audit/source, not full connected acceptance.

### Broader land references inside the existing plan — 2026-10-15 23:02 UTC

These are **parent-researched official/official-linked references**, not independently opened by this documentation worker. They extend the same living-land milestones and parent-maintained existing backlog JSON receipt; they create no competing feature backlog, adoption/parity claim, token or financial action. Preserve original Daedalus identity, full implemented apps, immutable versions and confirmed-gap-first code reuse.

| Parent reference | Bounded comparison and uncertainty |
|---|---|
| [Decentraland in-world overview](https://docs.decentraland.org/in-world/overview), [LAND manager](https://docs.decentraland.org/marketplace/land-manager) | Programmable LAND/Worlds and delegated editing patterns; inspect our existing publishing/permission interfaces before proposing wiring |
| [Pixels farm-land docs](https://docs.pixels.online/farm-land-nft) | Productive-farm reference; older numeric claims remain UNVERIFIED, no yield/revenue or current-feature inference |
| [Nifty Island creation](https://guide.niftyisland.com/island-token/token-utility/island-creation) | Creator islands, multiplayer and build-budget reference; no copied numeric budget or economic model |
| [Somnium parcels](https://somniumspace.com/en/documentation/parcels-worlds/parcels) | Persistent parcels/custom-world entry reference; no claim our complete saved entry/rejoin flow is accepted |
| [Voxels discovery](https://www.voxels.com/), [official scripting bundle](https://github.com/cryptovoxels/scripting-bundle) | Discovery and scripting-extension patterns; reference availability is not code/module license adoption or runtime acceptance |
| [Soulbound official-linked wiki](https://wiki.soulbound.game/NFT) | Parent's current read says legacy NFT land has NO FUNCTION; this supersedes the historical2024 apartment-utility reference, not proof of Daedalus functionality |
| Otherside | Current full land/resource economy was NOT verified; make neither missing-feature nor fully-shipped claims |

Six highest-value **code-audit candidates**, mapped into existing milestones rather than a new subsystem:

| Candidate | Initial evidence boundary and existing milestone |
|---|---|
| Persistent/versioned land publishing + rollback | PARTIAL manifests/package/source evidence; actual accepted publish/rollback unknown. Maps to meaningful customization, visible history and saved progress |
| ONE complete replayable land activity | PARTIAL ordered quest/activity sources and herder proposal; a complete replay/rejoin/receipt-backed player loop unverified. Maps to resource/craft/adventure and discoverable story |
| Social discovery + friend joins | PARTIAL bounded presence/world source; complete friend admission/safe-arrival/recovery UNKNOWN. Maps to neighboring-land collaboration and reliable transitions |
| Useful stations/resources | PARTIAL full farm/craft app and local station interfaces; cross-authority inventory/craft receipts unbound. Maps to functional habitat and production→craft→equipment→adventure |
| Collaboration + moderation | PARTIAL existing parcel/permission source; accepted delegated editing/moderation workflow UNKNOWN. Maps to meaningful customization and neighboring settlement cooperation |
| Shared inventory + quest continuity | PARTIAL progression saves/ordered quest source; durable atomic cross-realm inventory/quest/rejoin contracts remain missing or unverified. Maps to saved progress and reliable realm transitions |

Independent audit is assigned, not complete. Refine present/partial/missing/unknown only with exact current code and owner evidence; source discovery does not authorize a new shared writer or claim runtime completion. Reuse existing identity, full farm, chemistry, creature, crafting, minigame, quest and publishing contracts before any additive source claim. Cosmetic quality and active adventures remain primary. No staking, financial returns, asset copying or automatic inventory/currency transfer is proposed by this comparison. Stop this documentation batch here; parent owns the single existing backlog receipt and subsequent production assignments.

<a id="coordinator-buildout-20261015"></a>
### Finite build-out checkpoint: source, action and evidence — 2026-10-15 23:04 UTC

**ONE current build-out reference within this existing architecture section.** This table consolidates the standing living-land vision, seven acceptance milestones and all researched comparisons; it does not create another subsystem, feature backlog or replacement app. Parent maintains the ONE existing backlog JSON receipt and sends crew assignments from this exact anchor. Earlier tables retain their dated cutoffs; this checkpoint supersedes conflicting current-stage/next-action descriptions. Except this worker's pinned policy/data and file-guard evidence, current production statements below are parent-reported readbacks or retained source audits, not this worker's independent native/browser acceptance.

| Priority / owner and existing package | Current evidence / next bounded action | Completion gate still required |
|---|---|---|
| P1 unreal-team / Reedwheel cosmetic R3→R4 | R3 source/manifest delivered32489,19files, ownercommit591bfc761…. Parent reports independent all18manifest pins match, UCX naming/shared anchors pass. **A real binary-vertex pair at4.74547m disproves the claimed global8m wheel clearance**; this witness is not a computed global minimum. Preserve immutable R1/R2/R3 and request an owned R4 SOURCE correction. R3 has no renders. | Correct actual geometry/claim and independently inspect the new pinned source and clearance evidence before any rendering/native acceptance. Final [R3 review](C:/Users/730ri/Documents/Codex/2026-10-14/task/reedwheel-r3-independent-file-geometry-review-20261015.json),25850B,SHA494b58731a9a802478cbaf2a225bce35218593674ebc1eff9296419190c54a56; exact witness4.745474617m, owner notified32503. Do not call R3 accepted or clearance-passed. |
| P1 codex-play-guard / existing native intake PR147 | Parent reports remote source head4c2cdfc6510e59366094abd2e2d077ad432384f8 and217saved packages/143actors/184Cpp after six Winter4 namespace first saves22:45. New placement/view32491 is source preparation only. | Actual permitted native dispatch, retained world placement/save/readback and separate appearance/BAR/gameplay acceptance. No fresh compute/native claim follows from this table. |
| P1 Ultra / existing Prismheart graphics | Parent reports actual title work, two builds exit0 and eight supplementary JPEGs. Supported staging is a SOURCE proposal only. Primary main remainsc1ce262d74ad01e3e0ecd36fb8f3d52e57a1ef4c; intended47filecommit denied, exact command still unexposed/requested. | Resolve the denied action through its actual owner/approval evidence; no retry or other-writer bypass. Original pixel-JRPG genre/full features retained; combat/controller runtime acceptance UNRUN. |
| P2 existing TeamCodex/Astra source + Claude native collaboration / full Dungeon AI | Current owner ACK pending for existing bridge recovery. Parent found c579 adapter branch absent in both inspected checkouts. Final audit34227B SHA392f5c5ce1aa932d438ad0bad9cbf0b56e3dff1ea6accdcc8425113c05144f21 supersedes first artifact. | Accepted exact source owner/pin, recover/reuse the existing full app/bridge and bind actual identity/session/service/lifecycle evidence, then sole-operator native adoption. Full donor modules/API/UI/persistence/advanced capabilities remain required; usage credits stay separate from DAED/game currencies. |
| P2 codex-flowers-integration / full Flowers authority | Existing app/consumer/backend seams remain owned. Individual creature identity, farm capacity/capture/settlement/care transaction extension remains pending source-owner acceptance. | Actual owner-accepted authenticated identity, durable individual custody, reservation and atomic correlated result/recovery contract. No competing farm store or unowned shared edit. |
| P2 checkpoint_review / task/creature-handling-source | Portable policy/headerb9a6f555… and adventure data90df1c49… saved/static reviewed; config disabled, profiles empty, live host/registry/quest/item bindings NULL. Herder→Tide-Pen six-step bridge/eight useful references reuse ordered PortalQuest and original intent/receipt policy. | Separately authorized compile/validation and owner-bound snapshots, receipt verification, individual farm authority, safe native executor and actual recovery/save acceptance. Local onboarding and imported facts share scoped recognition; no automatic ownership/power/award. |
| P2 miniature_village_source / existing sheep-herders-source | ONE unranked exemplar source, proposed Maren/A Dry Path Home; no execution/generated roster, Nunspecified. | Real source→accepted generation/export/art review→existing intake/native/runtime gate under ownership and custody. No500 commitment or rarity-to-power rule. |
| P2 original Knights source owner / existing daed-knights package | Exactly23 proposed original authoring slots, null live identities; source pinsd21ac81c…/4e2735fe… and all four pins independently static CLEAR22:56:56. Review7345B SHAe02cb732a351b3e190930544293608028b0e55bf16a9cc563ed1a7be69dec6ad. | Preserve private default invisibility/artifact visibility+dialogue, context attraction, action reputation and in-world owned-land vault permissions as separate bindings. No compiled/generated/financial/runtime acceptance; wallet is read-only DESIGN ONLY; paid chance/holdings/MOST/overflow/share proposal remains LEGAL HOLD with parameters unset. |
| P2 codex-csrbt-reuse / existing production catalog | Local four-file source750933675098aeaeac885f6a780f90be34109c3b, receipt-intent owner/evidence/stage reconciliation; eight focused tests authored UNRUN. Final capability auditcb1f006a… retained. | Bounded actual validation/runtime evidence under future authorization; historical mocked tests do not transfer. No new store, connector, promotion or authority. |
| P3 root / same existing milestone and backlog receipt | Six code-audit candidates: versioned publishing/rollback; ONE complete replayable activity; social discovery/friend joins; useful stations/resources; collaboration/moderation; shared inventory/quest continuity. Final [land-mechanics checklist](C:/Users/730ri/Documents/Codex/2026-10-14/task/original-land-mechanics-reuse-checklist-20261015.json),27403B,SHAc586a06b09c827095dd0c21429c86d4746ae5f1eb3453ebb9dfe1df5c0efa4c6, rates seven areas PARTIAL at integrated level with exact present/missing/unknown evidence; no feature parity or blanket missing claim. | Exact current source/owner evidence first, select one concrete gap, reuse existing contracts and preserve versions; no second competing backlog or parity claim. |

**Comparison inputs, not adopted implementations.** Parent-researched primary references retained here: [Second Life checked key updates](https://wiki.secondlife.com/wiki/LlUpdateKeyValue); [ResoniteLink](https://github.com/Yellow-Dog-Man/ResoniteLink) (beta/session/snapshot and exact-file license limits retained); [Sandbox0.12](https://docs.sandbox.game/en/creator/game-maker/version-notes-and-changelogs/game-maker-0.12) (no SDK-copy permission established); [Axie Terrariums1.1](https://blog.axieinfinity.com/p/terrariums-v1-1-is-live) and [Estates adjacency](https://support.axieinfinity.com/hc/en-us/articles/54666286201115-Terrariums-Estates). These inform original persistent creature homes, evolved/accessory/cosmetic expression, functional biome decor, settlement synergies, upgrades, production→craft→equipment→adventure and visible history. Cosmetic quality and active adventures remain primary; no staking/returns/copy or Axie feature parity.

Other retained parent comparisons: [Decentraland LAND manager](https://docs.decentraland.org/marketplace/land-manager), [Pixels farm land](https://docs.pixels.online/farm-land-nft) (older numbers unverified), [Nifty Island creation](https://guide.niftyisland.com/island-token/token-utility/island-creation), [Somnium parcels](https://somniumspace.com/en/documentation/parcels-worlds/parcels), [Voxels](https://www.voxels.com/) and [official scripting](https://github.com/cryptovoxels/scripting-bundle). [Soulbound wiki](https://wiki.soulbound.game/NFT) parent-read legacy NFT land NO FUNCTION supersedes the historical2024 apartment-utility claim. Otherside's current full land/resource economy remains unverified; no missing/fully-shipped assertion. [World of Warcraft](https://worldofwarcraft.blizzard.com/) names the user's original adventure/collection inspiration only; no copied franchise material, API integration or verified code/license comparison follows. This worker did not independently browse these links.

Reedwheel's eight Library images already persisted per parent, separate from R3 and native quality. Coin auditf6293946… retains37pins; actual DAED contract/payment/award bindings remain unbound and MULE/local Gold/gems/AI usage credits separate. Preserve the BlackJack recovery denial and LBP publication HOLD. Shared roles, full existing apps, source/asset/current runtime stages and financial/legal boundaries remain explicit. Close this finite documentation checkpoint; root handles crew canonical-path broadcast and existing-package assignments.

### Scheduled all-team lessons review — 16 October 2026, 01:21 UTC

Coordinator pootscoot-coordination opened the scheduled session at01:21:54UTC in the existing D2-build/docs/production/TEAM-BLENDER-UNREAL-HARNESS.md, Whole workflow harness backlog. This is the current review checkpoint; earlier status paragraphs retain their historical cutoffs. Individual hub invitations32640–32656 are delivery evidence, not attendance or implementation. The existing coordination-member-audit-20261015.json records named current responses, independently read-back owner documentation and pending coverage; historical18/20 preparation is separate.

Ranked lessons now recorded there: preserve producer/validator/reconciliation states; fingerprint the actual receiver; separate immutable source acceptance from adoption/build/runtime and historical tests; constrain transport before dispatch and release input by retained ownership; separate generated output from pixel quality; state exact geometry/units/transform limits; bind comparison captures to actual app state and pinned assets; retain numeric prelaunch rejection evidence. Benefits and effort are ESTIMATED. Existing named owners retain their current scopes; this review assigns documentation consolidation, not fresh implementation or compute.

Current corrections: Willow's retained three-view exit0 is technically reconciled without rerender, with original failure/13pins preserved; visualFAIL/nativeHELD and no-PID resource-blocked reopen remain. Dungeon's corrected8files/71727bytes are receiving-accepted source-only32635, exact decision3190ea8a…/independent review7d64daa2…;191-source candidate/adoption/UHT/module/link/runtime remain pending. Ultra's four-source adapter/provenance is clear, zero accepted browser pairs, build/capture request32631 still held. R4's numerical static3m geometry is qualified; mixed-material receiving profile remains unaccepted. No historical test green transfers to changed code.

Latest saved native baseline218packages/145actors/184sources/mapf77f83a2… is a file receipt, not a fresh world query. Sole native owner codex-play-guard remains even if a lease expires. The human safe-editor-save/pause/close/191-build decision remains pending. Glorp is a separate user-authorized project with its own owner and future preview decision; no Daedalus scope, second editor, compute lease or Dungeon approval follows. Frozen packages/recipes/failed attempts/user data and other authors remain preserved.

Story/reproducibility discipline: link visible prototypes to their actual narrative purpose/player goal and explicit mechanic stage. Willow's pond remains an opaque preview; Residents is asset-only with no placement. Neither proves living ecosystems, fluid simulation or gameplay. No new lore, realm parity, public release or promised utility was invented by the review. Keep finished lands immutable and name any authorized future polished successor/version separately.
<!-- coordinator-creature-farm-architecture-20261015:end -->
## Team Codex review checkpoint — Willow, 15 October 2026 Pacific

Attributed source for the scheduled lessons review: [Willow lessons](AUTOMATION-LESSONS.md#team-codex--willow-lessons-review-15-october-2026-pacific)
and retained artifacts/biomes/shardstead/WillowWetland/pilot-r1/stage-plan-r1/PACKAGE-STATUS-r1.md.
Author/export succeeded; three images rendered and failed the visual bar. Root's
versioned Windows path reconciliation a7f60238 validates retained PNG evidence
without overwriting the original failed validator attempt. This closes that
technical reconciliation only. Source/byte/render evidence is not visual quality,
native import/save, gameplay or canonical species/inventory authority.

Reopen was blocked before any PID at retained memory floors; actual compute
release was verified. Missing numerical prelaunch memory evidence is an explicit
wrapper diagnostic gap, not permission to infer a value or retry. Named owner
remains Team Codex for the original kit and local wrapper; sole Unreal operator
codex-play-guard retains native custody even absent a lock. Proposed portable-path,
visual-gate and prelaunch-receipt improvements go to ROOT's existing Whole workflow
harness backlog; estimated benefits/effort are in the lessons section. No new
source, asset, allocation, dispatcher or framework is adopted by this checkpoint.
