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

## 13. The economy and life layer (2026-10-14, ADR-066) — islands → items → mechanics → story

Added on Richey's direction (13:25–14:18): every island must be *made of* something and *for* something, and the
loop between items, mechanics and the realm storyline must be tracked and iterated.

| Layer | What it is | Source of truth | Status |
|---|---|---|---|
| **Seeded chemistry** | `profile(seed, realm)`: geology grade (COMMON/RICH/LEGENDARY), ores + Heartstone, spring purity, fish, soil fertility + crops, orchard species with the fruit's uses, RingInfusion herb set, livestock yields, power source, power-unit parts, four goods FOOD/ENERGY/ORE/CRYSTAL with surplus and need. **Every realm has its own table** (`REALMS`). | `tools/blender/island_chemistry.py`; Chemistry sheet in `docs/production/Realm-production-2026-10-13.xlsx`; manifest next to every exported island | pure Python, in use by the generators |
| **Ecology** | seral stage per tile, biodiversity index, season (succession, grazing, burning, seeding by ark) | `engines/unreal/pcg-ecology/` (Pythagoras/Team Grok), `daedalus-core` Biogeography | rules + tests; UE hook pending |
| **Colony Ledger (M.U.L.E., advanced)** | plots = deeds; workers (pack mule / Codex PowerUnit) outfitted per good family by consuming parts; production = chemistry × ecology with the energy tax and adjacency bonus; market day double auction per item with shop/inn floors; sales fly as ark cargo; round events (meteor, blight, raiders → salvage hulk, wampus, festival); colony wealth score advances the realm story | `tools/economy/colony_ledger.py` (+10 tests), `docs/adr/ADR-066-colony-ledger.md` | core tested; server rounds/persistence/UI held |
| **Day book (Animal Crossing)** | daily finds — fish by season/hour, bugs by seral stage, fossils/starmetal shards, ripe fruit; museum collection with first-of-kind bonus; charm; news-board requests from the realm's cast (`data/art/<realm>/population-plan.json`: kings, unicorn guides, bakers…) that pay in what the island cannot make; quest-giver roles surface their quests (PORT09 quest core) | `colony_ledger.day_book/requests/fishing` | core tested; NPC binding pending |
| **Scavenge + defend (Arc Raiders)** | hulks and rich lands are loot sites; loot flies home as interceptable cargo; fences/lanterns/watchtowers/patrols/traps raise defence; caught raiders lose cargo | `colony_ledger.raid/defend` | core tested; native boarding/combat pending |
| **Water that floats in the sky** | lakes, streams, waterfalls, sky rivers arcing between islands and through clouds, floating ocean basins; fishing spots on all of them; **sky-sea boats** float on that water but cannot fly — the sky-river network is its own travel graph; water sockets in the Super Island standard open sea lanes when plots are tugged together | `hero_island.py`, `island_cluster._sky_river`, `voxel_super_island.py`, `colony_ledger.water_network` | Blender exported; Unreal water material + vessel physics pending (OCE01/OCE10) |
| **Islands as members of Super Islands** | 256 m pitch, 240 m envelope, sockets at ±120 m, 10 m deck, 16 m bridges (Ultra's Lumenwake standard); each member keeps seed, deed, chemistry | `voxel_super_island.py`, Ultra's `super_island_layout.py` | Blender exported; placement/tug authority ADR-065 |
| **Tracking** | Mechanics sheet rows WZ01–WZ17 + "Team Claude 2026-10-14" sheet; `docs/mechanics/MECHANICS-REGISTRY.md` says where every mechanic lives so teams build on each other instead of overlapping | the xlsx + the registry | live |

**The loop.** A realm's story names a need → a Mechanics row → a Chemistry row → the seed rolls it → the island
carries it with a reason → the day book, the market and the raids make it worth collecting → the story gains the
scene → repeat. Richer colony → richer story → more items.

## 14. How Team Claude builds an island, exactly (for whoever continues: Opus 5.5, Codex, anyone)

Richey 14:21: "be very specific how you make these islands so that Opus 5.5 on the team can continue to build those
and learn and iterate and get better." Everything below is on `main`; nothing needs the Blender GUI or Unreal.

### 14.1 The contract
- **Units.** 1 voxel = 1 m in the plan; the mesher writes 100 Blender units per voxel; the FBX arrives in Unreal at
  100× and is placed with actor scale **0.01**. Pivot = plateau top centre: the walk surface is z = 0 (Super
  Island members are lifted so the plateau sits on the 10 m deck datum).
- **Colours.** Every voxel carries a palette *key* (`"grass"`, `"rock2"`, `"heartstone"`, `"fruit_apple"`…), never an
  RGB. `hero_island.PAL` maps keys → linear RGB; kinds (`KINDS[kind]["pal"]`) and cluster themes override keys;
  inside a cluster each island's overridden keys become `key@kind` so one palette serves four kinds. The mesher
  writes `Col` byte colours **sRGB-encoded** (`c ** (1/2.2)`) because Unreal reads FBX vertex colours as sRGB.
- **Layers → meshes.** `H.LAYERS = island, water, trees, cottage, props, flowers, crystals, clouds`; `H.GROUPS`
  merges them into three meshes: `body` (everything solid), `water` (needs a translucent material), `clouds`.
- **Collision.** `V._ucx_boxes` makes one `UCX_<name>_body_NN` box (6 m deep) per walk-surface rectangle from
  `V.walk_rects(island_voxels)`. Bridges/landings add their plank rectangles. No hull.
- **Manifests.** `Island_H<seed>.chemistry.json` (`island_chemistry.manifest`) next to every FBX; Super Islands
  write `<name>.super-island.json` in Ultra's `daedalus.super-island.authoring/v1` schema.

### 14.2 The planner, step by step (`tools/blender/hero_island.py::plan(seed, realm, kind, size)`)
1. `rng = random.Random(seed * 7919 + 11)`; `salt` for the hash noise; `chem = island_chemistry.profile(seed, realm)`;
   `K = KINDS[kind]` (tree shape, lake kind, extra).
2. **Footprint**: `_disc(size, _harm(rng))` — radius = size × (1 + Σ a·sin(kθ+φ)) with three harmonics
   (a 0.04–0.10, k 2–5); `voxel_island.plan` adds a strong 2nd harmonic when `seed % 4 == 1` (two-lobed).
3. **Hill + lake**: hill centre `(hx, hy) = (-8, 6)`, radius 34, height `7·(1 − (d/34)²)`; lake = cells within 11.5 of
   the hill centre at `lake_z = hill − 2`; stream = a 2-wide meander (`sin(i/6)·0.9` across the heading) from the
   lake rim to the far rim; the rim cell where it leaves becomes the **waterfall** (5 wide, pours 46 m).
4. **Body** (`_body`): per top cell — sand if within 2 m of the edge, else grass/grass2 by `_patch` (4-voxel hash
   noise); 4 m of dirt under it; rock down to `depth = thick·(1 − frac^3.2)^0.7 + jag` (jag = −1..2 per 3×3
   column), `thick = int(size·0.63)`; `terrace=(7, 2)` drops the outer 7 m by 2.
5. **Water**: lake plane, stream bed, waterfall sheet; **ocean basin** = a second disc (size 30) 50 m below and
   22 m past the fall with a sea filling its interior and a thin overflow fall; **source islet** = a disc (size 14)
   34 m up and `size − 8` m behind the hill with a spring; **sky river** = a 3-wide ribbon from the spring to the
   lake: straight line in xy, `z = lerp + 14·sin(πt)` (rises then dives), lateral weave `1.2·sin(9t)`, foam every
   5th cell, droplets under it every 7th, a cloud at the apex it passes through.
6. **Buildings**: stone cottage 9×7×5 with red gable roof, chimney and smoke spheres, on the hill shoulder at
   `cang = sang + 0.75π`; path (2 wide, `"path"` keys replace the top) from the door to the dock with lantern posts
   every 6th step; dock planks + boat + sail; plank bridge with rails a third of the way down the stream;
   starter town (`tang = cang − 0.45`, 27 m out): well, news board, shop with striped awning, inn, smithy with
   anvil + forge glow + chimney, windmill with cloth sails, **power unit** (Codex recipe) beside the smithy.
7. **Farm + chemistry props**: crop rows (`"soil"` top + wheat/carrot), livestock pen with sheep and hens, herb
   ring (six beds, only `chem.flora.herbs` grow), brew trough + clean-water barrel, waterworks (filter hut + water
   wheel on the stream), orchard grove with fruit on the canopies (`chem.flora.orchard`), ark moored at the dock,
   fishing pier on the basin.
8. **ADR-050 geology**: Heartstone sphere at the keel (`−thick − 1`), ore veins by depth (coal −2..−22, copper
   −6..−28, iron −14..−38, gold −26..−46 with `gold_mult`), cave mouth + lit tunnel + geode, mine rails + cart,
   meteor crater + starmetal mass **only if `chem.geology.starmetal_crater`** (LEGENDARY).
9. **Trees**: `big_tree` = 2×2 trunk 6–9 m, canopy by `K["tree"]` — round (3 overlapping spheres r 3–4), pine
   (stacked diamonds), palm (8 fronds), mangrove (stilt roots), dead (bare forks + embers); 5 groves of 3–5, 4
   blossom trees, 3 on the islet; counts scale with `f2 = (size/60)²`.
10. **Dressing**: flowers (260·f2, five keys), fenced garden, mushrooms (14·f2), rocks (10·f2), the kind's extra
    (obsidian spires / cacti / lily pads / crystal spires / hot spring), crystals under all three rocks, 5 clouds.
11. Return `vox`. `build()` meshes it, writes the manifest, exports FBX; `export_hero.py` adds two Workbench views.

### 14.3 Clusters and Super Islands
- `island_cluster.plan(seed, theme)`: four `hero_island.plan(seed·10+i, realm, kind)` shifted by `ISLAND_LAYOUT`
  (`(0,0,0), (165,40,22), (60,170,−18), (−120,130,38)`), lakes found by `_lake_of`, sky rivers from each lake to
  the next lower lake (`18·sin(πt)` arc), rope bridges between rims 0–1, 0–3, 1–2 (sag `−4·sin(πt)`), then
  `_theme_props` (eggs/tulips, lantern strings, pumpkins/hay/scarecrows, jack-o-lanterns/candles/fog, lights/
  canes/gifts/star). Themes set `realm` (harvest → PARCELS, halloween → LABYRINTH).
- `voxel_super_island.plan(seed, kinds)`: Ultra's layout (256 m pitch, roots at (±128, ±128), sockets at ±120 m,
  deck 10 m) → `member_plan` (size 104, plateau lifted +10, a 12 m stone landing from the rim to each socket with
  posts/rails and lantern posts at the mouth) → `_bridge` for every connector (8 m walk, sills, rails, rope posts)
  → sky rivers between member lakes → manifest.

