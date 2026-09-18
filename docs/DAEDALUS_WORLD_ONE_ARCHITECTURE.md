# Daedalus World One — Architecture (post–World Zero)

**Status:** Audit. No World One production code in this document's scope.
**Date:** 2026-09-17
**Branch:** `cursor/living-maze-hardening-and-capacitated-flow`
**Depends on:** `docs/DAEDALUS_WORLD_ARCHITECTURE.md` (Phase 0–7, shipped)
**Decision:** Design the next ambitions at new seams. Do not implement them in this audit. Do not rewrite World Zero, the reactor, or KEEP clients.

This is an engineering decision record for everything Phase 0 listed as “after World Zero” or “do not implement yet.” World Zero stays the tiny correct volume. World One is composition: maze DNA inside that volume, plus observers and clients that do not retire the laboratory.

---

## 0. Why this document exists

World Zero acceptance (§8 of the Phase 0 record) is checked. The host already has:

- one process, one `world-zero`, 16³ chunks, five block types
- place / remove / inspect, file restart identity, revision on mutation
- STOMP `BLOCK_*` / `WORLD_REVISION_CHANGED`
- one door (`door-zero`) with inspect / open / close
- discover ≠ drive; harness fails if `UNACCOUNTED > 0`
- `MazePlugin.worldCapabilities()` default empty; runtime unions extras

Phase 0 §10 left the rest unscheduled. That list is now the subject, not the backlog dump. Viewing polish on the well is a different streak. Do not mix leftover-drag CSS into World One commits.

---

## 1. Non-negotiable KEEP

Same rule as Phase 0: **KEEP means reachable and tested.** A World One slice that hides `/`, deletes a generator, or replaces explore extrusion to “make voxels easier” is wrong.

| Surface | World One must not |
|---|---|
| 23 generators / 10 solvers | Become voxel fillers. They still emit / walk `MazeGrid` / `Graph`. |
| Living mazes, traffic, theory | Lose their maze ids. Stamp is a projection *from* them. |
| Well at `/` | Stop being the 2D laboratory. A world panel is beside it. |
| Desktop generate/solve | Become a voxel editor in the first World One slices. |
| Explore + OpenXR | Lose corridor extrusion. Voxel mesh is a second path. |
| Plugins | Break `META-INF/services` or rename `MazePlugin`. |
| JWT / prod table / RFC 7807 / bounded stores / goldens | Skip the three-file contract on new routes. |
| Single instance (ADR-005) | Grow a voxel Redis or a second JVM for “multiplayer.” |

No blockchain. No microservices. No seventh reactor module until a boundary is forced (it is not forced). No wallet type in `daedalus-core`.

---

## 2. Ambition classification