### 14.4 How to iterate (what to change, where, and how to check)
- **New prop with a reason**: add the palette key(s) to `PAL`, add the item to the realm's chemistry row (so the
  seed can roll it), place it in `plan()` near the thing it serves, add the registry line and the Mechanics row.
- **New kind**: a `KINDS` entry (palette overrides, `tree`, `lake`, `extra`) + the `extra` branch in `plan()`.
- **New theme**: a `THEMES` entry + a `_theme_props` branch.
- **Check without Blender**: `python -m unittest tools/blender/test_voxel_island.py`; raster preview = the 20-line
  isometric painter in the lessons (sort voxels by `x+y`, then `z`); `greedy_quads` count tells you the mesh cost.
- **Check with Blender (headless)**: `export_hero.py`, `export_heroes.py` (batches), `export_cluster.py`,
  `export_super.py`, `export_creatures.py` — always `-b --factory-startup --python-exit-code 1`, absolute out dir,
  one Blender process at a time on the shared PC; previews are Workbench VERTEX with the `Col` attribute active.
- **Check in Unreal (when it is our turn)**: `daedalus_claude_islands.import_island` (FbxImportUI: Nanite off,
  vertex colours REPLACE, no lightmap UVs, no auto collision) → `place` at the deed's `x_cm, y_cm, top_cm` from
  `docs/production/lands/<realm>.json`, scale 0.01 → `viewport_screenshot`.
- **Seeds**: same seed + realm + kind = same island forever. LEGENDARY seeds (crater): 39, 91, 124, 125, 131, 144, 158…
  (`[s for s in range(N) if CH.profile(s)["geology"]["grade"] == "LEGENDARY"]`).

### 14.5 Characters (`tools/blender/voxel_creatures.py`)
Body plans in 10 cm voxels → one mesh with a vertex group per bone → the shared 8-bone rig (root, body, head,
tail, leg.L/R, wing.L/R — Codex's Portal creature layout) → NLA clips Idle / Walk / Attack / Hurt → GLB with
animations + FBX + json. **171 species** (14:45): `_quadruped` (70 animals: farm, forest, cats, monkeys, snakes
with `legs=0`, extinct — mammoth, sabretooth, dodo, moa, dire wolf…), `_bird` (18; wings folded along the flank at
rest, rotated out by the Walk clip), `_bee` (9; hover + 6× wing beats in Idle), `_plant` (13 carnivorous; Attack
snaps the trap), `_fish` (8, the chemistry's `water.fish` + rainbow eel + basin ray; Walk = swim/tail wag),
`_biped` (24 **zombies** for the wave apocalypse: `rot` 0–2 = fresh/green/bones, hats, tools, crawler, giant,
elemental frost/ember/crystal/mud, ghoul, wraith), `_dino` (10: T-rex/raptor/allosaurus/carnotaurus bipeds,
triceratops/stegosaurus/ankylosaurus/brontosaurus quadrupeds, pterodactyl/quetzal fliers), `_sea` (19: shark →
starfish). Add a species = one dict entry (`ANIMALS/BIRDS/BEES/FISH/ZOMBIES`) or a branch (`_plant/_dino/_sea`).
Exports: `export_creatures.py OUT [family|species…] [--sheet] [--force]`; ~0.4 s per creature once each
creature's objects/actions are freed after export (left in the scene, Blender's exporters slow to 10 s each).
Where they live comes from the ecology (habitat by seral stage/water/biome), the chemistry (livestock, fish) and
the ledger events (zombie waves: 5 escalating waves vs defence, `ZOMBIE_WAVE`). 15:05: `_insect` (19: fliers hover
like bees, crawlers walk; worms/snails/centipedes on body+tail bones) and 16 burrowers in `ANIMALS` → **206**.

### 14.6 Dresser props (`tools/blender/voxel_flora.py`)
Static props named for ADR-054's library lookup so `Dress()` picks them up with no code change:
`Prop_Tree_<Species>_<Stage>` (21 species × Sapling/Young/Mature/Ancient, shapes round/column/pine/willow/palm/
umbrella/dead/bamboo/cactus, 50 cm voxels), `Prop_Plant_*` (33: ferns, grasses, reeds, lily pads, mosses, vines,
mushrooms incl. glowing, wildflowers, crops wheat/corn/carrot/cabbage/beet/pumpkin, the six herbs, 10 cm),
`Prop_Shrub_*` (12), `Prop_Cloud_*` (18 types and colours: cumulus, stratus, wisp, storm, thunder with a bolt,
sunset pink/orange, dawn violet, gold, blood red, fog bank, snow, ash, aurora ribbon, rainbow arc, rain; 1 m).
Bottom-centre pivot; `export_flora.py OUT [family…]` writes FBX + json and one contact sheet per family.

### 14.7 Farm kit (`tools/blender/voxel_farm.py`)
`Prop_Machine_*` (21: tractors in four liveries, plough, seeder, harrow, harvester, hay baler, sprayer, mower,
wagons, wheelbarrow, milk cart, horse cart, pumps, sprinkler, irrigation pipe, windpump, tank; 25 cm voxels;
**wheels are a separate `_Wheels` mesh** so Unreal can spin them), `Prop_Farm_*` buildings (16) and tools/fixtures
(27, 10 cm), `Prop_Crop_*` (35: trellises with fruit, root crops with the root below ground, greens, berry/melon
patches, grains/paddy/cane/cotton rows, orchard rows). `export_farm.py OUT [family…]`. In the ledger a machine
is an outfitted FOOD worker (`PART_COST["FOOD"]`), crops are the chemistry's `soil.crops`.

### 14.8 Eggs and hatching (`tools/blender/voxel_eggs.py`, 196 props)
`Prop_Egg_<Type>_<Intact|Cracked|Hatching|Shiny>` for 49 egg types (gemstone: ruby/sapphire/emerald/amethyst/
diamond/opal/…; metal: gold/silver/bronze/copper/platinum; material: silk/wool/stone/obsidian/ice/lava/cloud/…;
realm/holiday: easter, halloween, christmas, starmetal). Each `EGGS[type] = (pattern, colours, rarity, hatch_pool)`;
`RARITY` odds common 70 / rare 22 / legendary 7 / ultra 1, `SHINY_ODDS` for the Shiny re-skin. The shell is an
ellipsoid (`_shell`) painted by pattern (solid, speckle, stripe, swirl, facet, metallic), Cracked adds a zig-zag
crack, Hatching opens the top rim with eyes/nose/yolk showing; every stage sits in a twig nest (ground at z=0).
`hatch_pool` names a `voxel_creatures` family (quadruped/bird/bee/insect/plant/fish/dino/sea) — the game rolls the
species from that family using the realm's ecology, so one egg type hatches different things on different islands
(PORT06 egg stages, Adopt-Me-style minigame in the quality bar). `eggs.manifest.json` ships the whole table.
Export: `export_catalog.py eggs OUT`. Ledger: eggs are market goods found by scavenging/fishing/festival events.

### 14.9 House, grave and sports props (`tools/blender/voxel_props.py`, 150 props)
`Prop_House_*` (69: bed/bunk/sofa/tables/chairs/wardrobe/dresser/desk/bookshelf/fridge/stove/sink/counter/
dish rack/washer/bathtub/shower/toilet/towel rack/mirror/lamps/fireplace/television/rug/clock/plant pot/…),
`Prop_Grave_*` (29: tombstones round/cross/obelisk/angel/celtic/crooked/mossy, crypt, mausoleum door, open grave,
coffin, urn, wreath, lantern, dead tree, raven, bone pile, zombie hand — the zombie-wave spawn dressing),
`Prop_Sport_*` (52: baseball bat/ball/glove/bases/pitcher mound/backstop, basketball + hoop, football + goal posts,
dodgeballs (`json.throwable=true`), soccer, tennis, volleyball net, hockey, golf, bowling, frisbee, bleachers,
scoreboard, water cooler). `ball(...)` carries seams so a thrown ball reads at 10 cm voxels. Minigames
catch / dodgeball / baseball / basketball / football use the throwable set (row WZ25). Export: `export_catalog.py
props OUT [house|grave|sport]`.

### 14.10 Sims realm (`tools/blender/voxel_sims.py`, 66 assets) — the practical-apps realm's build-out
`Build_Sims_*` kit (26: floors wood/tile/carpet/lawn/concrete/driveway/pool, walls plain/window/door/corner/half/
exterior/garage, roofs flat/slope/ridge/gable-end/tile, stairs, porch, white fence, pool edge + ladder, chimney,
street mailbox; 1 m grid at 10 cm voxels), `Prop_Sims_*` practical machines (18) that map to real tools in
`docs/PRACTICAL-APPS.md` — the json `app` field names the app: Scanner_Printer→PhotosToPDFPC, Fax_Machine→
fax-trident, Photo_Workbench→image-optimizer, Study_Desk→synapse, Server_Rack→LoadBalancerPro; plus computer desk,
laptop, phones, router, shredder, filing cabinet, whiteboard, bulletin board, safe, 3D printer, camera tripod, game
console — and 21 appliances (washer/dryer/dishwasher/microwave/coffee/toaster/vacuum/iron board/treadmill/hot tub/
grill/patio set/lawnmower/sprinkler/bins/water cooler/AC/ceiling fan/aquarium/pet bed). `House_Sims_Starter` is a
furnished 10×8 m one-storey house (lounge, kitchen, bedroom, bathroom, office) assembled from `voxel_props.house`
furniture + the machines, on a lawn with driveway, fence, patio, grill and mailbox — exported as six part meshes
(floors/walls/roof/furniture/machines/yard) so Unreal can swap rooms. `starter_house()` is the recipe to copy for
more house types (`_place(dst, voxels, dx, dy, dz, rot)` stamps any catalogue item at a position/rotation).
A Sims-realm lot = one `Build_Sims_Floor_*` footprint on a PARCELS-realm plot; the machines are the practical
layer (use the scanner → run the real app), the appliances are the needs loop (hunger/hygiene/energy/fun) that
feeds the ledger's FOOD/ENERGY goods. Export: `export_catalog.py sims OUT [kit|machine|appliance|house]`.

### 14.11 Flying dragons (`tools/blender/voxel_dragons.py`, 504 rigged)
Species name `dragon_<element>_<form>_<nn>` → `Creature_Dragon<Element><Form><nn>.glb/.fbx/.json`. 12 elements
(fire ice storm earth forest shadow light crystal ocean lava poison gold → scale/belly/breath/membrane/horn colours)
× 6 forms (wyvern 2-leg big wings, classic 4-leg, serpent long body ribbon wings, drake stocky short wings, fairy
small butterfly wings with eye-spots, elder huge double horns) × 7 variants. The variant seeds horns (straight/ram/
crown/antler), tail tip (spade/fin/club/tuft), pattern (plain/stripes/spots/plates/gradient), size ±15 %, spines,
beard, frill — `spec(name)` is deterministic, `dragons.manifest.json` lists every dragon's spec. Wings are built
SPREAD (arm bar + finger bones + trailing membrane) because these fly; the shared 8-bone rig drives them via
`wing.L/R`. Clips (voxel_creatures, family "dragon"): Idle = hover (body lifted 0.25 h, slow beats), Walk = cruise,
Run = dive-speed (smooth keys, not stepped), Jump = launch, Attack = lunge, Action = breath (rear back, pour
forward, wings flare). `voxel_creatures.EXTRA` is the registry other catalogues use to ride the same rig/export;
`export_dragons.py OUT [element…]` writes everything plus `sheet-<element>.png` (42 per sheet).
Chemistry hook: an element's dragons roost on matching realms/kinds (fire~volcano, ice~frost, crystal~crystal,
ocean~mire, earth/forest~meadow/mesa, gold only on LEGENDARY-grade islands); in the ledger a dragon is a `raid`
event source and a mount once tamed (egg type `Prop_Egg_Dragon_*` hatches the fairy form).