| Ambition | Class | Why |
|---|---|---|
| Maze-stamped parcel | **ADAPT — first World One code after this audit** | Phase 0 UNKNOWN is now decidable: stamp is a **core** projection, not a plugin. Plugins may later *trigger* a stamp. |
| Living slab updates | **ADAPT — immediately after stamp** | Living ticks already exist on mazes. The slab is a write-through of those ticks into voxels. |
| Second observer | **ADAPT — proof, not a broker** | STOMP world topics already exist. Missing is a second subscriber test + a well/desktop fold that listens. |
| Well world panel | **ADAPT — after second-observer proof** | New panel or hash route. `/` stays the maze well. |
| Explore voxel view | **ADAPT — last of the client trio** | Second mesh in the same window. Do not stretch `ExploreMesh` over chunks. |
| Parcel record + `ownerId` string | **ADAPT — with stamp** | Phase 0 designed `Parcel`. World Zero is one implicit parcel (`system`). Stamp needs bounds. |
| Parcel permissions | **SHIPPED — inspect + grant/deny/revoke/forgive + gate** | Allow/deny lists exist on the parcel. REST grant/deny/revoke/forgive extra-list actors. `block.place` asks ParcelGate. DAEW v10 persists extras. Last drive persists as DAEW v11. Last drive actor persists as DAEW v12. Last drive at persists as DAEW v13. No wallet. |
| Desktop world inspect | **DEFER** | After REST/STOMP proof. Maze generate/solve stay. |
| Plugin objects (trap, portal, NPC) | **DEFER** | SPI already advertises ids. New ops + drive rows come one object at a time. Door is the template. |
| Agent builders | **SHIPPED** | `WorldBuilder` recipes call `WorldOps`. A step may pass `actorId` (stamp driver or grant/deny verb). Well `#worldBox` maps the same ids onto existing REST and reads `/trace`. |
| Browser WebGL voxel client | **NOT NOW** | Well panel is 2D/REST first. WebGL is a fourth client. |
| Inventories, shops | **NOT NOW** | Plugin-shaped later. No economy types in core. |
| Large procedural terrain | **NOT NOW** | World Zero scale stays tiny until stamp + observers are honest. |
| Plots bought or rented | **SHIPPED — lease + release strings on parcels** | A plot **is** a `Parcel`. `leaseId` is an account key string beside `ownerId`. `parcel.release` clears it. Buy/rent is a later market provider — not a second spatial type, not a chain, no wallet types in core. |
| Wearables | **NOT NOW — item provider** | Equipped looks bind to an avatar later. No clothing types in `daedalus-core` this streak. |
| NFT art display | **NOT NOW — display provider** | A framed surface on a parcel wall binds an item id (string). The world *shows*; a later provider proves ownership. No wallet type, no ledger, no mint in core. |
| City-scale look | **NOT NOW — later renderer** | Street-scale materials and skyline after W1.5. Distant voxels stay the **real stamp** (or culled). Never a six-cube placeholder LOD. |
| Street / place names | **SHIPPED — labels on parcels** | Inspired toponyms as `placeName` strings. Not GIS imports, not official street registries, not trademarked venues as if affiliated. |

`DEPRECATE` / `REMOVE`: still nothing in production.

---

## 3. What World Zero already is (do not rebuild)

```
MazeGrid / Graph / living / theory     KEEP
        \                         /
         \                       /
          REST + STOMP /ws  (maze topics stay)
                    |
              WorldService
                    |
         World + WorldStore (DAEW file)
                    |
         door-zero + CapabilityRegistry
                    |
         AutomationSession (discover / drive / observe / trace)
```

Facts this audit will not reopen:

- Voxels are not `MazeGrid`. Dual spatial models stay.
- World persistence is not the maze Caffeine cache.
- Inspect does not bump revision; place / remove / door open-close do (door results stay named, not silent).
- Extra `worldCapabilities()` ids are UNACCOUNTED until driven.
- Unknown `generatorId` still 404s; world writes must not call `MazeGenerationService` unless a stamp slice *explicitly* does, and then only to obtain a `MazeGrid`.

---

## 4. Proposed World One seams

Additive. Same process.

```
                    KEEP clients
           well /  desktop /  explore /  agents
              |        |          |         |
              +--------+----------+---------+
                         /ws + REST
                            |
                     WorldService
                            |
              +-------------+-------------+
              |             |             |
           World        ParcelHost     StampOps
           (voxels)     (bounds,       (MazeGrid →
            door)        ownerId)       slab writes)
              |             |             |
              +------+------+------+------+
                     |             |
              WorldStore      LivingSlab
              (DAEW)          (tick → voxels)
```

### 4.1 Stamp is a core operation

**Decision:** `StampOps` lives in `com.daedalus.world` (or `com.daedalus.world.stamp`). It is not a `MazePlugin`.

Reason: generators already have a stable contract (`MazeGrid`). A plugin stamp would force every algorithm JAR to know voxels. Core already owns both types.

```
StampRequest
  worldId
  origin          // BlockCoordinate of slab corner (inclusive)
  maze            // MazeGrid from a generator (already built)
  floorY          // one layer of walkable floor
  wallHeight      // posts above floor; World One starts at 1

StampResult
  parcelId
  bounds          // AABB in block coordinates
  mazeId          // existing maze identity if the grid was hosted; optional
  revision        // world revision after writes
```

Projection rules (pin in tests, do not invent lighting):