### 14.12 Owls (`tools/blender/voxel_owls.py`, 504 rigged)
`owl_<species>_<plumage>_<nn>` → `Creature_Owl<Species><Plumage><nn>`. 14 species (barn heart-face, snowy, great
horned + eagle + long-eared + screech with ear tufts, barred, elf, long-legged burrowing, short-eared, spectacled,
great grey, tawny, pygmy) × 6 plumages (plain, speckled, barred, streaked, masked, dusted) × 6 variants (size ±15 %,
eye colour, wings folded/spread, tail, brow, spectacles). Upright oval body, wide head with a facial disc, forward
eyes, hooked beak, talons. Family "owl" clips: Idle = head swivel (±1.2 rad, the owl look), Walk/Run = flight,
Action = silent swoop (wings wide, dip, talons forward). Night side of the ecology: hunts burrowers/insects, roosts
in Ancient trees, scouts in Living Island Defense. `export_owls.py OUT [species…]`, `owls.manifest.json`.
Note: species names contain underscores — split names with `spec(name)`, never `name.split("_")[1]`.

### 14.13 High-end islands (`tools/blender/hd_island.py`) — the next-level path
Learned from Codex's polish/cast tools (bevelled primitives, named Principled materials, smooth-shaded spheres,
decimated LODs) and Ultra's Lumenwake craft (authored height function with smoothstep blends, superellipse
plateau, clipped water, strata shell), rebuilt original. Recipe, in order (`build(seed, kind, out, offset)`):
1. `author(seed)` — lake ellipse, 3 hills, 4 level terraces (landmark / town / farm / dock), a stream from the lake
   to a waterfall lip on the rim, a spring from the big hill, a path, a source islet 40 m up off the rim.
2. `make_height()` — base deck 10 m + Perlin, gaussian hills, littoral shelf, terraces blended flat, lake basin and
   stream channel carved to 4.4 m, rim crest. One function = terrain, water, paths and scatter all agree.
3. `ground()` — 2 m grid mesh inside the superellipse (R = 110 m), smooth-shaded, POINT colour attribute coloured
   by sunlight / shore sand / slope rock through a VertexColor→Principled material; crest ring hides the grid edge.
4. `strata()` — six jagged layers (depth scales with plateau radius) to a tip, slots: cliff / light band / ore vein
   (first ore from the chemistry), emissive Heartstone crystal cluster at the tip.
5. Water = terrain triangles clipped at 7.25 m (exact shores), translucent material; waterfall sheet + mist;
   sky river = bevelled bezier tube (2.2 m) + foam core + droplets + apex cloud, from the islet pond into the lake.
6. `tree_bases()` + `scatter()` — kind-shaped tree meshes (round/pine/palm/dead/mangrove/crystal) instanced (shared
   mesh data) avoiding water, paths, terraces and steep slopes; rocks, flower drifts, grass tufts likewise.
7. `buildings()` — landmark shrine with emissive beacon, town (4 houses with glowing windows, chimneys, well,
   forge, anvil, PowerUnit frame/rotor/crystal), farm (barn, silo, chemistry crops in rows, pen), dock (planks,
   posts, sky-sea boat with mast + sail, lantern), path lamps, stream bridge.