| Maze fact | Voxel write |
|---|---|
| Carved passage | `STONE` (or existing floor type) at `floorY` |
| Wall / uncarved | `STONE` from `floorY` through `floorY + wallHeight` |
| Start | Same as passage; door occupancy may sit on this cell later — not in first stamp |
| Goal | Same as passage; no vault block type until a later palette slice |
| Out of maze rectangle | Untouched (AIR stays AIR) |

Forbidden in first stamp:

- Rewriting generators to emit chunks
- Deleting the source `MazeGrid`
- Living ticks
- Permissions
- Explore mesh
- Well UI

### 4.2 Parcel

World Zero’s implicit parcel becomes an explicit record when the first stamp lands:

```
Parcel
  parcelId
  worldId
  ownerId          // string; "system" until accounts; never a wallet type
  bounds           // block AABB
  mazeRef          // optional mazeId
  version
  createdAt / updatedAt
```

One world may hold many parcels later. World One first slice: **one** stamped parcel inside `world-zero`. Overlap is a named error (`PARCEL_OVERLAP`), not a silent merge.

Permissions stay off this slice. When they arrive: allow/deny on `(ownerId, verb)` — `block.place`, `door.open`, `stamp.apply`. No tokens, no chain.

Buy and rent are **lease verbs on this record**, not new cubes. `ownerId` stays a string account key; a later market provider may set `ownerId` or a `tenantId` string. Do not add `Wei`, `Wallet`, or listing books to `daedalus-core`.

### 4.3 Living slab

After a stamp exists:

- Living / braid / sealer keep running on the **maze**.
- `LivingSlab` is a subscriber: maze mutation → re-project dirty cells into the parcel AABB.
- Inspect-only maze reads do not write voxels.
- World revision bumps only when a projected cube *changes*.

Do not run living ticks on raw voxels. That would fork the living engine.

### 4.4 Second observer

Server work is already done (`/topic/world/{id}/events`). World One proves it:

1. **Test:** two STOMP sessions; place on A; B receives `BLOCK_PLACED` + matching revision. Same JVM.
2. **Well (later):** a fold or panel that only *listens* (no generate controls required).
3. **Desktop (later):** revision + last event line. Not a voxel viewport.

Do not add Redis pub/sub or a broker relay for this proof.

### 4.5 Metaverse providers (not this streak)

The product is a maze-native world that can later wear, hang, and lease. **Settlement is Ethereum** — a later provider module, never `daedalus-core`. Core keeps `ownerId` / `itemId` / lease as strings. The provider maps those strings to an Ethereum address, ERC-721 / ERC-1155 token, or listing. World Zero and World One do not import web3, do not hold keys, and do not mint.

| Later surface | Hosts on | Ethereum later | Forbidden in core |
|---|---|---|---|
| Plot buy / rent | `Parcel` + `ownerId` / lease strings | ERC-721 (or equivalent) deed / lease | `Wei`, `Wallet`, listing books |
| Wearables | Avatar / inventory item ids | ERC-1155 (or equivalent) | Clothing enums, SKUs |
| NFT art display | Framed wall bind (`itemId` string) | Existing ERC-721 shown, not reminted | Ledger, wallet verify, mint |

OpenXR stays the VR plugin. A later world view may show the same voxels; it does not become a chain client.

### 4.5 Well world panel

New UI beside the maze well, not instead:

- Suggested: `#world` fold or `/#world` hash. Default `/` paint stays maze.
- Talks only to `/api/v1/world/**` and world STOMP topics.
- First panel: revision, one chunk slice (text or existing ASCII well style), door state, last events.
- Stamp controls are **controls** — viewing autopilot does not own them. Architecture still names them: seed + generatorId → server stamps; the panel displays the slab.

Prod: same README + `ProdAuthPostureTest` + problem JSON if any new route appears. Prefer **no** new routes if existing inspect/events suffice.

### 4.6 Explore voxel view

Last of the client trio.

- Keep `ExploreMesh` / fog / story marks for extruded mazes.
- Add a **second** mesher that greedy-meshes occupied cubes in a parcel (or a camera AABB).
- Host may show maze corridor **or** voxel parcel; toggling must not unload the other world’s KEEP path.
- Collision for voxels is discrete occupancy (`World.contains`), not maze wall bits.
- OpenXR stays a plugin on the maze host until a later audit says otherwise.

### 4.7 City look (later — better than stub voxels)

The product bar is a maze-native city people want to walk, not a distant 6-cube prop.

- A far parcel is still its stamped cubes, or it is not drawn. **No stub LOD** that swaps a building for a handful of blocks.
- Street-scale look (facades, sidewalks, skyline) is a later mesher/material pass after the explore voxel view exists.
- Maze DNA is the city plan: stamps and living slabs stay the source. Do not replace generators with a city-builder.
- Place names are optional strings on a parcel later (`placeName`). Inspired street flavor is welcome. Do not import OpenStreetMap / Google as official streets. Do not sell a trademarked venue as if the product is affiliated.

Shared meshing with `ExploreMesh` stays UNKNOWN. Server remains authoritative on blocks.

### 4.8 Plugin objects and agents

Door is the template: named results, same domain method for human REST and `WorldOps`, capability id on the registry, drive row or UNACCOUNTED.

Trap, portal, and NPC are shipped (`trap-zero`, `portal-zero`, `npc-zero`, door template). Each added:

- core state + results
- `worldCapabilities()` ids
- REST/STOMP beside existing world routes
- one drive row

Agent builders call `WorldOps`. They do not get a parallel verb set.

### 4.9 Terrain / WebGL / shops

Out of World One. Compatible, not designed here beyond “not now.”

---

## 5. Module boundaries (World One)

| Module | First stamp slice | Later |
|---|---|---|
| `daedalus-core` | `StampOps`, `Parcel`, tests | `LivingSlab` |
| `daedalus-plugin-api` | Untouched | New default methods only when trap exists |
| `daedalus-plugin-runtime` | Untouched | Union stays as today |
| `daedalus-server` | Optional: stamp REST **after** core tests; posture triple | Observer proof test; well static only when panel ships |
| `daedalus-desktop` | Untouched | Revision line |
| `daedalus-explore` | Untouched | Second mesher last |

Well JS is untouched until the observer proof or panel slice, whichever the sequence reaches.

---

## 6. Sequence (locked)

Phase 0 already ordered the post-7 work. This audit keeps it:

| Step | Name | Success | Code? |
|---|---|---|---|
| W1.0 | This document | Classification + first slice named | Docs only |
| W1.1 | Stamp + one parcel | `MazeGrid` → slab; overlap fails; world restart still identical | core (+ store fields if parcel must persist) |
| W1.2 | Living slab | Maze tick changes only dirty cubes; inspect-only is quiet | core |
| W1.3 | Second observer | Two STOMP clients; B sees A's place | **shipped** — `WorldSecondObserverTest` |
| W1.4 | Well panel | Listen + inspect; `/` maze well unchanged | **shipped** — `#world` rail + `world.js` |
| W1.5 | Explore voxel view | Second mesh; corridor path still smokes | **shipped** — `WorldMesh` (B toggles voxels) |