8. `collision()` — `UCX_<terrain>_NN` box per terrace + a safety floor under the lake bed, hidden in renders.
9. `lods()` — terrain LOD1 (35 %) / LOD2 (12 %) parked below; json lists them. Export GLB + FBX + json (chemistry,
   sockets ±(R+10), terraces, islet, triangles, material list). Measured: seed 7 meadow = 612 objects, ~91 k tris, 17 s.
Kinds: meadow, volcano, frost, mesa, mire, crystal (palette + tree shape per kind).

### 14.14 Octets — eight connected islands (`tools/blender/hd_cluster.py`, 10 themes)
Hub island + seven on a 295 m ring, so ring neighbours sit exactly one 256 m pitch apart (Ultra's standard; hub gap
75 m, ring gap 36 m); each islet points away from the hub. 14 sagging rope-plank bridges (hub↔each, ring neighbours) with
gate posts and lanterns at the sockets; seven ring sky-streams carry water lake-to-lake through the air around the
octet. Themes by seed 1–10: Spring, Summer, Harvest, Winter, Easter, Halloween, Christmas, Valentine, Midsummer,
NewYear — kinds per plot, accent colour and a signature prop per island (blossoms, sunflowers, pumpkins/jack-o'-
lanterns, snowmen, eggs, gifts + tree + star, hearts, aurora ribbon, fireworks). Output per octet in
`engines/unreal/art/claude-octets/`: 8 plot GLB/FBX/json (`Octet_<Theme>_<seed>_Plot<i>_<Kind>`), `_Bridges`, `_Canal`
(sky streams + theme props), `.layout.json` (centres, sockets, bridge and stream graph), hero + top renders.
Plot seeds = seed × 100 + i, so any plot rebuilds alone with `hd_island.py OUT <seed*100+i> <kind>`.
Run it as 8 fresh processes (`hd_cluster.py OUT SEED --plot I`, I = 0..7) then `--links --render` — one process
for all eight slowed from 17 s to 65 s per plot as the scene filled; per-plot processes hold ~16 s (≈3 min/octet).