Permissions and desktop inspect shipped after W1.5. Trap, portal, NPC,
`WorldBuilder`, the well agent fold, plot lease strings,
`parcel.lease`, REST `/parcels/lease`, `stamp.apply`, desktop lease
inspect, lab-maze stamp (`mazeId` on `/stamp`), living-slab
subscribe, parcel `mazeRef` persist (DAEW v9), and mazeRef /
lease inspect on well, desktop, and explore, explore remesh
on living-slab revision, well stamp.apply mazeId, and WorldOps
stamp.apply with a MazeGrid and mazeRef, explore load of
the persisted DAEW file, explore remesh on DAEW mtime,
well Generate → stamp.apply, desktop Generate → stamp.apply,
explore B voxel toggle, next-plot stamp (+X street), and plot-street
inspect (newest maze + N plots), vacant-plot lease, and
inspired place names on stamp.apply, and
Generate → parcel.lease after a successful stamp, and
explore caption of the newest street name, and
a street directory of every plot name, and
newest-lot x,z on inspect, and
explore caption of that lot, and
a street of every lot origin, and
a living bind per mazeRef on the street, and
a street of every mazeRef, and
world.inspect street directory, and
well paint from that inspect, and
block.inspect / observe lot under a cube, and
explore lot under the boots, and
desktop last-event lot, and
STOMP / well last-event lot, and
chunk.inspect street of overlapping plots, and
occupancy inspect lot, and
desktop occupancy lot, and
explore occupancy under the boots, and
observe occupant on the aimed cube, and
chunk.inspect occupants, and
desktop chunk occupants, and
world.inspect occupants, and
explore hall occupants, and
STOMP / well last-event occupant, and
explore occupancy cubes, and
desktop last-event occupant, and
explore occupancy tint, and
world.inspect stands, and
chunk.inspect stands, and
desktop chunk stands, and
explore hall stands, and
world.inspect ACL, and
desktop inspect ACL, and
explore hall ACL, and
block.inspect ACL, and
observe ACL, and
door.inspect ACL, and
trap.inspect ACL, and
portal.inspect ACL, and
npc.inspect ACL, and
parcel.grant, and
parcel.deny, and
parcel.revoke, and
parcel.forgive, and
DAEW v10 ACL persist, and
ParcelGate on block.place and
block.remove, and
door.open and
door.close, and
stamp.apply, and
grant/deny verbs, and
well grant verb, and
well door actor, and
well remove actor, and
well stamp actor, and
well place actor, and
well grant actor, and
ParcelGate on trap.arm and
trap.disarm, and
trap REST actor, and
well trap actor, and
ParcelGate on portal.open and
portal.seal, and
portal REST actor, and
well portal actor, and
ParcelGate on npc.talk and
npc.hush, and
NPC REST actor, and
well NPC actor, and
well builder result, and
desktop builder result, and
explore hall last drive, and
well inspect drive, and
DAEW last drive, and
persist denied drive, and
well inspect drive actor, and
explore hall last drive actor, and
desktop last drive actor, and
DAEW last drive actor, and
well builder last actor, and
well inspect drive at, and
DAEW last drive at, and
explore hall last drive at, and
desktop last drive at, and
well builder last at, and
block inspect last drive, and
observe last drive, and
trap inspect last drive, and
door inspect last drive, and
portal inspect last drive, and
npc inspect last drive, and
chunk inspect last drive, and
well chunk last drive, and
desktop chunk last drive, and
chunk inspect last at, and
well chunk last at, and
desktop chunk last at, and
observe last drive at, and
block inspect last at, and
door inspect last at, and
trap inspect last at, and
portal inspect last at, and
npc inspect last at, and
well occupancy last at, and
STOMP last-event last drive, and
well last-event last drive, and
desktop last-event last drive, and
parcel.revoke, and
parcel.forgive, and
parcel.release, and
World builder actor, and
builder trace actor, and
REST trace actor, and
REST trace at, and
seed trace from last drive, and
living slab last drive, and
living slab last event, and
living slab keeps occupancy, and
living persist moves the store, and
living slab stays in bounds, and
parcel directory names the slab box, and
stamp apply names the slab box, and
stamp apply keeps occupancy, and
block inspect names the slab box, and
living slab clears leftover, and
living slab clears leftover height, and
door inspect names the slab box, and
trap inspect names the slab box, and
portal inspect names the slab box, and
npc inspect names the slab box, and
stamp skip and inspect share occupants, and
door inspect names the slab maze, and
trap inspect names the slab maze, and
portal inspect names the slab maze, and
npc inspect names the slab maze, and
door inspect names the slab lease, and
trap inspect names the slab lease, and
portal inspect names the slab lease, and
npc inspect names the slab lease, and
observe names the slab lease, and
observe names the slab maze, and
chunk inspect names overlapping mazes, and
chunk inspect names overlapping leases, and
chunk inspect names overlapping ACLs, and
parcel list names each plot ACL, and
stamp names the slab maze, and
lease names the slab maze, and
release names the remaining maze, and
grant names the slab maze, and
deny names the slab maze, and
revoke names the slab maze, and
forgive names the slab maze, and
grant names the slab lease, and
deny names the slab lease, and
revoke names the slab lease, and
forgive names the slab lease, and
stamp names the slab place, and
lease names the slab place, and
release names the remaining place, and
grant names the slab place, and
deny names the slab place, and
revoke names the slab place, and
forgive names the slab place, and
stamp names the slab lot, and
lease names the slab lot, and
release names the remaining lot, and
grant names the slab lot, and
deny names the slab lot, and
revoke names the slab lot, and
forgive names the slab lot, and
grant names the slab box, and
deny names the slab box, and
revoke names the slab box, and
forgive names the slab box
are shipped.
Next: WebGL / terrain (NOT NOW). Market provider on those strings later.
WorldService still does not open the maze Caffeine cache.

---

## 7. Acceptance — architecture (this audit)

- [x] World Zero KEEP / dual model restated
- [x] Stamp vs plugin decided (core `StampOps`)
- [x] Parcel vs implicit world-zero decided (explicit record at first stamp)
- [x] Living slab is maze-sourced, not a second living engine
- [x] Second observer is a proof of existing STOMP, not a new bus
- [x] Well panel does not replace `/`
- [x] Explore voxel view does not replace extrusion
- [x] Permissions / plugins / agents / WebGL / terrain slotted; agent client shipped
- [x] First code slice named in §8
- [ ] World One **code** — not this audit

---

## 8. First implementation slice (after the user asks)

**Do not start this slice in the architecture goal.** When implementation is requested, add only:

- `daedalus-core/src/main/java/com/daedalus/world/Parcel.java`
- `daedalus-core/src/main/java/com/daedalus/world/ParcelId.java`
- `daedalus-core/src/main/java/com/daedalus/world/stamp/StampOps.java`
- `daedalus-core/src/main/java/com/daedalus/world/stamp/StampRequest.java`
- `daedalus-core/src/main/java/com/daedalus/world/stamp/StampResult.java`
- `daedalus-core/src/test/java/com/daedalus/world/stamp/StampOpsTest.java`

Prove:

1. A tiny generated (or fixture) `MazeGrid` writes floor + wall posts into `world-zero` at a chosen origin
2. Cubes outside the maze rectangle stay AIR
3. A second overlapping stamp returns `PARCEL_OVERLAP` and does not mutate
4. Restart via `WorldStore` reloads the same occupied cubes (extend DAEW only if needed; if the current snapshot already stores all chunks, parcel metadata may be derived or version-bumped in the same slice)
5. Stamp bumps revision; a no-op overlap failure does not
6. Generators and solvers are not edited

Forbidden in W1.1:

- Living slab
- REST stamp route (unless tests cannot host a grid without it — prefer core fixture)
- Well / desktop / explore edits
- Permissions, door-on-start, new block types
- Blockchain, WebGL, terrain

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Stamp rewrites `MazeGrid` into 3D | Forbidden. Projection only. |
| Living ticks on voxels fork the engine | Slab is a subscriber. |
| Well panel becomes the homepage | `/` stays maze. |
| Explore mesh reuse “to save time” | Second mesher. |
| Observer work rebuilds messaging | Use existing world topics. |
| Viewing CSS mixed into stamp commits | Do not stage `index.html` paint on W1 slices. |
| Scope jump to NPCs / shops | §2 NOT NOW / DEFER. |

---

## 10. Audit answers

1. **What World One is.** Composition: maze DNA stamped into the World Zero volume, then observers and clients that already exist learn to watch it.
2. **What stays.** Everything KEEP. World Zero APIs stay. Door and accounting stay.
3. **What is adapted.** Core stamp + parcel; living as a slab writer; STOMP proof; well panel; explore second mesh.
4. **What is retired.** Nothing.
5. **What is not now.** WebGL client, shops, terrain, permission engine, trap/portal/NPC, wearables, NFT display, plot market, photoreal cities. Those last three providers stay Ethereum-on-strings. City look is a later renderer: honest distant stamps, inspired place names — no stub LOD, no GIS import.
6. **Smallest path.** §6 W1.1 → W1.5.
7. **Exact first code slice.** §8 file list. Stop there until the next ask.

Phase 0 remains the World Zero record. This file is the World One record. Do not merge them; World Zero acceptance must stay auditable.