### 14.15 HD island v2 + the 10,000-island run (`hd_island.py`, `hd_batch.py`)
**Built from the mechanics, not decorated.** `gameplay()` places every hook from its source and writes it to the
island json (`gameplay` rows with `local`/`world` positions and a `source`, plus `mechanics_sources`):
spawn overlook (data/spawn/spawn.json) · six NPC homes (data/npcs/npcs.json) · ark deck + latch range
(data/ark/travel.json) · well / spring (purity) / rain catch / lake + filter hut when `water.filter_needed`
(data/water/water.json + chemistry) · fishing pier with the fish list (chemistry `water.fish`) · herb ring coloured
by essence + brew trough (chemistry `flora.herbs`, data/herbs, RingInfusion.md) · orchard trees with their fruit and
uses (chemistry `flora.orchard`) · livestock pen (chemistry `fauna.livestock`, data/livestock) · crop rows (chemistry
`soil`, Ultra's island_farm.py) · ore nodes `Prop_OreNode_<Ore>_Small` (data/spawn/ore_nodes.json density ×
`geology.ore_mult`, `ores_here`) · caves (`geology.caves`) · starmetal crater only when LEGENDARY · Power Unit sited by
its `drive` (stream → water wheel) · shop crates (`economy.shop_stock`, data/trade) and inn (`economy.inn_menu`,
data/food) · Colony Ledger goods/surplus/need · watch post + carnivorous guard beds (Ultra LIVING-ISLAND-DEFENSE,
ledger `settle_wave`) · egg nests (voxel_eggs) · quest steps whose targets are on the island (data/quests).
Exported hooks are small posts named `MKR_<island>_<kind>_<id>`.
**Kind landmarks** (`kind_features`): volcano crater + lava flows + smoke + obsidian + hot spring; frost ice spires +
frozen lake + drifts + icicles; mesa banded buttes + cacti + vineyard; mire lily pads + boardwalk + cattails +
glowshrooms; crystal giant crystal clusters + floating shards; meadow windmill + hives + standing stones.
`rim_details`: hanging roots and drifting keel rocks on every island.
**Speed** (measured on the PC): v1/v2 with `bpy.ops` primitives took 17 s → 70 s per island (operators re-evaluate
the scene; cost grows with object count). Now: bmesh primitives (`_obj`, no operators), Catmull-Rom tubes, a
bmesh `join_parts` for tree templates, LODs resampled from the height function on 4 m / 8 m grids, and
`merge_static` joining single-material props into one mesh per material → **3.2–4 s per island**, ~550 objects
(mostly shared-mesh instances), 60–100 k tris, ~6 MB GLB+FBX.
**The run:** `hd_batch.py OUT 10000 10000 --workers 4 --worker I` × 4 processes → seeds 10000–19999, kind = seed % 6,
`OUT/<thousands>/HDIsland_<Kind>_<seed>.{glb,fbx,json,thumb.png}`, `index-worker<I>.jsonl` (seed, kind, tris, grade,
surplus, need, hooks, secs). Purges the scene after every island; resume-safe (skips existing json); memory guard
pauses a worker while available RAM/commit < 1.5 GB (shared PC). ~1 island/s with 4 workers.
